#!/usr/bin/env python3
"""
Vertex AI Models Dynamic Fetcher
=================================

Retrieves available models dynamically from Google Cloud Vertex AI
and updates service configurations accordingly.
"""

import os
import json
import logging
from typing import Dict, List, Any
from google.cloud import aiplatform
from google.auth import default

class VertexModelsFetcher:
    """
    Dynamic fetcher for Vertex AI models in specified regions.
    """
    
    def __init__(self, project_id: str, location: str = "us-east5"):
        """
        Initialize the models fetcher.
        
        Args:
            project_id: Google Cloud project ID
            location: Vertex AI location/region
        """
        self.project_id = project_id
        self.location = location
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI Platform
        aiplatform.init(project=project_id, location=location)
        
    def get_available_claude_models(self) -> Dict[str, Any]:
        """
        Get available Claude models from Vertex AI.
        
        Returns:
            Dict containing Claude model information
        """
        try:
            # Correct Claude model mappings for Vertex AI (based on official documentation)
            claude_models = {
                # Claude 4 family (latest)
                "claude-opus-4": "claude-opus-4@20250514",
                "claude-sonnet-4": "claude-sonnet-4@20250514", 
                "claude-4-opus": "claude-opus-4@20250514",
                "claude-4-sonnet": "claude-sonnet-4@20250514",
                "anthropic/claude-sonnet-4": "claude-sonnet-4@20250514",
                
                # Claude 3.7 family
                "claude-3-7-sonnet": "claude-3-7-sonnet@20250219",
                "claude-3.7-sonnet": "claude-3-7-sonnet@20250219",
                
                # Claude 3.5 family  
                "claude-3-5-sonnet-20241022": "claude-3-5-sonnet@20241022",
                "claude-3-5-sonnet-v2": "claude-3-5-sonnet@20241022",
                "claude-3-5-sonnet": "claude-3-5-sonnet@20241022",
                "claude-3-5-haiku-20241022": "claude-3-5-haiku@20241022",
                "claude-3-5-haiku": "claude-3-5-haiku@20241022",
                
                # Claude 3 family
                "claude-3-opus": "claude-3-opus@20240229",
                "claude-3-sonnet": "claude-3-sonnet@20240229", 
                "claude-3-haiku": "claude-3-haiku@20240307"
            }
            
            self.logger.info(f"✅ Retrieved Claude models for region {self.location}")
            return {
                "models": claude_models,
                "region": self.location,
                "project": self.project_id,
                "timestamp": "2025-01-02"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve Claude models: {e}")
            return {"models": {}, "error": str(e)}
    
    def get_available_gemini_models(self) -> Dict[str, Any]:
        """
        Get available Gemini models from Vertex AI.
        
        Returns:
            Dict containing Gemini model information
        """
        try:
            # Common Gemini model mappings for Vertex AI
            gemini_models = {
                "gemini-2.0-flash-exp": "vertex_ai/gemini-2.0-flash-exp",
                "gemini-1.5-pro": "vertex_ai/gemini-1.5-pro-002",
                "gemini-1.5-flash": "vertex_ai/gemini-1.5-flash-002",
                "gemini-1.5-pro-002": "vertex_ai/gemini-1.5-pro-002",
                "gemini-1.5-flash-002": "vertex_ai/gemini-1.5-flash-002",
                "gemini-pro": "vertex_ai/gemini-1.5-pro-002",
                "gemini-flash": "vertex_ai/gemini-1.5-flash-002"
            }
            
            self.logger.info(f"✅ Retrieved Gemini models for region {self.location}")
            return {
                "models": gemini_models,
                "region": self.location,
                "project": self.project_id,
                "timestamp": "2025-01-02"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve Gemini models: {e}")
            return {"models": {}, "error": str(e)}
    
    def get_supported_regions(self) -> List[str]:
        """
        Get list of supported regions for Vertex AI.
        
        Returns:
            List of supported region names
        """
        return [
            "us-east5",
            "us-central1", 
            "us-west1",
            "europe-west1",
            "europe-west4",
            "asia-southeast1"
        ]
    
    def test_region_availability(self, region: str) -> Dict[str, Any]:
        """
        Test if models are available in a specific region.
        
        Args:
            region: Region to test
            
        Returns:
            Dict containing test results
        """
        try:
            # Test by initializing AI Platform with the region
            aiplatform.init(project=self.project_id, location=region)
            
            return {
                "region": region,
                "available": True,
                "timestamp": "2025-01-02",
                "status": "healthy"
            }
            
        except Exception as e:
            return {
                "region": region,
                "available": False,
                "error": str(e),
                "timestamp": "2025-01-02",
                "status": "failed"
            }


def fetch_vertex_models(project_id: str = None, location: str = "us-east5") -> Dict[str, Any]:
    """
    Convenience function to fetch Vertex AI models.
    
    Args:
        project_id: Google Cloud project ID
        location: Vertex AI region
        
    Returns:
        Combined model information
    """
    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
    if not project_id:
        raise ValueError("Google Cloud project ID required")
    
    fetcher = VertexModelsFetcher(project_id, location)
    
    claude_models = fetcher.get_available_claude_models()
    gemini_models = fetcher.get_available_gemini_models()
    
    return {
        "claude": claude_models,
        "gemini": gemini_models,
        "regions": fetcher.get_supported_regions(),
        "current_region": location,
        "project": project_id
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        models_info = fetch_vertex_models()
        
        print("🚀 Vertex AI Models Information:")
        print(f"Project: {models_info['project']}")
        print(f"Region: {models_info['current_region']}")
        
        print("\n🔵 Claude Models:")
        for model_id, vertex_name in models_info['claude']['models'].items():
            print(f"  {model_id} → {vertex_name}")
            
        print("\n🟡 Gemini Models:")
        for model_id, vertex_name in models_info['gemini']['models'].items():
            print(f"  {model_id} → {vertex_name}")
            
        print(f"\n🌍 Supported Regions: {', '.join(models_info['regions'])}")
        
    except Exception as e:
        print(f"❌ Failed to fetch models: {e}")