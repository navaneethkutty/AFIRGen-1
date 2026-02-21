"""
test_property_cache_headers.py
-----------------------------------------------------------------------------
Property-Based Tests for Cache Header Middleware
-----------------------------------------------------------------------------

Property tests for cache header middleware using Hypothesis to verify:
- Property 16: Cache headers for cacheable responses

Requirements Validated: 3.6 (API Response Optimization - Cache Headers)
"""

import hashlib
import pytest
from hypothesis import given, strategies as st, settings, assume
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from middleware.cache_header_middleware import CacheHeaderMiddleware


# Feature: backend-optimization, Property 16: Cache headers for cacheable responses
@given(
    max_age=st.integers(min_value=60, max_value=86400),  # 1 minute to 1 day
    response_content=st.text(min_size=10, max_size=1000),
    status_code=st.just(200)  # Only successful responses
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_headers_for_cacheable_get_responses(max_age, response_content, status_code):
    """
    Property 16: For any cacheable API response (GET requests for immutable
    or slowly-changing data), the response should include appropriate
    Cache-Control headers.
    
    **Validates: Requirements 3.6**
    
    This property verifies that:
    1. GET requests receive Cache-Control headers
    2. Cache-Control includes max-age directive
    3. Cache-Control includes public directive
    4. ETag header is present
    5. ETag is consistently generated for same content
    """
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=max_age
    )
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Property assertions
    assert response.status_code == status_code, "Response should be successful"
    
    # Cache-Control header must be present
    assert "Cache-Control" in response.headers, \
        "GET responses should have Cache-Control header"
    
    cache_control = response.headers["Cache-Control"]
    
    # Cache-Control must include max-age directive
    assert f"max-age={max_age}" in cache_control, \
        f"Cache-Control should include max-age={max_age}"
    
    # Cache-Control must include public directive
    assert "public" in cache_control, \
        "Cache-Control should include public directive for cacheable responses"
    
    # ETag header must be present
    assert "ETag" in response.headers, \
        "GET responses should have ETag header"
    
    # ETag should be properly formatted (quoted)
    etag = response.headers["ETag"]
    assert etag.startswith('"') and etag.endswith('"'), \
        "ETag should be quoted"
    
    # ETag should be consistent for same content
    response2 = client.get("/test")
    assert response2.headers["ETag"] == etag, \
        "ETag should be consistent for same content"


@given(
    method=st.sampled_from(["POST", "PUT", "PATCH", "DELETE"]),
    response_content=st.text(min_size=10, max_size=1000)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_no_cache_headers_for_non_get_methods(method, response_content):
    """
    Property: For any non-GET HTTP method, cache headers should NOT
    be added to the response.
    
    **Validates: Requirements 3.6**
    
    This property verifies that only GET requests are cacheable,
    as other methods typically modify state.
    """
    app = FastAPI()
    
    # Register endpoint for the given method
    if method == "POST":
        @app.post("/test")
        async def test_endpoint():
            return Response(content=response_content, media_type="text/plain")
    elif method == "PUT":
        @app.put("/test")
        async def test_endpoint():
            return Response(content=response_content, media_type="text/plain")
    elif method == "PATCH":
        @app.patch("/test")
        async def test_endpoint():
            return Response(content=response_content, media_type="text/plain")
    elif method == "DELETE":
        @app.delete("/test")
        async def test_endpoint():
            return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600
    )
    
    client = TestClient(app)
    response = client.request(method, "/test")
    
    # Non-GET methods should not have cache headers
    assert "Cache-Control" not in response.headers, \
        f"{method} requests should not have Cache-Control header"
    assert "ETag" not in response.headers, \
        f"{method} requests should not have ETag header"


@given(
    content1=st.text(min_size=10, max_size=500),
    content2=st.text(min_size=10, max_size=500)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_etag_uniqueness_for_different_content(content1, content2):
    """
    Property: For any two different response contents, the generated
    ETags should be different.
    
    **Validates: Requirements 3.6**
    
    This property verifies that ETags uniquely identify response content.
    """
    # Skip if contents are the same
    assume(content1 != content2)
    
    app = FastAPI()
    
    @app.get("/test/{item_id}")
    async def test_endpoint(item_id: str):
        if item_id == "1":
            return Response(content=content1, media_type="text/plain")
        else:
            return Response(content=content2, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600
    )
    
    client = TestClient(app)
    
    response1 = client.get("/test/1")
    response2 = client.get("/test/2")
    
    etag1 = response1.headers["ETag"]
    etag2 = response2.headers["ETag"]
    
    # Different content should produce different ETags
    assert etag1 != etag2, \
        "Different content should produce different ETags"


@given(
    response_content=st.text(min_size=10, max_size=1000),
    max_age=st.integers(min_value=60, max_value=86400)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_conditional_request_304_not_modified(response_content, max_age):
    """
    Property: For any GET request with If-None-Match header matching
    the current ETag, the server should return 304 Not Modified.
    
    **Validates: Requirements 3.6**
    
    This property verifies that conditional requests work correctly
    to save bandwidth.
    """
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=max_age
    )
    
    client = TestClient(app)
    
    # First request to get ETag
    response1 = client.get("/test")
    etag = response1.headers["ETag"]
    
    # Second request with If-None-Match
    response2 = client.get("/test", headers={"If-None-Match": etag})
    
    # Should return 304 Not Modified
    assert response2.status_code == 304, \
        "Matching ETag should return 304 Not Modified"
    
    # 304 response should still have ETag
    assert "ETag" in response2.headers, \
        "304 response should include ETag header"
    
    assert response2.headers["ETag"] == etag, \
        "304 response ETag should match original"
    
    # 304 response should have empty body
    assert len(response2.content) == 0, \
        "304 response should have empty body"


@given(
    response_content=st.text(min_size=10, max_size=1000),
    wrong_etag=st.text(
        min_size=10,
        max_size=50,
        alphabet=st.characters(min_codepoint=32, max_codepoint=126)  # ASCII printable
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_conditional_request_200_when_etag_differs(response_content, wrong_etag):
    """
    Property: For any GET request with If-None-Match header that does NOT
    match the current ETag, the server should return 200 with full content.
    
    **Validates: Requirements 3.6**
    
    This property verifies that non-matching ETags result in full response.
    """
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600
    )
    
    client = TestClient(app)
    
    # Request with non-matching ETag (quoted)
    response = client.get("/test", headers={"If-None-Match": f'"{wrong_etag}"'})
    
    # Should return 200 with full content
    assert response.status_code == 200, \
        "Non-matching ETag should return 200 OK"
    
    assert len(response.content) > 0, \
        "Non-matching ETag should return full content"
    
    assert response.text == response_content, \
        "Response content should match original"


@given(
    path=st.sampled_from(["/health", "/metrics", "/admin/status", "/internal/debug"]),
    response_content=st.text(min_size=10, max_size=500)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_excluded_paths_no_cache_headers(path, response_content):
    """
    Property: For any path in the excluded paths set, cache headers
    should NOT be added regardless of request method.
    
    **Validates: Requirements 3.6**
    
    This property verifies that certain endpoints can be excluded
    from caching (e.g., health checks, metrics).
    """
    app = FastAPI()
    
    @app.get(path)
    async def test_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        exclude_paths={"/health", "/metrics", "/admin/status", "/internal/debug"}
    )
    
    client = TestClient(app)
    response = client.get(path)
    
    # Excluded paths should not have cache headers
    assert "Cache-Control" not in response.headers, \
        f"Excluded path {path} should not have Cache-Control header"
    assert "ETag" not in response.headers, \
        f"Excluded path {path} should not have ETag header"


@given(
    max_age=st.integers(min_value=300, max_value=7200),
    response_content=st.text(min_size=10, max_size=500)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_per_endpoint_cache_duration(max_age, response_content):
    """
    Property: For any endpoint with a specific cache duration configured,
    the Cache-Control max-age should match that duration.
    
    **Validates: Requirements 3.6**
    
    This property verifies that different endpoints can have different
    cache durations based on their data volatility.
    """
    app = FastAPI()
    
    @app.get("/custom")
    async def custom_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    @app.get("/default")
    async def default_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        cacheable_paths={
            "/custom": max_age
        }
    )
    
    client = TestClient(app)
    
    # Custom endpoint should use specified max-age
    response_custom = client.get("/custom")
    assert f"max-age={max_age}" in response_custom.headers["Cache-Control"], \
        f"Custom endpoint should have max-age={max_age}"
    
    # Default endpoint should use default max-age
    response_default = client.get("/default")
    assert "max-age=3600" in response_default.headers["Cache-Control"], \
        "Default endpoint should have max-age=3600"


@given(
    status_code=st.sampled_from([400, 401, 403, 404, 500, 502, 503]),
    response_content=st.text(min_size=10, max_size=500)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_no_cache_for_error_responses(status_code, response_content):
    """
    Property: For any error response (status code != 200), cache headers
    should NOT be added.
    
    **Validates: Requirements 3.6**
    
    This property verifies that only successful responses are cached,
    preventing caching of error states.
    """
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return Response(
            content=response_content,
            status_code=status_code,
            media_type="text/plain"
        )
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600
    )
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == status_code
    
    # Error responses should not have cache headers
    assert "Cache-Control" not in response.headers, \
        f"Error response {status_code} should not have Cache-Control header"
    assert "ETag" not in response.headers, \
        f"Error response {status_code} should not have ETag header"


@given(
    response_content=st.text(min_size=10, max_size=500)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_immutable_directive_for_static_resources(response_content):
    """
    Property: For any path marked as immutable, the Cache-Control header
    should include the "immutable" directive.
    
    **Validates: Requirements 3.6**
    
    This property verifies that static/immutable resources get the
    immutable directive to prevent unnecessary revalidation.
    """
    app = FastAPI()
    
    @app.get("/static/file.js")
    async def static_endpoint():
        return Response(content=response_content, media_type="application/javascript")
    
    @app.get("/dynamic/data")
    async def dynamic_endpoint():
        return Response(content=response_content, media_type="application/json")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600,
        immutable_paths={"/static/*"}
    )
    
    client = TestClient(app)
    
    # Static resource should have immutable directive
    response_static = client.get("/static/file.js")
    assert "immutable" in response_static.headers["Cache-Control"], \
        "Static resources should have immutable directive"
    
    # Dynamic resource should not have immutable directive
    response_dynamic = client.get("/dynamic/data")
    assert "immutable" not in response_dynamic.headers["Cache-Control"], \
        "Dynamic resources should not have immutable directive"


@given(
    response_content=st.text(min_size=10, max_size=500),
    num_etags=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_multiple_etags_in_if_none_match(response_content, num_etags):
    """
    Property: For any If-None-Match header containing multiple ETags,
    if any of them matches the current ETag, return 304 Not Modified.
    
    **Validates: Requirements 3.6**
    
    This property verifies that multiple ETags in If-None-Match are
    handled correctly (as per HTTP spec).
    """
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600
    )
    
    client = TestClient(app)
    
    # First request to get current ETag
    response1 = client.get("/test")
    current_etag = response1.headers["ETag"]
    
    # Create list of ETags including the current one
    fake_etags = [f'"fake-etag-{i}"' for i in range(num_etags - 1)]
    all_etags = fake_etags + [current_etag]
    if_none_match = ", ".join(all_etags)
    
    # Request with multiple ETags
    response2 = client.get("/test", headers={"If-None-Match": if_none_match})
    
    # Should return 304 because one ETag matches
    assert response2.status_code == 304, \
        "Should return 304 when any ETag in If-None-Match matches"


@given(
    response_content=st.text(min_size=10, max_size=500)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_wildcard_if_none_match(response_content):
    """
    Property: For any If-None-Match header with wildcard (*),
    always return 304 Not Modified.
    
    **Validates: Requirements 3.6**
    
    This property verifies that wildcard If-None-Match is handled
    correctly (as per HTTP spec).
    """
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return Response(content=response_content, media_type="text/plain")
    
    app.add_middleware(
        CacheHeaderMiddleware,
        default_max_age=3600
    )
    
    client = TestClient(app)
    
    # Request with wildcard If-None-Match
    response = client.get("/test", headers={"If-None-Match": "*"})
    
    # Should always return 304 for wildcard
    assert response.status_code == 304, \
        "Wildcard If-None-Match should always return 304"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
