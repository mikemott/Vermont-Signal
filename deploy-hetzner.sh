#!/bin/bash
# Vermont Signal V2 - Hetzner Deployment Script
# Automates deployment to Hetzner Cloud server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env.hetzner exists
if [ ! -f .env.hetzner ]; then
    log_error ".env.hetzner not found!"
    log_info "Copy .env.hetzner.example to .env.hetzner and fill in your values"
    exit 1
fi

# Load environment variables
export $(cat .env.hetzner | grep -v '^#' | xargs)

# Check if terraform/terraform.tfvars exists
if [ ! -f terraform/terraform.tfvars ]; then
    log_error "terraform/terraform.tfvars not found!"
    log_info "Copy terraform/terraform.tfvars.example to terraform/terraform.tfvars and fill in your values"
    exit 1
fi

# Parse command
COMMAND=${1:-help}

case $COMMAND in
    provision)
        log_info "🚀 Provisioning Hetzner Cloud server..."

        cd terraform
        terraform init
        terraform plan

        read -p "Apply this plan? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            terraform apply -auto-approve

            # Get server IP
            SERVER_IP=$(terraform output -raw server_ip)

            log_success "Server provisioned at: $SERVER_IP"
            log_info "Waiting 60 seconds for cloud-init to complete..."
            sleep 60

            # Save IP for later commands
            echo "$SERVER_IP" > ../.hetzner-server-ip

            log_success "Server ready! SSH: ssh root@$SERVER_IP"
        else
            log_warning "Provision cancelled"
        fi
        cd ..
        ;;

    deploy)
        log_info "📦 Deploying application to Hetzner server..."

        # Get server IP
        if [ -f .hetzner-server-ip ]; then
            SERVER_IP=$(cat .hetzner-server-ip)
        elif [ -f terraform/terraform.tfstate ]; then
            cd terraform
            SERVER_IP=$(terraform output -raw server_ip)
            cd ..
        else
            log_error "Server IP not found. Run 'provision' first or set SERVER_IP manually"
            exit 1
        fi

        log_info "Deploying to: $SERVER_IP"

        # Create temporary directory for deployment
        DEPLOY_DIR=$(mktemp -d)

        # Copy necessary files
        log_info "Copying files..."
        cp -r . "$DEPLOY_DIR/"
        cp .env.hetzner "$DEPLOY_DIR/.env"

        # Rsync project to server
        log_info "Syncing files to server..."
        rsync -avz -e "ssh -i ~/.ssh/hetzner_vermont_signal -o StrictHostKeyChecking=no" \
                   --exclude '.git' \
                   --exclude 'venv' \
                   --exclude '__pycache__' \
                   --exclude '*.pyc' \
                   --exclude 'node_modules' \
                   --exclude '.next' \
                   --exclude 'terraform' \
                   --exclude '.hetzner-server-ip' \
                   "$DEPLOY_DIR/" "root@$SERVER_IP:/opt/vermont-signal/"

        # Deploy on server
        log_info "Building and starting containers..."
        ssh -i ~/.ssh/hetzner_vermont_signal root@$SERVER_IP << 'ENDSSH'
set -e
cd /opt/vermont-signal

# Build and start services
docker compose -f docker-compose.hetzner.yml pull || true
docker compose -f docker-compose.hetzner.yml build --pull
docker compose -f docker-compose.hetzner.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 30

# Check status
docker compose -f docker-compose.hetzner.yml ps

# Test health endpoint
echo "🔍 Testing API health..."
sleep 5
curl -f http://localhost:8000/api/health || echo "⚠ Health check failed (may still be starting)"

echo "✓ Deployment complete!"
ENDSSH

        # Cleanup
        rm -rf "$DEPLOY_DIR"

        log_success "Application deployed successfully!"
        log_info "Access your app at: http://$SERVER_IP"
        log_info "API endpoint: http://$SERVER_IP:8000/api/health"
        ;;

    logs)
        log_info "📜 Fetching logs from server..."

        if [ -f .hetzner-server-ip ]; then
            SERVER_IP=$(cat .hetzner-server-ip)
        else
            log_error "Server IP not found"
            exit 1
        fi

        SERVICE=${2:-}

        if [ -z "$SERVICE" ]; then
            ssh -i ~/.ssh/hetzner_vermont_signal root@$SERVER_IP "cd /opt/vermont-signal && docker compose -f docker-compose.hetzner.yml logs --tail=100 -f"
        else
            ssh -i ~/.ssh/hetzner_vermont_signal root@$SERVER_IP "cd /opt/vermont-signal && docker compose -f docker-compose.hetzner.yml logs --tail=100 -f $SERVICE"
        fi
        ;;

    ssh)
        log_info "🔐 Connecting to server..."

        if [ -f .hetzner-server-ip ]; then
            SERVER_IP=$(cat .hetzner-server-ip)
        else
            log_error "Server IP not found"
            exit 1
        fi

        ssh -i ~/.ssh/hetzner_vermont_signal root@$SERVER_IP
        ;;

    status)
        log_info "📊 Checking server status..."

        if [ -f .hetzner-server-ip ]; then
            SERVER_IP=$(cat .hetzner-server-ip)
        else
            log_error "Server IP not found"
            exit 1
        fi

        ssh -i ~/.ssh/hetzner_vermont_signal root@$SERVER_IP "cd /opt/vermont-signal && docker compose -f docker-compose.hetzner.yml ps"
        ;;

    destroy)
        log_warning "⚠️  This will DESTROY the Hetzner server and all data!"
        read -p "Are you sure? Type 'destroy' to confirm: " confirm

        if [ "$confirm" = "destroy" ]; then
            cd terraform
            terraform destroy
            cd ..
            rm -f .hetzner-server-ip
            log_success "Server destroyed"
        else
            log_warning "Destroy cancelled"
        fi
        ;;

    help|*)
        echo ""
        echo "Vermont Signal V2 - Hetzner Deployment"
        echo ""
        echo "Usage: ./deploy-hetzner.sh [command]"
        echo ""
        echo "Commands:"
        echo "  provision   - Create Hetzner server with Terraform"
        echo "  deploy      - Deploy application to server"
        echo "  logs [svc]  - View logs (optional: specify service name)"
        echo "  ssh         - SSH into server"
        echo "  status      - Check container status"
        echo "  destroy     - Destroy server (WARNING: deletes everything)"
        echo "  help        - Show this help"
        echo ""
        echo "First-time setup:"
        echo "  1. cp terraform/terraform.tfvars.example terraform/terraform.tfvars"
        echo "  2. cp .env.hetzner.example .env.hetzner"
        echo "  3. Fill in your values in both files"
        echo "  4. ./deploy-hetzner.sh provision"
        echo "  5. ./deploy-hetzner.sh deploy"
        echo ""
        ;;
esac
