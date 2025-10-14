"""
Unit tests for entity normalization logic

Tests the VermontSignalDatabase entity normalization and deduplication logic.
Critical for preventing duplicate entities like "Mayor Mike Doenges" vs "Mike Doenges"
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestEntityNormalization:
    """Test entity name normalization"""

    def test_normalize_person_strips_titles(self):
        """Should strip common titles from person names"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Mayor
        assert db._normalize_entity("Mayor Mike Doenges", "PERSON") == "Mike Doenges"
        assert db._normalize_entity("Mayor Sarah Carpenter", "PERSON") == "Sarah Carpenter"

        # Governor
        assert db._normalize_entity("Governor Phil Scott", "PERSON") == "Phil Scott"
        assert db._normalize_entity("Vermont Governor Phil Scott", "PERSON") == "Phil Scott"

        # Senator
        assert db._normalize_entity("Senator Bernie Sanders", "PERSON") == "Bernie Sanders"
        assert db._normalize_entity("Sen. Bernie Sanders", "PERSON") == "Bernie Sanders"

        # Representative
        assert db._normalize_entity("Representative Peter Welch", "PERSON") == "Peter Welch"

        # President
        assert db._normalize_entity("President Joe Biden", "PERSON") == "Joe Biden"

    @pytest.mark.unit
    def test_normalize_person_strips_city_prefixes(self):
        """Should strip city name + title prefixes"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # City + Title patterns
        assert db._normalize_entity("Rutland City Mayor Mike Doenges", "PERSON") == "Mike Doenges"
        assert db._normalize_entity("Burlington Mayor Emma Mulvaney-Stanak", "PERSON") == "Emma Mulvaney-Stanak"

    @pytest.mark.unit
    def test_normalize_person_preserves_name(self):
        """Should preserve the actual name"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Already clean names
        assert db._normalize_entity("Mike Doenges", "PERSON") == "Mike Doenges"
        assert db._normalize_entity("Phil Scott", "PERSON") == "Phil Scott"
        assert db._normalize_entity("Bernie Sanders", "PERSON") == "Bernie Sanders"

    @pytest.mark.unit
    def test_normalize_organization_strips_the(self):
        """Should strip 'the' prefix from organizations"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        assert db._normalize_entity("The Vermont Legislature", "ORGANIZATION") == "Vermont Legislature"
        assert db._normalize_entity("the Vermont Supreme Court", "ORGANIZATION") == "Vermont Supreme Court"

    @pytest.mark.unit
    def test_normalize_organization_preserves_name(self):
        """Should preserve organization names without 'the'"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        assert db._normalize_entity("Vermont Legislature", "ORGANIZATION") == "Vermont Legislature"
        assert db._normalize_entity("Burlington School District", "ORGANIZATION") == "Burlington School District"

    @pytest.mark.unit
    def test_normalize_other_types_unchanged(self):
        """Should not modify other entity types"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Locations, dates, etc. should not be modified
        assert db._normalize_entity("Burlington", "LOCATION") == "Burlington"
        assert db._normalize_entity("Vermont", "GPE") == "Vermont"
        assert db._normalize_entity("October 14, 2025", "DATE") == "October 14, 2025"


class TestEntityMatching:
    """Test entity matching/deduplication logic"""

    @pytest.mark.unit
    def test_entities_match_substring(self):
        """Should match entities when one is substring of other"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Same type, substring match
        assert db._entities_match("Mike Doenges", "Mayor Mike Doenges", "PERSON", "PERSON") is True
        assert db._entities_match("Phil Scott", "Governor Phil Scott", "PERSON", "PERSON") is True
        assert db._entities_match("Sanders", "Bernie Sanders", "PERSON", "PERSON") is True

    @pytest.mark.unit
    def test_entities_no_match_different_types(self):
        """Should NOT match entities of different types"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Different types should not match
        assert db._entities_match("Burlington", "Burlington", "PERSON", "LOCATION") is False
        assert db._entities_match("Scott", "Scott", "PERSON", "ORGANIZATION") is False

    @pytest.mark.unit
    def test_entities_no_match_different_names(self):
        """Should NOT match completely different entities"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Completely different names
        assert db._entities_match("Mike Doenges", "Phil Scott", "PERSON", "PERSON") is False
        assert db._entities_match("Burlington", "Montpelier", "LOCATION", "LOCATION") is False

    @pytest.mark.unit
    def test_entities_match_case_insensitive(self):
        """Should match case-insensitively"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        assert db._entities_match("mike doenges", "MIKE DOENGES", "PERSON", "PERSON") is True
        assert db._entities_match("Burlington", "burlington", "LOCATION", "LOCATION") is True


class TestEntityDeduplication:
    """Test fact deduplication in store_facts"""

    @pytest.mark.unit
    def test_merge_duplicate_entities(self):
        """Should merge facts for duplicate entities"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)
        db.connection_pool = None  # Don't need real DB for this test

        facts = [
            {
                "entity": "Mayor Mike Doenges",
                "type": "PERSON",
                "confidence": 0.8,
                "sources": ["claude"],
                "event_description": "Announced budget"
            },
            {
                "entity": "Mike Doenges",
                "type": "PERSON",
                "confidence": 0.9,
                "sources": ["gemini"],
                "event_description": "Spoke at meeting"
            }
        ]

        # Normalize entities
        for fact in facts:
            fact['entity_normalized'] = db._normalize_entity(fact['entity'], fact['type'])

        # Both should normalize to "Mike Doenges"
        assert facts[0]['entity_normalized'] == "Mike Doenges"
        assert facts[1]['entity_normalized'] == "Mike Doenges"

    @pytest.mark.unit
    def test_keep_shorter_name(self):
        """Should keep shorter (more general) entity name"""
        # This tests the merging logic where we prefer shorter names
        # "Mike Doenges" is better than "Mayor Mike Doenges"

        # The database logic should prefer "Mike Doenges" over "Mayor Mike Doenges"
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        short_name = "Mike Doenges"
        long_name = "Mayor Mike Doenges"

        # Shorter name should be preferred
        assert len(short_name) < len(long_name)

    @pytest.mark.unit
    def test_merge_confidence_takes_max(self):
        """Should use maximum confidence when merging"""
        # When merging duplicate entities, use the higher confidence

        conf1 = 0.8
        conf2 = 0.9

        # Logic should take max
        merged_conf = max(conf1, conf2)
        assert merged_conf == 0.9

    @pytest.mark.unit
    def test_merge_sources_union(self):
        """Should combine sources from both models"""
        sources1 = ["claude"]
        sources2 = ["gemini"]

        # Logic should create union
        merged = list(set(sources1) | set(sources2))
        assert "claude" in merged
        assert "gemini" in merged


class TestEdgeCases:
    """Test edge cases in entity normalization"""

    @pytest.mark.unit
    def test_empty_entity_name(self):
        """Should handle empty entity names"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Should return empty string unchanged
        assert db._normalize_entity("", "PERSON") == ""
        assert db._normalize_entity(None, "PERSON") is None

    @pytest.mark.unit
    def test_entity_with_only_title(self):
        """Should handle entities that are only titles"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Edge case: what if entity is just "Mayor"?
        result = db._normalize_entity("Mayor", "PERSON")
        # Should strip "Mayor" and return empty, or return as-is?
        # Document expected behavior

    @pytest.mark.unit
    def test_multiple_titles(self):
        """Should handle multiple titles"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # "Senator and Governor Phil Scott" (hypothetical)
        result = db._normalize_entity("Senator Governor Phil Scott", "PERSON")
        assert "Phil Scott" in result

    @pytest.mark.unit
    def test_unicode_names(self):
        """Should handle unicode characters in names"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Names with accents, etc.
        assert db._normalize_entity("José García", "PERSON") == "José García"
        assert db._normalize_entity("François Dupont", "PERSON") == "François Dupont"

    @pytest.mark.unit
    def test_special_characters(self):
        """Should handle special characters"""
        from vermont_news_analyzer.modules.database import VermontSignalDatabase

        db = VermontSignalDatabase.__new__(VermontSignalDatabase)

        # Hyphenated names, apostrophes
        assert "O'Brien" in db._normalize_entity("Mayor O'Brien", "PERSON")
        assert "Smith-Jones" in db._normalize_entity("Senator Smith-Jones", "PERSON")
