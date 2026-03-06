"""
Pytest configuration for AFIRGen backend tests.
Sets up environment variables and fixtures.
"""

import os
import sys
import pytest

# Set environment variables BEFORE any imports
os.environ["AWS_REGION"] = "us-east-1"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "3306"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password"
os.environ["DB_NAME"] = "test_db"
os.environ["API_KEY"] = "test-api-key"
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-3-sonnet-20240229-v1:0"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run"""
    yield
    # Cleanup is not needed as environment variables are process-scoped
