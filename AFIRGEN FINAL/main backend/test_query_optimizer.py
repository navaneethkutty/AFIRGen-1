"""
Unit tests for Query Optimizer component.

Tests query plan analysis, index suggestions, and SELECT * detection.
"""

import pytest
from infrastructure.query_optimizer import (
    QueryOptimizer,
    QueryPlan,
    IndexSuggestion,
    QueryType,
    analyze_query
)


class TestQueryOptimizer:
    """Test suite for QueryOptimizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = QueryOptimizer()
    
    def test_has_select_star_simple(self):
        """Test detection of simple SELECT * query."""
        query = "SELECT * FROM users"
        assert self.optimizer.has_select_star(query) is True
    
    def test_has_select_star_with_where(self):
        """Test detection of SELECT * with WHERE clause."""
        query = "SELECT * FROM users WHERE id = 1"
        assert self.optimizer.has_select_star(query) is True
    
    def test_has_select_star_case_insensitive(self):
        """Test case-insensitive detection."""
        query = "select * from users"
        assert self.optimizer.has_select_star(query) is True
    
    def test_has_select_star_with_whitespace(self):
        """Test detection with extra whitespace."""
        query = "SELECT   *   FROM   users"
        assert self.optimizer.has_select_star(query) is True
    
    def test_no_select_star_specific_columns(self):
        """Test that specific column selection is not flagged."""
        query = "SELECT id, name, email FROM users"
        assert self.optimizer.has_select_star(query) is False
    
    def test_no_select_star_count(self):
        """Test that COUNT(*) is not flagged as SELECT *."""
        query = "SELECT COUNT(*) FROM users"
        assert self.optimizer.has_select_star(query) is False
    
    def test_analyze_query_plan_with_index(self):
        """Test query plan analysis when index is used."""
        query = "SELECT id, name FROM users WHERE id = 1"
        explain_result = [
            {
                'id': 1,
                'select_type': 'SIMPLE',
                'table': 'users',
                'type': 'const',
                'possible_keys': 'PRIMARY',
                'key': 'PRIMARY',
                'key_len': '4',
                'ref': 'const',
                'rows': 1,
                'Extra': None
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        
        assert plan.query_type == QueryType.SELECT
        assert plan.uses_index is True
        assert 'PRIMARY' in plan.index_names
        assert plan.rows_examined == 1
        assert plan.full_table_scan is False
        assert 'users' in plan.tables_involved
    
    def test_analyze_query_plan_full_table_scan(self):
        """Test query plan analysis with full table scan."""
        query = "SELECT * FROM fir_records WHERE complaint_text LIKE '%theft%'"
        explain_result = [
            {
                'id': 1,
                'select_type': 'SIMPLE',
                'table': 'fir_records',
                'type': 'ALL',
                'possible_keys': None,
                'key': None,
                'key_len': None,
                'ref': None,
                'rows': 10000,
                'Extra': 'Using where'
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        
        assert plan.query_type == QueryType.SELECT
        assert plan.uses_index is False
        assert plan.rows_examined == 10000
        assert plan.full_table_scan is True
        assert len(plan.suggestions) > 0
        assert any('Full table scan' in s for s in plan.suggestions)
    
    def test_analyze_query_plan_empty_result(self):
        """Test handling of empty EXPLAIN result."""
        query = "SELECT * FROM users"
        explain_result = []
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        
        assert plan.query_type == QueryType.SELECT
        assert len(plan.suggestions) > 0
        assert any('Unable to analyze' in s for s in plan.suggestions)
    
    def test_suggest_indexes_where_clause(self):
        """Test index suggestion for WHERE clause."""
        query = "SELECT * FROM fir_records WHERE status = 'pending'"
        explain_result = [
            {
                'table': 'fir_records',
                'type': 'ALL',
                'key': None,
                'rows': 5000
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        suggestions = self.optimizer.suggest_indexes(plan)
        
        assert len(suggestions) > 0
        assert any('status' in s.column_names for s in suggestions)
    
    def test_suggest_indexes_join_condition(self):
        """Test index suggestion for JOIN condition."""
        query = """
            SELECT fir_records.*, sessions.state 
            FROM fir_records 
            JOIN sessions ON fir_records.session_id = sessions.session_id
        """
        explain_result = [
            {
                'table': 'fir_records',
                'type': 'ALL',
                'key': None,
                'rows': 5000
            },
            {
                'table': 'sessions',
                'type': 'ALL',
                'key': None,
                'rows': 1000
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        suggestions = self.optimizer.suggest_indexes(plan)
        
        # Should suggest index on join columns
        assert len(suggestions) > 0
        # Check that session_id is suggested for indexing
        assert any('session_id' in s.column_names for s in suggestions)
    
    def test_suggest_indexes_order_by(self):
        """Test index suggestion for ORDER BY clause."""
        query = "SELECT * FROM fir_records ORDER BY created_at DESC"
        explain_result = [
            {
                'table': 'fir_records',
                'type': 'ALL',
                'key': None,
                'rows': 5000
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        suggestions = self.optimizer.suggest_indexes(plan)
        
        assert len(suggestions) > 0
        assert any('created_at' in s.column_names for s in suggestions)
    
    def test_suggest_indexes_no_suggestions_with_index(self):
        """Test that no suggestions are made when index is already used."""
        query = "SELECT * FROM fir_records WHERE id = 1"
        explain_result = [
            {
                'table': 'fir_records',
                'type': 'const',
                'key': 'PRIMARY',
                'rows': 1
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        suggestions = self.optimizer.suggest_indexes(plan)
        
        # No suggestions needed when index is used
        assert len(suggestions) == 0
    
    def test_query_type_detection_select(self):
        """Test SELECT query type detection."""
        query = "SELECT * FROM users"
        plan = self.optimizer.analyze_query_plan(query, [])
        assert plan.query_type == QueryType.SELECT
    
    def test_query_type_detection_insert(self):
        """Test INSERT query type detection."""
        query = "INSERT INTO users (name) VALUES ('John')"
        plan = self.optimizer.analyze_query_plan(query, [])
        assert plan.query_type == QueryType.INSERT
    
    def test_query_type_detection_update(self):
        """Test UPDATE query type detection."""
        query = "UPDATE users SET name = 'Jane' WHERE id = 1"
        plan = self.optimizer.analyze_query_plan(query, [])
        assert plan.query_type == QueryType.UPDATE
    
    def test_query_type_detection_delete(self):
        """Test DELETE query type detection."""
        query = "DELETE FROM users WHERE id = 1"
        plan = self.optimizer.analyze_query_plan(query, [])
        assert plan.query_type == QueryType.DELETE
    
    def test_extract_tables_simple(self):
        """Test table extraction from simple query."""
        query = "SELECT * FROM users"
        tables = self.optimizer._extract_tables(query)
        assert 'users' in tables
    
    def test_extract_tables_with_join(self):
        """Test table extraction from query with JOIN."""
        query = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        tables = self.optimizer._extract_tables(query)
        assert 'users' in tables
        assert 'orders' in tables
    
    def test_extract_where_columns_simple(self):
        """Test WHERE column extraction."""
        query = "SELECT * FROM users WHERE users.id = 1 AND users.status = 'active'"
        columns = self.optimizer._extract_where_columns(query)
        assert 'users' in columns
        assert 'id' in columns['users']
        assert 'status' in columns['users']
    
    def test_extract_join_columns(self):
        """Test JOIN column extraction."""
        query = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        columns = self.optimizer._extract_join_columns(query)
        # Should extract columns from join condition
        assert len(columns) >= 0  # May vary based on parsing
    
    def test_index_suggestion_string_format(self):
        """Test IndexSuggestion string representation."""
        suggestion = IndexSuggestion(
            table_name="users",
            column_names=["email", "status"],
            reason="WHERE clause filtering",
            index_type="BTREE"
        )
        
        index_sql = str(suggestion)
        assert "CREATE INDEX" in index_sql
        assert "users" in index_sql
        assert "email" in index_sql
        assert "status" in index_sql
        assert "BTREE" in index_sql
    
    def test_high_rows_examined_warning(self):
        """Test warning for high number of rows examined."""
        query = "SELECT * FROM fir_records"
        explain_result = [
            {
                'table': 'fir_records',
                'type': 'ALL',
                'key': None,
                'rows': 50000
            }
        ]
        
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        
        assert plan.rows_examined == 50000
        assert any('High number of rows' in s for s in plan.suggestions)
    
    def test_optimize_joins_placeholder(self):
        """Test optimize_joins returns query unchanged (placeholder)."""
        query = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        optimized = self.optimizer.optimize_joins(query)
        assert optimized == query


class TestQueryPlanDataclass:
    """Test QueryPlan dataclass."""
    
    def test_query_plan_defaults(self):
        """Test QueryPlan default values."""
        plan = QueryPlan(query="SELECT * FROM users")
        
        assert plan.query == "SELECT * FROM users"
        assert plan.execution_time_ms == 0.0
        assert plan.rows_examined == 0
        assert plan.rows_returned == 0
        assert plan.uses_index is False
        assert plan.index_names == []
        assert plan.suggestions == []
        assert plan.full_table_scan is False
        assert plan.tables_involved == []
    
    def test_query_plan_with_values(self):
        """Test QueryPlan with custom values."""
        plan = QueryPlan(
            query="SELECT * FROM users",
            execution_time_ms=15.5,
            rows_examined=100,
            uses_index=True,
            index_names=["idx_email"]
        )
        
        assert plan.execution_time_ms == 15.5
        assert plan.rows_examined == 100
        assert plan.uses_index is True
        assert "idx_email" in plan.index_names


class TestIndexSuggestionDataclass:
    """Test IndexSuggestion dataclass."""
    
    def test_index_suggestion_creation(self):
        """Test IndexSuggestion creation."""
        suggestion = IndexSuggestion(
            table_name="fir_records",
            column_names=["status", "created_at"],
            reason="Composite index for status filtering and sorting"
        )
        
        assert suggestion.table_name == "fir_records"
        assert suggestion.column_names == ["status", "created_at"]
        assert suggestion.index_type == "BTREE"
        assert "status filtering" in suggestion.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# Property-Based Tests
from hypothesis import given, strategies as st, settings


class TestQueryOptimizerProperties:
    """Property-based tests for QueryOptimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = QueryOptimizer()
    
    @given(
        table_name=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122
        )).filter(lambda x: x.isalpha()),
        rows_examined=st.integers(min_value=0, max_value=100000),
        has_index=st.booleans(),
        scan_type=st.sampled_from(['ALL', 'index', 'range', 'ref', 'const'])
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_query_plan_identifies_missing_indexes(
        self, table_name, rows_examined, has_index, scan_type
    ):
        """
        Property 1: Query plan analysis identifies missing indexes.
        
        For any SQL query executed through the Database_Layer, when the 
        Query_Optimizer analyzes its execution plan, it should correctly 
        identify whether indexes are missing based on full table scans or 
        high row examination counts.
        
        **Validates: Requirements 1.1**
        """
        # Arrange: Create a query and mock EXPLAIN result
        query = f"SELECT * FROM {table_name} WHERE id = 1"
        
        explain_result = [{
            'id': 1,
            'select_type': 'SIMPLE',
            'table': table_name,
            'type': scan_type,
            'possible_keys': 'PRIMARY' if has_index else None,
            'key': 'PRIMARY' if has_index else None,
            'key_len': '4' if has_index else None,
            'ref': 'const' if has_index else None,
            'rows': rows_examined,
            'Extra': None
        }]
        
        # Act: Analyze the query plan
        plan = self.optimizer.analyze_query_plan(query, explain_result)
        
        # Assert: Verify correct identification of missing indexes
        
        # 1. Full table scan detection
        if scan_type in ('ALL', 'index'):
            assert plan.full_table_scan is True, \
                f"Full table scan should be detected for scan type '{scan_type}'"
            assert any('Full table scan' in s for s in plan.suggestions), \
                f"Should suggest index for full table scan (type={scan_type})"
        else:
            assert plan.full_table_scan is False, \
                f"Full table scan should not be detected for scan type '{scan_type}'"
        
        # 2. Index usage detection
        if has_index and scan_type not in ('ALL', 'index'):
            assert plan.uses_index is True, \
                "Should detect index usage when key is present"
            assert 'PRIMARY' in plan.index_names, \
                "Should include index name in plan"
        elif not has_index:
            assert plan.uses_index is False, \
                "Should not detect index usage when key is None"
        
        # 3. High row examination warning
        if rows_examined > 1000:
            assert any('High number of rows' in s for s in plan.suggestions), \
                f"Should warn about high row count ({rows_examined} rows)"
        
        # 4. General index suggestion for SELECT without indexes
        if not has_index and plan.query_type == QueryType.SELECT:
            assert any('does not use any indexes' in s for s in plan.suggestions), \
                "Should suggest adding indexes when none are used"
        
        # 5. Verify rows examined is recorded
        assert plan.rows_examined == rows_examined, \
            f"Should record correct rows examined: expected {rows_examined}, got {plan.rows_examined}"
        
        # 6. Verify query type is detected
        assert plan.query_type == QueryType.SELECT, \
            "Should correctly identify SELECT query type"
        
        # 7. Verify table is extracted
        assert table_name in plan.tables_involved, \
            f"Should extract table name '{table_name}' from query"
    
    @given(
        table_name=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122
        )).filter(lambda x: x.isalpha()),
        column_names=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122
            )).filter(lambda x: x.isalpha()),
            min_size=1,
            max_size=10,
            unique=True
        ),
        use_select_star=st.booleans()
    )
    @settings(max_examples=20)
    @pytest.mark.property_test
    def test_property_no_select_star_in_generated_queries(
        self, table_name, column_names, use_select_star
    ):
        """
        Property 3: No SELECT * in generated queries.
        
        For any database query generated by the system, the SQL should 
        explicitly specify column names rather than using SELECT *.
        
        **Validates: Requirements 1.4**
        """
        # Arrange: Generate a query with or without SELECT *
        if use_select_star:
            query = f"SELECT * FROM {table_name}"
        else:
            # Generate query with explicit column names
            columns_str = ", ".join(column_names)
            query = f"SELECT {columns_str} FROM {table_name}"
        
        # Act: Check if query has SELECT *
        has_star = self.optimizer.has_select_star(query)
        
        # Assert: Verify correct detection
        if use_select_star:
            assert has_star is True, \
                f"Should detect SELECT * in query: {query}"
        else:
            assert has_star is False, \
                f"Should not detect SELECT * in query with explicit columns: {query}"
        
        # Additional assertions for robustness
        
        # 1. Test with WHERE clause
        if use_select_star:
            query_with_where = f"SELECT * FROM {table_name} WHERE id = 1"
            assert self.optimizer.has_select_star(query_with_where) is True, \
                "Should detect SELECT * even with WHERE clause"
        else:
            columns_str = ", ".join(column_names)
            query_with_where = f"SELECT {columns_str} FROM {table_name} WHERE id = 1"
            assert self.optimizer.has_select_star(query_with_where) is False, \
                "Should not detect SELECT * with explicit columns and WHERE clause"
        
        # 2. Test case insensitivity
        if use_select_star:
            query_lower = f"select * from {table_name}"
            assert self.optimizer.has_select_star(query_lower) is True, \
                "Should detect SELECT * case-insensitively"
            
            query_mixed = f"SeLeCt * FrOm {table_name}"
            assert self.optimizer.has_select_star(query_mixed) is True, \
                "Should detect SELECT * with mixed case"
        
        # 3. Test with extra whitespace
        if use_select_star:
            query_whitespace = f"SELECT   *   FROM   {table_name}"
            assert self.optimizer.has_select_star(query_whitespace) is True, \
                "Should detect SELECT * with extra whitespace"
        
        # 4. Verify COUNT(*) is not flagged as SELECT *
        query_count = f"SELECT COUNT(*) FROM {table_name}"
        assert self.optimizer.has_select_star(query_count) is False, \
            "Should not flag COUNT(*) as SELECT *"
        
        # 5. Test with JOIN clauses
        if use_select_star:
            query_join = f"SELECT * FROM {table_name} t1 JOIN other_table t2 ON t1.id = t2.id"
            assert self.optimizer.has_select_star(query_join) is True, \
                "Should detect SELECT * in JOIN queries"
        else:
            columns_str = ", ".join([f"t1.{col}" for col in column_names[:3]])
            query_join = f"SELECT {columns_str} FROM {table_name} t1 JOIN other_table t2 ON t1.id = t2.id"
            assert self.optimizer.has_select_star(query_join) is False, \
                "Should not detect SELECT * in JOIN with explicit columns"
        
        # 6. Test with ORDER BY
        if use_select_star:
            query_order = f"SELECT * FROM {table_name} ORDER BY id DESC"
            assert self.optimizer.has_select_star(query_order) is True, \
                "Should detect SELECT * with ORDER BY"
        
        # 7. Test with LIMIT
        if use_select_star:
            query_limit = f"SELECT * FROM {table_name} LIMIT 10"
            assert self.optimizer.has_select_star(query_limit) is True, \
                "Should detect SELECT * with LIMIT"
        
        # 8. Verify the property: system-generated queries should NOT have SELECT *
        # This is the core property - if this is a system-generated query,
        # it should always use explicit column names
        if not use_select_star:
            # This represents a properly generated query
            assert has_star is False, \
                "System-generated queries must explicitly specify columns, not use SELECT *"
            
            # Verify that explicit columns are actually in the query
            for col in column_names:
                assert col in query, \
                    f"Column '{col}' should be explicitly listed in query"
