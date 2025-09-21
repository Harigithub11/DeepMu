#!/usr/bin/env python3
"""
Test script to verify the hybrid search implementation
"""

import os
import sys
import asyncio

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_search_imports():
    """Test that search modules can be imported"""
    print("Testing search module imports...")
    
    try:
        from services.hybrid_search_service import hybrid_search_service
        from models.schemas import SearchQuery, HybridSearchResponse
        
        print("✅ Search modules imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error importing search modules: {e}")
        return False

def test_search_models():
    """Test that search models work correctly"""
    print("\nTesting search models...")
    
    try:
        from models.schemas import SearchQuery, HybridSearchResponse, SearchResult
        
        # Test SearchQuery model
        query = SearchQuery(text="test query", limit=10)
        print(f"✅ SearchQuery model works: {query.text}")
        
        # Test SearchResult model
        result = SearchResult(
            id="test123",
            title="Test Document",
            content="This is test content",
            score=0.95,
            metadata={"source": "test"},
            source="test"
        )
        print(f"✅ SearchResult model works: {result.title}")
        
        # Test HybridSearchResponse model
        response = HybridSearchResponse(
            query="test query",
            results=[result],
            total_results=1,
            search_time=0.1,
            backends_used=["test"],
            cache_hit=False
        )
        print(f"✅ HybridSearchResponse model works: {response.query}")
        
        print("✅ All search models verified")
        return True
        
    except Exception as e:
        print(f"❌ Error testing search models: {e}")
        return False

def test_cdn_config():
    """Test CDN configuration"""
    print("\nTesting CDN configuration...")
    
    try:
        from config.cdn_config import CDNConfig
        
        config = CDNConfig()
        print(f"✅ CDNConfig loaded successfully")
        print(f"Domain: {config.domain}")
        print(f"API Domain: {config.api_domain}")
        
        # Check cache settings
        cache_settings = config.cache_settings
        print(f"Cache settings keys: {list(cache_settings.keys())}")
        
        # Check performance headers
        perf_headers = config.performance_headers
        print(f"Performance headers keys: {list(perf_headers.keys())[:3]}...")  # Show first 3
        
        print("✅ CDN configuration verified")
        return True
        
    except Exception as e:
        print(f"❌ Error testing CDN configuration: {e}")
        return False

async def test_search_initialization():
    """Test hybrid search service initialization"""
    print("\nTesting hybrid search initialization...")
    
    try:
        from services.hybrid_search_service import hybrid_search_service
        
        # This will fail without actual services running, but we can test the structure
        print("✅ Hybrid search service structure verified")
        print("Note: Actual initialization requires running services")
        
        # Test health check structure
        health = await hybrid_search_service.health_check()
        print(f"✅ Health check structure works: {type(health)}")
        
        print("✅ Hybrid search initialization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing hybrid search initialization: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running hybrid search implementation tests...\n")
    
    tests = [
        test_search_imports,
        test_search_models,
        test_cdn_config,
        test_search_initialization
    ]
    
    results = []
    for test in tests:
        try:
            if test.__name__ == 'test_search_initialization':
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
        print("🎉 All hybrid search tests passed!")
        return 0
    else:
        print("💥 Some hybrid search tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
