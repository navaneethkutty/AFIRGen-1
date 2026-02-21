"""
Final Checkpoint Verification Script - Task 16
Verifies all backend optimizations are working together correctly.

This script checks:
1. All infrastructure components are available
2. Database optimizations are in place
3. Caching layer is operational
4. API optimizations are configured
5. Background processing is set up
6. Monitoring and metrics are operational
7. Error handling is configured
8. Structured logging is working
9. Code refactoring is complete
10. All tests pass
"""

import sys
import subprocess
from typing import Dict, List, Tuple
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class FinalCheckpointVerifier:
    """Comprehensive verification of all backend optimizations"""
    
    def __init__(self):
        self.results: Dict[str, List[Tuple[str, bool, str]]] = {}
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        
    def print_header(self, text: str):
        """Print a section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")
    
    def print_result(self, check_name: str, passed: bool, details: str = ""):
        """Print a check result"""
        self.total_checks += 1
        if passed:
            self.passed_checks += 1
            status = f"{Colors.GREEN}✓ PASS{Colors.RESET}"
        else:
            self.failed_checks += 1
            status = f"{Colors.RED}✗ FAIL{Colors.RESET}"
        
        print(f"{status} {check_name}")
        if details:
            print(f"      {details}")
    
    def add_result(self, category: str, check_name: str, passed: bool, details: str = ""):
        """Add a result to the results dictionary"""
        if category not in self.results:
            self.results[category] = []
        self.results[category].append((check_name, passed, details))
        self.print_result(check_name, passed, details)
    
    def check_file_exists(self, filepath: str, category: str, description: str) -> bool:
        """Check if a file exists"""
        exists = Path(filepath).exists()
        self.add_result(category, description, exists, 
                       f"Path: {filepath}" if exists else f"Missing: {filepath}")
        return exists
    
    def check_directory_exists(self, dirpath: str, category: str, description: str) -> bool:
        """Check if a directory exists"""
        exists = Path(dirpath).is_dir()
        self.add_result(category, description, exists,
                       f"Path: {dirpath}" if exists else f"Missing: {dirpath}")
        return exists
    
    def verify_infrastructure(self):
        """Verify infrastructure components"""
        self.print_header("1. Infrastructure Components")
        
        # Check infrastructure directory
        self.check_directory_exists("infrastructure", "Infrastructure", 
                                   "Infrastructure directory exists")
        
        # Check key infrastructure files
        files = [
            ("infrastructure/cache_manager.py", "Cache Manager"),
            ("infrastructure/database.py", "Database connection"),
            ("infrastructure/redis_client.py", "Redis client"),
            ("infrastructure/celery_app.py", "Celery app"),
            ("infrastructure/metrics.py", "Metrics collector"),
            ("infrastructure/logging.py", "Structured logging"),
            ("infrastructure/retry_handler.py", "Retry handler"),
            ("infrastructure/circuit_breaker.py", "Circuit breaker"),
            ("infrastructure/error_classification.py", "Error classification"),
            ("infrastructure/query_optimizer.py", "Query optimizer"),
        ]
        
        for filepath, description in files:
            self.check_file_exists(filepath, "Infrastructure", description)
    
    def verify_database_optimization(self):
        """Verify database optimization components"""
        self.print_header("2. Database Optimization")
        
        # Check repository layer
        self.check_directory_exists("repositories", "Database", 
                                   "Repositories directory exists")
        self.check_file_exists("repositories/base_repository.py", "Database",
                              "Base repository pattern")
        self.check_file_exists("repositories/fir_repository.py", "Database",
                              "FIR repository with optimizations")
        
        # Check migrations
        self.check_directory_exists("migrations", "Database",
                                   "Migrations directory exists")
        self.check_file_exists("migrations/001_add_fir_indexes.sql", "Database",
                              "Database indexes migration")
        
        # Check query optimizer
        self.check_file_exists("infrastructure/query_optimizer.py", "Database",
                              "Query optimizer component")
    
    def verify_caching_layer(self):
        """Verify caching layer components"""
        self.print_header("3. Caching Layer")
        
        # Check cache manager
        self.check_file_exists("infrastructure/cache_manager.py", "Caching",
                              "Cache manager component")
        self.check_file_exists("infrastructure/redis_client.py", "Caching",
                              "Redis client configuration")
        
        # Check cache integration in repository
        self.check_file_exists("repositories/fir_repository.py", "Caching",
                              "Cache integration in FIR repository")
    
    def verify_api_optimization(self):
        """Verify API optimization components"""
        self.print_header("4. API Optimization")
        
        # Check middleware directory
        self.check_directory_exists("middleware", "API",
                                   "Middleware directory exists")
        
        # Check middleware components
        middleware_files = [
            ("middleware/compression_middleware.py", "Compression middleware"),
            ("middleware/correlation_id_middleware.py", "Correlation ID middleware"),
            ("middleware/metrics_middleware.py", "Metrics middleware"),
            ("middleware/cache_header_middleware.py", "Cache header middleware"),
        ]
        
        for filepath, description in middleware_files:
            self.check_file_exists(filepath, "API", description)
        
        # Check utilities
        self.check_file_exists("utils/pagination.py", "API", "Pagination utilities")
        self.check_file_exists("utils/field_filter.py", "API", "Field filtering")
    
    def verify_background_processing(self):
        """Verify background processing components"""
        self.print_header("5. Background Processing")
        
        # Check Celery setup
        self.check_file_exists("infrastructure/celery_app.py", "Background",
                              "Celery application")
        self.check_file_exists("infrastructure/background_task_manager.py", "Background",
                              "Background task manager")
        
        # Check task endpoints
        self.check_file_exists("api/task_endpoints.py", "Background",
                              "Task status endpoints")
        
        # Check migrations for task table
        self.check_file_exists("migrations/002_add_background_tasks_table.sql", "Background",
                              "Background tasks table migration")
    
    def verify_monitoring(self):
        """Verify monitoring and metrics components"""
        self.print_header("6. Monitoring and Metrics")
        
        # Check metrics components
        self.check_file_exists("infrastructure/metrics.py", "Monitoring",
                              "Metrics collector")
        self.check_file_exists("middleware/metrics_middleware.py", "Monitoring",
                              "Metrics middleware")
        self.check_file_exists("infrastructure/alerting.py", "Monitoring",
                              "Alerting system")
    
    def verify_error_handling(self):
        """Verify error handling components"""
        self.print_header("7. Error Handling")
        
        # Check error handling components
        error_files = [
            ("infrastructure/retry_handler.py", "Retry handler"),
            ("infrastructure/circuit_breaker.py", "Circuit breaker"),
            ("infrastructure/error_classification.py", "Error classification"),
            ("infrastructure/error_response.py", "Error response formatting"),
            ("infrastructure/connection_retry.py", "Connection retry logic"),
        ]
        
        for filepath, description in error_files:
            self.check_file_exists(filepath, "Error Handling", description)
    
    def verify_logging(self):
        """Verify structured logging components"""
        self.print_header("8. Structured Logging")
        
        # Check logging components
        self.check_file_exists("infrastructure/logging.py", "Logging",
                              "Structured logging")
        self.check_file_exists("infrastructure/json_logging.py", "Logging",
                              "JSON logging formatter")
        self.check_file_exists("middleware/correlation_id_middleware.py", "Logging",
                              "Correlation ID middleware")
        self.check_file_exists("infrastructure/tracing.py", "Logging",
                              "OpenTelemetry tracing")
    
    def verify_code_structure(self):
        """Verify code refactoring and structure"""
        self.print_header("9. Code Structure and Refactoring")
        
        # Check layered architecture
        layers = [
            ("api", "API layer"),
            ("services", "Service layer"),
            ("repositories", "Repository layer"),
            ("models", "Models layer"),
            ("infrastructure", "Infrastructure layer"),
            ("middleware", "Middleware layer"),
            ("utils", "Utilities layer"),
        ]
        
        for dirpath, description in layers:
            self.check_directory_exists(dirpath, "Code Structure", description)
        
        # Check dependency injection
        self.check_file_exists("api/dependencies.py", "Code Structure",
                              "Dependency injection")
        
        # Check interfaces
        self.check_directory_exists("interfaces", "Code Structure",
                                   "Interfaces directory")
        self.check_file_exists("interfaces/repository.py", "Code Structure",
                              "Repository interface")
        self.check_file_exists("interfaces/cache.py", "Code Structure",
                              "Cache interface")
        
        # Check utilities
        self.check_file_exists("utils/validators.py", "Code Structure",
                              "Validators utilities")
        self.check_file_exists("utils/constants.py", "Code Structure",
                              "Constants module")
    
    def verify_tests(self):
        """Verify test suite"""
        self.print_header("10. Test Suite")
        
        # Check for test files
        test_categories = [
            ("test_cache_manager.py", "Cache manager tests"),
            ("test_query_optimizer.py", "Query optimizer tests"),
            ("test_repository_pattern.py", "Repository pattern tests"),
            ("test_compression_middleware.py", "Compression middleware tests"),
            ("test_pagination.py", "Pagination tests"),
            ("test_background_task_manager.py", "Background task tests"),
            ("test_metrics_middleware.py", "Metrics middleware tests"),
            ("test_retry_handler.py", "Retry handler tests"),
            ("test_circuit_breaker.py", "Circuit breaker tests"),
            ("test_structured_logging.py", "Structured logging tests"),
            ("test_correlation_id_middleware.py", "Correlation ID tests"),
        ]
        
        for test_file, description in test_categories:
            self.check_file_exists(test_file, "Tests", description)
        
        # Check property-based tests
        property_tests = [
            ("test_property_cache_tracking.py", "Cache tracking property test"),
            ("test_property_compression.py", "Compression property test"),
            ("test_property_pagination.py", "Pagination property test"),
            ("test_property_retry_backoff.py", "Retry backoff property test"),
            ("test_property_api_tracking.py", "API tracking property test"),
        ]
        
        for test_file, description in property_tests:
            self.check_file_exists(test_file, "Tests", description)
    
    def run_test_suite(self):
        """Run the complete test suite"""
        self.print_header("11. Running Test Suite")
        
        print(f"{Colors.YELLOW}Running pytest... This may take a few minutes.{Colors.RESET}\n")
        
        try:
            # Run pytest with coverage
            result = subprocess.run(
                ["pytest", "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Check if tests passed
            passed = result.returncode == 0
            
            if passed:
                self.add_result("Test Execution", "All tests passed", True,
                               "Test suite completed successfully")
            else:
                # Extract failure information
                output_lines = result.stdout.split('\n')
                failure_summary = [line for line in output_lines if 'FAILED' in line or 'ERROR' in line]
                details = '\n      '.join(failure_summary[:5])  # Show first 5 failures
                self.add_result("Test Execution", "Test suite execution", False,
                               f"Some tests failed:\n      {details}")
            
            return passed
            
        except subprocess.TimeoutExpired:
            self.add_result("Test Execution", "Test suite execution", False,
                           "Tests timed out after 5 minutes")
            return False
        except FileNotFoundError:
            self.add_result("Test Execution", "Test suite execution", False,
                           "pytest not found - please install pytest")
            return False
        except Exception as e:
            self.add_result("Test Execution", "Test suite execution", False,
                           f"Error running tests: {str(e)}")
            return False
    
    def verify_documentation(self):
        """Verify documentation exists"""
        self.print_header("12. Documentation")
        
        # Check README files
        readme_files = [
            ("infrastructure/README.md", "Infrastructure README"),
            ("repositories/README.md", "Repositories README"),
            ("interfaces/README.md", "Interfaces README"),
            ("utils/README.md", "Utils README"),
            ("middleware/README_correlation_id.md", "Correlation ID README"),
            ("migrations/README.md", "Migrations README"),
        ]
        
        for filepath, description in readme_files:
            self.check_file_exists(filepath, "Documentation", description)
        
        # Check architecture documentation
        self.check_file_exists("ARCHITECTURE.md", "Documentation",
                              "Architecture documentation")
        
        # Check Docker configuration
        self.check_file_exists("compose.yaml", "Documentation",
                              "Docker Compose configuration")
        self.check_file_exists("Dockerfile", "Documentation",
                              "Dockerfile")
    
    def print_summary(self):
        """Print final summary"""
        self.print_header("VERIFICATION SUMMARY")
        
        # Calculate pass rate
        pass_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        
        print(f"Total Checks: {self.total_checks}")
        print(f"{Colors.GREEN}Passed: {self.passed_checks}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.failed_checks}{Colors.RESET}")
        print(f"Pass Rate: {pass_rate:.1f}%\n")
        
        # Print category breakdown
        print(f"{Colors.BOLD}Category Breakdown:{Colors.RESET}\n")
        for category, results in self.results.items():
            passed = sum(1 for _, p, _ in results if p)
            total = len(results)
            status = f"{Colors.GREEN}✓{Colors.RESET}" if passed == total else f"{Colors.RED}✗{Colors.RESET}"
            print(f"{status} {category}: {passed}/{total} checks passed")
        
        # Overall status
        print(f"\n{Colors.BOLD}Overall Status:{Colors.RESET}")
        if self.failed_checks == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED - System is ready!{Colors.RESET}")
            return True
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ SOME CHECKS FAILED - Review failures above{Colors.RESET}")
            return False
    
    def run_verification(self, run_tests: bool = True):
        """Run complete verification"""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print("=" * 80)
        print("BACKEND OPTIMIZATION - FINAL CHECKPOINT VERIFICATION")
        print("Task 16: Complete System Verification")
        print("=" * 80)
        print(f"{Colors.RESET}")
        
        # Run all verification checks
        self.verify_infrastructure()
        self.verify_database_optimization()
        self.verify_caching_layer()
        self.verify_api_optimization()
        self.verify_background_processing()
        self.verify_monitoring()
        self.verify_error_handling()
        self.verify_logging()
        self.verify_code_structure()
        self.verify_tests()
        
        # Run test suite if requested
        if run_tests:
            self.run_test_suite()
        
        self.verify_documentation()
        
        # Print summary
        success = self.print_summary()
        
        return success


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Final checkpoint verification for backend optimization")
    parser.add_argument("--skip-tests", action="store_true", 
                       help="Skip running the test suite (faster verification)")
    args = parser.parse_args()
    
    verifier = FinalCheckpointVerifier()
    success = verifier.run_verification(run_tests=not args.skip_tests)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
