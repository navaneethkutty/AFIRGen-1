"""
Unit tests for cache invalidation logic in repository layer.

Tests cover:
- Cache invalidation on create operations
- Cache invalidation on update operations
- Cache invalidation on delete operations
- Fallback behavior when cache operations fail
- Pattern-based cache invalidation

Requirements: 2.4, 2.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from redis.exceptions import RedisError

# Import components to test
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from repositories.fir_repository import FIRRepository, FIR
from infrastructure.cache_manager import CacheManager


class TestCacheInvalidationUnit:
    """Unit tests for cache invalidation in repository layer."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        return mock_conn
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        mock_cache = Mock(spec=CacheManager)
        mock_cache.delete.return_value = True
        mock_cache.invalidate_pattern.return_value = 5
        # Configure get_or_fetch to call the fetch function
        mock_cache.get_or_fetch.side_effect = lambda key, fetch_fn, ttl, namespace: fetch_fn()
        return mock_cache
    
    @pytest.fixture
    def fir_repository(self, mock_connection, mock_cache_manager):
        """Create FIR repository with mocked dependencies."""
        return FIRRepository(mock_connection, mock_cache_manager)
    
    @pytest.fixture
    def sample_fir(self):
        """Create a sample FIR entity."""
        return FIR(
            id="fir_12345",
            user_id="user_789",
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            description="Test FIR",
            violation_text="Test violation",
            priority=1,
            assigned_to="officer_123"
        )
    
    def test_create_invalidates_cache(self, fir_repository, mock_cache_manager, sample_fir):
        """Test that creating a FIR invalidates relevant cache entries."""
        # Create FIR
        result = fir_repository.create(sample_fir)
        
        # Verify FIR was created
        assert result.id == sample_fir.id
        
        # Verify cache was invalidated
        mock_cache_manager.delete.assert_called()
        mock_cache_manager.invalidate_pattern.assert_called()
        
        # Verify invalidation patterns were used
        invalidation_calls = [call[0] for call in mock_cache_manager.invalidate_pattern.call_args_list]
        assert any("list:*" in str(call) for call in invalidation_calls)
        assert any("stats:*" in str(call) for call in invalidation_calls)
    
    def test_update_invalidates_cache(self, fir_repository, mock_cache_manager, mock_connection):
        """Test that updating a FIR invalidates relevant cache entries."""
        # Mock find_by_id to return updated entity
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = {
            'id': 'fir_12345',
            'user_id': 'user_789',
            'status': 'completed',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': 'Updated FIR',
            'violation_text': 'Test violation',
            'priority': 1,
            'assigned_to': 'officer_123'
        }
        
        # Update FIR
        updates = {'status': 'completed', 'description': 'Updated FIR'}
        result = fir_repository.update('fir_12345', updates)
        
        # Verify update was executed
        assert result is not None
        assert result.status == 'completed'
        
        # Verify cache was invalidated
        mock_cache_manager.delete.assert_called()
        mock_cache_manager.invalidate_pattern.assert_called()
    
    def test_delete_invalidates_cache(self, fir_repository, mock_cache_manager, mock_connection):
        """Test that deleting a FIR invalidates relevant cache entries."""
        # Mock successful delete
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 1
        
        # Delete FIR
        result = fir_repository.delete('fir_12345')
        
        # Verify delete was successful
        assert result is True
        
        # Verify cache was invalidated
        mock_cache_manager.delete.assert_called()
        mock_cache_manager.invalidate_pattern.assert_called()
    
    def test_delete_no_cache_invalidation_when_not_found(self, fir_repository, mock_cache_manager, mock_connection):
        """Test that cache is not invalidated when entity is not found."""
        # Mock unsuccessful delete (entity not found)
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 0
        
        # Delete non-existent FIR
        result = fir_repository.delete('nonexistent_id')
        
        # Verify delete returned False
        assert result is False
        
        # Verify cache was not invalidated
        mock_cache_manager.delete.assert_not_called()
        mock_cache_manager.invalidate_pattern.assert_not_called()
    
    def test_bulk_insert_invalidates_cache_for_all(self, fir_repository, mock_cache_manager, sample_fir):
        """Test that bulk insert invalidates cache for all inserted FIRs."""
        # Create multiple FIRs
        firs = [
            sample_fir,
            FIR(
                id="fir_67890",
                user_id="user_789",
                status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                description="Test FIR 2",
                violation_text="Test violation 2",
                priority=2,
                assigned_to="officer_456"
            )
        ]
        
        # Bulk insert
        result = fir_repository.bulk_insert(firs)
        
        # Verify all FIRs were inserted
        assert len(result) == 2
        
        # Verify cache was invalidated for each FIR
        assert mock_cache_manager.delete.call_count >= 2
        assert mock_cache_manager.invalidate_pattern.call_count >= 2
    
    def test_cache_invalidation_fallback_on_failure(self, fir_repository, mock_cache_manager, sample_fir):
        """Test that cache invalidation failures don't break create operations."""
        # Make cache operations fail
        mock_cache_manager.delete.side_effect = RedisError("Connection failed")
        mock_cache_manager.invalidate_pattern.side_effect = RedisError("Connection failed")
        
        # Create FIR - should succeed despite cache failures
        result = fir_repository.create(sample_fir)
        
        # Verify FIR was created successfully
        assert result.id == sample_fir.id
        
        # Verify cache operations were attempted
        mock_cache_manager.delete.assert_called()
    
    def test_update_fallback_on_cache_failure(self, fir_repository, mock_cache_manager, mock_connection):
        """Test that cache invalidation failures don't break update operations."""
        # Mock find_by_id to return updated entity
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = {
            'id': 'fir_12345',
            'user_id': 'user_789',
            'status': 'completed',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': 'Updated FIR',
            'violation_text': 'Test violation',
            'priority': 1,
            'assigned_to': 'officer_123'
        }
        
        # Make cache operations fail
        mock_cache_manager.delete.side_effect = RedisError("Connection failed")
        mock_cache_manager.invalidate_pattern.side_effect = RedisError("Connection failed")
        
        # Update FIR - should succeed despite cache failures
        updates = {'status': 'completed'}
        result = fir_repository.update('fir_12345', updates)
        
        # Verify update was successful
        assert result is not None
        assert result.status == 'completed'
    
    def test_delete_fallback_on_cache_failure(self, fir_repository, mock_cache_manager, mock_connection):
        """Test that cache invalidation failures don't break delete operations."""
        # Mock successful delete
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 1
        
        # Make cache operations fail
        mock_cache_manager.delete.side_effect = RedisError("Connection failed")
        mock_cache_manager.invalidate_pattern.side_effect = RedisError("Connection failed")
        
        # Delete FIR - should succeed despite cache failures
        result = fir_repository.delete('fir_12345')
        
        # Verify delete was successful
        assert result is True
    
    def test_repository_without_cache_manager(self, mock_connection, sample_fir):
        """Test that repository works without cache manager (no cache invalidation)."""
        # Create repository without cache manager
        repo = FIRRepository(mock_connection, cache_manager=None)
        
        # Create FIR - should succeed without cache invalidation
        result = repo.create(sample_fir)
        
        # Verify FIR was created
        assert result.id == sample_fir.id
    
    def test_cache_namespace_is_correct(self, fir_repository):
        """Test that FIR repository uses correct cache namespace."""
        namespace = fir_repository._get_cache_namespace()
        assert namespace == "fir"
    
    def test_invalidation_patterns_include_required_patterns(self, fir_repository):
        """Test that invalidation patterns include all required cache types."""
        patterns = fir_repository._get_invalidation_patterns("fir_12345")
        
        # Verify all required patterns are included
        assert "list:*" in patterns
        assert "query:*" in patterns
        assert "stats:*" in patterns
        assert "count:*" in patterns
        assert "user:*" in patterns
    
    def test_update_with_empty_updates_returns_entity(self, fir_repository, mock_connection):
        """Test that update with empty updates dict returns entity without modification."""
        # Mock find_by_id to return entity
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = {
            'id': 'fir_12345',
            'user_id': 'user_789',
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': 'Test FIR',
            'violation_text': 'Test violation',
            'priority': 1,
            'assigned_to': 'officer_123'
        }
        
        # Update with empty dict
        result = fir_repository.update('fir_12345', {})
        
        # Verify entity was returned
        assert result is not None
        assert result.id == 'fir_12345'
        
        # Verify no UPDATE query was executed (only SELECT)
        mock_cursor.execute.assert_called_once()
        assert "SELECT" in mock_cursor.execute.call_args[0][0]
    
    def test_create_commits_transaction(self, fir_repository, mock_connection, sample_fir):
        """Test that create commits the database transaction."""
        # Create FIR
        fir_repository.create(sample_fir)
        
        # Verify commit was called
        mock_connection.commit.assert_called_once()
    
    def test_update_commits_transaction(self, fir_repository, mock_connection):
        """Test that update commits the database transaction."""
        # Mock find_by_id
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = {
            'id': 'fir_12345',
            'user_id': 'user_789',
            'status': 'completed',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': 'Updated FIR',
            'violation_text': 'Test violation',
            'priority': 1,
            'assigned_to': 'officer_123'
        }
        
        # Update FIR
        fir_repository.update('fir_12345', {'status': 'completed'})
        
        # Verify commit was called
        assert mock_connection.commit.call_count >= 1
    
    def test_delete_commits_transaction(self, fir_repository, mock_connection):
        """Test that delete commits the database transaction."""
        # Mock successful delete
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 1
        
        # Delete FIR
        fir_repository.delete('fir_12345')
        
        # Verify commit was called
        mock_connection.commit.assert_called_once()
    
    def test_create_rollback_on_error(self, fir_repository, mock_connection, sample_fir):
        """Test that create rolls back transaction on error."""
        # Make execute fail
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Create FIR - should raise exception
        with pytest.raises(Exception, match="Database error"):
            fir_repository.create(sample_fir)
        
        # Verify rollback was called
        mock_connection.rollback.assert_called_once()
    
    def test_update_rollback_on_error(self, fir_repository, mock_connection):
        """Test that update rolls back transaction on error."""
        # Make execute fail
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Update FIR - should raise exception
        with pytest.raises(Exception, match="Database error"):
            fir_repository.update('fir_12345', {'status': 'completed'})
        
        # Verify rollback was called
        mock_connection.rollback.assert_called_once()
    
    def test_delete_rollback_on_error(self, fir_repository, mock_connection):
        """Test that delete rolls back transaction on error."""
        # Make execute fail
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Delete FIR - should raise exception
        with pytest.raises(Exception, match="Database error"):
            fir_repository.delete('fir_12345')
        
        # Verify rollback was called
        mock_connection.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
