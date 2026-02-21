"""
Celery application setup and configuration.

This module initializes the Celery application for background task processing
with Redis as the message broker. It configures task routing, prioritization,
and worker concurrency settings.

Task Queues and Priorities:
- email: Priority 3 (low) - Email notifications
- reports: Priority 5 (medium) - Report generation
- analytics: Priority 2 (low) - Analytics processing
- cleanup: Priority 1 (lowest) - Cleanup jobs
- default: Priority 5 (medium) - Default queue for unrouted tasks

Worker Concurrency:
- Prefetch multiplier: 4 (workers prefetch 4 tasks per process)
- Max tasks per child: 1000 (worker process restarts after 1000 tasks)
- Task acknowledgment: Late (task acknowledged after completion)

Requirements: 4.1, 4.5
"""

from celery import Celery
from kombu import Queue, Exchange
from .config import config


def create_celery_app() -> Celery:
    """
    Create and configure Celery application with Redis broker.
    
    Configures:
    - Task routing to different queues based on task type
    - Task prioritization (1-10 scale, higher = more important)
    - Worker concurrency settings for optimal performance
    - Retry and acknowledgment behavior
    
    Returns:
        Celery: Configured Celery application instance
    """
    app = Celery(
        "afirgen_tasks",
        broker=config.celery.broker_url,
        backend=config.celery.result_backend
    )
    
    # Define task queues with priority support
    task_queues = (
        Queue(
            "default",
            Exchange("default"),
            routing_key="default",
            queue_arguments={"x-max-priority": 10}
        ),
        Queue(
            "email",
            Exchange("email"),
            routing_key="email",
            queue_arguments={"x-max-priority": 10}
        ),
        Queue(
            "reports",
            Exchange("reports"),
            routing_key="reports",
            queue_arguments={"x-max-priority": 10}
        ),
        Queue(
            "analytics",
            Exchange("analytics"),
            routing_key="analytics",
            queue_arguments={"x-max-priority": 10}
        ),
        Queue(
            "cleanup",
            Exchange("cleanup"),
            routing_key="cleanup",
            queue_arguments={"x-max-priority": 10}
        ),
    )
    
    # Configure Celery
    app.conf.update(
        # Serialization
        task_serializer=config.celery.task_serializer,
        result_serializer=config.celery.result_serializer,
        accept_content=config.celery.accept_content,
        
        # Timezone
        timezone=config.celery.timezone,
        enable_utc=config.celery.enable_utc,
        
        # Task execution
        task_track_started=config.celery.task_track_started,
        task_time_limit=config.celery.task_time_limit,
        task_soft_time_limit=config.celery.task_soft_time_limit,
        
        # Worker concurrency settings
        worker_prefetch_multiplier=config.celery.worker_prefetch_multiplier,
        worker_max_tasks_per_child=config.celery.worker_max_tasks_per_child,
        worker_disable_rate_limits=False,
        worker_pool=config.celery.worker_pool,
        worker_concurrency=config.celery.worker_concurrency,
        
        # Task queues and routing
        task_queues=task_queues,
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
        task_routes={
            "afirgen_tasks.email.*": {
                "queue": "email",
                "routing_key": "email",
                "priority": 3
            },
            "afirgen_tasks.reports.*": {
                "queue": "reports",
                "routing_key": "reports",
                "priority": 5
            },
            "afirgen_tasks.analytics.*": {
                "queue": "analytics",
                "routing_key": "analytics",
                "priority": 2
            },
            "afirgen_tasks.cleanup.*": {
                "queue": "cleanup",
                "routing_key": "cleanup",
                "priority": 1
            },
        },
        
        # Retry and acknowledgment configuration
        task_acks_late=True,  # Acknowledge after task completion
        task_reject_on_worker_lost=True,  # Requeue if worker dies
        task_acks_on_failure_or_timeout=True,  # Acknowledge failed tasks
        
        # Result backend settings
        result_expires=3600,  # Results expire after 1 hour
        result_extended=True,  # Store additional task metadata
        result_backend_transport_options={
            "master_name": "mymaster",
            "visibility_timeout": 3600,
        },
        
        # Broker connection settings
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        
        # Task priority support
        task_inherit_parent_priority=True,
        task_default_priority=5,
    )
    
    return app


# Global Celery app instance
celery_app = create_celery_app()


# Auto-discover tasks from tasks module
celery_app.autodiscover_tasks(["infrastructure.tasks"])
