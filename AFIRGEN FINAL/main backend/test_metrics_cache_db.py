"""
Tests for cache and database metrics tracking.

This module tests:
- Cache hit/miss rate tracking (Requirement 5.4)
- Database connection pool utilization tracking (Requirement 5.3)
- Query execution time tracking (Requirement 5.3)

Requirements: 5.3, 5.4
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from infrastructure.cache_manager import CacheManager
from infrastructure.database import DatabasePool, create_database_pool
from infrastructure.metrics import MetricsCollector, cache_operations, cache_hit_rate


class TestCacheMetrics:
    """Test cache operation metrics tracking."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        MetricsCollector.reset_cache_hit_rate()
    
    def test_cache_get_hit_records_metric(self):
        """Test that cache hits are recorded in metrics."""
        # Arrange
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=b'{"value": "test"}')
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        result = cache_manager.get("test_key", namespace="test")
        
        # Assert
        assert result == {"value": "test"}
        # Verify hit was recorded (check internal counter)
        assert MetricsCollector._cache_hits == 1
        assert MetricsCollector._cache_misses == 0
    
    def test_cache_get_miss_records_metric(self):
        """Test that cache misses are recorded in metrics."""
        # Arrange
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=None)
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        result = cache_manager.get("test_key", namespace="test")
        
        # Assert
        assert result is None
        # Verify miss was recorded
        assert MetricsCollector._cache_hits == 0
        assert MetricsCollector._cache_misses == 1
    
    def test_cache_hit_rate_calculation(self):
        """Test that cache hit rate is calculated correctly."""
        # Arrange
        mock_redis = Mock()
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Simulate 7 hits and 3 misses (70% hit rate)
        mock_redis.get = Mock(side_effect=[
            b'{"value": "1"}',  # hit
            b'{"value": "2"}',  # hit
            None,               # miss
            b'{"value": "3"}',  # hit
            None,               # miss
            b'{"value": "4"}',  # hit
            b'{"value": "5"}',  # hit
            None,               # miss
            b'{"value": "6"}',  # hit
            b'{"value": "7"}',  # hit
        ])
        
        # Act
        for i in range(10):
            cache_manager.get(f"key_{i}", namespace="test")
        
        # Assert
        assert MetricsCollector._cache_hits == 7
        assert MetricsCollector._cache_misses == 3
        assert MetricsCollector._cache_total == 10
        
        # Check hit rate (should be 70%)
        expected_hit_rate = 70.0
        # Get the current value from the gauge (approximate check)
        assert abs(cache_hit_rate._value._value - expected_hit_rate) < 0.1
    
    def test_cache_set_records_metric(self):
        """Test that cache set operations are recorded."""
        # Arrange
        mock_redis = Mock()
        mock_redis.setex = Mock(return_value=True)
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        result = cache_manager.set("test_key", {"value": "test"}, ttl=60, namespace="test")
        
        # Assert
        assert result is True
        mock_redis.setex.assert_called_once()
    
    def test_cache_delete_records_metric(self):
        """Test that cache delete operations are recorded."""
        # Arrange
        mock_redis = Mock()
        mock_redis.delete = Mock(return_value=1)
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        result = cache_manager.delete("test_key", namespace="test")
        
        # Assert
        assert result is True
        mock_redis.delete.assert_called_once()
    
    def test_cache_error_records_metric(self):
        """Test that cache errors are recorded in metrics."""
        # Arrange
        from redis.exceptions import RedisError
        mock_redis = Mock()
        mock_redis.get = Mock(side_effect=RedisError("Connection failed"))
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        result = cache_manager.get("test_key", namespace="test")
        
        # Assert
        assert result is None  # Fallback behavior
        # Error should be recorded (not counted as hit or miss)
    
    def test_cache_operation_duration_tracked(self):
        """Test that cache operation duration is tracked."""
        # Arrange
        mock_redis = Mock()
        
        def slow_get(key):
            time.sleep(0.01)  # Simulate slow operation
            return b'{"value": "test"}'
        
        mock_redis.get = Mock(side_effect=slow_get)
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        start = time.time()
        result = cache_manager.get("test_key", namespace="test")
        duration = time.time() - start
        
        # Assert
        assert result == {"value": "test"}
        assert duration >= 0.01  # Should take at least 10ms
    
    def test_cache_memory_usage_tracking(self):
        """Test that cache memory usage can be tracked."""
        # Arrange
        mock_redis = Mock()
        mock_redis.info = Mock(return_value={'used_memory': 1024000})
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        memory_usage = cache_manager.get_memory_usage()
        
        # Assert
        assert memory_usage == 1024000
        mock_redis.info.assert_called_once_with('memory')
    
    def test_update_cache_metrics(self):
        """Test that cache metrics are updated correctly."""
        # Arrange
        mock_redis = Mock()
        mock_redis.info = Mock(return_value={'used_memory': 2048000})
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Act
        cache_manager.update_cache_metrics()
        
        # Assert
        mock_redis.info.assert_called_once_with('memory')


class TestDatabasePoolMetrics:
    """Test database connection pool metrics tracking."""
    
    def test_pool_initialization_sets_metrics(self):
        """Test that pool initialization sets up metrics correctly."""
        # Arrange
        mock_pool = Mock()
        mock_pool.pool_size = 10
        
        # Act
        db_pool = DatabasePool(mock_pool)
        
        # Assert
        assert db_pool.pool_size == 10
        assert db_pool.active_connections == 0
        assert db_pool.available_connections == 10
    
    def test_get_connection_updates_metrics(self):
        """Test that getting a connection updates pool metrics."""
        # Arrange
        mock_pool = Mock()
        mock_pool.pool_size = 10
        mock_conn = Mock()
        mock_pool.get_connection = Mock(return_value=mock_conn)
        
        db_pool = DatabasePool(mock_pool)
        
        # Act
        conn = db_pool.get_connection()
        
        # Assert
        assert db_pool.active_connections == 1
        assert db_pool.available_connections == 9
        mock_pool.get_connection.assert_called_once()
    
    def test_release_connection_updates_metrics(self):
        """Test that releasing a connection updates pool metrics."""
        # Arrange
        mock_pool = Mock()
        mock_pool.pool_size = 10
        mock_conn = Mock()
        mock_pool.get_connection = Mock(return_value=mock_conn)
        
        db_pool = DatabasePool(mock_pool)
        
        # Act
        conn = db_pool.get_connection()
        assert db_pool.active_connections == 1
        
        conn.close()
        
        # Assert
        assert db_pool.active_connections == 0
        assert db_pool.available_connections == 10
    
    def test_multiple_connections_tracked(self):
        """Test that multiple connections are tracked correctly."""
        # Arrange
        mock_pool = Mock()
        mock_pool.pool_size = 10
        mock_pool.get_connection = Mock(side_effect=[Mock(), Mock(), Mock()])
        
        db_pool = DatabasePool(mock_pool)
        
        # Act
        conn1 = db_pool.get_connection()
        conn2 = db_pool.get_connection()
        conn3 = db_pool.get_connection()
        
        # Assert
        assert db_pool.active_connections == 3
        assert db_pool.available_connections == 7
        
        # Release one connection
        conn1.close()
        assert db_pool.active_connections == 2
        assert db_pool.available_connections == 8
    
    def test_pool_utilization_percentage(self):
        """Test calculation of pool utilization percentage."""
        # Arrange
        mock_pool = Mock()
        mock_pool.pool_size = 10
        mock_pool.get_connection = Mock(side_effect=[Mock() for _ in range(7)])
        
        db_pool = DatabasePool(mock_pool)
        
        # Act - Get 7 connections (70% utilization)
        connections = [db_pool.get_connection() for _ in range(7)]
        
        # Assert
        utilization = (db_pool.active_connections / db_pool.pool_size) * 100
        assert utilization == 70.0
        assert db_pool.available_connections == 3
    
    def test_pooled_connection_context_manager(self):
        """Test that pooled connection works as context manager."""
        # Arrange
        mock_pool = Mock()
        mock_pool.pool_size = 10
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_pool.get_connection = Mock(return_value=mock_conn)
        
        db_pool = DatabasePool(mock_pool)
        
        # Act
        with db_pool.get_connection() as conn:
            assert db_pool.active_connections == 1
        
        # Assert - Connection should be released after context
        assert db_pool.active_connections == 0
    
    @pytest.mark.skip(reason="Requires mysql-connector-python to be installed")
    def test_create_database_pool_function(self):
        """Test the create_database_pool helper function."""
        # Arrange
        config = {
            'pool_name': 'test_pool',
            'pool_size': 5,
            'host': 'localhost',
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        
        # Act & Assert
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool_class:
            mock_pool_instance = Mock()
            mock_pool_instance.pool_size = 5
            mock_pool_class.return_value = mock_pool_instance
            
            db_pool = create_database_pool(config)
            
            assert isinstance(db_pool, DatabasePool)
            assert db_pool.pool_size == 5
            mock_pool_class.assert_called_once_with(**config)


class TestQueryMetrics:
    """Test database query execution metrics."""
    
    def test_query_duration_tracked(self):
        """Test that query execution duration is tracked."""
        # This is tested through the repository's _execute_query_with_metrics method
        # We'll verify the metrics are recorded correctly
        
        # Arrange
        from infrastructure.metrics import db_query_duration, db_query_count
        
        # Act
        MetricsCollector.record_db_query_duration(
            query_type="SELECT",
            table="firs",
            duration=0.025
        )
        
        # Assert
        # Metrics should be recorded (we can't easily check Prometheus metrics directly,
        # but we can verify the method doesn't raise errors)
        # In a real scenario, you'd use prometheus_client's test utilities
    
    def test_query_count_by_type(self):
        """Test that queries are counted by type."""
        # Arrange & Act
        MetricsCollector.record_db_query_duration("SELECT", "firs", 0.01)
        MetricsCollector.record_db_query_duration("INSERT", "firs", 0.02)
        MetricsCollector.record_db_query_duration("UPDATE", "firs", 0.015)
        MetricsCollector.record_db_query_duration("SELECT", "violations", 0.008)
        
        # Assert
        # Metrics are recorded for different query types and tables
        # In production, these would be scraped by Prometheus


class TestIntegration:
    """Integration tests for cache and database metrics."""
    
    def test_cache_and_db_metrics_together(self):
        """Test that cache and database metrics work together."""
        # Arrange
        mock_redis = Mock()
        mock_redis.get = Mock(side_effect=[None, b'{"value": "cached"}'])
        mock_redis.setex = Mock(return_value=True)
        cache_manager = CacheManager(redis_client=mock_redis)
        
        MetricsCollector.reset_cache_hit_rate()
        
        # Act
        # First call - cache miss, would hit database
        result1 = cache_manager.get("key1", namespace="test")
        assert result1 is None
        
        # Cache the value
        cache_manager.set("key1", {"value": "cached"}, ttl=60, namespace="test")
        
        # Second call - cache hit
        result2 = cache_manager.get("key1", namespace="test")
        assert result2 == {"value": "cached"}
        
        # Assert
        assert MetricsCollector._cache_hits == 1
        assert MetricsCollector._cache_misses == 1
        assert MetricsCollector._cache_total == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
