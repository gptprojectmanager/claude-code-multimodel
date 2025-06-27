#!/bin/bash

# Google Vertex AI Setup Script for Claude Code
# ==============================================

set -e  # Exit on any error

echo "🚀 Setting up Google Vertex AI for Claude Code..."

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

# Check if running on supported OS
if [[ "$OSTYPE" != "linux-gnu"* ]] && [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script requires Linux or macOS"
    exit 1
fi

# Check if gcloud is installed
print_step "Checking Google Cloud SDK installation..."
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud SDK is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

print_status "Google Cloud SDK found: $(gcloud version --format='value(Google Cloud SDK)')"

# Check if user is authenticated
print_step "Checking Google Cloud authentication..."
if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | head -1 > /dev/null; then
    print_warning "No active Google Cloud authentication found"
    echo "Please authenticate with Google Cloud:"
    echo "  gcloud auth login"
    echo "  gcloud auth application-default login"
    exit 1
fi

print_status "Authenticated as: $(gcloud auth list --filter='status:ACTIVE' --format='value(account)' | head -1)"

# Get or prompt for project ID
print_step "Configuring Google Cloud project..."
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    current_project=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -z "$current_project" ]; then
        echo "Please enter your Google Cloud Project ID:"
        read -r PROJECT_ID
    else
        echo "Current project: $current_project"
        echo "Use this project? (y/n): "
        read -r confirm
        if [[ $confirm == [yY] ]]; then
            PROJECT_ID=$current_project
        else
            echo "Please enter your Google Cloud Project ID:"
            read -r PROJECT_ID
        fi
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
else
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
fi

print_status "Using project: $PROJECT_ID"

# Enable required APIs
print_step "Enabling required Google Cloud APIs..."
apis=(
    "aiplatform.googleapis.com"
    "serviceusage.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "cloudbilling.googleapis.com"
)

for api in "${apis[@]}"; do
    print_status "Enabling $api..."
    gcloud services enable "$api" --project="$PROJECT_ID"
done

# Check Vertex AI access
print_step "Checking Vertex AI access..."
if ! gcloud ai models list --region=us-east5 --project="$PROJECT_ID" &>/dev/null; then
    print_warning "Cannot access Vertex AI models. You may need to:"
    echo "1. Enable billing for your project"
    echo "2. Request access to Claude models in Vertex AI Model Garden"
    echo "3. Wait for API activation (can take a few minutes)"
fi

# Create service account for Claude Code (optional)
print_step "Creating service account for Claude Code..."
SERVICE_ACCOUNT_NAME="claude-code-multimodel"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --description="Service account for Claude Code multi-model integration" \
        --display-name="Claude Code Multi-Model" \
        --project="$PROJECT_ID"
    
    # Grant necessary roles
    roles=(
        "roles/aiplatform.user"
        "roles/serviceusage.serviceUsageConsumer"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="$role"
    done
    
    print_status "Service account created: $SERVICE_ACCOUNT_EMAIL"
else
    print_status "Service account already exists: $SERVICE_ACCOUNT_EMAIL"
fi

# Create service account key
print_step "Creating service account key..."
KEY_FILE="./config/vertex-service-account.json"
if [ ! -f "$KEY_FILE" ]; then
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SERVICE_ACCOUNT_EMAIL" \
        --project="$PROJECT_ID"
    
    print_status "Service account key created: $KEY_FILE"
    print_warning "Keep this key file secure and do not commit it to version control"
else
    print_status "Service account key already exists: $KEY_FILE"
fi

# Update configuration file
print_step "Updating configuration file..."
CONFIG_FILE="./config/vertex-ai.env"
if [ -f "$CONFIG_FILE" ]; then
    # Update project ID in config file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/ANTHROPIC_VERTEX_PROJECT_ID=.*/ANTHROPIC_VERTEX_PROJECT_ID=$PROJECT_ID/" "$CONFIG_FILE"
    else
        # Linux
        sed -i "s/ANTHROPIC_VERTEX_PROJECT_ID=.*/ANTHROPIC_VERTEX_PROJECT_ID=$PROJECT_ID/" "$CONFIG_FILE"
    fi
    
    print_status "Configuration updated: $CONFIG_FILE"
fi

# Test Vertex AI connection
print_step "Testing Vertex AI connection..."
export ANTHROPIC_VERTEX_PROJECT_ID="$PROJECT_ID"
export CLOUD_ML_REGION="us-east5"
export CLAUDE_CODE_USE_VERTEX=1
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/$KEY_FILE"

# Simple test call
if python3 -c "
import os
import sys
sys.path.append('.')
try:
    from google.cloud import aiplatform
    aiplatform.init(project='$PROJECT_ID', location='us-east5')
    print('✅ Vertex AI connection successful')
except Exception as e:
    print(f'❌ Vertex AI connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
    print_status "Vertex AI setup completed successfully!"
else
    print_warning "Vertex AI connection test failed. This may be normal if:"
    echo "  - Claude models are not yet available in your region"
    echo "  - You need to request access in Vertex AI Model Garden"
    echo "  - Billing is not enabled for your project"
fi

# Display next steps
echo ""
echo -e "${GREEN}✅ Google Vertex AI setup completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Ensure billing is enabled for your project"
echo "2. Request access to Claude models in Vertex AI Model Garden:"
echo "   https://console.cloud.google.com/vertex-ai/model-garden"
echo "3. Source the configuration: source ./config/vertex-ai.env"
echo "4. Test with Claude Code: ANTHROPIC_BASE_URL=vertex claude"
echo ""
echo "Configuration file: $CONFIG_FILE"
echo "Service account key: $KEY_FILE"
echo ""