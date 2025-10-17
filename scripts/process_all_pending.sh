#!/bin/bash
#
# Process All Pending Articles (Server-Side Script)
#
# This script processes all pending articles directly on the server,
# bypassing the API rate limit. Run this on the production server.
#
# Usage:
#   ./scripts/process_all_pending.sh
#

set -e

echo "======================================================================"
echo "Vermont Signal - Process All Pending Articles"
echo "======================================================================"
echo ""

# Configuration
BATCH_SIZE=20
MAX_ITERATIONS=20
ITERATION=1

# Check we're in the right directory
if [ ! -f "vermont_news_analyzer/batch_processor.py" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Function to get pending count from database
get_pending_count() {
    docker exec vermont-postgres psql -U vermont_signal -d vermont_signal -t -c \
        "SELECT COUNT(*) FROM articles WHERE processing_status = 'pending';" | tr -d ' ' 2>/dev/null || echo "0"
}

# Function to get stats
show_stats() {
    docker exec vermont-postgres psql -U vermont_signal -d vermont_signal -c "
        SELECT
            processing_status,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM articles
        GROUP BY processing_status
        ORDER BY count DESC;
    "
}

echo "Current status:"
show_stats
echo ""

# Main processing loop
while [ $ITERATION -le $MAX_ITERATIONS ]; do
    PENDING=$(get_pending_count)

    if [ "$PENDING" = "0" ] || [ -z "$PENDING" ]; then
        echo ""
        echo "✓ No pending articles remaining!"
        break
    fi

    echo "======================================================================"
    echo "Batch $ITERATION - Processing up to $BATCH_SIZE articles"
    echo "Pending: $PENDING"
    echo "======================================================================"
    echo ""

    # Run batch processor
    python3 -m vermont_news_analyzer.batch_processor --limit $BATCH_SIZE

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "✓ Batch $ITERATION completed successfully"
    else
        echo ""
        echo "⚠ Batch $ITERATION exited with code $EXIT_CODE"
    fi

    ITERATION=$((ITERATION + 1))

    # Check remaining
    PENDING_AFTER=$(get_pending_count)
    echo "Remaining: $PENDING_AFTER pending articles"

    # Small delay between batches
    if [ "$PENDING_AFTER" != "0" ]; then
        echo "Waiting 5 seconds before next batch..."
        sleep 5
    fi
    echo ""
done

echo ""
echo "======================================================================"
echo "Processing Complete - Final Status"
echo "======================================================================"
echo ""
show_stats

echo ""
echo "======================================================================"
echo "Generating Entity Relationships"
echo "======================================================================"
echo ""

if [ -f "scripts/generate_relationships.py" ]; then
    python3 scripts/generate_relationships.py --days 30
else
    echo "⚠ Relationship generation script not found"
fi

echo ""
echo "======================================================================"
echo "Final Statistics"
echo "======================================================================"
echo ""

# Show detailed stats
docker exec vermont-postgres psql -U vermont_signal -d vermont_signal -c "
    SELECT
        'Total Articles' as metric,
        COUNT(*)::text as value
    FROM articles
    UNION ALL
    SELECT
        'Total Facts',
        COUNT(*)::text
    FROM facts
    UNION ALL
    SELECT
        'Total Entities',
        COUNT(DISTINCT entity)::text
    FROM facts
    UNION ALL
    SELECT
        'Total Relationships',
        COUNT(*)::text
    FROM entity_relationships
    UNION ALL
    SELECT
        'Avg Confidence',
        ROUND(AVG(confidence)::numeric, 4)::text
    FROM facts;
"

echo ""
echo "✓ All done!"
echo ""
