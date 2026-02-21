"""
FIR Repository implementation with optimized database access.

This module provides the FIR-specific repository implementation
demonstrating the use of the base repository patterns.

Requirements: 1.3, 1.4, 1.5, 1.6
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from .base_repository import BaseRepository, JoinClause, JoinType


@dataclass
class FIR:
    """FIR entity model."""
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    violation_text: Optional[str] = None
    priority: Optional[int] = None
    assigned_to: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FIR':
        """Create FIR from dictionary."""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            status=data['status'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            description=data.get('description'),
            violation_text=data.get('violation_text'),
            priority=data.get('priority'),
            assigned_to=data.get('assigned_to')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FIR to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'description': self.description,
            'violation_text': self.violation_text,
            'priority': self.priority,
            'assigned_to': self.assigned_to
        }


class FIRRepository(BaseRepository[FIR]):
    """
    Repository for FIR entities with optimized database access.
    
    Demonstrates:
    - Selective column retrieval
    - Cursor-based pagination
    - Optimized joins with index hints
    - Database-level aggregation
    - Cache invalidation on data modifications
    """
    
    # Define all columns explicitly (no SELECT *)
    ALL_COLUMNS = [
        'id',
        'user_id',
        'status',
        'created_at',
        'updated_at',
        'description',
        'violation_text',
        'priority',
        'assigned_to'
    ]
    
    def __init__(self, connection, cache_manager=None):
        """
        Initialize FIR repository.
        
        Args:
            connection: Database connection
            cache_manager: Optional CacheManager for cache invalidation
        """
        super().__init__(connection, cache_manager)
    
    @property
    def table_name(self) -> str:
        """Return the FIR table name."""
        return "firs"
    
    @property
    def primary_key(self) -> str:
        """Return the primary key column."""
        return "id"
    
    def _row_to_entity(self, row: Dict[str, Any]) -> FIR:
        """Convert database row to FIR entity."""
        return FIR.from_dict(row)
    
    def _get_cache_namespace(self) -> str:
        """Get cache namespace for FIR entities."""
        return "fir"
    
    def _get_invalidation_patterns(self, entity_id: Any) -> List[str]:
        """
        Get cache key patterns to invalidate for a FIR entity.
        
        Invalidates:
        - List caches (user-specific lists, status-based lists)
        - Query caches (search results)
        - Stats caches (dashboard statistics, counts by status)
        
        Args:
            entity_id: FIR ID
        
        Returns:
            List of cache key patterns to invalidate
        """
        return [
            "list:*",      # All list caches
            "query:*",     # All query caches
            "stats:*",     # All statistics caches
            "count:*",     # All count caches
            "user:*"       # User-specific caches
        ]
    
    def _build_column_list(self, fields: Optional[List[str]] = None) -> str:
        """
        Build column list for SELECT clause.
        
        Always uses explicit column names, never SELECT *.
        
        Validates: Requirements 1.4
        """
        if fields:
            # Validate requested fields
            invalid_fields = set(fields) - set(self.ALL_COLUMNS)
            if invalid_fields:
                raise ValueError(f"Invalid fields requested: {invalid_fields}")
            return ", ".join(fields)
        else:
            # Return all columns explicitly
            return ", ".join(self.ALL_COLUMNS)
    
    def find_by_id(
        self,
        entity_id: Any,
        fields: Optional[List[str]] = None
    ) -> Optional[FIR]:
        """
        Find FIR by ID with caching support.
        
        Implements cache-aside pattern:
        1. Check cache first
        2. If cache miss, query database
        3. Store result in cache
        
        Args:
            entity_id: FIR ID
            fields: Optional list of specific fields to retrieve
        
        Returns:
            FIR entity or None if not found
        
        Validates: Requirements 2.2, 2.3 (cache hit/miss, cache-aside pattern)
        """
        if self.cache_manager and fields is None:
            # Only use cache for full entity retrieval
            cache_key = self.generate_key("record", str(entity_id))
            
            def fetch_from_db():
                return super(FIRRepository, self).find_by_id(entity_id, fields)
            
            try:
                result = self.cache_manager.get_or_fetch(
                    key=cache_key,
                    fetch_fn=fetch_from_db,
                    ttl=3600,  # 1 hour TTL for FIR records
                    namespace=self._get_cache_namespace()
                )
                
                # Convert dict back to FIR if needed
                if result and isinstance(result, dict):
                    return FIR.from_dict(result)
                return result
            except Exception:
                # Fallback to database on cache failure
                return super(FIRRepository, self).find_by_id(entity_id, fields)
        else:
            # No cache for partial field retrieval
            return super(FIRRepository, self).find_by_id(entity_id, fields)
    
    def generate_key(self, entity_type: str, identifier: str) -> str:
        """Generate cache key for FIR entities."""
        return f"{entity_type}:{identifier}"
    
    def find_by_user(
        self,
        user_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[FIR]:
        """
        Find FIRs by user ID with selective column retrieval and caching.
        
        Args:
            user_id: User ID to filter by
            fields: Optional list of specific fields to retrieve
            limit: Maximum number of results
        
        Returns:
            List of FIR entities
        
        Validates: Requirements 1.4 (selective column retrieval), 2.2, 2.3 (caching)
        """
        if self.cache_manager and fields is None:
            # Cache user FIR lists
            cache_key = self.generate_key("user", f"{user_id}:limit:{limit}")
            
            def fetch_from_db():
                columns = self._build_column_list(fields)
                query = f"""
                    SELECT {columns}
                    FROM {self.table_name}
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                
                cursor = self.connection.cursor(dictionary=True)
                try:
                    cursor.execute(query, (user_id, limit))
                    rows = cursor.fetchall()
                    return [self._row_to_entity(row).to_dict() for row in rows]
                finally:
                    cursor.close()
            
            try:
                cached_result = self.cache_manager.get_or_fetch(
                    key=cache_key,
                    fetch_fn=fetch_from_db,
                    ttl=1800,  # 30 minutes TTL for user lists
                    namespace=self._get_cache_namespace()
                )
                
                # Convert dicts back to FIR entities
                return [FIR.from_dict(item) if isinstance(item, dict) else item 
                        for item in cached_result]
            except Exception:
                # Fallback to direct database query
                pass
        
        # Direct database query (no cache or cache failure)
        columns = self._build_column_list(fields)
        query = f"""
            SELECT {columns}
            FROM {self.table_name}
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, (user_id, limit))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            cursor.close()
    
    def find_by_status_paginated(
        self,
        status: str,
        cursor: Optional[str] = None,
        limit: int = 20,
        fields: Optional[List[str]] = None
    ):
        """
        Find FIRs by status with cursor-based pagination.
        
        Args:
            status: Status to filter by
            cursor: Optional cursor from previous page
            limit: Number of items per page
            fields: Optional list of specific fields to retrieve
        
        Returns:
            PaginatedResult with FIR entities
        
        Validates: Requirements 1.5 (cursor-based pagination)
        """
        return self.find_paginated(
            cursor=cursor,
            limit=limit,
            fields=fields,
            filters={'status': status},
            order_by='created_at DESC',
            sort_column='created_at'
        )
    
    def find_with_violations(
        self,
        fir_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Find FIR with related violations using optimized join.
        
        Demonstrates join with index hint for better performance.
        
        Args:
            fir_id: FIR ID to retrieve
            fields: Optional list of specific FIR fields to retrieve
        
        Returns:
            Dictionary with FIR and violation data
        
        Validates: Requirements 1.3 (optimized joins with index hints)
        """
        # Build column list with table prefixes
        fir_columns = self._build_column_list(fields)
        if fields:
            fir_columns = ", ".join([f"f.{col}" for col in fields])
        else:
            fir_columns = ", ".join([f"f.{col}" for col in self.ALL_COLUMNS])
        
        # Define join with index hint
        joins = [
            JoinClause(
                join_type=JoinType.LEFT,
                table="violations",
                alias="v",
                on_condition="f.id = v.fir_id",
                index_hint="idx_violations_fir_id"  # Assumes this index exists
            )
        ]
        
        query = f"""
            SELECT {fir_columns}, v.id as violation_id, v.violation_type, v.severity
            FROM {self.table_name} f
            {joins[0].to_sql()}
            WHERE f.id = %s
        """
        
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, (fir_id,))
            rows = cursor.fetchall()
            
            if not rows:
                return None
            
            # Combine FIR with violations
            fir_data = {k: v for k, v in rows[0].items() if not k.startswith('violation_')}
            violations = []
            
            for row in rows:
                if row.get('violation_id'):
                    violations.append({
                        'id': row['violation_id'],
                        'violation_type': row['violation_type'],
                        'severity': row['severity']
                    })
            
            return {
                'fir': self._row_to_entity(fir_data),
                'violations': violations
            }
        finally:
            cursor.close()
    
    def count_by_status(self) -> List[Dict[str, Any]]:
        """
        Count FIRs grouped by status using database-level aggregation with caching.
        
        Returns:
            List of dictionaries with status and count
        
        Validates: Requirements 1.6 (database-level aggregation), 2.2, 2.3 (caching)
        """
        if self.cache_manager:
            cache_key = "stats:count_by_status"
            
            def fetch_from_db():
                from .base_repository import AggregateFunction
                return self.aggregate(
                    function=AggregateFunction.COUNT,
                    column='*',
                    group_by=['status']
                )
            
            try:
                return self.cache_manager.get_or_fetch(
                    key=cache_key,
                    fetch_fn=fetch_from_db,
                    ttl=300,  # 5 minutes TTL for statistics
                    namespace=self._get_cache_namespace()
                )
            except Exception:
                # Fallback to database on cache failure
                pass
        
        # Direct database query
        from .base_repository import AggregateFunction
        return self.aggregate(
            function=AggregateFunction.COUNT,
            column='*',
            group_by=['status']
        )
    
    def avg_priority_by_user(self, user_id: str) -> float:
        """
        Calculate average priority for user's FIRs using database-level aggregation.
        
        Args:
            user_id: User ID to filter by
        
        Returns:
            Average priority value
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        return self.avg(
            column='priority',
            filters={'user_id': user_id}
        )
    
    def get_latest_fir_date(self, user_id: Optional[str] = None) -> Optional[datetime]:
        """
        Get the most recent FIR creation date using database-level MAX.
        
        Args:
            user_id: Optional user ID to filter by
        
        Returns:
            Most recent creation date
        
        Validates: Requirements 1.6 (database-level aggregation)
        """
        filters = {'user_id': user_id} if user_id else None
        return self.max(column='created_at', filters=filters)
    
    def bulk_insert(self, firs: List[FIR]) -> List[str]:
        """
        Insert multiple FIRs efficiently using bulk insert.
        
        Args:
            firs: List of FIR entities to insert
        
        Returns:
            List of inserted FIR IDs
        """
        if not firs:
            return []
        
        # Build bulk insert query with explicit columns
        columns = self.ALL_COLUMNS
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"""
            INSERT INTO {self.table_name} ({", ".join(columns)})
            VALUES ({placeholders})
        """
        
        cursor = self.connection.cursor()
        try:
            # Prepare values
            values_list = []
            for fir in firs:
                values = [
                    fir.id,
                    fir.user_id,
                    fir.status,
                    fir.created_at,
                    fir.updated_at,
                    fir.description,
                    fir.violation_text,
                    fir.priority,
                    fir.assigned_to
                ]
                values_list.append(values)
            
            # Execute bulk insert
            cursor.executemany(query, values_list)
            self.connection.commit()
            
            # Invalidate cache for all inserted FIRs
            for fir in firs:
                self._invalidate_cache_for_entity(fir.id)
            
            return [fir.id for fir in firs]
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def create(self, fir: FIR) -> FIR:
        """
        Create a new FIR with cache invalidation.
        
        Args:
            fir: FIR entity to create
        
        Returns:
            Created FIR entity
        
        Validates: Requirements 2.4 (cache invalidation on create)
        """
        columns = self.ALL_COLUMNS
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"""
            INSERT INTO {self.table_name} ({", ".join(columns)})
            VALUES ({placeholders})
        """
        
        cursor = self.connection.cursor()
        try:
            values = [
                fir.id,
                fir.user_id,
                fir.status,
                fir.created_at,
                fir.updated_at,
                fir.description,
                fir.violation_text,
                fir.priority,
                fir.assigned_to
            ]
            
            cursor.execute(query, values)
            self.connection.commit()
            
            # Invalidate cache after successful create
            self._invalidate_cache_for_entity(fir.id)
            
            # Also cache the newly created FIR
            if self.cache_manager:
                try:
                    cache_key = self.generate_key("record", str(fir.id))
                    self.cache_manager.set(
                        key=cache_key,
                        value=fir.to_dict(),
                        ttl=3600,
                        namespace=self._get_cache_namespace()
                    )
                except Exception:
                    # Cache failure shouldn't fail the create operation
                    pass
            
            return fir
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()
