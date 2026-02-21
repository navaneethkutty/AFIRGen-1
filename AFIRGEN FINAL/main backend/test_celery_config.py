"""
Unit tests for Celery task queue configuration.

Tests verify that Celery is properly configured with Redis broker,
task routing, prioritization, and worker concurrency settings.

Requirements: 4.1, 4.5
"""

import pytest
from unittest.mock import Mock, patch
from infrastructure.celery_app import create_celery_app, celery_app
from infrastructure.config import config


class TestCeleryConfiguration:
    """Test Celery application configuration."""
    
    def test_celery_app_creation(self):
        """Test that Celery app is created successfully."""
        app = create_celery_app()
        assert app is not None
        assert app.main == "afirgen_tasks"
    
    def test_broker_configuration(self):
        """Test that broker URL is configured correctly."""
        app = create_celery_app()
        assert app.conf.broker_url == config.celery.broker_url
        assert "redis://" in app.conf.broker_url
    
    def test_result_backend_configuration(self):
        """Test that result backend is configured correctly."""
        app = create_celery_app()
        assert app.conf.result_backend == config.celery.result_backend
        assert "redis://" in app.conf.result_backend
    
    def test_task_serialization_settings(self):
        """Test that task serialization is configured correctly."""
        app = create_celery_app()
        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert "json" in app.conf.accept_content
    
    def test_timezone_configuration(self):
        """Test that timezone settings are correct."""
        app = create_celery_app()
        assert app.conf.timezone == "UTC"
        assert app.conf.enable_utc is True
    
    def test_task_tracking_enabled(self):
        """Test that task tracking is enabled."""
        app = create_celery_app()
        assert app.conf.task_track_started is True
    
    def test_task_time_limits(self):
        """Test that task time limits are configured."""
        app = create_celery_app()
        assert app.conf.task_time_limit == config.celery.task_time_limit
        assert app.conf.task_soft_time_limit == config.celery.task_soft_time_limit
        assert app.conf.task_soft_time_limit < app.conf.task_time_limit
    
    def test_worker_prefetch_multiplier(self):
        """Test that worker prefetch multiplier is configured."""
        app = create_celery_app()
        assert app.conf.worker_prefetch_multiplier == config.celery.worker_prefetch_multiplier
        assert app.conf.worker_prefetch_multiplier > 0
    
    def test_worker_max_tasks_per_child(self):
        """Test that worker max tasks per child is configured."""
        app = create_celery_app()
        assert app.conf.worker_max_tasks_per_child == config.celery.worker_max_tasks_per_child
        assert app.conf.worker_max_tasks_per_child > 0
    
    def test_worker_pool_configuration(self):
        """Test that worker pool type is configured."""
        app = create_celery_app()
        assert app.conf.worker_pool == config.celery.worker_pool
        assert app.conf.worker_pool in ["prefork", "solo", "threads", "gevent"]
    
    def test_worker_concurrency_configuration(self):
        """Test that worker concurrency is configured."""
        app = create_celery_app()
        assert app.conf.worker_concurrency == config.celery.worker_concurrency
        assert app.conf.worker_concurrency > 0
    
    def test_task_queues_defined(self):
        """Test that task queues are properly defined."""
        app = create_celery_app()
        assert app.conf.task_queues is not None
        
        # Check that all expected queues are defined
        queue_names = [q.name for q in app.conf.task_queues]
        assert "default" in queue_names
        assert "email" in queue_names
        assert "reports" in queue_names
        assert "analytics" in queue_names
        assert "cleanup" in queue_names
    
    def test_task_queue_priorities(self):
        """Test that task queues have correct priorities via routing."""
        app = create_celery_app()
        
        # Verify priorities are set in task routes
        routes = app.conf.task_routes
        
        # Verify priorities match design
        assert routes["afirgen_tasks.email.*"]["priority"] == 3  # low
        assert routes["afirgen_tasks.reports.*"]["priority"] == 5  # medium
        assert routes["afirgen_tasks.analytics.*"]["priority"] == 2  # low
        assert routes["afirgen_tasks.cleanup.*"]["priority"] == 1  # lowest
        
        # Default priority
        assert app.conf.task_default_priority == 5  # medium
    
    def test_task_queue_max_priority(self):
        """Test that queues support priority range 1-10."""
        app = create_celery_app()
        
        for queue in app.conf.task_queues:
            assert "x-max-priority" in queue.queue_arguments
            assert queue.queue_arguments["x-max-priority"] == 10
    
    def test_task_routing_configuration(self):
        """Test that task routing is configured correctly."""
        app = create_celery_app()
        assert app.conf.task_routes is not None
        
        # Check routing patterns
        routes = app.conf.task_routes
        assert "afirgen_tasks.email.*" in routes
        assert "afirgen_tasks.reports.*" in routes
        assert "afirgen_tasks.analytics.*" in routes
        assert "afirgen_tasks.cleanup.*" in routes
    
    def test_email_task_routing(self):
        """Test that email tasks are routed to email queue with priority 3."""
        app = create_celery_app()
        route = app.conf.task_routes["afirgen_tasks.email.*"]
        assert route["queue"] == "email"
        assert route["routing_key"] == "email"
        assert route["priority"] == 3
    
    def test_reports_task_routing(self):
        """Test that report tasks are routed to reports queue with priority 5."""
        app = create_celery_app()
        route = app.conf.task_routes["afirgen_tasks.reports.*"]
        assert route["queue"] == "reports"
        assert route["routing_key"] == "reports"
        assert route["priority"] == 5
    
    def test_analytics_task_routing(self):
        """Test that analytics tasks are routed to analytics queue with priority 2."""
        app = create_celery_app()
        route = app.conf.task_routes["afirgen_tasks.analytics.*"]
        assert route["queue"] == "analytics"
        assert route["routing_key"] == "analytics"
        assert route["priority"] == 2
    
    def test_cleanup_task_routing(self):
        """Test that cleanup tasks are routed to cleanup queue with priority 1."""
        app = create_celery_app()
        route = app.conf.task_routes["afirgen_tasks.cleanup.*"]
        assert route["queue"] == "cleanup"
        assert route["routing_key"] == "cleanup"
        assert route["priority"] == 1
    
    def test_default_queue_configuration(self):
        """Test that default queue is configured for unrouted tasks."""
        app = create_celery_app()
        assert app.conf.task_default_queue == "default"
        assert app.conf.task_default_exchange == "default"
        assert app.conf.task_default_routing_key == "default"
    
    def test_task_acknowledgment_settings(self):
        """Test that task acknowledgment is configured for reliability."""
        app = create_celery_app()
        # Late acknowledgment: tasks acknowledged after completion
        assert app.conf.task_acks_late is True
        # Reject on worker lost: requeue tasks if worker dies
        assert app.conf.task_reject_on_worker_lost is True
        # Acknowledge failed tasks
        assert app.conf.task_acks_on_failure_or_timeout is True
    
    def test_result_backend_settings(self):
        """Test that result backend settings are configured."""
        app = create_celery_app()
        assert app.conf.result_expires == 3600  # 1 hour
        assert app.conf.result_extended is True
    
    def test_broker_connection_retry(self):
        """Test that broker connection retry is enabled."""
        app = create_celery_app()
        assert app.conf.broker_connection_retry is True
        assert app.conf.broker_connection_retry_on_startup is True
        assert app.conf.broker_connection_max_retries > 0
    
    def test_task_priority_inheritance(self):
        """Test that task priority inheritance is enabled."""
        app = create_celery_app()
        assert app.conf.task_inherit_parent_priority is True
        assert app.conf.task_default_priority == 5
    
    def test_global_celery_app_instance(self):
        """Test that global celery_app instance is available."""
        assert celery_app is not None
        assert celery_app.main == "afirgen_tasks"


class TestCeleryConfigurationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_missing_broker_url_uses_default(self):
        """Test that missing broker URL falls back to default."""
        with patch.dict('os.environ', {}, clear=True):
            from infrastructure.config import CeleryConfig
            celery_config = CeleryConfig()
            assert "redis://localhost:6379/1" in celery_config.broker_url
    
    def test_missing_result_backend_uses_default(self):
        """Test that missing result backend falls back to default."""
        with patch.dict('os.environ', {}, clear=True):
            from infrastructure.config import CeleryConfig
            celery_config = CeleryConfig()
            assert "redis://localhost:6379/2" in celery_config.result_backend
    
    def test_worker_concurrency_positive(self):
        """Test that worker concurrency is always positive."""
        app = create_celery_app()
        assert app.conf.worker_concurrency > 0
    
    def test_prefetch_multiplier_positive(self):
        """Test that prefetch multiplier is always positive."""
        app = create_celery_app()
        assert app.conf.worker_prefetch_multiplier > 0
    
    def test_max_tasks_per_child_positive(self):
        """Test that max tasks per child is always positive."""
        app = create_celery_app()
        assert app.conf.worker_max_tasks_per_child > 0


class TestCeleryTaskPrioritization:
    """Test task prioritization functionality."""
    
    def test_priority_ordering(self):
        """Test that priorities are ordered correctly (higher = more important)."""
        app = create_celery_app()
        routes = app.conf.task_routes
        
        # Extract priorities from routing configuration
        email_priority = routes["afirgen_tasks.email.*"]["priority"]
        reports_priority = routes["afirgen_tasks.reports.*"]["priority"]
        analytics_priority = routes["afirgen_tasks.analytics.*"]["priority"]
        cleanup_priority = routes["afirgen_tasks.cleanup.*"]["priority"]
        default_priority = app.conf.task_default_priority
        
        # Cleanup (1) < Analytics (2) < Email (3) < Reports/Default (5)
        assert cleanup_priority < analytics_priority
        assert analytics_priority < email_priority
        assert email_priority < reports_priority
        assert reports_priority == default_priority
    
    def test_all_queues_support_priority_range(self):
        """Test that all queues support the full priority range 1-10."""
        app = create_celery_app()
        
        for queue in app.conf.task_queues:
            max_priority = queue.queue_arguments.get("x-max-priority")
            assert max_priority == 10, f"Queue {queue.name} should support priority 1-10"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
