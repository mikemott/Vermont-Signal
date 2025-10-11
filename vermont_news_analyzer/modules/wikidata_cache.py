"""
Wikidata Caching and Rate Limiting Module
Handles efficient Wikidata lookups with caching, batching, and rate limiting
"""

import logging
import json
import requests
import time
import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class WikidataCache:
    """
    Local SQLite cache for Wikidata lookups

    Reduces API calls and speeds up repeated entity lookups
    """

    def __init__(self, cache_dir: Path = None):
        """
        Initialize Wikidata cache

        Args:
            cache_dir: Directory for cache database (default: ./data/cache)
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "cache"

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "wikidata_cache.db"

        self._init_database()
        logger.info(f"Wikidata cache initialized: {self.db_path}")

    def _init_database(self):
        """Create cache tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS entity_cache (
                entity_name TEXT PRIMARY KEY,
                wikidata_id TEXT,
                description TEXT,
                properties TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cached_at
            ON entity_cache(cached_at)
        """)

        conn.commit()
        conn.close()

    def get(self, entity_name: str, max_age_days: int = 30) -> Optional[Dict]:
        """
        Get cached Wikidata result

        Args:
            entity_name: Entity to lookup
            max_age_days: Maximum cache age in days (default: 30)

        Returns:
            Dict with wikidata_id, description, properties or None if not cached
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Get cache entry if it exists and is fresh
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        cur.execute("""
            SELECT wikidata_id, description, properties, hit_count
            FROM entity_cache
            WHERE entity_name = ?
              AND cached_at >= ?
        """, (entity_name.lower(), cutoff_date))

        row = cur.fetchone()

        if row:
            # Increment hit count
            cur.execute("""
                UPDATE entity_cache
                SET hit_count = hit_count + 1
                WHERE entity_name = ?
            """, (entity_name.lower(),))
            conn.commit()

            logger.debug(f"Cache HIT for '{entity_name}' (hits: {row[3] + 1})")

            result = {
                'wikidata_id': row[0],
                'description': row[1],
                'properties': json.loads(row[2]) if row[2] else {}
            }
        else:
            logger.debug(f"Cache MISS for '{entity_name}'")
            result = None

        conn.close()
        return result

    def set(self, entity_name: str, wikidata_id: str, description: str, properties: Dict):
        """
        Cache a Wikidata result

        Args:
            entity_name: Entity name
            wikidata_id: Wikidata Q-ID
            description: Entity description
            properties: Entity properties dict
        """
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
            INSERT OR REPLACE INTO entity_cache
            (entity_name, wikidata_id, description, properties)
            VALUES (?, ?, ?, ?)
        """, (
            entity_name.lower(),
            wikidata_id,
            description,
            json.dumps(properties)
        ))

        conn.commit()
        conn.close()

        logger.debug(f"Cached: '{entity_name}' -> {wikidata_id}")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Total cached entities
        cur.execute("SELECT COUNT(*) FROM entity_cache")
        total_entities = cur.fetchone()[0]

        # Total cache hits
        cur.execute("SELECT SUM(hit_count) FROM entity_cache")
        total_hits = cur.fetchone()[0] or 0

        # Top entities
        cur.execute("""
            SELECT entity_name, hit_count
            FROM entity_cache
            ORDER BY hit_count DESC
            LIMIT 10
        """)
        top_entities = [(row[0], row[1]) for row in cur.fetchall()]

        conn.close()

        return {
            'total_cached': total_entities,
            'total_hits': total_hits,
            'top_entities': top_entities
        }


class RateLimitedWikidataClient:
    """
    Wikidata API client with rate limiting and proper headers

    Features:
    - User-Agent header (required by Wikidata)
    - Rate limiting (max 60 requests/minute)
    - Request batching
    - Automatic retry with exponential backoff
    """

    def __init__(
        self,
        endpoint: str = "https://www.wikidata.org/w/api.php",
        requests_per_minute: int = 50,  # Conservative limit
        user_agent: str = "VermontSignal/2.0 (https://github.com/user/vermont-signal; contact@example.com)"
    ):
        """
        Initialize Wikidata client

        Args:
            endpoint: Wikidata API endpoint
            requests_per_minute: Max requests per minute
            user_agent: User agent string (REQUIRED by Wikidata)
        """
        self.endpoint = endpoint
        self.min_delay = 60.0 / requests_per_minute  # Seconds between requests
        self.last_request_time = 0
        self.user_agent = user_agent

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent
        })

        logger.info(f"Wikidata client initialized (max {requests_per_minute} req/min)")

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            sleep_time = self.min_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search_entity(
        self,
        entity_name: str,
        limit: int = 1,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        Search for entity in Wikidata

        Args:
            entity_name: Entity to search
            limit: Max results to return
            max_retries: Max retry attempts

        Returns:
            Dict with search results or None if not found
        """
        self._rate_limit()

        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': 'en',
            'search': entity_name,
            'limit': limit
        }

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    self.endpoint,
                    params=params,
                    timeout=10
                )

                response.raise_for_status()
                data = response.json()

                if data.get('search'):
                    return data['search'][0]  # Return first result
                else:
                    return None

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Too many requests
                    backoff = (2 ** attempt) * self.min_delay
                    logger.warning(f"Rate limited, backing off {backoff:.2f}s")
                    time.sleep(backoff)
                elif e.response.status_code == 403:
                    logger.error(f"403 Forbidden - check User-Agent header")
                    return None
                else:
                    logger.error(f"HTTP error: {e}")
                    return None

            except Exception as e:
                logger.error(f"Search failed for '{entity_name}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.min_delay * 2)
                else:
                    return None

        return None

    def get_entity_details(self, wikidata_id: str) -> Dict:
        """
        Get detailed entity properties

        Args:
            wikidata_id: Wikidata Q-ID

        Returns:
            Dict with entity properties
        """
        self._rate_limit()

        params = {
            'action': 'wbgetentities',
            'format': 'json',
            'ids': wikidata_id,
            'props': 'claims|labels|descriptions'
        }

        try:
            response = self.session.get(
                self.endpoint,
                params=params,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            entity = data['entities'].get(wikidata_id, {})
            claims = entity.get('claims', {})

            # Extract useful properties
            properties = {}

            # Population (P1082)
            if 'P1082' in claims:
                try:
                    properties['population'] = int(float(
                        claims['P1082'][0]['mainsnak']['datavalue']['value']['amount']
                    ))
                except:
                    pass

            # Coordinates (P625)
            if 'P625' in claims:
                try:
                    coords = claims['P625'][0]['mainsnak']['datavalue']['value']
                    properties['coordinates'] = {
                        'lat': coords['latitude'],
                        'lon': coords['longitude']
                    }
                except:
                    pass

            # Instance of (P31)
            if 'P31' in claims:
                try:
                    properties['instance_of'] = claims['P31'][0]['mainsnak']['datavalue']['value']['id']
                except:
                    pass

            return properties

        except Exception as e:
            logger.error(f"Failed to get details for {wikidata_id}: {e}")
            return {}

    def batch_search(
        self,
        entity_names: List[str],
        cache: WikidataCache = None
    ) -> Dict[str, Dict]:
        """
        Search for multiple entities with caching

        Args:
            entity_names: List of entity names to search
            cache: Optional WikidataCache for caching results

        Returns:
            Dict mapping entity_name -> wikidata result
        """
        results = {}

        for entity_name in entity_names:
            # Check cache first
            if cache:
                cached = cache.get(entity_name)
                if cached:
                    results[entity_name] = cached
                    continue

            # Search Wikidata
            search_result = self.search_entity(entity_name)

            if search_result:
                wikidata_id = search_result.get('id')
                description = search_result.get('description', '')

                # Get detailed properties
                properties = self.get_entity_details(wikidata_id)

                result = {
                    'wikidata_id': wikidata_id,
                    'description': description,
                    'properties': properties
                }

                results[entity_name] = result

                # Cache result
                if cache:
                    cache.set(entity_name, wikidata_id, description, properties)
            else:
                results[entity_name] = None

        return results


# Example usage
if __name__ == "__main__":
    # Initialize cache and client
    cache = WikidataCache()
    client = RateLimitedWikidataClient()

    # Test entities
    entities = ["Phil Scott", "Vermont", "Burlington", "University of Vermont"]

    print("Searching entities...")
    results = client.batch_search(entities, cache=cache)

    for entity, data in results.items():
        if data:
            print(f"\n{entity}:")
            print(f"  Wikidata ID: {data['wikidata_id']}")
            print(f"  Description: {data['description']}")
            print(f"  Properties: {data['properties']}")
        else:
            print(f"\n{entity}: Not found")

    # Show cache stats
    print("\n" + "=" * 60)
    print("Cache Statistics:")
    stats = cache.get_stats()
    print(f"  Total cached: {stats['total_cached']}")
    print(f"  Total hits: {stats['total_hits']}")
