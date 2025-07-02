#!/usr/bin/env python3
"""
Base Multi-Port Service
FastAPI + LiteLLM Library Integration

Based on patterns from /home/sam/claude-code-proxy/server.py
Provides reusable base class for provider-specific services.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import logging
import json
import os
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field, field_validator
import litellm
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Import Secret Manager for secure credential management
try:
    from utils.secret_manager import SecretManagerClient
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class BaseMultiPortService:
    """
    Base class for multi-port Claude Code services
    
    Provides common functionality for FastAPI + LiteLLM integration
    following patterns from claude-code-proxy/server.py
    """
    
    def __init__(self, port: int, provider_config: Dict[str, Any]):
        self.port = port
        self.provider_config = provider_config
        self.service_name = provider_config.get("service_name", f"service-{port}")
        self.provider = provider_config.get("provider", "unknown")
        
        # Setup logging
        self.logger = logging.getLogger(f"{self.service_name}")
        
        # Create FastAPI app
        self.app = FastAPI(
            title=f"Claude Code Multi-Port Service - {self.service_name}",
            description=f"Provider: {self.provider} | Port: {port}",
            version="1.0.0"
        )
        
        # Configure LiteLLM
        self.configure_litellm()
        
        # Setup routes
        self.setup_routes()
        
        self.logger.info(f"✅ {self.service_name} initialized on port {port}")
    
    def configure_litellm(self):
        """Configure LiteLLM for this specific provider"""
        litellm.drop_params = True
        litellm.set_verbose = False
        
        # Provider-specific configurations will be overridden in subclasses
        self.logger.info(f"🔧 LiteLLM configured for {self.provider}")
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/v1/messages")
        async def messages_endpoint(request: Request):
            """Main Claude API endpoint"""
            return await self.handle_messages(request)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return await self.get_health_status()
        
        @self.app.get("/v1/models") 
        async def list_models():
            """List available models for this provider"""
            return await self.get_available_models()
        
        @self.app.get("/info")
        async def service_info():
            """Service information"""
            return {
                "service_name": self.service_name,
                "provider": self.provider,
                "port": self.port,
                "status": "running"
            }
    
    async def handle_messages(self, request: Request) -> Union[JSONResponse, StreamingResponse]:
        """
        Handle Claude API messages endpoint
        
        This method should be overridden by provider-specific services
        to implement custom model mapping and provider logic.
        """
        try:
            # Parse request
            request_data = await request.json()
            
            # Log request
            self.logger.info(f"📨 Request received: {request_data.get('model', 'unknown model')}")
            
            # Map model (to be implemented by subclasses)
            mapped_model = await self.map_model(request_data.get("model", ""))
            
            # Prepare LiteLLM parameters
            litellm_params = await self.prepare_litellm_params(request_data, mapped_model)
            
            # Make LiteLLM call
            if request_data.get("stream", False):
                return await self.handle_streaming_request(litellm_params)
            else:
                return await self.handle_non_streaming_request(litellm_params)
                
        except Exception as e:
            self.logger.error(f"❌ Error handling request: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def map_model(self, model: str) -> str:
        """
        Map Claude model name to provider-specific model
        
        Should be overridden by provider-specific services
        """
        # Default implementation - return model as-is
        self.logger.debug(f"🔄 Model mapping: {model} -> {model} (default)")
        return model
    
    async def prepare_litellm_params(self, request_data: dict, mapped_model: str) -> dict:
        """Prepare parameters for LiteLLM call"""
        params = {
            "model": mapped_model,
            "messages": request_data.get("messages", []),
            "max_tokens": min(request_data.get("max_tokens", 4096), 8192),  # Limit max tokens
            "temperature": request_data.get("temperature", 0.7),
            "stream": request_data.get("stream", False)
        }
        
        # Add optional parameters if present
        for optional_param in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
            if optional_param in request_data:
                params[optional_param] = request_data[optional_param]
        
        return params
    
    async def handle_streaming_request(self, params: dict) -> StreamingResponse:
        """Handle streaming LiteLLM request"""
        async def generate():
            try:
                response = await litellm.acompletion(**params)
                async for chunk in response:
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                self.logger.error(f"❌ Streaming error: {str(e)}")
                error_chunk = {
                    "error": {
                        "message": str(e),
                        "type": "api_error"
                    }
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    async def handle_non_streaming_request(self, params: dict) -> JSONResponse:
        """Handle non-streaming LiteLLM request"""
        try:
            response = await litellm.acompletion(**params)
            
            # Log success
            self.logger.info(f"✅ Response generated successfully")
            
            # Convert ModelResponse to dict for JSON serialization
            response_dict = response.model_dump() if hasattr(response, 'model_dump') else dict(response)
            
            return JSONResponse(content=response_dict)
            
        except Exception as e:
            self.logger.error(f"❌ LiteLLM error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Provider error: {str(e)}"
            )
    
    async def get_health_status(self) -> dict:
        """Get service health status"""
        try:
            # Test provider connectivity (to be implemented by subclasses)
            provider_status = await self.check_provider_health()
            
            return {
                "status": "healthy" if provider_status else "unhealthy",
                "service_name": self.service_name,
                "provider": self.provider,
                "port": self.port,
                "provider_status": provider_status,
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "service_name": self.service_name,
                "provider": self.provider,
                "port": self.port,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def check_provider_health(self) -> bool:
        """
        Check provider-specific health
        
        Should be overridden by provider-specific services
        """
        # Default implementation - always healthy
        return True
    
    async def get_available_models(self) -> dict:
        """
        Get list of available models for this provider
        
        Should be overridden by provider-specific services
        """
        return {
            "object": "list",
            "data": [
                {
                    "id": "claude-3-5-sonnet-20241022",
                    "object": "model", 
                    "created": int(time.time()),
                    "owned_by": self.provider
                }
            ]
        }
    
    def run(self, host: str = "0.0.0.0", reload: bool = False):
        """Run the FastAPI service"""
        self.logger.info(f"🚀 Starting {self.service_name} on {host}:{self.port}")
        uvicorn.run(
            self.app,
            host=host,
            port=self.port,
            reload=reload,
            log_level="info",
            access_log=True
        )

# Pydantic models for request/response validation
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = Field(default=4096, le=8192)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)

if __name__ == "__main__":
    # Example usage
    config = {
        "service_name": "base-service",
        "provider": "test",
        "port": 8080
    }
    
    service = BaseMultiPortService(8080, config)
    service.run()