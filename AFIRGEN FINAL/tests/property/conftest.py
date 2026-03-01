"""
Pytest configuration for property-based tests.
"""

import pytest
import sys
import os
from hypothesis import settings, Verbosity

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure Hypothesis settings
settings.register_profile("default", max_examples=50, deadline=None)
settings.register_profile("ci", max_examples=100, deadline=None)
settings.register_profile("dev", max_examples=20, deadline=None, verbosity=Verbosity.verbose)
settings.register_profile("debug", max_examples=10, deadline=None, verbosity=Verbosity.debug)

# Load profile from environment or use default
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture(scope="session")
def aws_region():
    """AWS region for testing."""
    return "us-east-1"


@pytest.fixture(scope="session")
def s3_bucket():
    """S3 bucket name for testing."""
    return "afirgen-test-bucket"


@pytest.fixture(scope="session")
def bedrock_model_id():
    """Bedrock model ID for testing."""
    return "anthropic.claude-3-sonnet-20240229-v1:0"


@pytest.fixture(scope="session")
def embeddings_model_id():
    """Titan Embeddings model ID for testing."""
    return "amazon.titan-embed-text-v1"
