"""
Dynamic Thresholding System
Adaptive edge filtering based on article size and network characteristics
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ArticleSize(Enum):
    """Article size categories"""
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'


@dataclass
class ThresholdConfig:
    """Threshold configuration for an article size category"""
    min_npmi: float  # Minimum NPMI score (or min score for proximity-only)
    max_edges_per_entity: int  # Maximum connections per entity
    percentile_cutoff: int  # Percentile for edge filtering (e.g., 80 = keep top 20%)
    description: str


class DynamicThresholder:
    """
    Applies size-aware, adaptive filtering to entity relationship networks

    Strategy:
    1. Categorize article by entity count (small/medium/large)
    2. Apply absolute NPMI/score threshold
    3. Apply percentile-based filtering
    4. Cap per-node degree to prevent hubs

    This prevents:
    - Small articles: Over-filtering that leaves isolated nodes
    - Large articles: "Hairball" networks with too many edges
    """

    # Size boundaries
    SMALL_ARTICLE_THRESHOLD = 10  # entities
    MEDIUM_ARTICLE_THRESHOLD = 25  # entities

    # Threshold configurations by size
    THRESHOLDS = {
        ArticleSize.SMALL: ThresholdConfig(
            min_npmi=0.3,  # More permissive (few entities = need connections)
            max_edges_per_entity=5,
            percentile_cutoff=70,  # Keep top 30%
            description="Small article: permissive filtering to preserve sparse connections"
        ),
        ArticleSize.MEDIUM: ThresholdConfig(
            min_npmi=0.5,  # Moderate filtering
            max_edges_per_entity=8,
            percentile_cutoff=60,  # Keep top 40%
            description="Medium article: balanced filtering"
        ),
        ArticleSize.LARGE: ThresholdConfig(
            min_npmi=0.6,  # Strict filtering
            max_edges_per_entity=10,
            percentile_cutoff=50,  # Keep top 50%
            description="Large article: aggressive filtering to reduce clutter"
        )
    }

    @classmethod
    def determine_article_size(cls, entity_count: int) -> ArticleSize:
        """
        Categorize article by entity count

        Args:
            entity_count: Number of unique entities in article

        Returns:
            ArticleSize enum value
        """
        if entity_count <= cls.SMALL_ARTICLE_THRESHOLD:
            return ArticleSize.SMALL
        elif entity_count <= cls.MEDIUM_ARTICLE_THRESHOLD:
            return ArticleSize.MEDIUM
        else:
            return ArticleSize.LARGE

    @classmethod
    def get_threshold_config(cls, entity_count: int) -> ThresholdConfig:
        """
        Get threshold configuration for article size

        Args:
            entity_count: Number of entities

        Returns:
            ThresholdConfig object
        """
        size = cls.determine_article_size(entity_count)
        return cls.THRESHOLDS[size]

    @classmethod
    def filter_edges(
        cls,
        edges: List[Dict],
        entity_count: int,
        custom_config: Optional[ThresholdConfig] = None
    ) -> List[Dict]:
        """
        Apply multi-stage filtering to edges

        Args:
            edges: List of edge dicts with 'source', 'target', 'npmi'/'score', 'confidence_avg', etc.
            entity_count: Total number of unique entities
            custom_config: Optional custom threshold config (overrides defaults)

        Returns:
            Filtered list of edges
        """
        if not edges:
            return []

        # Get threshold config
        config = custom_config or cls.get_threshold_config(entity_count)
        size = cls.determine_article_size(entity_count)

        logger.info(
            f"Filtering {len(edges)} edges for {size.value} article "
            f"({entity_count} entities) with config: {config.description}"
        )

        # Stage 1: Absolute threshold (NPMI or score for proximity-only)
        # Use 'score' field which could be npmi or proximity_score
        candidates = [e for e in edges if e.get('score', 0) >= config.min_npmi]

        logger.info(f"  Stage 1 (score >= {config.min_npmi}): {len(candidates)} edges remain")

        if not candidates:
            # Fallback: If too strict, keep top 3 strongest edges
            logger.warning("No edges passed threshold, falling back to top 3")
            return sorted(edges, key=lambda e: e.get('score', 0), reverse=True)[:3]

        # Stage 2: Percentile-based cutoff
        scores = [e.get('score', 0) for e in candidates]
        percentile_value = np.percentile(scores, config.percentile_cutoff)
        candidates = [e for e in candidates if e.get('score', 0) >= percentile_value]

        logger.info(
            f"  Stage 2 (Percentile {config.percentile_cutoff}): "
            f"{len(candidates)} edges remain (cutoff: {percentile_value:.3f})"
        )

        # Stage 3: Per-node degree capping
        filtered = cls._apply_degree_cap(candidates, config.max_edges_per_entity)

        logger.info(
            f"  Stage 3 (Degree cap ≤{config.max_edges_per_entity}): "
            f"{len(filtered)} edges remain"
        )

        reduction_pct = ((len(edges) - len(filtered)) / len(edges) * 100) if edges else 0
        logger.info(
            f"Final: Kept {len(filtered)}/{len(edges)} edges "
            f"({reduction_pct:.1f}% reduction)"
        )

        return filtered

    @classmethod
    def _apply_degree_cap(
        cls,
        edges: List[Dict],
        max_degree: int
    ) -> List[Dict]:
        """
        Cap the degree (number of connections) for each node

        Args:
            edges: List of edge dicts
            max_degree: Maximum edges per node

        Returns:
            Filtered edges with degree cap applied
        """
        # Sort edges by strength (score * confidence)
        edges_sorted = sorted(
            edges,
            key=lambda e: e.get('score', 0) * e.get('confidence_avg', 1.0),
            reverse=True
        )

        # Track degree for each node
        node_degrees = defaultdict(int)
        filtered = []

        for edge in edges_sorted:
            src = edge['source']
            tgt = edge['target']

            # Check if either node would exceed degree limit
            if (node_degrees[src] < max_degree and
                node_degrees[tgt] < max_degree):
                filtered.append(edge)
                node_degrees[src] += 1
                node_degrees[tgt] += 1

        return filtered

    @classmethod
    def get_filtering_summary(
        cls,
        original_count: int,
        filtered_count: int,
        entity_count: int
    ) -> Dict:
        """
        Generate summary of filtering applied

        Args:
            original_count: Number of edges before filtering
            filtered_count: Number of edges after filtering
            entity_count: Number of entities

        Returns:
            Summary dict
        """
        size = cls.determine_article_size(entity_count)
        config = cls.get_threshold_config(entity_count)

        return {
            'article_size': size.value,
            'entity_count': entity_count,
            'original_edge_count': original_count,
            'filtered_edge_count': filtered_count,
            'reduction_percentage': ((original_count - filtered_count) / original_count * 100) if original_count > 0 else 0,
            'config_applied': {
                'min_npmi': config.min_npmi,
                'max_edges_per_entity': config.max_edges_per_entity,
                'percentile_cutoff': config.percentile_cutoff
            },
            'description': config.description
        }

    @classmethod
    def create_custom_config(
        cls,
        min_npmi: float = 0.5,
        max_edges_per_entity: int = 8,
        percentile_cutoff: int = 60,
        description: str = "Custom configuration"
    ) -> ThresholdConfig:
        """
        Create a custom threshold configuration

        Args:
            min_npmi: Minimum NPMI/score threshold
            max_edges_per_entity: Maximum connections per entity
            percentile_cutoff: Percentile for edge filtering
            description: Description of config

        Returns:
            ThresholdConfig object
        """
        return ThresholdConfig(
            min_npmi=min_npmi,
            max_edges_per_entity=max_edges_per_entity,
            percentile_cutoff=percentile_cutoff,
            description=description
        )

    @classmethod
    def estimate_edge_count(cls, entity_count: int) -> Dict[str, int]:
        """
        Estimate edge count before and after filtering

        Args:
            entity_count: Number of entities

        Returns:
            Dict with estimated counts
        """
        # Naive co-occurrence: N * (N-1) / 2
        naive_edges = (entity_count * (entity_count - 1)) // 2

        size = cls.determine_article_size(entity_count)
        config = cls.get_threshold_config(entity_count)

        # Rough estimate: after percentile filtering and degree cap
        # Percentile keeps (100 - percentile_cutoff)% of edges
        after_percentile = int(naive_edges * (100 - config.percentile_cutoff) / 100)

        # Degree cap: max_edges_per_entity * entity_count / 2 (since edges are bidirectional)
        degree_cap_limit = (config.max_edges_per_entity * entity_count) // 2

        estimated_filtered = min(after_percentile, degree_cap_limit)

        return {
            'naive_edges': naive_edges,
            'estimated_filtered': estimated_filtered,
            'reduction_percentage': ((naive_edges - estimated_filtered) / naive_edges * 100) if naive_edges > 0 else 0
        }
