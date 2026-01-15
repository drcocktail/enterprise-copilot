#!/bin/bash

# Stop all Enterprise Copilot services

echo "🛑 Stopping Enterprise Copilot services..."

# Stop backend
if [ -f ".backend.pid" ]; then
    echo "Stopping backend..."
    kill $(cat .backend.pid) 2>/dev/null || echo "Backend already stopped"
    rm .backend.pid
fi

# Stop frontend
if [ -f ".frontend.pid" ]; then
    echo "Stopping frontend..."
    kill $(cat .frontend.pid) 2>/dev/null || echo "Frontend already stopped"
    rm .frontend.pid
fi

# Stop Ollama if we started it
if [ -f ".ollama.pid" ]; then
    echo "Stopping Ollama..."
    kill $(cat .ollama.pid) 2>/dev/null || echo "Ollama already stopped"
    rm .ollama.pid
fi

# Kill any remaining processes on the ports
echo "Cleaning up ports..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

echo "✅ All services stopped"
