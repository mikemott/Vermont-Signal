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

    # Comprehensive stop words for Vermont news analysis
    # Includes common verbs, temporal words, generic nouns that don't represent topics
    CUSTOM_STOP_WORDS = {
        # Common reporting verbs
        'said', 'says', 'told', 'asked', 'announced', 'reported', 'stated',
        'explained', 'noted', 'added', 'continued', 'began', 'started',

        # Generic people/groups
        'man', 'woman', 'people', 'person', 'men', 'women', 'group', 'groups',
        'official', 'officials', 'resident', 'residents', 'member', 'members',

        # Temporal words (covered by dates, not topical)
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'january', 'february', 'march', 'april', 'may', 'june', 'july',
        'august', 'september', 'october', 'november', 'december',
        'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years',
        'today', 'yesterday', 'tomorrow', 'tonight', 'morning', 'afternoon', 'evening',

        # Generic locations (not specific Vermont places) - keep "town" and "state" as they ARE topical
        'area', 'areas', 'place', 'places', 'city', 'country',
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
        'point', 'points',

        # Articles/pronouns/conjunctions (usually caught by stop words, but just in case)
        'the', 'a', 'an', 'this', 'that', 'these', 'those', 'it', 'its',
        'he', 'she', 'they', 'them', 'their', 'his', 'her', 'our', 'your',
        'and', 'or', 'but', 'if', 'when', 'where', 'who', 'what', 'which',

        # Reporting/article structure
        'article', 'story', 'report', 'news', 'according', 'including',

        # Publication artifacts
        'hot', 'press', 'hot press', 'daily', 'headlines', 'digger',
        'local', 'stock', 'market', 'beta', 'nbc',

        # Vermont-specific but too generic
        'vermont', 'vt',

        # Modifiers that aren't topics themselves
        'like', 'new', 'just', 'now', 'well', 'good', 'best', 'better',
    }

    # Minimum c-TF-IDF score threshold for keywords (lowered to be less aggressive)
    MIN_TFIDF_SCORE = 0.01

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

    def _clean_html(self, text: str) -> str:
        """
        Clean HTML tags and artifacts from text

        Args:
            text: Raw text possibly containing HTML

        Returns:
            Cleaned text
        """
        import re
        from html import unescape

        # Remove script and style tags with content
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Unescape HTML entities
        text = unescape(text)

        # Remove common HTML/CSS attribute remnants
        text = re.sub(r'\b(class|style|id|href|src|alt|rel|target|width|height)="[^"]*"', ' ', text)
        text = re.sub(r'\b(class|style|id|href|src|alt|rel|target|width|height)=\S+', ' ', text)

        # Remove common web artifacts
        text = re.sub(r'\b(noreferrer|noopener|nofollow|relnoreferrer|styleheight)\b', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'classwp\w+', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'hrefhttp\S+', ' ', text)
        text = re.sub(r'\d+tdtda', ' ', text)  # Remove table data artifacts
        text = re.sub(r'probationli', ' ', text)  # Common artifact
        text = re.sub(r'\bpthe\b', 'the', text)  # Fix common tag remnant
        text = re.sub(r'\bpq\b', ' ', text)  # Remove paragraph/quote artifacts
        text = re.sub(r'div\b', ' ', text)  # Remove div remnants
        text = re.sub(r'figcaption', ' ', text)

        # Remove multiple spaces and trim
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _is_meaningful_keyword(self, keyword: str) -> bool:
        """
        Check if keyword is meaningful for topic representation
        Filters out HTML artifacts, stop words, and generic terms

        Args:
            keyword: Keyword to check

        Returns:
            True if keyword is meaningful, False if it should be filtered
        """
        # Too short keywords
        if len(keyword) < 3:
            return False

        # Filter out pure numbers or things containing numbers
        if keyword.isdigit() or any(char.isdigit() for char in keyword):
            return False

        # Not purely alphabetic (has numbers, special chars, underscores)
        if not keyword.isalpha():
            return False

        keyword_lower = keyword.lower()

        # Check against custom stop words
        if keyword_lower in self.CUSTOM_STOP_WORDS:
            return False

        # Common HTML/web prefixes and substrings
        html_indicators = [
            'href', 'class', 'style', 'rel', 'alt', 'src', 'div',
            'span', 'img', 'fig', 'wp', 'block', 'attachment',
            'noreferrer', 'noopener', 'nofollow', 'blockquote',
            'figcaption', 'probationli', 'classwp', 'styleheight',
            'tdtda', 'hrefhttp', 'pthe', 'pq'
        ]

        for indicator in html_indicators:
            if indicator in keyword_lower:
                return False

        # Contains mixed case indicating concatenated HTML (e.g. classwpBlock)
        if keyword != keyword.lower() and keyword != keyword.title():
            return False

        return True

    def _is_html_artifact(self, keyword: str) -> bool:
        """
        Check if keyword is likely an HTML/web artifact
        DEPRECATED: Use _is_meaningful_keyword instead

        Args:
            keyword: Keyword to check

        Returns:
            True if keyword appears to be HTML artifact
        """
        return not self._is_meaningful_keyword(keyword)

    def _filter_keywords_by_score(
        self,
        topic_words: List[Tuple[str, float]],
        min_score: float = None
    ) -> List[str]:
        """
        Filter keywords by c-TF-IDF score and meaningfulness

        Args:
            topic_words: List of (word, c-TF-IDF score) tuples from BERTopic
            min_score: Minimum c-TF-IDF score (defaults to class constant)

        Returns:
            List of filtered, meaningful keywords
        """
        min_score = min_score or self.MIN_TFIDF_SCORE
        filtered = []

        for word, score in topic_words:
            # Apply score threshold
            if score < min_score:
                continue

            # Apply meaningfulness check (removes stop words, HTML artifacts, etc.)
            if not self._is_meaningful_keyword(word):
                continue

            filtered.append(word)

        return filtered

    def _generate_topic_label(self, keywords: List[str], prefer_proper_nouns: bool = True) -> str:
        """
        Generate human-readable topic label from keywords
        Now uses the single most important keyword or a short phrase

        Args:
            keywords: List of top keywords for topic (already filtered)
            prefer_proper_nouns: Prefer capitalized words (usually more specific)

        Returns:
            Human-readable label
        """
        if not keywords:
            return "Miscellaneous"

        # Prefer proper nouns (capitalized words) as they're usually more specific
        # e.g., "Montpelier" is better than "budget"
        if prefer_proper_nouns:
            proper_nouns = [kw for kw in keywords if kw[0].isupper()]
            if proper_nouns:
                # Use the top proper noun as the label
                return proper_nouns[0].title()

        # If no proper nouns or not preferring them, check for multi-word phrases
        # BERTopic can generate phrases like "climate_change" with underscores
        for kw in keywords:
            if '_' in kw:
                # Convert underscore phrases to proper format
                return kw.replace('_', ' ').title()

        # Fall back to single most important keyword
        return keywords[0].title()

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

        # Clean HTML from documents
        cleaned_documents = [self._clean_html(doc) for doc in documents]
        logger.info("Cleaned HTML artifacts from documents")

        # Configure vectorizer for better topic representation
        vectorizer_model = CountVectorizer(
            ngram_range=NLPConfig.BERTOPIC_N_GRAM_RANGE,
            stop_words='english',
            min_df=2  # Ignore terms appearing in only 1 document
        ) if SKLEARN_AVAILABLE else None

        # Initialize BERTopic
        self.model = BERTopic(
            min_topic_size=self.min_topic_size,
            vectorizer_model=vectorizer_model,
            calculate_probabilities=True,
            verbose=False
        )

        # Fit model using cleaned documents
        topics, probabilities = self.model.fit_transform(cleaned_documents)

        # Get topic information
        topic_info = self.model.get_topic_info()

        # Extract topic representations with c-TF-IDF filtering
        topic_representations = {}
        for topic_id in set(topics):
            if topic_id != -1:  # Exclude outlier topic
                topic_words = self.model.get_topic(topic_id)  # Returns (word, score) tuples
                if topic_words:
                    # Apply c-TF-IDF score threshold and meaningfulness filtering
                    filtered_keywords = self._filter_keywords_by_score(topic_words)
                    topic_representations[topic_id] = filtered_keywords

        # Create topic summaries with human-readable labels
        topics_list = []
        for _, row in topic_info.iterrows():
            topic_id = row['Topic']
            if topic_id != -1:
                filtered_keywords = topic_representations.get(topic_id, [])

                # Skip topics with no meaningful keywords after filtering
                if not filtered_keywords:
                    logger.warning(f"Topic {topic_id} has no meaningful keywords after filtering, skipping")
                    continue

                # Generate clean human-readable label (now uses single best keyword)
                human_label = self._generate_topic_label(filtered_keywords)

                topics_list.append({
                    'topic_id': int(topic_id),
                    'count': int(row['Count']),
                    'name': human_label,
                    'keywords': filtered_keywords[:10]  # Store top 10 filtered keywords
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
