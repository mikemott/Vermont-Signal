"""
Export articles from V1 database for import into V2
"""
import json
import subprocess
import sys

def get_database_connection_string():
    """Get DATABASE_URL from Fly.io secrets"""
    try:
        result = subprocess.run(
            ['flyctl', 'secrets', 'list', '-a', 'vermont-signal'],
            capture_output=True,
            text=True,
            check=True
        )

        # Get the actual DATABASE_URL value
        result = subprocess.run(
            ['flyctl', 'ssh', 'console', '-a', 'vermont-signal', '-C', 'echo $DATABASE_URL'],
            capture_output=True,
            text=True,
            check=True
        )

        db_url = result.stdout.strip()
        return db_url
    except Exception as e:
        print(f"Error getting database connection: {e}")
        return None

def export_articles_via_ssh():
    """Export articles using SSH and psql on the database server"""

    # Query to export articles as JSON
    query = """
    SELECT json_agg(row_to_json(articles))
    FROM (
        SELECT id, title, url, content, summary, source, author,
               published_date, collected_date
        FROM articles
        ORDER BY published_date DESC
    ) articles;
    """

    # Run query via SSH on database server
    cmd = [
        'flyctl', 'ssh', 'console', '-a', 'vermont-signal-db',
        '-C', f'psql -U postgres -t -c "{query}"'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )

        output = result.stdout.strip()

        if output:
            # Parse JSON output
            articles = json.loads(output)

            # Save to file
            with open('v1_articles_export.json', 'w') as f:
                json.dump(articles, f, indent=2, default=str)

            print(f"✓ Exported {len(articles)} articles to v1_articles_export.json")
            return True
        else:
            print("No articles found in V1 database")
            return False

    except subprocess.TimeoutExpired:
        print("Connection timed out")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw output: {result.stdout}")
        return False
    except Exception as e:
        print(f"Error exporting articles: {e}")
        return False

if __name__ == '__main__':
    print("Exporting articles from V1 database...")
    success = export_articles_via_ssh()
    sys.exit(0 if success else 1)
