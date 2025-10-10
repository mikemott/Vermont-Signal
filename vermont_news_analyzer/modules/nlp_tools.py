"""
Tier 3 NLP Tools Module: High-precision entity extraction and topic modeling
Uses spaCy for NER and BERTopic for topic modeling as independent validation
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import sys

try:
    import spacy
    from spacy.tokens import Doc
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import CountVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))
from config import NLPConfig, PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class SpacyEntity:
    """Container for spaCy extracted entity"""
    text: str
    label: str
    start_char: int
    end_char: int
    confidence: float = 1.0  # spaCy is deterministic


@dataclass
class SpacyNERResult:
    """Container for spaCy NER results"""
    entities: List[SpacyEntity]
    entity_count: int
    entity_types: Dict[str, int]
    raw_doc: Optional[object] = None


@dataclass
class TopicResult:
    """Container for topic modeling results"""
    topics: List[Dict]
    document_topics: List[Tuple[int, float]]
    topic_representations: Dict[int, List[str]]
    metadata: Dict


class SpacyNER:
    """High-precision named entity recognition using spaCy transformer models"""

    def __init__(self, model_name: str = None):
        """
        Initialize spaCy NER

        Args:
            model_name: spaCy model to load (defaults to config)
        """
        if not SPACY_AVAILABLE:
            raise ImportError("spaCy not installed")

        self.model_name = model_name or NLPConfig.SPACY_MODEL

        try:
            logger.info(f"Loading spaCy model: {self.model_name}")
            self.nlp = spacy.load(self.model_name)
            logger.info("spaCy model loaded successfully")
        except OSError:
            logger.error(
                f"spaCy model '{self.model_name}' not found. "
                f"Download with: python -m spacy download {self.model_name}"
            )
            raise

    def extract_entities(self, text: str) -> SpacyNERResult:
        """
        Extract named entities from text

        Args:
            text: Input text

        Returns:
            SpacyNERResult with extracted entities
        """

        logger.info("Running spaCy NER extraction")

        # Process text
        doc = self.nlp(text)

        # Extract entities
        entities = []
        entity_types = {}

        for ent in doc.ents:
            # Map spaCy labels to our schema
            label = self._map_entity_label(ent.label_)

            # Only include relevant entity types
            if label in PipelineConfig.ENTITY_TYPES:
                entity = SpacyEntity(
                    text=ent.text,
                    label=label,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=1.0
                )
                entities.append(entity)

                # Count by type
                entity_types[label] = entity_types.get(label, 0) + 1

        logger.info(
            f"spaCy NER complete: {len(entities)} entities, "
            f"{len(entity_types)} types"
        )

        return SpacyNERResult(
            entities=entities,
            entity_count=len(entities),
            entity_types=entity_types,
            raw_doc=doc
        )

    def _map_entity_label(self, spacy_label: str) -> str:
        """
        Map spaCy entity labels to our schema

        Args:
            spacy_label: spaCy NER label

        Returns:
            str: Mapped label
        """

        label_mapping = {
            'PERSON': 'PERSON',
            'ORG': 'ORGANIZATION',
            'GPE': 'LOCATION',
            'LOC': 'LOCATION',
            'DATE': 'DATE',
            'TIME': 'DATE',
            'PRODUCT': 'PRODUCT',
            'EVENT': 'EVENT',
            'FAC': 'LOCATION',  # Facility -> Location
            'NORP': 'ORGANIZATION',  # Nationalities/religious/political groups
        }

        return label_mapping.get(spacy_label, spacy_label)

    def compare_with_llm_entities(
        self,
        spacy_result: SpacyNERResult,
        llm_facts: List[Dict]
    ) -> Dict:
        """
        Compare spaCy entities with LLM-extracted entities for validation

        Args:
            spacy_result: spaCy NER results
            llm_facts: LLM extracted facts

        Returns:
            Dict: Comparison metrics and discrepancies
        """

        spacy_entities = set(e.text.lower() for e in spacy_result.entities)
        llm_entities = set(f['entity'].lower() for f in llm_facts)

        # Entities in both (high confidence)
        in_both = spacy_entities & llm_entities

        # Entities only in spaCy (missed by LLMs)
        only_spacy = spacy_entities - llm_entities

        # Entities only in LLM (potential hallucinations or spaCy misses)
        only_llm = llm_entities - spacy_entities

        precision = len(in_both) / len(llm_entities) if llm_entities else 0.0
        recall = len(in_both) / len(spacy_entities) if spacy_entities else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        logger.info(
            f"spaCy vs LLM comparison: "
            f"Precision={precision:.2%}, Recall={recall:.2%}, F1={f1:.2%}"
        )

        return {
            'agreement': list(in_both),
            'only_spacy': list(only_spacy),
            'only_llm': list(only_llm),
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'total_spacy': len(spacy_entities),
            'total_llm': len(llm_entities)
        }


class TopicModeler:
    """Topic modeling using BERTopic for semantic clustering"""

    def __init__(self, min_topic_size: int = None):
        """
        Initialize topic modeler

        Args:
            min_topic_size: Minimum documents per topic (defaults to config)
        """
        if not BERTOPIC_AVAILABLE:
            raise ImportError("bertopic not installed")

        self.min_topic_size = min_topic_size or NLPConfig.BERTOPIC_MIN_TOPIC_SIZE
        self.model = None

    def train_topics(
        self,
        documents: List[str],
        custom_labels: Optional[List[str]] = None
    ) -> TopicResult:
        """
        Train topic model on document corpus

        Args:
            documents: List of article texts
            custom_labels: Optional labels for documents

        Returns:
            TopicResult with topics and assignments
        """

        logger.info(f"Training BERTopic model on {len(documents)} documents")

        # Configure vectorizer for better topic representation
        vectorizer_model = CountVectorizer(
            ngram_range=NLPConfig.BERTOPIC_N_GRAM_RANGE,
            stop_words='english'
        ) if SKLEARN_AVAILABLE else None

        # Initialize BERTopic
        self.model = BERTopic(
            min_topic_size=self.min_topic_size,
            vectorizer_model=vectorizer_model,
            calculate_probabilities=True,
            verbose=False
        )

        # Fit model
        topics, probabilities = self.model.fit_transform(documents)

        # Get topic information
        topic_info = self.model.get_topic_info()

        # Extract topic representations
        topic_representations = {}
        for topic_id in set(topics):
            if topic_id != -1:  # Exclude outlier topic
                topic_words = self.model.get_topic(topic_id)
                if topic_words:
                    topic_representations[topic_id] = [word for word, _ in topic_words[:10]]

        # Create topic summaries
        topics_list = []
        for _, row in topic_info.iterrows():
            topic_id = row['Topic']
            if topic_id != -1:
                topics_list.append({
                    'topic_id': int(topic_id),
                    'count': int(row['Count']),
                    'name': row.get('Name', f'Topic {topic_id}'),
                    'keywords': topic_representations.get(topic_id, [])
                })

        # Document-topic assignments
        document_topics = list(zip(topics, probabilities.max(axis=1).tolist()))

        logger.info(f"BERTopic training complete: {len(topics_list)} topics found")

        return TopicResult(
            topics=topics_list,
            document_topics=document_topics,
            topic_representations=topic_representations,
            metadata={
                'num_documents': len(documents),
                'num_topics': len(topics_list),
                'min_topic_size': self.min_topic_size
            }
        )

    def assign_topics(self, documents: List[str]) -> List[Tuple[int, float]]:
        """
        Assign topics to new documents using trained model

        Args:
            documents: List of new article texts

        Returns:
            List of (topic_id, probability) tuples
        """

        if self.model is None:
            logger.error("Model not trained. Call train_topics() first.")
            return []

        logger.info(f"Assigning topics to {len(documents)} new documents")

        topics, probabilities = self.model.transform(documents)
        document_topics = list(zip(topics, probabilities.max(axis=1).tolist()))

        return document_topics

    def get_topic_summary(self, topic_id: int, top_n: int = 10) -> Dict:
        """
        Get detailed summary of a specific topic

        Args:
            topic_id: Topic ID
            top_n: Number of top words to return

        Returns:
            Dict with topic details
        """

        if self.model is None:
            logger.error("Model not trained.")
            return {}

        topic_words = self.model.get_topic(topic_id)
        if not topic_words:
            return {}

        return {
            'topic_id': topic_id,
            'top_words': [word for word, _ in topic_words[:top_n]],
            'word_scores': [{'word': word, 'score': float(score)} for word, score in topic_words[:top_n]]
        }


class NLPAuditor:
    """
    Orchestrates spaCy and BERTopic for independent validation of LLM outputs
    """

    def __init__(self):
        """Initialize NLP auditor with spaCy and BERTopic"""
        try:
            self.spacy_ner = SpacyNER()
            logger.info("spaCy NER initialized")
        except Exception as e:
            logger.error(f"Failed to initialize spaCy: {e}")
            self.spacy_ner = None

        try:
            self.topic_modeler = TopicModeler()
            logger.info("BERTopic initialized")
        except Exception as e:
            logger.error(f"Failed to initialize BERTopic: {e}")
            self.topic_modeler = None

    def audit_single_article(
        self,
        article_text: str,
        llm_facts: List[Dict]
    ) -> Dict:
        """
        Audit a single article's LLM extraction using spaCy

        Args:
            article_text: Original article text
            llm_facts: Facts extracted by LLMs

        Returns:
            Dict with audit results
        """

        logger.info("Auditing single article with spaCy NER")

        if not self.spacy_ner:
            logger.error("spaCy NER not available")
            return {'error': 'spaCy not initialized'}

        # Extract entities with spaCy
        spacy_result = self.spacy_ner.extract_entities(article_text)

        # Compare with LLM entities
        comparison = self.spacy_ner.compare_with_llm_entities(
            spacy_result,
            llm_facts
        )

        return {
            'spacy_entities': [
                {
                    'text': e.text,
                    'label': e.label,
                    'confidence': e.confidence
                }
                for e in spacy_result.entities
            ],
            'entity_count': spacy_result.entity_count,
            'entity_types': spacy_result.entity_types,
            'comparison': comparison
        }

    def audit_corpus(
        self,
        articles: List[str],
        article_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Audit entire corpus with topic modeling

        Args:
            articles: List of article texts
            article_ids: Optional list of article IDs

        Returns:
            Dict with corpus-level topics
        """

        logger.info(f"Auditing corpus of {len(articles)} articles with BERTopic")

        if not self.topic_modeler:
            logger.error("BERTopic not available")
            return {'error': 'BERTopic not initialized'}

        # Train topic model
        topic_result = self.topic_modeler.train_topics(articles)

        # Map topics to articles
        article_topic_map = []
        for i, (topic_id, prob) in enumerate(topic_result.document_topics):
            article_topic_map.append({
                'article_id': article_ids[i] if article_ids else f"article_{i}",
                'topic_id': int(topic_id),
                'probability': float(prob)
            })

        return {
            'topics': topic_result.topics,
            'article_topics': article_topic_map,
            'metadata': topic_result.metadata
        }
