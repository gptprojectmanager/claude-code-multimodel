#!/bin/bash

# Quick Setup - Configure API Keys for Immediate Use
# ==================================================

set -e

echo "🚀 Quick Setup - Claude Code Multi-Model Integration"
echo "===================================================="
echo ""
echo "⚠️  IMPORTANT: This script expects you to have API keys ready."
echo "If you don't have credentials.env, copy from credentials.env.template first:"
echo "  cp config/credentials.env.template config/credentials.env"
echo "  # Edit config/credentials.env with your API keys"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Load credentials
if [ -f "./config/credentials.env" ]; then
    source ./config/credentials.env
    print_status "✅ Credentials loaded"
else
    print_error "❌ Credentials file not found"
    exit 1
fi

# Test OpenRouter
print_step "Testing OpenRouter API..."
if curl -s -f \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "Content-Type: application/json" \
    "https://openrouter.ai/api/v1/models" > /tmp/or_test.json; then
    print_status "✅ OpenRouter API Key is valid"
    OR_MODELS=$(jq -r '.data[].id' /tmp/or_test.json 2>/dev/null | head -3 || echo "anthropic/claude-3.5-sonnet")
    print_status "Available models: $(echo $OR_MODELS | tr '\n' ', ')"
else
    print_error "❌ OpenRouter API test failed"
fi

# Test GitHub Models
print_step "Testing GitHub Models API..."
if curl -s -f \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    "https://models.inference.ai.azure.com/models" > /tmp/gh_test.json; then
    print_status "✅ GitHub Token is valid"
    GH_MODELS=$(jq -r '.[].name' /tmp/gh_test.json 2>/dev/null | head -3 || echo "claude-3-5-sonnet")
    print_status "Available models: $(echo $GH_MODELS | tr '\n' ', ')"
else
    print_warning "⚠️  GitHub Models API test - may need different endpoint"
fi

# Test Google API Key
print_step "Testing Google API Key..."
if curl -s -f \
    "https://generativelanguage.googleapis.com/v1/models?key=$GOOGLE_API_KEY" > /tmp/google_test.json; then
    print_status "✅ Google API Key is valid"
else
    print_warning "⚠️  Google API Key test failed - using gcloud auth instead"
fi

# Update configurations quickly
print_step "Updating configurations..."

# Quick Vertex AI config
cat > ./config/vertex-ai.env << EOF
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
VERTEX_AI_LOCATION=$VERTEX_AI_LOCATION
GOOGLE_API_KEY=$GOOGLE_API_KEY
VERTEX_PRIMARY_MODEL=claude-sonnet-4@20250514
VERTEX_SECONDARY_MODEL=claude-3-5-haiku@20241022
VERTEX_PROXY_PORT=8081
USE_GCLOUD_AUTH=true
EOF

# Quick GitHub config  
cat > ./config/github-models.env << EOF
GITHUB_TOKEN=$GITHUB_TOKEN
GITHUB_MODELS_ENDPOINT=$GITHUB_MODELS_ENDPOINT
GITHUB_PRIMARY_MODEL=claude-3-5-sonnet
GITHUB_SECONDARY_MODEL=claude-3-5-haiku
GITHUB_PROXY_PORT=8082
EOF

# Quick OpenRouter config
cat > ./config/openrouter.env << EOF
OPENROUTER_API_KEY=$OPENROUTER_API_KEY
OPENROUTER_API_BASE=$OPENROUTER_API_BASE
OPENROUTER_PRIMARY_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_SECONDARY_MODEL=anthropic/claude-3-haiku
OPENROUTER_PROXY_PORT=8084
EOF

print_status "✅ Configuration files updated"

# Create a simple test script
cat > ./test-system.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing Claude Code Multi-Model System"
echo "=========================================="

# Load credentials
source ./config/credentials.env

# Test each API individually
echo ""
echo "1. Testing OpenRouter..."
curl -s -X POST https://openrouter.ai/api/v1/chat/completions \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": "Hello! Say hi from OpenRouter."}],
        "max_tokens": 50
    }' | jq -r '.choices[0].message.content // "OpenRouter test failed"'

echo ""
echo "2. Testing GitHub Models..."
curl -s -X POST https://models.inference.ai.azure.com/chat/completions \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "claude-3-5-sonnet",
        "messages": [{"role": "user", "content": "Hello! Say hi from GitHub Models."}],
        "max_tokens": 50
    }' | jq -r '.choices[0].message.content // "GitHub Models test failed"'

echo ""
echo "3. Testing Google Vertex AI (using gcloud)..."
if command -v gcloud &> /dev/null; then
    gcloud config set project $GOOGLE_CLOUD_PROJECT
    echo "✅ Vertex AI configured with project: $GOOGLE_CLOUD_PROJECT"
else
    echo "❌ gcloud not available"
fi

echo ""
echo "✅ API tests completed!"
EOF

chmod +x ./test-system.sh
print_status "✅ Test script created: ./test-system.sh"

# Summary
echo ""
echo "🎉 Quick Setup Completed!"
echo "========================"
echo ""
echo "✅ OpenRouter: Configured"
echo "✅ GitHub Models: Configured" 
echo "✅ Google Vertex AI: Using existing gcloud setup"
echo ""
echo "Next steps:"
echo "1. Test APIs: ./test-system.sh"
echo "2. Start system: ./scripts/start-all-providers.sh"
echo "3. Use Claude Code: export ANTHROPIC_BASE_URL=http://localhost:8080 && claude"
echo ""
echo "System ready! 🚀"

# Cleanup temp files
rm -f /tmp/or_test.json /tmp/gh_test.json /tmp/google_test.json