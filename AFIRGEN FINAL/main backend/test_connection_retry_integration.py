"""
Integration tests for connection retry with database and Redis.

Tests the integration of connection retry logic with actual
database pool and Redis client implementations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import ConnectionError as RedisConnectionError

from infrastructure.database import DatabasePool, create_database_pool
from infrastructure.redis_client import RedisClient
from infrastructure.connection_retry import (
    DatabaseConnectionRetry,
    RedisConnectionRetry
)


class TestDatabasePoolWithRetry:
    """Test database pool integration with retry logic."""
    
    def test_database_pool_get_connection_with_retry(self):
        """Test database pool uses retry logic for connection acquisition."""
        # Mock MySQL pool
        mock_mysql_pool = Mock()
        mock_mysql_pool.pool_size = 10
        mock_conn = Mock()
        
        # Simulate transient failure then success
        attempts = [0]
        def get_connection_side_effect():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ConnectionError("Connection failed")
            return mock_conn
        
        mock_mysql_pool.get_connection = Mock(side_effect=get_connection_side_effect)
        
        # Create database pool with retry
        retry_handler = DatabaseConnectionRetry(max_retries=3, base_delay=0.1)
        pool = DatabasePool(mock_mysql_pool, retry_handler)
        
        # Get connection should succeed after retry
        conn = pool.get_connection()
        assert conn is not None
        assert attempts[0] == 2
    
    def test_database_pool_handles_non_retryable_errors(self):
        """Test database pool raises non-retryable errors immediately."""
        # Mock MySQL pool
        mock_mysql_pool = Mock()
        mock_mysql_pool.pool_size = 10
        
        # Simulate non-retryable error
        mock_mysql_pool.get_connection = Mock(side_effect=ValueError("Invalid config"))
        
        # Create database pool with retry
        retry_handler = DatabaseConnectionRetry(max_retries=3, base_delay=0.1)
        pool = DatabasePool(mock_mysql_pool, retry_handler)
        
        # Should raise immediately without retries
        with pytest.raises(ValueError):
            pool.get_connection()


class TestRedisClientWithRetry:
    """Test Redis client integration with retry logic."""
    
    @patch('infrastructure.redis_client.ConnectionPool')
    @patch('infrastructure.redis_client.redis.Redis')
    def test_redis_client_get_client_with_retry(self, mock_redis_class, mock_pool_class):
        """Test Redis client uses retry logic for client creation."""
        # Reset class state
        RedisClient._pool = None
        RedisClient._client = None
        RedisClient._retry_handler = None
        
        # Mock pool
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        
        # Simulate transient failure then success
        attempts = [0]
        def redis_side_effect(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] < 2:
                raise RedisConnectionError("Connection failed")
            return mock_client
        
        mock_redis_class.side_effect = redis_side_effect
        
        # Get client should succeed after retry
        client = RedisClient.get_client()
        assert client == mock_client
        assert attempts[0] == 2
        
        # Cleanup
        RedisClient._pool = None
        RedisClient._client = None
        RedisClient._retry_handler = None
    
    @patch('infrastructure.redis_client.ConnectionPool')
    def test_redis_client_ping_with_retry(self, mock_pool_class):
        """Test Redis client ping uses retry logic."""
        # Reset class state
        RedisClient._pool = None
        RedisClient._client = None
        RedisClient._retry_handler = None
        
        # Mock pool
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        # Mock Redis client with ping that fails then succeeds
        mock_client = Mock()
        attempts = [0]
        def ping_side_effect():
            attempts[0] += 1
            if attempts[0] < 2:
                raise RedisConnectionError("Connection failed")
            return True
        
        mock_client.ping = Mock(side_effect=ping_side_effect)
        
        # Patch get_client to return our mock
        with patch.object(RedisClient, 'get_client', return_value=mock_client):
            result = RedisClient.ping()
            assert result is True
            assert attempts[0] == 2
        
        # Cleanup
        RedisClient._pool = None
        RedisClient._client = None
        RedisClient._retry_handler = None


class TestCreateDatabasePoolWithRetry:
    """Test create_database_pool function with retry logic."""
    
    def test_create_database_pool_with_custom_retry_handler(self):
        """Test database pool accepts custom retry handler."""
        mock_pool = Mock()
        mock_pool.pool_size = 10
        
        # Create custom retry handler
        retry_handler = DatabaseConnectionRetry(max_retries=5, base_delay=2.0)
        
        # Create database pool with custom retry handler
        pool = DatabasePool(mock_pool, retry_handler)
        
        # Verify retry handler is set
        assert pool._retry_handler.retry_handler.max_retries == 5
        assert pool._retry_handler.retry_handler.base_delay == 2.0
    
    def test_database_pool_uses_default_retry_handler(self):
        """Test database pool creates default retry handler if not provided."""
        mock_pool = Mock()
        mock_pool.pool_size = 10
        
        # Create database pool without retry handler
        pool = DatabasePool(mock_pool)
        
        # Verify default retry handler is created
        assert pool._retry_handler is not None
        assert pool._retry_handler.retry_handler.max_retries == 3
        assert pool._retry_handler.retry_handler.base_delay == 1.0
