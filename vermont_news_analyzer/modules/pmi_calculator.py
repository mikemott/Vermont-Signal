"""
Pointwise Mutual Information (PMI) Calculator
Calculates statistical significance of entity co-occurrences with hybrid scoring
"""

import logging
import math
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PMIScore:
    """Container for PMI calculation results"""
    entity_a: str
    entity_b: str
    pmi: Optional[float]  # Raw PMI (unbounded), None for rare entities
    npmi: Optional[float]  # Normalized PMI (range: -1 to 1), None for rare entities
    pmi_score: float  # Final scoring metric (hybrid: PMI or proximity-based)
    p_xy: float  # Joint probability
    p_x: float  # Marginal probability of entity_a
    p_y: float  # Marginal probability of entity_b
    raw_count: int  # Raw co-occurrence count
    is_rare_entity: bool = False  # True if using proximity-only scoring
    scoring_method: str = "pmi"  # "pmi" or "proximity-only"


class PMICalculator:
    """
    Calculates Pointwise Mutual Information for entity pairs with hybrid scoring

    PMI measures how much more often two entities appear together than
    would be expected by chance if they were independent.

    PMI = log(P(x,y) / (P(x) * P(y)))

    High PMI (> 0): Entities appear together more than random chance
    PMI ≈ 0: Entities appear independently
    Low PMI (< 0): Entities avoid each other (rare in same article)

    NPMI normalizes to range [-1, 1] for easier interpretation.

    HYBRID SCORING:
    - Entities appearing in 2+ articles each: Full PMI scoring
    - Entities where at least one appears in only 1 article: Proximity-only scoring
      (avoids unstable PMI for rare entities)
    """

    def __init__(self, smoothing: float = 1e-6, min_frequency_for_pmi: int = 2):
        """
        Initialize PMI calculator

        Args:
            smoothing: Laplace smoothing factor to avoid log(0)
            min_frequency_for_pmi: Minimum entity frequency to use PMI scoring
                                   (entities below this use proximity-only)
        """
        self.smoothing = smoothing
        self.min_frequency_for_pmi = min_frequency_for_pmi

    def calculate_corpus_frequencies(
        self,
        article_entities: Dict[int, list]
    ) -> Tuple[Dict[str, int], int]:
        """
        Calculate entity frequencies across entire corpus

        Args:
            article_entities: Dict mapping article_id to list of entity dicts

        Returns:
            Tuple of (entity_frequency_dict, total_documents)
        """
        entity_freq = defaultdict(set)  # entity -> set of article IDs

        for article_id, entities in article_entities.items():
            seen_entities = set()
            for entity in entities:
                entity_name = entity['entity']
                if entity_name not in seen_entities:
                    entity_freq[entity_name].add(article_id)
                    seen_entities.add(entity_name)

        # Convert sets to counts
        entity_counts = {entity: len(article_ids) for entity, article_ids in entity_freq.items()}
        total_docs = len(article_entities)

        logger.info(f"Calculated corpus frequencies: {len(entity_counts)} unique entities across {total_docs} articles")

        return entity_counts, total_docs

    def should_use_pmi(
        self,
        entity_freq_a: int,
        entity_freq_b: int
    ) -> bool:
        """
        Determine if PMI scoring should be used for this entity pair

        Args:
            entity_freq_a: Frequency of entity A
            entity_freq_b: Frequency of entity B

        Returns:
            True if both entities are frequent enough for stable PMI
        """
        return (entity_freq_a >= self.min_frequency_for_pmi and
                entity_freq_b >= self.min_frequency_for_pmi)

    def calculate_pmi(
        self,
        entity_a: str,
        entity_b: str,
        cooccurrence_count: int,
        entity_freq_a: int,
        entity_freq_b: int,
        total_documents: int,
        confidence_a: float = 1.0,
        confidence_b: float = 1.0,
        proximity_weight: float = 0.0
    ) -> PMIScore:
        """
        Calculate PMI score for an entity pair with hybrid scoring

        Args:
            entity_a: First entity name
            entity_b: Second entity name
            cooccurrence_count: Number of documents where they co-occur
            entity_freq_a: Number of documents containing entity_a
            entity_freq_b: Number of documents containing entity_b
            total_documents: Total number of documents in corpus
            confidence_a: Confidence score for entity_a (0-1)
            confidence_b: Confidence score for entity_b (0-1)
            proximity_weight: Proximity weight for rare entity fallback

        Returns:
            PMIScore object with all calculated metrics
        """
        # Calculate probabilities with smoothing
        p_xy = (cooccurrence_count + self.smoothing) / (total_documents + self.smoothing)
        p_x = (entity_freq_a + self.smoothing) / (total_documents + self.smoothing)
        p_y = (entity_freq_b + self.smoothing) / (total_documents + self.smoothing)

        # Check if we should use PMI or proximity-only scoring
        use_pmi = self.should_use_pmi(entity_freq_a, entity_freq_b)

        if use_pmi:
            # Full PMI calculation
            pmi = math.log(p_xy / (p_x * p_y + self.smoothing) + self.smoothing)

            # Normalized PMI (bounds to [-1, 1])
            # NPMI = PMI / -log(P(x,y))
            npmi = pmi / (-math.log(p_xy + self.smoothing) + self.smoothing)

            # Confidence-adjusted PMI
            avg_confidence = (confidence_a + confidence_b) / 2.0
            adjusted_pmi = pmi * avg_confidence

            return PMIScore(
                entity_a=entity_a,
                entity_b=entity_b,
                pmi=pmi,
                npmi=npmi,
                pmi_score=adjusted_pmi,
                p_xy=p_xy,
                p_x=p_x,
                p_y=p_y,
                raw_count=cooccurrence_count,
                is_rare_entity=False,
                scoring_method="pmi"
            )
        else:
            # Proximity-only scoring for rare entities
            # Use proximity weight + confidence as the score
            avg_confidence = (confidence_a + confidence_b) / 2.0
            proximity_score = proximity_weight * avg_confidence

            logger.debug(
                f"Using proximity-only scoring for {entity_a} ↔ {entity_b} "
                f"(freq_a={entity_freq_a}, freq_b={entity_freq_b})"
            )

            return PMIScore(
                entity_a=entity_a,
                entity_b=entity_b,
                pmi=None,  # No PMI for rare entities
                npmi=None,
                pmi_score=proximity_score,
                p_xy=p_xy,
                p_x=p_x,
                p_y=p_y,
                raw_count=cooccurrence_count,
                is_rare_entity=True,
                scoring_method="proximity-only"
            )

    def calculate_pmi_batch(
        self,
        cooccurrence_matrix: Dict[Tuple[str, str], Dict],
        entity_frequencies: Dict[str, int],
        total_documents: int
    ) -> Dict[Tuple[str, str], PMIScore]:
        """
        Calculate PMI for multiple entity pairs with hybrid scoring

        Args:
            cooccurrence_matrix: Dict mapping (entity_a, entity_b) to co-occurrence data
                                Expected keys: 'count', 'confidence_a', 'confidence_b', 'proximity_weight'
            entity_frequencies: Dict mapping entity names to document frequencies
            total_documents: Total number of documents

        Returns:
            Dict mapping entity pairs to PMIScore objects
        """
        pmi_scores = {}
        pmi_count = 0
        proximity_count = 0

        for (entity_a, entity_b), cooc_data in cooccurrence_matrix.items():
            # Extract data
            cooc_count = cooc_data.get('count', 0)
            conf_a = cooc_data.get('confidence_a', 1.0)
            conf_b = cooc_data.get('confidence_b', 1.0)
            proximity_weight = cooc_data.get('proximity_weight', 0.0)

            # Get entity frequencies
            freq_a = entity_frequencies.get(entity_a, 1)  # Default to 1 if not found
            freq_b = entity_frequencies.get(entity_b, 1)

            # Calculate PMI (hybrid)
            pmi_score = self.calculate_pmi(
                entity_a, entity_b,
                cooc_count,
                freq_a, freq_b,
                total_documents,
                conf_a, conf_b,
                proximity_weight
            )

            pmi_scores[(entity_a, entity_b)] = pmi_score

            if pmi_score.is_rare_entity:
                proximity_count += 1
            else:
                pmi_count += 1

        logger.info(
            f"Calculated scores for {len(pmi_scores)} entity pairs: "
            f"{pmi_count} PMI-scored, {proximity_count} proximity-only"
        )

        return pmi_scores

    def filter_by_pmi_threshold(
        self,
        pmi_scores: Dict[Tuple[str, str], PMIScore],
        min_pmi: float = 0.0,
        use_npmi: bool = True
    ) -> Dict[Tuple[str, str], PMIScore]:
        """
        Filter entity pairs by PMI threshold

        Args:
            pmi_scores: Dict of PMI scores
            min_pmi: Minimum PMI/NPMI threshold
            use_npmi: Whether to use NPMI (normalized) or raw PMI

        Returns:
            Filtered dict
        """
        filtered = {}

        for pair, score in pmi_scores.items():
            # For rare entities (proximity-only), always include if score > 0
            if score.is_rare_entity:
                if score.pmi_score > 0:
                    filtered[pair] = score
            else:
                # For PMI-scored entities, apply threshold
                if use_npmi:
                    if score.npmi is not None and score.npmi >= min_pmi:
                        filtered[pair] = score
                else:
                    if score.pmi is not None and score.pmi >= min_pmi:
                        filtered[pair] = score

        return filtered

    def get_pmi_statistics(
        self,
        pmi_scores: Dict[Tuple[str, str], PMIScore]
    ) -> Dict:
        """
        Calculate summary statistics for PMI scores

        Args:
            pmi_scores: Dict of PMI scores

        Returns:
            Dict with statistics
        """
        if not pmi_scores:
            return {
                'count': 0,
                'pmi_scored': 0,
                'proximity_scored': 0,
                'min_pmi': 0,
                'max_pmi': 0,
                'mean_pmi': 0,
                'min_npmi': 0,
                'max_npmi': 0,
                'mean_npmi': 0
            }

        pmi_scored = [s for s in pmi_scores.values() if not s.is_rare_entity]
        proximity_scored = [s for s in pmi_scores.values() if s.is_rare_entity]

        pmis = [s.pmi for s in pmi_scored if s.pmi is not None]
        npmis = [s.npmi for s in pmi_scored if s.npmi is not None]

        return {
            'count': len(pmi_scores),
            'pmi_scored': len(pmi_scored),
            'proximity_scored': len(proximity_scored),
            'min_pmi': min(pmis) if pmis else 0,
            'max_pmi': max(pmis) if pmis else 0,
            'mean_pmi': sum(pmis) / len(pmis) if pmis else 0,
            'min_npmi': min(npmis) if npmis else 0,
            'max_npmi': max(npmis) if npmis else 0,
            'mean_npmi': sum(npmis) / len(npmis) if npmis else 0
        }
