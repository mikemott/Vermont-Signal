"""
Export articles from V1 database via proxy connection
"""
import psycopg2
import json
import time
import sys

def export_articles():
    """Export articles using proxy connection"""

    # Wait for proxy to connect
    print("Waiting for proxy to connect...")
    time.sleep(3)

    # Connect via proxy
    conn_params = {
        'host': 'localhost',
        'port': 15432,
        'database': 'vermont_signal',
        'user': 'vermont_signal',
        'password': '',  # Try without password first
        'connect_timeout': 10
    }

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        # Check what tables exist
        print("Checking database tables...")
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cur.fetchall()
        print(f"Found tables: {[t[0] for t in tables]}")

        # Check if articles table exists
        if not any(t[0] == 'articles' for t in tables):
            print("No 'articles' table found in V1 database")
            return False

        # Get article count
        cur.execute("SELECT COUNT(*) FROM articles")
        count = cur.fetchone()[0]
        print(f"Found {count} articles in V1 database")

        if count == 0:
            print("No articles to export")
            return False

        # Export articles
        print("Exporting articles...")
        cur.execute("""
            SELECT id, title, url, content, summary, source, author,
                   published_date, collected_date
            FROM articles
            ORDER BY published_date DESC
        """)

        rows = cur.fetchall()
        articles = []

        for row in rows:
            articles.append({
                'id': row[0],
                'title': row[1],
                'url': row[2],
                'content': row[3],
                'summary': row[4],
                'source': row[5],
                'author': row[6],
                'published_date': row[7].isoformat() if row[7] else None,
                'collected_date': row[8].isoformat() if row[8] else None
            })

        # Save to file
        with open('v1_articles_export.json', 'w') as f:
            json.dump(articles, f, indent=2)

        print(f"✓ Exported {len(articles)} articles to v1_articles_export.json")

        cur.close()
        conn.close()

        return True

    except psycopg2.OperationalError as e:
        print(f"Connection error: {e}")
        print("Make sure the proxy is running: flyctl proxy 15432:5432 -a vermont-signal-db")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    success = export_articles()
    sys.exit(0 if success else 1)
