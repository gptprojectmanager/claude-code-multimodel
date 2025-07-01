#!/usr/bin/env python3
"""
OpenRouter Service - Port 8093  
Multi-Port Claude Code Service for OpenRouter (100+ models)

Based on claude-code-proxy patterns with LiteLLM library integration.
"""

import os
import httpx
from typing import Dict, Any, Optional
from .base_service import BaseMultiPortService
import litellm

class OpenRouterService(BaseMultiPortService):
    """
    OpenRouter service implementation
    
    Provides access to 100+ models via OpenRouter API including Claude models
    """
    
    def __init__(self, port: int = 8093):
        # Configuration for OpenRouter
        config = {
            "service_name": "openrouter",
            "provider": "openrouter", 
            "port": port,
            "endpoint": os.environ.get("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1"),
            "api_key": os.environ.get("OPENROUTER_API_KEY"),
            "models": {
                # Claude model mappings
                "claude-3-5-sonnet-20241022": "anthropic/claude-3.5-sonnet",
                "claude-3-5-haiku-20241022": "anthropic/claude-3-haiku",
                "claude-sonnet-4-20250514": "anthropic/claude-3.5-sonnet",  # Map to available model
                
                # OpenAI model mappings  
                "gpt-4o": "openai/gpt-4o",
                "gpt-4o-mini": "openai/gpt-4o-mini",
                
                # Meta Llama models
                "llama-3.2-90b": "meta-llama/llama-3.2-90b-vision-instruct",
                "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct"
            }
        }
        
        super().__init__(port, config)
        
        # Validate OpenRouter API key
        if not config["api_key"]:
            self.logger.warning("⚠️ OPENROUTER_API_KEY not set - service will not work")
    
    def configure_litellm(self):
        """Configure LiteLLM for OpenRouter"""
        super().configure_litellm()
        
        # Set OpenRouter API key for LiteLLM
        if self.provider_config.get("api_key"):
            os.environ["OPENROUTER_API_KEY"] = self.provider_config["api_key"]
            self.logger.info("🔧 OpenRouter API key configured for LiteLLM")
    
    async def map_model(self, model: str) -> str:
        """Map model names to OpenRouter format"""
        model_map = self.provider_config["models"]
        
        # Remove provider prefixes if present
        clean_model = model
        for prefix in ['anthropic/', 'openai/', 'openrouter/', 'meta-llama/']:
            if clean_model.startswith(prefix):
                clean_model = clean_model[len(prefix):]
                break
        
        # Direct mapping if available
        if clean_model in model_map:
            mapped = f"openrouter/{model_map[clean_model]}"
            self.logger.info(f"🔄 Model mapped: {model} -> {mapped}")
            return mapped
        
        # Pattern-based mapping for Claude models
        if 'haiku' in clean_model.lower():
            mapped = "openrouter/anthropic/claude-3-haiku"
            self.logger.info(f"🔄 Model mapped (haiku pattern): {model} -> {mapped}")
            return mapped
        elif 'sonnet' in clean_model.lower():
            mapped = "openrouter/anthropic/claude-3.5-sonnet"
            self.logger.info(f"🔄 Model mapped (sonnet pattern): {model} -> {mapped}")
            return mapped
        elif 'gpt-4' in clean_model.lower():
            if 'mini' in clean_model.lower():
                mapped = "openrouter/openai/gpt-4o-mini"
            else:
                mapped = "openrouter/openai/gpt-4o"
            self.logger.info(f"🔄 Model mapped (gpt pattern): {model} -> {mapped}")
            return mapped
        
        # Fallback: try to construct OpenRouter model name
        if not clean_model.startswith('openrouter/'):
            # Try to determine provider from model name
            if 'claude' in clean_model.lower():
                mapped = f"openrouter/anthropic/{clean_model}"
            elif 'gpt' in clean_model.lower():
                mapped = f"openrouter/openai/{clean_model}"
            elif 'llama' in clean_model.lower():
                mapped = f"openrouter/meta-llama/{clean_model}"
            else:
                mapped = f"openrouter/{clean_model}"
        else:
            mapped = clean_model
            
        self.logger.warning(f"⚠️ Model mapped (fallback): {model} -> {mapped}")
        return mapped
    
    async def check_provider_health(self) -> bool:
        """Check OpenRouter API health"""
        try:
            if not self.provider_config.get("api_key"):
                return False
            
            # Test API connectivity with models endpoint
            headers = {
                "Authorization": f"Bearer {self.provider_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.provider_config['endpoint']}/models",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.logger.debug("✅ OpenRouter API connectivity confirmed")
                    return True
                else:
                    self.logger.error(f"❌ OpenRouter API returned status {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"❌ OpenRouter health check failed: {str(e)}")
        
        return False
    
    async def get_available_models(self) -> dict:
        """Get list of available OpenRouter models"""
        try:
            # Try to fetch live models list from OpenRouter
            headers = {
                "Authorization": f"Bearer {self.provider_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.provider_config['endpoint']}/models",
                    headers=headers
                )
                
                if response.status_code == 200:
                    openrouter_models = response.json()
                    
                    # Filter for supported models and add Claude mappings
                    supported_models = []
                    for claude_model, openrouter_model in self.provider_config["models"].items():
                        supported_models.append({
                            "id": claude_model,
                            "object": "model",
                            "created": 1677610602,
                            "owned_by": "openrouter",
                            "provider_model": f"openrouter/{openrouter_model}"
                        })
                    
                    return {
                        "object": "list",
                        "data": supported_models,
                        "total_openrouter_models": len(openrouter_models.get("data", []))
                    }
                    
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch OpenRouter models: {str(e)}")
        
        # Fallback to static model list
        models = []
        for claude_model, openrouter_model in self.provider_config["models"].items():
            models.append({
                "id": claude_model,
                "object": "model", 
                "created": 1677610602,
                "owned_by": "openrouter",
                "provider_model": f"openrouter/{openrouter_model}"
            })
        
        return {
            "object": "list",
            "data": models
        }
    
    async def prepare_litellm_params(self, request_data: dict, mapped_model: str) -> dict:
        """Prepare OpenRouter specific parameters"""
        params = await super().prepare_litellm_params(request_data, mapped_model)
        
        # OpenRouter specific configurations
        params["timeout"] = 120  # Longer timeout for diverse model backends
        
        # OpenRouter supports higher max_tokens for some models
        max_tokens = params.get("max_tokens", 4096)
        if max_tokens > 32000:  # Some OpenRouter models support very high token counts
            self.logger.warning(f"⚠️ Limiting max_tokens from {max_tokens} to 32000 for OpenRouter")
            params["max_tokens"] = 32000
        
        # Add OpenRouter specific headers if needed
        # OpenRouter allows custom headers for tracking/preferences
        if "extra_headers" not in params:
            params["extra_headers"] = {}
        
        params["extra_headers"]["HTTP-Referer"] = "https://claude-code-multiport"
        params["extra_headers"]["X-Title"] = "Claude Code Multi-Port Service"
        
        return params

def create_service(port: int = 8093) -> OpenRouterService:
    """Factory function to create OpenRouter service"""
    return OpenRouterService(port)

if __name__ == "__main__":
    # Run OpenRouter service standalone
    service = OpenRouterService(8093)
    service.run()