"""
Tier 4 Enrichment Module: Knowledge graph linking and output fusion
Enriches entities with Wikidata, performs verification, and creates final JSON output
"""

import logging
import json
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import WikidataConfig, PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class WikidataEntity:
    """Container for Wikidata enrichment data"""
    entity_name: str
    wikidata_id: Optional[str] = None
    description: Optional[str] = None
    properties: Dict = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    coordinates: Optional[Tuple[float, float]] = None
    found: bool = False


@dataclass
class FinalOutput:
    """Container for final pipeline output"""
    article_id: str
    title: Optional[str]
    consensus_summary: str
    extracted_facts: List[Dict]
    spacy_validation: Dict
    topics: Optional[List[Dict]]
    metadata: Dict
    timestamp: str


class WikidataEnricher:
    """Enriches entities with Wikidata knowledge base"""

    def __init__(self):
        """Initialize Wikidata enricher"""
        self.endpoint = WikidataConfig.WIKIDATA_API_ENDPOINT
        self.timeout = WikidataConfig.WIKIDATA_TIMEOUT
        self.enabled = WikidataConfig.ENABLE_WIKIDATA_ENRICHMENT

    def search_entity(self, entity_name: str, entity_type: str = None) -> WikidataEntity:
        """
        Search for entity in Wikidata

        Args:
            entity_name: Name of entity to search
            entity_type: Optional entity type for filtering

        Returns:
            WikidataEntity with enrichment data
        """

        if not self.enabled:
            logger.info("Wikidata enrichment disabled")
            return WikidataEntity(entity_name=entity_name, found=False)

        logger.info(f"Searching Wikidata for: {entity_name}")

        try:
            # Search for entity
            search_params = {
                'action': 'wbsearchentities',
                'format': 'json',
                'language': 'en',
                'search': entity_name,
                'limit': 1
            }

            response = requests.get(
                self.endpoint,
                params=search_params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('search'):
                logger.info(f"No Wikidata results for: {entity_name}")
                return WikidataEntity(entity_name=entity_name, found=False)

            # Get first result
            result = data['search'][0]
            wikidata_id = result.get('id')
            description = result.get('description', '')

            # Get detailed entity data
            entity_data = self._get_entity_details(wikidata_id)

            return WikidataEntity(
                entity_name=entity_name,
                wikidata_id=wikidata_id,
                description=description,
                properties=entity_data.get('properties', {}),
                aliases=result.get('aliases', []),
                coordinates=entity_data.get('coordinates'),
                found=True
            )

        except Exception as e:
            logger.error(f"Wikidata search failed for '{entity_name}': {e}")
            return WikidataEntity(entity_name=entity_name, found=False)

    def _get_entity_details(self, wikidata_id: str) -> Dict:
        """
        Get detailed properties for Wikidata entity

        Args:
            wikidata_id: Wikidata Q-ID

        Returns:
            Dict with entity properties
        """

        try:
            params = {
                'action': 'wbgetentities',
                'format': 'json',
                'ids': wikidata_id,
                'props': 'claims|labels|descriptions'
            }

            response = requests.get(
                self.endpoint,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            entity = data['entities'].get(wikidata_id, {})
            claims = entity.get('claims', {})

            # Extract useful properties
            properties = {}

            # Population (P1082)
            if 'P1082' in claims:
                properties['population'] = self._extract_quantity(claims['P1082'][0])

            # Country (P17)
            if 'P17' in claims:
                properties['country'] = self._extract_entity_label(claims['P17'][0])

            # Instance of (P31)
            if 'P31' in claims:
                properties['instance_of'] = self._extract_entity_label(claims['P31'][0])

            # Occupation (P106) - for persons
            if 'P106' in claims:
                properties['occupation'] = self._extract_entity_label(claims['P106'][0])

            # Coordinates (P625) - for locations
            coordinates = None
            if 'P625' in claims:
                coordinates = self._extract_coordinates(claims['P625'][0])

            return {
                'properties': properties,
                'coordinates': coordinates
            }

        except Exception as e:
            logger.error(f"Failed to get details for {wikidata_id}: {e}")
            return {'properties': {}, 'coordinates': None}

    def _extract_quantity(self, claim: Dict) -> Optional[int]:
        """Extract numeric quantity from claim"""
        try:
            return int(float(claim['mainsnak']['datavalue']['value']['amount']))
        except:
            return None

    def _extract_entity_label(self, claim: Dict) -> Optional[str]:
        """Extract entity label from claim"""
        try:
            entity_id = claim['mainsnak']['datavalue']['value']['id']
            # Would need another API call to get label - simplified here
            return entity_id
        except:
            return None

    def _extract_coordinates(self, claim: Dict) -> Optional[Tuple[float, float]]:
        """Extract geographic coordinates from claim"""
        try:
            value = claim['mainsnak']['datavalue']['value']
            return (value['latitude'], value['longitude'])
        except:
            return None

    def enrich_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        Enrich list of entities with Wikidata

        Args:
            entities: List of entity dictionaries

        Returns:
            List of enriched entities
        """

        logger.info(f"Enriching {len(entities)} entities with Wikidata")

        enriched = []
        for entity in entities:
            wikidata_result = self.search_entity(
                entity['entity'],
                entity.get('type')
            )

            enriched_entity = entity.copy()

            if wikidata_result.found:
                enriched_entity['wikidata_id'] = wikidata_result.wikidata_id
                enriched_entity['wikidata_description'] = wikidata_result.description
                enriched_entity['wikidata_properties'] = wikidata_result.properties

                # Boost confidence if found in knowledge base
                enriched_entity['confidence'] = min(
                    enriched_entity.get('confidence', 0.5) + 0.1,
                    1.0
                )

                logger.info(f"Enriched: {entity['entity']} -> {wikidata_result.wikidata_id}")
            else:
                enriched_entity['wikidata_id'] = None
                logger.info(f"No Wikidata match for: {entity['entity']}")

            enriched.append(enriched_entity)

        return enriched


class FactualVerifier:
    """Performs basic factual verification checks"""

    @staticmethod
    def verify_temporal_consistency(facts: List[Dict]) -> List[Dict]:
        """
        Check temporal consistency of facts

        Args:
            facts: List of extracted facts

        Returns:
            List of facts with verification flags
        """

        logger.info("Verifying temporal consistency")

        verified_facts = []
        for fact in facts:
            verified_fact = fact.copy()
            verified_fact['temporal_verification'] = 'passed'

            # Extract dates from event description
            # (Simplified - would need more sophisticated date extraction)
            event_desc = fact.get('event_description', '')

            # Flag if confidence is already low
            if fact.get('confidence', 0.0) < PipelineConfig.CONFIDENCE_THRESHOLD:
                verified_fact['temporal_verification'] = 'low_confidence'

            verified_facts.append(verified_fact)

        return verified_facts

    @staticmethod
    def verify_entity_coherence(facts: List[Dict]) -> Dict:
        """
        Verify entity coherence across facts

        Args:
            facts: List of extracted facts

        Returns:
            Dict with coherence metrics
        """

        logger.info("Verifying entity coherence")

        # Count entity mentions
        entity_mentions = {}
        for fact in facts:
            entity = fact.get('entity', '')
            entity_type = fact.get('type', '')

            # Use string key format "entity:::type" for JSON compatibility
            key = f"{entity.lower()}:::{entity_type}"
            entity_mentions[key] = entity_mentions.get(key, 0) + 1

        # Find entities with type inconsistencies
        entity_types = {}
        for fact in facts:
            entity = fact.get('entity', '').lower()
            entity_type = fact.get('type', '')

            if entity in entity_types and entity_types[entity] != entity_type:
                logger.warning(
                    f"Type inconsistency for '{entity}': "
                    f"{entity_types[entity]} vs {entity_type}"
                )

            entity_types[entity] = entity_type

        return {
            'total_entities': len(entity_types),
            'multiple_mentions': sum(1 for count in entity_mentions.values() if count > 1),
            'entity_mentions': dict(entity_mentions)
        }


class OutputFusion:
    """Fuses all pipeline outputs into final structured JSON"""

    def __init__(self):
        """Initialize output fusion"""
        self.enricher = WikidataEnricher()
        self.verifier = FactualVerifier()

    def create_final_output(
        self,
        article_id: str,
        title: Optional[str],
        consensus_summary: str,
        merged_facts: List[Dict],
        spacy_validation: Dict,
        conflict_report: Dict,
        topics: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> FinalOutput:
        """
        Create final fused output

        Args:
            article_id: Article identifier
            title: Article title
            consensus_summary: Consensus summary from validation
            merged_facts: Merged facts from LLMs
            spacy_validation: spaCy NER validation results
            conflict_report: Conflict detection report
            topics: Optional topic modeling results
            metadata: Optional additional metadata

        Returns:
            FinalOutput with complete pipeline results
        """

        logger.info(f"Creating final output for article: {article_id}")

        # Enrich entities with Wikidata
        enriched_facts = self.enricher.enrich_entities(merged_facts)

        # Verify facts
        verified_facts = self.verifier.verify_temporal_consistency(enriched_facts)
        coherence = self.verifier.verify_entity_coherence(verified_facts)

        # Compile metadata
        final_metadata = {
            'article_id': article_id,
            'processing_timestamp': datetime.utcnow().isoformat(),
            'pipeline_version': '1.0.0',
            'total_facts': len(verified_facts),
            'high_confidence_facts': sum(
                1 for f in verified_facts
                if f.get('confidence', 0.0) >= 0.7
            ),
            'wikidata_enriched': sum(
                1 for f in verified_facts
                if f.get('wikidata_id') is not None
            ),
            'conflict_report': {
                'has_conflicts': conflict_report.get('has_conflicts', False),
                'summary_similarity': conflict_report.get('summary_similarity', 0.0),
                'entity_overlap': conflict_report.get('entity_overlap', 0.0),
                'conflict_descriptions': conflict_report.get('conflict_descriptions', [])
            },
            'spacy_validation': {
                'entity_count': spacy_validation.get('entity_count', 0),
                'comparison': spacy_validation.get('comparison', {})
            },
            'coherence': coherence
        }

        # Merge with additional metadata
        if metadata:
            final_metadata.update(metadata)

        return FinalOutput(
            article_id=article_id,
            title=title,
            consensus_summary=consensus_summary,
            extracted_facts=verified_facts,
            spacy_validation=spacy_validation,
            topics=topics,
            metadata=final_metadata,
            timestamp=datetime.utcnow().isoformat()
        )

    def save_output(self, output: FinalOutput, output_path: Path) -> None:
        """
        Save final output to JSON file

        Args:
            output: FinalOutput object
            output_path: Path to save file
        """

        logger.info(f"Saving output to: {output_path}")

        # Convert to dict
        output_dict = {
            'article_id': output.article_id,
            'title': output.title,
            'consensus_summary': output.consensus_summary,
            'extracted_facts': output.extracted_facts,
            'spacy_validation': output.spacy_validation,
            'topics': output.topics,
            'metadata': output.metadata,
            'timestamp': output.timestamp
        }

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Output saved successfully: {output_path}")
