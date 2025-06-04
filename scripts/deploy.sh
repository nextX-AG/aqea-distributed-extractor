#!/bin/bash
# AQEA Distributed Extractor Deployment Script
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_WORKERS=3
DEFAULT_LANGUAGE="de"
DEFAULT_SOURCE="wiktionary"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
AQEA Distributed Extractor Deployment Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    deploy          Deploy the distributed extractor system
    start           Start existing deployment
    stop            Stop the deployment
    restart         Restart the deployment
    scale           Scale worker nodes
    status          Show deployment status
    logs            Show logs
    cleanup         Clean up all resources
    test            Run test extraction
    estimate        Show cost estimation

Options:
    -w, --workers NUM       Number of worker nodes (default: $DEFAULT_WORKERS)
    -l, --language LANG     Language to extract (default: $DEFAULT_LANGUAGE)
    -s, --source SOURCE     Data source (default: $DEFAULT_SOURCE)
    -e, --env ENV          Environment (development/production, default: development)
    -h, --help             Show this help message

Examples:
    $0 deploy --workers 5 --language en
    $0 scale --workers 10
    $0 status
    $0 logs --follow
    $0 estimate --language de --workers 5

EOF
}

# Parse arguments
parse_args() {
    COMMAND=""
    WORKERS=$DEFAULT_WORKERS
    LANGUAGE=$DEFAULT_LANGUAGE
    SOURCE=$DEFAULT_SOURCE
    ENVIRONMENT="development"
    FOLLOW_LOGS=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            deploy|start|stop|restart|scale|status|logs|cleanup|test|estimate)
                COMMAND=$1
                shift
                ;;
            -w|--workers)
                WORKERS="$2"
                shift 2
                ;;
            -l|--language)
                LANGUAGE="$2"
                shift 2
                ;;
            -s|--source)
                SOURCE="$2"
                shift 2
                ;;
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --follow)
                FOLLOW_LOGS=true
                shift
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    log_success "All prerequisites are satisfied"
}

# Deploy function
deploy() {
    log_info "Deploying AQEA Distributed Extractor..."
    
    cd "$PROJECT_DIR"
    
    # Create necessary directories
    mkdir -p logs data

    # Build images
    log_info "Building Docker images..."
    docker-compose build

    # Start database first
    log_info "Starting database..."
    docker-compose up -d database
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    timeout 60 bash -c 'until docker-compose exec -T database pg_isready -U aqea -d aqea; do sleep 2; done'
    
    # Start master
    log_info "Starting master coordinator..."
    docker-compose up -d master
    
    # Wait for master to be ready
    log_info "Waiting for master to be ready..."
    timeout 60 bash -c 'until curl -s http://localhost:8080/api/health >/dev/null; do sleep 2; done'
    
    # Scale workers
    log_info "Starting $WORKERS worker nodes..."
    docker-compose up -d --scale worker=$WORKERS worker

    log_success "Deployment completed successfully!"
    show_status
}

# Start function
start() {
    log_info "Starting AQEA Distributed Extractor..."
    cd "$PROJECT_DIR"
    docker-compose up -d --scale worker=$WORKERS
    log_success "System started"
}

# Stop function
stop() {
    log_info "Stopping AQEA Distributed Extractor..."
    cd "$PROJECT_DIR"
    docker-compose down
    log_success "System stopped"
}

# Restart function
restart() {
    log_info "Restarting AQEA Distributed Extractor..."
    stop
    sleep 5
    start
}

# Scale function
scale() {
    log_info "Scaling workers to $WORKERS nodes..."
    cd "$PROJECT_DIR"
    docker-compose up -d --scale worker=$WORKERS worker
    log_success "Scaled to $WORKERS workers"
}

# Status function
show_status() {
    log_info "System Status:"
    cd "$PROJECT_DIR"
    
    echo "Docker Compose Services:"
    docker-compose ps
    
    echo -e "\nMaster Status:"
    if curl -s http://localhost:8080/api/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Master is healthy${NC}"
        curl -s http://localhost:8080/api/status | python -m json.tool 2>/dev/null || echo "Status API not available"
    else
        echo -e "${RED}✗ Master is not responding${NC}"
    fi
    
    echo -e "\nResource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# Logs function
show_logs() {
    cd "$PROJECT_DIR"
    if [[ "$FOLLOW_LOGS" == true ]]; then
        docker-compose logs -f
    else
        docker-compose logs --tail=100
    fi
}

# Cleanup function
cleanup() {
    log_warning "This will remove all containers, volumes, and data. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        cd "$PROJECT_DIR"
        docker-compose down -v --remove-orphans
        docker system prune -f
        rm -rf logs/* data/*
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

# Test function
test_extraction() {
    log_info "Running test extraction for $LANGUAGE from $SOURCE..."
    cd "$PROJECT_DIR"
    
    # Start a minimal test setup
    docker-compose up -d database master
    
    # Wait for services
    sleep 10
    
    # Run test command
    docker-compose run --rm worker python -m src.main test_source \
        --language "$LANGUAGE" \
        --source "$SOURCE" \
        --limit 10
    
    log_success "Test extraction completed"
}

# Estimate function
estimate_costs() {
    log_info "Estimating costs for $LANGUAGE with $WORKERS workers..."
    cd "$PROJECT_DIR"
    
    docker-compose run --rm worker python -m src.main estimate \
        --language "$LANGUAGE" \
        --workers "$WORKERS" \
        --provider hetzner
}

# Main execution
main() {
    parse_args "$@"
    
    case $COMMAND in
        deploy)
            check_prerequisites
            deploy
            ;;
        start)
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        scale)
            scale
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        cleanup)
            cleanup
            ;;
        test)
            test_extraction
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

# Run main function
main "$@" 