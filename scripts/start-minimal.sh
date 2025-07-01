#!/bin/bash

# Minimal LiteLLM startup script for testing
set -e

echo "🚀 Starting Minimal LiteLLM Proxy..."

# Load environment variables
if [ -f "config/unified.env" ]; then
    echo "📋 Loading environment variables..."
    set -a
    source config/unified.env
    set +a
else
    echo "⚠️  No unified.env file found - using defaults"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found! Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check LiteLLM installation
if ! command -v litellm &> /dev/null; then
    echo "❌ LiteLLM not found! Installing..."
    pip install litellm[proxy]
fi

# Configuration file
CONFIG_FILE="config/litellm-minimal.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Configuration file not found: $CONFIG_FILE"
    exit 1
fi

echo "📁 Using configuration: $CONFIG_FILE"

# Port configuration
PORT=${LITELLM_PORT:-8083}

echo "🌐 Starting LiteLLM proxy on port $PORT..."
echo "📊 Health check will be available at: http://localhost:$PORT/health"
echo "🔍 API documentation at: http://localhost:$PORT/docs"

# Start LiteLLM with minimal configuration
litellm --config "$CONFIG_FILE" --port "$PORT" --debug