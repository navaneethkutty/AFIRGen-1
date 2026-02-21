#!/usr/bin/env python3
"""
Checkpoint 11 Verification Script
Verifies monitoring, error handling, and logging implementations
"""

import subprocess
import sys
from typing import List, Tuple

def run_test_suite(test_pattern: str, description: str) -> Tuple[bool, str]:
    """Run a test suite and return success status and output"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-v", test_pattern, "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"\n{status}: {description}")
        
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT: {description}")
        return False, "Test suite timed out"
    except Exception as e:
        print(f"✗ ERROR: {description} - {str(e)}")
        return False, str(e)

def main():
    """Run all checkpoint 11 verification tests"""
    print("="*80)
    print("CHECKPOINT 11: Monitoring, Error Handling, and Logging Verification")
    print("="*80)
    
    test_suites: List[Tuple[str, str]] = [
        # Monitoring tests (Task 8)
        ("test_property_api_tracking.py", "Property 21: API request tracking"),
        ("test_property_cache_tracking.py", "Property 22: Cache operation tracking"),
        ("test_property_model_server_tracking.py", "Property 23: Model server latency tracking"),
        ("test_property_threshold_alerting.py", "Property 24: Threshold alerting"),
        ("test_metrics_middleware.py", "Metrics middleware unit tests"),
        ("test_cache_db_metrics.py", "Cache and database metrics tests"),
        ("test_model_server_monitoring.py", "Model server monitoring tests"),
        ("test_alerting.py", "Alerting system tests"),
        ("test_prometheus_endpoint.py", "Prometheus endpoint tests"),
        
        # Error handling tests (Task 9)
        ("test_property_retry_backoff.py", "Property 25: Retry with exponential backoff"),
        ("test_error_classification_property.py", "Property 29: Error classification"),
        ("test_circuit_breaker_property.py", "Property 27: Circuit breaker pattern"),
        ("test_connection_retry_property.py", "Property 28: Connection retry"),
        ("test_error_response_logging_property.py", "Properties 26 & 30: Error response and logging"),
        ("test_retry_handler.py", "Retry handler unit tests"),
        ("test_error_classification.py", "Error classification unit tests"),
        ("test_circuit_breaker.py", "Circuit breaker unit tests"),
        ("test_connection_retry.py", "Connection retry unit tests"),
        ("test_error_response.py", "Error response formatting tests"),
        
        # Logging tests (Task 10)
        ("test_correlation_id_property.py", "Properties 31 & 32: Correlation ID generation and propagation"),
        ("test_log_format_property.py", "Properties 33, 34, 35: Log format, fields, and redaction"),
        ("test_correlation_id_middleware.py", "Correlation ID middleware unit tests"),
        ("test_structured_logging.py", "Structured logging unit tests"),
        ("test_logger_enhancements.py", "Logger enhancements tests"),
        ("test_tracing.py", "OpenTelemetry tracing tests"),
    ]
    
    results = []
    for test_file, description in test_suites:
        success, output = run_test_suite(test_file, description)
        results.append((description, success, output))
    
    # Summary
    print("\n" + "="*80)
    print("CHECKPOINT 11 VERIFICATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} test suites passed\n")
    
    for description, success, _ in results:
        status = "✓" if success else "✗"
        print(f"{status} {description}")
    
    # Detailed failure analysis
    failures = [(desc, output) for desc, success, output in results if not success]
    if failures:
        print("\n" + "="*80)
        print("FAILURE DETAILS")
        print("="*80)
        for desc, output in failures:
            print(f"\n{desc}:")
            print("-" * 80)
            # Print last 50 lines of output for context
            lines = output.split('\n')
            relevant_lines = lines[-50:] if len(lines) > 50 else lines
            print('\n'.join(relevant_lines))
    
    print("\n" + "="*80)
    if passed == total:
        print("✓ CHECKPOINT 11 VERIFICATION PASSED")
        print("All monitoring, error handling, and logging tests passed!")
        print("="*80)
        return 0
    else:
        print("✗ CHECKPOINT 11 VERIFICATION FAILED")
        print(f"{total - passed} test suite(s) failed. Review the details above.")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
