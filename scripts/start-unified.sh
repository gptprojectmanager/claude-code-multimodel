#!/bin/bash

# LiteLLM Unified Startup Script
# ==============================

echo "🚀 Starting LiteLLM Unified Proxy..."

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration files
ENV_FILE="$PROJECT_DIR/config/unified.env"
CONFIG_FILE="$PROJECT_DIR/config/litellm-unified.yaml"

# Check if configuration files exist
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found at $ENV_FILE"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Configuration file not found at $CONFIG_FILE"
    exit 1
fi

# Load environment variables
echo "📝 Loading environment variables..."
set -a
source "$ENV_FILE"
set +a

# Validate required environment variables
echo "🔍 Validating configuration..."

# Check virtual environment
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "❌ Error: Virtual environment not found. Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$PROJECT_DIR/venv/bin/activate"

# Check if litellm is installed
if ! command -v litellm &> /dev/null; then
    echo "❌ Error: LiteLLM not found. Please install: pip install 'litellm[proxy]'"
    exit 1
fi

# Show available providers based on configuration
echo "🌐 Available providers:"
if [ -n "$GITHUB_TOKEN" ]; then
    echo "  ✅ GitHub Models (token configured)"
else
    echo "  ⚠️  GitHub Models (token missing)"
fi

if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "  ✅ Vertex AI (project: $GOOGLE_CLOUD_PROJECT)"
else
    echo "  ⚠️  Vertex AI (project not configured)"
fi

if [ -n "$OPENROUTER_API_KEY" ] && [ "$OPENROUTER_API_KEY" != "your-openrouter-api-key-here" ]; then
    echo "  ✅ OpenRouter (key configured)"
else
    echo "  ⚠️  OpenRouter (key missing or placeholder)"
fi

# Start LiteLLM
PORT=${LITELLM_PORT:-8082}
echo "🎯 Starting LiteLLM on port $PORT..."
echo "📊 Configuration: $CONFIG_FILE"
echo "🔗 Health check: http://localhost:$PORT/health"
echo "📚 API docs: http://localhost:$PORT/docs"
echo ""
echo "Press Ctrl+C to stop..."

litellm --config "$CONFIG_FILE" --port "$PORT"