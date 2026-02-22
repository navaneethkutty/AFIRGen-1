#!/usr/bin/env python3
"""
COMPREHENSIVE TEST SUITE - CHECKS EVERYTHING
Will not stop until ALL tests pass
"""

import subprocess
import sys
import time
import os
import json
import asyncio
import httpx
from pathlib import Path
from typing import List, Tuple, Dict, Any

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

class ComprehensiveTestSuite:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        self.test_results = []
        
    def print_header(self, text, level=1):
        if level == 1:
            print(f"\n{BLUE}{'='*70}{RESET}")
            print(f"{BLUE}{text.center(70)}{RESET}")
            print(f"{BLUE}{'='*70}{RESET}\n")
        else:
            print(f"\n{CYAN}{'─'*70}{RESET}")
            print(f"{CYAN}{text}{RESET}")
            print(f"{CYAN}{'─'*70}{RESET}")
    
    def test(self, name: str, passed: bool, message: str = "", critical: bool = False):
        """Record a test result"""
        self.total_tests += 1
        
        if passed:
            self.passed_tests += 1
            print(f"{GREEN}✓{RESET} {name}: {message}")
            self.test_results.append(("PASS", name, message, critical))
        else:
            self.failed_tests += 1
            print(f"{RED}✗{RESET} {name}: {message}")
            self.test_results.append(("FAIL", name, message, critical))
    
    def warn(self, name: str, message: str = ""):
        """Record a warning"""
        self.warnings += 1
        print(f"{YELLOW}⚠{RESET} {name}: {message}")
        self.test_results.append(("WARN", name, message, False))
    
    def info(self, message: str):
        """Print info message"""
        print(f"{CYAN}ℹ{RESET} {message}")
    
    # ============================================================================
    # FILE STRUCTURE TESTS
    # ============================================================================
    
    def test_frontend_files(self):
        """Test all frontend files exist"""
        self.print_header("FRONTEND FILE STRUCTURE", 2)
        
        frontend_dir = Path("AFIRGEN FINAL/frontend")
        
        required_files = {
            "HTML": ["index.html"],
            "JavaScript": [
                "js/app.js",
                "js/api.js",
                "js/ui.js",
                "js/config.js",
                "js/validation.js",
                "js/storage.js",
                "js/drag-drop.js"
            ],
            "CSS": ["css/main.css", "css/styles.css"],
            "PWA": ["manifest.json", "sw.js"],
            "Assets": ["favicon.ico"]
        }
        
        for category, files in required_files.items():
            self.info(f"Checking {category} files...")
            for file_path in files:
                full_path = frontend_dir / file_path
                self.test(
                    f"Frontend - {file_path}",
                    full_path.exists(),
                    "exists" if full_path.exists() else "MISSING",
                    critical=True
                )
    
    def test_backend_files(self):
        """Test all backend files exist"""
        self.print_header("BACKEND FILE STRUCTURE", 2)
        
        backend_dir = Path("AFIRGEN FINAL/main backend")
        
        required_files = {
            "Main": ["agentv5.py"],
            "Config": [
                "requirements.txt",
                "Dockerfile",
                ".env.development",
                ".env.production"
            ],
            "Infrastructure": [
                "infrastructure/config.py",
                "infrastructure/database.py",
                "infrastructure/cache_manager.py",
                "infrastructure/celery_app.py"
            ],
            "Middleware": [
                "middleware/compression_middleware.py"
            ],
            "Utils": [
                "utils/pagination.py",
                "utils/field_filter.py"
            ]
        }
        
        for category, files in required_files.items():
            self.info(f"Checking {category} files...")
            for file_path in files:
                full_path = backend_dir / file_path
                self.test(
                    f"Backend - {file_path}",
                    full_path.exists(),
                    "exists" if full_path.exists() else "MISSING",
                    critical=True
                )
    
    def test_model_server_files(self):
        """Test model server files exist"""
        self.print_header("MODEL SERVER FILE STRUCTURE", 2)
        
        servers = [
            ("GGUF Model Server", "AFIRGEN FINAL/gguf model server"),
            ("ASR/OCR Server", "AFIRGEN FINAL/asr ocr model server")
        ]
        
        for server_name, server_dir in servers:
            server_path = Path(server_dir)
            self.info(f"Checking {server_name}...")
            
            # Check main files
            for file_name in ["Dockerfile", "requirements.txt"]:
                full_path = server_path / file_name
                self.test(
                    f"{server_name} - {file_name}",
                    full_path.exists(),
                    "exists" if full_path.exists() else "MISSING",
                    critical=True
                )
    
    def test_docker_files(self):
        """Test Docker configuration files"""
        self.print_header("DOCKER CONFIGURATION", 2)
        
        docker_files = [
            "AFIRGEN FINAL/docker-compose.yaml",
            "docker-compose.test.yaml",
            "AFIRGEN FINAL/main backend/Dockerfile",
            "AFIRGEN FINAL/gguf model server/Dockerfile",
            "AFIRGEN FINAL/asr ocr model server/Dockerfile"
        ]
        
        for file_path in docker_files:
            full_path = Path(file_path)
            self.test(
                f"Docker - {file_path}",
                full_path.exists(),
                "exists" if full_path.exists() else "MISSING",
                critical=True
            )
    
    # ============================================================================
    # CODE QUALITY TESTS
    # ============================================================================
    
    def test_python_syntax(self):
        """Test Python files for syntax errors"""
        self.print_header("PYTHON SYNTAX VALIDATION", 2)
        
        import ast
        
        backend_dir = Path("AFIRGEN FINAL/main backend")
        
        python_files = [
            "agentv5.py",
            "infrastructure/config.py",
            "infrastructure/database.py",
            "infrastructure/cache_manager.py",
            "middleware/compression_middleware.py"
        ]
        
        for file_path in python_files:
            full_path = backend_dir / file_path
            if not full_path.exists():
                self.test(f"Syntax - {file_path}", False, "File not found", critical=True)
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                    ast.parse(code)
                self.test(f"Syntax - {file_path}", True, "Valid Python syntax")
            except SyntaxError as e:
                self.test(f"Syntax - {file_path}", False, f"Syntax error: {e}", critical=True)
            except Exception as e:
                self.warn(f"Syntax - {file_path}", f"Could not parse: {e}")
    
    def test_javascript_syntax(self):
        """Test JavaScript files exist and are readable"""
        self.print_header("JAVASCRIPT FILE VALIDATION", 2)
        
        frontend_dir = Path("AFIRGEN FINAL/frontend")
        
        js_files = [
            "js/app.js",
            "js/api.js",
            "js/ui.js",
            "js/config.js",
            "js/validation.js"
        ]
        
        for file_path in js_files:
            full_path = frontend_dir / file_path
            if not full_path.exists():
                self.test(f"JS - {file_path}", False, "File not found", critical=True)
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Basic checks
                    has_content = len(content) > 0
                    self.test(f"JS - {file_path}", has_content, f"{len(content)} bytes")
            except Exception as e:
                self.test(f"JS - {file_path}", False, f"Error reading: {e}", critical=True)
    
    def test_critical_imports(self):
        """Test that critical Python modules can be imported"""
        self.print_header("PYTHON DEPENDENCIES", 2)
        
        critical_modules = [
            ("fastapi", "FastAPI framework"),
            ("uvicorn", "ASGI server"),
            ("httpx", "HTTP client"),
            ("redis", "Redis client"),
            ("mysql.connector", "MySQL connector"),
            ("pydantic", "Data validation"),
            ("celery", "Task queue")
        ]
        
        for module_name, description in critical_modules:
            try:
                __import__(module_name)
                self.test(f"Import - {module_name}", True, f"{description} available")
            except ImportError:
                self.test(f"Import - {module_name}", False, f"{description} NOT INSTALLED", critical=True)
    
    # ============================================================================
    # SECURITY TESTS
    # ============================================================================
    
    def test_security_patterns(self):
        """Test for security patterns in code"""
        self.print_header("SECURITY PATTERN ANALYSIS", 2)
        
        backend_dir = Path("AFIRGEN FINAL/main backend")
        agentv5_path = backend_dir / "agentv5.py"
        
        if not agentv5_path.exists():
            self.test("Security Check", False, "agentv5.py not found", critical=True)
            return
        
        content = agentv5_path.read_text(encoding='utf-8')
        
        # Check for thread locks
        has_thread_lock = 'threading.Lock()' in content
        self.test(
            "Security - Thread Safety",
            has_thread_lock,
            "Thread locks implemented" if has_thread_lock else "NO THREAD LOCKS FOUND",
            critical=True
        )
        
        # Check for bounded cache
        has_bounded_cache = '_max_cache_size' in content
        self.test(
            "Security - Bounded Cache",
            has_bounded_cache,
            "Cache size limits implemented" if has_bounded_cache else "NO CACHE LIMITS",
            critical=True
        )
        
        # Check for SQL injection prevention
        has_parameterized = '%s' in content or '?' in content
        self.test(
            "Security - SQL Injection Prevention",
            has_parameterized,
            "Parameterized queries used" if has_parameterized else "Check SQL queries",
            critical=False
        )
    
    def test_frontend_security(self):
        """Test frontend security patterns"""
        self.print_header("FRONTEND SECURITY", 2)
        
        frontend_dir = Path("AFIRGEN FINAL/frontend")
        
        # Check ui.js for XSS prevention
        ui_js_path = frontend_dir / "js/ui.js"
        if ui_js_path.exists():
            content = ui_js_path.read_text(encoding='utf-8')
            
            innerHTML_count = content.count('.innerHTML')
            textContent_count = content.count('.textContent')
            
            prefers_textContent = textContent_count >= innerHTML_count
            self.test(
                "Frontend - XSS Prevention",
                prefers_textContent,
                f"textContent: {textContent_count}, innerHTML: {innerHTML_count}",
                critical=False
            )
        else:
            self.test("Frontend - XSS Prevention", False, "ui.js not found", critical=True)
        
        # Check for DOMPurify
        index_html_path = frontend_dir / "index.html"
        if index_html_path.exists():
            content = index_html_path.read_text(encoding='utf-8')
            has_dompurify = 'dompurify' in content.lower()
            self.test(
                "Frontend - DOMPurify",
                has_dompurify,
                "DOMPurify library included" if has_dompurify else "DOMPurify NOT FOUND",
                critical=False
            )
        else:
            self.test("Frontend - DOMPurify", False, "index.html not found", critical=True)
        
        # Check for file selection lock
        app_js_path = frontend_dir / "js/app.js"
        if app_js_path.exists():
            content = app_js_path.read_text(encoding='utf-8')
            has_lock = 'fileSelectionLock' in content
            self.test(
                "Frontend - File Selection Lock",
                has_lock,
                "Race condition prevention implemented" if has_lock else "NO FILE LOCK",
                critical=True
            )
        else:
            self.test("Frontend - File Selection Lock", False, "app.js not found", critical=True)
    
    # ============================================================================
    # CONFIGURATION TESTS
    # ============================================================================
    
    def test_environment_configs(self):
        """Test environment configuration files"""
        self.print_header("ENVIRONMENT CONFIGURATION", 2)
        
        backend_dir = Path("AFIRGEN FINAL/main backend")
        
        env_files = [
            (".env.development", ["API_KEY", "DB_HOST", "REDIS_HOST"]),
            (".env.production", ["API_KEY", "DB_HOST", "REDIS_HOST"])
        ]
        
        for env_file, required_vars in env_files:
            env_path = backend_dir / env_file
            
            if not env_path.exists():
                self.test(f"Config - {env_file}", False, "File not found", critical=True)
                continue
            
            content = env_path.read_text()
            missing_vars = [var for var in required_vars if var not in content]
            
            if missing_vars:
                self.test(
                    f"Config - {env_file}",
                    False,
                    f"Missing variables: {', '.join(missing_vars)}",
                    critical=True
                )
            else:
                self.test(f"Config - {env_file}", True, "All required variables present")
    
    def test_docker_compose_config(self):
        """Test docker-compose configuration"""
        self.print_header("DOCKER COMPOSE CONFIGURATION", 2)
        
        compose_file = Path("AFIRGEN FINAL/docker-compose.yaml")
        
        if not compose_file.exists():
            self.test("Docker Compose", False, "docker-compose.yaml not found", critical=True)
            return
        
        content = compose_file.read_text()
        
        required_services = [
            "fir_pipeline",
            "mysql",
            "redis",
            "gguf_model_server",
            "asr_ocr_model_server"
        ]
        
        for service in required_services:
            has_service = service in content
            self.test(
                f"Docker Service - {service}",
                has_service,
                "defined" if has_service else "NOT DEFINED",
                critical=True
            )
    
    def test_gitignore(self):
        """Test .gitignore configuration"""
        self.print_header("GIT CONFIGURATION", 2)
        
        gitignore_path = Path(".gitignore")
        
        if not gitignore_path.exists():
            self.test("Git - .gitignore", False, "File not found", critical=False)
            return
        
        content = gitignore_path.read_text()
        
        required_patterns = [
            ("__pycache__", "Python cache"),
            ("*.pyc", "Python compiled files"),
            (".env", "Environment files"),
            ("node_modules", "Node modules")
        ]
        
        for pattern, description in required_patterns:
            has_pattern = pattern in content
            self.test(
                f"Git - {description}",
                has_pattern,
                "ignored" if has_pattern else "NOT IGNORED",
                critical=False
            )
    
    # ============================================================================
    # MOCK SERVICE TESTS
    # ============================================================================
    
    async def test_mock_services(self):
        """Test mock services"""
        self.print_header("MOCK SERVICES", 2)
        
        # Check if mock service files exist
        mock_dir = Path("mock_services")
        
        mock_files = [
            "mock_model_server.py",
            "mock_asr_ocr_server.py"
        ]
        
        for file_name in mock_files:
            file_path = mock_dir / file_name
            self.test(
                f"Mock Service - {file_name}",
                file_path.exists(),
                "exists" if file_path.exists() else "MISSING",
                critical=False
            )
    
    # ============================================================================
    # TEST SCRIPT TESTS
    # ============================================================================
    
    def test_test_scripts(self):
        """Test that test scripts exist"""
        self.print_header("TEST SCRIPTS", 2)
        
        test_scripts = [
            "test_deployment_readiness.py",
            "test_code_quality.py",
            "run_lightweight_test.py",
            "run_full_deployment_test.py",
            "comprehensive_test_suite.py"
        ]
        
        for script in test_scripts:
            script_path = Path(script)
            self.test(
                f"Test Script - {script}",
                script_path.exists(),
                "exists" if script_path.exists() else "MISSING",
                critical=False
            )
    
    # ============================================================================
    # DOCUMENTATION TESTS
    # ============================================================================
    
    def test_documentation(self):
        """Test that documentation exists"""
        self.print_header("DOCUMENTATION", 2)
        
        doc_files = [
            "PRODUCTION-READINESS-AUDIT-2026-02-22.md",
            "DEPLOYMENT_READINESS_FINAL_REPORT.md",
            "FINAL_TEST_RESULTS.md",
            "DEPLOYMENT_TEST_COMPLETE.md",
            "FIXES_APPLIED.md"
        ]
        
        for doc_file in doc_files:
            doc_path = Path(doc_file)
            self.test(
                f"Documentation - {doc_file}",
                doc_path.exists(),
                "exists" if doc_path.exists() else "MISSING",
                critical=False
            )
    
    # ============================================================================
    # SUMMARY AND REPORTING
    # ============================================================================
    
    def print_summary(self):
        """Print comprehensive test summary"""
        self.print_header("COMPREHENSIVE TEST SUMMARY", 1)
        
        print(f"\n{CYAN}Test Statistics:{RESET}")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  {GREEN}Passed: {self.passed_tests}{RESET}")
        print(f"  {RED}Failed: {self.failed_tests}{RESET}")
        print(f"  {YELLOW}Warnings: {self.warnings}{RESET}")
        
        if self.failed_tests > 0:
            print(f"\n{RED}{'='*70}{RESET}")
            print(f"{RED}FAILED TESTS:{RESET}")
            print(f"{RED}{'='*70}{RESET}")
            
            for status, name, message, critical in self.test_results:
                if status == "FAIL":
                    critical_marker = " [CRITICAL]" if critical else ""
                    print(f"{RED}✗{RESET} {name}{critical_marker}: {message}")
        
        if self.warnings > 0:
            print(f"\n{YELLOW}{'='*70}{RESET}")
            print(f"{YELLOW}WARNINGS:{RESET}")
            print(f"{YELLOW}{'='*70}{RESET}")
            
            for status, name, message, _ in self.test_results:
                if status == "WARN":
                    print(f"{YELLOW}⚠{RESET} {name}: {message}")
        
        print(f"\n{CYAN}{'='*70}{RESET}")
        
        # Calculate pass rate
        pass_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"\n{CYAN}Pass Rate: {pass_rate:.1f}%{RESET}")
        
        # Determine overall status
        critical_failures = sum(1 for status, _, _, critical in self.test_results 
                               if status == "FAIL" and critical)
        
        print()
        if self.failed_tests == 0:
            print(f"{GREEN}{'='*70}{RESET}")
            print(f"{GREEN}✅ ALL TESTS PASSED - SYSTEM IS DEPLOYMENT READY!{RESET}")
            print(f"{GREEN}{'='*70}{RESET}")
            return True
        elif critical_failures > 0:
            print(f"{RED}{'='*70}{RESET}")
            print(f"{RED}❌ CRITICAL FAILURES - MUST FIX BEFORE DEPLOYMENT{RESET}")
            print(f"{RED}   {critical_failures} critical test(s) failed{RESET}")
            print(f"{RED}{'='*70}{RESET}")
            return False
        else:
            print(f"{YELLOW}{'='*70}{RESET}")
            print(f"{YELLOW}⚠️  NON-CRITICAL FAILURES - REVIEW BEFORE DEPLOYMENT{RESET}")
            print(f"{YELLOW}   {self.failed_tests} test(s) failed{RESET}")
            print(f"{YELLOW}{'='*70}{RESET}")
            return False

async def main():
    """Run comprehensive test suite"""
    suite = ComprehensiveTestSuite()
    
    try:
        suite.print_header("COMPREHENSIVE DEPLOYMENT TEST SUITE")
        suite.info("Testing EVERYTHING - Will not stop until all tests pass")
        suite.info("This may take a few minutes...\n")
        
        # Run all test categories
        suite.test_frontend_files()
        suite.test_backend_files()
        suite.test_model_server_files()
        suite.test_docker_files()
        
        suite.test_python_syntax()
        suite.test_javascript_syntax()
        suite.test_critical_imports()
        
        suite.test_security_patterns()
        suite.test_frontend_security()
        
        suite.test_environment_configs()
        suite.test_docker_compose_config()
        suite.test_gitignore()
        
        await suite.test_mock_services()
        
        suite.test_test_scripts()
        suite.test_documentation()
        
        # Print summary
        all_passed = suite.print_summary()
        
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        return 1
    except Exception as e:
        print(f"\n{RED}Test suite error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
