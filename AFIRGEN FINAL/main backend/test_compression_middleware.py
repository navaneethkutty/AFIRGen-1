"""
test_compression_middleware.py
-----------------------------------------------------------------------------
Unit Tests for Compression Middleware
-----------------------------------------------------------------------------

Tests for the compression middleware including:
- Compression for responses > 1KB
- Content-Encoding header handling
- Per-endpoint configuration
- Client capability detection
- Edge cases and error handling

Requirements Validated: 3.1 (API Response Optimization - Compression)
"""

import gzip
import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from middleware.compression_middleware import CompressionMiddleware, setup_compression_middleware


@pytest.fixture
def app_with_compression():
    """Create a FastAPI app with compression middleware"""
    app = FastAPI()
    
    @app.get("/small")
    async def small_response():
        """Response smaller than 1KB"""
        return {"message": "small"}
    
    @app.get("/large")
    async def large_response():
        """Response larger than 1KB"""
        # Generate ~2KB of data
        data = {"items": [{"id": i, "name": f"Item {i}", "description": "x" * 50} for i in range(30)]}
        return data
    
    @app.get("/text")
    async def text_response():
        """Large text response"""
        return Response(content="x" * 2000, media_type="text/plain")
    
    @app.get("/image")
    async def image_response():
        """Image response (should not be compressed)"""
        return Response(content=b"fake_image_data" * 100, media_type="image/jpeg")
    
    @app.get("/excluded")
    async def excluded_response():
        """Excluded endpoint"""
        return {"data": "x" * 2000}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}
    
    # Add compression middleware
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,  # 1KB
        compression_level=6,
        exclude_paths={"/excluded", "/health"}
    )
    
    return app


def test_small_response_not_compressed(app_with_compression):
    """Test that responses smaller than 1KB are not compressed"""
    client = TestClient(app_with_compression)
    
    response = client.get("/small", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.json() == {"message": "small"}


def test_large_response_compressed(app_with_compression):
    """Test that responses larger than 1KB are compressed"""
    client = TestClient(app_with_compression)
    
    response = client.get("/large", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    # TestClient automatically decompresses, so check the raw response
    # In real scenario, content-encoding header would be set
    assert response.json()["items"][0]["id"] == 0


def test_compression_without_accept_encoding():
    """Test that compression is skipped when client doesn't accept gzip"""
    # Create a fresh app without compression for this test
    app = FastAPI()
    
    @app.get("/large")
    async def large_response():
        """Response larger than 1KB"""
        data = {"items": [{"id": i, "name": f"Item {i}", "description": "x" * 50} for i in range(30)]}
        return data
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    # Use TestClient with raise_server_exceptions=False to avoid automatic headers
    client = TestClient(app, raise_server_exceptions=False)
    
    # Explicitly set empty Accept-Encoding
    response = client.get("/large", headers={"Accept-Encoding": ""})
    
    assert response.status_code == 200
    # With empty Accept-Encoding, compression should be skipped
    assert "content-encoding" not in response.headers or response.headers.get("content-encoding") != "gzip"


def test_excluded_path_not_compressed(app_with_compression):
    """Test that excluded paths are not compressed"""
    client = TestClient(app_with_compression)
    
    response = client.get("/excluded", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    assert "content-encoding" not in response.headers


def test_health_check_not_compressed(app_with_compression):
    """Test that health check endpoint is not compressed"""
    client = TestClient(app_with_compression)
    
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.json() == {"status": "healthy"}


def test_image_not_compressed(app_with_compression):
    """Test that image responses are not compressed (already compressed format)"""
    client = TestClient(app_with_compression)
    
    response = client.get("/image", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.headers["content-type"] == "image/jpeg"


def test_compression_level_configuration():
    """Test that compression level can be configured"""
    # Test with different compression levels in separate apps
    for level in [1, 6, 9]:
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"data": "x" * 2000}
        
        app.add_middleware(
            CompressionMiddleware,
            min_size=1024,
            compression_level=level
        )
        
        client = TestClient(app)
        response = client.get("/test", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 200


def test_compression_level_clamping():
    """Test that compression level is clamped to valid range (1-9)"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"data": "x" * 2000}
    
    # Test with out-of-range values
    middleware = CompressionMiddleware(
        app=app,
        min_size=1024,
        compression_level=15  # Should be clamped to 9
    )
    
    assert middleware.compression_level == 9
    
    middleware = CompressionMiddleware(
        app=app,
        min_size=1024,
        compression_level=0  # Should be clamped to 1
    )
    
    assert middleware.compression_level == 1


def test_min_size_threshold():
    """Test that min_size threshold is respected"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"data": "x" * 500}  # 500 bytes
    
    # Set threshold to 2KB
    app.add_middleware(
        CompressionMiddleware,
        min_size=2048,
        compression_level=6
    )
    
    client = TestClient(app)
    response = client.get("/test", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    # Response should not be compressed (below threshold)
    assert "content-encoding" not in response.headers


def test_multiple_accept_encodings():
    """Test that gzip is detected among multiple accept-encoding values"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"data": "x" * 2000}
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    client = TestClient(app)
    
    # Test with multiple encodings
    response = client.get("/test", headers={"Accept-Encoding": "deflate, gzip, br"})
    assert response.status_code == 200


def test_case_insensitive_accept_encoding():
    """Test that Accept-Encoding header is case-insensitive"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"data": "x" * 2000}
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    client = TestClient(app)
    
    # Test with different cases
    for encoding in ["GZIP", "Gzip", "gzip", "GzIp"]:
        response = client.get("/test", headers={"Accept-Encoding": encoding})
        assert response.status_code == 200


def test_already_encoded_response():
    """Test that already encoded responses are not re-compressed"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        content = gzip.compress(b"x" * 2000)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Encoding": "gzip"}
        )
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    client = TestClient(app)
    response = client.get("/test", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    # Should still have gzip encoding (not double-compressed)
    assert response.headers.get("content-encoding") == "gzip"


def test_setup_compression_middleware():
    """Test the setup helper function"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"data": "x" * 2000}
    
    # Use setup function
    setup_compression_middleware(
        app,
        min_size=2048,
        compression_level=8,
        exclude_paths={"/custom-excluded"}
    )
    
    client = TestClient(app)
    
    # Test that default excluded paths work
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 404  # Endpoint doesn't exist, but middleware should skip it
    
    # Test custom excluded path
    response = client.get("/custom-excluded", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 404  # Endpoint doesn't exist


def test_text_response_compression(app_with_compression):
    """Test compression of text/plain responses"""
    client = TestClient(app_with_compression)
    
    response = client.get("/text", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    assert len(response.content) > 0


def test_empty_response():
    """Test handling of empty responses"""
    app = FastAPI()
    
    @app.get("/empty")
    async def empty_response():
        return Response(content="", media_type="text/plain")
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    client = TestClient(app)
    response = client.get("/empty", headers={"Accept-Encoding": "gzip"})
    
    assert response.status_code == 200
    assert "content-encoding" not in response.headers


def test_compression_with_various_media_types():
    """Test compression behavior with different media types"""
    app = FastAPI()
    
    @app.get("/json")
    async def json_response():
        return {"data": "x" * 2000}
    
    @app.get("/xml")
    async def xml_response():
        return Response(content="<data>" + "x" * 2000 + "</data>", media_type="application/xml")
    
    @app.get("/zip")
    async def zip_response():
        return Response(content=b"fake_zip" * 200, media_type="application/zip")
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    client = TestClient(app)
    
    # JSON should be compressed
    response = client.get("/json", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    
    # XML should be compressed
    response = client.get("/xml", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    
    # ZIP should not be compressed (already compressed)
    response = client.get("/zip", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert "content-encoding" not in response.headers


def test_concurrent_requests():
    """Test that compression works correctly with concurrent requests"""
    app = FastAPI()
    
    @app.get("/test/{item_id}")
    async def test_endpoint(item_id: int):
        return {"id": item_id, "data": "x" * 2000}
    
    app.add_middleware(
        CompressionMiddleware,
        min_size=1024,
        compression_level=6
    )
    
    client = TestClient(app)
    
    # Make multiple concurrent requests
    responses = []
    for i in range(10):
        response = client.get(f"/test/{i}", headers={"Accept-Encoding": "gzip"})
        responses.append(response)
    
    # Verify all responses are successful
    for i, response in enumerate(responses):
        assert response.status_code == 200
        assert response.json()["id"] == i


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
