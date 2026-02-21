"""
Unit tests for error classification system.

Tests cover:
- Error category classification
- Retryable exception identification
- Non-retryable exception identification
- Critical exception identification
- Custom exception registration
- HTTP status code classification
- Inheritance-based classification
"""

import pytest
from infrastructure.error_classification import (
    ErrorClassifier,
    ErrorCategory,
    classify_error,
    is_retryable_error,
    is_non_retryable_error,
    is_critical_error,
    get_retryable_exceptions,
    get_non_retryable_exceptions,
    classify_http_error,
    is_retryable_http_status,
    HTTPError
)


class TestErrorClassifierInitialization:
    """Test ErrorClassifier initialization."""
    
    def test_default_initialization(self):
        """Test ErrorClassifier with default exception mappings."""
        classifier = ErrorClassifier()
        
        # Verify retryable exceptions are set
        retryable = classifier.get_retryable_exceptions()
        assert ConnectionError in retryable
        assert TimeoutError in retryable
        assert OSError in retryable
        
        # Verify non-retryable exceptions are set
        non_retryable = classifier.get_non_retryable_exceptions()
        assert ValueError in non_retryable
        assert TypeError in non_retryable
        assert KeyError in non_retryable
        
        # Verify critical exceptions are set
        critical = classifier.get_critical_exceptions()
        assert MemoryError in critical
        assert SystemError in critical


class TestErrorClassification:
    """Test error classification logic."""
    
    def test_classify_retryable_exceptions(self):
        """Test classification of retryable exceptions."""
        classifier = ErrorClassifier()
        
        assert classifier.classify(ConnectionError("Failed")) == ErrorCategory.RETRYABLE
        assert classifier.classify(TimeoutError("Timeout")) == ErrorCategory.RETRYABLE
        assert classifier.classify(OSError("OS error")) == ErrorCategory.RETRYABLE
    
    def test_classify_non_retryable_exceptions(self):
        """Test classification of non-retryable exceptions."""
        classifier = ErrorClassifier()
        
        assert classifier.classify(ValueError("Invalid")) == ErrorCategory.NON_RETRYABLE
        assert classifier.classify(TypeError("Type error")) == ErrorCategory.NON_RETRYABLE
        assert classifier.classify(KeyError("Not found")) == ErrorCategory.NON_RETRYABLE
        assert classifier.classify(AttributeError("No attr")) == ErrorCategory.NON_RETRYABLE
    
    def test_classify_critical_exceptions(self):
        """Test classification of critical exceptions."""
        classifier = ErrorClassifier()
        
        assert classifier.classify(MemoryError("Out of memory")) == ErrorCategory.CRITICAL
        assert classifier.classify(SystemError("System error")) == ErrorCategory.CRITICAL
        assert classifier.classify(RecursionError("Too deep")) == ErrorCategory.CRITICAL
    
    def test_classify_unknown_exception(self):
        """Test that unknown exceptions default to non-retryable."""
        classifier = ErrorClassifier()
        
        class CustomUnknownError(Exception):
            pass
        
        # Unknown exceptions should default to non-retryable (fail-safe)
        assert classifier.classify(CustomUnknownError("Unknown")) == ErrorCategory.NON_RETRYABLE


class TestIsRetryable:
    """Test is_retryable method."""
    
    def test_is_retryable_true(self):
        """Test that retryable exceptions return True."""
        classifier = ErrorClassifier()
        
        assert classifier.is_retryable(ConnectionError("Failed")) is True
        assert classifier.is_retryable(TimeoutError("Timeout")) is True
        assert classifier.is_retryable(OSError("OS error")) is True
    
    def test_is_retryable_false(self):
        """Test that non-retryable exceptions return False."""
        classifier = ErrorClassifier()
        
        assert classifier.is_retryable(ValueError("Invalid")) is False
        assert classifier.is_retryable(TypeError("Type error")) is False
        assert classifier.is_retryable(KeyError("Not found")) is False
    
    def test_is_retryable_critical(self):
        """Test that critical exceptions return False for is_retryable."""
        classifier = ErrorClassifier()
        
        assert classifier.is_retryable(MemoryError("Out of memory")) is False
        assert classifier.is_retryable(SystemError("System error")) is False


class TestIsNonRetryable:
    """Test is_non_retryable method."""
    
    def test_is_non_retryable_true(self):
        """Test that non-retryable exceptions return True."""
        classifier = ErrorClassifier()
        
        assert classifier.is_non_retryable(ValueError("Invalid")) is True
        assert classifier.is_non_retryable(TypeError("Type error")) is True
        assert classifier.is_non_retryable(KeyError("Not found")) is True
    
    def test_is_non_retryable_false(self):
        """Test that retryable exceptions return False."""
        classifier = ErrorClassifier()
        
        assert classifier.is_non_retryable(ConnectionError("Failed")) is False
        assert classifier.is_non_retryable(TimeoutError("Timeout")) is False


class TestIsCritical:
    """Test is_critical method."""
    
    def test_is_critical_true(self):
        """Test that critical exceptions return True."""
        classifier = ErrorClassifier()
        
        assert classifier.is_critical(MemoryError("Out of memory")) is True
        assert classifier.is_critical(SystemError("System error")) is True
        assert classifier.is_critical(RecursionError("Too deep")) is True
    
    def test_is_critical_false(self):
        """Test that non-critical exceptions return False."""
        classifier = ErrorClassifier()
        
        assert classifier.is_critical(ValueError("Invalid")) is False
        assert classifier.is_critical(ConnectionError("Failed")) is False


class TestCustomExceptionRegistration:
    """Test custom exception registration."""
    
    def test_register_retryable(self):
        """Test registering custom retryable exceptions."""
        classifier = ErrorClassifier()
        
        class CustomNetworkError(Exception):
            pass
        
        # Initially should be non-retryable (unknown)
        assert classifier.is_retryable(CustomNetworkError("Failed")) is False
        
        # Register as retryable
        classifier.register_retryable(CustomNetworkError)
        
        # Now should be retryable
        assert classifier.is_retryable(CustomNetworkError("Failed")) is True
        assert classifier.classify(CustomNetworkError("Failed")) == ErrorCategory.RETRYABLE
    
    def test_register_non_retryable(self):
        """Test registering custom non-retryable exceptions."""
        classifier = ErrorClassifier()
        
        class CustomValidationError(Exception):
            pass
        
        # Register as non-retryable
        classifier.register_non_retryable(CustomValidationError)
        
        # Should be non-retryable
        assert classifier.is_non_retryable(CustomValidationError("Invalid")) is True
        assert classifier.classify(CustomValidationError("Invalid")) == ErrorCategory.NON_RETRYABLE
    
    def test_register_critical(self):
        """Test registering custom critical exceptions."""
        classifier = ErrorClassifier()
        
        class CustomCriticalError(Exception):
            pass
        
        # Register as critical
        classifier.register_critical(CustomCriticalError)
        
        # Should be critical
        assert classifier.is_critical(CustomCriticalError("Critical")) is True
        assert classifier.classify(CustomCriticalError("Critical")) == ErrorCategory.CRITICAL
    
    def test_register_multiple_exceptions(self):
        """Test registering multiple exceptions at once."""
        classifier = ErrorClassifier()
        
        class CustomError1(Exception):
            pass
        
        class CustomError2(Exception):
            pass
        
        class CustomError3(Exception):
            pass
        
        # Register multiple
        classifier.register_retryable(CustomError1, CustomError2, CustomError3)
        
        # All should be retryable
        assert classifier.is_retryable(CustomError1("Failed")) is True
        assert classifier.is_retryable(CustomError2("Failed")) is True
        assert classifier.is_retryable(CustomError3("Failed")) is True
    
    def test_register_moves_between_categories(self):
        """Test that registering moves exceptions between categories."""
        classifier = ErrorClassifier()
        
        class CustomError(Exception):
            pass
        
        # Register as retryable
        classifier.register_retryable(CustomError)
        assert classifier.is_retryable(CustomError("Failed")) is True
        
        # Re-register as non-retryable
        classifier.register_non_retryable(CustomError)
        assert classifier.is_non_retryable(CustomError("Failed")) is True
        assert classifier.is_retryable(CustomError("Failed")) is False
        
        # Re-register as critical
        classifier.register_critical(CustomError)
        assert classifier.is_critical(CustomError("Failed")) is True
        assert classifier.is_retryable(CustomError("Failed")) is False
        assert classifier.is_non_retryable(CustomError("Failed")) is False
    
    def test_register_invalid_type(self):
        """Test that registering non-exception types raises TypeError."""
        classifier = ErrorClassifier()
        
        with pytest.raises(TypeError, match="is not an Exception subclass"):
            classifier.register_retryable(str)
        
        with pytest.raises(TypeError, match="is not an Exception subclass"):
            classifier.register_non_retryable(int)
        
        with pytest.raises(TypeError, match="is not an Exception subclass"):
            classifier.register_critical(dict)


class TestInheritanceBasedClassification:
    """Test that classification works with exception inheritance."""
    
    def test_subclass_inherits_classification(self):
        """Test that subclasses inherit parent classification."""
        classifier = ErrorClassifier()
        
        # ConnectionError is retryable
        class CustomConnectionError(ConnectionError):
            pass
        
        # Subclass should also be retryable
        assert classifier.is_retryable(CustomConnectionError("Failed")) is True
    
    def test_custom_base_class_classification(self):
        """Test classification with custom base classes."""
        classifier = ErrorClassifier()
        
        class CustomRetryableError(Exception):
            pass
        
        class SpecificRetryableError(CustomRetryableError):
            pass
        
        # Register base class as retryable
        classifier.register_retryable(CustomRetryableError)
        
        # Both base and subclass should be retryable
        assert classifier.is_retryable(CustomRetryableError("Failed")) is True
        assert classifier.is_retryable(SpecificRetryableError("Failed")) is True


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_classify_error(self):
        """Test global classify_error function."""
        assert classify_error(ConnectionError("Failed")) == ErrorCategory.RETRYABLE
        assert classify_error(ValueError("Invalid")) == ErrorCategory.NON_RETRYABLE
        assert classify_error(MemoryError("Out of memory")) == ErrorCategory.CRITICAL
    
    def test_is_retryable_error(self):
        """Test global is_retryable_error function."""
        assert is_retryable_error(ConnectionError("Failed")) is True
        assert is_retryable_error(ValueError("Invalid")) is False
    
    def test_is_non_retryable_error(self):
        """Test global is_non_retryable_error function."""
        assert is_non_retryable_error(ValueError("Invalid")) is True
        assert is_non_retryable_error(ConnectionError("Failed")) is False
    
    def test_is_critical_error(self):
        """Test global is_critical_error function."""
        assert is_critical_error(MemoryError("Out of memory")) is True
        assert is_critical_error(ValueError("Invalid")) is False
    
    def test_get_retryable_exceptions(self):
        """Test global get_retryable_exceptions function."""
        exceptions = get_retryable_exceptions()
        assert ConnectionError in exceptions
        assert TimeoutError in exceptions
        assert OSError in exceptions
    
    def test_get_non_retryable_exceptions(self):
        """Test global get_non_retryable_exceptions function."""
        exceptions = get_non_retryable_exceptions()
        assert ValueError in exceptions
        assert TypeError in exceptions
        assert KeyError in exceptions


class TestHTTPErrorClassification:
    """Test HTTP status code based classification."""
    
    def test_classify_retryable_http_errors(self):
        """Test classification of retryable HTTP status codes."""
        # Timeout
        assert classify_http_error(408) == ErrorCategory.RETRYABLE
        
        # Rate limit
        assert classify_http_error(429) == ErrorCategory.RETRYABLE
        
        # Bad gateway
        assert classify_http_error(502) == ErrorCategory.RETRYABLE
        
        # Service unavailable
        assert classify_http_error(503) == ErrorCategory.RETRYABLE
        
        # Gateway timeout
        assert classify_http_error(504) == ErrorCategory.RETRYABLE
    
    def test_classify_non_retryable_http_errors(self):
        """Test classification of non-retryable HTTP status codes."""
        # Bad request
        assert classify_http_error(400) == ErrorCategory.NON_RETRYABLE
        
        # Unauthorized
        assert classify_http_error(401) == ErrorCategory.NON_RETRYABLE
        
        # Forbidden
        assert classify_http_error(403) == ErrorCategory.NON_RETRYABLE
        
        # Not found
        assert classify_http_error(404) == ErrorCategory.NON_RETRYABLE
        
        # Unprocessable entity
        assert classify_http_error(422) == ErrorCategory.NON_RETRYABLE
    
    def test_classify_server_errors_as_retryable(self):
        """Test that most 5xx errors are retryable."""
        # Internal server error (may be transient)
        assert classify_http_error(500) == ErrorCategory.RETRYABLE
        
        # Generic 5xx errors
        assert classify_http_error(501) == ErrorCategory.RETRYABLE
        assert classify_http_error(505) == ErrorCategory.RETRYABLE
    
    def test_is_retryable_http_status(self):
        """Test is_retryable_http_status helper function."""
        assert is_retryable_http_status(503) is True
        assert is_retryable_http_status(404) is False
        assert is_retryable_http_status(500) is True
        assert is_retryable_http_status(400) is False
    
    def test_classify_success_codes(self):
        """Test classification of success codes (should be non-retryable)."""
        assert classify_http_error(200) == ErrorCategory.NON_RETRYABLE
        assert classify_http_error(201) == ErrorCategory.NON_RETRYABLE
        assert classify_http_error(204) == ErrorCategory.NON_RETRYABLE


class TestHTTPError:
    """Test HTTPError exception class."""
    
    def test_http_error_creation(self):
        """Test creating HTTPError with status code."""
        error = HTTPError("Not found", 404)
        assert str(error) == "Not found"
        assert error.status_code == 404
    
    def test_http_error_classification(self):
        """Test that HTTPError can be classified."""
        classifier = ErrorClassifier()
        
        # HTTPError itself is not in any category by default
        error = HTTPError("Server error", 500)
        
        # But we can register it
        classifier.register_retryable(HTTPError)
        assert classifier.is_retryable(error) is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exception_with_no_message(self):
        """Test classification of exceptions with no message."""
        classifier = ErrorClassifier()
        
        assert classifier.is_retryable(ConnectionError()) is True
        assert classifier.is_non_retryable(ValueError()) is True
    
    def test_exception_with_complex_args(self):
        """Test classification of exceptions with complex arguments."""
        classifier = ErrorClassifier()
        
        error = ConnectionError("Failed", {"details": "Network unreachable"})
        assert classifier.is_retryable(error) is True
    
    def test_multiple_inheritance(self):
        """Test classification with multiple inheritance."""
        classifier = ErrorClassifier()
        
        class MixinA:
            pass
        
        class CustomError(MixinA, ConnectionError):
            pass
        
        # Should still be classified as retryable (inherits from ConnectionError)
        assert classifier.is_retryable(CustomError("Failed")) is True
    
    def test_deeply_nested_inheritance(self):
        """Test classification with deeply nested inheritance."""
        classifier = ErrorClassifier()
        
        class Level1(ConnectionError):
            pass
        
        class Level2(Level1):
            pass
        
        class Level3(Level2):
            pass
        
        # All levels should be retryable
        assert classifier.is_retryable(Level1("Failed")) is True
        assert classifier.is_retryable(Level2("Failed")) is True
        assert classifier.is_retryable(Level3("Failed")) is True
    
    def test_empty_exception_sets(self):
        """Test behavior with empty exception sets."""
        classifier = ErrorClassifier()
        
        # Clear all exceptions (for testing)
        classifier._retryable.clear()
        classifier._non_retryable.clear()
        classifier._critical.clear()
        
        # All exceptions should default to non-retryable
        assert classifier.classify(ConnectionError("Failed")) == ErrorCategory.NON_RETRYABLE
        assert classifier.classify(ValueError("Invalid")) == ErrorCategory.NON_RETRYABLE
