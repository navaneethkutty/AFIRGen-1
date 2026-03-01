"""
LRU cache for frequently accessed IPC sections.
Reduces embedding API calls by caching query results.
"""

import hashlib
import logging
from typing import List, Optional, Dict, Any
from collections import OrderedDict
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class CachedIPCResult:
    """Cached IPC section search result."""
    query_hash: str
    ipc_sections: List[Dict[str, Any]]
    hit_count: int = 0


class IPCCache:
    """
    LRU cache for IPC section search results.
    Implements least recently used eviction policy.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize IPC cache.
        
        Args:
            max_size: Maximum number of cached entries
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, CachedIPCResult] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, query_text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached IPC sections for query.
        
        Args:
            query_text: Query text to look up
        
        Returns:
            List of IPC sections if cached, None otherwise
        """
        query_hash = self._compute_hash(query_text)
        
        if query_hash in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(query_hash)
            
            # Update hit count
            cached_result = self.cache[query_hash]
            cached_result.hit_count += 1
            
            self.hits += 1
            logger.debug(f"Cache hit for query hash: {query_hash[:8]}...")
            
            return cached_result.ipc_sections
        
        self.misses += 1
        logger.debug(f"Cache miss for query hash: {query_hash[:8]}...")
        return None
    
    def put(self, query_text: str, ipc_sections: List[Dict[str, Any]]) -> None:
        """
        Store IPC sections in cache.
        
        Args:
            query_text: Query text
            ipc_sections: List of IPC sections to cache
        """
        query_hash = self._compute_hash(query_text)
        
        # If already exists, update and move to end
        if query_hash in self.cache:
            self.cache[query_hash].ipc_sections = ipc_sections
            self.cache.move_to_end(query_hash)
            logger.debug(f"Updated cache entry: {query_hash[:8]}...")
            return
        
        # Check if cache is full
        if len(self.cache) >= self.max_size:
            # Remove least recently used (first item)
            evicted_hash, evicted_result = self.cache.popitem(last=False)
            logger.debug(
                f"Evicted LRU entry: {evicted_hash[:8]}... "
                f"(hits: {evicted_result.hit_count})"
            )
        
        # Add new entry
        self.cache[query_hash] = CachedIPCResult(
            query_hash=query_hash,
            ipc_sections=ipc_sections
        )
        logger.debug(f"Added cache entry: {query_hash[:8]}...")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }
    
    def _compute_hash(self, text: str) -> str:
        """
        Compute stable hash for query text.
        
        Args:
            text: Input text
        
        Returns:
            SHA256 hash of normalized text
        """
        # Normalize text: lowercase, strip whitespace
        normalized = text.lower().strip()
        
        # Compute SHA256 hash
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
