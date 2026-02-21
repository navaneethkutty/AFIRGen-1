# Background Task Manager

This document describes the Background Task Manager implementation for the AFIRGen backend optimization project.

## Overview

The Background Task Manager provides task enqueueing with priority support, task status tracking in the database, and REST API endpoints for querying task status.

**Requirements Addressed:**
- 4.1: Async task queuing without blocking API requests
- 4.4: Task status tracking and updates
- 4.6: Task status query endpoints

**Task:** 6.2 Create background task manager

## Architecture

### Components

1. **BackgroundTaskManager** (`infrastructure/background_task_manager.py`)
   - Manages task enqueueing with priority support
   - Tracks task status in MySQL database
   - Provides query methods for task status and listing

2. **DatabaseTask** (`infrastructure/tasks/base_task.py`)
   - Base Celery task class with automatic status tracking
   - Updates task status in database during execution lifecycle
   - Handles task start, completion, failure, and retry events

3. **Task API Endpoints** (`api/task_endpoints.py`)
   - REST API endpoints for task operations
   - Enqueue tasks, query status, list tasks, cancel tasks

4. **Database Schema** (`migrations/002_add_background_tasks_table.sql`)
   - `background_tasks` table for task metadata and status

## Database Schema

```sql
CREATE TABLE background_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    priority INT DEFAULT 5,
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled'),
    params JSON,
    result JSON,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    -- Indexes for efficient queries
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_status_priority (status, priority)
);
```

## Task Status Lifecycle

```
pending → running → completed
                 ↓
                failed (with retries) → pending (retry) → ...
                 ↓
                failed (max retries exceeded)
```

Tasks can also be cancelled at any point:
```
pending/running → cancelled
```

## Usage

### 1. Initialize Task Manager

```python
from infrastructure.background_task_manager import (
    BackgroundTaskManager,
    TaskType
)
from infrastructure.tasks.base_task import DatabaseTask

# Initialize with database pool
task_manager = BackgroundTaskManager(db_pool)

# Set database pool for automatic status tracking
DatabaseTask.set_db_pool(db_pool)
```

### 2. Enqueue Tasks

```python
# Enqueue an email task
task_id = task_manager.enqueue_task(
    task_name="afirgen_tasks.email.send_confirmation",
    task_type=TaskType.EMAIL,
    params={
        "fir_id": "fir_12345",
        "recipient_email": "user@example.com"
    },
    priority=5,  # 1-10 scale, higher = more important
    max_retries=3
)

print(f"Task enqueued: {task_id}")
```

### 3. Query Task Status

```python
# Get status of specific task
status = task_manager.get_task_status(task_id)
print(f"Task status: {status['status']}")
print(f"Result: {status['result']}")

# List all pending tasks
pending_tasks = task_manager.list_tasks(
    status=TaskStatus.PENDING,
    limit=50,
    offset=0
)

# Get count of failed tasks
failed_count = task_manager.get_task_count(status=TaskStatus.FAILED)
```

### 4. Cancel Tasks

```python
# Cancel a pending or running task
success = task_manager.cancel_task(task_id)
if success:
    print("Task cancelled successfully")
```

## API Endpoints

### POST /api/tasks/enqueue

Enqueue a new background task.

**Request:**
```json
{
  "task_name": "afirgen_tasks.email.send_confirmation",
  "task_type": "email",
  "params": {
    "fir_id": "fir_12345",
    "recipient_email": "user@example.com"
  },
  "priority": 5,
  "max_retries": 3
}
```

**Response (201):**
```json
{
  "task_id": "abc-123-def-456",
  "message": "Task enqueued successfully with priority 5"
}
```

### GET /api/tasks/{task_id}

Get status of a specific task.

**Response (200):**
```json
{
  "task_id": "abc-123-def-456",
  "task_name": "afirgen_tasks.email.send_confirmation",
  "task_type": "email",
  "priority": 5,
  "status": "completed",
  "params": {
    "fir_id": "fir_12345",
    "recipient_email": "user@example.com"
  },
  "result": {
    "status": "success",
    "message": "Email sent successfully"
  },
  "error_message": null,
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2024-01-15T10:30:00",
  "started_at": "2024-01-15T10:30:05",
  "completed_at": "2024-01-15T10:30:10"
}
```

### GET /api/tasks/

List tasks with optional filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed, cancelled)
- `task_type` (optional): Filter by type (email, report, analytics, cleanup)
- `limit` (optional): Maximum tasks to return (default: 100, max: 1000)
- `offset` (optional): Number of tasks to skip (default: 0)

**Response (200):**
```json
{
  "tasks": [
    {
      "task_id": "abc-123",
      "task_name": "afirgen_tasks.email.send_confirmation",
      "status": "completed",
      ...
    },
    {
      "task_id": "def-456",
      "task_name": "afirgen_tasks.reports.generate_pdf",
      "status": "running",
      ...
    }
  ],
  "total_count": 150,
  "limit": 100,
  "offset": 0
}
```

### GET /api/tasks/count/all

Get count of tasks matching filters.

**Query Parameters:**
- `status` (optional): Filter by status
- `task_type` (optional): Filter by type

**Response (200):**
```json
{
  "count": 42,
  "status": "pending",
  "task_type": "email"
}
```

### POST /api/tasks/{task_id}/cancel

Cancel a pending or running task.

**Response (200):**
```json
{
  "task_id": "abc-123-def-456",
  "success": true,
  "message": "Task cancelled successfully"
}
```

## Task Types

The system supports four task types:

| Type | Priority | Queue | Description |
|------|----------|-------|-------------|
| `email` | 3 (low) | email | Email notifications |
| `report` | 5 (medium) | reports | Report generation |
| `analytics` | 2 (low) | analytics | Analytics processing |
| `cleanup` | 1 (lowest) | cleanup | Cleanup and maintenance |

## Priority System

- Priorities range from 1 (lowest) to 10 (highest)
- Higher priority tasks are processed before lower priority tasks
- Each task type has a default priority, but can be overridden
- Tasks with the same priority are processed in FIFO order

## Automatic Status Tracking

Tasks that inherit from `DatabaseTask` automatically update their status:

1. **Task Start**: Status set to `running`, `started_at` timestamp recorded
2. **Task Success**: Status set to `completed`, result stored, `completed_at` timestamp recorded
3. **Task Failure**: Status set to `failed`, error message stored, `completed_at` timestamp recorded
4. **Task Retry**: Status set to `pending`, retry count incremented, error message updated

### Example Task with Automatic Tracking

```python
from infrastructure.celery_app import celery_app
from infrastructure.tasks.base_task import DatabaseTask

@celery_app.task(
    name="afirgen_tasks.email.send_confirmation",
    bind=True,
    base=DatabaseTask,  # Enable automatic status tracking
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True
)
def send_confirmation_email(self, fir_id: str, recipient_email: str):
    """
    Send FIR confirmation email.
    Status is automatically tracked in database.
    """
    # Task implementation
    # Status updates happen automatically:
    # - 'running' when task starts
    # - 'completed' with result when task succeeds
    # - 'failed' with error when task fails
    # - 'pending' with retry count when task retries
    
    return {
        "status": "success",
        "fir_id": fir_id,
        "recipient": recipient_email
    }
```

## Integration with FastAPI

```python
from fastapi import FastAPI
from api.task_endpoints import create_task_router
from infrastructure.background_task_manager import BackgroundTaskManager

# Initialize FastAPI app
app = FastAPI()

# Initialize task manager with database pool
task_manager = BackgroundTaskManager(db_pool)

# Create and include task router
task_router = create_task_router(task_manager)
app.include_router(task_router)

# Set database pool for automatic status tracking
from infrastructure.tasks.base_task import DatabaseTask
DatabaseTask.set_db_pool(db_pool)
```

## Running Database Migration

```bash
# Apply migration
mysql -u root -p afirgen_db < migrations/002_add_background_tasks_table.sql

# Rollback migration (if needed)
mysql -u root -p afirgen_db < migrations/002_add_background_tasks_table_rollback.sql
```

## Testing

### Unit Tests

```bash
# Test background task manager
pytest test_background_task_manager.py -v

# Test API endpoints
pytest test_task_endpoints.py -v
```

### Manual Testing

```bash
# Start Celery worker
celery -A infrastructure.celery_app worker --loglevel=info

# In another terminal, start FastAPI app
uvicorn agentv5:app --reload

# Enqueue a task via API
curl -X POST http://localhost:8000/api/tasks/enqueue \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "afirgen_tasks.email.send_confirmation",
    "task_type": "email",
    "params": {"fir_id": "fir_123", "recipient_email": "test@example.com"},
    "priority": 5
  }'

# Check task status
curl http://localhost:8000/api/tasks/{task_id}

# List all tasks
curl http://localhost:8000/api/tasks/
```

## Monitoring

### Check Task Queue Status

```bash
# View active tasks
celery -A infrastructure.celery_app inspect active

# View task stats
celery -A infrastructure.celery_app inspect stats

# View queue lengths
celery -A infrastructure.celery_app inspect active_queues
```

### Database Queries

```sql
-- Count tasks by status
SELECT status, COUNT(*) as count
FROM background_tasks
GROUP BY status;

-- Find failed tasks
SELECT task_id, task_name, error_message, retry_count
FROM background_tasks
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;

-- Find long-running tasks
SELECT task_id, task_name, 
       TIMESTAMPDIFF(SECOND, started_at, NOW()) as duration_seconds
FROM background_tasks
WHERE status = 'running'
  AND started_at IS NOT NULL
ORDER BY duration_seconds DESC;

-- Task completion rate
SELECT 
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM background_tasks;
```

## Best Practices

1. **Task Idempotency**: Design tasks to be safely retried
   - Check if work is already done before executing
   - Use unique identifiers to prevent duplicates

2. **Task Size**: Keep tasks small and focused
   - Break large jobs into smaller tasks
   - Use task chains for complex workflows

3. **Error Handling**: Handle errors gracefully
   - Use try-except blocks
   - Log errors with context
   - Return meaningful error messages

4. **Priority Assignment**: Use priorities appropriately
   - High priority (8-10): Critical, time-sensitive tasks
   - Medium priority (5-7): Normal tasks
   - Low priority (1-4): Background maintenance tasks

5. **Monitoring**: Track task performance
   - Monitor queue lengths
   - Track task execution times
   - Alert on high failure rates

## Troubleshooting

### Tasks Not Being Processed

1. Check if Celery workers are running
2. Verify database connection
3. Check task queue lengths
4. Review worker logs for errors

### High Task Failure Rate

1. Check error messages in database
2. Review task implementation for bugs
3. Verify external service availability
4. Check retry configuration

### Slow Task Processing

1. Increase worker concurrency
2. Add more worker instances
3. Optimize task code
4. Check for database/network bottlenecks

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MySQL JSON Data Type](https://dev.mysql.com/doc/refman/8.0/en/json.html)
