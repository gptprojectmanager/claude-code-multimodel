#!/bin/bash
# Start all multi-port Claude Code services
# Services: GitHub Models (8092), OpenRouter (8093)
# Note: Vertex services (8090, 8091) will be added in Task 4

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting Multi-Port Claude Code Services..."
echo "==============================================="

# Check if required environment variables are set
echo "🔍 Checking environment variables..."

# Check GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️ GITHUB_TOKEN not set - GitHub Models service may not work"
fi

# Check OpenRouter API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️ OPENROUTER_API_KEY not set - OpenRouter service will not work"
fi

echo ""

# Function to start service in background
start_service() {
    local service_name=$1
    local port=$2
    local config_file=$3
    
    echo "🔧 Starting $service_name on port $port..."
    
    # Start service in background and capture PID
    nohup "$SCRIPT_DIR/start-service.sh" "$service_name" "$port" "$config_file" \
        > "/tmp/${service_name}.log" 2>&1 &
    
    local pid=$!
    echo "   PID: $pid"
    
    # Give service time to start
    sleep 2
    
    # Check if service is still running
    if kill -0 $pid 2>/dev/null; then
        echo "✅ $service_name started successfully"
    else
        echo "❌ $service_name failed to start"
        echo "   Check log: /tmp/${service_name}.log"
        return 1
    fi
    
    return 0
}

# Start services
echo "📦 Starting available services..."
echo ""

# Start GitHub Models service (Port 8092)
if start_service "github_models" "8092" "github-models.env"; then
    GITHUB_STARTED=true
else
    GITHUB_STARTED=false
fi

echo ""

# Start OpenRouter service (Port 8093)
if start_service "openrouter" "8093" "openrouter.env"; then
    OPENROUTER_STARTED=true
else
    OPENROUTER_STARTED=false
fi

echo ""

# Wait for services to fully initialize
echo "⏳ Waiting for services to initialize..."
sleep 5

# Health check all started services
echo ""
echo "🏥 Health checking services..."
echo "=============================="

health_check() {
    local service_name=$1
    local port=$2
    
    echo -n "   $service_name (port $port): "
    
    if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

HEALTHY_COUNT=0
TOTAL_COUNT=0

if [ "$GITHUB_STARTED" = true ]; then
    ((TOTAL_COUNT++))
    if health_check "GitHub Models" "8092"; then
        ((HEALTHY_COUNT++))
    fi
fi

if [ "$OPENROUTER_STARTED" = true ]; then
    ((TOTAL_COUNT++))
    if health_check "OpenRouter" "8093"; then
        ((HEALTHY_COUNT++))
    fi
fi

echo ""
echo "📊 Service Status Summary"
echo "========================"
echo "   Healthy services: $HEALTHY_COUNT/$TOTAL_COUNT"

if [ $HEALTHY_COUNT -eq $TOTAL_COUNT ] && [ $TOTAL_COUNT -gt 0 ]; then
    echo "🎯 All services are running successfully!"
    echo ""
    echo "📡 Available endpoints:"
    [ "$GITHUB_STARTED" = true ] && echo "   GitHub Models: http://localhost:8092"
    [ "$OPENROUTER_STARTED" = true ] && echo "   OpenRouter:    http://localhost:8093"
    echo ""
    echo "🔧 Test with:"
    echo "   curl http://localhost:8092/health"
    echo "   curl http://localhost:8093/health"
    echo ""
    echo "📄 View logs:"
    echo "   tail -f /tmp/github_models.log"
    echo "   tail -f /tmp/openrouter.log"
else
    echo "⚠️ Some services failed to start or are unhealthy"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   1. Check environment variables (GITHUB_TOKEN, OPENROUTER_API_KEY)"
    echo "   2. Check logs in /tmp/<service_name>.log"
    echo "   3. Verify ports are not in use: netstat -tlnp | grep -E ':(8092|8093)'"
    exit 1
fi