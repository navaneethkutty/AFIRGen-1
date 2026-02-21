"""
Prometheus metrics collection and monitoring.

This module provides metrics collection for API requests, database queries,
cache operations, and system resources.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from typing import Optional
import time
import psutil
from .config import config
from .alerting import alert_manager, MetricType


# API Metrics
api_request_count = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status"]
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["endpoint", "method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

api_request_in_progress = Gauge(
    "api_requests_in_progress",
    "Number of API requests currently being processed",
    ["endpoint", "method"]
)


# Database Metrics
db_query_count = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["query_type", "table"]
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size"
)

db_connection_pool_available = Gauge(
    "db_connection_pool_available",
    "Number of available connections in the pool"
)


# Cache Metrics
cache_operations = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "result"]  # result: hit, miss, error
)

cache_operation_duration = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
)

cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate percentage"
)

cache_memory_usage = Gauge(
    "cache_memory_usage_bytes",
    "Cache memory usage in bytes"
)

cache_evictions = Counter(
    "cache_evictions_total",
    "Total number of cache evictions"
)


# Model Server Metrics
model_server_requests = Counter(
    "model_server_requests_total",
    "Total number of model server requests",
    ["server", "status"]
)

model_server_latency = Histogram(
    "model_server_latency_seconds",
    "Model server request latency in seconds",
    ["server"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

model_server_availability = Gauge(
    "model_server_availability",
    "Model server availability (1=up, 0=down)",
    ["server"]
)


# Background Task Metrics
background_tasks_queued = Gauge(
    "background_tasks_queued",
    "Number of background tasks in queue",
    ["queue", "priority"]
)

background_tasks_processed = Counter(
    "background_tasks_processed_total",
    "Total number of background tasks processed",
    ["task_type", "status"]
)

background_task_duration = Histogram(
    "background_task_duration_seconds",
    "Background task processing duration in seconds",
    ["task_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0)
)


# System Metrics
system_cpu_percent = Gauge(
    "system_cpu_percent",
    "System CPU usage percentage"
)

system_memory_percent = Gauge(
    "system_memory_percent",
    "System memory usage percentage"
)

system_disk_io_read_bytes = Counter(
    "system_disk_io_read_bytes_total",
    "Total disk I/O read bytes"
)

system_disk_io_write_bytes = Counter(
    "system_disk_io_write_bytes_total",
    "Total disk I/O write bytes"
)

system_network_sent_bytes = Counter(
    "system_network_sent_bytes_total",
    "Total network bytes sent"
)

system_network_recv_bytes = Counter(
    "system_network_recv_bytes_total",
    "Total network bytes received"
)


class MetricsCollector:
    """Centralized metrics collection interface."""
    
    # Track cache hits and misses for hit rate calculation
    _cache_hits = 0
    _cache_misses = 0
    _cache_total = 0
    
    @staticmethod
    def record_request_duration(endpoint: str, method: str, duration: float, status: int):
        """Record API request metrics."""
        api_request_count.labels(endpoint=endpoint, method=method, status=status).inc()
        api_request_duration.labels(endpoint=endpoint, method=method).observe(duration)
    
    @staticmethod
    def record_db_query_duration(query_type: str, table: str, duration: float):
        """Record database query metrics."""
        db_query_count.labels(query_type=query_type, table=table).inc()
        db_query_duration.labels(query_type=query_type, table=table).observe(duration)
    
    @staticmethod
    def record_cache_operation(operation: str, hit: bool, duration: Optional[float] = None):
        """
        Record cache operation metrics.
        
        Validates: Requirements 5.4
        """
        result = "hit" if hit else "miss"
        cache_operations.labels(operation=operation, result=result).inc()
        if duration is not None:
            cache_operation_duration.labels(operation=operation).observe(duration)
        
        # Update hit rate tracking for 'get' operations
        if operation == "get":
            if hit:
                MetricsCollector._cache_hits += 1
            else:
                MetricsCollector._cache_misses += 1
            MetricsCollector._cache_total += 1
            
            # Update hit rate gauge
            if MetricsCollector._cache_total > 0:
                hit_rate = (MetricsCollector._cache_hits / MetricsCollector._cache_total) * 100
                cache_hit_rate.set(hit_rate)
                
                # Check cache hit rate threshold (only after sufficient samples)
                if config.alerting.enabled and MetricsCollector._cache_total >= 100:
                    alert_manager.check_metric(
                        MetricType.CACHE_HIT_RATE,
                        hit_rate,
                        metadata={"operation": operation, "total_operations": MetricsCollector._cache_total}
                    )
    
    @staticmethod
    def record_cache_error(operation: str):
        """Record cache error."""
        cache_operations.labels(operation=operation, result="error").inc()
    
    @staticmethod
    def record_model_server_latency(server: str, duration: float, success: bool):
        """Record model server request metrics."""
        status = "success" if success else "error"
        model_server_requests.labels(server=server, status=status).inc()
        model_server_latency.labels(server=server).observe(duration)
        
        # Check model server latency threshold
        if config.alerting.enabled and success:
            alert_manager.check_metric(
                MetricType.MODEL_SERVER_LATENCY,
                duration,
                metadata={"server": server, "status": status}
            )
    
    @staticmethod
    def update_db_pool_metrics(pool_size: int, available: int):
        """
        Update database connection pool metrics.
        
        Args:
            pool_size: Total size of the connection pool
            available: Number of available connections
            
        Validates: Requirements 5.3
        """
        db_connection_pool_size.set(pool_size)
        db_connection_pool_available.set(available)
        
        # Calculate and check pool utilization
        if config.alerting.enabled and pool_size > 0:
            utilization = ((pool_size - available) / pool_size) * 100
            alert_manager.check_metric(
                MetricType.DB_POOL_UTILIZATION,
                utilization,
                metadata={"pool_size": pool_size, "available": available}
            )
    
    @staticmethod
    def update_system_metrics():
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_percent.set(cpu_percent)
            
            # Check CPU threshold
            if config.alerting.enabled:
                alert_manager.check_metric(
                    MetricType.CPU_PERCENT,
                    cpu_percent,
                    metadata={"source": "system_metrics"}
                )
            
            # Memory usage
            memory = psutil.virtual_memory()
            system_memory_percent.set(memory.percent)
            
            # Check memory threshold
            if config.alerting.enabled:
                alert_manager.check_metric(
                    MetricType.MEMORY_PERCENT,
                    memory.percent,
                    metadata={"source": "system_metrics"}
                )
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                system_disk_io_read_bytes.inc(disk_io.read_bytes)
                system_disk_io_write_bytes.inc(disk_io.write_bytes)
            
            # Network I/O
            net_io = psutil.net_io_counters()
            if net_io:
                system_network_sent_bytes.inc(net_io.bytes_sent)
                system_network_recv_bytes.inc(net_io.bytes_recv)
        except Exception:
            # Silently fail if system metrics cannot be collected
            pass
    
    @staticmethod
    def get_metrics() -> bytes:
        """Get Prometheus metrics in exposition format."""
        return generate_latest()
    
    @staticmethod
    def get_content_type() -> str:
        """Get Prometheus metrics content type."""
        return CONTENT_TYPE_LATEST
    
    @staticmethod
    def reset_cache_hit_rate():
        """Reset cache hit rate counters (useful for testing)."""
        MetricsCollector._cache_hits = 0
        MetricsCollector._cache_misses = 0
        MetricsCollector._cache_total = 0
        cache_hit_rate.set(0)


# Context manager for tracking request duration
class track_request_duration:
    """Context manager to track API request duration."""
    
    def __init__(self, endpoint: str, method: str):
        self.endpoint = endpoint
        self.method = method
        self.start_time = None
        self.status = None
    
    def __enter__(self):
        self.start_time = time.time()
        api_request_in_progress.labels(endpoint=self.endpoint, method=self.method).inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        api_request_in_progress.labels(endpoint=self.endpoint, method=self.method).dec()
        
        # Determine status code
        if exc_type is None:
            status = self.status or 200
        else:
            status = 500
        
        MetricsCollector.record_request_duration(
            self.endpoint,
            self.method,
            duration,
            status
        )
        
        # Check response time threshold
        if config.alerting.enabled:
            alert_manager.check_metric(
                MetricType.RESPONSE_TIME,
                duration,
                metadata={"endpoint": self.endpoint, "method": self.method, "status": status}
            )
    
    def set_status(self, status: int):
        """Set the response status code."""
        self.status = status
