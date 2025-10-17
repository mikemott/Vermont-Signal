#!/usr/bin/env python3
"""
Topic Computation Script for Vermont Signal
Computes BERTopic topics from processed articles and stores in database
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.modules.nlp_tools import TopicModeler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopicComputer:
    """
    Compute and store topics from article corpus
    """

    def __init__(self, min_topic_size: int = 3):
        """
        Initialize topic computer

        Args:
            min_topic_size: Minimum documents per topic
        """
        self.db = VermontSignalDatabase()
        self.topic_modeler = TopicModeler(min_topic_size=min_topic_size)
        self.min_topic_size = min_topic_size

    def connect(self):
        """Connect to database"""
        self.db.connect()
        logger.info("Connected to database")

    def disconnect(self):
        """Disconnect from database"""
        self.db.disconnect()
        logger.info("Disconnected from database")

    def get_articles_for_topic_modeling(
        self,
        days: Optional[int] = None,
        min_length: int = 100
    ) -> List[Dict]:
        """
        Retrieve articles for topic modeling

        Args:
            days: Only include articles from last N days (None = all)
            min_length: Minimum article content length

        Returns:
            List of article dicts with id, title, content
        """
        logger.info(f"Fetching articles for topic modeling (days={days}, min_length={min_length})")

        query = """
            SELECT id, title, content, published_date
            FROM articles
            WHERE processing_status = 'completed'
              AND content IS NOT NULL
              AND LENGTH(content) >= %s
        """

        params = [min_length]

        if days:
            query += " AND published_date >= CURRENT_DATE - INTERVAL %s"
            params.append(f'{days} days')

        query += " ORDER BY published_date DESC"

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

                articles = []
                for row in rows:
                    articles.append({
                        'id': row[0],
                        'title': row[1],
                        'content': row[2],
                        'published_date': row[3]
                    })

                logger.info(f"Retrieved {len(articles)} articles for topic modeling")
                return articles

    def compute_topics(
        self,
        articles: List[Dict],
        use_consensus_summary: bool = False
    ) -> Dict:
        """
        Compute topics from articles using BERTopic

        Args:
            articles: List of article dicts
            use_consensus_summary: Use consensus summary instead of full content

        Returns:
            Topic result dict with topics and article assignments
        """
        if not articles:
            logger.error("No articles provided for topic modeling")
            return None

        logger.info(f"Computing topics from {len(articles)} articles")

        # Prepare documents
        if use_consensus_summary:
            # Use consensus summaries instead of full content
            documents = []
            article_ids = []

            for article in articles:
                # Fetch consensus summary from extraction_results
                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT consensus_summary FROM extraction_results WHERE article_id = %s",
                            (article['id'],)
                        )
                        result = cur.fetchone()
                        if result and result[0]:
                            documents.append(result[0])
                            article_ids.append(article['id'])

            logger.info(f"Using {len(documents)} consensus summaries for topic modeling")
        else:
            # Use full article content
            documents = [a['content'] for a in articles]
            article_ids = [a['id'] for a in articles]

        if not documents:
            logger.error("No valid documents for topic modeling")
            return None

        # Train topic model
        topic_result = self.topic_modeler.train_topics(documents)

        # Add article IDs to result
        topic_result.article_ids = article_ids

        logger.info(
            f"Topic modeling complete: {len(topic_result.topics)} topics found, "
            f"{len(topic_result.document_topics)} document assignments"
        )

        return topic_result

    def store_topics(self, topic_result, corpus_size: int) -> int:
        """
        Store computed topics in database

        Args:
            topic_result: TopicResult from BERTopic
            corpus_size: Total number of documents in corpus

        Returns:
            Number of topics stored
        """
        logger.info("Storing topics in database")

        computed_at = datetime.now()
        stored_count = 0

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Store each topic in corpus_topics
                for topic in topic_result.topics:
                    topic_id = topic['topic_id']
                    topic_label = topic.get('name', f"Topic {topic_id}")
                    keywords = topic.get('keywords', [])
                    article_count = topic.get('count', 0)

                    # Get representative documents (top 3 article titles)
                    representative_docs = []
                    for i, (doc_topic_id, prob) in enumerate(topic_result.document_topics):
                        if doc_topic_id == topic_id and len(representative_docs) < 3:
                            article_id = topic_result.article_ids[i]
                            # Fetch article title
                            cur.execute(
                                "SELECT title FROM articles WHERE id = %s",
                                (article_id,)
                            )
                            title_row = cur.fetchone()
                            if title_row:
                                representative_docs.append(title_row[0])

                    # Insert into corpus_topics
                    cur.execute("""
                        INSERT INTO corpus_topics
                        (topic_id, topic_label, keywords, representative_docs, article_count, computed_at, corpus_size)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        topic_id,
                        topic_label,
                        keywords,
                        representative_docs,
                        article_count,
                        computed_at,
                        corpus_size
                    ))

                    stored_count += 1

                conn.commit()

        logger.info(f"Stored {stored_count} topics in corpus_topics table")
        return stored_count

    def store_article_topic_assignments(self, topic_result) -> int:
        """
        Store article-topic assignments in database

        Args:
            topic_result: TopicResult from BERTopic

        Returns:
            Number of assignments stored
        """
        logger.info("Storing article-topic assignments")

        stored_count = 0

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Clear existing assignments (for fresh computation)
                cur.execute("DELETE FROM article_topics")

                # Store each article-topic assignment
                for i, (topic_id, probability) in enumerate(topic_result.document_topics):
                    article_id = topic_result.article_ids[i]

                    # Only store if topic is not outlier (-1)
                    if topic_id != -1:
                        cur.execute("""
                            INSERT INTO article_topics (article_id, topic_id, probability)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (article_id, topic_id) DO UPDATE
                            SET probability = EXCLUDED.probability
                        """, (article_id, topic_id, probability))

                        stored_count += 1

                conn.commit()

        logger.info(f"Stored {stored_count} article-topic assignments")
        return stored_count

    def run_topic_computation(
        self,
        days: Optional[int] = None,
        use_summary: bool = False,
        min_length: int = 100
    ) -> Dict:
        """
        Complete topic computation workflow

        Args:
            days: Only process articles from last N days
            use_summary: Use consensus summaries instead of full content
            min_length: Minimum article content length

        Returns:
            Summary statistics
        """
        logger.info("=" * 60)
        logger.info("TOPIC COMPUTATION START")
        logger.info("=" * 60)

        # Step 1: Fetch articles
        articles = self.get_articles_for_topic_modeling(days=days, min_length=min_length)

        if not articles:
            logger.error("No articles available for topic modeling")
            return {
                'success': False,
                'error': 'No articles found',
                'articles_processed': 0,
                'topics_found': 0
            }

        # Step 2: Compute topics
        topic_result = self.compute_topics(articles, use_consensus_summary=use_summary)

        if not topic_result:
            logger.error("Topic computation failed")
            return {
                'success': False,
                'error': 'Topic computation failed',
                'articles_processed': len(articles),
                'topics_found': 0
            }

        # Step 3: Store topics
        topics_stored = self.store_topics(topic_result, len(articles))

        # Step 4: Store article-topic assignments
        assignments_stored = self.store_article_topic_assignments(topic_result)

        logger.info("=" * 60)
        logger.info("TOPIC COMPUTATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Articles processed: {len(articles)}")
        logger.info(f"Topics found: {len(topic_result.topics)}")
        logger.info(f"Topics stored: {topics_stored}")
        logger.info(f"Assignments stored: {assignments_stored}")

        return {
            'success': True,
            'articles_processed': len(articles),
            'topics_found': len(topic_result.topics),
            'topics_stored': topics_stored,
            'assignments_stored': assignments_stored
        }


def main():
    parser = argparse.ArgumentParser(
        description='Compute BERTopic topics from Vermont Signal articles'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='Only process articles from last N days (default: all articles)'
    )
    parser.add_argument(
        '--min-topic-size',
        type=int,
        default=3,
        help='Minimum articles per topic (default: 3)'
    )
    parser.add_argument(
        '--use-summary',
        action='store_true',
        help='Use consensus summaries instead of full article content'
    )
    parser.add_argument(
        '--min-length',
        type=int,
        default=100,
        help='Minimum article content length (default: 100 characters)'
    )

    args = parser.parse_args()

    # Initialize topic computer
    computer = TopicComputer(min_topic_size=args.min_topic_size)

    try:
        # Connect to database
        computer.connect()

        # Run topic computation
        results = computer.run_topic_computation(
            days=args.days,
            use_summary=args.use_summary,
            min_length=args.min_length
        )

        if results['success']:
            print("\n✅ Topic computation successful!")
            print(f"   Articles processed: {results['articles_processed']}")
            print(f"   Topics found: {results['topics_found']}")
            print(f"   Topics stored: {results['topics_stored']}")
            print(f"   Assignments stored: {results['assignments_stored']}")
            sys.exit(0)
        else:
            print(f"\n❌ Topic computation failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Topic computation failed with exception: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        computer.disconnect()


if __name__ == "__main__":
    main()
