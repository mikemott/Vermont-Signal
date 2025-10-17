#!/usr/bin/env python3
"""
Standalone test for topic filtering logic
Tests the filtering logic without importing full modules
"""


# Replicate the CUSTOM_STOP_WORDS set
CUSTOM_STOP_WORDS = {
    # Common reporting verbs
    'said', 'says', 'told', 'asked', 'announced', 'reported', 'stated',
    'explained', 'noted', 'added', 'continued', 'began', 'started',
    # Generic people/groups
    'man', 'woman', 'people', 'person', 'men', 'women', 'group', 'groups',
    'official', 'officials', 'resident', 'residents', 'member', 'members',
    # Temporal words
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'january', 'february', 'march', 'april', 'may', 'june', 'july',
    'august', 'september', 'october', 'november', 'december',
    'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years',
    'today', 'yesterday', 'tomorrow', 'tonight', 'morning', 'afternoon', 'evening',
    # Generic locations
    'area', 'areas', 'place', 'places', 'town', 'city', 'state', 'country',
    'county', 'region', 'location', 'locations',
    # Numbers and quantifiers
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
    'first', 'second', 'third', 'many', 'several', 'few', 'lot', 'number',
    # Generic actions/states
    'make', 'makes', 'made', 'take', 'takes', 'took', 'get', 'gets', 'got',
    'give', 'gives', 'gave', 'go', 'goes', 'went', 'come', 'comes', 'came',
    'want', 'wants', 'wanted', 'need', 'needs', 'needed', 'know', 'knows', 'knew',
    'think', 'thinks', 'thought', 'see', 'sees', 'saw', 'look', 'looks', 'looked',
    'find', 'finds', 'found', 'work', 'works', 'worked', 'working',
    # Generic objects/concepts
    'thing', 'things', 'something', 'anything', 'everything', 'nothing',
    'way', 'ways', 'time', 'times', 'part', 'parts', 'case', 'cases',
    'point', 'points', 'issue', 'issues', 'problem', 'problems',
    # Articles/pronouns/conjunctions
    'the', 'a', 'an', 'this', 'that', 'these', 'those', 'it', 'its',
    'he', 'she', 'they', 'them', 'their', 'his', 'her', 'our', 'your',
    'and', 'or', 'but', 'if', 'when', 'where', 'who', 'what', 'which',
    # Reporting/article structure
    'article', 'story', 'report', 'news', 'according', 'including',
    # Common Vermont terms that are too generic
    'vermont', 'vt',
}


def is_meaningful_keyword(keyword):
    """Check if keyword is meaningful"""
    if len(keyword) < 3:
        return False
    if not keyword.isalpha():
        return False
    if keyword.lower() in CUSTOM_STOP_WORDS:
        return False

    html_indicators = [
        'href', 'class', 'style', 'rel', 'alt', 'src', 'div',
        'span', 'img', 'fig', 'wp', 'block', 'attachment',
    ]

    keyword_lower = keyword.lower()
    for indicator in html_indicators:
        if indicator in keyword_lower:
            return False

    if keyword != keyword.lower() and keyword != keyword.title():
        return False

    return True


def test_filtering():
    """Test keyword filtering"""

    print("=" * 70)
    print("TOPIC FILTERING TEST")
    print("=" * 70)

    # Test cases
    test_cases = [
        # (keyword, should_pass)
        ("said", False),
        ("told", False),
        ("man", False),
        ("october", False),
        ("year", False),
        ("Montpelier", True),
        ("Burlington", True),
        ("Budget", True),
        ("Education", True),
        ("Legislature", True),
        ("Housing", True),
        ("Climate", True),
        ("vermont", False),  # Too generic
        ("vt", False),  # Too generic
    ]

    passed = 0
    failed = 0

    print("\nTesting keywords:")
    print("-" * 70)

    for keyword, expected in test_cases:
        result = is_meaningful_keyword(keyword)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1

        expected_str = "KEEP" if expected else "FILTER"
        actual_str = "KEEP" if result else "FILTER"

        print(f"{status} '{keyword:15s}' Expected={expected_str:8s} Got={actual_str:8s}")

    print("-" * 70)
    print(f"\nResults: {passed}/{len(test_cases)} tests passed")

    if failed == 0:
        print("\n✓ All tests passed! Filtering logic works correctly.")
        return True
    else:
        print(f"\n✗ {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = test_filtering()
    exit(0 if success else 1)
