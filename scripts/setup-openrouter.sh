#!/bin/bash

# OpenRouter Setup Script for Claude Code
# ========================================

set -e  # Exit on any error

echo "🚀 Setting up OpenRouter integration for Claude Code..."

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

print_status "Python found: $(python3 --version)"

# Check if curl is available for API testing
if ! command -v curl &> /dev/null; then
    print_warning "curl not found. API testing will be skipped."
fi

# Prompt for OpenRouter API key
print_step "Configuring OpenRouter API key..."
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo ""
    echo "OpenRouter provides access to multiple AI models through a single API."
    echo "Sign up at: https://openrouter.ai/"
    echo ""
    echo "Benefits of OpenRouter:"
    echo "  - Access to 100+ models (Claude, GPT, Gemini, Llama, etc.)"
    echo "  - Competitive pricing and automatic fallbacks"
    echo "  - Rate limiting and cost controls"
    echo ""
    echo "Please enter your OpenRouter API key (or press Enter to skip):"
    read -s OPENROUTER_API_KEY
    echo ""
    
    if [ -z "$OPENROUTER_API_KEY" ]; then
        print_warning "No OpenRouter API key provided. You'll need to set OPENROUTER_API_KEY manually."
        OPENROUTER_API_KEY="your-openrouter-api-key-here"
    else
        print_status "OpenRouter API key configured"
    fi
fi

# Activate virtual environment if it exists
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
    print_status "Virtual environment activated"
else
    # Create virtual environment if it doesn't exist
    print_step "Creating Python virtual environment..."
    python3 -m venv ./venv
    source ./venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    print_status "Virtual environment created and activated"
fi

# Install Python dependencies
print_step "Installing Python dependencies..."
if [ -f "./proxy/requirements.txt" ]; then
    pip install -r ./proxy/requirements.txt > /dev/null 2>&1
    print_status "Dependencies installed successfully"
else
    print_error "Requirements file not found: ./proxy/requirements.txt"
    exit 1
fi

# Test OpenRouter API access
print_step "Testing OpenRouter API access..."
if [ "$OPENROUTER_API_KEY" != "your-openrouter-api-key-here" ] && command -v curl &> /dev/null; then
    TEST_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/openrouter_test.json \
        -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        -H "Content-Type: application/json" \
        "https://openrouter.ai/api/v1/models" || echo "000")
    
    if [ "$TEST_RESPONSE" = "200" ]; then
        print_status "✅ OpenRouter API access successful"
        
        # Show available models (top 10)
        if command -v jq &> /dev/null; then
            AVAILABLE_MODELS=$(jq -r '.data[].id' /tmp/openrouter_test.json 2>/dev/null | head -10)
            if [ ! -z "$AVAILABLE_MODELS" ]; then
                print_status "Available models (first 10):"
                echo "$AVAILABLE_MODELS" | while read model; do
                    echo "  - $model"
                done
            fi
        fi
        
        # Check account balance if available
        BALANCE_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/openrouter_balance.json \
            -H "Authorization: Bearer $OPENROUTER_API_KEY" \
            "https://openrouter.ai/api/v1/auth/key" 2>/dev/null || echo "000")
        
        if [ "$BALANCE_RESPONSE" = "200" ] && command -v jq &> /dev/null; then
            BALANCE=$(jq -r '.data.credit_left // "unknown"' /tmp/openrouter_balance.json 2>/dev/null)
            if [ "$BALANCE" != "unknown" ] && [ "$BALANCE" != "null" ]; then
                print_status "Account balance: \$$BALANCE"
            fi
        fi
        
    elif [ "$TEST_RESPONSE" = "401" ]; then
        print_error "❌ OpenRouter API key authentication failed"
        print_warning "Please check your API key at: https://openrouter.ai/keys"
    elif [ "$TEST_RESPONSE" = "403" ]; then
        print_error "❌ Access forbidden. Your API key may not have sufficient permissions"
    else
        print_warning "⚠️  OpenRouter API test failed (HTTP $TEST_RESPONSE)"
        print_warning "This may be normal if there are temporary network issues"
    fi
    
    rm -f /tmp/openrouter_test.json /tmp/openrouter_balance.json
else
    print_warning "Skipping API test - no valid key provided or curl not available"
fi

# Update configuration file
print_step "Updating configuration file..."
CONFIG_FILE="./config/openrouter.env"
if [ -f "$CONFIG_FILE" ]; then
    # Update OpenRouter API key in config file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$OPENROUTER_API_KEY/" "$CONFIG_FILE"
    else
        # Linux
        sed -i "s/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$OPENROUTER_API_KEY/" "$CONFIG_FILE"
    fi
    
    print_status "Configuration updated: $CONFIG_FILE"
fi

# Create start script for OpenRouter
print_step "Creating start script..."
START_SCRIPT="./scripts/start-openrouter.sh"
cat > "$START_SCRIPT" << 'EOF'
#!/bin/bash

# Start OpenRouter Proxy
echo "🚀 Starting OpenRouter Proxy..."

# Load configuration
if [ -f "./config/openrouter.env" ]; then
    source ./config/openrouter.env
    echo "✅ Configuration loaded"
else
    echo "❌ Configuration file not found: ./config/openrouter.env"
    exit 1
fi

# Activate virtual environment
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Please run setup-openrouter.sh first"
    exit 1
fi

# Start the proxy
echo "🌐 Starting proxy on http://localhost:${OPENROUTER_PORT:-8084}"
echo "📊 Stats available at: http://localhost:${OPENROUTER_PORT:-8084}/stats"
python ./proxy/openrouter_proxy.py
EOF

chmod +x "$START_SCRIPT"
print_status "Start script created: $START_SCRIPT"

# Create systemd service file (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
    print_step "Creating systemd service..."
    
    SERVICE_FILE="/tmp/openrouter-proxy.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=OpenRouter Proxy for Claude Code
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment=PATH=$PWD/venv/bin
ExecStart=$PWD/venv/bin/python $PWD/proxy/openrouter_proxy.py
EnvironmentFile=$PWD/config/openrouter.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    print_status "Systemd service file created: $SERVICE_FILE"
    echo "To install the service, run:"
    echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable openrouter-proxy"
    echo "  sudo systemctl start openrouter-proxy"
fi

# Test proxy startup
print_step "Testing proxy startup..."
if command -v timeout &> /dev/null; then
    # Test if the proxy can start (run for 5 seconds then kill)
    OPENROUTER_API_KEY="$OPENROUTER_API_KEY" timeout 5s python ./proxy/openrouter_proxy.py > /tmp/proxy_test.log 2>&1 &
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

# Create monitoring script
print_step "Creating monitoring script..."
MONITOR_SCRIPT="./scripts/monitor-openrouter.sh"
cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash

# OpenRouter Proxy Monitor
echo "📊 OpenRouter Proxy Monitoring Dashboard"
echo "========================================"

# Load configuration
if [ -f "./config/openrouter.env" ]; then
    source ./config/openrouter.env
else
    echo "❌ Configuration file not found"
    exit 1
fi

PROXY_URL="http://localhost:${OPENROUTER_PORT:-8084}"

# Check if proxy is running
if curl -s "$PROXY_URL/health" > /dev/null 2>&1; then
    echo "✅ Proxy is running"
    
    # Get stats
    if command -v jq &> /dev/null; then
        echo ""
        echo "📈 Statistics:"
        curl -s "$PROXY_URL/stats" | jq -r '
        "Total Requests: " + (.total_requests | tostring),
        "Provider Stats:",
        (.provider_stats | to_entries[] | "  " + .key + ": " + (.value.successful_requests | tostring) + "/" + (.value.total_requests | tostring) + " success"),
        "Recent Requests: " + (.recent_requests | length | tostring)
        '
    else
        echo ""
        echo "📈 Raw Statistics:"
        curl -s "$PROXY_URL/stats"
    fi
    
    echo ""
    echo "🔗 Available endpoints:"
    echo "  Health: $PROXY_URL/health"
    echo "  Stats:  $PROXY_URL/stats"
    echo "  Models: $PROXY_URL/v1/models"
    
else
    echo "❌ Proxy is not responding"
    echo "Start it with: ./scripts/start-openrouter.sh"
fi
EOF

chmod +x "$MONITOR_SCRIPT"
print_status "Monitoring script created: $MONITOR_SCRIPT"

# Display next steps
echo ""
echo -e "${GREEN}✅ OpenRouter setup completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Get your API key from: https://openrouter.ai/keys"
echo "2. Add credits to your account if needed"
echo "3. Start the proxy: ./scripts/start-openrouter.sh"
echo "4. Monitor usage: ./scripts/monitor-openrouter.sh"
echo "5. Test with Claude Code:"
echo "   ANTHROPIC_BASE_URL=http://localhost:8084 claude"
echo ""
echo "Configuration file: $CONFIG_FILE"
echo "Start script: $START_SCRIPT"
echo "Monitor script: $MONITOR_SCRIPT"
echo ""
echo "Available model providers:"
echo "  - Anthropic (Claude models)"
echo "  - OpenAI (GPT models)"
echo "  - Google (Gemini models)"
echo "  - Meta (Llama models)"
echo "  - And many more!"
echo ""

# Deactivate virtual environment
deactivate