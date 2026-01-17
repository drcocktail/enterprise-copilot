#!/bin/bash
echo "🛑 Stopping Nexus Microservices..."

# Kill PIDs if files exist
if [ -d "logs" ]; then
    for pidfile in logs/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            echo "Killing PID $pid ($pidfile)..."
            kill $pid 2>/dev/null || true
            rm "$pidfile"
        fi
    done
fi

# Force kill fallbacks
echo "Ensuring all python/node processes are dead..."
pkill -f "svc_gateway.py" || true
pkill -f "svc_ingestion.py" || true
pkill -f "svc_chat.py" || true
pkill -f "svc_core.py" || true
pkill -f "vite" || true

echo "✅ All services stopped."
