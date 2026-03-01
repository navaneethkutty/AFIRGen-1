"""
Unit tests for IPCCache.
Tests LRU eviction, cache hits/misses, and statistics.
"""

import pytest
from services.cache.ipc_cache import IPCCache, CachedIPCResult


class TestIPCCache:
    """Test suite for IPCCache."""
    
    def test_cache_initialization(self):
        """Test cache initializes with correct defaults."""
        cache = IPCCache(max_size=100)
        
        assert cache.max_size == 100
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = IPCCache()
        
        result = cache.get("test query")
        
        assert result is None
        assert cache.misses == 1
        assert cache.hits == 0
    
    def test_cache_put_and_get(self):
        """Test putting and getting from cache."""
        cache = IPCCache()
        ipc_sections = [
            {'section_number': 'IPC 420', 'description': 'Cheating', 'penalty': '7 years'}
        ]
        
        cache.put("fraud case", ipc_sections)
        result = cache.get("fraud case")
        
        assert result == ipc_sections
        assert cache.hits == 1
        assert cache.misses == 0
    
    def test_cache_hit_increments_count(self):
        """Test cache hit increments hit count."""
        cache = IPCCache()
        ipc_sections = [
            {'section_number': 'IPC 302', 'description': 'Murder', 'penalty': 'Life'}
        ]
        
        cache.put("murder case", ipc_sections)
        
        # Multiple hits
        cache.get("murder case")
        cache.get("murder case")
        cache.get("murder case")
        
        assert cache.hits == 3
        # Get the hash to access the cache entry
        query_hash = cache._compute_hash("murder case")
        assert cache.cache[query_hash].hit_count == 3
    
    def test_cache_normalization(self):
        """Test query text normalization (lowercase, strip)."""
        cache = IPCCache()
        ipc_sections = [
            {'section_number': 'IPC 420', 'description': 'Cheating', 'penalty': '7 years'}
        ]
        
        cache.put("  Fraud Case  ", ipc_sections)
        
        # Different formatting should hit cache
        result1 = cache.get("fraud case")
        result2 = cache.get("FRAUD CASE")
        result3 = cache.get("  fraud case  ")
        
        assert result1 == ipc_sections
        assert result2 == ipc_sections
        assert result3 == ipc_sections
        assert cache.hits == 3
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = IPCCache(max_size=3)
        
        # Fill cache
        cache.put("query1", [{'section_number': 'IPC 1'}])
        cache.put("query2", [{'section_number': 'IPC 2'}])
        cache.put("query3", [{'section_number': 'IPC 3'}])
        
        assert len(cache.cache) == 3
        
        # Add one more - should evict query1 (least recently used)
        cache.put("query4", [{'section_number': 'IPC 4'}])
        
        assert len(cache.cache) == 3
        assert cache.get("query1") is None  # Evicted
        assert cache.get("query2") is not None
        assert cache.get("query3") is not None
        assert cache.get("query4") is not None
    
    def test_lru_access_updates_order(self):
        """Test accessing entry moves it to end (most recently used)."""
        cache = IPCCache(max_size=3)
        
        # Fill cache
        cache.put("query1", [{'section_number': 'IPC 1'}])
        cache.put("query2", [{'section_number': 'IPC 2'}])
        cache.put("query3", [{'section_number': 'IPC 3'}])
        
        # Access query1 to make it most recently used
        cache.get("query1")
        
        # Add query4 - should evict query2 (now least recently used)
        cache.put("query4", [{'section_number': 'IPC 4'}])
        
        assert cache.get("query1") is not None  # Still in cache
        assert cache.get("query2") is None  # Evicted
        assert cache.get("query3") is not None
        assert cache.get("query4") is not None
    
    def test_cache_update_existing_entry(self):
        """Test updating existing cache entry."""
        cache = IPCCache()
        
        # Initial put
        cache.put("query", [{'section_number': 'IPC 1'}])
        
        # Update with new data
        new_data = [{'section_number': 'IPC 2'}]
        cache.put("query", new_data)
        
        result = cache.get("query")
        assert result == new_data
        assert len(cache.cache) == 1  # Still only one entry
    
    def test_cache_clear(self):
        """Test clearing cache."""
        cache = IPCCache()
        
        # Add entries
        cache.put("query1", [{'section_number': 'IPC 1'}])
        cache.put("query2", [{'section_number': 'IPC 2'}])
        cache.get("query1")
        
        # Clear
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_get_stats(self):
        """Test cache statistics."""
        cache = IPCCache(max_size=100)
        
        # Add entries and access
        cache.put("query1", [{'section_number': 'IPC 1'}])
        cache.put("query2", [{'section_number': 'IPC 2'}])
        cache.get("query1")  # Hit
        cache.get("query1")  # Hit
        cache.get("query3")  # Miss
        
        stats = cache.get_stats()
        
        assert stats['size'] == 2
        assert stats['max_size'] == 100
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['total_requests'] == 3
        assert stats['hit_rate'] == 2/3
    
    def test_get_stats_empty_cache(self):
        """Test statistics for empty cache."""
        cache = IPCCache()
        
        stats = cache.get_stats()
        
        assert stats['size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['total_requests'] == 0
        assert stats['hit_rate'] == 0.0
    
    def test_hash_computation_stability(self):
        """Test hash computation is stable for same input."""
        cache = IPCCache()
        
        hash1 = cache._compute_hash("test query")
        hash2 = cache._compute_hash("test query")
        
        assert hash1 == hash2
    
    def test_hash_computation_different_inputs(self):
        """Test different inputs produce different hashes."""
        cache = IPCCache()
        
        hash1 = cache._compute_hash("query1")
        hash2 = cache._compute_hash("query2")
        
        assert hash1 != hash2
    
    def test_large_cache_operations(self):
        """Test cache with many entries."""
        cache = IPCCache(max_size=1000)
        
        # Add many entries
        for i in range(1500):
            cache.put(f"query{i}", [{'section_number': f'IPC {i}'}])
        
        # Should only have max_size entries
        assert len(cache.cache) == 1000
        
        # Oldest entries should be evicted
        assert cache.get("query0") is None
        assert cache.get("query499") is None
        
        # Recent entries should exist
        assert cache.get("query1499") is not None
        assert cache.get("query1000") is not None
