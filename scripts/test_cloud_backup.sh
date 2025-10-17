#!/bin/bash
# Vermont Signal V2 - Test Cloud Backup System
# Verifies B2 credentials, connectivity, and backup functionality

set -e

echo "======================================================================"
echo "Vermont Signal - Cloud Backup Test Suite"
echo "======================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check B2 credentials exist
echo "Test 1: Checking B2 environment variables..."
if [ -z "$B2_APPLICATION_KEY_ID" ] || [ -z "$B2_APPLICATION_KEY" ]; then
    echo -e "${RED}✗ FAIL${NC} - B2 credentials not set"
    echo "  Please set B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    echo -e "${GREEN}✓ PASS${NC} - B2 credentials found"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi
echo ""

# Test 2: Authorize with B2
echo "Test 2: Testing B2 authorization..."
if b2 authorize-account "$B2_APPLICATION_KEY_ID" "$B2_APPLICATION_KEY" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Successfully authorized with B2"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - B2 authorization failed"
    echo "  Check your B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 3: Check if bucket exists
echo "Test 3: Checking B2 bucket access..."
BUCKET_NAME="${B2_BUCKET_NAME:-vermont-signal-backups}"
if b2 ls "$BUCKET_NAME" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Bucket '$BUCKET_NAME' accessible"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Cannot access bucket '$BUCKET_NAME'"
    echo "  Create bucket at: https://secure.backblaze.com/b2_buckets.htm"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 4: Check local backup directory
echo "Test 4: Checking local backup directory..."
BACKUP_DIR="/var/backups/vermont-signal"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "vermont_signal_*.sql.gz" -type f 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ PASS${NC} - Backup directory exists with $BACKUP_COUNT backup(s)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARN${NC} - Backup directory doesn't exist yet"
    echo "  Directory will be created on first backup"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi
echo ""

# Test 5: Test upload with small file
echo "Test 5: Testing B2 upload functionality..."
TEST_FILE="/tmp/vermont_signal_test_$(date +%s).txt"
echo "Vermont Signal Cloud Backup Test - $(date)" > "$TEST_FILE"

if b2 upload-file --quiet "$BUCKET_NAME" "$TEST_FILE" "test/$(basename $TEST_FILE)" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - Successfully uploaded test file to B2"
    TESTS_PASSED=$((TESTS_PASSED + 1))

    # Clean up test file
    TEST_FILE_NAME="test/$(basename $TEST_FILE)"
    FILE_ID=$(b2 ls "$BUCKET_NAME" "$TEST_FILE_NAME" 2>/dev/null | awk '{print $1}' | head -1)
    if [ ! -z "$FILE_ID" ]; then
        b2 delete-file-version "$TEST_FILE_NAME" "$FILE_ID" 2>/dev/null || true
        echo "  Test file cleaned up"
    fi
else
    echo -e "${RED}✗ FAIL${NC} - Failed to upload test file"
    echo "  Check bucket permissions (must allow write access)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
rm -f "$TEST_FILE"
echo ""

# Test 6: Check existing cloud backups
echo "Test 6: Checking existing cloud backups..."
CLOUD_BACKUP_COUNT=$(b2 ls "$BUCKET_NAME" backups/ 2>/dev/null | grep -c "vermont_signal_" || echo "0")
if [ "$CLOUD_BACKUP_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Found $CLOUD_BACKUP_COUNT backup(s) in cloud"
    echo "  Most recent backups:"
    b2 ls "$BUCKET_NAME" backups/ 2>/dev/null | grep "vermont_signal_" | tail -3 | while read line; do
        FILE_NAME=$(echo "$line" | awk '{print $NF}')
        FILE_DATE=$(echo "$FILE_NAME" | grep -oP 'vermont_signal_\K\d{8}' 2>/dev/null || echo "$FILE_NAME" | sed -E 's/.*vermont_signal_([0-9]{8})_.*/\1/')
        echo "    - $FILE_NAME (date: $FILE_DATE)"
    done
else
    echo -e "${YELLOW}⚠ INFO${NC} - No cloud backups found yet"
    echo "  First backup will be created on next scheduled run (4:15am ET)"
fi
TESTS_PASSED=$((TESTS_PASSED + 1))
echo ""

# Test 7: Check backup scripts exist
echo "Test 7: Checking backup scripts..."
if [ -f "/app/scripts/backup_database.sh" ] && [ -f "/app/scripts/backup_to_cloud.sh" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Backup scripts found"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Backup scripts missing"
    echo "  Expected: /app/scripts/backup_database.sh"
    echo "  Expected: /app/scripts/backup_to_cloud.sh"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 8: Check cron configuration
echo "Test 8: Checking cron configuration..."
if crontab -l 2>/dev/null | grep -q "backup_to_cloud.sh"; then
    echo -e "${GREEN}✓ PASS${NC} - Cloud backup cron job configured"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Cloud backup cron job not found"
    echo "  Expected cron entry for backup_to_cloud.sh"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Summary
echo "======================================================================"
echo "Test Summary"
echo "======================================================================"
TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo "Total tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
else
    echo "Failed: 0"
fi
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Cloud backup system is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Wait for automated backup at 4:15am ET, or"
    echo "  2. Run manual backup: /bin/bash /app/scripts/backup_to_cloud.sh"
    echo "  3. Monitor logs: tail -f /app/logs/cloud_backup.log"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please fix the issues above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Set B2 credentials in .env.hetzner"
    echo "  - Create bucket 'vermont-signal-backups' in B2 console"
    echo "  - Ensure application key has read/write permissions"
    echo "  - Restart worker: docker compose restart worker"
    exit 1
fi
