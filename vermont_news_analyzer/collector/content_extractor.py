"""
Vermont Signal Content Extractor
Extracts full article text from URLs using newspaper3k
"""

import logging
from typing import Optional

try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContentExtractor:
    """
    Full-text content extractor using newspaper3k

    Extracts clean article text from URLs, removing ads, navigation,
    and other boilerplate content.
    """

    def __init__(self, timeout: int = 10):
        """
        Initialize content extractor

        Args:
            timeout: Request timeout in seconds (default 10)
        """
        if not NEWSPAPER_AVAILABLE:
            logger.warning(
                "newspaper3k not available. Install with: pip install newspaper3k"
            )

        self.timeout = timeout

    def extract(self, url: str) -> Optional[str]:
        """
        Extract full article text from URL

        Args:
            url: Article URL

        Returns:
            Clean article text or None if extraction fails
        """
        if not NEWSPAPER_AVAILABLE:
            logger.error("newspaper3k not installed, cannot extract content")
            return None

        try:
            article = Article(url)
            article.download()
            article.parse()

            # Return full text
            text = article.text

            if not text or len(text) < 100:
                logger.warning(f"Extracted text too short for {url} ({len(text)} chars)")
                return None

            logger.debug(f"Extracted {len(text)} chars from {url}")
            return text

        except Exception as e:
            logger.debug(f"Content extraction failed for {url}: {e}")
            return None

    def extract_with_metadata(self, url: str) -> Optional[dict]:
        """
        Extract full article text and metadata from URL

        Args:
            url: Article URL

        Returns:
            Dict with text, title, authors, publish_date, or None if extraction fails
        """
        if not NEWSPAPER_AVAILABLE:
            logger.error("newspaper3k not installed, cannot extract content")
            return None

        try:
            article = Article(url)
            article.download()
            article.parse()

            # Extract metadata
            result = {
                'text': article.text,
                'title': article.title,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'top_image': article.top_image,
                'meta_description': article.meta_description
            }

            if not result['text'] or len(result['text']) < 100:
                logger.warning(f"Extracted text too short for {url} ({len(result['text'])} chars)")
                return None

            logger.debug(f"Extracted {len(result['text'])} chars + metadata from {url}")
            return result

        except Exception as e:
            logger.debug(f"Content extraction failed for {url}: {e}")
            return None
