"""
Redis client setup and connection management with retry logic.

This module provides Redis connection pooling and client initialization
for the caching layer with automatic retry on connection failures.

Requirements: 6.4
"""

import redis
from redis.connection import ConnectionPool
from typing import Optional

from .config import config
from .connection_retry import RedisConnectionRetry
from .logging import get_logger


logger = get_logger(__name__)


class RedisClient:
    """Redis client wrapper with connection pooling and retry logic."""
    
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _retry_handler: Optional[RedisConnectionRetry] = None
    
    @classmethod
    def _get_retry_handler(cls) -> RedisConnectionRetry:
        """Get or create Redis connection retry handler."""
        if cls._retry_handler is None:
            cls._retry_handler = RedisConnectionRetry(
                max_retries=3,
                base_delay=0.5,
                max_delay=10.0
            )
        return cls._retry_handler
    
    @classmethod
    def get_pool(cls) -> ConnectionPool:
        """
        Get or create Redis connection pool with retry logic.
        
        Validates: Requirements 6.4
        """
        if cls._pool is None:
            retry_handler = cls._get_retry_handler()
            
            def _create_pool():
                return ConnectionPool(
                    host=config.redis.host,
                    port=config.redis.port,
                    db=config.redis.db,
                    password=config.redis.password,
                    max_connections=config.redis.max_connections,
                    socket_timeout=config.redis.socket_timeout,
                    socket_connect_timeout=config.redis.socket_connect_timeout,
                    decode_responses=config.redis.decode_responses
                )
            
            cls._pool = retry_handler.execute_with_retry(
                _create_pool,
                operation_name="create Redis connection pool"
            )
            logger.info("Redis connection pool created successfully")
        
        return cls._pool
    
    @classmethod
    def get_client(cls) -> redis.Redis:
        """
        Get or create Redis client instance with retry logic.
        
        Validates: Requirements 6.4
        """
        if cls._client is None:
            retry_handler = cls._get_retry_handler()
            
            def _create_client():
                pool = cls.get_pool()
                client = redis.Redis(connection_pool=pool)
                # Test connection
                client.ping()
                return client
            
            cls._client = retry_handler.execute_with_retry(
                _create_client,
                operation_name="create Redis client"
            )
            logger.info("Redis client created and connected successfully")
        
        return cls._client
    
    @classmethod
    def close(cls):
        """Close Redis connection pool."""
        if cls._pool is not None:
            cls._pool.disconnect()
            cls._pool = None
            cls._client = None
    
    @classmethod
    def ping(cls) -> bool:
        """
        Check if Redis connection is alive with retry logic.
        
        Validates: Requirements 6.4
        """
        try:
            retry_handler = cls._get_retry_handler()
            
            def _ping():
                client = cls.get_client()
                return client.ping()
            
            return retry_handler.execute_with_retry(
                _ping,
                operation_name="ping Redis"
            )
        except Exception as e:
            logger.error("Redis ping failed after retries", error=str(e))
            return False


# Convenience function to get Redis client
def get_redis_client() -> redis.Redis:
    """Get Redis client instance for dependency injection."""
    return RedisClient.get_client()
