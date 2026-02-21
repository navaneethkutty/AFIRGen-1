"""
Base task class with automatic status tracking and retry handling.

This module provides a base Celery task class that automatically updates
task status in the database during task execution and implements exponential
backoff retry logic with configurable parameters.

Requirements: 4.3, 4.4
Task: 6.2 Create background task manager, 6.4 Implement retry handler
"""

from celery import Task
from typing import Any, Optional, Type, Tuple
from infrastructure.logging import get_logger
import time

logger = get_logger(__name__)


# Retry configuration constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 600.0  # 10 minutes
DEFAULT_EXPONENTIAL_BASE = 2.0
DEFAULT_JITTER = True


class DatabaseTask(Task):
    """
    Base Celery task with automatic database status tracking and retry handling.
    
    This task class automatically updates task status in the database:
    - Sets status to 'running' when task starts
    - Sets status to 'completed' with result when task succeeds
    - Sets status to 'failed' with error message when task fails
    - Updates retry count on retries
    - Implements exponential backoff retry logic with jitter
    
    Retry Strategy:
    - Exponential backoff: delay = min(base_delay * (exponential_base ^ retry_count), max_delay)
    - Jitter: adds randomness to prevent thundering herd (±20% of calculated delay)
    - Configurable max retries, delays, and exponential base
    
    Requirements: 4.3, 4.4
    """
    
    _db_pool = None
    
    # Default retry configuration (can be overridden per task)
    autoretry_for: Tuple[Type[Exception], ...] = (Exception,)
    retry_kwargs = {
        'max_retries': DEFAULT_MAX_RETRIES,
    }
    retry_backoff = True
    retry_backoff_max = DEFAULT_MAX_DELAY
    retry_jitter = DEFAULT_JITTER
    
    @classmethod
    def set_db_pool(cls, db_pool):
        """Set the database connection pool for all tasks."""
        cls._db_pool = db_pool
    
    def calculate_retry_delay(
        self,
        retry_count: int,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        exponential_base: float = DEFAULT_EXPONENTIAL_BASE,
        jitter: bool = DEFAULT_JITTER
    ) -> float:
        """
        Calculate retry delay with exponential backoff and optional jitter.
        
        Formula: delay = min(base_delay * (exponential_base ^ retry_count), max_delay)
        With jitter: delay ± (delay * 0.2 * random)
        
        Args:
            retry_count: Current retry attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation
            jitter: Whether to add random jitter
            
        Returns:
            Calculated delay in seconds
            
        Requirements: 4.3
        """
        import random
        
        # Calculate exponential backoff
        delay = base_delay * (exponential_base ** retry_count)
        
        # Cap at max delay
        delay = min(delay, max_delay)
        
        # Add jitter if enabled (±20% randomness)
        if jitter:
            jitter_amount = delay * 0.2 * (random.random() * 2 - 1)  # -20% to +20%
            delay = max(0, delay + jitter_amount)
        
        return delay
    
    def retry_with_backoff(
        self,
        exc: Exception,
        max_retries: Optional[int] = None,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        exponential_base: float = DEFAULT_EXPONENTIAL_BASE,
        jitter: bool = DEFAULT_JITTER
    ):
        """
        Retry task with exponential backoff.
        
        Args:
            exc: Exception that triggered the retry
            max_retries: Maximum number of retries (None = use task default)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation
            jitter: Whether to add random jitter
            
        Raises:
            Exception: Re-raises the exception if max retries exceeded
            
        Requirements: 4.3
        """
        retry_count = self.request.retries
        
        # Use task's max_retries if not specified
        if max_retries is None:
            max_retries = self.max_retries or DEFAULT_MAX_RETRIES
        
        # Check if we've exceeded max retries
        if retry_count >= max_retries:
            logger.error(
                "Task failed after max retries",
                task_name=self.name,
                task_id=self.request.id,
                retry_count=retry_count,
                error=str(exc)
            )
            raise exc
        
        # Calculate retry delay
        countdown = self.calculate_retry_delay(
            retry_count=retry_count,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter
        )
        
        logger.warning(
            "Task retry scheduled",
            task_name=self.name,
            task_id=self.request.id,
            retry_attempt=retry_count + 1,
            max_retries=max_retries,
            countdown=countdown,
            error=str(exc)
        )
        
        # Retry with calculated countdown
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)
    
    @staticmethod
    def is_retryable_error(exc: Exception) -> bool:
        """
        Determine if an exception is retryable.
        
        Retryable errors:
        - Network timeouts and connection errors
        - Temporary database unavailability
        - Rate limit errors
        - Service temporarily unavailable
        
        Non-retryable errors:
        - Validation errors
        - Authentication/authorization failures
        - Resource not found
        - Malformed data
        
        Args:
            exc: Exception to classify
            
        Returns:
            True if error is retryable, False otherwise
            
        Requirements: 4.3, 6.5
        """
        import socket
        
        # Retryable error types (built-in)
        retryable_types = [
            # Network errors
            socket.timeout,
            TimeoutError,
            ConnectionError,
            ConnectionRefusedError,
            ConnectionResetError,
            BrokenPipeError,
        ]
        
        # Add requests library errors if available
        try:
            from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError
            retryable_types.extend([Timeout, RequestsConnectionError])
        except ImportError:
            pass
        
        # Check exception type
        if isinstance(exc, tuple(retryable_types)):
            return True
        
        # Check exception message for retryable patterns
        error_msg = str(exc).lower()
        retryable_patterns = [
            'timeout',
            'connection',
            'temporarily unavailable',
            'rate limit',
            'too many requests',
            'service unavailable',
            'gateway timeout',
            'bad gateway',
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_msg:
                return True
        
        # Non-retryable by default
        return False
    
    def before_start(self, task_id: str, args: tuple, kwargs: dict) -> None:
        """
        Called before task execution starts.
        Updates task status to 'running'.
        """
        if self._db_pool:
            try:
                self._update_task_status(
                    task_id=task_id,
                    status='running'
                )
                logger.info("Task started", task_id=task_id, task_name=self.name)
            except Exception as e:
                logger.error("Failed to update task status to running", error=str(e), task_id=task_id)
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """
        Called when task completes successfully.
        Updates task status to 'completed' with result.
        """
        if self._db_pool:
            try:
                self._update_task_status(
                    task_id=task_id,
                    status='completed',
                    result=retval if isinstance(retval, dict) else {"result": str(retval)}
                )
                logger.info("Task completed successfully", task_id=task_id, task_name=self.name)
            except Exception as e:
                logger.error("Failed to update task status to completed", error=str(e), task_id=task_id)
    
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any
    ) -> None:
        """
        Called when task fails permanently (after all retries exhausted).
        Updates task status to 'failed' with detailed error information.
        
        Requirements: 4.3, 4.4
        """
        if self._db_pool:
            try:
                retry_count = self.request.retries
                max_retries = self.max_retries or DEFAULT_MAX_RETRIES
                
                error_details = {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                    "traceback": str(einfo) if einfo else None
                }
                
                self._update_task_status(
                    task_id=task_id,
                    status='failed',
                    error_message=f"Failed after {retry_count} retries: {str(exc)}"
                )
                
                logger.error(
                    "Task permanently failed",
                    task_name=self.name,
                    task_id=task_id,
                    **error_details
                )
            except Exception as e:
                logger.error("Failed to update task status to failed", error=str(e), task_id=task_id)
    
    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any
    ) -> None:
        """
        Called when task is retried.
        Updates retry count in database.
        """
        if self._db_pool:
            try:
                # Get current retry count from task request
                retry_count = self.request.retries
                
                self._update_task_status(
                    task_id=task_id,
                    status='pending',  # Back to pending for retry
                    retry_count=retry_count,
                    error_message=f"Retry {retry_count}: {str(exc)}"
                )
                logger.warning("Task retry", task_id=task_id, retry_count=retry_count, error=str(exc))
            except Exception as e:
                logger.error("Failed to update task retry status", error=str(e), task_id=task_id)
    
    def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[dict] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None
    ) -> None:
        """
        Update task status in database.
        
        Args:
            task_id: Celery task ID
            status: New task status
            result: Task result (for completed tasks)
            error_message: Error message (for failed tasks)
            retry_count: Current retry count
        """
        import json
        
        conn = None
        try:
            conn = self._db_pool.get_connection()
            conn.autocommit = False
            
            with conn.cursor() as cur:
                # Build update query
                updates = ["status = %s"]
                params = [status]
                
                # Set timestamps based on status
                if status == 'running':
                    updates.append("started_at = NOW()")
                elif status in ['completed', 'failed', 'cancelled']:
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
                conn.commit()
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if conn:
                conn.close()
