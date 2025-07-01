#!/usr/bin/env python3
"""
Vertex AI Proxy for Claude Code
Handles Claude models via Google Cloud Vertex AI
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

# Try to import Google Cloud libraries
try:
    from google.cloud import aiplatform
    from google.auth import default
    from google.auth.transport.requests import Request as AuthRequest
    import google.auth.transport.requests
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VertexAIProxy:
    """
    Proxy server that translates Anthropic API calls to Google Vertex AI
    """
    
    def __init__(self):
        self.app = FastAPI(title="Vertex AI Proxy for Claude Code")
        self.setup_cors()
        self.setup_routes()
        
        # Configuration
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', '')
        self.location = os.getenv('VERTEX_AI_LOCATION', 'us-east5')
        self.service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', './config/vertex-service-account.json')
        
        # Model mapping
        self.model_mapping = {
            'claude-3-haiku-20240307': 'claude-3-haiku@20240307',
            'claude-3-5-haiku-20241022': 'claude-3-5-haiku@20241022',
            'claude-3-sonnet-20240229': 'claude-3-sonnet@20240229',
            'claude-3-5-sonnet-20241022': 'claude-3-5-sonnet@20241022',
            'claude-sonnet-4-20250514': 'claude-3-5-sonnet@20241022',  # Fallback to available model
        }
        
        # Cost tracking
        self.usage_log_file = os.getenv('VERTEX_USAGE_LOG_FILE', '/tmp/vertex-ai-usage.log')
        self.enable_cost_tracking = os.getenv('ENABLE_VERTEX_COST_TRACKING', 'true').lower() == 'true'
        
        # Rate limiting
        self.max_requests_per_minute = int(os.getenv('VERTEX_MAX_REQUESTS_PER_MINUTE', '60'))
        self.max_tokens_per_minute = int(os.getenv('VERTEX_MAX_TOKENS_PER_MINUTE', '50000'))
        
        # Initialize Vertex AI
        self.setup_vertex_ai()
        
        logger.info(f"Vertex AI Proxy initialized")
        logger.info(f"Project: {self.project_id}")
        logger.info(f"Location: {self.location}")
        logger.info(f"Model Mapping: {self.model_mapping}")

    def setup_vertex_ai(self):
        """Initialize Vertex AI client"""
        if not GOOGLE_AVAILABLE:
            logger.error("Google Cloud libraries not available. Install with: pip install google-cloud-aiplatform")
            raise ImportError("Google Cloud libraries not available")
        
        try:
            # Set up authentication
            if os.path.exists(self.service_account_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.service_account_path
                logger.info(f"Using service account: {self.service_account_path}")
            
            # Initialize Vertex AI
            aiplatform.init(project=self.project_id, location=self.location)
            logger.info("Vertex AI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise

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
            return {"message": "Vertex AI Proxy for Claude Code", "status": "running"}

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
            for anthropic_model, vertex_model in self.model_mapping.items():
                models.append({
                    "id": anthropic_model,
                    "object": "model",
                    "created": int(datetime.now().timestamp()),
                    "owned_by": "vertex-ai",
                    "mapped_to": vertex_model
                })
            return {"object": "list", "data": models}

    async def handle_anthropic_request(self, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert Anthropic API request to Vertex AI format and proxy it
        """
        # Extract model from request
        anthropic_model = body.get('model', 'claude-3-5-sonnet-20241022')
        vertex_model = self.model_mapping.get(anthropic_model, 'claude-3-5-sonnet@20241022')
        
        logger.info(f"Mapping {anthropic_model} -> {vertex_model}")
        
        # Log usage for cost tracking
        if self.enable_cost_tracking:
            self.log_usage(anthropic_model, vertex_model, body)
        
        try:
            # Make request to Vertex AI
            response = await self.call_vertex_ai(body, vertex_model)
            return response
            
        except Exception as e:
            logger.error(f"Error calling Vertex AI: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def call_vertex_ai(self, body: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        Call Vertex AI API with converted request
        """
        try:
            # Convert messages to Vertex AI format
            messages = self.convert_anthropic_to_vertex(body)
            
            # Prepare request parameters
            parameters = {
                "temperature": body.get('temperature', 0.7),
                "max_output_tokens": body.get('max_tokens', 1024),
                "top_p": body.get('top_p', 0.95),
            }
            
            # Use httpx to make the API call since we're in async context
            async with httpx.AsyncClient() as client:
                # Get access token
                credentials, project = default()
                auth_req = AuthRequest()
                credentials.refresh(auth_req)
                access_token = credentials.token
                
                # Prepare request
                url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/anthropic/models/{model}:streamGenerateContent"
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                
                # Prepare request body
                request_body = {
                    "contents": messages,
                    "generation_config": parameters,
                }
                
                response = await client.post(
                    url,
                    json=request_body,
                    headers=headers,
                    timeout=300.0
                )
                
                response.raise_for_status()
                vertex_response = response.json()
                
                # Convert back to Anthropic format
                anthropic_response = self.convert_vertex_to_anthropic(vertex_response, body.get('model', 'claude-3-5-sonnet-20241022'))
                
                return anthropic_response
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Vertex AI API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error(f"Error calling Vertex AI: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def convert_anthropic_to_vertex(self, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert Anthropic messages format to Vertex AI format"""
        contents = []
        
        # Handle system message if present
        if 'system' in body:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {body['system']}"}]
            })
        
        # Convert messages
        for msg in body.get('messages', []):
            role = "user" if msg['role'] == 'user' else "model"
            content = msg['content']
            
            # Handle different content formats
            if isinstance(content, str):
                contents.append({
                    "role": role,
                    "parts": [{"text": content}]
                })
            elif isinstance(content, list):
                # Handle multi-modal content
                parts = []
                for part in content:
                    if part.get('type') == 'text':
                        parts.append({"text": part['text']})
                    elif part.get('type') == 'image':
                        # Vertex AI supports images, but format may differ
                        parts.append({"text": "[Image content - format conversion needed]"})
                
                contents.append({
                    "role": role,
                    "parts": parts
                })
        
        return contents

    def convert_vertex_to_anthropic(self, response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Convert Vertex AI response to Anthropic format"""
        try:
            # Extract text from Vertex AI response
            candidates = response.get('candidates', [])
            if not candidates:
                raise ValueError("No candidates in Vertex AI response")
            
            candidate = candidates[0]
            content = candidate.get('content', {})
            parts = content.get('parts', [])
            
            if not parts:
                raise ValueError("No parts in Vertex AI response")
            
            text = parts[0].get('text', '')
            
            # Get usage information
            usage_metadata = response.get('usageMetadata', {})
            input_tokens = usage_metadata.get('promptTokenCount', 0)
            output_tokens = usage_metadata.get('candidatesTokenCount', 0)
            
            # Convert to Anthropic format
            anthropic_response = {
                "id": f"msg_vertex_{int(datetime.now().timestamp())}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ],
                "model": model,
                "stop_reason": self.map_finish_reason(candidate.get('finishReason')),
                "stop_sequence": None,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                }
            }
            
            return anthropic_response
            
        except Exception as e:
            logger.error(f"Error converting Vertex AI response: {e}")
            raise ValueError(f"Failed to convert Vertex AI response: {e}")

    def map_finish_reason(self, vertex_reason: str) -> str:
        """Map Vertex AI finish reason to Anthropic format"""
        mapping = {
            'STOP': 'end_turn',
            'MAX_TOKENS': 'max_tokens',
            'SAFETY': 'stop_sequence',
            'RECITATION': 'stop_sequence',
            'OTHER': 'end_turn',
            None: 'end_turn'
        }
        return mapping.get(vertex_reason, 'end_turn')

    def log_usage(self, anthropic_model: str, vertex_model: str, body: Dict[str, Any]):
        """Log usage for cost tracking"""
        try:
            usage_entry = {
                "timestamp": datetime.now().isoformat(),
                "anthropic_model": anthropic_model,
                "vertex_model": vertex_model,
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
    proxy = VertexAIProxy()
    
    host = os.getenv('VERTEX_PROXY_HOST', '0.0.0.0')
    port = int(os.getenv('VERTEX_PROXY_PORT', '8081'))
    
    logger.info(f"Starting Vertex AI Proxy on {host}:{port}")
    
    uvicorn.run(
        proxy.app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()