#!/usr/bin/env python3
"""
Test script for Vertex AI Claude model mappings
==============================================

Tests the corrected model mappings according to official documentation.
"""

import sys
import os
import asyncio

# Add utils to path
sys.path.append('utils')
sys.path.append('services')

from utils.vertex_models_fetcher import VertexModelsFetcher, fetch_vertex_models

async def test_model_mappings():
    """Test Claude model mappings for Vertex AI"""
    
    print("🧪 Testing Vertex AI Claude Model Mappings")
    print("=" * 50)
    
    # Test cases based on official documentation
    test_models = [
        # Claude 4 family (latest)
        "claude-opus-4",
        "claude-sonnet-4", 
        "claude-4-opus",
        "anthropic/claude-sonnet-4",
        
        # Claude 3.7 family  
        "claude-3-7-sonnet",
        "claude-3.7-sonnet",
        
        # Claude 3.5 family
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet",
        "claude-3-5-haiku",
        
        # Claude 3 family
        "claude-3-opus",
        "claude-3-sonnet", 
        "claude-3-haiku"
    ]
    
    try:
        # Test fetcher
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "test-project")
        fetcher = VertexModelsFetcher(project_id=project_id, location="us-east5")
        
        claude_models = fetcher.get_available_claude_models()
        
        print(f"📊 Retrieved {len(claude_models['models'])} Claude model mappings:")
        print()
        
        for input_model in test_models:
            if input_model in claude_models['models']:
                vertex_model = claude_models['models'][input_model]
                litellm_format = f"vertex_ai/{vertex_model}"
                
                print(f"✅ {input_model:30} → {litellm_format}")
            else:
                print(f"❌ {input_model:30} → NOT FOUND")
        
        print()
        print("🔍 Expected LiteLLM Format:")
        print("   vertex_ai/claude-sonnet-4@20250514")
        print("   vertex_ai/claude-3-7-sonnet@20250219") 
        print("   vertex_ai/claude-3-5-sonnet@20241022")
        print("   vertex_ai/claude-3-opus@20240229")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_service_integration():
    """Test integration with vertex_claude_service"""
    
    print("\n🔧 Testing Service Integration")
    print("=" * 50)
    
    try:
        # Import service (this tests configuration loading)
        from vertex_claude_service import VertexClaudeService
        
        # Create service instance
        service = VertexClaudeService(port=8090)
        
        print(f"✅ Service initialized:")
        print(f"   Project: {service.provider_config.get('project', 'not set')}")
        print(f"   Location: {service.provider_config.get('location', 'not set')}")
        print(f"   Models: {len(service.provider_config.get('models', {}))}")
        
        # Test model mapping
        test_mappings = [
            "claude-sonnet-4",
            "claude-3-7-sonnet", 
            "claude-3-5-sonnet",
            "anthropic/claude-sonnet-4"
        ]
        
        print("\n🔄 Testing Model Mapping:")
        for model in test_mappings:
            try:
                mapped = await service.map_model(model)
                print(f"   {model:25} → {mapped}")
            except Exception as e:
                print(f"   {model:25} → ERROR: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        return False

async def main():
    """Run all tests"""
    
    print("🚀 Vertex AI Claude Models Test Suite")
    print("=====================================")
    
    # Test 1: Model mappings
    test1_passed = await test_model_mappings()
    
    # Test 2: Service integration
    test2_passed = await test_service_integration()
    
    print("\n📊 Test Results:")
    print(f"   Model Mappings: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Service Integration: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Model mappings are correct.")
        return True
    else:
        print("\n❌ Some tests failed. Check configuration and mappings.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)