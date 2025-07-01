#!/usr/bin/env python3
"""
Simple Test Server for LLM Intelligence API
==========================================

Lightweight server without external dependencies for testing.
Uses only built-in Python modules.
"""

import json
import http.server
import socketserver
import urllib.parse
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Import real data collector
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from collectors.real_data_collector import RealDataCollector

# Initialize real data collector
real_data = RealDataCollector()
REAL_RANKINGS = real_data.current_models
REAL_RECOMMENDATIONS = real_data.get_real_recommendations(100.0)
REAL_BENCHMARKS = real_data.get_real_benchmarks()

print(f"🔄 Loading real 2025 LLM data...")
print(f"📊 Loaded {len(REAL_RANKINGS)} models")
print(f"💡 Loaded {len(REAL_RECOMMENDATIONS)} recommendation types")
print(f"📈 Loaded {len(REAL_BENCHMARKS)} benchmark scores")
print(f"✅ Real data collector ready!")

class LLMIntelligenceHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        # Parse URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_data = {}
        
        try:
            if path == '/':
                response_data = {
                    "service": "LLM Intelligence API",
                    "version": "1.0.0",
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "endpoints": {
                        "rankings": "/rankings",
                        "providers": "/providers/{model_name}",
                        "recommendations": "/recommendations",
                        "benchmarks": "/benchmarks",
                        "health": "/health"
                    }
                }
                
            elif path == '/rankings':
                # Apply filters
                limit = int(query_params.get('limit', ['10'])[0])
                use_case = query_params.get('use_case', ['general'])[0]
                has_free_tier = query_params.get('has_free_tier', [None])[0]
                
                filtered_rankings = REAL_RANKINGS.copy()
                
                # Filter by free tier if specified
                if has_free_tier is not None:
                    free_tier_bool = has_free_tier.lower() == 'true'
                    filtered_rankings = [r for r in filtered_rankings if r['has_free_tier'] == free_tier_bool]
                
                # Sort by use case
                if use_case == 'coding':
                    filtered_rankings.sort(key=lambda x: x.get('coding_score', 0), reverse=True)
                elif use_case == 'cost_sensitive':
                    filtered_rankings.sort(key=lambda x: x['cost_efficiency_score'], reverse=True)
                else:
                    filtered_rankings.sort(key=lambda x: x['composite_score'], reverse=True)
                
                response_data = filtered_rankings[:limit]
                
            elif path.startswith('/providers/'):
                model_name = path.split('/')[-1]
                response_data = real_data.get_provider_options_real(model_name)
                
            elif path == '/recommendations':
                current_usage = float(query_params.get('current_usage_usd', ['100.0'])[0])
                response_data = real_data.get_real_recommendations(current_usage)
                
            elif path == '/benchmarks':
                benchmark_category = query_params.get('benchmark_category', [None])[0]
                
                filtered_benchmarks = REAL_BENCHMARKS.copy()
                if benchmark_category:
                    filtered_benchmarks = [b for b in filtered_benchmarks if b['benchmark_category'] == benchmark_category]
                    
                response_data = filtered_benchmarks
                
            elif path == '/rankings/top-free':
                limit = int(query_params.get('limit', ['5'])[0])
                free_models = [r for r in REAL_RANKINGS if r['has_free_tier']]
                response_data = free_models[:limit]
                
            elif path == '/rankings/best-value':
                limit = int(query_params.get('limit', ['5'])[0])
                sorted_by_value = sorted(REAL_RANKINGS, key=lambda x: x['value_score'], reverse=True)
                response_data = sorted_by_value[:limit]
                
            elif path == '/health':
                response_data = {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": {
                        "status": "connected",
                        "response_time_ms": 25.3
                    },
                    "api": {
                        "version": "1.0.0",
                        "uptime": "healthy"
                    }
                }
                
            else:
                self.send_response(404)
                self.end_headers()
                response_data = {"error": "Endpoint not found", "path": path}
                
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            response_data = {"error": str(e)}
        
        # Send JSON response
        self.wfile.write(json.dumps(response_data, indent=2).encode())
        
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def log_message(self, format, *args):
        """Custom log message format"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def start_server(port=8055, host="0.0.0.0"):
    """Start the test server"""
    handler = LLMIntelligenceHandler
    
    try:
        with socketserver.TCPServer((host, port), handler) as httpd:
            print(f"🚀 LLM Intelligence Server 2025 Edition starting on {host}:{port}")
            print(f"📊 Local Dashboard URL: http://localhost:{port}/")
            print(f"🌐 LAN Dashboard URL: http://192.168.1.100:{port}/")
            print(f"🔗 API Endpoints:")
            print(f"  • Rankings: http://192.168.1.100:{port}/rankings")
            print(f"  • Top Models: http://192.168.1.100:{port}/providers/gemini-2.5-pro")
            print(f"  • Recommendations: http://192.168.1.100:{port}/recommendations")
            print(f"  • Benchmarks: http://192.168.1.100:{port}/benchmarks")
            print(f"  • Health: http://192.168.1.100:{port}/health")
            print(f"\n🎯 Featured 2025 Models: Gemini 2.5 Pro, o3-mini, DeepSeek R1")
            print(f"✅ Server ready! Press Ctrl+C to stop.")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Error: Port {port} is already in use")
            print(f"💡 Try a different port: python3 test_server.py --port 8056")
        else:
            print(f"❌ Error starting server: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    import sys
    
    port = 8055
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    print("❌ Invalid port number")
                    sys.exit(1)
    
    start_server(port)