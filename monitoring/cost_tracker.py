#!/usr/bin/env python3
"""
Comprehensive Cost Tracking and Monitoring System
for Claude Code Multi-Model Integration
"""

import os
import sys
import json
import sqlite3
import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from pathlib import Path
import time

import psutil
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

# Setup structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@dataclass
class UsageMetrics:
    """Usage metrics for a single request"""
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    response_time: float
    success: bool
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None

@dataclass
class ProviderCosts:
    """Cost structure for different providers"""
    vertex_ai_input: float = 0.000003  # Per token
    vertex_ai_output: float = 0.000015  # Per token
    github_models_input: float = 0.0000025  # Per token  
    github_models_output: float = 0.00001   # Per token
    openrouter_input: float = 0.000003      # Per token (varies by model)
    openrouter_output: float = 0.000015     # Per token (varies by model)

class CostTracker:
    """
    Comprehensive cost tracking system with multiple backends
    """
    
    def __init__(self, db_path: str = "/tmp/claude_multimodel_costs.db"):
        self.db_path = db_path
        self.setup_database()
        self.setup_prometheus_metrics()
        
        # Provider cost configurations
        self.provider_costs = ProviderCosts()
        
        # Rate limiting tracking
        self.rate_limits = {}
        self.request_counts = {}
        
        # Alert thresholds
        self.daily_cost_threshold = float(os.getenv('DAILY_COST_ALERT_THRESHOLD', '50.0'))
        self.hourly_cost_threshold = float(os.getenv('HOURLY_COST_ALERT_THRESHOLD', '10.0'))
        
        # Performance tracking
        self.performance_history = []
        
        logger.info("Cost tracker initialized", db_path=db_path)

    def setup_database(self):
        """Setup SQLite database for cost tracking"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                response_time REAL NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                request_id TEXT,
                user_id TEXT
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS provider_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                provider TEXT NOT NULL,
                total_requests INTEGER NOT NULL,
                successful_requests INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                avg_response_time REAL NOT NULL,
                rate_limit_hits INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS cost_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                threshold REAL NOT NULL,
                actual_value REAL NOT NULL,
                provider TEXT,
                message TEXT
            )
        ''')
        
        self.conn.commit()

    def setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        self.request_counter = Counter(
            'claude_multimodel_requests_total',
            'Total number of requests',
            ['provider', 'model', 'status']
        )
        
        self.cost_counter = Counter(
            'claude_multimodel_cost_total',
            'Total estimated cost',
            ['provider', 'model']
        )
        
        self.response_time_histogram = Histogram(
            'claude_multimodel_response_time_seconds',
            'Response time distribution',
            ['provider', 'model']
        )
        
        self.token_usage_counter = Counter(
            'claude_multimodel_tokens_total',
            'Total token usage',
            ['provider', 'model', 'type']  # type: input/output
        )
        
        self.rate_limit_gauge = Gauge(
            'claude_multimodel_rate_limits',
            'Current rate limit status',
            ['provider']
        )
        
        self.active_requests_gauge = Gauge(
            'claude_multimodel_active_requests',
            'Number of active requests',
            ['provider']
        )

    def log_usage(self, metrics: UsageMetrics):
        """Log usage metrics to database and Prometheus"""
        try:
            # Insert into database
            self.conn.execute('''
                INSERT INTO usage_metrics 
                (timestamp, provider, model, input_tokens, output_tokens, 
                 estimated_cost, response_time, success, error_message, request_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.provider,
                metrics.model,
                metrics.input_tokens,
                metrics.output_tokens,
                metrics.estimated_cost,
                metrics.response_time,
                metrics.success,
                metrics.error_message,
                metrics.request_id,
                metrics.user_id
            ))
            self.conn.commit()
            
            # Update Prometheus metrics
            status = 'success' if metrics.success else 'error'
            self.request_counter.labels(
                provider=metrics.provider,
                model=metrics.model,
                status=status
            ).inc()
            
            self.cost_counter.labels(
                provider=metrics.provider,
                model=metrics.model
            ).inc(metrics.estimated_cost)
            
            self.response_time_histogram.labels(
                provider=metrics.provider,
                model=metrics.model
            ).observe(metrics.response_time)
            
            self.token_usage_counter.labels(
                provider=metrics.provider,
                model=metrics.model,
                type='input'
            ).inc(metrics.input_tokens)
            
            self.token_usage_counter.labels(
                provider=metrics.provider,
                model=metrics.model,
                type='output'
            ).inc(metrics.output_tokens)
            
            # Check for cost alerts
            self.check_cost_alerts(metrics)
            
            logger.info(
                "Usage logged",
                provider=metrics.provider,
                model=metrics.model,
                cost=metrics.estimated_cost,
                tokens=metrics.input_tokens + metrics.output_tokens
            )
            
        except Exception as e:
            logger.error("Failed to log usage", error=str(e))

    def calculate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on provider and model"""
        try:
            if provider.lower() == 'vertex':
                return (input_tokens * self.provider_costs.vertex_ai_input + 
                       output_tokens * self.provider_costs.vertex_ai_output)
            elif provider.lower() == 'github':
                return (input_tokens * self.provider_costs.github_models_input + 
                       output_tokens * self.provider_costs.github_models_output)
            elif provider.lower() == 'openrouter':
                # OpenRouter costs vary by model - this is a simplified calculation
                if 'claude' in model.lower():
                    return (input_tokens * 0.000003 + output_tokens * 0.000015)
                elif 'gpt-4' in model.lower():
                    return (input_tokens * 0.00001 + output_tokens * 0.00003)
                elif 'gemini' in model.lower():
                    return (input_tokens * 0.00000125 + output_tokens * 0.00000375)
                else:
                    return (input_tokens * self.provider_costs.openrouter_input + 
                           output_tokens * self.provider_costs.openrouter_output)
            else:
                # Default calculation
                return (input_tokens + output_tokens) * 0.000001
                
        except Exception as e:
            logger.warning("Cost calculation failed", provider=provider, model=model, error=str(e))
            return 0.0

    def check_cost_alerts(self, metrics: UsageMetrics):
        """Check if cost thresholds are exceeded"""
        try:
            now = datetime.now(timezone.utc)
            
            # Check hourly costs
            hourly_cost = self.get_cost_for_period(
                provider=metrics.provider,
                start_time=now - timedelta(hours=1),
                end_time=now
            )
            
            if hourly_cost > self.hourly_cost_threshold:
                self.create_alert(
                    alert_type='hourly_cost_exceeded',
                    threshold=self.hourly_cost_threshold,
                    actual_value=hourly_cost,
                    provider=metrics.provider,
                    message=f"Hourly cost limit exceeded for {metrics.provider}: ${hourly_cost:.2f}"
                )
            
            # Check daily costs
            daily_cost = self.get_cost_for_period(
                provider=metrics.provider,
                start_time=now - timedelta(days=1),
                end_time=now
            )
            
            if daily_cost > self.daily_cost_threshold:
                self.create_alert(
                    alert_type='daily_cost_exceeded',
                    threshold=self.daily_cost_threshold,
                    actual_value=daily_cost,
                    provider=metrics.provider,
                    message=f"Daily cost limit exceeded for {metrics.provider}: ${daily_cost:.2f}"
                )
                
        except Exception as e:
            logger.error("Cost alert check failed", error=str(e))

    def create_alert(self, alert_type: str, threshold: float, actual_value: float, 
                    provider: str = None, message: str = None):
        """Create a cost alert"""
        try:
            self.conn.execute('''
                INSERT INTO cost_alerts 
                (timestamp, alert_type, threshold, actual_value, provider, message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(timezone.utc).isoformat(),
                alert_type,
                threshold,
                actual_value,
                provider,
                message
            ))
            self.conn.commit()
            
            logger.warning(
                "Cost alert triggered",
                alert_type=alert_type,
                threshold=threshold,
                actual_value=actual_value,
                provider=provider,
                message=message
            )
            
        except Exception as e:
            logger.error("Failed to create alert", error=str(e))

    def get_cost_for_period(self, provider: str = None, start_time: datetime = None, 
                           end_time: datetime = None) -> float:
        """Get total cost for a specific period and provider"""
        try:
            query = "SELECT SUM(estimated_cost) FROM usage_metrics WHERE 1=1"
            params = []
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            cursor = self.conn.execute(query, params)
            result = cursor.fetchone()[0]
            return result if result else 0.0
            
        except Exception as e:
            logger.error("Failed to get cost for period", error=str(e))
            return 0.0

    def get_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            
            # Get overall stats
            cursor = self.conn.execute('''
                SELECT 
                    provider,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
                    SUM(input_tokens + output_tokens) as total_tokens,
                    SUM(estimated_cost) as total_cost,
                    AVG(response_time) as avg_response_time
                FROM usage_metrics 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY provider
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            provider_stats = {}
            for row in cursor.fetchall():
                provider_stats[row[0]] = {
                    'total_requests': row[1],
                    'successful_requests': row[2],
                    'success_rate': row[2] / row[1] if row[1] > 0 else 0,
                    'total_tokens': row[3],
                    'total_cost': row[4],
                    'avg_response_time': row[5]
                }
            
            # Get recent alerts
            cursor = self.conn.execute('''
                SELECT alert_type, threshold, actual_value, provider, message, timestamp
                FROM cost_alerts 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (start_time.isoformat(),))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'alert_type': row[0],
                    'threshold': row[1],
                    'actual_value': row[2],
                    'provider': row[3],
                    'message': row[4],
                    'timestamp': row[5]
                })
            
            # Calculate cost trends
            hourly_costs = []
            for i in range(hours):
                hour_start = end_time - timedelta(hours=i+1)
                hour_end = end_time - timedelta(hours=i)
                cost = self.get_cost_for_period(start_time=hour_start, end_time=hour_end)
                hourly_costs.append({
                    'hour': hour_start.isoformat(),
                    'cost': cost
                })
            
            return {
                'period_hours': hours,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'provider_stats': provider_stats,
                'recent_alerts': alerts,
                'hourly_costs': hourly_costs,
                'total_cost': sum(stats['total_cost'] for stats in provider_stats.values()),
                'total_requests': sum(stats['total_requests'] for stats in provider_stats.values()),
                'total_tokens': sum(stats['total_tokens'] for stats in provider_stats.values())
            }
            
        except Exception as e:
            logger.error("Failed to get usage stats", error=str(e))
            return {}

    def log_rate_limit(self, provider: str, reset_time: datetime = None):
        """Log rate limit hit"""
        try:
            if provider not in self.rate_limits:
                self.rate_limits[provider] = {
                    'count': 0,
                    'last_hit': None,
                    'reset_time': None
                }
            
            self.rate_limits[provider]['count'] += 1
            self.rate_limits[provider]['last_hit'] = datetime.now(timezone.utc)
            if reset_time:
                self.rate_limits[provider]['reset_time'] = reset_time
            
            # Update Prometheus metric
            self.rate_limit_gauge.labels(provider=provider).set(1)
            
            logger.warning("Rate limit hit", provider=provider, reset_time=reset_time)
            
        except Exception as e:
            logger.error("Failed to log rate limit", error=str(e))

    def is_rate_limited(self, provider: str) -> bool:
        """Check if provider is currently rate limited"""
        try:
            if provider not in self.rate_limits:
                return False
            
            rate_limit_info = self.rate_limits[provider]
            if not rate_limit_info['reset_time']:
                return False
            
            now = datetime.now(timezone.utc)
            if now < rate_limit_info['reset_time']:
                return True
            else:
                # Rate limit has expired
                self.rate_limit_gauge.labels(provider=provider).set(0)
                return False
                
        except Exception as e:
            logger.error("Failed to check rate limit", error=str(e))
            return False

    def export_cost_report(self, format: str = 'json', hours: int = 24) -> str:
        """Export cost report in specified format"""
        try:
            stats = self.get_usage_stats(hours)
            
            if format.lower() == 'json':
                return json.dumps(stats, indent=2, default=str)
            elif format.lower() == 'csv':
                return self.convert_to_csv(stats)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error("Failed to export cost report", error=str(e))
            return ""

    def convert_to_csv(self, stats: Dict[str, Any]) -> str:
        """Convert stats to CSV format"""
        try:
            lines = []
            lines.append("Provider,Total Requests,Successful Requests,Success Rate,Total Tokens,Total Cost,Avg Response Time")
            
            for provider, data in stats.get('provider_stats', {}).items():
                lines.append(f"{provider},{data['total_requests']},{data['successful_requests']},{data['success_rate']:.3f},{data['total_tokens']},{data['total_cost']:.6f},{data['avg_response_time']:.3f}")
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error("Failed to convert to CSV", error=str(e))
            return ""

    def start_prometheus_server(self, port: int = 8090):
        """Start Prometheus metrics server"""
        try:
            start_http_server(port)
            logger.info("Prometheus metrics server started", port=port)
        except Exception as e:
            logger.error("Failed to start Prometheus server", error=str(e))

    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    """Main function for testing"""
    tracker = CostTracker()
    
    # Start Prometheus server
    tracker.start_prometheus_server()
    
    # Example usage
    metrics = UsageMetrics(
        timestamp=datetime.now(timezone.utc),
        provider='vertex',
        model='claude-sonnet-4',
        input_tokens=100,
        output_tokens=200,
        estimated_cost=0.001,
        response_time=1.5,
        success=True
    )
    
    tracker.log_usage(metrics)
    
    # Get stats
    stats = tracker.get_usage_stats(24)
    print("Usage Stats:", json.dumps(stats, indent=2, default=str))
    
    # Keep server running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down cost tracker")
        tracker.close()

if __name__ == "__main__":
    main()