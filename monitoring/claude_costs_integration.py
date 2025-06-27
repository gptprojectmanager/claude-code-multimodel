#!/usr/bin/env python3
"""
Claude Code Costs Integration
Integrates with philipp-spiess/claude-code-costs for native Claude Code cost analysis
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeCodeCostsIntegration:
    """
    Integration with claude-code-costs for comprehensive cost analysis
    """
    
    def __init__(self):
        self.claude_dir = Path.home() / ".claude"
        self.projects_dir = self.claude_dir / "projects"
        self.temp_dir = Path("/tmp/claude-multimodel-costs")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Check if claude-code-costs is available
        self.costs_tool_available = self.check_costs_tool()
        
    def check_costs_tool(self) -> bool:
        """Check if claude-code-costs is available"""
        try:
            result = subprocess.run(
                ["npx", "claude-code-costs", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def install_costs_tool(self) -> bool:
        """Install claude-code-costs if not available"""
        try:
            logger.info("Installing claude-code-costs...")
            result = subprocess.run(
                ["npm", "install", "-g", "claude-code-costs"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("claude-code-costs installed successfully")
                return True
            else:
                logger.error(f"Failed to install claude-code-costs: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing claude-code-costs: {e}")
            return False

    def get_native_costs(self) -> Optional[Dict[str, Any]]:
        """Get costs from native Claude Code conversations"""
        if not self.costs_tool_available and not self.install_costs_tool():
            logger.warning("claude-code-costs not available, skipping native cost analysis")
            return None
        
        try:
            # Run claude-code-costs with JSON output
            result = subprocess.run(
                ["npx", "claude-code-costs"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(Path.home())
            )
            
            if result.returncode != 0:
                logger.error(f"claude-code-costs failed: {result.stderr}")
                return None
            
            # Parse output to extract cost information
            output_lines = result.stdout.strip().split('\n')
            costs_data = self.parse_costs_output(output_lines)
            
            return costs_data
            
        except Exception as e:
            logger.error(f"Error running claude-code-costs: {e}")
            return None

    def parse_costs_output(self, output_lines: List[str]) -> Dict[str, Any]:
        """Parse claude-code-costs output"""
        costs_data = {
            "total_cost": 0.0,
            "conversations": [],
            "daily_breakdown": [],
            "projects": {},
            "summary": {}
        }
        
        try:
            # Look for cost information in output
            for line in output_lines:
                line = line.strip()
                
                # Extract total cost
                if "Total cost:" in line:
                    cost_str = line.split("Total cost:")[-1].strip()
                    # Extract numeric value (remove $ and other characters)
                    cost_value = ''.join(c for c in cost_str if c.isdigit() or c == '.')
                    if cost_value:
                        costs_data["total_cost"] = float(cost_value)
                
                # Extract conversation costs (this would need to be adapted based on actual output format)
                if "expensive conversations" in line.lower():
                    # Parse conversation data...
                    pass
            
            # If we have access to the projects directory, get more detailed info
            if self.projects_dir.exists():
                costs_data.update(self.analyze_claude_projects())
            
            return costs_data
            
        except Exception as e:
            logger.error(f"Error parsing costs output: {e}")
            return costs_data

    def analyze_claude_projects(self) -> Dict[str, Any]:
        """Analyze Claude Code projects directory for detailed costs"""
        analysis = {
            "projects": {},
            "total_conversations": 0,
            "total_messages": 0,
            "estimated_tokens": 0
        }
        
        try:
            if not self.projects_dir.exists():
                return analysis
            
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    project_analysis = self.analyze_project(project_dir)
                    analysis["projects"][project_dir.name] = project_analysis
                    analysis["total_conversations"] += project_analysis.get("conversations", 0)
                    analysis["total_messages"] += project_analysis.get("messages", 0)
                    analysis["estimated_tokens"] += project_analysis.get("estimated_tokens", 0)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing Claude projects: {e}")
            return analysis

    def analyze_project(self, project_dir: Path) -> Dict[str, Any]:
        """Analyze a single Claude Code project"""
        analysis = {
            "conversations": 0,
            "messages": 0,
            "estimated_tokens": 0,
            "last_activity": None,
            "cost_estimate": 0.0
        }
        
        try:
            # Look for conversation files
            conversation_files = list(project_dir.glob("**/*.json"))
            analysis["conversations"] = len(conversation_files)
            
            total_chars = 0
            latest_timestamp = None
            
            for conv_file in conversation_files:
                try:
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        conv_data = json.load(f)
                    
                    # Count messages and estimate tokens
                    if isinstance(conv_data, dict):
                        messages = conv_data.get("messages", [])
                        analysis["messages"] += len(messages)
                        
                        for message in messages:
                            content = message.get("content", "")
                            if isinstance(content, str):
                                total_chars += len(content)
                            elif isinstance(content, list):
                                for part in content:
                                    if isinstance(part, dict) and part.get("type") == "text":
                                        total_chars += len(part.get("text", ""))
                            
                            # Track latest activity
                            timestamp = message.get("timestamp")
                            if timestamp and (not latest_timestamp or timestamp > latest_timestamp):
                                latest_timestamp = timestamp
                
                except Exception as e:
                    logger.warning(f"Error reading conversation file {conv_file}: {e}")
                    continue
            
            # Estimate tokens (rough: 4 chars per token)
            analysis["estimated_tokens"] = total_chars // 4
            analysis["last_activity"] = latest_timestamp
            
            # Estimate cost (rough: $0.000003 per token for Claude models)
            analysis["cost_estimate"] = analysis["estimated_tokens"] * 0.000003
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing project {project_dir}: {e}")
            return analysis

    def generate_integrated_report(self) -> Dict[str, Any]:
        """Generate comprehensive cost report combining native and multi-model costs"""
        report = {
            "timestamp": json.dumps(os.times(), default=str),
            "native_claude_costs": {},
            "multimodel_costs": {},
            "combined_summary": {},
            "recommendations": []
        }
        
        try:
            # Get native Claude Code costs
            native_costs = self.get_native_costs()
            if native_costs:
                report["native_claude_costs"] = native_costs
            
            # Get multi-model costs from our cost tracker
            multimodel_costs = self.get_multimodel_costs()
            if multimodel_costs:
                report["multimodel_costs"] = multimodel_costs
            
            # Generate combined summary
            report["combined_summary"] = self.generate_combined_summary(
                native_costs, multimodel_costs
            )
            
            # Generate recommendations
            report["recommendations"] = self.generate_recommendations(
                native_costs, multimodel_costs
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating integrated report: {e}")
            return report

    def get_multimodel_costs(self) -> Dict[str, Any]:
        """Get costs from our multi-model system"""
        try:
            # Import our cost tracker
            sys.path.append(str(Path(__file__).parent))
            from cost_tracker import CostTracker
            
            tracker = CostTracker()
            stats = tracker.get_usage_stats(24 * 7)  # Last 7 days
            tracker.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting multimodel costs: {e}")
            return {}

    def generate_combined_summary(self, native_costs: Optional[Dict], 
                                 multimodel_costs: Optional[Dict]) -> Dict[str, Any]:
        """Generate combined cost summary"""
        summary = {
            "total_estimated_cost": 0.0,
            "native_cost": 0.0,
            "multimodel_cost": 0.0,
            "cost_breakdown": {},
            "savings_analysis": {}
        }
        
        try:
            if native_costs:
                summary["native_cost"] = native_costs.get("total_cost", 0.0)
            
            if multimodel_costs:
                summary["multimodel_cost"] = multimodel_costs.get("total_cost", 0.0)
                
                # Breakdown by provider
                for provider, stats in multimodel_costs.get("provider_stats", {}).items():
                    summary["cost_breakdown"][provider] = stats.get("total_cost", 0.0)
            
            summary["total_estimated_cost"] = summary["native_cost"] + summary["multimodel_cost"]
            
            # Calculate potential savings
            if summary["total_estimated_cost"] > 0:
                summary["savings_analysis"] = self.calculate_savings_potential(
                    native_costs, multimodel_costs
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating combined summary: {e}")
            return summary

    def calculate_savings_potential(self, native_costs: Optional[Dict], 
                                   multimodel_costs: Optional[Dict]) -> Dict[str, Any]:
        """Calculate potential cost savings"""
        savings = {
            "potential_monthly_savings": 0.0,
            "cheaper_alternatives": [],
            "optimization_suggestions": []
        }
        
        try:
            # Analyze provider costs to suggest optimizations
            if multimodel_costs and "provider_stats" in multimodel_costs:
                provider_costs = []
                for provider, stats in multimodel_costs["provider_stats"].items():
                    cost = stats.get("total_cost", 0.0)
                    requests = stats.get("total_requests", 1)
                    avg_cost_per_request = cost / requests if requests > 0 else 0
                    
                    provider_costs.append({
                        "provider": provider,
                        "total_cost": cost,
                        "avg_cost_per_request": avg_cost_per_request,
                        "requests": requests
                    })
                
                # Sort by cost per request
                provider_costs.sort(key=lambda x: x["avg_cost_per_request"])
                
                if len(provider_costs) > 1:
                    cheapest = provider_costs[0]
                    most_expensive = provider_costs[-1]
                    
                    potential_savings = (most_expensive["avg_cost_per_request"] - 
                                       cheapest["avg_cost_per_request"]) * most_expensive["requests"]
                    
                    savings["potential_monthly_savings"] = potential_savings * 30  # Estimate monthly
                    
                    savings["cheaper_alternatives"].append({
                        "suggestion": f"Consider using {cheapest['provider']} instead of {most_expensive['provider']}",
                        "estimated_savings": potential_savings,
                        "cost_reduction_percentage": ((most_expensive["avg_cost_per_request"] - 
                                                     cheapest["avg_cost_per_request"]) / 
                                                    most_expensive["avg_cost_per_request"] * 100)
                    })
            
            # Add general optimization suggestions
            savings["optimization_suggestions"] = [
                "Use smaller models (haiku vs sonnet) for simple tasks",
                "Implement request batching to reduce API overhead",
                "Use caching for frequently requested information",
                "Optimize prompts to reduce token usage",
                "Set up rate limiting to prevent unexpected costs"
            ]
            
            return savings
            
        except Exception as e:
            logger.error(f"Error calculating savings potential: {e}")
            return savings

    def generate_recommendations(self, native_costs: Optional[Dict], 
                               multimodel_costs: Optional[Dict]) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        try:
            # Analyze usage patterns
            if multimodel_costs and "provider_stats" in multimodel_costs:
                total_cost = multimodel_costs.get("total_cost", 0.0)
                
                if total_cost > 10:  # $10+ usage
                    recommendations.append(
                        "Consider setting up cost alerts to monitor daily/weekly spending"
                    )
                
                # Check success rates
                for provider, stats in multimodel_costs["provider_stats"].items():
                    success_rate = stats.get("success_rate", 0.0)
                    if success_rate < 0.9:  # Less than 90% success
                        recommendations.append(
                            f"Investigate {provider} reliability issues (success rate: {success_rate:.1%})"
                        )
                
                # Check for uneven usage
                provider_costs = [stats.get("total_cost", 0.0) 
                                for stats in multimodel_costs["provider_stats"].values()]
                if provider_costs and max(provider_costs) > 3 * min(provider_costs):
                    recommendations.append(
                        "Consider load balancing across providers to optimize costs"
                    )
            
            # Add general recommendations
            recommendations.extend([
                "Review and optimize prompts to reduce unnecessary token usage",
                "Implement caching for repeated queries",
                "Use appropriate model sizes for different types of tasks",
                "Monitor rate limits to avoid unnecessary fallback costs"
            ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return recommendations

    def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """Save report to file"""
        try:
            if not filename:
                timestamp = json.dumps(os.times(), default=str).replace(":", "-")
                filename = f"claude-multimodel-cost-report-{timestamp}.json"
            
            report_path = self.temp_dir / filename
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Report saved to: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            return ""

def main():
    """Main function for testing"""
    integration = ClaudeCodeCostsIntegration()
    
    # Generate integrated report
    report = integration.generate_integrated_report()
    
    # Save report
    report_path = integration.save_report(report)
    
    # Print summary
    print("Claude Code Multi-Model Cost Analysis")
    print("====================================")
    print(f"Report saved to: {report_path}")
    print()
    
    summary = report.get("combined_summary", {})
    print(f"Total Estimated Cost: ${summary.get('total_estimated_cost', 0.0):.4f}")
    print(f"Native Claude Cost:   ${summary.get('native_cost', 0.0):.4f}")
    print(f"Multi-Model Cost:     ${summary.get('multimodel_cost', 0.0):.4f}")
    print()
    
    print("Cost Breakdown by Provider:")
    for provider, cost in summary.get("cost_breakdown", {}).items():
        print(f"  {provider}: ${cost:.4f}")
    print()
    
    recommendations = report.get("recommendations", [])
    if recommendations:
        print("Recommendations:")
        for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
            print(f"  {i}. {rec}")

if __name__ == "__main__":
    main()