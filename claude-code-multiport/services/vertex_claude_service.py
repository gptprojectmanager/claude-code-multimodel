#!/usr/bin/env python3
"""
Vertex AI Claude Service - Port 8090
Multi-Port Claude Code Service for Vertex AI Claude models (us-east5)

Based on claude-code-proxy patterns with LiteLLM library integration.
Primary service for Claude models via Google Cloud Vertex AI.
"""

import os
import httpx
from typing import Dict, Any, Optional
from .base_service import BaseMultiPortService
import litellm

class VertexClaudeService(BaseMultiPortService):
    """
    Vertex AI Claude service implementation
    
    Primary service for Claude models via Google Cloud Vertex AI in us-east5 region
    """
    
    def __init__(self, port: int = 8090):
        # Configuration for Vertex AI Claude
        config = {
            "service_name": "vertex-claude",
            "provider": "vertex_ai",
            "port": port,
            "project": os.environ.get("GOOGLE_CLOUD_PROJECT", "custom-mix-460500-g9"),
            "location": os.environ.get("VERTEX_AI_LOCATION", "us-east5"),
            "credentials": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "models": {
                # Claude model mappings for us-east5
                "claude-sonnet-4-20250514": "claude-sonnet-4@20250514",
                "claude-3-5-sonnet-20241022": "claude-3-5-sonnet@20240620",
                "claude-3-5-haiku-20241022": "claude-3-5-haiku@20241022",
                
                # Fallback mappings for various Claude model names
                "claude-3-5-sonnet": "claude-3-5-sonnet@20240620",
                "claude-3-haiku": "claude-3-5-haiku@20241022"
            }
        }
        
        super().__init__(port, config)
        
        # Validate Google Cloud configuration
        if not config["project"]:
            self.logger.warning("⚠️ GOOGLE_CLOUD_PROJECT not set - service may not work")
        
        self.logger.info(f"🔵 Vertex AI configured: project={config['project']}, location={config['location']}")
    
    def configure_litellm(self):
        """Configure LiteLLM for Vertex AI"""
        super().configure_litellm()
        
        # Set Vertex AI environment variables for LiteLLM
        os.environ["VERTEX_PROJECT"] = self.provider_config["project"]
        os.environ["VERTEX_LOCATION"] = self.provider_config["location"]
        
        # Set credentials if provided
        if self.provider_config.get("credentials"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.provider_config["credentials"]
            self.logger.info("🔧 Google Application Credentials configured")
        else:
            self.logger.info("🔧 Using default Google Cloud credentials (gcloud auth)")
        
        self.logger.info(f"✅ Vertex AI LiteLLM configured: {self.provider_config['location']}")
    
    async def map_model(self, model: str) -> str:
        """Map Claude model names to Vertex AI format"""
        model_map = self.provider_config["models"]
        
        # Remove provider prefixes if present
        clean_model = model
        prefixes = ['anthropic/', 'vertex_ai/', 'vertex/', 'claude/']
        for prefix in prefixes:
            if clean_model.startswith(prefix):
                clean_model = clean_model[len(prefix):]
                break
        
        # Direct mapping if available
        if clean_model in model_map:
            mapped = f"vertex_ai/{model_map[clean_model]}"
            self.logger.info(f"🔄 Model mapped: {model} -> {mapped}")
            return mapped
        
        # Pattern-based mapping for Claude models
        if 'sonnet-4' in clean_model.lower() or 'sonnet4' in clean_model.lower():
            mapped = "vertex_ai/claude-sonnet-4@20250514"
            self.logger.info(f"🔄 Model mapped (sonnet-4 pattern): {model} -> {mapped}")
            return mapped
        elif 'sonnet' in clean_model.lower():
            mapped = "vertex_ai/claude-3-5-sonnet@20240620"
            self.logger.info(f"🔄 Model mapped (sonnet pattern): {model} -> {mapped}")
            return mapped
        elif 'haiku' in clean_model.lower():
            mapped = "vertex_ai/claude-3-5-haiku@20241022"
            self.logger.info(f"🔄 Model mapped (haiku pattern): {model} -> {mapped}")
            return mapped
        
        # Default to Sonnet if it's a Claude model
        if 'claude' in clean_model.lower():
            mapped = "vertex_ai/claude-3-5-sonnet@20240620"
            self.logger.warning(f"⚠️ Model mapped (claude fallback): {model} -> {mapped}")
            return mapped
        
        # Final fallback
        mapped = f"vertex_ai/{clean_model}"
        self.logger.warning(f"⚠️ Model mapped (final fallback): {model} -> {mapped}")
        return mapped
    
    async def check_provider_health(self) -> bool:
        """Check Vertex AI health and authentication"""
        try:
            # Test authentication by attempting to list models (if possible)
            # This is a basic connectivity test
            
            # For now, we'll do a simple environment check
            required_vars = ["VERTEX_PROJECT", "VERTEX_LOCATION"]
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            
            if missing_vars:
                self.logger.error(f"❌ Missing required environment variables: {missing_vars}")
                return False
            
            # Additional check: verify gcloud auth or service account
            credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path:
                # Check if service account file exists
                if not os.path.exists(credentials_path):
                    self.logger.error(f"❌ Service account file not found: {credentials_path}")
                    return False
                self.logger.debug("✅ Service account file found")
            else:
                # Using default credentials (gcloud auth)
                self.logger.debug("✅ Using default Google Cloud credentials")
            
            self.logger.debug("✅ Vertex AI configuration appears valid")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Vertex AI health check failed: {str(e)}")
            return False
    
    async def get_available_models(self) -> dict:
        """Get list of available Vertex AI Claude models"""
        models = []
        
        for claude_model, vertex_model in self.provider_config["models"].items():
            models.append({
                "id": claude_model,
                "object": "model",
                "created": 1677610602,
                "owned_by": "google",
                "provider_model": f"vertex_ai/{vertex_model}",
                "region": self.provider_config["location"]
            })
        
        return {
            "object": "list",
            "data": models,
            "region": self.provider_config["location"],
            "project": self.provider_config["project"]
        }
    
    async def prepare_litellm_params(self, request_data: dict, mapped_model: str) -> dict:
        """Prepare Vertex AI specific parameters"""
        params = await super().prepare_litellm_params(request_data, mapped_model)
        
        # Vertex AI specific configurations
        params["timeout"] = 90  # Longer timeout for Vertex AI
        
        # Vertex AI Claude models have specific token limits
        max_tokens = params.get("max_tokens", 4096)
        if max_tokens > 8192:
            self.logger.warning(f"⚠️ Limiting max_tokens from {max_tokens} to 8192 for Vertex AI Claude")
            params["max_tokens"] = 8192
        
        # Add Vertex AI specific metadata
        if "extra_headers" not in params:
            params["extra_headers"] = {}
        
        params["extra_headers"]["User-Agent"] = "Claude-Code-MultiPort/1.0"
        
        return params

def create_service(port: int = 8090) -> VertexClaudeService:
    """Factory function to create Vertex AI Claude service"""
    return VertexClaudeService(port)

if __name__ == "__main__":
    # Run Vertex AI Claude service standalone
    service = VertexClaudeService(8090)
    service.run()