"""
Unit tests for CircuitBreaker.
Tests state transitions, failure thresholds, and recovery.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock

from services.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
    with_circuit_breaker
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker."""
    
    def test_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=3
        )
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60.0
        assert breaker.half_open_max_calls == 3
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test successful call in CLOSED state."""
        breaker = CircuitBreaker()
        mock_func = AsyncMock(return_value="success")
        
        result = await breaker.call(mock_func, "arg1", key="value")
        
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_transition_to_open_after_threshold(self):
        """Test circuit opens after failure threshold reached."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Fail threshold times
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 0  # Reset after opening
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self):
        """Test OPEN circuit rejects calls immediately."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Next call should be rejected without calling function
        call_count_before = mock_func.call_count
        
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(mock_func)
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
        assert mock_func.call_count == call_count_before  # Not called
    
    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(0.3)
        
        # Next call should transition to HALF_OPEN
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = await breaker.call(mock_func)
        
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_half_open_success_transitions_to_closed(self):
        """Test HALF_OPEN transitions to CLOSED after successful calls."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=3
        )
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait and transition to HALF_OPEN
        await asyncio.sleep(0.2)
        
        # Succeed half_open_max_calls times
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        for _ in range(3):
            await breaker.call(mock_func)
        
        # Should transition to CLOSED
        assert breaker.state == CircuitState.CLOSED
        assert breaker.success_count == 0  # Reset
    
    @pytest.mark.asyncio
    async def test_half_open_failure_transitions_to_open(self):
        """Test HALF_OPEN transitions back to OPEN on failure."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=3
        )
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait and transition to HALF_OPEN
        await asyncio.sleep(0.2)
        
        # First call succeeds
        mock_func.side_effect = None
        mock_func.return_value = "success"
        await breaker.call(mock_func)
        
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Second call fails - should transition back to OPEN
        mock_func.side_effect = Exception("Error")
        
        with pytest.raises(Exception):
            await breaker.call(mock_func)
        
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_closed_success_resets_failure_count(self):
        """Test success in CLOSED state resets failure count."""
        breaker = CircuitBreaker(failure_threshold=5)
        mock_func = AsyncMock()
        
        # Fail a few times
        mock_func.side_effect = Exception("Error")
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.failure_count == 3
        
        # Succeed once
        mock_func.side_effect = None
        mock_func.return_value = "success"
        await breaker.call(mock_func)
        
        # Failure count should reset
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_half_open_call_limit(self):
        """Test HALF_OPEN enforces max calls limit."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2
        )
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait and transition to HALF_OPEN
        await asyncio.sleep(0.2)
        
        # Make max_calls successful calls
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        await breaker.call(mock_func)
        await breaker.call(mock_func)
        
        # Circuit should now be CLOSED
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_get_state(self):
        """Test get_state returns current state info."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        state = breaker.get_state()
        
        assert state['state'] == 'closed'
        assert state['failure_count'] == 0
        assert state['success_count'] == 0
        assert state['time_until_retry'] is None
    
    @pytest.mark.asyncio
    async def test_get_state_when_open(self):
        """Test get_state includes time_until_retry when OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        state = breaker.get_state()
        
        assert state['state'] == 'open'
        assert state['time_until_retry'] is not None
        assert 0 <= state['time_until_retry'] <= 10.0
    
    @pytest.mark.asyncio
    async def test_time_until_retry_decreases(self):
        """Test time_until_retry decreases over time."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        time1 = breaker._time_until_retry()
        await asyncio.sleep(0.2)
        time2 = breaker._time_until_retry()
        
        assert time2 < time1
    
    @pytest.mark.asyncio
    async def test_with_circuit_breaker_decorator(self):
        """Test with_circuit_breaker decorator."""
        
        @with_circuit_breaker(failure_threshold=2, recovery_timeout=0.1)
        async def failing_function():
            if not hasattr(failing_function, 'call_count'):
                failing_function.call_count = 0
            failing_function.call_count += 1
            
            if failing_function.call_count <= 2:
                raise Exception("Error")
            return "success"
        
        # First two calls fail
        with pytest.raises(Exception):
            await failing_function()
        
        with pytest.raises(Exception):
            await failing_function()
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            await failing_function()
    
    @pytest.mark.asyncio
    async def test_multiple_failures_increment_count(self):
        """Test multiple failures increment failure count."""
        breaker = CircuitBreaker(failure_threshold=5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        for i in range(4):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
            assert breaker.failure_count == i + 1
        
        assert breaker.state == CircuitState.CLOSED
        
        # One more failure should open circuit
        with pytest.raises(Exception):
            await breaker.call(mock_func)
        
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_half_open_tracks_success_count(self):
        """Test HALF_OPEN tracks success count."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=3
        )
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait and transition to HALF_OPEN
        await asyncio.sleep(0.2)
        
        # Make successful calls
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        await breaker.call(mock_func)
        assert breaker.success_count == 1
        
        await breaker.call(mock_func)
        assert breaker.success_count == 2
        
        await breaker.call(mock_func)
        # Should transition to CLOSED and reset
        assert breaker.state == CircuitState.CLOSED
        assert breaker.success_count == 0
    
    @pytest.mark.asyncio
    async def test_exception_propagates_correctly(self):
        """Test original exception propagates through circuit breaker."""
        breaker = CircuitBreaker()
        
        class CustomError(Exception):
            pass
        
        mock_func = AsyncMock(side_effect=CustomError("Custom error"))
        
        with pytest.raises(CustomError) as exc_info:
            await breaker.call(mock_func)
        
        assert str(exc_info.value) == "Custom error"
    
    @pytest.mark.asyncio
    async def test_function_args_preserved(self):
        """Test function arguments are preserved through circuit breaker."""
        breaker = CircuitBreaker()
        mock_func = AsyncMock(return_value="success")
        
        result = await breaker.call(mock_func, "arg1", "arg2", key1="val1", key2="val2")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", key1="val1", key2="val2")
