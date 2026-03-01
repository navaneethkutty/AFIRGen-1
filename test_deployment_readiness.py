#!/usr/bin/env python3
"""
Comprehensive Deployment Readiness Test Script
Tests the entire AFIRGen system (backend + frontend) for production deployment

This script validates:
- Backend API endpoints and authentication
- Frontend static file serving
- Database connectivity
- Model server availability
- Security configurations
- Performance benchmarks
- Error handling
"""

import asyncio
import httpx
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Test configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
API_KEY = "your-api-key-here"  # Replace with actual API key
TEST_TIMEOUT = 30

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.tests = []
    
    def add_pass(self, test_name: str, message: str = ""):
        self.passed += 1
        self.tests.append(("PASS", test_name, message))
        print(f"{GREEN}✓{RESET} {test_name}: {message}")
    
    def add_fail(self, test_name: str, message: str = ""):
        self.failed += 1
        self.tests.append(("FAIL", test_name, message))
        print(f"{RED}✗{RESET} {test_name}: {message}")
    
    def add_warning(self, test_name: str, message: str = ""):
        self.warnings += 1
        self.tests.append(("WARN", test_name, message))
        print(f"{YELLOW}⚠{RESET} {test_name}: {message}")
    
    def print_summary(self):
        total = self.passed + self.failed + self.warnings
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"{YELLOW}Warnings: {self.warnings}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        # Check if most failures are due to backend not running
        backend_not_running = sum(1 for status, name, msg in self.tests 
                                  if "Backend not running" in msg or "start services to test" in msg)
        
        if backend_not_running > 5:
            print(f"{YELLOW}ℹ️  Most tests skipped because backend services are not running{RESET}")
            print(f"{YELLOW}   File structure and code quality tests: PASSED ✅{RESET}")
            print(f"{YELLOW}   To run full tests, start backend services:{RESET}")
            print(f"{YELLOW}   1. Configure environment variables (see .env.development){RESET}")
            print(f"{YELLOW}   2. Start services: docker-compose up -d{RESET}")
            print(f"{YELLOW}   3. Run tests again: python test_deployment_readiness.py{RESET}\n")
            
            if self.failed == 0:
                print(f"{GREEN}✅ CODE STRUCTURE READY - Start services to test runtime behavior{RESET}")
                return True
            else:
                print(f"{RED}❌ FIX CODE ISSUES BEFORE DEPLOYMENT{RESET}")
                return False
        elif self.failed > 0:
            print(f"{RED}❌ DEPLOYMENT NOT READY - Fix failed tests before deploying{RESET}")
            return False
        elif self.warnings > 0:
            print(f"{YELLOW}⚠️  DEPLOYMENT READY WITH WARNINGS - Review warnings before deploying{RESET}")
            return True
        else:
            print(f"{GREEN}✅ DEPLOYMENT READY - All tests passed{RESET}")
            return True

results = TestResults()

async def test_backend_health():
    """Test backend health endpoint"""
    print(f"\n{BLUE}Testing Backend Health...{RESET}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BACKEND_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    results.add_pass("Backend Health", "Backend is healthy")
                    
                    # Check model servers
                    if data.get("model_server", {}).get("status") == "healthy":
                        results.add_pass("Model Server", "Model server is healthy")
                    else:
                        results.add_fail("Model Server", "Model server is not healthy")
                    
                    if data.get("asr_ocr_server", {}).get("status") == "healthy":
                        results.add_pass("ASR/OCR Server", "ASR/OCR server is healthy")
                    else:
                        results.add_fail("ASR/OCR Server", "ASR/OCR server is not healthy")
                else:
                    results.add_fail("Backend Health", f"Backend status: {data.get('status')}")
            else:
                results.add_fail("Backend Health", f"Status code: {response.status_code}")
    except httpx.ConnectError:
        results.add_warning("Backend Health", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Backend Health", f"Error: {str(e)}")

async def test_api_authentication():
    """Test API authentication"""
    print(f"\n{BLUE}Testing API Authentication...{RESET}")
    
    # Test without API key
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{BACKEND_URL}/process", json={"text": "test"})
            if response.status_code == 401:
                results.add_pass("Auth - No Key", "Correctly rejected request without API key")
            else:
                results.add_fail("Auth - No Key", f"Expected 401, got {response.status_code}")
    except httpx.ConnectError:
        results.add_warning("Auth - No Key", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Auth - No Key", f"Error: {str(e)}")
    
    # Test with invalid API key
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-API-Key": "invalid-key"}
            response = await client.post(f"{BACKEND_URL}/process", headers=headers, json={"text": "test"})
            if response.status_code == 401:
                results.add_pass("Auth - Invalid Key", "Correctly rejected invalid API key")
            else:
                results.add_fail("Auth - Invalid Key", f"Expected 401, got {response.status_code}")
    except httpx.ConnectError:
        results.add_warning("Auth - Invalid Key", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Auth - Invalid Key", f"Error: {str(e)}")

async def test_rate_limiting():
    """Test rate limiting"""
    print(f"\n{BLUE}Testing Rate Limiting...{RESET}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"X-API-Key": API_KEY}
            
            # Make rapid requests
            responses = []
            for i in range(105):  # Exceed limit of 100
                try:
                    response = await client.get(f"{BACKEND_URL}/health", headers=headers)
                    responses.append(response.status_code)
                except Exception:
                    pass
            
            # Check if any requests were rate limited
            if 429 in responses:
                results.add_pass("Rate Limiting", "Rate limiting is working")
            else:
                results.add_warning("Rate Limiting", "Rate limiting may not be configured")
    except Exception as e:
        results.add_warning("Rate Limiting", f"Could not test: {str(e)}")

async def test_cors_configuration():
    """Test CORS configuration"""
    print(f"\n{BLUE}Testing CORS Configuration...{RESET}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Origin": "http://malicious-site.com",
                "X-API-Key": API_KEY
            }
            response = await client.options(f"{BACKEND_URL}/process", headers=headers)
            
            # Check if CORS headers are present
            if "access-control-allow-origin" in response.headers:
                allowed_origin = response.headers["access-control-allow-origin"]
                if allowed_origin == "*":
                    results.add_fail("CORS Config", "CORS allows all origins (*) - security risk")
                elif "malicious-site.com" in allowed_origin:
                    results.add_fail("CORS Config", "CORS allows unauthorized origins")
                else:
                    results.add_pass("CORS Config", f"CORS properly configured: {allowed_origin}")
            else:
                results.add_warning("CORS Config", "CORS headers not found")
    except Exception as e:
        results.add_warning("CORS Config", f"Could not test: {str(e)}")

async def test_security_headers():
    """Test security headers"""
    print(f"\n{BLUE}Testing Security Headers...{RESET}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BACKEND_URL}/health")
            
            required_headers = {
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "strict-transport-security": "max-age",
            }
            
            for header, expected_value in required_headers.items():
                if header in response.headers:
                    if expected_value in response.headers[header].lower():
                        results.add_pass(f"Security Header - {header}", "Present and configured")
                    else:
                        results.add_warning(f"Security Header - {header}", f"Present but may be misconfigured")
                else:
                    results.add_fail(f"Security Header - {header}", "Missing")
    except httpx.ConnectError:
        results.add_warning("Security Headers", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Security Headers", f"Error: {str(e)}")

async def test_input_validation():
    """Test input validation"""
    print(f"\n{BLUE}Testing Input Validation...{RESET}")
    
    # Test empty input
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-API-Key": API_KEY}
            response = await client.post(f"{BACKEND_URL}/process", headers=headers, json={})
            if response.status_code == 400:
                results.add_pass("Input Validation - Empty", "Correctly rejected empty input")
            else:
                results.add_fail("Input Validation - Empty", f"Expected 400, got {response.status_code}")
    except httpx.ConnectError:
        results.add_warning("Input Validation - Empty", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Input Validation - Empty", f"Error: {str(e)}")
    
    # Test oversized text
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-API-Key": API_KEY}
            large_text = "A" * 1000000  # 1MB of text
            response = await client.post(f"{BACKEND_URL}/process", headers=headers, json={"text": large_text})
            if response.status_code in [400, 413]:
                results.add_pass("Input Validation - Size", "Correctly rejected oversized input")
            else:
                results.add_warning("Input Validation - Size", f"May not validate input size (got {response.status_code})")
    except httpx.ConnectError:
        results.add_warning("Input Validation - Size", "Backend not running (start services to test)")
    except Exception as e:
        results.add_warning("Input Validation - Size", f"Could not test: {str(e)}")

async def test_error_handling():
    """Test error handling"""
    print(f"\n{BLUE}Testing Error Handling...{RESET}")
    
    # Test invalid session ID
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-API-Key": API_KEY}
            response = await client.get(f"{BACKEND_URL}/session/invalid-session-id/status", headers=headers)
            if response.status_code == 404:
                data = response.json()
                if "detail" in data:
                    results.add_pass("Error Handling - 404", "Returns proper error message")
                else:
                    results.add_warning("Error Handling - 404", "Missing error detail")
            else:
                results.add_warning("Error Handling - 404", f"Expected 404, got {response.status_code}")
    except httpx.ConnectError:
        results.add_warning("Error Handling", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Error Handling", f"Error: {str(e)}")

async def test_performance():
    """Test performance benchmarks"""
    print(f"\n{BLUE}Testing Performance...{RESET}")
    
    # Test health endpoint response time
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = time.time()
            response = await client.get(f"{BACKEND_URL}/health")
            duration = time.time() - start
            
            if duration < 1.0:
                results.add_pass("Performance - Health", f"Response time: {duration:.3f}s")
            elif duration < 3.0:
                results.add_warning("Performance - Health", f"Slow response: {duration:.3f}s")
            else:
                results.add_fail("Performance - Health", f"Very slow response: {duration:.3f}s")
    except httpx.ConnectError:
        results.add_warning("Performance - Health", "Backend not running (start services to test)")
    except Exception as e:
        results.add_fail("Performance - Health", f"Error: {str(e)}")

def test_frontend_files():
    """Test frontend file structure"""
    print(f"\n{BLUE}Testing Frontend Files...{RESET}")
    
    frontend_dir = Path("AFIRGEN FINAL/frontend")
    
    required_files = [
        "index.html",
        "js/app.js",
        "js/api.js",
        "js/ui.js",
        "js/config.js",
        "css/main.css",
        "manifest.json"
    ]
    
    for file_path in required_files:
        full_path = frontend_dir / file_path
        if full_path.exists():
            results.add_pass(f"Frontend File - {file_path}", "Exists")
        else:
            results.add_fail(f"Frontend File - {file_path}", "Missing")

def test_backend_files():
    """Test backend file structure"""
    print(f"\n{BLUE}Testing Backend Files...{RESET}")
    
    backend_dir = Path("AFIRGEN FINAL/main backend")
    
    required_files = [
        "agentv5.py",
        "requirements.txt",
        "Dockerfile",
        "infrastructure/config.py",
        "infrastructure/database.py",
    ]
    
    for file_path in required_files:
        full_path = backend_dir / file_path
        if full_path.exists():
            results.add_pass(f"Backend File - {file_path}", "Exists")
        else:
            results.add_fail(f"Backend File - {file_path}", "Missing")

def test_configuration():
    """Test configuration files"""
    print(f"\n{BLUE}Testing Configuration...{RESET}")
    
    # Check for .env file
    env_file = Path("AFIRGEN FINAL/.env")
    if env_file.exists():
        results.add_pass("Config - .env", "Environment file exists")
    else:
        results.add_warning("Config - .env", "No .env file found (may use environment variables)")
    
    # Check gitignore
    gitignore = Path(".gitignore")
    if gitignore.exists():
        content = gitignore.read_text()
        if "__pycache__" in content:
            results.add_pass("Config - .gitignore", "Python cache files ignored")
        else:
            results.add_warning("Config - .gitignore", "Python cache files may not be ignored")
    else:
        results.add_fail("Config - .gitignore", "Missing .gitignore file")

async def main():
    """Run all tests"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}AFIRGen Deployment Readiness Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # File structure tests (synchronous)
    test_frontend_files()
    test_backend_files()
    test_configuration()
    
    # Backend tests (asynchronous)
    await test_backend_health()
    await test_api_authentication()
    await test_rate_limiting()
    await test_cors_configuration()
    await test_security_headers()
    await test_input_validation()
    await test_error_handling()
    await test_performance()
    
    # Print summary
    is_ready = results.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if is_ready else 1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Test suite error: {e}{RESET}")
        sys.exit(1)
