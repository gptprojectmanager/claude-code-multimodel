#!/usr/bin/env python3
"""
Intelligent Rate Limiting Detection and Auto-Routing System
for Claude Code Multi-Model Integration
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import time
import random

import httpx
import structlog
from prometheus_client import Counter, Histogram, Gauge

# Setup structured logging
logger = structlog.get_logger(__name__)

class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    OVERLOADED = "overloaded"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class RateLimitInfo:
    """Rate limit information for a provider"""
    requests_per_minute: int
    requests_remaining: int
    reset_time: datetime
    retry_after: int = 0
    daily_limit: Optional[int] = None
    daily_remaining: Optional[int] = None

@dataclass
class ProviderHealth:
    """Health metrics for a provider"""
    status: ProviderStatus
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    rate_limit_info: Optional[RateLimitInfo] = None
    cost_per_token: float = 0.0
    priority_score: float = 1.0

@dataclass
class RoutingDecision:
    """Routing decision with reasoning"""
    selected_provider: str
    selected_model: str
    reasoning: str
    fallback_options: List[Tuple[str, str]]  # [(provider, model), ...]
    estimated_cost: float
    estimated_delay: float = 0.0

class RateLimitingRouter:
    """
    Intelligent router that detects rate limits and automatically
    switches to alternative providers
    """
    
    def __init__(self):
        # Provider configurations
        self.providers = {
            'vertex': {
                'primary_model': 'claude-sonnet-4@20250514',
                'secondary_model': 'claude-3-5-haiku@20241022',
                'base_url': 'https://us-east5-aiplatform.googleapis.com/v1',
                'max_requests_per_minute': 1000,
                'max_tokens_per_minute': 50000,
                'cost_multiplier': 1.0,
                'priority': 10
            },
            'github': {
                'primary_model': 'claude-3-5-sonnet',
                'secondary_model': 'claude-3-5-haiku',
                'base_url': 'http://localhost:8082',
                'max_requests_per_minute': 500,
                'max_tokens_per_minute': 100000,
                'cost_multiplier': 0.8,
                'priority': 8
            },
            'openrouter': {
                'primary_model': 'anthropic/claude-3.5-sonnet',
                'secondary_model': 'anthropic/claude-3-haiku',
                'base_url': 'http://localhost:8084',
                'max_requests_per_minute': 200,
                'max_tokens_per_minute': 80000,
                'cost_multiplier': 1.2,
                'priority': 6
            }
        }
        
        # Health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}
        self.initialize_provider_health()
        
        # Request tracking
        self.request_history: Dict[str, List[datetime]] = {}
        self.token_usage: Dict[str, List[Tuple[datetime, int]]] = {}
        
        # Routing strategy
        self.routing_strategy = os.getenv('ROUTING_STRATEGY', 'intelligent')  # intelligent, cost, performance, availability
        self.enable_auto_fallback = os.getenv('ENABLE_AUTO_FALLBACK', 'true').lower() == 'true'
        self.max_fallback_attempts = int(os.getenv('MAX_FALLBACK_ATTEMPTS', '3'))
        
        # Rate limiting detection
        self.rate_limit_detection_window = int(os.getenv('RATE_LIMIT_DETECTION_WINDOW', '60'))  # seconds
        self.rate_limit_threshold = float(os.getenv('RATE_LIMIT_THRESHOLD', '0.8'))  # 80% of limit
        
        # Cost optimization
        self.enable_cost_optimization = os.getenv('ENABLE_COST_OPTIMIZATION', 'true').lower() == 'true'
        self.max_cost_per_request = float(os.getenv('MAX_COST_PER_REQUEST', '1.0'))
        
        # Performance tracking
        self.performance_window = timedelta(minutes=int(os.getenv('PERFORMANCE_WINDOW', '10')))
        
        # Prometheus metrics
        self.setup_metrics()
        
        logger.info("Rate limiting router initialized", 
                   strategy=self.routing_strategy,
                   providers=list(self.providers.keys()))

    def setup_metrics(self):
        """Setup Prometheus metrics"""
        self.route_decisions_counter = Counter(
            'route_decisions_total',
            'Total routing decisions made',
            ['strategy', 'selected_provider', 'reasoning']
        )
        
        self.rate_limit_detected_counter = Counter(
            'rate_limits_detected_total',
            'Total rate limits detected',
            ['provider', 'limit_type']
        )
        
        self.fallback_attempts_counter = Counter(
            'fallback_attempts_total',
            'Total fallback attempts',
            ['from_provider', 'to_provider', 'success']
        )
        
        self.provider_health_gauge = Gauge(
            'provider_health_score',
            'Provider health score (0-1)',
            ['provider']
        )

    def initialize_provider_health(self):
        """Initialize provider health tracking"""
        for provider_name in self.providers.keys():
            self.provider_health[provider_name] = ProviderHealth(
                status=ProviderStatus.AVAILABLE,
                priority_score=self.providers[provider_name]['priority'] / 10.0
            )
            self.request_history[provider_name] = []
            self.token_usage[provider_name] = []

    async def route_request(self, anthropic_model: str, request_body: Dict[str, Any], 
                          user_preferences: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Main routing logic - decides which provider and model to use
        """
        logger.info("Routing request", model=anthropic_model, strategy=self.routing_strategy)
        
        # Update provider health
        await self.update_provider_health()
        
        # Get available providers
        available_providers = self.get_available_providers()
        
        if not available_providers:
            raise Exception("No providers available")
        
        # Select provider based on strategy
        if self.routing_strategy == 'cost':
            decision = await self.route_by_cost(anthropic_model, request_body, available_providers)
        elif self.routing_strategy == 'performance':
            decision = await self.route_by_performance(anthropic_model, request_body, available_providers)
        elif self.routing_strategy == 'availability':
            decision = await self.route_by_availability(anthropic_model, request_body, available_providers)
        else:  # intelligent
            decision = await self.route_intelligently(anthropic_model, request_body, available_providers, user_preferences)
        
        # Log decision
        self.route_decisions_counter.labels(
            strategy=self.routing_strategy,
            selected_provider=decision.selected_provider,
            reasoning=decision.reasoning[:50]  # Truncate for labels
        ).inc()
        
        logger.info("Routing decision made",
                   provider=decision.selected_provider,
                   model=decision.selected_model,
                   reasoning=decision.reasoning,
                   estimated_cost=decision.estimated_cost)
        
        return decision

    async def route_intelligently(self, anthropic_model: str, request_body: Dict[str, Any], 
                                available_providers: List[str], 
                                user_preferences: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Intelligent routing that considers multiple factors
        """
        scores = {}
        
        for provider in available_providers:
            score = await self.calculate_provider_score(provider, anthropic_model, request_body, user_preferences)
            scores[provider] = score
        
        # Select best provider
        best_provider = max(scores.keys(), key=lambda p: scores[p])
        selected_model = self.select_model_for_provider(best_provider, anthropic_model)
        
        # Calculate fallback options
        fallback_options = []
        sorted_providers = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)[1:]
        for provider in sorted_providers[:3]:  # Top 3 fallbacks
            model = self.select_model_for_provider(provider, anthropic_model)
            fallback_options.append((provider, model))
        
        return RoutingDecision(
            selected_provider=best_provider,
            selected_model=selected_model,
            reasoning=f"Intelligent routing: score={scores[best_provider]:.2f}, factors=rate_limits+cost+performance",
            fallback_options=fallback_options,
            estimated_cost=self.estimate_cost(best_provider, selected_model, request_body)
        )

    async def calculate_provider_score(self, provider: str, anthropic_model: str, 
                                     request_body: Dict[str, Any], 
                                     user_preferences: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate a comprehensive score for a provider
        """
        health = self.provider_health[provider]
        config = self.providers[provider]
        
        # Base score from provider priority
        score = health.priority_score
        
        # Rate limiting penalty
        if await self.is_approaching_rate_limit(provider):
            score *= 0.3  # Heavy penalty for approaching rate limits
        elif health.status == ProviderStatus.RATE_LIMITED:
            score *= 0.1  # Very heavy penalty for active rate limits
        
        # Performance bonus
        if health.avg_response_time > 0:
            # Prefer faster providers
            performance_factor = max(0.5, 2.0 / (1 + health.avg_response_time))
            score *= performance_factor
        
        # Success rate bonus
        if health.success_count > 0:
            success_rate = health.success_count / (health.success_count + health.error_count)
            score *= success_rate
        
        # Cost optimization
        if self.enable_cost_optimization:
            cost = self.estimate_cost(provider, self.select_model_for_provider(provider, anthropic_model), request_body)
            cost_factor = max(0.5, 1.0 / (1 + cost))
            score *= cost_factor
        
        # Model availability check
        selected_model = self.select_model_for_provider(provider, anthropic_model)
        if not await self.is_model_available(provider, selected_model):
            score *= 0.2
        
        # User preferences
        if user_preferences:
            if user_preferences.get('prefer_fast', False) and health.avg_response_time < 2.0:
                score *= 1.2
            if user_preferences.get('prefer_cheap', False):
                score *= config['cost_multiplier'] ** -1
            if user_preferences.get('preferred_provider') == provider:
                score *= 1.5
        
        return score

    async def route_by_cost(self, anthropic_model: str, request_body: Dict[str, Any], 
                          available_providers: List[str]) -> RoutingDecision:
        """Route by lowest cost"""
        costs = {}
        for provider in available_providers:
            model = self.select_model_for_provider(provider, anthropic_model)
            costs[provider] = self.estimate_cost(provider, model, request_body)
        
        cheapest_provider = min(costs.keys(), key=lambda p: costs[p])
        selected_model = self.select_model_for_provider(cheapest_provider, anthropic_model)
        
        fallback_options = []
        sorted_providers = sorted(costs.keys(), key=lambda p: costs[p])[1:]
        for provider in sorted_providers[:3]:
            model = self.select_model_for_provider(provider, anthropic_model)
            fallback_options.append((provider, model))
        
        return RoutingDecision(
            selected_provider=cheapest_provider,
            selected_model=selected_model,
            reasoning=f"Cost optimization: ${costs[cheapest_provider]:.4f}",
            fallback_options=fallback_options,
            estimated_cost=costs[cheapest_provider]
        )

    async def route_by_performance(self, anthropic_model: str, request_body: Dict[str, Any], 
                                 available_providers: List[str]) -> RoutingDecision:
        """Route by best performance"""
        performance_scores = {}
        
        for provider in available_providers:
            health = self.provider_health[provider]
            
            # Calculate performance score
            score = 1.0
            if health.avg_response_time > 0:
                score = 10.0 / (1 + health.avg_response_time)
            
            if health.success_count > 0:
                success_rate = health.success_count / (health.success_count + health.error_count)
                score *= success_rate
            
            performance_scores[provider] = score
        
        best_provider = max(performance_scores.keys(), key=lambda p: performance_scores[p])
        selected_model = self.select_model_for_provider(best_provider, anthropic_model)
        
        fallback_options = []
        sorted_providers = sorted(performance_scores.keys(), key=lambda p: performance_scores[p], reverse=True)[1:]
        for provider in sorted_providers[:3]:
            model = self.select_model_for_provider(provider, anthropic_model)
            fallback_options.append((provider, model))
        
        return RoutingDecision(
            selected_provider=best_provider,
            selected_model=selected_model,
            reasoning=f"Performance optimization: score={performance_scores[best_provider]:.2f}",
            fallback_options=fallback_options,
            estimated_cost=self.estimate_cost(best_provider, selected_model, request_body)
        )

    async def route_by_availability(self, anthropic_model: str, request_body: Dict[str, Any], 
                                  available_providers: List[str]) -> RoutingDecision:
        """Route by highest availability"""
        availability_scores = {}
        
        for provider in available_providers:
            health = self.provider_health[provider]
            
            score = 1.0
            if health.status == ProviderStatus.AVAILABLE:
                score = 1.0
            elif health.status == ProviderStatus.RATE_LIMITED:
                score = 0.2
            elif health.status == ProviderStatus.OVERLOADED:
                score = 0.5
            else:
                score = 0.1
            
            # Boost score based on recent success
            if health.last_success and health.last_error:
                if health.last_success > health.last_error:
                    score *= 1.2
            
            availability_scores[provider] = score
        
        best_provider = max(availability_scores.keys(), key=lambda p: availability_scores[p])
        selected_model = self.select_model_for_provider(best_provider, anthropic_model)
        
        fallback_options = []
        sorted_providers = sorted(availability_scores.keys(), key=lambda p: availability_scores[p], reverse=True)[1:]
        for provider in sorted_providers[:3]:
            model = self.select_model_for_provider(provider, anthropic_model)
            fallback_options.append((provider, model))
        
        return RoutingDecision(
            selected_provider=best_provider,
            selected_model=selected_model,
            reasoning=f"Availability optimization: score={availability_scores[best_provider]:.2f}",
            fallback_options=fallback_options,
            estimated_cost=self.estimate_cost(best_provider, selected_model, request_body)
        )

    def select_model_for_provider(self, provider: str, anthropic_model: str) -> str:
        """Select appropriate model for a provider based on requested model"""
        config = self.providers[provider]
        
        # Model mapping logic
        if 'haiku' in anthropic_model.lower():
            return config['secondary_model']
        else:
            return config['primary_model']

    def estimate_cost(self, provider: str, model: str, request_body: Dict[str, Any]) -> float:
        """Estimate cost for a request"""
        # Rough token estimation
        estimated_tokens = self.estimate_tokens(request_body.get('messages', []))
        
        # Base cost per token (simplified)
        base_cost_per_token = 0.000003  # Average cost
        
        # Apply provider cost multiplier
        cost_multiplier = self.providers[provider]['cost_multiplier']
        
        return estimated_tokens * base_cost_per_token * cost_multiplier

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
        return max(100, total_chars // 4)  # Minimum 100 tokens

    async def is_approaching_rate_limit(self, provider: str) -> bool:
        """Check if provider is approaching rate limits"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.rate_limit_detection_window)
        
        # Count recent requests
        recent_requests = [
            req_time for req_time in self.request_history[provider]
            if req_time > window_start
        ]
        
        # Check request rate limit
        config = self.providers[provider]
        requests_per_window = len(recent_requests)
        max_requests_per_window = config['max_requests_per_minute'] * (self.rate_limit_detection_window / 60)
        
        if requests_per_window > max_requests_per_window * self.rate_limit_threshold:
            logger.warning("Approaching request rate limit", 
                         provider=provider,
                         current=requests_per_window,
                         limit=max_requests_per_window)
            return True
        
        # Check token rate limit
        recent_tokens = sum([
            tokens for req_time, tokens in self.token_usage[provider]
            if req_time > window_start
        ])
        
        max_tokens_per_window = config['max_tokens_per_minute'] * (self.rate_limit_detection_window / 60)
        
        if recent_tokens > max_tokens_per_window * self.rate_limit_threshold:
            logger.warning("Approaching token rate limit", 
                         provider=provider,
                         current=recent_tokens,
                         limit=max_tokens_per_window)
            return True
        
        return False

    async def is_model_available(self, provider: str, model: str) -> bool:
        """Check if model is available for provider"""
        # For now, assume all configured models are available
        # In a real implementation, this would check the provider's API
        return True

    def get_available_providers(self) -> List[str]:
        """Get list of currently available providers"""
        available = []
        for provider, health in self.provider_health.items():
            if health.status in [ProviderStatus.AVAILABLE, ProviderStatus.OVERLOADED]:
                available.append(provider)
        
        return available

    async def update_provider_health(self):
        """Update health status for all providers"""
        for provider in self.providers.keys():
            await self.check_provider_health(provider)

    async def check_provider_health(self, provider: str):
        """Check health of a specific provider"""
        health = self.provider_health[provider]
        config = self.providers[provider]
        
        try:
            # Check if rate limited
            if await self.is_approaching_rate_limit(provider):
                health.status = ProviderStatus.RATE_LIMITED
                self.rate_limit_detected_counter.labels(
                    provider=provider,
                    limit_type='approaching'
                ).inc()
            else:
                health.status = ProviderStatus.AVAILABLE
            
            # Update Prometheus metrics
            health_score = self.calculate_health_score(health)
            self.provider_health_gauge.labels(provider=provider).set(health_score)
            
        except Exception as e:
            logger.error("Error checking provider health", provider=provider, error=str(e))
            health.status = ProviderStatus.ERROR

    def calculate_health_score(self, health: ProviderHealth) -> float:
        """Calculate a 0-1 health score for a provider"""
        if health.status == ProviderStatus.AVAILABLE:
            base_score = 1.0
        elif health.status == ProviderStatus.OVERLOADED:
            base_score = 0.7
        elif health.status == ProviderStatus.RATE_LIMITED:
            base_score = 0.3
        else:
            base_score = 0.1
        
        # Adjust based on success rate
        if health.success_count > 0:
            success_rate = health.success_count / (health.success_count + health.error_count)
            base_score *= success_rate
        
        return base_score

    async def record_request(self, provider: str, model: str, success: bool, 
                           response_time: float, tokens_used: int, error: str = None):
        """Record a request for tracking"""
        now = datetime.now(timezone.utc)
        health = self.provider_health[provider]
        
        # Update request history
        self.request_history[provider].append(now)
        self.token_usage[provider].append((now, tokens_used))
        
        # Keep only recent history
        cutoff_time = now - timedelta(hours=1)
        self.request_history[provider] = [
            req_time for req_time in self.request_history[provider]
            if req_time > cutoff_time
        ]
        self.token_usage[provider] = [
            (req_time, tokens) for req_time, tokens in self.token_usage[provider]
            if req_time > cutoff_time
        ]
        
        # Update health metrics
        if success:
            health.success_count += 1
            health.last_success = now
        else:
            health.error_count += 1
            health.last_error = now
        
        # Update average response time
        if health.avg_response_time == 0:
            health.avg_response_time = response_time
        else:
            health.avg_response_time = (health.avg_response_time + response_time) / 2

    async def detect_rate_limit_from_response(self, provider: str, status_code: int, 
                                            headers: Dict[str, str], response_body: str):
        """Detect rate limiting from API response"""
        health = self.provider_health[provider]
        
        if status_code == 429:  # Too Many Requests
            health.status = ProviderStatus.RATE_LIMITED
            
            # Extract rate limit information from headers
            rate_limit_info = self.parse_rate_limit_headers(headers)
            if rate_limit_info:
                health.rate_limit_info = rate_limit_info
            
            self.rate_limit_detected_counter.labels(
                provider=provider,
                limit_type='active'
            ).inc()
            
            logger.warning("Rate limit detected", 
                         provider=provider, 
                         retry_after=rate_limit_info.retry_after if rate_limit_info else 'unknown')
        
        elif status_code in [502, 503, 504]:  # Server errors
            health.status = ProviderStatus.OVERLOADED
            logger.warning("Provider overloaded", provider=provider, status_code=status_code)

    def parse_rate_limit_headers(self, headers: Dict[str, str]) -> Optional[RateLimitInfo]:
        """Parse rate limit information from response headers"""
        try:
            # Common rate limit headers
            retry_after = headers.get('retry-after', headers.get('Retry-After'))
            reset_time = headers.get('x-ratelimit-reset', headers.get('X-RateLimit-Reset'))
            remaining = headers.get('x-ratelimit-remaining', headers.get('X-RateLimit-Remaining'))
            limit = headers.get('x-ratelimit-limit', headers.get('X-RateLimit-Limit'))
            
            if not any([retry_after, reset_time, remaining, limit]):
                return None
            
            # Parse reset time
            reset_datetime = None
            if reset_time:
                try:
                    reset_datetime = datetime.fromtimestamp(int(reset_time), timezone.utc)
                except (ValueError, TypeError):
                    pass
            
            return RateLimitInfo(
                requests_per_minute=int(limit) if limit else 0,
                requests_remaining=int(remaining) if remaining else 0,
                reset_time=reset_datetime or datetime.now(timezone.utc) + timedelta(minutes=1),
                retry_after=int(retry_after) if retry_after else 60
            )
            
        except Exception as e:
            logger.warning("Failed to parse rate limit headers", error=str(e))
            return None

    async def handle_fallback(self, original_decision: RoutingDecision, 
                            error: Exception) -> Optional[RoutingDecision]:
        """Handle fallback when primary provider fails"""
        if not self.enable_auto_fallback or not original_decision.fallback_options:
            return None
        
        logger.info("Attempting fallback", 
                   original_provider=original_decision.selected_provider,
                   fallback_options=len(original_decision.fallback_options))
        
        for provider, model in original_decision.fallback_options:
            if self.provider_health[provider].status == ProviderStatus.AVAILABLE:
                self.fallback_attempts_counter.labels(
                    from_provider=original_decision.selected_provider,
                    to_provider=provider,
                    success='attempted'
                ).inc()
                
                return RoutingDecision(
                    selected_provider=provider,
                    selected_model=model,
                    reasoning=f"Fallback from {original_decision.selected_provider} due to {type(error).__name__}",
                    fallback_options=[],  # No nested fallbacks for now
                    estimated_cost=self.estimate_cost(provider, model, {}),
                    estimated_delay=2.0  # Small delay for fallback
                )
        
        return None

def main():
    """Test the rate limiting router"""
    router = RateLimitingRouter()
    
    async def test_routing():
        # Test request
        request_body = {
            'messages': [
                {'role': 'user', 'content': 'Hello, how are you?'}
            ],
            'max_tokens': 100
        }
        
        # Test different routing strategies
        strategies = ['intelligent', 'cost', 'performance', 'availability']
        
        for strategy in strategies:
            router.routing_strategy = strategy
            decision = await router.route_request('claude-3-5-sonnet-20241022', request_body)
            print(f"\nStrategy: {strategy}")
            print(f"Provider: {decision.selected_provider}")
            print(f"Model: {decision.selected_model}")
            print(f"Reasoning: {decision.reasoning}")
            print(f"Estimated Cost: ${decision.estimated_cost:.4f}")
    
    asyncio.run(test_routing())

if __name__ == "__main__":
    main()