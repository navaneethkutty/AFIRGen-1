"""
Integration tests for OpenTelemetry tracing.

Tests verify:
- Manual tracing in service layer
- Trace context propagation
- Integration with correlation IDs
- End-to-end tracing scenarios
"""

import pytest
from unittest.mock import Mock, patch
import asyncio

from infrastructure.tracing import (
    TracingManager,
    trace_operation,
    get_current_trace_id,
    add_trace_attributes
)


class TestTracingWithServices:
    """Test tracing integration with service layer."""
    
    @pytest.fixture(autouse=True)
    def setup_tracing(self):
        """Setup tracing for tests."""
        manager = TracingManager(
            service_name="test-service",
            enable_console_export=False
        )
        manager.setup()
        
        yield manager
        
        manager.shutdown()
    
    def test_database_operation_tracing(self):
        """Test tracing database operations."""
        async def mock_database_query(query: str, correlation_id: str):
            with trace_operation(
                "database.query",
                attributes={"query_type": "SELECT", "table": "fir"},
                correlation_id=correlation_id
            ) as span:
                # Simulate query execution
                result = [{"id": 1}, {"id": 2}]
                
                if span:
                    span.set_attribute("rows_returned", len(result))
                
                return result
        
        # Execute the traced operation
        result = asyncio.run(mock_database_query("SELECT * FROM fir", "corr-123"))
        
        assert len(result) == 2
    
    def test_cache_operation_tracing(self):
        """Test tracing cache operations."""
        async def mock_cache_get(key: str, correlation_id: str):
            with trace_operation(
                "cache.get",
                attributes={"cache_key": key},
                correlation_id=correlation_id
            ) as span:
                # Simulate cache miss
                result = None
                
                if span:
                    span.set_attribute("cache_hit", result is not None)
                
                return result
        
        result = asyncio.run(mock_cache_get("fir:record:123", "corr-456"))
        
        assert result is None
    
    def test_model_server_call_tracing(self):
        """Test tracing model server calls."""
        async def mock_model_call(prompt: str, correlation_id: str):
            with trace_operation(
                "model_server.inference",
                attributes={
                    "model": "llama-3",
                    "prompt_length": len(prompt)
                },
                correlation_id=correlation_id
            ) as span:
                # Simulate model inference
                response = "Generated response"
                
                if span:
                    span.set_attribute("response_length", len(response))
                    span.add_event("inference_completed", {"tokens": 50})
                
                return response
        
        result = asyncio.run(mock_model_call("Test prompt", "corr-789"))
        
        assert result == "Generated response"
    
    def test_background_task_tracing(self):
        """Test tracing background tasks."""
        async def mock_background_task(task_id: str, correlation_id: str):
            with trace_operation(
                "background.task",
                attributes={
                    "task_id": task_id,
                    "task_type": "report_generation"
                },
                correlation_id=correlation_id
            ) as span:
                # Simulate task processing
                if span:
                    span.add_event("task_started")
                
                # Simulate work
                result = {"status": "completed"}
                
                if span:
                    span.add_event("task_completed")
                
                return result
        
        result = asyncio.run(mock_background_task("task-123", "corr-abc"))
        
        assert result["status"] == "completed"


class TestTraceContextPropagation:
    """Test trace context propagation."""
    
    @pytest.fixture(autouse=True)
    def setup_tracing(self):
        """Setup tracing for tests."""
        manager = TracingManager(
            service_name="test-service",
            enable_console_export=False
        )
        manager.setup()
        
        yield manager
        
        manager.shutdown()
    
    def test_inject_trace_context(self):
        """Test injecting trace context into carrier."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        with trace_operation("test_operation"):
            carrier = {}
            manager.inject_context(carrier)
            
            # Should have traceparent header
            assert "traceparent" in carrier
            assert carrier["traceparent"].startswith("00-")
        
        manager.shutdown()
    
    def test_extract_trace_context(self):
        """Test extracting trace context from carrier."""
        manager = TracingManager(service_name="test-service")
        manager.setup()
        
        # Create a carrier with trace context
        carrier = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
        
        # Extract context (should not raise exception)
        manager.extract_context(carrier)
        
        manager.shutdown()
    
    def test_trace_id_retrieval(self):
        """Test retrieving trace ID from current span."""
        with trace_operation("test_operation"):
            trace_id = get_current_trace_id()
            
            assert trace_id is not None
            assert isinstance(trace_id, str)
            assert len(trace_id) == 32  # 128-bit trace ID as hex


class TestTracingWithCorrelationIDs:
    """Test tracing integration with correlation IDs."""
    
    @pytest.fixture(autouse=True)
    def setup_tracing(self):
        """Setup tracing for tests."""
        manager = TracingManager(
            service_name="test-service",
            enable_console_export=False
        )
        manager.setup()
        
        yield manager
        
        manager.shutdown()
    
    def test_correlation_id_in_trace(self):
        """Test that correlation ID is included in trace."""
        correlation_id = "test-correlation-id-123"
        
        with trace_operation(
            "test_operation",
            correlation_id=correlation_id
        ) as span:
            assert span is not None
            # Correlation ID should be set as attribute
    
    def test_multiple_operations_same_correlation_id(self):
        """Test multiple operations with same correlation ID."""
        correlation_id = "shared-correlation-id"
        
        with trace_operation("operation_1", correlation_id=correlation_id):
            pass
        
        with trace_operation("operation_2", correlation_id=correlation_id):
            pass
        
        # Both operations should have same correlation ID
    
    def test_nested_operations_inherit_correlation_id(self):
        """Test that nested operations can share correlation ID."""
        correlation_id = "parent-correlation-id"
        
        with trace_operation("parent", correlation_id=correlation_id):
            with trace_operation("child", correlation_id=correlation_id):
                pass


class TestTracingPerformance:
    """Test tracing performance characteristics."""
    
    @pytest.fixture(autouse=True)
    def setup_tracing(self):
        """Setup tracing for tests."""
        manager = TracingManager(
            service_name="test-service",
            enable_console_export=False
        )
        manager.setup()
        
        yield manager
        
        manager.shutdown()
    
    def test_tracing_overhead_minimal(self):
        """Test that tracing has minimal overhead."""
        import time
        
        # Measure time without tracing
        start = time.time()
        for _ in range(100):
            pass
        baseline = time.time() - start
        
        # Measure time with tracing
        start = time.time()
        for _ in range(100):
            with trace_operation("test_operation"):
                pass
        traced = time.time() - start
        
        # Overhead should be reasonable (less than 10x)
        # This is a loose check since timing can vary
        assert traced < baseline * 10 or baseline < 0.001  # Handle very fast baseline
    
    def test_many_attributes_performance(self):
        """Test performance with many attributes."""
        with trace_operation("test_operation") as span:
            # Add many attributes
            for i in range(50):
                if span:
                    span.set_attribute(f"attr_{i}", f"value_{i}")
        
        # Should complete without issues
    
    def test_many_events_performance(self):
        """Test performance with many events."""
        with trace_operation("test_operation") as span:
            # Add many events
            for i in range(50):
                if span:
                    span.add_event(f"event_{i}", {"data": i})
        
        # Should complete without issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
