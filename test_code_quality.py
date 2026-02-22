#!/usr/bin/env python3
"""
Code Quality and Static Analysis Test
Tests code without requiring running services

This validates:
- Python syntax
- Import statements
- Critical security patterns
- Code structure
- Configuration files
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class CodeQualityResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def add_pass(self, test_name: str, message: str = ""):
        self.passed += 1
        print(f"{GREEN}✓{RESET} {test_name}: {message}")
    
    def add_fail(self, test_name: str, message: str = ""):
        self.failed += 1
        print(f"{RED}✗{RESET} {test_name}: {message}")
    
    def add_warning(self, test_name: str, message: str = ""):
        self.warnings += 1
        print(f"{YELLOW}⚠{RESET} {test_name}: {message}")
    
    def print_summary(self):
        total = self.passed + self.failed + self.warnings
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Code Quality Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"{YELLOW}Warnings: {self.warnings}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        if self.failed > 0:
            print(f"{RED}❌ CODE QUALITY ISSUES FOUND{RESET}")
            return False
        elif self.warnings > 0:
            print(f"{YELLOW}⚠️  CODE QUALITY GOOD WITH WARNINGS{RESET}")
            return True
        else:
            print(f"{GREEN}✅ CODE QUALITY EXCELLENT{RESET}")
            return True

results = CodeQualityResults()

def test_python_syntax():
    """Test Python files for syntax errors"""
    print(f"\n{BLUE}Testing Python Syntax...{RESET}")
    
    backend_dir = Path("AFIRGEN FINAL/main backend")
    python_files = [
        "agentv5.py",
        "infrastructure/config.py",
        "infrastructure/database.py",
        "infrastructure/cache_manager.py",
        "middleware/compression_middleware.py",
    ]
    
    for file_path in python_files:
        full_path = backend_dir / file_path
        if not full_path.exists():
            results.add_warning(f"Syntax - {file_path}", "File not found")
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                code = f.read()
                ast.parse(code)
            results.add_pass(f"Syntax - {file_path}", "Valid Python syntax")
        except SyntaxError as e:
            results.add_fail(f"Syntax - {file_path}", f"Syntax error: {e}")
        except Exception as e:
            results.add_warning(f"Syntax - {file_path}", f"Could not parse: {e}")

def test_critical_imports():
    """Test that critical modules can be imported"""
    print(f"\n{BLUE}Testing Critical Imports...{RESET}")
    
    critical_modules = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"),
        ("httpx", "HTTP client"),
        ("redis", "Redis client"),
        ("mysql.connector", "MySQL connector"),
    ]
    
    for module_name, description in critical_modules:
        try:
            __import__(module_name)
            results.add_pass(f"Import - {module_name}", f"{description} available")
        except ImportError:
            results.add_fail(f"Import - {module_name}", f"{description} not installed")

def test_security_patterns():
    """Test for security anti-patterns in code"""
    print(f"\n{BLUE}Testing Security Patterns...{RESET}")
    
    backend_dir = Path("AFIRGEN FINAL/main backend")
    
    # Check agentv5.py for hardcoded secrets
    agentv5_path = backend_dir / "agentv5.py"
    if agentv5_path.exists():
        content = agentv5_path.read_text(encoding='utf-8')
        
        # Check for default secret values
        if 'default="' in content and ('API_KEY' in content or 'PASSWORD' in content):
            # Check if it's in get_secret calls with defaults
            if 'get_secret(' in content and 'default=' in content:
                results.add_warning("Security - Secrets", "Found default values in get_secret calls")
            else:
                results.add_pass("Security - Secrets", "No obvious hardcoded secrets")
        else:
            results.add_pass("Security - Secrets", "No default secret values found")
        
        # Check for SQL injection patterns
        if 'f"SELECT' in content or "f'SELECT" in content:
            results.add_warning("Security - SQL", "Found f-string in SQL query (check for injection)")
        else:
            results.add_pass("Security - SQL", "No obvious SQL injection patterns")
        
        # Check for threading locks
        if 'threading.Lock()' in content:
            results.add_pass("Security - Threading", "Thread locks implemented")
        else:
            results.add_warning("Security - Threading", "No thread locks found")
    else:
        results.add_fail("Security Check", "agentv5.py not found")

def test_frontend_security():
    """Test frontend security patterns"""
    print(f"\n{BLUE}Testing Frontend Security...{RESET}")
    
    frontend_dir = Path("AFIRGEN FINAL/frontend")
    
    # Check ui.js for XSS prevention
    ui_js_path = frontend_dir / "js/ui.js"
    if ui_js_path.exists():
        content = ui_js_path.read_text(encoding='utf-8')
        
        # Check for innerHTML usage
        innerHTML_count = content.count('.innerHTML')
        textContent_count = content.count('.textContent')
        
        if innerHTML_count > textContent_count:
            results.add_warning("Frontend - XSS", f"More innerHTML ({innerHTML_count}) than textContent ({textContent_count})")
        else:
            results.add_pass("Frontend - XSS", "Prefers textContent over innerHTML")
    else:
        results.add_warning("Frontend - XSS", "ui.js not found")
    
    # Check for DOMPurify
    index_html_path = frontend_dir / "index.html"
    if index_html_path.exists():
        content = index_html_path.read_text(encoding='utf-8')
        
        if 'dompurify' in content.lower():
            results.add_pass("Frontend - DOMPurify", "DOMPurify library included")
        else:
            results.add_warning("Frontend - DOMPurify", "DOMPurify not found")
    else:
        results.add_fail("Frontend - HTML", "index.html not found")

def test_configuration_files():
    """Test configuration files"""
    print(f"\n{BLUE}Testing Configuration Files...{RESET}")
    
    # Check .env.development
    env_dev = Path("AFIRGEN FINAL/main backend/.env.development")
    if env_dev.exists():
        content = env_dev.read_text()
        
        required_vars = [
            "API_KEY",
            "DB_HOST",
            "DB_PASSWORD",
            "REDIS_HOST",
            "MODEL_SERVER_URL",
        ]
        
        missing = [var for var in required_vars if var not in content]
        if missing:
            results.add_fail("Config - .env.development", f"Missing: {', '.join(missing)}")
        else:
            results.add_pass("Config - .env.development", "All required variables present")
    else:
        results.add_fail("Config - .env.development", "File not found")
    
    # Check docker-compose.yaml
    docker_compose = Path("AFIRGEN FINAL/docker-compose.yaml")
    if docker_compose.exists():
        content = docker_compose.read_text()
        
        required_services = [
            "fir_pipeline",
            "mysql",
            "redis",
            "gguf_model_server",
            "asr_ocr_model_server",
        ]
        
        missing = [svc for svc in required_services if svc not in content]
        if missing:
            results.add_fail("Config - docker-compose", f"Missing services: {', '.join(missing)}")
        else:
            results.add_pass("Config - docker-compose", "All required services defined")
    else:
        results.add_fail("Config - docker-compose", "File not found")

def test_critical_fixes():
    """Verify critical fixes from audit are applied"""
    print(f"\n{BLUE}Testing Critical Fixes...{RESET}")
    
    backend_dir = Path("AFIRGEN FINAL/main backend")
    agentv5_path = backend_dir / "agentv5.py"
    
    if agentv5_path.exists():
        content = agentv5_path.read_text(encoding='utf-8')
        
        # Check for thread safety in PersistentSessionManager
        if 'class PersistentSessionManager' in content:
            if 'self._lock = threading.Lock()' in content or 'self._cache_lock = threading.Lock()' in content:
                results.add_pass("Fix - Thread Safety", "Session manager has thread lock")
            else:
                results.add_fail("Fix - Thread Safety", "Session manager missing thread lock")
        
        # Check for bounded cache in ModelPool
        if 'class ModelPool' in content:
            if '_max_cache_size' in content:
                results.add_pass("Fix - Bounded Cache", "ModelPool has cache size limit")
            else:
                results.add_fail("Fix - Bounded Cache", "ModelPool missing cache size limit")
        
        # Check for no default secrets
        if 'get_secret(' in content:
            # Count get_secret calls with default parameter
            default_count = content.count('get_secret(') - content.count('required=True')
            if default_count > 5:  # Some defaults are OK for non-sensitive config
                results.add_warning("Fix - Secrets", f"Found {default_count} get_secret calls without required=True")
            else:
                results.add_pass("Fix - Secrets", "Most secrets require explicit configuration")
    else:
        results.add_fail("Fix Verification", "agentv5.py not found")
    
    # Check frontend file selection lock
    app_js_path = Path("AFIRGEN FINAL/frontend/js/app.js")
    if app_js_path.exists():
        content = app_js_path.read_text(encoding='utf-8')
        
        if 'fileSelectionLock' in content:
            results.add_pass("Fix - File Selection", "File selection lock implemented")
        else:
            results.add_fail("Fix - File Selection", "File selection lock missing")
    else:
        results.add_fail("Fix - File Selection", "app.js not found")

def main():
    """Run all code quality tests"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}AFIRGen Code Quality Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    test_python_syntax()
    test_critical_imports()
    test_security_patterns()
    test_frontend_security()
    test_configuration_files()
    test_critical_fixes()
    
    is_ready = results.print_summary()
    sys.exit(0 if is_ready else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Test suite error: {e}{RESET}")
        sys.exit(1)
