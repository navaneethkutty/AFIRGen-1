"""
Pytest configuration for property-based tests
Handles mocking of external dependencies to allow tests to run without actual AWS/DB connections
"""

import pytest
import sys
from unittest.mock import MagicMock, Mock

# Mock external dependencies before any imports
def pytest_configure(config):
    """Configure pytest with necessary mocks"""
    # Mock mysql.connector to prevent actual database connections
    mock_mysql = MagicMock()
    mock_mysql.connector = MagicMock()
    mock_mysql.connector.pooling = MagicMock()
    mock_mysql.connector.Error = Exception
    sys.modules['mysql.connector'] = mock_mysql.connector
    sys.modules['mysql.connector.pooling'] = mock_mysql.connector.pooling
    
    # Mock boto3 to prevent actual AWS connections
    mock_boto3 = MagicMock()
    sys.modules['boto3'] = mock_boto3
    
    # Mock botocore
    mock_botocore = MagicMock()
    sys.modules['botocore'] = mock_botocore
    sys.modules['botocore.exceptions'] = mock_botocore.exceptions
