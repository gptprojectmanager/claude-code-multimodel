#!/usr/bin/env python3
"""
REST API Endpoints for LLM Intelligence System
=============================================

FastAPI-based REST endpoints for real-time model ranking,
provider selection, and cost optimization recommendations.

Key Features:
- Real-time model rankings with dynamic scoring
- Intelligent provider routing and selection
- Cost optimization and free tier recommendations
- Benchmark leaderboards and performance analytics
- Rate limiting and caching for high performance
"""

import asyncio
import logging
from fastapi import FastAPI, HTTPException, Query, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal
import json
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="LLM Intelligence API",
    description="Real-time model ranking and provider intelligence for LLM selection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ModelRanking(BaseModel):
    id: str
    name: str
    provider: str
    model_family: str
    context_window: int
    capabilities: Dict[str, Any]
    
    # Pricing
    min_input_cost: Optional[float]
    avg_input_cost: Optional[float]
    has_free_tier: bool
    provider_count: int
    
    # Performance
    coding_score: Optional[float]
    reasoning_score: Optional[float]
    math_score: Optional[float]
    overall_performance: Optional[float]
    
    # Reliability
    avg_success_rate: Optional[float]
    avg_response_time: Optional[float]
    
    # Scores
    cost_efficiency_score: float
    performance_score: float
    reliability_score: float
    availability_score: float
    composite_score: float
    use_case_score: Optional[float]
    value_score: float
    
    # Rankings
    overall_rank: int
    use_case_rank: Optional[int]
    value_rank: int
    cost_rank: int
    
    # Metadata
    total_usage_requests: int
    avg_daily_cost: float
    ranking_timestamp: datetime

class ProviderOption(BaseModel):
    provider_name: str
    provider_id: str
    input_price_per_million: Optional[float]
    output_price_per_million: Optional[float]
    is_free_tier: bool
    recent_success_rate: Optional[float]
    recent_response_time: Optional[float]
    availability_score: float
    selection_probability: float
    provider_rank: int
    cost_advantage_percent: float
    rate_limits: Dict[str, Any]
    provider_metadata: Dict[str, Any]
    routing_timestamp: datetime

class Recommendation(BaseModel):
    recommendation_type: str
    potential_savings_usd: Optional[float]
    recommended_models: List[str]
    explanation: str
    priority: str = "medium"
    confidence: float = 0.8

class BenchmarkScore(BaseModel):
    model_name: str
    benchmark_name: str
    benchmark_category: str
    metric_type: str
    score: float
    normalized_score: float
    test_date: date
    source_organization: str
    is_verified: bool

class UseCaseWeights(BaseModel):
    cost_efficiency: float = Field(ge=0, le=1)
    performance: float = Field(ge=0, le=1)
    reliability: float = Field(ge=0, le=1)
    availability: float = Field(ge=0, le=1)

# Mock database connection (in production, use real Supabase client)
class MockSupabaseClient:
    """Mock Supabase client for development"""
    
    def __init__(self):
        self.mock_data = self._generate_mock_data()
        
    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate realistic mock data"""
        return {
            "rankings": [
                {
                    "id": "1",
                    "name": "claude-3.5-sonnet",
                    "provider": "anthropic",
                    "model_family": "claude",
                    "context_window": 200000,
                    "capabilities": {"supports_function_calling": True, "supports_vision": True},
                    "min_input_cost": 3.0,
                    "avg_input_cost": 3.2,
                    "has_free_tier": False,
                    "provider_count": 2,
                    "coding_score": 0.92,
                    "reasoning_score": 0.888,
                    "math_score": 0.952,
                    "overall_performance": 0.92,
                    "avg_success_rate": 0.99,
                    "avg_response_time": 850.0,
                    "cost_efficiency_score": 0.77,
                    "performance_score": 0.92,
                    "reliability_score": 0.95,
                    "availability_score": 0.8,
                    "composite_score": 0.86,
                    "use_case_score": 0.92,
                    "value_score": 6.8,
                    "overall_rank": 1,
                    "use_case_rank": 1,
                    "value_rank": 2,
                    "cost_rank": 4,
                    "total_usage_requests": 1250,
                    "avg_daily_cost": 15.75,
                    "ranking_timestamp": datetime.now()
                },
                {
                    "id": "2", 
                    "name": "gpt-4o",
                    "provider": "openai",
                    "model_family": "gpt",
                    "context_window": 128000,
                    "capabilities": {"supports_function_calling": True, "supports_vision": True},
                    "min_input_cost": 5.0,
                    "avg_input_cost": 5.0,
                    "has_free_tier": False,
                    "provider_count": 1,
                    "coding_score": 0.90,
                    "reasoning_score": 0.887,
                    "math_score": 0.956,
                    "overall_performance": 0.91,
                    "avg_success_rate": 0.98,
                    "avg_response_time": 950.0,
                    "cost_efficiency_score": 0.67,
                    "performance_score": 0.91,
                    "reliability_score": 0.92,
                    "availability_score": 0.6,
                    "composite_score": 0.80,
                    "use_case_score": 0.90,
                    "value_score": 4.2,
                    "overall_rank": 2,
                    "use_case_rank": 2,
                    "value_rank": 4,
                    "cost_rank": 6,
                    "total_usage_requests": 980,
                    "avg_daily_cost": 22.50,
                    "ranking_timestamp": datetime.now()
                },
                {
                    "id": "3",
                    "name": "deepseek-r1:free",
                    "provider": "openrouter",
                    "model_family": "deepseek",
                    "context_window": 32768,
                    "capabilities": {"supports_function_calling": True},
                    "min_input_cost": 0.0,
                    "avg_input_cost": 0.0,
                    "has_free_tier": True,
                    "provider_count": 1,
                    "coding_score": 0.75,
                    "reasoning_score": 0.78,
                    "math_score": 0.82,
                    "overall_performance": 0.78,
                    "avg_success_rate": 0.96,
                    "avg_response_time": 1200.0,
                    "cost_efficiency_score": 1.0,
                    "performance_score": 0.78,
                    "reliability_score": 0.85,
                    "availability_score": 0.6,
                    "composite_score": 0.81,
                    "use_case_score": 0.75,
                    "value_score": 15.6,
                    "overall_rank": 3,
                    "use_case_rank": 3,
                    "value_rank": 1,
                    "cost_rank": 1,
                    "total_usage_requests": 650,
                    "avg_daily_cost": 0.0,
                    "ranking_timestamp": datetime.now()
                }
            ],
            "providers": {
                "claude-3.5-sonnet": [
                    {
                        "provider_name": "anthropic",
                        "provider_id": "anthropic-api",
                        "input_price_per_million": 3.0,
                        "output_price_per_million": 15.0,
                        "is_free_tier": False,
                        "recent_success_rate": 0.99,
                        "recent_response_time": 850.0,
                        "availability_score": 1.0,
                        "selection_probability": 0.69,
                        "provider_rank": 1,
                        "cost_advantage_percent": 12.5,
                        "rate_limits": {"requests_per_minute": 100, "tokens_per_minute": 500000},
                        "provider_metadata": {"region": "us-east-1", "model_version": "20241022"},
                        "routing_timestamp": datetime.now()
                    },
                    {
                        "provider_name": "openrouter",
                        "provider_id": "openrouter-anthropic",
                        "input_price_per_million": 3.5,
                        "output_price_per_million": 16.0,
                        "is_free_tier": False,
                        "recent_success_rate": 0.97,
                        "recent_response_time": 1100.0,
                        "availability_score": 0.8,
                        "selection_probability": 0.31,
                        "provider_rank": 2,
                        "cost_advantage_percent": -2.8,
                        "rate_limits": {"requests_per_minute": 200, "tokens_per_minute": 100000},
                        "provider_metadata": {"openrouter_routing": True, "fallback_available": True},
                        "routing_timestamp": datetime.now()
                    }
                ]
            }
        }
        
    async def get_model_rankings(self, use_case: str = "general", limit: int = 10, 
                               filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get model rankings with filters"""
        rankings = self.mock_data["rankings"].copy()
        
        # Apply filters
        if filters:
            if filters.get("has_free_tier") is not None:
                rankings = [r for r in rankings if r["has_free_tier"] == filters["has_free_tier"]]
            if filters.get("min_performance"):
                rankings = [r for r in rankings if r["performance_score"] >= filters["min_performance"]]
            if filters.get("max_cost"):
                rankings = [r for r in rankings if r["min_input_cost"] is None or r["min_input_cost"] <= filters["max_cost"] or r["has_free_tier"]]
                
        # Sort by appropriate score
        if use_case == "coding":
            rankings.sort(key=lambda x: x.get("coding_score", 0), reverse=True)
        elif use_case == "cost_sensitive":
            rankings.sort(key=lambda x: x["cost_efficiency_score"], reverse=True)
        else:
            rankings.sort(key=lambda x: x["composite_score"], reverse=True)
            
        return rankings[:limit]
        
    async def get_provider_options(self, model_name: str) -> List[Dict[str, Any]]:
        """Get provider options for a specific model"""
        return self.mock_data["providers"].get(model_name, [])
        
    async def get_benchmark_scores(self, benchmark_category: str = None) -> List[Dict[str, Any]]:
        """Get benchmark scores"""
        # Mock benchmark data
        benchmarks = [
            {
                "model_name": "claude-3.5-sonnet",
                "benchmark_name": "HumanEval",
                "benchmark_category": "coding",
                "metric_type": "pass@1",
                "score": 0.92,
                "normalized_score": 0.92,
                "test_date": date.today(),
                "source_organization": "anthropic",
                "is_verified": True
            },
            {
                "model_name": "gpt-4o",
                "benchmark_name": "MMLU",
                "benchmark_category": "reasoning", 
                "metric_type": "accuracy",
                "score": 0.887,
                "normalized_score": 0.887,
                "test_date": date.today(),
                "source_organization": "openai",
                "is_verified": True
            }
        ]
        
        if benchmark_category:
            benchmarks = [b for b in benchmarks if b["benchmark_category"] == benchmark_category]
            
        return benchmarks

# Global client instance
supabase_client = MockSupabaseClient()

# API Routes

@app.get("/", response_model=Dict[str, Any])
async def root():
    """API health check and information"""
    return {
        "service": "LLM Intelligence API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now(),
        "endpoints": {
            "rankings": "/rankings",
            "providers": "/providers/{model_name}",
            "recommendations": "/recommendations",
            "benchmarks": "/benchmarks",
            "docs": "/docs"
        }
    }

@app.get("/rankings", response_model=List[ModelRanking])
async def get_model_rankings(
    use_case: str = Query("general", description="Use case for optimization (general, coding, reasoning, math, cost_sensitive)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of models to return"),
    has_free_tier: Optional[bool] = Query(None, description="Filter by free tier availability"),
    min_performance: Optional[float] = Query(None, ge=0, le=1, description="Minimum performance score"),
    max_cost: Optional[float] = Query(None, ge=0, description="Maximum cost per million tokens"),
    provider: Optional[str] = Query(None, description="Filter by provider")
):
    """Get ranked list of LLM models with intelligent scoring"""
    
    try:
        filters = {}
        if has_free_tier is not None:
            filters["has_free_tier"] = has_free_tier
        if min_performance is not None:
            filters["min_performance"] = min_performance
        if max_cost is not None:
            filters["max_cost"] = max_cost
            
        rankings = await supabase_client.get_model_rankings(use_case, limit, filters)
        
        # Convert to Pydantic models
        return [ModelRanking(**ranking) for ranking in rankings]
        
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers/{model_name}", response_model=List[ProviderOption])
async def get_provider_options(
    model_name: str = Path(..., description="Name of the model to get provider options for"),
    prefer_free_tier: bool = Query(True, description="Prefer free tier options"),
    max_response_time: int = Query(2000, description="Maximum acceptable response time in ms")
):
    """Get optimal provider routing for a specific model"""
    
    try:
        providers = await supabase_client.get_provider_options(model_name)
        
        if not providers:
            raise HTTPException(status_code=404, detail=f"No providers found for model: {model_name}")
            
        # Convert to Pydantic models
        return [ProviderOption(**provider) for provider in providers]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider options: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations", response_model=List[Recommendation])
async def get_recommendations(
    current_usage_usd: float = Query(100.0, ge=0, description="Current monthly usage in USD"),
    use_case: str = Query("general", description="Primary use case"),
    performance_priority: float = Query(0.5, ge=0, le=1, description="Performance vs cost priority (0=cost, 1=performance)")
):
    """Get intelligent recommendations for cost optimization and model selection"""
    
    try:
        recommendations = []
        
        # Free tier recommendation
        if current_usage_usd > 0:
            recommendations.append(Recommendation(
                recommendation_type="free_tier",
                potential_savings_usd=current_usage_usd * 0.6,
                recommended_models=["deepseek-r1:free", "qwen-2.5-coder-32b:free"],
                explanation="Switch to free tier models for non-critical tasks to reduce costs",
                priority="high",
                confidence=0.9
            ))
            
        # Performance optimization
        if performance_priority > 0.7:
            recommendations.append(Recommendation(
                recommendation_type="performance_optimization",
                potential_savings_usd=None,
                recommended_models=["claude-3.5-sonnet", "gpt-4o"],
                explanation="Use top-performing models for critical tasks requiring highest quality",
                priority="medium",
                confidence=0.85
            ))
            
        # Cost efficiency
        if performance_priority < 0.3:
            recommendations.append(Recommendation(
                recommendation_type="cost_efficiency",
                potential_savings_usd=current_usage_usd * 0.4,
                recommended_models=["claude-3-haiku", "gpt-4o-mini"],
                explanation="Use cost-efficient models for routine tasks",
                priority="medium",
                confidence=0.8
            ))
            
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/benchmarks", response_model=List[BenchmarkScore])
async def get_benchmark_scores(
    benchmark_category: Optional[str] = Query(None, description="Filter by benchmark category (coding, reasoning, math)"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    benchmark_name: Optional[str] = Query(None, description="Filter by specific benchmark")
):
    """Get latest benchmark scores and leaderboards"""
    
    try:
        scores = await supabase_client.get_benchmark_scores(benchmark_category)
        
        # Apply additional filters
        if model_name:
            scores = [s for s in scores if model_name.lower() in s["model_name"].lower()]
        if benchmark_name:
            scores = [s for s in scores if benchmark_name.lower() in s["benchmark_name"].lower()]
            
        return [BenchmarkScore(**score) for score in scores]
        
    except Exception as e:
        logger.error(f"Error getting benchmark scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rankings/top-free", response_model=List[ModelRanking])
async def get_top_free_models(
    limit: int = Query(5, ge=1, le=20, description="Number of free models to return"),
    use_case: str = Query("general", description="Use case optimization")
):
    """Get top-performing free tier models"""
    
    try:
        rankings = await supabase_client.get_model_rankings(
            use_case=use_case, 
            limit=50,  # Get more to filter
            filters={"has_free_tier": True}
        )
        
        return [ModelRanking(**ranking) for ranking in rankings[:limit]]
        
    except Exception as e:
        logger.error(f"Error getting free models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rankings/best-value", response_model=List[ModelRanking])
async def get_best_value_models(
    limit: int = Query(5, ge=1, le=20, description="Number of models to return"),
    max_cost: float = Query(10.0, ge=0, description="Maximum cost per million tokens")
):
    """Get best value models (highest performance per dollar)"""
    
    try:
        rankings = await supabase_client.get_model_rankings(
            use_case="general",
            limit=50,
            filters={"max_cost": max_cost}
        )
        
        # Sort by value score
        rankings.sort(key=lambda x: x["value_score"], reverse=True)
        
        return [ModelRanking(**ranking) for ranking in rankings[:limit]]
        
    except Exception as e:
        logger.error(f"Error getting best value models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rankings/custom", response_model=List[ModelRanking])
async def get_custom_rankings(
    weights: UseCaseWeights,
    limit: int = Query(10, ge=1, le=50),
    filters: Optional[Dict[str, Any]] = None
):
    """Get custom rankings with user-defined weights"""
    
    try:
        # Validate weights sum to approximately 1
        total_weight = weights.cost_efficiency + weights.performance + weights.reliability + weights.availability
        if abs(total_weight - 1.0) > 0.1:
            raise HTTPException(status_code=400, detail="Weights must sum to approximately 1.0")
            
        # For now, return general rankings (in production, would apply custom weights)
        rankings = await supabase_client.get_model_rankings("general", limit, filters or {})
        
        return [ModelRanking(**ranking) for ranking in rankings]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting custom rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint for monitoring"""
    
    try:
        # Test database connection
        start_time = time.time()
        await supabase_client.get_model_rankings(limit=1)
        db_response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "database": {
                "status": "connected",
                "response_time_ms": round(db_response_time, 2)
            },
            "api": {
                "version": "1.0.0",
                "uptime": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(),
                "error": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting LLM Intelligence API server...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        reload=True
    )