"""
Position Tracker Module
Tracks sentence and character positions of entities within articles
"""

import logging
import spacy
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EntityPosition:
    """Container for entity position information"""
    entity: str
    entity_type: str
    sentence_index: int
    paragraph_index: int
    char_start: int
    char_end: int
    sentence_text: str


class PositionTracker:
    """
    Tracks positions of entities within article text using spaCy

    This module enables proximity-based relationship detection by tracking:
    - Sentence index (zero-indexed)
    - Paragraph index (zero-indexed)
    - Character offsets
    """

    def __init__(self, spacy_model: str = 'en_core_web_trf'):
        """
        Initialize position tracker

        Args:
            spacy_model: spaCy model name (must support sentence segmentation)
        """
        try:
            self.nlp = spacy.load(spacy_model)
            logger.info(f"Loaded spaCy model: {spacy_model}")
        except Exception as e:
            logger.error(f"Failed to load spaCy model {spacy_model}: {e}")
            raise

    def parse_document(self, text: str) -> spacy.tokens.Doc:
        """
        Parse document with spaCy

        Args:
            text: Full article text

        Returns:
            spaCy Doc object with sentence boundaries
        """
        return self.nlp(text)

    def get_sentence_boundaries(self, doc: spacy.tokens.Doc) -> List[Tuple[int, int, str]]:
        """
        Extract sentence boundaries from parsed document

        Args:
            doc: spaCy Doc object

        Returns:
            List of (start_char, end_char, sentence_text) tuples
        """
        sentences = []
        for sent in doc.sents:
            sentences.append((
                sent.start_char,
                sent.end_char,
                sent.text.strip()
            ))
        return sentences

    def find_entity_positions(
        self,
        text: str,
        entities: List[Dict],
        use_spacy: bool = True
    ) -> List[EntityPosition]:
        """
        Find positions of entities within text

        Args:
            text: Full article text
            entities: List of entity dicts with 'entity' and 'type' keys
            use_spacy: Whether to use spaCy for sentence segmentation

        Returns:
            List of EntityPosition objects
        """
        if use_spacy:
            doc = self.parse_document(text)
            sentences = self.get_sentence_boundaries(doc)
        else:
            # Fallback: simple sentence splitting
            sentences = self._simple_sentence_split(text)

        # Build paragraph index mapping
        paragraph_boundaries = self._get_paragraph_boundaries(text)

        positions = []

        for entity_dict in entities:
            entity_text = entity_dict['entity']
            entity_type = entity_dict.get('type', 'UNKNOWN')

            # Find all occurrences of this entity in text
            entity_occurrences = self._find_entity_occurrences(
                text,
                entity_text,
                entity_type,
                sentences,
                paragraph_boundaries
            )

            # Take the first occurrence (most relevant)
            if entity_occurrences:
                positions.append(entity_occurrences[0])

        return positions

    def _find_entity_occurrences(
        self,
        text: str,
        entity: str,
        entity_type: str,
        sentences: List[Tuple[int, int, str]],
        paragraph_boundaries: List[int]
    ) -> List[EntityPosition]:
        """
        Find all occurrences of entity and map to sentences/paragraphs

        Args:
            text: Full text
            entity: Entity string to find
            entity_type: Entity type (PERSON, LOCATION, etc.)
            sentences: List of (start, end, text) tuples
            paragraph_boundaries: List of paragraph start positions

        Returns:
            List of EntityPosition objects for each occurrence
        """
        occurrences = []
        entity_lower = entity.lower()
        search_pos = 0

        while True:
            # Find next occurrence (case-insensitive)
            pos = text.lower().find(entity_lower, search_pos)
            if pos == -1:
                break

            char_start = pos
            char_end = pos + len(entity)

            # Find which sentence this belongs to
            sentence_idx = None
            sentence_text = None
            for idx, (sent_start, sent_end, sent_text) in enumerate(sentences):
                if sent_start <= char_start < sent_end:
                    sentence_idx = idx
                    sentence_text = sent_text
                    break

            # Find which paragraph this belongs to
            paragraph_idx = 0
            for idx, para_start in enumerate(paragraph_boundaries):
                if char_start >= para_start:
                    paragraph_idx = idx
                else:
                    break

            if sentence_idx is not None:
                occurrences.append(EntityPosition(
                    entity=entity,
                    entity_type=entity_type,
                    sentence_index=sentence_idx,
                    paragraph_index=paragraph_idx,
                    char_start=char_start,
                    char_end=char_end,
                    sentence_text=sentence_text or ""
                ))

            search_pos = char_end

        return occurrences

    def _get_paragraph_boundaries(self, text: str) -> List[int]:
        """
        Get paragraph boundaries (double newline positions)

        Args:
            text: Full article text

        Returns:
            List of character positions where paragraphs start
        """
        boundaries = [0]  # First paragraph starts at 0
        pos = 0

        while True:
            pos = text.find('\n\n', pos)
            if pos == -1:
                break
            boundaries.append(pos + 2)  # After the double newline
            pos += 2

        return boundaries

    def _simple_sentence_split(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Simple regex-based sentence splitting (fallback)

        Args:
            text: Full text

        Returns:
            List of (start, end, sentence_text) tuples
        """
        import re

        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+'
        sentences = re.split(sentence_pattern, text)

        result = []
        pos = 0
        for sent in sentences:
            if sent.strip():
                start = text.find(sent, pos)
                end = start + len(sent)
                result.append((start, end, sent.strip()))
                pos = end

        return result

    def enrich_entities_with_positions(
        self,
        text: str,
        entities: List[Dict]
    ) -> List[Dict]:
        """
        Add position information to entity dictionaries

        Args:
            text: Full article text
            entities: List of entity dicts (modified in place)

        Returns:
            Same list with added position fields
        """
        positions = self.find_entity_positions(text, entities)

        # Create mapping from entity name to position
        entity_pos_map = {}
        for pos in positions:
            if pos.entity not in entity_pos_map:
                entity_pos_map[pos.entity] = pos

        # Enrich entities
        for entity in entities:
            entity_name = entity['entity']
            if entity_name in entity_pos_map:
                pos = entity_pos_map[entity_name]
                entity['sentence_index'] = pos.sentence_index
                entity['paragraph_index'] = pos.paragraph_index
                entity['char_start'] = pos.char_start
                entity['char_end'] = pos.char_end
            else:
                # Entity not found in text (shouldn't happen, but handle gracefully)
                logger.warning(f"Entity '{entity_name}' not found in article text")
                entity['sentence_index'] = None
                entity['paragraph_index'] = None
                entity['char_start'] = None
                entity['char_end'] = None

        return entities
