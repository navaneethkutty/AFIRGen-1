"""
Query Optimizer Component for Database Query Analysis and Optimization.

This module provides tools to analyze MySQL query execution plans, suggest indexes,
and identify inefficient query patterns like SELECT *.

Requirements: 1.1, 1.4
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .logging import get_logger


logger = get_logger(__name__)


class QueryType(str, Enum):
    """Types of SQL queries."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UNKNOWN = "UNKNOWN"


@dataclass
class IndexSuggestion:
    """Represents a suggested index for query optimization."""
    table_name: str
    column_names: List[str]
    reason: str
    index_type: str = "BTREE"  # BTREE, HASH, FULLTEXT
    
    def __str__(self) -> str:
        cols = ", ".join(self.column_names)
        return f"CREATE INDEX idx_{self.table_name}_{'_'.join(self.column_names)} ON {self.table_name}({cols}) USING {self.index_type}"


@dataclass
class QueryPlan:
    """Represents the execution plan analysis for a query."""
    query: str
    execution_time_ms: float = 0.0
    rows_examined: int = 0
    rows_returned: int = 0
    uses_index: bool = False
    index_names: List[str] = None
    suggestions: List[str] = None
    full_table_scan: bool = False
    query_type: QueryType = QueryType.UNKNOWN
    tables_involved: List[str] = None
    
    def __post_init__(self):
        if self.index_names is None:
            self.index_names = []
        if self.suggestions is None:
            self.suggestions = []
        if self.tables_involved is None:
            self.tables_involved = []


class QueryOptimizer:
    """
    Analyzes database queries and provides optimization suggestions.
    
    Features:
    - Query execution plan analysis using EXPLAIN
    - Index suggestion based on query patterns
    - Detection of SELECT * queries
    - Identification of full table scans
    """
    
    def __init__(self):
        """Initialize the Query Optimizer."""
        self._select_star_pattern = re.compile(
            r'\bSELECT\s+\*\s+FROM\b',
            re.IGNORECASE
        )
        self._table_pattern = re.compile(
            r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\b',
            re.IGNORECASE
        )
        self._where_pattern = re.compile(
            r'\bWHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|\s+;|\s*$)',
            re.IGNORECASE | re.DOTALL
        )
        self._join_pattern = re.compile(
            r'\b(?:INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:[a-zA-Z_][a-zA-Z0-9_]*\s+)?ON\s+(.+?)(?:\s+(?:INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|JOIN|WHERE|ORDER|GROUP|LIMIT|;)|\s*$)',
            re.IGNORECASE | re.DOTALL
        )
    
    def analyze_query_plan(self, query: str, explain_result: List[Dict[str, Any]]) -> QueryPlan:
        """
        Analyze a query execution plan from EXPLAIN output.
        
        Args:
            query: The SQL query being analyzed
            explain_result: List of dictionaries from EXPLAIN query output
        
        Returns:
            QueryPlan object with analysis results
        
        Validates: Requirements 1.1
        """
        plan = QueryPlan(query=query)
        
        # Determine query type
        plan.query_type = self._get_query_type(query)
        
        # Extract tables involved
        plan.tables_involved = self._extract_tables(query)
        
        if not explain_result:
            plan.suggestions.append("Unable to analyze query - no EXPLAIN output")
            return plan
        
        # Analyze EXPLAIN output
        total_rows_examined = 0
        uses_any_index = False
        has_full_scan = False
        index_names = []
        
        for row in explain_result:
            # Extract rows examined
            rows = row.get('rows', 0) or 0
            total_rows_examined += rows
            
            # Check for index usage
            key = row.get('key')
            if key and key != 'NULL':
                uses_any_index = True
                index_names.append(key)
            
            # Check for full table scan
            select_type = row.get('type', '')
            if select_type in ('ALL', 'index'):
                has_full_scan = True
                table = row.get('table', 'unknown')
                plan.suggestions.append(
                    f"Full table scan detected on table '{table}' - consider adding an index"
                )
        
        plan.rows_examined = total_rows_examined
        plan.uses_index = uses_any_index
        plan.index_names = index_names
        plan.full_table_scan = has_full_scan
        
        # Add general suggestions
        if not uses_any_index and plan.query_type == QueryType.SELECT:
            plan.suggestions.append("Query does not use any indexes - performance may be poor")
        
        if total_rows_examined > 1000:
            plan.suggestions.append(
                f"High number of rows examined ({total_rows_examined}) - consider optimizing query or adding indexes"
            )
        
        return plan
    
    def suggest_indexes(self, query_plan: QueryPlan) -> List[IndexSuggestion]:
        """
        Suggest indexes based on query plan analysis.
        
        Args:
            query_plan: QueryPlan object from analyze_query_plan
        
        Returns:
            List of IndexSuggestion objects
        
        Validates: Requirements 1.1
        """
        suggestions = []
        query = query_plan.query
        
        # Only suggest indexes for SELECT queries with full table scans
        if query_plan.query_type != QueryType.SELECT:
            return suggestions
        
        if not query_plan.full_table_scan:
            return suggestions
        
        # Extract WHERE clause columns
        where_columns = self._extract_where_columns(query)
        if where_columns:
            for table, columns in where_columns.items():
                if columns:
                    suggestions.append(IndexSuggestion(
                        table_name=table,
                        column_names=columns,
                        reason=f"WHERE clause filtering on {', '.join(columns)}",
                        index_type="BTREE"
                    ))
        
        # Extract JOIN columns
        join_columns = self._extract_join_columns(query)
        if join_columns:
            for table, columns in join_columns.items():
                if columns:
                    suggestions.append(IndexSuggestion(
                        table_name=table,
                        column_names=columns,
                        reason=f"JOIN condition on {', '.join(columns)}",
                        index_type="BTREE"
                    ))
        
        # Extract ORDER BY columns
        order_columns = self._extract_order_by_columns(query)
        if order_columns:
            for table, columns in order_columns.items():
                if columns:
                    suggestions.append(IndexSuggestion(
                        table_name=table,
                        column_names=columns,
                        reason=f"ORDER BY clause on {', '.join(columns)}",
                        index_type="BTREE"
                    ))
        
        return suggestions
    
    def has_select_star(self, query: str) -> bool:
        """
        Check if a query uses SELECT *.
        
        Args:
            query: SQL query string
        
        Returns:
            True if query contains SELECT *, False otherwise
        
        Validates: Requirements 1.4
        """
        # Normalize whitespace
        normalized = ' '.join(query.split())
        return bool(self._select_star_pattern.search(normalized))
    
    def optimize_joins(self, query: str) -> str:
        """
        Suggest optimizations for JOIN queries.
        
        Args:
            query: SQL query string with JOINs
        
        Returns:
            Optimized query string (currently returns original with comments)
        
        Note: This is a placeholder for future join optimization logic.
        """
        # For now, just return the original query
        # Future: Could reorder joins, suggest STRAIGHT_JOIN, etc.
        return query
    
    def _get_query_type(self, query: str) -> QueryType:
        """Determine the type of SQL query."""
        normalized = query.strip().upper()
        if normalized.startswith('SELECT'):
            return QueryType.SELECT
        elif normalized.startswith('INSERT'):
            return QueryType.INSERT
        elif normalized.startswith('UPDATE'):
            return QueryType.UPDATE
        elif normalized.startswith('DELETE'):
            return QueryType.DELETE
        return QueryType.UNKNOWN
    
    def _extract_tables(self, query: str) -> List[str]:
        """Extract table names from query."""
        tables = []
        
        # Extract FROM clause tables
        from_matches = self._table_pattern.findall(query)
        tables.extend(from_matches)
        
        # Extract JOIN clause tables
        join_matches = self._join_pattern.findall(query)
        for match in join_matches:
            if isinstance(match, tuple):
                tables.append(match[0])
            else:
                tables.append(match)
        
        return list(set(tables))  # Remove duplicates
    
    def _extract_where_columns(self, query: str) -> Dict[str, List[str]]:
        """
        Extract columns used in WHERE clause.
        
        Returns:
            Dictionary mapping table names to column lists
        """
        result = {}
        
        where_match = self._where_pattern.search(query)
        if not where_match:
            return result
        
        where_clause = where_match.group(1)
        
        # Extract column references (table.column or just column)
        column_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b')
        matches = column_pattern.findall(where_clause)
        
        for table, column in matches:
            if table not in result:
                result[table] = []
            if column not in result[table]:
                result[table].append(column)
        
        # If no table-qualified columns found, try to infer from query
        if not result:
            tables = self._extract_tables(query)
            if tables:
                # Extract simple column names
                simple_column_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]')
                simple_matches = simple_column_pattern.findall(where_clause)
                if simple_matches:
                    # Assume first table for unqualified columns
                    result[tables[0]] = list(set(simple_matches))
        
        return result
    
    def _extract_join_columns(self, query: str) -> Dict[str, List[str]]:
        """
        Extract columns used in JOIN conditions.
        
        Returns:
            Dictionary mapping table names to column lists
        """
        result = {}
        
        join_matches = self._join_pattern.findall(query)
        for match in join_matches:
            if not isinstance(match, tuple) or len(match) < 2:
                continue
            
            table = match[0]
            condition = match[1]
            
            # Extract column references
            column_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b')
            columns = column_pattern.findall(condition)
            
            for tbl, col in columns:
                if tbl == table:
                    if table not in result:
                        result[table] = []
                    if col not in result[table]:
                        result[table].append(col)
        
        return result
    
    def _extract_order_by_columns(self, query: str) -> Dict[str, List[str]]:
        """
        Extract columns used in ORDER BY clause.
        
        Returns:
            Dictionary mapping table names to column lists
        """
        result = {}
        
        order_pattern = re.compile(
            r'\bORDER\s+BY\s+(.+?)(?:\s+LIMIT|\s+;|\s*$)',
            re.IGNORECASE | re.DOTALL
        )
        
        order_match = order_pattern.search(query)
        if not order_match:
            return result
        
        order_clause = order_match.group(1)
        
        # Extract column references
        column_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b')
        matches = column_pattern.findall(order_clause)
        
        for table, column in matches:
            if table not in result:
                result[table] = []
            if column not in result[table]:
                result[table].append(column)
        
        # Handle unqualified columns
        if not result:
            tables = self._extract_tables(query)
            if tables:
                simple_column_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
                simple_matches = simple_column_pattern.findall(order_clause)
                # Filter out SQL keywords
                keywords = {'ASC', 'DESC', 'BY', 'ORDER'}
                columns = [col for col in simple_matches if col.upper() not in keywords]
                if columns:
                    result[tables[0]] = columns
        
        return result


# Convenience function for quick analysis
def analyze_query(query: str, cursor) -> QueryPlan:
    """
    Convenience function to analyze a query using EXPLAIN.
    
    Args:
        query: SQL query to analyze
        cursor: Database cursor for executing EXPLAIN
    
    Returns:
        QueryPlan with analysis results
    """
    optimizer = QueryOptimizer()
    
    try:
        # Execute EXPLAIN
        explain_query = f"EXPLAIN {query}"
        cursor.execute(explain_query)
        explain_result = cursor.fetchall()
        
        # Analyze the plan
        plan = optimizer.analyze_query_plan(query, explain_result)
        
        return plan
    except Exception as e:
        logger.error("Failed to analyze query", error=str(e), query=query[:100])
        plan = QueryPlan(query=query)
        plan.suggestions.append(f"Analysis failed: {str(e)}")
        return plan
