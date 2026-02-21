"""
Connection retry logic for database and Redis connections.

This module provides retry wrappers for database and Redis connections
to handle transient connection failures gracefully.

Validates: Requirements 6.4
"""

from typing import Optional, Callable, Any
from functools import wraps
import redis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
    BusyLoadingError,
    ResponseError
)

from .retry_handler import RetryHandler, ErrorClassifier
from .error_classification import ErrorCategory
from .logging import get_logger


logger = get_logger(__name__)


# Register Redis-specific exceptions as retryable
def _setup_redis_error_classification():
    """Register Redis connection errors as retryable."""
    classifier = ErrorClassifier()
    classifier.register_retryable(
        RedisConnectionError,
        RedisTimeoutError,
        BusyLoadingError,
        ConnectionRefusedError,
        ConnectionResetError,
        BrokenPipeError
    )
    return classifier


# Create classifier with Redis exceptions registered
_redis_classifier = _setup_redis_error_classification()


class DatabaseConnectionRetry:
    """
    Database connection retry wrapper.
    
    Provides retry logic for database connection operations with
    exponential backoff for transient connection failures.
    
    Validates: Requirements 6.4
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize database connection retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for first retry (default: 1.0)
            max_delay: Maximum delay in seconds between retries (default: 30.0)
            exponential_base: Base for exponential backoff (default: 2.0)
        """
        self.retry_handler = RetryHandler(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=True
        )
    
    def connect_with_retry(
        self,
        connect_func: Callable[[], Any],
        connection_name: str = "database"
    ) -> Any:
        """
        Attempt to establish a database connection with retry logic.
        
        Args:
            connect_func: Function that establishes the connection
            connection_name: Name of the connection for logging (default: "database")
            
        Returns:
            Database connection object
            
        Raises:
            Exception: If all retry attempts are exhausted
            
        Example:
            >>> retry = DatabaseConnectionRetry(max_retries=3)
            >>> def connect():
            ...     return mysql.connector.connect(**config)
            >>> conn = retry.connect_with_retry(connect, "mysql")
            
        Validates: Requirements 6.4
        """
        logger.info("Attempting to connect", connection_name=connection_name)
        
        try:
            connection = self.retry_handler.execute_with_retry(
                connect_func,
                retryable_exceptions=None  # Use automatic classification
            )
            logger.info("Successfully connected", connection_name=connection_name)
            return connection
        except Exception as e:
            logger.error(
                "Failed to connect after retries",
                connection_name=connection_name,
                max_retries=self.retry_handler.max_retries,
                error=str(e)
            )
            raise
    
    def execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str = "database operation"
    ) -> Any:
        """
        Execute a database operation with retry logic.
        
        Args:
            operation: Function that performs the database operation
            operation_name: Name of the operation for logging
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If all retry attempts are exhausted
            
        Example:
            >>> retry = DatabaseConnectionRetry()
            >>> def query():
            ...     cursor.execute("SELECT * FROM users")
            ...     return cursor.fetchall()
            >>> results = retry.execute_with_retry(query, "fetch users")
            
        Validates: Requirements 6.4
        """
        try:
            return self.retry_handler.execute_with_retry(
                operation,
                retryable_exceptions=None
            )
        except Exception as e:
            logger.error(
                "Failed to execute database operation after retries",
                operation_name=operation_name,
                max_retries=self.retry_handler.max_retries,
                error=str(e)
            )
            raise


class RedisConnectionRetry:
    """
    Redis connection retry wrapper.
    
    Provides retry logic for Redis connection operations with
    exponential backoff for transient connection failures.
    
    Validates: Requirements 6.4
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize Redis connection retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for first retry (default: 0.5)
            max_delay: Maximum delay in seconds between retries (default: 10.0)
            exponential_base: Base for exponential backoff (default: 2.0)
        """
        self.retry_handler = RetryHandler(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=True,
            error_classifier=_redis_classifier
        )
    
    def connect_with_retry(
        self,
        connect_func: Callable[[], redis.Redis],
        connection_name: str = "redis"
    ) -> redis.Redis:
        """
        Attempt to establish a Redis connection with retry logic.
        
        Args:
            connect_func: Function that establishes the Redis connection
            connection_name: Name of the connection for logging (default: "redis")
            
        Returns:
            Redis client object
            
        Raises:
            Exception: If all retry attempts are exhausted
            
        Example:
            >>> retry = RedisConnectionRetry(max_retries=3)
            >>> def connect():
            ...     return redis.Redis(host='localhost', port=6379)
            >>> client = retry.connect_with_retry(connect, "redis-cache")
            
        Validates: Requirements 6.4
        """
        logger.info("Attempting to connect", connection_name=connection_name)
        
        try:
            client = self.retry_handler.execute_with_retry(
                connect_func,
                retryable_exceptions=None  # Use automatic classification
            )
            
            # Verify connection with ping
            def ping():
                return client.ping()
            
            self.retry_handler.execute_with_retry(
                ping,
                retryable_exceptions=None
            )
            
            logger.info("Successfully connected", connection_name=connection_name)
            return client
        except Exception as e:
            logger.error(
                "Failed to connect after retries",
                connection_name=connection_name,
                max_retries=self.retry_handler.max_retries,
                error=str(e)
            )
            raise
    
    def execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str = "redis operation"
    ) -> Any:
        """
        Execute a Redis operation with retry logic.
        
        Args:
            operation: Function that performs the Redis operation
            operation_name: Name of the operation for logging
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If all retry attempts are exhausted
            
        Example:
            >>> retry = RedisConnectionRetry()
            >>> def get_value():
            ...     return redis_client.get("my_key")
            >>> value = retry.execute_with_retry(get_value, "get my_key")
            
        Validates: Requirements 6.4
        """
        try:
            return self.retry_handler.execute_with_retry(
                operation,
                retryable_exceptions=None
            )
        except Exception as e:
            logger.error(
                "Failed to execute Redis operation after retries",
                operation_name=operation_name,
                max_retries=self.retry_handler.max_retries,
                error=str(e)
            )
            raise


def with_db_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """
    Decorator for adding database connection retry logic to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds between retries
        
    Returns:
        Decorated function with retry logic
        
    Example:
        >>> @with_db_retry(max_retries=3)
        ... def fetch_user(user_id: str):
        ...     conn = get_db_connection()
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        ...     return cursor.fetchone()
        
    Validates: Requirements 6.4
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry = DatabaseConnectionRetry(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay
            )
            return retry.execute_with_retry(
                lambda: func(*args, **kwargs),
                operation_name=func.__name__
            )
        return wrapper
    return decorator


def with_redis_retry(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0
):
    """
    Decorator for adding Redis connection retry logic to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds between retries
        
    Returns:
        Decorated function with retry logic
        
    Example:
        >>> @with_redis_retry(max_retries=3)
        ... def get_cached_value(key: str):
        ...     client = get_redis_client()
        ...     return client.get(key)
        
    Validates: Requirements 6.4
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry = RedisConnectionRetry(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay
            )
            return retry.execute_with_retry(
                lambda: func(*args, **kwargs),
                operation_name=func.__name__
            )
        return wrapper
    return decorator


# Factory functions for dependency injection
def get_db_connection_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
) -> DatabaseConnectionRetry:
    """
    Factory function to create a DatabaseConnectionRetry instance.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds between retries
        
    Returns:
        DatabaseConnectionRetry instance
    """
    return DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay
    )


def get_redis_connection_retry(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0
) -> RedisConnectionRetry:
    """
    Factory function to create a RedisConnectionRetry instance.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds between retries
        
    Returns:
        RedisConnectionRetry instance
    """
    return RedisConnectionRetry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay
    )
