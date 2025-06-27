#!/usr/bin/env python3
"""
LLM Intelligence Integration with Rate Limiting Router
====================================================

Enhances the existing rate_limiting_router.py with real-time 
LLM intelligence data from Supabase for optimal provider 
and model selection.

Key Features:
- Real-time model rankings integration
- Dynamic provider routing based on cost/performance data
- Free tier optimization and quota management
- Benchmark-driven model selection
- Multi-provider intelligence with fallback optimization
"""

import asyncio
import logging
import json
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import httpx

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rate_limiting_router import RateLimitingRouter, RoutingDecision, ProviderStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMIntelligenceClient:
    """Client for LLM Intelligence API integration"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.session = httpx.AsyncClient(timeout=10.0)
        
    async def get_model_rankings(self, use_case: str = "general", 
                               limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """Get real-time model rankings from intelligence API"""
        try:
            params = {"use_case": use_case, "limit": limit, **filters}
            response = await self.session.get(f"{self.api_base_url}/rankings", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get model rankings: {e}")
            return []
            
    async def get_provider_options(self, model_name: str) -> List[Dict[str, Any]]:
        """Get optimal provider routing for specific model"""
        try:
            response = await self.session.get(f"{self.api_base_url}/providers/{model_name}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get provider options for {model_name}: {e}")
            return []
            
    async def get_recommendations(self, current_usage_usd: float = 100.0, 
                                use_case: str = "general") -> List[Dict[str, Any]]:
        """Get intelligent cost optimization recommendations"""
        try:
            params = {"current_usage_usd": current_usage_usd, "use_case": use_case}
            response = await self.session.get(f"{self.api_base_url}/recommendations", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get recommendations: {e}")
            return []
            
    async def get_free_tier_models(self, use_case: str = "general", 
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """Get top free tier models"""
        try:
            params = {"use_case": use_case, "limit": limit}
            response = await self.session.get(f"{self.api_base_url}/rankings/top-free", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get free tier models: {e}")
            return []

class IntelligentRoutingEnhancement(RateLimitingRouter):
    """Enhanced rate limiting router with LLM intelligence integration"""
    
    def __init__(self, intelligence_api_url: str = "http://localhost:8000"):
        super().__init__()
        self.intelligence_client = LLMIntelligenceClient(intelligence_api_url)
        
        # Enhanced provider mapping to include intelligence data
        self.provider_model_mapping = {
            'vertex': {
                'claude-3-5-sonnet': 'claude-sonnet-4@20250514',
                'claude-3-haiku': 'claude-3-5-haiku@20241022',
                'gemini-1.5-pro': 'gemini-1.5-pro-002'
            },
            'github': {
                'claude-3-5-sonnet': 'claude-3-5-sonnet',
                'claude-3-haiku': 'claude-3-5-haiku',
                'gpt-4o': 'gpt-4o',
                'gpt-4o-mini': 'gpt-4o-mini',
                'llama-3.1-405b': 'llama-3.1-405b-instruct'
            },
            'openrouter': {
                'claude-3-5-sonnet': 'anthropic/claude-3.5-sonnet',
                'claude-3-haiku': 'anthropic/claude-3-haiku',
                'gpt-4o': 'openai/gpt-4o',
                'deepseek-r1': 'deepseek/deepseek-r1:free',
                'qwen-2.5-coder': 'qwen/qwen-2.5-coder-32b-instruct:free'
            }
        }
        
        # Intelligence-based optimization settings
        self.enable_intelligence_routing = os.getenv('ENABLE_INTELLIGENCE_ROUTING', 'true').lower() == 'true'
        self.intelligence_cache_ttl = int(os.getenv('INTELLIGENCE_CACHE_TTL', '300'))  # 5 minutes
        self.intelligence_cache = {}
        self.last_intelligence_update = {}
        
        logger.info("Intelligent routing enhancement initialized", 
                   intelligence_enabled=self.enable_intelligence_routing,
                   api_url=intelligence_api_url)
        
    async def route_intelligently(self, anthropic_model: str, request_body: Dict[str, Any], 
                                available_providers: List[str], 
                                user_preferences: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Enhanced intelligent routing with LLM intelligence data
        """
        if not self.enable_intelligence_routing:
            return await super().route_intelligently(anthropic_model, request_body, 
                                                   available_providers, user_preferences)
        
        logger.info("Using intelligence-enhanced routing", model=anthropic_model)
        
        # Get intelligence data
        intelligence_data = await self.get_cached_intelligence_data(anthropic_model, user_preferences)
        
        # Calculate enhanced scores
        scores = {}
        for provider in available_providers:
            score = await self.calculate_enhanced_provider_score(
                provider, anthropic_model, request_body, user_preferences, intelligence_data
            )
            scores[provider] = score
            
        # Select best provider
        best_provider = max(scores.keys(), key=lambda p: scores[p])
        selected_model = await self.select_intelligent_model(best_provider, anthropic_model, intelligence_data)
        
        # Calculate enhanced fallback options
        fallback_options = await self.calculate_intelligent_fallbacks(
            scores, anthropic_model, intelligence_data
        )
        
        reasoning = await self.generate_intelligent_reasoning(
            best_provider, selected_model, scores[best_provider], intelligence_data
        )
        
        return RoutingDecision(
            selected_provider=best_provider,
            selected_model=selected_model,
            reasoning=reasoning,
            fallback_options=fallback_options,
            estimated_cost=await self.calculate_enhanced_cost(best_provider, selected_model, request_body, intelligence_data)
        )
        
    async def get_cached_intelligence_data(self, model: str, 
                                         user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get cached intelligence data with TTL"""
        cache_key = f"{model}_{hash(str(user_preferences))}"
        now = datetime.now()
        
        # Check cache
        if (cache_key in self.intelligence_cache and 
            cache_key in self.last_intelligence_update and
            (now - self.last_intelligence_update[cache_key]).seconds < self.intelligence_cache_ttl):
            return self.intelligence_cache[cache_key]
            
        # Fetch fresh data
        logger.info("Fetching fresh intelligence data", model=model)
        
        try:
            # Determine use case from user preferences
            use_case = "general"
            if user_preferences:
                if user_preferences.get('use_case'):
                    use_case = user_preferences['use_case']
                elif user_preferences.get('prefer_coding', False):
                    use_case = "coding"
                elif user_preferences.get('prefer_cheap', False):
                    use_case = "cost_sensitive"
                    
            # Fetch intelligence data
            rankings = await self.intelligence_client.get_model_rankings(use_case=use_case, limit=20)
            provider_options = await self.intelligence_client.get_provider_options(model)
            recommendations = await self.intelligence_client.get_recommendations(use_case=use_case)
            free_models = await self.intelligence_client.get_free_tier_models(use_case=use_case)
            
            intelligence_data = {
                'rankings': rankings,
                'provider_options': provider_options,
                'recommendations': recommendations,
                'free_models': free_models,
                'use_case': use_case,
                'timestamp': now
            }
            
            # Cache the data
            self.intelligence_cache[cache_key] = intelligence_data
            self.last_intelligence_update[cache_key] = now
            
            return intelligence_data
            
        except Exception as e:
            logger.error(f"Failed to fetch intelligence data: {e}")
            # Return empty data structure
            return {
                'rankings': [], 'provider_options': [], 
                'recommendations': [], 'free_models': [],
                'use_case': use_case, 'timestamp': now
            }
            
    async def calculate_enhanced_provider_score(self, provider: str, anthropic_model: str, 
                                              request_body: Dict[str, Any], 
                                              user_preferences: Optional[Dict[str, Any]],
                                              intelligence_data: Dict[str, Any]) -> float:
        """Calculate enhanced provider score using intelligence data"""
        
        # Start with base score from parent class
        base_score = await super().calculate_provider_score(provider, anthropic_model, request_body, user_preferences)
        
        # Apply intelligence enhancements
        intelligence_bonus = 0.0
        
        # Model ranking bonus
        model_ranking = self.find_model_in_rankings(anthropic_model, intelligence_data['rankings'])
        if model_ranking:
            # Boost score based on model performance
            performance_bonus = model_ranking.get('composite_score', 0.5) * 0.3
            intelligence_bonus += performance_bonus
            
            # Free tier bonus
            if model_ranking.get('has_free_tier', False) and user_preferences and user_preferences.get('prefer_cheap', False):
                intelligence_bonus += 0.5
                
        # Provider option bonus
        provider_option = self.find_provider_option(provider, intelligence_data['provider_options'])
        if provider_option:
            # Selection probability bonus
            selection_prob = provider_option.get('selection_probability', 0.5)
            intelligence_bonus += selection_prob * 0.2
            
            # Cost advantage bonus
            cost_advantage = provider_option.get('cost_advantage_percent', 0)
            if cost_advantage > 0:
                intelligence_bonus += min(cost_advantage / 100, 0.3)
                
        # Free tier recommendation bonus
        if self.is_model_in_free_tier(anthropic_model, intelligence_data['free_models']):
            if user_preferences and user_preferences.get('prefer_cheap', False):
                intelligence_bonus += 1.0  # Huge bonus for free tier when cost-sensitive
            else:
                intelligence_bonus += 0.3  # Moderate bonus otherwise
                
        # Apply intelligence bonus
        enhanced_score = base_score + intelligence_bonus
        
        logger.debug("Enhanced provider score calculated",
                    provider=provider,
                    base_score=base_score,
                    intelligence_bonus=intelligence_bonus,
                    enhanced_score=enhanced_score)
        
        return enhanced_score
        
    async def select_intelligent_model(self, provider: str, anthropic_model: str, 
                                     intelligence_data: Dict[str, Any]) -> str:
        """Select best model variant using intelligence data"""
        
        # Check if we have specific provider options
        provider_options = intelligence_data.get('provider_options', [])
        
        for option in provider_options:
            if option.get('provider_name') == provider:
                # Use the exact model ID from intelligence data
                model_id = option.get('provider_metadata', {}).get('model_id')
                if model_id:
                    return model_id
                    
        # Fall back to provider mapping
        provider_mapping = self.provider_model_mapping.get(provider, {})
        
        # Try to find exact match first
        if anthropic_model in provider_mapping:
            return provider_mapping[anthropic_model]
            
        # Fall back to base class logic
        return self.select_model_for_provider(provider, anthropic_model)
        
    async def calculate_intelligent_fallbacks(self, scores: Dict[str, float], 
                                            anthropic_model: str,
                                            intelligence_data: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Calculate intelligent fallback options"""
        fallback_options = []
        
        # Sort providers by score (excluding the best one)
        sorted_providers = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)[1:]
        
        for provider in sorted_providers[:3]:  # Top 3 fallbacks
            model = await self.select_intelligent_model(provider, anthropic_model, intelligence_data)
            fallback_options.append((provider, model))
            
        # Add free tier fallbacks if available
        free_models = intelligence_data.get('free_models', [])
        for free_model in free_models[:2]:  # Top 2 free models
            model_name = free_model.get('name', '')
            
            # Find provider for this free model
            for provider, mapping in self.provider_model_mapping.items():
                if model_name in mapping:
                    fallback_options.append((provider, mapping[model_name]))
                    break
                    
        return fallback_options[:5]  # Limit to 5 fallbacks
        
    async def generate_intelligent_reasoning(self, provider: str, model: str, 
                                           score: float, intelligence_data: Dict[str, Any]) -> str:
        """Generate detailed reasoning for the routing decision"""
        reasons = []
        
        # Base score reasoning
        reasons.append(f"Enhanced score: {score:.2f}")
        
        # Intelligence-specific reasoning
        model_ranking = self.find_model_in_rankings(model, intelligence_data['rankings'])
        if model_ranking:
            rank = model_ranking.get('overall_rank', 'unknown')
            performance = model_ranking.get('performance_score', 0)
            cost_efficiency = model_ranking.get('cost_efficiency_score', 0)
            
            reasons.append(f"Model rank: #{rank}")
            reasons.append(f"Performance: {performance:.2f}")
            reasons.append(f"Cost efficiency: {cost_efficiency:.2f}")
            
            if model_ranking.get('has_free_tier', False):
                reasons.append("Free tier available")
                
        # Provider-specific reasoning
        provider_option = self.find_provider_option(provider, intelligence_data['provider_options'])
        if provider_option:
            selection_prob = provider_option.get('selection_probability', 0)
            cost_advantage = provider_option.get('cost_advantage_percent', 0)
            
            reasons.append(f"Selection probability: {selection_prob:.1%}")
            if cost_advantage > 0:
                reasons.append(f"Cost advantage: {cost_advantage:.1f}%")
                
        # Use case reasoning
        use_case = intelligence_data.get('use_case', 'general')
        if use_case != 'general':
            reasons.append(f"Optimized for: {use_case}")
            
        return "Intelligence-enhanced routing: " + ", ".join(reasons)
        
    async def calculate_enhanced_cost(self, provider: str, model: str, 
                                    request_body: Dict[str, Any],
                                    intelligence_data: Dict[str, Any]) -> float:
        """Calculate enhanced cost estimate using intelligence data"""
        
        # Check for free tier
        if self.is_model_in_free_tier(model, intelligence_data['free_models']):
            return 0.0
            
        # Get cost from provider options
        provider_option = self.find_provider_option(provider, intelligence_data['provider_options'])
        if provider_option:
            input_price = provider_option.get('input_price_per_million')
            output_price = provider_option.get('output_price_per_million')
            
            if input_price is not None and output_price is not None:
                # Estimate tokens
                estimated_input_tokens = self.estimate_tokens(request_body.get('messages', []))
                estimated_output_tokens = request_body.get('max_tokens', 150)
                
                # Calculate precise cost
                cost = (estimated_input_tokens * input_price + 
                       estimated_output_tokens * output_price) / 1_000_000
                       
                return cost
                
        # Fall back to base estimation
        return self.estimate_cost(provider, model, request_body)
        
    def find_model_in_rankings(self, model: str, rankings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find model in rankings data"""
        for ranking in rankings:
            if (ranking.get('name', '').lower() == model.lower() or
                model.lower() in ranking.get('name', '').lower()):
                return ranking
        return None
        
    def find_provider_option(self, provider: str, provider_options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find provider in provider options"""
        for option in provider_options:
            if option.get('provider_name', '').lower() == provider.lower():
                return option
        return None
        
    def is_model_in_free_tier(self, model: str, free_models: List[Dict[str, Any]]) -> bool:
        """Check if model is in free tier"""
        for free_model in free_models:
            if (model.lower() in free_model.get('name', '').lower() or
                free_model.get('name', '').lower() in model.lower()):
                return True
        return False
        
    async def get_intelligence_recommendations(self, current_usage_usd: float = 100.0) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations"""
        try:
            recommendations = await self.intelligence_client.get_recommendations(current_usage_usd)
            logger.info(f"Retrieved {len(recommendations)} intelligence recommendations")
            return recommendations
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []
            
    async def optimize_for_cost(self, anthropic_model: str, request_body: Dict[str, Any]) -> RoutingDecision:
        """Optimize routing specifically for cost using intelligence data"""
        
        # Get free tier models first
        intelligence_data = await self.get_cached_intelligence_data(anthropic_model, {'prefer_cheap': True})
        free_models = intelligence_data.get('free_models', [])
        
        # Try to use free tier model if available
        for free_model in free_models:
            model_name = free_model.get('name', '')
            
            # Find provider that supports this free model
            for provider, mapping in self.provider_model_mapping.items():
                if any(model_name.lower() in mapped_model.lower() for mapped_model in mapping.values()):
                    if self.provider_health[provider].status == ProviderStatus.AVAILABLE:
                        selected_model = next(
                            mapped_model for mapped_model in mapping.values() 
                            if model_name.lower() in mapped_model.lower()
                        )
                        
                        return RoutingDecision(
                            selected_provider=provider,
                            selected_model=selected_model,
                            reasoning=f"Cost optimization: Free tier model {model_name}",
                            fallback_options=[],
                            estimated_cost=0.0
                        )
                        
        # If no free tier available, use intelligence cost routing
        user_prefs = {'prefer_cheap': True, 'use_case': 'cost_sensitive'}
        return await self.route_intelligently(anthropic_model, request_body, 
                                            self.get_available_providers(), user_prefs)

async def main():
    """Test enhanced intelligent routing"""
    print("🧠 Testing LLM Intelligence Enhanced Routing")
    print("=" * 60)
    
    # Initialize enhanced router
    router = IntelligentRoutingEnhancement()
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'General Claude Request',
            'model': 'claude-3-5-sonnet',
            'request': {
                'messages': [{'role': 'user', 'content': 'Write a Python function to calculate fibonacci numbers'}],
                'max_tokens': 200
            },
            'preferences': None
        },
        {
            'name': 'Cost-Sensitive Request',
            'model': 'claude-3-haiku',
            'request': {
                'messages': [{'role': 'user', 'content': 'Simple greeting response'}],
                'max_tokens': 50
            },
            'preferences': {'prefer_cheap': True, 'use_case': 'cost_sensitive'}
        },
        {
            'name': 'Coding-Optimized Request',
            'model': 'claude-3-5-sonnet',
            'request': {
                'messages': [{'role': 'user', 'content': 'Debug this complex JavaScript code'}],
                'max_tokens': 500
            },
            'preferences': {'use_case': 'coding', 'prefer_fast': True}
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🔄 Testing: {scenario['name']}")
        print("-" * 40)
        
        try:
            decision = await router.route_request(
                scenario['model'],
                scenario['request'],
                scenario['preferences']
            )
            
            print(f"Selected Provider: {decision.selected_provider}")
            print(f"Selected Model: {decision.selected_model}")
            print(f"Reasoning: {decision.reasoning}")
            print(f"Estimated Cost: ${decision.estimated_cost:.6f}")
            print(f"Fallback Options: {len(decision.fallback_options)}")
            
            if decision.fallback_options:
                print("Fallbacks:")
                for i, (provider, model) in enumerate(decision.fallback_options[:3], 1):
                    print(f"  {i}. {provider}: {model}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            
    # Test cost optimization
    print(f"\n💰 Testing Cost Optimization")
    print("-" * 40)
    
    try:
        cost_decision = await router.optimize_for_cost(
            'claude-3-haiku',
            {'messages': [{'role': 'user', 'content': 'Hello'}], 'max_tokens': 50}
        )
        
        print(f"Cost-Optimized Provider: {cost_decision.selected_provider}")
        print(f"Cost-Optimized Model: {cost_decision.selected_model}")
        print(f"Cost: ${cost_decision.estimated_cost:.6f}")
        print(f"Reasoning: {cost_decision.reasoning}")
        
    except Exception as e:
        print(f"❌ Cost optimization error: {e}")
        
    # Test recommendations
    print(f"\n💡 Testing Intelligence Recommendations")
    print("-" * 40)
    
    try:
        recommendations = await router.get_intelligence_recommendations(150.0)
        
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"{i}. {rec.get('recommendation_type', 'Unknown')}")
            print(f"   {rec.get('explanation', 'No explanation')}")
            if rec.get('potential_savings_usd'):
                print(f"   Potential savings: ${rec['potential_savings_usd']:.2f}")
            if rec.get('recommended_models'):
                print(f"   Models: {', '.join(rec['recommended_models'][:3])}")
            print()
            
    except Exception as e:
        print(f"❌ Recommendations error: {e}")
        
    print("\n🎉 Enhanced routing testing completed!")

if __name__ == "__main__":
    asyncio.run(main())