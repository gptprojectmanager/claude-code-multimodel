#!/bin/bash
# Start individual multi-port service with Google Secret Manager support
# Usage: ./start-service.sh <service_name> <port> [config_file]
# Note: config_file is now optional when using Secret Manager

set -e

SERVICE_NAME=$1
PORT=$2
CONFIG_FILE=$3

if [ -z "$SERVICE_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <service_name> <port> [config_file]"
    echo "Example: $0 github_models 8092"
    echo "Example: $0 github_models 8092 github-models.env (fallback mode)"
    echo ""
    echo "Available services: vertex_claude, vertex_gemini, github_models, openrouter"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"

echo "🚀 Starting $SERVICE_NAME on port $PORT..."

# Activate Python virtual environment
VENV_PATH="$ROOT_DIR/venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "🐍 Activating Python virtual environment..."
    source "$VENV_PATH"
else
    echo "⚠️ Python virtual environment not found at $VENV_PATH"
fi

# Check Secret Manager access first
echo "🔐 Checking Google Secret Manager access..."
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Test Secret Manager connectivity
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from utils.secret_manager import SecretManagerClient
    client = SecretManagerClient()
    config = client.get_provider_config('${SERVICE_NAME}')
    print('✅ Secret Manager access verified for ${SERVICE_NAME}')
    print(f'✅ Configuration loaded with {len(config)} keys')
except Exception as e:
    print(f'⚠️ Secret Manager not available: {e}')
    print('⚠️ Will attempt fallback to .env file configuration')
    sys.exit(1)
"; then
    echo "🔐 Using Google Secret Manager for secure credential management"
    USE_SECRET_MANAGER=true
else
    echo "⚠️ Secret Manager unavailable, falling back to .env file mode"
    USE_SECRET_MANAGER=false
    
    # Ensure config file is provided when Secret Manager is unavailable
    if [ -z "$CONFIG_FILE" ]; then
        echo "❌ CONFIG_FILE required when Secret Manager is unavailable"
        echo "   Example: $0 $SERVICE_NAME $PORT ${SERVICE_NAME}.env"
        exit 1
    fi
fi

# Save original service name before loading config
ORIGINAL_SERVICE_NAME="$SERVICE_NAME"

# Load .env files only if Secret Manager is not available
if [ "$USE_SECRET_MANAGER" = false ]; then
    echo "📁 Loading configuration from .env files (fallback mode)"
    
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
        echo "❌ Configuration file not found: $CONFIG_PATH"
        echo "   Available .env files in $PROJECT_DIR/config/:"
        ls -la "$PROJECT_DIR/config/"*.env.template 2>/dev/null || echo "   No .env.template files found"
        exit 1
    fi

    # Ensure LiteLLM gets the correct environment variable names
    if [ -n "$GITHUB_TOKEN" ]; then
        export GITHUB_API_KEY="$GITHUB_TOKEN"
        echo "🔧 Set GITHUB_API_KEY for LiteLLM"
    fi
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

# Activate Python virtual environment
VENV_PATH="$ROOT_DIR/venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "🐍 Activating Python virtual environment..."
    source "$VENV_PATH"
else
    echo "⚠️ Python virtual environment not found at $VENV_PATH"
fi
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