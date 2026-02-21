# Query Optimizer Component

## Overview

The Query Optimizer component provides tools to analyze MySQL query execution plans, suggest indexes, and identify inefficient query patterns.

## Features

- **Query Execution Plan Analysis**: Uses MySQL EXPLAIN to analyze query performance
- **Index Suggestions**: Automatically suggests indexes based on query patterns
- **SELECT * Detection**: Identifies queries using SELECT * instead of specific columns
- **Full Table Scan Detection**: Flags queries that perform full table scans
- **Join Analysis**: Analyzes JOIN conditions and suggests appropriate indexes

## Requirements

Validates:
- Requirement 1.1: Query plan analysis identifies missing indexes
- Requirement 1.4: No SELECT * in generated queries

## Usage

### Basic Query Analysis

```python
from infrastructure.query_optimizer import QueryOptimizer, analyze_query

# Create optimizer instance
optimizer = QueryOptimizer()

# Check for SELECT *
query = "SELECT * FROM fir_records WHERE status = 'pending'"
if optimizer.has_select_star(query):
    print("Warning: Query uses SELECT *")

# Analyze query plan with database cursor
with db._cursor() as cursor:
    plan = analyze_query(query, cursor)
    
    print(f"Uses index: {plan.uses_index}")
    print(f"Rows examined: {plan.rows_examined}")
    print(f"Full table scan: {plan.full_table_scan}")
    
    for suggestion in plan.suggestions:
        print(f"Suggestion: {suggestion}")
```

### Index Suggestions

```python
from infrastructure.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer()

# Analyze a query
query = "SELECT * FROM fir_records WHERE status = 'pending' ORDER BY created_at DESC"
explain_result = [
    {
        'table': 'fir_records',
        'type': 'ALL',
        'key': None,
        'rows': 10000
    }
]

plan = optimizer.analyze_query_plan(query, explain_result)
suggestions = optimizer.suggest_indexes(plan)

for suggestion in suggestions:
    print(f"Table: {suggestion.table_name}")
    print(f"Columns: {', '.join(suggestion.column_names)}")
    print(f"Reason: {suggestion.reason}")
    print(f"SQL: {str(suggestion)}")
    print()
```

### Integration with Database Layer

```python
from infrastructure.query_optimizer import QueryOptimizer

class OptimizedDB(DB):
    def __init__(self):
        super().__init__()
        self.optimizer = QueryOptimizer()
    
    def _execute_with_analysis(self, query: str, params=None):
        """Execute query with performance analysis."""
        # Check for SELECT *
        if self.optimizer.has_select_star(query):
            logger.warning(f"Query uses SELECT *: {query[:100]}")
        
        # Execute with EXPLAIN for analysis
        with self._cursor() as cursor:
            # Get execution plan
            explain_query = f"EXPLAIN {query}"
            cursor.execute(explain_query)
            explain_result = cursor.fetchall()
            
            # Analyze plan
            plan = self.optimizer.analyze_query_plan(query, explain_result)
            
            # Log warnings
            if plan.full_table_scan:
                logger.warning(f"Full table scan detected: {query[:100]}")
            
            if not plan.uses_index and plan.rows_examined > 100:
                logger.warning(f"No index used, {plan.rows_examined} rows examined")
                
                # Get index suggestions
                suggestions = self.optimizer.suggest_indexes(plan)
                for suggestion in suggestions:
                    logger.info(f"Index suggestion: {str(suggestion)}")
            
            # Execute actual query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            return cursor.fetchall()
```

## API Reference

### QueryOptimizer

#### Methods

- `analyze_query_plan(query: str, explain_result: List[Dict]) -> QueryPlan`
  - Analyzes query execution plan from EXPLAIN output
  - Returns QueryPlan object with analysis results

- `suggest_indexes(query_plan: QueryPlan) -> List[IndexSuggestion]`
  - Suggests indexes based on query plan analysis
  - Returns list of IndexSuggestion objects

- `has_select_star(query: str) -> bool`
  - Checks if query uses SELECT *
  - Returns True if SELECT * is found

- `optimize_joins(query: str) -> str`
  - Placeholder for future join optimization
  - Currently returns original query

### QueryPlan

Dataclass representing query execution plan analysis:

- `query: str` - The SQL query
- `execution_time_ms: float` - Execution time in milliseconds
- `rows_examined: int` - Number of rows examined
- `rows_returned: int` - Number of rows returned
- `uses_index: bool` - Whether query uses an index
- `index_names: List[str]` - Names of indexes used
- `suggestions: List[str]` - Optimization suggestions
- `full_table_scan: bool` - Whether full table scan occurred
- `query_type: QueryType` - Type of query (SELECT, INSERT, etc.)
- `tables_involved: List[str]` - Tables referenced in query

### IndexSuggestion

Dataclass representing an index suggestion:

- `table_name: str` - Table to create index on
- `column_names: List[str]` - Columns to include in index
- `reason: str` - Reason for suggestion
- `index_type: str` - Type of index (BTREE, HASH, FULLTEXT)

Convert to SQL with `str(suggestion)`:
```python
suggestion = IndexSuggestion(
    table_name="fir_records",
    column_names=["status", "created_at"],
    reason="WHERE and ORDER BY optimization"
)
print(str(suggestion))
# Output: CREATE INDEX idx_fir_records_status_created_at ON fir_records(status, created_at) USING BTREE
```

## Examples

### Example 1: Detecting Inefficient Queries

```python
# Query with full table scan
query = "SELECT * FROM fir_records WHERE complaint_text LIKE '%theft%'"

with db._cursor() as cursor:
    plan = analyze_query(query, cursor)
    
    if plan.full_table_scan:
        print("⚠️  Full table scan detected!")
        print(f"Rows examined: {plan.rows_examined}")
        
        suggestions = optimizer.suggest_indexes(plan)
        if suggestions:
            print("\nSuggested indexes:")
            for s in suggestions:
                print(f"  - {str(s)}")
```

### Example 2: Monitoring Query Performance

```python
def monitor_query_performance(query: str, cursor):
    """Monitor and log query performance metrics."""
    optimizer = QueryOptimizer()
    
    # Check for SELECT *
    if optimizer.has_select_star(query):
        logger.warning("Query uses SELECT * - consider specifying columns")
    
    # Analyze execution plan
    cursor.execute(f"EXPLAIN {query}")
    explain_result = cursor.fetchall()
    
    plan = optimizer.analyze_query_plan(query, explain_result)
    
    # Log metrics
    logger.info(f"Query analysis:", extra={
        "uses_index": plan.uses_index,
        "rows_examined": plan.rows_examined,
        "full_table_scan": plan.full_table_scan,
        "tables": plan.tables_involved
    })
    
    # Log suggestions
    for suggestion in plan.suggestions:
        logger.info(f"Optimization suggestion: {suggestion}")
    
    return plan
```

### Example 3: Automated Index Creation

```python
def auto_suggest_indexes(db_cursor):
    """Analyze slow queries and suggest indexes."""
    optimizer = QueryOptimizer()
    
    # Get slow queries from MySQL slow query log
    slow_queries = get_slow_queries()  # Your implementation
    
    all_suggestions = []
    
    for query in slow_queries:
        cursor.execute(f"EXPLAIN {query}")
        explain_result = cursor.fetchall()
        
        plan = optimizer.analyze_query_plan(query, explain_result)
        suggestions = optimizer.suggest_indexes(plan)
        
        all_suggestions.extend(suggestions)
    
    # Deduplicate suggestions
    unique_suggestions = {}
    for s in all_suggestions:
        key = (s.table_name, tuple(s.column_names))
        if key not in unique_suggestions:
            unique_suggestions[key] = s
    
    # Print SQL for creating indexes
    print("-- Suggested indexes based on slow query analysis")
    for suggestion in unique_suggestions.values():
        print(f"{str(suggestion)};")
```

## Testing

Run the test suite:

```bash
pytest test_query_optimizer.py -v
```

All 27 tests should pass, covering:
- SELECT * detection
- Query plan analysis
- Index suggestions
- Query type detection
- Table and column extraction
- Edge cases and error handling

## Performance Considerations

- Query analysis adds minimal overhead (single EXPLAIN query)
- Use caching for repeated query analysis
- Consider analyzing only in development/staging environments
- For production, analyze queries offline from slow query logs

## Future Enhancements

- [ ] Automatic query rewriting to remove SELECT *
- [ ] JOIN order optimization
- [ ] Subquery optimization suggestions
- [ ] Query cost estimation
- [ ] Integration with MySQL performance schema
- [ ] Automated index creation based on workload analysis
