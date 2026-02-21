"""
Database connection pool wrapper with metrics tracking and retry logic.

This module provides a wrapper around MySQL connection pool
that tracks connection pool utilization metrics and handles
connection failures with retry logic.

Requirements: 5.3, 6.4
"""

from typing import Optional, TYPE_CHECKING
from .metrics import MetricsCollector
from .connection_retry import DatabaseConnectionRetry
from .logging import get_logger

if TYPE_CHECKING:
    from mysql.connector import pooling


logger = get_logger(__name__)


class DatabasePool:
    """
    Database connection pool wrapper with metrics tracking and retry logic.
    
    Wraps MySQL connection pool and tracks:
    - Pool size
    - Available connections
    - Connection acquisition/release
    
    Provides automatic retry for connection failures.
    
    Validates: Requirements 5.3, 6.4
    """
    
    def __init__(self, pool, retry_handler: Optional[DatabaseConnectionRetry] = None):
        """
        Initialize database pool wrapper.
        
        Args:
            pool: MySQL connection pool instance
            retry_handler: Optional DatabaseConnectionRetry instance for connection retry
        """
        self._pool = pool
        self._pool_size = pool.pool_size
        self._active_connections = 0
        self._retry_handler = retry_handler or DatabaseConnectionRetry(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0
        )
    
    def get_connection(self):
        """
        Get a connection from the pool with retry logic and track metrics.
        
        Automatically retries on connection failures with exponential backoff.
        
        Returns:
            Database connection
            
        Validates: Requirements 5.3, 6.4
        """
        def _get_conn():
            try:
                conn = self._pool.get_connection()
                self._active_connections += 1
                
                # Update pool metrics
                available = self._pool_size - self._active_connections
                MetricsCollector.update_db_pool_metrics(
                    pool_size=self._pool_size,
                    available=available
                )
                
                # Wrap connection to track release
                return PooledConnection(conn, self)
            except Exception as e:
                logger.error("Failed to get database connection", error=str(e))
                raise
        
        # Use retry handler for connection acquisition
        return self._retry_handler.execute_with_retry(
            _get_conn,
            operation_name="get database connection"
        )
    
    def _release_connection(self):
        """
        Track connection release.
        
        Called by PooledConnection when connection is closed.
        """
        self._active_connections = max(0, self._active_connections - 1)
        
        # Update pool metrics
        available = self._pool_size - self._active_connections
        MetricsCollector.update_db_pool_metrics(
            pool_size=self._pool_size,
            available=available
        )
    
    @property
    def pool_size(self) -> int:
        """Get total pool size."""
        return self._pool_size
    
    @property
    def active_connections(self) -> int:
        """Get number of active connections."""
        return self._active_connections
    
    @property
    def available_connections(self) -> int:
        """Get number of available connections."""
        return self._pool_size - self._active_connections


class PooledConnection:
    """
    Wrapper around database connection to track release.
    
    This class wraps a MySQL connection and tracks when it's
    released back to the pool for metrics purposes.
    """
    
    def __init__(self, connection, pool: DatabasePool):
        """
        Initialize pooled connection wrapper.
        
        Args:
            connection: MySQL connection
            pool: DatabasePool instance
        """
        self._connection = connection
        self._pool = pool
        self._closed = False
    
    def __getattr__(self, name):
        """Delegate attribute access to underlying connection."""
        return getattr(self._connection, name)
    
    def __enter__(self):
        """Context manager entry."""
        return self._connection.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        result = self._connection.__exit__(exc_type, exc_val, exc_tb)
        self.close()
        return result
    
    def close(self):
        """Close connection and track release."""
        if not self._closed:
            self._connection.close()
            self._pool._release_connection()
            self._closed = True
    
    def cursor(self, *args, **kwargs):
        """Create cursor from underlying connection."""
        return self._connection.cursor(*args, **kwargs)
    
    def commit(self):
        """Commit transaction."""
        return self._connection.commit()
    
    def rollback(self):
        """Rollback transaction."""
        return self._connection.rollback()


def create_database_pool(pool_config: dict, retry_handler: Optional[DatabaseConnectionRetry] = None) -> DatabasePool:
    """
    Create a database connection pool with metrics tracking and retry logic.
    
    Args:
        pool_config: Configuration dictionary for MySQL connection pool
        retry_handler: Optional DatabaseConnectionRetry instance for connection retry
        
    Returns:
        DatabasePool instance
        
    Example:
        >>> config = {
        ...     'pool_name': 'myapp_pool',
        ...     'pool_size': 10,
        ...     'host': 'localhost',
        ...     'database': 'mydb',
        ...     'user': 'user',
        ...     'password': 'pass'
        ... }
        >>> pool = create_database_pool(config)
        
    Validates: Requirements 6.4
    """
    from mysql.connector import pooling
    
    # Create retry handler if not provided
    if retry_handler is None:
        retry_handler = DatabaseConnectionRetry(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0
        )
    
    # Use retry logic to create the pool
    def _create_pool():
        return pooling.MySQLConnectionPool(**pool_config)
    
    mysql_pool = retry_handler.execute_with_retry(
        _create_pool,
        operation_name="create database pool"
    )
    
    return DatabasePool(mysql_pool, retry_handler)
