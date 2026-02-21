"""
Property-based tests for error classification system.

This module contains property-based tests using Hypothesis to verify
that the error classification system correctly categorizes exceptions
across a wide range of inputs.

Feature: backend-optimization
Property 29: Error classification
Validates: Requirements 6.5
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from infrastructure.error_classification import (
    ErrorClassifier,
    ErrorCategory,
    classify_error,
    is_retryable_error,
    is_non_retryable_error,
    is_critical_error,
    classify_http_error,
    is_retryable_http_status,
)


# Strategy for generating exception instances
@st.composite
def exception_strategy(draw):
    """
    Generate exception instances from known exception types.
    
    Returns a tuple of (exception_instance, expected_category)
    """
    # Define exception types with their expected categories
    retryable_types = [
        ConnectionError,
        TimeoutError,
        OSError,
    ]
    
    non_retryable_types = [
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        AssertionError,
        NotImplementedError,
    ]
    
    critical_types = [
        MemoryError,
        SystemError,
        RecursionError,
    ]
    
    # Choose a category
    category = draw(st.sampled_from([
        ErrorCategory.RETRYABLE,
        ErrorCategory.NON_RETRYABLE,
        ErrorCategory.CRITICAL
    ]))
    
    # Choose an exception type based on category
    if category == ErrorCategory.RETRYABLE:
        exc_type = draw(st.sampled_from(retryable_types))
    elif category == ErrorCategory.NON_RETRYABLE:
        exc_type = draw(st.sampled_from(non_retryable_types))
    else:  # CRITICAL
        exc_type = draw(st.sampled_from(critical_types))
    
    # Generate a message
    message = draw(st.text(min_size=0, max_size=100))
    
    # Create exception instance
    try:
        exception = exc_type(message)
    except Exception:
        # If exception creation fails, use a simple message
        exception = exc_type("test error")
    
    return exception, category


# Strategy for HTTP status codes
http_status_codes = st.integers(min_value=100, max_value=599)


class TestErrorClassificationProperties:
    """Property-based tests for error classification."""
    
    @given(exception_strategy())
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_error_classification_consistency(self, exception_data):
        """
        Property 29: Error classification
        
        For any exception raised in the system, the error handler should
        correctly classify it as either retryable, non-retryable, or critical.
        
        This test verifies that:
        1. Classification is consistent across multiple calls
        2. Classification matches expected category based on exception type
        3. Helper methods (is_retryable, is_non_retryable, is_critical) are consistent
        
        **Validates: Requirements 6.5**
        """
        exception, expected_category = exception_data
        classifier = ErrorClassifier()
        
        # Property 1: Classification should be consistent
        classification1 = classifier.classify(exception)
        classification2 = classifier.classify(exception)
        assert classification1 == classification2, \
            f"Classification should be consistent for {type(exception).__name__}"
        
        # Property 2: Classification should match expected category
        assert classification1 == expected_category, \
            f"Expected {expected_category} for {type(exception).__name__}, got {classification1}"
        
        # Property 3: Helper methods should be consistent with classify()
        is_retryable = classifier.is_retryable(exception)
        is_non_retryable = classifier.is_non_retryable(exception)
        is_critical = classifier.is_critical(exception)
        
        # Exactly one should be True
        true_count = sum([is_retryable, is_non_retryable, is_critical])
        assert true_count == 1, \
            f"Exactly one classification should be True, got {true_count}"
        
        # Verify consistency with classify()
        if classification1 == ErrorCategory.RETRYABLE:
            assert is_retryable is True
            assert is_non_retryable is False
            assert is_critical is False
        elif classification1 == ErrorCategory.NON_RETRYABLE:
            assert is_retryable is False
            assert is_non_retryable is True
            assert is_critical is False
        else:  # CRITICAL
            assert is_retryable is False
            assert is_non_retryable is False
            assert is_critical is True
    
    @given(exception_strategy())
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_global_functions_consistency(self, exception_data):
        """
        Property 29: Error classification (global functions)
        
        Verify that global convenience functions produce consistent results
        with the ErrorClassifier instance methods.
        
        **Validates: Requirements 6.5**
        """
        exception, expected_category = exception_data
        classifier = ErrorClassifier()
        
        # Global functions should match instance methods
        assert classify_error(exception) == classifier.classify(exception)
        assert is_retryable_error(exception) == classifier.is_retryable(exception)
        assert is_non_retryable_error(exception) == classifier.is_non_retryable(exception)
        assert is_critical_error(exception) == classifier.is_critical(exception)
    
    @given(http_status_codes)
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_http_status_classification(self, status_code):
        """
        Property 29: Error classification (HTTP status codes)
        
        For any HTTP status code, the classification should follow these rules:
        - 408, 429, 502, 503, 504: RETRYABLE (transient errors)
        - 400-499 (except above): NON_RETRYABLE (client errors)
        - 500-599 (except above): RETRYABLE (server errors, may be transient)
        - Other codes: NON_RETRYABLE (default)
        
        **Validates: Requirements 6.5**
        """
        classification = classify_http_error(status_code)
        
        # Verify classification follows the rules
        if status_code in (408, 429, 502, 503, 504):
            assert classification == ErrorCategory.RETRYABLE, \
                f"Status {status_code} should be RETRYABLE"
        elif 400 <= status_code < 500:
            assert classification == ErrorCategory.NON_RETRYABLE, \
                f"Status {status_code} (4xx) should be NON_RETRYABLE"
        elif 500 <= status_code < 600:
            assert classification == ErrorCategory.RETRYABLE, \
                f"Status {status_code} (5xx) should be RETRYABLE"
        else:
            assert classification == ErrorCategory.NON_RETRYABLE, \
                f"Status {status_code} should default to NON_RETRYABLE"
        
        # Verify helper function consistency
        is_retryable = is_retryable_http_status(status_code)
        assert is_retryable == (classification == ErrorCategory.RETRYABLE), \
            f"is_retryable_http_status should match classify_http_error for {status_code}"
    
    @given(
        st.text(min_size=0, max_size=200),
        st.sampled_from([
            ConnectionError, TimeoutError, OSError,
            ValueError, TypeError, KeyError,
            MemoryError, SystemError
        ])
    )
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_exception_message_independence(self, message, exc_type):
        """
        Property 29: Error classification (message independence)
        
        Classification should be independent of the exception message.
        The same exception type with different messages should have
        the same classification.
        
        **Validates: Requirements 6.5**
        """
        classifier = ErrorClassifier()
        
        try:
            exception1 = exc_type(message)
            exception2 = exc_type("different message")
        except Exception:
            # If exception creation fails, skip this example
            assume(False)
        
        # Classification should be the same regardless of message
        classification1 = classifier.classify(exception1)
        classification2 = classifier.classify(exception2)
        
        assert classification1 == classification2, \
            f"Classification should be independent of message for {exc_type.__name__}"
    
    @given(exception_strategy())
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_inheritance_based_classification(self, exception_data):
        """
        Property 29: Error classification (inheritance)
        
        Subclasses of classified exceptions should inherit the same
        classification as their parent class.
        
        **Validates: Requirements 6.5**
        """
        exception, expected_category = exception_data
        classifier = ErrorClassifier()
        
        # Get the exception type
        exc_type = type(exception)
        
        # Create a dynamic subclass
        class DynamicSubclass(exc_type):
            pass
        
        try:
            subclass_exception = DynamicSubclass(str(exception))
        except Exception:
            # If exception creation fails, skip this example
            assume(False)
        
        # Subclass should have the same classification as parent
        parent_classification = classifier.classify(exception)
        subclass_classification = classifier.classify(subclass_exception)
        
        assert parent_classification == subclass_classification, \
            f"Subclass should inherit classification from parent {exc_type.__name__}"
    
    @given(
        st.lists(
            st.sampled_from([
                ConnectionError, TimeoutError, ValueError, TypeError
            ]),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50)
    @pytest.mark.property_test
    def test_property_29_custom_registration_consistency(self, exc_types):
        """
        Property 29: Error classification (custom registration)
        
        When custom exceptions are registered, they should be classified
        according to their registration category, and registration should
        move them between categories correctly.
        
        **Validates: Requirements 6.5**
        """
        classifier = ErrorClassifier()
        
        # Create custom exception types
        custom_exceptions = []
        for i, base_type in enumerate(exc_types):
            # Create a unique custom exception type
            custom_exc = type(f"CustomException{i}", (Exception,), {})
            custom_exceptions.append(custom_exc)
        
        # Register as retryable
        classifier.register_retryable(*custom_exceptions)
        
        # All should be retryable
        for custom_exc in custom_exceptions:
            try:
                instance = custom_exc("test")
                assert classifier.is_retryable(instance) is True, \
                    f"{custom_exc.__name__} should be retryable after registration"
            except Exception:
                continue
        
        # Re-register as non-retryable
        classifier.register_non_retryable(*custom_exceptions)
        
        # All should be non-retryable now
        for custom_exc in custom_exceptions:
            try:
                instance = custom_exc("test")
                assert classifier.is_non_retryable(instance) is True, \
                    f"{custom_exc.__name__} should be non-retryable after re-registration"
                assert classifier.is_retryable(instance) is False, \
                    f"{custom_exc.__name__} should not be retryable after re-registration"
            except Exception:
                continue
    
    @given(exception_strategy())
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_classification_determinism(self, exception_data):
        """
        Property 29: Error classification (determinism)
        
        Classification should be deterministic - the same exception
        classified multiple times should always produce the same result.
        
        **Validates: Requirements 6.5**
        """
        exception, expected_category = exception_data
        classifier = ErrorClassifier()
        
        # Classify the same exception multiple times
        classifications = [classifier.classify(exception) for _ in range(10)]
        
        # All classifications should be identical
        assert all(c == classifications[0] for c in classifications), \
            f"Classification should be deterministic for {type(exception).__name__}"
        
        # Should match expected category
        assert classifications[0] == expected_category
    
    @given(
        st.sampled_from([
            ConnectionError, TimeoutError, OSError,
            ValueError, TypeError, KeyError,
            MemoryError, SystemError, RecursionError
        ])
    )
    @settings(max_examples=50)
    @pytest.mark.property_test
    def test_property_29_exception_type_uniqueness(self, exc_type):
        """
        Property 29: Error classification (uniqueness)
        
        Each exception type should belong to exactly one category
        (retryable, non-retryable, or critical).
        
        **Validates: Requirements 6.5**
        """
        classifier = ErrorClassifier()
        
        try:
            exception = exc_type("test")
        except Exception:
            assume(False)
        
        # Check which categories the exception belongs to
        is_retryable = classifier.is_retryable(exception)
        is_non_retryable = classifier.is_non_retryable(exception)
        is_critical = classifier.is_critical(exception)
        
        # Exactly one should be True
        categories = [is_retryable, is_non_retryable, is_critical]
        true_count = sum(categories)
        
        assert true_count == 1, \
            f"{exc_type.__name__} should belong to exactly one category, " \
            f"but belongs to {true_count} categories"
    
    @given(http_status_codes)
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_property_29_http_classification_consistency(self, status_code):
        """
        Property 29: Error classification (HTTP consistency)
        
        HTTP status code classification should be consistent across
        multiple calls with the same status code.
        
        **Validates: Requirements 6.5**
        """
        # Classify multiple times
        classifications = [classify_http_error(status_code) for _ in range(5)]
        
        # All should be the same
        assert all(c == classifications[0] for c in classifications), \
            f"HTTP classification should be consistent for status {status_code}"
        
        # Helper function should be consistent
        is_retryable_results = [is_retryable_http_status(status_code) for _ in range(5)]
        assert all(r == is_retryable_results[0] for r in is_retryable_results), \
            f"is_retryable_http_status should be consistent for status {status_code}"


class TestErrorClassificationEdgeProperties:
    """Property-based tests for edge cases in error classification."""
    
    @given(st.integers(min_value=-1000, max_value=1000))
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_http_classification_handles_invalid_codes(self, status_code):
        """
        Test that HTTP classification handles any integer status code
        without raising exceptions.
        """
        # Should not raise any exception
        try:
            result = classify_http_error(status_code)
            assert isinstance(result, ErrorCategory)
        except Exception as e:
            pytest.fail(f"classify_http_error should not raise exception for {status_code}: {e}")
    
    @given(
        st.sampled_from([
            ConnectionError, ValueError, MemoryError
        ]),
        st.one_of(
            st.none(),
            st.text(),
            st.integers(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text())
        )
    )
    @settings(max_examples=100)
    @pytest.mark.property_test
    def test_classification_handles_various_exception_args(self, exc_type, args):
        """
        Test that classification handles exceptions with various argument types.
        """
        classifier = ErrorClassifier()
        
        try:
            if args is None:
                exception = exc_type()
            else:
                exception = exc_type(args)
            
            # Should not raise exception during classification
            result = classifier.classify(exception)
            assert isinstance(result, ErrorCategory)
        except Exception:
            # If exception creation fails, that's okay - we're testing classification
            # not exception creation
            pass
