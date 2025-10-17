# Vermont Signal: Intelligent Entity Network Implementation Plan
## Option B: Full Implementation (3-Week Timeline)

**Project Goal:** Transform entity networks from naive article-level co-occurrence to an intelligent proximity-weighted, PMI-scored, dynamically-filtered system.

**Expected Outcome:**
- 70-85% reduction in false connections
- Dramatically improved network clarity
- Small articles: Show meaningful connections (not isolated nodes)
- Large articles: Filter to top relationships (not hairballs)

**Cost Impact:** <$1/month additional hosting cost
**Code Addition:** ~1,150 lines of new code (+52% to backend)
**Timeline:** 15 working days

---

## Table of Contents

1. [Week 1: Foundation - Position Tracking & Proximity](#week-1-foundation)
   - Day 1-2: Database Schema Enhancement
   - Day 3-4: Position Tracking in Extraction Pipeline
   - Day 5-7: Proximity-Weighted Co-occurrence Matrix
2. [Week 2: Intelligence - PMI & Dynamic Thresholding](#week-2-intelligence)
   - Day 8-9: PMI Calculator Implementation
   - Day 10-11: Dynamic Thresholding System
   - Day 12: Confidence-Driven Pruning
3. [Week 3: Integration - API, Visualization & Testing](#week-3-integration)
   - Day 13: Integrated Relationship Generator
   - Day 14: API Endpoints & Frontend Updates
   - Day 15: Testing, Documentation & Deployment

---

## ✓ WEEK 1 COMPLETED: Foundation - Position Tracking & Proximity Co-occurrence

**Status:** Implemented and pushed to GitHub (Commits: Week 1 Day 1-2, Day 3-4, Day 5-7)

### Summary of Implementation

**Day 1-2: Database Schema Enhancement**
- Created migration scripts (`001_add_position_tracking.sql`, `002_enhance_relationships_table.sql`)
- Added position columns to `facts` table: `sentence_index`, `paragraph_index`, `char_start`, `char_end`
- Enhanced `entity_relationships` table with: `pmi_score`, `npmi_score`, `proximity_weight`, `min_sentence_distance`, `avg_sentence_distance`, `confidence_avg`
- Updated `database.py` schema and `store_facts()` method to handle position data
- All changes backward compatible (nullable columns)

**Day 3-4: Position Tracking in Extraction Pipeline**
- Created `position_tracker.py` module with `PositionTracker` class
- Uses spaCy for sentence segmentation with regex fallback
- Finds entity positions at sentence, paragraph, and character level
- Integrated into `batch_processor.py` with graceful degradation
- Created comprehensive unit tests (`test_position_tracker.py`)
- Tested: sentence splitting, paragraph boundaries, entity finding, position enrichment

**Day 5-7: Proximity Matrix & PMI Calculator**
- Created `proximity_matrix.py` with `ProximityMatrix` class
  - Configurable window size (default ±2 sentences)
  - Proximity weighting: same sentence=3.0, adjacent=2.0, near=1.0
  - Tracks min/max/avg distances and occurrence counts
- Created `pmi_calculator.py` with **HYBRID SCORING APPROACH**
  - **PMI scoring** for entities appearing in 2+ articles (stable statistics)
  - **Proximity-only scoring** for entities in 1 article (avoids PMI instability)
  - Calculates PMI, NPMI, confidence-weighted scores
  - Batch processing and corpus-level frequencies
- Created `dynamic_thresholder.py` with adaptive filtering
  - Size-aware: small (≤10 entities), medium (11-25), large (>25)
  - Three-stage filtering: absolute threshold → percentile → degree cap
  - Prevents over-filtering (small articles) and hairballs (large articles)
- Created comprehensive unit tests for all modules (15+ tests each)

**Key Technical Decisions:**
- Hybrid scoring addresses PMI instability for rare entities
- Graceful degradation if position tracking fails
- Backward compatible database schema
- All modules tested with edge cases

**Files Created/Modified:**
- `scripts/migrations/001_add_position_tracking.sql` (+ rollback)
- `scripts/migrations/002_enhance_relationships_table.sql` (+ rollback)
- `vermont_news_analyzer/modules/database.py` (modified)
- `vermont_news_analyzer/modules/position_tracker.py` (new)
- `vermont_news_analyzer/modules/proximity_matrix.py` (new)
- `vermont_news_analyzer/modules/pmi_calculator.py` (new)
- `vermont_news_analyzer/modules/dynamic_thresholder.py` (new)
- `vermont_news_analyzer/batch_processor.py` (modified)
- `tests/unit/test_position_tracker.py` (new)
- `tests/unit/test_proximity_matrix.py` (new)
- `tests/unit/test_pmi_calculator.py` (new)
- `tests/unit/test_dynamic_thresholder.py` (new)

---
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
```

**Unit Test File:** `tests/unit/test_proximity_matrix.py`

```python
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
    matrix_builder = ProximityMatrix(window_size=1)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Alice and Bob in same sentence (index 0)
    alice_bob = co_matrix.get(('Alice', 'Bob'))
    assert alice_bob is not None
    assert alice_bob.same_sentence_count >= 1
    assert alice_bob.total_weight >= 3  # Same sentence = weight 3


def test_build_matrix_adjacent_sentences(sample_entities):
    """Test co-occurrence in adjacent sentences"""
    matrix_builder = ProximityMatrix(window_size=1)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Alice in sentence 0, Charlie in sentence 1
    alice_charlie = co_matrix.get(('Alice', 'Charlie'))
    assert alice_charlie is not None
    assert alice_charlie.adjacent_sentence_count >= 1
    assert alice_charlie.total_weight >= 2  # Adjacent = weight 2


def test_build_matrix_window_size():
    """Test different window sizes"""
    entities = [
        {'entity': 'A', 'type': 'X', 'sentence_index': 0, 'confidence': 1.0},
        {'entity': 'B', 'type': 'X', 'sentence_index': 3, 'confidence': 1.0},
    ]

    # Window size 0: no connection (3 sentences apart)
    matrix_0 = ProximityMatrix(window_size=0).build_matrix(entities)
    assert ('A', 'B') not in matrix_0

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


def test_filter_by_weight(sample_entities):
    """Test filtering by minimum weight"""
    matrix_builder = ProximityMatrix(window_size=1)
    co_matrix = matrix_builder.build_matrix(sample_entities)

    # Filter for weight >= 3 (same sentence only)
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
```

---

## WEEK 2: Intelligence - PMI & Dynamic Thresholding

### Day 8-9: PMI Calculator Implementation

#### Task 2.1: Create PMI Calculator Module

**File:** `vermont_news_analyzer/modules/pmi_calculator.py`

```python
"""
Pointwise Mutual Information (PMI) Calculator
Calculates statistical significance of entity co-occurrences
"""

import logging
import math
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PMIScore:
    """Container for PMI calculation results"""
    entity_a: str
    entity_b: str
    pmi: float  # Raw PMI (unbounded)
    npmi: float  # Normalized PMI (range: -1 to 1)
    pmi_score: float  # Adjusted PMI (confidence-weighted)
    p_xy: float  # Joint probability
    p_x: float  # Marginal probability of entity_a
    p_y: float  # Marginal probability of entity_b
    raw_count: int  # Raw co-occurrence count


class PMICalculator:
    """
    Calculates Pointwise Mutual Information for entity pairs

    PMI measures how much more often two entities appear together than
    would be expected by chance if they were independent.

    PMI = log(P(x,y) / (P(x) * P(y)))

    High PMI (> 0): Entities appear together more than random chance
    PMI ≈ 0: Entities appear independently
    Low PMI (< 0): Entities avoid each other (rare in same article)

    NPMI normalizes to range [-1, 1] for easier interpretation
    """

    def __init__(self, smoothing: float = 1e-6):
        """
        Initialize PMI calculator

        Args:
            smoothing: Laplace smoothing factor to avoid log(0)
        """
        self.smoothing = smoothing

    def calculate_corpus_frequencies(
        self,
        article_entities: Dict[int, list]
    ) -> Tuple[Dict[str, int], int]:
        """
        Calculate entity frequencies across entire corpus

        Args:
            article_entities: Dict mapping article_id to list of entity dicts

        Returns:
            Tuple of (entity_frequency_dict, total_documents)
        """
        entity_freq = defaultdict(set)  # entity -> set of article IDs

        for article_id, entities in article_entities.items():
            seen_entities = set()
            for entity in entities:
                entity_name = entity['entity']
                if entity_name not in seen_entities:
                    entity_freq[entity_name].add(article_id)
                    seen_entities.add(entity_name)

        # Convert sets to counts
        entity_counts = {entity: len(article_ids) for entity, article_ids in entity_freq.items()}
        total_docs = len(article_entities)

        logger.info(f"Calculated corpus frequencies: {len(entity_counts)} unique entities across {total_docs} articles")

        return entity_counts, total_docs

    def calculate_pmi(
        self,
        entity_a: str,
        entity_b: str,
        cooccurrence_count: int,
        entity_freq_a: int,
        entity_freq_b: int,
        total_documents: int,
        confidence_a: float = 1.0,
        confidence_b: float = 1.0
    ) -> PMIScore:
        """
        Calculate PMI score for an entity pair

        Args:
            entity_a: First entity name
            entity_b: Second entity name
            cooccurrence_count: Number of documents where they co-occur
            entity_freq_a: Number of documents containing entity_a
            entity_freq_b: Number of documents containing entity_b
            total_documents: Total number of documents in corpus
            confidence_a: Confidence score for entity_a (0-1)
            confidence_b: Confidence score for entity_b (0-1)

        Returns:
            PMIScore object with all calculated metrics
        """
        # Calculate probabilities with smoothing
        p_xy = (cooccurrence_count + self.smoothing) / (total_documents + self.smoothing)
        p_x = (entity_freq_a + self.smoothing) / (total_documents + self.smoothing)
        p_y = (entity_freq_b + self.smoothing) / (total_documents + self.smoothing)

        # Calculate PMI
        pmi = math.log(p_xy / (p_x * p_y + self.smoothing) + self.smoothing)

        # Calculate Normalized PMI (bounds to [-1, 1])
        # NPMI = PMI / -log(P(x,y))
        npmi = pmi / (-math.log(p_xy + self.smoothing) + self.smoothing)

        # Confidence-adjusted PMI
        avg_confidence = (confidence_a + confidence_b) / 2.0
        adjusted_pmi = pmi * avg_confidence

        return PMIScore(
            entity_a=entity_a,
            entity_b=entity_b,
            pmi=pmi,
            npmi=npmi,
            pmi_score=adjusted_pmi,
            p_xy=p_xy,
            p_x=p_x,
            p_y=p_y,
            raw_count=cooccurrence_count
        )

    def calculate_pmi_batch(
        self,
        cooccurrence_matrix: Dict[Tuple[str, str], Dict],
        entity_frequencies: Dict[str, int],
        total_documents: int
    ) -> Dict[Tuple[str, str], PMIScore]:
        """
        Calculate PMI for multiple entity pairs

        Args:
            cooccurrence_matrix: Dict mapping (entity_a, entity_b) to co-occurrence data
                                Expected keys: 'count', 'confidence_a', 'confidence_b'
            entity_frequencies: Dict mapping entity names to document frequencies
            total_documents: Total number of documents

        Returns:
            Dict mapping entity pairs to PMIScore objects
        """
        pmi_scores = {}

        for (entity_a, entity_b), cooc_data in cooccurrence_matrix.items():
            # Extract data
            cooc_count = cooc_data.get('count', 0)
            conf_a = cooc_data.get('confidence_a', 1.0)
            conf_b = cooc_data.get('confidence_b', 1.0)

            # Get entity frequencies
            freq_a = entity_frequencies.get(entity_a, 1)  # Default to 1 if not found
            freq_b = entity_frequencies.get(entity_b, 1)

            # Calculate PMI
            pmi_score = self.calculate_pmi(
                entity_a, entity_b,
                cooc_count,
                freq_a, freq_b,
                total_documents,
                conf_a, conf_b
            )

            pmi_scores[(entity_a, entity_b)] = pmi_score

        logger.info(f"Calculated PMI for {len(pmi_scores)} entity pairs")

        return pmi_scores

    def filter_by_pmi_threshold(
        self,
        pmi_scores: Dict[Tuple[str, str], PMIScore],
        min_pmi: float = 0.0,
        use_npmi: bool = True
    ) -> Dict[Tuple[str, str], PMIScore]:
        """
        Filter entity pairs by PMI threshold

        Args:
            pmi_scores: Dict of PMI scores
            min_pmi: Minimum PMI/NPMI threshold
            use_npmi: Whether to use NPMI (normalized) or raw PMI

        Returns:
            Filtered dict
        """
        if use_npmi:
            return {
                pair: score
                for pair, score in pmi_scores.items()
                if score.npmi >= min_pmi
            }
        else:
            return {
                pair: score
                for pair, score in pmi_scores.items()
                if score.pmi >= min_pmi
            }

    def get_pmi_statistics(
        self,
        pmi_scores: Dict[Tuple[str, str], PMIScore]
    ) -> Dict:
        """
        Calculate summary statistics for PMI scores

        Args:
            pmi_scores: Dict of PMI scores

        Returns:
            Dict with statistics
        """
        if not pmi_scores:
            return {
                'count': 0,
                'min_pmi': 0,
                'max_pmi': 0,
                'mean_pmi': 0,
                'min_npmi': 0,
                'max_npmi': 0,
                'mean_npmi': 0
            }

        pmis = [score.pmi for score in pmi_scores.values()]
        npmis = [score.npmi for score in pmi_scores.values()]

        return {
            'count': len(pmi_scores),
            'min_pmi': min(pmis),
            'max_pmi': max(pmis),
            'mean_pmi': sum(pmis) / len(pmis),
            'min_npmi': min(npmis),
            'max_npmi': max(npmis),
            'mean_npmi': sum(npmis) / len(npmis)
        }
```

**Unit Test File:** `tests/unit/test_pmi_calculator.py`

```python
"""
Unit tests for PMI calculator
"""

import pytest
import math
from vermont_news_analyzer.modules.pmi_calculator import PMICalculator, PMIScore


@pytest.fixture
def calculator():
    return PMICalculator(smoothing=1e-6)


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
        confidence_b=1.0
    )

    # PMI should be high (they always appear together)
    assert pmi_score.pmi > 0
    # NPMI should be close to 1
    assert pmi_score.npmi > 0.5


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
        total_documents=100
    )

    # PMI should be close to 0 (independent)
    assert abs(pmi_score.pmi) < 0.5
    assert abs(pmi_score.npmi) < 0.3


def test_pmi_calculation_rare_cooccurrence(calculator):
    """Test PMI with rare but significant co-occurrence"""
    # Both entities are rare (appear in 2/100 documents each)
    # But they co-occur both times = strong signal

    pmi_score = calculator.calculate_pmi(
        entity_a='A',
        entity_b='B',
        cooccurrence_count=2,
        entity_freq_a=2,
        entity_freq_b=2,
        total_documents=100
    )

    # High PMI despite low counts
    assert pmi_score.pmi > 0


def test_pmi_batch_calculation(calculator):
    """Test batch PMI calculation"""
    cooc_matrix = {
        ('A', 'B'): {'count': 10, 'confidence_a': 0.9, 'confidence_b': 0.85},
        ('A', 'C'): {'count': 5, 'confidence_a': 0.9, 'confidence_b': 0.8},
        ('B', 'C'): {'count': 3, 'confidence_a': 0.85, 'confidence_b': 0.8}
    }

    entity_frequencies = {
        'A': 15,
        'B': 12,
        'C': 8
    }

    pmi_scores = calculator.calculate_pmi_batch(
        cooc_matrix,
        entity_frequencies,
        total_documents=20
    )

    assert len(pmi_scores) == 3
    assert ('A', 'B') in pmi_scores
    assert all(isinstance(score, PMIScore) for score in pmi_scores.values())


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


def test_pmi_filtering(calculator):
    """Test PMI threshold filtering"""
    pmi_scores = {
        ('A', 'B'): PMIScore('A', 'B', pmi=2.0, npmi=0.8, pmi_score=1.8, p_xy=0.1, p_x=0.2, p_y=0.2, raw_count=10),
        ('A', 'C'): PMIScore('A', 'C', pmi=0.5, npmi=0.2, pmi_score=0.4, p_xy=0.05, p_x=0.2, p_y=0.1, raw_count=5),
        ('B', 'C'): PMIScore('B', 'C', pmi=-0.5, npmi=-0.1, pmi_score=-0.4, p_xy=0.02, p_x=0.2, p_y=0.1, raw_count=2)
    }

    # Filter for NPMI >= 0.5
    filtered = calculator.filter_by_pmi_threshold(pmi_scores, min_pmi=0.5, use_npmi=True)

    assert len(filtered) == 1
    assert ('A', 'B') in filtered


def test_confidence_weighting(calculator):
    """Test that confidence affects PMI score"""
    # Same co-occurrence, different confidences

    high_conf = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=10,
        entity_freq_a=20, entity_freq_b=20, total_documents=100,
        confidence_a=0.9, confidence_b=0.9
    )

    low_conf = calculator.calculate_pmi(
        'A', 'B',
        cooccurrence_count=10,
        entity_freq_a=20, entity_freq_b=20, total_documents=100,
        confidence_a=0.5, confidence_b=0.5
    )

    # PMI and NPMI should be same (statistical measure)
    assert abs(high_conf.pmi - low_conf.pmi) < 0.001
    assert abs(high_conf.npmi - low_conf.npmi) < 0.001

    # But adjusted PMI score should differ
    assert high_conf.pmi_score > low_conf.pmi_score
```

---

### Day 10-11: Dynamic Thresholding System

#### Task 2.2: Create Dynamic Thresholder Module

**File:** `vermont_news_analyzer/modules/dynamic_thresholder.py`

```python
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
    min_npmi: float  # Minimum NPMI score
    max_edges_per_entity: int  # Maximum connections per entity
    percentile_cutoff: int  # Percentile for edge filtering (e.g., 80 = keep top 20%)
    description: str


class DynamicThresholder:
    """
    Applies size-aware, adaptive filtering to entity relationship networks

    Strategy:
    1. Categorize article by entity count (small/medium/large)
    2. Apply absolute NPMI threshold
    3. Apply percentile-based filtering
    4. Cap per-node degree to prevent hubs
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
            edges: List of edge dicts with 'source', 'target', 'npmi', 'confidence', etc.
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

        # Stage 1: Absolute NPMI threshold
        candidates = [e for e in edges if e.get('npmi', 0) >= config.min_npmi]

        logger.info(f"  Stage 1 (NPMI >= {config.min_npmi}): {len(candidates)} edges remain")

        if not candidates:
            # Fallback: If too strict, keep top 3 strongest edges
            logger.warning("No edges passed NPMI threshold, falling back to top 3")
            return sorted(edges, key=lambda e: e.get('npmi', 0), reverse=True)[:3]

        # Stage 2: Percentile-based cutoff
        npmi_values = [e.get('npmi', 0) for e in candidates]
        percentile_value = np.percentile(npmi_values, config.percentile_cutoff)
        candidates = [e for e in candidates if e.get('npmi', 0) >= percentile_value]

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

        logger.info(
            f"Final: Kept {len(filtered)}/{len(edges)} edges "
            f"({len(filtered)/len(edges)*100:.1f}% reduction)"
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
        # Sort edges by strength (NPMI * confidence)
        edges.sort(
            key=lambda e: e.get('npmi', 0) * e.get('confidence_avg', 1.0),
            reverse=True
        )

        # Track degree for each node
        node_degrees = defaultdict(int)
        filtered = []

        for edge in edges:
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
        Create custom threshold configuration

        Args:
            min_npmi: Minimum NPMI threshold
            max_edges_per_entity: Max connections per entity
            percentile_cutoff: Percentile for filtering
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
```

**Unit Test File:** `tests/unit/test_dynamic_thresholder.py`

```python
"""
Unit tests for dynamic thresholder
"""

import pytest
from vermont_news_analyzer.modules.dynamic_thresholder import (
    DynamicThresholder, ArticleSize, ThresholdConfig
)


def test_article_size_determination():
    """Test article size categorization"""
    assert DynamicThresholder.determine_article_size(5) == ArticleSize.SMALL
    assert DynamicThresholder.determine_article_size(10) == ArticleSize.SMALL
    assert DynamicThresholder.determine_article_size(15) == ArticleSize.MEDIUM
    assert DynamicThresholder.determine_article_size(25) == ArticleSize.MEDIUM
    assert DynamicThresholder.determine_article_size(30) == ArticleSize.LARGE


def test_get_threshold_config():
    """Test getting appropriate config for article size"""
    small_config = DynamicThresholder.get_threshold_config(5)
    assert small_config.min_npmi < 0.5  # More permissive

    large_config = DynamicThresholder.get_threshold_config(40)
    assert large_config.min_npmi > 0.5  # More strict


def test_filter_edges_small_article():
    """Test filtering for small article"""
    edges = [
        {'source': 'A', 'target': 'B', 'npmi': 0.8, 'confidence_avg': 0.9},
        {'source': 'A', 'target': 'C', 'npmi': 0.4, 'confidence_avg': 0.85},
        {'source': 'B', 'target': 'C', 'npmi': 0.2, 'confidence_avg': 0.8}
    ]

    # Small article (5 entities) should be more permissive
    filtered = DynamicThresholder.filter_edges(edges, entity_count=5)

    # Should keep some edges even with lower NPMI
    assert len(filtered) >= 1


def test_filter_edges_large_article():
    """Test filtering for large article"""
    # Create many edges
    edges = []
    for i in range(50):
        edges.append({
            'source': f'Entity{i}',
            'target': f'Entity{i+1}',
            'npmi': 0.3 + (i * 0.01),  # NPMI from 0.3 to 0.8
            'confidence_avg': 0.8
        })

    # Large article (40 entities) should filter aggressively
    filtered = DynamicThresholder.filter_edges(edges, entity_count=40)

    # Should significantly reduce edge count
    assert len(filtered) < len(edges) * 0.6  # At least 40% reduction


def test_degree_capping():
    """Test per-node degree capping"""
    # Create hub: Entity A connects to many others
    edges = []
    for i in range(15):
        edges.append({
            'source': 'A',
            'target': f'B{i}',
            'npmi': 0.8,
            'confidence_avg': 0.9
        })

    # Apply degree cap of 5
    config = ThresholdConfig(min_npmi=0.3, max_edges_per_entity=5, percentile_cutoff=50, description="Test")
    filtered = DynamicThresholder.filter_edges(edges, entity_count=20, custom_config=config)

    # Entity A should have at most 5 connections
    a_edges = [e for e in filtered if e['source'] == 'A' or e['target'] == 'A']
    assert len(a_edges) <= 5


def test_percentile_filtering():
    """Test percentile-based filtering"""
    # Create edges with varying NPMI
    edges = []
    for i in range(100):
        edges.append({
            'source': f'E{i}',
            'target': f'E{i+1}',
            'npmi': i / 100.0,  # NPMI from 0.0 to 0.99
            'confidence_avg': 0.8
        })

    # Use 80th percentile cutoff
    config = ThresholdConfig(min_npmi=0.0, max_edges_per_entity=100, percentile_cutoff=80, description="Test")
    filtered = DynamicThresholder.filter_edges(edges, entity_count=100, custom_config=config)

    # Should keep roughly top 20%
    assert len(filtered) <= 25  # Allow some variance


def test_fallback_for_strict_threshold():
    """Test fallback when no edges pass threshold"""
    edges = [
        {'source': 'A', 'target': 'B', 'npmi': 0.1, 'confidence_avg': 0.7},
        {'source': 'A', 'target': 'C', 'npmi': 0.2, 'confidence_avg': 0.6},
        {'source': 'B', 'target': 'C', 'npmi': 0.15, 'confidence_avg': 0.65}
    ]

    # Very strict config that would filter everything
    config = ThresholdConfig(min_npmi=0.9, max_edges_per_entity=5, percentile_cutoff=90, description="Very strict")
    filtered = DynamicThresholder.filter_edges(edges, entity_count=3, custom_config=config)

    # Should fall back to top 3 edges
    assert len(filtered) == 3


def test_filtering_summary():
    """Test filtering summary generation"""
    summary = DynamicThresholder.get_filtering_summary(
        original_count=100,
        filtered_count=30,
        entity_count=15
    )

    assert summary['article_size'] == 'medium'
    assert summary['entity_count'] == 15
    assert summary['reduction_percentage'] == 70.0
    assert 'config_applied' in summary


def test_custom_config_creation():
    """Test creating custom configuration"""
    config = DynamicThresholder.create_custom_config(
        min_npmi=0.7,
        max_edges_per_entity=6,
        percentile_cutoff=75,
        description="Custom test config"
    )

    assert config.min_npmi == 0.7
    assert config.max_edges_per_entity == 6
    assert config.percentile_cutoff == 75
    assert config.description == "Custom test config"
```

---

### Day 12: Confidence-Driven Pruning

#### Task 2.3: Add Confidence Weighting Functions

**File:** `vermont_news_analyzer/modules/confidence_weighting.py`

```python
"""
Confidence-Driven Edge Pruning
Adjusts relationship strength based on entity confidence scores
"""

import logging
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceMode(Enum):
    """Confidence weighting strategies"""
    MULTIPLY = 'multiply'  # strength = PMI × conf_a × conf_b
    HARMONIC = 'harmonic'  # strength = PMI × harmonic_mean(conf_a, conf_b)
    MINIMUM = 'minimum'    # strength = PMI × min(conf_a, conf_b)
    HYBRID = 'hybrid'      # Weighted combination


class ConfidenceWeighter:
    """
    Applies confidence-based weighting to relationship strengths
    """

    @staticmethod
    def calculate_confidence_weight(
        confidence_a: float,
        confidence_b: float,
        mode: ConfidenceMode = ConfidenceMode.HARMONIC
    ) -> float:
        """
        Calculate confidence weight for an entity pair

        Args:
            confidence_a: Confidence score for entity A (0-1)
            confidence_b: Confidence score for entity B (0-1)
            mode: Weighting strategy

        Returns:
            Confidence weight (0-1)
        """
        if mode == ConfidenceMode.MULTIPLY:
            # Multiplicative: Harshly penalizes low confidence
            return confidence_a * confidence_b

        elif mode == ConfidenceMode.HARMONIC:
            # Harmonic mean: More forgiving than multiply
            if confidence_a == 0 or confidence_b == 0:
                return 0
            return 2 / (1/confidence_a + 1/confidence_b)

        elif mode == ConfidenceMode.MINIMUM:
            # Weakest link: Only as strong as weakest entity
            return min(confidence_a, confidence_b)

        elif mode == ConfidenceMode.HYBRID:
            # Weighted combination
            return (
                (confidence_a * confidence_b) * 0.4 +  # Product
                min(confidence_a, confidence_b) * 0.3 +  # Minimum
                (confidence_a + confidence_b) / 2 * 0.3  # Average
            )

        return 1.0

    @staticmethod
    def apply_confidence_weighting(
        pmi_score: float,
        confidence_a: float,
        confidence_b: float,
        mode: ConfidenceMode = ConfidenceMode.HARMONIC
    ) -> float:
        """
        Apply confidence weighting to PMI score

        Args:
            pmi_score: PMI or NPMI score
            confidence_a: Confidence for entity A
            confidence_b: Confidence for entity B
            mode: Weighting strategy

        Returns:
            Confidence-weighted score
        """
        conf_weight = ConfidenceWeighter.calculate_confidence_weight(
            confidence_a, confidence_b, mode
        )
        return pmi_score * conf_weight

    @staticmethod
    def filter_by_confidence(
        edges: List[Dict],
        min_entity_confidence: float = 0.6,
        min_relationship_confidence: float = 0.5,
        mode: ConfidenceMode = ConfidenceMode.HARMONIC
    ) -> List[Dict]:
        """
        Filter edges based on confidence thresholds

        Args:
            edges: List of edge dicts with confidence scores
            min_entity_confidence: Minimum confidence for individual entities
            min_relationship_confidence: Minimum for weighted relationship
            mode: Weighting strategy

        Returns:
            Filtered edges with added 'weighted_strength' field
        """
        filtered = []

        for edge in edges:
            conf_a = edge.get('confidence_a', 1.0)
            conf_b = edge.get('confidence_b', 1.0)

            # Check individual entity confidences
            if conf_a < min_entity_confidence or conf_b < min_entity_confidence:
                continue

            # Calculate weighted strength
            pmi = edge.get('npmi', 0)
            weighted_strength = ConfidenceWeighter.apply_confidence_weighting(
                pmi, conf_a, conf_b, mode
            )

            # Check relationship confidence
            if weighted_strength >= min_relationship_confidence:
                edge['weighted_strength'] = weighted_strength
                edge['confidence_weight'] = ConfidenceWeighter.calculate_confidence_weight(
                    conf_a, conf_b, mode
                )
                filtered.append(edge)

        logger.info(
            f"Confidence filtering: {len(filtered)}/{len(edges)} edges passed "
            f"(mode: {mode.value}, min_entity: {min_entity_confidence}, "
            f"min_relationship: {min_relationship_confidence})"
        )

        return filtered

    @staticmethod
    def boost_wikidata_confidence(
        entities: List[Dict],
        boost_amount: float = 0.1
    ) -> List[Dict]:
        """
        Boost confidence for entities with Wikidata validation

        Args:
            entities: List of entity dicts
            boost_amount: Amount to boost confidence (0-0.2 recommended)

        Returns:
            Same list with boosted confidences
        """
        for entity in entities:
            if entity.get('wikidata_id'):
                original_conf = entity.get('confidence', 0.5)
                entity['confidence'] = min(1.0, original_conf + boost_amount)
                entity['confidence_boosted'] = True

        boosted_count = sum(1 for e in entities if e.get('confidence_boosted'))
        logger.info(f"Boosted confidence for {boosted_count} Wikidata-validated entities")

        return entities
```

**Unit Test File:** `tests/unit/test_confidence_weighting.py`

```python
"""
Unit tests for confidence weighting
"""

import pytest
from vermont_news_analyzer.modules.confidence_weighting import (
    ConfidenceWeighter, ConfidenceMode
)


def test_multiply_mode():
    """Test multiplicative confidence weighting"""
    # Perfect confidence
    assert ConfidenceWeighter.calculate_confidence_weight(1.0, 1.0, ConfidenceMode.MULTIPLY) == 1.0

    # Moderate confidence
    weight = ConfidenceWeighter.calculate_confidence_weight(0.7, 0.7, ConfidenceMode.MULTIPLY)
    assert weight == pytest.approx(0.49)

    # One low confidence
    weight = ConfidenceWeighter.calculate_confidence_weight(0.9, 0.5, ConfidenceMode.MULTIPLY)
    assert weight == pytest.approx(0.45)


def test_harmonic_mode():
    """Test harmonic mean confidence weighting"""
    # Equal confidence
    weight = ConfidenceWeighter.calculate_confidence_weight(0.7, 0.7, ConfidenceMode.HARMONIC)
    assert weight == pytest.approx(0.7)

    # Unequal confidence - should be closer to lower value
    weight = ConfidenceWeighter.calculate_confidence_weight(0.9, 0.5, ConfidenceMode.HARMONIC)
    assert 0.5 < weight < 0.7  # Between min and average

    # Zero confidence
    weight = ConfidenceWeighter.calculate_confidence_weight(0.8, 0.0, ConfidenceMode.HARMONIC)
    assert weight == 0.0


def test_minimum_mode():
    """Test minimum confidence weighting"""
    weight = ConfidenceWeighter.calculate_confidence_weight(0.9, 0.6, ConfidenceMode.MINIMUM)
    assert weight == 0.6  # Weakest link

    weight = ConfidenceWeighter.calculate_confidence_weight(0.5, 0.8, ConfidenceMode.MINIMUM)
    assert weight == 0.5


def test_apply_confidence_weighting():
    """Test applying confidence to PMI score"""
    pmi = 2.0

    weighted = ConfidenceWeighter.apply_confidence_weighting(
        pmi, 0.8, 0.8, ConfidenceMode.MULTIPLY
    )

    assert weighted == pytest.approx(2.0 * 0.64)


def test_filter_by_confidence():
    """Test edge filtering by confidence"""
    edges = [
        {'source': 'A', 'target': 'B', 'npmi': 0.8, 'confidence_a': 0.9, 'confidence_b': 0.85},
        {'source': 'A', 'target': 'C', 'npmi': 0.7, 'confidence_a': 0.9, 'confidence_b': 0.5},  # Low B
        {'source': 'B', 'target': 'C', 'npmi': 0.6, 'confidence_a': 0.4, 'confidence_b': 0.8},  # Low A
        {'source': 'D', 'target': 'E', 'npmi': 0.9, 'confidence_a': 0.95, 'confidence_b': 0.9}
    ]

    filtered = ConfidenceWeighter.filter_by_confidence(
        edges,
        min_entity_confidence=0.6,
        min_relationship_confidence=0.5,
        mode=ConfidenceMode.HARMONIC
    )

    # Should filter out edges with confidence < 0.6
    assert len(filtered) == 2
    assert all(e.get('weighted_strength') is not None for e in filtered)


def test_wikidata_confidence_boost():
    """Test confidence boosting for Wikidata entities"""
    entities = [
        {'entity': 'A', 'confidence': 0.7, 'wikidata_id': 'Q123'},
        {'entity': 'B', 'confidence': 0.8, 'wikidata_id': None},
        {'entity': 'C', 'confidence': 0.6, 'wikidata_id': 'Q456'}
    ]

    boosted = ConfidenceWeighter.boost_wikidata_confidence(entities, boost_amount=0.1)

    assert boosted[0]['confidence'] == pytest.approx(0.8)  # Boosted
    assert boosted[1]['confidence'] == pytest.approx(0.8)  # Unchanged
    assert boosted[2]['confidence'] == pytest.approx(0.7)  # Boosted

    assert boosted[0].get('confidence_boosted') is True
    assert boosted[1].get('confidence_boosted') is None


def test_confidence_weight_comparison():
    """Compare different weighting modes"""
    conf_a, conf_b = 0.7, 0.9

    multiply = ConfidenceWeighter.calculate_confidence_weight(conf_a, conf_b, ConfidenceMode.MULTIPLY)
    harmonic = ConfidenceWeighter.calculate_confidence_weight(conf_a, conf_b, ConfidenceMode.HARMONIC)
    minimum = ConfidenceWeighter.calculate_confidence_weight(conf_a, conf_b, ConfidenceMode.MINIMUM)
    hybrid = ConfidenceWeighter.calculate_confidence_weight(conf_a, conf_b, ConfidenceMode.HYBRID)

    # Multiply should be harshest
    assert multiply < harmonic
    assert multiply < hybrid

    # Minimum should equal the lower value
    assert minimum == 0.7

    # Hybrid should be intermediate
    assert minimum < hybrid < (conf_a + conf_b) / 2
```

---

## WEEK 3: Integration - API, Visualization & Testing

### Day 13: Integrated Relationship Generator

#### Task 3.1: Create Integrated Relationship Generation Script

**File:** `scripts/generate_relationships_v3.py`

```python
#!/usr/bin/env python3
"""
Vermont Signal V3: Intelligent Relationship Generator
Combines proximity, PMI, dynamic thresholding, and confidence weighting
"""

import sys
import os
import logging
from typing import Dict, List, Optional
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.modules.proximity_matrix import ProximityMatrix
from vermont_news_analyzer.modules.pmi_calculator import PMICalculator
from vermont_news_analyzer.modules.dynamic_thresholder import DynamicThresholder
from vermont_news_analyzer.modules.confidence_weighting import ConfidenceWeighter, ConfidenceMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntelligentRelationshipGenerator:
    """
    Complete relationship generation pipeline with all intelligence layers
    """

    def __init__(self, db: VermontSignalDatabase):
        """
        Initialize generator

        Args:
            db: Database connection
        """
        self.db = db
        self.proximity_builder = ProximityMatrix(window_size=1)
        self.pmi_calculator = PMICalculator(smoothing=1e-6)
        self.confidence_mode = ConfidenceMode.HARMONIC

    def fetch_articles_with_entities(
        self,
        days: int = 30
    ) -> Dict[int, List[Dict]]:
        """
        Fetch articles and their entities from database

        Args:
            days: Articles from last N days

        Returns:
            Dict mapping article_id to list of entity dicts
        """
        query = """
            SELECT
                f.article_id,
                f.entity,
                f.entity_type,
                f.confidence,
                f.sentence_index,
                f.paragraph_index,
                a.title
            FROM facts f
            JOIN articles a ON f.article_id = a.id
            WHERE a.published_date >= CURRENT_DATE - INTERVAL %s
              AND a.processing_status = 'completed'
              AND f.sentence_index IS NOT NULL  -- Only entities with positions
            ORDER BY f.article_id, f.sentence_index
        """

        article_entities = defaultdict(list)

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (f'{days} days',))

                for row in cur.fetchall():
                    article_id = row[0]
                    article_entities[article_id].append({
                        'entity': row[1],
                        'type': row[2],
                        'confidence': float(row[3]) if row[3] else 0.8,
                        'sentence_index': row[4],
                        'paragraph_index': row[5],
                        'article_title': row[6]
                    })

        logger.info(f"Loaded {len(article_entities)} articles with entities")
        return dict(article_entities)

    def generate_for_article(
        self,
        article_id: int,
        entities: List[Dict]
    ) -> List[Dict]:
        """
        Generate relationships for a single article

        Args:
            article_id: Article ID
            entities: List of entity dicts with positions

        Returns:
            List of relationship dicts ready for database insertion
        """
        if not entities:
            return []

        logger.info(f"Processing article {article_id} with {len(entities)} entities")

        # Step 1: Build proximity-weighted co-occurrence matrix
        co_matrix = self.proximity_builder.build_matrix(entities, article_id)

        if not co_matrix:
            logger.warning(f"Article {article_id}: No co-occurrences found")
            return []

        # Step 2: Calculate entity frequencies (for this article only)
        entity_freq = self.proximity_builder.calculate_entity_frequencies(entities)
        total_sentences = len(set(e['sentence_index'] for e in entities if e.get('sentence_index') is not None))

        # Step 3: Calculate PMI scores
        pmi_inputs = {}
        for (entity_a, entity_b), cooc_data in co_matrix.items():
            # Get average confidence from occurrences
            if cooc_data.occurrences:
                avg_conf_a = sum(o['confidence_a'] for o in cooc_data.occurrences) / len(cooc_data.occurrences)
                avg_conf_b = sum(o['confidence_b'] for o in cooc_data.occurrences) / len(cooc_data.occurrences)
            else:
                avg_conf_a = avg_conf_b = 0.8

            pmi_inputs[(entity_a, entity_b)] = {
                'count': int(cooc_data.total_weight),
                'confidence_a': avg_conf_a,
                'confidence_b': avg_conf_b
            }

        pmi_scores = self.pmi_calculator.calculate_pmi_batch(
            pmi_inputs,
            entity_freq,
            total_sentences
        )

        # Step 4: Build edge list with all metadata
        edges = []
        for (entity_a, entity_b), pmi_score in pmi_scores.items():
            cooc_data = co_matrix[(entity_a, entity_b)]

            # Get confidence-weighted strength
            weighted_strength = ConfidenceWeighter.apply_confidence_weighting(
                pmi_score.npmi,
                pmi_score.p_x,  # Use from PMI score
                pmi_score.p_y,
                self.confidence_mode
            )

            edges.append({
                'source': entity_a,
                'target': entity_b,
                'npmi': pmi_score.npmi,
                'pmi': pmi_score.pmi,
                'confidence_a': pmi_inputs[(entity_a, entity_b)]['confidence_a'],
                'confidence_b': pmi_inputs[(entity_a, entity_b)]['confidence_b'],
                'confidence_avg': (pmi_inputs[(entity_a, entity_b)]['confidence_a'] +
                                  pmi_inputs[(entity_a, entity_b)]['confidence_b']) / 2,
                'weighted_strength': weighted_strength,
                'proximity_weight': cooc_data.total_weight,
                'min_distance': cooc_data.min_distance,
                'avg_distance': cooc_data.avg_distance,
                'raw_count': int(cooc_data.total_weight),
                'relationship_type': self.proximity_builder.get_relationship_type(cooc_data),
                'relationship_description': self.proximity_builder.format_relationship_description(cooc_data)
            })

        # Step 5: Apply dynamic thresholding
        filtered_edges = DynamicThresholder.filter_edges(edges, len(entities))

        # Step 6: Format for database insertion
        relationships = []
        for edge in filtered_edges:
            relationships.append({
                'article_id': article_id,
                'entity_a': edge['source'],
                'entity_b': edge['target'],
                'relationship_type': edge['relationship_type'],
                'relationship_description': edge['relationship_description'],
                'confidence': edge['confidence_avg'],
                'pmi_score': edge['pmi'],
                'npmi_score': edge['npmi'],
                'raw_cooccurrence_count': edge['raw_count'],
                'proximity_weight': edge['proximity_weight'],
                'min_sentence_distance': edge['min_distance'],
                'avg_sentence_distance': edge['avg_distance']
            })

        logger.info(
            f"Article {article_id}: Generated {len(relationships)} relationships "
            f"(filtered from {len(edges)} candidates)"
        )

        return relationships

    def store_relationships(self, relationships: List[Dict]):
        """
        Store relationships in database

        Args:
            relationships: List of relationship dicts
        """
        if not relationships:
            return

        insert_query = """
            INSERT INTO entity_relationships (
                article_id, entity_a, entity_b,
                relationship_type, relationship_description, confidence,
                pmi_score, npmi_score, raw_cooccurrence_count,
                proximity_weight, min_sentence_distance, avg_sentence_distance
            )
            VALUES (
                %(article_id)s, %(entity_a)s, %(entity_b)s,
                %(relationship_type)s, %(relationship_description)s, %(confidence)s,
                %(pmi_score)s, %(npmi_score)s, %(raw_cooccurrence_count)s,
                %(proximity_weight)s, %(min_sentence_distance)s, %(avg_sentence_distance)s
            )
            ON CONFLICT (article_id, entity_a, entity_b, relationship_type)
            DO UPDATE SET
                confidence = EXCLUDED.confidence,
                pmi_score = EXCLUDED.pmi_score,
                npmi_score = EXCLUDED.npmi_score,
                raw_cooccurrence_count = EXCLUDED.raw_cooccurrence_count,
                proximity_weight = EXCLUDED.proximity_weight,
                min_sentence_distance = EXCLUDED.min_sentence_distance,
                avg_sentence_distance = EXCLUDED.avg_sentence_distance
        """

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                for rel in relationships:
                    cur.execute(insert_query, rel)
                conn.commit()

        logger.info(f"Stored {len(relationships)} relationships")

    def generate_all(self, days: int = 30):
        """
        Generate relationships for all articles

        Args:
            days: Process articles from last N days
        """
        logger.info("=" * 80)
        logger.info("INTELLIGENT RELATIONSHIP GENERATION")
        logger.info("=" * 80)

        # Clear old relationships
        logger.info("Clearing old relationships...")
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM entity_relationships WHERE relationship_type IN ('same-sentence', 'adjacent-sentence', 'near-proximity')")
                deleted = cur.rowcount
                conn.commit()
        logger.info(f"Deleted {deleted} old proximity-based relationships")

        # Load articles
        article_entities = self.fetch_articles_with_entities(days)

        if not article_entities:
            logger.warning("No articles with positioned entities found!")
            return

        # Process each article
        total_relationships = 0
        for article_id, entities in article_entities.items():
            try:
                relationships = self.generate_for_article(article_id, entities)
                self.store_relationships(relationships)
                total_relationships += len(relationships)
            except Exception as e:
                logger.error(f"Failed to process article {article_id}: {e}", exc_info=True)

        logger.info("=" * 80)
        logger.info(f"COMPLETE: Generated {total_relationships} relationships across {len(article_entities)} articles")
        logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate intelligent entity relationships (v3 with proximity + PMI + dynamic filtering)'
    )
    parser.add_argument('--days', type=int, default=30, help='Process articles from last N days')

    args = parser.parse_args()

    # Initialize database
    db = VermontSignalDatabase()
    db.connect()

    try:
        # Generate relationships
        generator = IntelligentRelationshipGenerator(db)
        generator.generate_all(days=args.days)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
```

---

### Day 14: API Endpoints & Frontend Updates

#### Task 3.2: Update API Endpoints

**File:** `api_server.py`

**Modification Location:** Update the `/api/entities/network/article/{article_id}` endpoint (around line 426)

```python
@app.get("/api/entities/network/article/{article_id}")
@limiter.limit("100/minute")
def get_article_entity_network(
    request: Request,
    article_id: int,
    proximity_filter: str = Query('all', regex='^(all|same-sentence|adjacent|near)$'),
    min_npmi: float = Query(0.0, ge=-1.0, le=1.0)
):
    """
    Get entity network for a single article with intelligent filtering

    NEW PARAMETERS:
        proximity_filter: Filter by proximity type
            - 'all': All relationship types
            - 'same-sentence': Only same-sentence co-occurrences
            - 'adjacent': Same-sentence + adjacent sentences
            - 'near': All proximity types
        min_npmi: Minimum NPMI score (-1 to 1)

    Returns:
        Entity network with metadata about filtering applied
    """

    # Get all entities from this article
    entity_query = """
        SELECT entity, entity_type, confidence
        FROM facts
        WHERE article_id = %s
        ORDER BY confidence DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(entity_query, (article_id,))
            entity_rows = cur.fetchall()

            if not entity_rows:
                raise HTTPException(status_code=404, detail="No entities found for this article")

            entities = []
            entity_set = set()

            for row in entity_rows:
                entity_name = row[0]
                entities.append({
                    'id': entity_name,
                    'label': entity_name,
                    'type': row[1],
                    'confidence': float(row[2]) if row[2] else 0.8
                })
                entity_set.add(entity_name)

    # Build proximity filter
    proximity_map = {
        'same-sentence': ['same-sentence'],
        'adjacent': ['same-sentence', 'adjacent-sentence'],
        'near': ['same-sentence', 'adjacent-sentence', 'near-proximity'],
        'all': None  # No filter
    }

    filter_types = proximity_map[proximity_filter]
    entity_list = list(entity_set)

    # Get relationships with new metadata
    relationships_query = """
        SELECT
            entity_a, entity_b, relationship_type,
            relationship_description, confidence,
            npmi_score, proximity_weight,
            min_sentence_distance, raw_cooccurrence_count
        FROM entity_relationships
        WHERE article_id = %s
          AND entity_a = ANY(%s)
          AND entity_b = ANY(%s)
          AND npmi_score >= %s
          AND (%s IS NULL OR relationship_type = ANY(%s))
        ORDER BY npmi_score DESC, proximity_weight DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                relationships_query,
                (article_id, entity_list, entity_list, min_npmi, filter_types, filter_types)
            )
            rel_rows = cur.fetchall()

            relationships = []
            for row in rel_rows:
                relationships.append({
                    'source': row[0],
                    'target': row[1],
                    'type': row[2],
                    'label': row[3] or row[2],
                    'confidence': float(row[4]) if row[4] else 0.8,
                    'npmi': float(row[5]) if row[5] else 0.0,
                    'proximity_weight': float(row[6]) if row[6] else 0.0,
                    'sentence_distance': int(row[7]) if row[7] is not None else 999,
                    'raw_count': int(row[8]) if row[8] else 0
                })

            # Get article title
            cur.execute("SELECT title FROM articles WHERE id = %s", (article_id,))
            article_row = cur.fetchone()
            article_title = article_row[0] if article_row else f"Article {article_id}"

    return {
        'nodes': entities,
        'connections': relationships,
        'total_entities': len(entities),
        'total_relationships': len(relationships),
        'article_id': article_id,
        'article_title': article_title,
        'view_type': 'article',
        'filters_applied': {
            'proximity': proximity_filter,
            'min_npmi': min_npmi
        }
    }
```

---

#### Task 3.3: Update D3 Visualization Component

**File:** `web/app/components/EntityNetworkD3.tsx`

**Modification:** Add visual encoding for relationship strength

Find the link rendering section (around line 170-178) and REPLACE with:

```typescript
    // Create links with strength-based styling
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => {
        // Color by NPMI score
        const npmi = d.npmi || 0;
        if (npmi >= 0.7) return '#5a8c69';  // Green: strong
        if (npmi >= 0.4) return '#d4a574';  // Gold: moderate
        return '#e8e3db';  // Cream: weak
      })
      .attr('stroke-width', d => {
        // Width by proximity weight
        const weight = d.proximity_weight || 1;
        return Math.max(1, Math.min(4, weight));  // 1-4px
      })
      .attr('opacity', d => {
        // Opacity by NPMI
        const npmi = d.npmi || 0;
        return Math.max(0.3, Math.min(1.0, 0.3 + npmi));
      })
      .attr('marker-end', 'url(#arrowhead)');
```

**Add tooltip for edges:**

After the link creation, ADD:

```typescript
    // Add tooltips to links
    link.append('title')
      .text(d => {
        const npmi = (d.npmi || 0).toFixed(2);
        const dist = d.sentence_distance !== undefined ? d.sentence_distance : '?';
        return `${d.label}\nStrength: ${npmi}\nDistance: ${dist} sentences`;
      });
```

---

### Day 15: Testing, Documentation & Deployment

#### Task 3.4: Integration Testing Script

**File:** `scripts/test_intelligent_relationships.py`

```python
#!/usr/bin/env python3
"""
Integration test for intelligent relationship generation
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from scripts.generate_relationships_v3 import IntelligentRelationshipGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_on_sample_article():
    """Test relationship generation on a single article"""

    db = VermontSignalDatabase()
    db.connect()

    try:
        # Get a sample article with good entity coverage
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT a.id, a.title, COUNT(f.id) as entity_count
                    FROM articles a
                    JOIN facts f ON a.id = f.article_id
                    WHERE f.sentence_index IS NOT NULL
                    GROUP BY a.id, a.title
                    HAVING COUNT(f.id) BETWEEN 10 AND 30
                    ORDER BY a.processed_date DESC
                    LIMIT 1
                """)

                row = cur.fetchone()
                if not row:
                    logger.error("No suitable test article found!")
                    return False

                article_id, title, entity_count = row
                logger.info(f"Testing on article {article_id}: '{title}' ({entity_count} entities)")

        # Generate relationships
        generator = IntelligentRelationshipGenerator(db)

        # Fetch entities
        article_entities = generator.fetch_articles_with_entities(days=365)  # Get older articles too
        if article_id not in article_entities:
            logger.error(f"Article {article_id} not found in fetch!")
            return False

        entities = article_entities[article_id]

        # Generate
        relationships = generator.generate_for_article(article_id, entities)

        # Analyze results
        logger.info("=" * 60)
        logger.info("RESULTS:")
        logger.info(f"  Entities: {len(entities)}")
        logger.info(f"  Relationships generated: {len(relationships)}")

        if relationships:
            # Show sample relationships
            logger.info("\nTop 5 relationships:")
            sorted_rels = sorted(relationships, key=lambda r: r['npmi_score'], reverse=True)[:5]
            for i, rel in enumerate(sorted_rels, 1):
                logger.info(
                    f"  {i}. {rel['entity_a']} ↔ {rel['entity_b']}\n"
                    f"     Type: {rel['relationship_type']}, "
                    f"NPMI: {rel['npmi_score']:.3f}, "
                    f"Distance: {rel['min_sentence_distance']} sentences"
                )

        logger.info("=" * 60)
        return True

    finally:
        db.disconnect()


if __name__ == "__main__":
    success = test_on_sample_article()
    sys.exit(0 if success else 1)
```

**Run test:**
```bash
cd /Users/mike/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/Vermont-Signal
python scripts/test_intelligent_relationships.py
```

---

#### Task 3.5: Update Documentation

**File:** `docs/intelligent_entity_networks.md` (CREATE NEW)

```markdown
# Intelligent Entity Networks

Vermont Signal's entity network system uses a multi-layered approach to identify meaningful connections between entities while filtering out noise.

## Architecture

### 1. Position Tracking
- **Sentence-level tracking**: Each entity mention is mapped to its sentence within the article
- **Paragraph tracking**: Secondary grouping for broader context
- **Character offsets**: Precise position for potential highlighting

### 2. Proximity-Weighted Co-occurrence
- **Same sentence** (weight: 3): Entities appearing together strongly indicate relationship
- **Adjacent sentences** (weight: 2): Close proximity suggests connection
- **Near proximity** (weight: 1): Within 2-3 sentences

### 3. PMI Scoring (Pointwise Mutual Information)
- **Statistical significance**: Measures how much more often entities appear together than chance
- **Corpus-wide analysis**: Uses entity frequencies across all articles
- **NPMI normalization**: Bounded score (-1 to 1) for easier interpretation

### 4. Dynamic Thresholding
- **Small articles** (≤10 entities): Permissive filtering (keep sparse connections)
- **Medium articles** (11-25 entities): Balanced filtering
- **Large articles** (>25 entities): Aggressive filtering (reduce clutter)

### 5. Confidence Weighting
- **Entity confidence**: From LLM extraction (0-1)
- **Harmonic mean**: Balanced weighting that doesn't over-penalize
- **Wikidata boost**: +0.1 confidence for validated entities

## API Usage

### Get Article Network

```bash
GET /api/entities/network/article/{article_id}?proximity_filter=adjacent&min_npmi=0.5
```

**Parameters:**
- `proximity_filter`: `all`, `same-sentence`, `adjacent`, `near`
- `min_npmi`: Minimum NPMI score (-1.0 to 1.0)

**Response:**
```json
{
  "nodes": [
    {"id": "Phil Scott", "label": "Phil Scott", "type": "PERSON", "confidence": 0.92}
  ],
  "connections": [
    {
      "source": "Phil Scott",
      "target": "Vermont",
      "type": "same-sentence",
      "npmi": 0.78,
      "proximity_weight": 6.0,
      "sentence_distance": 0
    }
  ],
  "filters_applied": {
    "proximity": "adjacent",
    "min_npmi": 0.5
  }
}
```

## Maintenance

### Regenerate Relationships

```bash
# Regenerate for last 30 days
python scripts/generate_relationships_v3.py --days 30

# Regenerate for all articles
python scripts/generate_relationships_v3.py --days 9999
```

### Monitor Performance

```sql
-- Check relationship statistics
SELECT
    relationship_type,
    COUNT(*) as count,
    AVG(npmi_score) as avg_npmi,
    AVG(proximity_weight) as avg_weight
FROM entity_relationships
GROUP BY relationship_type
ORDER BY count DESC;
```

## Troubleshooting

### No relationships generated
- **Check positions**: Ensure `sentence_index` is populated
- **Run backfill**: See "Backfilling Positions" section

### Too many relationships
- **Increase min_npmi**: Try 0.6 or 0.7
- **Reduce window_size**: Edit `ProximityMatrix(window_size=0)`

### Too few relationships
- **Decrease min_npmi**: Try 0.3
- **Check entity count**: Small articles may be over-filtered
```

---

#### Task 3.6: Deployment Checklist

**File:** `DEPLOYMENT_CHECKLIST.md` (CREATE NEW)

```markdown
# Intelligent Entity Networks - Deployment Checklist

## Pre-Deployment

- [ ] All unit tests pass: `pytest tests/unit/`
- [ ] Integration test succeeds: `python scripts/test_intelligent_relationships.py`
- [ ] Database migrations reviewed and tested on staging
- [ ] Code review completed
- [ ] Performance benchmarks acceptable (<5 min for 1000 articles)

## Deployment Steps

### 1. Database Migrations
```bash
# SSH to Hetzner
ssh root@159.69.202.29

# Backup database
docker exec vermont-signal-postgres pg_dump -U postgres vermont_signal_v2 > backup_$(date +%Y%m%d).sql

# Run migrations
docker exec vermont-signal-postgres psql -U postgres -d vermont_signal_v2 < /opt/vermont-signal/scripts/migrations/001_add_position_tracking.sql
docker exec vermont-signal-postgres psql -U postgres -d vermont_signal_v2 < /opt/vermont-signal/scripts/migrations/002_enhance_relationships_table.sql

# Verify
docker exec vermont-signal-postgres psql -U postgres -d vermont_signal_v2 -c "\d facts"
```

### 2. Deploy Code
```bash
# From local machine
cd /Users/mike/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/Vermont-Signal

# Push to repo
git add .
git commit -m "Add intelligent entity networks (proximity + PMI + dynamic filtering)"
git push origin main

# On server
ssh root@159.69.202.29
cd /opt/vermont-signal
git pull origin main

# Restart services
docker-compose restart api worker
```

### 3. Backfill Positions (Optional, for existing articles)
```bash
# Run backfill script (creates positions for old articles)
docker exec vermont-signal-worker python scripts/backfill_positions.py --limit 100
```

### 4. Generate Relationships
```bash
# Generate intelligent relationships
docker exec vermont-signal-worker python scripts/generate_relationships_v3.py --days 30
```

### 5. Update Frontend
```bash
# Rebuild frontend with new visualization
cd /opt/vermont-signal/web
npm run build
docker-compose restart frontend
```

## Post-Deployment Validation

- [ ] API health check: `curl https://your-domain.com/api/health`
- [ ] Test article network endpoint: `curl https://your-domain.com/api/entities/network/article/1`
- [ ] Visual inspection: Check 5 sample article networks in UI
- [ ] Performance check: Relationship generation time for 100 articles
- [ ] Monitor logs for errors: `docker logs vermont-signal-worker -f`

## Rollback Plan

If issues occur:

```bash
# Revert database migrations
docker exec vermont-signal-postgres psql -U postgres -d vermont_signal_v2 < /opt/vermont-signal/scripts/migrations/001_rollback_position_tracking.sql

# Revert code
cd /opt/vermont-signal
git revert HEAD
docker-compose restart api worker frontend

# Restore backup
docker exec -i vermont-signal-postgres psql -U postgres vermont_signal_v2 < backup_YYYYMMDD.sql
```

## Monitoring

First 24 hours:
- Check error logs every 2 hours
- Monitor relationship generation time
- Collect user feedback on network clarity
- Track API endpoint latency

First week:
- Review network quality on 20 random articles
- Tune thresholds if needed
- Document any issues

## Success Metrics

- [ ] Relationship count reduced by 60-80%
- [ ] User engagement with networks increases
- [ ] Generation time <5 minutes for 1000 articles
- [ ] No database performance degradation
- [ ] API response times <500ms
```

---

## Appendix: Quick Reference

### Key Configuration Parameters

**Location:** `vermont_news_analyzer/modules/dynamic_thresholder.py`

```python
# Adjust these if networks are still too cluttered/sparse
SMALL_ARTICLE_THRESHOLD = 10
MEDIUM_ARTICLE_THRESHOLD = 25

THRESHOLDS = {
    ArticleSize.SMALL: ThresholdConfig(
        min_npmi=0.3,  # ← Lower = more permissive
        max_edges_per_entity=5,  # ← Higher = more connections
        percentile_cutoff=70,  # ← Lower = keep more edges
        ...
    ),
    ...
}
```

### Running the Pipeline

```bash
# Full pipeline (30 days)
python scripts/generate_relationships_v3.py --days 30

# Test on single article
python scripts/test_intelligent_relationships.py

# Check results
psql $DATABASE_URL -c "SELECT relationship_type, COUNT(*) FROM entity_relationships GROUP BY relationship_type;"
```

### File Structure

```
Vermont-Signal/
├── vermont_news_analyzer/
│   └── modules/
│       ├── position_tracker.py          (NEW)
│       ├── proximity_matrix.py          (NEW)
│       ├── pmi_calculator.py            (NEW)
│       ├── dynamic_thresholder.py       (NEW)
│       └── confidence_weighting.py      (NEW)
├── scripts/
│   ├── migrations/
│   │   ├── 001_add_position_tracking.sql
│   │   ├── 001_rollback_position_tracking.sql
│   │   └── 002_enhance_relationships_table.sql
│   ├── generate_relationships_v3.py     (NEW)
│   └── test_intelligent_relationships.py (NEW)
├── tests/
│   └── unit/
│       ├── test_position_tracker.py
│       ├── test_proximity_matrix.py
│       ├── test_pmi_calculator.py
│       ├── test_dynamic_thresholder.py
│       └── test_confidence_weighting.py
├── docs/
│   └── intelligent_entity_networks.md   (NEW)
└── DEPLOYMENT_CHECKLIST.md              (NEW)
```

---

## End of Implementation Plan

**Total New Files:** 15
**Total Modified Files:** 4
**Estimated Lines of Code:** ~1,150 (new) + ~200 (modifications)
**Timeline:** 15 working days
**Cost Impact:** <$1/month additional

**Next Steps:**
1. Review this plan
2. Begin Week 1, Day 1: Database migrations
3. Proceed sequentially through tasks
4. Test at each milestone
5. Deploy with monitoring

Good luck! 🚀
