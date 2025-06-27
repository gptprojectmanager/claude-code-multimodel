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
from datetime import datetime
from typing import Dict, List, Any

# Mock data for testing
MOCK_RANKINGS = [
    {
        "id": "1",
        "name": "claude-3.5-sonnet",
        "provider": "anthropic",
        "model_family": "claude",
        "context_window": 200000,
        "capabilities": {"supports_function_calling": True, "supports_vision": True},
        "min_input_cost": 3.0,
        "avg_input_cost": 3.2,
        "has_free_tier": False,
        "provider_count": 2,
        "coding_score": 0.92,
        "reasoning_score": 0.888,
        "math_score": 0.952,
        "overall_performance": 0.92,
        "avg_success_rate": 0.99,
        "avg_response_time": 850.0,
        "cost_efficiency_score": 0.77,
        "performance_score": 0.92,
        "reliability_score": 0.95,
        "availability_score": 0.8,
        "composite_score": 0.86,
        "use_case_score": 0.92,
        "value_score": 6.8,
        "overall_rank": 1,
        "use_case_rank": 1,
        "value_rank": 2,
        "cost_rank": 4,
        "total_usage_requests": 1250,
        "avg_daily_cost": 15.75,
        "ranking_timestamp": datetime.now().isoformat()
    },
    {
        "id": "2", 
        "name": "gpt-4o",
        "provider": "openai",
        "model_family": "gpt",
        "context_window": 128000,
        "capabilities": {"supports_function_calling": True, "supports_vision": True},
        "min_input_cost": 5.0,
        "avg_input_cost": 5.0,
        "has_free_tier": False,
        "provider_count": 1,
        "coding_score": 0.90,
        "reasoning_score": 0.887,
        "math_score": 0.956,
        "overall_performance": 0.91,
        "avg_success_rate": 0.98,
        "avg_response_time": 950.0,
        "cost_efficiency_score": 0.67,
        "performance_score": 0.91,
        "reliability_score": 0.92,
        "availability_score": 0.6,
        "composite_score": 0.80,
        "use_case_score": 0.90,
        "value_score": 4.2,
        "overall_rank": 2,
        "use_case_rank": 2,
        "value_rank": 4,
        "cost_rank": 6,
        "total_usage_requests": 980,
        "avg_daily_cost": 22.50,
        "ranking_timestamp": datetime.now().isoformat()
    },
    {
        "id": "3",
        "name": "deepseek-r1:free",
        "provider": "openrouter",
        "model_family": "deepseek",
        "context_window": 32768,
        "capabilities": {"supports_function_calling": True},
        "min_input_cost": 0.0,
        "avg_input_cost": 0.0,
        "has_free_tier": True,
        "provider_count": 1,
        "coding_score": 0.75,
        "reasoning_score": 0.78,
        "math_score": 0.82,
        "overall_performance": 0.78,
        "avg_success_rate": 0.96,
        "avg_response_time": 1200.0,
        "cost_efficiency_score": 1.0,
        "performance_score": 0.78,
        "reliability_score": 0.85,
        "availability_score": 0.6,
        "composite_score": 0.81,
        "use_case_score": 0.75,
        "value_score": 15.6,
        "overall_rank": 3,
        "use_case_rank": 3,
        "value_rank": 1,
        "cost_rank": 1,
        "total_usage_requests": 650,
        "avg_daily_cost": 0.0,
        "ranking_timestamp": datetime.now().isoformat()
    },
    {
        "id": "4",
        "name": "claude-3-haiku",
        "provider": "anthropic",
        "model_family": "claude",
        "context_window": 200000,
        "capabilities": {"supports_function_calling": True},
        "min_input_cost": 0.25,
        "avg_input_cost": 0.25,
        "has_free_tier": False,
        "provider_count": 2,
        "coding_score": 0.75,
        "reasoning_score": 0.752,
        "math_score": 0.882,
        "overall_performance": 0.76,
        "avg_success_rate": 0.99,
        "avg_response_time": 650.0,
        "cost_efficiency_score": 0.98,
        "performance_score": 0.76,
        "reliability_score": 0.98,
        "availability_score": 0.8,
        "composite_score": 0.84,
        "use_case_score": 0.75,
        "value_score": 8.2,
        "overall_rank": 4,
        "use_case_rank": 4,
        "value_rank": 3,
        "cost_rank": 2,
        "total_usage_requests": 890,
        "avg_daily_cost": 3.25,
        "ranking_timestamp": datetime.now().isoformat()
    },
    {
        "id": "5",
        "name": "qwen-2.5-coder:free",
        "provider": "openrouter",
        "model_family": "qwen",
        "context_window": 32768,
        "capabilities": {"supports_function_calling": True},
        "min_input_cost": 0.0,
        "avg_input_cost": 0.0,
        "has_free_tier": True,
        "provider_count": 1,
        "coding_score": 0.88,
        "reasoning_score": 0.72,
        "math_score": 0.76,
        "overall_performance": 0.79,
        "avg_success_rate": 0.97,
        "avg_response_time": 1100.0,
        "cost_efficiency_score": 1.0,
        "performance_score": 0.79,
        "reliability_score": 0.87,
        "availability_score": 0.6,
        "composite_score": 0.82,
        "use_case_score": 0.88,
        "value_score": 17.8,
        "overall_rank": 5,
        "use_case_rank": 1,
        "value_rank": 1,
        "cost_rank": 1,
        "total_usage_requests": 420,
        "avg_daily_cost": 0.0,
        "ranking_timestamp": datetime.now().isoformat()
    }
]

MOCK_PROVIDERS = {
    "claude-3.5-sonnet": [
        {
            "provider_name": "anthropic",
            "provider_id": "anthropic-api",
            "input_price_per_million": 3.0,
            "output_price_per_million": 15.0,
            "is_free_tier": False,
            "recent_success_rate": 0.99,
            "recent_response_time": 850.0,
            "availability_score": 1.0,
            "selection_probability": 0.69,
            "provider_rank": 1,
            "cost_advantage_percent": 12.5,
            "rate_limits": {"requests_per_minute": 100, "tokens_per_minute": 500000},
            "provider_metadata": {"region": "us-east-1", "model_version": "20241022"},
            "routing_timestamp": datetime.now().isoformat()
        },
        {
            "provider_name": "openrouter",
            "provider_id": "openrouter-anthropic",
            "input_price_per_million": 3.5,
            "output_price_per_million": 16.0,
            "is_free_tier": False,
            "recent_success_rate": 0.97,
            "recent_response_time": 1100.0,
            "availability_score": 0.8,
            "selection_probability": 0.31,
            "provider_rank": 2,
            "cost_advantage_percent": -2.8,
            "rate_limits": {"requests_per_minute": 200, "tokens_per_minute": 100000},
            "provider_metadata": {"openrouter_routing": True, "fallback_available": True},
            "routing_timestamp": datetime.now().isoformat()
        }
    ]
}

MOCK_RECOMMENDATIONS = [
    {
        "recommendation_type": "free_tier",
        "potential_savings_usd": 90.0,
        "recommended_models": ["deepseek-r1:free", "qwen-2.5-coder:free"],
        "explanation": "Switch to free tier models for non-critical tasks to reduce costs",
        "priority": "high",
        "confidence": 0.9
    },
    {
        "recommendation_type": "cost_efficiency",
        "potential_savings_usd": 40.0,
        "recommended_models": ["claude-3-haiku", "gpt-4o-mini"],
        "explanation": "Use cost-efficient models for routine tasks",
        "priority": "medium",
        "confidence": 0.8
    },
    {
        "recommendation_type": "performance_optimization",
        "potential_savings_usd": None,
        "recommended_models": ["claude-3.5-sonnet", "gpt-4o"],
        "explanation": "Use top-performing models for critical tasks requiring highest quality",
        "priority": "medium",
        "confidence": 0.85
    }
]

MOCK_BENCHMARKS = [
    {
        "model_name": "claude-3.5-sonnet",
        "benchmark_name": "HumanEval",
        "benchmark_category": "coding",
        "metric_type": "pass@1",
        "score": 0.92,
        "normalized_score": 0.92,
        "test_date": "2024-06-27",
        "source_organization": "anthropic",
        "is_verified": True
    },
    {
        "model_name": "gpt-4o",
        "benchmark_name": "MMLU",
        "benchmark_category": "reasoning", 
        "metric_type": "accuracy",
        "score": 0.887,
        "normalized_score": 0.887,
        "test_date": "2024-06-27",
        "source_organization": "openai",
        "is_verified": True
    },
    {
        "model_name": "claude-3.5-sonnet",
        "benchmark_name": "GSM8K",
        "benchmark_category": "math",
        "metric_type": "accuracy",
        "score": 0.952,
        "normalized_score": 0.952,
        "test_date": "2024-06-27",
        "source_organization": "anthropic",
        "is_verified": True
    }
]

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
                
                filtered_rankings = MOCK_RANKINGS.copy()
                
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
                response_data = MOCK_PROVIDERS.get(model_name, [])
                
            elif path == '/recommendations':
                current_usage = float(query_params.get('current_usage_usd', ['100.0'])[0])
                response_data = MOCK_RECOMMENDATIONS
                
            elif path == '/benchmarks':
                benchmark_category = query_params.get('benchmark_category', [None])[0]
                
                filtered_benchmarks = MOCK_BENCHMARKS.copy()
                if benchmark_category:
                    filtered_benchmarks = [b for b in filtered_benchmarks if b['benchmark_category'] == benchmark_category]
                    
                response_data = filtered_benchmarks
                
            elif path == '/rankings/top-free':
                limit = int(query_params.get('limit', ['5'])[0])
                free_models = [r for r in MOCK_RANKINGS if r['has_free_tier']]
                response_data = free_models[:limit]
                
            elif path == '/rankings/best-value':
                limit = int(query_params.get('limit', ['5'])[0])
                sorted_by_value = sorted(MOCK_RANKINGS, key=lambda x: x['value_score'], reverse=True)
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

def start_server(port=8055):
    """Start the test server"""
    handler = LLMIntelligenceHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🚀 LLM Intelligence Test Server starting on port {port}")
            print(f"📊 Dashboard URL: http://localhost:{port}/")
            print(f"🔗 API Endpoints:")
            print(f"  • Rankings: http://localhost:{port}/rankings")
            print(f"  • Providers: http://localhost:{port}/providers/claude-3.5-sonnet")
            print(f"  • Recommendations: http://localhost:{port}/recommendations")
            print(f"  • Benchmarks: http://localhost:{port}/benchmarks")
            print(f"  • Health: http://localhost:{port}/health")
            print(f"\n✅ Server ready! Press Ctrl+C to stop.")
            
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