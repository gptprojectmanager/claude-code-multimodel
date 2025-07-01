#!/usr/bin/env python3
"""
GitHub Models Service - Port 8092
Multi-Port Claude Code Service for GitHub Models (Azure-backed)

Based on claude-code-proxy patterns with LiteLLM library integration.
"""

import os
import httpx
from typing import Dict, Any, Optional
from .base_service import BaseMultiPortService
import litellm

class GitHubModelsService(BaseMultiPortService):
    """
    GitHub Models service implementation
    
    Provides access to Claude models via GitHub Models API (Azure-backed)
    """
    
    def __init__(self, port: int = 8092):
        # Configuration for GitHub Models
        config = {
            "service_name": "github-models",
            "provider": "github_models",
            "port": port,
            "endpoint": os.environ.get("GITHUB_MODELS_ENDPOINT", "https://models.inference.ai.azure.com"),
            "token": os.environ.get("GITHUB_TOKEN"),
            "models": {
                # Claude model mappings
                "claude-3-5-sonnet-20241022": "claude-3-5-sonnet",
                "claude-3-5-haiku-20241022": "claude-3-5-haiku", 
                "claude-sonnet-4-20250514": "claude-3-5-sonnet",  # Fallback to available model
                
                # OpenAI model mappings
                "gpt-4o": "gpt-4o",
                "gpt-4o-mini": "gpt-4o-mini"
            }
        }
        
        super().__init__(port, config)
        
        # Validate GitHub token
        if not config["token"]:
            self.logger.warning("⚠️ GITHUB_TOKEN not set - service may not work properly")
    
    def configure_litellm(self):
        """Configure LiteLLM for GitHub Models"""
        super().configure_litellm()
        
        # Set GitHub token for LiteLLM
        if self.provider_config.get("token"):
            os.environ["GITHUB_TOKEN"] = self.provider_config["token"]
            self.logger.info("🔧 GitHub token configured for LiteLLM")
    
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