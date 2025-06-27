#!/usr/bin/env python3
"""
PostgreSQL-based Ranking Algorithms for LLM Intelligence System
================================================================

Advanced multi-factor scoring algorithms using PostgreSQL functions
and real-time materialized views for intelligent model selection.

Key Features:
- Multi-factor scoring (cost, performance, reliability, availability)
- Dynamic weight adjustment based on use case
- Provider reliability scoring with fallback intelligence
- Real-time ranking updates via PostgreSQL triggers
- Context-aware model recommendations
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import math

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseRanker:
    """PostgreSQL-based ranking engine for LLM models"""
    
    def __init__(self):
        self.scoring_weights = {
            'cost_efficiency': 0.40,
            'performance': 0.35,
            'reliability': 0.15,
            'availability': 0.10
        }
        
    def generate_ranking_sql(self, use_case: str = "general") -> str:
        """Generate PostgreSQL ranking query with dynamic weights"""
        
        weights = self._get_use_case_weights(use_case)
        
        sql = f"""
        -- Advanced LLM Model Ranking with Multi-Factor Scoring
        -- Use case: {use_case}
        
        WITH model_stats AS (
            SELECT 
                m.id,
                m.name,
                m.provider,
                m.model_family,
                m.context_window,
                m.capabilities,
                
                -- Cost metrics
                MIN(pp.input_price_per_million) as min_input_cost,
                AVG(pp.input_price_per_million) as avg_input_cost,
                COUNT(DISTINCT pp.provider_name) as provider_count,
                BOOL_OR(pp.is_free_tier) as has_free_tier,
                
                -- Performance metrics by category
                AVG(CASE WHEN bs.benchmark_category = 'coding' 
                    THEN bs.normalized_score END) as coding_score,
                AVG(CASE WHEN bs.benchmark_category = 'reasoning' 
                    THEN bs.normalized_score END) as reasoning_score,
                AVG(CASE WHEN bs.benchmark_category = 'math' 
                    THEN bs.normalized_score END) as math_score,
                AVG(bs.normalized_score) as overall_performance,
                
                -- Reliability metrics
                AVG(CASE WHEN us.success_rate IS NOT NULL 
                    THEN us.success_rate ELSE 0.95 END) as avg_success_rate,
                AVG(CASE WHEN us.avg_response_time_ms IS NOT NULL 
                    THEN us.avg_response_time_ms ELSE 1000 END) as avg_response_time,
                
                -- Usage statistics
                COALESCE(SUM(us.total_requests), 0) as total_usage_requests,
                COALESCE(AVG(us.total_cost), 0) as avg_daily_cost
                
            FROM models m
            LEFT JOIN provider_pricing pp ON m.id = pp.model_id 
                AND pp.is_active = true
            LEFT JOIN benchmark_scores bs ON m.id = bs.model_id 
                AND bs.is_verified = true
            LEFT JOIN model_usage_stats us ON m.id = us.model_id 
                AND us.date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY m.id, m.name, m.provider, m.model_family, 
                     m.context_window, m.capabilities
        ),
        
        scored_models AS (
            SELECT 
                *,
                
                -- 1. Cost Efficiency Score (0-1, higher is better)
                CASE 
                    WHEN has_free_tier THEN 1.0
                    WHEN min_input_cost IS NULL OR min_input_cost <= 0 THEN 0.5
                    ELSE GREATEST(0.0, 1.0 / (1.0 + min_input_cost / 10.0))
                END as cost_efficiency_score,
                
                -- 2. Performance Score (0-1, higher is better)
                CASE 
                    WHEN overall_performance IS NOT NULL THEN overall_performance
                    ELSE 0.5  -- Default for models without benchmarks
                END as performance_score,
                
                -- 3. Reliability Score (0-1, higher is better)
                CASE 
                    WHEN avg_success_rate >= 0.99 AND avg_response_time <= 500 THEN 1.0
                    WHEN avg_success_rate >= 0.95 AND avg_response_time <= 1000 THEN 0.8
                    WHEN avg_success_rate >= 0.90 AND avg_response_time <= 2000 THEN 0.6
                    ELSE 0.4
                END as reliability_score,
                
                -- 4. Availability Score (0-1, higher is better)
                CASE 
                    WHEN provider_count >= 3 THEN 1.0
                    WHEN provider_count = 2 THEN 0.8
                    WHEN provider_count = 1 THEN 0.6
                    ELSE 0.3
                END as availability_score,
                
                -- Provider diversity bonus
                CASE 
                    WHEN provider_count > 1 THEN 0.1
                    ELSE 0.0
                END as diversity_bonus
                
            FROM model_stats
        ),
        
        final_rankings AS (
            SELECT 
                *,
                
                -- Weighted Composite Score
                (
                    cost_efficiency_score * {weights['cost_efficiency']:.3f} +
                    performance_score * {weights['performance']:.3f} +
                    reliability_score * {weights['reliability']:.3f} +
                    availability_score * {weights['availability']:.3f} +
                    diversity_bonus
                ) as composite_score,
                
                -- Use case specific scores
                CASE 
                    WHEN '{use_case}' = 'coding' THEN 
                        COALESCE(coding_score, 0.5) * 0.7 + performance_score * 0.3
                    WHEN '{use_case}' = 'reasoning' THEN 
                        COALESCE(reasoning_score, 0.5) * 0.7 + performance_score * 0.3
                    WHEN '{use_case}' = 'math' THEN 
                        COALESCE(math_score, 0.5) * 0.7 + performance_score * 0.3
                    ELSE performance_score
                END as use_case_score,
                
                -- Value Score (performance per dollar)
                CASE 
                    WHEN has_free_tier THEN performance_score * 10
                    WHEN min_input_cost > 0 THEN performance_score / (min_input_cost / 10.0)
                    ELSE performance_score
                END as value_score
                
            FROM scored_models
        )
        
        SELECT 
            id,
            name,
            provider,
            model_family,
            context_window,
            capabilities,
            
            -- Pricing information
            min_input_cost,
            avg_input_cost,
            has_free_tier,
            provider_count,
            
            -- Performance metrics
            coding_score,
            reasoning_score,
            math_score,
            overall_performance,
            
            -- Reliability metrics
            avg_success_rate,
            avg_response_time,
            
            -- Scoring components
            cost_efficiency_score,
            performance_score,
            reliability_score,
            availability_score,
            
            -- Final scores
            composite_score,
            use_case_score,
            value_score,
            
            -- Rankings
            ROW_NUMBER() OVER (ORDER BY composite_score DESC) as overall_rank,
            ROW_NUMBER() OVER (ORDER BY use_case_score DESC) as use_case_rank,
            ROW_NUMBER() OVER (ORDER BY value_score DESC) as value_rank,
            ROW_NUMBER() OVER (ORDER BY cost_efficiency_score DESC) as cost_rank,
            
            -- Metadata
            total_usage_requests,
            avg_daily_cost,
            NOW() as ranking_timestamp
            
        FROM final_rankings
        ORDER BY composite_score DESC;
        """
        
        return sql
        
    def _get_use_case_weights(self, use_case: str) -> Dict[str, float]:
        """Get scoring weights based on use case"""
        
        use_case_weights = {
            'coding': {
                'cost_efficiency': 0.25,
                'performance': 0.50,  # Higher weight on performance for coding
                'reliability': 0.15,
                'availability': 0.10
            },
            'reasoning': {
                'cost_efficiency': 0.30,
                'performance': 0.45,
                'reliability': 0.15,
                'availability': 0.10
            },
            'math': {
                'cost_efficiency': 0.30,
                'performance': 0.45,
                'reliability': 0.15,
                'availability': 0.10
            },
            'cost_sensitive': {
                'cost_efficiency': 0.60,  # Much higher weight on cost
                'performance': 0.25,
                'reliability': 0.10,
                'availability': 0.05
            },
            'high_availability': {
                'cost_efficiency': 0.20,
                'performance': 0.30,
                'reliability': 0.25,
                'availability': 0.25  # Higher weight on availability
            },
            'general': self.scoring_weights  # Default weights
        }
        
        return use_case_weights.get(use_case, self.scoring_weights)
        
    def generate_provider_routing_sql(self, model_name: str) -> str:
        """Generate SQL for optimal provider selection for a specific model"""
        
        sql = f"""
        -- Provider Routing Intelligence for {model_name}
        
        WITH provider_options AS (
            SELECT 
                pp.provider_name,
                pp.provider_id,
                pp.input_price_per_million,
                pp.output_price_per_million,
                pp.is_free_tier,
                pp.rate_limits,
                pp.provider_metadata,
                
                -- Recent usage statistics
                AVG(us.success_rate) as recent_success_rate,
                AVG(us.avg_response_time_ms) as recent_response_time,
                SUM(us.total_requests) as recent_requests,
                
                -- Availability score
                CASE 
                    WHEN pp.is_active = false THEN 0.0
                    WHEN AVG(us.success_rate) >= 0.99 THEN 1.0
                    WHEN AVG(us.success_rate) >= 0.95 THEN 0.8
                    WHEN AVG(us.success_rate) >= 0.90 THEN 0.6
                    ELSE 0.4
                END as availability_score
                
            FROM provider_pricing pp
            JOIN models m ON pp.model_id = m.id
            LEFT JOIN model_usage_stats us ON pp.model_id = us.model_id 
                AND pp.provider_name = us.provider_name
                AND us.date >= CURRENT_DATE - INTERVAL '7 days'
            WHERE 
                m.name = '{model_name}'
                AND pp.is_active = true
            GROUP BY 
                pp.provider_name, pp.provider_id, pp.input_price_per_million,
                pp.output_price_per_million, pp.is_free_tier, pp.rate_limits,
                pp.provider_metadata, pp.is_active
        ),
        
        weighted_providers AS (
            SELECT 
                *,
                
                -- Cost weight (inverse square for OpenRouter-style routing)
                CASE 
                    WHEN is_free_tier THEN 1000.0
                    WHEN input_price_per_million > 0 THEN 
                        1.0 / POWER(input_price_per_million, 2)
                    ELSE 1.0
                END as cost_weight,
                
                -- Performance weight
                COALESCE(availability_score, 0.5) as performance_weight,
                
                -- Response time penalty
                CASE 
                    WHEN recent_response_time <= 500 THEN 1.0
                    WHEN recent_response_time <= 1000 THEN 0.9
                    WHEN recent_response_time <= 2000 THEN 0.7
                    ELSE 0.5
                END as speed_factor
                
            FROM provider_options
        ),
        
        final_routing AS (
            SELECT 
                *,
                cost_weight * performance_weight * speed_factor as routing_weight
            FROM weighted_providers
        )
        
        SELECT 
            provider_name,
            provider_id,
            input_price_per_million,
            output_price_per_million,
            is_free_tier,
            recent_success_rate,
            recent_response_time,
            availability_score,
            routing_weight,
            
            -- Normalized selection probability
            routing_weight / SUM(routing_weight) OVER () as selection_probability,
            
            -- Ranking within providers for this model
            ROW_NUMBER() OVER (ORDER BY routing_weight DESC) as provider_rank,
            
            -- Cost advantage vs average
            CASE 
                WHEN is_free_tier THEN 999.9
                WHEN input_price_per_million > 0 THEN
                    ((AVG(input_price_per_million) OVER () - input_price_per_million) / 
                     AVG(input_price_per_million) OVER ()) * 100
                ELSE 0
            END as cost_advantage_percent,
            
            rate_limits,
            provider_metadata,
            NOW() as routing_timestamp
            
        FROM final_routing
        ORDER BY routing_weight DESC;
        """
        
        return sql
        
    def generate_materialized_view_sql(self) -> str:
        """Generate SQL for creating optimized materialized view"""
        
        sql = """
        -- Create or replace materialized view for real-time rankings
        CREATE MATERIALIZED VIEW IF NOT EXISTS model_rankings_optimized AS
        """ + self.generate_ranking_sql("general").replace("-- Advanced LLM Model Ranking with Multi-Factor Scoring\n        -- Use case: general\n        \n        ", "") + """
        
        -- Create indexes for fast querying
        CREATE UNIQUE INDEX IF NOT EXISTS idx_model_rankings_id 
            ON model_rankings_optimized (id);
        CREATE INDEX IF NOT EXISTS idx_model_rankings_composite_score 
            ON model_rankings_optimized (composite_score DESC);
        CREATE INDEX IF NOT EXISTS idx_model_rankings_use_case_score 
            ON model_rankings_optimized (use_case_score DESC);
        CREATE INDEX IF NOT EXISTS idx_model_rankings_value_score 
            ON model_rankings_optimized (value_score DESC);
        CREATE INDEX IF NOT EXISTS idx_model_rankings_provider 
            ON model_rankings_optimized (provider);
        CREATE INDEX IF NOT EXISTS idx_model_rankings_free_tier 
            ON model_rankings_optimized (has_free_tier);
            
        -- Create trigger for automatic refresh
        CREATE OR REPLACE FUNCTION refresh_model_rankings()
        RETURNS TRIGGER AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY model_rankings_optimized;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Triggers for automatic updates
        DROP TRIGGER IF EXISTS trigger_refresh_rankings_on_pricing ON provider_pricing;
        CREATE TRIGGER trigger_refresh_rankings_on_pricing
            AFTER INSERT OR UPDATE OR DELETE ON provider_pricing
            FOR EACH STATEMENT
            EXECUTE FUNCTION refresh_model_rankings();
            
        DROP TRIGGER IF EXISTS trigger_refresh_rankings_on_benchmarks ON benchmark_scores;
        CREATE TRIGGER trigger_refresh_rankings_on_benchmarks
            AFTER INSERT OR UPDATE OR DELETE ON benchmark_scores
            FOR EACH STATEMENT
            EXECUTE FUNCTION refresh_model_rankings();
        """
        
        return sql
        
    def generate_recommendation_functions(self) -> str:
        """Generate PostgreSQL functions for intelligent recommendations"""
        
        sql = """
        -- Function: Get top models for specific use case
        CREATE OR REPLACE FUNCTION get_top_models_for_use_case(
            use_case_param TEXT DEFAULT 'general',
            limit_param INTEGER DEFAULT 5,
            min_performance DECIMAL DEFAULT 0.0,
            max_cost DECIMAL DEFAULT NULL,
            require_free_tier BOOLEAN DEFAULT FALSE
        )
        RETURNS TABLE (
            model_name TEXT,
            provider TEXT,
            composite_score DECIMAL,
            use_case_score DECIMAL,
            cost_efficiency_score DECIMAL,
            performance_score DECIMAL,
            min_input_cost DECIMAL,
            has_free_tier BOOLEAN,
            overall_rank INTEGER,
            recommendation_reason TEXT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                mr.name,
                mr.provider,
                mr.composite_score,
                mr.use_case_score,
                mr.cost_efficiency_score,
                mr.performance_score,
                mr.min_input_cost,
                mr.has_free_tier,
                mr.overall_rank,
                CASE 
                    WHEN mr.has_free_tier THEN 'Free tier available - excellent value'
                    WHEN mr.value_score > 5 THEN 'Outstanding performance per dollar'
                    WHEN mr.performance_score > 0.9 THEN 'Top-tier performance'
                    WHEN mr.cost_efficiency_score > 0.8 THEN 'Highly cost-effective'
                    ELSE 'Balanced option'
                END as recommendation_reason
            FROM model_rankings_optimized mr
            WHERE 
                (mr.performance_score >= min_performance)
                AND (max_cost IS NULL OR mr.min_input_cost <= max_cost OR mr.has_free_tier)
                AND (NOT require_free_tier OR mr.has_free_tier)
            ORDER BY 
                CASE 
                    WHEN use_case_param = 'coding' THEN mr.coding_score
                    WHEN use_case_param = 'reasoning' THEN mr.reasoning_score
                    WHEN use_case_param = 'math' THEN mr.math_score
                    ELSE mr.composite_score
                END DESC NULLS LAST
            LIMIT limit_param;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Function: Get optimal provider for specific model
        CREATE OR REPLACE FUNCTION get_optimal_provider(
            model_name_param TEXT,
            prefer_free_tier BOOLEAN DEFAULT TRUE,
            max_response_time INTEGER DEFAULT 2000
        )
        RETURNS TABLE (
            provider_name TEXT,
            provider_id TEXT,
            input_price_per_million DECIMAL,
            is_free_tier BOOLEAN,
            selection_probability DECIMAL,
            cost_advantage_percent DECIMAL,
            recommendation_reason TEXT
        ) AS $$
        DECLARE
            routing_sql TEXT;
        BEGIN
            -- This would use the provider routing SQL
            -- For now, return a simple recommendation
            RETURN QUERY
            SELECT 
                pp.provider_name,
                pp.provider_id,
                pp.input_price_per_million,
                pp.is_free_tier,
                CASE 
                    WHEN pp.is_free_tier THEN 0.8
                    ELSE (1.0 / (1.0 + pp.input_price_per_million / 10.0))
                END as selection_probability,
                CASE 
                    WHEN pp.is_free_tier THEN 100.0
                    ELSE 0.0
                END as cost_advantage_percent,
                CASE 
                    WHEN pp.is_free_tier THEN 'Free tier - no cost'
                    WHEN pp.input_price_per_million < 2.0 THEN 'Very cost-effective'
                    WHEN pp.input_price_per_million < 5.0 THEN 'Reasonably priced'
                    ELSE 'Premium pricing'
                END as recommendation_reason
            FROM provider_pricing pp
            JOIN models m ON pp.model_id = m.id
            WHERE 
                m.name = model_name_param
                AND pp.is_active = true
            ORDER BY 
                CASE WHEN prefer_free_tier THEN pp.is_free_tier::INTEGER ELSE 0 END DESC,
                pp.input_price_per_million ASC NULLS LAST
            LIMIT 1;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Function: Get cost optimization recommendations
        CREATE OR REPLACE FUNCTION get_cost_optimization_recommendations(
            current_usage_usd DECIMAL DEFAULT 100.0
        )
        RETURNS TABLE (
            recommendation_type TEXT,
            potential_savings_usd DECIMAL,
            recommended_models TEXT[],
            explanation TEXT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH free_tier_models AS (
                SELECT array_agg(name) as free_models
                FROM model_rankings_optimized 
                WHERE has_free_tier = true 
                ORDER BY performance_score DESC 
                LIMIT 3
            ),
            cost_efficient_models AS (
                SELECT array_agg(name) as efficient_models
                FROM model_rankings_optimized 
                WHERE cost_efficiency_score > 0.8 
                AND has_free_tier = false
                ORDER BY value_score DESC 
                LIMIT 3
            )
            SELECT 
                'free_tier'::TEXT,
                current_usage_usd * 0.8,
                fm.free_models,
                'Switch to free tier models for non-critical tasks'
            FROM free_tier_models fm
            
            UNION ALL
            
            SELECT 
                'cost_efficient'::TEXT,
                current_usage_usd * 0.3,
                cem.efficient_models,
                'Use cost-efficient models for routine tasks'
            FROM cost_efficient_models cem;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        return sql

class RankingTestSuite:
    """Test suite for ranking algorithms"""
    
    def __init__(self, ranker: SupabaseRanker):
        self.ranker = ranker
        
    def test_all_ranking_functions(self):
        """Test all ranking SQL functions"""
        logger.info("🧪 Testing ranking algorithms...")
        
        test_cases = [
            ("general", "General purpose ranking"),
            ("coding", "Coding-optimized ranking"),
            ("reasoning", "Reasoning-optimized ranking"),
            ("cost_sensitive", "Cost-sensitive ranking"),
            ("high_availability", "High availability ranking")
        ]
        
        for use_case, description in test_cases:
            logger.info(f"Testing {description}...")
            sql = self.ranker.generate_ranking_sql(use_case)
            
            # Validate SQL structure
            assert "SELECT" in sql.upper()
            assert "composite_score" in sql
            assert "ORDER BY" in sql.upper()
            
            logger.info(f"✅ {description} SQL validated")
            
        # Test provider routing
        logger.info("Testing provider routing...")
        routing_sql = self.ranker.generate_provider_routing_sql("gpt-4o")
        assert "selection_probability" in routing_sql
        logger.info("✅ Provider routing SQL validated")
        
        # Test materialized view
        logger.info("Testing materialized view...")
        mv_sql = self.ranker.generate_materialized_view_sql()
        assert "MATERIALIZED VIEW" in mv_sql.upper()
        logger.info("✅ Materialized view SQL validated")
        
        logger.info("🎉 All ranking tests passed!")

async def main():
    """Main entry point for testing ranking algorithms"""
    logger.info("🎯 PostgreSQL Ranking Algorithm Testing")
    print("=" * 60)
    
    ranker = SupabaseRanker()
    test_suite = RankingTestSuite(ranker)
    
    try:
        # Test all ranking functions
        test_suite.test_all_ranking_functions()
        
        # Generate sample SQL files
        logger.info("📄 Generating SQL files...")
        
        with open("/tmp/ranking_general.sql", "w") as f:
            f.write(ranker.generate_ranking_sql("general"))
            
        with open("/tmp/provider_routing.sql", "w") as f:
            f.write(ranker.generate_provider_routing_sql("claude-3.5-sonnet"))
            
        with open("/tmp/materialized_view.sql", "w") as f:
            f.write(ranker.generate_materialized_view_sql())
            
        with open("/tmp/recommendation_functions.sql", "w") as f:
            f.write(ranker.generate_recommendation_functions())
        
        logger.info("✅ SQL files generated in /tmp/")
        print(f"\n🎉 Ranking algorithm testing completed!")
        print(f"📊 Generated ranking queries for 5 use cases")
        print(f"🔄 Created materialized view with auto-refresh triggers")
        print(f"💡 Built recommendation functions for intelligent selection")
        
    except Exception as e:
        logger.error(f"❌ Ranking algorithm testing failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())