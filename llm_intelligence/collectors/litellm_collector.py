#!/usr/bin/env python3
"""
LiteLLM Data Collector for LLM Intelligence System
==================================================

Syncs model pricing and metadata from LiteLLM's model_prices_and_context_window.json
to Supabase database via MCP tools.

This collector:
1. Fetches latest LiteLLM model data from GitHub
2. Parses model information, pricing, and capabilities
3. Syncs to Supabase models and provider_pricing tables
4. Handles provider-specific routing (especially OpenRouter)
"""

import json
import asyncio
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import subprocess
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiteLLMCollector:
    """Collector for LiteLLM model data with Supabase MCP integration"""
    
    def __init__(self):
        self.litellm_url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
        self.session = requests.Session()
        
    def fetch_litellm_data(self) -> Dict[str, Any]:
        """Fetch latest LiteLLM model pricing data"""
        logger.info("🔄 Fetching LiteLLM model data...")
        
        try:
            response = self.session.get(self.litellm_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Fetched {len(data)} models from LiteLLM")
            return data
        except Exception as e:
            logger.error(f"❌ Failed to fetch LiteLLM data: {e}")
            raise
            
    def parse_model_data(self, model_name: str, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LiteLLM model data into normalized format"""
        
        # Extract provider information
        provider = model_info.get('litellm_provider', 'unknown')
        
        # Handle OpenRouter special case
        if provider == 'openrouter' and '/' in model_name:
            provider_parts = model_name.split('/')
            if len(provider_parts) >= 2:
                actual_provider = provider_parts[0]
                model_family = provider_parts[1].split('-')[0] if '-' in provider_parts[1] else provider_parts[1]
            else:
                actual_provider = provider
                model_family = model_name
        else:
            actual_provider = provider
            # Extract model family from name
            if '/' in model_name:
                model_family = model_name.split('/')[1].split('-')[0]
            elif '-' in model_name:
                model_family = model_name.split('-')[0]
            else:
                model_family = model_name
                
        # Build capabilities object
        capabilities = {}
        
        # Function calling support
        if model_info.get('supports_function_calling'):
            capabilities['supports_function_calling'] = True
            
        if model_info.get('supports_parallel_function_calling'):
            capabilities['supports_parallel_function_calling'] = True
            
        # Vision support
        if model_info.get('supports_vision'):
            capabilities['supports_vision'] = True
            
        # Other capabilities
        for cap in ['supports_pdf_input', 'supports_response_schema', 
                   'supports_system_messages', 'supports_tool_choice']:
            if model_info.get(cap):
                capabilities[cap] = True
                
        # Output formats
        if model_info.get('mode'):
            capabilities['mode'] = model_info['mode']
            
        # Model data structure
        parsed_model = {
            'name': model_name,
            'provider': actual_provider,
            'model_family': model_family,
            'context_window': model_info.get('max_input_tokens', model_info.get('max_tokens')),
            'max_tokens': model_info.get('max_output_tokens', model_info.get('max_tokens')),
            'input_token_limit': model_info.get('max_input_tokens'),
            'output_token_limit': model_info.get('max_output_tokens'),
            'capabilities': capabilities,
            'model_type': model_info.get('mode', 'chat'),
            'deprecation_date': model_info.get('deprecation_date')
        }
        
        return parsed_model
        
    def parse_pricing_data(self, model_name: str, model_info: Dict[str, Any], model_id: str) -> List[Dict[str, Any]]:
        """Parse pricing data for multiple providers"""
        pricing_entries = []
        
        # Main provider pricing
        provider = model_info.get('litellm_provider', 'unknown')
        
        pricing_entry = {
            'model_id': model_id,
            'provider_name': provider,
            'provider_id': f"{provider}-primary",
            'input_price_per_million': self._safe_decimal(model_info.get('input_cost_per_token'), 1_000_000),
            'output_price_per_million': self._safe_decimal(model_info.get('output_cost_per_token'), 1_000_000),
            'batch_input_price_per_million': self._safe_decimal(model_info.get('input_cost_per_token_batches'), 1_000_000),
            'batch_output_price_per_million': self._safe_decimal(model_info.get('output_cost_per_token_batches'), 1_000_000),
            'is_free_tier': self._is_free_model(model_info),
            'rate_limits': self._extract_rate_limits(model_info),
            'provider_metadata': self._extract_provider_metadata(model_info),
            'is_active': True
        }
        
        pricing_entries.append(pricing_entry)
        
        # OpenRouter specific: Add multiple provider entries if available
        if provider == 'openrouter':
            # OpenRouter often has multiple providers for the same model
            # We'll add a generic OpenRouter entry and potentially discover more via API
            or_pricing = pricing_entry.copy()
            or_pricing.update({
                'provider_name': 'openrouter',
                'provider_id': 'openrouter-api',
                'provider_metadata': {
                    'source': 'openrouter_aggregate',
                    'supports_provider_routing': True
                }
            })
            pricing_entries.append(or_pricing)
            
        return pricing_entries
        
    def _safe_decimal(self, value: Any, multiplier: int = 1) -> Optional[Decimal]:
        """Safely convert value to Decimal with multiplier"""
        if value is None:
            return None
        try:
            return Decimal(str(float(value) * multiplier))
        except (ValueError, TypeError):
            return None
            
    def _is_free_model(self, model_info: Dict[str, Any]) -> bool:
        """Determine if model has free tier"""
        input_cost = model_info.get('input_cost_per_token', 0)
        output_cost = model_info.get('output_cost_per_token', 0)
        
        # Consider free if both costs are 0 or very low
        return (input_cost == 0 and output_cost == 0) or (
            input_cost is not None and input_cost < 0.000001 and
            output_cost is not None and output_cost < 0.000001
        )
        
    def _extract_rate_limits(self, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract rate limiting information"""
        limits = {}
        
        # Common rate limit patterns in LiteLLM data
        if 'max_tokens' in model_info:
            limits['max_tokens_per_request'] = model_info['max_tokens']
            
        # Provider-specific limits would be added here
        # Based on provider type and known limits
        
        return limits
        
    def _extract_provider_metadata(self, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract provider-specific metadata"""
        metadata = {}
        
        # Supported regions
        if 'supported_regions' in model_info:
            metadata['supported_regions'] = model_info['supported_regions']
            
        # Other metadata
        for key in ['mode', 'litellm_provider']:
            if key in model_info:
                metadata[key] = model_info[key]
                
        return metadata
        
    def call_mcp_supabase(self, operation: str, **kwargs) -> Any:
        """Call MCP Supabase tools via subprocess"""
        # This is a simplified approach - in practice you'd use proper MCP client
        # For now we'll simulate the calls
        logger.info(f"🔧 MCP Supabase {operation}: {kwargs}")
        return {"status": "success", "data": []}
        
    async def sync_model_to_supabase(self, model_data: Dict[str, Any]) -> str:
        """Sync single model to Supabase and return model ID"""
        logger.info(f"📤 Syncing model: {model_data['name']}")
        
        try:
            # First, try to find existing model
            existing = self.call_mcp_supabase(
                'read_table_rows',
                table_name='models',
                filters={'name': model_data['name']},
                limit=1
            )
            
            if existing.get('data'):
                # Update existing model
                model_id = existing['data'][0]['id']
                self.call_mcp_supabase(
                    'update_table_records',
                    table_name='models',
                    updates=model_data,
                    filters={'id': model_id}
                )
                logger.info(f"✅ Updated existing model: {model_data['name']}")
            else:
                # Create new model
                result = self.call_mcp_supabase(
                    'create_table_records',
                    table_name='models',
                    records=model_data
                )
                model_id = result['data'][0]['id']
                logger.info(f"✅ Created new model: {model_data['name']}")
                
            return model_id
            
        except Exception as e:
            logger.error(f"❌ Failed to sync model {model_data['name']}: {e}")
            raise
            
    async def sync_pricing_to_supabase(self, pricing_entries: List[Dict[str, Any]]):
        """Sync pricing data to Supabase"""
        for pricing in pricing_entries:
            logger.info(f"💰 Syncing pricing for {pricing['provider_name']}")
            
            try:
                # Check for existing pricing
                existing = self.call_mcp_supabase(
                    'read_table_rows',
                    table_name='provider_pricing',
                    filters={
                        'model_id': pricing['model_id'],
                        'provider_name': pricing['provider_name'],
                        'provider_id': pricing['provider_id']
                    },
                    limit=1
                )
                
                if existing.get('data'):
                    # Update existing pricing
                    self.call_mcp_supabase(
                        'update_table_records',
                        table_name='provider_pricing',
                        updates=pricing,
                        filters={
                            'model_id': pricing['model_id'],
                            'provider_name': pricing['provider_name'],
                            'provider_id': pricing['provider_id']
                        }
                    )
                    logger.info(f"✅ Updated pricing for {pricing['provider_name']}")
                else:
                    # Create new pricing
                    self.call_mcp_supabase(
                        'create_table_records',
                        table_name='provider_pricing',
                        records=pricing
                    )
                    logger.info(f"✅ Created pricing for {pricing['provider_name']}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to sync pricing for {pricing['provider_name']}: {e}")
                
    async def run_full_sync(self):
        """Run complete LiteLLM data synchronization"""
        logger.info("🚀 Starting LiteLLM full sync to Supabase")
        
        try:
            # Fetch LiteLLM data
            litellm_data = self.fetch_litellm_data()
            
            total_models = len(litellm_data)
            processed = 0
            
            for model_name, model_info in litellm_data.items():
                try:
                    logger.info(f"🔄 Processing {model_name} ({processed+1}/{total_models})")
                    
                    # Parse model data
                    model_data = self.parse_model_data(model_name, model_info)
                    
                    # Sync model to Supabase
                    model_id = await self.sync_model_to_supabase(model_data)
                    
                    # Parse and sync pricing data
                    pricing_entries = self.parse_pricing_data(model_name, model_info, model_id)
                    await self.sync_pricing_to_supabase(pricing_entries)
                    
                    processed += 1
                    
                    # Rate limiting
                    if processed % 10 == 0:
                        logger.info(f"📊 Progress: {processed}/{total_models} models processed")
                        await asyncio.sleep(1)  # Brief pause to avoid overwhelming Supabase
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process {model_name}: {e}")
                    continue
                    
            logger.info(f"🎉 LiteLLM sync completed! Processed {processed}/{total_models} models")
            
            # Refresh materialized view
            logger.info("🔄 Refreshing model rankings...")
            # This would be done via direct DB connection or API call
            
        except Exception as e:
            logger.error(f"❌ LiteLLM sync failed: {e}")
            raise

def main():
    """Main entry point"""
    collector = LiteLLMCollector()
    
    # Run async sync
    asyncio.run(collector.run_full_sync())

if __name__ == "__main__":
    main()