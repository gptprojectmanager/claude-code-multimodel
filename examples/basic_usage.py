#!/usr/bin/env python3
"""
Basic usage examples for Claude Code Multi-Model Integration
"""

import os
import asyncio
import httpx

# Example 1: Basic API call
async def basic_api_call():
    """Make a basic API call to the intelligent proxy"""
    
    url = "http://localhost:8080/v1/messages"
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "messages": [
            {
                "role": "user", 
                "content": "Hello! Can you explain what quantum computing is in simple terms?"
            }
        ],
        "max_tokens": 200
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        print("Response Status:", response.status_code)
        print("Response:", response.json())

# Example 2: Check system health
async def check_system_health():
    """Check the health of the intelligent proxy system"""
    
    url = "http://localhost:8080/health"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        health_data = response.json()
        
        print("System Status:", health_data.get("status"))
        print("Active Requests:", health_data.get("active_requests"))
        
        print("\nProvider Health:")
        for provider, health in health_data.get("provider_health", {}).items():
            print(f"  {provider}: {health.get('status')} ({health.get('success_rate', 0)*100:.1f}% success)")

# Example 3: Get system statistics
async def get_system_stats():
    """Get detailed system statistics"""
    
    url = "http://localhost:8080/stats"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        stats = response.json()
        
        request_stats = stats.get("request_stats", {})
        print("System Statistics:")
        print(f"  Total Requests: {request_stats.get('total_requests', 0)}")
        print(f"  Successful: {request_stats.get('successful_requests', 0)}")
        print(f"  Failed: {request_stats.get('failed_requests', 0)}")
        print(f"  Fallback: {request_stats.get('fallback_requests', 0)}")
        print(f"  Rate Limited: {request_stats.get('rate_limited_requests', 0)}")

# Example 4: Change routing strategy
async def change_routing_strategy(strategy="cost"):
    """Change the routing strategy"""
    
    url = "http://localhost:8080/admin/routing-strategy"
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {"strategy": strategy}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        print(f"Routing strategy changed to: {strategy}")
        print("Response:", response.json())

# Example 5: Test different models
async def test_different_models():
    """Test requests with different model names"""
    
    models = [
        "claude-3-5-sonnet-20241022",  # Will route to primary models
        "claude-3-5-haiku-20241022",   # Will route to secondary models
        "claude-sonnet-4-20250514"     # Latest model
    ]
    
    for model in models:
        print(f"\nTesting model: {model}")
        
        url = "http://localhost:8080/v1/messages"
        headers = {"Content-Type": "application/json"}
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": f"Hello! I'm testing with {model}. Please respond briefly."}
            ],
            "max_tokens": 50
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                result = response.json()
                
                # Extract the response text
                content = result.get("content", [])
                if content and len(content) > 0:
                    text = content[0].get("text", "No text found")
                    print(f"  Response: {text[:100]}...")
                    print(f"  Model used: {result.get('model', 'Unknown')}")
                else:
                    print("  No content in response")
                    
            except Exception as e:
                print(f"  Error: {e}")

# Example 6: Monitor costs in real-time
async def monitor_costs():
    """Monitor cost information"""
    
    # Get basic stats
    url = "http://localhost:8080/stats"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        stats = response.json()
        
        print("Cost Monitoring:")
        print(f"  Active Requests: {stats.get('active_requests', 0)}")
        
        # Check if cost data is available
        if "router_stats" in stats:
            print("  Detailed cost data available in router_stats")
        
        # Try to get Prometheus metrics
        try:
            metrics_response = await client.get("http://localhost:8090/metrics")
            if metrics_response.status_code == 200:
                print("  ✅ Prometheus metrics available at http://localhost:8090/metrics")
            else:
                print("  ⚠️ Prometheus metrics not available")
        except:
            print("  ⚠️ Could not connect to Prometheus metrics server")

async def main():
    """Run all examples"""
    
    print("Claude Code Multi-Model Integration - Usage Examples")
    print("=" * 60)
    
    # Check if the proxy is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health")
            if response.status_code != 200:
                print("❌ Intelligent proxy is not running!")
                print("Please start it with: ./scripts/start-intelligent-proxy.sh")
                return
    except:
        print("❌ Cannot connect to intelligent proxy!")
        print("Please start it with: ./scripts/start-intelligent-proxy.sh")
        return
    
    print("✅ Intelligent proxy is running\n")
    
    # Run examples
    try:
        print("1. Checking system health...")
        await check_system_health()
        
        print("\n2. Getting system statistics...")
        await get_system_stats()
        
        print("\n3. Testing basic API call...")
        await basic_api_call()
        
        print("\n4. Testing different models...")
        await test_different_models()
        
        print("\n5. Changing routing strategy to 'cost'...")
        await change_routing_strategy("cost")
        
        print("\n6. Monitoring costs...")
        await monitor_costs()
        
        print("\n7. Resetting routing strategy to 'intelligent'...")
        await change_routing_strategy("intelligent")
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")

if __name__ == "__main__":
    asyncio.run(main())