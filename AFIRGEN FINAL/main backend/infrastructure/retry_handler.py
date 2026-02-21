"""
Retry handler component with exponential backoff and jitter.

This module provides a reusable retry mechanism for handling transient failures
with exponential backoff and jitter to prevent thundering herd problems.
"""

import time
import random
from typing import Callable, TypeVar, Tuple, Type, Optional, Any
from functools import wraps

from .error_classification import (
    ErrorClassifier,
    ErrorCategory,
    is_retryable_error,
    get_retryable_exceptions
)


T = TypeVar('T')


class RetryHandler:
    """
    Retry handler with exponential backoff and jitter.
    
    Implements retry logic for transient failures with:
    - Exponential backoff: delay = base_delay * (exponential_base ^ attempt)
    - Jitter: final_delay = delay * random(0.5, 1.5)
    - Configurable max retries and delays
    - Automatic error classification (retryable vs non-retryable)
    
    Validates: Requirements 6.1, 6.5
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        error_classifier: Optional[ErrorClassifier] = None
    ):
        """
        Initialize RetryHandler.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for first retry (default: 1.0)
            max_delay: Maximum delay in seconds between retries (default: 60.0)
            exponential_base: Base for exponential backoff calculation (default: 2.0)
            jitter: Whether to add jitter to prevent thundering herd (default: True)
            error_classifier: ErrorClassifier instance for error classification (default: None, uses default classifier)
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if max_delay < base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if exponential_base <= 1:
            raise ValueError("exponential_base must be > 1")
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.error_classifier = error_classifier or ErrorClassifier()
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt with exponential backoff and jitter.
        
        Formula:
        - Base delay: base_delay * (exponential_base ^ attempt)
        - With jitter: delay * random(0.5, 1.5)
        - Capped at max_delay
        
        Args:
            attempt: Current retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds
            
        Example:
            >>> handler = RetryHandler(base_delay=1.0, exponential_base=2.0)
            >>> handler.calculate_delay(0)  # First retry
            # Returns ~1.0 seconds (with jitter: 0.5-1.5)
            >>> handler.calculate_delay(1)  # Second retry
            # Returns ~2.0 seconds (with jitter: 1.0-3.0)
            >>> handler.calculate_delay(2)  # Third retry
            # Returns ~4.0 seconds (with jitter: 2.0-6.0)
        """
        # Calculate exponential backoff delay
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            # Jitter range: 0.5 to 1.5 of the delay
            jitter_factor = random.uniform(0.5, 1.5)
            delay = delay * jitter_factor
        
        return delay
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with retry logic.
        
        Retries the function on retryable exceptions with exponential backoff.
        Non-retryable exceptions are raised immediately.
        
        If retryable_exceptions is None, uses the error classifier to automatically
        determine if exceptions are retryable.
        
        Args:
            func: Function to execute
            retryable_exceptions: Optional tuple of exception types to retry on.
                                 If None, uses error classifier for automatic classification.
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func
            
        Returns:
            Result of successful function execution
            
        Raises:
            Exception: The last exception if all retries are exhausted,
                      or immediately if a non-retryable exception occurs
            
        Example:
            >>> handler = RetryHandler(max_retries=3)
            >>> # Automatic classification
            >>> result = handler.execute_with_retry(my_api_call, url="https://api.example.com")
            >>> # Manual classification
            >>> result = handler.execute_with_retry(
            ...     my_api_call,
            ...     retryable_exceptions=(ConnectionError, TimeoutError),
            ...     url="https://api.example.com"
            ... )
            
        Validates: Requirements 6.1, 6.5
        """
        last_exception = None
        use_classifier = retryable_exceptions is None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Attempt to execute the function
                return func(*args, **kwargs)
            except Exception as e:
                # Determine if exception is retryable
                if use_classifier:
                    # Use error classifier for automatic classification
                    if not self.error_classifier.is_retryable(e):
                        # Non-retryable exception - raise immediately
                        raise
                else:
                    # Use manual exception list
                    if not isinstance(e, retryable_exceptions):
                        # Non-retryable exception - raise immediately
                        raise
                
                last_exception = e
                
                # If this was the last attempt, raise the exception
                if attempt >= self.max_retries:
                    raise
                
                # Calculate delay and wait before retrying
                delay = self.calculate_delay(attempt)
                time.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry handler state")
    
    def is_retryable(self, exception: Exception) -> bool:
        """
        Check if an exception is retryable using the error classifier.
        
        Args:
            exception: Exception to check
            
        Returns:
            True if exception is retryable, False otherwise
            
        Example:
            >>> handler = RetryHandler()
            >>> handler.is_retryable(ConnectionError("Connection failed"))
            True
            >>> handler.is_retryable(ValueError("Invalid input"))
            False
            
        Validates: Requirements 6.5
        """
        return self.error_classifier.is_retryable(exception)
    
    def classify_error(self, exception: Exception) -> ErrorCategory:
        """
        Classify an exception using the error classifier.
        
        Args:
            exception: Exception to classify
            
        Returns:
            ErrorCategory indicating the classification
            
        Example:
            >>> handler = RetryHandler()
            >>> handler.classify_error(ConnectionError("Failed"))
            ErrorCategory.RETRYABLE
            >>> handler.classify_error(ValueError("Invalid"))
            ErrorCategory.NON_RETRYABLE
            
        Validates: Requirements 6.5
        """
        return self.error_classifier.classify(exception)


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    error_classifier: Optional[ErrorClassifier] = None
):
    """
    Decorator for adding retry logic to functions.
    
    If retryable_exceptions is None, uses error classifier for automatic
    error classification.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add jitter to prevent thundering herd
        retryable_exceptions: Optional tuple of exception types to retry on.
                             If None, uses error classifier.
        error_classifier: Optional ErrorClassifier instance
        
    Returns:
        Decorated function with retry logic
        
    Example:
        >>> # Automatic classification
        >>> @retry(max_retries=3)
        ... def fetch_data(url: str):
        ...     response = requests.get(url)
        ...     return response.json()
        >>> 
        >>> # Manual classification
        >>> @retry(max_retries=3, retryable_exceptions=(ConnectionError,))
        ... def fetch_data(url: str):
        ...     response = requests.get(url)
        ...     return response.json()
        
    Validates: Requirements 6.1, 6.5
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            handler = RetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                error_classifier=error_classifier
            )
            return handler.execute_with_retry(
                func,
                retryable_exceptions,
                *args,
                **kwargs
            )
        return wrapper
    return decorator


# Common retryable exception types
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

DATABASE_EXCEPTIONS = (
    # Add database-specific exceptions here
    # e.g., pymysql.err.OperationalError
)

REDIS_EXCEPTIONS = (
    # Add Redis-specific exceptions here
    # e.g., redis.exceptions.ConnectionError
)


def get_retry_handler(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    error_classifier: Optional[ErrorClassifier] = None
) -> RetryHandler:
    """
    Factory function to create a RetryHandler instance.
    
    Useful for dependency injection.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add jitter
        error_classifier: Optional ErrorClassifier instance
        
    Returns:
        RetryHandler instance
    """
    return RetryHandler(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        error_classifier=error_classifier
    )
