#!/usr/bin/env python3
"""
Tests for Vertex AI Services
============================

Tests for Vertex AI Claude and Gemini services
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import patch, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vertex_claude_service import VertexClaudeService
from services.vertex_gemini_service import VertexGeminiService

class TestVertexClaudeService:
    """Test Vertex AI Claude service functionality"""
    
    def test_vertex_claude_initialization(self):
        """Test that Vertex Claude service initializes correctly"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexClaudeService(8090)
            
            assert service.port == 8090
            assert service.service_name == "vertex-claude"
            assert service.provider == "vertex_ai"
            assert service.provider_config["location"] == "us-east5"
    
    @pytest.mark.asyncio
    async def test_vertex_claude_model_mapping(self):
        """Test Vertex Claude model mapping"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexClaudeService(8090)
            
            # Test specific mappings
            mapped = await service.map_model("claude-sonnet-4-20250514")
            assert mapped == "vertex_ai/claude-sonnet-4@20250514"
            
            mapped = await service.map_model("claude-3-5-sonnet-20241022")
            assert mapped == "vertex_ai/claude-3-5-sonnet@20240620"
            
            # Test pattern matching
            mapped = await service.map_model("some-sonnet-4-model")
            assert mapped == "vertex_ai/claude-sonnet-4@20250514"
            
            mapped = await service.map_model("some-haiku-model")
            assert mapped == "vertex_ai/claude-3-5-haiku@20241022"
            
            # Test Claude fallback
            mapped = await service.map_model("claude-unknown-model")
            assert mapped == "vertex_ai/claude-3-5-sonnet@20240620"
    
    @pytest.mark.asyncio
    async def test_vertex_claude_health_check(self):
        """Test Vertex Claude health check"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5",
            "VERTEX_PROJECT": "test-project",
            "VERTEX_LOCATION": "us-east5"
        }, clear=False):
            service = VertexClaudeService(8090)
            health = await service.check_provider_health()
            
            # Should be healthy with proper environment variables
            assert health == True
    
    @pytest.mark.asyncio
    async def test_vertex_claude_available_models(self):
        """Test getting available Vertex Claude models"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexClaudeService(8090)
            models = await service.get_available_models()
            
            assert models["object"] == "list"
            assert len(models["data"]) > 0
            assert models["region"] == "us-east5"
            assert models["project"] == "test-project"
            assert all("provider_model" in model for model in models["data"])

class TestVertexGeminiService:
    """Test Vertex AI Gemini service functionality"""
    
    def test_vertex_gemini_initialization(self):
        """Test that Vertex Gemini service initializes correctly"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexGeminiService(8091)
            
            assert service.port == 8091
            assert service.service_name == "vertex-gemini"
            assert service.provider == "vertex_ai_gemini"
            assert service.provider_config["location"] == "us-east5"
    
    @pytest.mark.asyncio
    async def test_vertex_gemini_model_mapping(self):
        """Test Vertex Gemini model mapping"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexGeminiService(8091)
            
            # Test Gemini specific mappings
            mapped = await service.map_model("gemini-2.0-flash-exp")
            assert mapped == "vertex_ai/gemini-2.0-flash-exp"
            
            mapped = await service.map_model("gemini-1.5-pro")
            assert mapped == "vertex_ai/gemini-1.5-pro-002"
            
            # Test pattern matching
            mapped = await service.map_model("gemini-2-something")
            assert mapped == "vertex_ai/gemini-2.0-flash-exp"
            
            mapped = await service.map_model("some-pro-model")
            assert mapped == "vertex_ai/gemini-1.5-pro-002"
            
            mapped = await service.map_model("some-flash-model")
            assert mapped == "vertex_ai/gemini-1.5-flash-002"
            
            # Test Claude to Gemini fallback mappings
            mapped = await service.map_model("claude-3-5-sonnet-20241022")
            assert mapped == "vertex_ai/gemini-1.5-pro-002"
            
            mapped = await service.map_model("claude-3-5-haiku-20241022")
            assert mapped == "vertex_ai/gemini-1.5-flash-002"
            
            mapped = await service.map_model("claude-sonnet-4-20250514")
            assert mapped == "vertex_ai/gemini-2.0-flash-exp"
    
    @pytest.mark.asyncio
    async def test_vertex_gemini_health_check(self):
        """Test Vertex Gemini health check"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5",
            "VERTEX_PROJECT": "test-project",
            "VERTEX_LOCATION": "us-east5"
        }, clear=False):
            service = VertexGeminiService(8091)
            health = await service.check_provider_health()
            
            # Should be healthy with proper environment variables
            assert health == True
    
    @pytest.mark.asyncio
    async def test_vertex_gemini_available_models(self):
        """Test getting available Vertex Gemini models"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexGeminiService(8091)
            models = await service.get_available_models()
            
            assert models["object"] == "list"
            assert len(models["data"]) > 0
            assert models["region"] == "us-east5"
            assert models["project"] == "test-project"
            
            # Check for both Gemini and Claude fallback models
            model_types = {model.get("type") for model in models["data"]}
            assert "gemini" in model_types
            assert "claude_fallback" in model_types
    
    @pytest.mark.asyncio
    async def test_vertex_gemini_token_limits(self):
        """Test Vertex Gemini token limit handling"""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "VERTEX_AI_LOCATION": "us-east5"
        }, clear=False):
            service = VertexGeminiService(8091)
            
            # Test high token count is properly limited
            request_data = {
                "model": "gemini-1.5-pro",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 50000  # Very high
            }
            
            params = await service.prepare_litellm_params(request_data, "vertex_ai/gemini-1.5-pro-002")
            
            # Should be limited to 32768 for Gemini
            assert params["max_tokens"] <= 32768

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])