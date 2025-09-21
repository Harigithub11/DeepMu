#!/usr/bin/env python3
"""
Test script to verify the environment configuration and setup
"""

import os
import sys
import asyncio

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_env_loading():
    """Test environment loading"""
    print("Testing environment loading...")
    
    try:
        from config.environment_manager import env_manager
        
        # Load environment
        success = env_manager.load_environment()
        if not success:
            print("❌ Failed to load environment")
            return False
            
        print("✅ Environment loaded successfully")
        
        # Test domain configuration
        print(f"Primary domain: {env_manager.domain_config['primary']}")
        print(f"Allowed origins: {env_manager.allowed_origins[:3]}...")  # Show first 3
        
        # Test SSL configuration
        print(f"SSL enabled: {env_manager.ssl_config['enabled']}")
        
        # Test feature flags
        features = env_manager.get_feature_flags()
        print(f"Feature flags: {list(features.keys())[:3]}...")  # Show first 3
        
        print("✅ Environment configuration tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing environment: {e}")
        return False

def test_config_files():
    """Test that config files exist and are readable"""
    print("\nTesting config files...")
    
    config_files = [
        '.env.example',
        '.env.production',
        'config/environment_manager.py',
        'utils/domain_health.py'
    ]
    
    for file_path in config_files:
        full_path = os.path.join('project', file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    print("✅ All config files verified")
    return True

async def test_domain_health():
    """Test domain health checking"""
    print("\nTesting domain health checking...")
    
    try:
        from utils.domain_health import DomainHealthChecker
        
        # Test with a few domains
        domains = ['deepmu.tech']
        checker = DomainHealthChecker(domains)
        result = await checker.check_all_domains()
        
        print(f"Domain health check result: {result['overall_status']}")
        print("✅ Domain health checking works")
        return True
        
    except Exception as e:
        print(f"❌ Error in domain health check: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running environment and configuration tests...\n")
    
    tests = [
        test_env_loading,
        test_config_files,
        test_domain_health
    ]
    
    results = []
    for test in tests:
        try:
            if test.__name__ == 'test_domain_health':
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
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
