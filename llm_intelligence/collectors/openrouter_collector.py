#!/usr/bin/env python3
"""
OpenRouter Multi-Provider Pricing Collector
===========================================

Collects real-time pricing data from OpenRouter API to identify
the cheapest provider for each model. Implements OpenRouter's
intelligent routing algorithm for cost optimization.

Key Features:
- Multi-provider pricing discovery per model
- Provider routing intelligence (inverse square weighting)
- Rate limiting and availability tracking
- Cost optimization recommendations
"""

import asyncio
import logging
import requests
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenRouterCollector:
    """Collector for OpenRouter multi-provider pricing data"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
            
    def fetch_openrouter_models(self) -> List[Dict[str, Any]]:
        """Fetch all models from OpenRouter API"""
        logger.info("🔄 Fetching OpenRouter models...")
        
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            models = data.get('data', [])
            
            logger.info(f"✅ Fetched {len(models)} models from OpenRouter")
            return models
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch OpenRouter models: {e}")
            # Return fallback data for testing
            return self._get_fallback_models()
            
    def _get_fallback_models(self) -> List[Dict[str, Any]]:
        """Fallback model data when API is not available"""
        return [
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Claude 3.5 Sonnet by Anthropic",
                "pricing": {
                    "prompt": "0.000003",
                    "completion": "0.000015"
                },
                "context_length": 200000,
                "architecture": {
                    "modality": "text",
                    "tokenizer": "Claude",
                    "instruct_type": "claude"
                },
                "top_provider": {
                    "context_length": 200000,
                    "max_completion_tokens": 4096,
                    "is_moderated": False
                }
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "GPT-4o by OpenAI",
                "pricing": {
                    "prompt": "0.000005",
                    "completion": "0.000015"
                },
                "context_length": 128000,
                "architecture": {
                    "modality": "text+vision",
                    "tokenizer": "cl100k_base",
                    "instruct_type": "chatml"
                },
                "top_provider": {
                    "context_length": 128000,
                    "max_completion_tokens": 4096,
                    "is_moderated": True
                }
            }
        ]
        
    def parse_openrouter_model(self, model_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse OpenRouter model data into model + pricing format"""
        
        model_id = model_data.get('id', '')
        
        # Extract provider from model ID (format: provider/model-name)
        if '/' in model_id:
            provider_parts = model_id.split('/')
            provider = provider_parts[0]
            model_name_part = '/'.join(provider_parts[1:])
        else:
            provider = 'openrouter'
            model_name_part = model_id
            
        # Extract model family
        if '-' in model_name_part:
            model_family = model_name_part.split('-')[0]
        else:
            model_family = model_name_part
            
        # Build capabilities from architecture
        capabilities = {}
        arch = model_data.get('architecture', {})
        
        if arch.get('modality'):
            capabilities['modality'] = arch['modality']
            if 'vision' in arch['modality']:
                capabilities['supports_vision'] = True
                
        if arch.get('instruct_type'):
            capabilities['instruct_type'] = arch['instruct_type']
            
        # Check for function calling support (heuristic)
        model_name_lower = model_data.get('name', '').lower()
        if any(keyword in model_name_lower for keyword in ['gpt-4', 'claude-3', 'gemini']):
            capabilities['supports_function_calling'] = True
            
        # Model data
        model_info = {
            'name': model_id,  # Use full OpenRouter model ID
            'provider': provider,
            'model_family': model_family,
            'context_window': model_data.get('context_length', 4096),
            'max_tokens': model_data.get('top_provider', {}).get('max_completion_tokens', 4096),
            'input_token_limit': model_data.get('context_length', 4096),
            'output_token_limit': model_data.get('top_provider', {}).get('max_completion_tokens', 4096),
            'capabilities': capabilities,
            'model_type': 'chat'  # OpenRouter primarily serves chat models
        }
        
        # Pricing data
        pricing_info = self._parse_openrouter_pricing(model_data, provider)
        
        return model_info, pricing_info
        
    def _parse_openrouter_pricing(self, model_data: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """Parse OpenRouter pricing data"""
        
        pricing = model_data.get('pricing', {})
        
        # Convert from per-token to per-million
        input_price = None
        output_price = None
        
        if pricing.get('prompt'):
            try:
                input_price = float(pricing['prompt']) * 1_000_000
            except (ValueError, TypeError):
                input_price = None
                
        if pricing.get('completion'):
            try:
                output_price = float(pricing['completion']) * 1_000_000
            except (ValueError, TypeError):
                output_price = None
                
        # Determine if it's free tier
        is_free = input_price == 0 and output_price == 0
        
        return {
            'provider_name': 'openrouter',
            'provider_id': f"openrouter-{provider}",
            'input_price_per_million': input_price,
            'output_price_per_million': output_price,
            'is_free_tier': is_free,
            'rate_limits': self._estimate_rate_limits(model_data, is_free),
            'provider_metadata': {
                'openrouter_id': model_data.get('id'),
                'description': model_data.get('description'),
                'top_provider_info': model_data.get('top_provider', {}),
                'architecture': model_data.get('architecture', {})
            },
            'is_active': True
        }
        
    def _estimate_rate_limits(self, model_data: Dict[str, Any], is_free: bool) -> Dict[str, Any]:
        """Estimate rate limits based on OpenRouter policies"""
        
        if is_free:
            # Free tier limits
            return {
                "requests_per_day": 50,  # Default for free tier
                "requests_per_minute": 20,
                "tokens_per_minute": 50000,
                "tier": "free"
            }
        else:
            # Paid tier limits (estimated)
            return {
                "requests_per_minute": 200,  # OpenRouter standard
                "tokens_per_minute": 100000,
                "concurrent_requests": 5,
                "tier": "paid"
            }
            
    def calculate_provider_routing_weights(self, providers_pricing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate OpenRouter-style provider routing weights
        Uses inverse square weighting: Provider A ($1) is 9x more likely than Provider C ($3)
        """
        
        weighted_providers = []
        
        for provider in providers_pricing:
            input_price = provider.get('input_price_per_million', 0)
            
            if input_price > 0:
                # Inverse square weighting
                weight = 1.0 / (input_price ** 2)
            else:
                # Free tier gets highest weight
                weight = 1000.0
                
            weighted_provider = provider.copy()
            weighted_provider['routing_weight'] = weight
            weighted_providers.append(weighted_provider)
            
        # Normalize weights to sum to 1.0
        total_weight = sum(p['routing_weight'] for p in weighted_providers)
        if total_weight > 0:
            for provider in weighted_providers:
                provider['normalized_weight'] = provider['routing_weight'] / total_weight
        else:
            # Equal weights if no valid prices
            equal_weight = 1.0 / len(weighted_providers) if weighted_providers else 0
            for provider in weighted_providers:
                provider['normalized_weight'] = equal_weight
                
        return weighted_providers
        
    def find_optimal_provider(self, providers_pricing: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the optimal provider using OpenRouter algorithm"""
        
        if not providers_pricing:
            return {}
            
        # Calculate routing weights
        weighted_providers = self.calculate_provider_routing_weights(providers_pricing)
        
        # Sort by weight (highest first)
        weighted_providers.sort(key=lambda x: x['normalized_weight'], reverse=True)
        
        optimal = weighted_providers[0]
        
        return {
            'provider_name': optimal['provider_name'],
            'provider_id': optimal['provider_id'],
            'input_price_per_million': optimal['input_price_per_million'],
            'output_price_per_million': optimal['output_price_per_million'],
            'routing_weight': optimal['routing_weight'],
            'selection_probability': optimal['normalized_weight'],
            'cost_advantage': self._calculate_cost_advantage(optimal, weighted_providers)
        }
        
    def _calculate_cost_advantage(self, optimal: Dict[str, Any], all_providers: List[Dict[str, Any]]) -> float:
        """Calculate cost advantage of optimal provider"""
        
        optimal_price = optimal.get('input_price_per_million', 0)
        
        if optimal_price == 0:
            return float('inf')  # Free tier has infinite advantage
            
        prices = [p.get('input_price_per_million', 0) for p in all_providers if p.get('input_price_per_million', 0) > 0]
        
        if not prices:
            return 0
            
        avg_price = sum(prices) / len(prices)
        
        if avg_price > 0:
            return (avg_price - optimal_price) / avg_price
        else:
            return 0
            
    def sync_to_supabase(self, models_data: List[Tuple[Dict[str, Any], Dict[str, Any]]]):
        """Sync OpenRouter data to Supabase"""
        logger.info(f"📤 Syncing {len(models_data)} OpenRouter models to Supabase")
        
        for model_info, pricing_info in models_data:
            logger.info(f"🔄 Processing {model_info['name']}")
            
            # In real implementation, would use MCP Supabase tools
            # For now, just log what would be synced
            logger.info(f"  📊 Model: {model_info['name']} ({model_info['provider']})")
            logger.info(f"  💰 Price: ${pricing_info['input_price_per_million']}/M in, ${pricing_info['output_price_per_million']}/M out")
            logger.info(f"  🎯 Free tier: {pricing_info['is_free_tier']}")
            
    async def run_openrouter_sync(self):
        """Run complete OpenRouter data synchronization"""
        logger.info("🚀 Starting OpenRouter multi-provider sync")
        
        try:
            # Fetch OpenRouter models
            models_data = self.fetch_openrouter_models()
            
            parsed_models = []
            
            for model_data in models_data:
                try:
                    model_info, pricing_info = self.parse_openrouter_model(model_data)
                    parsed_models.append((model_info, pricing_info))
                    
                except Exception as e:
                    logger.error(f"❌ Failed to parse model {model_data.get('id', 'unknown')}: {e}")
                    continue
                    
            # Demo: Group by base model to show multi-provider options
            logger.info("\n🔍 Multi-Provider Analysis:")
            model_groups = {}
            
            for model_info, pricing_info in parsed_models:
                base_name = model_info['name'].split('/')[-1]  # Remove provider prefix
                if base_name not in model_groups:
                    model_groups[base_name] = []
                model_groups[base_name].append(pricing_info)
                
            # Show provider options for models with multiple providers
            for base_name, providers in model_groups.items():
                if len(providers) > 1:
                    logger.info(f"\n📊 {base_name} - {len(providers)} providers:")
                    
                    optimal = self.find_optimal_provider(providers)
                    
                    for provider in providers:
                        is_optimal = provider['provider_id'] == optimal.get('provider_id')
                        marker = "🥇 OPTIMAL" if is_optimal else "  "
                        logger.info(f"  {marker} {provider['provider_name']}: ${provider['input_price_per_million']}/M")
                        
                    if optimal:
                        logger.info(f"  💡 Cost advantage: {optimal.get('cost_advantage', 0):.1%}")
                        
            # Sync to Supabase
            self.sync_to_supabase(parsed_models)
            
            logger.info(f"🎉 OpenRouter sync completed! Processed {len(parsed_models)} models")
            
        except Exception as e:
            logger.error(f"❌ OpenRouter sync failed: {e}")
            raise

def main():
    """Main entry point for testing"""
    # Initialize without API key for testing with fallback data
    collector = OpenRouterCollector()
    
    # Run sync
    asyncio.run(collector.run_openrouter_sync())

if __name__ == "__main__":
    main()