#!/bin/bash

# Start GitHub Models Proxy
echo "🚀 Starting GitHub Models Proxy..."

# Load configuration
if [ -f "./config/github-models.env" ]; then
    set -a  # automatically export all variables
    source ./config/github-models.env
    set +a  # stop automatically exporting
    echo "✅ Configuration loaded"
    
    # Verify token is loaded
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "❌ GITHUB_TOKEN not found in configuration"
        exit 1
    fi
    echo "✅ GitHub token loaded (${#GITHUB_TOKEN} characters)"
else
    echo "❌ Configuration file not found: ./config/github-models.env"
    exit 1
fi

# Activate virtual environment
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Please run setup-github-models.sh first"
    exit 1
fi

# Start the proxy
echo "🌐 Starting proxy on http://localhost:${LITELLM_PORT:-8082}"
python ./proxy/github_models_proxy.py
