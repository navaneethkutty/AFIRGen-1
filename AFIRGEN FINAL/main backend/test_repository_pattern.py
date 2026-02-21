"""
Unit tests for optimized repository pattern.

Tests cover:
- Selective column retrieval (no SELECT *)
- Cursor-based pagination
- Optimized joins with index hints
- Database-level aggregation methods

Requirements: 1.3, 1.4, 1.5, 1.6
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, call
from repositories.base_repository import (
    BaseRepository,
    CursorInfo,
    PaginatedResult,
    JoinClause,
    JoinType,
    AggregateFunction
)
from repositories.fir_repository import FIR, FIRRepository


class TestCursorInfo:
    """Test cursor encoding and decoding."""
    
    def test_cursor_encode_decode_with_id_only(self):
        """Test cursor encoding/decoding with ID only."""
        cursor_info = CursorInfo(last_id="fir_123")
        encoded = cursor_info.encode()
        
        decoded = CursorInfo.decode(encoded)
        assert decoded.last_id == "fir_123"
        assert decoded.last_sort_value is None
    
    def test_cursor_encode_decode_with_sort_value(self):
        """Test cursor encoding/decoding with sort value."""
        cursor_info = CursorInfo(
            last_id="fir_123",
            last_sort_value="2024-01-15 10:30:00"
        )
        encoded = cursor_info.encode()
        
        decoded = CursorInfo.decode(encoded)
        assert decoded.last_id == "fir_123"
        assert decoded.last_sort_value == "2024-01-15 10:30:00"
    
    def test_cursor_decode_invalid_format(self):
        """Test cursor decoding with invalid format."""
        with pytest.raises(ValueError, match="Invalid cursor format"):
            CursorInfo.decode("invalid_cursor")


class TestJoinClause:
    """Test JOIN clause generation."""
    
    def test_inner_join_without_index_hint(self):
        """Test INNER JOIN SQL generation without index hint."""
        join = JoinClause(
            join_type=JoinType.INNER,
            table="violations",
            alias="v",
            on_condition="f.id = v.fir_id"
        )
        
        sql = join.to_sql()
        assert sql == "INNER JOIN violations v ON f.id = v.fir_id"
    
    def test_left_join_with_index_hint(self):
        """Test LEFT JOIN SQL generation with index hint."""
        join = JoinClause(
            join_type=JoinType.LEFT,
            table="violations",
            alias="v",
            on_condition="f.id = v.fir_id",
            index_hint="idx_violations_fir_id"
        )
        
        sql = join.to_sql()
        assert sql == "LEFT JOIN violations v USE INDEX (idx_violations_fir_id) ON f.id = v.fir_id"
    
    def test_join_without_alias(self):
        """Test JOIN SQL generation without alias."""
        join = JoinClause(
            join_type=JoinType.RIGHT,
            table="users",
            alias=None,
            on_condition="f.user_id = users.id"
        )
        
        sql = join.to_sql()
        assert sql == "RIGHT JOIN users ON f.user_id = users.id"


class TestFIRRepository:
    """Test FIR repository implementation."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection."""
        connection = Mock()
        cursor = Mock()
        cursor.fetchone = Mock()
        cursor.fetchall = Mock()
        cursor.execute = Mock()
        cursor.close = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        connection.cursor = Mock(return_value=cursor)
        connection.commit = Mock()
        connection.rollback = Mock()
        return connection
    
    @pytest.fixture
    def repository(self, mock_connection):
        """Create FIR repository instance."""
        return FIRRepository(mock_connection)
    
    def test_selective_column_retrieval(self, repository, mock_connection):
        """
        Test that repository uses selective column retrieval instead of SELECT *.
        
        Validates: Requirements 1.4
        """
        # Setup mock with all required fields
        cursor = mock_connection.cursor.return_value
        cursor.fetchone.return_value = {
            'id': 'fir_123',
            'user_id': 'user_1',
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': None,
            'violation_text': None,
            'priority': None,
            'assigned_to': None
        }
        
        # Execute with specific fields
        result = repository.find_by_id('fir_123', fields=['id', 'status', 'user_id', 'created_at', 'updated_at'])
        
        # Verify query uses explicit columns, not SELECT *
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        assert 'SELECT id, status, user_id, created_at, updated_at FROM' in query
        assert 'SELECT *' not in query
    
    def test_no_select_star_in_default_query(self, repository, mock_connection):
        """
        Test that default queries use explicit column names.
        
        Validates: Requirements 1.4
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchone.return_value = {
            'id': 'fir_123',
            'user_id': 'user_1',
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Execute without specifying fields
        result = repository.find_by_id('fir_123')
        
        # Verify query uses explicit columns
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should contain all column names
        for col in FIRRepository.ALL_COLUMNS:
            assert col in query
    
    def test_cursor_based_pagination(self, repository, mock_connection):
        """
        Test cursor-based pagination for efficient large result set handling.
        
        Validates: Requirements 1.5
        """
        # Setup mock with separate cursors for count and data queries
        count_cursor = Mock()
        count_cursor.fetchall.return_value = [{'aggregate_value': 100}]
        count_cursor.close = Mock()
        count_cursor.__enter__ = Mock(return_value=count_cursor)
        count_cursor.__exit__ = Mock(return_value=False)
        
        data_cursor = Mock()
        mock_rows = [
            {
                'id': f'fir_{i}',
                'user_id': 'user_1',
                'status': 'pending',
                'created_at': datetime(2024, 1, i+1),
                'updated_at': datetime(2024, 1, i+1),
                'description': None,
                'violation_text': None,
                'priority': None,
                'assigned_to': None
            }
            for i in range(5)
        ]
        data_cursor.fetchall.return_value = mock_rows
        data_cursor.close = Mock()
        data_cursor.__enter__ = Mock(return_value=data_cursor)
        data_cursor.__exit__ = Mock(return_value=False)
        
        # Return data cursor first (for main query), then count cursor (for total count)
        mock_connection.cursor.side_effect = [data_cursor, count_cursor]
        
        # Execute pagination
        result = repository.find_paginated(limit=4)
        
        # Verify cursor-based approach
        assert mock_connection.cursor.call_count == 2  # Data query + count query
        
        # Check the data query
        data_cursor.execute.assert_called_once()
        data_query = data_cursor.execute.call_args[0][0]
        
        # Should use LIMIT (not OFFSET)
        assert 'LIMIT' in data_query
        assert 'OFFSET' not in data_query
        
        # Should return paginated result
        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 4
        assert result.has_more is True
        assert result.next_cursor is not None
    
    def test_pagination_with_cursor(self, repository, mock_connection):
        """
        Test pagination using cursor from previous page.
        
        Validates: Requirements 1.5
        """
        # Create cursor for second page
        cursor_info = CursorInfo(last_id='fir_4')
        encoded_cursor = cursor_info.encode()
        
        # Setup mock with separate cursors
        count_cursor = Mock()
        count_cursor.fetchall.return_value = [{'aggregate_value': 100}]
        count_cursor.close = Mock()
        count_cursor.__enter__ = Mock(return_value=count_cursor)
        count_cursor.__exit__ = Mock(return_value=False)
        
        data_cursor = Mock()
        data_cursor.fetchall.return_value = []
        data_cursor.close = Mock()
        data_cursor.__enter__ = Mock(return_value=data_cursor)
        data_cursor.__exit__ = Mock(return_value=False)
        
        # Return data cursor first, then count cursor
        mock_connection.cursor.side_effect = [data_cursor, count_cursor]
        
        # Execute pagination with cursor
        result = repository.find_paginated(cursor=encoded_cursor, limit=4)
        
        # Verify cursor is used in query (check the data query)
        data_cursor.execute.assert_called_once()
        data_query = data_cursor.execute.call_args[0][0]
        data_params = data_cursor.execute.call_args[0][1]
        
        # Should filter by cursor ID
        assert 'id > %s' in data_query or '>' in data_query
        assert 'fir_4' in data_params
    
    def test_optimized_join_with_index_hint(self, repository, mock_connection):
        """
        Test optimized joins with index hints.
        
        Validates: Requirements 1.3
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchall.return_value = [{
            'id': 'fir_123',
            'user_id': 'user_1',
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': None,
            'violation_text': None,
            'priority': None,
            'assigned_to': None,
            'violation_id': 'v_1',
            'violation_type': 'speeding',
            'severity': 'high'
        }]
        
        # Execute join query
        result = repository.find_with_violations('fir_123')
        
        # Verify join with index hint
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should contain JOIN with USE INDEX
        assert 'JOIN' in query.upper()
        assert 'USE INDEX' in query
        assert 'idx_violations_fir_id' in query
    
    def test_database_level_count_aggregation(self, repository, mock_connection):
        """
        Test database-level COUNT aggregation.
        
        Validates: Requirements 1.6
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchall.return_value = [{'aggregate_value': 42}]
        
        # Execute count
        result = repository.count(filters={'status': 'pending'})
        
        # Verify database-level aggregation
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should use COUNT(*) in SQL
        assert 'COUNT(*)' in query.upper()
        assert result == 42
    
    def test_database_level_sum_aggregation(self, repository, mock_connection):
        """
        Test database-level SUM aggregation.
        
        Validates: Requirements 1.6
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchall.return_value = [{'aggregate_value': 150.5}]
        
        # Execute sum
        result = repository.sum('priority', filters={'status': 'pending'})
        
        # Verify database-level aggregation
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should use SUM() in SQL
        assert 'SUM(priority)' in query
        assert result == 150.5
    
    def test_database_level_avg_aggregation(self, repository, mock_connection):
        """
        Test database-level AVG aggregation.
        
        Validates: Requirements 1.6
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchall.return_value = [{'aggregate_value': 3.5}]
        
        # Execute average
        result = repository.avg('priority', filters={'user_id': 'user_1'})
        
        # Verify database-level aggregation
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should use AVG() in SQL
        assert 'AVG(priority)' in query
        assert result == 3.5
    
    def test_database_level_max_aggregation(self, repository, mock_connection):
        """
        Test database-level MAX aggregation.
        
        Validates: Requirements 1.6
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        max_date = datetime(2024, 1, 15)
        cursor.fetchall.return_value = [{'aggregate_value': max_date}]
        
        # Execute max
        result = repository.max('created_at')
        
        # Verify database-level aggregation
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should use MAX() in SQL
        assert 'MAX(created_at)' in query
        assert result == max_date
    
    def test_database_level_min_aggregation(self, repository, mock_connection):
        """
        Test database-level MIN aggregation.
        
        Validates: Requirements 1.6
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        min_date = datetime(2024, 1, 1)
        cursor.fetchall.return_value = [{'aggregate_value': min_date}]
        
        # Execute min
        result = repository.min('created_at')
        
        # Verify database-level aggregation
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should use MIN() in SQL
        assert 'MIN(created_at)' in query
        assert result == min_date
    
    def test_group_by_aggregation(self, repository, mock_connection):
        """
        Test aggregation with GROUP BY clause.
        
        Validates: Requirements 1.6
        """
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchall.return_value = [
            {'status': 'pending', 'aggregate_value': 10},
            {'status': 'completed', 'aggregate_value': 25},
            {'status': 'rejected', 'aggregate_value': 5}
        ]
        
        # Execute grouped aggregation
        result = repository.count_by_status()
        
        # Verify GROUP BY in query
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Should use GROUP BY
        assert 'GROUP BY' in query.upper()
        assert 'status' in query
        assert len(result) == 3
    
    def test_bulk_insert(self, repository, mock_connection):
        """Test bulk insert operation."""
        # Create test FIRs
        firs = [
            FIR(
                id=f'fir_{i}',
                user_id='user_1',
                status='pending',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for i in range(3)
        ]
        
        # Setup mock
        cursor = mock_connection.cursor.return_value
        
        # Execute bulk insert
        result = repository.bulk_insert(firs)
        
        # Verify executemany was called
        cursor.executemany.assert_called_once()
        query = cursor.executemany.call_args[0][0]
        
        # Should use INSERT with explicit columns
        assert 'INSERT INTO' in query
        assert 'VALUES' in query
        assert len(result) == 3
        
        # Verify commit was called
        mock_connection.commit.assert_called_once()
    
    def test_column_name_sanitization(self, repository):
        """Test that invalid column names are rejected."""
        # Test with SQL injection attempt - FIRRepository validates against allowed columns
        with pytest.raises(ValueError, match="Invalid fields requested"):
            repository.find_by_id('fir_123', fields=['id; DROP TABLE firs;'])
        
        # Test with invalid characters - also caught by field validation
        with pytest.raises(ValueError, match="Invalid fields requested"):
            repository.find_by_id('fir_123', fields=['id', 'user@id'])
    
    def test_valid_column_names_with_table_prefix(self, repository, mock_connection):
        """Test that valid column names are accepted."""
        # Setup mock
        cursor = mock_connection.cursor.return_value
        cursor.fetchone.return_value = {
            'id': 'fir_123',
            'user_id': 'user_1',
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'description': None,
            'violation_text': None,
            'priority': None,
            'assigned_to': None
        }
        
        # Should allow valid column names
        try:
            repository.find_by_id('fir_123', fields=['id', 'status'])
        except ValueError:
            pytest.fail("Should allow valid column names")


class TestPaginatedResult:
    """Test paginated result model."""
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary for API responses."""
        result = PaginatedResult(
            items=[{'id': 'fir_1'}, {'id': 'fir_2'}],
            total_count=100,
            page_size=20,
            next_cursor='abc123',
            has_more=True
        )
        
        data = result.to_dict()
        
        assert data['items'] == [{'id': 'fir_1'}, {'id': 'fir_2'}]
        assert data['total_count'] == 100
        assert data['page_size'] == 20
        assert data['next_cursor'] == 'abc123'
        assert data['has_more'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
