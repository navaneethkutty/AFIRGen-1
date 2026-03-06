"""
Standalone unit tests for RateLimiter class

Tests verify that the rate limiter:
- Limits requests to 100 per minute per IP address
- Uses in-memory storage for rate limit tracking
- Resets rate limit counters every minute
- Is thread-safe

Requirements: 21.1, 21.4, 21.5, 21.6
"""

import pytest
import time
import threading
from typing import Dict, List


# Standalone RateLimiter class for testing (copied from agentv5_clean.py)
class RateLimiter:
    """In-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if request is allowed"""
        with self.lock:
            now = time.time()
            
            # Initialize or clean up old requests
            if ip_address not in self.requests:
                self.requests[ip_address] = []
            
            # Remove requests older than 1 minute
            self.requests[ip_address] = [
                req_time for req_time in self.requests[ip_address]
                if now - req_time < 60
            ]
            
            # Check if limit exceeded
            if len(self.requests[ip_address]) >= self.requests_per_minute:
                return False
            
            # Add current request
            self.requests[ip_address].append(now)
            return True


@pytest.fixture
def rate_limiter():
    """Create fresh rate limiter instance for testing"""
    return RateLimiter(requests_per_minute=5)  # Lower limit for faster testing


class TestRateLimiterBasicFunctionality:
    """Test basic rate limiter functionality"""
    
    def test_allows_requests_under_limit(self, rate_limiter):
        """Test that requests under the limit are allowed
        
        Requirement 21.1: Limit requests to 100 per minute per IP address
        """
        ip = "192.168.1.1"
        
        # Should allow 5 requests
        for i in range(5):
            result = rate_limiter.is_allowed(ip)
            assert result is True, f"Request {i+1} should be allowed"
    
    def test_blocks_requests_over_limit(self, rate_limiter):
        """Test that requests over the limit are blocked
        
        Requirement 21.1: Limit requests to 100 per minute per IP address
        """
        ip = "192.168.1.2"
        
        # Allow 5 requests
        for i in range(5):
            rate_limiter.is_allowed(ip)
        
        # 6th request should be blocked
        result = rate_limiter.is_allowed(ip)
        assert result is False, "Request over limit should be blocked"
    
    def test_tracks_different_ips_separately(self, rate_limiter):
        """Test that different IPs are tracked separately
        
        Requirement 21.1: Limit requests to 100 per minute per IP address
        """
        ip1 = "192.168.1.3"
        ip2 = "192.168.1.4"
        
        # Use up limit for ip1
        for i in range(5):
            rate_limiter.is_allowed(ip1)
        
        # ip1 should be blocked
        assert rate_limiter.is_allowed(ip1) is False
        
        # ip2 should still be allowed
        assert rate_limiter.is_allowed(ip2) is True


class TestRateLimiterTimeBasedReset:
    """Test time-based reset functionality"""
    
    def test_resets_after_one_minute(self, rate_limiter):
        """Test that rate limit resets after 1 minute
        
        Requirement 21.6: Reset rate limit counters every minute
        """
        ip = "192.168.1.5"
        
        # Use up limit
        for i in range(5):
            rate_limiter.is_allowed(ip)
        
        # Should be blocked
        assert rate_limiter.is_allowed(ip) is False
        
        # Manually manipulate time by setting old requests
        rate_limiter.requests[ip] = [
            time.time() - 61  # Request from 61 seconds ago
        ]
        
        # Should be allowed again
        assert rate_limiter.is_allowed(ip) is True
    
    def test_cleanup_removes_old_requests(self, rate_limiter):
        """Test that old requests are properly cleaned up
        
        Requirement 21.6: Reset rate limit counters every minute
        """
        ip = "192.168.1.6"
        
        # Add mix of old and new requests
        now = time.time()
        rate_limiter.requests[ip] = [
            now - 70,  # Old (should be removed)
            now - 65,  # Old (should be removed)
            now - 30,  # Recent (should be kept)
            now - 10,  # Recent (should be kept)
        ]
        
        # Make a new request to trigger cleanup
        rate_limiter.is_allowed(ip)
        
        # Should only have recent requests plus the new one
        assert len(rate_limiter.requests[ip]) == 3
        assert all(now - req_time < 60 for req_time in rate_limiter.requests[ip])


class TestRateLimiterThreadSafety:
    """Test thread safety"""
    
    def test_thread_safety(self, rate_limiter):
        """Test that rate limiter is thread-safe"""
        ip = "192.168.1.7"
        results = []
        
        def make_request():
            results.append(rate_limiter.is_allowed(ip))
        
        # Create 10 threads making requests simultaneously
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 5 True and 5 False
        true_count = sum(results)
        assert true_count == 5, f"Expected 5 allowed requests, got {true_count}"


class TestRateLimiterRequirements:
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


class TestRateLimiterEdgeCases:
    """Test edge cases"""
    
    def test_empty_ip_address(self):
        """Test handling of empty IP address"""
        limiter = RateLimiter()
        
        # Should handle empty string
        assert limiter.is_allowed("") is True
    
    def test_multiple_ips_dont_interfere(self):
        """Test that multiple IPs don't interfere with each other"""
        limiter = RateLimiter(requests_per_minute=3)
        
        # Use up limit for multiple IPs
        for i in range(3):
            assert limiter.is_allowed("192.168.1.1") is True
        for i in range(3):
            assert limiter.is_allowed("192.168.1.2") is True
        for i in range(3):
            assert limiter.is_allowed("192.168.1.3") is True
        
        # All should be blocked now
        assert limiter.is_allowed("192.168.1.1") is False
        assert limiter.is_allowed("192.168.1.2") is False
        assert limiter.is_allowed("192.168.1.3") is False
    
    def test_zero_requests_per_minute(self):
        """Test with zero requests per minute (blocks all)"""
        limiter = RateLimiter(requests_per_minute=0)
        
        # Should block all requests
        assert limiter.is_allowed("192.168.1.1") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
