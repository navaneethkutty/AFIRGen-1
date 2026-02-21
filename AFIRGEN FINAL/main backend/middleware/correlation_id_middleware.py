"""
Correlation ID middleware for FastAPI.

This middleware generates a unique correlation ID for each incoming request,
adds it to the request context, and propagates it through all operations
for request tracing.
"""

import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate correlation IDs for request tracing.
    
    For each incoming request:
    1. Generates a unique correlation ID (or uses existing from header)
    2. Adds correlation ID to request.state for access in handlers
    3. Binds correlation ID to structlog context for automatic inclusion in logs
    4. Adds correlation ID to response headers
    """
    
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and manage correlation ID.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The HTTP response with correlation ID header
        """
        # Check if correlation ID already exists in request headers
        # (e.g., from upstream service or client)
        correlation_id = request.headers.get(self.CORRELATION_ID_HEADER)
        
        # Generate new correlation ID if not provided
        if not correlation_id:
            correlation_id = self._generate_correlation_id()
        
        # Add correlation ID to request state for access in handlers
        request.state.correlation_id = correlation_id
        
        # Bind correlation ID to structlog context
        # This ensures all logs during this request include the correlation ID
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.CORRELATION_ID_HEADER] = correlation_id
            
            return response
            
        finally:
            # Clear structlog context after request completes
            structlog.contextvars.clear_contextvars()
    
    def _generate_correlation_id(self) -> str:
        """
        Generate a unique correlation ID.
        
        Uses UUID4 for guaranteed uniqueness across distributed systems.
        
        Returns:
            A unique correlation ID string
        """
        return str(uuid.uuid4())


def setup_correlation_id_middleware(app):
    """
    Setup correlation ID middleware for FastAPI application.
    
    This should be added early in the middleware stack to ensure
    correlation IDs are available for all subsequent middleware and handlers.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(CorrelationIdMiddleware)
