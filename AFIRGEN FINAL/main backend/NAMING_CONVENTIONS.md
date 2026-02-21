# Python Naming Conventions (PEP 8)

This document outlines the naming conventions followed in the AFIRGen backend codebase, based on PEP 8 standards.

## General Principles

1. **Consistency**: Use consistent naming patterns throughout the codebase
2. **Clarity**: Names should be descriptive and self-documenting
3. **PEP 8 Compliance**: Follow Python Enhancement Proposal 8 guidelines
4. **American English**: Use American English spelling (e.g., `sanitize` not `sanitise`)

## Naming Patterns

### Functions and Variables

- **Style**: `snake_case` (lowercase with underscores)
- **Examples**:
  - ✅ `get_user_data()`
  - ✅ `calculate_total_amount()`
  - ✅ `user_id`
  - ✅ `connection_timeout`
  - ❌ `getUserData()` (camelCase)
  - ❌ `CalculateTotalAmount()` (PascalCase)

### Classes

- **Style**: `PascalCase` (capitalize first letter of each word)
- **Examples**:
  - ✅ `DatabasePool`
  - ✅ `CacheManager`
  - ✅ `FIRRepository`
  - ❌ `database_pool` (snake_case)
  - ❌ `cacheManager` (camelCase)

### Constants

- **Style**: `UPPER_CASE_WITH_UNDERSCORES`
- **Examples**:
  - ✅ `MAX_RETRIES`
  - ✅ `DEFAULT_TIMEOUT`
  - ✅ `API_VERSION`
  - ❌ `maxRetries` (camelCase)
  - ❌ `Max_Retries` (mixed case)

### Private Methods and Attributes

- **Style**: Prefix with single underscore `_`
- **Examples**:
  - ✅ `_internal_method()`
  - ✅ `_private_attribute`
  - ✅ `_cursor()`
  - ❌ `__double_underscore()` (reserved for name mangling)

### Module Names

- **Style**: `lowercase` or `lowercase_with_underscores`
- **Examples**:
  - ✅ `cache_manager.py`
  - ✅ `error_response.py`
  - ✅ `utils.py`
  - ❌ `CacheManager.py` (PascalCase)
  - ❌ `error-response.py` (hyphens)

## Abbreviation Guidelines

### Consistent Abbreviations

Use consistent abbreviations throughout the codebase:

| Full Term | Abbreviation | Usage |
|-----------|--------------|-------|
| database | `db` | Use `db` for short variable names, `database` for clarity in function names |
| connection | `conn` | Use `conn` for short variable names, `connection` for clarity |
| configuration | `config` | Consistently use `config` |
| repository | `repo` | Use `repository` in class names, `repo` in variable names |
| identifier | `id` | Consistently use `id` |
| maximum | `max` | Consistently use `max` |
| minimum | `min` | Consistently use `min` |

### Examples

**Database-related naming**:
- ✅ `db_pool` - database pool variable
- ✅ `get_database_connection()` - function name (clarity)
- ✅ `DatabasePool` - class name (full word)
- ✅ `conn` - connection variable
- ✅ `create_connection()` - function name (clarity)

**Configuration-related naming**:
- ✅ `config` - configuration variable
- ✅ `RedisConfig` - class name
- ✅ `load_config()` - function name

## Domain-Specific Conventions

### FIR (First Information Report)

- **Acronym**: Always use uppercase `FIR` in class names
- **Examples**:
  - ✅ `FIRRepository`
  - ✅ `FIRService`
  - ✅ `fir_id` (variable)
  - ✅ `fir_number` (variable)
  - ❌ `FirRepository` (mixed case)
  - ❌ `firRepository` (camelCase)

### HTTP/API-related

- **Style**: Use descriptive names for endpoints and handlers
- **Examples**:
  - ✅ `process_endpoint()`
  - ✅ `validate_step()`
  - ✅ `get_session_status()`
  - ✅ `authenticate_fir()`

### Async Functions

- **Style**: Same as regular functions (snake_case)
- **Prefix**: Use `async def` keyword, no special naming
- **Examples**:
  - ✅ `async def fetch_data()`
  - ✅ `async def process_request()`
  - ❌ `async def asyncFetchData()` (don't add async prefix)

## Type Hints

- **Style**: Use proper type hints throughout
- **Examples**:
  - ✅ `def get_user(user_id: str) -> Optional[Dict[str, Any]]:`
  - ✅ `connection: Connection`
  - ✅ `timeout: float = 30.0`

## Boolean Variables and Functions

- **Prefix**: Use `is_`, `has_`, `can_`, `should_` for boolean variables/functions
- **Examples**:
  - ✅ `is_valid`
  - ✅ `has_permission`
  - ✅ `can_retry`
  - ✅ `should_compress`
  - ❌ `valid` (ambiguous)
  - ❌ `permission` (ambiguous)

## Collection Variables

- **Plural**: Use plural names for collections
- **Examples**:
  - ✅ `users = []`
  - ✅ `fir_records = []`
  - ✅ `error_messages = []`
  - ❌ `user_list = []` (redundant suffix)
  - ❌ `fir_array = []` (redundant suffix)

## Exception Classes

- **Suffix**: End with `Error` or `Exception`
- **Examples**:
  - ✅ `CircuitBreakerError`
  - ✅ `ValidationException`
  - ✅ `DatabaseConnectionError`
  - ❌ `CircuitBreakerFailure` (inconsistent)

## Test Functions

- **Prefix**: Start with `test_`
- **Style**: Descriptive snake_case
- **Examples**:
  - ✅ `test_cache_hit_returns_cached_value()`
  - ✅ `test_retry_with_exponential_backoff()`
  - ✅ `test_property_pagination_metadata()`

## Property-Based Test Functions

- **Prefix**: Start with `test_property_`
- **Include**: Property number from design document
- **Examples**:
  - ✅ `test_property_11_cache_key_namespacing()`
  - ✅ `test_property_25_retry_with_exponential_backoff()`

## Middleware Classes

- **Suffix**: End with `Middleware`
- **Examples**:
  - ✅ `CompressionMiddleware`
  - ✅ `CorrelationIdMiddleware`
  - ✅ `MetricsMiddleware`

## Service Classes

- **Suffix**: End with `Service`
- **Examples**:
  - ✅ `FIRService`
  - ✅ `ModelServerService`
  - ✅ `SessionService`

## Repository Classes

- **Suffix**: End with `Repository`
- **Examples**:
  - ✅ `FIRRepository`
  - ✅ `BaseRepository`
  - ✅ `CacheRepository`

## Manager Classes

- **Suffix**: End with `Manager`
- **Examples**:
  - ✅ `CacheManager`
  - ✅ `BackgroundTaskManager`
  - ✅ `SessionManager`

## Handler Classes

- **Suffix**: End with `Handler`
- **Examples**:
  - ✅ `RetryHandler`
  - ✅ `PaginationHandler`
  - ✅ `ErrorHandler`

## Spelling Conventions

### American vs British English

Always use American English spelling:

| ❌ British | ✅ American |
|-----------|------------|
| sanitise | sanitize |
| optimise | optimize |
| initialise | initialize |
| finalise | finalize |
| colour | color |
| behaviour | behavior |

## Documentation

- **Docstrings**: Use triple quotes `"""`
- **Style**: Follow Google or NumPy docstring format
- **Example**:
```python
def calculate_total(items: List[Dict], tax_rate: float = 0.1) -> float:
    """
    Calculate total amount including tax.
    
    Args:
        items: List of item dictionaries with 'price' key
        tax_rate: Tax rate as decimal (default: 0.1 for 10%)
    
    Returns:
        Total amount including tax
    
    Raises:
        ValueError: If items list is empty or tax_rate is negative
    """
    pass
```

## Refactoring Checklist

When refactoring code for naming conventions:

1. ✅ Rename functions to snake_case
2. ✅ Rename classes to PascalCase
3. ✅ Rename constants to UPPER_CASE
4. ✅ Use consistent abbreviations (db, conn, config)
5. ✅ Use American English spelling
6. ✅ Add type hints where missing
7. ✅ Update docstrings to match new names
8. ✅ Update tests to use new names
9. ✅ Run linters (pylint, mypy) to verify
10. ✅ Update documentation

## Tools

Use these tools to enforce naming conventions:

- **pylint**: Checks PEP 8 compliance
- **mypy**: Type checking
- **black**: Auto-formatting
- **flake8**: Style guide enforcement

## References

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
