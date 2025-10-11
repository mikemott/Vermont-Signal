#!/bin/bash
set -e

# Vermont Signal - Automated Railway Deployment Script
# This script handles the complete deployment of Vermont Signal to Railway

echo "🚂 Vermont Signal - Railway Deployment"
echo "======================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI not found${NC}"
    echo "Install it with: brew install railway"
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo -e "${YELLOW}🔑 Not logged in to Railway${NC}"
    echo "Logging in..."
    railway login
fi

echo -e "${GREEN}✓${NC} Railway CLI ready"
echo ""

# Project setup
echo -e "${BLUE}📦 Setting up Railway project...${NC}"

# Check if already linked
if railway status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Already linked to a Railway project${NC}"
    read -p "Do you want to unlink and create a new project? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        railway unlink
    else
        echo "Using existing project"
    fi
fi

# Create new project if not linked
if ! railway status &> /dev/null; then
    echo -e "${BLUE}Creating new Railway project: vermont-signal${NC}"
    railway init --name vermont-signal
fi

echo -e "${GREEN}✓${NC} Project ready"
echo ""

# Add PostgreSQL database
echo -e "${BLUE}🗄️  Setting up PostgreSQL database...${NC}"
railway add --database postgresql || echo "Database may already exist"
echo -e "${GREEN}✓${NC} Database configured"
echo ""

# Set environment variables
echo -e "${BLUE}🔐 Setting environment variables...${NC}"

# Check if .env file exists
if [ -f .env ]; then
    # Read and set API keys from .env
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue

        # Only set API keys and model configs
        if [[ $key =~ ^(ANTHROPIC_API_KEY|GOOGLE_API_KEY|OPENAI_API_KEY|CLAUDE_MODEL|GEMINI_MODEL|OPENAI_MODEL|SPACY_MODEL)$ ]]; then
            # Remove quotes from value
            value="${value%\"}"
            value="${value#\"}"
            echo "Setting $key"
            railway variables --set "$key=$value" 2>/dev/null || true
        fi
    done < .env
else
    echo -e "${YELLOW}⚠️  No .env file found. You'll need to set API keys manually:${NC}"
    echo "  railway variables --set ANTHROPIC_API_KEY=your_key"
    echo "  railway variables --set GOOGLE_API_KEY=your_key"
    echo "  railway variables --set OPENAI_API_KEY=your_key"
fi

echo -e "${GREEN}✓${NC} Environment variables configured"
echo ""

# Deploy API service
echo -e "${BLUE}🚀 Deploying API service...${NC}"
echo "This will build and deploy the FastAPI backend"
echo ""

# The railway.toml will be automatically detected
railway up --detach

echo -e "${GREEN}✓${NC} API service deployed"
echo ""

# Create worker service
echo -e "${BLUE}⚙️  Setting up worker service...${NC}"
echo ""
echo -e "${YELLOW}Note: Worker service needs to be created via Railway dashboard${NC}"
echo ""
echo "Steps to complete worker setup:"
echo "1. Go to: https://railway.app/dashboard"
echo "2. Open your 'vermont-signal' project"
echo "3. Click '+ New' → 'Empty Service'"
echo "4. Name it: 'worker'"
echo "5. In service settings:"
echo "   - Source: Same GitHub repo"
echo "   - Root Directory: /"
echo "   - Build: Dockerfile"
echo "   - Dockerfile Path: Dockerfile.worker"
echo "   - Config Path: railway.worker.json"
echo "6. Copy environment variables from API service"
echo "7. Click 'Deploy'"
echo ""

# Get deployment info
echo -e "${BLUE}📊 Deployment Information${NC}"
echo "=========================="
echo ""

# Get project URL
PROJECT_URL=$(railway status 2>/dev/null | grep -o 'https://[^ ]*' || echo "URL will be available after first deployment")
echo -e "API URL: ${GREEN}${PROJECT_URL}${NC}"
echo ""

# Show next steps
echo -e "${BLUE}✅ Next Steps${NC}"
echo "============="
echo ""
echo "1. Wait for API deployment to complete (check: railway logs)"
echo "2. Set up worker service via dashboard (see instructions above)"
echo "3. Generate Railway domain for API:"
echo "   - Dashboard → API service → Settings → Networking → Generate Domain"
echo "4. Test the API:"
echo "   curl \${API_URL}/api/health"
echo "5. Initialize database (automatic on first API start)"
echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "Useful commands:"
echo "  railway logs          # View deployment logs"
echo "  railway logs -f       # Follow logs in real-time"
echo "  railway status        # Check deployment status"
echo "  railway variables     # View environment variables"
echo "  railway open          # Open project in dashboard"
echo ""
