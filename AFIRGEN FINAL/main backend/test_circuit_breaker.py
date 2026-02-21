"""
Unit tests for circuit breaker implementation.

Tests the circuit breaker pattern implementation including:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure threshold behavior
- Recovery timeout behavior
- Half-open state testing
- Thread safety
- Statistics tracking

Validates: Requirements 6.3
"""

import pytest
import time
import threading
from infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
    circuit_breaker,
    get_circuit_breaker,
    get_all_circuit_breakers,
    reset_all_circuit_breakers
)


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes with correct defaults."""
        cb = CircuitBreaker("test")
        
        assert cb.name == "test"
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.half_open_max_calls == 3
        assert cb.get_state() == CircuitState.CLOSED
    
    def test_circuit_breaker_custom_parameters(self):
        """Test circuit breaker with custom parameters."""
        cb = CircuitBreaker(
            name="custom",
            failure_threshold=3,
            recovery_timeout=30,
            half_open_max_calls=2
        )
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.half_open_max_calls == 2
    
    def test_circuit_breaker_invalid_parameters(self):
        """Test circuit breaker rejects invalid parameters."""
        with pytest.raises(ValueError, match="failure_threshold must be >= 1"):
            CircuitBreaker("test", failure_threshold=0)
        
        with pytest.raises(ValueError, match="recovery_timeout must be >= 0"):
            CircuitBreaker("test", recovery_timeout=-1)
        
        with pytest.raises(ValueError, match="half_open_max_calls must be >= 1"):
            CircuitBreaker("test", half_open_max_calls=0)


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions."""
    
    def test_successful_calls_keep_circuit_closed(self):
        """Test that successful calls keep circuit in CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def success_func():
            return "success"
        
        # Make multiple successful calls
        for _ in range(10):
            result = cb.call(success_func)
            assert result == "success"
            assert cb.get_state() == CircuitState.CLOSED
    
    def test_circuit_opens_after_threshold_failures(self):
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def failing_func():
            raise Exception("Service unavailable")
        
        # First 3 calls should fail but pass through
        for i in range(3):
            with pytest.raises(Exception, match="Service unavailable"):
                cb.call(failing_func)
        
        # Circuit should now be open
        assert cb.get_state() == CircuitState.OPEN
        
        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(failing_func)
        
        assert exc_info.value.circuit_name == "test"
        assert exc_info.value.state == CircuitState.OPEN
    
    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)
        
        def failing_func():
            raise Exception("Failed")
        
        # Trigger circuit to open
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.get_state() == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Next call should transition to HALF_OPEN
        # (it will fail, but the state should change first)
        with pytest.raises(Exception):
            cb.call(failing_func)
        
        # Circuit should be back to OPEN after failure in HALF_OPEN
        assert cb.get_state() == CircuitState.OPEN
    
    def test_circuit_closes_after_successful_half_open_calls(self):
        """Test circuit closes after successful calls in HALF_OPEN state."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1, half_open_max_calls=2)
        
        call_count = [0]
        
        def sometimes_failing_func():
            call_count[0] += 1
            # Fail first 2 times, then succeed
            if call_count[0] <= 2:
                raise Exception("Failed")
            return "success"
        
        # Trigger circuit to open
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(sometimes_failing_func)
        
        assert cb.get_state() == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Next 2 calls should succeed and close the circuit
        result1 = cb.call(sometimes_failing_func)
        result2 = cb.call(sometimes_failing_func)
        
        assert result1 == "success"
        assert result2 == "success"
        assert cb.get_state() == CircuitState.CLOSED
    
    def test_circuit_reopens_on_failure_in_half_open(self):
        """Test circuit reopens if a call fails in HALF_OPEN state."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)
        
        def failing_func():
            raise Exception("Still failing")
        
        # Trigger circuit to open
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.get_state() == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Next call should fail and reopen circuit
        with pytest.raises(Exception):
            cb.call(failing_func)
        
        assert cb.get_state() == CircuitState.OPEN


class TestCircuitBreakerStatistics:
    """Test circuit breaker statistics tracking."""
    
    def test_statistics_track_calls(self):
        """Test that statistics track total calls."""
        cb = CircuitBreaker("test")
        
        def success_func():
            return "success"
        
        # Make some calls
        for _ in range(5):
            cb.call(success_func)
        
        stats = cb.get_stats()
        assert stats.total_calls == 5
        assert stats.total_successes == 5
        assert stats.total_failures == 0
    
    def test_statistics_track_failures(self):
        """Test that statistics track failures."""
        cb = CircuitBreaker("test", failure_threshold=10)
        
        def failing_func():
            raise Exception("Failed")
        
        # Make some failing calls
        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        stats = cb.get_stats()
        assert stats.total_calls == 3
        assert stats.total_successes == 0
        assert stats.total_failures == 3
        assert stats.failure_count == 3
    
    def test_statistics_track_last_failure_time(self):
        """Test that statistics track last failure time."""
        cb = CircuitBreaker("test")
        
        def failing_func():
            raise Exception("Failed")
        
        before = time.time()
        with pytest.raises(Exception):
            cb.call(failing_func)
        after = time.time()
        
        stats = cb.get_stats()
        assert stats.last_failure_time is not None
        assert before <= stats.last_failure_time <= after
    
    def test_statistics_to_dict(self):
        """Test statistics can be converted to dictionary."""
        cb = CircuitBreaker("test")
        
        def success_func():
            return "success"
        
        cb.call(success_func)
        
        stats_dict = cb.get_stats().to_dict()
        
        assert "state" in stats_dict
        assert "failure_count" in stats_dict
        assert "total_calls" in stats_dict
        assert "total_successes" in stats_dict
        assert "total_failures" in stats_dict
        assert stats_dict["state"] == "closed"
        assert stats_dict["total_calls"] == 1


class TestCircuitBreakerManualControl:
    """Test manual circuit breaker control."""
    
    def test_manual_reset(self):
        """Test manual reset of circuit breaker."""
        cb = CircuitBreaker("test", failure_threshold=2)
        
        def failing_func():
            raise Exception("Failed")
        
        # Trigger circuit to open
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.get_state() == CircuitState.OPEN
        
        # Manually reset
        cb.reset()
        
        assert cb.get_state() == CircuitState.CLOSED
        stats = cb.get_stats()
        assert stats.failure_count == 0
    
    def test_force_open(self):
        """Test forcing circuit breaker to OPEN state."""
        cb = CircuitBreaker("test")
        
        assert cb.get_state() == CircuitState.CLOSED
        
        # Force open
        cb.force_open()
        
        assert cb.get_state() == CircuitState.OPEN
        
        # Calls should be rejected
        def success_func():
            return "success"
        
        with pytest.raises(CircuitBreakerError):
            cb.call(success_func)


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator."""
    
    def test_decorator_basic_usage(self):
        """Test circuit breaker decorator works correctly."""
        @circuit_breaker("test_decorator", failure_threshold=2)
        def my_function(x):
            if x < 0:
                raise ValueError("Negative value")
            return x * 2
        
        # Successful calls
        assert my_function(5) == 10
        assert my_function(10) == 20
        
        # Failing calls
        with pytest.raises(ValueError):
            my_function(-1)
        with pytest.raises(ValueError):
            my_function(-2)
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            my_function(5)
    
    def test_decorator_attaches_circuit_breaker(self):
        """Test decorator attaches circuit breaker to function."""
        @circuit_breaker("test_attached", failure_threshold=3)
        def my_function():
            return "success"
        
        # Circuit breaker should be attached
        assert hasattr(my_function, 'circuit_breaker')
        assert isinstance(my_function.circuit_breaker, CircuitBreaker)
        assert my_function.circuit_breaker.name == "test_attached"


class TestCircuitBreakerRegistry:
    """Test global circuit breaker registry."""
    
    def test_get_circuit_breaker_creates_new(self):
        """Test get_circuit_breaker creates new instance."""
        cb = get_circuit_breaker("registry_test_1", failure_threshold=3)
        
        assert cb.name == "registry_test_1"
        assert cb.failure_threshold == 3
    
    def test_get_circuit_breaker_returns_existing(self):
        """Test get_circuit_breaker returns existing instance."""
        cb1 = get_circuit_breaker("registry_test_2", failure_threshold=5)
        cb2 = get_circuit_breaker("registry_test_2", failure_threshold=10)
        
        # Should return the same instance (first parameters used)
        assert cb1 is cb2
        assert cb1.failure_threshold == 5
    
    def test_get_all_circuit_breakers(self):
        """Test getting all circuit breakers from registry."""
        cb1 = get_circuit_breaker("registry_test_3")
        cb2 = get_circuit_breaker("registry_test_4")
        
        all_breakers = get_all_circuit_breakers()
        
        assert "registry_test_3" in all_breakers
        assert "registry_test_4" in all_breakers
        assert all_breakers["registry_test_3"] is cb1
        assert all_breakers["registry_test_4"] is cb2
    
    def test_reset_all_circuit_breakers(self):
        """Test resetting all circuit breakers."""
        cb1 = get_circuit_breaker("registry_test_5", failure_threshold=1)
        cb2 = get_circuit_breaker("registry_test_6", failure_threshold=1)
        
        def failing_func():
            raise Exception("Failed")
        
        # Open both circuits
        with pytest.raises(Exception):
            cb1.call(failing_func)
        with pytest.raises(Exception):
            cb2.call(failing_func)
        
        assert cb1.get_state() == CircuitState.OPEN
        assert cb2.get_state() == CircuitState.OPEN
        
        # Reset all
        reset_all_circuit_breakers()
        
        assert cb1.get_state() == CircuitState.CLOSED
        assert cb2.get_state() == CircuitState.CLOSED


class TestCircuitBreakerThreadSafety:
    """Test circuit breaker thread safety."""
    
    def test_concurrent_calls(self):
        """Test circuit breaker handles concurrent calls correctly."""
        cb = CircuitBreaker("concurrent_test", failure_threshold=10)
        results = []
        errors = []
        
        def success_func(value):
            time.sleep(0.01)  # Simulate some work
            return value * 2
        
        def worker(value):
            try:
                result = cb.call(success_func, value)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All calls should succeed
        assert len(results) == 20
        assert len(errors) == 0
        assert cb.get_state() == CircuitState.CLOSED
        
        stats = cb.get_stats()
        assert stats.total_calls == 20
        assert stats.total_successes == 20
    
    def test_concurrent_failures(self):
        """Test circuit breaker handles concurrent failures correctly."""
        cb = CircuitBreaker("concurrent_fail_test", failure_threshold=5)
        errors = []
        
        def failing_func():
            time.sleep(0.01)
            raise Exception("Failed")
        
        def worker():
            try:
                cb.call(failing_func)
            except Exception as e:
                errors.append(type(e).__name__)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Circuit should be open
        assert cb.get_state() == CircuitState.OPEN
        
        # Should have at least some Exception errors (the ones that triggered the circuit)
        assert "Exception" in errors
        # Note: Due to concurrent execution, CircuitBreakerError might not appear
        # if all threads started before the circuit opened
        assert len(errors) == 10


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases."""
    
    def test_success_resets_failure_count_in_closed_state(self):
        """Test that success resets failure count in CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def sometimes_failing(should_fail):
            if should_fail:
                raise Exception("Failed")
            return "success"
        
        # Fail twice
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(sometimes_failing, True)
        
        stats = cb.get_stats()
        assert stats.failure_count == 2
        
        # Succeed once
        cb.call(sometimes_failing, False)
        
        # Failure count should be reset
        stats = cb.get_stats()
        assert stats.failure_count == 0
    
    def test_circuit_breaker_with_specific_exception_type(self):
        """Test circuit breaker with specific exception type."""
        cb = CircuitBreaker("test", failure_threshold=2, expected_exception=ValueError)
        
        def value_error_func():
            raise ValueError("Invalid value")
        
        def type_error_func():
            raise TypeError("Invalid type")
        
        # ValueError should be caught
        with pytest.raises(ValueError):
            cb.call(value_error_func)
        
        # TypeError should not be caught (passes through)
        with pytest.raises(TypeError):
            cb.call(type_error_func)
        
        # Only ValueError should count towards threshold
        stats = cb.get_stats()
        assert stats.failure_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
