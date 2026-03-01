"""
Retry handler with exponential backoff and jitter.
Handles transient failures in AWS service calls.
"""

import asyncio
import logging
import random
from typing import Callable, Any, List, Type
from functools import wraps


logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Retry handler with exponential backoff and jitter.
    Retries on throttling and transient errors.
    """
    
    # Retryable error codes
    RETRYABLE_ERRORS = [
        'ThrottlingException',
        'ServiceUnavailable',
        'InternalServerError',
        'RequestTimeout',
        'TooManyRequestsException',
        'ProvisionedThroughputExceededException'
    ]
    
    # HTTP status codes to retry
    RETRYABLE_STATUS_CODES = [429, 500, 502, 503, 504]
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to delay
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            Function result
        
        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if error is retryable
                if not self._is_retryable(e):
                    logger.warning(f"Non-retryable error: {type(e).__name__}: {str(e)}")
                    raise
                
                # Check if we have retries left
                if attempt >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded")
                    raise
                
                # Calculate delay
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Retryable error on attempt {attempt + 1}/{self.max_retries + 1}: "
                    f"{type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # Should never reach here, but just in case
        raise last_exception
    
    def _is_retryable(self, exception: Exception) -> bool:
        """
        Check if exception is retryable.
        
        Args:
            exception: Exception to check
        
        Returns:
            True if retryable, False otherwise
        """
        # Check error code (for boto3 ClientError)
        if hasattr(exception, 'response'):
            error_code = exception.response.get('Error', {}).get('Code', '')
            if error_code in self.RETRYABLE_ERRORS:
                return True
            
            # Check HTTP status code
            status_code = exception.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
            if status_code in self.RETRYABLE_STATUS_CODES:
                return True
        
        # Check exception type
        exception_name = type(exception).__name__
        if exception_name in self.RETRYABLE_ERRORS:
            return True
        
        # Check for network errors
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * 2^attempt
        delay = self.base_delay * (2 ** attempt)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = random.uniform(0, delay * 0.1)  # Up to 10% jitter
            delay += jitter_amount
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        return delay


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """
    Decorator for adding retry logic to async functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            handler = RetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay
            )
            return await handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator
