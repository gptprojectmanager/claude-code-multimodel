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

# Load configuration if file exists
CONFIG_PATH="$PROJECT_DIR/config/$CONFIG_FILE"
if [ -f "$CONFIG_PATH" ]; then
    echo "📋 Loading configuration from $CONFIG_PATH"
    set -a
    source "$CONFIG_PATH"
    set +a
else
    echo "⚠️ Configuration file not found: $CONFIG_PATH"
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
    "github_models")
        python -m services.github_models_service
        ;;
    "openrouter")
        python -m services.openrouter_service
        ;;
    "vertex_claude")
        echo "⚠️ Vertex Claude service not yet implemented"
        exit 1
        ;;
    "vertex_gemini")
        echo "⚠️ Vertex Gemini service not yet implemented"  
        exit 1
        ;;
    *)
        echo "❌ Unknown service: $SERVICE_NAME"
        echo "   Available services: github_models, openrouter, vertex_claude, vertex_gemini"
        exit 1
        ;;
esac