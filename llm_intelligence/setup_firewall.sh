#!/bin/bash

# Firewall Setup for LLM Intelligence LAN Access
# Opens necessary ports for API and Dashboard access from LAN

echo "🔥 Setting up firewall rules for LLM Intelligence System"
echo "======================================================="

# Check if ufw is installed
if ! command -v ufw &> /dev/null; then
    echo "⚠️  UFW not found. Firewall rules not applied."
    echo "💡 Install with: sudo apt install ufw"
    exit 0
fi

# Check if running as root/sudo
if [[ $EUID -ne 0 ]]; then
   echo "🔐 This script needs sudo privileges to modify firewall rules"
   echo "💡 Run with: sudo ./setup_firewall.sh"
   exit 1
fi

echo "🔧 Current UFW status:"
ufw status

echo ""
echo "🌐 Opening ports for LAN access..."

# Open API port (8055)
echo "📡 Opening port 8055 for API server..."
ufw allow from 192.168.1.0/24 to any port 8055
echo "✅ Port 8055 opened for 192.168.1.x network"

# Open Dashboard port (8056)
echo "🎨 Opening port 8056 for Dashboard server..."
ufw allow from 192.168.1.0/24 to any port 8056
echo "✅ Port 8056 opened for 192.168.1.x network"

# Optional: Open for broader LAN access (common private networks)
read -p "🤔 Also open for 192.168.0.x and 10.0.0.x networks? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ufw allow from 192.168.0.0/24 to any port 8055
    ufw allow from 192.168.0.0/24 to any port 8056
    ufw allow from 10.0.0.0/8 to any port 8055
    ufw allow from 10.0.0.0/8 to any port 8056
    echo "✅ Opened for additional private networks"
fi

# Enable UFW if not already enabled
if ! ufw status | grep -q "Status: active"; then
    read -p "🔥 UFW is inactive. Enable now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ufw --force enable
        echo "✅ UFW enabled"
    fi
fi

echo ""
echo "🎉 Firewall setup complete!"
echo "📊 Current rules:"
ufw status numbered

echo ""
echo "🔗 Your LLM Intelligence system should now be accessible from:"
echo "  • Dashboard: http://192.168.1.100:8056/realtime_dashboard.html"
echo "  • API:       http://192.168.1.100:8055/health"
echo ""
echo "💡 To remove these rules later:"
echo "  sudo ufw delete allow from 192.168.1.0/24 to any port 8055"
echo "  sudo ufw delete allow from 192.168.1.0/24 to any port 8056"