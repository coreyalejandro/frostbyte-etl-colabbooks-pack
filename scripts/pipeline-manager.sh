#!/bin/bash
# Frostbyte Pipeline API Manager
# Robust auto-start with retry logic, health checks, and clear error messaging
# Usage: ./scripts/pipeline-manager.sh [start|stop|restart|status|logs]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/frostbyte-pipeline.pid"
LOG_FILE="/tmp/frostbyte-pipeline.log"
MAX_RETRIES=5
RETRY_DELAY=3
API_URL="http://localhost:8000/health"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Check if infrastructure is running
check_infrastructure() {
    local all_good=true
    
    log_step "Checking infrastructure..."
    
    # Check Redis
    if ! redis-cli ping > /dev/null 2>&1; then
        log_error "Redis is not running on port 6379"
        log_info "Fix: docker-compose up -d redis"
        all_good=false
    else
        log_success "Redis is running"
    fi
    
    # Check PostgreSQL
    if ! pg_isready -h localhost -p 5433 -U frostbyte > /dev/null 2>&1; then
        log_error "PostgreSQL is not running on port 5433"
        log_info "Fix: docker-compose up -d postgres"
        all_good=false
    else
        log_success "PostgreSQL is running"
    fi
    
    # Check MinIO
    if ! curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log_error "MinIO is not running on port 9000"
        log_info "Fix: docker-compose up -d minio"
        all_good=false
    else
        log_success "MinIO is running"
    fi
    
    # Check Qdrant
    if ! curl -s http://localhost:6333/readyz > /dev/null 2>&1; then
        log_error "Qdrant is not running on port 6333"
        log_info "Fix: docker-compose up -d qdrant"
        all_good=false
    else
        log_success "Qdrant is running"
    fi
    
    if [ "$all_good" = false ]; then
        log_error "Infrastructure not ready. Cannot start Pipeline API."
        if ! docker info > /dev/null 2>&1; then
            log_info "Docker daemon is not running. Start Docker Desktop (or the Docker service), then run:"
        else
            log_info "From project root run:"
        fi
        log_info "  cd $PROJECT_ROOT && docker-compose up -d"
        exit 1
    fi
    
    log_success "All infrastructure services are running"
}

# Wait for API to be ready with timeout
wait_for_api() {
    local timeout=${1:-30}
    local attempt=1
    
    log_step "Waiting for Pipeline API to be ready (timeout: ${timeout}s)..."
    
    while [ $attempt -le $timeout ]; do
        if curl -s "$API_URL" > /dev/null 2>&1; then
            log_success "Pipeline API is ready!"
            return 0
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            echo -n "[$attempt/${timeout}] "
        else
            echo -n "."
        fi
        
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo ""
    log_error "Pipeline API failed to start within ${timeout} seconds"
    return 1
}

# Start the Pipeline API with retry logic
start_pipeline() {
    local attempt=1
    
    # Check if already running
    if is_running; then
        log_warn "Pipeline API is already running (PID: $(cat $PID_FILE))"
        if wait_for_api 5; then
            log_success "Pipeline API is healthy"
            return 0
        else
            log_warn "Existing process not responding, restarting..."
            stop_pipeline
        fi
    fi
    
    # Check infrastructure first
    check_infrastructure
    
    log_step "Starting Pipeline API (attempt $attempt/$MAX_RETRIES)..."
    
    while [ $attempt -le $MAX_RETRIES ]; do
        # Clear old log
        > "$LOG_FILE"
        
        # Set environment variables
        export FROSTBYTE_AUTH_BYPASS=true
        export REDIS_URL=redis://localhost:6379/0
        export FROSTBYTE_REDIS_URL=redis://localhost:6379/0
        export POSTGRES_URL=postgresql+asyncpg://frostbyte:frostbyte@localhost:5433/frostbyte
        export MINIO_ENDPOINT=http://localhost:9000
        export MINIO_ACCESS_KEY=minioadmin
        export MINIO_SECRET_KEY=minioadmin
        export QDRANT_URL=http://localhost:6333
        export CORS_ORIGINS="http://localhost:5174,http://localhost:5175,http://localhost:3000"
        export PYTHONUNBUFFERED=1
        
        # Start the API in background
        cd "$PROJECT_ROOT/pipeline"
        nohup uvicorn pipeline.main:app --host 0.0.0.0 --port 8000 --reload --log-level info > "$LOG_FILE" 2>&1 &
        local pid=$!
        
        # Save PID
        echo $pid > "$PID_FILE"
        log_info "Started with PID: $pid"
        
        # Wait for it to be ready
        if wait_for_api 30; then
            log_success "✅ Pipeline API started successfully!"
            log_info "API URL: http://localhost:8000"
            log_info "Docs: http://localhost:8000/docs"
            log_info "Log file: $LOG_FILE"
            return 0
        fi
        
        # Failed to start - check why
        log_error "Attempt $attempt failed"
        
        if [ $attempt -lt $MAX_RETRIES ]; then
            log_warn "Retrying in ${RETRY_DELAY} seconds..."
            sleep $RETRY_DELAY
            
            # Kill any existing process
            if kill -0 $pid 2>/dev/null; then
                kill $pid 2>/dev/null || true
                sleep 1
            fi
            
            attempt=$((attempt + 1))
            log_step "Retry attempt $attempt/$MAX_RETRIES..."
        else
            log_error "❌ Failed to start Pipeline API after $MAX_RETRIES attempts"
            show_diagnostics
            return 1
        fi
    done
}

# Show diagnostic information
show_diagnostics() {
    echo ""
    log_step "Diagnostic Information:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f "$LOG_FILE" ]; then
        log_info "Last 50 lines of log:"
        echo "---"
        tail -50 "$LOG_FILE" | sed 's/^/  /'
        echo "---"
    fi
    
    echo ""
    log_info "Port 8000 status:"
    lsof -i :8000 2>/dev/null || echo "  No process on port 8000"
    
    echo ""
    log_info "Python/uvicorn availability:"
    which python3 && python3 --version
    which uvicorn && uvicorn --version
    
    echo ""
    log_info "Common fixes:"
    echo "  1. Check if port 8000 is in use: lsof -i :8000"
    echo "  2. Kill existing process: kill -9 \$(lsof -t -i:8000)"
    echo "  3. Check dependencies: pip install -e ./pipeline"
    echo "  4. View full log: tail -f $LOG_FILE"
    echo ""
}

# Check if Pipeline API is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Stop the Pipeline API
stop_pipeline() {
    log_step "Stopping Pipeline API..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "Force killing process $pid..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            
            log_success "Pipeline API stopped"
        else
            log_warn "Process not running"
        fi
        
        rm -f "$PID_FILE"
    else
        log_warn "No PID file found"
    fi
    
    # Clean up any remaining uvicorn processes on port 8000
    local remaining=$(lsof -t -i:8000 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        log_warn "Killing remaining processes on port 8000: $remaining"
        kill -9 $remaining 2>/dev/null || true
    fi
}

# Show status
show_status() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Frostbyte Pipeline Manager Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Infrastructure
    log_step "Infrastructure Services:"
    
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis (6379) - Running"
    else
        log_error "Redis (6379) - Down"
    fi
    
    if pg_isready -h localhost -p 5433 -U frostbyte > /dev/null 2>&1; then
        log_success "PostgreSQL (5433) - Running"
    else
        log_error "PostgreSQL (5433) - Down"
    fi
    
    if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log_success "MinIO (9000) - Running"
    else
        log_error "MinIO (9000) - Down"
    fi
    
    if curl -s http://localhost:6333/readyz > /dev/null 2>&1; then
        log_success "Qdrant (6333) - Running"
    else
        log_error "Qdrant (6333) - Down"
    fi
    
    echo ""
    log_step "Pipeline API:"
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Pipeline API (8000) - Running & Healthy"
        local health=$(curl -s http://localhost:8000/health)
        log_info "Health: $health"
    elif is_running; then
        log_warn "Pipeline API (8000) - Process exists but not responding"
        log_info "PID: $(cat $PID_FILE)"
    else
        log_error "Pipeline API (8000) - Not running"
    fi
    
    echo ""
    log_step "SSE Stream Test:"
    if timeout 2 curl -s -N http://localhost:8000/api/v1/pipeline/stream 2>/dev/null | head -1 | grep -q "data:"; then
        log_success "SSE stream is active"
    else
        log_error "SSE stream is not available"
    fi
    
    echo ""
}

# Show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        log_info "Showing logs (Ctrl+C to exit):"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        tail -f "$LOG_FILE"
    else
        log_error "No log file found at $LOG_FILE"
    fi
}

# Auto-start (used by frontend integration)
auto_start() {
    # Quick check if already running
    if curl -s "$API_URL" > /dev/null 2>&1; then
        exit 0  # Already running, all good
    fi
    
    # Try to start
    start_pipeline
}

# Main command handler
case "${1:-start}" in
    start)
        start_pipeline
        ;;
    auto)
        auto_start
        ;;
    stop)
        stop_pipeline
        ;;
    restart)
        stop_pipeline
        sleep 2
        start_pipeline
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    diagnose|debug)
        show_diagnostics
        ;;
    *)
        echo "Frostbyte Pipeline Manager"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start      Start Pipeline API with retry logic"
        echo "  auto       Auto-start if not running (for scripts)"
        echo "  stop       Stop Pipeline API"
        echo "  restart    Restart Pipeline API"
        echo "  status     Show status of all services"
        echo "  logs       Show and follow logs"
        echo "  diagnose   Show diagnostic information"
        echo ""
        echo "Examples:"
        echo "  $0 start       # Start with full output"
        echo "  $0 auto        # Silent auto-start"
        echo "  $0 status      # Check everything"
        echo ""
        ;;
esac
