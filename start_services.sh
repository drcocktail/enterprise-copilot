#!/bin/bash
echo "🚀 Starting Nexus Microservices..."

cd backend

# 1. Gateway
echo "Starting Gateway (Port 8000)..."
python3 svc_gateway.py > ../logs/gateway.log 2>&1 &
echo $! > ../logs/gateway.pid

# 2. Ingestion
echo "Starting Ingestion Service (Port 8001)..."
python3 svc_ingestion.py > ../logs/ingestion.log 2>&1 &
echo $! > ../logs/ingestion.pid

# 3. Chat
echo "Starting Chat Service (Port 8002)..."
python3 svc_chat.py > ../logs/chat.log 2>&1 &
echo $! > ../logs/chat.pid

# 4. Core
echo "Starting Core Service (Port 8003)..."
python3 svc_core.py > ../logs/core.log 2>&1 &
echo $! > ../logs/core.pid

cd ..

echo "🎨 Starting Frontend..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
cd ..

echo "✅ All services started! Check logs/ for output."
echo "Gateway: http://localhost:8000"
echo "Frontend: http://localhost:3000"
