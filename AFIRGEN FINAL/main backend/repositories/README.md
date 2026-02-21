# Repository Pattern Implementation

This directory contains the optimized repository pattern implementation for database access in the AFIRGen backend system.

## Overview

The repository pattern provides a clean abstraction layer for database operations with built-in optimizations:

- **Selective Column Retrieval**: Never uses `SELECT *`, always specifies explicit columns
- **Cursor-Based Pagination**: Efficient pagination for large result sets using indexed columns
- **Optimized Joins**: Support for JOIN operations with optional index hints
- **Database-Level Aggregation**: COUNT, SUM, AVG, MAX, MIN operations at the database level

## Requirements Validated

- **Requirement 1.3**: Optimized joins with index hints
- **Requirement 1.4**: Selective column retrieval (no SELECT *)
- **Requirement 1.5**: Cursor-based pagination for large result sets
- **Requirement 1.6**: Database-level aggregation functions

## Architecture

```
repositories/
├── __init__.py              # Package exports
├── base_repository.py       # Base repository with optimization patterns
├── fir_repository.py        # FIR-specific repository implementation
└── README.md               # This file
```

## Base Repository

The `BaseRepository` class provides the foundation for all repository implementations:

### Key Features

1. **Selective Column Retrieval**
   ```python
   # Retrieve specific fields only
   fir = repository.find_by_id('fir_123', fields=['id', 'status', 'created_at'])
   
   # Retrieve all fields (explicitly listed, not SELECT *)
   fir = repository.find_by_id('fir_123')
   ```

2. **Cursor-Based Pagination**
   ```python
   # First page
   result = repository.find_paginated(limit=20)
   
   # Next page using cursor
   result = repository.find_paginated(cursor=result.next_cursor, limit=20)
   
   # Result includes:
   # - items: List of entities
   # - total_count: Total number of items
   # - page_size: Items per page
   # - next_cursor: Cursor for next page
   # - has_more: Boolean indicating more pages
   ```

3. **Optimized Joins with Index Hints**
   ```python
   joins = [
       JoinClause(
           join_type=JoinType.LEFT,
           table="violations",
           alias="v",
           on_condition="f.id = v.fir_id",
           index_hint="idx_violations_fir_id"  # Optional index hint
       )
   ]
   
   results = repository.find_with_join(
       joins=joins,
       fields=['f.id', 'f.status', 'v.violation_type'],
       filters={'f.status': 'pending'}
   )
   ```

4. **Database-Level Aggregation**
   ```python
   # Count
   total = repository.count(filters={'status': 'pending'})
   
   # Sum
   total_priority = repository.sum('priority', filters={'user_id': 'user_1'})
   
   # Average
   avg_priority = repository.avg('priority')
   
   # Max/Min
   latest_date = repository.max('created_at')
   earliest_date = repository.min('created_at')
   
   # Group by
   stats = repository.aggregate(
       function=AggregateFunction.COUNT,
       column='*',
       group_by=['status']
   )
   ```

## FIR Repository

The `FIRRepository` demonstrates a concrete implementation of the base repository:

### Example Usage

```python
from repositories import FIRRepository

# Initialize with database connection
repository = FIRRepository(connection)

# Find by ID with specific fields
fir = repository.find_by_id('fir_123', fields=['id', 'status', 'description'])

# Find by user with pagination
firs = repository.find_by_user('user_1', limit=10)

# Paginated query by status
result = repository.find_by_status_paginated('pending', limit=20)

# Find with related violations (optimized join)
data = repository.find_with_violations('fir_123')
# Returns: {'fir': FIR, 'violations': [Violation, ...]}

# Aggregation queries
status_counts = repository.count_by_status()
avg_priority = repository.avg_priority_by_user('user_1')
latest_fir = repository.get_latest_fir_date()

# Bulk insert
firs = [FIR(...), FIR(...), FIR(...)]
ids = repository.bulk_insert(firs)
```

## Creating Custom Repositories

To create a new repository, extend `BaseRepository`:

```python
from repositories.base_repository import BaseRepository
from typing import Dict, Any

class MyEntityRepository(BaseRepository[MyEntity]):
    # Define all columns explicitly
    ALL_COLUMNS = ['id', 'name', 'created_at', 'updated_at']
    
    @property
    def table_name(self) -> str:
        return "my_entities"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def _row_to_entity(self, row: Dict[str, Any]) -> MyEntity:
        return MyEntity.from_dict(row)
    
    def _build_column_list(self, fields: Optional[List[str]] = None) -> str:
        if fields:
            # Validate requested fields
            invalid_fields = set(fields) - set(self.ALL_COLUMNS)
            if invalid_fields:
                raise ValueError(f"Invalid fields requested: {invalid_fields}")
            return ", ".join(fields)
        else:
            # Return all columns explicitly
            return ", ".join(self.ALL_COLUMNS)
    
    # Add custom query methods as needed
    def find_by_name(self, name: str) -> List[MyEntity]:
        return self.find_all(filters={'name': name})
```

## Performance Benefits

### 1. Selective Column Retrieval
- **Reduces network transfer**: Only requested columns are transferred
- **Reduces memory usage**: Smaller result sets in memory
- **Improves query performance**: Database can optimize for specific columns

### 2. Cursor-Based Pagination
- **Consistent performance**: O(1) complexity regardless of page number
- **No offset overhead**: Uses indexed columns for filtering
- **Scalable**: Works efficiently with millions of records

**Comparison with OFFSET-based pagination:**
```sql
-- OFFSET-based (slow for large offsets)
SELECT * FROM firs ORDER BY created_at LIMIT 20 OFFSET 10000;
-- Database must scan 10,020 rows

-- Cursor-based (fast)
SELECT * FROM firs WHERE created_at > '2024-01-15' ORDER BY created_at LIMIT 20;
-- Database uses index to jump directly to position
```

### 3. Index Hints
- **Query optimization**: Guides database to use specific indexes
- **Predictable performance**: Ensures consistent query plans
- **Avoids full table scans**: Forces index usage for joins

### 4. Database-Level Aggregation
- **Reduces data transfer**: Only aggregated results are returned
- **Leverages database optimization**: Database engines are optimized for aggregation
- **Reduces application memory**: No need to load all data into memory

## Testing

The repository pattern includes comprehensive unit tests:

```bash
# Run all repository tests
python -m pytest test_repository_pattern.py -v

# Run specific test class
python -m pytest test_repository_pattern.py::TestFIRRepository -v

# Run specific test
python -m pytest test_repository_pattern.py::TestFIRRepository::test_cursor_based_pagination -v
```

## Best Practices

1. **Always specify columns**: Never use `SELECT *` in production code
2. **Use pagination for lists**: Always paginate list endpoints to prevent memory issues
3. **Add index hints for critical queries**: Use index hints for frequently executed joins
4. **Aggregate at database level**: Use COUNT, SUM, AVG instead of loading all data
5. **Validate field names**: Always validate user-provided field names to prevent SQL injection
6. **Use transactions**: Wrap multiple operations in transactions for consistency

## Security Considerations

1. **SQL Injection Prevention**:
   - All column names are validated against allowed lists
   - Parameterized queries are used for all values
   - Field names are sanitized using regex validation

2. **Input Validation**:
   - Field names must match `^[a-zA-Z_][a-zA-Z0-9_.]*$` pattern
   - Invalid fields are rejected with clear error messages

3. **Access Control**:
   - Repository layer focuses on data access
   - Authorization should be handled in service layer
   - Never expose repository methods directly to API endpoints

## Future Enhancements

Potential improvements for future iterations:

1. **Query Result Caching**: Integrate with Redis cache layer
2. **Read Replicas**: Support for read replica routing
3. **Query Logging**: Log slow queries for optimization
4. **Connection Pooling**: Integrate with connection pool management
5. **Soft Deletes**: Add support for soft delete patterns
6. **Audit Logging**: Track all data modifications
7. **Batch Operations**: Optimize bulk updates and deletes

## References

- Design Document: `.kiro/specs/backend-optimization/design.md`
- Requirements Document: `.kiro/specs/backend-optimization/requirements.md`
- Task List: `.kiro/specs/backend-optimization/tasks.md`
