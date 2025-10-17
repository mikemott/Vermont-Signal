"""
Unit tests for Dynamic Thresholder with adaptive filtering
"""

import pytest
from vermont_news_analyzer.modules.dynamic_thresholder import (
    DynamicThresholder,
    ThresholdConfig,
    ArticleSize
)


def test_article_size_determination():
    """Test article size categorization"""
    # Small articles (≤10 entities)
    assert DynamicThresholder.determine_article_size(5) == ArticleSize.SMALL
    assert DynamicThresholder.determine_article_size(10) == ArticleSize.SMALL

    # Medium articles (11-25 entities)
    assert DynamicThresholder.determine_article_size(11) == ArticleSize.MEDIUM
    assert DynamicThresholder.determine_article_size(20) == ArticleSize.MEDIUM
    assert DynamicThresholder.determine_article_size(25) == ArticleSize.MEDIUM

    # Large articles (>25 entities)
    assert DynamicThresholder.determine_article_size(26) == ArticleSize.LARGE
    assert DynamicThresholder.determine_article_size(50) == ArticleSize.LARGE
    assert DynamicThresholder.determine_article_size(100) == ArticleSize.LARGE


def test_threshold_config_retrieval():
    """Test getting threshold configs for different article sizes"""
    # Small article config
    small_config = DynamicThresholder.get_threshold_config(8)
    assert small_config.min_npmi == 0.3
    assert small_config.max_edges_per_entity == 5
    assert small_config.percentile_cutoff == 70

    # Medium article config
    medium_config = DynamicThresholder.get_threshold_config(20)
    assert medium_config.min_npmi == 0.5
    assert medium_config.max_edges_per_entity == 8
    assert medium_config.percentile_cutoff == 60

    # Large article config
    large_config = DynamicThresholder.get_threshold_config(50)
    assert large_config.min_npmi == 0.6
    assert large_config.max_edges_per_entity == 10
    assert large_config.percentile_cutoff == 50


def test_filter_edges_empty():
    """Test filtering with empty edge list"""
    filtered = DynamicThresholder.filter_edges([], entity_count=10)
    assert filtered == []


def test_filter_edges_stage1_absolute_threshold():
    """Test Stage 1: Absolute score threshold"""
    edges = [
        {'source': 'A', 'target': 'B', 'score': 0.8, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'C', 'score': 0.4, 'confidence_avg': 0.85},
        {'source': 'B', 'target': 'C', 'score': 0.2, 'confidence_avg': 0.8},
        {'source': 'D', 'target': 'E', 'score': 0.1, 'confidence_avg': 0.75}
    ]

    # Small article: min_npmi=0.3
    filtered = DynamicThresholder.filter_edges(edges, entity_count=8)

    # Should keep edges with score >= 0.3
    filtered_pairs = {(e['source'], e['target']) for e in filtered}
    assert ('A', 'B') in filtered_pairs  # 0.8 >= 0.3
    assert ('A', 'C') in filtered_pairs  # 0.4 >= 0.3


def test_filter_edges_stage2_percentile():
    """Test Stage 2: Percentile-based cutoff"""
    # Create edges with scores from 0.3 to 1.0
    edges = [
        {'source': f'E{i}', 'target': f'E{i+1}', 'score': 0.3 + (i * 0.1), 'confidence_avg': 0.9}
        for i in range(8)  # Scores: 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0
    ]

    # Small article: percentile_cutoff=70 (keep top 30%)
    filtered = DynamicThresholder.filter_edges(edges, entity_count=8)

    # Should keep approximately top 30% (but also subject to degree cap)
    assert len(filtered) <= len(edges)

    # Check that higher scores are preferred
    if filtered:
        min_score = min(e['score'] for e in filtered)
        assert min_score >= 0.5  # Should filter out lower scores


def test_filter_edges_stage3_degree_cap():
    """Test Stage 3: Per-node degree capping"""
    # Create a star topology: A connects to B, C, D, E, F, G
    edges = [
        {'source': 'A', 'target': 'B', 'score': 0.9, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'C', 'score': 0.8, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'D', 'score': 0.7, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'E', 'score': 0.6, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'F', 'score': 0.5, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'G', 'score': 0.4, 'confidence_avg': 0.9},
    ]

    # Small article: max_edges_per_entity=5
    filtered = DynamicThresholder.filter_edges(edges, entity_count=7)

    # Node A should have at most 5 connections
    a_connections = sum(1 for e in filtered if e['source'] == 'A' or e['target'] == 'A')
    assert a_connections <= 5

    # Should keep strongest edges (sorted by score * confidence)
    if filtered:
        scores = [e['score'] for e in filtered]
        assert scores == sorted(scores, reverse=True)


def test_filter_edges_fallback():
    """Test fallback when no edges pass threshold"""
    edges = [
        {'source': 'A', 'target': 'B', 'score': 0.1, 'confidence_avg': 0.5},
        {'source': 'C', 'target': 'D', 'score': 0.05, 'confidence_avg': 0.4},
        {'source': 'E', 'target': 'F', 'score': 0.15, 'confidence_avg': 0.6},
        {'source': 'G', 'target': 'H', 'score': 0.08, 'confidence_avg': 0.45}
    ]

    # Large article with strict threshold (min_npmi=0.6)
    # None of these edges should pass
    filtered = DynamicThresholder.filter_edges(edges, entity_count=50)

    # Should fall back to top 3 edges
    assert len(filtered) == 3

    # Should be the three strongest edges
    scores = sorted([e['score'] for e in filtered], reverse=True)
    assert scores[0] == 0.15  # Strongest
    assert scores[1] == 0.1
    assert scores[2] == 0.08


def test_custom_config():
    """Test using custom threshold configuration"""
    edges = [
        {'source': 'A', 'target': 'B', 'score': 0.7, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'C', 'score': 0.5, 'confidence_avg': 0.85},
        {'source': 'B', 'target': 'C', 'score': 0.3, 'confidence_avg': 0.8},
    ]

    # Custom config: very strict
    custom_config = DynamicThresholder.create_custom_config(
        min_npmi=0.6,
        max_edges_per_entity=2,
        percentile_cutoff=80,
        description="Very strict filtering"
    )

    filtered = DynamicThresholder.filter_edges(
        edges,
        entity_count=10,
        custom_config=custom_config
    )

    # Only edge with score >= 0.6 should pass
    assert len(filtered) <= 1
    if filtered:
        assert filtered[0]['score'] >= 0.6


def test_filtering_summary():
    """Test filtering summary generation"""
    summary = DynamicThresholder.get_filtering_summary(
        original_count=100,
        filtered_count=30,
        entity_count=20
    )

    assert summary['article_size'] == 'medium'
    assert summary['entity_count'] == 20
    assert summary['original_edge_count'] == 100
    assert summary['filtered_edge_count'] == 30
    assert summary['reduction_percentage'] == 70.0
    assert 'config_applied' in summary
    assert summary['config_applied']['min_npmi'] == 0.5
    assert summary['config_applied']['max_edges_per_entity'] == 8
    assert summary['config_applied']['percentile_cutoff'] == 60


def test_edge_count_estimation():
    """Test edge count estimation"""
    # Small article (10 entities)
    estimate = DynamicThresholder.estimate_edge_count(10)

    # Naive edges: 10 * 9 / 2 = 45
    assert estimate['naive_edges'] == 45
    assert estimate['estimated_filtered'] < estimate['naive_edges']
    assert estimate['reduction_percentage'] > 0

    # Large article (50 entities)
    estimate_large = DynamicThresholder.estimate_edge_count(50)

    # Should have much more aggressive reduction
    assert estimate_large['reduction_percentage'] > estimate['reduction_percentage']


def test_degree_cap_application():
    """Test degree cap application in detail"""
    # Create edges where node A would exceed degree cap
    edges = [
        {'source': 'A', 'target': 'B', 'score': 1.0, 'confidence_avg': 1.0},  # Strongest
        {'source': 'A', 'target': 'C', 'score': 0.9, 'confidence_avg': 1.0},
        {'source': 'A', 'target': 'D', 'score': 0.8, 'confidence_avg': 1.0},
        {'source': 'A', 'target': 'E', 'score': 0.7, 'confidence_avg': 1.0},
        {'source': 'A', 'target': 'F', 'score': 0.6, 'confidence_avg': 1.0},
        {'source': 'A', 'target': 'G', 'score': 0.5, 'confidence_avg': 1.0},  # 6th edge
        {'source': 'B', 'target': 'C', 'score': 0.4, 'confidence_avg': 1.0},
    ]

    filtered = DynamicThresholder._apply_degree_cap(edges, max_degree=5)

    # Count A's connections
    a_degree = sum(1 for e in filtered if e['source'] == 'A' or e['target'] == 'A')
    assert a_degree <= 5

    # Should keep the strongest edges for A
    a_edges = [e for e in filtered if e['source'] == 'A' or e['target'] == 'A']
    if a_edges:
        a_scores = [e['score'] for e in a_edges]
        # All kept edges should be among the strongest
        assert min(a_scores) >= 0.6  # Weakest kept edge should be strong


def test_filter_edges_preserves_edge_structure():
    """Test that filtered edges preserve all original fields"""
    edges = [
        {
            'source': 'A',
            'target': 'B',
            'score': 0.8,
            'confidence_avg': 0.9,
            'pmi': 2.5,
            'npmi': 0.75,
            'proximity_weight': 3.0,
            'custom_field': 'test'
        }
    ]

    filtered = DynamicThresholder.filter_edges(edges, entity_count=10)

    assert len(filtered) > 0
    # Check all fields preserved
    assert filtered[0]['source'] == 'A'
    assert filtered[0]['target'] == 'B'
    assert filtered[0]['score'] == 0.8
    assert filtered[0]['confidence_avg'] == 0.9
    assert filtered[0]['pmi'] == 2.5
    assert filtered[0]['npmi'] == 0.75
    assert filtered[0]['proximity_weight'] == 3.0
    assert filtered[0]['custom_field'] == 'test'


def test_different_article_sizes_different_filtering():
    """Test that different article sizes apply different filtering strategies"""
    edges = [
        {'source': 'A', 'target': 'B', 'score': 0.4, 'confidence_avg': 0.9},
        {'source': 'C', 'target': 'D', 'score': 0.35, 'confidence_avg': 0.85},
        {'source': 'E', 'target': 'F', 'score': 0.32, 'confidence_avg': 0.8},
    ]

    # Small article (min_npmi=0.3) - should keep all
    small_filtered = DynamicThresholder.filter_edges(edges, entity_count=8)

    # Medium article (min_npmi=0.5) - should keep fewer
    medium_filtered = DynamicThresholder.filter_edges(edges, entity_count=20)

    # Large article (min_npmi=0.6) - should keep fewest
    large_filtered = DynamicThresholder.filter_edges(edges, entity_count=50)

    # Small should keep more than medium, medium more than large
    assert len(small_filtered) >= len(medium_filtered)
    assert len(medium_filtered) >= len(large_filtered)


def test_zero_entity_count():
    """Test edge case: zero entities"""
    edges = [{'source': 'A', 'target': 'B', 'score': 0.8, 'confidence_avg': 0.9}]

    # Should default to small article behavior
    filtered = DynamicThresholder.filter_edges(edges, entity_count=0)

    # Should still filter based on small article config
    assert isinstance(filtered, list)


def test_summary_zero_edges():
    """Test summary generation with zero edges"""
    summary = DynamicThresholder.get_filtering_summary(
        original_count=0,
        filtered_count=0,
        entity_count=10
    )

    assert summary['reduction_percentage'] == 0
    assert summary['original_edge_count'] == 0
    assert summary['filtered_edge_count'] == 0
