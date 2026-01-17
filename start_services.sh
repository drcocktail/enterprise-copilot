#!/bin/bash

# Configuration
# Start the Modular Monolith
# Use nohup to keep it running? Or just run it.

echo "🚀 Starting DevOps Copilot V3 (Modular Monolith)..."
echo "   - Single Process Architecture"
echo "   - Port: 8000"

# Kill generic python processes that might be lingering (Use with caution)
# pkill -f "uvicorn backend.server:app" 

# Start Backend
cd backend
# Use nohup to run in background or just run directly
# Assuming this is for user to run in terminal
uvicorn server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "✅ Backend started (PID: $BACKEND_PID)"
echo "   - Health Check: http://localhost:8000/api/health"
echo "   - Docs: http://localhost:8000/docs"

# Start Frontend (Optional, usually run separately via npm run dev)
# cd frontend
# npm run dev &
# FRONTEND_PID=$!
# echo "✅ Frontend started (PID: $FRONTEND_PID)"

wait $BACKEND_PID
