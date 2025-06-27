#!/usr/bin/env python3
"""
Dashboard Web Server for LAN Access
==================================

Serves the HTML dashboard on port 8056 for LAN access.
The API runs on port 8055, dashboard on 8056.
"""

import http.server
import socketserver
import os
import sys

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='dashboard', **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def serve_dashboard(port=8056, host="0.0.0.0"):
    """Serve the dashboard on LAN"""
    
    # Check if dashboard directory exists
    dashboard_dir = 'dashboard'
    if not os.path.exists(dashboard_dir):
        print(f"❌ Error: {dashboard_dir} directory not found")
        print("Make sure you're running from the llm_intelligence directory")
        return
        
    if not os.path.exists(os.path.join(dashboard_dir, 'realtime_dashboard.html')):
        print(f"❌ Error: realtime_dashboard.html not found in {dashboard_dir}/")
        return
    
    try:
        with socketserver.TCPServer((host, port), DashboardHandler) as httpd:
            print(f"🎨 Dashboard Server starting on {host}:{port}")
            print(f"📊 Local Dashboard: http://localhost:{port}/realtime_dashboard.html")
            print(f"🌐 LAN Dashboard: http://192.168.1.100:{port}/realtime_dashboard.html")
            print(f"📱 Mobile Access: http://192.168.1.100:{port}/realtime_dashboard.html")
            print(f"\n💡 Make sure the API server is running on port 8055!")
            print(f"✅ Dashboard ready! Press Ctrl+C to stop.")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n🛑 Dashboard server stopped")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Error: Port {port} is already in use")
            print(f"💡 Try: python3 serve_dashboard.py --port 8057")
        else:
            print(f"❌ Error starting dashboard server: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    port = 8056
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    print("❌ Invalid port number")
                    sys.exit(1)
    
    serve_dashboard(port)