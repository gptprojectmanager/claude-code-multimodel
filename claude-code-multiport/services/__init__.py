"""
Multi-Port Claude Code Services
===============================

FastAPI + LiteLLM based services for multiple AI providers:
- Vertex AI Claude Service (Port 8090) - Primary Claude models via Vertex AI us-east5
- Vertex AI Gemini Service (Port 8091) - Google Gemini models via Vertex AI us-east5
- GitHub Models Service (Port 8092) - Azure-backed Claude access
- OpenRouter Service (Port 8093) - 100+ model access
"""

from .base_service import BaseMultiPortService
from .vertex_claude_service import VertexClaudeService
from .vertex_gemini_service import VertexGeminiService
from .github_models_service import GitHubModelsService
from .openrouter_service import OpenRouterService

__all__ = [
    "BaseMultiPortService",
    "VertexClaudeService",
    "VertexGeminiService", 
    "GitHubModelsService", 
    "OpenRouterService"
]