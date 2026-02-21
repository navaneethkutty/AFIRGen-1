"""
Health and metrics API routes.

This module contains health check and metrics endpoints.
Requirements: 8.1 - Separate business logic from API routing
"""

import asyncio
from fastapi import APIRouter, Depends

from infrastructure.cloudwatch_metrics import record_health_check
from infrastructure.logging import get_logger
from infrastructure.cache_manager import CacheManager
from infrastructure.database import DatabasePool
from api.dependencies import get_cache, get_database_pool

# Initialize logger
log = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    cache: CacheManager = Depends(get_cache),
    db_pool: DatabasePool = Depends(get_database_pool)
):
    """
    Health check endpoint with dependency injection.
    
    Checks health of database and cache connections.
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        health_status = {
            "status": "healthy",
            "components": {}
        }
        
        # Check database connection
        try:
            conn = db_pool.get_connection()
            conn.close()
            health_status["components"]["database"] = {
                "status": "healthy",
                "pool_size": db_pool.pool_size,
                "available": db_pool.available_connections
            }
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check cache connection
        try:
            cache_healthy = cache.ping()
            health_status["components"]["cache"] = {
                "status": "healthy" if cache_healthy else "unhealthy"
            }
            if not cache_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["components"]["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Record health check metrics
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        healthy = health_status.get("status") == "healthy"
        record_health_check("main-backend", healthy, duration_ms)
        
        return health_status
        
    except Exception as e:
        log.error(f"Health check failed: {e}")
        
        # Record unhealthy status
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        record_health_check("main-backend", False, duration_ms)
        
        return {"status": "unhealthy", "error": str(e)}


@router.get("/metrics")
async def get_metrics(
    cache: CacheManager = Depends(get_cache),
    db_pool: DatabasePool = Depends(get_database_pool)
):
    """
    Endpoint for monitoring performance metrics with dependency injection.
    
    Returns current system metrics including database and cache status.
    """
    try:
        from infrastructure.metrics import MetricsCollector
        
        metrics = {
            "database": {
                "pool_size": db_pool.pool_size,
                "active_connections": db_pool.active_connections,
                "available_connections": db_pool.available_connections
            },
            "cache": {
                "memory_usage": cache.get_memory_usage(),
                "connected": cache.ping()
            }
        }
        
        return metrics
        
    except Exception as e:
        log.error(f"Error retrieving metrics: {e}")
        return {"error": str(e)}

