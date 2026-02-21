"""
Dependency injection functions for FastAPI.

This module provides dependency injection functions that create and manage
service, repository, and infrastructure dependencies for API endpoints.

Requirements: 8.2 - Use dependency injection for external service dependencies
"""

from typing import Generator, Optional
from fastapi import Depends
from functools import lru_cache

# Infrastructure dependencies
from infrastructure.database import DatabasePool, create_database_pool
from infrastructure.cache_manager import CacheManager, get_cache_manager
from infrastructure.logging import get_logger
from infrastructure.metrics import MetricsCollector
from infrastructure.connection_retry import DatabaseConnectionRetry
from infrastructure.circuit_breaker import CircuitBreaker
from infrastructure.retry_handler import RetryHandler

# Repository dependencies
from repositories.fir_repository import FIRRepository
from repositories.base_repository import BaseRepository

# Service dependencies
from services.session_service import SessionService
try:
    from services.model_service import ModelService
    MODEL_SERVICE_AVAILABLE = True
except ImportError:
    MODEL_SERVICE_AVAILABLE = False
    ModelService = None

# Global instances (initialized during app startup)
_db_pool: Optional[DatabasePool] = None
_cache_manager: Optional[CacheManager] = None
_logger = get_logger(__name__)


# ============================================================================
# Infrastructure Dependencies
# ============================================================================

def get_database_pool() -> DatabasePool:
    """
    Get database connection pool instance.
    
    This should be initialized during app startup via init_dependencies().
    
    Returns:
        DatabasePool instance
        
    Raises:
        RuntimeError: If database pool is not initialized
        
    Validates: Requirements 8.2
    """
    global _db_pool
    if _db_pool is None:
        raise RuntimeError(
            "Database pool not initialized. Call init_dependencies() during app startup."
        )
    return _db_pool


def get_cache() -> CacheManager:
    """
    Get cache manager instance.
    
    This should be initialized during app startup via init_dependencies().
    
    Returns:
        CacheManager instance
        
    Raises:
        RuntimeError: If cache manager is not initialized
        
    Validates: Requirements 8.2
    """
    global _cache_manager
    if _cache_manager is None:
        raise RuntimeError(
            "Cache manager not initialized. Call init_dependencies() during app startup."
        )
    return _cache_manager


@lru_cache()
def get_metrics_collector() -> MetricsCollector:
    """
    Get metrics collector instance (singleton).
    
    Returns:
        MetricsCollector instance
        
    Validates: Requirements 8.2
    """
    return MetricsCollector


@lru_cache()
def get_retry_handler() -> RetryHandler:
    """
    Get retry handler instance (singleton).
    
    Returns:
        RetryHandler instance with default configuration
        
    Validates: Requirements 8.2
    """
    return RetryHandler(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0
    )


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        
    Returns:
        CircuitBreaker instance
        
    Validates: Requirements 8.2
    """
    return CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )


# ============================================================================
# Repository Dependencies
# ============================================================================

def get_fir_repository(
    db_pool: DatabasePool = Depends(get_database_pool),
    cache: CacheManager = Depends(get_cache)
) -> FIRRepository:
    """
    Get FIR repository instance with injected dependencies.
    
    Note: FIRRepository expects a connection, not a pool. This function
    gets a connection from the pool. In production, this should be used
    within a context manager or request scope.
    
    Args:
        db_pool: Database connection pool (injected)
        cache: Cache manager (injected)
        
    Returns:
        FIRRepository instance
        
    Validates: Requirements 8.2
    """
    # Get connection from pool
    connection = db_pool.get_connection()
    return FIRRepository(connection=connection, cache_manager=cache)


def get_base_repository(
    db_pool: DatabasePool = Depends(get_database_pool)
) -> BaseRepository:
    """
    Get base repository instance with injected dependencies.
    
    Args:
        db_pool: Database connection pool (injected)
        
    Returns:
        BaseRepository instance
        
    Validates: Requirements 8.2
    """
    return BaseRepository(db_pool=db_pool)


# ============================================================================
# Service Dependencies
# ============================================================================

def get_session_service(
    cache: CacheManager = Depends(get_cache),
    db_pool: DatabasePool = Depends(get_database_pool)
) -> SessionService:
    """
    Get session service instance with injected dependencies.
    
    Note: SessionService expects a session_manager. This function creates
    a PersistentSessionManager with the injected database pool.
    
    TODO: Refactor SessionService to accept db_pool and cache directly.
    
    Args:
        cache: Cache manager (injected)
        db_pool: Database connection pool (injected)
        
    Returns:
        SessionService instance
        
    Validates: Requirements 8.2
    """
    # Import here to avoid circular dependency
    from agentv5 import PersistentSessionManager
    
    # Create session manager with database
    # Note: This is a temporary solution. SessionService should be refactored
    # to accept dependencies directly.
    session_manager = PersistentSessionManager(db_path="sessions.db")
    
    return SessionService(session_manager=session_manager)


def get_model_service(
    circuit_breaker: CircuitBreaker = Depends(
        lambda: get_circuit_breaker("model_server", failure_threshold=5, recovery_timeout=60)
    ),
    retry_handler: RetryHandler = Depends(get_retry_handler),
    cache: CacheManager = Depends(get_cache)
) -> ModelService:
    """
    Get model service instance with injected dependencies.
    
    Args:
        circuit_breaker: Circuit breaker for model server calls (injected)
        retry_handler: Retry handler for transient failures (injected)
        cache: Cache manager for health status caching (injected)
        
    Returns:
        ModelService instance
        
    Raises:
        RuntimeError: If ModelService is not available
        
    Validates: Requirements 8.2
    """
    if not MODEL_SERVICE_AVAILABLE:
        raise RuntimeError("ModelService is not available. Check dependencies.")
    
    return ModelService(
        circuit_breaker=circuit_breaker,
        retry_handler=retry_handler,
        cache=cache
    )


# ============================================================================
# Initialization
# ============================================================================

def init_dependencies(db_config: dict, redis_client=None):
    """
    Initialize global dependencies during app startup.
    
    This should be called once during FastAPI app startup (in lifespan context).
    
    Args:
        db_config: Database configuration dictionary
        redis_client: Optional Redis client instance
        
    Example:
        >>> from contextlib import asynccontextmanager
        >>> from fastapi import FastAPI
        >>> 
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     # Startup
        ...     db_config = {
        ...         'pool_name': 'afirgen_pool',
        ...         'pool_size': 10,
        ...         'host': 'localhost',
        ...         'database': 'afirgen',
        ...         'user': 'user',
        ...         'password': 'pass'
        ...     }
        ...     init_dependencies(db_config)
        ...     yield
        ...     # Shutdown
        ...     cleanup_dependencies()
        >>> 
        >>> app = FastAPI(lifespan=lifespan)
        
    Validates: Requirements 8.2
    """
    global _db_pool, _cache_manager
    
    try:
        # Initialize database pool with retry logic
        _logger.info("Initializing database connection pool")
        retry_handler = DatabaseConnectionRetry(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0
        )
        _db_pool = create_database_pool(db_config, retry_handler)
        _logger.info(
            "Database pool initialized",
            pool_size=_db_pool.pool_size,
            available=_db_pool.available_connections
        )
        
        # Initialize cache manager
        _logger.info("Initializing cache manager")
        _cache_manager = CacheManager(redis_client=redis_client)
        
        # Test cache connection
        if _cache_manager.ping():
            _logger.info("Cache manager initialized successfully")
        else:
            _logger.warning("Cache manager initialized but Redis connection failed")
        
    except Exception as e:
        _logger.error("Failed to initialize dependencies", error=str(e))
        raise


def cleanup_dependencies():
    """
    Cleanup global dependencies during app shutdown.
    
    This should be called once during FastAPI app shutdown (in lifespan context).
    
    Validates: Requirements 8.2
    """
    global _db_pool, _cache_manager
    
    try:
        _logger.info("Cleaning up dependencies")
        
        # Note: MySQL connection pool doesn't need explicit cleanup
        # Connections are automatically closed when pool is garbage collected
        _db_pool = None
        
        # Cache manager doesn't need explicit cleanup
        # Redis connections are managed by redis-py connection pool
        _cache_manager = None
        
        _logger.info("Dependencies cleaned up successfully")
        
    except Exception as e:
        _logger.error("Error during dependency cleanup", error=str(e))


# ============================================================================
# Testing Support
# ============================================================================

def override_database_pool(pool: DatabasePool):
    """
    Override database pool for testing.
    
    Args:
        pool: Mock or test database pool
        
    Example:
        >>> from unittest.mock import Mock
        >>> mock_pool = Mock(spec=DatabasePool)
        >>> override_database_pool(mock_pool)
    """
    global _db_pool
    _db_pool = pool


def override_cache_manager(cache: CacheManager):
    """
    Override cache manager for testing.
    
    Args:
        cache: Mock or test cache manager
        
    Example:
        >>> from unittest.mock import Mock
        >>> mock_cache = Mock(spec=CacheManager)
        >>> override_cache_manager(mock_cache)
    """
    global _cache_manager
    _cache_manager = cache


def reset_dependencies():
    """
    Reset all dependencies to None (for testing).
    
    Example:
        >>> reset_dependencies()
        >>> # Now dependencies must be re-initialized
    """
    global _db_pool, _cache_manager
    _db_pool = None
    _cache_manager = None
