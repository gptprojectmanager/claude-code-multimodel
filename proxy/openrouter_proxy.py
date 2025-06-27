#!/usr/bin/env python3
"""
OpenRouter Proxy for Claude Code
Based on CogAgent/claude-code-proxy with enhanced routing and fallback
"""

import os
import sys
import json
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import random

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

@dataclass
class ModelInfo:
    """Information about a model"""
    id: str
    provider: str
    cost_per_token: float
    context_length: int
    is_available: bool = True
    last_error: Optional[str] = None
    error_count: int = 0

@dataclass
class ProviderStats:
    """Statistics for a provider"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_cost: float = 0.0
    avg_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    rate_limit_reset: Optional[datetime] = None

class OpenRouterProxy:
    """
    Advanced OpenRouter proxy with intelligent routing, fallback, and cost optimization
    """
    
    def __init__(self):
        self.app = FastAPI(title="OpenRouter Proxy for Claude Code")
        self.setup_cors()
        self.setup_routes()
        
        # Configuration
        self.api_key = os.getenv('OPENROUTER_API_KEY', '')
        self.api_base = os.getenv('OPENROUTER_API_BASE', 'https://openrouter.ai/api/v1')
        self.site_url = os.getenv('OPENROUTER_SITE_URL', 'https://claude-code-multimodel.local')
        self.app_name = os.getenv('OPENROUTER_APP_NAME', 'Claude Code Multi-Model')
        
        # Model configuration
        self.primary_model = os.getenv('OPENROUTER_PRIMARY_MODEL', 'anthropic/claude-3.5-sonnet')
        self.secondary_model = os.getenv('OPENROUTER_SECONDARY_MODEL', 'anthropic/claude-3-haiku')
        
        # Parse fallback models
        fallback_str = os.getenv('OPENROUTER_FALLBACK_MODELS', 'google/gemini-2.0-flash,openai/gpt-4o')
        self.fallback_models = [m.strip() for m in fallback_str.split(',')]
        
        # Cost and performance settings
        self.enable_cost_optimization = os.getenv('ENABLE_COST_OPTIMIZATION', 'true').lower() == 'true'
        self.max_cost_per_request = float(os.getenv('MAX_COST_PER_REQUEST', '1.0'))
        self.prefer_cheaper_models = os.getenv('PREFER_CHEAPER_MODELS', 'false').lower() == 'true'
        
        # Rate limiting
        self.max_requests_per_minute = int(os.getenv('OPENROUTER_MAX_REQUESTS_PER_MINUTE', '60'))
        self.max_tokens_per_minute = int(os.getenv('OPENROUTER_MAX_TOKENS_PER_MINUTE', '100000'))
        
        # Fallback configuration
        self.enable_auto_fallback = os.getenv('ENABLE_AUTO_FALLBACK', 'true').lower() == 'true'
        self.fallback_on_rate_limit = os.getenv('FALLBACK_ON_RATE_LIMIT', 'true').lower() == 'true'
        self.fallback_timeout = int(os.getenv('FALLBACK_TIMEOUT', '30'))
        
        # Provider selection strategy
        self.selection_strategy = os.getenv('PROVIDER_SELECTION_STRATEGY', 'performance')
        
        # Initialize tracking
        self.provider_stats: Dict[str, ProviderStats] = {}
        self.model_info: Dict[str, ModelInfo] = {}
        self.request_history: List[Dict] = []
        
        # Cost tracking
        self.enable_cost_tracking = os.getenv('ENABLE_OPENROUTER_COST_TRACKING', 'true').lower() == 'true'
        self.cost_log_file = os.getenv('OPENROUTER_COST_LOG_FILE', '/tmp/openrouter-usage.log')
        
        # Initialize model information
        self.initialize_models()
        
        logger.info(f"OpenRouter Proxy initialized")
        logger.info(f"Primary model: {self.primary_model}")
        logger.info(f"Fallback models: {self.fallback_models}")

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
            return {
                "message": "OpenRouter Proxy for Claude Code",
                "status": "running",
                "primary_model": self.primary_model,
                "fallback_models": self.fallback_models
            }

        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "provider_stats": {k: v.__dict__ for k, v in self.provider_stats.items()}
            }

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
            for model_id, model_info in self.model_info.items():
                models.append({
                    "id": model_id,
                    "object": "model",
                    "created": int(datetime.now().timestamp()),
                    "owned_by": model_info.provider,
                    "cost_per_token": model_info.cost_per_token,
                    "context_length": model_info.context_length,
                    "is_available": model_info.is_available
                })
            return {"object": "list", "data": models}

        @self.app.get("/stats")
        async def get_stats():
            """Get detailed statistics"""
            return {
                "provider_stats": {k: v.__dict__ for k, v in self.provider_stats.items()},
                "model_info": {k: v.__dict__ for k, v in self.model_info.items()},
                "recent_requests": self.request_history[-10:],  # Last 10 requests
                "total_requests": len(self.request_history)
            }

    def initialize_models(self):
        """Initialize model information"""
        # Common model configurations
        models = {
            # Anthropic models
            'anthropic/claude-3.5-sonnet': ModelInfo('anthropic/claude-3.5-sonnet', 'anthropic', 0.000003, 200000),
            'anthropic/claude-3-haiku': ModelInfo('anthropic/claude-3-haiku', 'anthropic', 0.00000025, 200000),
            'anthropic/claude-3-opus': ModelInfo('anthropic/claude-3-opus', 'anthropic', 0.000015, 200000),
            
            # OpenAI models
            'openai/gpt-4o': ModelInfo('openai/gpt-4o', 'openai', 0.0000025, 128000),
            'openai/gpt-4o-mini': ModelInfo('openai/gpt-4o-mini', 'openai', 0.00000015, 128000),
            'openai/o1-preview': ModelInfo('openai/o1-preview', 'openai', 0.000015, 128000),
            
            # Google models
            'google/gemini-2.0-flash': ModelInfo('google/gemini-2.0-flash', 'google', 0.00000075, 1000000),
            'google/gemini-1.5-pro': ModelInfo('google/gemini-1.5-pro', 'google', 0.00000125, 2000000),
            'google/gemini-1.5-flash': ModelInfo('google/gemini-1.5-flash', 'google', 0.00000037, 1000000),
            
            # Meta models
            'meta-llama/llama-3.2-90b-vision': ModelInfo('meta-llama/llama-3.2-90b-vision', 'meta', 0.0000009, 128000),
            'meta-llama/llama-3.1-405b': ModelInfo('meta-llama/llama-3.1-405b', 'meta', 0.000002, 128000),
        }
        
        self.model_info.update(models)
        
        # Initialize provider stats
        providers = set(model.provider for model in models.values())
        for provider in providers:
            self.provider_stats[provider] = ProviderStats()

    async def handle_anthropic_request(self, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle Anthropic API request with intelligent routing and fallback
        """
        start_time = time.time()
        
        # Extract requested model
        anthropic_model = body.get('model', 'claude-3-5-sonnet-20241022')
        
        # Select best model based on request and strategy
        selected_model = await self.select_optimal_model(anthropic_model, body)
        
        logger.info(f"Request: {anthropic_model} -> {selected_model}")
        
        # Try primary model, then fallback if needed
        models_to_try = [selected_model] + self.fallback_models
        last_error = None
        
        for model in models_to_try:
            try:
                response = await self.make_openrouter_request(body, model, headers)
                
                # Log successful request
                self.log_request(model, body, True, time.time() - start_time)
                
                return response
                
            except HTTPException as e:
                last_error = e
                
                # Check if we should try fallback
                if not self.should_try_fallback(e.status_code, model):
                    break
                    
                logger.warning(f"Model {model} failed (HTTP {e.status_code}), trying fallback...")
                self.update_model_error(model, str(e.detail))
                
                # Wait before retry
                await asyncio.sleep(min(2, self.fallback_timeout / len(models_to_try)))
                
            except Exception as e:
                last_error = HTTPException(status_code=500, detail=str(e))
                logger.error(f"Unexpected error with model {model}: {e}")
                
                if not self.enable_auto_fallback:
                    break
        
        # All models failed
        self.log_request(selected_model, body, False, time.time() - start_time, str(last_error))
        
        if last_error:
            raise last_error
        else:
            raise HTTPException(status_code=500, detail="All models failed")

    async def select_optimal_model(self, requested_model: str, body: Dict[str, Any]) -> str:
        """
        Select the optimal model based on request characteristics and strategy
        """
        # Map common Claude model names to OpenRouter equivalents
        model_mapping = {
            'claude-3-haiku-20240307': 'anthropic/claude-3-haiku',
            'claude-3-5-haiku-20241022': 'anthropic/claude-3-haiku',
            'claude-3-sonnet-20240229': 'anthropic/claude-3.5-sonnet',
            'claude-3-5-sonnet-20241022': 'anthropic/claude-3.5-sonnet',
            'claude-sonnet-4-20250514': 'anthropic/claude-3.5-sonnet',
        }
        
        # Get mapped model or use primary/secondary
        if requested_model in model_mapping:
            base_model = model_mapping[requested_model]
        elif 'haiku' in requested_model.lower():
            base_model = self.secondary_model
        else:
            base_model = self.primary_model
        
        # Apply selection strategy
        if self.selection_strategy == 'cost' and self.prefer_cheaper_models:
            return self.select_cheapest_model(base_model)
        elif self.selection_strategy == 'performance':
            return self.select_best_performance_model(base_model)
        elif self.selection_strategy == 'availability':
            return self.select_most_available_model(base_model)
        else:
            return base_model

    def select_cheapest_model(self, base_model: str) -> str:
        """Select the cheapest available model"""
        available_models = [
            (model_id, info) for model_id, info in self.model_info.items()
            if info.is_available and info.provider in ['anthropic', 'google', 'openai']
        ]
        
        if not available_models:
            return base_model
            
        # Sort by cost
        available_models.sort(key=lambda x: x[1].cost_per_token)
        return available_models[0][0]

    def select_best_performance_model(self, base_model: str) -> str:
        """Select model with best performance metrics"""
        provider = self.model_info.get(base_model, {}).provider if base_model in self.model_info else 'anthropic'
        
        # Get stats for this provider
        stats = self.provider_stats.get(provider, ProviderStats())
        
        # If provider has good stats, use it
        if stats.total_requests > 0 and stats.successful_requests / stats.total_requests > 0.9:
            return base_model
            
        # Otherwise, find best performing provider
        best_provider = 'anthropic'
        best_success_rate = 0
        
        for prov, prov_stats in self.provider_stats.items():
            if prov_stats.total_requests > 5:  # Minimum requests for reliable stats
                success_rate = prov_stats.successful_requests / prov_stats.total_requests
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_provider = prov
        
        # Find a model from the best provider
        for model_id, info in self.model_info.items():
            if info.provider == best_provider and info.is_available:
                return model_id
                
        return base_model

    def select_most_available_model(self, base_model: str) -> str:
        """Select most available model"""
        # Check if base model is available
        if base_model in self.model_info and self.model_info[base_model].is_available:
            return base_model
            
        # Find any available model
        for model_id, info in self.model_info.items():
            if info.is_available and info.error_count < 3:
                return model_id
                
        return base_model

    def should_try_fallback(self, status_code: int, current_model: str) -> bool:
        """Determine if we should try fallback based on error type"""
        if not self.enable_auto_fallback:
            return False
            
        # Always fallback on rate limits
        if status_code == 429 and self.fallback_on_rate_limit:
            return True
            
        # Fallback on server errors
        if status_code >= 500:
            return True
            
        # Fallback on authentication issues (might be model-specific)
        if status_code == 401 or status_code == 403:
            return True
            
        return False

    async def make_openrouter_request(self, body: Dict[str, Any], model: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Make request to OpenRouter API
        """
        # Convert Anthropic format to OpenAI format
        openai_body = self.convert_anthropic_to_openai(body, model)
        
        # Prepare headers
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }
        
        # Add OpenRouter-specific headers
        if model in self.model_info:
            request_headers["X-Model"] = model
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.fallback_timeout)) as client:
            try:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    json=openai_body,
                    headers=request_headers
                )
                
                response.raise_for_status()
                openai_response = response.json()
                
                # Convert back to Anthropic format
                anthropic_response = self.convert_openai_to_anthropic(openai_response, model)
                
                # Log cost if enabled
                if self.enable_cost_tracking:
                    self.log_cost(model, openai_response.get('usage', {}))
                
                return anthropic_response
                
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
                
                # Update provider stats
                provider = self.model_info.get(model, ModelInfo(model, 'unknown', 0, 0)).provider
                if provider in self.provider_stats:
                    self.provider_stats[provider].failed_requests += 1
                
                # Handle rate limiting
                if e.response.status_code == 429:
                    self.handle_rate_limit(model, e.response.headers)
                
                raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

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
                        text_parts.append("[Image content]")
                
                messages.append({"role": role, "content": " ".join(text_parts)})
        
        openai_body = {
            "model": model,
            "messages": messages,
            "temperature": body.get('temperature', 0.7),
            "max_tokens": body.get('max_tokens', 1024),
            "stream": body.get('stream', False),
        }
        
        # Add additional parameters
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
            "id": response.get('id', 'msg_openrouter'),
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

    def handle_rate_limit(self, model: str, headers: Dict[str, str]):
        """Handle rate limiting response"""
        # Extract rate limit reset time if available
        reset_time = headers.get('x-ratelimit-reset')
        if reset_time:
            try:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                provider = self.model_info.get(model, ModelInfo(model, 'unknown', 0, 0)).provider
                if provider in self.provider_stats:
                    self.provider_stats[provider].rate_limit_reset = reset_datetime
            except (ValueError, TypeError):
                pass

    def update_model_error(self, model: str, error: str):
        """Update model error information"""
        if model in self.model_info:
            self.model_info[model].error_count += 1
            self.model_info[model].last_error = error
            
            # Disable model if too many errors
            if self.model_info[model].error_count >= 5:
                self.model_info[model].is_available = False
                logger.warning(f"Model {model} disabled due to repeated errors")

    def log_request(self, model: str, body: Dict[str, Any], success: bool, response_time: float, error: str = None):
        """Log request for monitoring"""
        request_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "success": success,
            "response_time": response_time,
            "estimated_tokens": self.estimate_tokens(body.get('messages', [])),
            "error": error
        }
        
        self.request_history.append(request_entry)
        
        # Keep only last 1000 requests
        if len(self.request_history) > 1000:
            self.request_history = self.request_history[-1000:]
        
        # Update provider stats
        provider = self.model_info.get(model, ModelInfo(model, 'unknown', 0, 0)).provider
        if provider in self.provider_stats:
            stats = self.provider_stats[provider]
            stats.total_requests += 1
            if success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
            
            # Update average response time
            if stats.avg_response_time == 0:
                stats.avg_response_time = response_time
            else:
                stats.avg_response_time = (stats.avg_response_time + response_time) / 2
            
            stats.last_request_time = datetime.now()

    def log_cost(self, model: str, usage: Dict[str, Any]):
        """Log cost information"""
        try:
            if model in self.model_info:
                model_info = self.model_info[model]
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                
                # Calculate cost (simplified - real costs may vary)
                cost = (input_tokens + output_tokens) * model_info.cost_per_token
                
                # Update provider stats
                if model_info.provider in self.provider_stats:
                    self.provider_stats[model_info.provider].total_cost += cost
                
                # Log to file
                cost_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "estimated_cost": cost,
                    "provider": model_info.provider
                }
                
                with open(self.cost_log_file, 'a') as f:
                    f.write(json.dumps(cost_entry) + '\n')
                    
        except Exception as e:
            logger.warning(f"Failed to log cost: {e}")

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
    proxy = OpenRouterProxy()
    
    host = os.getenv('OPENROUTER_HOST', '0.0.0.0')
    port = int(os.getenv('OPENROUTER_PORT', '8084'))
    
    logger.info(f"Starting OpenRouter Proxy on {host}:{port}")
    
    uvicorn.run(
        proxy.app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()