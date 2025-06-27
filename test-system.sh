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
