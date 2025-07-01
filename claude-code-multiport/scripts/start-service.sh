#!/bin/bash
# Start individual multi-port service
# Usage: ./start-service.sh <service_name> <port> <config_file>

set -e

SERVICE_NAME=$1
PORT=$2
CONFIG_FILE=$3

if [ -z "$SERVICE_NAME" ] || [ -z "$PORT" ] || [ -z "$CONFIG_FILE" ]; then
    echo "Usage: $0 <service_name> <port> <config_file>"
    echo "Example: $0 github_models 8092 github-models.env"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"

echo "🚀 Starting $SERVICE_NAME on port $PORT..."

# Save original service name before loading config
ORIGINAL_SERVICE_NAME="$SERVICE_NAME"

# Load global credentials first (from main config directory)
GLOBAL_CREDENTIALS="$ROOT_DIR/config/credentials.env"
if [ -f "$GLOBAL_CREDENTIALS" ]; then
    echo "🔑 Loading global credentials from $GLOBAL_CREDENTIALS"
    set -a
    source "$GLOBAL_CREDENTIALS"
    set +a
fi

# Load service-specific configuration
CONFIG_PATH="$PROJECT_DIR/config/$CONFIG_FILE"
if [ -f "$CONFIG_PATH" ]; then
    echo "📋 Loading configuration from $CONFIG_PATH"
    set -a
    source "$CONFIG_PATH"
    set +a
    # Restore original service name (don't let config override it)
    SERVICE_NAME="$ORIGINAL_SERVICE_NAME"
else
    echo "⚠️ Configuration file not found: $CONFIG_PATH"
fi

# Ensure LiteLLM gets the correct environment variable names
if [ -n "$GITHUB_TOKEN" ]; then
    export GITHUB_API_KEY="$GITHUB_TOKEN"
    echo "🔧 Set GITHUB_API_KEY for LiteLLM"
fi

# Create logs directory if it doesn't exist
mkdir -p "$ROOT_DIR/logs"

# Set Python path to include services directory
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Check if port is already in use
if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "❌ Port $PORT is already in use!"
    echo "   Use: sudo netstat -tlnp | grep :$PORT to see what's using it"
    exit 1
fi

# Start the service
echo "🔧 Starting service with Python path: $PYTHONPATH"
echo "📁 Working directory: $PROJECT_DIR"

cd "$PROJECT_DIR"

# Run the service based on service name
case $SERVICE_NAME in
    "vertex_claude")
        python3 -m services.vertex_claude_service
        ;;
    "vertex_gemini")
        python3 -m services.vertex_gemini_service
        ;;
    "github_models")
        python3 -m services.github_models_service
        ;;
    "openrouter")
        python3 -m services.openrouter_service
        ;;
    *)
        echo "❌ Unknown service: $SERVICE_NAME"
        echo "   Available services: vertex_claude, vertex_gemini, github_models, openrouter"
        exit 1
        ;;
esac