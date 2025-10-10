"""
Tier 1 Preprocessing Module: Text Cleaning and Chunking
Prepares raw news text for multi-model extraction pipeline
"""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class ProcessedArticle:
    """Container for processed article data"""
    article_id: str
    title: Optional[str]
    clean_text: str
    chunks: List[Dict[str, any]]
    metadata: Dict[str, any]


class TextCleaner:
    """Cleans raw article text by removing boilerplate, ads, and noise"""

    @staticmethod
    def clean_html(html_content: str) -> str:
        """
        Remove HTML tags and extract clean text

        Args:
            html_content: Raw HTML string

        Returns:
            str: Clean text without HTML tags
        """
        if not BS4_AVAILABLE:
            logger.warning("BeautifulSoup not available, skipping HTML cleaning")
            return html_content

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # Get text and clean whitespace
        text = soup.get_text(separator=' ', strip=True)
        return text

    @staticmethod
    def remove_boilerplate(text: str) -> str:
        """
        Remove common boilerplate phrases and noise

        Args:
            text: Raw text string

        Returns:
            str: Text with boilerplate removed
        """

        # Common news boilerplate patterns
        boilerplate_patterns = [
            r'Click here to subscribe.*',
            r'Sign up for our newsletter.*',
            r'Advertisement\s*',
            r'ADVERTISEMENT\s*',
            r'Read more:.*',
            r'Related articles?:.*',
            r'Share on (Facebook|Twitter|LinkedIn).*',
            r'©\s*\d{4}.*All rights reserved.*',
            r'This story was originally published.*',
            r'Contact the author at.*',
            r'\[.*?(Photo|Image|Video).*?\]',
        ]

        cleaned = text
        for pattern in boilerplate_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)

        return cleaned

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize whitespace and fix common formatting issues

        Args:
            text: Text with irregular whitespace

        Returns:
            str: Text with normalized whitespace
        """

        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)

        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    @classmethod
    def clean_text(cls, text: str, is_html: bool = False) -> str:
        """
        Main cleaning pipeline

        Args:
            text: Raw text or HTML content
            is_html: Whether the input is HTML

        Returns:
            str: Fully cleaned text
        """

        # Remove HTML if needed
        if is_html:
            text = cls.clean_html(text)

        # Remove boilerplate
        text = cls.remove_boilerplate(text)

        # Normalize whitespace
        text = cls.normalize_whitespace(text)

        return text


class ArticleChunker:
    """Splits articles into manageable chunks for LLM processing"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        Initialize chunker with configuration

        Args:
            chunk_size: Maximum tokens per chunk (defaults to config)
            chunk_overlap: Token overlap between chunks (defaults to config)
        """
        self.chunk_size = chunk_size or PipelineConfig.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or PipelineConfig.CHUNK_OVERLAP

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using simple regex

        Args:
            text: Input text

        Returns:
            List[str]: List of sentences
        """

        # Simple sentence splitting (improved with abbreviation handling)
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, text)

        return [s.strip() for s in sentences if s.strip()]

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count (rough approximation: ~4 chars per token)

        Args:
            text: Input text

        Returns:
            int: Estimated token count
        """
        return len(text) // 4

    def chunk_by_paragraphs(self, text: str) -> List[Dict[str, any]]:
        """
        Chunk text by paragraphs (preserves natural breaks)

        Args:
            text: Full article text

        Returns:
            List[Dict]: List of chunk dictionaries
        """

        paragraphs = text.split('\n\n')
        chunks = []

        for idx, para in enumerate(paragraphs):
            if para.strip():
                chunks.append({
                    'chunk_index': idx,
                    'text': para.strip(),
                    'token_estimate': self._estimate_token_count(para),
                    'chunk_type': 'paragraph'
                })

        logger.info(f"Created {len(chunks)} paragraph-based chunks")
        return chunks

    def chunk_by_sentences(self, text: str) -> List[Dict[str, any]]:
        """
        Chunk text by sentences with size and overlap constraints

        Args:
            text: Full article text

        Returns:
            List[Dict]: List of chunk dictionaries
        """

        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_token_count(sentence)

            # If adding this sentence exceeds chunk size, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'chunk_index': chunk_index,
                    'text': chunk_text,
                    'token_estimate': current_tokens,
                    'chunk_type': 'sentence_aligned'
                })

                # Start new chunk with overlap
                overlap_tokens = 0
                overlap_sentences = []

                # Add sentences from the end for overlap
                for s in reversed(current_chunk):
                    s_tokens = self._estimate_token_count(s)
                    if overlap_tokens + s_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break

                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
                chunk_index += 1

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add final chunk if any sentences remain
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'chunk_index': chunk_index,
                'text': chunk_text,
                'token_estimate': current_tokens,
                'chunk_type': 'sentence_aligned'
            })

        logger.info(f"Created {len(chunks)} sentence-aligned chunks")
        return chunks


class ArticleIngestion:
    """Main ingestion class that orchestrates cleaning and chunking"""

    def __init__(self):
        """Initialize ingestion pipeline"""
        self.cleaner = TextCleaner()
        self.chunker = ArticleChunker()

    def process_text(
        self,
        text: str,
        article_id: str,
        title: Optional[str] = None,
        is_html: bool = False,
        chunk_strategy: str = 'sentence'
    ) -> ProcessedArticle:
        """
        Process raw text through cleaning and chunking pipeline

        Args:
            text: Raw article text or HTML
            article_id: Unique identifier for the article
            title: Article title (optional)
            is_html: Whether input is HTML
            chunk_strategy: 'sentence' or 'paragraph'

        Returns:
            ProcessedArticle: Processed article with chunks
        """

        logger.info(f"Processing article: {article_id}")

        # Clean the text
        clean_text = self.cleaner.clean_text(text, is_html=is_html)

        # Chunk the text
        if chunk_strategy == 'paragraph':
            chunks = self.chunker.chunk_by_paragraphs(clean_text)
        else:
            chunks = self.chunker.chunk_by_sentences(clean_text)

        # Create metadata
        metadata = {
            'article_id': article_id,
            'title': title,
            'original_length': len(text),
            'clean_length': len(clean_text),
            'num_chunks': len(chunks),
            'chunk_strategy': chunk_strategy
        }

        logger.info(
            f"Article {article_id} processed: "
            f"{metadata['num_chunks']} chunks, "
            f"{metadata['clean_length']} chars"
        )

        return ProcessedArticle(
            article_id=article_id,
            title=title,
            clean_text=clean_text,
            chunks=chunks,
            metadata=metadata
        )

    def process_url(self, url: str, article_id: Optional[str] = None) -> Optional[ProcessedArticle]:
        """
        Fetch and process article from URL using newspaper3k

        Args:
            url: Article URL
            article_id: Optional ID (uses URL if not provided)

        Returns:
            ProcessedArticle or None if extraction fails
        """

        if not NEWSPAPER_AVAILABLE:
            logger.error("newspaper3k not installed, cannot process URLs")
            return None

        try:
            article = Article(url)
            article.download()
            article.parse()

            article_id = article_id or url
            return self.process_text(
                text=article.text,
                article_id=article_id,
                title=article.title,
                is_html=False
            )

        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            return None

    def process_file(self, file_path: Path) -> Optional[ProcessedArticle]:
        """
        Process article from text or HTML file

        Args:
            file_path: Path to file

        Returns:
            ProcessedArticle or None if reading fails
        """

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            is_html = file_path.suffix.lower() in ['.html', '.htm']
            article_id = file_path.stem

            return self.process_text(
                text=text,
                article_id=article_id,
                is_html=is_html
            )

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return None
