#!/bin/bash
# HTTP endpoint wrapper for pipeline auto-start
# Usage: ./scripts/auto-start-http.sh [port]
# This creates a simple HTTP endpoint that triggers auto-start

PORT=${1:-9999}
PID_FILE="/tmp/frostbyte-autostart-http.pid"

start_server() {
    echo "Starting auto-start HTTP endpoint on port $PORT..."
    
    # Simple HTTP server using nc (netcat)
    while true; do
        {
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: application/json"
            echo "Access-Control-Allow-Origin: *"
            echo ""
            
            # Check if pipeline is running
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo '{"status": "running", "message": "Pipeline API is already running"}'
            else
                # Try to start it
                SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                if "$SCRIPT_DIR/pipeline-manager.sh" auto > /dev/null 2>&1; then
                    sleep 2
                    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                        echo '{"status": "started", "message": "Pipeline API started successfully"}'
                    else
                        echo '{"status": "error", "message": "Failed to start Pipeline API"}'
                    fi
                else
                    echo '{"status": "error", "message": "Auto-start script failed"}'
                fi
            fi
        } | nc -l "$PORT" -q 1
    done &
    
    echo $! > "$PID_FILE"
    echo "Auto-start HTTP endpoint running on http://localhost:$PORT"
    echo "Test with: curl http://localhost:$PORT"
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null || true
        rm -f "$PID_FILE"
        echo "Auto-start HTTP endpoint stopped"
    fi
}

case "${1:-start}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    *)
        echo "Usage: $0 [start|stop] [port]"
        echo ""
        echo "This creates an HTTP endpoint that frontend can call to auto-start Pipeline API"
        echo ""
        echo "Example:"
        echo "  $0 start 9999    # Start on port 9999"
        echo "  curl http://localhost:9999  # Trigger auto-start"
        ;;
esac
