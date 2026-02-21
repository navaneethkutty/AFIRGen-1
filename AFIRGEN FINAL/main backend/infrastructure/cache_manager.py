"""
CacheManager component for Redis-based caching with TTL support.

This module provides a high-level caching interface with:
- Cache key generation with namespacing
- Get, set, delete operations with TTL support
- Cache invalidation by pattern matching
- Get-or-fetch pattern for cache-aside strategy
- Connection pooling via RedisClient

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.3
"""

import json
import hashlib
import time
from typing import Any, Optional, Callable, List
from redis import Redis
from redis.exceptions import RedisError
from .redis_client import get_redis_client
from .metrics import MetricsCollector
from interfaces.cache import ICacheManager


class CacheManager(ICacheManager):
    """
    Redis-based cache manager with namespacing and TTL support.
    
    Implements ICacheManager interface to ensure consistent caching patterns.
    Implements cache-aside pattern with automatic fallback on failures.
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.3
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize CacheManager.
        
        Args:
            redis_client: Optional Redis client instance. If None, uses default client.
        """
        self._redis = redis_client or get_redis_client()
    
    def generate_key(self, namespace: str, entity_type: str, identifier: str) -> str:
        """
        Generate cache key with namespacing pattern.
        
        Format: {namespace}:{entity_type}:{identifier}
        
        Args:
            namespace: Cache namespace (e.g., "fir", "violation", "kb")
            entity_type: Entity type (e.g., "record", "check", "query")
            identifier: Unique identifier for the entity
            
        Returns:
            Formatted cache key string
            
        Example:
            >>> cm = CacheManager()
            >>> cm.generate_key("fir", "record", "12345")
            'fir:record:12345'
        """
        return f"{namespace}:{entity_type}:{identifier}"
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (will be namespaced)
            namespace: Cache namespace
            
        Returns:
            Cached value if exists and not expired, None otherwise
            
        Validates: Requirements 2.2, 5.4
        """
        start_time = time.time()
        try:
            full_key = f"{namespace}:{key}" if not key.startswith(f"{namespace}:") else key
            value = self._redis.get(full_key)
            
            duration = time.time() - start_time
            
            if value is None:
                # Cache miss
                MetricsCollector.record_cache_operation("get", hit=False, duration=duration)
                return None
            
            # Deserialize JSON value
            result = json.loads(value)
            
            # Cache hit
            MetricsCollector.record_cache_operation("get", hit=True, duration=duration)
            return result
        except RedisError:
            # Cache error
            duration = time.time() - start_time
            MetricsCollector.record_cache_error("get")
            return None
        except (json.JSONDecodeError, TypeError):
            # Invalid cached data, count as miss
            duration = time.time() - start_time
            MetricsCollector.record_cache_operation("get", hit=False, duration=duration)
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int,
        namespace: str = "default"
    ) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key (will be namespaced)
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
            
        Validates: Requirements 2.1, 5.4
        """
        start_time = time.time()
        try:
            full_key = f"{namespace}:{key}" if not key.startswith(f"{namespace}:") else key
            
            # Serialize value to JSON
            serialized_value = json.dumps(value)
            
            # Set with TTL
            self._redis.setex(full_key, ttl, serialized_value)
            
            duration = time.time() - start_time
            MetricsCollector.record_cache_operation("set", hit=True, duration=duration)
            return True
        except (RedisError, TypeError, ValueError):
            # Fallback: return False on cache failure
            duration = time.time() - start_time
            MetricsCollector.record_cache_error("set")
            return False
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key (will be namespaced)
            namespace: Cache namespace
            
        Returns:
            True if key was deleted, False otherwise
            
        Validates: Requirements 5.4
        """
        start_time = time.time()
        try:
            full_key = f"{namespace}:{key}" if not key.startswith(f"{namespace}:") else key
            result = self._redis.delete(full_key)
            
            duration = time.time() - start_time
            MetricsCollector.record_cache_operation("delete", hit=(result > 0), duration=duration)
            return result > 0
        except RedisError:
            # Fallback: return False on cache failure
            duration = time.time() - start_time
            MetricsCollector.record_cache_error("delete")
            return False
    
    def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports Redis glob-style patterns)
            namespace: Cache namespace
            
        Returns:
            Number of keys deleted
            
        Example:
            >>> cm = CacheManager()
            >>> cm.invalidate_pattern("user:*", "fir")
            5  # Deleted 5 keys matching fir:user:*
            
        Validates: Requirements 2.4, 5.4
        """
        start_time = time.time()
        try:
            full_pattern = f"{namespace}:{pattern}"
            
            # Find all keys matching pattern
            keys = self._redis.keys(full_pattern)
            
            if not keys:
                duration = time.time() - start_time
                MetricsCollector.record_cache_operation("invalidate_pattern", hit=False, duration=duration)
                return 0
            
            # Delete all matching keys
            deleted_count = self._redis.delete(*keys)
            
            duration = time.time() - start_time
            MetricsCollector.record_cache_operation("invalidate_pattern", hit=True, duration=duration)
            return deleted_count
        except RedisError:
            # Fallback: return 0 on cache failure
            duration = time.time() - start_time
            MetricsCollector.record_cache_error("invalidate_pattern")
            return 0

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        ttl: int,
        namespace: str = "default"
    ) -> Any:
        """
        Get value from cache or fetch from source if not cached (cache-aside pattern).
        
        This implements the cache-aside strategy:
        1. Try to get value from cache
        2. If cache miss, call fetch_fn to get value from source
        3. Store fetched value in cache with TTL
        4. Return the value
        
        Args:
            key: Cache key (will be namespaced)
            fetch_fn: Function to call if cache miss (should return the value)
            ttl: Time-to-live in seconds for cached value
            namespace: Cache namespace
            
        Returns:
            Cached or fetched value
            
        Example:
            >>> def fetch_user(user_id):
            ...     return db.query(User).filter_by(id=user_id).first()
            >>> 
            >>> cm = CacheManager()
            >>> user = cm.get_or_fetch(
            ...     key="user:123",
            ...     fetch_fn=lambda: fetch_user(123),
            ...     ttl=3600,
            ...     namespace="fir"
            ... )
            
        Validates: Requirements 2.3
        """
        # Try to get from cache first
        cached_value = self.get(key, namespace)
        
        if cached_value is not None:
            return cached_value
        
        # Cache miss - fetch from source
        try:
            fetched_value = fetch_fn()
            
            # Store in cache for future requests
            self.set(key, fetched_value, ttl, namespace)
            
            return fetched_value
        except Exception:
            # If fetch fails, re-raise the exception
            # (don't silently fail - caller should handle)
            raise
    
    def exists(self, key: str, namespace: str = "default") -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key (will be namespaced)
            namespace: Cache namespace
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            full_key = f"{namespace}:{key}" if not key.startswith(f"{namespace}:") else key
            return self._redis.exists(full_key) > 0
        except RedisError:
            return False
    
    def get_ttl(self, key: str, namespace: str = "default") -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key (will be namespaced)
            namespace: Cache namespace
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist or has no TTL
        """
        try:
            full_key = f"{namespace}:{key}" if not key.startswith(f"{namespace}:") else key
            ttl = self._redis.ttl(full_key)
            
            # Redis returns -2 if key doesn't exist, -1 if no TTL
            if ttl < 0:
                return None
            
            return ttl
        except RedisError:
            return None
    
    def set_multiple(
        self,
        items: List[tuple[str, Any, int]],
        namespace: str = "default"
    ) -> int:
        """
        Set multiple cache entries at once.
        
        Args:
            items: List of (key, value, ttl) tuples
            namespace: Cache namespace
            
        Returns:
            Number of items successfully cached
        """
        success_count = 0
        
        for key, value, ttl in items:
            if self.set(key, value, ttl, namespace):
                success_count += 1
        
        return success_count
    
    def get_multiple(
        self,
        keys: List[str],
        namespace: str = "default"
    ) -> dict[str, Any]:
        """
        Get multiple cache entries at once.
        
        Args:
            keys: List of cache keys
            namespace: Cache namespace
            
        Returns:
            Dictionary mapping keys to their values (only includes existing keys)
        """
        result = {}
        
        for key in keys:
            value = self.get(key, namespace)
            if value is not None:
                result[key] = value
        
        return result
    
    def flush_namespace(self, namespace: str) -> int:
        """
        Delete all keys in a namespace.
        
        Args:
            namespace: Cache namespace to flush
            
        Returns:
            Number of keys deleted
        """
        return self.invalidate_pattern("*", namespace)
    
    def ping(self) -> bool:
        """
        Check if Redis connection is alive.
        
        Returns:
            True if connection is alive, False otherwise
        """
        try:
            return self._redis.ping()
        except RedisError:
            return False
    
    def get_memory_usage(self) -> Optional[int]:
        """
        Get Redis memory usage in bytes.
        
        Returns:
            Memory usage in bytes, or None if unavailable
            
        Validates: Requirements 5.4
        """
        try:
            info = self._redis.info('memory')
            return info.get('used_memory', None)
        except RedisError:
            return None
    
    def update_cache_metrics(self):
        """
        Update cache-related metrics (memory usage).
        
        This should be called periodically to update gauge metrics.
        
        Validates: Requirements 5.4
        """
        try:
            # Update memory usage
            memory_usage = self.get_memory_usage()
            if memory_usage is not None:
                from .metrics import cache_memory_usage
                cache_memory_usage.set(memory_usage)
        except Exception:
            # Silently fail if metrics cannot be updated
            pass


# Convenience function for dependency injection
def get_cache_manager() -> CacheManager:
    """Get CacheManager instance for dependency injection."""
    return CacheManager()
