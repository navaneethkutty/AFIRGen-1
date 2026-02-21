"""
Property-based tests for cache invalidation and fallback behavior.

This module tests the correctness properties:
- Property 9: Data modification invalidates cache
- Property 10: Cache failure fallback

Requirements: 2.4, 2.5
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from hypothesis import given, strategies as st, settings, assume

# Import components to test
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from repositories.fir_repository import FIRRepository, FIR
from infrastructure.cache_manager import CacheManager


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def fir_entity(draw):
    """Generate a valid FIR entity for property testing."""
    return FIR(
        id=draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))),
        user_id=draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))),
        status=draw(st.sampled_from(['pending', 'in_progress', 'completed', 'rejected'])),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        description=draw(st.text(min_size=10, max_size=200)),
        violation_text=draw(st.text(min_size=10, max_size=200)),
        priority=draw(st.integers(min_value=1, max_value=5)),
        assigned_to=draw(st.one_of(st.none(), st.text(min_size=5, max_size=50)))
    )


@st.composite
def update_dict(draw):
    """Generate a valid update dictionary for property testing."""
    updates = {}
    
    # Randomly include different fields
    if draw(st.booleans()):
        updates['status'] = draw(st.sampled_from(['pending', 'in_progress', 'completed', 'rejected']))
    
    if draw(st.booleans()):
        updates['description'] = draw(st.text(min_size=10, max_size=200))
    
    if draw(st.booleans()):
        updates['priority'] = draw(st.integers(min_value=1, max_value=5))
    
    if draw(st.booleans()):
        updates['assigned_to'] = draw(st.text(min_size=5, max_size=50))
    
    # Ensure at least one field is updated
    if not updates:
        updates['status'] = draw(st.sampled_from(['pending', 'in_progress', 'completed', 'rejected']))
    
    return updates


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_connection():
    """Create a mock database connection for testing."""
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # Configure cursor behavior
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.rowcount = 1
    mock_cursor.execute.return_value = None
    
    # Configure cursor context manager
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    
    # Configure connection
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None
    
    return mock_conn, mock_cursor


def create_mock_cache_manager():
    """Create a mock cache manager for testing."""
    mock_cache = Mock(spec=CacheManager)
    mock_cache.delete.return_value = True
    mock_cache.invalidate_pattern.return_value = 5
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    # Configure get_or_fetch to call the fetch function
    mock_cache.get_or_fetch.side_effect = lambda key, fetch_fn, ttl, namespace: fetch_fn()
    return mock_cache


def create_failing_cache_manager():
    """Create a cache manager that always fails."""
    mock_cache = Mock(spec=CacheManager)
    mock_cache.delete.side_effect = RedisError("Connection failed")
    mock_cache.invalidate_pattern.side_effect = RedisError("Connection failed")
    mock_cache.get.side_effect = RedisError("Connection failed")
    mock_cache.set.side_effect = RedisError("Connection failed")
    # Configure get_or_fetch to call the fetch function even when cache fails
    mock_cache.get_or_fetch.side_effect = lambda key, fetch_fn, ttl, namespace: fetch_fn()
    return mock_cache


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestCacheInvalidationProperties:
    """Property-based tests for cache invalidation correctness."""
    
    # Property 9: Data modification invalidates cache
    # Validates: Requirements 2.4
    @given(fir=fir_entity())
    @settings(max_examples=20)
    def test_property_create_invalidates_cache(self, fir):
        """
        Property 9: Data modification invalidates cache (CREATE)
        
        For any data modification operation (create, update, delete), the
        corresponding cache entries should be invalidated or updated to
        maintain consistency.
        
        This test verifies that CREATE operations invalidate cache.
        
        **Validates: Requirements 2.4**
        """
        # Setup
        mock_conn, mock_cursor = create_mock_connection()
        mock_cache = create_mock_cache_manager()
        repository = FIRRepository(mock_conn, mock_cache)
        
        # Execute create operation
        result = repository.create(fir)
        
        # Verify entity was created
        assert result.id == fir.id
        
        # Verify cache invalidation was called
        # Should invalidate direct entity cache
        mock_cache.delete.assert_called()
        
        # Should invalidate pattern-based caches
        mock_cache.invalidate_pattern.assert_called()
        
        # Verify invalidation was called at least once for each type
        assert mock_cache.delete.call_count >= 1
        assert mock_cache.invalidate_pattern.call_count >= 1
        
        # Verify the entity key was invalidated
        delete_calls = [call[0] for call in mock_cache.delete.call_args_list]
        entity_key_invalidated = any(f"record:{fir.id}" in str(call) for call in delete_calls)
        assert entity_key_invalidated, "Entity cache key should be invalidated"
    
    @given(
        entity_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        updates=update_dict()
    )
    @settings(max_examples=20)
    def test_property_update_invalidates_cache(self, entity_id, updates):
        """
        Property 9: Data modification invalidates cache (UPDATE)
        
        For any data modification operation (create, update, delete), the
        corresponding cache entries should be invalidated or updated to
        maintain consistency.
        
        This test verifies that UPDATE operations invalidate cache.
        
        **Validates: Requirements 2.4**
        """
        # Setup
        mock_conn, mock_cursor = create_mock_connection()
        mock_cache = create_mock_cache_manager()
        repository = FIRRepository(mock_conn, mock_cache)
        
        # Mock find_by_id to return updated entity
        mock_cursor.fetchone.return_value = {
            'id': entity_id,
            'user_id': 'user_123',
            'status': updates.get('status', 'pending'),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': updates.get('description', 'Test'),
            'violation_text': 'Test violation',
            'priority': updates.get('priority', 1),
            'assigned_to': updates.get('assigned_to', 'officer_123')
        }
        
        # Execute update operation
        result = repository.update(entity_id, updates)
        
        # Verify entity was updated
        assert result is not None
        assert result.id == entity_id
        
        # Verify cache invalidation was called
        mock_cache.delete.assert_called()
        mock_cache.invalidate_pattern.assert_called()
        
        # Verify invalidation was called at least once for each type
        assert mock_cache.delete.call_count >= 1
        assert mock_cache.invalidate_pattern.call_count >= 1
        
        # Verify the entity key was invalidated
        delete_calls = [call[0] for call in mock_cache.delete.call_args_list]
        entity_key_invalidated = any(f"record:{entity_id}" in str(call) for call in delete_calls)
        assert entity_key_invalidated, "Entity cache key should be invalidated on update"
    
    @given(entity_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))))
    @settings(max_examples=20)
    def test_property_delete_invalidates_cache(self, entity_id):
        """
        Property 9: Data modification invalidates cache (DELETE)
        
        For any data modification operation (create, update, delete), the
        corresponding cache entries should be invalidated or updated to
        maintain consistency.
        
        This test verifies that DELETE operations invalidate cache.
        
        **Validates: Requirements 2.4**
        """
        # Setup
        mock_conn, mock_cursor = create_mock_connection()
        mock_cache = create_mock_cache_manager()
        repository = FIRRepository(mock_conn, mock_cache)
        
        # Mock successful delete
        mock_cursor.rowcount = 1
        
        # Execute delete operation
        result = repository.delete(entity_id)
        
        # Verify entity was deleted
        assert result is True
        
        # Verify cache invalidation was called
        mock_cache.delete.assert_called()
        mock_cache.invalidate_pattern.assert_called()
        
        # Verify invalidation was called at least once for each type
        assert mock_cache.delete.call_count >= 1
        assert mock_cache.invalidate_pattern.call_count >= 1
        
        # Verify the entity key was invalidated
        delete_calls = [call[0] for call in mock_cache.delete.call_args_list]
        entity_key_invalidated = any(f"record:{entity_id}" in str(call) for call in delete_calls)
        assert entity_key_invalidated, "Entity cache key should be invalidated on delete"
    
    @given(entity_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))))
    @settings(max_examples=10)
    def test_property_delete_no_invalidation_when_not_found(self, entity_id):
        """
        Property 9: Data modification invalidates cache (DELETE - not found case)
        
        When a delete operation finds no entity to delete, cache should NOT
        be invalidated since no data was modified.
        
        **Validates: Requirements 2.4**
        """
        # Setup
        mock_conn, mock_cursor = create_mock_connection()
        mock_cache = create_mock_cache_manager()
        repository = FIRRepository(mock_conn, mock_cache)
        
        # Mock unsuccessful delete (entity not found)
        mock_cursor.rowcount = 0
        
        # Execute delete operation
        result = repository.delete(entity_id)
        
        # Verify delete returned False
        assert result is False
        
        # Verify cache was NOT invalidated
        mock_cache.delete.assert_not_called()
        mock_cache.invalidate_pattern.assert_not_called()
    
    @given(firs=st.lists(fir_entity(), min_size=1, max_size=10))
    @settings(max_examples=10)
    def test_property_bulk_insert_invalidates_cache_for_all(self, firs):
        """
        Property 9: Data modification invalidates cache (BULK INSERT)
        
        For bulk insert operations, cache should be invalidated for ALL
        inserted entities to maintain consistency.
        
        **Validates: Requirements 2.4**
        """
        # Ensure unique IDs
        unique_firs = []
        seen_ids = set()
        for fir in firs:
            if fir.id not in seen_ids:
                unique_firs.append(fir)
                seen_ids.add(fir.id)
        
        assume(len(unique_firs) > 0)
        
        # Setup
        mock_conn, mock_cursor = create_mock_connection()
        mock_cache = create_mock_cache_manager()
        repository = FIRRepository(mock_conn, mock_cache)
        
        # Execute bulk insert
        result = repository.bulk_insert(unique_firs)
        
        # Verify all FIRs were inserted
        assert len(result) == len(unique_firs)
        
        # Verify cache invalidation was called for each FIR
        # Each FIR should trigger at least one delete and one invalidate_pattern call
        assert mock_cache.delete.call_count >= len(unique_firs)
        assert mock_cache.invalidate_pattern.call_count >= len(unique_firs)


class TestCacheFallbackProperties:
    """Property-based tests for cache failure fallback behavior."""
    
    # Property 10: Cache failure fallback
    # Validates: Requirements 2.5
    @given(fir=fir_entity())
    @settings(max_examples=20)
    def test_property_create_fallback_on_cache_failure(self, fir):
        """
        Property 10: Cache failure fallback (CREATE)
        
        For any cache operation that fails (connection error, timeout), the
        system should fall back to database queries and continue serving
        requests without error.
        
        This test verifies that CREATE operations succeed even when cache
        invalidation fails.
        
        **Validates: Requirements 2.5**
        """
        # Setup with failing cache
        mock_conn, mock_cursor = create_mock_connection()
        failing_cache = create_failing_cache_manager()
        repository = FIRRepository(mock_conn, failing_cache)
        
        # Execute create operation - should succeed despite cache failures
        result = repository.create(fir)
        
        # Verify entity was created successfully
        assert result is not None
        assert result.id == fir.id
        
        # Verify cache operations were attempted (and failed)
        failing_cache.delete.assert_called()
        
        # Verify database commit was called (operation succeeded)
        mock_conn.commit.assert_called()
        
        # Verify no exception was raised (fallback worked)
        # If we got here, the test passed
    
    @given(
        entity_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        updates=update_dict()
    )
    @settings(max_examples=20)
    def test_property_update_fallback_on_cache_failure(self, entity_id, updates):
        """
        Property 10: Cache failure fallback (UPDATE)
        
        For any cache operation that fails (connection error, timeout), the
        system should fall back to database queries and continue serving
        requests without error.
        
        This test verifies that UPDATE operations succeed even when cache
        invalidation fails.
        
        **Validates: Requirements 2.5**
        """
        # Setup with failing cache
        mock_conn, mock_cursor = create_mock_connection()
        failing_cache = create_failing_cache_manager()
        repository = FIRRepository(mock_conn, failing_cache)
        
        # Mock find_by_id to return updated entity
        mock_cursor.fetchone.return_value = {
            'id': entity_id,
            'user_id': 'user_123',
            'status': updates.get('status', 'pending'),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': updates.get('description', 'Test'),
            'violation_text': 'Test violation',
            'priority': updates.get('priority', 1),
            'assigned_to': updates.get('assigned_to', 'officer_123')
        }
        
        # Execute update operation - should succeed despite cache failures
        result = repository.update(entity_id, updates)
        
        # Verify entity was updated successfully
        assert result is not None
        assert result.id == entity_id
        
        # Verify cache operations were attempted (and failed)
        failing_cache.delete.assert_called()
        
        # Verify database commit was called (operation succeeded)
        assert mock_conn.commit.call_count >= 1
        
        # Verify no exception was raised (fallback worked)
    
    @given(entity_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))))
    @settings(max_examples=20)
    def test_property_delete_fallback_on_cache_failure(self, entity_id):
        """
        Property 10: Cache failure fallback (DELETE)
        
        For any cache operation that fails (connection error, timeout), the
        system should fall back to database queries and continue serving
        requests without error.
        
        This test verifies that DELETE operations succeed even when cache
        invalidation fails.
        
        **Validates: Requirements 2.5**
        """
        # Setup with failing cache
        mock_conn, mock_cursor = create_mock_connection()
        failing_cache = create_failing_cache_manager()
        repository = FIRRepository(mock_conn, failing_cache)
        
        # Mock successful delete
        mock_cursor.rowcount = 1
        
        # Execute delete operation - should succeed despite cache failures
        result = repository.delete(entity_id)
        
        # Verify entity was deleted successfully
        assert result is True
        
        # Verify cache operations were attempted (and failed)
        failing_cache.delete.assert_called()
        
        # Verify database commit was called (operation succeeded)
        mock_conn.commit.assert_called()
        
        # Verify no exception was raised (fallback worked)
    
    @given(firs=st.lists(fir_entity(), min_size=1, max_size=10))
    @settings(max_examples=10)
    def test_property_bulk_insert_fallback_on_cache_failure(self, firs):
        """
        Property 10: Cache failure fallback (BULK INSERT)
        
        For any cache operation that fails (connection error, timeout), the
        system should fall back to database queries and continue serving
        requests without error.
        
        This test verifies that BULK INSERT operations succeed even when
        cache invalidation fails.
        
        **Validates: Requirements 2.5**
        """
        # Ensure unique IDs
        unique_firs = []
        seen_ids = set()
        for fir in firs:
            if fir.id not in seen_ids:
                unique_firs.append(fir)
                seen_ids.add(fir.id)
        
        assume(len(unique_firs) > 0)
        
        # Setup with failing cache
        mock_conn, mock_cursor = create_mock_connection()
        failing_cache = create_failing_cache_manager()
        repository = FIRRepository(mock_conn, failing_cache)
        
        # Execute bulk insert - should succeed despite cache failures
        result = repository.bulk_insert(unique_firs)
        
        # Verify all FIRs were inserted successfully
        assert len(result) == len(unique_firs)
        
        # Verify cache operations were attempted (and failed)
        assert failing_cache.delete.call_count >= len(unique_firs)
        
        # Verify database commit was called (operation succeeded)
        mock_conn.commit.assert_called()
        
        # Verify no exception was raised (fallback worked)
    
    @given(fir=fir_entity())
    @settings(max_examples=10)
    def test_property_repository_works_without_cache_manager(self, fir):
        """
        Property 10: Cache failure fallback (NO CACHE MANAGER)
        
        The repository should work correctly even when no cache manager
        is provided (cache_manager=None), treating it as a graceful fallback.
        
        **Validates: Requirements 2.5**
        """
        # Setup without cache manager
        mock_conn, mock_cursor = create_mock_connection()
        repository = FIRRepository(mock_conn, cache_manager=None)
        
        # Execute create operation - should succeed without cache
        result = repository.create(fir)
        
        # Verify entity was created successfully
        assert result is not None
        assert result.id == fir.id
        
        # Verify database commit was called
        mock_conn.commit.assert_called()
        
        # Verify no exception was raised


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
