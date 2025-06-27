#!/bin/bash

# LLM Intelligence Server Launcher
# Handles dependencies and error checking

echo "🚀 Starting LLM Intelligence Server..."

# Check if port is available
PORT=${1:-8055}

if lsof -i :$PORT > /dev/null 2>&1; then
    echo "❌ Error: Port $PORT is already in use"
    echo "💡 Try a different port: ./start_server.sh 8056"
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

echo "✅ Port $PORT is available"
echo "✅ Python3 found: $(python3 --version)"

# Start the server
echo "🔄 Starting server on port $PORT..."
echo "📊 Dashboard will be available at: http://localhost:$PORT/"
echo "🔗 API endpoints at: http://localhost:$PORT/rankings"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"

python3 test_server.py --port $PORT