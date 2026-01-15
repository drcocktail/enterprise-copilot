#!/bin/bash

# Enterprise Copilot - Complete Setup and Startup Script
# This script sets up and starts both backend and frontend

set -e  # Exit on error

echo "🚀 Enterprise Copilot Setup & Startup"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is installed
echo "📦 Checking prerequisites..."
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama is not installed${NC}"
    echo "Please install Ollama:"
    echo "  macOS: brew install ollama"
    echo "  Linux: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi
echo -e "${GREEN}✅ Ollama is installed${NC}"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama is not running. Starting Ollama...${NC}"
    ollama serve &
    OLLAMA_PID=$!
    echo "Waiting for Ollama to start..."
    sleep 5
else
    echo -e "${GREEN}✅ Ollama is running${NC}"
fi

# Pull required models
echo ""
echo "📥 Checking Ollama models..."
if ! ollama list | grep -q "llama3.2"; then
    echo "Pulling llama3.2 model..."
    ollama pull llama3.2
else
    echo -e "${GREEN}✅ llama3.2 model is available${NC}"
fi

if ! ollama list | grep -q "nomic-embed-text"; then
    echo "Pulling nomic-embed-text model..."
    ollama pull nomic-embed-text
else
    echo -e "${GREEN}✅ nomic-embed-text model is available${NC}"
fi

# Setup Backend
echo ""
echo "🐍 Setting up Backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
fi

echo -e "${GREEN}✅ Backend setup complete${NC}"

# Setup Frontend
echo ""
echo "⚛️  Setting up Frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install --silent
else
    echo -e "${GREEN}✅ Node modules already installed${NC}"
fi

echo -e "${GREEN}✅ Frontend setup complete${NC}"

# Start Backend
echo ""
echo "🚀 Starting Backend Server..."
cd ../backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
sleep 5

# Check backend health
if curl -s http://localhost:8000/api/health &> /dev/null; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Backend health check failed, but continuing...${NC}"
fi

# Start Frontend
echo ""
echo "🚀 Starting Frontend Server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "   Frontend UI: http://localhost:3000"

# Instructions
echo ""
echo "==========================================="
echo -e "${GREEN}🎉 Enterprise Copilot is now running!${NC}"
echo "==========================================="
echo ""
echo "📍 Access Points:"
echo "   • Frontend:  http://localhost:3000"
echo "   • Backend:   http://localhost:8000"
echo "   • API Docs:  http://localhost:8000/docs"
echo ""
echo "🎭 Available Personas:"
echo "   • C-Suite Executive (Financial data)"
echo "   • HR Director (Employee data)"  
echo "   • DevOps Engineer (Code access)"
echo ""
echo "📚 Next Steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Try switching between personas"
echo "   3. Ask questions relevant to each role"
echo "   4. View the live audit log panel"
echo ""
echo "💡 To ingest documents:"
echo "   curl -X POST http://localhost:8000/api/ingest/documents \\"
echo "     -H 'x-iam-role: CHIEF_STRATEGY_OFFICER'"
echo ""
echo "🛑 To stop all services:"
echo "   Press Ctrl+C or run: ./stop.sh"
echo ""

# Save PIDs for cleanup
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid
if [ ! -z "$OLLAMA_PID" ]; then
    echo "$OLLAMA_PID" > .ollama.pid
fi

# Wait for Ctrl+C
trap cleanup INT

cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    
    if [ -f ".backend.pid" ]; then
        kill $(cat .backend.pid) 2>/dev/null || true
        rm .backend.pid
    fi
    
    if [ -f ".frontend.pid" ]; then
        kill $(cat .frontend.pid) 2>/dev/null || true
        rm .frontend.pid
    fi
    
    if [ -f ".ollama.pid" ]; then
        kill $(cat .ollama.pid) 2>/dev/null || true
        rm .ollama.pid
    fi
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Keep script running
echo "Press Ctrl+C to stop all services..."
wait
