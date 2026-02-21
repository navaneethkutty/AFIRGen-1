"""
Unit tests and property-based tests for CacheManager component.

Tests cover:
- Cache key generation with namespacing
- Get, set, delete operations with TTL support
- Cache invalidation by pattern matching
- Get-or-fetch pattern for cache-aside strategy
- Connection pooling and error handling
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from hypothesis import given, strategies as st, settings, assume

# Import the components to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'infrastructure'))

from infrastructure.cache_manager import CacheManager
from infrastructure.redis_client import RedisClient


# ============================================================================
# Unit Tests
# ============================================================================

class TestCacheManagerUnit:
    """Unit tests for CacheManager basic operations."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = Mock()
        mock.ping.return_value = True
        return mock
    
    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create CacheManager with mock Redis client."""
        return CacheManager(redis_client=mock_redis)
    
    def test_generate_key_format(self, cache_manager):
        """Test cache key generation follows namespacing pattern."""
        key = cache_manager.generate_key("fir", "record", "12345")
        assert key == "fir:record:12345"
        
        key = cache_manager.generate_key("violation", "check", "abc-def")
        assert key == "violation:check:abc-def"
    
    def test_set_with_ttl(self, cache_manager, mock_redis):
        """Test setting cache value with TTL."""
        result = cache_manager.set("test_key", {"data": "value"}, ttl=3600, namespace="test")
        
        assert result is True
        mock_redis.setex.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test:test_key"  # key with namespace
        assert call_args[0][1] == 3600  # TTL
        assert json.loads(call_args[0][2]) == {"data": "value"}  # serialized value
    
    def test_get_existing_key(self, cache_manager, mock_redis):
        """Test getting an existing cache value."""
        mock_redis.get.return_value = json.dumps({"data": "value"})
        
        result = cache_manager.get("test_key", namespace="test")
        
        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("test:test_key")
    
    def test_get_nonexistent_key(self, cache_manager, mock_redis):
        """Test getting a non-existent cache value returns None."""
        mock_redis.get.return_value = None
        
        result = cache_manager.get("missing_key", namespace="test")
        
        assert result is None
    
    def test_delete_existing_key(self, cache_manager, mock_redis):
        """Test deleting an existing cache key."""
        mock_redis.delete.return_value = 1
        
        result = cache_manager.delete("test_key", namespace="test")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test:test_key")
    
    def test_delete_nonexistent_key(self, cache_manager, mock_redis):
        """Test deleting a non-existent key returns False."""
        mock_redis.delete.return_value = 0
        
        result = cache_manager.delete("missing_key", namespace="test")
        
        assert result is False
    
    def test_invalidate_pattern(self, cache_manager, mock_redis):
        """Test invalidating cache entries by pattern."""
        # Mock keys matching pattern
        mock_redis.keys.return_value = [
            b"test:user:1",
            b"test:user:2",
            b"test:user:3"
        ]
        mock_redis.delete.return_value = 3
        
        result = cache_manager.invalidate_pattern("user:*", namespace="test")
        
        assert result == 3
        mock_redis.keys.assert_called_once_with("test:user:*")
        mock_redis.delete.assert_called_once()
    
    def test_invalidate_pattern_no_matches(self, cache_manager, mock_redis):
        """Test invalidating pattern with no matches returns 0."""
        mock_redis.keys.return_value = []
        
        result = cache_manager.invalidate_pattern("nomatch:*", namespace="test")
        
        assert result == 0
    
    def test_get_or_fetch_cache_hit(self, cache_manager, mock_redis):
        """Test get_or_fetch returns cached value without calling fetch function."""
        mock_redis.get.return_value = json.dumps({"data": "cached"})
        fetch_fn = Mock()
        
        result = cache_manager.get_or_fetch(
            key="test_key",
            fetch_fn=fetch_fn,
            ttl=3600,
            namespace="test"
        )
        
        assert result == {"data": "cached"}
        fetch_fn.assert_not_called()
    
    def test_get_or_fetch_cache_miss(self, cache_manager, mock_redis):
        """Test get_or_fetch calls fetch function on cache miss and stores result."""
        mock_redis.get.return_value = None
        fetch_fn = Mock(return_value={"data": "fetched"})
        
        result = cache_manager.get_or_fetch(
            key="test_key",
            fetch_fn=fetch_fn,
            ttl=3600,
            namespace="test"
        )
        
        assert result == {"data": "fetched"}
        fetch_fn.assert_called_once()
        mock_redis.setex.assert_called_once()
    
    def test_get_or_fetch_propagates_fetch_error(self, cache_manager, mock_redis):
        """Test get_or_fetch propagates exceptions from fetch function."""
        mock_redis.get.return_value = None
        fetch_fn = Mock(side_effect=ValueError("Fetch failed"))
        
        with pytest.raises(ValueError, match="Fetch failed"):
            cache_manager.get_or_fetch(
                key="test_key",
                fetch_fn=fetch_fn,
                ttl=3600,
                namespace="test"
            )
    
    def test_cache_failure_fallback_on_get(self, cache_manager, mock_redis):
        """Test that Redis errors on get return None (fallback behavior)."""
        mock_redis.get.side_effect = RedisError("Connection failed")
        
        result = cache_manager.get("test_key", namespace="test")
        
        assert result is None
    
    def test_cache_failure_fallback_on_set(self, cache_manager, mock_redis):
        """Test that Redis errors on set return False (fallback behavior)."""
        mock_redis.setex.side_effect = RedisError("Connection failed")
        
        result = cache_manager.set("test_key", {"data": "value"}, ttl=3600, namespace="test")
        
        assert result is False
    
    def test_cache_failure_fallback_on_delete(self, cache_manager, mock_redis):
        """Test that Redis errors on delete return False (fallback behavior)."""
        mock_redis.delete.side_effect = RedisError("Connection failed")
        
        result = cache_manager.delete("test_key", namespace="test")
        
        assert result is False
    
    def test_cache_failure_fallback_on_invalidate_pattern(self, cache_manager, mock_redis):
        """Test that Redis errors on invalidate_pattern return 0 (fallback behavior)."""
        mock_redis.keys.side_effect = RedisError("Connection failed")
        
        result = cache_manager.invalidate_pattern("user:*", namespace="test")
        
        assert result == 0
    
    def test_exists_key_present(self, cache_manager, mock_redis):
        """Test exists returns True for existing key."""
        mock_redis.exists.return_value = 1
        
        result = cache_manager.exists("test_key", namespace="test")
        
        assert result is True
    
    def test_exists_key_absent(self, cache_manager, mock_redis):
        """Test exists returns False for non-existent key."""
        mock_redis.exists.return_value = 0
        
        result = cache_manager.exists("missing_key", namespace="test")
        
        assert result is False
    
    def test_get_ttl_existing_key(self, cache_manager, mock_redis):
        """Test get_ttl returns remaining TTL for existing key."""
        mock_redis.ttl.return_value = 3600
        
        result = cache_manager.get_ttl("test_key", namespace="test")
        
        assert result == 3600
    
    def test_get_ttl_nonexistent_key(self, cache_manager, mock_redis):
        """Test get_ttl returns None for non-existent key."""
        mock_redis.ttl.return_value = -2  # Redis returns -2 for non-existent keys
        
        result = cache_manager.get_ttl("missing_key", namespace="test")
        
        assert result is None
    
    def test_get_ttl_no_expiry(self, cache_manager, mock_redis):
        """Test get_ttl returns None for key with no TTL."""
        mock_redis.ttl.return_value = -1  # Redis returns -1 for keys with no TTL
        
        result = cache_manager.get_ttl("test_key", namespace="test")
        
        assert result is None
    
    def test_set_multiple(self, cache_manager, mock_redis):
        """Test setting multiple cache entries at once."""
        items = [
            ("key1", {"data": "value1"}, 3600),
            ("key2", {"data": "value2"}, 7200),
            ("key3", {"data": "value3"}, 1800)
        ]
        
        result = cache_manager.set_multiple(items, namespace="test")
        
        assert result == 3
        assert mock_redis.setex.call_count == 3
    
    def test_get_multiple(self, cache_manager, mock_redis):
        """Test getting multiple cache entries at once."""
        def mock_get(key):
            values = {
                "test:key1": json.dumps({"data": "value1"}),
                "test:key2": json.dumps({"data": "value2"}),
                "test:key3": None
            }
            return values.get(key)
        
        mock_redis.get.side_effect = mock_get
        
        result = cache_manager.get_multiple(["key1", "key2", "key3"], namespace="test")
        
        assert result == {
            "key1": {"data": "value1"},
            "key2": {"data": "value2"}
        }
        assert "key3" not in result
    
    def test_flush_namespace(self, cache_manager, mock_redis):
        """Test flushing all keys in a namespace."""
        mock_redis.keys.return_value = [b"test:key1", b"test:key2", b"test:key3"]
        mock_redis.delete.return_value = 3
        
        result = cache_manager.flush_namespace("test")
        
        assert result == 3
        mock_redis.keys.assert_called_once_with("test:*")
    
    def test_ping_success(self, cache_manager, mock_redis):
        """Test ping returns True when Redis is available."""
        mock_redis.ping.return_value = True
        
        result = cache_manager.ping()
        
        assert result is True
    
    def test_ping_failure(self, cache_manager, mock_redis):
        """Test ping returns False when Redis is unavailable."""
        mock_redis.ping.side_effect = RedisError("Connection failed")
        
        result = cache_manager.ping()
        
        assert result is False
    
    def test_json_decode_error_returns_none(self, cache_manager, mock_redis):
        """Test that invalid JSON in cache returns None."""
        mock_redis.get.return_value = "invalid json {"
        
        result = cache_manager.get("test_key", namespace="test")
        
        assert result is None
    
    def test_set_with_non_serializable_value(self, cache_manager, mock_redis):
        """Test that non-JSON-serializable values return False."""
        # Create a non-serializable object
        class NonSerializable:
            pass
        
        result = cache_manager.set("test_key", NonSerializable(), ttl=3600, namespace="test")
        
        assert result is False


# ============================================================================
# Property-Based Tests
# ============================================================================

def create_mock_redis_for_property_tests():
    """Create a mock Redis client for property tests."""
    mock = Mock()
    mock.ping.return_value = True
    # Store data in memory for property tests
    mock._data = {}
    mock._ttls = {}
    
    def mock_setex(key, ttl, value):
        mock._data[key] = value
        mock._ttls[key] = ttl
        return True
    
    def mock_get(key):
        return mock._data.get(key)
    
    def mock_delete(*keys):
        count = 0
        for key in keys:
            if key in mock._data:
                del mock._data[key]
                if key in mock._ttls:
                    del mock._ttls[key]
                count += 1
        return count
    
    def mock_exists(key):
        return 1 if key in mock._data else 0
    
    def mock_ttl(key):
        if key not in mock._data:
            return -2
        return mock._ttls.get(key, -1)
    
    def mock_keys(pattern):
        # Simple pattern matching for tests
        import fnmatch
        return [k for k in mock._data.keys() if fnmatch.fnmatch(k, pattern.replace('*', '*'))]
    
    mock.setex.side_effect = mock_setex
    mock.get.side_effect = mock_get
    mock.delete.side_effect = mock_delete
    mock.exists.side_effect = mock_exists
    mock.ttl.side_effect = mock_ttl
    mock.keys.side_effect = mock_keys
    
    return mock


class TestCacheManagerProperties:
    """Property-based tests for CacheManager correctness properties."""
    
    # Property 6: Cache entries have TTL values
    # Validates: Requirements 2.1
    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.booleans())
        ),
        ttl=st.integers(min_value=1, max_value=86400),
        namespace=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=20)
    def test_property_cache_entries_have_ttl(self, key, value, ttl, namespace):
        """
        Property 6: Cache entries have TTL values
        
        For any data stored in the Cache_Layer, the cache entry should have
        a TTL (time-to-live) value set, ensuring automatic expiration.
        
        Validates: Requirements 2.1
        """
        # Create fresh mock and cache manager for each test
        mock_redis = create_mock_redis_for_property_tests()
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Set cache entry
        result = cache_manager.set(key, value, ttl, namespace)
        
        # Verify set was successful
        assert result is True
        
        # Verify TTL was set
        full_key = f"{namespace}:{key}"
        assert full_key in mock_redis._ttls
        assert mock_redis._ttls[full_key] == ttl
        assert mock_redis._ttls[full_key] > 0
    
    # Property 7: Cache hit returns cached value
    # Validates: Requirements 2.2
    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.booleans())
        ),
        ttl=st.integers(min_value=60, max_value=3600),
        namespace=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=20)
    def test_property_cache_hit_returns_cached_value(self, key, value, ttl, namespace):
        """
        Property 7: Cache hit returns cached value
        
        For any cache key that exists and is not expired, requesting that key
        should return the cached value without querying the database.
        
        Validates: Requirements 2.2
        """
        # Create fresh mock and cache manager for each test
        mock_redis = create_mock_redis_for_property_tests()
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Store value in cache
        cache_manager.set(key, value, ttl, namespace)
        
        # Retrieve value from cache
        cached_value = cache_manager.get(key, namespace)
        
        # Verify cached value matches original
        assert cached_value == value
        assert cached_value is not None
    
    # Property 8: Cache miss triggers fetch and populate
    # Validates: Requirements 2.3
    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.booleans())
        ),
        ttl=st.integers(min_value=60, max_value=3600),
        namespace=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=20)
    def test_property_cache_miss_triggers_fetch(self, key, value, ttl, namespace):
        """
        Property 8: Cache miss triggers fetch and populate
        
        For any cache key that does not exist, requesting that key should
        trigger a database fetch and populate the cache with the result.
        
        Validates: Requirements 2.3
        """
        # Create fresh mock and cache manager for each test
        mock_redis = create_mock_redis_for_property_tests()
        cache_manager = CacheManager(redis_client=mock_redis)
        
        # Create fetch function that returns the value
        fetch_fn = Mock(return_value=value)
        
        # Ensure key doesn't exist in cache
        full_key = f"{namespace}:{key}"
        if full_key in mock_redis._data:
            del mock_redis._data[full_key]
        
        # Call get_or_fetch
        result = cache_manager.get_or_fetch(key, fetch_fn, ttl, namespace)
        
        # Verify fetch function was called
        fetch_fn.assert_called_once()
        
        # Verify result matches fetched value
        assert result == value
        
        # Verify value was stored in cache
        cached_value = cache_manager.get(key, namespace)
        assert cached_value == value
    
    # Property 11: Cache key namespacing
    # Validates: Requirements 2.6
    @given(
        namespace=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        entity_type=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        identifier=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=20)
    def test_property_cache_key_namespacing(self, namespace, entity_type, identifier):
        """
        Property 11: Cache key namespacing
        
        For any cache entry, the cache key should follow the namespacing pattern
        {namespace}:{entity_type}:{identifier} to prevent key collisions across
        different data types.
        
        Validates: Requirements 2.6
        """
        # Create fresh cache manager for each test
        cache_manager = CacheManager(redis_client=Mock())
        
        # Generate cache key
        key = cache_manager.generate_key(namespace, entity_type, identifier)
        
        # Verify format
        expected_pattern = f"{namespace}:{entity_type}:{identifier}"
        assert key == expected_pattern
        
        # Verify key starts with namespace and entity_type
        assert key.startswith(f"{namespace}:{entity_type}:")
        
        # Verify key components can be extracted (split with maxsplit to handle colons in identifier)
        parts = key.split(':', 2)  # Split only on first 2 colons
        assert len(parts) == 3
        assert parts[0] == namespace
        assert parts[1] == entity_type
        assert parts[2] == identifier
    
    # Property 10: Cache failure fallback
    # Validates: Requirements 2.5
    @given(
        key=st.text(min_size=1, max_size=50),
        namespace=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=10)
    def test_property_cache_failure_fallback(self, key, namespace):
        """
        Property 10: Cache failure fallback
        
        For any cache operation that fails (connection error, timeout), the system
        should fall back to database queries and continue serving requests without error.
        
        Validates: Requirements 2.5
        """
        # Create cache manager with failing Redis client
        failing_redis = Mock()
        failing_redis.get.side_effect = RedisError("Connection failed")
        failing_redis.setex.side_effect = RedisError("Connection failed")
        failing_redis.delete.side_effect = RedisError("Connection failed")
        failing_redis.keys.side_effect = RedisError("Connection failed")
        failing_redis.ping.side_effect = RedisError("Connection failed")
        
        cache_manager = CacheManager(redis_client=failing_redis)
        
        # Test get operation - should return None instead of raising exception
        result = cache_manager.get(key, namespace)
        assert result is None
        
        # Test set operation - should return False instead of raising exception
        result = cache_manager.set(key, {"data": "value"}, 3600, namespace)
        assert result is False
        
        # Test delete operation - should return False instead of raising exception
        result = cache_manager.delete(key, namespace)
        assert result is False
        
        # Test invalidate_pattern - should return 0 instead of raising exception
        result = cache_manager.invalidate_pattern("*", namespace)
        assert result == 0
        
        # Test ping - should return False instead of raising exception
        result = cache_manager.ping()
        assert result is False


# ============================================================================
# Integration Tests (with real Redis - optional, requires Redis running)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("REDIS_INTEGRATION_TESTS"),
    reason="Redis integration tests disabled. Set REDIS_INTEGRATION_TESTS=1 to enable."
)
class TestCacheManagerIntegration:
    """Integration tests with real Redis instance."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create CacheManager with real Redis connection."""
        # Use test database (db=15) to avoid conflicts
        from infrastructure.redis_client import RedisClient
        import redis
        
        test_redis = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        
        # Clear test database before each test
        test_redis.flushdb()
        
        cm = CacheManager(redis_client=test_redis)
        yield cm
        
        # Cleanup after test
        test_redis.flushdb()
        test_redis.close()
    
    def test_real_redis_set_get_delete(self, cache_manager):
        """Test basic operations with real Redis."""
        # Set value
        result = cache_manager.set("test_key", {"data": "value"}, ttl=60, namespace="test")
        assert result is True
        
        # Get value
        value = cache_manager.get("test_key", namespace="test")
        assert value == {"data": "value"}
        
        # Delete value
        result = cache_manager.delete("test_key", namespace="test")
        assert result is True
        
        # Verify deleted
        value = cache_manager.get("test_key", namespace="test")
        assert value is None
    
    def test_real_redis_ttl_expiration(self, cache_manager):
        """Test TTL expiration with real Redis."""
        # Set value with 2 second TTL
        cache_manager.set("expiring_key", {"data": "value"}, ttl=2, namespace="test")
        
        # Verify value exists
        value = cache_manager.get("expiring_key", namespace="test")
        assert value == {"data": "value"}
        
        # Wait for expiration
        time.sleep(3)
        
        # Verify value expired
        value = cache_manager.get("expiring_key", namespace="test")
        assert value is None
    
    def test_real_redis_pattern_invalidation(self, cache_manager):
        """Test pattern-based invalidation with real Redis."""
        # Set multiple keys
        cache_manager.set("user:1", {"name": "Alice"}, ttl=60, namespace="test")
        cache_manager.set("user:2", {"name": "Bob"}, ttl=60, namespace="test")
        cache_manager.set("post:1", {"title": "Post 1"}, ttl=60, namespace="test")
        
        # Invalidate user keys
        count = cache_manager.invalidate_pattern("user:*", namespace="test")
        assert count == 2
        
        # Verify user keys deleted
        assert cache_manager.get("user:1", namespace="test") is None
        assert cache_manager.get("user:2", namespace="test") is None
        
        # Verify post key still exists
        assert cache_manager.get("post:1", namespace="test") == {"title": "Post 1"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
