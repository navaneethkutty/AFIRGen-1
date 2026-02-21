"""
cache_header_middleware.py
-----------------------------------------------------------------------------
HTTP Cache Header Middleware with ETag Support
-----------------------------------------------------------------------------

This module provides cache header middleware that:
- Sets Cache-Control headers for cacheable GET requests
- Generates and validates ETags for conditional requests
- Supports If-None-Match header for 304 Not Modified responses
- Allows per-endpoint cache configuration

Requirements Validated: 3.6 (API Response Optimization - Cache Headers)
"""

import hashlib
from typing import Set, Optional, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.datastructures import MutableHeaders

from infrastructure.logging import get_logger


logger = get_logger(__name__)


class CacheHeaderMiddleware(BaseHTTPMiddleware):
    """
    HTTP cache header middleware for API responses.
    
    This middleware adds cache headers to GET responses for cacheable endpoints:
    - Sets Cache-Control headers with configurable max-age
    - Generates ETags based on response content hash
    - Handles If-None-Match conditional requests (304 Not Modified)
    - Supports per-endpoint cache configuration
    
    Features:
    - Automatic ETag generation from response body
    - 304 Not Modified responses for matching ETags
    - Configurable cache duration per endpoint
    - Exclusion of non-cacheable endpoints
    - Support for immutable resources
    
    Example usage:
        app.add_middleware(
            CacheHeaderMiddleware,
            default_max_age=3600,  # 1 hour default
            cacheable_paths={
                "/api/v1/fir/{id}": 3600,  # 1 hour
                "/api/v1/violations": 1800,  # 30 minutes
            },
            exclude_paths={"/api/v1/process"}
        )
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_max_age: int = 3600,  # 1 hour default
        cacheable_paths: Optional[Dict[str, int]] = None,
        exclude_paths: Optional[Set[str]] = None,
        immutable_paths: Optional[Set[str]] = None,
    ):
        """
        Initialize cache header middleware.
        
        Args:
            app: ASGI application
            default_max_age: Default cache duration in seconds (default 1 hour)
            cacheable_paths: Dict mapping path patterns to cache durations in seconds
            exclude_paths: Set of paths to exclude from caching
            immutable_paths: Set of paths for immutable resources (Cache-Control: immutable)
        """
        super().__init__(app)
        self.default_max_age = default_max_age
        self.cacheable_paths = cacheable_paths or {}
        self.exclude_paths = exclude_paths or set()
        self.immutable_paths = immutable_paths or set()
        
        logger.info(
            "Cache header middleware initialized",
            default_max_age=default_max_age,
            cacheable_paths_count=len(self.cacheable_paths),
            excluded_paths_count=len(self.exclude_paths)
        )
    
    def _should_cache(self, request: Request) -> bool:
        """
        Determine if the request should have cache headers.
        
        Args:
            request: The incoming request
            
        Returns:
            True if the response should be cached, False otherwise
        """
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Check if path is explicitly excluded
        path = request.url.path
        if path in self.exclude_paths:
            return False
        
        # Check if path matches any excluded pattern
        for excluded in self.exclude_paths:
            if excluded.endswith("*") and path.startswith(excluded[:-1]):
                return False
        
        return True
    
    def _get_cache_duration(self, path: str) -> int:
        """
        Get cache duration for a specific path.
        
        Args:
            path: Request path
            
        Returns:
            Cache duration in seconds
        """
        # Check exact path match
        if path in self.cacheable_paths:
            return self.cacheable_paths[path]
        
        # Check pattern match (e.g., "/api/v1/fir/*")
        for pattern, duration in self.cacheable_paths.items():
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return duration
        
        # Return default
        return self.default_max_age
    
    def _is_immutable(self, path: str) -> bool:
        """
        Check if the path represents an immutable resource.
        
        Args:
            path: Request path
            
        Returns:
            True if the resource is immutable, False otherwise
        """
        if path in self.immutable_paths:
            return True
        
        # Check pattern match
        for pattern in self.immutable_paths:
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return True
        
        return False
    
    def _generate_etag(self, content: bytes) -> str:
        """
        Generate ETag from response content.
        
        Args:
            content: Response body content
            
        Returns:
            ETag value (MD5 hash of content)
        """
        # Use MD5 hash for ETag (fast and sufficient for cache validation)
        content_hash = hashlib.md5(content).hexdigest()
        return f'"{content_hash}"'
    
    def _etag_matches(self, etag: str, if_none_match: str) -> bool:
        """
        Check if ETag matches If-None-Match header.
        
        Args:
            etag: Generated ETag value
            if_none_match: If-None-Match header value from request
            
        Returns:
            True if ETags match, False otherwise
        """
        # Handle multiple ETags in If-None-Match (comma-separated)
        if_none_match_values = [tag.strip() for tag in if_none_match.split(",")]
        
        # Check for wildcard match
        if "*" in if_none_match_values:
            return True
        
        # Check for exact match
        return etag in if_none_match_values
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and add cache headers to response if applicable.
        
        Args:
            request: The incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response with cache headers added
        """
        # Check if this request should have cache headers
        if not self._should_cache(request):
            return await call_next(request)
        
        # Get the response
        response = await call_next(request)
        
        # Only add cache headers to successful responses
        if response.status_code != 200:
            return response
        
        # Read response body to generate ETag
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Generate ETag
        etag = self._generate_etag(body)
        
        # Check If-None-Match header for conditional request
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and self._etag_matches(etag, if_none_match):
            # Return 304 Not Modified
            return Response(
                content=b"",
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": response.headers.get("cache-control", ""),
                }
            )
        
        # Get cache duration for this path
        path = request.url.path
        max_age = self._get_cache_duration(path)
        
        # Build Cache-Control header
        cache_control_parts = [f"max-age={max_age}"]
        
        # Add public directive (cacheable by any cache)
        cache_control_parts.append("public")
        
        # Add immutable directive if applicable
        if self._is_immutable(path):
            cache_control_parts.append("immutable")
        
        cache_control = ", ".join(cache_control_parts)
        
        # Create new response with cache headers
        headers = MutableHeaders(response.headers)
        headers["Cache-Control"] = cache_control
        headers["ETag"] = etag
        
        # Create new response with updated headers
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(headers),
            media_type=response.media_type,
        )


# Example usage
if __name__ == "__main__":
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Configure cache header middleware
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,  # 1 hour default
        cacheable_paths={
            "/api/v1/fir/*": 3600,  # FIR records: 1 hour
            "/api/v1/violations": 1800,  # Violations: 30 minutes
            "/api/v1/kb/*": 7200,  # Knowledge base: 2 hours
        },
        exclude_paths={
            "/api/v1/process",  # Don't cache FIR generation
            "/health",
            "/metrics",
        },
        immutable_paths={
            "/api/v1/static/*",  # Static resources are immutable
        }
    )
    
    @app.get("/api/v1/fir/{fir_id}")
    async def get_fir(fir_id: str):
        return {"id": fir_id, "status": "completed"}
    
    @app.get("/api/v1/violations")
    async def get_violations():
        return [{"id": "v1", "type": "speeding"}]
    
    print("Cache header middleware example configured")

