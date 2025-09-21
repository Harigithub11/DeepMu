#!/usr/bin/env python3
"""
Test script to verify Docker deployment setup
"""
import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def test_docker_build():
    """Test that Dockerfile builds correctly"""
    print("Testing Docker build...")
    
    success, output = run_command("docker build --target production -t documind-test .")
    if success:
        print("✓ Docker build successful")
        return True
    else:
        print("✗ Docker build failed:")
        print(output)
        return False

def test_compose_file():
    """Test that docker-compose file is valid"""
    print("Testing docker-compose file...")
    
    success, output = run_command("docker-compose config")
    if success:
        print("✓ docker-compose file is valid")
        return True
    else:
        print("✗ docker-compose file validation failed:")
        print(output)
        return False

def test_ssl_scripts():
    """Test that SSL scripts exist and are executable"""
    print("Testing SSL scripts...")
    
    scripts = [
        "scripts/ssl/init-ssl.sh",
        "scripts/ssl/renew-certificates.sh"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print(f"✓ {script} exists and is executable")
            else:
                print(f"✗ {script} exists but is not executable")
                return False
        else:
            print(f"✗ {script} does not exist")
            return False
    
    return True

def test_entrypoint_script():
    """Test that entrypoint script exists"""
    print("Testing entrypoint script...")
    
    script = "scripts/entrypoint.sh"
    if os.path.exists(script):
        if os.access(script, os.X_OK):
            print("✓ entrypoint.sh exists and is executable")
            return True
        else:
            print("✗ entrypoint.sh exists but is not executable")
            return False
    else:
        print("✗ entrypoint.sh does not exist")
        return False

def main():
    """Run all tests"""
    print("Running Docker deployment tests...\n")
    
    tests = [
        test_docker_build,
        test_compose_file,
        test_ssl_scripts,
        test_entrypoint_script
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Docker deployment setup looks good.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
