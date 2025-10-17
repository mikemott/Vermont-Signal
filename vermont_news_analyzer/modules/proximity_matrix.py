"""
Proximity-Weighted Co-occurrence Matrix Builder
Generates entity relationship matrices based on sentence-level proximity
"""

import logging
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CooccurrenceData:
    """Container for co-occurrence statistics"""
    entity_a: str
    entity_b: str
    total_weight: float
    occurrences: List[Dict] = field(default_factory=list)
    min_distance: int = 999
    max_distance: int = 0
    avg_distance: float = 0.0
    same_sentence_count: int = 0
    adjacent_sentence_count: int = 0
    near_proximity_count: int = 0


class ProximityMatrix:
    """
    Builds proximity-weighted co-occurrence matrices from entities with positions

    Weights:
    - Same sentence (distance=0): weight 3
    - Adjacent sentences (distance=1): weight 2
    - Near proximity (distance=2+): weight 1
    """

    def __init__(self, window_size: int = 2):
        """
        Initialize proximity matrix builder

        Args:
            window_size: Sentence window for co-occurrence
                        0 = same sentence only
                        1 = same or adjacent sentences (±1)
                        2 = within ±2 sentences (default)
        """
        self.window_size = window_size

    def build_matrix(
        self,
        entities: List[Dict],
        article_id: Optional[int] = None
    ) -> Dict[Tuple[str, str], CooccurrenceData]:
        """
        Build proximity-weighted co-occurrence matrix for a single article

        Args:
            entities: List of entity dicts with position information
                     Required fields: entity, type, sentence_index, confidence
            article_id: Optional article ID for logging

        Returns:
            Dictionary mapping (entity_a, entity_b) tuples to CooccurrenceData
        """
        # Filter entities with valid positions
        valid_entities = [
            e for e in entities
            if e.get('sentence_index') is not None
        ]

        if not valid_entities:
            logger.warning(f"Article {article_id}: No entities with position data")
            return {}

        # Group entities by sentence
        entities_by_sentence = defaultdict(list)
        for entity in valid_entities:
            sent_idx = entity['sentence_index']
            entities_by_sentence[sent_idx].append(entity)

        # Build co-occurrence matrix
        co_matrix = {}

        # Get sorted sentence indices
        sentence_indices = sorted(entities_by_sentence.keys())

        # For each sentence
        for i, sent_idx in enumerate(sentence_indices):
            entities_i = entities_by_sentence[sent_idx]

            # Define window bounds
            window_start = max(0, i - self.window_size)
            window_end = min(len(sentence_indices), i + self.window_size + 1)

            # For each entity in current sentence
            for entity_a in entities_i:
                # Look at entities in window
                for j in range(window_start, window_end):
                    sent_idx_j = sentence_indices[j]

                    for entity_b in entities_by_sentence[sent_idx_j]:
                        # Skip self-connections
                        if entity_a['entity'] == entity_b['entity']:
                            continue

                        # Create ordered pair (alphabetical to avoid duplicates)
                        pair = tuple(sorted([entity_a['entity'], entity_b['entity']]))

                        # Calculate sentence distance
                        distance = abs(sent_idx - sent_idx_j)

                        # Skip if outside window
                        if distance > self.window_size:
                            continue

                        # Calculate proximity weight
                        # Weight: 3 for same sentence, 2 for adjacent, 1 for within window
                        if distance == 0:
                            weight = 3.0
                        elif distance == 1:
                            weight = 2.0
                        else:
                            weight = 1.0

                        # Initialize or update co-occurrence data
                        if pair not in co_matrix:
                            co_matrix[pair] = CooccurrenceData(
                                entity_a=pair[0],
                                entity_b=pair[1],
                                total_weight=0,
                                occurrences=[],
                                min_distance=999,
                                max_distance=0
                            )

                        co_data = co_matrix[pair]
                        co_data.total_weight += weight
                        co_data.min_distance = min(co_data.min_distance, distance)
                        co_data.max_distance = max(co_data.max_distance, distance)

                        # Count by proximity category
                        if distance == 0:
                            co_data.same_sentence_count += 1
                        elif distance == 1:
                            co_data.adjacent_sentence_count += 1
                        else:
                            co_data.near_proximity_count += 1

                        # Store occurrence details
                        co_data.occurrences.append({
                            'article_id': article_id,
                            'sentence_index': sent_idx,
                            'distance': distance,
                            'weight': weight,
                            'confidence_a': entity_a.get('confidence', 1.0),
                            'confidence_b': entity_b.get('confidence', 1.0)
                        })

        # Calculate average distances
        for pair, data in co_matrix.items():
            if data.occurrences:
                data.avg_distance = sum(o['distance'] for o in data.occurrences) / len(data.occurrences)

        logger.info(
            f"Article {article_id}: Built co-occurrence matrix with "
            f"{len(co_matrix)} entity pairs from {len(valid_entities)} entities"
        )

        return co_matrix

    def calculate_entity_frequencies(
        self,
        entities: List[Dict]
    ) -> Dict[str, int]:
        """
        Calculate how many sentences each entity appears in

        Args:
            entities: List of entity dicts with sentence_index

        Returns:
            Dictionary mapping entity names to sentence counts
        """
        entity_sentences = defaultdict(set)

        for entity in entities:
            if entity.get('sentence_index') is not None:
                entity_sentences[entity['entity']].add(entity['sentence_index'])

        # Convert to counts
        return {entity: len(sentences) for entity, sentences in entity_sentences.items()}

    def filter_by_weight(
        self,
        co_matrix: Dict[Tuple[str, str], CooccurrenceData],
        min_weight: float = 2.0
    ) -> Dict[Tuple[str, str], CooccurrenceData]:
        """
        Filter co-occurrence matrix by minimum total weight

        Args:
            co_matrix: Co-occurrence matrix
            min_weight: Minimum total weight to keep

        Returns:
            Filtered matrix
        """
        return {
            pair: data
            for pair, data in co_matrix.items()
            if data.total_weight >= min_weight
        }

    def get_relationship_type(self, data: CooccurrenceData) -> str:
        """
        Determine relationship type based on proximity pattern

        Args:
            data: CooccurrenceData object

        Returns:
            Relationship type string
        """
        if data.same_sentence_count > 0:
            return 'same-sentence'
        elif data.adjacent_sentence_count > 0:
            return 'adjacent-sentence'
        elif data.near_proximity_count > 0:
            return 'near-proximity'
        else:
            return 'cross-article'

    def format_relationship_description(self, data: CooccurrenceData) -> str:
        """
        Generate human-readable relationship description

        Args:
            data: CooccurrenceData object

        Returns:
            Description string
        """
        rel_type = self.get_relationship_type(data)

        if rel_type == 'same-sentence':
            return f"Appear together in same sentence ({data.same_sentence_count} times, weight: {data.total_weight:.1f})"
        elif rel_type == 'adjacent-sentence':
            return f"Appear in adjacent sentences ({data.adjacent_sentence_count} times, weight: {data.total_weight:.1f})"
        elif rel_type == 'near-proximity':
            return f"Appear nearby (avg distance: {data.avg_distance:.1f} sentences, weight: {data.total_weight:.1f})"
        else:
            return f"Appear in article (weight: {data.total_weight:.1f})"

    def get_statistics(self, co_matrix: Dict[Tuple[str, str], CooccurrenceData]) -> Dict:
        """
        Calculate summary statistics for co-occurrence matrix

        Args:
            co_matrix: Co-occurrence matrix

        Returns:
            Dictionary with statistics
        """
        if not co_matrix:
            return {
                'total_pairs': 0,
                'same_sentence': 0,
                'adjacent_sentence': 0,
                'near_proximity': 0,
                'avg_weight': 0.0,
                'max_weight': 0.0,
                'min_weight': 0.0
            }

        weights = [data.total_weight for data in co_matrix.values()]

        return {
            'total_pairs': len(co_matrix),
            'same_sentence': sum(1 for d in co_matrix.values() if d.same_sentence_count > 0),
            'adjacent_sentence': sum(1 for d in co_matrix.values() if d.adjacent_sentence_count > 0 and d.same_sentence_count == 0),
            'near_proximity': sum(1 for d in co_matrix.values() if d.near_proximity_count > 0 and d.same_sentence_count == 0 and d.adjacent_sentence_count == 0),
            'avg_weight': sum(weights) / len(weights),
            'max_weight': max(weights),
            'min_weight': min(weights)
        }
