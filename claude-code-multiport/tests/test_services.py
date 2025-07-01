#!/usr/bin/env python3
"""
Tests for Multi-Port Services
=============================

Basic tests to verify service functionality
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import patch, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseMultiPortService
from services.github_models_service import GitHubModelsService
from services.openrouter_service import OpenRouterService

class TestBaseService:
    """Test base service functionality"""
    
    def test_base_service_initialization(self):
        """Test that base service initializes correctly"""
        config = {
            "service_name": "test-service",
            "provider": "test",
            "port": 8080
        }
        
        service = BaseMultiPortService(8080, config)
        
        assert service.port == 8080
        assert service.service_name == "test-service"
        assert service.provider == "test"
        assert service.app is not None
    
    @pytest.mark.asyncio
    async def test_base_service_health_check(self):
        """Test health check endpoint"""
        config = {
            "service_name": "test-service",
            "provider": "test",
            "port": 8080
        }
        
        service = BaseMultiPortService(8080, config)
        health = await service.get_health_status()
        
        assert health["service_name"] == "test-service"
        assert health["provider"] == "test"
        assert health["port"] == 8080
        assert "status" in health
    
    @pytest.mark.asyncio
    async def test_model_mapping_default(self):
        """Test default model mapping"""
        config = {
            "service_name": "test-service",
            "provider": "test",
            "port": 8080
        }
        
        service = BaseMultiPortService(8080, config)
        mapped = await service.map_model("claude-3-5-sonnet")
        
        assert mapped == "claude-3-5-sonnet"  # Default returns same model

class TestGitHubModelsService:
    """Test GitHub Models service"""
    
    def test_github_service_initialization(self):
        """Test GitHub Models service initialization"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}, clear=False):
            service = GitHubModelsService(8092)
            
            assert service.port == 8092
            assert service.service_name == "github-models"
            assert service.provider == "github_models"
    
    @pytest.mark.asyncio
    async def test_github_model_mapping(self):
        """Test GitHub Models model mapping"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}, clear=False):
            service = GitHubModelsService(8092)
            
            # Test specific mappings
            mapped = await service.map_model("claude-3-5-sonnet-20241022")
            assert mapped == "github/claude-3-5-sonnet"
            
            # Test haiku pattern
            mapped = await service.map_model("claude-3-5-haiku-20241022")  
            assert mapped == "github/claude-3-5-haiku"
            
            # Test pattern matching
            mapped = await service.map_model("some-haiku-model")
            assert mapped == "github/claude-3-5-haiku"
            
            mapped = await service.map_model("some-sonnet-model")
            assert mapped == "github/claude-3-5-sonnet"
    
    @pytest.mark.asyncio
    async def test_github_available_models(self):
        """Test getting available models"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}, clear=False):
            service = GitHubModelsService(8092)
            models = await service.get_available_models()
            
            assert models["object"] == "list"
            assert len(models["data"]) > 0
            assert all("id" in model for model in models["data"])

class TestOpenRouterService:
    """Test OpenRouter service"""
    
    def test_openrouter_service_initialization(self):
        """Test OpenRouter service initialization"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}, clear=False):
            service = OpenRouterService(8093)
            
            assert service.port == 8093
            assert service.service_name == "openrouter"
            assert service.provider == "openrouter"
    
    @pytest.mark.asyncio
    async def test_openrouter_model_mapping(self):
        """Test OpenRouter model mapping"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}, clear=False):
            service = OpenRouterService(8093)
            
            # Test specific mappings
            mapped = await service.map_model("claude-3-5-sonnet-20241022")
            assert mapped == "openrouter/anthropic/claude-3.5-sonnet"
            
            # Test pattern matching
            mapped = await service.map_model("some-haiku-model")
            assert mapped == "openrouter/anthropic/claude-3-haiku"
            
            mapped = await service.map_model("gpt-4o-mini")
            assert mapped == "openrouter/openai/gpt-4o-mini"
    
    @pytest.mark.asyncio
    async def test_openrouter_available_models(self):
        """Test getting available models"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}, clear=False):
            service = OpenRouterService(8093)
            models = await service.get_available_models()
            
            assert models["object"] == "list"
            assert len(models["data"]) > 0
            assert all("id" in model for model in models["data"])

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])