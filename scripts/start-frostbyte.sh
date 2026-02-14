#!/bin/bash
# Frostbyte ETL Pipeline — Production Startup Script
# Usage: ./scripts/start-frostbyte.sh [dev|prod|stop|status|logs]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    log_success "Docker is running"
}

# Wait for service to be healthy
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    log_info "Waiting for $service to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log_success "$service is ready"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "$service failed to start after $max_attempts attempts"
    return 1
}

# Start all services
start_services() {
    local mode=${1:-dev}
    
    log_info "Starting Frostbyte ETL Pipeline ($mode mode)..."
    
    check_docker
    
    # Build and start
    log_info "Building and starting services..."
    cd "$PROJECT_ROOT"
    
    if [ "$mode" == "prod" ]; then
        docker-compose -f "$COMPOSE_FILE" up -d --build
    else
        # Dev mode: build with cache, don't rebuild unless needed
        docker-compose -f "$COMPOSE_FILE" up -d
    fi
    
    # Wait for critical services
    log_info "Waiting for services to initialize..."
    sleep 5
    
    # Health checks
    local all_healthy=true
    
    if ! wait_for_service "Pipeline API" "http://localhost:8000/health" 30; then
        all_healthy=false
    fi
    
    if ! wait_for_service "Admin Dashboard" "http://localhost:5174/admin/" 20; then
        all_healthy=false
    fi
    
    echo ""
    
    if [ "$all_healthy" = true ]; then
        log_success "All services are running!"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  🚀 Frostbyte ETL Pipeline is ready!"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  Admin Dashboard: http://localhost:5174/admin/"
        echo "  Pipeline API:    http://localhost:8000"
        echo "  API Docs:        http://localhost:8000/docs"
        echo "  Health Check:    http://localhost:8000/health"
        echo ""
        echo "  Services:"
        echo "    - MinIO:      http://localhost:9000 (console: 9001)"
        echo "    - Qdrant:     http://localhost:6333"
        echo "    - PostgreSQL: localhost:5433"
        echo "    - Redis:      localhost:6379"
        echo ""
        echo "  Commands:"
        echo "    View logs:  ./scripts/start-frostbyte.sh logs"
        echo "    Stop all:   ./scripts/start-frostbyte.sh stop"
        echo "    Status:     ./scripts/start-frostbyte.sh status"
        echo ""
        
        # Test SSE endpoint
        log_info "Testing SSE stream..."
        if curl -s -N http://localhost:8000/api/v1/pipeline/stream 2>&1 | head -1 | grep -q "data:"; then
            log_success "SSE stream is active"
        else
            log_warn "SSE stream test inconclusive (may need browser test)"
        fi
        
    else
        log_error "Some services failed to start. Checking logs..."
        docker-compose -f "$COMPOSE_FILE" logs --tail=50
        exit 1
    fi
}

# Stop all services
stop_services() {
    log_info "Stopping Frostbyte services..."
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" down
    log_success "All services stopped"
}

# Show status
show_status() {
    log_info "Service Status:"
    echo ""
    
    local services=("redis" "postgres" "minio" "qdrant" "pipeline-api" "admin-dashboard")
    
    for service in "${services[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "frostbyte-$service\|$service"; then
            local status=$(docker inspect --format='{{.State.Status}}' "frostbyte-$service" 2>/dev/null || echo "unknown")
            local health=$(docker inspect --format='{{.State.Health.Status}}' "frostbyte-$service" 2>/dev/null || echo "N/A")
            
            if [ "$health" == "healthy" ]; then
                printf "  ${GREEN}✓${NC} %-20s %s (%s)\n" "$service" "$status" "$health"
            elif [ "$status" == "running" ]; then
                printf "  ${YELLOW}○${NC} %-20s %s (starting...)\n" "$service" "$status"
            else
                printf "  ${RED}✗${NC} %-20s %s\n" "$service" "$status"
            fi
        else
            printf "  ${RED}✗${NC} %-20s not running\n" "$service"
        fi
    done
    
    echo ""
    
    # Test endpoints
    log_info "Endpoint Tests:"
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Pipeline API: http://localhost:8000/health"
    else
        log_error "Pipeline API: http://localhost:8000/health (unreachable)"
    fi
    
    if curl -s http://localhost:5174/admin/ > /dev/null 2>&1; then
        log_success "Admin Dashboard: http://localhost:5174/admin/"
    else
        log_error "Admin Dashboard: http://localhost:5174/admin/ (unreachable)"
    fi
}

# Show logs
show_logs() {
    local service=$1
    cd "$PROJECT_ROOT"
    
    if [ -z "$service" ]; then
        docker-compose -f "$COMPOSE_FILE" logs -f
    else
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    fi
}

# Reset everything (DANGER: destroys data)
reset_all() {
    log_warn "This will destroy all data and volumes!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" == "yes" ]; then
        cd "$PROJECT_ROOT"
        docker-compose -f "$COMPOSE_FILE" down -v
        log_success "All data destroyed. Run './scripts/start-frostbyte.sh start' to recreate."
    else
        log_info "Reset cancelled"
    fi
}

# Main command handler
case "${1:-start}" in
    start|dev)
        start_services "dev"
        ;;
    prod)
        start_services "prod"
        ;;
    stop|down)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    reset)
        reset_all
        ;;
    restart)
        stop_services
        sleep 2
        start_services "dev"
        ;;
    help|--help|-h)
        echo "Frostbyte ETL Pipeline — Startup Script"
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  start, dev     Start all services in development mode (default)"
        echo "  prod           Start all services in production mode (rebuild)"
        echo "  stop, down     Stop all services"
        echo "  restart        Restart all services"
        echo "  status         Show service status and health"
        echo "  logs [svc]     Show logs (optionally for specific service)"
        echo "  reset          DANGER: Stop and destroy all data"
        echo "  help           Show this help"
        echo ""
        echo "Services: redis, postgres, minio, qdrant, pipeline-api, admin-dashboard"
        echo ""
        echo "Examples:"
        echo "  $0 start                    # Start everything"
        echo "  $0 logs pipeline-api        # View pipeline API logs"
        echo "  $0 status                   # Check service health"
        echo ""
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
