#!/bin/bash
#
# Vermont Signal V1 → V2 Migration Helper
# Migrates articles from Fly.io to Hetzner with filtering
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load Hetzner environment variables
if [ -f .env.hetzner ]; then
    export $(grep -v '^#' .env.hetzner | grep -v '^$' | xargs)
else
    echo -e "${RED}Error: .env.hetzner not found${NC}"
    exit 1
fi

# Read Hetzner IP
if [ -f .hetzner-server-ip ]; then
    HETZNER_IP=$(cat .hetzner-server-ip | tr -d '\n')
else
    echo -e "${RED}Error: .hetzner-server-ip not found${NC}"
    echo "Run './deploy-hetzner.sh provision' first"
    exit 1
fi

# V1 Database credentials
V1_HOST="localhost"
V1_PORT="5432"
V1_DATABASE="vermont_signal"
V1_USER="vermont_signal"
V1_PASSWORD="vermont_v1_2025_secure"

# V2 Database credentials (Hetzner)
V2_HOST="$HETZNER_IP"
V2_PORT="5432"
V2_DATABASE="vermont_signal"
V2_USER="vermont_signal"
V2_PASSWORD="$DATABASE_PASSWORD"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Function to check if proxy is running
check_proxy() {
    if ! pgrep -f "flyctl proxy.*5432" > /dev/null; then
        return 1
    fi
    return 0
}

# Function to start proxy
start_proxy() {
    echo -e "${BLUE}Starting Fly.io database proxy...${NC}"
    flyctl proxy 5432:5432 -a vermont-signal-db > /tmp/flyctl-proxy.log 2>&1 &
    PROXY_PID=$!

    # Wait for proxy to be ready
    echo -e "${YELLOW}Waiting for proxy to connect...${NC}"
    sleep 5

    if check_proxy; then
        echo -e "${GREEN}✓ Proxy started (PID: $PROXY_PID)${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to start proxy${NC}"
        cat /tmp/flyctl-proxy.log
        return 1
    fi
}

# Function to stop proxy
stop_proxy() {
    echo -e "${BLUE}Stopping proxy...${NC}"
    pkill -f "flyctl proxy.*5432" || true
    sleep 1
    echo -e "${GREEN}✓ Proxy stopped${NC}"
}

# Function to test V1 connection
test_v1_connection() {
    echo -e "${BLUE}Testing V1 (Fly.io) database connection...${NC}"

    if ! check_proxy; then
        echo -e "${YELLOW}Proxy not running, starting it...${NC}"
        start_proxy || return 1
    fi

    PGPASSWORD="$V1_PASSWORD" psql -h "$V1_HOST" -p "$V1_PORT" -U "$V1_USER" -d "$V1_DATABASE" -c "SELECT COUNT(*) FROM articles;" > /tmp/v1-test.txt 2>&1

    if [ $? -eq 0 ]; then
        ARTICLE_COUNT=$(grep -oE '[0-9]+' /tmp/v1-test.txt | head -1)
        echo -e "${GREEN}✓ V1 connection successful${NC}"
        echo -e "${BLUE}  Articles in V1: $ARTICLE_COUNT${NC}"
        return 0
    else
        echo -e "${RED}✗ V1 connection failed${NC}"
        cat /tmp/v1-test.txt
        return 1
    fi
}

# Function to test V2 connection
test_v2_connection() {
    echo -e "${BLUE}Testing V2 (Hetzner) database connection...${NC}"

    PGPASSWORD="$V2_PASSWORD" psql -h "$V2_HOST" -p "$V2_PORT" -U "$V2_USER" -d "$V2_DATABASE" -c "SELECT COUNT(*) FROM articles;" > /tmp/v2-test.txt 2>&1

    if [ $? -eq 0 ]; then
        ARTICLE_COUNT=$(grep -oE '[0-9]+' /tmp/v2-test.txt | head -1)
        echo -e "${GREEN}✓ V2 connection successful${NC}"
        echo -e "${BLUE}  Articles in V2: $ARTICLE_COUNT${NC}"
        return 0
    else
        echo -e "${RED}✗ V2 connection failed${NC}"
        cat /tmp/v2-test.txt
        return 1
    fi
}

# Function to run analysis
run_analysis() {
    local DAYS=${1:-365}
    local LIMIT=${2:-""}

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Running Migration Analysis${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}Time period: Last $DAYS days${NC}"
    [ -n "$LIMIT" ] && echo -e "${YELLOW}Limit: $LIMIT articles${NC}"
    echo ""

    # Build command
    CMD="python scripts/migrate_v1_to_v2.py \
        --analyze \
        --days $DAYS \
        --v1-host $V1_HOST \
        --v1-port $V1_PORT \
        --v1-database $V1_DATABASE \
        --v1-user $V1_USER \
        --v1-password $V1_PASSWORD"

    [ -n "$LIMIT" ] && CMD="$CMD --limit $LIMIT"

    # Run analysis
    eval $CMD

    echo ""
    echo -e "${GREEN}✓ Analysis complete${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Review the analysis above"
    echo -e "  2. Run: ${BLUE}./migrate-to-hetzner.sh dry-run${NC} to test without writing"
    echo -e "  3. Run: ${BLUE}./migrate-to-hetzner.sh migrate${NC} to perform actual migration"
}

# Function to run dry-run
run_dry_run() {
    local DAYS=${1:-365}

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Running Dry-Run Migration${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}Time period: Last $DAYS days${NC}"
    echo -e "${YELLOW}Mode: DRY RUN (no changes will be made)${NC}"
    echo ""

    python scripts/migrate_v1_to_v2.py \
        --import \
        --dry-run \
        --days $DAYS \
        --v1-host $V1_HOST \
        --v1-port $V1_PORT \
        --v1-database $V1_DATABASE \
        --v1-user $V1_USER \
        --v1-password $V1_PASSWORD

    echo ""
    echo -e "${GREEN}✓ Dry-run complete${NC}"
    echo ""
    echo -e "${YELLOW}This was a simulation - no articles were imported${NC}"
    echo -e "Next step: Run ${BLUE}./migrate-to-hetzner.sh migrate${NC} to perform actual migration"
}

# Function to run actual migration
run_migration() {
    local DAYS=${1:-365}

    echo -e "${RED}========================================${NC}"
    echo -e "${RED}ATTENTION: LIVE MIGRATION${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "${YELLOW}This will import articles from V1 to V2${NC}"
    echo -e "${YELLOW}Time period: Last $DAYS days${NC}"
    echo ""

    read -p "Are you sure you want to proceed? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}Migration cancelled${NC}"
        return 1
    fi

    echo -e "${BLUE}Starting migration...${NC}"
    echo ""

    python scripts/migrate_v1_to_v2.py \
        --import \
        --days $DAYS \
        --v1-host $V1_HOST \
        --v1-port $V1_PORT \
        --v1-database $V1_DATABASE \
        --v1-user $V1_USER \
        --v1-password $V1_PASSWORD

    echo ""
    echo -e "${GREEN}✓ Migration complete!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Run: ${BLUE}./migrate-to-hetzner.sh verify${NC} to check results"
    echo -e "  2. Trigger batch processing to analyze migrated articles"
}

# Function to verify migration
verify_migration() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Verifying Migration Results${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # Connect to V2 and run verification queries
    PGPASSWORD="$V2_PASSWORD" psql -h "$V2_HOST" -p "$V2_PORT" -U "$V2_USER" -d "$V2_DATABASE" << 'EOF'
-- Article counts
\echo '=== Article Counts ==='
SELECT COUNT(*) as total_articles FROM articles;

-- By processing status
\echo ''
\echo '=== By Processing Status ==='
SELECT processing_status, COUNT(*)
FROM articles
GROUP BY processing_status
ORDER BY COUNT(*) DESC;

-- By source
\echo ''
\echo '=== By Source ==='
SELECT source, COUNT(*)
FROM articles
GROUP BY source
ORDER BY COUNT(*) DESC;

-- Date range
\echo ''
\echo '=== Date Range ==='
SELECT
    MIN(published_date)::date as oldest,
    MAX(published_date)::date as newest,
    COUNT(*) as total
FROM articles;

-- Recent articles
\echo ''
\echo '=== Recent Articles (last 10) ==='
SELECT id, title, source, published_date::date
FROM articles
ORDER BY published_date DESC
LIMIT 10;
EOF

    echo ""
    echo -e "${GREEN}✓ Verification complete${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
${GREEN}Vermont Signal V1 → V2 Migration Tool${NC}

${BLUE}Usage:${NC}
  $0 <command> [options]

${BLUE}Commands:${NC}
  ${GREEN}test${NC}            Test connections to V1 and V2 databases
  ${GREEN}analyze${NC} [days]  Analyze V1 articles (default: 365 days)
  ${GREEN}dry-run${NC} [days]  Run migration simulation (default: 365 days)
  ${GREEN}migrate${NC} [days]  Perform actual migration (default: 365 days)
  ${GREEN}verify${NC}          Verify migration results in V2
  ${GREEN}stop-proxy${NC}      Stop Fly.io proxy
  ${GREEN}help${NC}            Show this help message

${BLUE}Examples:${NC}
  $0 test                    # Test both database connections
  $0 analyze 90              # Analyze last 90 days of articles
  $0 dry-run 365             # Simulate full year migration
  $0 migrate 180             # Migrate last 6 months
  $0 verify                  # Check migration results

${BLUE}Prerequisites:${NC}
  1. Hetzner server deployed and accessible
  2. Virtual environment activated
  3. Fly.io CLI authenticated (run: flyctl auth login)

${BLUE}Migration Process:${NC}
  1. Run: $0 test           # Verify connections
  2. Run: $0 analyze        # Review what will be imported
  3. Run: $0 dry-run        # Test migration
  4. Run: $0 migrate        # Perform actual import
  5. Run: $0 verify         # Check results

EOF
}

# Main script logic
main() {
    local COMMAND=${1:-help}
    local DAYS=${2:-365}

    case "$COMMAND" in
        test)
            echo -e "${BLUE}Testing database connections...${NC}"
            echo ""
            test_v1_connection
            echo ""
            test_v2_connection
            echo ""
            echo -e "${GREEN}✓ Connection tests complete${NC}"
            ;;

        analyze)
            if ! check_proxy; then
                start_proxy || exit 1
            fi
            test_v1_connection || exit 1
            test_v2_connection || exit 1
            echo ""
            run_analysis $DAYS
            ;;

        dry-run)
            if ! check_proxy; then
                start_proxy || exit 1
            fi
            test_v1_connection || exit 1
            test_v2_connection || exit 1
            echo ""
            run_dry_run $DAYS
            ;;

        migrate)
            if ! check_proxy; then
                start_proxy || exit 1
            fi
            test_v1_connection || exit 1
            test_v2_connection || exit 1
            echo ""
            run_migration $DAYS
            ;;

        verify)
            test_v2_connection || exit 1
            echo ""
            verify_migration
            ;;

        stop-proxy)
            stop_proxy
            ;;

        help|--help|-h)
            show_usage
            ;;

        *)
            echo -e "${RED}Error: Unknown command '$COMMAND'${NC}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
