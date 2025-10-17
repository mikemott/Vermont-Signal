"""
Unit tests for position tracker
"""

import pytest
from vermont_news_analyzer.modules.position_tracker import PositionTracker, EntityPosition


@pytest.fixture
def tracker():
    """Create position tracker instance"""
    return PositionTracker()


def test_simple_sentence_split(tracker):
    """Test fallback sentence splitting"""
    text = "This is sentence one. This is sentence two! Is this sentence three?"
    sentences = tracker._simple_sentence_split(text)

    assert len(sentences) == 3
    assert "sentence one" in sentences[0][2]
    assert "sentence two" in sentences[1][2]


def test_paragraph_boundaries(tracker):
    """Test paragraph boundary detection"""
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    boundaries = tracker._get_paragraph_boundaries(text)

    assert len(boundaries) == 3
    assert boundaries[0] == 0
    assert boundaries[1] > 0
    assert boundaries[2] > boundaries[1]


def test_find_entity_positions(tracker):
    """Test entity position finding"""
    text = "Phil Scott is the governor. Phil Scott lives in Vermont."
    entities = [
        {'entity': 'Phil Scott', 'type': 'PERSON'},
        {'entity': 'Vermont', 'type': 'GPE'}
    ]

    positions = tracker.find_entity_positions(text, entities, use_spacy=False)

    assert len(positions) >= 2  # At least one Phil Scott and one Vermont

    phil_positions = [p for p in positions if p.entity == 'Phil Scott']
    assert phil_positions[0].sentence_index == 0

    vermont_positions = [p for p in positions if p.entity == 'Vermont']
    assert vermont_positions[0].sentence_index == 1


def test_enrich_entities_with_positions(tracker):
    """Test adding positions to entity dicts"""
    text = "Alice met Bob. Charlie joined later."
    entities = [
        {'entity': 'Alice', 'type': 'PERSON'},
        {'entity': 'Bob', 'type': 'PERSON'},
        {'entity': 'Charlie', 'type': 'PERSON'}
    ]

    enriched = tracker.enrich_entities_with_positions(text, entities)

    assert enriched[0]['sentence_index'] == 0  # Alice in first sentence
    assert enriched[1]['sentence_index'] == 0  # Bob in first sentence
    assert enriched[2]['sentence_index'] == 1  # Charlie in second sentence

    assert enriched[0]['char_start'] is not None
    assert enriched[0]['char_end'] is not None


def test_case_insensitive_matching(tracker):
    """Test that entity matching is case-insensitive"""
    text = "VERMONT is beautiful. Vermont has mountains."
    entities = [{'entity': 'Vermont', 'type': 'GPE'}]

    positions = tracker.find_entity_positions(text, entities, use_spacy=False)

    # Should find both occurrences
    assert len(positions) == 1  # Takes first occurrence
    assert positions[0].char_start == 0  # Finds "VERMONT"


def test_multiple_occurrences(tracker):
    """Test handling of entities that appear multiple times"""
    text = "Bob went to the store. Bob bought apples. Bob came home."
    entities = [{'entity': 'Bob', 'type': 'PERSON'}]

    # find_entity_positions returns all occurrences internally but only exposes first
    positions = tracker._find_entity_occurrences(
        text,
        'Bob',
        'PERSON',
        tracker._simple_sentence_split(text),
        tracker._get_paragraph_boundaries(text)
    )

    # Should find 3 occurrences of Bob
    assert len(positions) == 3
    assert all(p.entity == 'Bob' for p in positions)


def test_empty_entities_list(tracker):
    """Test handling of empty entities list"""
    text = "This is some text."
    entities = []

    enriched = tracker.enrich_entities_with_positions(text, entities)

    assert len(enriched) == 0


def test_entity_not_in_text(tracker):
    """Test handling when entity is not found in text"""
    text = "This is some text."
    entities = [{'entity': 'Nonexistent', 'type': 'PERSON'}]

    enriched = tracker.enrich_entities_with_positions(text, entities)

    # Should have None values for positions
    assert enriched[0]['sentence_index'] is None
    assert enriched[0]['paragraph_index'] is None
    assert enriched[0]['char_start'] is None
    assert enriched[0]['char_end'] is None
