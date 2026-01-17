#!/bin/bash
echo "🚀 Starting Nexus Microservices with Auto-Reload..."

cd backend

# 1. Gateway
echo "Starting Gateway (Port 8000)..."
nohup uvicorn svc_gateway:app --reload --port 8000 --host 0.0.0.0 > ../logs/gateway.log 2>&1 &
echo $! > ../logs/gateway.pid

# 2. Ingestion
echo "Starting Ingestion Service (Port 8001)..."
nohup uvicorn svc_ingestion:app --reload --port 8001 --host 0.0.0.0 > ../logs/ingestion.log 2>&1 &
echo $! > ../logs/ingestion.pid

# 3. Chat
echo "Starting Chat Service (Port 8002)..."
nohup uvicorn svc_chat:app --reload --port 8002 --host 0.0.0.0 > ../logs/chat.log 2>&1 &
echo $! > ../logs/chat.pid

# 4. Core
echo "Starting Core Service (Port 8003)..."
nohup uvicorn svc_core:app --reload --port 8003 --host 0.0.0.0 > ../logs/core.log 2>&1 &
echo $! > ../logs/core.pid

cd ..

echo "🎨 Starting Frontend..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
cd ..

echo "✅ All services started in background with RELOAD enabled!"
echo "Gateway: http://localhost:8000"
echo "Frontend: http://localhost:3000"
