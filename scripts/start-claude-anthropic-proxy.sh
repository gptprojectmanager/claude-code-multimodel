#!/bin/bash

# Claude Anthropic API Proxy Startup Script
# Based on claude-code-proxy design

echo "🚀 Starting Claude Anthropic API Proxy..."

# Load environment variables
if [ -f "config/unified.env" ]; then
    echo "📄 Loading unified.env configuration..."
    set -a
    source config/unified.env
    set +a
fi

# Check required dependencies
echo "🔍 Checking dependencies..."
python3 -c "import fastapi, litellm, uvicorn, pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip install fastapi uvicorn litellm python-dotenv pydantic
fi

# Check provider configuration
echo "🔧 Configuration check:"
echo "   Preferred Provider: ${PREFERRED_PROVIDER:-openrouter}"
echo "   OpenRouter API Key: ${OPENROUTER_API_KEY:+✅ Set}"
echo "   GitHub Token: ${GITHUB_TOKEN:+✅ Set}"
echo "   Google Cloud Project: ${GOOGLE_CLOUD_PROJECT:+✅ Set}"
echo "   OpenAI API Key: ${OPENAI_API_KEY:+✅ Set}"

# Set default port
PORT=${PORT:-8080}

echo "🌟 Starting proxy server on port $PORT..."
echo "📋 Endpoints:"
echo "   • Anthropic API: http://localhost:$PORT/v1/messages"
echo "   • Health Check: http://localhost:$PORT/health"
echo "   • Service Info: http://localhost:$PORT/"

# Start the server
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python3 proxy/claude_anthropic_proxy.py

echo "🔄 Claude Anthropic API Proxy stopped."