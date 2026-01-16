#!/bin/bash

echo "🛑 Stopping DevOps Copilot V3 services..."

# Kill Python backend processes
pkill -f "uvicorn main:app"
pkill -f "python3 -m uvicorn"

# Kill Node frontend processes
pkill -f "vite"
pkill -f "npm run dev"

echo "✅ All services stopped."
