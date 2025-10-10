#!/bin/bash
set -e

echo "🚂 Vermont Signal V2 - Railway Deployment Script"
echo "================================================"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing via Homebrew..."
    brew install railway
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway..."
    railway login
else
    echo "✅ Already logged in to Railway"
fi

echo ""
echo "📦 Creating Railway project..."
railway init --name vermont-signal-v2

echo ""
echo "🗄️  Adding PostgreSQL database..."
railway add --database postgres

echo ""
echo "🔑 Environment variables..."
echo "   Please set these via Railway Dashboard if not already set:"
echo "   - ANTHROPIC_API_KEY"
echo "   - GOOGLE_API_KEY"
echo "   - OPENAI_API_KEY"
echo "   - SPACY_MODEL=en_core_web_trf"
echo "   - TZ=America/New_York"
echo ""
railway variables

echo ""
echo "🚀 Deploying Worker service (with full ML stack)..."
railway up --service worker --dockerfile Dockerfile.worker

echo ""
echo "🌐 Creating API service..."
railway service create api

echo ""
echo "🚀 Deploying API service..."
railway service use api
railway up --dockerfile Dockerfile.api

echo ""
echo "🌍 Generating public domain for API..."
railway domain

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 View your deployment:"
echo "   Dashboard: https://railway.app/dashboard"
echo "   Logs:      railway logs"
echo "   Status:    railway status"
echo ""
echo "🎉 Your Vermont Signal V2 is now live on Railway!"
