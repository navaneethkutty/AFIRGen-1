"""
Configuration management for backend optimization infrastructure.

This module provides centralized configuration for Redis, Celery, Prometheus,
and structured logging components.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis configuration settings."""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
    socket_connect_timeout: int = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
    decode_responses: bool = True
    
    @property
    def url(self) -> str:
        """Generate Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class CeleryConfig:
    """Celery configuration settings."""
    broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: Optional[list[str]] = None
    timezone: str = "UTC"
    enable_utc: bool = True
    task_track_started: bool = True
    task_time_limit: int = int(os.getenv("CELERY_TASK_TIME_LIMIT", "3600"))  # 1 hour
    task_soft_time_limit: int = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "3300"))  # 55 minutes
    worker_prefetch_multiplier: int = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "4"))
    worker_max_tasks_per_child: int = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "1000"))
    
    # Worker concurrency settings
    worker_pool: str = os.getenv("CELERY_WORKER_POOL", "prefork")  # prefork, solo, threads, gevent
    worker_concurrency: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))  # Number of worker processes
    
    def __post_init__(self) -> None:
        if self.accept_content is None:
            self.accept_content = ["json"]


@dataclass
class PrometheusConfig:
    """Prometheus metrics configuration."""
    enabled: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    port: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    metrics_path: str = os.getenv("PROMETHEUS_METRICS_PATH", "/metrics")


@dataclass
class LoggingConfig:
    """Structured logging configuration."""
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = os.getenv("LOG_FORMAT", "json")  # json or console
    service_name: str = os.getenv("SERVICE_NAME", "afirgen-backend")
    
    # Log output destination
    output_destination: str = os.getenv("LOG_OUTPUT", "stdout")  # stdout, stderr, or file path
    
    # Per-module log levels (format: MODULE_NAME=LEVEL,MODULE_NAME2=LEVEL2)
    module_levels: Optional[dict[str, str]] = None
    
    # Sensitive fields to redact in logs
    sensitive_fields: Optional[list[str]] = None
    
    def __post_init__(self) -> None:
        if self.sensitive_fields is None:
            self.sensitive_fields = [
                "password",
                "token",
                "api_key",
                "secret",
                "authorization",
                "credit_card",
                "ssn",
                "phone",
                "email"
            ]
        
        # Parse per-module log levels from environment variable
        if self.module_levels is None:
            self.module_levels = {}
            module_levels_str = os.getenv("LOG_MODULE_LEVELS", "")
            if module_levels_str:
                for module_level in module_levels_str.split(","):
                    if "=" in module_level:
                        module, level = module_level.strip().split("=", 1)
                        self.module_levels[module.strip()] = level.strip().upper()


@dataclass
class AlertingConfig:
    """Alerting system configuration."""
    enabled: bool = os.getenv("ALERTING_ENABLED", "true").lower() == "true"
    deduplication_window: int = int(os.getenv("ALERT_DEDUPLICATION_WINDOW", "300"))  # 5 minutes
    
    # Default thresholds (can be overridden via environment variables)
    cpu_warning_threshold: float = float(os.getenv("ALERT_CPU_WARNING", "70.0"))
    cpu_critical_threshold: float = float(os.getenv("ALERT_CPU_CRITICAL", "90.0"))
    memory_warning_threshold: float = float(os.getenv("ALERT_MEMORY_WARNING", "75.0"))
    memory_critical_threshold: float = float(os.getenv("ALERT_MEMORY_CRITICAL", "90.0"))
    response_time_warning_threshold: float = float(os.getenv("ALERT_RESPONSE_TIME_WARNING", "2.0"))
    response_time_critical_threshold: float = float(os.getenv("ALERT_RESPONSE_TIME_CRITICAL", "5.0"))
    error_rate_warning_threshold: float = float(os.getenv("ALERT_ERROR_RATE_WARNING", "5.0"))
    error_rate_critical_threshold: float = float(os.getenv("ALERT_ERROR_RATE_CRITICAL", "10.0"))


@dataclass
class AppConfig:
    """Main application configuration."""
    redis: Optional[RedisConfig] = None
    celery: Optional[CeleryConfig] = None
    prometheus: Optional[PrometheusConfig] = None
    logging: Optional[LoggingConfig] = None
    alerting: Optional[AlertingConfig] = None
    
    def __post_init__(self) -> None:
        if self.redis is None:
            self.redis = RedisConfig()
        if self.celery is None:
            self.celery = CeleryConfig()
        if self.prometheus is None:
            self.prometheus = PrometheusConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.alerting is None:
            self.alerting = AlertingConfig()


# Global configuration instance
config = AppConfig()
