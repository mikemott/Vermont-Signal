#!/bin/bash
#
# Monitor Vermont Signal Batch Processing
#
# Usage: ./scripts/monitor_processing.sh [--watch]
#

WATCH_MODE=false
if [ "$1" = "--watch" ]; then
    WATCH_MODE=true
fi

API_URL="https://vermontsignal.com/api"

# Function to show status
show_status() {
    clear
    echo "======================================================================"
    echo "Vermont Signal - Processing Monitor"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "======================================================================"
    echo ""

    # Get stats
    STATS=$(curl -sk "$API_URL/stats" 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo "❌ Error: Could not connect to API"
        return 1
    fi

    # Parse JSON using Python
    python3 << EOF
import json
import sys

try:
    data = json.loads('''$STATS''')

    articles = data['articles']
    facts = data['facts']
    entities = data['entities']
    costs = data['costs']

    total = articles['total']
    processed = articles['processed']
    pending = articles['pending']
    failed = articles['failed']

    progress_pct = (processed / total) * 100

    print(f"ARTICLES:")
    print(f"  Total:     {total:4d}")
    print(f"  Processed: {processed:4d} ({progress_pct:5.1f}%)")
    print(f"  Pending:   {pending:4d} ({(pending/total)*100:5.1f}%)")
    print(f"  Failed:    {failed:4d} ({(failed/total)*100:5.1f}%)")
    print()

    print(f"PROGRESS BAR:")
    bar_width = 50
    filled = int((processed / total) * bar_width)
    bar = '█' * filled + '░' * (bar_width - filled)
    print(f"  [{bar}] {progress_pct:.1f}%")
    print()

    print(f"DATA EXTRACTED:")
    print(f"  Facts:        {facts['total']:6,d}")
    print(f"  Entities:     {entities['total']:6,d}")
    print(f"  Avg Confidence: {facts['average_confidence']:.2%}")
    print()

    print(f"COSTS:")
    print(f"  Daily:   \${costs['daily']:6.2f} / \$10.00")
    print(f"  Monthly: \${costs['monthly']:6.2f} / \$50.00")
    print()

    if pending > 0:
        est_minutes = (pending * 10) / 60
        print(f"ESTIMATED COMPLETION:")
        print(f"  Remaining: {pending} articles")
        print(f"  Est. time: ~{est_minutes:.0f} minutes processing")
        print(f"  (Plus any rate limit wait time)")
    else:
        print("✓ ALL ARTICLES PROCESSED!")

except Exception as e:
    print(f"Error parsing stats: {e}")
    sys.exit(1)
EOF

    echo ""
    echo "======================================================================"

    # Check background process
    if pgrep -f "continue_processing.sh" > /dev/null; then
        echo "Background processor: ✓ RUNNING"
    else
        echo "Background processor: NOT RUNNING"
    fi

    echo ""
}

# Main execution
if [ "$WATCH_MODE" = true ]; then
    echo "Watch mode - Press Ctrl+C to exit"
    echo ""
    while true; do
        show_status
        sleep 10
    done
else
    show_status
    echo ""
    echo "Tip: Run with --watch to auto-refresh every 10 seconds"
    echo ""
fi
