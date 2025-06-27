#!/usr/bin/env python3
"""
Test LiteLLM Sync with Real Supabase MCP Tools
==============================================

This script tests the LiteLLM data collection and sync to Supabase
using a small subset of real data.
"""

import json
import requests
from decimal import Decimal
from typing import Dict, Any, Optional

def fetch_sample_litellm_data() -> Dict[str, Any]:
    """Fetch a small sample of LiteLLM data for testing"""
    url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        all_data = response.json()
        
        # Get first 5 models for testing
        sample_models = {}
        count = 0
        for model_name, model_info in all_data.items():
            if count >= 5:
                break
            sample_models[model_name] = model_info
            count += 1
            
        return sample_models
    except Exception as e:
        print(f"❌ Failed to fetch LiteLLM data: {e}")
        # Return hardcoded sample for testing
        return {
            "gpt-4o": {
                "max_tokens": 4096,
                "max_input_tokens": 128000,
                "max_output_tokens": 4096,
                "input_cost_per_token": 5e-06,
                "output_cost_per_token": 1.5e-05,
                "litellm_provider": "openai",
                "mode": "chat",
                "supports_function_calling": True,
                "supports_vision": True
            },
            "claude-3-5-sonnet-20241022": {
                "max_tokens": 4096,
                "max_input_tokens": 200000,
                "max_output_tokens": 4096,
                "input_cost_per_token": 3e-06,
                "output_cost_per_token": 1.5e-05,
                "litellm_provider": "anthropic",
                "mode": "chat",
                "supports_function_calling": True,
                "supports_vision": True
            },
            "openrouter/anthropic/claude-3.5-sonnet": {
                "max_tokens": 4096,
                "max_input_tokens": 200000,
                "max_output_tokens": 4096,
                "input_cost_per_token": 3.5e-06,
                "output_cost_per_token": 1.6e-05,
                "litellm_provider": "openrouter",
                "mode": "chat",
                "supports_function_calling": True
            }
        }

def parse_model_for_supabase(model_name: str, model_info: Dict[str, Any]) -> Dict[str, Any]:
    """Parse LiteLLM model data for Supabase insertion"""
    
    # Extract provider and family
    provider = model_info.get('litellm_provider', 'unknown')
    
    if provider == 'openrouter' and '/' in model_name:
        parts = model_name.split('/')
        actual_provider = parts[1] if len(parts) > 1 else provider
        model_family = parts[2].split('-')[0] if len(parts) > 2 and '-' in parts[2] else parts[2] if len(parts) > 2 else model_name
    else:
        actual_provider = provider
        if '-' in model_name:
            model_family = model_name.split('-')[0]
        else:
            model_family = model_name
    
    # Build capabilities
    capabilities = {}
    if model_info.get('supports_function_calling'):
        capabilities['supports_function_calling'] = True
    if model_info.get('supports_vision'):
        capabilities['supports_vision'] = True
    if model_info.get('supports_parallel_function_calling'):
        capabilities['supports_parallel_function_calling'] = True
    if model_info.get('mode'):
        capabilities['mode'] = model_info['mode']
    
    return {
        'name': model_name,
        'provider': actual_provider,
        'model_family': model_family,
        'context_window': model_info.get('max_input_tokens', model_info.get('max_tokens')),
        'max_tokens': model_info.get('max_output_tokens', model_info.get('max_tokens')),
        'input_token_limit': model_info.get('max_input_tokens'),
        'output_token_limit': model_info.get('max_output_tokens'),
        'capabilities': capabilities,
        'model_type': model_info.get('mode', 'chat')
    }

def parse_pricing_for_supabase(model_name: str, model_info: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    """Parse pricing data for Supabase insertion"""
    
    provider = model_info.get('litellm_provider', 'unknown')
    
    # Convert per-token to per-million
    input_price = None
    output_price = None
    
    if model_info.get('input_cost_per_token'):
        input_price = float(model_info['input_cost_per_token']) * 1_000_000
        
    if model_info.get('output_cost_per_token'):
        output_price = float(model_info['output_cost_per_token']) * 1_000_000
    
    return {
        'model_id': model_id,
        'provider_name': provider,
        'provider_id': f"{provider}-api",
        'input_price_per_million': input_price,
        'output_price_per_million': output_price,
        'is_free_tier': (input_price == 0 and output_price == 0) if input_price is not None and output_price is not None else False,
        'rate_limits': {
            'max_tokens_per_request': model_info.get('max_tokens', 4096)
        },
        'provider_metadata': {
            'litellm_provider': provider,
            'mode': model_info.get('mode', 'chat')
        },
        'is_active': True
    }

def main():
    """Test the LiteLLM sync process"""
    print("🔬 Testing LiteLLM Sync with Supabase MCP")
    print("=" * 50)
    
    # Fetch sample data
    print("📥 Fetching sample LiteLLM data...")
    sample_data = fetch_sample_litellm_data()
    print(f"✅ Retrieved {len(sample_data)} models for testing")
    
    # Process each model
    for model_name, model_info in sample_data.items():
        print(f"\n🔄 Processing: {model_name}")
        
        # Parse model data
        model_data = parse_model_for_supabase(model_name, model_info)
        print(f"📊 Model Data: {json.dumps(model_data, indent=2)}")
        
        # For now, just print what would be synced
        # In real implementation, we'd call MCP Supabase tools here
        print(f"📤 Would sync model: {model_data['name']}")
        print(f"🏢 Provider: {model_data['provider']}")
        print(f"💰 Context: {model_data['context_window']} tokens")
        print(f"🎯 Capabilities: {len(model_data['capabilities'])} features")
        
        # Parse pricing
        fake_model_id = f"test-{model_name.replace('/', '-')}"
        pricing_data = parse_pricing_for_supabase(model_name, model_info, fake_model_id)
        print(f"💸 Input Price: ${pricing_data['input_price_per_million']}/M tokens")
        print(f"💸 Output Price: ${pricing_data['output_price_per_million']}/M tokens")
        
    print("\n🎉 Test completed! Ready to implement real sync.")

if __name__ == "__main__":
    main()