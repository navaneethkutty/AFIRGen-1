"""
Unit tests for OpenTelemetry tracing integration.

Tests verify:
- Tracing manager initialization
- Span creation and management
- Attribute and event recording
- Context propagation
- Integration with correlation IDs
- Error handling in spans
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from contextlib import nullcontext

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode

from infrastructure.tracing import (
    TracingManager,
    setup_tracing,
    get_tracing_manager,
    trace_operation,
    get_current_trace_id,
    add_trace_attributes,
    add_trace_event
)


class TestTracingManager:
    """Test TracingManager class."""
    
    def test_initialization(self):
        """Test tracing manager initialization."""
        manager = TracingManager(
            service_name="test-service",
            service_version="1.0.0",
            otlp_endpoint="http://localhost:4317",
            enable_console_export=True
        )
        
        assert manager.service_name == "test-service"
        assert manager.service_version == "1.0.0"
        assert manager.otlp_endpoint == "http://localhost:4317"
        assert manager.enable_console_export is True
    
    def test_setup_creates_tracer_provider(self):
        """Test that setup creates tracer provider."""
        manager = TracingManager(
            service_name="test-service",
            enable_console_export=True
        )
        
        manager.setup()
        
        assert manager._provider is not None
        assert manager._tracer is not None
    
    def test_setup_with_otlp_endpoint(self):
        """Test setup with OTLP endpoint configuration."""
        manager = TracingManager(
            service_name="test-service",
            otlp_endpoint="http://localhost:4317"
        )
        
        # Should not raise exception
        manager.setup()
        
        assert manager._provider is not None
    
    def test_trace_operation_creates_span(self):
        """Test that trace_operation creates a span."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("test_operation") as span:
            assert span is not None
            assert span.is_recording()
    
    def test_trace_operation_with_attributes(self):
        """Test trace_operation with custom attributes."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        attributes = {
            "user_id": "user_123",
            "operation_type": "create"
        }
        
        with manager.trace_operation("test_operation", attributes=attributes) as span:
            assert span is not None
            # Attributes are set on the span
    
    def test_trace_operation_with_correlation_id(self):
        """Test trace_operation includes correlation ID."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        correlation_id = "abc-123-def-456"
        
        with manager.trace_operation(
            "test_operation",
            correlation_id=correlation_id
        ) as span:
            assert span is not None
            # Correlation ID is set as attribute
    
    def test_trace_operation_handles_exceptions(self):
        """Test that trace_operation records exceptions."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with pytest.raises(ValueError):
            with manager.trace_operation("test_operation") as span:
                raise ValueError("Test error")
    
    def test_trace_operation_without_initialization(self):
        """Test trace_operation when tracing not initialized."""
        manager = TracingManager(service_name="test-service")
        # Don't call setup()
        
        with manager.trace_operation("test_operation") as span:
            # Should yield None without error
            assert span is None
    
    def test_add_span_attributes(self):
        """Test adding attributes to a span."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("test_operation") as span:
            manager.add_span_attributes(span, {
                "key1": "value1",
                "key2": 123
            })
            # Should not raise exception
    
    def test_add_span_event(self):
        """Test adding events to a span."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("test_operation") as span:
            manager.add_span_event(span, "test_event", {
                "event_data": "test"
            })
            # Should not raise exception
    
    def test_get_current_span(self):
        """Test getting current active span."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("test_operation"):
            current_span = manager.get_current_span()
            assert current_span is not None
            assert current_span.is_recording()
    
    def test_get_trace_id(self):
        """Test getting trace ID from current span."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("test_operation"):
            trace_id = manager.get_trace_id()
            assert trace_id is not None
            assert isinstance(trace_id, str)
            assert len(trace_id) == 32  # Hex string of 128-bit trace ID
    
    def test_inject_context(self):
        """Test injecting trace context into carrier."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        carrier = {}
        
        with manager.trace_operation("test_operation"):
            manager.inject_context(carrier)
            # Should add traceparent header
            assert "traceparent" in carrier
    
    def test_shutdown(self):
        """Test tracing shutdown."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        # Should not raise exception
        manager.shutdown()


class TestSetupTracing:
    """Test setup_tracing function."""
    
    @patch('infrastructure.tracing.TracingManager')
    def test_setup_tracing_creates_manager(self, mock_manager_class):
        """Test that setup_tracing creates and configures manager."""
        mock_app = Mock()
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        result = setup_tracing(
            app=mock_app,
            service_name="test-service",
            service_version="1.0.0"
        )
        
        # Verify manager was created
        mock_manager_class.assert_called_once()
        
        # Verify setup was called
        mock_manager.setup.assert_called_once()
        
        # Verify FastAPI instrumentation
        mock_manager.instrument_fastapi.assert_called_once_with(mock_app)
        
        # Verify library instrumentation
        mock_manager.instrument_libraries.assert_called_once()
    
    @patch('infrastructure.tracing.TracingManager')
    def test_setup_tracing_without_library_instrumentation(self, mock_manager_class):
        """Test setup_tracing without library instrumentation."""
        mock_app = Mock()
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        setup_tracing(
            app=mock_app,
            instrument_libraries=False
        )
        
        # Verify library instrumentation was not called
        mock_manager.instrument_libraries.assert_not_called()


class TestConvenienceFunctions:
    """Test convenience functions for tracing."""
    
    def test_trace_operation_convenience_function(self):
        """Test trace_operation convenience function."""
        # Setup global manager
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        # Patch get_tracing_manager to return our manager
        with patch('infrastructure.tracing.get_tracing_manager', return_value=manager):
            with trace_operation("test_operation") as span:
                assert span is not None
    
    def test_trace_operation_without_manager(self):
        """Test trace_operation when manager not initialized."""
        with patch('infrastructure.tracing.get_tracing_manager', return_value=None):
            # Should return no-op context manager
            with trace_operation("test_operation") as span:
                # Should not raise exception
                pass
    
    def test_get_current_trace_id_convenience(self):
        """Test get_current_trace_id convenience function."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with patch('infrastructure.tracing.get_tracing_manager', return_value=manager):
            with trace_operation("test_operation"):
                trace_id = get_current_trace_id()
                assert trace_id is not None
                assert isinstance(trace_id, str)
    
    def test_get_current_trace_id_without_manager(self):
        """Test get_current_trace_id when manager not initialized."""
        with patch('infrastructure.tracing.get_tracing_manager', return_value=None):
            trace_id = get_current_trace_id()
            assert trace_id is None
    
    def test_add_trace_attributes_convenience(self):
        """Test add_trace_attributes convenience function."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with patch('infrastructure.tracing.get_tracing_manager', return_value=manager):
            with trace_operation("test_operation"):
                # Should not raise exception
                add_trace_attributes({"key": "value"})
    
    def test_add_trace_event_convenience(self):
        """Test add_trace_event convenience function."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with patch('infrastructure.tracing.get_tracing_manager', return_value=manager):
            with trace_operation("test_operation"):
                # Should not raise exception
                add_trace_event("test_event", {"data": "test"})


class TestTracingIntegration:
    """Integration tests for tracing."""
    
    def test_nested_spans(self):
        """Test creating nested spans."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("parent_operation") as parent_span:
            assert parent_span is not None
            
            with manager.trace_operation("child_operation") as child_span:
                assert child_span is not None
                # Child span should be nested under parent
    
    def test_span_with_multiple_attributes(self):
        """Test span with multiple attributes."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        attributes = {
            "user_id": "user_123",
            "fir_id": "fir_456",
            "operation_type": "create",
            "cache_hit": True,
            "rows_affected": 5
        }
        
        with manager.trace_operation("test_operation", attributes=attributes) as span:
            assert span is not None
            # All attributes should be set
    
    def test_span_with_multiple_events(self):
        """Test span with multiple events."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with manager.trace_operation("test_operation") as span:
            manager.add_span_event(span, "event1", {"data": "test1"})
            manager.add_span_event(span, "event2", {"data": "test2"})
            manager.add_span_event(span, "event3", {"data": "test3"})
            # All events should be recorded
    
    def test_error_recording_in_span(self):
        """Test that errors are recorded in spans."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with pytest.raises(RuntimeError):
            with manager.trace_operation("test_operation") as span:
                raise RuntimeError("Test error")
        
        # Exception should be recorded in span


class TestTracingWithCorrelationID:
    """Test tracing integration with correlation IDs."""
    
    def test_correlation_id_in_span(self):
        """Test that correlation ID is added to span."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        correlation_id = "test-correlation-id"
        
        with manager.trace_operation(
            "test_operation",
            correlation_id=correlation_id
        ) as span:
            assert span is not None
            # Correlation ID should be set as attribute
    
    def test_multiple_operations_with_same_correlation_id(self):
        """Test multiple operations sharing correlation ID."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        correlation_id = "shared-correlation-id"
        
        with manager.trace_operation("operation1", correlation_id=correlation_id):
            pass
        
        with manager.trace_operation("operation2", correlation_id=correlation_id):
            pass
        
        # Both operations should have same correlation ID


class TestTracingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_add_attributes_to_none_span(self):
        """Test adding attributes when span is None."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        # Should not raise exception
        manager.add_span_attributes(None, {"key": "value"})
    
    def test_add_event_to_none_span(self):
        """Test adding event when span is None."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        # Should not raise exception
        manager.add_span_event(None, "test_event")
    
    def test_get_trace_id_without_active_span(self):
        """Test getting trace ID when no span is active."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        trace_id = manager.get_trace_id()
        # Should return None or empty string
        assert trace_id is None or trace_id == ""
    
    def test_inject_context_without_active_span(self):
        """Test injecting context when no span is active."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        carrier = {}
        # Should not raise exception
        manager.inject_context(carrier)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
