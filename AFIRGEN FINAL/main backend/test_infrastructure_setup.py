"""
Test infrastructure setup for backend optimization.

This test verifies that all infrastructure components are properly configured
and can be imported without errors.
"""

import pytest


def test_config_import():
    """Test that configuration module can be imported."""
    from infrastructure.config import config, RedisConfig, CeleryConfig, PrometheusConfig, LoggingConfig
    
    assert config is not None
    assert isinstance(config.redis, RedisConfig)
    assert isinstance(config.celery, CeleryConfig)
    assert isinstance(config.prometheus, PrometheusConfig)
    assert isinstance(config.logging, LoggingConfig)


def test_redis_config():
    """Test Redis configuration defaults."""
    from infrastructure.config import RedisConfig
    
    redis_config = RedisConfig()
    assert redis_config.host == "localhost"
    assert redis_config.port == 6379
    assert redis_config.db == 0
    assert redis_config.max_connections == 50
    assert redis_config.decode_responses is True
    
    # Test URL generation
    url = redis_config.url
    assert "redis://" in url
    assert "localhost:6379" in url


def test_celery_config():
    """Test Celery configuration defaults."""
    from infrastructure.config import CeleryConfig
    
    celery_config = CeleryConfig()
    assert celery_config.task_serializer == "json"
    assert celery_config.result_serializer == "json"
    assert celery_config.timezone == "UTC"
    assert celery_config.enable_utc is True
    assert celery_config.task_track_started is True
    assert "json" in celery_config.accept_content


def test_prometheus_config():
    """Test Prometheus configuration defaults."""
    from infrastructure.config import PrometheusConfig
    
    prometheus_config = PrometheusConfig()
    assert prometheus_config.enabled is True
    assert prometheus_config.port == 9090
    assert prometheus_config.metrics_path == "/metrics"


def test_logging_config():
    """Test logging configuration defaults."""
    from infrastructure.config import LoggingConfig
    
    logging_config = LoggingConfig()
    assert logging_config.level == "INFO"
    assert logging_config.format == "json"
    assert logging_config.service_name == "afirgen-backend"
    assert "password" in logging_config.sensitive_fields
    assert "token" in logging_config.sensitive_fields


def test_redis_client_import():
    """Test that Redis client module can be imported."""
    from infrastructure.redis_client import RedisClient, get_redis_client
    
    assert RedisClient is not None
    assert get_redis_client is not None


def test_celery_app_import():
    """Test that Celery app module can be imported."""
    from infrastructure.celery_app import celery_app, create_celery_app
    
    assert celery_app is not None
    assert create_celery_app is not None
    assert celery_app.conf.task_serializer == "json"


def test_logging_import():
    """Test that logging module can be imported."""
    from infrastructure.logging import get_logger, StructuredLogger, configure_logging
    
    assert get_logger is not None
    assert StructuredLogger is not None
    assert configure_logging is not None


def test_metrics_import():
    """Test that metrics module can be imported."""
    from infrastructure.metrics import (
        MetricsCollector,
        track_request_duration,
        api_request_count,
        cache_operations,
        db_query_count
    )
    
    assert MetricsCollector is not None
    assert track_request_duration is not None
    assert api_request_count is not None
    assert cache_operations is not None
    assert db_query_count is not None


def test_logger_creation():
    """Test that logger can be created."""
    from infrastructure.logging import get_logger
    
    logger = get_logger("test")
    assert logger is not None
    
    # Test with context
    logger_with_context = logger.with_context(test_id="123")
    assert logger_with_context is not None


def test_metrics_collector_methods():
    """Test that MetricsCollector has required methods."""
    from infrastructure.metrics import MetricsCollector
    
    assert hasattr(MetricsCollector, "record_request_duration")
    assert hasattr(MetricsCollector, "record_db_query_duration")
    assert hasattr(MetricsCollector, "record_cache_operation")
    assert hasattr(MetricsCollector, "record_model_server_latency")
    assert hasattr(MetricsCollector, "update_system_metrics")
    assert hasattr(MetricsCollector, "get_metrics")


def test_sensitive_data_redaction():
    """Test that sensitive data redaction works."""
    from infrastructure.logging import redact_sensitive_fields
    
    event_dict = {
        "message": "User login",
        "password": "secret123",
        "token": "abc-def-ghi",
        "user_id": "123"
    }
    
    redacted = redact_sensitive_fields(None, None, event_dict)
    
    assert redacted["password"] == "***REDACTED***"
    assert redacted["token"] == "***REDACTED***"
    assert redacted["user_id"] == "123"  # Not sensitive


def test_track_request_duration_context_manager():
    """Test that track_request_duration context manager works."""
    from infrastructure.metrics import track_request_duration
    
    with track_request_duration("/test", "GET") as tracker:
        assert tracker is not None
        tracker.set_status(200)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
