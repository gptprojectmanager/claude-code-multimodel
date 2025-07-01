#!/bin/bash

# Start Vertex AI Proxy
echo "🚀 Starting Vertex AI Proxy..."

# Load configuration
if [ -f "./config/vertex-ai.env" ]; then
    set -a  # automatically export all variables
    source ./config/vertex-ai.env
    set +a  # stop automatically exporting
    echo "✅ Configuration loaded"
    
    # Verify project is set
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        echo "❌ GOOGLE_CLOUD_PROJECT not found in configuration"
        exit 1
    fi
    echo "✅ Google Cloud project: $GOOGLE_CLOUD_PROJECT"
else
    echo "❌ Configuration file not found: ./config/vertex-ai.env"
    echo "Please copy vertex-ai.env.template to vertex-ai.env and configure it"
    exit 1
fi

# Check for service account key
if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "❌ Service account key not found: $GOOGLE_APPLICATION_CREDENTIALS"
    echo "Please run ./scripts/setup-vertex.sh to create it"
    exit 1
fi

# Activate virtual environment
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Please run setup-vertex.sh first"
    exit 1
fi

# Check if Google Cloud libraries are installed
python3 -c "import google.cloud.aiplatform" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Google Cloud libraries not installed"
    echo "Installing required packages..."
    pip install google-cloud-aiplatform google-auth google-auth-oauthlib google-auth-httplib2
fi

# Start the proxy
echo "🌐 Starting proxy on http://localhost:${VERTEX_PROXY_PORT:-8081}"
python ./proxy/vertex_ai_proxy.py