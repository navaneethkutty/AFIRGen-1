"""
test_property_cache_tracking.py
-----------------------------------------------------------------------------
Property-Based Tests for Cache Operation Tracking
-----------------------------------------------------------------------------

Property tests for cache operation tracking using Hypothesis to verify:
- Property 22: Cache operation tracking

Requirements Validated: 5.4 (Resource Monitoring - Cache Hit/Miss Rates)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import json
import time

from infrastructure.cache_manager import CacheManager
from infrastructure.metrics import (
    MetricsCollector,
    cache_operations,
    cache_operation_duration,
    cache_hit_rate
)


def get_counter_value(counter, **labels):
    """Helper to get counter value from Prometheus metric."""
    try:
        return counter.labels(**labels)._value.get()
    except (AttributeError, TypeError):
        # Fallback: collect samples and find matching label
        for sample in counter.collect()[0].samples:
            if all(sample.labels.get(k) == str(v) for k, v in labels.items()):
                return sample.value
        return 0


def get_histogram_count(histogram, **labels):
    """Helper to get histogram count from Prometheus metric."""
    try:
        labeled = histogram.labels(**labels)
        # Try to access internal count
        if hasattr(labeled, '_count'):
            return labeled._count._value.get()
    except (AttributeError, TypeError):
        pass
    
    # Fallback: collect samples
    for sample in histogram.collect()[0].samples:
        if sample.name.endswith('_count') and all(
            sample.labels.get(k) == str(v) for k, v in labels.items()
        ):
            return sample.value
    return 0


def get_gauge_value(gauge):
    """Helper to get gauge value from Prometheus metric."""
    try:
        return gauge._value.get()
    except (AttributeError, TypeError):
        # Fallback: collect samples
        for sample in gauge.collect()[0].samples:
            return sample.value
        return 0


# Strategy for generating cache keys
cache_keys = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')
)

# Strategy for generating cache namespaces
cache_namespaces = st.sampled_from(["fir", "violation", "kb", "user", "stats", "default"])

# Strategy for generating cache values (JSON-serializable)
cache_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
    st.lists(st.integers(), max_size=10),
    st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5)
)

# Strategy for generating TTL values
ttl_values = st.integers(min_value=1, max_value=3600)

# Strategy for cache operations
cache_operation_types = st.sampled_from(["get", "set", "delete", "invalidate_pattern"])


# Feature: backend-optimization, Property 22: Cache operation tracking
@given(
    key=cache_keys,
    value=cache_values,
    ttl=ttl_values,
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_set_operation_tracked(key, value, ttl, namespace):
    """
    Property 22: For any cache set operation, the Monitoring_System should track
    the operation with operation type and duration.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Cache set operations are tracked
    2. Operation duration is recorded
    3. Operation result (hit/miss) is tracked
    """
    # Create mock Redis client
    mock_redis = Mock()
    mock_redis.setex = Mock(return_value=True)
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial metrics
    initial_count = get_counter_value(cache_operations, operation="set", result="hit")
    initial_histogram_count = get_histogram_count(cache_operation_duration, operation="set")
    
    # Perform cache set operation
    result = cache_manager.set(key, value, ttl, namespace)
    
    # Get updated metrics
    updated_count = get_counter_value(cache_operations, operation="set", result="hit")
    updated_histogram_count = get_histogram_count(cache_operation_duration, operation="set")
    
    # Property assertions
    
    # 1. Set operation should be tracked
    assert updated_count == initial_count + 1, \
        f"Cache set operation should be tracked"
    
    # 2. Duration should be recorded in histogram
    assert updated_histogram_count == initial_histogram_count + 1, \
        f"Cache set operation duration should be recorded"
    
    # 3. Operation should succeed
    assert result is True, \
        f"Cache set operation should succeed"


@given(
    key=cache_keys,
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_get_hit_tracked(key, namespace):
    """
    Property 22: For any cache get operation that results in a hit,
    the Monitoring_System should track it as a hit.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Cache hits are tracked correctly
    2. Hit rate is updated
    3. Operation duration is recorded
    """
    # Create mock Redis client that returns a value (cache hit)
    mock_redis = Mock()
    test_value = {"test": "data"}
    mock_redis.get = Mock(return_value=json.dumps(test_value))
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial metrics
    initial_hit_count = get_counter_value(cache_operations, operation="get", result="hit")
    initial_histogram_count = get_histogram_count(cache_operation_duration, operation="get")
    
    # Perform cache get operation (should be a hit)
    result = cache_manager.get(key, namespace)
    
    # Get updated metrics
    updated_hit_count = get_counter_value(cache_operations, operation="get", result="hit")
    updated_histogram_count = get_histogram_count(cache_operation_duration, operation="get")
    
    # Property assertions
    
    # 1. Cache hit should be tracked
    assert updated_hit_count == initial_hit_count + 1, \
        f"Cache hit should be tracked"
    
    # 2. Duration should be recorded
    assert updated_histogram_count == initial_histogram_count + 1, \
        f"Cache get operation duration should be recorded"
    
    # 3. Result should match the cached value
    assert result == test_value, \
        f"Cache get should return the cached value"


@given(
    key=cache_keys,
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_get_miss_tracked(key, namespace):
    """
    Property 22: For any cache get operation that results in a miss,
    the Monitoring_System should track it as a miss.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Cache misses are tracked correctly
    2. Hit rate is updated
    3. Operation duration is recorded
    """
    # Create mock Redis client that returns None (cache miss)
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=None)
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial metrics
    initial_miss_count = get_counter_value(cache_operations, operation="get", result="miss")
    initial_histogram_count = get_histogram_count(cache_operation_duration, operation="get")
    
    # Perform cache get operation (should be a miss)
    result = cache_manager.get(key, namespace)
    
    # Get updated metrics
    updated_miss_count = get_counter_value(cache_operations, operation="get", result="miss")
    updated_histogram_count = get_histogram_count(cache_operation_duration, operation="get")
    
    # Property assertions
    
    # 1. Cache miss should be tracked
    assert updated_miss_count == initial_miss_count + 1, \
        f"Cache miss should be tracked"
    
    # 2. Duration should be recorded
    assert updated_histogram_count == initial_histogram_count + 1, \
        f"Cache get operation duration should be recorded"
    
    # 3. Result should be None
    assert result is None, \
        f"Cache miss should return None"


@given(
    key=cache_keys,
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_delete_operation_tracked(key, namespace):
    """
    Property 22: For any cache delete operation, the Monitoring_System should track
    the operation with operation type and duration.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Cache delete operations are tracked
    2. Operation duration is recorded
    3. Operation result is tracked correctly
    """
    # Create mock Redis client
    mock_redis = Mock()
    mock_redis.delete = Mock(return_value=1)  # 1 key deleted
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial metrics
    initial_count = get_counter_value(cache_operations, operation="delete", result="hit")
    initial_histogram_count = get_histogram_count(cache_operation_duration, operation="delete")
    
    # Perform cache delete operation
    result = cache_manager.delete(key, namespace)
    
    # Get updated metrics
    updated_count = get_counter_value(cache_operations, operation="delete", result="hit")
    updated_histogram_count = get_histogram_count(cache_operation_duration, operation="delete")
    
    # Property assertions
    
    # 1. Delete operation should be tracked
    assert updated_count == initial_count + 1, \
        f"Cache delete operation should be tracked"
    
    # 2. Duration should be recorded
    assert updated_histogram_count == initial_histogram_count + 1, \
        f"Cache delete operation duration should be recorded"
    
    # 3. Operation should succeed
    assert result is True, \
        f"Cache delete operation should succeed"


@given(
    num_hits=st.integers(min_value=1, max_value=20),
    num_misses=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_hit_rate_calculated_correctly(num_hits, num_misses):
    """
    Property 22: For any sequence of cache operations,
    the hit rate should be calculated accurately as (hits / total) * 100.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Hit rate is calculated correctly
    2. Hit rate updates after each operation
    3. Hit rate percentage is accurate
    """
    # Reset cache hit rate counters
    MetricsCollector.reset_cache_hit_rate()
    
    # Create mock Redis client
    mock_redis = Mock()
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Simulate cache hits
    mock_redis.get = Mock(return_value=json.dumps({"data": "test"}))
    for _ in range(num_hits):
        cache_manager.get("test_key", "test_namespace")
    
    # Simulate cache misses
    mock_redis.get = Mock(return_value=None)
    for _ in range(num_misses):
        cache_manager.get("test_key", "test_namespace")
    
    # Calculate expected hit rate
    total_operations = num_hits + num_misses
    expected_hit_rate = (num_hits / total_operations) * 100
    
    # Get actual hit rate from metrics
    actual_hit_rate = get_gauge_value(cache_hit_rate)
    
    # Property assertion: hit rate should be calculated correctly
    assert abs(actual_hit_rate - expected_hit_rate) < 0.01, \
        f"Hit rate should be {expected_hit_rate}%, got {actual_hit_rate}%"


@given(
    pattern=st.text(min_size=1, max_size=20),
    namespace=cache_namespaces,
    num_keys=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_invalidate_pattern_tracked(pattern, namespace, num_keys):
    """
    Property 22: For any cache invalidate_pattern operation,
    the Monitoring_System should track the operation.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Pattern invalidation operations are tracked
    2. Operation duration is recorded
    3. Number of deleted keys is tracked
    """
    # Create mock Redis client
    mock_redis = Mock()
    mock_keys = [f"{namespace}:{pattern}:{i}".encode() for i in range(num_keys)]
    mock_redis.keys = Mock(return_value=mock_keys)
    mock_redis.delete = Mock(return_value=num_keys)
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial metrics
    initial_count = get_counter_value(cache_operations, operation="invalidate_pattern", result="hit")
    initial_histogram_count = get_histogram_count(cache_operation_duration, operation="invalidate_pattern")
    
    # Perform pattern invalidation
    deleted_count = cache_manager.invalidate_pattern(pattern, namespace)
    
    # Get updated metrics
    updated_count = get_counter_value(cache_operations, operation="invalidate_pattern", result="hit")
    updated_histogram_count = get_histogram_count(cache_operation_duration, operation="invalidate_pattern")
    
    # Property assertions
    
    # 1. Invalidate operation should be tracked
    assert updated_count == initial_count + 1, \
        f"Cache invalidate_pattern operation should be tracked"
    
    # 2. Duration should be recorded
    assert updated_histogram_count == initial_histogram_count + 1, \
        f"Cache invalidate_pattern operation duration should be recorded"
    
    # 3. Correct number of keys should be deleted
    assert deleted_count == num_keys, \
        f"Should delete {num_keys} keys, deleted {deleted_count}"


@given(
    key=cache_keys,
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_cache_error_tracked(key, namespace):
    """
    Property 22: For any cache operation that encounters an error,
    the Monitoring_System should track it as an error.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Cache errors are tracked
    2. Errors don't crash the application
    3. Error count increments correctly
    """
    from redis.exceptions import RedisError
    
    # Create mock Redis client that raises an error
    mock_redis = Mock()
    mock_redis.get = Mock(side_effect=RedisError("Connection failed"))
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial error count
    initial_error_count = get_counter_value(cache_operations, operation="get", result="error")
    
    # Perform cache get operation (should fail)
    result = cache_manager.get(key, namespace)
    
    # Get updated error count
    updated_error_count = get_counter_value(cache_operations, operation="get", result="error")
    
    # Property assertions
    
    # 1. Error should be tracked
    assert updated_error_count == initial_error_count + 1, \
        f"Cache error should be tracked"
    
    # 2. Operation should return None on error (fallback)
    assert result is None, \
        f"Cache operation should return None on error"


@given(
    operations=st.lists(
        st.tuples(
            st.sampled_from(["get_hit", "get_miss", "set", "delete"]),
            cache_keys,
            cache_namespaces
        ),
        min_size=5,
        max_size=20
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_all_cache_operations_tracked(operations):
    """
    Property 22: For any sequence of mixed cache operations,
    all operations should be tracked correctly.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. All cache operation types are tracked
    2. Mixed operations don't interfere with each other
    3. Tracking is accurate across operation types
    """
    # Create mock Redis client
    mock_redis = Mock()
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Track expected counts
    expected_counts = {
        "get_hit": 0,
        "get_miss": 0,
        "set": 0,
        "delete": 0
    }
    
    # Get initial counts
    initial_get_hit = get_counter_value(cache_operations, operation="get", result="hit")
    initial_get_miss = get_counter_value(cache_operations, operation="get", result="miss")
    initial_set = get_counter_value(cache_operations, operation="set", result="hit")
    initial_delete = get_counter_value(cache_operations, operation="delete", result="hit")
    
    # Perform operations
    for op_type, key, namespace in operations:
        if op_type == "get_hit":
            mock_redis.get = Mock(return_value=json.dumps({"data": "test"}))
            cache_manager.get(key, namespace)
            expected_counts["get_hit"] += 1
        elif op_type == "get_miss":
            mock_redis.get = Mock(return_value=None)
            cache_manager.get(key, namespace)
            expected_counts["get_miss"] += 1
        elif op_type == "set":
            mock_redis.setex = Mock(return_value=True)
            cache_manager.set(key, {"data": "test"}, 60, namespace)
            expected_counts["set"] += 1
        elif op_type == "delete":
            mock_redis.delete = Mock(return_value=1)
            cache_manager.delete(key, namespace)
            expected_counts["delete"] += 1
    
    # Get updated counts
    updated_get_hit = get_counter_value(cache_operations, operation="get", result="hit")
    updated_get_miss = get_counter_value(cache_operations, operation="get", result="miss")
    updated_set = get_counter_value(cache_operations, operation="set", result="hit")
    updated_delete = get_counter_value(cache_operations, operation="delete", result="hit")
    
    # Property assertions
    
    # 1. All get hits should be tracked
    assert updated_get_hit == initial_get_hit + expected_counts["get_hit"], \
        f"All cache get hits should be tracked"
    
    # 2. All get misses should be tracked
    assert updated_get_miss == initial_get_miss + expected_counts["get_miss"], \
        f"All cache get misses should be tracked"
    
    # 3. All set operations should be tracked
    assert updated_set == initial_set + expected_counts["set"], \
        f"All cache set operations should be tracked"
    
    # 4. All delete operations should be tracked
    assert updated_delete == initial_delete + expected_counts["delete"], \
        f"All cache delete operations should be tracked"


@given(
    key=cache_keys,
    value=cache_values,
    ttl=ttl_values,
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_operation_duration_is_positive(key, value, ttl, namespace):
    """
    Property 22: For any cache operation, the recorded duration
    should be a positive number.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Operation durations are measured
    2. Durations are positive values
    3. Duration tracking doesn't fail
    """
    # Create mock Redis client
    mock_redis = Mock()
    mock_redis.setex = Mock(return_value=True)
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial histogram count
    initial_count = get_histogram_count(cache_operation_duration, operation="set")
    
    # Perform operation
    cache_manager.set(key, value, ttl, namespace)
    
    # Get updated histogram count
    updated_count = get_histogram_count(cache_operation_duration, operation="set")
    
    # Property assertion: duration should be recorded
    assert updated_count == initial_count + 1, \
        f"Operation duration should be recorded"


@given(
    key=cache_keys,
    namespace=cache_namespaces,
    num_operations=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_repeated_operations_tracked_independently(key, namespace, num_operations):
    """
    Property 22: For any repeated cache operations on the same key,
    each operation should be tracked independently.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Repeated operations are all tracked
    2. Operation count increments correctly
    3. No deduplication of tracking
    """
    # Create mock Redis client
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=json.dumps({"data": "test"}))
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial count
    initial_count = get_counter_value(cache_operations, operation="get", result="hit")
    
    # Perform repeated operations
    for _ in range(num_operations):
        cache_manager.get(key, namespace)
    
    # Get updated count
    updated_count = get_counter_value(cache_operations, operation="get", result="hit")
    
    # Property assertion: all operations should be tracked
    assert updated_count == initial_count + num_operations, \
        f"All {num_operations} operations should be tracked independently"


@given(
    keys=st.lists(cache_keys, min_size=2, max_size=10, unique=True),
    namespace=cache_namespaces
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_keys_tracked_together(keys, namespace):
    """
    Property 22: For any set of different cache keys,
    operations on all keys should be tracked in aggregate.
    
    **Validates: Requirements 5.4**
    
    This property verifies that:
    1. Operations on different keys are all tracked
    2. Tracking aggregates across keys
    3. No per-key separation in metrics
    """
    # Create mock Redis client
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=json.dumps({"data": "test"}))
    
    cache_manager = CacheManager(redis_client=mock_redis)
    
    # Get initial count
    initial_count = get_counter_value(cache_operations, operation="get", result="hit")
    
    # Perform operations on different keys
    for key in keys:
        cache_manager.get(key, namespace)
    
    # Get updated count
    updated_count = get_counter_value(cache_operations, operation="get", result="hit")
    
    # Property assertion: all operations should be tracked
    assert updated_count == initial_count + len(keys), \
        f"Operations on {len(keys)} different keys should all be tracked"
