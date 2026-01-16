#!/bin/bash

# DevOps Copilot V3 - Startup Script

echo "🚀 DevOps Copilot V3 Setup & Startup"
echo "====================================="

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it first."
    exit 1
fi

echo "📦 Checking Ollama models..."
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text

echo "🐍 Setting up Backend..."
cd backend
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
# Ensure proper tree-sitter build if needed
# python build_treesitter.py (if we had a build script)

echo "⚛️  Setting up Frontend..."
cd ../frontend
npm install

echo "🚀 Starting Services..."

# Start Backend
cd ../backend
echo "Starting FastAPI Backend..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start Frontend
cd ../frontend
echo "Starting React Frontend..."
npm run dev -- --host &
FRONTEND_PID=$!

echo "==========================================="
echo "🎉 DevOps Copilot V3 is running!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "==========================================="

wait $BACKEND_PID $FRONTEND_PID
