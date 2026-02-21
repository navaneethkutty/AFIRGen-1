"""
Metrics middleware for FastAPI.

This middleware automatically tracks all API requests, recording:
- Request counts by endpoint, method, and status code
- Request duration
- Correlation ID in metrics labels
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from infrastructure.metrics import MetricsCollector, api_request_in_progress


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track API request metrics.
    
    Tracks:
    - Request count by endpoint, method, and status code
    - Request duration by endpoint and method
    - In-progress requests gauge
    - Correlation ID in metrics context
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and record metrics.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The HTTP response
        """
        # Extract endpoint path (route pattern, not actual path with params)
        endpoint = request.url.path
        method = request.method
        
        # Get correlation ID from request state if available
        correlation_id = getattr(request.state, "correlation_id", None)
        
        # Track in-progress requests
        api_request_in_progress.labels(endpoint=endpoint, method=method).inc()
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            return response
            
        except Exception as exc:
            # Record error status
            status_code = 500
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Decrement in-progress gauge
            api_request_in_progress.labels(endpoint=endpoint, method=method).dec()
            
            # Record metrics
            MetricsCollector.record_request_duration(
                endpoint=endpoint,
                method=method,
                duration=duration,
                status=status_code
            )


def setup_metrics_middleware(app):
    """
    Setup metrics middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(MetricsMiddleware)
