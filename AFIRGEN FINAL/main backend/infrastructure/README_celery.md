# Celery Task Queue Configuration

This document describes the Celery task queue setup for the AFIRGen backend optimization project.

## Overview

Celery is configured with Redis as the message broker and result backend. The system uses multiple queues with different priorities to handle various types of background tasks efficiently.

**Requirements Addressed:**
- 4.1: Async task queuing without blocking API requests
- 4.5: Task prioritization for different job types

## Architecture

### Task Queues

The system defines five task queues with different priorities:

| Queue | Priority | Purpose | Example Tasks |
|-------|----------|---------|---------------|
| `default` | 5 (medium) | Default queue for unrouted tasks | General background jobs |
| `email` | 3 (low) | Email notifications | FIR confirmation emails |
| `reports` | 5 (medium) | Report generation | PDF report generation |
| `analytics` | 2 (low) | Analytics processing | Dashboard updates |
| `cleanup` | 1 (lowest) | Cleanup jobs | Archive old records, clear cache |

### Priority System

- Priorities range from 1 (lowest) to 10 (highest)
- Higher priority tasks are processed before lower priority tasks
- Each queue has a default priority, but individual tasks can override it
- Priority inheritance: Child tasks inherit parent task priority

### Worker Concurrency

**Prefetch Multiplier (default: 4)**
- Workers prefetch 4 tasks per process to reduce broker round-trips
- Balances between task distribution and worker efficiency
- Adjust based on task duration and worker count

**Max Tasks Per Child (default: 1000)**
- Worker processes restart after executing 1000 tasks
- Prevents memory leaks from accumulating
- Ensures fresh worker state periodically

**Worker Pool (default: prefork)**
- `prefork`: Multi-process pool (recommended for CPU-bound tasks)
- `solo`: Single process (for debugging)
- `threads`: Multi-threaded pool (for I/O-bound tasks)
- `gevent`: Greenlet-based pool (for high concurrency I/O)

**Worker Concurrency (default: 4)**
- Number of worker processes/threads
- Recommended: Number of CPU cores for CPU-bound tasks
- Can be higher for I/O-bound tasks

## Configuration

### Environment Variables

```bash
# Broker and backend
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Task execution limits
CELERY_TASK_TIME_LIMIT=3600          # Hard limit: 1 hour
CELERY_TASK_SOFT_TIME_LIMIT=3300     # Soft limit: 55 minutes

# Worker concurrency
CELERY_WORKER_PREFETCH_MULTIPLIER=4  # Tasks prefetched per worker
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000  # Tasks before worker restart
CELERY_WORKER_POOL=prefork           # Worker pool type
CELERY_WORKER_CONCURRENCY=4          # Number of worker processes
```

### Task Routing

Tasks are automatically routed to queues based on their name pattern:

```python
# Email tasks → email queue (priority 3)
@celery_app.task(name="afirgen_tasks.email.send_confirmation")
def send_confirmation_email(fir_id: str):
    pass

# Report tasks → reports queue (priority 5)
@celery_app.task(name="afirgen_tasks.reports.generate_pdf")
def generate_pdf_report(fir_id: str):
    pass

# Analytics tasks → analytics queue (priority 2)
@celery_app.task(name="afirgen_tasks.analytics.update_dashboard")
def update_dashboard_stats():
    pass

# Cleanup tasks → cleanup queue (priority 1)
@celery_app.task(name="afirgen_tasks.cleanup.archive_old_records")
def archive_old_records():
    pass
```

## Starting Workers

### Start All Queues

```bash
celery -A infrastructure.celery_app worker --loglevel=info
```

### Start Specific Queue

```bash
# Email queue only
celery -A infrastructure.celery_app worker -Q email --loglevel=info

# Multiple queues
celery -A infrastructure.celery_app worker -Q email,reports --loglevel=info
```

### Production Configuration

```bash
# Start with custom concurrency
celery -A infrastructure.celery_app worker \
  --loglevel=info \
  --concurrency=8 \
  --max-tasks-per-child=1000 \
  --prefetch-multiplier=4

# Start with autoscaling (min 2, max 8 workers)
celery -A infrastructure.celery_app worker \
  --loglevel=info \
  --autoscale=8,2
```

## Task Acknowledgment

**Late Acknowledgment (task_acks_late=True)**
- Tasks are acknowledged AFTER completion, not when received
- If worker crashes, task is requeued automatically
- Ensures tasks are not lost due to worker failures

**Reject on Worker Lost (task_reject_on_worker_lost=True)**
- If worker dies unexpectedly, task is requeued
- Another worker will pick up the task
- Improves reliability

## Monitoring

### Celery Flower (Web UI)

```bash
# Install Flower
pip install flower

# Start Flower
celery -A infrastructure.celery_app flower --port=5555
```

Access at: http://localhost:5555

### Command Line Monitoring

```bash
# Active tasks
celery -A infrastructure.celery_app inspect active

# Registered tasks
celery -A infrastructure.celery_app inspect registered

# Worker stats
celery -A infrastructure.celery_app inspect stats

# Queue lengths
celery -A infrastructure.celery_app inspect active_queues
```

## Performance Tuning

### For CPU-Bound Tasks

```bash
CELERY_WORKER_POOL=prefork
CELERY_WORKER_CONCURRENCY=4  # Match CPU cores
CELERY_WORKER_PREFETCH_MULTIPLIER=1  # Reduce prefetch
```

### For I/O-Bound Tasks

```bash
CELERY_WORKER_POOL=gevent
CELERY_WORKER_CONCURRENCY=100  # Higher concurrency
CELERY_WORKER_PREFETCH_MULTIPLIER=4
```

### For Mixed Workloads

```bash
# Run separate workers for different task types
# CPU-bound worker
celery -A infrastructure.celery_app worker -Q reports --pool=prefork --concurrency=4

# I/O-bound worker
celery -A infrastructure.celery_app worker -Q email,analytics --pool=gevent --concurrency=50
```

## Best Practices

1. **Task Naming**: Use descriptive names with namespace prefixes
   - Good: `afirgen_tasks.email.send_confirmation`
   - Bad: `send_email`

2. **Task Idempotency**: Design tasks to be safely retried
   - Check if work is already done before executing
   - Use unique identifiers to prevent duplicates

3. **Task Size**: Keep tasks small and focused
   - Break large jobs into smaller tasks
   - Use task chains or groups for complex workflows

4. **Error Handling**: Handle errors gracefully
   - Use try-except blocks
   - Log errors with context
   - Return meaningful error messages

5. **Resource Management**: Clean up resources
   - Close database connections
   - Release file handles
   - Clear temporary data

6. **Monitoring**: Track task performance
   - Monitor queue lengths
   - Track task execution times
   - Alert on failures

## Troubleshooting

### Tasks Not Being Processed

1. Check if workers are running: `celery -A infrastructure.celery_app inspect active`
2. Check queue lengths: `celery -A infrastructure.celery_app inspect active_queues`
3. Verify Redis connection: `redis-cli ping`
4. Check worker logs for errors

### High Memory Usage

1. Reduce `worker_max_tasks_per_child` to restart workers more frequently
2. Reduce `worker_prefetch_multiplier` to limit prefetched tasks
3. Check for memory leaks in task code
4. Use `worker_pool=solo` for debugging

### Slow Task Processing

1. Increase `worker_concurrency` for more parallel processing
2. Add more worker instances
3. Optimize task code
4. Check for database/network bottlenecks

### Tasks Timing Out

1. Increase `CELERY_TASK_TIME_LIMIT` and `CELERY_TASK_SOFT_TIME_LIMIT`
2. Break large tasks into smaller chunks
3. Optimize task code
4. Check for external service delays

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#tips-and-best-practices)
- [Redis as Celery Broker](https://docs.celeryproject.org/en/stable/getting-started/backends-and-brokers/redis.html)
