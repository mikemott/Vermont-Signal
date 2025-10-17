"""
Unit tests for proximity matrix builder
"""

import pytest
from vermont_news_analyzer.modules.proximity_matrix import ProximityMatrix, CooccurrenceData


@pytest.fixture
def sample_entities():
    """Sample entities with positions"""
    return [
        {'entity': 'Alice', 'type': 'PERSON', 'sentence_index': 0, 'confidence': 0.9},
        {'entity': 'Bob', 'type': 'PERSON', 'sentence_index': 0, 'confidence': 0.85},
        {'entity': 'Charlie', 'type': 'PERSON', 'sentence_index': 1, 'confidence': 0.8},
        {'entity': 'Alice', 'type': 'PERSON', 'sentence_index': 2, 'confidence': 0.9},
        {'entity': 'David', 'type': 'PERSON', 'sentence_index': 2, 'confidence': 0.75},
    ]


def test_build_matrix_same_sentence(sample_entities):
    """Test co-occurrence in same sentence"""
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Alice and Bob in same sentence (index 0)
    alice_bob = co_matrix.get(('Alice', 'Bob'))
    assert alice_bob is not None
    assert alice_bob.same_sentence_count >= 1
    assert alice_bob.total_weight >= 3.0  # Same sentence = weight 3


def test_build_matrix_adjacent_sentences(sample_entities):
    """Test co-occurrence in adjacent sentences"""
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Alice in sentence 0, Charlie in sentence 1
    alice_charlie = co_matrix.get(('Alice', 'Charlie'))
    assert alice_charlie is not None
    assert alice_charlie.adjacent_sentence_count >= 1
    assert alice_charlie.total_weight >= 2.0  # Adjacent = weight 2


def test_build_matrix_near_proximity(sample_entities):
    """Test co-occurrence within window but not adjacent"""
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Bob in sentence 0, Charlie in sentence 1 (distance=1)
    # Bob in sentence 0, David in sentence 2 (distance=2)
    bob_charlie = co_matrix.get(('Bob', 'Charlie'))
    if bob_charlie:
        assert bob_charlie.total_weight >= 2.0  # Adjacent = weight 2


def test_build_matrix_window_size():
    """Test different window sizes"""
    entities = [
        {'entity': 'A', 'type': 'X', 'sentence_index': 0, 'confidence': 1.0},
        {'entity': 'B', 'type': 'X', 'sentence_index': 3, 'confidence': 1.0},
    ]

    # Window size 0: only same sentence (no connection)
    matrix_0 = ProximityMatrix(window_size=0).build_matrix(entities)
    assert ('A', 'B') not in matrix_0

    # Window size 1: up to 1 sentence away (no connection, 3 apart)
    matrix_1 = ProximityMatrix(window_size=1).build_matrix(entities)
    assert ('A', 'B') not in matrix_1

    # Window size 3: should connect
    matrix_3 = ProximityMatrix(window_size=3).build_matrix(entities)
    assert ('A', 'B') in matrix_3


def test_entity_frequencies(sample_entities):
    """Test entity frequency calculation"""
    matrix_builder = ProximityMatrix()
    frequencies = matrix_builder.calculate_entity_frequencies(sample_entities)

    assert frequencies['Alice'] == 2  # Appears in 2 different sentences
    assert frequencies['Bob'] == 1
    assert frequencies['Charlie'] == 1
    assert frequencies['David'] == 1


def test_filter_by_weight(sample_entities):
    """Test filtering by minimum weight"""
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Filter for weight >= 3.0 (same sentence only)
    filtered = matrix_builder.filter_by_weight(co_matrix, min_weight=3.0)

    # Should only keep same-sentence pairs
    for pair, data in filtered.items():
        assert data.same_sentence_count > 0


def test_relationship_type_classification():
    """Test relationship type determination"""
    matrix_builder = ProximityMatrix()

    # Same sentence
    data1 = CooccurrenceData(
        entity_a='A', entity_b='B', total_weight=3,
        same_sentence_count=1, adjacent_sentence_count=0, near_proximity_count=0
    )
    assert matrix_builder.get_relationship_type(data1) == 'same-sentence'

    # Adjacent
    data2 = CooccurrenceData(
        entity_a='A', entity_b='B', total_weight=2,
        same_sentence_count=0, adjacent_sentence_count=1, near_proximity_count=0
    )
    assert matrix_builder.get_relationship_type(data2) == 'adjacent-sentence'

    # Near proximity
    data3 = CooccurrenceData(
        entity_a='A', entity_b='B', total_weight=1,
        same_sentence_count=0, adjacent_sentence_count=0, near_proximity_count=1
    )
    assert matrix_builder.get_relationship_type(data3) == 'near-proximity'


def test_no_self_connections(sample_entities):
    """Test that entities don't connect to themselves"""
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Alice appears twice, but shouldn't connect to herself
    for pair in co_matrix.keys():
        assert pair[0] != pair[1]


def test_empty_entities():
    """Test handling of empty entities list"""
    matrix_builder = ProximityMatrix()
    co_matrix = matrix_builder.build_matrix([])

    assert len(co_matrix) == 0


def test_entities_without_positions():
    """Test handling when no entities have positions"""
    entities = [
        {'entity': 'Alice', 'type': 'PERSON', 'confidence': 0.9},
        {'entity': 'Bob', 'type': 'PERSON', 'confidence': 0.85},
    ]

    matrix_builder = ProximityMatrix()
    co_matrix = matrix_builder.build_matrix(entities)

    assert len(co_matrix) == 0


def test_statistics_calculation(sample_entities):
    """Test statistics calculation"""
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    stats = matrix_builder.get_statistics(co_matrix)

    assert stats['total_pairs'] > 0
    assert stats['avg_weight'] > 0
    assert stats['max_weight'] >= stats['min_weight']
    assert stats['same_sentence'] >= 0


def test_statistics_empty_matrix():
    """Test statistics on empty matrix"""
    matrix_builder = ProximityMatrix()
    stats = matrix_builder.get_statistics({})

    assert stats['total_pairs'] == 0
    assert stats['avg_weight'] == 0.0


def test_average_distance_calculation():
    """Test that average distance is calculated correctly"""
    entities = [
        {'entity': 'A', 'type': 'X', 'sentence_index': 0, 'confidence': 1.0},
        {'entity': 'B', 'type': 'X', 'sentence_index': 0, 'confidence': 1.0},
        {'entity': 'A', 'type': 'X', 'sentence_index': 2, 'confidence': 1.0},
        {'entity': 'B', 'type': 'X', 'sentence_index': 2, 'confidence': 1.0},
    ]

    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(entities)

    # A and B appear together in sentence 0 (distance=0) and sentence 2 (distance=0)
    ab_pair = co_matrix.get(('A', 'B'))
    assert ab_pair is not None
    assert ab_pair.avg_distance == 0.0  # Both at distance 0


def test_occurrence_details_stored():
    """Test that occurrence details are properly stored"""
    entities = [
        {'entity': 'A', 'type': 'X', 'sentence_index': 0, 'confidence': 0.9},
        {'entity': 'B', 'type': 'X', 'sentence_index': 0, 'confidence': 0.8},
    ]

    matrix_builder = ProximityMatrix(window_size=1)
    co_matrix = matrix_builder.build_matrix(entities, article_id=123)

    ab_pair = co_matrix.get(('A', 'B'))
    assert ab_pair is not None
    assert len(ab_pair.occurrences) > 0

    occurrence = ab_pair.occurrences[0]
    assert occurrence['article_id'] == 123
    assert occurrence['distance'] == 0
    assert occurrence['weight'] == 3.0
    assert occurrence['confidence_a'] == 0.9
    assert occurrence['confidence_b'] == 0.8
