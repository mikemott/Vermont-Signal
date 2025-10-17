"""
Confidence-Driven Edge Weighting
Adjusts relationship strength based on entity confidence scores
"""

import logging
from typing import List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceMode(Enum):
    """Confidence weighting strategies"""
    MULTIPLY = 'multiply'  # strength = score × conf_a × conf_b
    HARMONIC = 'harmonic'  # strength = score × harmonic_mean(conf_a, conf_b)
    MINIMUM = 'minimum'    # strength = score × min(conf_a, conf_b)
    AVERAGE = 'average'    # strength = score × (conf_a + conf_b) / 2


class ConfidenceWeighter:
    """
    Applies confidence-based weighting to relationship strengths
    """

    @staticmethod
    def calculate_confidence_weight(
        confidence_a: float,
        confidence_b: float,
        mode: ConfidenceMode = ConfidenceMode.HARMONIC
    ) -> float:
        """
        Calculate confidence weight for an entity pair

        Args:
            confidence_a: Confidence score for entity A (0-1)
            confidence_b: Confidence score for entity B (0-1)
            mode: Weighting strategy

        Returns:
            Confidence weight (0-1)
        """
        if mode == ConfidenceMode.MULTIPLY:
            # Multiplicative: Harshly penalizes low confidence
            return confidence_a * confidence_b

        elif mode == ConfidenceMode.HARMONIC:
            # Harmonic mean: More forgiving than multiply
            if confidence_a == 0 or confidence_b == 0:
                return 0
            return 2 / (1/confidence_a + 1/confidence_b)

        elif mode == ConfidenceMode.MINIMUM:
            # Weakest link: Only as strong as weakest entity
            return min(confidence_a, confidence_b)

        elif mode == ConfidenceMode.AVERAGE:
            # Simple average
            return (confidence_a + confidence_b) / 2.0

        return 1.0

    @staticmethod
    def apply_confidence_weighting(
        score: float,
        confidence_a: float,
        confidence_b: float,
        mode: ConfidenceMode = ConfidenceMode.HARMONIC
    ) -> float:
        """
        Apply confidence weighting to a score

        Args:
            score: Base score (PMI, NPMI, or proximity)
            confidence_a: Confidence for entity A
            confidence_b: Confidence for entity B
            mode: Weighting strategy

        Returns:
            Confidence-weighted score
        """
        conf_weight = ConfidenceWeighter.calculate_confidence_weight(
            confidence_a, confidence_b, mode
        )
        return score * conf_weight

    @staticmethod
    def boost_wikidata_confidence(
        entities: List[Dict],
        boost_amount: float = 0.1,
        max_confidence: float = 1.0
    ) -> List[Dict]:
        """
        Boost confidence for entities with Wikidata validation

        Args:
            entities: List of entity dicts
            boost_amount: Amount to boost confidence (0-0.2 recommended)
            max_confidence: Maximum allowed confidence (default 1.0)

        Returns:
            Same list with boosted confidences
        """
        boosted_count = 0

        for entity in entities:
            if entity.get('wikidata_id'):
                original_conf = entity.get('confidence', 0.5)
                boosted_conf = min(max_confidence, original_conf + boost_amount)

                if boosted_conf > original_conf:
                    entity['confidence'] = boosted_conf
                    entity['confidence_boosted'] = True
                    entity['confidence_boost_amount'] = boosted_conf - original_conf
                    boosted_count += 1

        if boosted_count > 0:
            logger.info(f"Boosted confidence for {boosted_count} Wikidata-validated entities")

        return entities

    @staticmethod
    def filter_by_confidence(
        edges: List[Dict],
        min_entity_confidence: float = 0.6,
        min_relationship_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Filter edges based on confidence thresholds

        Args:
            edges: List of edge dicts with confidence scores
            min_entity_confidence: Minimum confidence for individual entities
            min_relationship_confidence: Minimum for average relationship confidence

        Returns:
            Filtered edges
        """
        filtered = []

        for edge in edges:
            conf_a = edge.get('confidence_a', 1.0)
            conf_b = edge.get('confidence_b', 1.0)
            avg_conf = (conf_a + conf_b) / 2.0

            # Check individual entity confidences
            if conf_a < min_entity_confidence or conf_b < min_entity_confidence:
                continue

            # Check average relationship confidence
            if avg_conf >= min_relationship_confidence:
                filtered.append(edge)

        if len(filtered) < len(edges):
            logger.info(
                f"Confidence filtering: {len(filtered)}/{len(edges)} edges passed "
                f"(min_entity: {min_entity_confidence}, min_relationship: {min_relationship_confidence})"
            )

        return filtered
