#!/usr/bin/env python3
"""
Test script for new topic filtering improvements
Tests keyword filtering without needing database connection
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from vermont_news_analyzer.modules.nlp_tools import TopicModeler


def test_keyword_filtering():
    """Test that stop words and generic terms are filtered correctly"""

    print("=" * 70)
    print("TESTING TOPIC KEYWORD FILTERING")
    print("=" * 70)

    modeler = TopicModeler()

    # Test cases: (keyword, should_be_meaningful)
    test_cases = [
        # Should be filtered (not meaningful)
        ("said", False),
        ("told", False),
        ("man", False),
        ("woman", False),
        ("october", False),
        ("monday", False),
        ("year", False),
        ("years", False),
        ("people", False),
        ("vermont", False),
        ("vt", False),
        ("day", False),
        ("time", False),
        ("area", False),
        ("one", False),
        ("two", False),
        ("first", False),

        # Should pass (meaningful)
        ("Montpelier", True),
        ("Burlington", True),
        ("Legislature", True),
        ("Budget", True),
        ("Education", True),
        ("Healthcare", True),
        ("Housing", True),
        ("Climate", True),
        ("Agriculture", True),
        ("Tourism", True),
        ("Infrastructure", True),
        ("Scott", True),  # Governor Scott
        ("Police", True),
        ("Hospital", True),
        ("School", True),
    ]

    passed = 0
    failed = 0

    print("\nTesting keyword meaningfulness filter:")
    print("-" * 70)

    for keyword, expected_meaningful in test_cases:
        result = modeler._is_meaningful_keyword(keyword)
        status = "✓" if result == expected_meaningful else "✗"

        if result == expected_meaningful:
            passed += 1
        else:
            failed += 1

        expected_str = "KEEP" if expected_meaningful else "FILTER"
        actual_str = "KEEP" if result else "FILTER"

        print(f"{status} '{keyword}': Expected={expected_str}, Got={actual_str}")

    print("-" * 70)
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)} tests")

    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")

    return failed == 0


def test_score_filtering():
    """Test c-TF-IDF score filtering"""

    print("\n" + "=" * 70)
    print("TESTING c-TF-IDF SCORE FILTERING")
    print("=" * 70)

    modeler = TopicModeler()

    # Simulate BERTopic output: list of (word, c-TF-IDF score)
    topic_words = [
        ("Montpelier", 0.85),
        ("Budget", 0.72),
        ("Legislature", 0.68),
        ("said", 0.45),  # High score but should be filtered as stop word
        ("Education", 0.42),
        ("School", 0.38),
        ("man", 0.15),  # Low score AND stop word
        ("October", 0.12),  # Low score AND stop word
        ("Housing", 0.08),  # Good word but below threshold
        ("year", 0.06),  # Low score AND stop word
    ]

    print("\nInput topic words (word, c-TF-IDF score):")
    for word, score in topic_words:
        print(f"  {word}: {score:.2f}")

    # Test with default threshold (0.05)
    filtered = modeler._filter_keywords_by_score(topic_words)

    print(f"\nFiltered keywords (threshold={modeler.MIN_TFIDF_SCORE}):")
    print(f"  {filtered}")

    # Expected: Should keep Montpelier, Budget, Legislature, Education, School
    # Should filter: said (stop word), man (stop word), October (stop word),
    #                Housing (below threshold), year (stop word)
    expected = ["Montpelier", "Budget", "Legislature", "Education", "School"]

    print(f"\nExpected: {expected}")
    print(f"Got:      {filtered}")

    if filtered == expected:
        print("✓ Score filtering test passed!")
        return True
    else:
        print("✗ Score filtering test failed")
        print(f"  Missing: {set(expected) - set(filtered)}")
        print(f"  Extra:   {set(filtered) - set(expected)}")
        return False


def test_label_generation():
    """Test topic label generation"""

    print("\n" + "=" * 70)
    print("TESTING TOPIC LABEL GENERATION")
    print("=" * 70)

    modeler = TopicModeler()

    test_cases = [
        # (keywords, expected_pattern)
        (["Montpelier", "budget", "legislature"], "Montpelier"),  # Prefer proper noun
        (["budget", "education", "funding"], "Budget"),  # No proper noun, use first
        (["climate_change", "environment"], "Climate Change"),  # Underscore phrase
        (["school", "education", "students"], "School"),  # All lowercase
        ([], "Miscellaneous"),  # Empty keywords
    ]

    print("\nTesting label generation:")
    print("-" * 70)

    passed = 0
    failed = 0

    for keywords, expected in test_cases:
        result = modeler._generate_topic_label(keywords)
        matches = result == expected
        status = "✓" if matches else "✗"

        if matches:
            passed += 1
        else:
            failed += 1

        print(f"{status} Keywords: {keywords}")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print()

    print("-" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")

    return failed == 0


if __name__ == "__main__":
    print("Vermont Signal - Topic Filtering Test Suite\n")

    # Run all tests
    test1 = test_keyword_filtering()
    test2 = test_score_filtering()
    test3 = test_label_generation()

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    if test1 and test2 and test3:
        print("✓ All test suites passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
