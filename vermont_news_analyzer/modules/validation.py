"""
Tier 2 Validation Module: Cross-validation and Conflict Resolution
Compares outputs from multiple LLMs, detects conflicts, and achieves consensus
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
from pathlib import Path
import sys

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))
from config import PipelineConfig, NLPConfig
from modules.llm_extraction import ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ConflictReport:
    """Container for conflict detection results"""
    has_conflicts: bool
    conflict_descriptions: List[str] = field(default_factory=list)
    summary_similarity: float = 0.0
    entity_overlap: float = 0.0
    conflicting_entities: List[Dict] = field(default_factory=list)
    confidence_discrepancies: List[Dict] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Container for validation and consensus results"""
    consensus_summary: str
    merged_facts: List[Dict]
    conflict_report: ConflictReport
    requires_arbitration: bool
    metadata: Dict


class SimilarityAnalyzer:
    """Analyzes similarity between text and entities using embeddings"""

    def __init__(self, model_name: str = None):
        """
        Initialize similarity analyzer

        Args:
            model_name: Sentence transformer model (defaults to config)
        """
        if not SENTENCE_TRANSFORMER_AVAILABLE:
            raise ImportError("sentence-transformers not installed")

        self.model_name = model_name or NLPConfig.SENTENCE_TRANSFORMER_MODEL
        logger.info(f"Loading sentence transformer model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

    def compute_text_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            float: Similarity score (0.0 to 1.0)
        """

        embeddings = self.model.encode([text1, text2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

        return float(similarity)

    def compute_entity_similarity(self, entity1: str, entity2: str) -> float:
        """
        Compute similarity between entity names

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            float: Similarity score
        """

        # Exact match
        if entity1.lower() == entity2.lower():
            return 1.0

        # Embedding-based similarity
        return self.compute_text_similarity(entity1, entity2)


class EntityMerger:
    """Merges entity lists from multiple sources"""

    def __init__(self, similarity_threshold: float = None):
        """
        Initialize entity merger

        Args:
            similarity_threshold: Threshold for entity matching
        """
        self.similarity_threshold = similarity_threshold or PipelineConfig.SIMILARITY_THRESHOLD
        self.similarity_analyzer = SimilarityAnalyzer()

    def merge_entities(
        self,
        claude_facts: List[Dict],
        gemini_facts: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Merge entity lists, marking agreement and conflicts

        Args:
            claude_facts: Facts from Claude
            gemini_facts: Facts from Gemini

        Returns:
            Tuple of (merged_facts, conflicting_entities)
        """

        merged = []
        conflicts = []
        gemini_matched = set()

        # Process Claude entities
        for c_fact in claude_facts:
            c_entity = c_fact['entity']
            c_type = c_fact['type']

            # Find matching entity in Gemini output
            best_match = None
            best_similarity = 0.0

            for i, g_fact in enumerate(gemini_facts):
                if i in gemini_matched:
                    continue

                similarity = self.similarity_analyzer.compute_entity_similarity(
                    c_entity,
                    g_fact['entity']
                )

                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = (i, g_fact)

            if best_match:
                # Entity found in both outputs - high confidence
                g_idx, g_fact = best_match
                gemini_matched.add(g_idx)

                # Check for type conflicts
                if c_type != g_fact['type']:
                    conflicts.append({
                        'entity': c_entity,
                        'claude_type': c_type,
                        'gemini_type': g_fact['type'],
                        'conflict_type': 'entity_type_mismatch'
                    })

                # Average confidence scores
                avg_confidence = (c_fact['confidence'] + g_fact['confidence']) / 2

                # Check for confidence discrepancy
                conf_diff = abs(c_fact['confidence'] - g_fact['confidence'])
                if conf_diff > 0.3:
                    conflicts.append({
                        'entity': c_entity,
                        'claude_confidence': c_fact['confidence'],
                        'gemini_confidence': g_fact['confidence'],
                        'conflict_type': 'confidence_discrepancy'
                    })

                # Merge the facts
                merged_fact = {
                    'entity': c_entity,
                    'type': c_type,  # Use Claude's type unless conflict
                    'confidence': min(avg_confidence + 0.1, 1.0),  # Boost for agreement
                    'event_description': c_fact['event_description'],
                    'sources': ['claude', 'gemini'],
                    'similarity': best_similarity,
                    'note': c_fact.get('note', '')
                }

                # Combine event descriptions if different
                if c_fact['event_description'] != g_fact['event_description']:
                    merged_fact['event_description_gemini'] = g_fact['event_description']

                merged.append(merged_fact)

            else:
                # Entity only in Claude output
                merged_fact = c_fact.copy()
                merged_fact['sources'] = ['claude']
                merged_fact['confidence'] = max(c_fact['confidence'] - 0.1, 0.0)  # Penalty for single source
                merged.append(merged_fact)

        # Add Gemini entities that weren't matched
        for i, g_fact in enumerate(gemini_facts):
            if i not in gemini_matched:
                merged_fact = g_fact.copy()
                merged_fact['sources'] = ['gemini']
                merged_fact['confidence'] = max(g_fact['confidence'] - 0.1, 0.0)
                merged.append(merged_fact)

        logger.info(
            f"Entity merging complete: {len(merged)} total, "
            f"{len(conflicts)} conflicts detected"
        )

        return merged, conflicts


class ConflictDetector:
    """Detects conflicts between model outputs"""

    def __init__(self):
        """Initialize conflict detector"""
        self.similarity_analyzer = SimilarityAnalyzer()

    def detect_conflicts(
        self,
        claude_result: ExtractionResult,
        gemini_result: ExtractionResult,
        merged_facts: List[Dict],
        entity_conflicts: List[Dict]
    ) -> ConflictReport:
        """
        Analyze outputs and detect conflicts

        Args:
            claude_result: Claude extraction result
            gemini_result: Gemini extraction result
            merged_facts: Merged entity list
            entity_conflicts: Entity-level conflicts

        Returns:
            ConflictReport
        """

        logger.info("Running conflict detection")

        # Compute summary similarity
        summary_similarity = self.similarity_analyzer.compute_text_similarity(
            claude_result.consensus_summary,
            gemini_result.consensus_summary
        )

        # Compute entity overlap
        claude_entities = set(f['entity'].lower() for f in claude_result.extracted_facts)
        gemini_entities = set(f['entity'].lower() for f in gemini_result.extracted_facts)

        if len(claude_entities) + len(gemini_entities) > 0:
            entity_overlap = len(claude_entities & gemini_entities) / \
                           len(claude_entities | gemini_entities)
        else:
            entity_overlap = 0.0

        # Identify conflicts
        conflict_descriptions = []

        # Summary divergence
        if summary_similarity < PipelineConfig.SIMILARITY_THRESHOLD:
            conflict_descriptions.append(
                f"Summary similarity low: {summary_similarity:.2f} "
                f"(threshold: {PipelineConfig.SIMILARITY_THRESHOLD})"
            )

        # Low entity overlap
        if entity_overlap < 0.5:
            conflict_descriptions.append(
                f"Low entity overlap: {entity_overlap:.2%}"
            )

        # Entity type conflicts
        type_conflicts = [c for c in entity_conflicts if c.get('conflict_type') == 'entity_type_mismatch']
        if type_conflicts:
            conflict_descriptions.append(
                f"Entity type mismatches: {len(type_conflicts)} conflicts"
            )

        # Confidence discrepancies
        conf_conflicts = [c for c in entity_conflicts if c.get('conflict_type') == 'confidence_discrepancy']
        if conf_conflicts:
            conflict_descriptions.append(
                f"Confidence discrepancies: {len(conf_conflicts)} entities"
            )

        has_conflicts = len(conflict_descriptions) > 0

        logger.info(
            f"Conflict detection complete: {len(conflict_descriptions)} issues found"
        )

        return ConflictReport(
            has_conflicts=has_conflicts,
            conflict_descriptions=conflict_descriptions,
            summary_similarity=summary_similarity,
            entity_overlap=entity_overlap,
            conflicting_entities=type_conflicts,
            confidence_discrepancies=conf_conflicts
        )


class Validator:
    """Main validation orchestrator for Tier 2"""

    def __init__(self):
        """Initialize validator with all components"""
        self.similarity_analyzer = SimilarityAnalyzer()
        self.entity_merger = EntityMerger()
        self.conflict_detector = ConflictDetector()

    def validate_and_merge(
        self,
        claude_result: ExtractionResult,
        gemini_result: ExtractionResult,
        original_text: str
    ) -> ValidationResult:
        """
        Validate and merge outputs from Claude and Gemini

        Args:
            claude_result: Claude extraction result
            gemini_result: Gemini extraction result
            original_text: Original article text

        Returns:
            ValidationResult with consensus or arbitration flag
        """

        logger.info("Starting validation and merging process")

        # Check if both extractions succeeded
        if not claude_result.success or not gemini_result.success:
            logger.warning("One or more extractions failed, returning best available")
            return self._handle_extraction_failure(claude_result, gemini_result)

        # Merge entities
        merged_facts, entity_conflicts = self.entity_merger.merge_entities(
            claude_result.extracted_facts,
            gemini_result.extracted_facts
        )

        # Detect conflicts
        conflict_report = self.conflict_detector.detect_conflicts(
            claude_result,
            gemini_result,
            merged_facts,
            entity_conflicts
        )

        # Decide on consensus summary
        if conflict_report.summary_similarity >= PipelineConfig.SIMILARITY_THRESHOLD:
            # High agreement - use Claude's summary (slightly preferred)
            consensus_summary = claude_result.consensus_summary
        else:
            # Low agreement - concatenate with marker
            consensus_summary = (
                f"{claude_result.consensus_summary} "
                f"[Alternative perspective: {gemini_result.consensus_summary}]"
            )

        # Determine if arbitration is needed
        requires_arbitration = (
            conflict_report.has_conflicts and
            conflict_report.summary_similarity < 0.6
        )

        logger.info(
            f"Validation complete. Requires arbitration: {requires_arbitration}"
        )

        return ValidationResult(
            consensus_summary=consensus_summary,
            merged_facts=merged_facts,
            conflict_report=conflict_report,
            requires_arbitration=requires_arbitration,
            metadata={
                'claude_success': claude_result.success,
                'gemini_success': gemini_result.success,
                'total_facts': len(merged_facts),
                'conflicts': len(conflict_report.conflict_descriptions),
                'summary_similarity': conflict_report.summary_similarity,
                'entity_overlap': conflict_report.entity_overlap
            }
        )

    def _handle_extraction_failure(
        self,
        claude_result: ExtractionResult,
        gemini_result: ExtractionResult
    ) -> ValidationResult:
        """
        Handle case where one or more extractions failed

        Args:
            claude_result: Claude result (may have failed)
            gemini_result: Gemini result (may have failed)

        Returns:
            ValidationResult with best available data
        """

        if claude_result.success:
            logger.warning("Using Claude output only (Gemini failed)")
            return ValidationResult(
                consensus_summary=claude_result.consensus_summary,
                merged_facts=claude_result.extracted_facts,
                conflict_report=ConflictReport(has_conflicts=True, conflict_descriptions=["Gemini extraction failed"]),
                requires_arbitration=False,
                metadata={'gemini_failed': True}
            )

        elif gemini_result.success:
            logger.warning("Using Gemini output only (Claude failed)")
            return ValidationResult(
                consensus_summary=gemini_result.consensus_summary,
                merged_facts=gemini_result.extracted_facts,
                conflict_report=ConflictReport(has_conflicts=True, conflict_descriptions=["Claude extraction failed"]),
                requires_arbitration=False,
                metadata={'claude_failed': True}
            )

        else:
            logger.error("Both extractions failed")
            return ValidationResult(
                consensus_summary="[Extraction failed]",
                merged_facts=[],
                conflict_report=ConflictReport(has_conflicts=True, conflict_descriptions=["Both models failed"]),
                requires_arbitration=False,
                metadata={'both_failed': True}
            )
