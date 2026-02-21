"""
test_cache_header_middleware.py
-----------------------------------------------------------------------------
Unit Tests for HTTP Cache Header Middleware
-----------------------------------------------------------------------------

Tests the cache header middleware functionality including:
- Cache-Control header generation
- ETag generation and validation
- Conditional request handling (304 Not Modified)
- Per-endpoint cache configuration
- Exclusion of non-cacheable endpoints

Requirements Validated: 3.6 (API Response Optimization - Cache Headers)
"""

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from middleware.cache_header_middleware import CacheHeaderMiddleware


def test_cache_headers_added_to_get_requests():
    """Test that Cache-Control and ETag headers are added to GET requests."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert "ETag" in response.headers
    assert "max-age=3600" in response.headers["Cache-Control"]
    assert "public" in response.headers["Cache-Control"]


def test_no_cache_headers_for_post_requests():
    """Test that cache headers are not added to POST requests."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.post("/test")
    async def test_endpoint():
        return {"message": "created"}
    
    client = TestClient(app)
    response = client.post("/test")
    
    assert response.status_code == 200
    assert "Cache-Control" not in response.headers
    assert "ETag" not in response.headers


def test_etag_generation_consistent():
    """Test that ETag is consistently generated for same content."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    
    # Make two requests
    response1 = client.get("/test")
    response2 = client.get("/test")
    
    # ETags should be identical for same content
    assert response1.headers["ETag"] == response2.headers["ETag"]


def test_etag_different_for_different_content():
    """Test that different content generates different ETags."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test/{item_id}")
    async def test_endpoint(item_id: str):
        return {"id": item_id, "message": "test data"}
    
    client = TestClient(app)
    
    # Make requests with different parameters
    response1 = client.get("/test/1")
    response2 = client.get("/test/2")
    
    # ETags should be different for different content
    assert response1.headers["ETag"] != response2.headers["ETag"]


def test_conditional_request_304_not_modified():
    """Test that If-None-Match returns 304 Not Modified when ETag matches."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    
    # First request to get ETag
    response1 = client.get("/test")
    etag = response1.headers["ETag"]
    
    # Second request with If-None-Match
    response2 = client.get("/test", headers={"If-None-Match": etag})
    
    assert response2.status_code == 304
    assert response2.headers["ETag"] == etag
    assert len(response2.content) == 0  # No body for 304


def test_conditional_request_200_when_etag_differs():
    """Test that If-None-Match returns 200 when ETag doesn't match."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    
    # Request with non-matching ETag
    response = client.get("/test", headers={"If-None-Match": '"different-etag"'})
    
    assert response.status_code == 200
    assert "ETag" in response.headers
    assert len(response.content) > 0  # Full body returned


def test_per_endpoint_cache_duration():
    """Test that different endpoints can have different cache durations."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        cacheable_paths={
            "/short": 300,  # 5 minutes
            "/long": 7200,  # 2 hours
        }
    )
    
    @app.get("/short")
    async def short_cache():
        return {"cache": "short"}
    
    @app.get("/long")
    async def long_cache():
        return {"cache": "long"}
    
    @app.get("/default")
    async def default_cache():
        return {"cache": "default"}
    
    client = TestClient(app)
    
    # Check short cache
    response_short = client.get("/short")
    assert "max-age=300" in response_short.headers["Cache-Control"]
    
    # Check long cache
    response_long = client.get("/long")
    assert "max-age=7200" in response_long.headers["Cache-Control"]
    
    # Check default cache
    response_default = client.get("/default")
    assert "max-age=3600" in response_default.headers["Cache-Control"]


def test_wildcard_path_matching():
    """Test that wildcard path patterns work correctly."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        cacheable_paths={
            "/api/v1/fir/*": 1800,
        }
    )
    
    @app.get("/api/v1/fir/123")
    async def get_fir():
        return {"id": "123"}
    
    @app.get("/api/v1/other/456")
    async def get_other():
        return {"id": "456"}
    
    client = TestClient(app)
    
    # FIR endpoint should use custom duration
    response_fir = client.get("/api/v1/fir/123")
    assert "max-age=1800" in response_fir.headers["Cache-Control"]
    
    # Other endpoint should use default
    response_other = client.get("/api/v1/other/456")
    assert "max-age=3600" in response_other.headers["Cache-Control"]


def test_excluded_paths_no_cache():
    """Test that excluded paths don't get cache headers."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        exclude_paths={"/health", "/metrics"}
    )
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/data")
    async def data():
        return {"data": "value"}
    
    client = TestClient(app)
    
    # Excluded endpoint should not have cache headers
    response_health = client.get("/health")
    assert "Cache-Control" not in response_health.headers
    assert "ETag" not in response_health.headers
    
    # Normal endpoint should have cache headers
    response_data = client.get("/data")
    assert "Cache-Control" in response_data.headers
    assert "ETag" in response_data.headers


def test_excluded_wildcard_paths():
    """Test that wildcard exclusion patterns work."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        exclude_paths={"/admin/*"}
    )
    
    @app.get("/admin/users")
    async def admin_users():
        return {"users": []}
    
    @app.get("/public/data")
    async def public_data():
        return {"data": "value"}
    
    client = TestClient(app)
    
    # Admin endpoint should not have cache headers
    response_admin = client.get("/admin/users")
    assert "Cache-Control" not in response_admin.headers
    
    # Public endpoint should have cache headers
    response_public = client.get("/public/data")
    assert "Cache-Control" in response_public.headers


def test_immutable_resources():
    """Test that immutable resources get immutable directive."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        immutable_paths={"/static/*"}
    )
    
    @app.get("/static/logo.png")
    async def static_file():
        return Response(content=b"fake image data", media_type="image/png")
    
    @app.get("/dynamic/data")
    async def dynamic_data():
        return {"data": "value"}
    
    client = TestClient(app)
    
    # Static resource should have immutable directive
    response_static = client.get("/static/logo.png")
    assert "immutable" in response_static.headers["Cache-Control"]
    
    # Dynamic resource should not have immutable directive
    response_dynamic = client.get("/dynamic/data")
    assert "immutable" not in response_dynamic.headers["Cache-Control"]


def test_no_cache_for_error_responses():
    """Test that cache headers are not added to error responses."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/error")
    async def error_endpoint():
        return Response(content="Not Found", status_code=404)
    
    client = TestClient(app)
    
    response = client.get("/error")
    assert response.status_code == 404
    assert "Cache-Control" not in response.headers
    assert "ETag" not in response.headers


def test_multiple_etags_in_if_none_match():
    """Test that multiple ETags in If-None-Match are handled correctly."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    
    # First request to get ETag
    response1 = client.get("/test")
    etag = response1.headers["ETag"]
    
    # Request with multiple ETags (one matching)
    response2 = client.get(
        "/test",
        headers={"If-None-Match": f'"old-etag", {etag}, "another-etag"'}
    )
    
    assert response2.status_code == 304


def test_wildcard_if_none_match():
    """Test that wildcard (*) in If-None-Match always returns 304."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    
    # Request with wildcard If-None-Match
    response = client.get("/test", headers={"If-None-Match": "*"})
    
    assert response.status_code == 304


def test_etag_format():
    """Test that ETag is properly formatted with quotes."""
    app = FastAPI()
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test data"}
    
    client = TestClient(app)
    
    response = client.get("/test")
    etag = response.headers["ETag"]
    
    # ETag should be quoted
    assert etag.startswith('"')
    assert etag.endswith('"')
    # ETag should contain hex characters (MD5 hash)
    assert len(etag) == 34  # 32 hex chars + 2 quotes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
