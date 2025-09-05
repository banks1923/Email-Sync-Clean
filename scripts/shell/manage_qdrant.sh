#!/bin/bash
# Qdrant vector database management script
# Usage: ./scripts/shell/manage_qdrant.sh [start|stop|status|restart]

set -e

# Source environment variables
if [ -f .envrc ]; then
  source .envrc
fi

QDRANT_PORT=6333
QDRANT_BIN="$HOME/bin/qdrant"
QDRANT_LOG="${QDRANT__LOG__PATH:-./logs/qdrant.log}"

# Ensure logs directory exists
mkdir -p "$(dirname "$QDRANT_LOG")"

check_status() {
    if lsof -i :$QDRANT_PORT > /dev/null 2>&1; then
        echo "✅ Qdrant is running on port $QDRANT_PORT"
        return 0
    else
        echo "❌ Qdrant is not running"
        return 1
    fi
}

start_qdrant() {
    if check_status > /dev/null 2>&1; then
        echo "✅ Qdrant already running on port $QDRANT_PORT"
        return 0
    fi
    
    echo "🚀 Starting Qdrant vector database..."
    nohup "$QDRANT_BIN" > "$QDRANT_LOG" 2>&1 &
    
    # Wait for startup
    for i in {1..10}; do
        if lsof -i :$QDRANT_PORT > /dev/null 2>&1; then
            echo "✅ Qdrant started successfully"
            echo "📝 Logs: $QDRANT_LOG"
            return 0
        fi
        sleep 0.5
    done
    
    echo "⚠️  Failed to start Qdrant. Check logs: $QDRANT_LOG"
    return 1
}

stop_qdrant() {
    if ! check_status > /dev/null 2>&1; then
        echo "❌ Qdrant is not running"
        return 0
    fi
    
    echo "🛑 Stopping Qdrant..."
    pkill -f "$QDRANT_BIN" || true
    sleep 1
    
    if check_status > /dev/null 2>&1; then
        echo "⚠️  Failed to stop Qdrant gracefully, trying force kill..."
        pkill -9 -f "$QDRANT_BIN" || true
        sleep 1
    fi
    
    if ! check_status > /dev/null 2>&1; then
        echo "✅ Qdrant stopped"
    else
        echo "❌ Failed to stop Qdrant"
        return 1
    fi
}

restart_qdrant() {
    stop_qdrant
    sleep 1
    start_qdrant
}

# Main command handling
case "${1:-status}" in
    start)
        start_qdrant
        ;;
    stop)
        stop_qdrant
        ;;
    restart)
        restart_qdrant
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        echo "  start   - Start Qdrant if not running"
        echo "  stop    - Stop Qdrant if running"
        echo "  status  - Check if Qdrant is running"
        echo "  restart - Restart Qdrant"
        exit 1
        ;;
esac