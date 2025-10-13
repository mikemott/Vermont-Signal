#!/bin/bash
# Vermont Signal V2 - Domain Setup Script
# Automates HTTPS configuration with Let's Encrypt

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Vermont Signal V2 - Domain Setup${NC}"
echo ""

# Get domain from user
read -p "Enter your domain name (e.g., vermontsignal.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: Domain name is required${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Domain: $DOMAIN${NC}"
echo -e "${YELLOW}This will:${NC}"
echo "  1. Update .env.hetzner with your domain"
echo "  2. Update CORS origins for production"
echo "  3. Deploy to Hetzner"
echo "  4. Caddy will automatically obtain Let's Encrypt SSL certificate"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Setup cancelled"
    exit 0
fi

# Update .env.hetzner
echo ""
echo -e "${BLUE}Updating .env.hetzner...${NC}"

# Check if DOMAIN line exists
if grep -q "^DOMAIN=" .env.hetzner; then
    # Update existing DOMAIN
    sed -i.bak "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" .env.hetzner
else
    # Add DOMAIN if not present
    echo "DOMAIN=$DOMAIN" >> .env.hetzner
fi

# Update CORS_ORIGINS to include domain
echo -e "${BLUE}Updating CORS origins...${NC}"
CORS_VALUE="https://$DOMAIN,https://www.$DOMAIN,http://159.69.202.29"
sed -i.bak "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$CORS_VALUE|" .env.hetzner

echo -e "${GREEN}✓ Configuration updated${NC}"
echo ""

# Show DNS setup instructions
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}IMPORTANT: DNS Configuration Required${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Before deploying, add these DNS records to your domain registrar:"
echo ""
echo -e "${GREEN}A Record:${NC}"
echo "  Type: A"
echo "  Name: @ (or $DOMAIN)"
echo "  Value: 159.69.202.29"
echo "  TTL: 300"
echo ""
echo -e "${GREEN}A Record (www):${NC}"
echo "  Type: A"
echo "  Name: www"
echo "  Value: 159.69.202.29"
echo "  TTL: 300"
echo ""
echo -e "${YELLOW}Wait 5-10 minutes for DNS propagation, then press Enter to continue...${NC}"
read

# Check DNS
echo ""
echo -e "${BLUE}Checking DNS resolution...${NC}"
if host "$DOMAIN" | grep -q "159.69.202.29"; then
    echo -e "${GREEN}✓ DNS is configured correctly${NC}"
else
    echo -e "${YELLOW}⚠ DNS not yet propagated. You can deploy anyway, but SSL may not work immediately.${NC}"
    read -p "Deploy anyway? (yes/no): " DEPLOY_CONFIRM
    if [ "$DEPLOY_CONFIRM" != "yes" ]; then
        echo "Deployment cancelled. Run this script again when DNS is ready."
        exit 0
    fi
fi

# Deploy
echo ""
echo -e "${BLUE}Deploying to Hetzner...${NC}"
./deploy-hetzner.sh deploy

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Domain setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Your site will be available at:"
echo "  • https://$DOMAIN"
echo "  • https://www.$DOMAIN"
echo ""
echo "Caddy will automatically:"
echo "  • Obtain Let's Encrypt SSL certificate"
echo "  • Redirect HTTP → HTTPS"
echo "  • Auto-renew certificates before expiration"
echo ""
echo "API endpoints:"
echo "  • https://$DOMAIN/api/health"
echo "  • https://$DOMAIN/api/articles"
echo ""
echo -e "${YELLOW}Note: First SSL certificate may take 1-2 minutes to provision${NC}"
