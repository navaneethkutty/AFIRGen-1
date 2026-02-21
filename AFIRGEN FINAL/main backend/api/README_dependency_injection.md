# Dependency Injection Implementation

## Overview

This document describes the dependency injection implementation for the AFIRGen backend API.

**Requirements Addressed:**
- **Requirement 8.2**: Use dependency injection for external service dependencies

## Architecture

The dependency injection system follows FastAPI's built-in dependency injection pattern using `Depends()`. Dependencies are organized into three layers:

1. **Infrastructure Layer**: Database pools, cache managers, retry handlers, circuit breakers
2. **Repository Layer**: Data access objects that depend on infrastructure
3. **Service Layer**: Business logic services that depend on repositories and infrastructure

## Key Components

### 1. Dependency Module (`api/dependencies.py`)

Central module that provides:
- Dependency injection functions for all layers
- Global instance management for infrastructure components
- Initialization and cleanup functions for app lifecycle
- Testing support functions for dependency overrides

### 2. Infrastructure Dependencies

```python
from api.dependencies import (
    get_database_pool,
    get_cache,
    get_metrics_collector,
    get_retry_handler,
    get_circuit_breaker
)
```

**Database Pool:**
```python
def get_database_pool() -> DatabasePool:
    """Get database connection pool instance."""
```

**Cache Manager:**
```python
def get_cache() -> CacheManager:
    """Get cache manager instance."""
```

**Retry Handler:**
```python
def get_retry_handler() -> RetryHandler:
    """Get retry handler with default configuration."""
```

**Circuit Breaker:**
```python
def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """Get or create a circuit breaker instance."""
```

### 3. Repository Dependencies

```python
from api.dependencies import (
    get_fir_repository,
    get_base_repository
)
```

**FIR Repository:**
```python
def get_fir_repository(
    db_pool: DatabasePool = Depends(get_database_pool),
    cache: CacheManager = Depends(get_cache)
) -> FIRRepository:
    """Get FIR repository with injected dependencies."""
```

### 4. Service Dependencies

```python
from api.dependencies import (
    get_session_service,
    get_model_service
)
```

**Session Service:**
```python
def get_session_service(
    cache: CacheManager = Depends(get_cache),
    db_pool: DatabasePool = Depends(get_database_pool)
) -> SessionService:
    """Get session service with injected dependencies."""
```

**Model Service:**
```python
def get_model_service(
    circuit_breaker: CircuitBreaker = Depends(...),
    retry_handler: RetryHandler = Depends(get_retry_handler),
    cache: CacheManager = Depends(get_cache)
) -> ModelService:
    """Get model service with injected dependencies."""
```

## Usage in API Routes

### Before (Hard-coded Dependencies)

```python
@router.post("/process")
async def process_endpoint(
    audio: Optional[UploadFile] = File(None),
    fir_processing_service: FIRProcessingService = None,  # Not injected!
):
    # Had to manually create service instance
    service = FIRProcessingService()
    result = await service.process_input(audio=audio)
    return result
```

### After (Dependency Injection)

```python
from fastapi import Depends
from api.dependencies import get_session_service

@router.post("/process")
async def process_endpoint(
    audio: Optional[UploadFile] = File(None),
    session_service: SessionService = Depends(get_session_service),
):
    # Service is automatically injected with all its dependencies
    result = await session_service.process_input(audio=audio)
    return result
```

## Application Lifecycle Integration

### Initialization (App Startup)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.dependencies import init_dependencies, cleanup_dependencies

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize dependencies
    db_config = {
        'pool_name': 'afirgen_pool',
        'pool_size': 10,
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'afirgen'),
        'user': os.getenv('DB_USER', 'user'),
        'password': os.getenv('DB_PASSWORD', 'pass')
    }
    
    init_dependencies(db_config)
    
    yield
    
    # Shutdown: Cleanup dependencies
    cleanup_dependencies()

app = FastAPI(lifespan=lifespan)
```

### Route Registration

```python
from api.routes import fir_routes, health_routes

# Register routers
app.include_router(fir_routes.router)
app.include_router(health_routes.router)
```

## Benefits

### 1. Testability

Dependencies can be easily mocked for testing:

```python
from unittest.mock import Mock
from api.dependencies import override_cache_manager

def test_endpoint():
    # Override cache with mock
    mock_cache = Mock(spec=CacheManager)
    override_cache_manager(mock_cache)
    
    # Test endpoint
    response = client.get("/api/v1/session/123/status")
    
    # Verify mock was called
    mock_cache.get.assert_called_once()
```

### 2. Loose Coupling

Routes don't need to know how to create services:

```python
# Route only depends on service interface
async def process_endpoint(
    session_service: SessionService = Depends(get_session_service)
):
    # Don't care how session_service was created
    return await session_service.process_input(...)
```

### 3. Single Responsibility

Each layer has clear responsibilities:
- **Routes**: HTTP concerns (validation, error handling)
- **Services**: Business logic
- **Repositories**: Data access
- **Infrastructure**: Cross-cutting concerns

### 4. Resource Management

Infrastructure components are created once and reused:

```python
# Database pool created once during startup
init_dependencies(db_config)

# All routes share the same pool
@router.get("/endpoint1")
async def endpoint1(db_pool: DatabasePool = Depends(get_database_pool)):
    # Uses shared pool
    pass

@router.get("/endpoint2")
async def endpoint2(db_pool: DatabasePool = Depends(get_database_pool)):
    # Uses same shared pool
    pass
```

### 5. Configuration Flexibility

Dependencies can be configured differently per environment:

```python
# Development
init_dependencies({
    'pool_size': 5,
    'host': 'localhost'
})

# Production
init_dependencies({
    'pool_size': 50,
    'host': 'prod-db.example.com'
})
```

## Dependency Graph

```
API Routes
    ↓ (depends on)
Services (SessionService, ModelService)
    ↓ (depends on)
Repositories (FIRRepository)
    ↓ (depends on)
Infrastructure (DatabasePool, CacheManager, RetryHandler, CircuitBreaker)
```

## Testing Support

### Override Dependencies

```python
from api.dependencies import (
    override_database_pool,
    override_cache_manager,
    reset_dependencies
)

# Override for testing
mock_pool = Mock(spec=DatabasePool)
override_database_pool(mock_pool)

# Reset after test
reset_dependencies()
```

### FastAPI Dependency Override

```python
from fastapi.testclient import TestClient
from api.dependencies import get_cache

app = FastAPI()
client = TestClient(app)

# Override dependency
def mock_cache():
    return Mock(spec=CacheManager)

app.dependency_overrides[get_cache] = mock_cache

# Test with overridden dependency
response = client.get("/health")
```

## Migration Guide

### Step 1: Update Route Imports

```python
# Add dependency imports
from fastapi import Depends
from api.dependencies import get_session_service
```

### Step 2: Update Route Signatures

```python
# Before
async def endpoint(service: Service = None):
    pass

# After
async def endpoint(service: Service = Depends(get_service)):
    pass
```

### Step 3: Remove Manual Service Creation

```python
# Before
async def endpoint():
    service = Service()  # Manual creation
    return await service.do_something()

# After
async def endpoint(service: Service = Depends(get_service)):
    return await service.do_something()  # Injected
```

### Step 4: Initialize Dependencies in App Startup

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_dependencies(db_config)
    yield
    cleanup_dependencies()

app = FastAPI(lifespan=lifespan)
```

## Best Practices

1. **Always use Depends()**: Never create service instances manually in routes
2. **Initialize once**: Call `init_dependencies()` only during app startup
3. **Cleanup properly**: Call `cleanup_dependencies()` during app shutdown
4. **Test with overrides**: Use dependency overrides for testing
5. **Keep dependencies pure**: Dependency functions should have no side effects
6. **Document dependencies**: Add docstrings explaining what each dependency provides

## Validation

### Requirements 8.2 Validation

✅ **Database dependencies injected**: `get_database_pool()` provides shared pool
✅ **Cache dependencies injected**: `get_cache()` provides shared cache manager
✅ **Service dependencies injected**: `get_session_service()`, `get_model_service()`
✅ **Hard-coded dependencies removed**: All routes use `Depends()`
✅ **Testability improved**: Dependencies can be overridden for testing
✅ **Resource management**: Shared instances created once during startup

## Examples

### Complete Route Example

```python
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_session_service
from services.session_service import SessionService

router = APIRouter()

@router.get("/session/{session_id}/status")
async def get_session_status(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Get session status with injected service."""
    try:
        status = await session_service.get_session_status(session_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Complete Test Example

```python
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from api.dependencies import get_session_service

def test_get_session_status():
    # Create mock service
    mock_service = Mock(spec=SessionService)
    mock_service.get_session_status = AsyncMock(
        return_value={"status": "active"}
    )
    
    # Override dependency
    app.dependency_overrides[get_session_service] = lambda: mock_service
    
    # Test endpoint
    client = TestClient(app)
    response = client.get("/session/123/status")
    
    # Verify
    assert response.status_code == 200
    assert response.json() == {"status": "active"}
    mock_service.get_session_status.assert_called_once_with("123")
```

## Conclusion

The dependency injection implementation provides:
- ✅ Clean separation of concerns
- ✅ Improved testability
- ✅ Better resource management
- ✅ Loose coupling between layers
- ✅ Configuration flexibility
- ✅ Compliance with Requirement 8.2

All API routes now use dependency injection instead of hard-coded dependencies, making the codebase more maintainable and testable.
