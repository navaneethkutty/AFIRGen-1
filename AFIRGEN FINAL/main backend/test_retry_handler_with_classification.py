"""
Unit tests for retry handler with error classification integration.

Tests cover:
- Automatic error classification (no manual exception list)
- Manual exception list (backward compatibility)
- Error classifier integration
- Custom error classifier usage
"""

import pytest
import time
from unittest.mock import Mock
from infrastructure.retry_handler import RetryHandler, retry
from infrastructure.error_classification import ErrorClassifier, ErrorCategory


class TestAutomaticErrorClassification:
    """Test automatic error classification in retry handler."""
    
    def test_automatic_retry_on_retryable_errors(self):
        """Test that retryable errors are automatically retried."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        # ConnectionError is retryable by default
        mock_func = Mock(side_effect=[
            ConnectionError("Network failed"),
            ConnectionError("Network failed"),
            "success"
        ])
        
        # No retryable_exceptions specified - uses automatic classification
        result = handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_automatic_no_retry_on_non_retryable_errors(self):
        """Test that non-retryable errors are not retried."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        # ValueError is non-retryable by default
        mock_func = Mock(side_effect=ValueError("Invalid input"))
        
        # No retryable_exceptions specified - uses automatic classification
        with pytest.raises(ValueError, match="Invalid input"):
            handler.execute_with_retry(mock_func)
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_automatic_classification_with_multiple_error_types(self):
        """Test automatic classification with different error types."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Network error"),  # Retryable
            TimeoutError("Timeout"),           # Retryable
            OSError("OS error"),               # Retryable
            "success"
        ])
        
        result = handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 4
    
    def test_automatic_classification_stops_on_non_retryable(self):
        """Test that automatic classification stops on non-retryable errors."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Network error"),  # Retryable - retry
            ValueError("Invalid input"),       # Non-retryable - stop
            "success"
        ])
        
        with pytest.raises(ValueError, match="Invalid input"):
            handler.execute_with_retry(mock_func)
        
        # Should be called twice (initial + 1 retry, then non-retryable)
        assert mock_func.call_count == 2


class TestManualExceptionList:
    """Test manual exception list (backward compatibility)."""
    
    def test_manual_exception_list_retries(self):
        """Test that manual exception list works as before."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            "success"
        ])
        
        # Explicitly specify retryable exceptions
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_manual_exception_list_no_retry(self):
        """Test that manual exception list prevents retry on unlisted exceptions."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=TimeoutError("Timeout"))
        
        # Only ConnectionError is retryable
        with pytest.raises(TimeoutError, match="Timeout"):
            handler.execute_with_retry(
                mock_func,
                retryable_exceptions=(ConnectionError,)
            )
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_manual_exception_list_overrides_classifier(self):
        """Test that manual exception list overrides automatic classification."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        # ValueError is normally non-retryable, but we'll make it retryable manually
        mock_func = Mock(side_effect=[
            ValueError("Invalid"),
            "success"
        ])
        
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ValueError,)
        )
        
        assert result == "success"
        assert mock_func.call_count == 2


class TestCustomErrorClassifier:
    """Test using custom error classifier."""
    
    def test_custom_classifier_with_registered_exceptions(self):
        """Test retry handler with custom error classifier."""
        # Create custom classifier
        classifier = ErrorClassifier()
        
        # Register custom exception as retryable
        class CustomNetworkError(Exception):
            pass
        
        classifier.register_retryable(CustomNetworkError)
        
        # Create handler with custom classifier
        handler = RetryHandler(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
            error_classifier=classifier
        )
        
        mock_func = Mock(side_effect=[
            CustomNetworkError("Custom error"),
            "success"
        ])
        
        result = handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_custom_classifier_non_retryable(self):
        """Test custom classifier with non-retryable exceptions."""
        classifier = ErrorClassifier()
        
        class CustomValidationError(Exception):
            pass
        
        classifier.register_non_retryable(CustomValidationError)
        
        handler = RetryHandler(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
            error_classifier=classifier
        )
        
        mock_func = Mock(side_effect=CustomValidationError("Validation failed"))
        
        with pytest.raises(CustomValidationError, match="Validation failed"):
            handler.execute_with_retry(mock_func)
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1


class TestClassifyErrorMethod:
    """Test classify_error method on RetryHandler."""
    
    def test_classify_error_retryable(self):
        """Test classify_error method for retryable exceptions."""
        handler = RetryHandler()
        
        assert handler.classify_error(ConnectionError("Failed")) == ErrorCategory.RETRYABLE
        assert handler.classify_error(TimeoutError("Timeout")) == ErrorCategory.RETRYABLE
    
    def test_classify_error_non_retryable(self):
        """Test classify_error method for non-retryable exceptions."""
        handler = RetryHandler()
        
        assert handler.classify_error(ValueError("Invalid")) == ErrorCategory.NON_RETRYABLE
        assert handler.classify_error(TypeError("Type error")) == ErrorCategory.NON_RETRYABLE
    
    def test_classify_error_critical(self):
        """Test classify_error method for critical exceptions."""
        handler = RetryHandler()
        
        assert handler.classify_error(MemoryError("Out of memory")) == ErrorCategory.CRITICAL


class TestRetryDecoratorWithClassification:
    """Test retry decorator with automatic classification."""
    
    def test_decorator_automatic_classification(self):
        """Test decorator with automatic error classification."""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.01, jitter=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network failed")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 3
    
    def test_decorator_stops_on_non_retryable(self):
        """Test decorator stops on non-retryable errors."""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.01, jitter=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")
        
        with pytest.raises(ValueError, match="Invalid input"):
            test_func()
        
        # Should only be called once
        assert call_count == 1
    
    def test_decorator_manual_exceptions(self):
        """Test decorator with manual exception list."""
        call_count = 0
        
        @retry(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
            retryable_exceptions=(ValueError,)
        )
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retryable validation error")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 3
    
    def test_decorator_with_custom_classifier(self):
        """Test decorator with custom error classifier."""
        classifier = ErrorClassifier()
        
        class CustomError(Exception):
            pass
        
        classifier.register_retryable(CustomError)
        
        call_count = 0
        
        @retry(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
            error_classifier=classifier
        )
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CustomError("Custom error")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 3


class TestMixedScenarios:
    """Test mixed scenarios with different error types."""
    
    def test_retryable_then_success(self):
        """Test retryable error followed by success."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            TimeoutError("Timeout"),
            "success"
        ])
        
        result = handler.execute_with_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retryable_then_non_retryable(self):
        """Test retryable error followed by non-retryable error."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            ValueError("Invalid")
        ])
        
        with pytest.raises(ValueError, match="Invalid"):
            handler.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 2
    
    def test_max_retries_with_automatic_classification(self):
        """Test max retries exhausted with automatic classification."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=ConnectionError("Failed"))
        
        with pytest.raises(ConnectionError, match="Failed"):
            handler.execute_with_retry(mock_func)
        
        # Should be called 3 times (initial + 2 retries)
        assert mock_func.call_count == 3
    
    def test_critical_error_not_retried(self):
        """Test that critical errors are not retried."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=MemoryError("Out of memory"))
        
        with pytest.raises(MemoryError, match="Out of memory"):
            handler.execute_with_retry(mock_func)
        
        # Should only be called once (critical errors are not retried)
        assert mock_func.call_count == 1


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_old_style_usage_still_works(self):
        """Test that old-style usage with explicit exceptions still works."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            "success"
        ])
        
        # Old style: explicitly pass retryable_exceptions
        result = handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_new_style_usage_works(self):
        """Test that new-style usage with automatic classification works."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=[
            ConnectionError("Failed"),
            "success"
        ])
        
        # New style: no retryable_exceptions, uses automatic classification
        result = handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_empty_tuple_prevents_all_retries(self):
        """Test that empty tuple prevents all retries (edge case)."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
        
        mock_func = Mock(side_effect=ConnectionError("Failed"))
        
        # Empty tuple means no exceptions are retryable
        with pytest.raises(ConnectionError, match="Failed"):
            handler.execute_with_retry(
                mock_func,
                retryable_exceptions=()
            )
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
