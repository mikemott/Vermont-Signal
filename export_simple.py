"""Simple export script to run on V1 app"""
import psycopg2
import json
import os

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT id, title, url, content, summary, source, author,
           to_char(published_date, 'YYYY-MM-DD HH24:MI:SS'),
           to_char(collected_date, 'YYYY-MM-DD HH24:MI:SS')
    FROM articles
    ORDER BY published_date DESC
""")

articles = []
for row in cur.fetchall():
    articles.append({
        'id': row[0],
        'title': row[1],
        'url': row[2],
        'content': row[3],
        'summary': row[4],
        'source': row[5],
        'author': row[6],
        'published_date': row[7],
        'collected_date': row[8]
    })

print(json.dumps(articles, indent=2))
cur.close()
conn.close()
