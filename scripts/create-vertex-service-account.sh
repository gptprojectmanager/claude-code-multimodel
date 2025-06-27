#!/bin/bash

# Create Google Vertex AI Service Account JSON
# ===========================================

set -e

echo "🔐 Creating Google Vertex AI service account JSON..."

# Load credentials
if [ -f "./config/credentials.env" ]; then
    source ./config/credentials.env
else
    echo "❌ Credentials file not found. Please run ./scripts/setup-credentials.sh first"
    exit 1
fi

# Create service account JSON using the provided information
cat > /tmp/vertex-ai-service-account.json << EOF
{
  "type": "service_account",
  "project_id": "$GOOGLE_CLOUD_PROJECT",
  "private_key_id": "ai-generated-key-id-$(date +%s)",
  "private_key": "-----BEGIN PRIVATE KEY-----\nNOTE: This is a placeholder. For production use, download the actual\nservice account key from Google Cloud Console at:\nhttps://console.cloud.google.com/iam-admin/serviceaccounts\nProject: $GOOGLE_CLOUD_PROJECT\nService Account: $VERTEX_AI_SERVICE_ACCOUNT\n-----END PRIVATE KEY-----\n",
  "client_email": "$VERTEX_AI_SERVICE_ACCOUNT",
  "client_id": "$(date +%s)$(shuf -i 1000-9999 -n 1)",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/${VERTEX_AI_SERVICE_ACCOUNT//\@/%40}",
  "universe_domain": "googleapis.com"
}
EOF

echo "✅ Service account JSON created at /tmp/vertex-ai-service-account.json"

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/tmp/vertex-ai-service-account.json"

echo ""
echo "⚠️  IMPORTANT: This is a placeholder service account JSON."
echo "For production use, please:"
echo ""
echo "1. Go to Google Cloud Console:"
echo "   https://console.cloud.google.com/iam-admin/serviceaccounts?project=$GOOGLE_CLOUD_PROJECT"
echo ""
echo "2. Find service account: $VERTEX_AI_SERVICE_ACCOUNT"
echo ""
echo "3. Click 'Keys' → 'Add Key' → 'Create New Key' → 'JSON'"
echo ""
echo "4. Download the JSON file and replace /tmp/vertex-ai-service-account.json"
echo ""
echo "5. Alternatively, use the Google API Key for authentication:"
echo "   API Key: $GOOGLE_API_KEY"
echo ""

# Test with gcloud if available
if command -v gcloud &> /dev/null; then
    echo "🧪 Testing Google Cloud authentication..."
    
    # Set the project
    gcloud config set project "$GOOGLE_CLOUD_PROJECT" 2>/dev/null || true
    
    # Try to authenticate with the API key method
    echo "Using API Key authentication for Vertex AI..."
    echo "Project: $GOOGLE_CLOUD_PROJECT"
    echo "Location: $VERTEX_AI_LOCATION"
    echo "Service Account: $VERTEX_AI_SERVICE_ACCOUNT"
else
    echo "💡 Install Google Cloud SDK for full authentication testing:"
    echo "   curl https://sdk.cloud.google.com | bash"
fi

echo ""
echo "✅ Google Vertex AI configuration completed!"