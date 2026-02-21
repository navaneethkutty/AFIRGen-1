"""
OpenTelemetry tracing integration for distributed tracing.

This module configures OpenTelemetry with trace context propagation,
automatic instrumentation for FastAPI, and manual tracing for critical paths.
"""

from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
import structlog

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .config import config

logger = structlog.get_logger(__name__)


class TracingManager:
    """
    Manages OpenTelemetry tracing configuration and operations.
    
    Provides:
    - Automatic instrumentation for FastAPI, HTTP clients, Redis, MySQL, Celery
    - Manual tracing for critical paths
    - Trace context propagation
    - Integration with correlation IDs
    """
    
    def __init__(
        self,
        service_name: str = "afirgen-backend",
        service_version: str = "1.0.0",
        otlp_endpoint: Optional[str] = None,
        enable_console_export: bool = False
    ):
        """
        Initialize tracing manager.
        
        Args:
            service_name: Name of the service for trace identification
            service_version: Version of the service
            otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
            enable_console_export: Whether to export traces to console for debugging
        """
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_export = enable_console_export
        self._tracer: Optional[trace.Tracer] = None
        self._provider: Optional[TracerProvider] = None
        self._propagator = TraceContextTextMapPropagator()
        
    def setup(self) -> None:
        """
        Configure OpenTelemetry tracing with providers and exporters.
        """
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
        })
        
        # Create tracer provider
        self._provider = TracerProvider(resource=resource)
        
        # Add span processors
        if self.otlp_endpoint:
            # Export to OTLP collector (e.g., Jaeger, Tempo, etc.)
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            self._provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("OpenTelemetry OTLP exporter configured", endpoint=self.otlp_endpoint)
        
        if self.enable_console_export:
            # Export to console for debugging
            console_exporter = ConsoleSpanExporter()
            self._provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("OpenTelemetry console exporter enabled")
        
        # Set global tracer provider
        trace.set_tracer_provider(self._provider)
        
        # Get tracer instance
        self._tracer = trace.get_tracer(__name__)
        
        logger.info("OpenTelemetry tracing initialized", service=self.service_name)
    
    def instrument_fastapi(self, app) -> None:
        """
        Add automatic instrumentation for FastAPI application.
        
        Args:
            app: FastAPI application instance
        """
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    
    def instrument_libraries(self) -> None:
        """
        Add automatic instrumentation for common libraries.
        """
        # Instrument HTTP client
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
        
        # Instrument Redis
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
        
        # Instrument MySQL
        MySQLInstrumentor().instrument()
        logger.info("MySQL instrumentation enabled")
        
        # Instrument Celery
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumentation enabled")
    
    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Context manager for manual tracing of operations.
        
        Args:
            operation_name: Name of the operation being traced
            attributes: Additional attributes to add to the span
            correlation_id: Correlation ID to link with logs
            
        Yields:
            The created span for additional customization
            
        Example:
            with tracing_manager.trace_operation("database_query", {"query": "SELECT ..."}) as span:
                result = execute_query()
                span.set_attribute("rows_returned", len(result))
        """
        if not self._tracer:
            # Tracing not initialized, yield None
            yield None
            return
        
        with self._tracer.start_as_current_span(operation_name) as span:
            try:
                # Add correlation ID if provided
                if correlation_id:
                    span.set_attribute("correlation_id", correlation_id)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                yield span
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    def add_span_attributes(self, span: Optional[Span], attributes: Dict[str, Any]) -> None:
        """
        Add attributes to an existing span.
        
        Args:
            span: The span to add attributes to
            attributes: Dictionary of attributes to add
        """
        if span and span.is_recording():
            for key, value in attributes.items():
                span.set_attribute(key, value)
    
    def add_span_event(self, span: Optional[Span], name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to an existing span.
        
        Args:
            span: The span to add the event to
            name: Name of the event
            attributes: Optional attributes for the event
        """
        if span and span.is_recording():
            span.add_event(name, attributes or {})
    
    def get_current_span(self) -> Optional[Span]:
        """
        Get the current active span.
        
        Returns:
            The current span or None if no span is active
        """
        return trace.get_current_span()
    
    def get_trace_id(self) -> Optional[str]:
        """
        Get the trace ID of the current span.
        
        Returns:
            The trace ID as a hex string or None if no span is active
        """
        span = self.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
        return None
    
    def inject_context(self, carrier: Dict[str, str]) -> None:
        """
        Inject trace context into a carrier (e.g., HTTP headers).
        
        Args:
            carrier: Dictionary to inject context into (will be modified)
        """
        self._propagator.inject(carrier)
    
    def extract_context(self, carrier: Dict[str, str]) -> None:
        """
        Extract trace context from a carrier (e.g., HTTP headers).
        
        Args:
            carrier: Dictionary containing trace context
        """
        return self._propagator.extract(carrier)
    
    def shutdown(self) -> None:
        """
        Shutdown tracing and flush remaining spans.
        """
        if self._provider:
            self._provider.shutdown()
            logger.info("OpenTelemetry tracing shutdown")


# Global tracing manager instance
_tracing_manager: Optional[TracingManager] = None


def get_tracing_manager() -> Optional[TracingManager]:
    """
    Get the global tracing manager instance.
    
    Returns:
        The tracing manager or None if not initialized
    """
    return _tracing_manager


def setup_tracing(
    app,
    service_name: str = "afirgen-backend",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
    instrument_libraries: bool = True
) -> TracingManager:
    """
    Setup OpenTelemetry tracing for the application.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint
        enable_console_export: Whether to export to console
        instrument_libraries: Whether to auto-instrument libraries
        
    Returns:
        The configured tracing manager
    """
    global _tracing_manager
    
    # Create and configure tracing manager
    _tracing_manager = TracingManager(
        service_name=service_name,
        service_version=service_version,
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console_export
    )
    
    # Setup tracing
    _tracing_manager.setup()
    
    # Instrument FastAPI
    _tracing_manager.instrument_fastapi(app)
    
    # Instrument libraries if requested
    if instrument_libraries:
        _tracing_manager.instrument_libraries()
    
    logger.info("Tracing setup complete")
    
    return _tracing_manager


# Convenience functions for common tracing operations

def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
):
    """
    Convenience function for tracing operations.
    
    Args:
        operation_name: Name of the operation
        attributes: Optional attributes
        correlation_id: Optional correlation ID
        
    Returns:
        Context manager for the traced operation
    """
    manager = get_tracing_manager()
    if manager:
        return manager.trace_operation(operation_name, attributes, correlation_id)
    else:
        # Return a no-op context manager if tracing not initialized
        from contextlib import nullcontext
        return nullcontext()


def get_current_trace_id() -> Optional[str]:
    """
    Get the current trace ID.
    
    Returns:
        The trace ID or None
    """
    manager = get_tracing_manager()
    if manager:
        return manager.get_trace_id()
    return None


def add_trace_attributes(attributes: Dict[str, Any]) -> None:
    """
    Add attributes to the current span.
    
    Args:
        attributes: Dictionary of attributes to add
    """
    manager = get_tracing_manager()
    if manager:
        span = manager.get_current_span()
        manager.add_span_attributes(span, attributes)


def add_trace_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.
    
    Args:
        name: Name of the event
        attributes: Optional attributes
    """
    manager = get_tracing_manager()
    if manager:
        span = manager.get_current_span()
        manager.add_span_event(span, name, attributes)
