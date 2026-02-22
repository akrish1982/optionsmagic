#!/bin/bash
# Approval Worker Manager
# Manages the background approval worker process

set -euo pipefail

BASE_DIR="/home/openclaw/.openclaw/workspace/optionsmagic"
POETRY="$HOME/.local/bin/poetry"
PIDFILE="$BASE_DIR/trade_automation/worker.pid"
LOGFILE="$BASE_DIR/logs/approval_worker.log"

cd "$BASE_DIR"

usage() {
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
}

check_running() {
    if [ -f "$PIDFILE" ]; then
        pid=$(cat "$PIDFILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
}

start_worker() {
    if check_running; then
        echo "Approval worker is already running (PID: $(cat "$PIDFILE"))"
        return 1
    fi

    echo "Starting approval worker..."
    mkdir -p "$BASE_DIR/logs"

    # Start in background with nohup
    nohup "$POETRY" run python trade_automation/approval_worker.py >> "$LOGFILE" 2>&1 &
    pid=$!

    # Save PID
    echo "$pid" > "$PIDFILE"

    # Wait a moment to verify it started
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        echo "✅ Approval worker started (PID: $pid)"
        echo "Logs: $LOGFILE"
    else
        echo "❌ Failed to start approval worker"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_worker() {
    if ! check_running; then
        echo "Approval worker is not running"
        rm -f "$PIDFILE"
        return 0
    fi

    pid=$(cat "$PIDFILE")
    echo "Stopping approval worker (PID: $pid)..."

    # Try graceful shutdown first
    kill "$pid" 2>/dev/null || true
    sleep 2

    # Force kill if still running
    if kill -0 "$pid" 2>/dev/null; then
        echo "Force killing worker..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PIDFILE"
    echo "✅ Approval worker stopped"
}

status_worker() {
    if check_running; then
        pid=$(cat "$PIDFILE")
        echo "✅ Approval worker is running (PID: $pid)"
        echo "Log file: $LOGFILE"
        echo "Recent log entries:"
        tail -5 "$LOGFILE" 2>/dev/null || echo "(no log entries yet)"
    else
        echo "❌ Approval worker is not running"
        rm -f "$PIDFILE"
    fi
}

show_logs() {
    if [ -f "$LOGFILE" ]; then
        tail -f "$LOGFILE"
    else
        echo "No log file found at $LOGFILE"
    fi
}

# Main
case "${1:-}" in
    start)
        start_worker
        ;;
    stop)
        stop_worker
        ;;
    restart)
        stop_worker
        sleep 1
        start_worker
        ;;
    status)
        status_worker
        ;;
    logs)
        show_logs
        ;;
    *)
        usage
        ;;
esac
