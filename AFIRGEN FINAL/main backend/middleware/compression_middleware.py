"""
compression_middleware.py
-----------------------------------------------------------------------------
Response Compression Middleware with Configurable Gzip Compression
-----------------------------------------------------------------------------

This module provides compression middleware that:
- Applies gzip compression for responses larger than a configurable threshold (default 1KB)
- Sets appropriate Content-Encoding headers
- Allows per-endpoint compression configuration
- Respects client Accept-Encoding headers

Requirements Validated: 3.1 (API Response Optimization - Compression)
"""

import gzip
from typing import Set, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.datastructures import Headers, MutableHeaders

from infrastructure.logging import get_logger


logger = get_logger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Gzip compression middleware for API responses.
    
    This middleware compresses responses larger than min_size bytes using gzip
    compression when the client supports it (via Accept-Encoding header).
    
    Features:
    - Configurable minimum response size threshold (default 1KB)
    - Configurable compression level (1-9, default 6)
    - Per-endpoint exclusion support
    - Automatic Content-Encoding header management
    - Client capability detection via Accept-Encoding
    
    Example usage:
        app.add_middleware(
            CompressionMiddleware,
            min_size=1024,  # 1KB threshold
            compression_level=6,
            exclude_paths={"/health", "/metrics"}
        )
    """
    
    def __init__(
        self,
        app: ASGIApp,
        min_size: int = 1024,  # 1KB default threshold
        compression_level: int = 6,  # Balanced compression level
        exclude_paths: Optional[Set[str]] = None,
        exclude_media_types: Optional[Set[str]] = None,
    ):
        """
        Initialize compression middleware.
        
        Args:
            app: ASGI application
            min_size: Minimum response size in bytes to trigger compression (default 1KB)
            compression_level: Gzip compression level 1-9 (default 6)
            exclude_paths: Set of paths to exclude from compression
            exclude_media_types: Set of media types to exclude from compression
        """
        super().__init__(app)
        self.min_size = min_size
        self.compression_level = max(1, min(9, compression_level))  # Clamp to 1-9
        self.exclude_paths = exclude_paths or set()
        
        # Default media types to exclude (already compressed formats)
        self.exclude_media_types = exclude_media_types or {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "video/mp4",
            "video/mpeg",
            "audio/mpeg",
            "audio/mp3",
            "application/zip",
            "application/gzip",
            "application/x-gzip",
        }
        
        logger.info(
            "Compression middleware initialized",
            min_size=min_size,
            compression_level=self.compression_level,
            excluded_paths_count=len(self.exclude_paths)
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and compress response if applicable.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response with compression applied if conditions are met
        """
        # Check if path is excluded
        if request.url.path in self.exclude_paths:
            logger.debug("Compression skipped for excluded path", path=request.url.path)
            return await call_next(request)
        
        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            logger.debug("Client does not accept gzip encoding", path=request.url.path)
            return await call_next(request)
        
        # Get the response
        response = await call_next(request)
        
        # Check if response should be compressed
        if not self._should_compress(response):
            return response
        
        # Compress the response
        return await self._compress_response(response, request.url.path)
    
    def _should_compress(self, response: Response) -> bool:
        """
        Determine if response should be compressed.
        
        Args:
            response: The response to check
            
        Returns:
            True if response should be compressed, False otherwise
        """
        # Don't compress if already encoded
        if response.headers.get("content-encoding"):
            logger.debug("Response already has content-encoding, skipping compression")
            return False
        
        # Check media type
        content_type = response.headers.get("content-type", "")
        media_type = content_type.split(";")[0].strip().lower()
        
        if media_type in self.exclude_media_types:
            logger.debug(f"Media type excluded from compression: {media_type}")
            return False
        
        # Check response size
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size < self.min_size:
                    logger.debug(f"Response too small for compression: {size}B < {self.min_size}B")
                    return False
            except ValueError:
                pass  # Invalid content-length, proceed with compression attempt
        
        return True
    
    async def _compress_response(self, response: Response, path: str) -> Response:
        """
        Compress response body using gzip.
        
        Args:
            response: The response to compress
            path: Request path for logging
            
        Returns:
            Compressed response
        """
        try:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            original_size = len(body)
            
            # Check size threshold
            if original_size < self.min_size:
                logger.debug(
                    "Response body too small after reading",
                    original_size=original_size,
                    min_size=self.min_size
                )
                # Return uncompressed response
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            
            # Compress the body
            compressed_body = gzip.compress(body, compresslevel=self.compression_level)
            compressed_size = len(compressed_body)
            
            # Calculate compression ratio
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            logger.debug(
                "Compressed response",
                path=path,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=f"{compression_ratio:.1f}%"
            )
            
            # Create new response with compressed body
            headers = MutableHeaders(response.headers)
            headers["content-encoding"] = "gzip"
            headers["content-length"] = str(compressed_size)
            
            # Remove any existing content-length that might be incorrect
            if "content-length" in response.headers:
                del headers["content-length"]
            headers["content-length"] = str(compressed_size)
            
            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=dict(headers),
                media_type=response.media_type,
            )
            
        except Exception as e:
            logger.error("Compression failed", path=path, error=str(e))
            # Return original response on compression failure
            return response


def setup_compression_middleware(
    app,
    min_size: int = 1024,
    compression_level: int = 6,
    exclude_paths: Optional[Set[str]] = None,
    exclude_media_types: Optional[Set[str]] = None,
) -> None:
    """
    Setup compression middleware for the application.
    
    Args:
        app: FastAPI application
        min_size: Minimum response size in bytes to trigger compression (default 1KB)
        compression_level: Gzip compression level 1-9 (default 6)
        exclude_paths: Set of paths to exclude from compression
        exclude_media_types: Set of media types to exclude from compression
    """
    # Default excluded paths (health checks, metrics, docs)
    if exclude_paths is None:
        exclude_paths = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=min_size,
        compression_level=compression_level,
        exclude_paths=exclude_paths,
        exclude_media_types=exclude_media_types,
    )
    
    logger.info(
        "Compression middleware configured",
        min_size=min_size,
        compression_level=compression_level
    )

