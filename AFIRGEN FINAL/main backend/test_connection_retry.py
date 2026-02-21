"""
Unit tests for connection retry logic.

Tests database and Redis connection retry functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from infrastructure.connection_retry import (
    DatabaseConnectionRetry,
    RedisConnectionRetry,
    with_db_retry,
    with_redis_retry,
    get_db_connection_retry,
    get_redis_connection_retry
)


class TestDatabaseConnectionRetry:
    """Test database connection retry functionality."""
    
    def test_successful_connection_on_first_attempt(self):
        """Test successful connection without retries."""
        retry = DatabaseConnectionRetry(max_retries=3)
        mock_conn = Mock()
        
        def connect():
            return mock_conn
        
        result = retry.connect_with_retry(connect, "test-db")
        assert result == mock_conn
    
    def test_connection_succeeds_after_retries(self):
        """Test connection succeeds after transient failures."""
        retry = DatabaseConnectionRetry(max_retries=3, base_delay=0.1)
        mock_conn = Mock()
        attempts = [0]
        
        def connect():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("Connection failed")
            return mock_conn
        
        result = retry.connect_with_retry(connect, "test-db")
        assert result == mock_conn
        assert attempts[0] == 3

    def test_connection_fails_after_max_retries(self):
        """Test connection fails after exhausting retries."""
        retry = DatabaseConnectionRetry(max_retries=2, base_delay=0.1)
        
        def connect():
            raise ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            retry.connect_with_retry(connect, "test-db")
    
    def test_non_retryable_error_raised_immediately(self):
        """Test non-retryable errors are not retried."""
        retry = DatabaseConnectionRetry(max_retries=3, base_delay=0.1)
        attempts = [0]
        
        def connect():
            attempts[0] += 1
            raise ValueError("Invalid configuration")
        
        with pytest.raises(ValueError):
            retry.connect_with_retry(connect, "test-db")
        
        # Should only attempt once (no retries for non-retryable errors)
        assert attempts[0] == 1
    
    def test_execute_with_retry_success(self):
        """Test execute_with_retry for successful operation."""
        retry = DatabaseConnectionRetry(max_retries=3)
        
        def operation():
            return "success"
        
        result = retry.execute_with_retry(operation, "test-operation")
        assert result == "success"
    
    def test_execute_with_retry_after_failures(self):
        """Test execute_with_retry succeeds after transient failures."""
        retry = DatabaseConnectionRetry(max_retries=3, base_delay=0.1)
        attempts = [0]
        
        def operation():
            attempts[0] += 1
            if attempts[0] < 2:
                raise TimeoutError("Operation timeout")
            return "success"
        
        result = retry.execute_with_retry(operation, "test-operation")
        assert result == "success"
        assert attempts[0] == 2


class TestRedisConnectionRetry:
    """Test Redis connection retry functionality."""
    
    def test_successful_redis_connection_on_first_attempt(self):
        """Test successful Redis connection without retries."""
        retry = RedisConnectionRetry(max_retries=3)
        mock_client = Mock(spec=redis.Redis)
        mock_client.ping.return_value = True
        
        def connect():
            return mock_client
        
        result = retry.connect_with_retry(connect, "test-redis")
        assert result == mock_client
        mock_client.ping.assert_called_once()
    
    def test_redis_connection_succeeds_after_retries(self):
        """Test Redis connection succeeds after transient failures."""
        retry = RedisConnectionRetry(max_retries=3, base_delay=0.1)
        mock_client = Mock(spec=redis.Redis)
        mock_client.ping.return_value = True
        attempts = [0]
        
        def connect():
            attempts[0] += 1
            if attempts[0] < 3:
                raise RedisConnectionError("Connection failed")
            return mock_client
        
        result = retry.connect_with_retry(connect, "test-redis")
        assert result == mock_client
        assert attempts[0] == 3
    
    def test_redis_connection_fails_after_max_retries(self):
        """Test Redis connection fails after exhausting retries."""
        retry = RedisConnectionRetry(max_retries=2, base_delay=0.1)
        
        def connect():
            raise RedisConnectionError("Connection failed")
        
        with pytest.raises(RedisConnectionError):
            retry.connect_with_retry(connect, "test-redis")
    
    def test_redis_execute_with_retry_success(self):
        """Test Redis execute_with_retry for successful operation."""
        retry = RedisConnectionRetry(max_retries=3)
        
        def operation():
            return "cached_value"
        
        result = retry.execute_with_retry(operation, "get-key")
        assert result == "cached_value"


class TestConnectionRetryDecorators:
    """Test connection retry decorators."""
    
    def test_with_db_retry_decorator_success(self):
        """Test with_db_retry decorator for successful operation."""
        @with_db_retry(max_retries=3, base_delay=0.1)
        def fetch_data():
            return "data"
        
        result = fetch_data()
        assert result == "data"
    
    def test_with_db_retry_decorator_with_retries(self):
        """Test with_db_retry decorator retries on failure."""
        attempts = [0]
        
        @with_db_retry(max_retries=3, base_delay=0.1)
        def fetch_data():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ConnectionError("Connection failed")
            return "data"
        
        result = fetch_data()
        assert result == "data"
        assert attempts[0] == 2
    
    def test_with_redis_retry_decorator_success(self):
        """Test with_redis_retry decorator for successful operation."""
        @with_redis_retry(max_retries=3, base_delay=0.1)
        def get_cached():
            return "cached"
        
        result = get_cached()
        assert result == "cached"
    
    def test_with_redis_retry_decorator_with_retries(self):
        """Test with_redis_retry decorator retries on failure."""
        attempts = [0]
        
        @with_redis_retry(max_retries=3, base_delay=0.1)
        def get_cached():
            attempts[0] += 1
            if attempts[0] < 2:
                raise RedisConnectionError("Connection failed")
            return "cached"
        
        result = get_cached()
        assert result == "cached"
        assert attempts[0] == 2


class TestConnectionRetryFactories:
    """Test factory functions for connection retry."""
    
    def test_get_db_connection_retry_factory(self):
        """Test database connection retry factory."""
        retry = get_db_connection_retry(max_retries=5, base_delay=2.0)
        assert retry.retry_handler.max_retries == 5
        assert retry.retry_handler.base_delay == 2.0
    
    def test_get_redis_connection_retry_factory(self):
        """Test Redis connection retry factory."""
        retry = get_redis_connection_retry(max_retries=5, base_delay=1.0)
        assert retry.retry_handler.max_retries == 5
        assert retry.retry_handler.base_delay == 1.0
