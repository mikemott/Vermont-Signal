"""
Unit tests for PMI calculator with hybrid scoring
"""

import pytest
import math
from vermont_news_analyzer.modules.pmi_calculator import PMICalculator, PMIScore


@pytest.fixture
def calculator():
    return PMICalculator(smoothing=1e-6, min_frequency_for_pmi=2)


def test_pmi_calculation_perfect_correlation(calculator):
    """Test PMI when entities always appear together"""
    # Entity A and B always appear together (10 times)
    # Both appear in 10 documents each
    # Perfect correlation

    pmi_score = calculator.calculate_pmi(
        entity_a='A',
        entity_b='B',
        cooccurrence_count=10,
        entity_freq_a=10,
        entity_freq_b=10,
        total_documents=10,
        confidence_a=1.0,
        confidence_b=1.0,
        proximity_weight=3.0
    )

    # PMI should be high (they always appear together)
    assert pmi_score.pmi is not None
    assert pmi_score.pmi > 0
    # NPMI should be close to 1
    assert pmi_score.npmi is not None
    assert pmi_score.npmi > 0.5
    assert not pmi_score.is_rare_entity
    assert pmi_score.scoring_method == "pmi"


def test_pmi_calculation_independence(calculator):
    """Test PMI when entities are independent"""
    # Entity A appears in 50 of 100 documents
    # Entity B appears in 50 of 100 documents
    # They co-occur in 25 documents (0.5 * 0.5 * 100 = expected)

    pmi_score = calculator.calculate_pmi(
        entity_a='A',
        entity_b='B',
        cooccurrence_count=25,
        entity_freq_a=50,
        entity_freq_b=50,
        total_documents=100,
        proximity_weight=2.0
    )

    # PMI should be close to 0 (independent)
    assert pmi_score.pmi is not None
    assert abs(pmi_score.pmi) < 0.5
    assert abs(pmi_score.npmi) < 0.3


def test_hybrid_scoring_rare_entity(calculator):
    """Test that rare entities use proximity-only scoring"""
    # Entity A appears in only 1 document (rare)
    # Entity B appears in 10 documents
    # Should use proximity-only scoring

    pmi_score = calculator.calculate_pmi(
        entity_a='A',
        entity_b='B',
        cooccurrence_count=1,
        entity_freq_a=1,  # Rare!
        entity_freq_b=10,
        total_documents=100,
        confidence_a=0.9,
        confidence_b=0.85,
        proximity_weight=3.0  # Same sentence weight
    )

    # Should use proximity-only scoring
    assert pmi_score.is_rare_entity
    assert pmi_score.scoring_method == "proximity-only"
    assert pmi_score.pmi is None
    assert pmi_score.npmi is None
    # Score should be proximity_weight * avg_confidence
    expected_score = 3.0 * ((0.9 + 0.85) / 2.0)
    assert abs(pmi_score.pmi_score - expected_score) < 0.01


def test_should_use_pmi(calculator):
    """Test PMI threshold logic"""
    # Both entities frequent enough
    assert calculator.should_use_pmi(2, 2) is True
    assert calculator.should_use_pmi(10, 10) is True

    # One entity too rare
    assert calculator.should_use_pmi(1, 10) is False
    assert calculator.should_use_pmi(10, 1) is False

    # Both entities too rare
    assert calculator.should_use_pmi(1, 1) is False


def test_corpus_frequency_calculation(calculator):
    """Test corpus-level entity frequency calculation"""
    article_entities = {
        1: [{'entity': 'A'}, {'entity': 'B'}],
        2: [{'entity': 'A'}, {'entity': 'C'}],
        3: [{'entity': 'B'}, {'entity': 'C'}],
        4: [{'entity': 'A'}]
    }

    entity_freq, total_docs = calculator.calculate_corpus_frequencies(article_entities)

    assert total_docs == 4
    assert entity_freq['A'] == 3  # Appears in 3 articles
    assert entity_freq['B'] == 2
    assert entity_freq['C'] == 2


def test_pmi_batch_calculation(calculator):
    """Test batch PMI calculation with hybrid scoring"""
    cooc_matrix = {
        ('A', 'B'): {'count': 10, 'confidence_a': 0.9, 'confidence_b': 0.85, 'proximity_weight': 3.0},
        ('A', 'C'): {'count': 5, 'confidence_a': 0.9, 'confidence_b': 0.8, 'proximity_weight': 2.0},
        ('B', 'C'): {'count': 3, 'confidence_a': 0.85, 'confidence_b': 0.8, 'proximity_weight': 1.0},
        ('D', 'E'): {'count': 1, 'confidence_a': 0.9, 'confidence_b': 0.9, 'proximity_weight': 3.0}  # Rare
    }

    entity_frequencies = {
        'A': 15,
        'B': 12,
        'C': 8,
        'D': 1,  # Rare
        'E': 1   # Rare
    }

    pmi_scores = calculator.calculate_pmi_batch(
        cooc_matrix,
        entity_frequencies,
        total_documents=20
    )

    assert len(pmi_scores) == 4

    # A, B, C should use PMI (frequent enough)
    assert not pmi_scores[('A', 'B')].is_rare_entity
    assert not pmi_scores[('A', 'C')].is_rare_entity
    assert not pmi_scores[('B', 'C')].is_rare_entity

    # D, E should use proximity-only (too rare)
    assert pmi_scores[('D', 'E')].is_rare_entity
    assert pmi_scores[('D', 'E')].pmi is None
    assert pmi_scores[('D', 'E')].npmi is None


def test_pmi_filtering(calculator):
    """Test PMI threshold filtering"""
    pmi_scores = {
        ('A', 'B'): PMIScore('A', 'B', pmi=2.0, npmi=0.8, pmi_score=1.8, p_xy=0.1, p_x=0.2, p_y=0.2, raw_count=10, is_rare_entity=False, scoring_method="pmi"),
        ('A', 'C'): PMIScore('A', 'C', pmi=0.5, npmi=0.2, pmi_score=0.4, p_xy=0.05, p_x=0.2, p_y=0.1, raw_count=5, is_rare_entity=False, scoring_method="pmi"),
        ('B', 'C'): PMIScore('B', 'C', pmi=-0.5, npmi=-0.1, pmi_score=-0.4, p_xy=0.02, p_x=0.2, p_y=0.1, raw_count=2, is_rare_entity=False, scoring_method="pmi"),
        ('D', 'E'): PMIScore('D', 'E', pmi=None, npmi=None, pmi_score=2.7, p_xy=0.01, p_x=0.01, p_y=0.01, raw_count=1, is_rare_entity=True, scoring_method="proximity-only")
    }

    # Filter for NPMI >= 0.5
    filtered = calculator.filter_by_pmi_threshold(pmi_scores, min_pmi=0.5, use_npmi=True)

    # Should keep high NPMI pairs and rare entities with positive score
    assert len(filtered) == 2
    assert ('A', 'B') in filtered  # High NPMI
    assert ('D', 'E') in filtered  # Rare but positive score


def test_confidence_weighting(calculator):
    """Test that confidence affects PMI score"""
    # Same co-occurrence, different confidences

    high_conf = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=10,
        entity_freq_a=20, entity_freq_b=20, total_documents=100,
        confidence_a=0.9, confidence_b=0.9,
        proximity_weight=3.0
    )

    low_conf = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=10,
        entity_freq_a=20, entity_freq_b=20, total_documents=100,
        confidence_a=0.5, confidence_b=0.5,
        proximity_weight=3.0
    )

    # PMI and NPMI should be same (statistical measure)
    assert abs(high_conf.pmi - low_conf.pmi) < 0.001
    assert abs(high_conf.npmi - low_conf.npmi) < 0.001

    # But adjusted PMI score should differ
    assert high_conf.pmi_score > low_conf.pmi_score


def test_statistics_calculation(calculator):
    """Test statistics generation"""
    pmi_scores = {
        ('A', 'B'): PMIScore('A', 'B', pmi=2.0, npmi=0.8, pmi_score=1.8, p_xy=0.1, p_x=0.2, p_y=0.2, raw_count=10, is_rare_entity=False, scoring_method="pmi"),
        ('A', 'C'): PMIScore('A', 'C', pmi=0.5, npmi=0.2, pmi_score=0.4, p_xy=0.05, p_x=0.2, p_y=0.1, raw_count=5, is_rare_entity=False, scoring_method="pmi"),
        ('D', 'E'): PMIScore('D', 'E', pmi=None, npmi=None, pmi_score=2.7, p_xy=0.01, p_x=0.01, p_y=0.01, raw_count=1, is_rare_entity=True, scoring_method="proximity-only")
    }

    stats = calculator.get_pmi_statistics(pmi_scores)

    assert stats['count'] == 3
    assert stats['pmi_scored'] == 2
    assert stats['proximity_scored'] == 1
    assert stats['max_pmi'] == 2.0
    assert stats['min_pmi'] == 0.5
    assert stats['mean_npmi'] > 0


def test_statistics_empty(calculator):
    """Test statistics on empty dict"""
    stats = calculator.get_pmi_statistics({})

    assert stats['count'] == 0
    assert stats['pmi_scored'] == 0
    assert stats['proximity_scored'] == 0


def test_rare_entity_both_sides(calculator):
    """Test when both entities are rare"""
    pmi_score = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=1,
        entity_freq_a=1,
        entity_freq_b=1,
        total_documents=100,
        confidence_a=0.9,
        confidence_b=0.8,
        proximity_weight=3.0
    )

    assert pmi_score.is_rare_entity
    assert pmi_score.scoring_method == "proximity-only"
    # Score = 3.0 * (0.9 + 0.8) / 2
    expected = 3.0 * 0.85
    assert abs(pmi_score.pmi_score - expected) < 0.01


def test_proximity_weight_affects_rare_entity_score(calculator):
    """Test that proximity weight matters for rare entities"""
    # Same entities, different proximity weights

    same_sent = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=1,
        entity_freq_a=1, entity_freq_b=10,
        total_documents=100,
        confidence_a=0.9, confidence_b=0.9,
        proximity_weight=3.0  # Same sentence
    )

    adjacent_sent = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=1,
        entity_freq_a=1, entity_freq_b=10,
        total_documents=100,
        confidence_a=0.9, confidence_b=0.9,
        proximity_weight=2.0  # Adjacent
    )

    # Higher proximity weight should give higher score
    assert same_sent.pmi_score > adjacent_sent.pmi_score
    assert same_sent.pmi_score == 3.0 * 0.9
    assert adjacent_sent.pmi_score == 2.0 * 0.9
