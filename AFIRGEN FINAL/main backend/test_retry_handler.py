"""
Unit tests for retry handler component.

Tests cover:
- Exponential backoff calculation
- Jitter application
- Retry logic with retryable exceptions
- Non-retryable exception handling
- Max retries enforcement
- Decorator functionality
"""

import pytest
import time
from unittest.mock import Mock, patch
from infrastructure.retry_handler import (
    RetryHandler,
    retry,
    get_retry_handler,
    NETWORK_EXCEPTIONS
)


class TestRetryHandlerInitialization:
    """Test RetryHandler initialization and validation."""
    
    def test_default_initialization(self):
        """Test RetryHandler with default parameters."""
        handler = RetryHandler()
        assert handler.max_retries == 3
        assert handler.base_delay == 1.0
        assert handler.max_delay == 60.0
        assert handler.exponential_base == 2.0
        assert handler.jitter is True
    
    def test_custom_initialization(self):
        """Test RetryHandler with custom parameters."""
        handler = RetryHandler(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False
        )
        assert handler.max_retries == 5
        assert handler.base_delay == 0.5
        assert handler.max_delay == 30.0
        assert handler.exponential_base == 3.0
        assert handler.jitter is False
    
    def test_invalid_max_retries(self):
        """Test that negative max_retries raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryHandler(max_retries=-1)
    
    def test_invalid_base_delay(self):
        """Test that non-positive base_delay raises ValueError."""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryHandler(base_delay=0)
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryHandler(base_delay=-1)
    
    def test_invalid_max_delay(self):
        """Test that max_delay < base_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryHandler(base_delay=10.0, max_delay=5.0)
    
    def test_invalid_exponential_base(self):
        """Test that exponential_base <= 1 raises ValueError."""
        with pytest.raises(ValueError, match="exponential_base must be > 1"):
            RetryHandler(exponential_base=1.0)
        with pytest.raises(ValueError, match="exponential_base must be > 1"):
            RetryHandler(exponential_base=0.5)


class TestDelayCalculation:
    """Test exponential backoff delay calculation."""
    
    def test_exponential_backoff_without_jitter(self):
        """Test exponential backoff calculation without jitter."""
        handler = RetryHandler(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        
        # First retry: 1.0 * (2^0) = 1.0
        assert handler.calculate_delay(0) == 1.0
        
        # Second retry: 1.0 * (2^1) = 2.0
        assert handler.calculate_delay(1) == 2.0
        
        # Third retry: 1.0 * (2^2) = 4.0
        assert handler.calculate_delay(2) == 4.0
        
        # Fourth retry: 1.0 * (2^3) = 8.0
        assert handler.calculate_delay(3) == 8.0
    
    def test_exponential_backoff_with_max_delay(self):
        """Test that delay is capped at max_delay."""
        handler = RetryHandler(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False
        )
        
        # First retry: 1.0 * (2^0) = 1.0 (under max)
        assert handler.calculate_delay(0) == 1.0
        
        # Second retry: 1.0 * (2^1) = 2.0 (under max)
        assert handler.calculate_delay(1) == 2.0
        
        # Third retry: 1.0 * (2^2) = 4.0 (under max)
        assert handler.calculate_delay(2) == 4.0
        
        # Fourth retry: 1.0 * (2^3) = 8.0 -> capped at 5.0
        assert handler.calculate_delay(3) == 5.0
        
        # Fifth retry: still capped at 5.0
        assert handler.calculate_delay(4) == 5.0
    
    def test_exponential_backoff_with_jitter(self):
        """Test that jitter is applied correctly."""
        handler = RetryHandler(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True
        )
        
        # Test multiple times to verify jitter randomness
        delays = [handler.calculate_delay(0) for _ in range(100)]
        
        # All delays should be in range [0.5, 1.5] for attempt 0
        # (base_delay=1.0, jitter range 0.5-1.5)
        assert all(0.5 <= d <= 1.5 for d in delays)
        
        # Delays should vary (not all the same)
        assert len(set(delays)) > 1
    
    def test_jitter_range(self):
        """Test that jitter is within expected range."""
        handler = RetryHandler(
            base_delay=10.0,
            exponential_base=2.0,
            jitter=True
        )
        
        # For attempt 0: base delay = 10.0
        # With jitter: 10.0 * [0.5, 1.5] = [5.0, 15.0]
        delays = [handler.calculate_delay(0) for _ in range(100)]
        assert all(5.0 <= d <= 15.0 for d in delays)
        
        # For attempt 1: base delay = 20.0
        # With jitter: 20.0 * [0.5, 1.5] = [10.0, 30.0]
        delays = [handler.calculate_delay(1) for _ in range(100)]
        assert all(10.0 <= d <= 30.0 for d in delays)
    
    def test_different_exponential_bases(self):
        """Test exponential backoff with different bases."""
        # Base 3
        handler = RetryHandler(
            base_delay=1.0,
            exponential_base=3.0,
            jitter=False
        )
        assert handler.calculate_delay(0) == 1.0  # 1.0 * (3^0)
        assert handler.calculate_delay(1) == 3.0  # 1.0 * (3^1)
        assert handler.calculate_delay(2) == 9.0  # 1.0 * (3^2)
        
        # Base 1.5
        handler = RetryHandler(
            base_delay=2.0,
            exponential_base=1.5,
            jitter=False
        )
        assert handler.calculate_delay(0) == 2.0  # 2.0 * (1.5^0)
        assert handler.calculate_delay(1) == 3.0  # 2.0 * (1.5^1)
        assert abs(handler.calculate_delay(2) - 4.5) < 0.01  # 2.0 * (1.5^2)


class TestRetryExecution:
    """Test retry execution logic."""
    
    def test_successful_execution_no_retry(self):
        """Test that successful execution doesn't retry."""
        handler = RetryHandler(max_retries=3)
        mock_func = Mock(return_value="success")
        
        result = handler.execute_with_retry(mock_func, (Exception,))
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_on_retryable_exception(self):
        """Test that retryable exceptions trigger retries."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            ConnectionError("Failed"),
            "success"
        ])
        
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_non_retryable_exception_raised_immediately(self):
        """Test that non-retryable exceptions are raised immediately."""
        handler = RetryHandler(max_retries=3)
        mock_func = Mock(side_effect=ValueError("Invalid input"))
        
        with pytest.raises(ValueError, match="Invalid input"):
            handler.execute_with_retry(
                mock_func,
                retryable_exceptions=(ConnectionError,)
            )
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_max_retries_exhausted(self):
        """Test that exception is raised after max retries."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        mock_func = Mock(side_effect=ConnectionError("Failed"))
        
        with pytest.raises(ConnectionError, match="Failed"):
            handler.execute_with_retry(
                mock_func,
                retryable_exceptions=(ConnectionError,)
            )
        
        # Should be called 3 times (initial + 2 retries)
        assert mock_func.call_count == 3
    
    def test_retry_with_function_arguments(self):
        """Test that function arguments are passed correctly."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        def test_func(a, b, c=None):
            if c is None:
                raise ValueError("c is required")
            return a + b + c
        
        result = handler.execute_with_retry(
            test_func,
            (ValueError,),
            1, 2, c=3
        )
        
        assert result == 6
    
    def test_retry_timing(self):
        """Test that retries respect delay timing."""
        handler = RetryHandler(
            max_retries=2,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False
        )
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            ConnectionError("Failed"),
            "success"
        ])
        
        start_time = time.time()
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
        elapsed_time = time.time() - start_time
        
        # Expected delays: 0.1 (first retry) + 0.2 (second retry) = 0.3
        # Allow some tolerance for execution time
        assert elapsed_time >= 0.3
        assert elapsed_time < 0.5
        assert result == "success"
    
    def test_multiple_retryable_exception_types(self):
        """Test retry with multiple exception types."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Network error"),
            TimeoutError("Timeout"),
            OSError("OS error"),
            "success"
        ])
        
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError)
        )
        
        assert result == "success"
        assert mock_func.call_count == 4


class TestIsRetryable:
    """Test is_retryable method with error classifier."""
    
    def test_retryable_exception(self):
        """Test that retryable exceptions are identified correctly."""
        handler = RetryHandler()
        
        # Using error classifier (automatic classification)
        assert handler.is_retryable(ConnectionError("Failed"))
        assert handler.is_retryable(TimeoutError("Timeout"))
        assert handler.is_retryable(OSError("OS error"))
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are identified correctly."""
        handler = RetryHandler()
        
        # Using error classifier (automatic classification)
        assert not handler.is_retryable(ValueError("Invalid"))
        assert not handler.is_retryable(KeyError("Not found"))
        assert not handler.is_retryable(TypeError("Type error"))


class TestRetryDecorator:
    """Test retry decorator."""
    
    def test_decorator_basic_usage(self):
        """Test basic decorator usage."""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.01, jitter=False, retryable_exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 3
    
    def test_decorator_with_arguments(self):
        """Test decorator with function arguments."""
        @retry(max_retries=1, base_delay=0.01, jitter=False, retryable_exceptions=(ValueError,))
        def add(a, b):
            return a + b
        
        result = add(2, 3)
        assert result == 5
    
    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        @retry(max_retries=1)
        def my_function():
            """This is my function."""
            return "result"
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "This is my function."


class TestFactoryFunction:
    """Test get_retry_handler factory function."""
    
    def test_factory_default_parameters(self):
        """Test factory function with default parameters."""
        handler = get_retry_handler()
        assert isinstance(handler, RetryHandler)
        assert handler.max_retries == 3
        assert handler.base_delay == 1.0
    
    def test_factory_custom_parameters(self):
        """Test factory function with custom parameters."""
        handler = get_retry_handler(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False
        )
        assert isinstance(handler, RetryHandler)
        assert handler.max_retries == 5
        assert handler.base_delay == 0.5
        assert handler.max_delay == 30.0
        assert handler.exponential_base == 3.0
        assert handler.jitter is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_max_retries(self):
        """Test with zero max retries (no retries)."""
        handler = RetryHandler(max_retries=0, base_delay=0.01)
        mock_func = Mock(side_effect=ConnectionError("Failed"))
        
        with pytest.raises(ConnectionError):
            handler.execute_with_retry(
                mock_func,
                retryable_exceptions=(ConnectionError,)
            )
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_very_small_base_delay(self):
        """Test with very small base delay."""
        handler = RetryHandler(
            max_retries=2,
            base_delay=0.001,
            jitter=False
        )
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            "success"
        ])
        
        start_time = time.time()
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        # Should complete very quickly
        assert elapsed_time < 0.1
    
    def test_empty_retryable_exceptions_tuple(self):
        """Test with empty retryable exceptions tuple."""
        handler = RetryHandler(max_retries=2, base_delay=0.01)
        mock_func = Mock(side_effect=ConnectionError("Failed"))
        
        # With empty tuple, no exceptions are retryable
        with pytest.raises(ConnectionError):
            handler.execute_with_retry(
                mock_func,
                retryable_exceptions=()
            )
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_exception_with_no_message(self):
        """Test handling exceptions with no message."""
        handler = RetryHandler(max_retries=1, base_delay=0.01, jitter=False)
        mock_func = Mock(side_effect=[ConnectionError(), "success"])
        
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
        
        assert result == "success"
        assert mock_func.call_count == 2


class TestNetworkExceptions:
    """Test predefined network exception constants."""
    
    def test_network_exceptions_tuple(self):
        """Test that NETWORK_EXCEPTIONS contains expected types."""
        assert ConnectionError in NETWORK_EXCEPTIONS
        assert TimeoutError in NETWORK_EXCEPTIONS
        assert OSError in NETWORK_EXCEPTIONS
    
    def test_retry_with_network_exceptions(self):
        """Test retry with predefined network exceptions."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Network error"),
            "success"
        ])
        
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=NETWORK_EXCEPTIONS
        )
        
        assert result == "success"
        assert mock_func.call_count == 2
