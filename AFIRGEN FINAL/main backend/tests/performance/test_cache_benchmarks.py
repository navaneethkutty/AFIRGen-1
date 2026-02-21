"""
Cache Performance Benchmarks

This module contains performance benchmarks for cache operations.
Tests measure cache hit rates, response time improvements, and cache under load.

Requirements: 9.3
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time
import random
import string

from infrastructure.performance_testing import (
    PerformanceTestFramework,
    TestType,
    PerformanceThreshold
)
from infrastructure.cache_manager import CacheManager


# Cache operation thresholds
CACHE_THRESHOLDS = {
    'cache_get_hit': PerformanceThreshold(
        max_p95_ms=5,  # Cache hits should be very fast
        max_p99_ms=10,
        min_throughput_ops=1000
    ),
    'cache_get_miss': PerformanceThreshold(
        max_p95_ms=10,  # Cache misses slightly slower
        max_p99_ms=20,
        min_throughput_ops=500
    ),
    'cache_set': PerformanceThreshold(
        max_p95_ms=10,  # Cache writes should be fast
        max_p99_ms=20,
        min_throughput_ops=500
    ),
    'cache_delete': PerformanceThreshold(
        max_p95_ms=10,
        max_p99_ms=20,
        min_throughput_ops=500
    ),
    'cache_get_or_fetch': PerformanceThreshold(
        max_p95_ms=50,  # Includes potential DB fetch
        max_p99_ms=100,
        min_throughput_ops=100
    )
}


@pytest.fixture
def performance_framework():
    """Create performance test framework"""
    return PerformanceTestFramework()


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis_client = Mock()
    
    # Mock cache storage
    cache_data = {}
    
    def mock_get(key):
        return cache_data.get(key)
    
    def mock_set(key, value, ex=None):
        cache_data[key] = value
        return True
    
    def mock_delete(key):
        if key in cache_data:
            del cache_data[key]
            return 1
        return 0
    
    def mock_exists(key):
        return 1 if key in cache_data else 0
    
    redis_client.get = Mock(side_effect=mock_get)
    redis_client.set = Mock(side_effect=mock_set)
    redis_client.delete = Mock(side_effect=mock_delete)
    redis_client.exists = Mock(side_effect=mock_exists)
    redis_client.ping = Mock(return_value=True)
    
    # Pre-populate some cache entries
    for i in range(100):
        cache_data[f'test:key:{i}'] = f'value_{i}'
    
    return redis_client


@pytest.fixture
def cache_manager(mock_redis):
    """Create cache manager with mock Redis"""
    with patch('infrastructure.cache_manager.redis.Redis', return_value=mock_redis):
        manager = CacheManager(host='localhost', port=6379)
        manager.redis = mock_redis
        return manager


class TestCacheOperationBenchmarks:
    """Performance benchmarks for basic cache operations"""
    
    def test_cache_get_hit_benchmark(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark cache GET operation with cache hit.
        
        This should be the fastest operation - data is in memory.
        """
        # Pre-populate cache
        cache_manager.set('benchmark:key', 'test_value', ttl=3600)
        
        def operation():
            result = cache_manager.get('benchmark:key')
            assert result is not None
        
        result = performance_framework.run_benchmark(
            test_name='cache_get_hit',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=500,
            threshold=CACHE_THRESHOLDS['cache_get_hit'],
            metadata={'operation': 'get', 'hit': True}
        )
        
        assert result.metrics.iterations == 500
        print(f"\nCache GET (hit) - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms, "
              f"Throughput: {result.metrics.throughput_ops_per_sec:.2f} ops/sec")
    
    def test_cache_get_miss_benchmark(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark cache GET operation with cache miss.
        
        Tests performance when key doesn't exist.
        """
        def operation():
            result = cache_manager.get('nonexistent:key')
            assert result is None
        
        result = performance_framework.run_benchmark(
            test_name='cache_get_miss',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=500,
            threshold=CACHE_THRESHOLDS['cache_get_miss'],
            metadata={'operation': 'get', 'hit': False}
        )
        
        assert result.metrics.iterations == 500
        print(f"\nCache GET (miss) - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_cache_set_benchmark(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark cache SET operation.
        
        Tests write performance to cache.
        """
        counter = {'value': 0}
        
        def operation():
            key = f'benchmark:set:{counter["value"]}'
            counter['value'] += 1
            result = cache_manager.set(key, f'value_{counter["value"]}', ttl=3600)
            assert result is True
        
        result = performance_framework.run_benchmark(
            test_name='cache_set',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=500,
            threshold=CACHE_THRESHOLDS['cache_set'],
            metadata={'operation': 'set'}
        )
        
        assert result.metrics.iterations == 500
        print(f"\nCache SET - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_cache_delete_benchmark(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark cache DELETE operation.
        
        Tests cache invalidation performance.
        """
        # Pre-populate keys
        for i in range(500):
            cache_manager.set(f'benchmark:delete:{i}', f'value_{i}', ttl=3600)
        
        counter = {'value': 0}
        
        def operation():
            key = f'benchmark:delete:{counter["value"]}'
            counter['value'] += 1
            cache_manager.delete(key)
        
        result = performance_framework.run_benchmark(
            test_name='cache_delete',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=500,
            threshold=CACHE_THRESHOLDS['cache_delete'],
            metadata={'operation': 'delete'}
        )
        
        assert result.metrics.iterations == 500
        print(f"\nCache DELETE - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_cache_get_or_fetch_hit_benchmark(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark get_or_fetch with cache hit.
        
        Tests cache-aside pattern when data is cached.
        """
        # Pre-populate cache
        cache_manager.set('benchmark:fetch', 'cached_value', ttl=3600)
        
        def fetch_fn():
            # Simulate database fetch
            time.sleep(0.01)  # 10ms simulated DB query
            return 'fetched_value'
        
        def operation():
            result = cache_manager.get_or_fetch(
                'benchmark:fetch',
                fetch_fn,
                ttl=3600
            )
            assert result == 'cached_value'  # Should return cached value
        
        result = performance_framework.run_benchmark(
            test_name='cache_get_or_fetch_hit',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=200,
            threshold=CACHE_THRESHOLDS['cache_get_hit'],
            metadata={'operation': 'get_or_fetch', 'hit': True}
        )
        
        assert result.metrics.iterations == 200
        print(f"\nCache get_or_fetch (hit) - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_cache_get_or_fetch_miss_benchmark(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark get_or_fetch with cache miss.
        
        Tests cache-aside pattern when data must be fetched.
        """
        counter = {'value': 0}
        
        def fetch_fn():
            # Simulate database fetch
            time.sleep(0.01)  # 10ms simulated DB query
            return f'fetched_value_{counter["value"]}'
        
        def operation():
            key = f'benchmark:fetch_miss:{counter["value"]}'
            counter['value'] += 1
            result = cache_manager.get_or_fetch(key, fetch_fn, ttl=3600)
            assert result is not None
        
        result = performance_framework.run_benchmark(
            test_name='cache_get_or_fetch_miss',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=100,
            threshold=CACHE_THRESHOLDS['cache_get_or_fetch'],
            metadata={'operation': 'get_or_fetch', 'hit': False}
        )
        
        assert result.metrics.iterations == 100
        print(f"\nCache get_or_fetch (miss) - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")


class TestCacheHitRateBenchmarks:
    """Benchmarks for cache hit rate analysis"""
    
    def test_cache_hit_rate_measurement(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Measure cache hit rate under realistic workload.
        
        Simulates 80% cache hit rate (typical for well-cached system).
        """
        # Pre-populate cache with 80% of keys
        for i in range(80):
            cache_manager.set(f'hitrate:key:{i}', f'value_{i}', ttl=3600)
        
        hits = 0
        misses = 0
        
        def operation():
            nonlocal hits, misses
            # 80% chance of hitting cached key
            key_id = random.randint(0, 99)
            result = cache_manager.get(f'hitrate:key:{key_id}')
            if result is not None:
                hits += 1
            else:
                misses += 1
        
        result = performance_framework.run_benchmark(
            test_name='cache_hit_rate_80pct',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=500,
            threshold=CACHE_THRESHOLDS['cache_get_hit'],
            metadata={'operation': 'hit_rate_test', 'expected_hit_rate': 0.80}
        )
        
        actual_hit_rate = hits / (hits + misses)
        print(f"\nCache Hit Rate Test:")
        print(f"  Hits: {hits}, Misses: {misses}")
        print(f"  Hit Rate: {actual_hit_rate:.2%}")
        print(f"  Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")
        
        # Verify hit rate is close to expected
        assert 0.75 <= actual_hit_rate <= 0.85, f"Hit rate {actual_hit_rate:.2%} outside expected range"
    
    def test_cache_performance_improvement(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Measure performance improvement from caching.
        
        Compares cached vs uncached response times.
        """
        def fetch_from_db():
            # Simulate database query
            time.sleep(0.05)  # 50ms DB query
            return 'db_value'
        
        # Test 1: Without cache (always fetch from DB)
        def operation_uncached():
            result = fetch_from_db()
            assert result is not None
        
        result_uncached = performance_framework.run_benchmark(
            test_name='uncached_fetch',
            test_type=TestType.CACHE_OPERATION,
            operation=operation_uncached,
            iterations=50,
            metadata={'cached': False}
        )
        
        # Test 2: With cache (cache hit)
        cache_manager.set('perf:comparison', 'cached_value', ttl=3600)
        
        def operation_cached():
            result = cache_manager.get('perf:comparison')
            assert result is not None
        
        result_cached = performance_framework.run_benchmark(
            test_name='cached_fetch',
            test_type=TestType.CACHE_OPERATION,
            operation=operation_cached,
            iterations=50,
            metadata={'cached': True}
        )
        
        # Calculate improvement
        improvement_pct = (
            (result_uncached.metrics.mean_time_ms - result_cached.metrics.mean_time_ms) /
            result_uncached.metrics.mean_time_ms * 100
        )
        
        print(f"\nCache Performance Improvement:")
        print(f"  Uncached Mean: {result_uncached.metrics.mean_time_ms:.2f}ms")
        print(f"  Cached Mean: {result_cached.metrics.mean_time_ms:.2f}ms")
        print(f"  Improvement: {improvement_pct:.1f}%")
        
        # Verify significant improvement
        assert improvement_pct > 50, "Cache should provide >50% improvement"


class TestCacheUnderLoad:
    """Benchmarks for cache performance under load"""
    
    def test_cache_concurrent_reads(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Test cache read performance under concurrent load.
        
        Simulates multiple concurrent cache reads.
        """
        # Pre-populate cache
        for i in range(100):
            cache_manager.set(f'concurrent:key:{i}', f'value_{i}', ttl=3600)
        
        def operation():
            key_id = random.randint(0, 99)
            result = cache_manager.get(f'concurrent:key:{key_id}')
            assert result is not None
        
        results = performance_framework.run_concurrent_benchmark(
            test_name='cache_concurrent_reads',
            operation=operation,
            concurrency_levels=[1, 5, 10, 20, 50],
            iterations_per_level=50,
            threshold=PerformanceThreshold(
                max_p95_ms=20,  # Allow higher latency under load
                max_error_rate=0.01
            ),
            metadata={'operation': 'concurrent_reads'}
        )
        
        print("\nCache Concurrent Read Results:")
        for result in results:
            concurrency = result.metrics.metadata['concurrency']
            print(f"  Concurrency {concurrency}: "
                  f"Mean={result.metrics.mean_time_ms:.2f}ms, "
                  f"P95={result.metrics.p95_time_ms:.2f}ms, "
                  f"Throughput={result.metrics.throughput_ops_per_sec:.2f} ops/sec")
    
    def test_cache_mixed_operations(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Test cache with mixed read/write operations.
        
        Simulates realistic workload with 80% reads, 20% writes.
        """
        counter = {'value': 0}
        
        def operation():
            # 80% reads, 20% writes
            if random.random() < 0.8:
                # Read operation
                key_id = random.randint(0, 99)
                cache_manager.get(f'mixed:key:{key_id}')
            else:
                # Write operation
                key_id = counter['value'] % 100
                counter['value'] += 1
                cache_manager.set(f'mixed:key:{key_id}', f'value_{counter["value"]}', ttl=3600)
        
        result = performance_framework.run_benchmark(
            test_name='cache_mixed_operations',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=500,
            threshold=PerformanceThreshold(
                max_p95_ms=15,
                max_p99_ms=30
            ),
            metadata={'operation': 'mixed', 'read_pct': 80, 'write_pct': 20}
        )
        
        assert result.metrics.iterations == 500
        print(f"\nCache Mixed Operations - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")


class TestCacheKeyNamespacing:
    """Benchmarks for cache key namespacing performance"""
    
    def test_namespaced_key_generation(
        self,
        performance_framework,
        cache_manager
    ):
        """
        Benchmark namespaced key generation performance.
        
        Tests overhead of key namespacing.
        """
        def operation():
            key = cache_manager.generate_key('fir', 'record', '12345')
            assert key == 'fir:record:12345'
        
        result = performance_framework.run_benchmark(
            test_name='namespaced_key_generation',
            test_type=TestType.CACHE_OPERATION,
            operation=operation,
            iterations=1000,
            threshold=PerformanceThreshold(
                max_p95_ms=1,  # Should be negligible overhead
                max_p99_ms=2
            ),
            metadata={'operation': 'key_generation'}
        )
        
        assert result.metrics.iterations == 1000
        print(f"\nNamespaced Key Generation - Mean: {result.metrics.mean_time_ms:.2f}ms, "
              f"P95: {result.metrics.p95_time_ms:.2f}ms")


def test_generate_cache_benchmark_report(performance_framework):
    """
    Generate comprehensive cache benchmark report.
    
    This test runs after all cache benchmarks to generate a report.
    """
    if performance_framework.results:
        report = performance_framework.generate_report(
            output_file='cache_benchmark_report.txt'
        )
        
        # Export JSON for CI/CD integration
        performance_framework.export_json('cache_benchmark_results.json')
        
        print("\n" + report)
        
        # Verify report was generated
        assert len(report) > 0
        assert 'PERFORMANCE TEST REPORT' in report


# Mark all tests as performance tests
pytestmark = pytest.mark.performance
