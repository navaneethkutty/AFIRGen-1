"""
Property-based tests for pagination and aggregation.

This module contains property tests that validate:
- Property 4: Cursor-based pagination for large result sets
- Property 5: Database-level aggregation

Requirements: 1.5, 1.6
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from repositories.base_repository import (
    BaseRepository,
    CursorInfo,
    PaginatedResult,
    AggregateFunction
)
from repositories.fir_repository import FIR, FIRRepository


# Custom strategies for generating test data
@st.composite
def fir_id_strategy(draw):
    """Generate valid FIR IDs."""
    prefix = draw(st.sampled_from(['fir', 'FIR', 'f']))
    number = draw(st.integers(min_value=1, max_value=999999))
    return f"{prefix}_{number}"


@st.composite
def fir_entity_strategy(draw):
    """Generate FIR entities for testing."""
    fir_id = draw(fir_id_strategy())
    user_id = f"user_{draw(st.integers(min_value=1, max_value=100))}"
    status = draw(st.sampled_from(['pending', 'completed', 'rejected', 'in_progress']))
    
    base_date = datetime(2024, 1, 1)
    days_offset = draw(st.integers(min_value=0, max_value=365))
    created_at = base_date + timedelta(days=days_offset)
    updated_at = created_at + timedelta(hours=draw(st.integers(min_value=0, max_value=48)))
    
    priority = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10)))
    
    return FIR(
        id=fir_id,
        user_id=user_id,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        description=draw(st.one_of(st.none(), st.text(min_size=10, max_size=100))),
        violation_text=draw(st.one_of(st.none(), st.text(min_size=10, max_size=100))),
        priority=priority,
        assigned_to=draw(st.one_of(st.none(), st.text(min_size=5, max_size=20)))
    )


class TestPaginationProperties:
    """
    Property-based tests for cursor-based pagination.
    
    **Validates: Requirements 1.5**
    """
    
    @given(
        limit=st.integers(min_value=1, max_value=100),
        total_items=st.integers(min_value=0, max_value=500)
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_4_cursor_based_pagination_uses_cursor_not_offset(self, limit, total_items):
        """
        Property 4: Cursor-based pagination for large result sets.
        
        For any paginated query request, the Database_Layer should use cursor-based
        pagination (using a unique sortable column) rather than OFFSET-based pagination.
        
        This property verifies that:
        1. Pagination queries use cursor filtering (WHERE id > cursor_value)
        2. Pagination queries do NOT use OFFSET clause
        3. Pagination uses LIMIT to control page size
        
        **Validates: Requirements 1.5**
        """
        # Arrange: Create mock connection and repository
        mock_connection = Mock()
        
        # Create separate cursors for data and count queries
        data_cursor = Mock()
        count_cursor = Mock()
        
        # Generate mock data
        mock_rows = []
        for i in range(min(limit + 1, total_items)):
            mock_rows.append({
                'id': f'fir_{i}',
                'user_id': 'user_1',
                'status': 'pending',
                'created_at': datetime(2024, 1, 1) + timedelta(days=i),
                'updated_at': datetime(2024, 1, 1) + timedelta(days=i),
                'description': None,
                'violation_text': None,
                'priority': None,
                'assigned_to': None
            })
        
        data_cursor.fetchall.return_value = mock_rows
        data_cursor.close = Mock()
        data_cursor.__enter__ = Mock(return_value=data_cursor)
        data_cursor.__exit__ = Mock(return_value=False)
        
        count_cursor.fetchall.return_value = [{'aggregate_value': total_items}]
        count_cursor.close = Mock()
        count_cursor.__enter__ = Mock(return_value=count_cursor)
        count_cursor.__exit__ = Mock(return_value=False)
        
        # Return data cursor first, then count cursor
        mock_connection.cursor.side_effect = [data_cursor, count_cursor]
        
        repository = FIRRepository(mock_connection)
        
        # Act: Execute pagination without cursor (first page)
        result = repository.find_paginated(limit=limit)
        
        # Assert: Verify cursor-based pagination properties
        assert mock_connection.cursor.call_count == 2  # Data query + count query
        
        # Check the data query (first cursor call)
        data_cursor.execute.assert_called_once()
        data_query = data_cursor.execute.call_args[0][0]
        
        # Property 1: Query should use LIMIT (for page size control)
        assert 'LIMIT' in data_query.upper(), \
            "Cursor-based pagination must use LIMIT clause"
        
        # Property 2: Query should NOT use OFFSET (inefficient for large datasets)
        assert 'OFFSET' not in data_query.upper(), \
            "Cursor-based pagination must NOT use OFFSET clause"
        
        # Property 3: Result should be a PaginatedResult
        assert isinstance(result, PaginatedResult), \
            "Pagination should return PaginatedResult object"
        
        # Property 4: Page size should not exceed limit
        assert len(result.items) <= limit, \
            f"Page size {len(result.items)} should not exceed limit {limit}"
    
    @given(
        limit=st.integers(min_value=1, max_value=50),
        cursor_id=fir_id_strategy()
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_4_pagination_with_cursor_filters_by_cursor(self, limit, cursor_id):
        """
        Property 4: Cursor-based pagination uses cursor for filtering.
        
        For any paginated query with a cursor, the query should filter results
        using the cursor value (WHERE id > cursor_value) rather than using OFFSET.
        
        This ensures efficient pagination for large datasets by using indexed columns.
        
        **Validates: Requirements 1.5**
        """
        # Arrange: Create cursor
        cursor_info = CursorInfo(last_id=cursor_id)
        encoded_cursor = cursor_info.encode()
        
        # Create mock connection
        mock_connection = Mock()
        
        data_cursor = Mock()
        count_cursor = Mock()
        
        data_cursor.fetchall.return_value = []
        data_cursor.close = Mock()
        data_cursor.__enter__ = Mock(return_value=data_cursor)
        data_cursor.__exit__ = Mock(return_value=False)
        
        count_cursor.fetchall.return_value = [{'aggregate_value': 0}]
        count_cursor.close = Mock()
        count_cursor.__enter__ = Mock(return_value=count_cursor)
        count_cursor.__exit__ = Mock(return_value=False)
        
        mock_connection.cursor.side_effect = [data_cursor, count_cursor]
        
        repository = FIRRepository(mock_connection)
        
        # Act: Execute pagination with cursor
        result = repository.find_paginated(cursor=encoded_cursor, limit=limit)
        
        # Assert: Verify cursor filtering
        data_cursor.execute.assert_called_once()
        data_query = data_cursor.execute.call_args[0][0]
        data_params = data_cursor.execute.call_args[0][1]
        
        # Property 1: Query should filter by cursor (WHERE id > cursor_value)
        assert '>' in data_query, \
            "Cursor-based pagination must filter using cursor value"
        
        # Property 2: Cursor ID should be in query parameters
        assert cursor_id in data_params, \
            f"Cursor ID '{cursor_id}' should be used in query parameters"
        
        # Property 3: Should still use LIMIT, not OFFSET
        assert 'LIMIT' in data_query.upper(), \
            "Pagination with cursor must still use LIMIT"
        assert 'OFFSET' not in data_query.upper(), \
            "Pagination with cursor must NOT use OFFSET"
    
    @given(
        limit=st.integers(min_value=1, max_value=50),
        total_items=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_4_pagination_has_more_flag_correctness(self, limit, total_items):
        """
        Property 4: Pagination correctly indicates if more items exist.
        
        For any paginated result, the has_more flag should accurately reflect
        whether additional pages exist beyond the current page.
        
        **Validates: Requirements 1.5**
        """
        # Arrange
        mock_connection = Mock()
        
        data_cursor = Mock()
        count_cursor = Mock()
        
        # Generate mock data (limit + 1 to check for more items)
        items_to_return = min(limit + 1, total_items)
        mock_rows = []
        for i in range(items_to_return):
            mock_rows.append({
                'id': f'fir_{i}',
                'user_id': 'user_1',
                'status': 'pending',
                'created_at': datetime(2024, 1, 1) + timedelta(days=i),
                'updated_at': datetime(2024, 1, 1) + timedelta(days=i),
                'description': None,
                'violation_text': None,
                'priority': None,
                'assigned_to': None
            })
        
        data_cursor.fetchall.return_value = mock_rows
        data_cursor.close = Mock()
        data_cursor.__enter__ = Mock(return_value=data_cursor)
        data_cursor.__exit__ = Mock(return_value=False)
        
        count_cursor.fetchall.return_value = [{'aggregate_value': total_items}]
        count_cursor.close = Mock()
        count_cursor.__enter__ = Mock(return_value=count_cursor)
        count_cursor.__exit__ = Mock(return_value=False)
        
        mock_connection.cursor.side_effect = [data_cursor, count_cursor]
        
        repository = FIRRepository(mock_connection)
        
        # Act
        result = repository.find_paginated(limit=limit)
        
        # Assert: Verify has_more flag correctness
        expected_has_more = total_items > limit
        
        assert result.has_more == expected_has_more, \
            f"has_more should be {expected_has_more} when total_items={total_items} and limit={limit}"
        
        # Property: If has_more is True, next_cursor should be provided
        if result.has_more:
            assert result.next_cursor is not None, \
                "next_cursor must be provided when has_more is True"
        
        # Property: Returned items should not exceed limit
        assert len(result.items) <= limit, \
            f"Returned {len(result.items)} items but limit was {limit}"


class TestAggregationProperties:
    """
    Property-based tests for database-level aggregation.
    
    **Validates: Requirements 1.6**
    """
    
    @given(
        aggregate_func=st.sampled_from([
            AggregateFunction.COUNT,
            AggregateFunction.SUM,
            AggregateFunction.AVG,
            AggregateFunction.MAX,
            AggregateFunction.MIN
        ]),
        column=st.sampled_from(['priority', 'created_at', '*'])
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_5_database_level_aggregation_uses_sql_functions(
        self,
        aggregate_func,
        column
    ):
        """
        Property 5: Database-level aggregation.
        
        For any aggregate operation (COUNT, SUM, AVG, MAX, MIN), the query should
        use SQL aggregate functions rather than fetching all rows and computing
        in application code.
        
        This property verifies that:
        1. Aggregation queries use SQL aggregate functions (COUNT, SUM, AVG, MAX, MIN)
        2. Aggregation is performed at the database level, not in application code
        3. Queries return aggregated results, not raw data
        
        **Validates: Requirements 1.6**
        """
        # Skip invalid combinations
        if aggregate_func != AggregateFunction.COUNT and column == '*':
            assume(False)  # SUM(*), AVG(*), etc. are invalid
        
        # Arrange
        mock_connection = Mock()
        cursor = Mock()
        
        # Mock aggregation result
        if aggregate_func == AggregateFunction.COUNT:
            mock_result = [{'aggregate_value': 42}]
        elif aggregate_func in [AggregateFunction.SUM, AggregateFunction.AVG]:
            mock_result = [{'aggregate_value': 123.45}]
        elif aggregate_func == AggregateFunction.MAX:
            mock_result = [{'aggregate_value': datetime(2024, 12, 31)}]
        else:  # MIN
            mock_result = [{'aggregate_value': datetime(2024, 1, 1)}]
        
        cursor.fetchall.return_value = mock_result
        cursor.close = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        
        mock_connection.cursor.return_value = cursor
        
        repository = FIRRepository(mock_connection)
        
        # Act: Execute aggregation
        result = repository.aggregate(
            function=aggregate_func,
            column=column
        )
        
        # Assert: Verify database-level aggregation
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Property 1: Query should contain the SQL aggregate function
        assert aggregate_func.value in query.upper(), \
            f"Query must use SQL {aggregate_func.value} function for database-level aggregation"
        
        # Property 2: Query should NOT fetch all rows (no SELECT without aggregation)
        # The presence of aggregate function and absence of raw column selection indicates this
        assert 'aggregate_value' in query.lower() or 'as aggregate_value' in query.lower(), \
            "Aggregation query should alias result as 'aggregate_value'"
        
        # Property 3: Result should be aggregated, not raw data
        assert isinstance(result, list), \
            "Aggregation should return a list of results"
        assert len(result) > 0, \
            "Aggregation should return at least one result"
        assert 'aggregate_value' in result[0], \
            "Aggregation result should contain 'aggregate_value' key"
    
    @given(
        values=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_5_count_aggregation_returns_correct_count(self, values):
        """
        Property 5: COUNT aggregation returns correct count.
        
        For any set of database rows, COUNT(*) should return the exact number
        of rows, computed at the database level.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        expected_count = len(values)
        
        mock_connection = Mock()
        cursor = Mock()
        cursor.fetchall.return_value = [{'aggregate_value': expected_count}]
        cursor.close = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        
        mock_connection.cursor.return_value = cursor
        
        repository = FIRRepository(mock_connection)
        
        # Act
        result = repository.count()
        
        # Assert
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Property 1: Query uses COUNT(*)
        assert 'COUNT(*)' in query.upper(), \
            "Count aggregation must use COUNT(*) SQL function"
        
        # Property 2: Result matches expected count
        assert result == expected_count, \
            f"COUNT should return {expected_count}, got {result}"
    
    @given(
        column=st.sampled_from(['priority', 'created_at']),
        filter_column=st.sampled_from(['status', 'user_id']),
        filter_value=st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_5_aggregation_with_filters_applies_where_clause(
        self,
        column,
        filter_column,
        filter_value
    ):
        """
        Property 5: Aggregation with filters applies WHERE clause at database level.
        
        For any aggregate operation with filters, the filtering should be applied
        at the database level using WHERE clause, not by fetching all rows and
        filtering in application code.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        mock_connection = Mock()
        cursor = Mock()
        cursor.fetchall.return_value = [{'aggregate_value': 10}]
        cursor.close = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        
        mock_connection.cursor.return_value = cursor
        
        repository = FIRRepository(mock_connection)
        
        filters = {filter_column: filter_value}
        
        # Act
        result = repository.aggregate(
            function=AggregateFunction.COUNT,
            column='*',
            filters=filters
        )
        
        # Assert
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]
        
        # Property 1: Query should contain WHERE clause
        assert 'WHERE' in query.upper(), \
            "Aggregation with filters must use WHERE clause at database level"
        
        # Property 2: Filter column should be in query
        assert filter_column in query, \
            f"Filter column '{filter_column}' should be in WHERE clause"
        
        # Property 3: Filter value should be in parameters (parameterized query)
        assert filter_value in params, \
            f"Filter value '{filter_value}' should be in query parameters"
    
    @given(
        group_columns=st.lists(
            st.sampled_from(['status', 'user_id']),
            min_size=1,
            max_size=2,
            unique=True
        )
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_5_aggregation_with_group_by_uses_sql_group_by(self, group_columns):
        """
        Property 5: Aggregation with GROUP BY uses SQL GROUP BY clause.
        
        For any aggregate operation with grouping, the grouping should be performed
        at the database level using GROUP BY clause, not by fetching all rows and
        grouping in application code.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        mock_connection = Mock()
        cursor = Mock()
        
        # Mock grouped results
        mock_results = [
            {group_columns[0]: f'value_{i}', 'aggregate_value': i * 10}
            for i in range(3)
        ]
        cursor.fetchall.return_value = mock_results
        cursor.close = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        
        mock_connection.cursor.return_value = cursor
        
        repository = FIRRepository(mock_connection)
        
        # Act
        result = repository.aggregate(
            function=AggregateFunction.COUNT,
            column='*',
            group_by=group_columns
        )
        
        # Assert
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        
        # Property 1: Query should contain GROUP BY clause
        assert 'GROUP BY' in query.upper(), \
            "Aggregation with grouping must use GROUP BY clause at database level"
        
        # Property 2: All group columns should be in GROUP BY clause
        for col in group_columns:
            assert col in query, \
                f"Group column '{col}' should be in GROUP BY clause"
        
        # Property 3: Result should contain grouped data
        assert isinstance(result, list), \
            "Grouped aggregation should return a list"
        assert len(result) > 0, \
            "Grouped aggregation should return results"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'property_test'])
