#!/usr/bin/env python3
"""
Check pipeline status and calculate ETA for remaining articles

Usage:
    python scripts/check_pipeline_status.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vermont_news_analyzer.modules.database import VermontSignalDatabase


def get_article_stats(db):
    """Get article processing statistics"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Overall status counts
            cur.execute("""
                SELECT
                    status,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM articles
                GROUP BY status
                ORDER BY count DESC
            """)
            status_counts = cur.fetchall()

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

            # Recent completions (last 24 hours)
            cur.execute("""
                SELECT COUNT(*)
                FROM articles
                WHERE status = 'completed'
                  AND updated_at >= NOW() - INTERVAL '24 hours'
            """)
            recent_completions = cur.fetchone()[0]

            # Average processing time (for completed articles in last 7 days)
            cur.execute("""
                SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_seconds
                FROM articles
                WHERE status = 'completed'
                  AND updated_at >= NOW() - INTERVAL '7 days'
                  AND created_at IS NOT NULL
            """)
            avg_time_result = cur.fetchone()[0]
            avg_processing_time = float(avg_time_result) if avg_time_result else None

            # Get some sample pending articles
            cur.execute("""
                SELECT id, title, source, created_at
                FROM articles
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 5
            """)
            sample_pending = cur.fetchall()

            # Get some sample failed articles
            cur.execute("""
                SELECT id, title, source, error_message
                FROM articles
                WHERE status = 'failed'
                ORDER BY updated_at DESC
                LIMIT 3
            """)
            sample_failed = cur.fetchall()

            # Facts count
            cur.execute("SELECT COUNT(*) FROM facts")
            total_facts = cur.fetchone()[0]

            # Entity relationships count
            cur.execute("SELECT COUNT(*) FROM entity_relationships")
            total_relationships = cur.fetchone()[0]

    return {
        'status_counts': status_counts,
        'totals': totals,
        'recent_completions': recent_completions,
        'avg_processing_time': avg_processing_time,
        'sample_pending': sample_pending,
        'sample_failed': sample_failed,
        'total_facts': total_facts,
        'total_relationships': total_relationships
    }


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
        db = VermontSignalDatabase()
        db.connect()
        stats = get_article_stats(db)
        db.disconnect()

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return 1

    # Print header
    print("\n" + "=" * 70)
    print("VERMONT SIGNAL - PIPELINE STATUS")
    print("=" * 70)

    # Overall status
    total = stats['totals'][0]
    completed = stats['totals'][1]
    pending = stats['totals'][2]
    processing = stats['totals'][3]
    failed = stats['totals'][4]
    duplicate = stats['totals'][5] if len(stats['totals']) > 5 else 0

    print(f"\n📊 ARTICLE COUNTS:")
    print(f"   Total Articles:      {total:,}")
    print(f"   ✅ Completed:        {completed:,} ({completed/total*100:.1f}%)")
    print(f"   ⏳ Pending:          {pending:,} ({pending/total*100:.1f}%)")
    print(f"   🔄 Processing:       {processing:,} ({processing/total*100:.1f}%)")
    print(f"   ❌ Failed:           {failed:,} ({failed/total*100:.1f}%)")
    if duplicate > 0:
        print(f"   🔁 Duplicate:        {duplicate:,} ({duplicate/total*100:.1f}%)")

    # Status breakdown
    print(f"\n📈 STATUS BREAKDOWN:")
    for status, count, pct in stats['status_counts']:
        bar_length = int(pct / 2)  # Scale to fit in terminal
        bar = "█" * bar_length
        print(f"   {status:12s} {count:5,} ({pct:5.1f}%) {bar}")

    # Facts and relationships
    print(f"\n🔍 EXTRACTED DATA:")
    print(f"   Facts:               {stats['total_facts']:,}")
    print(f"   Relationships:       {stats['total_relationships']:,}")
    if completed > 0:
        print(f"   Avg facts/article:   {stats['total_facts']/completed:.1f}")

    # Recent activity
    print(f"\n⚡ RECENT ACTIVITY:")
    print(f"   Completed (24h):     {stats['recent_completions']:,} articles")

    # ETA calculation
    if pending > 0 and stats['avg_processing_time']:
        avg_time = stats['avg_processing_time']
        print(f"   Avg processing time: {format_time(avg_time)}")

        # Sequential ETA
        sequential_eta_seconds = pending * avg_time
        print(f"\n⏱️  ESTIMATED TIME REMAINING:")
        print(f"   Sequential (1 at a time): {format_time(sequential_eta_seconds)}")

        # Parallel ETA (assuming batch processing with ~10 parallel)
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
    if stats['sample_pending']:
        print(f"\n📄 SAMPLE PENDING ARTICLES:")
        for article_id, title, source, created_at in stats['sample_pending'][:3]:
            title_short = title[:50] + "..." if len(title) > 50 else title
            age = (datetime.now(created_at.tzinfo) - created_at) if created_at else None
            age_str = f"({format_time(age.total_seconds())} old)" if age else ""
            print(f"   [{article_id}] {title_short} {age_str}")
            print(f"         Source: {source}")

    # Sample failed articles
    if stats['sample_failed']:
        print(f"\n❌ SAMPLE FAILED ARTICLES:")
        for article_id, title, source, error_msg in stats['sample_failed']:
            title_short = title[:50] + "..." if len(title) > 50 else title
            error_short = error_msg[:60] + "..." if error_msg and len(error_msg) > 60 else (error_msg or "No error message")
            print(f"   [{article_id}] {title_short}")
            print(f"         Error: {error_short}")

    print("\n" + "=" * 70 + "\n")

    # Return exit code based on pending/failed
    if failed > pending * 0.1:  # More than 10% failed
        return 2
    elif pending > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
