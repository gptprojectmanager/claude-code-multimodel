#!/usr/bin/env python3
"""
FastAPI Claude Proxy - Usage Examples

This file demonstrates various ways to use the FastAPI Claude Proxy
with different providers and configurations.
"""

import asyncio
import json
import os
import httpx
from typing import Dict, List, Optional

# Configuration
PROXY_BASE_URL = "http://localhost:8080"
PROXY_HEADERS = {"Content-Type": "application/json"}

class ClaudeProxyClient:
    """Simple client for interacting with the FastAPI Claude Proxy"""
    
    def __init__(self, base_url: str = PROXY_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def send_message(
        self, 
        model: str, 
        messages: List[Dict], 
        max_tokens: int = 1024,
        temperature: float = 1.0,
        stream: bool = False
    ) -> Dict:
        """Send a message to the Claude proxy"""
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        response = await self.client.post(
            f"{self.base_url}/v1/messages",
            json=payload,
            headers=PROXY_HEADERS
        )
        response.raise_for_status()
        return response.json()
    
    async def stream_message(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 1024,
        temperature: float = 1.0
    ):
        """Stream a message from the Claude proxy"""
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/v1/messages",
            json=payload,
            headers=PROXY_HEADERS
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                if chunk.strip():
                    yield chunk
    
    async def get_health(self) -> Dict:
        """Get proxy health status"""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Example functions
async def example_basic_chat():
    """Basic chat example with Haiku model"""
    print("🤖 Basic Chat Example (Haiku)")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    
    try:
        response = await client.send_message(
            model="claude-3-5-haiku-20241022",
            messages=[
                {"role": "user", "content": "Hello! Can you tell me a short joke?"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        print(f"Model: {response['model']}")
        print(f"Response: {response['content'][0]['text']}")
        print(f"Tokens used: {response['usage']['input_tokens']} → {response['usage']['output_tokens']}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_advanced_chat():
    """Advanced chat example with Sonnet model"""
    print("\n🧠 Advanced Chat Example (Sonnet)")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    
    try:
        response = await client.send_message(
            model="claude-sonnet-4-20250514",
            messages=[
                {"role": "user", "content": "Explain the concept of recursion in programming with a simple example."}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        print(f"Model: {response['model']}")
        print(f"Response: {response['content'][0]['text']}")
        print(f"Tokens used: {response['usage']['input_tokens']} → {response['usage']['output_tokens']}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_conversation():
    """Multi-turn conversation example"""
    print("\n💬 Multi-turn Conversation Example")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    
    # Build conversation history
    messages = [
        {"role": "user", "content": "What's the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What's the population of that city?"}
    ]
    
    try:
        response = await client.send_message(
            model="claude-3-5-haiku-20241022",
            messages=messages,
            max_tokens=200,
            temperature=0.5
        )
        
        print("Conversation history:")
        for msg in messages[:-1]:  # Show all but last message
            print(f"  {msg['role']}: {msg['content']}")
        
        print(f"  user: {messages[-1]['content']}")
        print(f"  assistant: {response['content'][0]['text']}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_streaming():
    """Streaming response example"""
    print("\n🌊 Streaming Response Example")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    
    try:
        print("Streaming response:")
        async for chunk in client.stream_message(
            model="claude-3-5-haiku-20241022",
            messages=[
                {"role": "user", "content": "Write a short poem about technology."}
            ],
            max_tokens=200,
            temperature=0.8
        ):
            print(chunk, end="", flush=True)
        
        print("\n[Stream complete]")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_different_models():
    """Test different models with the same prompt"""
    print("\n🔄 Model Comparison Example")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    prompt = "Explain AI in one sentence."
    
    models = [
        "claude-3-5-haiku-20241022",
        "claude-sonnet-4-20250514"
    ]
    
    try:
        for model in models:
            print(f"\n{model}:")
            response = await client.send_message(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.5
            )
            
            print(f"  Response: {response['content'][0]['text']}")
            print(f"  Tokens: {response['usage']['input_tokens']} → {response['usage']['output_tokens']}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_health_check():
    """Health check example"""
    print("\n🏥 Health Check Example")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    
    try:
        health = await client.get_health()
        print(f"Health Status: {json.dumps(health, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_error_handling():
    """Error handling example"""
    print("\n⚠️ Error Handling Example")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    
    # Test invalid model
    try:
        response = await client.send_message(
            model="invalid-model-name",
            messages=[{"role": "user", "content": "This should fail"}],
            max_tokens=100
        )
        print("Unexpected success!")
        
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"Other Error: {e}")
    
    # Test max tokens validation
    try:
        response = await client.send_message(
            model="claude-3-5-haiku-20241022",
            messages=[{"role": "user", "content": "Test max tokens"}],
            max_tokens=50000  # Should be automatically limited to 8192
        )
        print(f"Max tokens handled: {response['usage']['output_tokens']} tokens generated")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def example_temperature_variations():
    """Temperature variation example"""
    print("\n🌡️ Temperature Variation Example")
    print("-" * 50)
    
    client = ClaudeProxyClient()
    prompt = "Complete this story: 'The old wizard looked at the mysterious crystal and...'"
    
    temperatures = [0.1, 0.5, 1.0, 1.5]
    
    try:
        for temp in temperatures:
            print(f"\nTemperature {temp}:")
            response = await client.send_message(
                model="claude-3-5-haiku-20241022",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=temp
            )
            
            print(f"  Response: {response['content'][0]['text'][:100]}...")
            
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

# curl examples for command line testing
def print_curl_examples():
    """Print curl examples for command line testing"""
    print("\n📡 Curl Examples")
    print("-" * 50)
    
    examples = [
        {
            "name": "Basic Haiku Request",
            "curl": '''curl -X POST http://localhost:8080/v1/messages \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "claude-3-5-haiku-20241022",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }' '''
        },
        {
            "name": "Sonnet Request",
            "curl": '''curl -X POST http://localhost:8080/v1/messages \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "Explain quantum computing"}],
    "max_tokens": 500,
    "temperature": 0.3
  }' '''
        },
        {
            "name": "Health Check",
            "curl": "curl http://localhost:8080/health"
        }
    ]
    
    for example in examples:
        print(f"\n{example['name']}:")
        print(example['curl'])

async def main():
    """Run all examples"""
    print("🚀 FastAPI Claude Proxy Examples")
    print("=" * 50)
    
    examples = [
        example_health_check,
        example_basic_chat,
        example_advanced_chat,
        example_conversation,
        example_different_models,
        example_temperature_variations,
        example_error_handling,
        # example_streaming,  # Uncomment to test streaming
    ]
    
    for example_func in examples:
        try:
            await example_func()
            await asyncio.sleep(1)  # Small delay between examples
        except Exception as e:
            print(f"Example failed: {e}")
            continue
    
    # Print curl examples
    print_curl_examples()
    
    print("\n✅ Examples completed!")
    print("\nTo run individual examples:")
    print("  python examples/fastapi_claude_proxy_examples.py")
    print("\nMake sure the proxy is running:")
    print("  ./scripts/start-claude-anthropic-proxy.sh")

if __name__ == "__main__":
    asyncio.run(main())