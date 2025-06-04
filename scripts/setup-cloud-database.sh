#!/bin/bash
# AQEA Cloud Database Setup Script
# Deploy distributed extractor with central Supabase database

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
DEFAULT_LANGUAGE="de"
DEFAULT_TOTAL_WORKERS=15
SUPABASE_PROJECT=""
SUPABASE_PASSWORD=""

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
🚀 AQEA Cloud Database Deployment Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup           Initial setup with Supabase
    deploy-multi    Deploy across multiple cloud providers
    deploy-single   Deploy to single provider
    status          Show global status
    cleanup         Cleanup all deployments

Options:
    --language LANG         Language to extract (default: $DEFAULT_LANGUAGE)
    --workers NUM           Total workers across all providers (default: $DEFAULT_TOTAL_WORKERS)
    --supabase-project ID   Supabase project ID
    --supabase-password PWD Supabase database password
    
Examples:
    $0 setup --supabase-project xyz123 --supabase-password mypassword
    $0 deploy-multi --language de --workers 20
    $0 deploy-single --provider hetzner --workers 5
    $0 status

Multi-Provider Deployment:
    Hetzner:      60% workers (cheapest)
    DigitalOcean: 30% workers  
    Linode:       10% workers

EOF
}

# Parse arguments
parse_args() {
    COMMAND=""
    LANGUAGE=$DEFAULT_LANGUAGE
    TOTAL_WORKERS=$DEFAULT_TOTAL_WORKERS
    PROVIDER=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            setup|deploy-multi|deploy-single|status|cleanup)
                COMMAND=$1
                shift
                ;;
            --language)
                LANGUAGE="$2"
                shift 2
                ;;
            --workers)
                TOTAL_WORKERS="$2"
                shift 2
                ;;
            --supabase-project)
                SUPABASE_PROJECT="$2"
                shift 2
                ;;
            --supabase-password)
                SUPABASE_PASSWORD="$2"
                shift 2
                ;;
            --provider)
                PROVIDER="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
}

# Setup Supabase database
setup_supabase() {
    log_info "Setting up Supabase database..."
    
    if [[ -z "$SUPABASE_PROJECT" ]] || [[ -z "$SUPABASE_PASSWORD" ]]; then
        log_error "Supabase project ID and password required for setup"
        log_info "Usage: $0 setup --supabase-project YOUR_PROJECT --supabase-password YOUR_PASSWORD"
        exit 1
    fi
    
    # Create environment file
    cat > "$PROJECT_DIR/.env.cloud" << EOF
# AQEA Cloud Database Configuration
SUPABASE_DATABASE_URL=postgresql://postgres:${SUPABASE_PASSWORD}@${SUPABASE_PROJECT}.supabase.co:5432/postgres
SUPABASE_PROJECT=${SUPABASE_PROJECT}
SUPABASE_PASSWORD=${SUPABASE_PASSWORD}

# Default settings
LANGUAGE=${LANGUAGE}
TOTAL_WORKERS=${TOTAL_WORKERS}

# Redis Cache (Optional)
REDIS_URL=redis://localhost:6379

# Monitoring (Optional)
GRAFANA_PASSWORD=admin123
EOF

    log_success "Environment file created: .env.cloud"
    
    # Initialize database schema
    log_info "Initializing database schema..."
    
    # Use psql to run initialization script
    if command -v psql &> /dev/null; then
        psql "postgresql://postgres:${SUPABASE_PASSWORD}@${SUPABASE_PROJECT}.supabase.co:5432/postgres" \
            -f "$PROJECT_DIR/scripts/init-db.sql"
        log_success "Database schema initialized"
    else
        log_warning "psql not found. Please run the following manually:"
        log_info "psql 'postgresql://postgres:${SUPABASE_PASSWORD}@${SUPABASE_PROJECT}.supabase.co:5432/postgres' -f scripts/init-db.sql"
    fi
}

# Deploy to multiple cloud providers
deploy_multi_cloud() {
    log_info "🌍 Deploying AQEA across multiple cloud providers..."
    
    if [[ ! -f "$PROJECT_DIR/.env.cloud" ]]; then
        log_error "Environment file not found. Run setup first."
        exit 1
    fi
    
    source "$PROJECT_DIR/.env.cloud"
    
    # Calculate worker distribution
    HETZNER_WORKERS=$((TOTAL_WORKERS * 60 / 100))      # 60%
    DIGITALOCEAN_WORKERS=$((TOTAL_WORKERS * 30 / 100)) # 30%
    LINODE_WORKERS=$((TOTAL_WORKERS * 10 / 100))       # 10%
    
    log_info "Worker distribution:"
    log_info "  Hetzner Cloud:  $HETZNER_WORKERS workers (60%)"
    log_info "  DigitalOcean:   $DIGITALOCEAN_WORKERS workers (30%)"
    log_info "  Linode:         $LINODE_WORKERS workers (10%)"
    log_info "  Total:          $TOTAL_WORKERS workers"
    
    cd "$PROJECT_DIR"
    
    # Deploy Hetzner (Primary)
    if [[ $HETZNER_WORKERS -gt 0 ]]; then
        log_info "🇩🇪 Deploying to Hetzner Cloud..."
        
        export CLOUD_PROVIDER=hetzner
        export CLOUD_REGION=nbg1
        export WORKER_COUNT=$HETZNER_WORKERS
        export MASTER_PORT=8080
        export DASHBOARD_PORT=8090
        
        docker-compose -f docker-compose.cloud.yml -p aqea-hetzner up -d
        log_success "Hetzner deployment started"
    fi
    
    # Deploy DigitalOcean
    if [[ $DIGITALOCEAN_WORKERS -gt 0 ]]; then
        log_info "🌊 Deploying to DigitalOcean..."
        
        export CLOUD_PROVIDER=digitalocean
        export CLOUD_REGION=fra1
        export WORKER_COUNT=$DIGITALOCEAN_WORKERS
        export MASTER_PORT=8081
        export DASHBOARD_PORT=8091
        
        docker-compose -f docker-compose.cloud.yml -p aqea-digitalocean up -d
        log_success "DigitalOcean deployment started"
    fi
    
    # Deploy Linode
    if [[ $LINODE_WORKERS -gt 0 ]]; then
        log_info "🔗 Deploying to Linode..."
        
        export CLOUD_PROVIDER=linode
        export CLOUD_REGION=eu-west
        export WORKER_COUNT=$LINODE_WORKERS
        export MASTER_PORT=8082
        export DASHBOARD_PORT=8092
        
        docker-compose -f docker-compose.cloud.yml -p aqea-linode up -d
        log_success "Linode deployment started"
    fi
    
    log_success "🎉 Multi-cloud deployment completed!"
    show_deployment_status
}

# Deploy to single provider
deploy_single_provider() {
    if [[ -z "$PROVIDER" ]]; then
        log_error "Provider required for single deployment"
        log_info "Usage: $0 deploy-single --provider hetzner --workers 5"
        exit 1
    fi
    
    log_info "🚀 Deploying to $PROVIDER..."
    
    source "$PROJECT_DIR/.env.cloud"
    cd "$PROJECT_DIR"
    
    export CLOUD_PROVIDER=$PROVIDER
    export WORKER_COUNT=$TOTAL_WORKERS
    
    case $PROVIDER in
        hetzner)
            export CLOUD_REGION=nbg1
            export MASTER_PORT=8080
            ;;
        digitalocean)
            export CLOUD_REGION=fra1
            export MASTER_PORT=8081
            ;;
        linode)
            export CLOUD_REGION=eu-west
            export MASTER_PORT=8082
            ;;
        *)
            log_error "Unsupported provider: $PROVIDER"
            exit 1
            ;;
    esac
    
    docker-compose -f docker-compose.cloud.yml -p "aqea-$PROVIDER" up -d
    log_success "Deployment to $PROVIDER completed!"
}

# Show deployment status
show_deployment_status() {
    log_info "📊 Global Deployment Status"
    echo "=" * 60
    
    # Check active deployments
    ACTIVE_DEPLOYMENTS=()
    
    if docker-compose -p aqea-hetzner ps -q &>/dev/null; then
        ACTIVE_DEPLOYMENTS+=("hetzner:8080")
    fi
    
    if docker-compose -p aqea-digitalocean ps -q &>/dev/null; then
        ACTIVE_DEPLOYMENTS+=("digitalocean:8081")
    fi
    
    if docker-compose -p aqea-linode ps -q &>/dev/null; then
        ACTIVE_DEPLOYMENTS+=("linode:8082")
    fi
    
    if [[ ${#ACTIVE_DEPLOYMENTS[@]} -eq 0 ]]; then
        log_warning "No active deployments found"
        return
    fi
    
    echo "Active Deployments:"
    for deployment in "${ACTIVE_DEPLOYMENTS[@]}"; do
        provider=$(echo $deployment | cut -d: -f1)
        port=$(echo $deployment | cut -d: -f2)
        
        echo "  🌍 $provider: http://localhost:$port"
        
        # Check master health
        if curl -s "http://localhost:$port/api/health" >/dev/null 2>&1; then
            echo "    ✅ Master: Healthy"
        else
            echo "    ❌ Master: Unreachable"
        fi
    done
    
    echo ""
    echo "Global Dashboard URLs:"
    for deployment in "${ACTIVE_DEPLOYMENTS[@]}"; do
        provider=$(echo $deployment | cut -d: -f1)
        port=$(echo $deployment | cut -d: -f2)
        dashboard_port=$((port + 10))
        echo "  📊 $provider Dashboard: http://localhost:$dashboard_port"
    done
    
    # Show database status
    echo ""
    echo "📋 Database Status:"
    if [[ -f "$PROJECT_DIR/.env.cloud" ]]; then
        source "$PROJECT_DIR/.env.cloud"
        echo "  🗄️  Database: $SUPABASE_PROJECT.supabase.co"
        echo "  🔗 Connection: $(echo $SUPABASE_DATABASE_URL | sed 's/:[^:]*@/:***@/')"
    else
        echo "  ❌ No database configuration found"
    fi
}

# Cleanup all deployments
cleanup_deployments() {
    log_warning "🧹 Cleaning up all AQEA deployments..."
    
    cd "$PROJECT_DIR"
    
    # Stop all project deployments
    docker-compose -p aqea-hetzner down -v 2>/dev/null || true
    docker-compose -p aqea-digitalocean down -v 2>/dev/null || true
    docker-compose -p aqea-linode down -v 2>/dev/null || true
    
    # Clean up images
    docker system prune -f
    
    log_success "Cleanup completed"
}

# Cost estimation
estimate_costs() {
    source "$PROJECT_DIR/.env.cloud" 2>/dev/null || true
    
    cat << EOF

💰 Cost Estimation for Multi-Cloud Deployment

Configuration:
  Language: $LANGUAGE
  Total Workers: $TOTAL_WORKERS
  
Provider Distribution:
  Hetzner (60%):     $((TOTAL_WORKERS * 60 / 100)) workers × €0.015/hour = €$(echo "scale=2; $TOTAL_WORKERS * 60 / 100 * 0.015" | bc)/hour
  DigitalOcean (30%): $((TOTAL_WORKERS * 30 / 100)) workers × €0.024/hour = €$(echo "scale=2; $TOTAL_WORKERS * 30 / 100 * 0.024" | bc)/hour  
  Linode (10%):      $((TOTAL_WORKERS * 10 / 100)) workers × €0.018/hour = €$(echo "scale=2; $TOTAL_WORKERS * 10 / 100 * 0.018" | bc)/hour

Total Hourly Cost: €$(echo "scale=2; ($TOTAL_WORKERS * 60 / 100 * 0.015) + ($TOTAL_WORKERS * 30 / 100 * 0.024) + ($TOTAL_WORKERS * 10 / 100 * 0.018)" | bc)/hour

Database: Supabase (Free tier up to 10GB)
Estimated extraction time for German: 22 hours
Total project cost: ~€$(echo "scale=0; 22 * (($TOTAL_WORKERS * 60 / 100 * 0.015) + ($TOTAL_WORKERS * 30 / 100 * 0.024) + ($TOTAL_WORKERS * 10 / 100 * 0.018))" | bc)

EOF
}

# Main execution
main() {
    parse_args "$@"
    
    case $COMMAND in
        setup)
            setup_supabase
            ;;
        deploy-multi)
            deploy_multi_cloud
            ;;
        deploy-single)
            deploy_single_provider
            ;;
        status)
            show_deployment_status
            ;;
        cleanup)
            cleanup_deployments
            ;;
        estimate)
            estimate_costs
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    command -v docker >/dev/null 2>&1 || missing_deps+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing_deps+=("docker-compose")
    
    if [[ ${#missing_deps[@]} -ne 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# Pre-flight check
check_dependencies

# Run main function
main "$@" 