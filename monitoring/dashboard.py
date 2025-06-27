#!/usr/bin/env python3
"""
Web Dashboard for Claude Code Multi-Model Cost Monitoring
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Create dashboard app
app = FastAPI(title="Claude Code Multi-Model Dashboard")

# Setup templates directory
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))

class DashboardServer:
    """
    Web dashboard for monitoring costs and usage
    """
    
    def __init__(self):
        self.setup_routes()
        
    def setup_routes(self):
        """Setup web routes"""
        
        @app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page"""
            return templates.TemplateResponse("dashboard.html", {"request": request})
        
        @app.get("/api/stats")
        async def get_stats():
            """Get current statistics"""
            try:
                from cost_tracker import CostTracker
                tracker = CostTracker()
                stats = tracker.get_usage_stats(24)
                tracker.close()
                return JSONResponse(stats)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @app.get("/api/providers")
        async def get_provider_stats():
            """Get provider-specific statistics"""
            try:
                from cost_tracker import CostTracker
                tracker = CostTracker()
                stats = tracker.get_usage_stats(24)
                tracker.close()
                
                providers = []
                for provider, data in stats.get("provider_stats", {}).items():
                    providers.append({
                        "name": provider,
                        "requests": data.get("total_requests", 0),
                        "success_rate": data.get("success_rate", 0),
                        "cost": data.get("total_cost", 0),
                        "avg_response_time": data.get("avg_response_time", 0),
                        "tokens": data.get("total_tokens", 0)
                    })
                
                return JSONResponse({"providers": providers})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @app.get("/api/costs/hourly")
        async def get_hourly_costs():
            """Get hourly cost breakdown"""
            try:
                from cost_tracker import CostTracker
                tracker = CostTracker()
                stats = tracker.get_usage_stats(24)
                tracker.close()
                
                return JSONResponse({"hourly_costs": stats.get("hourly_costs", [])})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @app.get("/api/alerts")
        async def get_alerts():
            """Get recent alerts"""
            try:
                from cost_tracker import CostTracker
                tracker = CostTracker()
                stats = tracker.get_usage_stats(24)
                tracker.close()
                
                return JSONResponse({"alerts": stats.get("recent_alerts", [])})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @app.get("/api/report")
        async def get_integrated_report():
            """Get integrated cost report"""
            try:
                from claude_costs_integration import ClaudeCodeCostsIntegration
                integration = ClaudeCodeCostsIntegration()
                report = integration.generate_integrated_report()
                return JSONResponse(report)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

    def create_dashboard_template(self):
        """Create the main dashboard HTML template"""
        template_path = templates_dir / "dashboard.html"
        
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Multi-Model Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .metric-card {
            @apply bg-white p-6 rounded-lg shadow-md border border-gray-200;
        }
        .metric-value {
            @apply text-3xl font-bold;
        }
        .metric-label {
            @apply text-sm text-gray-600 uppercase tracking-wide;
        }
        .status-good { @apply text-green-600; }
        .status-warning { @apply text-yellow-600; }
        .status-error { @apply text-red-600; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-4xl font-bold text-gray-900 mb-2">Claude Code Multi-Model Dashboard</h1>
            <p class="text-gray-600">Real-time monitoring of costs, usage, and performance across all providers</p>
            <div class="mt-4">
                <span id="lastUpdate" class="text-sm text-gray-500">Last updated: Loading...</span>
                <button onclick="refreshData()" class="ml-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    Refresh
                </button>
            </div>
        </div>

        <!-- Key Metrics -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="metric-card">
                <div class="metric-label">Total Cost (24h)</div>
                <div id="totalCost" class="metric-value text-blue-600">$0.00</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Requests</div>
                <div id="totalRequests" class="metric-value text-green-600">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div id="successRate" class="metric-value text-purple-600">0%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Alerts</div>
                <div id="activeAlerts" class="metric-value text-red-600">0</div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold mb-4">Hourly Costs</h3>
                <canvas id="costChart" width="400" height="200"></canvas>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold mb-4">Provider Distribution</h3>
                <canvas id="providerChart" width="400" height="200"></canvas>
            </div>
        </div>

        <!-- Provider Stats Table -->
        <div class="bg-white rounded-lg shadow-md mb-8">
            <div class="p-6 border-b border-gray-200">
                <h3 class="text-lg font-semibold">Provider Statistics</h3>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Provider</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Requests</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Success Rate</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Response Time</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tokens</th>
                        </tr>
                    </thead>
                    <tbody id="providerTableBody" class="bg-white divide-y divide-gray-200">
                        <tr>
                            <td colspan="6" class="px-6 py-4 text-center text-gray-500">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Alerts Panel -->
        <div class="bg-white rounded-lg shadow-md">
            <div class="p-6 border-b border-gray-200">
                <h3 class="text-lg font-semibold">Recent Alerts</h3>
            </div>
            <div id="alertsContainer" class="p-6">
                <p class="text-gray-500">Loading alerts...</p>
            </div>
        </div>
    </div>

    <script>
        let costChart = null;
        let providerChart = null;

        // Initialize charts
        function initCharts() {
            // Cost chart
            const costCtx = document.getElementById('costChart').getContext('2d');
            costChart = new Chart(costCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Hourly Cost ($)',
                        data: [],
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(4);
                                }
                            }
                        }
                    }
                }
            });

            // Provider chart
            const providerCtx = document.getElementById('providerChart').getContext('2d');
            providerChart = new Chart(providerCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#F97316'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        // Fetch and update data
        async function refreshData() {
            try {
                document.getElementById('lastUpdate').textContent = 'Updating...';
                
                // Fetch stats
                const statsResponse = await fetch('/api/stats');
                const stats = await statsResponse.json();
                
                // Update key metrics
                document.getElementById('totalCost').textContent = '$' + (stats.total_cost || 0).toFixed(4);
                document.getElementById('totalRequests').textContent = stats.total_requests || 0;
                
                // Calculate overall success rate
                let totalRequests = 0;
                let successfulRequests = 0;
                Object.values(stats.provider_stats || {}).forEach(provider => {
                    totalRequests += provider.total_requests || 0;
                    successfulRequests += provider.successful_requests || 0;
                });
                const successRate = totalRequests > 0 ? (successfulRequests / totalRequests * 100) : 0;
                document.getElementById('successRate').textContent = successRate.toFixed(1) + '%';
                
                // Update charts
                await updateCharts();
                
                // Update provider table
                await updateProviderTable();
                
                // Update alerts
                await updateAlerts();
                
                document.getElementById('lastUpdate').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
                
            } catch (error) {
                console.error('Error refreshing data:', error);
                document.getElementById('lastUpdate').textContent = 'Error updating data';
            }
        }

        async function updateCharts() {
            try {
                // Update cost chart
                const costResponse = await fetch('/api/costs/hourly');
                const costData = await costResponse.json();
                
                if (costData.hourly_costs) {
                    const labels = costData.hourly_costs.map(item => {
                        const date = new Date(item.hour);
                        return date.getHours() + ':00';
                    }).reverse();
                    const costs = costData.hourly_costs.map(item => item.cost).reverse();
                    
                    costChart.data.labels = labels;
                    costChart.data.datasets[0].data = costs;
                    costChart.update();
                }

                // Update provider chart
                const providerResponse = await fetch('/api/providers');
                const providerData = await providerResponse.json();
                
                if (providerData.providers) {
                    const labels = providerData.providers.map(p => p.name);
                    const costs = providerData.providers.map(p => p.cost);
                    
                    providerChart.data.labels = labels;
                    providerChart.data.datasets[0].data = costs;
                    providerChart.update();
                }
                
            } catch (error) {
                console.error('Error updating charts:', error);
            }
        }

        async function updateProviderTable() {
            try {
                const response = await fetch('/api/providers');
                const data = await response.json();
                
                const tbody = document.getElementById('providerTableBody');
                
                if (data.providers && data.providers.length > 0) {
                    tbody.innerHTML = data.providers.map(provider => `
                        <tr>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${provider.name}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${provider.requests}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                <span class="${provider.success_rate > 0.9 ? 'status-good' : provider.success_rate > 0.7 ? 'status-warning' : 'status-error'}">
                                    ${(provider.success_rate * 100).toFixed(1)}%
                                </span>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">$${provider.cost.toFixed(4)}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${provider.avg_response_time.toFixed(2)}s</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${provider.tokens}</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No provider data available</td></tr>';
                }
                
            } catch (error) {
                console.error('Error updating provider table:', error);
            }
        }

        async function updateAlerts() {
            try {
                const response = await fetch('/api/alerts');
                const data = await response.json();
                
                const container = document.getElementById('alertsContainer');
                
                if (data.alerts && data.alerts.length > 0) {
                    document.getElementById('activeAlerts').textContent = data.alerts.length;
                    
                    container.innerHTML = data.alerts.map(alert => `
                        <div class="mb-4 p-4 border-l-4 border-red-400 bg-red-50">
                            <div class="flex">
                                <div class="ml-3">
                                    <h3 class="text-sm font-medium text-red-800">${alert.alert_type}</h3>
                                    <div class="mt-1 text-sm text-red-700">
                                        <p>${alert.message}</p>
                                        <p class="mt-1 text-xs">Provider: ${alert.provider} | Threshold: $${alert.threshold} | Actual: $${alert.actual_value.toFixed(4)}</p>
                                        <p class="mt-1 text-xs">Time: ${new Date(alert.timestamp).toLocaleString()}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    document.getElementById('activeAlerts').textContent = '0';
                    container.innerHTML = '<p class="text-gray-500">No recent alerts</p>';
                }
                
            } catch (error) {
                console.error('Error updating alerts:', error);
            }
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            refreshData();
            
            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);
        });
    </script>
</body>
</html>'''
        
        with open(template_path, 'w') as f:
            f.write(html_content)

def start_dashboard(host: str = "0.0.0.0", port: int = 8888):
    """Start the dashboard server"""
    dashboard = DashboardServer()
    dashboard.create_dashboard_template()
    
    print(f"🚀 Starting Claude Code Multi-Model Dashboard on http://{host}:{port}")
    print(f"📊 Dashboard available at: http://localhost:{port}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

def main():
    """Main function"""
    port = int(os.getenv('DASHBOARD_PORT', '8888'))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    
    start_dashboard(host, port)

if __name__ == "__main__":
    main()