#!/usr/bin/env python3
"""
GitHub Models Service - Port 8092
Multi-Port Claude Code Service for GitHub Models (Azure-backed)

Based on claude-code-proxy patterns with LiteLLM library integration.
"""

import os
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from .base_service import BaseMultiPortService
import litellm

class GitHubModelsService(BaseMultiPortService):
    """
    GitHub Models service implementation
    
    Provides access to Claude models via GitHub Models API (Azure-backed)
    """
    
    def __init__(self, port: int = 8092):
        # Configuration for GitHub Models (start with fallback models)
        config = {
            "service_name": "github-models",
            "provider": "github_models",
            "port": port,
            "endpoint": os.environ.get("GITHUB_MODELS_ENDPOINT", "https://models.github.ai"),
            "token": os.environ.get("GITHUB_TOKEN"),
            "models": {
                # Fallback model mappings (will be updated dynamically)
                "claude-3-5-sonnet-20241022": "gpt-4o",
                "claude-3-5-haiku-20241022": "gpt-4o-mini",
                "claude-sonnet-4-20250514": "gpt-4o",
                "gpt-4o": "gpt-4o",
                "gpt-4o-mini": "gpt-4o-mini",
                "openai/gpt-4o": "gpt-4o",
                "openai/gpt-4o-mini": "gpt-4o-mini"
            }
        }
        
        super().__init__(port, config)
        
        # Validate GitHub token
        if not config["token"]:
            self.logger.warning("⚠️ GITHUB_TOKEN not set - service may not work properly")
        
        # Flag to track if models have been fetched
        self._models_initialized = False
        
        # Add startup event to initialize models after server starts
        @self.app.on_event("startup")
        async def startup_event():
            """Initialize models after FastAPI server startup"""
            asyncio.create_task(self._initialize_models_async())
    
    async def _initialize_models_async(self):
        """Initialize models asynchronously after service startup"""
        try:
            await asyncio.sleep(2)  # Wait for service to be fully started
            available_models = await self.fetch_available_models()
            
            if available_models:
                dynamic_mapping = self.create_dynamic_model_mapping(available_models)
                # Update the configuration with dynamic mapping
                self.provider_config["models"].update(dynamic_mapping)
                self._models_initialized = True
                self.logger.info(f"🔄 Dynamic model mapping updated with {len(available_models)} models")
            else:
                self.logger.warning("⚠️ No models fetched, using fallback mapping")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize dynamic models: {str(e)}")
    
    def configure_litellm(self):
        """Configure LiteLLM for GitHub Models"""
        super().configure_litellm()
        
        # Set GitHub API key for LiteLLM (let LiteLLM handle endpoint automatically)
        if self.provider_config.get("token"):
            os.environ["GITHUB_API_KEY"] = self.provider_config["token"]
            self.logger.info("🔧 GitHub API key configured for LiteLLM auto-detection")
    
    async def fetch_available_models(self) -> List[str]:
        """Fetch available models from GitHub Models API"""
        try:
            token = self.provider_config.get("token")
            
            if not token:
                self.logger.warning("⚠️ No GitHub token available, using fallback models")
                return ["gpt-4o", "gpt-4o-mini"]
            
            # Use the correct GitHub Models catalog endpoint
            # According to docs: https://docs.github.com/en/rest/models/catalog
            catalog_url = "https://models.github.ai/catalog/models"
            
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(catalog_url, headers=headers)
                
                if response.status_code == 200:
                    models_data = response.json()
                    # Extract model IDs in {publisher}/{model_name} format
                    if isinstance(models_data, dict) and "data" in models_data:
                        model_ids = [model.get("id", "") for model in models_data["data"] if model.get("id")]
                    elif isinstance(models_data, list):
                        model_ids = [model.get("id", "") for model in models_data if model.get("id")]
                    else:
                        model_ids = []
                    
                    if model_ids:
                        self.logger.info(f"🔍 Fetched {len(model_ids)} available models from GitHub")
                        return model_ids
                
                self.logger.warning(f"⚠️ GitHub Models API returned {response.status_code}, using fallback models")
                return ["gpt-4o", "gpt-4o-mini"]
                
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to fetch GitHub models: {str(e)}, using fallback models")
            return ["gpt-4o", "gpt-4o-mini"]
    
    def create_dynamic_model_mapping(self, available_models: List[str]) -> Dict[str, str]:
        """Create model mapping based on available models"""
        model_map = {}
        
        # Find available OpenAI models
        openai_models = [m for m in available_models if m.startswith("openai/")]
        
        # Prefer gpt-4o for Claude Sonnet, gpt-4o-mini for Haiku
        preferred_sonnet = "gpt-4o" if "openai/gpt-4o" in available_models else None
        preferred_haiku = "gpt-4o-mini" if "openai/gpt-4o-mini" in available_models else None
        
        # If we don't have preferred models, use the first available OpenAI model
        if not preferred_sonnet and openai_models:
            preferred_sonnet = openai_models[0].replace("openai/", "")
        if not preferred_haiku and openai_models:
            preferred_haiku = openai_models[0].replace("openai/", "")
        
        # Map Claude models to available models
        if preferred_sonnet:
            model_map.update({
                "claude-3-5-sonnet-20241022": preferred_sonnet,
                "claude-sonnet-4-20250514": preferred_sonnet,
            })
        
        if preferred_haiku:
            model_map["claude-3-5-haiku-20241022"] = preferred_haiku
        
        # Add direct mappings for available models
        for model_id in available_models:
            if "/" in model_id:
                # Extract model name without prefix
                model_name = model_id.split("/", 1)[1]
                model_map[model_name] = model_name
                model_map[model_id] = model_name
            else:
                model_map[model_id] = model_id
        
        return model_map
    
    async def map_model(self, model: str) -> str:
        """Map Claude model names to GitHub Models"""
        model_map = self.provider_config["models"]
        
        # Remove provider prefixes if present
        clean_model = model
        if clean_model.startswith('anthropic/'):
            clean_model = clean_model[10:]
        elif clean_model.startswith('openai/'):
            clean_model = clean_model[7:]
        elif clean_model.startswith('github/'):
            clean_model = clean_model[7:]
        
        # Map to GitHub Models format
        if clean_model in model_map:
            mapped = f"github/{model_map[clean_model]}"
            self.logger.info(f"🔄 Model mapped: {model} -> {mapped}")
            return mapped
        
        # Default mapping for Haiku/Sonnet patterns
        if 'haiku' in clean_model.lower():
            mapped = "github/claude-3-5-haiku"
            self.logger.info(f"🔄 Model mapped (haiku pattern): {model} -> {mapped}")
            return mapped
        elif 'sonnet' in clean_model.lower():
            mapped = "github/claude-3-5-sonnet"  
            self.logger.info(f"🔄 Model mapped (sonnet pattern): {model} -> {mapped}")
            return mapped
        
        # Fallback to original model name with github prefix
        mapped = f"github/{clean_model}"
        self.logger.warning(f"⚠️ Model mapped (fallback): {model} -> {mapped}")
        return mapped
    
    async def check_provider_health(self) -> bool:
        """Check GitHub Models API health"""
        try:
            if not self.provider_config.get("token"):
                return False
            
            # Test API connectivity
            headers = {
                "Authorization": f"Bearer {self.provider_config['token']}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to get models list (if endpoint supports it)
                response = await client.get(
                    f"{self.provider_config['endpoint']}/models",
                    headers=headers
                )
                
                # GitHub Models may not have a models endpoint, so check for common HTTP responses
                if response.status_code in [200, 404, 403]:  # 404/403 are ok, means endpoint exists
                    self.logger.debug("✅ GitHub Models API connectivity confirmed")
                    return True
                    
        except Exception as e:
            self.logger.error(f"❌ GitHub Models health check failed: {str(e)}")
        
        return False
    
    async def get_available_models(self) -> dict:
        """Get list of available GitHub Models"""
        models = []
        
        for claude_model, github_model in self.provider_config["models"].items():
            models.append({
                "id": claude_model,
                "object": "model",
                "created": 1677610602,
                "owned_by": "github",
                "provider_model": f"github/{github_model}"
            })
        
        return {
            "object": "list",
            "data": models
        }
    
    async def prepare_litellm_params(self, request_data: dict, mapped_model: str) -> dict:
        """Prepare GitHub Models specific parameters"""
        params = await super().prepare_litellm_params(request_data, mapped_model)
        
        # GitHub Models specific configurations
        params["timeout"] = 60  # Longer timeout for Azure backend
        
        # Validate max_tokens for GitHub Models
        max_tokens = params.get("max_tokens", 4096)
        if max_tokens > 8192:
            self.logger.warning(f"⚠️ Limiting max_tokens from {max_tokens} to 8192 for GitHub Models")
            params["max_tokens"] = 8192
        
        return params

def create_service(port: int = 8092) -> GitHubModelsService:
    """Factory function to create GitHub Models service"""
    return GitHubModelsService(port)

if __name__ == "__main__":
    # Run GitHub Models service standalone
    service = GitHubModelsService(8092)
    service.run()