"""
Test for GET /health endpoint
Tests Requirements 24.1-24.8
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Set environment variables before importing the app
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['DB_HOST'] = 'test-host'
os.environ['DB_PASSWORD'] = 'test-password'
os.environ['API_KEY'] = 'test-api-key'
os.environ['AWS_REGION'] = 'us-east-1'

# Mock the database and AWS clients before importing the app
with patch('agentv5_clean.DatabaseManager'), \
     patch('agentv5_clean.AWSServiceClients'):
    from agentv5_clean import app, config


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_endpoint_exists(client):
    """Test that /health endpoint exists and returns 200"""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_no_auth_required(client):
    """Test that /health endpoint does not require API key authentication"""
    # Should work without X-API-Key header
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client):
    """Test that /health response has correct structure"""
    response = client.get("/health")
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "checks" in data
    assert "timestamp" in data
    
    # Check status is either "healthy" or "unhealthy"
    assert data["status"] in ["healthy", "unhealthy"]
    
    # Check checks is a dictionary
    assert isinstance(data["checks"], dict)
    
    # Check timestamp is a string
    assert isinstance(data["timestamp"], str)


def test_health_checks_include_mysql_and_bedrock(client):
    """Test that health checks include MySQL and Bedrock"""
    response = client.get("/health")
    data = response.json()
    
    checks = data["checks"]
    assert "mysql" in checks
    assert "bedrock" in checks
    
    # Check values are boolean
    assert isinstance(checks["mysql"], bool)
    assert isinstance(checks["bedrock"], bool)


@patch('agentv5_clean.db_manager')
@patch('agentv5_clean.boto3.client')
def test_health_status_healthy_when_all_pass(mock_boto3_client, mock_db_manager, client):
    """Test that status is 'healthy' when all checks pass"""
    # Mock MySQL connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db_manager.mysql_pool.get_connection.return_value = mock_conn
    
    # Mock Bedrock client
    mock_bedrock = MagicMock()
    mock_bedrock.list_foundation_models.return_value = {}
    mock_boto3_client.return_value = mock_bedrock
    
    with patch('agentv5_clean.db_manager', mock_db_manager), \
         patch('agentv5_clean.boto3.client', mock_boto3_client):
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["checks"]["mysql"] == True
        assert data["checks"]["bedrock"] == True


@patch('agentv5_clean.db_manager')
@patch('agentv5_clean.boto3.client')
def test_health_status_unhealthy_when_mysql_fails(mock_boto3_client, mock_db_manager, client):
    """Test that status is 'unhealthy' when MySQL check fails"""
    # Mock MySQL connection failure
    mock_db_manager.mysql_pool.get_connection.side_effect = Exception("Connection failed")
    
    # Mock Bedrock client (working)
    mock_bedrock = MagicMock()
    mock_bedrock.list_foundation_models.return_value = {}
    mock_boto3_client.return_value = mock_bedrock
    
    with patch('agentv5_clean.db_manager', mock_db_manager), \
         patch('agentv5_clean.boto3.client', mock_boto3_client):
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["checks"]["mysql"] == False


@patch('agentv5_clean.db_manager')
@patch('agentv5_clean.boto3.client')
def test_health_status_unhealthy_when_bedrock_fails(mock_boto3_client, mock_db_manager, client):
    """Test that status is 'unhealthy' when Bedrock check fails"""
    # Mock MySQL connection (working)
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db_manager.mysql_pool.get_connection.return_value = mock_conn
    
    # Mock Bedrock client failure
    mock_boto3_client.side_effect = Exception("Bedrock unavailable")
    
    with patch('agentv5_clean.db_manager', mock_db_manager), \
         patch('agentv5_clean.boto3.client', mock_boto3_client):
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["checks"]["bedrock"] == False


@patch('agentv5_clean.db_manager')
@patch('agentv5_clean.boto3.client')
def test_health_status_unhealthy_when_all_fail(mock_boto3_client, mock_db_manager, client):
    """Test that status is 'unhealthy' when all checks fail"""
    # Mock MySQL connection failure
    mock_db_manager.mysql_pool.get_connection.side_effect = Exception("Connection failed")
    
    # Mock Bedrock client failure
    mock_boto3_client.side_effect = Exception("Bedrock unavailable")
    
    with patch('agentv5_clean.db_manager', mock_db_manager), \
         patch('agentv5_clean.boto3.client', mock_boto3_client):
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["checks"]["mysql"] == False
        assert data["checks"]["bedrock"] == False


def test_health_timestamp_format(client):
    """Test that timestamp is in ISO format"""
    response = client.get("/health")
    data = response.json()
    
    timestamp = data["timestamp"]
    # Should be able to parse as ISO format
    try:
        # Remove 'Z' suffix and parse
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"Timestamp '{timestamp}' is not in valid ISO format")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
