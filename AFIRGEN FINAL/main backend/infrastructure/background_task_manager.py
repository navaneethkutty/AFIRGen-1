"""
Background Task Manager

This module provides task enqueueing with priority support, task status tracking,
and integration with Celery for asynchronous task processing.

Requirements: 4.1, 4.4, 4.6
Task: 6.2 Create background task manager
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json
from contextlib import contextmanager

from infrastructure.celery_app import celery_app
from infrastructure.logging import get_logger
from celery.result import AsyncResult


logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of background tasks"""
    EMAIL = "email"
    REPORT = "report"
    ANALYTICS = "analytics"
    CLEANUP = "cleanup"


class BackgroundTaskManager:
    """
    Manages background task enqueueing, status tracking, and querying.
    
    Features:
    - Task enqueueing with priority support (1-10 scale)
    - Task status tracking in database
    - Task status query methods
    - Integration with Celery task queue
    
    Requirements: 4.1, 4.4, 4.6
    """
    
    def __init__(self, db_pool):
        """
        Initialize background task manager.
        
        Args:
            db_pool: MySQL connection pool for database operations
        """
        self.db_pool = db_pool
        logger.info("BackgroundTaskManager initialized")
    
    @contextmanager
    def _cursor(self, autocommit: bool = True):
        """
        Context manager for database cursor with transaction support.
        
        Args:
            autocommit: Whether to auto-commit transactions
            
        Yields:
            Database cursor
        """
        conn = None
        try:
            conn = self.db_pool.get_connection()
            conn.autocommit = autocommit
            with conn.cursor(dictionary=True) as cur:
                yield cur
                if not autocommit:
                    conn.commit()
        except Exception as e:
            if conn and not autocommit:
                try:
                    conn.rollback()
                    logger.warning("Transaction rolled back due to error", error=str(e))
                except Exception as rollback_error:
                    logger.error("Rollback failed", error=str(rollback_error))
            logger.error("Database operation failed", error=str(e))
            raise
        finally:
            if conn:
                conn.close()
    
    def enqueue_task(
        self,
        task_name: str,
        task_type: TaskType,
        params: Dict[str, Any],
        priority: int = 5,
        max_retries: int = 3
    ) -> str:
        """
        Enqueue a background task with priority support.
        
        Args:
            task_name: Celery task name (e.g., "afirgen_tasks.email.send_confirmation")
            task_type: Type of task (email, report, analytics, cleanup)
            params: Task parameters as dictionary
            priority: Task priority (1-10, higher = more important)
            max_retries: Maximum retry attempts
            
        Returns:
            Task ID (Celery task ID)
            
        Requirements: 4.1, 4.5
        """
        # Validate priority
        if not 1 <= priority <= 10:
            raise ValueError("Priority must be between 1 and 10")
        
        # Submit task to Celery with priority
        celery_result = celery_app.send_task(
            task_name,
            kwargs=params,
            priority=priority,
            retry=True,
            max_retries=max_retries
        )
        
        task_id = celery_result.id
        
        # Store task metadata in database
        with self._cursor(autocommit=False) as cur:
            cur.execute(
                """
                INSERT INTO background_tasks 
                (task_id, task_name, task_type, priority, status, params, max_retries)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    task_id,
                    task_name,
                    task_type.value,
                    priority,
                    TaskStatus.PENDING.value,
                    json.dumps(params),
                    max_retries
                )
            )
        
        logger.info(
            "Task enqueued",
            task_id=task_id,
            task_name=task_name,
            task_type=task_type.value,
            priority=priority
        )
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status from database.
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Task status dictionary or None if not found
            
        Requirements: 4.4, 4.6
        """
        with self._cursor(autocommit=True) as cur:
            cur.execute(
                """
                SELECT 
                    task_id,
                    task_name,
                    task_type,
                    priority,
                    status,
                    params,
                    result,
                    error_message,
                    retry_count,
                    max_retries,
                    created_at,
                    started_at,
                    completed_at
                FROM background_tasks
                WHERE task_id = %s
                """,
                (task_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return None
            
            # Parse JSON fields
            if row['params']:
                row['params'] = json.loads(row['params']) if isinstance(row['params'], str) else row['params']
            if row['result']:
                row['result'] = json.loads(row['result']) if isinstance(row['result'], str) else row['result']
            
            # Convert datetime to ISO format
            for field in ['created_at', 'started_at', 'completed_at']:
                if row[field]:
                    row[field] = row[field].isoformat()
            
            return row
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None
    ) -> bool:
        """
        Update task status in database.
        
        Args:
            task_id: Celery task ID
            status: New task status
            result: Task result (for completed tasks)
            error_message: Error message (for failed tasks)
            retry_count: Current retry count
            
        Returns:
            True if update successful, False otherwise
            
        Requirements: 4.4
        """
        with self._cursor(autocommit=False) as cur:
            # Build update query dynamically based on provided fields
            updates = ["status = %s"]
            params = [status.value]
            
            # Set timestamps based on status
            if status == TaskStatus.RUNNING:
                updates.append("started_at = NOW()")
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                updates.append("completed_at = NOW()")
            
            if result is not None:
                updates.append("result = %s")
                params.append(json.dumps(result))
            
            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)
            
            if retry_count is not None:
                updates.append("retry_count = %s")
                params.append(retry_count)
            
            params.append(task_id)
            
            query = f"""
                UPDATE background_tasks
                SET {', '.join(updates)}
                WHERE task_id = %s
            """
            
            cur.execute(query, params)
            success = cur.rowcount > 0
            
            if success:
                logger.info("Task status updated", task_id=task_id, status=status.value)
            else:
                logger.warning("Task not found for status update", task_id=task_id)
            
            return success
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Filter by task status
            task_type: Filter by task type
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            
        Returns:
            List of task dictionaries
            
        Requirements: 4.6
        """
        # Build query with filters
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = %s")
            params.append(status.value)
        
        if task_type:
            where_clauses.append("task_type = %s")
            params.append(task_type.value)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        params.extend([limit, offset])
        
        with self._cursor(autocommit=True) as cur:
            query = f"""
                SELECT 
                    task_id,
                    task_name,
                    task_type,
                    priority,
                    status,
                    params,
                    result,
                    error_message,
                    retry_count,
                    max_retries,
                    created_at,
                    started_at,
                    completed_at
                FROM background_tasks
                {where_sql}
                ORDER BY priority DESC, created_at DESC
                LIMIT %s OFFSET %s
            """
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Parse JSON fields and convert datetimes
            for row in rows:
                if row['params']:
                    row['params'] = json.loads(row['params']) if isinstance(row['params'], str) else row['params']
                if row['result']:
                    row['result'] = json.loads(row['result']) if isinstance(row['result'], str) else row['result']
                
                for field in ['created_at', 'started_at', 'completed_at']:
                    if row[field]:
                        row[field] = row[field].isoformat()
            
            return rows
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending or running task.
        
        Args:
            task_id: Celery task ID
            
        Returns:
            True if cancellation successful, False otherwise
        """
        # Revoke task in Celery
        celery_app.control.revoke(task_id, terminate=True)
        
        # Update status in database
        success = self.update_task_status(task_id, TaskStatus.CANCELLED)
        
        if success:
            logger.info("Task cancelled", task_id=task_id)
        
        return success
    
    def get_task_count(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None
    ) -> int:
        """
        Get count of tasks matching filters.
        
        Args:
            status: Filter by task status
            task_type: Filter by task type
            
        Returns:
            Number of matching tasks
        """
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = %s")
            params.append(status.value)
        
        if task_type:
            where_clauses.append("task_type = %s")
            params.append(task_type.value)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        with self._cursor(autocommit=True) as cur:
            query = f"SELECT COUNT(*) as count FROM background_tasks {where_sql}"
            cur.execute(query, params)
            result = cur.fetchone()
            return result['count'] if result else 0
