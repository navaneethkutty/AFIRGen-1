"""
Regression Tests for Bedrock Migration

This package contains regression tests for bugs discovered during
Task 12.5 (Bug Triage and Fixes). Each test verifies that a specific
bug has been fixed and prevents regression in future releases.

Test Naming Convention:
- test_bug_XXXX.py - Tests for specific bug ID
- test_<component>_<issue>.py - Tests for component-specific issues

Running Tests:
    pytest tests/regression/ -v
    pytest tests/regression/test_s3_encryption.py -v
"""
