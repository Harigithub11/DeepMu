#!/usr/bin/env python3
"""
Test script to verify the AI integration implementation
"""

import os
import sys
import asyncio

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ai_imports():
    """Test that AI modules can be imported"""
    print("Testing AI module imports...")
    
    try:
        from services.ai_service import ai_service
        from models.schemas import (
            DocumentAnalysisRequest, DocumentAnalysisResponse,
            ResearchInsightRequest, ResearchInsightResponse,
            SummarizationRequest, SummarizationResponse
        )
        
        print("✅ AI modules imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error importing AI modules: {e}")
        return False

def test_ai_models():
    """Test that AI models work correctly"""
    print("\nTesting AI models...")
    
    try:
        from models.schemas import (
            DocumentAnalysisRequest, ResearchInsightRequest, SummarizationRequest
        )
        
        # Test DocumentAnalysisRequest model
        doc_request = DocumentAnalysisRequest(
            document_id="test123",
            title="Test Document",
            content="This is test content for analysis",
            metadata={"domain": "deepmu.tech"}
        )
        print(f"✅ DocumentAnalysisRequest model works: {doc_request.document_id}")
        
        # Test ResearchInsightRequest model
        insight_request = ResearchInsightRequest(
            query="test research query",
            documents=[{"title": "Doc1", "content": "Content1"}],
            metadata={"domain": "deepmu.tech"}
        )
        print(f"✅ ResearchInsightRequest model works: {insight_request.query}")
        
        # Test SummarizationRequest model
        summary_request = SummarizationRequest(
            content="This is test content to summarize that meets the minimum length requirement",
            max_length=100
        )
        print(f"✅ SummarizationRequest model works: {len(summary_request.content)} chars")
        
        print("✅ All AI models verified")
        return True
        
    except Exception as e:
        print(f"❌ Error testing AI models: {e}")
        return False

def test_security_config():
    """Test security configuration"""
    print("\nTesting security configuration...")
    
    try:
        from config.security import security_config
        
        print(f"✅ Security config loaded successfully")
        print(f"Domain: {security_config.domain}")
        print(f"Allowed origins count: {len(security_config.allowed_origins)}")
        
        # Test JWT functionality
        token_data = {"user_id": "test_user"}
        token = security_config.create_access_token(token_data)
        print(f"✅ JWT token creation works")
        
        # Note: We won't test token verification here as it requires proper secret
        
        print("✅ Security configuration verified")
        return True
        
    except Exception as e:
        print(f"❌ Error testing security configuration: {e}")
        return False

async def test_ai_initialization():
    """Test AI service initialization"""
    print("\nTesting AI service initialization...")
    
    try:
        from services.ai_service import ai_service
        
        # Test health check structure (this won't fully work without actual services)
        health = await ai_service.health_check()
        print(f"✅ AI service health check structure works: {type(health)}")
        
        print("✅ AI initialization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing AI initialization: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running AI integration implementation tests...\n")
    
    tests = [
        test_ai_imports,
        test_ai_models,
        test_security_config,
        test_ai_initialization
    ]
    
    results = []
    for test in tests:
        try:
            if test.__name__ == 'test_ai_initialization':
                # This is async
                result = asyncio.run(test())
            else:
                result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All AI integration tests passed!")
        return 0
    else:
        print("💥 Some AI integration tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
