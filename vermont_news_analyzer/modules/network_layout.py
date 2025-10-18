"""
Network Layout Computation
Pre-computes force-directed layouts for entity networks using NetworkX
"""

import logging
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import hashlib

try:
    import networkx as nx
except ImportError:
    nx = None
    logging.warning("NetworkX not installed. Install with: pip install networkx")

logger = logging.getLogger(__name__)


class NetworkLayoutComputer:
    """
    Pre-computes network layouts for faster frontend rendering
    Uses NetworkX spring layout (Fruchterman-Reingold force-directed algorithm)
    """

    def __init__(self, db):
        """
        Initialize layout computer

        Args:
            db: VermontSignalDatabase instance
        """
        self.db = db
        if nx is None:
            raise ImportError("NetworkX is required. Install with: pip install networkx")

    def compute_layout(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        width: int = 1200,
        height: int = 600,
        iterations: int = 50,
        k: Optional[float] = None,
        seed: int = 42
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute force-directed layout positions for a network

        Args:
            nodes: List of node dicts with 'id', 'label', 'type', 'weight'
            edges: List of edge dicts with 'source', 'target', 'strength'
            width: Target viewport width
            height: Target viewport height
            iterations: Number of layout iterations (more = better quality, slower)
            k: Optimal distance between nodes (None = auto)
            seed: Random seed for reproducibility

        Returns:
            Dict mapping node_id -> (x, y) coordinates
        """
        if not nodes:
            return {}

        # Build NetworkX graph
        G = nx.Graph()

        # Add nodes with weight attribute
        for node in nodes:
            G.add_node(
                node['id'],
                weight=node.get('weight', 1),
                type=node.get('type', 'UNKNOWN')
            )

        # Add edges with strength as weight
        for edge in edges:
            strength = edge.get('strength') or edge.get('npmi') or edge.get('proximity_weight', 1)
            if strength and isinstance(strength, (int, float)):
                # Normalize to reasonable weight range (0.1 - 10)
                weight = max(0.1, min(10, strength * 10))
            else:
                weight = 1.0

            G.add_edge(
                edge['source'],
                edge['target'],
                weight=weight
            )

        # Compute spring layout (Fruchterman-Reingold)
        # Weight influences edge length: higher weight = nodes pulled closer
        try:
            pos = nx.spring_layout(
                G,
                k=k,
                iterations=iterations,
                weight='weight',
                seed=seed,
                scale=min(width, height) / 2.5  # Scale to viewport
            )
        except Exception as e:
            logger.warning(f"Spring layout failed, falling back to random: {e}")
            pos = nx.random_layout(G, seed=seed)

        # Transform to viewport coordinates (0,0 at top-left)
        # NetworkX gives coordinates in [-1, 1] range centered at (0, 0)
        positions = {}
        for node_id, (x, y) in pos.items():
            # Map from [-1, 1] to viewport coords
            viewport_x = (x + 1) * width / 2
            viewport_y = (y + 1) * height / 2
            positions[node_id] = (viewport_x, viewport_y)

        logger.info(f"Computed layout for {len(nodes)} nodes, {len(edges)} edges")
        return positions

    def compute_and_cache_article_layout(
        self,
        article_id: int,
        nodes: List[Dict],
        edges: List[Dict],
        width: int = 1200,
        height: int = 600,
        cache_hours: int = 24
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute layout and cache in database

        Args:
            article_id: Article ID
            nodes: List of node dicts
            edges: List of edge dicts
            width: Viewport width
            height: Viewport height
            cache_hours: Cache duration in hours

        Returns:
            Dict mapping node_id -> (x, y) coordinates
        """
        # Compute layout
        positions = self.compute_layout(nodes, edges, width, height)

        # Generate cache key based on article + dimensions
        cache_key = self._generate_cache_key(article_id, width, height)

        # Store in database
        self._store_layout_cache(
            cache_key=cache_key,
            article_id=article_id,
            positions=positions,
            cache_hours=cache_hours
        )

        return positions

    def get_cached_layout(
        self,
        article_id: int,
        width: int = 1200,
        height: int = 600
    ) -> Optional[Dict[str, Tuple[float, float]]]:
        """
        Retrieve cached layout if available and not expired

        Args:
            article_id: Article ID
            width: Viewport width
            height: Viewport height

        Returns:
            Cached positions dict or None if not found/expired
        """
        cache_key = self._generate_cache_key(article_id, width, height)

        query = """
            SELECT layout_data, computed_at
            FROM network_layout_cache
            WHERE cache_key = %s
              AND computed_at > NOW() - INTERVAL '24 hours'
            ORDER BY computed_at DESC
            LIMIT 1
        """

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (cache_key,))
                    row = cur.fetchone()

                    if row:
                        layout_json = row[0]
                        computed_at = row[1]
                        logger.info(f"Cache HIT for article {article_id} (computed {computed_at})")
                        return json.loads(layout_json)
                    else:
                        logger.info(f"Cache MISS for article {article_id}")
                        return None
        except Exception as e:
            logger.error(f"Failed to retrieve cached layout: {e}")
            return None

    def _generate_cache_key(self, article_id: int, width: int, height: int) -> str:
        """
        Generate cache key based on article ID and viewport dimensions

        Args:
            article_id: Article ID
            width: Viewport width
            height: Viewport height

        Returns:
            SHA256 hash string
        """
        # Round dimensions to nearest 100px to improve cache hit rate
        rounded_w = round(width / 100) * 100
        rounded_h = round(height / 100) * 100

        key_string = f"article_{article_id}_w{rounded_w}_h{rounded_h}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _store_layout_cache(
        self,
        cache_key: str,
        article_id: int,
        positions: Dict[str, Tuple[float, float]],
        cache_hours: int
    ):
        """
        Store computed layout in database cache

        Args:
            cache_key: Unique cache key
            article_id: Article ID
            positions: Node positions dict
            cache_hours: Cache duration
        """
        layout_json = json.dumps(positions)

        insert_query = """
            INSERT INTO network_layout_cache (
                cache_key, article_id, layout_data, computed_at
            )
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (cache_key)
            DO UPDATE SET
                layout_data = EXCLUDED.layout_data,
                computed_at = EXCLUDED.computed_at
        """

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(insert_query, (cache_key, article_id, layout_json))
                    conn.commit()
                    logger.info(f"Cached layout for article {article_id} (key: {cache_key[:12]}...)")
        except Exception as e:
            logger.error(f"Failed to cache layout: {e}")

    def init_cache_table(self):
        """
        Create network_layout_cache table if it doesn't exist
        """
        create_table_query = """
            CREATE TABLE IF NOT EXISTS network_layout_cache (
                id SERIAL PRIMARY KEY,
                cache_key VARCHAR(64) UNIQUE NOT NULL,
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                layout_data JSONB NOT NULL,
                computed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_layout_cache_article
                ON network_layout_cache(article_id);
            CREATE INDEX IF NOT EXISTS idx_layout_cache_computed
                ON network_layout_cache(computed_at);
        """

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_table_query)
                    conn.commit()
                    logger.info("Network layout cache table initialized")
        except Exception as e:
            logger.error(f"Failed to create layout cache table: {e}")
            raise

    def clear_expired_cache(self, hours: int = 24):
        """
        Remove expired cache entries

        Args:
            hours: Remove entries older than this
        """
        delete_query = """
            DELETE FROM network_layout_cache
            WHERE computed_at < NOW() - INTERVAL %s
        """

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(delete_query, (f'{hours} hours',))
                    deleted = cur.rowcount
                    conn.commit()
                    logger.info(f"Cleared {deleted} expired layout cache entries")
                    return deleted
        except Exception as e:
            logger.error(f"Failed to clear expired cache: {e}")
            return 0
