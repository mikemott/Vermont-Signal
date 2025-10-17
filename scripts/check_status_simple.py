#!/usr/bin/env python3
"""
Simple pipeline status check (no heavy dependencies)
"""

import os
import psycopg2
from datetime import datetime, timedelta

# Database connection params
DB_HOST = os.getenv('DATABASE_HOST', '65.109.160.153')
DB_PORT = os.getenv('DATABASE_PORT', '5432')
DB_NAME = os.getenv('DATABASE_NAME', 'vermont_signal')
DB_USER = os.getenv('DATABASE_USER', 'postgres')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD', 'O9GjQvXVult0Hx7QwOjgBR3V3ikmIwmfyhjsqtdf85oWfrZG')


def format_time(seconds):
    """Format seconds into human readable time"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def main():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()

        print("\n" + "=" * 70)
        print("VERMONT SIGNAL - PIPELINE STATUS")
        print("=" * 70)

        # Total counts
        cur.execute("""
            SELECT
                COUNT(*) as total_articles,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'duplicate') as duplicate
            FROM articles
        """)
        totals = cur.fetchone()
        total, completed, pending, processing, failed, duplicate = totals

        print(f"\n📊 ARTICLE COUNTS:")
        print(f"   Total Articles:      {total:,}")
        print(f"   ✅ Completed:        {completed:,} ({completed/total*100:.1f}%)")
        print(f"   ⏳ Pending:          {pending:,} ({pending/total*100:.1f}%)")
        print(f"   🔄 Processing:       {processing:,} ({processing/total*100:.1f}%)")
        print(f"   ❌ Failed:           {failed:,} ({failed/total*100:.1f}%)")
        if duplicate > 0:
            print(f"   🔁 Duplicate:        {duplicate:,} ({duplicate/total*100:.1f}%)")

        # Status breakdown
        cur.execute("""
            SELECT
                status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM articles
            GROUP BY status
            ORDER BY count DESC
        """)
        print(f"\n📈 STATUS BREAKDOWN:")
        for status, count, pct in cur.fetchall():
            bar_length = int(pct / 2)
            bar = "█" * bar_length
            print(f"   {status:12s} {count:5,} ({pct:5.1f}%) {bar}")

        # Facts and relationships
        cur.execute("SELECT COUNT(*) FROM facts")
        total_facts = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM entity_relationships")
        total_relationships = cur.fetchone()[0]

        print(f"\n🔍 EXTRACTED DATA:")
        print(f"   Facts:               {total_facts:,}")
        print(f"   Relationships:       {total_relationships:,}")
        if completed > 0:
            print(f"   Avg facts/article:   {total_facts/completed:.1f}")

        # Recent activity
        cur.execute("""
            SELECT COUNT(*)
            FROM articles
            WHERE status = 'completed'
              AND updated_at >= NOW() - INTERVAL '24 hours'
        """)
        recent_completions = cur.fetchone()[0]

        # Average processing time
        cur.execute("""
            SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_seconds
            FROM articles
            WHERE status = 'completed'
              AND updated_at >= NOW() - INTERVAL '7 days'
              AND created_at IS NOT NULL
        """)
        avg_time_result = cur.fetchone()[0]
        avg_processing_time = float(avg_time_result) if avg_time_result else None

        print(f"\n⚡ RECENT ACTIVITY:")
        print(f"   Completed (24h):     {recent_completions:,} articles")

        # ETA calculation
        if pending > 0 and avg_processing_time:
            avg_time = avg_processing_time
            print(f"   Avg processing time: {format_time(avg_time)}")

            sequential_eta_seconds = pending * avg_time
            print(f"\n⏱️  ESTIMATED TIME REMAINING:")
            print(f"   Sequential (1 at a time): {format_time(sequential_eta_seconds)}")

            parallel_eta_seconds = sequential_eta_seconds / 10
            print(f"   Parallel (batch=10):      {format_time(parallel_eta_seconds)}")

            if sequential_eta_seconds < 86400:
                eta_datetime = datetime.now() + timedelta(seconds=parallel_eta_seconds)
                print(f"   Expected completion:      {eta_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        elif pending > 0:
            print(f"\n⏱️  ESTIMATED TIME REMAINING:")
            print(f"   Unable to calculate (no recent completions)")
            print(f"   Estimated: ~{pending * 8} seconds sequential (~{pending * 8 / 10} sec parallel)")

        # Sample pending articles
        cur.execute("""
            SELECT id, title, source, created_at
            FROM articles
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT 5
        """)
        sample_pending = cur.fetchall()

        if sample_pending:
            print(f"\n📄 SAMPLE PENDING ARTICLES:")
            for article_id, title, source, created_at in sample_pending[:3]:
                title_short = title[:50] + "..." if len(title) > 50 else title
                age = (datetime.now(created_at.tzinfo) - created_at) if created_at else None
                age_str = f"({format_time(age.total_seconds())} old)" if age else ""
                print(f"   [{article_id}] {title_short} {age_str}")
                print(f"         Source: {source}")

        # Sample failed articles
        cur.execute("""
            SELECT id, title, source, error_message
            FROM articles
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT 3
        """)
        sample_failed = cur.fetchall()

        if sample_failed:
            print(f"\n❌ SAMPLE FAILED ARTICLES:")
            for article_id, title, source, error_msg in sample_failed:
                title_short = title[:50] + "..." if len(title) > 50 else title
                error_short = error_msg[:60] + "..." if error_msg and len(error_msg) > 60 else (error_msg or "No error message")
                print(f"   [{article_id}] {title_short}")
                print(f"         Error: {error_short}")

        print("\n" + "=" * 70 + "\n")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
