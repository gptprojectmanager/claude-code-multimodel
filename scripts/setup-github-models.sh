#!/bin/bash

# GitHub Models Setup Script for Claude Code
# ===========================================

set -e  # Exit on any error

echo "🚀 Setting up GitHub Models integration for Claude Code..."

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

# Check if Python 3 is installed
print_step "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
print_status "Python found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed"
    echo "Please install pip3"
    exit 1
fi

# Check for GitHub CLI (optional but recommended)
print_step "Checking GitHub CLI..."
if command -v gh &> /dev/null; then
    print_status "GitHub CLI found: $(gh --version | head -1)"
    
    # Check if user is authenticated
    if gh auth status &> /dev/null; then
        print_status "GitHub CLI is authenticated"
        GITHUB_USER=$(gh api user --jq .login 2>/dev/null || echo "unknown")
        print_status "Authenticated as: $GITHUB_USER"
    else
        print_warning "GitHub CLI is not authenticated"
        echo "To authenticate with GitHub CLI, run: gh auth login"
    fi
else
    print_warning "GitHub CLI not found. Install it for easier token management:"
    echo "  https://cli.github.com/"
fi

# Prompt for GitHub token
print_step "Configuring GitHub token..."
if [ -z "$GITHUB_TOKEN" ]; then
    echo ""
    echo "GitHub Models requires a GitHub token with appropriate permissions."
    echo "You can create one at: https://github.com/settings/tokens"
    echo ""
    echo "Required scopes for GitHub Models:"
    echo "  - model:inference (for GitHub Models access)"
    echo "  - read:user (basic user information)"
    echo ""
    echo "Please enter your GitHub token (or press Enter to skip):"
    read -s GITHUB_TOKEN
    echo ""
    
    if [ -z "$GITHUB_TOKEN" ]; then
        print_warning "No GitHub token provided. You'll need to set GITHUB_TOKEN manually."
        GITHUB_TOKEN="your-github-token-here"
    else
        print_status "GitHub token configured"
    fi
fi

# Create virtual environment
print_step "Creating Python virtual environment..."
VENV_PATH="./venv"
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
    print_status "Virtual environment created: $VENV_PATH"
else
    print_status "Virtual environment already exists: $VENV_PATH"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"
print_status "Virtual environment activated"

# Upgrade pip
print_step "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install Python dependencies
print_step "Installing Python dependencies..."
if [ -f "./proxy/requirements.txt" ]; then
    pip install -r ./proxy/requirements.txt
    print_status "Dependencies installed successfully"
else
    print_error "Requirements file not found: ./proxy/requirements.txt"
    exit 1
fi

# Test GitHub Models API access
print_step "Testing GitHub Models API access..."
if [ "$GITHUB_TOKEN" != "your-github-token-here" ]; then
    TEST_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/github_models_test.json \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Content-Type: application/json" \
        "https://models.inference.ai.azure.com/v1/models" || echo "000")
    
    if [ "$TEST_RESPONSE" = "200" ]; then
        print_status "✅ GitHub Models API access successful"
        AVAILABLE_MODELS=$(jq -r '.data[].id' /tmp/github_models_test.json 2>/dev/null | head -5)
        if [ ! -z "$AVAILABLE_MODELS" ]; then
            print_status "Available models (first 5):"
            echo "$AVAILABLE_MODELS" | while read model; do
                echo "  - $model"
            done
        fi
    elif [ "$TEST_RESPONSE" = "401" ]; then
        print_error "❌ GitHub token authentication failed"
        print_warning "Please check your token has the required scopes"
    elif [ "$TEST_RESPONSE" = "403" ]; then
        print_error "❌ Access forbidden. You may need to:"
        echo "  1. Request access to GitHub Models"
        echo "  2. Ensure your token has model:inference scope"
    else
        print_warning "⚠️  GitHub Models API test failed (HTTP $TEST_RESPONSE)"
        print_warning "This may be normal if you haven't requested access yet"
    fi
    
    rm -f /tmp/github_models_test.json
else
    print_warning "Skipping API test - no valid token provided"
fi

# Update configuration file
print_step "Updating configuration file..."
CONFIG_FILE="./config/github-models.env"
if [ -f "$CONFIG_FILE" ]; then
    # Update GitHub token in config file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=$GITHUB_TOKEN/" "$CONFIG_FILE"
    else
        # Linux
        sed -i "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=$GITHUB_TOKEN/" "$CONFIG_FILE"
    fi
    
    print_status "Configuration updated: $CONFIG_FILE"
fi

# Create systemd service file (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
    print_step "Creating systemd service..."
    
    SERVICE_FILE="/tmp/github-models-proxy.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GitHub Models Proxy for Claude Code
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment=PATH=$PWD/venv/bin
ExecStart=$PWD/venv/bin/python $PWD/proxy/github_models_proxy.py
EnvironmentFile=$PWD/config/github-models.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    print_status "Systemd service file created: $SERVICE_FILE"
    echo "To install the service, run:"
    echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable github-models-proxy"
    echo "  sudo systemctl start github-models-proxy"
fi

# Create start script
print_step "Creating start script..."
START_SCRIPT="./scripts/start-github-models.sh"
cat > "$START_SCRIPT" << 'EOF'
#!/bin/bash

# Start GitHub Models Proxy
echo "🚀 Starting GitHub Models Proxy..."

# Load configuration
if [ -f "./config/github-models.env" ]; then
    source ./config/github-models.env
    echo "✅ Configuration loaded"
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
echo "🌐 Starting proxy on http://localhost:${LITELLM_PORT:-8083}"
python ./proxy/github_models_proxy.py
EOF

chmod +x "$START_SCRIPT"
print_status "Start script created: $START_SCRIPT"

# Test proxy startup
print_step "Testing proxy startup..."
if command -v timeout &> /dev/null; then
    # Test if the proxy can start (run for 5 seconds then kill)
    GITHUB_TOKEN="$GITHUB_TOKEN" timeout 5s python ./proxy/github_models_proxy.py > /tmp/proxy_test.log 2>&1 &
    PROXY_PID=$!
    sleep 2
    
    if kill -0 $PROXY_PID 2>/dev/null; then
        print_status "✅ Proxy startup test successful"
        kill $PROXY_PID 2>/dev/null || true
    else
        print_warning "⚠️  Proxy startup test failed. Check logs:"
        cat /tmp/proxy_test.log
    fi
    
    rm -f /tmp/proxy_test.log
else
    print_status "Skipping proxy startup test (timeout command not available)"
fi

# Display next steps
echo ""
echo -e "${GREEN}✅ GitHub Models setup completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Ensure you have a valid GitHub token with model:inference scope"
echo "2. Request access to GitHub Models if you haven't already:"
echo "   https://github.com/marketplace/models"
echo "3. Start the proxy: ./scripts/start-github-models.sh"
echo "4. Test with Claude Code:"
echo "   ANTHROPIC_BASE_URL=http://localhost:8083 claude"
echo ""
echo "Configuration file: $CONFIG_FILE"
echo "Start script: $START_SCRIPT"
echo "Proxy endpoint: http://localhost:8083"
echo ""

# Deactivate virtual environment
deactivate