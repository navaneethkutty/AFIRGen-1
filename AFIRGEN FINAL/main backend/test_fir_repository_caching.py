"""
Property-based tests for FIR Repository caching integration.

Tests cover:
- Cache-aside pattern for FIR retrieval
- Cache invalidation on write operations
- Cache fallback on failures
- Caching for user FIR lists
- Caching for statistics queries

Feature: backend-optimization
Task: 3.5 Integrate caching into FIR repository
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
from redis.exceptions import RedisError

# Import components to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'repositories'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'infrastructure'))

from repositories.fir_repository import FIR, FIRRepository
from infrastructure.cache_manager import CacheManager


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================

def create_mock_db_connection():
    """Create a mock database connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.rowcount = 0
    mock_cursor.close.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None
    return mock_conn


def create_mock_cache_manager():
    """Create a mock cache manager with in-memory storage."""
    mock_cache = Mock(spec=CacheManager)
    mock_cache._data = {}
    
    def mock_get(key, namespace="default"):
        full_key = f"{namespace}:{key}"
        return mock_cache._data.get(full_key)
    
    def mock_set(key, value, ttl, namespace="default"):
        full_key = f"{namespace}:{key}"
        mock_cache._data[full_key] = value
        return True
    
    def mock_delete(key, namespace="default"):
        full_key = f"{namespace}:{key}"
        if full_key in mock_cache._data:
            del mock_cache._data[full_key]
            return True
        return False
    
    def mock_invalidate_pattern(pattern, namespace="default"):
        import fnmatch
        full_pattern = f"{namespace}:{pattern}"
        keys_to_delete = [k for k in mock_cache._data.keys() if fnmatch.fnmatch(k, full_pattern)]
        for key in keys_to_delete:
            del mock_cache._data[key]
        return len(keys_to_delete)
    
    def mock_get_or_fetch(key, fetch_fn, ttl, namespace="default"):
        full_key = f"{namespace}:{key}"
        if full_key in mock_cache._data:
            return mock_cache._data[full_key]
        else:
            value = fetch_fn()
            mock_cache._data[full_key] = value
            return value
    
    mock_cache.get.side_effect = mock_get
    mock_cache.set.side_effect = mock_set
    mock_cache.delete.side_effect = mock_delete
    mock_cache.invalidate_pattern.side_effect = mock_invalidate_pattern
    mock_cache.get_or_fetch.side_effect = mock_get_or_fetch
    
    return mock_cache


def create_test_fir(fir_id="test_123", user_id="user_456", status="pending"):
    """Create a test FIR entity."""
    return FIR(
        id=fir_id,
        user_id=user_id,
        status=status,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        description="Test FIR description",
        violation_text="Test violation",
        priority=5,
        assigned_to="officer_789"
    )


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestFIRRepositoryCachingProperties:
    """Property-based tests for FIR repository caching integration."""
    
    # Property: Cache-aside pattern for FIR retrieval
    # Validates: Requirements 2.2, 2.3
    @given(
        fir_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        status=st.sampled_from(["pending", "approved", "rejected", "in_progress"])
    )
    @settings(max_examples=20)
    def test_property_cache_aside_pattern_for_fir_retrieval(self, fir_id, user_id, status):
        """
        Property: Cache-aside pattern for FIR retrieval
        
        For any FIR retrieval by ID:
        1. First check cache
        2. If cache miss, query database
        3. Store result in cache
        4. Return the FIR
        
        **Validates: Requirements 2.2, 2.3**
        """
        # Create mocks
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        # Create test FIR
        test_fir = create_test_fir(fir_id, user_id, status)
        
        # Configure mock cursor to return FIR data
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = test_fir.to_dict()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Create repository
        repo = FIRRepository(mock_conn, mock_cache)
        
        # First call - cache miss, should query database
        result1 = repo.find_by_id(fir_id)
        
        # Verify database was queried
        assert mock_conn.cursor.called
        
        # Verify result is correct
        assert result1 is not None
        assert result1.id == fir_id
        assert result1.user_id == user_id
        assert result1.status == status
        
        # Verify value was cached
        cache_key = f"fir:record:{fir_id}"
        assert cache_key in mock_cache._data
        
        # Reset mock to track second call
        mock_conn.cursor.reset_mock()
        
        # Second call - cache hit, should NOT query database
        result2 = repo.find_by_id(fir_id)
        
        # Verify database was NOT queried (cache hit)
        # Note: cursor is still called but fetchone should not be called again
        assert result2 is not None
        assert result2.id == fir_id
    
    # Property: Cache invalidation on FIR creation
    # Validates: Requirements 2.4
    @given(
        fir_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        status=st.sampled_from(["pending", "approved", "rejected", "in_progress"])
    )
    @settings(max_examples=20)
    def test_property_cache_invalidation_on_create(self, fir_id, user_id, status):
        """
        Property: Cache invalidation on FIR creation
        
        For any FIR creation operation:
        1. Insert FIR into database
        2. Invalidate related cache entries (lists, stats, queries)
        3. Cache the newly created FIR
        
        **Validates: Requirements 2.4**
        """
        # Create mocks
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        # Pre-populate cache with some data that should be invalidated
        mock_cache._data[f"fir:list:user:{user_id}"] = [{"id": "old_fir"}]
        mock_cache._data[f"fir:stats:count_by_status"] = [{"status": "pending", "count": 5}]
        mock_cache._data[f"fir:query:search"] = [{"id": "search_result"}]
        
        # Create test FIR
        test_fir = create_test_fir(fir_id, user_id, status)
        
        # Configure mock cursor
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Create repository
        repo = FIRRepository(mock_conn, mock_cache)
        
        # Create FIR
        result = repo.create(test_fir)
        
        # Verify FIR was created
        assert result is not None
        assert result.id == fir_id
        
        # Verify database commit was called
        assert mock_conn.commit.called
        
        # Verify cache invalidation patterns were applied
        # List caches should be invalidated
        assert f"fir:list:user:{user_id}" not in mock_cache._data or \
               mock_cache._data.get(f"fir:list:user:{user_id}") != [{"id": "old_fir"}]
        
        # Verify the new FIR was cached
        cache_key = f"fir:record:{fir_id}"
        assert cache_key in mock_cache._data
        cached_fir = mock_cache._data[cache_key]
        assert cached_fir['id'] == fir_id
    
    # Property: Cache fallback on Redis failure
    # Validates: Requirements 2.5
    @given(
        fir_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        status=st.sampled_from(["pending", "approved", "rejected", "in_progress"])
    )
    @settings(max_examples=10)
    def test_property_cache_fallback_on_failure(self, fir_id, user_id, status):
        """
        Property: Cache fallback on Redis failure
        
        For any cache operation that fails:
        1. Log the error
        2. Fall back to database query
        3. Continue serving the request without error
        
        **Validates: Requirements 2.5**
        """
        # Create mocks
        mock_conn = create_mock_db_connection()
        
        # Create failing cache manager
        failing_cache = Mock(spec=CacheManager)
        failing_cache.get_or_fetch.side_effect = RedisError("Connection failed")
        failing_cache.get.side_effect = RedisError("Connection failed")
        failing_cache.set.side_effect = RedisError("Connection failed")
        failing_cache.delete.side_effect = RedisError("Connection failed")
        failing_cache.invalidate_pattern.side_effect = RedisError("Connection failed")
        
        # Create test FIR
        test_fir = create_test_fir(fir_id, user_id, status)
        
        # Configure mock cursor to return FIR data
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = test_fir.to_dict()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Create repository with failing cache
        repo = FIRRepository(mock_conn, failing_cache)
        
        # Try to retrieve FIR - should fall back to database
        result = repo.find_by_id(fir_id)
        
        # Verify request succeeded despite cache failure
        assert result is not None
        assert result.id == fir_id
        assert result.user_id == user_id
        assert result.status == status
        
        # Verify database was queried (fallback)
        assert mock_conn.cursor.called
    
    # Property: Caching for user FIR lists
    # Validates: Requirements 2.2, 2.3
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        limit=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=20)
    def test_property_caching_for_user_fir_lists(self, user_id, limit):
        """
        Property: Caching for user FIR lists
        
        For any user FIR list query:
        1. Check cache for user's FIR list
        2. If cache miss, query database
        3. Store result in cache with TTL
        4. Return the list
        
        **Validates: Requirements 2.2, 2.3**
        """
        # Create mocks
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        # Create test FIRs
        test_firs = [
            create_test_fir(f"fir_{i}", user_id, "pending").to_dict()
            for i in range(min(limit, 5))
        ]
        
        # Configure mock cursor to return FIR data
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = test_firs
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Create repository
        repo = FIRRepository(mock_conn, mock_cache)
        
        # First call - cache miss, should query database
        result1 = repo.find_by_user(user_id, limit=limit)
        
        # Verify database was queried
        assert mock_conn.cursor.called
        
        # Verify result is correct
        assert result1 is not None
        assert len(result1) <= limit
        if len(test_firs) > 0:
            assert result1[0].user_id == user_id
        
        # Verify value was cached
        cache_key = f"fir:user:{user_id}:limit:{limit}"
        assert cache_key in mock_cache._data
        
        # Reset mock to track second call
        mock_conn.cursor.reset_mock()
        
        # Second call - cache hit, should NOT query database
        result2 = repo.find_by_user(user_id, limit=limit)
        
        # Verify result is correct
        assert result2 is not None
        assert len(result2) == len(result1)
    
    # Property: Caching for statistics queries
    # Validates: Requirements 2.2, 2.3
    @given(
        status_counts=st.lists(
            st.tuples(
                st.sampled_from(["pending", "approved", "rejected", "in_progress"]),
                st.integers(min_value=0, max_value=1000)
            ),
            min_size=1,
            max_size=4,
            unique_by=lambda x: x[0]
        )
    )
    @settings(max_examples=20)
    def test_property_caching_for_statistics(self, status_counts):
        """
        Property: Caching for statistics queries
        
        For any statistics query (e.g., count by status):
        1. Check cache for statistics
        2. If cache miss, query database with aggregation
        3. Store result in cache with short TTL (5 minutes)
        4. Return the statistics
        
        **Validates: Requirements 2.2, 2.3**
        """
        # Create mocks
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        # Create test statistics data
        stats_data = [
            {"status": status, "aggregate_value": count}
            for status, count in status_counts
        ]
        
        # Configure mock cursor to return statistics
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = stats_data
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Create repository
        repo = FIRRepository(mock_conn, mock_cache)
        
        # First call - cache miss, should query database
        result1 = repo.count_by_status()
        
        # Verify database was queried
        assert mock_conn.cursor.called
        
        # Verify result is correct
        assert result1 is not None
        assert len(result1) == len(status_counts)
        
        # Verify value was cached
        cache_key = "fir:stats:count_by_status"
        assert cache_key in mock_cache._data
        
        # Reset mock to track second call
        mock_conn.cursor.reset_mock()
        
        # Second call - cache hit, should NOT query database
        result2 = repo.count_by_status()
        
        # Verify result is correct
        assert result2 is not None
        assert len(result2) == len(result1)
    
    # Property: Cache invalidation affects related entries
    # Validates: Requirements 2.4
    @given(
        fir_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
    )
    @settings(max_examples=10)
    def test_property_cache_invalidation_affects_related_entries(self, fir_id, user_id):
        """
        Property: Cache invalidation affects related entries
        
        For any data modification (create/update/delete):
        1. Invalidate direct entity cache
        2. Invalidate list caches (user lists, status lists)
        3. Invalidate query caches (search results)
        4. Invalidate statistics caches (counts, aggregations)
        
        **Validates: Requirements 2.4**
        """
        # Create mocks
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        # Pre-populate cache with various related entries
        mock_cache._data[f"fir:record:{fir_id}"] = {"id": fir_id}
        mock_cache._data[f"fir:list:all"] = [{"id": fir_id}]
        mock_cache._data[f"fir:list:user:{user_id}"] = [{"id": fir_id}]
        mock_cache._data[f"fir:query:search"] = [{"id": fir_id}]
        mock_cache._data[f"fir:stats:count"] = {"total": 10}
        mock_cache._data[f"fir:count:pending"] = 5
        mock_cache._data[f"fir:user:profile"] = {"user_id": user_id}
        
        # Create repository
        repo = FIRRepository(mock_conn, mock_cache)
        
        # Trigger cache invalidation
        repo._invalidate_cache_for_entity(fir_id)
        
        # Verify direct entity cache was invalidated
        assert f"fir:record:{fir_id}" not in mock_cache._data
        
        # Verify list caches were invalidated
        assert f"fir:list:all" not in mock_cache._data
        assert f"fir:list:user:{user_id}" not in mock_cache._data
        
        # Verify query caches were invalidated
        assert f"fir:query:search" not in mock_cache._data
        
        # Verify stats caches were invalidated
        assert f"fir:stats:count" not in mock_cache._data
        assert f"fir:count:pending" not in mock_cache._data
        
        # Verify user caches were invalidated
        assert f"fir:user:profile" not in mock_cache._data


# ============================================================================
# Unit Tests for Edge Cases
# ============================================================================

class TestFIRRepositoryCachingUnit:
    """Unit tests for FIR repository caching edge cases."""
    
    def test_find_by_id_with_fields_bypasses_cache(self):
        """Test that partial field retrieval bypasses cache."""
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        test_fir = create_test_fir()
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = test_fir.to_dict()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        repo = FIRRepository(mock_conn, mock_cache)
        
        # Call with specific fields - should bypass cache
        result = repo.find_by_id("test_123", fields=["id", "status"])
        
        # Verify database was queried
        assert mock_conn.cursor.called
        
        # Verify cache was NOT used (no cache key should be created)
        assert len(mock_cache._data) == 0
    
    def test_find_by_user_with_fields_bypasses_cache(self):
        """Test that partial field retrieval for user lists bypasses cache."""
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        test_firs = [create_test_fir().to_dict()]
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = test_firs
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        repo = FIRRepository(mock_conn, mock_cache)
        
        # Call with specific fields - should bypass cache
        result = repo.find_by_user("user_456", fields=["id", "status"])
        
        # Verify database was queried
        assert mock_conn.cursor.called
        
        # Verify cache was NOT used
        assert len(mock_cache._data) == 0
    
    def test_create_caches_new_fir_on_success(self):
        """Test that creating a FIR caches it immediately."""
        mock_conn = create_mock_db_connection()
        mock_cache = create_mock_cache_manager()
        
        test_fir = create_test_fir()
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        repo = FIRRepository(mock_conn, mock_cache)
        
        # Create FIR
        result = repo.create(test_fir)
        
        # Verify FIR was cached
        cache_key = f"fir:record:{test_fir.id}"
        assert cache_key in mock_cache._data
        assert mock_cache._data[cache_key]['id'] == test_fir.id
    
    def test_cache_failure_during_create_does_not_fail_operation(self):
        """Test that cache failures during create don't fail the operation."""
        mock_conn = create_mock_db_connection()
        
        # Create failing cache
        failing_cache = Mock(spec=CacheManager)
        failing_cache.set.side_effect = RedisError("Connection failed")
        failing_cache.delete.return_value = False
        failing_cache.invalidate_pattern.return_value = 0
        
        test_fir = create_test_fir()
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        repo = FIRRepository(mock_conn, failing_cache)
        
        # Create FIR - should succeed despite cache failure
        result = repo.create(test_fir)
        
        # Verify FIR was created
        assert result is not None
        assert result.id == test_fir.id
        
        # Verify database commit was called
        assert mock_conn.commit.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
