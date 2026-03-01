"""
Unit tests for RetryHandler.
Tests retry logic, exponential backoff, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from botocore.exceptions import ClientError

from services.resilience.retry_handler import RetryHandler, with_retry


class TestRetryHandler:
    """Test suite for RetryHandler."""
    
    def test_initialization(self):
        """Test retry handler initializes with correct defaults."""
        handler = RetryHandler(max_retries=3, base_delay=1.0, max_delay=30.0)
        
        assert handler.max_retries == 3
        assert handler.base_delay == 1.0
        assert handler.max_delay == 30.0
        assert handler.jitter is True
    
    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test successful execution without retries."""
        handler = RetryHandler(max_retries=3)
        
        mock_func = AsyncMock(return_value="success")
        
        result = await handler.execute_with_retry(mock_func, "arg1", key="value")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", key="value")
    
    @pytest.mark.asyncio
    async def test_retry_on_throttling_error(self):
        """Test retry on throttling exception."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        mock_func = AsyncMock()
        mock_func.side_effect = [
            ClientError(
                {'Error': {'Code': 'ThrottlingException'}},
                'operation'
            ),
            "success"
        ]
        
        result = await handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """Test retry on 500 server error."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        mock_func = AsyncMock()
        error = ClientError(
            {
                'Error': {'Code': 'InternalServerError'},
                'ResponseMetadata': {'HTTPStatusCode': 500}
            },
            'operation'
        )
        mock_func.side_effect = [error, "success"]
        
        result = await handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self):
        """Test no retry on 4xx client errors (except 429)."""
        handler = RetryHandler(max_retries=3)
        
        mock_func = AsyncMock()
        error = ClientError(
            {
                'Error': {'Code': 'ValidationException'},
                'ResponseMetadata': {'HTTPStatusCode': 400}
            },
            'operation'
        )
        mock_func.side_effect = error
        
        with pytest.raises(ClientError):
            await handler.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Test exception raised when max retries exhausted."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        mock_func = AsyncMock()
        error = ClientError(
            {'Error': {'Code': 'ThrottlingException'}},
            'operation'
        )
        mock_func.side_effect = error
        
        with pytest.raises(ClientError):
            await handler.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        handler = RetryHandler(max_retries=3, base_delay=1.0, jitter=False)
        
        # Test delay calculation
        delay0 = handler._calculate_delay(0)
        delay1 = handler._calculate_delay(1)
        delay2 = handler._calculate_delay(2)
        
        assert delay0 == 1.0  # base * 2^0
        assert delay1 == 2.0  # base * 2^1
        assert delay2 == 4.0  # base * 2^2
    
    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        handler = RetryHandler(base_delay=10.0, max_delay=20.0, jitter=False)
        
        delay = handler._calculate_delay(5)  # Would be 10 * 2^5 = 320
        
        assert delay == 20.0  # Capped at max_delay
    
    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delay."""
        handler = RetryHandler(base_delay=1.0, jitter=True)
        
        delays = [handler._calculate_delay(1) for _ in range(10)]
        
        # All delays should be different due to jitter
        assert len(set(delays)) > 1
        
        # All delays should be around 2.0 (base * 2^1) with some variance
        for delay in delays:
            assert 2.0 <= delay <= 2.2  # Up to 10% jitter
    
    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Test retry on connection errors."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        mock_func = AsyncMock()
        mock_func.side_effect = [ConnectionError("Network error"), "success"]
        
        result = await handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """Test retry on timeout errors."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        mock_func = AsyncMock()
        mock_func.side_effect = [TimeoutError("Request timeout"), "success"]
        
        result = await handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_is_retryable_throttling_errors(self):
        """Test throttling errors are retryable."""
        handler = RetryHandler()
        
        retryable_codes = [
            'ThrottlingException',
            'TooManyRequestsException',
            'ProvisionedThroughputExceededException'
        ]
        
        for code in retryable_codes:
            error = ClientError({'Error': {'Code': code}}, 'operation')
            assert handler._is_retryable(error) is True
    
    @pytest.mark.asyncio
    async def test_is_retryable_server_errors(self):
        """Test server errors are retryable."""
        handler = RetryHandler()
        
        retryable_codes = [500, 502, 503, 504]
        
        for status_code in retryable_codes:
            error = ClientError(
                {
                    'Error': {'Code': 'InternalError'},
                    'ResponseMetadata': {'HTTPStatusCode': status_code}
                },
                'operation'
            )
            assert handler._is_retryable(error) is True
    
    @pytest.mark.asyncio
    async def test_is_not_retryable_client_errors(self):
        """Test client errors (except 429) are not retryable."""
        handler = RetryHandler()
        
        non_retryable_codes = [400, 401, 403, 404]
        
        for status_code in non_retryable_codes:
            error = ClientError(
                {
                    'Error': {'Code': 'ClientError'},
                    'ResponseMetadata': {'HTTPStatusCode': status_code}
                },
                'operation'
            )
            assert handler._is_retryable(error) is False
    
    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """Test with_retry decorator."""
        
        @with_retry(max_retries=2, base_delay=0.1)
        async def failing_function():
            if not hasattr(failing_function, 'call_count'):
                failing_function.call_count = 0
            failing_function.call_count += 1
            
            if failing_function.call_count < 2:
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException'}},
                    'operation'
                )
            return "success"
        
        result = await failing_function()
        
        assert result == "success"
        assert failing_function.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_with_args_and_kwargs(self):
        """Test retry preserves function arguments."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        mock_func = AsyncMock()
        mock_func.side_effect = [
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'op'),
            "success"
        ]
        
        result = await handler.execute_with_retry(
            mock_func,
            "arg1",
            "arg2",
            key1="value1",
            key2="value2"
        )
        
        assert result == "success"
        
        # Verify all calls had correct arguments
        for call in mock_func.call_args_list:
            assert call[0] == ("arg1", "arg2")
            assert call[1] == {"key1": "value1", "key2": "value2"}
    
    @pytest.mark.asyncio
    async def test_retry_delay_actually_waits(self):
        """Test that retry actually waits between attempts."""
        handler = RetryHandler(max_retries=2, base_delay=0.1, jitter=False)
        
        mock_func = AsyncMock()
        mock_func.side_effect = [
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'op'),
            "success"
        ]
        
        import time
        start = time.time()
        await handler.execute_with_retry(mock_func)
        elapsed = time.time() - start
        
        # Should have waited at least base_delay (0.1s)
        assert elapsed >= 0.1
