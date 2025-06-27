-- LLM Data Intelligence Schema for Supabase
-- ==================================================
-- This schema supports comprehensive LLM model data collection,
-- multi-provider pricing intelligence, benchmark tracking,
-- and real-time ranking for cost/performance optimization.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===================================
-- CORE TABLES
-- ===================================

-- Models table - Core LLM model information
-- Stores fundamental model data with capabilities
CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL,
    model_family TEXT,
    context_window INTEGER,
    max_tokens INTEGER,
    input_token_limit INTEGER,
    output_token_limit INTEGER,
    
    -- Model capabilities as JSONB for flexibility
    capabilities JSONB DEFAULT '{}',
    
    -- Metadata
    model_type TEXT, -- chat, completion, embedding, etc.
    release_date DATE,
    deprecation_date DATE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT models_name_provider_unique UNIQUE(name, provider)
);

-- Provider pricing table - Multi-provider cost tracking
-- Supports OpenRouter's multiple providers per model
CREATE TABLE IF NOT EXISTS provider_pricing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    
    -- Provider information
    provider_name TEXT NOT NULL,
    provider_id TEXT, -- OpenRouter provider ID
    
    -- Pricing (per million tokens)
    input_price_per_million DECIMAL(12,8),
    output_price_per_million DECIMAL(12,8),
    batch_input_price_per_million DECIMAL(12,8),
    batch_output_price_per_million DECIMAL(12,8),
    
    -- Free tier information
    is_free_tier BOOLEAN DEFAULT FALSE,
    free_tier_quota INTEGER, -- requests per day/month
    
    -- Rate limits as JSONB
    rate_limits JSONB DEFAULT '{}',
    
    -- Provider-specific metadata
    provider_metadata JSONB DEFAULT '{}',
    
    -- Status tracking
    is_active BOOLEAN DEFAULT TRUE,
    last_verified TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique provider per model
    CONSTRAINT provider_pricing_unique UNIQUE(model_id, provider_name, provider_id)
);

-- Benchmark scores table - Performance tracking
-- Stores scores from various benchmarks (HumanEval, MMLU, GSM8K, etc.)
CREATE TABLE IF NOT EXISTS benchmark_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    
    -- Benchmark information
    benchmark_name TEXT NOT NULL,
    benchmark_category TEXT, -- coding, reasoning, math, general
    metric_type TEXT NOT NULL, -- pass@1, accuracy, bleu, etc.
    
    -- Score data
    score DECIMAL(8,6) NOT NULL,
    max_possible_score DECIMAL(8,6),
    normalized_score DECIMAL(5,4), -- 0-1 normalized
    
    -- Test metadata
    test_date DATE NOT NULL,
    test_version TEXT,
    sample_size INTEGER,
    
    -- Source information
    source_url TEXT,
    source_paper TEXT,
    source_organization TEXT,
    
    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verification_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique benchmark per model per test date
    CONSTRAINT benchmark_scores_unique UNIQUE(model_id, benchmark_name, metric_type, test_date)
);

-- Model usage statistics - Track actual usage and performance
CREATE TABLE IF NOT EXISTS model_usage_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    provider_name TEXT NOT NULL,
    
    -- Usage statistics
    total_requests INTEGER DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_cost DECIMAL(12,4) DEFAULT 0,
    
    -- Performance metrics
    avg_response_time_ms INTEGER,
    success_rate DECIMAL(5,4), -- 0-1
    error_count INTEGER DEFAULT 0,
    
    -- Time period
    date DATE NOT NULL,
    hour INTEGER, -- 0-23 for hourly stats
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique stats per model/provider/date/hour
    CONSTRAINT usage_stats_unique UNIQUE(model_id, provider_name, date, hour)
);

-- ===================================
-- MATERIALIZED VIEWS
-- ===================================

-- Model rankings - Comprehensive ranking based on multiple factors
CREATE MATERIALIZED VIEW IF NOT EXISTS model_rankings AS
SELECT 
    m.id,
    m.name,
    m.provider,
    m.model_family,
    m.context_window,
    
    -- Cost metrics
    MIN(pp.input_price_per_million) as min_input_cost,
    AVG(pp.input_price_per_million) as avg_input_cost,
    MIN(pp.output_price_per_million) as min_output_cost,
    AVG(pp.output_price_per_million) as avg_output_cost,
    
    -- Provider information
    COUNT(DISTINCT pp.provider_name) as provider_count,
    BOOL_OR(pp.is_free_tier) as has_free_tier,
    
    -- Benchmark metrics
    AVG(CASE WHEN bs.benchmark_category = 'coding' THEN bs.normalized_score END) as coding_score,
    AVG(CASE WHEN bs.benchmark_category = 'reasoning' THEN bs.normalized_score END) as reasoning_score,
    AVG(CASE WHEN bs.benchmark_category = 'math' THEN bs.normalized_score END) as math_score,
    AVG(CASE WHEN bs.benchmark_category = 'general' THEN bs.normalized_score END) as general_score,
    AVG(bs.normalized_score) as overall_benchmark_score,
    
    -- Usage metrics
    COALESCE(SUM(us.total_requests), 0) as total_usage,
    COALESCE(AVG(us.avg_response_time_ms), 0) as avg_response_time,
    COALESCE(AVG(us.success_rate), 1.0) as avg_success_rate,
    
    -- Calculated ranking scores (0-1)
    CASE 
        WHEN MIN(pp.input_price_per_million) IS NULL THEN 0
        ELSE 1.0 / (1.0 + MIN(pp.input_price_per_million) / 10.0)
    END as cost_efficiency_score,
    
    COALESCE(AVG(bs.normalized_score), 0) as performance_score,
    
    -- Overall composite score
    (
        CASE 
            WHEN MIN(pp.input_price_per_million) IS NULL THEN 0
            ELSE 1.0 / (1.0 + MIN(pp.input_price_per_million) / 10.0)
        END * 0.4 +
        COALESCE(AVG(bs.normalized_score), 0) * 0.4 +
        COALESCE(AVG(us.success_rate), 1.0) * 0.2
    ) as composite_score,
    
    -- Timestamps
    NOW() as last_updated
    
FROM models m
LEFT JOIN provider_pricing pp ON m.id = pp.model_id AND pp.is_active = TRUE
LEFT JOIN benchmark_scores bs ON m.id = bs.model_id AND bs.is_verified = TRUE
LEFT JOIN model_usage_stats us ON m.id = us.model_id 
    AND us.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY m.id, m.name, m.provider, m.model_family, m.context_window;

-- Create indexes for performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_model_rankings_id ON model_rankings(id);
CREATE INDEX IF NOT EXISTS idx_model_rankings_composite_score ON model_rankings(composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_model_rankings_cost ON model_rankings(min_input_cost ASC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_model_rankings_performance ON model_rankings(performance_score DESC);

-- ===================================
-- INDEXES
-- ===================================

-- Models table indexes
CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);
CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider);
CREATE INDEX IF NOT EXISTS idx_models_family ON models(model_family);
CREATE INDEX IF NOT EXISTS idx_models_capabilities ON models USING GIN(capabilities);

-- Provider pricing indexes
CREATE INDEX IF NOT EXISTS idx_provider_pricing_model_id ON provider_pricing(model_id);
CREATE INDEX IF NOT EXISTS idx_provider_pricing_provider ON provider_pricing(provider_name);
CREATE INDEX IF NOT EXISTS idx_provider_pricing_cost ON provider_pricing(input_price_per_million, output_price_per_million);
CREATE INDEX IF NOT EXISTS idx_provider_pricing_free_tier ON provider_pricing(is_free_tier) WHERE is_free_tier = TRUE;
CREATE INDEX IF NOT EXISTS idx_provider_pricing_active ON provider_pricing(is_active) WHERE is_active = TRUE;

-- Benchmark scores indexes  
CREATE INDEX IF NOT EXISTS idx_benchmark_scores_model_id ON benchmark_scores(model_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_scores_benchmark ON benchmark_scores(benchmark_name);
CREATE INDEX IF NOT EXISTS idx_benchmark_scores_category ON benchmark_scores(benchmark_category);
CREATE INDEX IF NOT EXISTS idx_benchmark_scores_score ON benchmark_scores(normalized_score DESC);
CREATE INDEX IF NOT EXISTS idx_benchmark_scores_date ON benchmark_scores(test_date DESC);

-- Usage stats indexes
CREATE INDEX IF NOT EXISTS idx_usage_stats_model_id ON model_usage_stats(model_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_provider ON model_usage_stats(provider_name);
CREATE INDEX IF NOT EXISTS idx_usage_stats_date ON model_usage_stats(date DESC);

-- ===================================
-- FUNCTIONS
-- ===================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_models_updated_at 
    BEFORE UPDATE ON models 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_pricing_updated_at 
    BEFORE UPDATE ON provider_pricing 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_benchmark_scores_updated_at 
    BEFORE UPDATE ON benchmark_scores 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to refresh model rankings
CREATE OR REPLACE FUNCTION refresh_model_rankings()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY model_rankings;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-refresh rankings on data changes
CREATE TRIGGER refresh_rankings_on_pricing_change
    AFTER INSERT OR UPDATE OR DELETE ON provider_pricing
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_model_rankings();

CREATE TRIGGER refresh_rankings_on_benchmark_change
    AFTER INSERT OR UPDATE OR DELETE ON benchmark_scores
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_model_rankings();

CREATE TRIGGER refresh_rankings_on_usage_change
    AFTER INSERT OR UPDATE OR DELETE ON model_usage_stats
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_model_rankings();

-- ===================================
-- SAMPLE DATA TYPES AND EXAMPLES
-- ===================================

-- Example capabilities JSONB structure:
-- {
--   "supports_function_calling": true,
--   "supports_vision": true,
--   "supports_code_execution": false,
--   "supports_web_search": false,
--   "max_function_calls": 10,
--   "supported_languages": ["en", "es", "fr"],
--   "output_formats": ["text", "json", "code"]
-- }

-- Example rate_limits JSONB structure:
-- {
--   "requests_per_minute": 60,
--   "requests_per_day": 1000,
--   "tokens_per_minute": 100000,
--   "concurrent_requests": 5,
--   "burst_limit": 10,
--   "reset_time": "daily"
-- }

-- Example provider_metadata JSONB structure:
-- {
--   "region": "us-east-1",
--   "availability_zones": ["us-east-1a", "us-east-1b"],
--   "sla_uptime": 99.9,
--   "support_tier": "enterprise",
--   "custom_domains": true
-- }