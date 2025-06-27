#!/usr/bin/env python3
"""
Intelligent Master Proxy for Claude Code Multi-Model Integration
Orchestrates all providers with advanced routing, rate limiting, and fallback
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta, timezone
import time
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from pydantic import BaseModel
import structlog

# Import our components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rate_limiting_router import RateLimitingRouter, RoutingDecision, ProviderStatus

# Setup structured logging
logger = structlog.get_logger(__name__)

# Security
security = HTTPBearer(auto_error=False)

class RequestModel(BaseModel):
    """Pydantic model for request validation"""
    model: str
    messages: List[Dict[str, Any]]
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    system: Optional[str] = None

class IntelligentProxy:
    """
    Master proxy that intelligently routes requests across all providers
    with rate limiting detection, auto-fallback, and cost optimization
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="Claude Code Intelligent Multi-Model Proxy",
            description="Intelligent proxy with rate limiting detection and auto-routing",
            version="1.0.0"
        )
        
        # Initialize components
        self.router = RateLimitingRouter()
        
        # Configuration
        self.load_configuration()
        
        # Setup middleware and routes
        self.setup_cors()
        self.setup_routes()
        
        # Request tracking
        self.active_requests = {}
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'fallback_requests': 0,
            'rate_limited_requests': 0
        }
        
        # Provider endpoints
        self.provider_endpoints = {
            'vertex': os.getenv('VERTEX_PROXY_URL', 'http://localhost:8081'),
            'github': os.getenv('GITHUB_PROXY_URL', 'http://localhost:8082'),
            'openrouter': os.getenv('OPENROUTER_PROXY_URL', 'http://localhost:8084')
        }
        
        # Cost tracking integration
        self.cost_tracker = None
        if os.getenv('ENABLE_COST_TRACKING', 'true').lower() == 'true':
            try:
                sys.path.append('/home/sam/claude-code-multimodel/monitoring')
                from cost_tracker import CostTracker, UsageMetrics
                self.cost_tracker = CostTracker()
                logger.info("Cost tracking enabled")
            except ImportError:
                logger.warning("Cost tracker not available")
        
        logger.info("Intelligent proxy initialized", 
                   providers=list(self.provider_endpoints.keys()))

    def load_configuration(self):
        """Load configuration from environment"""
        self.enable_authentication = os.getenv('ENABLE_AUTHENTICATION', 'false').lower() == 'true'
        self.api_key = os.getenv('MASTER_PROXY_API_KEY', 'proxy-key-12345')
        self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', '100'))
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '300'))  # 5 minutes
        self.fallback_delay = float(os.getenv('FALLBACK_DELAY', '1.0'))
        
        # Default routing preferences
        self.default_routing_strategy = os.getenv('DEFAULT_ROUTING_STRATEGY', 'intelligent')
        
        # Health check configuration
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))  # seconds
        
        logger.info("Configuration loaded", 
                   auth_enabled=self.enable_authentication,
                   max_concurrent=self.max_concurrent_requests,
                   routing_strategy=self.default_routing_strategy)

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
                "message": "Claude Code Intelligent Multi-Model Proxy",
                "version": "1.0.0",
                "status": "running",
                "providers": list(self.provider_endpoints.keys()),
                "routing_strategy": self.default_routing_strategy,
                "features": [
                    "intelligent_routing",
                    "rate_limit_detection",
                    "auto_fallback",
                    "cost_optimization",
                    "real_time_monitoring"
                ]
            }

        @self.app.get("/health")
        async def health_check():
            provider_health = {}
            for provider in self.provider_endpoints.keys():
                health = self.router.provider_health.get(provider)
                if health:
                    provider_health[provider] = {
                        "status": health.status.value,
                        "avg_response_time": health.avg_response_time,
                        "success_rate": health.success_count / (health.success_count + health.error_count) if (health.success_count + health.error_count) > 0 else 0,
                        "last_success": health.last_success.isoformat() if health.last_success else None
                    }
            
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_requests": len(self.active_requests),
                "provider_health": provider_health,
                "stats": self.request_stats
            }

        @self.app.post("/v1/messages")
        async def create_message(
            request: Request,
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
        ):
            """Main endpoint for Anthropic API compatibility"""
            
            # Authentication check
            if self.enable_authentication:
                if not credentials or credentials.credentials != self.api_key:
                    raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Rate limiting check
            if len(self.active_requests) >= self.max_concurrent_requests:
                raise HTTPException(status_code=429, detail="Too many concurrent requests")
            
            try:
                body = await request.json()
                request_id = str(uuid.uuid4())
                
                # Track request
                self.active_requests[request_id] = {
                    "start_time": datetime.now(timezone.utc),
                    "provider": None,
                    "model": body.get('model', 'unknown')
                }
                
                self.request_stats['total_requests'] += 1
                
                # Route and process request
                response = await self.process_request(request_id, body, dict(request.headers))
                
                self.request_stats['successful_requests'] += 1
                return response
                
            except HTTPException:
                self.request_stats['failed_requests'] += 1
                raise
            except Exception as e:
                self.request_stats['failed_requests'] += 1
                logger.error("Unexpected error in message endpoint", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                # Clean up request tracking
                if request_id in self.active_requests:
                    del self.active_requests[request_id]

        @self.app.get("/v1/models")
        async def list_models():
            """List available models across all providers"""
            models = []
            
            # Get models from each provider
            for provider, endpoint in self.provider_endpoints.items():
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{endpoint}/v1/models")
                        if response.status_code == 200:
                            provider_models = response.json().get('data', [])
                            for model in provider_models:
                                model['provider'] = provider
                                models.append(model)
                except Exception as e:
                    logger.warning(f"Failed to get models from {provider}", error=str(e))
            
            return {"object": "list", "data": models}

        @self.app.get("/stats")
        async def get_detailed_stats():
            """Get detailed statistics"""
            return {
                "request_stats": self.request_stats,
                "active_requests": len(self.active_requests),
                "router_stats": await self.router.get_stats() if hasattr(self.router, 'get_stats') else {},
                "provider_endpoints": self.provider_endpoints
            }

        @self.app.post("/admin/routing-strategy")
        async def update_routing_strategy(
            strategy_update: Dict[str, str],
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
        ):
            """Update routing strategy (admin endpoint)"""
            if self.enable_authentication:
                if not credentials or credentials.credentials != self.api_key:
                    raise HTTPException(status_code=401, detail="Invalid API key")
            
            strategy = strategy_update.get('strategy')
            if strategy in ['intelligent', 'cost', 'performance', 'availability']:
                self.router.routing_strategy = strategy
                return {"message": f"Routing strategy updated to {strategy}"}
            else:
                raise HTTPException(status_code=400, detail="Invalid routing strategy")

        @self.app.get("/admin/provider/{provider}/health")
        async def get_provider_health(
            provider: str,
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
        ):
            """Get detailed health information for a specific provider"""
            if self.enable_authentication:
                if not credentials or credentials.credentials != self.api_key:
                    raise HTTPException(status_code=401, detail="Invalid API key")
            
            if provider not in self.router.provider_health:
                raise HTTPException(status_code=404, detail="Provider not found")
            
            health = self.router.provider_health[provider]
            return {
                "provider": provider,
                "status": health.status.value,
                "metrics": {
                    "success_count": health.success_count,
                    "error_count": health.error_count,
                    "avg_response_time": health.avg_response_time,
                    "last_success": health.last_success.isoformat() if health.last_success else None,
                    "last_error": health.last_error.isoformat() if health.last_error else None
                },
                "rate_limit_info": health.rate_limit_info.__dict__ if health.rate_limit_info else None
            }

    async def process_request(self, request_id: str, body: Dict[str, Any], 
                            headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Main request processing logic with intelligent routing and fallback
        """
        start_time = time.time()
        anthropic_model = body.get('model', 'claude-3-5-sonnet-20241022')
        
        logger.info("Processing request", 
                   request_id=request_id, 
                   model=anthropic_model)
        
        # Get routing decision
        routing_decision = await self.router.route_request(anthropic_model, body)
        
        # Update active request tracking
        self.active_requests[request_id]['provider'] = routing_decision.selected_provider
        
        # Try primary choice
        response = await self.try_provider_request(
            routing_decision.selected_provider,
            routing_decision.selected_model,
            body,
            headers,
            request_id
        )
        
        if response is not None:
            # Log successful request
            response_time = time.time() - start_time
            await self.log_request_result(
                routing_decision.selected_provider,
                routing_decision.selected_model,
                True,
                response_time,
                self.estimate_tokens(body.get('messages', [])),
                response.get('usage', {})
            )
            return response
        
        # Primary failed, try fallbacks
        if routing_decision.fallback_options:
            logger.info("Primary provider failed, trying fallbacks", 
                       request_id=request_id,
                       fallback_count=len(routing_decision.fallback_options))
            
            self.request_stats['fallback_requests'] += 1
            
            for provider, model in routing_decision.fallback_options:
                # Add fallback delay
                if self.fallback_delay > 0:
                    await asyncio.sleep(self.fallback_delay)
                
                logger.info("Trying fallback provider", 
                           request_id=request_id,
                           provider=provider,
                           model=model)
                
                response = await self.try_provider_request(provider, model, body, headers, request_id)
                
                if response is not None:
                    # Log successful fallback
                    response_time = time.time() - start_time
                    await self.log_request_result(
                        provider,
                        model,
                        True,
                        response_time,
                        self.estimate_tokens(body.get('messages', [])),
                        response.get('usage', {})
                    )
                    
                    logger.info("Fallback succeeded", 
                               request_id=request_id,
                               provider=provider)
                    return response
        
        # All providers failed
        logger.error("All providers failed", request_id=request_id)
        raise HTTPException(status_code=503, detail="All providers unavailable")

    async def try_provider_request(self, provider: str, model: str, body: Dict[str, Any], 
                                 headers: Dict[str, str], request_id: str) -> Optional[Dict[str, Any]]:
        """
        Try to make a request to a specific provider
        """
        if provider not in self.provider_endpoints:
            logger.error("Unknown provider", provider=provider, request_id=request_id)
            return None
        
        endpoint = self.provider_endpoints[provider]
        
        try:
            # Prepare request
            request_body = body.copy()
            request_body['model'] = model
            
            request_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Claude-Code-Intelligent-Proxy/1.0'
            }
            
            # Forward authentication if present
            if 'authorization' in headers:
                request_headers['Authorization'] = headers['authorization']
            
            # Add request ID for tracing
            request_headers['X-Request-ID'] = request_id
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.request_timeout)) as client:
                response = await client.post(
                    f"{endpoint}/v1/messages",
                    json=request_body,
                    headers=request_headers
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    await self.router.detect_rate_limit_from_response(
                        provider, 
                        response.status_code, 
                        dict(response.headers),
                        response.text
                    )
                    self.request_stats['rate_limited_requests'] += 1
                    logger.warning("Rate limit detected", 
                                 provider=provider, 
                                 request_id=request_id)
                    return None
                
                # Check for other errors
                if response.status_code >= 400:
                    await self.router.detect_rate_limit_from_response(
                        provider, 
                        response.status_code, 
                        dict(response.headers),
                        response.text
                    )
                    
                    logger.warning("Provider request failed", 
                                 provider=provider,
                                 status_code=response.status_code,
                                 request_id=request_id)
                    return None
                
                # Success
                result = response.json()
                logger.info("Provider request succeeded", 
                           provider=provider,
                           request_id=request_id)
                return result
                
        except asyncio.TimeoutError:
            logger.warning("Provider request timeout", 
                         provider=provider,
                         request_id=request_id)
            return None
        except Exception as e:
            logger.error("Provider request error", 
                        provider=provider,
                        error=str(e),
                        request_id=request_id)
            return None

    async def log_request_result(self, provider: str, model: str, success: bool, 
                               response_time: float, estimated_tokens: int, 
                               usage_info: Dict[str, Any]):
        """Log request result for monitoring and cost tracking"""
        
        # Update router stats
        await self.router.record_request(
            provider=provider,
            model=model,
            success=success,
            response_time=response_time,
            tokens_used=estimated_tokens
        )
        
        # Log to cost tracker if available
        if self.cost_tracker:
            try:
                from cost_tracker import UsageMetrics
                
                input_tokens = usage_info.get('input_tokens', estimated_tokens // 2)
                output_tokens = usage_info.get('output_tokens', estimated_tokens // 2)
                
                cost = self.cost_tracker.calculate_cost(provider, model, input_tokens, output_tokens)
                
                metrics = UsageMetrics(
                    timestamp=datetime.now(timezone.utc),
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost=cost,
                    response_time=response_time,
                    success=success
                )
                
                self.cost_tracker.log_usage(metrics)
            except Exception as e:
                logger.warning("Failed to log cost metrics", error=str(e))

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate token count from messages"""
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
        return max(100, total_chars // 4)

    def start_health_monitoring(self):
        """Start background health monitoring"""
        async def health_monitor():
            while True:
                try:
                    await self.router.update_provider_health()
                    await asyncio.sleep(self.health_check_interval)
                except Exception as e:
                    logger.error("Health monitoring error", error=str(e))
                    await asyncio.sleep(self.health_check_interval)
        
        asyncio.create_task(health_monitor())

def create_app() -> FastAPI:
    """Create and configure the FastAPI app"""
    proxy = IntelligentProxy()
    proxy.start_health_monitoring()
    return proxy.app

def main():
    """Main function to start the server"""
    app = create_app()
    
    host = os.getenv('PROXY_HOST', '0.0.0.0')
    port = int(os.getenv('PROXY_PORT', '8080'))
    
    logger.info(f"Starting Intelligent Proxy on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()