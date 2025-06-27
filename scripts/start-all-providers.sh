#!/bin/bash

# Start All Provider Proxies and Intelligent Master Proxy
# =======================================================

set -e  # Exit on any error

echo "🚀 Starting Claude Code Multi-Model System..."

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
if [ ! -f "./README.md" ] || [ ! -d "./scripts" ]; then
    print_error "Please run this script from the claude-code-multimodel directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Create logs directory
mkdir -p ./logs

# Function to check if a service is running
check_service() {
    local port=$1
    local name=$2
    
    if curl -s --max-time 3 "http://localhost:$port/health" > /dev/null 2>&1; then
        print_status "✅ $name is already running on port $port"
        return 0
    else
        return 1
    fi
}

# Function to start a service and wait for it
start_service() {
    local script=$1
    local port=$2
    local name=$3
    local timeout=${4:-30}
    
    print_step "Starting $name..."
    
    # Start the service in background
    bash "$script" > "./logs/${name,,}.log" 2>&1 &
    local pid=$!
    
    # Wait for service to be ready
    local count=0
    while [ $count -lt $timeout ]; do
        if curl -s --max-time 2 "http://localhost:$port/health" > /dev/null 2>&1; then
            print_status "✅ $name started successfully on port $port (PID: $pid)"
            echo $pid > "./logs/${name,,}.pid"
            return 0
        fi
        
        # Check if process is still running
        if ! kill -0 $pid 2>/dev/null; then
            print_error "❌ $name failed to start (process died)"
            echo "Last few lines from log:"
            tail -10 "./logs/${name,,}.log"
            return 1
        fi
        
        sleep 1
        count=$((count + 1))
        
        # Show progress
        if [ $((count % 5)) -eq 0 ]; then
            echo -n "."
        fi
    done
    
    print_error "❌ $name failed to start within $timeout seconds"
    kill $pid 2>/dev/null || true
    return 1
}

# Display startup banner
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           Claude Code Multi-Model Integration System             ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  This script will start all provider proxies and the master     ║"
echo "║  intelligent proxy that provides rate limiting detection,       ║"
echo "║  auto-fallback, and cost optimization.                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
print_step "Checking prerequisites..."

if [ ! -f "./venv/bin/activate" ]; then
    print_error "Virtual environment not found. Please run setup scripts first:"
    echo "  ./scripts/setup-vertex.sh"
    echo "  ./scripts/setup-github-models.sh"
    echo "  ./scripts/setup-openrouter.sh"
    exit 1
fi

# Load API credentials
print_step "Loading API credentials..."
if [ -f "./config/credentials.env" ]; then
    source ./config/credentials.env
    print_status "✅ API credentials loaded"
    
    # Also load provider-specific configs
    [ -f "./config/vertex-ai.env" ] && source ./config/vertex-ai.env
    [ -f "./config/github-models.env" ] && source ./config/github-models.env  
    [ -f "./config/openrouter.env" ] && source ./config/openrouter.env
    
    # Set Google Application Credentials if available
    if [ ! -z "$GOOGLE_CLOUD_PROJECT" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="/tmp/vertex-ai-service-account.json"
        export GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT"
    fi
    
else
    print_warning "⚠️  No credentials found. Please run: ./scripts/setup-credentials.sh"
    print_warning "Continuing without API keys - you'll need to configure them manually"
fi

# Check for required scripts
REQUIRED_SCRIPTS=(
    "./scripts/start-vertex.sh"
    "./scripts/start-github-models.sh"
    "./scripts/start-openrouter.sh"
    "./scripts/start-intelligent-proxy.sh"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        print_error "Required script not found: $script"
        echo "Please run the setup scripts first."
        exit 1
    fi
done

print_status "Prerequisites check passed"

# Stop any existing services
print_step "Stopping any existing services..."

# Kill existing processes
for service in vertex github-models openrouter intelligent-proxy; do
    if [ -f "./logs/${service}.pid" ]; then
        local pid=$(cat "./logs/${service}.pid")
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping existing $service (PID: $pid)"
            kill $pid 2>/dev/null || true
            sleep 2
        fi
        rm -f "./logs/${service}.pid"
    fi
done

# Kill by port if needed
for port in 8081 8082 8084 8080; do
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        print_warning "Killing process on port $port (PID: $pid)"
        kill $pid 2>/dev/null || true
        sleep 1
    fi
done

print_status "Cleanup completed"

# Start services in order
echo ""
print_step "Starting provider proxies..."

# Start Vertex AI proxy (port 8081)
if ! check_service 8081 "Vertex AI Proxy"; then
    if ! start_service "./scripts/start-vertex.sh" 8081 "Vertex"; then
        print_warning "Failed to start Vertex AI proxy - continuing with other providers"
    fi
fi

# Small delay between services
sleep 2

# Start GitHub Models proxy (port 8082)
if ! check_service 8082 "GitHub Models Proxy"; then
    if ! start_service "./scripts/start-github-models.sh" 8082 "GitHub-Models"; then
        print_warning "Failed to start GitHub Models proxy - continuing with other providers"
    fi
fi

# Small delay between services
sleep 2

# Start OpenRouter proxy (port 8084)
if ! check_service 8084 "OpenRouter Proxy"; then
    if ! start_service "./scripts/start-openrouter.sh" 8084 "OpenRouter"; then
        print_warning "Failed to start OpenRouter proxy - continuing with other providers"
    fi
fi

# Wait a bit for all providers to stabilize
print_step "Waiting for providers to stabilize..."
sleep 5

# Check which providers are actually running
print_step "Checking provider status..."

VERTEX_RUNNING=0
GITHUB_RUNNING=0
OPENROUTER_RUNNING=0

if check_service 8081 "Vertex AI"; then
    VERTEX_RUNNING=1
fi

if check_service 8082 "GitHub Models"; then
    GITHUB_RUNNING=1
fi

if check_service 8084 "OpenRouter"; then
    OPENROUTER_RUNNING=1
fi

TOTAL_PROVIDERS=$((VERTEX_RUNNING + GITHUB_RUNNING + OPENROUTER_RUNNING))

if [ $TOTAL_PROVIDERS -eq 0 ]; then
    print_error "No provider proxies are running! Cannot start intelligent proxy."
    echo ""
    echo "Check the logs in ./logs/ for error details:"
    echo "  ./logs/vertex.log"
    echo "  ./logs/github-models.log"
    echo "  ./logs/openrouter.log"
    exit 1
fi

print_status "$TOTAL_PROVIDERS provider(s) are running"

# Start intelligent master proxy (port 8080)
print_step "Starting intelligent master proxy..."

if ! check_service 8080 "Intelligent Proxy"; then
    if ! start_service "./scripts/start-intelligent-proxy.sh" 8080 "Intelligent-Proxy" 45; then
        print_error "Failed to start intelligent proxy"
        echo "Check the log: ./logs/intelligent-proxy.log"
        exit 1
    fi
fi

# Final status check
echo ""
print_step "Final system status check..."

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                     System Status Summary                        ║"
echo "╠══════════════════════════════════════════════════════════════════╣"

if [ $VERTEX_RUNNING -eq 1 ]; then
    echo "║  ✅ Vertex AI Proxy     - http://localhost:8081                  ║"
else
    echo "║  ❌ Vertex AI Proxy     - Not running                           ║"
fi

if [ $GITHUB_RUNNING -eq 1 ]; then
    echo "║  ✅ GitHub Models Proxy - http://localhost:8082                  ║"
else
    echo "║  ❌ GitHub Models Proxy - Not running                           ║"
fi

if [ $OPENROUTER_RUNNING -eq 1 ]; then
    echo "║  ✅ OpenRouter Proxy    - http://localhost:8084                  ║"
else
    echo "║  ❌ OpenRouter Proxy    - Not running                           ║"
fi

if check_service 8080 "Intelligent Proxy" > /dev/null 2>&1; then
    echo "║  ✅ Intelligent Proxy   - http://localhost:8080                  ║"
    INTELLIGENT_RUNNING=1
else
    echo "║  ❌ Intelligent Proxy   - Not running                           ║"
    INTELLIGENT_RUNNING=0
fi

echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                        Quick Access URLs                         ║"
echo "╠══════════════════════════════════════════════════════════════════╣"

if [ $INTELLIGENT_RUNNING -eq 1 ]; then
    echo "║  🌐 Main API Endpoint: http://localhost:8080/v1/messages         ║"
    echo "║  📊 Health Dashboard:  http://localhost:8080/health              ║"
    echo "║  📈 Statistics:        http://localhost:8080/stats               ║"
    echo "║  📉 Metrics:           http://localhost:8090/metrics             ║"
else
    echo "║  ❌ Intelligent proxy not running - no unified endpoint          ║"
fi

echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Usage instructions
if [ $INTELLIGENT_RUNNING -eq 1 ]; then
    echo "🔧 Usage with Claude Code:"
    echo "   export ANTHROPIC_BASE_URL=http://localhost:8080"
    echo "   claude"
    echo ""
    echo "🧪 Test the system:"
    echo "   curl -X POST http://localhost:8080/v1/messages \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"model\":\"claude-3-5-sonnet-20241022\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}],\"max_tokens\":100}'"
    echo ""
    echo "📊 Monitor the system:"
    echo "   ./scripts/monitor-intelligent-proxy.sh"
    echo ""
    echo "🛑 Stop all services:"
    echo "   ./scripts/stop-all-providers.sh"
fi

# Create stop script
cat > ./scripts/stop-all-providers.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping Claude Code Multi-Model System..."

# Kill by PID files
for service in vertex github-models openrouter intelligent-proxy; do
    if [ -f "./logs/${service}.pid" ]; then
        pid=$(cat "./logs/${service}.pid")
        if kill -0 $pid 2>/dev/null; then
            echo "Stopping $service (PID: $pid)"
            kill $pid 2>/dev/null || true
        fi
        rm -f "./logs/${service}.pid"
    fi
done

# Kill by port
for port in 8080 8081 8082 8084 8090; do
    pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill $pid 2>/dev/null || true
    fi
done

echo "✅ All services stopped"
EOF

chmod +x ./scripts/stop-all-providers.sh

echo "💾 Logs are available in:"
echo "   ./logs/vertex.log"
echo "   ./logs/github-models.log" 
echo "   ./logs/openrouter.log"
echo "   ./logs/intelligent-proxy.log"
echo ""

if [ $INTELLIGENT_RUNNING -eq 1 ]; then
    print_status "🎉 Claude Code Multi-Model System is ready!"
    echo ""
    echo "The system will automatically:"
    echo "  • Detect rate limits and switch providers"
    echo "  • Optimize for cost or performance"
    echo "  • Provide detailed monitoring and analytics"
    echo "  • Handle failover between providers seamlessly"
else
    print_warning "⚠️  System started with issues. Check logs for details."
fi