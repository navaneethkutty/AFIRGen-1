"""
Cache Interface

Defines the abstract base class for cache manager implementations.
All cache implementations should inherit from this interface to ensure
consistent caching patterns across the application.

Requirements: 8.3 - Define clear interfaces for cache interactions
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable, List


class ICacheManager(ABC):
    """
    Abstract base class for cache manager implementations.
    
    This interface defines the contract for caching operations including:
    - Get/Set/Delete operations with TTL support
    - Cache key generation with namespacing
    - Pattern-based invalidation
    - Cache-aside pattern (get-or-fetch)
    - Batch operations
    
    All concrete cache implementations must implement these methods
    to ensure consistent caching behavior.
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace for key isolation
        
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        pass
    
    @abstractmethod
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
            key: Cache key
            value: Value to cache (must be serializable)
            ttl: Time-to-live in seconds
            namespace: Cache namespace for key isolation
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, key: str, namespace: str = "default") -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
        
        Returns:
            True if key was deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, key: str, namespace: str = "default") -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
        
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_ttl(self, key: str, namespace: str = "default") -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            namespace: Cache namespace
        
        Returns:
            Remaining TTL in seconds, None if key doesn't exist or has no TTL
        """
        pass
    
    @abstractmethod
    def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports glob-style patterns like "user:*")
            namespace: Cache namespace
        
        Returns:
            Number of keys deleted
        """
        pass
    
    @abstractmethod
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
            key: Cache key
            fetch_fn: Function to call if cache miss (should return the value)
            ttl: Time-to-live in seconds for cached value
            namespace: Cache namespace
        
        Returns:
            Cached or fetched value
        """
        pass
    
    @abstractmethod
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
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def flush_namespace(self, namespace: str) -> int:
        """
        Delete all keys in a namespace.
        
        Args:
            namespace: Cache namespace to flush
        
        Returns:
            Number of keys deleted
        """
        pass
    
    @abstractmethod
    def ping(self) -> bool:
        """
        Check if cache connection is alive.
        
        Returns:
            True if connection is alive, False otherwise
        """
        pass


class ICacheInvalidationStrategy(ABC):
    """
    Abstract base class for cache invalidation strategies.
    
    This interface allows different invalidation strategies to be implemented
    and injected into repositories or services.
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def invalidate_for_entity(
        self,
        cache_manager: ICacheManager,
        entity_id: Any,
        namespace: str
    ) -> None:
        """
        Invalidate cache entries for a specific entity.
        
        Args:
            cache_manager: Cache manager instance
            entity_id: Entity identifier
            namespace: Cache namespace
        """
        pass
    
    @abstractmethod
    def get_invalidation_patterns(self, entity_id: Any) -> List[str]:
        """
        Get cache key patterns to invalidate for an entity.
        
        Args:
            entity_id: Entity identifier
        
        Returns:
            List of cache key patterns to invalidate
        """
        pass
