#!/bin/bash

# Start Intelligent Multi-Model Proxy
# ===================================

set -e  # Exit on any error

echo "🚀 Starting Claude Code Intelligent Multi-Model Proxy..."

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
if [ ! -f "./core/intelligent_proxy.py" ]; then
    print_error "Please run this script from the claude-code-multimodel directory"
    echo "Current directory: $(pwd)"
    echo "Expected files: ./core/intelligent_proxy.py"
    exit 1
fi

# Check if Python virtual environment exists
print_step "Checking Python environment..."
if [ ! -f "./venv/bin/activate" ]; then
    print_error "Virtual environment not found"
    echo "Please run setup scripts first:"
    echo "  ./scripts/setup-vertex.sh"
    echo "  ./scripts/setup-github-models.sh"
    echo "  ./scripts/setup-openrouter.sh"
    exit 1
fi

# Activate virtual environment
source ./venv/bin/activate
print_status "Virtual environment activated"

# Check if dependencies are installed
print_step "Checking dependencies..."
if ! python -c "import fastapi, uvicorn, httpx, structlog, prometheus_client" 2>/dev/null; then
    print_warning "Installing missing dependencies..."
    pip install fastapi uvicorn httpx structlog prometheus-client psutil > /dev/null 2>&1
fi

# Load configuration and credentials
print_step "Loading configuration and credentials..."

# Load API credentials first
if [ -f "./config/credentials.env" ]; then
    source ./config/credentials.env
    print_status "✅ API credentials loaded"
    
    # Also load provider-specific configs
    [ -f "./config/vertex-ai.env" ] && source ./config/vertex-ai.env
    [ -f "./config/github-models.env" ] && source ./config/github-models.env  
    [ -f "./config/openrouter.env" ] && source ./config/openrouter.env
    [ -f "./config/claude-code-integration.env" ] && source ./config/claude-code-integration.env
    
else
    print_warning "⚠️  No credentials found. Please run: ./scripts/setup-credentials.sh"
fi

# Set default values (can be overridden by credentials.env)
export PROXY_HOST=${PROXY_HOST:-"0.0.0.0"}
export PROXY_PORT=${PROXY_PORT:-"8080"}
export ENABLE_AUTHENTICATION=${ENABLE_AUTHENTICATION:-"false"}
export MASTER_PROXY_API_KEY=${MASTER_PROXY_API_KEY:-"proxy-key-12345"}
export MAX_CONCURRENT_REQUESTS=${MAX_CONCURRENT_REQUESTS:-"100"}
export REQUEST_TIMEOUT=${REQUEST_TIMEOUT:-"300"}
export DEFAULT_ROUTING_STRATEGY=${DEFAULT_ROUTING_STRATEGY:-"intelligent"}
export ENABLE_COST_TRACKING=${ENABLE_COST_TRACKING:-"true"}

# Provider endpoints
export VERTEX_PROXY_URL=${VERTEX_PROXY_URL:-"http://localhost:8081"}
export GITHUB_PROXY_URL=${GITHUB_PROXY_URL:-"http://localhost:8082"}
export OPENROUTER_PROXY_URL=${OPENROUTER_PROXY_URL:-"http://localhost:8084"}

# Routing configuration
export ROUTING_STRATEGY=${ROUTING_STRATEGY:-"intelligent"}
export ENABLE_AUTO_FALLBACK=${ENABLE_AUTO_FALLBACK:-"true"}
export MAX_FALLBACK_ATTEMPTS=${MAX_FALLBACK_ATTEMPTS:-"3"}
export FALLBACK_DELAY=${FALLBACK_DELAY:-"1.0"}

# Rate limiting
export RATE_LIMIT_DETECTION_WINDOW=${RATE_LIMIT_DETECTION_WINDOW:-"60"}
export RATE_LIMIT_THRESHOLD=${RATE_LIMIT_THRESHOLD:-"0.8"}

# Cost optimization
export ENABLE_COST_OPTIMIZATION=${ENABLE_COST_OPTIMIZATION:-"true"}
export MAX_COST_PER_REQUEST=${MAX_COST_PER_REQUEST:-"1.0"}

print_status "Configuration loaded"

# Check provider availability
print_step "Checking provider availability..."

check_provider() {
    local name=$1
    local url=$2
    local timeout=5
    
    if curl -s --max-time $timeout "$url/health" > /dev/null 2>&1; then
        print_status "✅ $name proxy is running ($url)"
        return 0
    else
        print_warning "⚠️  $name proxy not available ($url)"
        return 1
    fi
}

# Check each provider
VERTEX_AVAILABLE=0
GITHUB_AVAILABLE=0
OPENROUTER_AVAILABLE=0

if check_provider "Vertex AI" "$VERTEX_PROXY_URL"; then
    VERTEX_AVAILABLE=1
fi

if check_provider "GitHub Models" "$GITHUB_PROXY_URL"; then
    GITHUB_AVAILABLE=1
fi

if check_provider "OpenRouter" "$OPENROUTER_PROXY_URL"; then
    OPENROUTER_AVAILABLE=1
fi

# Warn if no providers are available
TOTAL_AVAILABLE=$((VERTEX_AVAILABLE + GITHUB_AVAILABLE + OPENROUTER_AVAILABLE))
if [ $TOTAL_AVAILABLE -eq 0 ]; then
    print_error "No provider proxies are running!"
    echo ""
    echo "Please start the provider proxies first:"
    echo "  ./scripts/start-vertex.sh &"
    echo "  ./scripts/start-github-models.sh &"
    echo "  ./scripts/start-openrouter.sh &"
    echo ""
    echo "Or run the quick start script:"
    echo "  ./scripts/start-all-providers.sh"
    exit 1
elif [ $TOTAL_AVAILABLE -eq 1 ]; then
    print_warning "Only 1 provider available - fallback options will be limited"
else
    print_status "$TOTAL_AVAILABLE providers available - full fallback capability enabled"
fi

# Start cost tracking if enabled
if [ "$ENABLE_COST_TRACKING" = "true" ]; then
    print_step "Starting cost tracking..."
    
    # Start Prometheus metrics server in background
    if command -v python &> /dev/null; then
        python -c "
import sys
sys.path.append('./monitoring')
from cost_tracker import CostTracker
tracker = CostTracker()
tracker.start_prometheus_server(8090)
print('Prometheus metrics server started on port 8090')
" > /tmp/cost_tracker.log 2>&1 &
        
        sleep 2
        if curl -s http://localhost:8090/metrics > /dev/null 2>&1; then
            print_status "✅ Cost tracking and metrics server started (port 8090)"
        else
            print_warning "⚠️  Cost tracking metrics server may not be running"
        fi
    fi
fi

# Create startup banner
print_step "Starting intelligent proxy..."
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                Claude Code Intelligent Multi-Model Proxy         ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  🌐 Proxy URL: http://${PROXY_HOST}:${PROXY_PORT}                                     ║"
echo "║  📊 Health Check: http://${PROXY_HOST}:${PROXY_PORT}/health                           ║"
echo "║  📈 Statistics: http://${PROXY_HOST}:${PROXY_PORT}/stats                             ║"
echo "║  🔧 Routing Strategy: ${DEFAULT_ROUTING_STRATEGY}                                   ║"
echo "║  💰 Cost Tracking: ${ENABLE_COST_TRACKING}                                        ║"
echo "║  🔄 Auto Fallback: ${ENABLE_AUTO_FALLBACK}                                        ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Available Providers:                                            ║"
if [ $VERTEX_AVAILABLE -eq 1 ]; then
    echo "║    ✅ Google Vertex AI                                           ║"
else
    echo "║    ❌ Google Vertex AI                                           ║"
fi
if [ $GITHUB_AVAILABLE -eq 1 ]; then
    echo "║    ✅ GitHub Models                                              ║"
else
    echo "║    ❌ GitHub Models                                              ║"
fi
if [ $OPENROUTER_AVAILABLE -eq 1 ]; then
    echo "║    ✅ OpenRouter                                                 ║"
else
    echo "║    ❌ OpenRouter                                                 ║"
fi
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Usage examples
echo "🔧 Usage Examples:"
echo ""
echo "1. Use with Claude Code:"
echo "   export ANTHROPIC_BASE_URL=http://localhost:${PROXY_PORT}"
echo "   claude"
echo ""
echo "2. Test with curl:"
echo "   curl -X POST http://localhost:${PROXY_PORT}/v1/messages \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"model\":\"claude-3-5-sonnet-20241022\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}],\"max_tokens\":100}'"
echo ""
echo "3. Change routing strategy:"
echo "   curl -X POST http://localhost:${PROXY_PORT}/admin/routing-strategy \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"strategy\":\"cost\"}'"
echo ""
echo "4. Monitor in real-time:"
echo "   watch curl -s http://localhost:${PROXY_PORT}/health"
echo ""

# Create a simple monitoring script
cat > ./scripts/monitor-intelligent-proxy.sh << 'EOF'
#!/bin/bash

# Monitor Intelligent Proxy
echo "📊 Claude Code Intelligent Proxy Monitor"
echo "========================================"

PROXY_URL="http://localhost:${PROXY_PORT:-8080}"

while true; do
    clear
    echo "📊 Claude Code Intelligent Proxy Monitor"
    echo "========================================"
    echo "Time: $(date)"
    echo ""
    
    # Health check
    if curl -s "$PROXY_URL/health" > /tmp/proxy_health.json 2>&1; then
        echo "✅ Proxy Status: HEALTHY"
        
        if command -v jq &> /dev/null; then
            echo ""
            echo "📈 Statistics:"
            jq -r '
            "Active Requests: " + (.active_requests | tostring),
            "Total Requests: " + (.stats.total_requests | tostring),
            "Success Rate: " + ((.stats.successful_requests / .stats.total_requests * 100) | tostring | .[0:5]) + "%",
            "Fallback Rate: " + ((.stats.fallback_requests / .stats.total_requests * 100) | tostring | .[0:5]) + "%"
            ' /tmp/proxy_health.json
            
            echo ""
            echo "🔧 Provider Health:"
            jq -r '.provider_health | to_entries[] | "  " + .key + ": " + .value.status + " (" + (.value.success_rate * 100 | tostring | .[0:5]) + "% success)"' /tmp/proxy_health.json
        else
            echo ""
            echo "Raw health data:"
            cat /tmp/proxy_health.json | head -20
        fi
    else
        echo "❌ Proxy Status: UNAVAILABLE"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done
EOF

chmod +x ./scripts/monitor-intelligent-proxy.sh
print_status "Monitor script created: ./scripts/monitor-intelligent-proxy.sh"

# Start the proxy
echo "🚀 Starting proxy server..."
echo ""

# Set Python path to include our modules
export PYTHONPATH="${PYTHONPATH}:$(pwd)/core:$(pwd)/monitoring"

# Start the intelligent proxy
python ./core/intelligent_proxy.py