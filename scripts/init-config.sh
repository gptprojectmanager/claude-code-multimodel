#!/bin/bash

# Initialize Configuration Files from Templates
# =============================================

echo "🔧 Initializing configuration files from templates..."

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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in the right directory
if [ ! -d "./config" ]; then
    echo "❌ Config directory not found. Please run from project root."
    exit 1
fi

# Function to copy template if target doesn't exist
copy_template() {
    local template_file=$1
    local target_file=$2
    
    if [ -f "$template_file" ]; then
        if [ ! -f "$target_file" ]; then
            cp "$template_file" "$target_file"
            print_status "✅ Created $target_file from template"
        else
            print_warning "⚠️  $target_file already exists, skipping"
        fi
    else
        print_warning "⚠️  Template $template_file not found"
    fi
}

print_step "Copying configuration templates..."

# Copy all template files
copy_template "config/credentials.env.template" "config/credentials.env"
copy_template "config/vertex-ai.env.template" "config/vertex-ai.env"
copy_template "config/github-models.env.template" "config/github-models.env"
copy_template "config/openrouter.env.template" "config/openrouter.env"

echo ""
echo "📝 Configuration files created! Now you need to:"
echo ""
echo "1. Edit config/credentials.env with your API keys:"
echo "   - OPENROUTER_API_KEY=your-key"
echo "   - GITHUB_TOKEN=your-token"
echo "   - GOOGLE_CLOUD_PROJECT=your-project"
echo "   - GOOGLE_API_KEY=your-api-key"
echo ""
echo "2. Run the setup: ./scripts/quick-setup.sh"
echo ""
echo "3. Start the system: ./scripts/start-all-providers.sh"
echo ""
print_status "✅ Configuration initialization completed!"