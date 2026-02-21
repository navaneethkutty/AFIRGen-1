# Interfaces Documentation

This directory contains abstract base classes (interfaces) that define clear contracts for the AFIRGen backend system. These interfaces establish consistent patterns for data access, caching, and external service integration.

## Overview

The interfaces module provides three main categories of abstractions:

1. **Repository Interfaces** - Data access layer contracts
2. **Cache Interfaces** - Caching layer contracts
3. **External Service Interfaces** - External service integration contracts

## Requirements

**Validates: Requirements 8.3** - Define clear interfaces for database, cache, and external service interactions

## Repository Interfaces

### IRepository[T]

Abstract base class for all repository implementations. Defines the contract for data access operations.

**Key Methods:**
- `find_by_id(entity_id, fields)` - Find entity by primary key
- `find_all(fields, filters, order_by)` - Find all entities matching filters
- `find_paginated(cursor, limit, ...)` - Cursor-based pagination
- `count(filters)` - Count entities
- `create(entity)` - Create new entity
- `update(entity_id, updates)` - Update entity
- `delete(entity_id)` - Delete entity
- `aggregate(function, column, ...)` - Database-level aggregation

**Properties:**
- `table_name` - Primary table name
- `primary_key` - Primary key column name

**Usage Example:**
```python
from interfaces import IRepository
from typing import Dict, Any

class UserRepository(IRepository[User]):
    @property
    def table_name(self) -> str:
        return "users"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_id(self, entity_id: Any, fields=None) -> Optional[User]:
        # Implementation
        pass
    
    # ... implement other abstract methods
```

### IRepositoryFactory

Factory interface for creating repository instances. Enables dependency injection and testing.

**Key Methods:**
- `create_repository(entity_type)` - Create repository for entity type

## Cache Interfaces

### ICacheManager

Abstract base class for cache manager implementations. Defines the contract for caching operations.

**Key Methods:**
- `get(key, namespace)` - Get value from cache
- `set(key, value, ttl, namespace)` - Set value with TTL
- `delete(key, namespace)` - Delete value
- `exists(key, namespace)` - Check if key exists
- `get_ttl(key, namespace)` - Get remaining TTL
- `invalidate_pattern(pattern, namespace)` - Pattern-based invalidation
- `get_or_fetch(key, fetch_fn, ttl, namespace)` - Cache-aside pattern
- `generate_key(namespace, entity_type, identifier)` - Generate namespaced key
- `get_multiple(keys, namespace)` - Batch get
- `set_multiple(items, namespace)` - Batch set
- `flush_namespace(namespace)` - Clear namespace
- `ping()` - Health check

**Cache Key Format:**
```
{namespace}:{entity_type}:{identifier}

Examples:
- fir:record:12345
- violation:check:abc-def
- kb:query:hash_value
```

**Usage Example:**
```python
from interfaces import ICacheManager

class RedisCacheManager(ICacheManager):
    def __init__(self, redis_client):
        self._redis = redis_client
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        full_key = f"{namespace}:{key}"
        value = self._redis.get(full_key)
        return json.loads(value) if value else None
    
    def set(self, key: str, value: Any, ttl: int, namespace: str = "default") -> bool:
        full_key = f"{namespace}:{key}"
        return self._redis.setex(full_key, ttl, json.dumps(value))
    
    # ... implement other abstract methods
```

### ICacheInvalidationStrategy

Strategy interface for cache invalidation patterns. Allows different invalidation strategies to be implemented.

**Key Methods:**
- `invalidate_for_entity(cache_manager, entity_id, namespace)` - Invalidate for entity
- `get_invalidation_patterns(entity_id)` - Get patterns to invalidate

**Usage Example:**
```python
from interfaces import ICacheInvalidationStrategy

class FIRCacheInvalidationStrategy(ICacheInvalidationStrategy):
    def get_invalidation_patterns(self, entity_id: Any) -> List[str]:
        return [
            "list:*",      # All list caches
            "query:*",     # All query caches
            "stats:*",     # All statistics caches
            f"user:{entity_id}:*"  # User-specific caches
        ]
    
    def invalidate_for_entity(
        self,
        cache_manager: ICacheManager,
        entity_id: Any,
        namespace: str
    ) -> None:
        patterns = self.get_invalidation_patterns(entity_id)
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern, namespace)
```

## External Service Interfaces

### IExternalService

Base interface for all external service integrations. Defines common operations for health checks and monitoring.

**Key Methods:**
- `health_check()` - Check if service is healthy
- `get_status()` - Get service status (AVAILABLE, UNAVAILABLE, DEGRADED, UNKNOWN)
- `get_metrics()` - Get service metrics

**Properties:**
- `service_name` - Name of the external service

### IModelServer

Extended interface for AI model server integrations. Adds model-specific operations.

**Key Methods:**
- `call(input_data, **kwargs)` - Call model server
- `call_with_retry(input_data, max_retries, **kwargs)` - Call with retry
- `get_circuit_breaker_status()` - Get circuit breaker status
- `reset_circuit_breaker()` - Reset circuit breaker

### ILLMModelServer

Interface for Large Language Model servers. Extends IModelServer with LLM-specific operations.

**Key Methods:**
- `generate_text(prompt, max_tokens, temperature, **kwargs)` - Generate text
- `generate_completion(prompt, stop_sequences, **kwargs)` - Generate completion

**Usage Example:**
```python
from interfaces import ILLMModelServer, ServiceStatus

class GGUFModelServer(ILLMModelServer):
    def __init__(self, url: str, circuit_breaker, retry_handler):
        self._url = url
        self._circuit_breaker = circuit_breaker
        self._retry_handler = retry_handler
    
    @property
    def service_name(self) -> str:
        return "gguf_llm_server"
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self._url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_status(self) -> ServiceStatus:
        if self.health_check():
            return ServiceStatus.AVAILABLE
        return ServiceStatus.UNAVAILABLE
    
    def generate_text(self, prompt: str, max_tokens: int = 512, **kwargs) -> Dict[str, Any]:
        def _call():
            response = requests.post(
                f"{self._url}/generate",
                json={"prompt": prompt, "max_tokens": max_tokens, **kwargs}
            )
            response.raise_for_status()
            return response.json()
        
        return self._circuit_breaker.call(
            self._retry_handler.execute_with_retry,
            _call,
            None
        )
    
    # ... implement other abstract methods
```

### IASRModelServer

Interface for Automatic Speech Recognition servers.

**Key Methods:**
- `transcribe_audio(audio_data, language, **kwargs)` - Transcribe audio to text

### IOCRModelServer

Interface for Optical Character Recognition servers.

**Key Methods:**
- `extract_text(image_data, language, **kwargs)` - Extract text from image

### IServiceFactory

Factory interface for creating external service instances.

**Key Methods:**
- `create_llm_service(config)` - Create LLM service
- `create_asr_service(config)` - Create ASR service
- `create_ocr_service(config)` - Create OCR service

## Custom Exceptions

The external service interfaces define custom exceptions for error handling:

- `ServiceError` - Base exception for service errors
- `ServiceUnavailableError` - Service is unavailable
- `ServiceTimeoutError` - Request timed out
- `CircuitBreakerOpenError` - Circuit breaker is open

## Benefits of Using Interfaces

### 1. Clear Contracts

Interfaces establish clear contracts between layers, making it explicit what operations are available and what behavior is expected.

### 2. Dependency Injection

Interfaces enable dependency injection, allowing concrete implementations to be injected at runtime:

```python
from fastapi import Depends
from interfaces import IRepository, ICacheManager

def get_fir_service(
    repository: IRepository = Depends(get_fir_repository),
    cache: ICacheManager = Depends(get_cache_manager)
) -> FIRService:
    return FIRService(repository, cache)
```

### 3. Testing

Interfaces make testing easier by allowing mock implementations:

```python
from unittest.mock import Mock
from interfaces import ICacheManager

def test_fir_service():
    # Create mock cache manager
    mock_cache = Mock(spec=ICacheManager)
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    
    # Inject mock into service
    service = FIRService(repository, mock_cache)
    
    # Test service behavior
    result = service.get_fir("123")
    mock_cache.get.assert_called_once()
```

### 4. Maintainability

Interfaces improve maintainability by:
- Documenting expected behavior
- Enforcing consistent patterns
- Making it easier to swap implementations
- Reducing coupling between layers

### 5. Type Safety

Interfaces provide type hints that enable:
- IDE autocomplete and type checking
- Static analysis with mypy
- Better documentation
- Fewer runtime errors

## Implementation Guidelines

### For Repository Implementations

1. Inherit from `IRepository[T]` where T is your entity type
2. Implement all abstract methods
3. Use selective column retrieval (no SELECT *)
4. Implement cursor-based pagination
5. Use database-level aggregation
6. Invalidate cache on data modifications

### For Cache Implementations

1. Inherit from `ICacheManager`
2. Implement all abstract methods
3. Use namespaced keys to prevent collisions
4. Set appropriate TTL values
5. Handle cache failures gracefully (fallback to source)
6. Track metrics for cache operations

### For External Service Implementations

1. Inherit from appropriate interface (ILLMModelServer, IASRModelServer, etc.)
2. Implement all abstract methods
3. Use circuit breaker pattern for protection
4. Implement retry logic for transient failures
5. Track metrics for service calls
6. Provide health check endpoints

## Migration Guide

### Updating Existing Code

To update existing implementations to use these interfaces:

1. **Repositories:**
```python
# Before
class FIRRepository(BaseRepository[FIR]):
    pass

# After
from interfaces import IRepository

class FIRRepository(BaseRepository[FIR], IRepository[FIR]):
    pass
```

2. **Cache Managers:**
```python
# Before
class CacheManager:
    pass

# After
from interfaces import ICacheManager

class CacheManager(ICacheManager):
    pass
```

3. **External Services:**
```python
# Before
class ModelServerService:
    pass

# After
from interfaces import ILLMModelServer

class GGUFModelServer(ILLMModelServer):
    pass
```

## Testing with Interfaces

### Creating Mock Implementations

```python
from interfaces import IRepository, ICacheManager
from unittest.mock import Mock

# Mock repository
mock_repo = Mock(spec=IRepository)
mock_repo.find_by_id.return_value = FIR(id="123", ...)

# Mock cache
mock_cache = Mock(spec=ICacheManager)
mock_cache.get.return_value = None
mock_cache.set.return_value = True

# Use mocks in tests
service = FIRService(mock_repo, mock_cache)
```

### Creating Test Implementations

```python
from interfaces import ICacheManager

class InMemoryCacheManager(ICacheManager):
    """In-memory cache for testing."""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        full_key = f"{namespace}:{key}"
        return self._cache.get(full_key)
    
    def set(self, key: str, value: Any, ttl: int, namespace: str = "default") -> bool:
        full_key = f"{namespace}:{key}"
        self._cache[full_key] = value
        return True
    
    # ... implement other methods
```

## See Also

- [Base Repository Implementation](../repositories/base_repository.py)
- [FIR Repository Implementation](../repositories/fir_repository.py)
- [Cache Manager Implementation](../infrastructure/cache_manager.py)
- [Model Server Service Implementation](../services/model_server_service.py)
- [Dependency Injection](../api/dependencies.py)
