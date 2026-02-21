"""
Error classification system for distinguishing retryable and non-retryable errors.

This module provides a comprehensive error classification system that categorizes
exceptions into retryable (transient) and non-retryable (permanent) errors.

Validates: Requirements 6.5
"""

from typing import Type, Tuple, Set
from enum import Enum


class ErrorCategory(Enum):
    """
    Error category classification.
    
    Categories:
    - RETRYABLE: Transient errors that may succeed on retry
    - NON_RETRYABLE: Permanent errors that will not succeed on retry
    - CRITICAL: Errors requiring immediate attention
    """
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    CRITICAL = "critical"


class ErrorClassifier:
    """
    Classifies exceptions into retryable and non-retryable categories.
    
    Provides methods to:
    - Classify exceptions by type
    - Get retryable exception types
    - Get non-retryable exception types
    - Register custom exception classifications
    
    Validates: Requirements 6.5
    """
    
    # Retryable exceptions (transient errors)
    RETRYABLE_EXCEPTIONS: Set[Type[Exception]] = {
        # Network errors
        ConnectionError,
        TimeoutError,
        OSError,
        
        # Add more as needed based on actual dependencies
        # These will be populated when the actual libraries are imported
    }
    
    # Non-retryable exceptions (permanent errors)
    NON_RETRYABLE_EXCEPTIONS: Set[Type[Exception]] = {
        # Validation errors
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        
        # Logic errors
        AssertionError,
        NotImplementedError,
        
        # Add more as needed
    }
    
    # Critical exceptions (require immediate attention)
    CRITICAL_EXCEPTIONS: Set[Type[Exception]] = {
        MemoryError,
        SystemError,
        RecursionError,
    }
    
    def __init__(self):
        """Initialize ErrorClassifier with default exception mappings."""
        # Create mutable copies for instance-level customization
        self._retryable = self.RETRYABLE_EXCEPTIONS.copy()
        self._non_retryable = self.NON_RETRYABLE_EXCEPTIONS.copy()
        self._critical = self.CRITICAL_EXCEPTIONS.copy()
    
    def classify(self, exception: Exception) -> ErrorCategory:
        """
        Classify an exception into a category.
        
        Args:
            exception: Exception instance to classify
            
        Returns:
            ErrorCategory indicating the classification
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> classifier.classify(ConnectionError("Network failed"))
            ErrorCategory.RETRYABLE
            >>> classifier.classify(ValueError("Invalid input"))
            ErrorCategory.NON_RETRYABLE
            
        Validates: Requirements 6.5
        """
        exception_type = type(exception)
        
        # Check critical first (highest priority)
        if self._is_type_in_set(exception_type, self._critical):
            return ErrorCategory.CRITICAL
        
        # Check retryable
        if self._is_type_in_set(exception_type, self._retryable):
            return ErrorCategory.RETRYABLE
        
        # Check non-retryable
        if self._is_type_in_set(exception_type, self._non_retryable):
            return ErrorCategory.NON_RETRYABLE
        
        # Default to non-retryable for unknown exceptions (fail-safe)
        return ErrorCategory.NON_RETRYABLE
    
    def is_retryable(self, exception: Exception) -> bool:
        """
        Check if an exception is retryable.
        
        Args:
            exception: Exception instance to check
            
        Returns:
            True if exception is retryable, False otherwise
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> classifier.is_retryable(ConnectionError("Failed"))
            True
            >>> classifier.is_retryable(ValueError("Invalid"))
            False
            
        Validates: Requirements 6.5
        """
        return self.classify(exception) == ErrorCategory.RETRYABLE
    
    def is_non_retryable(self, exception: Exception) -> bool:
        """
        Check if an exception is non-retryable.
        
        Args:
            exception: Exception instance to check
            
        Returns:
            True if exception is non-retryable, False otherwise
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> classifier.is_non_retryable(ValueError("Invalid"))
            True
            >>> classifier.is_non_retryable(ConnectionError("Failed"))
            False
        """
        return self.classify(exception) == ErrorCategory.NON_RETRYABLE
    
    def is_critical(self, exception: Exception) -> bool:
        """
        Check if an exception is critical.
        
        Args:
            exception: Exception instance to check
            
        Returns:
            True if exception is critical, False otherwise
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> classifier.is_critical(MemoryError("Out of memory"))
            True
            >>> classifier.is_critical(ValueError("Invalid"))
            False
        """
        return self.classify(exception) == ErrorCategory.CRITICAL
    
    def get_retryable_exceptions(self) -> Tuple[Type[Exception], ...]:
        """
        Get tuple of retryable exception types.
        
        Returns:
            Tuple of retryable exception types
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> exceptions = classifier.get_retryable_exceptions()
            >>> ConnectionError in exceptions
            True
        """
        return tuple(self._retryable)
    
    def get_non_retryable_exceptions(self) -> Tuple[Type[Exception], ...]:
        """
        Get tuple of non-retryable exception types.
        
        Returns:
            Tuple of non-retryable exception types
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> exceptions = classifier.get_non_retryable_exceptions()
            >>> ValueError in exceptions
            True
        """
        return tuple(self._non_retryable)
    
    def get_critical_exceptions(self) -> Tuple[Type[Exception], ...]:
        """
        Get tuple of critical exception types.
        
        Returns:
            Tuple of critical exception types
        """
        return tuple(self._critical)
    
    def register_retryable(self, *exception_types: Type[Exception]) -> None:
        """
        Register custom exception types as retryable.
        
        Args:
            *exception_types: Exception types to register as retryable
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> class CustomNetworkError(Exception):
            ...     pass
            >>> classifier.register_retryable(CustomNetworkError)
            >>> classifier.is_retryable(CustomNetworkError("Failed"))
            True
        """
        for exc_type in exception_types:
            if not issubclass(exc_type, Exception):
                raise TypeError(f"{exc_type} is not an Exception subclass")
            self._retryable.add(exc_type)
            # Remove from other categories if present
            self._non_retryable.discard(exc_type)
            self._critical.discard(exc_type)
    
    def register_non_retryable(self, *exception_types: Type[Exception]) -> None:
        """
        Register custom exception types as non-retryable.
        
        Args:
            *exception_types: Exception types to register as non-retryable
            
        Example:
            >>> classifier = ErrorClassifier()
            >>> class CustomValidationError(Exception):
            ...     pass
            >>> classifier.register_non_retryable(CustomValidationError)
            >>> classifier.is_non_retryable(CustomValidationError("Invalid"))
            True
        """
        for exc_type in exception_types:
            if not issubclass(exc_type, Exception):
                raise TypeError(f"{exc_type} is not an Exception subclass")
            self._non_retryable.add(exc_type)
            # Remove from other categories if present
            self._retryable.discard(exc_type)
            self._critical.discard(exc_type)
    
    def register_critical(self, *exception_types: Type[Exception]) -> None:
        """
        Register custom exception types as critical.
        
        Args:
            *exception_types: Exception types to register as critical
        """
        for exc_type in exception_types:
            if not issubclass(exc_type, Exception):
                raise TypeError(f"{exc_type} is not an Exception subclass")
            self._critical.add(exc_type)
            # Remove from other categories if present
            self._retryable.discard(exc_type)
            self._non_retryable.discard(exc_type)
    
    def _is_type_in_set(
        self,
        exception_type: Type[Exception],
        exception_set: Set[Type[Exception]]
    ) -> bool:
        """
        Check if exception type or any of its base classes are in the set.
        
        This allows for inheritance-based classification.
        
        Args:
            exception_type: Exception type to check
            exception_set: Set of exception types to check against
            
        Returns:
            True if exception_type or any base class is in the set
        """
        # Check the exception type itself
        if exception_type in exception_set:
            return True
        
        # Check base classes (inheritance)
        for base_class in exception_type.__mro__[1:]:
            if base_class in exception_set:
                return True
        
        return False


# Global classifier instance for convenience
_default_classifier = ErrorClassifier()


def classify_error(exception: Exception) -> ErrorCategory:
    """
    Classify an exception using the default classifier.
    
    Args:
        exception: Exception to classify
        
    Returns:
        ErrorCategory indicating the classification
        
    Example:
        >>> classify_error(ConnectionError("Failed"))
        ErrorCategory.RETRYABLE
        >>> classify_error(ValueError("Invalid"))
        ErrorCategory.NON_RETRYABLE
        
    Validates: Requirements 6.5
    """
    return _default_classifier.classify(exception)


def is_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception is retryable using the default classifier.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if exception is retryable, False otherwise
        
    Example:
        >>> is_retryable_error(ConnectionError("Failed"))
        True
        >>> is_retryable_error(ValueError("Invalid"))
        False
        
    Validates: Requirements 6.5
    """
    return _default_classifier.is_retryable(exception)


def is_non_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception is non-retryable using the default classifier.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if exception is non-retryable, False otherwise
    """
    return _default_classifier.is_non_retryable(exception)


def is_critical_error(exception: Exception) -> bool:
    """
    Check if an exception is critical using the default classifier.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if exception is critical, False otherwise
    """
    return _default_classifier.is_critical(exception)


def get_retryable_exceptions() -> Tuple[Type[Exception], ...]:
    """
    Get tuple of retryable exception types from the default classifier.
    
    Returns:
        Tuple of retryable exception types
    """
    return _default_classifier.get_retryable_exceptions()


def get_non_retryable_exceptions() -> Tuple[Type[Exception], ...]:
    """
    Get tuple of non-retryable exception types from the default classifier.
    
    Returns:
        Tuple of non-retryable exception types
    """
    return _default_classifier.get_non_retryable_exceptions()


# HTTP status code based classification helpers
class HTTPError(Exception):
    """Base class for HTTP errors with status codes."""
    
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def classify_http_error(status_code: int) -> ErrorCategory:
    """
    Classify HTTP errors by status code.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        ErrorCategory based on status code
        
    Classification:
    - 408 (Timeout), 429 (Rate Limit), 503 (Service Unavailable), 504 (Gateway Timeout): RETRYABLE
    - 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 422 (Unprocessable): NON_RETRYABLE
    - 500 (Internal Server Error), 502 (Bad Gateway): RETRYABLE (may be transient)
    
    Example:
        >>> classify_http_error(503)
        ErrorCategory.RETRYABLE
        >>> classify_http_error(404)
        ErrorCategory.NON_RETRYABLE
    """
    # Retryable HTTP errors (transient)
    if status_code in (408, 429, 502, 503, 504):
        return ErrorCategory.RETRYABLE
    
    # Non-retryable HTTP errors (client errors)
    if 400 <= status_code < 500:
        return ErrorCategory.NON_RETRYABLE
    
    # Server errors (500-599) - generally retryable except specific cases
    if 500 <= status_code < 600:
        return ErrorCategory.RETRYABLE
    
    # Default to non-retryable
    return ErrorCategory.NON_RETRYABLE


def is_retryable_http_status(status_code: int) -> bool:
    """
    Check if an HTTP status code represents a retryable error.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        True if status code is retryable, False otherwise
    """
    return classify_http_error(status_code) == ErrorCategory.RETRYABLE
