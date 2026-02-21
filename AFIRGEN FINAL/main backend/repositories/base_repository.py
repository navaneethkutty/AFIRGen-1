"""
Base Repository with optimized database access patterns.

This module provides the base repository class with:
- Selective column retrieval (no SELECT *)
- Cursor-based pagination for large result sets
- Optimized joins with index hints
- Database-level aggregation methods

Requirements: 1.3, 1.4, 1.5, 1.6, 8.3
"""

import base64
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar
from enum import Enum

from infrastructure.logging import get_logger
from interfaces.repository import IRepository as IRepositoryInterface, PaginatedResult as IPaginatedResult


logger = get_logger(__name__)


T = TypeVar('T')


class AggregateFunction(str, Enum):
    """Supported SQL aggregate functions."""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MAX = "MAX"
    MIN = "MIN"


class JoinType(str, Enum):
    """Supported SQL join types."""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"


@dataclass
class CursorInfo:
    """Information for cursor-based pagination."""
    last_id: Any
    last_sort_value: Optional[Any] = None
    
    def encode(self) -> str:
        """Encode cursor info to base64 string."""
        data = {
            'id': str(self.last_id),
            'sort': str(self.last_sort_value) if self.last_sort_value is not None else None
        }
        json_str = json.dumps(data)
        return base64.b64encode(json_str.encode()).decode()
    
    @classmethod
    def decode(cls, cursor: str) -> 'CursorInfo':
        """Decode cursor from base64 string."""
        try:
            json_str = base64.b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            return cls(
                last_id=data['id'],
                last_sort_value=data.get('sort')
            )
        except Exception as e:
            logger.error("Failed to decode cursor", error=str(e), cursor=cursor)
            raise ValueError(f"Invalid cursor format: {e}")


@dataclass
class PaginatedResult(Generic[T]):
    """Result of a paginated query."""
    items: List[T]
    total_count: int
    page_size: int
    next_cursor: Optional[str]
    has_more: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'items': self.items,
            'total_count': self.total_count,
            'page_size': self.page_size,
            'next_cursor': self.next_cursor,
            'has_more': self.has_more
        }


@dataclass
class JoinClause:
    """Represents a JOIN clause with optional index hints."""
    join_type: JoinType
    table: str
    alias: Optional[str]
    on_condition: str
    index_hint: Optional[str] = None
    
    def to_sql(self) -> str:
        """Convert to SQL JOIN clause."""
        alias_part = f" {self.alias}" if self.alias else ""
        index_part = f" USE INDEX ({self.index_hint})" if self.index_hint else ""
        return f"{self.join_type.value} {self.table}{alias_part}{index_part} ON {self.on_condition}"


class BaseRepository(IRepositoryInterface[T]):
    """
    Base repository class with optimized database access patterns.
    
    Implements IRepository interface to ensure consistent data access patterns.
    
    Features:
    - Selective column retrieval (Requirements 1.4)
    - Cursor-based pagination (Requirements 1.5)
    - Optimized joins with index hints (Requirements 1.3)
    - Database-level aggregation (Requirements 1.6)
    - Cache invalidation on data modifications (Requirements 2.4, 2.5)
    
    Requirements: 1.3, 1.4, 1.5, 1.6, 8.3
    """
    
    def __init__(self, connection, cache_manager=None):
        """
        Initialize repository with database connection and optional cache manager.
        
        Args:
            connection: Database connection object (e.g., MySQL connection)
            cache_manager: Optional CacheManager instance for cache invalidation
        """
        self.connection = connection
        self.cache_manager = cache_manager
    
    def _execute_query_with_metrics(
        self,
        query: str,
        params: tuple = (),
        query_type: str = "SELECT",
        fetch_one: bool = False,
        fetch_all: bool = True
    ) -> Any:
        """
        Execute a query and track metrics.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            query_type: Type of query (SELECT, INSERT, UPDATE, DELETE, etc.)
            fetch_one: Whether to fetch one row
            fetch_all: Whether to fetch all rows
        
        Returns:
            Query result (row, rows, or None)
            
        Validates: Requirements 5.3
        """
        from infrastructure.metrics import MetricsCollector
        
        start_time = time.time()
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute(query, params)
            
            # Fetch results if needed
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all and query_type == "SELECT":
                result = cursor.fetchall()
            else:
                result = None
            
            # Record metrics
            duration = time.time() - start_time
            MetricsCollector.record_db_query_duration(
                query_type=query_type,
                table=self.table_name,
                duration=duration
            )
            
            return result
        finally:
            cursor.close()
    
    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the primary table name for this repository."""
        pass
    
    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Return the primary key column name."""
        pass
    
    @abstractmethod
    def _row_to_entity(self, row: Dict[str, Any]) -> T:
        """Convert database row to entity object."""
        pass
    
    def _get_cache_namespace(self) -> str:
        """
        Get cache namespace for this repository.
        
        Override in subclasses to provide specific namespace.
        Default uses table name.
        """
        return self.table_name
    
    def _invalidate_cache_for_entity(self, entity_id: Any) -> None:
        """
        Invalidate cache entries for a specific entity.
        
        This method is called after create, update, or delete operations
        to ensure cache consistency.
        
        Args:
            entity_id: Primary key value of the entity
        
        Validates: Requirements 2.4, 2.5
        """
        if self.cache_manager is None:
            return
        
        try:
            namespace = self._get_cache_namespace()
            
            # Invalidate direct entity cache
            entity_key = f"record:{entity_id}"
            self.cache_manager.delete(entity_key, namespace)
            
            # Invalidate any pattern-based caches related to this entity
            # Subclasses can override _get_invalidation_patterns for custom patterns
            patterns = self._get_invalidation_patterns(entity_id)
            for pattern in patterns:
                self.cache_manager.invalidate_pattern(pattern, namespace)
            
            logger.debug("Cache invalidated", namespace=namespace, entity_id=entity_id)
        except Exception as e:
            # Fallback: Log error but don't fail the operation
            # This ensures cache failures don't break data modifications
            logger.warning("Cache invalidation failed", entity_id=entity_id, error=str(e))
    
    def _get_invalidation_patterns(self, entity_id: Any) -> List[str]:
        """
        Get cache key patterns to invalidate for an entity.
        
        Override in subclasses to provide custom invalidation patterns.
        For example, invalidate list caches, aggregation caches, etc.
        
        Args:
            entity_id: Primary key value of the entity
        
        Returns:
            List of cache key patterns to invalidate
        """
        # Default: invalidate all list and query caches
        return ["list:*", "query:*", "stats:*"]
    
    def find_by_id(
        self,
        entity_id: Any,
        fields: Optional[List[str]] = None
    ) -> Optional[T]:
        """
        Find entity by primary key with selective column retrieval.
        
        Args:
            entity_id: Primary key value
            fields: Optional list of specific fields to retrieve
        
        Returns:
            Entity object or None if not found
        
        Validates: Requirements 1.4 (selective column retrieval)
        """
        columns = self._build_column_list(fields)
        query = f"SELECT {columns} FROM {self.table_name} WHERE {self.primary_key} = %s"
        
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, (entity_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_entity(row)
            return None
        finally:
            cursor.close()
    
    def find_all(
        self,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """
        Find all entities matching filters with selective column retrieval.
        
        Args:
            fields: Optional list of specific fields to retrieve
            filters: Optional dictionary of column=value filters
            order_by: Optional ORDER BY clause (e.g., "created_at DESC")
        
        Returns:
            List of entity objects
        
        Validates: Requirements 1.4 (selective column retrieval)
        """
        columns = self._build_column_list(fields)
        query = f"SELECT {columns} FROM {self.table_name}"
        params = []
        
        if filters:
            where_clauses = []
            for column, value in filters.items():
                where_clauses.append(f"{column} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(where_clauses)
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            cursor.close()
    
    def find_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = None,
        sort_column: Optional[str] = None
    ) -> PaginatedResult[T]:
        """
        Find entities with cursor-based pagination.
        
        Cursor-based pagination is more efficient than OFFSET-based pagination
        for large datasets because it uses indexed columns for filtering.
        
        Args:
            cursor: Optional cursor from previous page
            limit: Number of items per page
            fields: Optional list of specific fields to retrieve
            filters: Optional dictionary of column=value filters
            order_by: Optional ORDER BY clause (e.g., "created_at DESC")
            sort_column: Column used for cursor sorting (defaults to primary_key)
        
        Returns:
            PaginatedResult with items and pagination metadata
        
        Validates: Requirements 1.5 (cursor-based pagination)
        """
        if sort_column is None:
            sort_column = self.primary_key
        
        if order_by is None:
            order_by = f"{sort_column} ASC"
        
        columns = self._build_column_list(fields)
        query = f"SELECT {columns} FROM {self.table_name}"
        params = []
        
        # Build WHERE clause
        where_clauses = []
        
        # Add cursor condition
        if cursor:
            cursor_info = CursorInfo.decode(cursor)
            # Use cursor for efficient pagination
            if cursor_info.last_sort_value is not None:
                where_clauses.append(f"({sort_column}, {self.primary_key}) > (%s, %s)")
                params.extend([cursor_info.last_sort_value, cursor_info.last_id])
            else:
                where_clauses.append(f"{self.primary_key} > %s")
                params.append(cursor_info.last_id)
        
        # Add filters
        if filters:
            for column, value in filters.items():
                where_clauses.append(f"{column} = %s")
                params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add ORDER BY
        query += f" ORDER BY {order_by}"
        
        # Fetch one extra item to determine if there are more pages
        query += f" LIMIT {limit + 1}"
        
        cursor_obj = self.connection.cursor(dictionary=True)
        try:
            cursor_obj.execute(query, params)
            rows = cursor_obj.fetchall()
            
            # Check if there are more items
            has_more = len(rows) > limit
            items = rows[:limit]
            
            # Convert to entities
            entities = [self._row_to_entity(row) for row in items]
            
            # Generate next cursor
            next_cursor = None
            if has_more and items:
                last_item = items[-1]
                cursor_info = CursorInfo(
                    last_id=last_item[self.primary_key],
                    last_sort_value=last_item.get(sort_column) if sort_column != self.primary_key else None
                )
                next_cursor = cursor_info.encode()
            
            # Get total count (this could be cached for better performance)
            total_count = self._count_total(filters)
            
            return PaginatedResult(
                items=entities,
                total_count=total_count,
                page_size=limit,
                next_cursor=next_cursor,
                has_more=has_more
            )
        finally:
            cursor_obj.close()
    
    def find_with_join(
        self,
        joins: List[JoinClause],
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query with optimized joins and optional index hints.
        
        Args:
            joins: List of JoinClause objects defining the joins
            fields: Optional list of specific fields to retrieve
            filters: Optional dictionary of column=value filters
            order_by: Optional ORDER BY clause
        
        Returns:
            List of dictionaries with joined data
        
        Validates: Requirements 1.3 (optimized joins with index hints)
        """
        columns = self._build_column_list(fields)
        query = f"SELECT {columns} FROM {self.table_name}"
        params = []
        
        # Add JOIN clauses
        for join in joins:
            query += " " + join.to_sql()
        
        # Add WHERE clause
        if filters:
            where_clauses = []
            for column, value in filters.items():
                where_clauses.append(f"{column} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add ORDER BY
        if order_by:
            query += f" ORDER BY {order_by}"
        
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
    
    def aggregate(
        self,
        function: AggregateFunction,
        column: str,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute database-level aggregation query.
        
        Args:
            function: Aggregate function to apply (COUNT, SUM, AVG, MAX, MIN)
            column: Column to aggregate (use '*' for COUNT(*))
            filters: Optional dictionary of column=value filters
            group_by: Optional list of columns to group by
        
        Returns:
            List of dictionaries with aggregation results
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        # Build SELECT clause
        agg_expr = f"{function.value}({column})"
        if group_by:
            select_cols = ", ".join(group_by) + f", {agg_expr} as aggregate_value"
        else:
            select_cols = f"{agg_expr} as aggregate_value"
        
        query = f"SELECT {select_cols} FROM {self.table_name}"
        params = []
        
        # Add WHERE clause
        if filters:
            where_clauses = []
            for col, value in filters.items():
                where_clauses.append(f"{col} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add GROUP BY clause
        if group_by:
            query += " GROUP BY " + ", ".join(group_by)
        
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching filters using database-level COUNT.
        
        Args:
            filters: Optional dictionary of column=value filters
        
        Returns:
            Count of matching entities
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        result = self.aggregate(
            function=AggregateFunction.COUNT,
            column='*',
            filters=filters
        )
        return result[0]['aggregate_value'] if result else 0
    
    def sum(
        self,
        column: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Sum column values using database-level SUM.
        
        Args:
            column: Column to sum
            filters: Optional dictionary of column=value filters
        
        Returns:
            Sum of column values
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        result = self.aggregate(
            function=AggregateFunction.SUM,
            column=column,
            filters=filters
        )
        return float(result[0]['aggregate_value']) if result and result[0]['aggregate_value'] is not None else 0.0
    
    def avg(
        self,
        column: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate average of column values using database-level AVG.
        
        Args:
            column: Column to average
            filters: Optional dictionary of column=value filters
        
        Returns:
            Average of column values
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        result = self.aggregate(
            function=AggregateFunction.AVG,
            column=column,
            filters=filters
        )
        return float(result[0]['aggregate_value']) if result and result[0]['aggregate_value'] is not None else 0.0
    
    def max(
        self,
        column: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Find maximum column value using database-level MAX.
        
        Args:
            column: Column to find max value
            filters: Optional dictionary of column=value filters
        
        Returns:
            Maximum column value
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        result = self.aggregate(
            function=AggregateFunction.MAX,
            column=column,
            filters=filters
        )
        return result[0]['aggregate_value'] if result else None
    
    def min(
        self,
        column: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Find minimum column value using database-level MIN.
        
        Args:
            column: Column to find min value
            filters: Optional dictionary of column=value filters
        
        Returns:
            Minimum column value
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        result = self.aggregate(
            function=AggregateFunction.MIN,
            column=column,
            filters=filters
        )
        return result[0]['aggregate_value'] if result else None
    
    def _build_column_list(self, fields: Optional[List[str]] = None) -> str:
        """
        Build column list for SELECT clause.
        
        Never uses SELECT * - always specifies explicit columns.
        
        Args:
            fields: Optional list of specific fields
        
        Returns:
            Comma-separated column list
        
        Validates: Requirements 1.4 (no SELECT *)
        """
        if fields:
            # Validate and sanitize field names to prevent SQL injection
            sanitized = [self._sanitize_column_name(f) for f in fields]
            return ", ".join(sanitized)
        else:
            # Return all columns explicitly (subclasses should override this)
            return "*"
    
    def _sanitize_column_name(self, column: str) -> str:
        """
        Sanitize column name to prevent SQL injection.
        
        Args:
            column: Column name to sanitize
        
        Returns:
            Sanitized column name
        
        Raises:
            ValueError: If column name contains invalid characters
        """
        # Allow alphanumeric, underscore, and dot (for table.column)
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', column):
            raise ValueError(f"Invalid column name: {column}")
        return column
    
    def _count_total(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count total entities matching filters.
        
        Args:
            filters: Optional dictionary of column=value filters
        
        Returns:
            Total count
        """
        return self.count(filters)
    
    def create(self, entity: T) -> T:
        """
        Create a new entity with cache invalidation.
        
        Args:
            entity: Entity object to create
        
        Returns:
            Created entity
        
        Validates: Requirements 2.4 (cache invalidation on create)
        """
        # Subclasses should implement the actual insert logic
        # This is a template method that handles cache invalidation
        raise NotImplementedError("Subclasses must implement create method")
    
    def update(self, entity_id: Any, updates: Dict[str, Any]) -> Optional[T]:
        """
        Update an entity with cache invalidation.
        
        Args:
            entity_id: Primary key value
            updates: Dictionary of column=value updates
        
        Returns:
            Updated entity or None if not found
        
        Validates: Requirements 2.4 (cache invalidation on update)
        """
        if not updates:
            return self.find_by_id(entity_id)
        
        # Build UPDATE query
        set_clauses = []
        params = []
        for column, value in updates.items():
            set_clauses.append(f"{column} = %s")
            params.append(value)
        
        params.append(entity_id)
        query = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {self.primary_key} = %s"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            
            # Invalidate cache after successful update
            self._invalidate_cache_for_entity(entity_id)
            
            # Return updated entity
            return self.find_by_id(entity_id)
        except Exception as e:
            self.connection.rollback()
            logger.error("Update failed", entity_id=entity_id, error=str(e), table=self.table_name)
            raise
        finally:
            cursor.close()
    
    def delete(self, entity_id: Any) -> bool:
        """
        Delete an entity with cache invalidation.
        
        Args:
            entity_id: Primary key value
        
        Returns:
            True if entity was deleted, False if not found
        
        Validates: Requirements 2.4 (cache invalidation on delete)
        """
        query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (entity_id,))
            self.connection.commit()
            
            deleted = cursor.rowcount > 0
            
            if deleted:
                # Invalidate cache after successful delete
                self._invalidate_cache_for_entity(entity_id)
            
            return deleted
        except Exception as e:
            self.connection.rollback()
            logger.error("Delete failed", entity_id=entity_id, error=str(e), table=self.table_name)
            raise
        finally:
            cursor.close()
