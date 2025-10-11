#!/bin/bash
# Initialize database via the running API container
# This creates a temporary script and executes it inside Railway

echo "🗄️  Initializing Database Schema on Railway"
echo "=" * 60

# Get the API URL
API_URL="https://api-production-9b77.up.railway.app"

echo ""
echo "Checking API health..."
HEALTH=$(curl -s "$API_URL/api/health")
echo "$HEALTH"

if [[ $HEALTH != *"healthy"* ]]; then
    echo "❌ API is not healthy. Cannot proceed."
    exit 1
fi

echo ""
echo "Attempting to initialize database..."
echo "Note: Admin endpoint may not be deployed yet."
echo ""

# Try admin endpoint
RESULT=$(curl -s -X POST "$API_URL/api/admin/init-db" 2>&1)
echo "$RESULT"

if [[ $RESULT == *"success"* ]]; then
    echo ""
    echo "✅ Database initialized successfully!"
    echo ""
    echo "Verifying..."
    curl -s "$API_URL/api/stats" | python3 -m json.tool
    exit 0
elif [[ $RESULT == *"Not Found"* ]]; then
    echo ""
    echo "⚠️  Admin endpoint not found. New deployment not live yet."
    echo ""
    echo "Please wait 5-10 minutes for Railway to deploy the latest code,"
    echo "then run this script again, OR use Railway dashboard:"
    echo ""
    echo "1. Go to: https://railway.app/dashboard"
    echo "2. Open 'vermont-signal-v2' project"
    echo "3. Click on 'api' service"
    echo "4. Go to 'Deployments' tab"
    echo "5. Wait for latest deployment to complete"
    echo "6. Run this script again"
    exit 1
else
    echo ""
    echo "❌ Unexpected response. Check Railway logs:"
    echo "   railway logs"
    exit 1
fi
