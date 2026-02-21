#!/usr/bin/env python3
"""
run_property_tests.py
-----------------------------------------------------------------------------
Script to run all property-based tests with reduced iterations for faster execution.
-----------------------------------------------------------------------------

This script runs all 36 property tests with reduced iterations (10-20 instead of 100+)
to speed up test execution while still validating the properties.

Usage:
    python run_property_tests.py
"""

import sys
import subprocess
from pathlib import Path

# List of all property-based test files
PROPERTY_TEST_FILES = [
    # Dedicated property test files
    "test_property_api_tracking.py",
    "test_property_background_tasks.py",
    "test_property_cache_headers.py",
    "test_property_cache_tracking.py",
    "test_property_compression.py",
    "test_property_field_filter.py",
    "test_property_model_server_tracking.py",
    "test_property_pagination.py",
    "test_property_pagination_aggregation.py",
    "test_property_retry_backoff.py",
    "test_property_select_star.py",
    "test_property_task_retry.py",
    "test_property_threshold_alerting.py",
    
    # Other test files with property tests
    "test_circuit_breaker_property.py",
    "test_connection_retry_property.py",
    "test_correlation_id_property.py",
    "test_error_classification_property.py",
    "test_error_response_logging_property.py",
    "test_log_format_property.py",
    "test_query_optimizer.py",  # Contains property tests
]


def run_property_tests():
    """Run all property-based tests with reduced iterations."""
    
    print("=" * 80)
    print("Running All Property-Based Tests")
    print("=" * 80)
    print(f"\nTotal test files: {len(PROPERTY_TEST_FILES)}")
    print("\nNote: Tests are configured with max_examples=10-20 for faster execution")
    print("=" * 80)
    print()
    
    # Run pytest with property test marker
    # The tests already have @settings(max_examples=10-20) configured
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "-m", "property_test",
        "--tb=short",
        "--color=yes",
        *PROPERTY_TEST_FILES
    ]
    
    print(f"Running command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=False,
            text=True
        )
        
        print("\n" + "=" * 80)
        if result.returncode == 0:
            print("✓ All property-based tests PASSED!")
        else:
            print("✗ Some property-based tests FAILED!")
            print(f"Exit code: {result.returncode}")
        print("=" * 80)
        
        return result.returncode
        
    except Exception as e:
        print(f"\n✗ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_property_tests()
    sys.exit(exit_code)
