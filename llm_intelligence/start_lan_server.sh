#!/bin/bash

# LLM Intelligence LAN Server Launcher
# Starts both API server (8055) and Dashboard server (8056) for LAN access

echo "🌐 Starting LLM Intelligence System for LAN Access"
echo "=================================================="

# Check if running as root (needed for ports < 1024)
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  Warning: Running as root. Consider using ports > 1024 for security."
fi

# Default ports
API_PORT=8055
DASHBOARD_PORT=8056

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-port)
            API_PORT="$2"
            shift 2
            ;;
        --dashboard-port)
            DASHBOARD_PORT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--api-port 8055] [--dashboard-port 8056]"
            echo ""
            echo "Options:"
            echo "  --api-port PORT        Port for API server (default: 8055)"
            echo "  --dashboard-port PORT  Port for Dashboard server (default: 8056)"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if ports are available
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        echo "❌ Error: Port $port is already in use (needed for $service)"
        echo "💡 Use different ports: $0 --api-port 8057 --dashboard-port 8058"
        return 1
    fi
    echo "✅ Port $port is available for $service"
    return 0
}

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "💡 Install: sudo apt install python3"
    exit 1
fi

echo "✅ Python3 found: $(python3 --version)"

# Check ports
check_port $API_PORT "API Server" || exit 1
check_port $DASHBOARD_PORT "Dashboard Server" || exit 1

# Check if dashboard directory exists
if [ ! -d "dashboard" ]; then
    echo "❌ Error: dashboard directory not found"
    echo "💡 Make sure you're in the llm_intelligence directory"
    exit 1
fi

# Get the server's actual IP
SERVER_IP=$(hostname -I | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="192.168.1.100"  # Fallback
fi

echo "🔧 Configuration:"
echo "  • Server IP: $SERVER_IP"
echo "  • API Port: $API_PORT"
echo "  • Dashboard Port: $DASHBOARD_PORT"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo "  ✅ API server stopped"
    fi
    if [ ! -z "$DASHBOARD_PID" ]; then
        kill $DASHBOARD_PID 2>/dev/null
        echo "  ✅ Dashboard server stopped"
    fi
    echo "👋 Goodbye!"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Start API server in background
echo "🚀 Starting API Server on port $API_PORT..."
python3 test_server.py --port $API_PORT > api_server.log 2>&1 &
API_PID=$!

# Wait a moment for API server to start
sleep 2

# Check if API server started successfully
if ! ps -p $API_PID > /dev/null; then
    echo "❌ Error: API server failed to start"
    echo "📋 Check api_server.log for details"
    exit 1
fi

echo "✅ API Server started (PID: $API_PID)"

# Start Dashboard server in background
echo "🎨 Starting Dashboard Server on port $DASHBOARD_PORT..."
python3 serve_dashboard.py --port $DASHBOARD_PORT > dashboard_server.log 2>&1 &
DASHBOARD_PID=$!

# Wait a moment for dashboard server to start
sleep 2

# Check if dashboard server started successfully
if ! ps -p $DASHBOARD_PID > /dev/null; then
    echo "❌ Error: Dashboard server failed to start"
    echo "📋 Check dashboard_server.log for details"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo "✅ Dashboard Server started (PID: $DASHBOARD_PID)"
echo ""

# Display access information
echo "🎉 LLM Intelligence System is ready for LAN access!"
echo "=" * 60
echo ""
echo "📊 Dashboard Access:"
echo "  • Local:   http://localhost:$DASHBOARD_PORT/realtime_dashboard.html"
echo "  • LAN:     http://$SERVER_IP:$DASHBOARD_PORT/realtime_dashboard.html"
echo "  • Mobile:  http://$SERVER_IP:$DASHBOARD_PORT/realtime_dashboard.html"
echo ""
echo "🔗 API Endpoints:"
echo "  • Health:  http://$SERVER_IP:$API_PORT/health"
echo "  • Rankings:http://$SERVER_IP:$API_PORT/rankings"
echo "  • Docs:    http://$SERVER_IP:$API_PORT/"
echo ""
echo "📱 Connect from any device in your LAN (192.168.1.x network)"
echo "🔥 Real-time updates every 30 seconds"
echo ""
echo "📋 Server Logs:"
echo "  • API:       tail -f api_server.log"
echo "  • Dashboard: tail -f dashboard_server.log"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "=================================="

# Wait for user to stop
wait