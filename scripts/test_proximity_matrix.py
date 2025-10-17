#!/usr/bin/env python3
"""
Test script for proximity matrix builder
Demonstrates proximity-weighted co-occurrence calculation
"""

import sys
sys.path.insert(0, '/Users/mike/Library/Mobile Documents/com~apple~CloudDocs/Projects/Vermont-Signal')

from vermont_news_analyzer.modules.proximity_matrix import ProximityMatrix

# Sample article with entities at different positions
sample_entities = [
    # Sentence 0: Governor Phil Scott and Vermont Legislature
    {'entity': 'Phil Scott', 'type': 'PERSON', 'sentence_index': 0, 'confidence': 0.95},
    {'entity': 'Vermont Legislature', 'type': 'ORG', 'sentence_index': 0, 'confidence': 0.90},

    # Sentence 1: Budget discussion with Commissioner Mike Smith
    {'entity': 'Mike Smith', 'type': 'PERSON', 'sentence_index': 1, 'confidence': 0.88},
    {'entity': 'Vermont Legislature', 'type': 'ORG', 'sentence_index': 1, 'confidence': 0.90},

    # Sentence 2: Phil Scott responds
    {'entity': 'Phil Scott', 'type': 'PERSON', 'sentence_index': 2, 'confidence': 0.95},

    # Sentence 3: Montpelier location mentioned
    {'entity': 'Montpelier', 'type': 'GPE', 'sentence_index': 3, 'confidence': 0.92},

    # Sentence 5: New topic - unrelated entity
    {'entity': 'Burlington', 'type': 'GPE', 'sentence_index': 5, 'confidence': 0.93},
]

def main():
    print("=" * 80)
    print("PROXIMITY MATRIX TEST")
    print("=" * 80)

    # Build proximity matrix with window size 2
    matrix_builder = ProximityMatrix(window_size=2)
    co_matrix = matrix_builder.build_matrix(sample_entities, article_id=1)

    print(f"\nTotal entity pairs detected: {len(co_matrix)}")
    print(f"Entities processed: {len(sample_entities)}")

    # Get statistics
    stats = matrix_builder.get_statistics(co_matrix)
    print("\n" + "-" * 80)
    print("STATISTICS")
    print("-" * 80)
    print(f"Total pairs: {stats['total_pairs']}")
    print(f"Same sentence: {stats['same_sentence']}")
    print(f"Adjacent sentence: {stats['adjacent_sentence']}")
    print(f"Near proximity: {stats['near_proximity']}")
    print(f"Average weight: {stats['avg_weight']:.2f}")
    print(f"Max weight: {stats['max_weight']:.1f}")
    print(f"Min weight: {stats['min_weight']:.1f}")

    # Display top relationships by weight
    print("\n" + "-" * 80)
    print("TOP RELATIONSHIPS (by proximity weight)")
    print("-" * 80)

    sorted_pairs = sorted(co_matrix.items(), key=lambda x: x[1].total_weight, reverse=True)

    for pair, data in sorted_pairs[:10]:  # Top 10
        rel_type = matrix_builder.get_relationship_type(data)
        description = matrix_builder.format_relationship_description(data)

        print(f"\n{pair[0]} ↔ {pair[1]}")
        print(f"  Type: {rel_type}")
        print(f"  Weight: {data.total_weight:.1f}")
        print(f"  Distance: min={data.min_distance}, avg={data.avg_distance:.1f}, max={data.max_distance}")
        print(f"  Description: {description}")

    # Test filtering
    print("\n" + "-" * 80)
    print("FILTERED RELATIONSHIPS (weight >= 3.0, same sentence only)")
    print("-" * 80)

    filtered = matrix_builder.filter_by_weight(co_matrix, min_weight=3.0)
    print(f"Pairs after filtering: {len(filtered)}/{len(co_matrix)}")

    for pair, data in filtered.items():
        print(f"  {pair[0]} ↔ {pair[1]}: weight={data.total_weight:.1f}")

    # Entity frequencies
    print("\n" + "-" * 80)
    print("ENTITY FREQUENCIES (sentences)")
    print("-" * 80)

    frequencies = matrix_builder.calculate_entity_frequencies(sample_entities)
    for entity, count in sorted(frequencies.items(), key=lambda x: x[1], reverse=True):
        print(f"  {entity}: {count} sentence(s)")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
