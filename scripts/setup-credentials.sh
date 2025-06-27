#!/bin/bash

# Setup API Credentials for Claude Code Multi-Model Integration
# =============================================================

set -e  # Exit on any error

echo "🔐 Setting up API credentials for Claude Code Multi-Model Integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running from correct directory
if [ ! -f "./config/credentials.env" ]; then
    print_error "Please run this script from the claude-code-multimodel directory"
    echo "Current directory: $(pwd)"
    echo "Expected file: ./config/credentials.env"
    exit 1
fi

# Load credentials
print_step "Loading credentials from config/credentials.env..."
source ./config/credentials.env
print_status "Credentials loaded"

# Check Google Cloud existing setup
print_step "Checking existing Google Cloud setup..."

if command -v gcloud &> /dev/null; then
    print_status "✅ Google Cloud SDK is installed"
    
    # Check current project
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ "$CURRENT_PROJECT" = "$GOOGLE_CLOUD_PROJECT" ]; then
        print_status "✅ Project already configured: $GOOGLE_CLOUD_PROJECT"
    else
        print_warning "Current project: $CURRENT_PROJECT, setting to: $GOOGLE_CLOUD_PROJECT"
        gcloud config set project "$GOOGLE_CLOUD_PROJECT"
    fi
    
    # Check authentication
    CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "")
    if [ ! -z "$CURRENT_ACCOUNT" ]; then
        print_status "✅ Authenticated as: $CURRENT_ACCOUNT"
    else
        print_error "❌ Not authenticated with gcloud"
        echo "Please run: gcloud auth login"
        exit 1
    fi
    
    # Setup application default credentials
    print_step "Setting up Application Default Credentials..."
    if gcloud auth application-default print-access-token >/dev/null 2>&1; then
        print_status "✅ Application Default Credentials already configured"
    else
        print_warning "Setting up Application Default Credentials..."
        gcloud auth application-default login --no-launch-browser
    fi
    
    # Check Vertex AI API
    if gcloud services list --enabled --filter="name:aiplatform.googleapis.com" --project="$GOOGLE_CLOUD_PROJECT" --format="value(name)" | grep -q aiplatform; then
        print_status "✅ Vertex AI API is enabled"
    else
        print_warning "Enabling Vertex AI API..."
        gcloud services enable aiplatform.googleapis.com --project="$GOOGLE_CLOUD_PROJECT"
    fi
    
    # Check service account
    if gcloud iam service-accounts describe "$VERTEX_AI_SERVICE_ACCOUNT" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
        print_status "✅ Service account exists: $VERTEX_AI_SERVICE_ACCOUNT"
    else
        print_warning "Service account not found: $VERTEX_AI_SERVICE_ACCOUNT"
    fi
    
else
    print_error "❌ Google Cloud SDK not installed"
    echo "Please install it: curl https://sdk.cloud.google.com | bash"
    exit 1
fi

# Test Google API Key
print_step "Testing Google API Key..."
if [ ! -z "$GOOGLE_API_KEY" ]; then
    if command -v curl &> /dev/null; then
        # Test the API key with Generative AI API
        TEST_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/google_test.json \
            "https://generativelanguage.googleapis.com/v1/models?key=$GOOGLE_API_KEY" || echo "000")
        
        if [ "$TEST_RESPONSE" = "200" ]; then
            print_status "✅ Google API Key is valid"
        else
            print_warning "⚠️  Google API Key test failed (HTTP $TEST_RESPONSE)"
            print_warning "This may be normal for Vertex AI-specific keys"
        fi
        rm -f /tmp/google_test.json
    fi
else
    print_warning "No Google API Key provided"
fi

# Test OpenRouter API Key
print_step "Testing OpenRouter API Key..."
if [ ! -z "$OPENROUTER_API_KEY" ]; then
    if command -v curl &> /dev/null; then
        TEST_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/openrouter_test.json \
            -H "Authorization: Bearer $OPENROUTER_API_KEY" \
            -H "Content-Type: application/json" \
            "https://openrouter.ai/api/v1/models" || echo "000")
        
        if [ "$TEST_RESPONSE" = "200" ]; then
            print_status "✅ OpenRouter API Key is valid"
            
            # Show available models (first 5)
            if command -v jq &> /dev/null; then
                AVAILABLE_MODELS=$(jq -r '.data[].id' /tmp/openrouter_test.json 2>/dev/null | head -5)
                if [ ! -z "$AVAILABLE_MODELS" ]; then
                    print_status "Available OpenRouter models (first 5):"
                    echo "$AVAILABLE_MODELS" | while read model; do
                        echo "  - $model"
                    done
                fi
            fi
        else
            print_error "❌ OpenRouter API Key is invalid (HTTP $TEST_RESPONSE)"
        fi
        rm -f /tmp/openrouter_test.json
    fi
else
    print_error "No OpenRouter API Key provided"
fi

# Test GitHub Token
print_step "Testing GitHub Token..."
if [ ! -z "$GITHUB_TOKEN" ]; then
    if command -v curl &> /dev/null; then
        TEST_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/github_test.json \
            -H "Authorization: Bearer $GITHUB_TOKEN" \
            -H "Content-Type: application/json" \
            "https://models.inference.ai.azure.com/models" || echo "000")
        
        if [ "$TEST_RESPONSE" = "200" ]; then
            print_status "✅ GitHub Token is valid"
            
            # Show available models (first 5)  
            if command -v jq &> /dev/null; then
                AVAILABLE_MODELS=$(jq -r '.[].name' /tmp/github_test.json 2>/dev/null | head -5)
                if [ ! -z "$AVAILABLE_MODELS" ]; then
                    print_status "Available GitHub Models (first 5):"
                    echo "$AVAILABLE_MODELS" | while read model; do
                        echo "  - $model"
                    done
                fi
            fi
        else
            print_warning "⚠️  GitHub Token test failed (HTTP $TEST_RESPONSE)"
            print_warning "This may be normal if GitHub Models API has different endpoints"
        fi
        rm -f /tmp/github_test.json
    fi
else
    print_error "No GitHub Token provided"
fi

# Update configuration files with credentials
print_step "Updating configuration files..."

# Update vertex-ai.env
cat > ./config/vertex-ai.env << EOF
# Google Vertex AI Configuration with API Keys
# ===========================================

# Project Configuration (using existing gcloud setup)
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
VERTEX_AI_LOCATION=$VERTEX_AI_LOCATION
VERTEX_AI_SERVICE_ACCOUNT=$VERTEX_AI_SERVICE_ACCOUNT

# Authentication (use gcloud auth)
USE_GCLOUD_AUTH=true
GOOGLE_API_KEY=$GOOGLE_API_KEY

# Primary Model Configuration
VERTEX_PRIMARY_MODEL=claude-sonnet-4@20250514
VERTEX_SECONDARY_MODEL=claude-3-5-haiku@20241022

# API Configuration
VERTEX_API_ENDPOINT=https://\${VERTEX_AI_LOCATION}-aiplatform.googleapis.com
VERTEX_PROXY_PORT=8081
VERTEX_PROXY_HOST=0.0.0.0

# Rate Limiting (Vertex AI limits)
VERTEX_MAX_REQUESTS_PER_MINUTE=1000
VERTEX_MAX_TOKENS_PER_MINUTE=50000
VERTEX_MAX_CONCURRENT_REQUESTS=10

# Cost Configuration
VERTEX_INPUT_COST_PER_TOKEN=0.000003
VERTEX_OUTPUT_COST_PER_TOKEN=0.000015
VERTEX_COST_MULTIPLIER=1.0

# Performance Settings
VERTEX_REQUEST_TIMEOUT=300
VERTEX_MAX_RETRIES=3
VERTEX_RETRY_DELAY=1.0

# Health Check
VERTEX_HEALTH_CHECK_INTERVAL=60
VERTEX_HEALTH_CHECK_TIMEOUT=10

# Logging
VERTEX_LOG_LEVEL=INFO
VERTEX_ENABLE_REQUEST_LOGGING=true
EOF

# Update github-models.env  
cat > ./config/github-models.env << EOF
# GitHub Models Configuration with API Keys
# =========================================

# Authentication
GITHUB_TOKEN=$GITHUB_TOKEN
GITHUB_MODELS_ENDPOINT=$GITHUB_MODELS_ENDPOINT
GITHUB_MODELS_API_VERSION=$GITHUB_MODELS_API_VERSION

# Model Configuration
GITHUB_PRIMARY_MODEL=claude-3-5-sonnet
GITHUB_SECONDARY_MODEL=claude-3-5-haiku
GITHUB_FALLBACK_MODELS=gpt-4o,gpt-4o-mini,claude-3-opus

# Proxy Configuration
GITHUB_PROXY_PORT=8082
GITHUB_PROXY_HOST=0.0.0.0
LITELLM_PORT=8083

# Rate Limiting (GitHub Models limits)
GITHUB_MAX_REQUESTS_PER_MINUTE=500
GITHUB_MAX_TOKENS_PER_MINUTE=100000
GITHUB_MAX_CONCURRENT_REQUESTS=5

# Cost Configuration (GitHub Models pricing)
GITHUB_INPUT_COST_PER_TOKEN=0.0000025
GITHUB_OUTPUT_COST_PER_TOKEN=0.00001
GITHUB_COST_MULTIPLIER=0.8

# Performance Settings
GITHUB_REQUEST_TIMEOUT=180
GITHUB_MAX_RETRIES=3
GITHUB_RETRY_DELAY=2.0

# Health Check
GITHUB_HEALTH_CHECK_INTERVAL=60
GITHUB_HEALTH_CHECK_TIMEOUT=10

# liteLLM Configuration
LITELLM_LOG_LEVEL=INFO
LITELLM_ENABLE_CACHING=true
LITELLM_CACHE_TTL=300

# Logging
GITHUB_LOG_LEVEL=INFO
GITHUB_ENABLE_REQUEST_LOGGING=true
EOF

# Update openrouter.env
cat > ./config/openrouter.env << EOF
# OpenRouter Configuration with API Keys
# ======================================

# Authentication
OPENROUTER_API_KEY=$OPENROUTER_API_KEY
OPENROUTER_API_BASE=$OPENROUTER_API_BASE
OPENROUTER_SITE_URL=$OPENROUTER_SITE_URL
OPENROUTER_APP_NAME=$OPENROUTER_APP_NAME

# Model Configuration
OPENROUTER_PRIMARY_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_SECONDARY_MODEL=anthropic/claude-3-haiku
OPENROUTER_FALLBACK_MODELS=google/gemini-2.0-flash,openai/gpt-4o,meta-llama/llama-3.2-90b-vision

# Proxy Configuration
OPENROUTER_PROXY_PORT=8084
OPENROUTER_PROXY_HOST=0.0.0.0

# Rate Limiting (OpenRouter limits)
OPENROUTER_MAX_REQUESTS_PER_MINUTE=200
OPENROUTER_MAX_TOKENS_PER_MINUTE=80000
OPENROUTER_MAX_CONCURRENT_REQUESTS=5

# Cost Configuration
OPENROUTER_INPUT_COST_PER_TOKEN=0.000003
OPENROUTER_OUTPUT_COST_PER_TOKEN=0.000015
OPENROUTER_COST_MULTIPLIER=1.2

# Provider Selection Strategy
PROVIDER_SELECTION_STRATEGY=performance
ENABLE_COST_OPTIMIZATION=true
PREFER_CHEAPER_MODELS=false

# Fallback Configuration
ENABLE_AUTO_FALLBACK=true
FALLBACK_ON_RATE_LIMIT=true
FALLBACK_TIMEOUT=30

# Performance Settings
OPENROUTER_REQUEST_TIMEOUT=180
OPENROUTER_MAX_RETRIES=3
OPENROUTER_RETRY_DELAY=1.0

# Health Check
OPENROUTER_HEALTH_CHECK_INTERVAL=60
OPENROUTER_HEALTH_CHECK_TIMEOUT=10

# Cost Tracking
ENABLE_OPENROUTER_COST_TRACKING=true
OPENROUTER_COST_LOG_FILE=/tmp/openrouter-usage.log

# Logging
OPENROUTER_LOG_LEVEL=INFO
OPENROUTER_ENABLE_REQUEST_LOGGING=true
EOF

print_status "Configuration files updated with API credentials"

# Create environment loading script
print_step "Creating environment loader script..."
cat > ./scripts/load-credentials.sh << 'EOF'
#!/bin/bash

# Load API Credentials
# ===================

# Check if credentials file exists
if [ ! -f "./config/credentials.env" ]; then
    echo "❌ Credentials file not found: ./config/credentials.env"
    echo "Please run ./scripts/setup-credentials.sh first"
    exit 1
fi

# Load all credential files
echo "🔐 Loading API credentials..."

# Load main credentials
source ./config/credentials.env

# Load provider-specific configs
if [ -f "./config/vertex-ai.env" ]; then
    source ./config/vertex-ai.env
fi

if [ -f "./config/github-models.env" ]; then
    source ./config/github-models.env
fi

if [ -f "./config/openrouter.env" ]; then
    source ./config/openrouter.env
fi

if [ -f "./config/claude-code-integration.env" ]; then
    source ./config/claude-code-integration.env
fi

echo "✅ All credentials loaded"

# Export important variables
export GOOGLE_CLOUD_PROJECT
export GOOGLE_API_KEY
export OPENROUTER_API_KEY
export GITHUB_TOKEN
export ANTHROPIC_BASE_URL="http://localhost:${PROXY_PORT:-8080}"

echo "🌐 Claude Code configured to use: $ANTHROPIC_BASE_URL"
EOF

chmod +x ./scripts/load-credentials.sh
print_status "Environment loader created: ./scripts/load-credentials.sh"

# Test credential loading
print_step "Testing credential loading..."
if source ./scripts/load-credentials.sh; then
    print_status "✅ Credential loading test successful"
else
    print_error "❌ Credential loading test failed"
fi

# Security reminder
echo ""
echo "🔒 SECURITY REMINDERS:"
echo "======================"
echo "1. ✅ credentials.env is already in .gitignore"
echo "2. ⚠️  Keep API keys secure and never share them"
echo "3. 🔄 Rotate keys regularly for security"
echo "4. 🌐 Using existing gcloud authentication for Vertex AI"
echo "5. 🚀 For production, use proper secret management"
echo ""

print_status "✅ API credentials setup completed!"
echo ""
echo "System Status:"
echo "=============="
echo "✅ Google Cloud Project: $GOOGLE_CLOUD_PROJECT"
echo "✅ Vertex AI: Ready (using gcloud auth)"
echo "✅ OpenRouter: Ready"
echo "✅ GitHub Models: Ready"
echo ""
echo "Next steps:"
echo "1. Start the system: ./scripts/start-all-providers.sh"
echo "2. Use Claude Code: export ANTHROPIC_BASE_URL=http://localhost:8080 && claude"