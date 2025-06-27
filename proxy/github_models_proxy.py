#!/usr/bin/env python3
"""
GitHub Models Proxy for Claude Code
Based on claude-code-litellm integration
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubModelsProxy:
    """
    Proxy server that translates Anthropic API calls to GitHub Models via liteLLM
    """
    
    def __init__(self):
        self.app = FastAPI(title="GitHub Models Proxy for Claude Code")
        self.setup_cors()
        self.setup_routes()
        
        # Configuration
        self.github_token = os.getenv('GITHUB_TOKEN', '')
        self.github_api_base = os.getenv('GITHUB_MODELS_API_BASE', 'https://models.inference.ai.azure.com')
        self.litellm_base_url = os.getenv('LITELLM_BASE_URL', 'http://localhost:8083')
        
        # Model mapping
        self.model_mapping = {
            'claude-3-haiku-20240307': os.getenv('GITHUB_SMALL_MODEL', 'gpt-4o-mini'),
            'claude-3-5-haiku-20241022': os.getenv('GITHUB_SMALL_MODEL', 'gpt-4o-mini'),
            'claude-3-sonnet-20240229': os.getenv('GITHUB_BIG_MODEL', 'gpt-4o'),
            'claude-3-5-sonnet-20241022': os.getenv('GITHUB_BIG_MODEL', 'gpt-4o'),
            'claude-sonnet-4-20250514': os.getenv('GITHUB_BIG_MODEL', 'gpt-4o'),
        }
        
        # Cost tracking
        self.usage_log_file = os.getenv('GITHUB_MODELS_COST_LOG_FILE', '/tmp/github-models-usage.log')
        self.enable_cost_tracking = os.getenv('ENABLE_GITHUB_MODELS_COST_TRACKING', 'true').lower() == 'true'
        
        # Rate limiting
        self.max_requests_per_minute = int(os.getenv('GITHUB_MODELS_MAX_REQUESTS_PER_MINUTE', '60'))
        self.max_tokens_per_minute = int(os.getenv('GITHUB_MODELS_MAX_TOKENS_PER_MINUTE', '50000'))
        
        logger.info(f"GitHub Models Proxy initialized")
        logger.info(f"GitHub API Base: {self.github_api_base}")
        logger.info(f"Model Mapping: {self.model_mapping}")

    def setup_cors(self):
        """Setup CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "GitHub Models Proxy for Claude Code", "status": "running"}

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.post("/v1/messages")
        async def create_message(request: Request):
            """Main endpoint that handles Anthropic API calls"""
            try:
                body = await request.json()
                return await self.handle_anthropic_request(body, request.headers)
            except Exception as e:
                logger.error(f"Error in /v1/messages: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/v1/models")
        async def list_models():
            """List available models"""
            models = []
            for anthropic_model, github_model in self.model_mapping.items():
                models.append({
                    "id": anthropic_model,
                    "object": "model",
                    "created": int(datetime.now().timestamp()),
                    "owned_by": "github-models",
                    "mapped_to": github_model
                })
            return {"object": "list", "data": models}

    async def handle_anthropic_request(self, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert Anthropic API request to GitHub Models format and proxy it
        """
        # Extract model from request
        anthropic_model = body.get('model', 'claude-3-5-sonnet-20241022')
        github_model = self.model_mapping.get(anthropic_model, 'gpt-4o')
        
        logger.info(f"Mapping {anthropic_model} -> {github_model}")
        
        # Convert Anthropic messages format to OpenAI format
        openai_body = self.convert_anthropic_to_openai(body, github_model)
        
        # Log usage for cost tracking
        if self.enable_cost_tracking:
            self.log_usage(anthropic_model, github_model, body)
        
        # Make request to GitHub Models via OpenAI-compatible endpoint
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.github_api_base}/v1/chat/completions",
                    json=openai_body,
                    headers={
                        "Authorization": f"Bearer {self.github_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=300.0
                )
                
                response.raise_for_status()
                openai_response = response.json()
                
                # Convert back to Anthropic format
                anthropic_response = self.convert_openai_to_anthropic(openai_response, anthropic_model)
                
                return anthropic_response
                
            except httpx.HTTPStatusError as e:
                logger.error(f"GitHub Models API error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 429:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
            except Exception as e:
                logger.error(f"Error calling GitHub Models API: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def convert_anthropic_to_openai(self, body: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Convert Anthropic API format to OpenAI format"""
        messages = []
        
        # Handle system message
        if 'system' in body:
            messages.append({
                "role": "system",
                "content": body['system']
            })
        
        # Convert messages
        for msg in body.get('messages', []):
            role = msg['role']
            content = msg['content']
            
            # Handle different content formats
            if isinstance(content, str):
                messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle multi-modal content
                text_parts = []
                for part in content:
                    if part.get('type') == 'text':
                        text_parts.append(part['text'])
                    elif part.get('type') == 'image':
                        # GitHub Models may not support images for all models
                        text_parts.append("[Image content not supported]")
                
                messages.append({"role": role, "content": " ".join(text_parts)})
        
        openai_body = {
            "model": model,
            "messages": messages,
            "temperature": body.get('temperature', 0.7),
            "max_tokens": body.get('max_tokens', 1024),
            "stream": body.get('stream', False),
        }
        
        # Add additional parameters if present
        if 'top_p' in body:
            openai_body['top_p'] = body['top_p']
        if 'stop_sequences' in body:
            openai_body['stop'] = body['stop_sequences']
            
        return openai_body

    def convert_openai_to_anthropic(self, response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Convert OpenAI API response to Anthropic format"""
        choice = response['choices'][0]
        message = choice['message']
        
        anthropic_response = {
            "id": response.get('id', 'msg_github_models'),
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": message['content']
                }
            ],
            "model": model,
            "stop_reason": self.map_finish_reason(choice.get('finish_reason')),
            "stop_sequence": None,
            "usage": {
                "input_tokens": response.get('usage', {}).get('prompt_tokens', 0),
                "output_tokens": response.get('usage', {}).get('completion_tokens', 0)
            }
        }
        
        return anthropic_response

    def map_finish_reason(self, openai_reason: str) -> str:
        """Map OpenAI finish reason to Anthropic format"""
        mapping = {
            'stop': 'end_turn',
            'length': 'max_tokens',
            'content_filter': 'stop_sequence',
            'function_call': 'tool_use',
            None: 'end_turn'
        }
        return mapping.get(openai_reason, 'end_turn')

    def log_usage(self, anthropic_model: str, github_model: str, body: Dict[str, Any]):
        """Log usage for cost tracking"""
        try:
            usage_entry = {
                "timestamp": datetime.now().isoformat(),
                "anthropic_model": anthropic_model,
                "github_model": github_model,
                "estimated_input_tokens": self.estimate_tokens(body.get('messages', [])),
                "max_tokens": body.get('max_tokens', 1024),
                "temperature": body.get('temperature', 0.7),
            }
            
            with open(self.usage_log_file, 'a') as f:
                f.write(json.dumps(usage_entry) + '\n')
                
        except Exception as e:
            logger.warning(f"Failed to log usage: {e}")

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Rough estimation of token count"""
        total_chars = 0
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for part in content:
                    if part.get('type') == 'text':
                        total_chars += len(part.get('text', ''))
        
        # Rough estimation: 4 characters per token
        return total_chars // 4

def main():
    """Main function to start the server"""
    proxy = GitHubModelsProxy()
    
    host = os.getenv('LITELLM_HOST', '0.0.0.0')
    port = int(os.getenv('LITELLM_PORT', '8083'))
    
    logger.info(f"Starting GitHub Models Proxy on {host}:{port}")
    
    uvicorn.run(
        proxy.app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()