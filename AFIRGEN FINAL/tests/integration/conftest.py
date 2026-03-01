"""
Pytest configuration for integration tests.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that call real AWS services"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires --integration flag)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --integration flag is provided."""
    if config.getoption("--integration"):
        return
    
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def aws_region():
    """Get AWS region from environment."""
    region = os.getenv("AWS_REGION", "us-east-1")
    return region


@pytest.fixture(scope="session")
def s3_bucket():
    """Get S3 bucket name from environment."""
    bucket = os.getenv("S3_BUCKET_NAME")
    if not bucket:
        pytest.skip("S3_BUCKET_NAME environment variable not set")
    return bucket


@pytest.fixture(scope="session")
def kms_key_id():
    """Get KMS key ID from environment."""
    return os.getenv("KMS_KEY_ID")


@pytest.fixture(scope="session")
def bedrock_model_id():
    """Get Bedrock model ID from environment."""
    return os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")


@pytest.fixture(scope="session")
def embeddings_model_id():
    """Get embeddings model ID from environment."""
    return os.getenv("BEDROCK_EMBEDDINGS_MODEL_ID", "amazon.titan-embed-text-v1")


@pytest.fixture(scope="session")
def vector_db_type():
    """Get vector database type from environment."""
    db_type = os.getenv("VECTOR_DB_TYPE", "opensearch")
    return db_type


@pytest.fixture(scope="session")
def opensearch_endpoint():
    """Get OpenSearch endpoint from environment."""
    return os.getenv("OPENSEARCH_ENDPOINT")


@pytest.fixture(scope="session")
def aurora_config():
    """Get Aurora configuration from environment."""
    return {
        "host": os.getenv("AURORA_HOST"),
        "port": int(os.getenv("AURORA_PORT", "5432")),
        "database": os.getenv("AURORA_DATABASE"),
        "user": os.getenv("AURORA_USER"),
        "password": os.getenv("AURORA_PASSWORD"),
        "table": os.getenv("AURORA_TABLE_NAME", "ipc_sections")
    }
