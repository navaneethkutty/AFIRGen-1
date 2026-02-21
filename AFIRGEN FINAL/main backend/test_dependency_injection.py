"""
Unit tests for dependency injection implementation.

Tests verify that dependency injection functions work correctly and
that dependencies can be overridden for testing.

Requirements: 8.2
Task: 12.2 Implement dependency injection
"""

import pytest
from unittest.mock import Mock, MagicMock
from api.dependencies import (
    get_database_pool,
    get_cache,
    get_metrics_collector,
    get_retry_handler,
    get_circuit_breaker,
    get_fir_repository,
    get_session_service,
    init_dependencies,
    cleanup_dependencies,
    override_database_pool,
    override_cache_manager,
    reset_dependencies,
    MODEL_SERVICE_AVAILABLE
)

# Conditionally import model service
if MODEL_SERVICE_AVAILABLE:
    from api.dependencies import get_model_service
    from services.model_service import ModelService

from infrastructure.database import DatabasePool
from infrastructure.cache_manager import CacheManager
from infrastructure.retry_handler import RetryHandler
from infrastructure.circuit_breaker import CircuitBreaker
from repositories.fir_repository import FIRRepository
from services.session_service import SessionService


class TestInfrastructureDependencies:
    """Test infrastructure dependency injection functions."""
    
    def test_get_database_pool_not_initialized(self):
        """Test that get_database_pool raises error when not initialized."""
        reset_dependencies()
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            get_database_pool()
    
    def test_get_cache_not_initialized(self):
        """Test that get_cache raises error when not initialized."""
        reset_dependencies()
        
        with pytest.raises(RuntimeError, match="Cache manager not initialized"):
            get_cache()
    
    def test_get_metrics_collector(self):
        """Test that get_metrics_collector returns MetricsCollector."""
        collector = get_metrics_collector()
        # MetricsCollector is a class, not an instance
        assert collector is not None
    
    def test_get_retry_handler(self):
        """Test that get_retry_handler returns RetryHandler instance."""
        handler = get_retry_handler()
        
        assert isinstance(handler, RetryHandler)
        assert handler.max_retries == 3
        assert handler.base_delay == 1.0
        assert handler.max_delay == 60.0
    
    def test_get_circuit_breaker(self):
        """Test that get_circuit_breaker returns CircuitBreaker instance."""
        breaker = get_circuit_breaker("test_breaker", failure_threshold=3, recovery_timeout=30)
        
        assert isinstance(breaker, CircuitBreaker)
        assert breaker.name == "test_breaker"
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30


class TestRepositoryDependencies:
    """Test repository dependency injection functions."""
    
    def test_get_fir_repository(self):
        """Test that get_fir_repository creates FIRRepository with dependencies."""
        # Setup mocks
        mock_pool = Mock(spec=DatabasePool)
        mock_cache = Mock(spec=CacheManager)
        
        override_database_pool(mock_pool)
        override_cache_manager(mock_cache)
        
        # Get repository
        repo = get_fir_repository()
        
        # Verify it's a FIRRepository instance
        assert isinstance(repo, FIRRepository)
        
        # Cleanup
        reset_dependencies()


class TestServiceDependencies:
    """Test service dependency injection functions."""
    
    def test_get_session_service(self):
        """Test that get_session_service creates SessionService with dependencies."""
        # Setup mocks
        mock_pool = Mock(spec=DatabasePool)
        mock_cache = Mock(spec=CacheManager)
        
        override_database_pool(mock_pool)
        override_cache_manager(mock_cache)
        
        # Get service
        service = get_session_service()
        
        # Verify it's a SessionService instance
        assert isinstance(service, SessionService)
        
        # Cleanup
        reset_dependencies()
    
    @pytest.mark.skipif(not MODEL_SERVICE_AVAILABLE, reason="ModelService not available")
    def test_get_model_service(self):
        """Test that get_model_service creates ModelService with dependencies."""
        # Setup mocks
        mock_cache = Mock(spec=CacheManager)
        override_cache_manager(mock_cache)
        
        # Get service
        service = get_model_service()
        
        # Verify it's a ModelService instance
        assert isinstance(service, ModelService)
        
        # Cleanup
        reset_dependencies()


class TestDependencyLifecycle:
    """Test dependency initialization and cleanup."""
    
    def test_init_dependencies_creates_pool_and_cache(self):
        """Test that init_dependencies creates database pool and cache manager."""
        # Mock MySQL pooling
        mock_mysql_pool = MagicMock()
        mock_mysql_pool.pool_size = 10
        
        # Create mock for mysql.connector.pooling.MySQLConnectionPool
        import sys
        from unittest.mock import patch
        
        with patch('mysql.connector.pooling.MySQLConnectionPool', return_value=mock_mysql_pool):
            # Initialize dependencies
            db_config = {
                'pool_name': 'test_pool',
                'pool_size': 10,
                'host': 'localhost',
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass'
            }
            
            init_dependencies(db_config)
            
            # Verify pool is initialized
            pool = get_database_pool()
            assert pool is not None
            assert isinstance(pool, DatabasePool)
            
            # Verify cache is initialized
            cache = get_cache()
            assert cache is not None
            assert isinstance(cache, CacheManager)
            
            # Cleanup
            cleanup_dependencies()
    
    def test_cleanup_dependencies_resets_globals(self):
        """Test that cleanup_dependencies resets global instances."""
        # Setup
        mock_pool = Mock(spec=DatabasePool)
        mock_cache = Mock(spec=CacheManager)
        
        override_database_pool(mock_pool)
        override_cache_manager(mock_cache)
        
        # Verify initialized
        assert get_database_pool() is not None
        assert get_cache() is not None
        
        # Cleanup
        cleanup_dependencies()
        
        # Verify reset
        with pytest.raises(RuntimeError):
            get_database_pool()
        
        with pytest.raises(RuntimeError):
            get_cache()


class TestDependencyOverrides:
    """Test dependency override functions for testing."""
    
    def test_override_database_pool(self):
        """Test that override_database_pool replaces the pool."""
        mock_pool = Mock(spec=DatabasePool)
        override_database_pool(mock_pool)
        
        pool = get_database_pool()
        assert pool is mock_pool
        
        reset_dependencies()
    
    def test_override_cache_manager(self):
        """Test that override_cache_manager replaces the cache."""
        mock_cache = Mock(spec=CacheManager)
        override_cache_manager(mock_cache)
        
        cache = get_cache()
        assert cache is mock_cache
        
        reset_dependencies()
    
    def test_reset_dependencies(self):
        """Test that reset_dependencies clears all overrides."""
        mock_pool = Mock(spec=DatabasePool)
        mock_cache = Mock(spec=CacheManager)
        
        override_database_pool(mock_pool)
        override_cache_manager(mock_cache)
        
        # Verify overrides work
        assert get_database_pool() is mock_pool
        assert get_cache() is mock_cache
        
        # Reset
        reset_dependencies()
        
        # Verify reset
        with pytest.raises(RuntimeError):
            get_database_pool()
        
        with pytest.raises(RuntimeError):
            get_cache()


class TestDependencyInjectionIntegration:
    """Integration tests for dependency injection in routes."""
    
    def test_dependencies_are_singletons(self):
        """Test that infrastructure dependencies are singletons."""
        mock_pool = Mock(spec=DatabasePool)
        mock_cache = Mock(spec=CacheManager)
        
        override_database_pool(mock_pool)
        override_cache_manager(mock_cache)
        
        # Get dependencies multiple times
        pool1 = get_database_pool()
        pool2 = get_database_pool()
        
        cache1 = get_cache()
        cache2 = get_cache()
        
        # Verify same instances
        assert pool1 is pool2
        assert cache1 is cache2
        
        reset_dependencies()
    
    def test_service_dependencies_are_created_fresh(self):
        """Test that service dependencies are created fresh each time."""
        mock_pool = Mock(spec=DatabasePool)
        mock_cache = Mock(spec=CacheManager)
        
        override_database_pool(mock_pool)
        override_cache_manager(mock_cache)
        
        # Get services multiple times
        service1 = get_session_service()
        service2 = get_session_service()
        
        # Verify different instances (not singletons)
        assert service1 is not service2
        
        reset_dependencies()


def test_dependency_injection_removes_hard_coded_dependencies():
    """
    Test that dependency injection removes hard-coded dependencies.
    
    This test verifies Requirement 8.2: Remove hard-coded dependencies.
    """
    # Setup mocks
    mock_pool = Mock(spec=DatabasePool)
    mock_cache = Mock(spec=CacheManager)
    
    override_database_pool(mock_pool)
    override_cache_manager(mock_cache)
    
    # Get service through dependency injection
    service = get_session_service()
    
    # Verify service was created (not hard-coded)
    assert service is not None
    assert isinstance(service, SessionService)
    
    # Verify service has injected dependencies (not hard-coded)
    # The service should have cache and db_pool attributes from injection
    assert hasattr(service, 'cache') or hasattr(service, '_cache')
    
    reset_dependencies()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
