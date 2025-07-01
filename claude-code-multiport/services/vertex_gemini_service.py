#!/usr/bin/env python3
"""
Vertex AI Gemini Service - Port 8091
Multi-Port Claude Code Service for Vertex AI Gemini models (us-east5)

Based on claude-code-proxy patterns with LiteLLM library integration.
Secondary service for Google's Gemini models via Vertex AI.
"""

import os
import httpx
from typing import Dict, Any, Optional
from .base_service import BaseMultiPortService
import litellm

class VertexGeminiService(BaseMultiPortService):
    """
    Vertex AI Gemini service implementation
    
    Secondary service for Google's Gemini models via Vertex AI in us-east5 region
    """
    
    def __init__(self, port: int = 8091):
        # Configuration for Vertex AI Gemini
        config = {
            "service_name": "vertex-gemini",
            "provider": "vertex_ai_gemini",
            "port": port,
            "project": os.environ.get("GOOGLE_CLOUD_PROJECT", "custom-mix-460500-g9"),
            "location": os.environ.get("VERTEX_AI_LOCATION", "us-east5"),
            "credentials": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "models": {
                # Gemini model mappings for us-east5
                "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
                "gemini-1.5-pro": "gemini-1.5-pro-002",
                "gemini-1.5-flash": "gemini-1.5-flash-002",
                "gemini-1.5-pro-002": "gemini-1.5-pro-002",
                "gemini-1.5-flash-002": "gemini-1.5-flash-002",
                
                # Claude fallback mappings to Gemini (when Claude is unavailable)
                "claude-3-5-sonnet-20241022": "gemini-1.5-pro-002",  # Map Sonnet to Pro
                "claude-3-5-haiku-20241022": "gemini-1.5-flash-002",  # Map Haiku to Flash
                "claude-sonnet-4-20250514": "gemini-2.0-flash-exp"   # Map Sonnet-4 to 2.0
            }
        }
        
        super().__init__(port, config)
        
        # Validate Google Cloud configuration
        if not config["project"]:
            self.logger.warning("⚠️ GOOGLE_CLOUD_PROJECT not set - service may not work")
        
        self.logger.info(f"🟡 Vertex AI Gemini configured: project={config['project']}, location={config['location']}")
    
    def configure_litellm(self):
        """Configure LiteLLM for Vertex AI Gemini"""
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
        
        self.logger.info(f"✅ Vertex AI Gemini LiteLLM configured: {self.provider_config['location']}")
    
    async def map_model(self, model: str) -> str:
        """Map model names to Vertex AI Gemini format"""
        model_map = self.provider_config["models"]
        
        # Remove provider prefixes if present
        clean_model = model
        prefixes = ['google/', 'vertex_ai/', 'vertex/', 'gemini/', 'anthropic/', 'claude/']
        for prefix in prefixes:
            if clean_model.startswith(prefix):
                clean_model = clean_model[len(prefix):]
                break
        
        # Direct mapping if available
        if clean_model in model_map:
            mapped = f"vertex_ai/{model_map[clean_model]}"
            self.logger.info(f"🔄 Model mapped: {model} -> {mapped}")
            return mapped
        
        # Pattern-based mapping for Gemini models
        if 'gemini-2' in clean_model.lower() or '2.0' in clean_model:
            mapped = "vertex_ai/gemini-2.0-flash-exp"
            self.logger.info(f"🔄 Model mapped (gemini-2 pattern): {model} -> {mapped}")
            return mapped
        elif 'pro' in clean_model.lower():
            mapped = "vertex_ai/gemini-1.5-pro-002"
            self.logger.info(f"🔄 Model mapped (pro pattern): {model} -> {mapped}")
            return mapped
        elif 'flash' in clean_model.lower():
            mapped = "vertex_ai/gemini-1.5-flash-002"
            self.logger.info(f"🔄 Model mapped (flash pattern): {model} -> {mapped}")
            return mapped
        
        # Claude to Gemini fallback mappings
        if 'sonnet-4' in clean_model.lower() or 'sonnet4' in clean_model.lower():
            mapped = "vertex_ai/gemini-2.0-flash-exp"
            self.logger.info(f"🔄 Model mapped (claude sonnet-4 → gemini-2.0): {model} -> {mapped}")
            return mapped
        elif 'sonnet' in clean_model.lower():
            mapped = "vertex_ai/gemini-1.5-pro-002"
            self.logger.info(f"🔄 Model mapped (claude sonnet → gemini-pro): {model} -> {mapped}")
            return mapped
        elif 'haiku' in clean_model.lower():
            mapped = "vertex_ai/gemini-1.5-flash-002"
            self.logger.info(f"🔄 Model mapped (claude haiku → gemini-flash): {model} -> {mapped}")
            return mapped
        elif 'claude' in clean_model.lower():
            # General Claude fallback to Gemini Pro
            mapped = "vertex_ai/gemini-1.5-pro-002"
            self.logger.warning(f"⚠️ Model mapped (claude fallback → gemini-pro): {model} -> {mapped}")
            return mapped
        
        # Default to Gemini Flash for unknown models
        if 'gemini' in clean_model.lower():
            mapped = f"vertex_ai/{clean_model}"
        else:
            mapped = "vertex_ai/gemini-1.5-flash-002"
        
        self.logger.warning(f"⚠️ Model mapped (default fallback): {model} -> {mapped}")
        return mapped
    
    async def check_provider_health(self) -> bool:
        """Check Vertex AI Gemini health and authentication"""
        try:
            # Test authentication by checking environment variables
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
            
            self.logger.debug("✅ Vertex AI Gemini configuration appears valid")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Vertex AI Gemini health check failed: {str(e)}")
            return False
    
    async def get_available_models(self) -> dict:
        """Get list of available Vertex AI Gemini models"""
        models = []
        
        # Include native Gemini models
        gemini_models = {
            "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
            "gemini-1.5-pro-002": "gemini-1.5-pro-002", 
            "gemini-1.5-flash-002": "gemini-1.5-flash-002"
        }
        
        for model_id, vertex_model in gemini_models.items():
            models.append({
                "id": model_id,
                "object": "model",
                "created": 1677610602,
                "owned_by": "google",
                "provider_model": f"vertex_ai/{vertex_model}",
                "region": self.provider_config["location"],
                "type": "gemini"
            })
        
        # Include Claude fallback mappings
        claude_fallbacks = {
            "claude-3-5-sonnet-20241022": "gemini-1.5-pro-002",
            "claude-3-5-haiku-20241022": "gemini-1.5-flash-002",
            "claude-sonnet-4-20250514": "gemini-2.0-flash-exp"
        }
        
        for claude_model, gemini_model in claude_fallbacks.items():
            models.append({
                "id": claude_model,
                "object": "model",
                "created": 1677610602,
                "owned_by": "google",
                "provider_model": f"vertex_ai/{gemini_model}",
                "region": self.provider_config["location"],
                "type": "claude_fallback"
            })
        
        return {
            "object": "list",
            "data": models,
            "region": self.provider_config["location"],
            "project": self.provider_config["project"],
            "note": "This service provides Gemini models and Claude fallback mappings"
        }
    
    async def prepare_litellm_params(self, request_data: dict, mapped_model: str) -> dict:
        """Prepare Vertex AI Gemini specific parameters"""
        params = await super().prepare_litellm_params(request_data, mapped_model)
        
        # Vertex AI Gemini specific configurations
        params["timeout"] = 90  # Longer timeout for Vertex AI
        
        # Gemini models support higher token limits
        max_tokens = params.get("max_tokens", 4096)
        if max_tokens > 32768:  # Gemini supports up to 32K tokens
            self.logger.warning(f"⚠️ Limiting max_tokens from {max_tokens} to 32768 for Vertex AI Gemini")
            params["max_tokens"] = 32768
        
        # Add Vertex AI specific metadata
        if "extra_headers" not in params:
            params["extra_headers"] = {}
        
        params["extra_headers"]["User-Agent"] = "Claude-Code-MultiPort-Gemini/1.0"
        
        return params

def create_service(port: int = 8091) -> VertexGeminiService:
    """Factory function to create Vertex AI Gemini service"""
    return VertexGeminiService(port)

if __name__ == "__main__":
    # Run Vertex AI Gemini service standalone
    service = VertexGeminiService(8091)
    service.run()