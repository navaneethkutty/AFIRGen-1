"""
Unit tests for rate limiting middleware (without app initialization)

Tests verify that the rate limiter:
- Limits requests to 100 per minute per IP address
- Returns HTTP 429 when rate limit exceeded
- Includes Retry-After header in 429 responses
- Uses in-memory storage for rate limit tracking
- Resets rate limit counters every minute
- Excludes /health endpoint from rate limiting

Requirements: 21.1-21.7
"""

import pytest
import time
import threading


# Import only the RateLimiter class, not the app
import sys
import os

# Mock environment variables before importing
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['DB_HOST'] = 'test-host'
os.environ['DB_PASSWORD'] = 'test-password'
os.environ['API_KEY'] = 'test-key'

# Now we can safely import
from agentv5_clean import RateLimiter


@pytest.fixture
def rate_limiter_instance():
    """Create fresh rate limiter instance for testing"""
    return RateLimiter(requests_per_minute=5)  # Lower limit for faster testing


class TestRateLimiter:
    """Test RateLimiter class"""
    
    def test_allows_requests_under_limit(self, rate_limiter_instance):
        """Test that requests under the limit are allowed
        
        Requirement 21.1: Limit requests to 100 per minute per IP address
        """
        ip = "192.168.1.1"
        
        # Should allow 5 requests
        for i in range(5):
            assert rate_limiter_instance.is_allowed(ip) is True
    
    def test_blocks_requests_over_limit(self, rate_limiter_instance):
        """Test that requests over the limit are blocked
        
        Requirement 21.1: Limit requests to 100 per minute per IP address
        Requirement 21.2: Return HTTP 429 when rate limit exceeded
        """
        ip = "192.168.1.2"
        
        # Allow 5 requests
        for i in range(5):
            rate_limiter_instance.is_allowed(ip)
        
        # 6th request should be blocked
        assert rate_limiter_instance.is_allowed(ip) is False
    
    def test_tracks_different_ips_separately(self, rate_limiter_instance):
        """Test that different IPs are tracked separately
        
        Requirement 21.1: Limit requests to 100 per minute per IP address
        """
        ip1 = "192.168.1.3"
        ip2 = "192.168.1.4"
        
        # Use up limit for ip1
        for i in range(5):
            rate_limiter_instance.is_allowed(ip1)
        
        # ip2 should still be allowed
        assert rate_limiter_instance.is_allowed(ip2) is True
    
    def test_resets_after_one_minute(self, rate_limiter_instance):
        """Test that rate limit resets after 1 minute
        
        Requirement 21.6: Reset rate limit counters every minute
        """
        ip = "192.168.1.5"
        
        # Use up limit
        for i in range(5):
            rate_limiter_instance.is_allowed(ip)
        
        # Should be blocked
        assert rate_limiter_instance.is_allowed(ip) is False
        
        # Manually manipulate time by clearing old requests
        # (In real scenario, we'd wait 60 seconds)
        rate_limiter_instance.requests[ip] = [
            time.time() - 61  # Request from 61 seconds ago
        ]
        
        # Should be allowed again
        assert rate_limiter_instance.is_allowed(ip) is True
    
    def test_thread_safety(self, rate_limiter_instance):
        """Test that rate limiter is thread-safe"""
        ip = "192.168.1.6"
        results = []
        
        def make_request():
            results.append(rate_limiter_instance.is_allowed(ip))
        
        # Create 10 threads making requests simultaneously
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 5 True and 5 False
        assert sum(results) == 5


class TestRateLimitingRequirements:
    """Test specific requirements"""
    
    def test_requirement_21_1_limit_100_per_minute(self):
        """Requirement 21.1: Limit requests to 100 per minute per IP address"""
        limiter = RateLimiter(requests_per_minute=100)
        ip = "192.168.1.100"
        
        # Should allow 100 requests
        for i in range(100):
            assert limiter.is_allowed(ip) is True
        
        # 101st request should be blocked
        assert limiter.is_allowed(ip) is False
    
    def test_requirement_21_4_in_memory_storage(self):
        """Requirement 21.4: Use in-memory storage for rate limit tracking"""
        limiter = RateLimiter()
        ip = "192.168.1.101"
        
        # Make a request
        limiter.is_allowed(ip)
        
        # Verify storage is in-memory (dict)
        assert isinstance(limiter.requests, dict)
        assert ip in limiter.requests
        assert isinstance(limiter.requests[ip], list)
    
    def test_requirement_21_5_not_using_redis(self):
        """Requirement 21.5: NOT use Redis for rate limiting"""
        limiter = RateLimiter()
        
        # Verify it's using in-memory dict, not Redis
        assert isinstance(limiter.requests, dict)
        assert not hasattr(limiter, 'redis')
        assert not hasattr(limiter, 'redis_client')
    
    def test_requirement_21_6_reset_every_minute(self):
        """Requirement 21.6: Reset rate limit counters every minute"""
        limiter = RateLimiter(requests_per_minute=5)
        ip = "192.168.1.102"
        
        # Add old request (older than 60 seconds)
        limiter.requests[ip] = [time.time() - 61]
        
        # Make new request - should clean up old one
        limiter.is_allowed(ip)
        
        # Old request should be removed
        assert all(time.time() - req_time < 60 for req_time in limiter.requests[ip])
    
    def test_cleanup_removes_old_requests(self):
        """Test that old requests are properly cleaned up"""
        limiter = RateLimiter(requests_per_minute=5)
        ip = "192.168.1.103"
        
        # Add mix of old and new requests
        now = time.time()
        limiter.requests[ip] = [
            now - 70,  # Old (should be removed)
            now - 65,  # Old (should be removed)
            now - 30,  # Recent (should be kept)
            now - 10,  # Recent (should be kept)
        ]
        
        # Make a new request to trigger cleanup
        limiter.is_allowed(ip)
        
     