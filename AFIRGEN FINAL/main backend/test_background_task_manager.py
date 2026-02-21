"""
Unit tests for Background Task Manager.

Tests task enqueueing, status tracking, and query endpoints.

Requirements: 4.1, 4.4, 4.6
Task: 6.2 Create background task manager
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from infrastructure.background_task_manager import (
    BackgroundTaskManager,
    TaskStatus,
    TaskType
)


@pytest.fixture
def mock_db_pool():
    """Create mock database connection pool"""
    pool = Mock()
    conn = Mock()
    cursor = Mock()
    
    # Setup cursor context manager
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    
    # Setup connection context manager
    conn.cursor = Mock(return_value=cursor)
    conn.autocommit = True
    conn.commit = Mock()
    conn.rollback = Mock()
    conn.close = Mock()
    
    pool.get_connection = Mock(return_value=conn)
    
    return pool, conn, cursor


def test_enqueue_task_success(mock_db_pool):
    """Test successful task enqueueing"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        # Mock Celery task submission
        mock_result = Mock()
        mock_result.id = "test-task-id-123"
        mock_celery.send_task = Mock(return_value=mock_result)
        
        # Enqueue task
        task_id = manager.enqueue_task(
            task_name="afirgen_tasks.email.send_confirmation",
            task_type=TaskType.EMAIL,
            params={"fir_id": "fir_123", "email": "test@example.com"},
            priority=5,
            max_retries=3
        )
        
        # Verify task ID returned
        assert task_id == "test-task-id-123"
        
        # Verify Celery task was submitted with correct parameters
        mock_celery.send_task.assert_called_once()
        call_args = mock_celery.send_task.call_args
        assert call_args[0][0] == "afirgen_tasks.email.send_confirmation"
        assert call_args[1]['priority'] == 5
        assert call_args[1]['max_retries'] == 3
        
        # Verify database insert was called
        cursor.execute.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        assert "INSERT INTO background_tasks" in sql
        assert "task_id" in sql


def test_enqueue_task_invalid_priority(mock_db_pool):
    """Test task enqueueing with invalid priority"""
    pool, _, _ = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Priority too low
    with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
        manager.enqueue_task(
            task_name="test_task",
            task_type=TaskType.EMAIL,
            params={},
            priority=0
        )
    
    # Priority too high
    with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
        manager.enqueue_task(
            task_name="test_task",
            task_type=TaskType.EMAIL,
            params={},
            priority=11
        )


def test_get_task_status_found(mock_db_pool):
    """Test getting task status when task exists"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock database response
    cursor.fetchone = Mock(return_value={
        'task_id': 'test-task-123',
        'task_name': 'afirgen_tasks.email.send_confirmation',
        'task_type': 'email',
        'priority': 5,
        'status': 'completed',
        'params': '{"fir_id": "fir_123"}',
        'result': '{"status": "success"}',
        'error_message': None,
        'retry_count': 0,
        'max_retries': 3,
        'created_at': datetime(2024, 1, 15, 10, 30, 0),
        'started_at': datetime(2024, 1, 15, 10, 30, 5),
        'completed_at': datetime(2024, 1, 15, 10, 30, 10)
    })
    
    # Get task status
    status = manager.get_task_status('test-task-123')
    
    # Verify result
    assert status is not None
    assert status['task_id'] == 'test-task-123'
    assert status['status'] == 'completed'
    assert status['params'] == {"fir_id": "fir_123"}
    assert status['result'] == {"status": "success"}
    assert status['retry_count'] == 0


def test_get_task_status_not_found(mock_db_pool):
    """Test getting task status when task doesn't exist"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock database response - no task found
    cursor.fetchone = Mock(return_value=None)
    
    # Get task status
    status = manager.get_task_status('nonexistent-task')
    
    # Verify result
    assert status is None


def test_update_task_status_to_running(mock_db_pool):
    """Test updating task status to running"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock successful update
    cursor.rowcount = 1
    
    # Update status
    success = manager.update_task_status(
        task_id='test-task-123',
        status=TaskStatus.RUNNING
    )
    
    # Verify result
    assert success is True
    
    # Verify SQL includes status and started_at
    sql = cursor.execute.call_args[0][0]
    assert "status = %s" in sql
    assert "started_at = NOW()" in sql


def test_update_task_status_to_completed(mock_db_pool):
    """Test updating task status to completed with result"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock successful update
    cursor.rowcount = 1
    
    # Update status
    result = {"status": "success", "message": "Task completed"}
    success = manager.update_task_status(
        task_id='test-task-123',
        status=TaskStatus.COMPLETED,
        result=result
    )
    
    # Verify result
    assert success is True
    
    # Verify SQL includes status, result, and completed_at
    sql = cursor.execute.call_args[0][0]
    assert "status = %s" in sql
    assert "result = %s" in sql
    assert "completed_at = NOW()" in sql


def test_update_task_status_to_failed(mock_db_pool):
    """Test updating task status to failed with error message"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock successful update
    cursor.rowcount = 1
    
    # Update status
    success = manager.update_task_status(
        task_id='test-task-123',
        status=TaskStatus.FAILED,
        error_message="Connection timeout"
    )
    
    # Verify result
    assert success is True
    
    # Verify SQL includes status, error_message, and completed_at
    sql = cursor.execute.call_args[0][0]
    assert "status = %s" in sql
    assert "error_message = %s" in sql
    assert "completed_at = NOW()" in sql


def test_list_tasks_no_filters(mock_db_pool):
    """Test listing tasks without filters"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock database response
    cursor.fetchall = Mock(return_value=[
        {
            'task_id': 'task-1',
            'task_name': 'afirgen_tasks.email.send_confirmation',
            'task_type': 'email',
            'priority': 5,
            'status': 'completed',
            'params': '{}',
            'result': '{}',
            'error_message': None,
            'retry_count': 0,
            'max_retries': 3,
            'created_at': datetime(2024, 1, 15, 10, 30, 0),
            'started_at': datetime(2024, 1, 15, 10, 30, 5),
            'completed_at': datetime(2024, 1, 15, 10, 30, 10)
        },
        {
            'task_id': 'task-2',
            'task_name': 'afirgen_tasks.reports.generate_pdf',
            'task_type': 'report',
            'priority': 7,
            'status': 'running',
            'params': '{}',
            'result': None,
            'error_message': None,
            'retry_count': 0,
            'max_retries': 3,
            'created_at': datetime(2024, 1, 15, 10, 31, 0),
            'started_at': datetime(2024, 1, 15, 10, 31, 5),
            'completed_at': None
        }
    ])
    
    # List tasks
    tasks = manager.list_tasks(limit=100, offset=0)
    
    # Verify result
    assert len(tasks) == 2
    assert tasks[0]['task_id'] == 'task-1'
    assert tasks[1]['task_id'] == 'task-2'
    
    # Verify SQL query
    sql = cursor.execute.call_args[0][0]
    assert "ORDER BY priority DESC, created_at DESC" in sql
    assert "LIMIT %s OFFSET %s" in sql


def test_list_tasks_with_status_filter(mock_db_pool):
    """Test listing tasks filtered by status"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    cursor.fetchall = Mock(return_value=[])
    
    # List tasks with status filter
    tasks = manager.list_tasks(
        status=TaskStatus.COMPLETED,
        limit=50,
        offset=0
    )
    
    # Verify SQL includes WHERE clause
    sql = cursor.execute.call_args[0][0]
    assert "WHERE status = %s" in sql
    
    # Verify parameters
    params = cursor.execute.call_args[0][1]
    assert 'completed' in params


def test_list_tasks_with_type_filter(mock_db_pool):
    """Test listing tasks filtered by type"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    cursor.fetchall = Mock(return_value=[])
    
    # List tasks with type filter
    tasks = manager.list_tasks(
        task_type=TaskType.EMAIL,
        limit=50,
        offset=0
    )
    
    # Verify SQL includes WHERE clause
    sql = cursor.execute.call_args[0][0]
    assert "WHERE task_type = %s" in sql
    
    # Verify parameters
    params = cursor.execute.call_args[0][1]
    assert 'email' in params


def test_cancel_task(mock_db_pool):
    """Test cancelling a task"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock successful update
    cursor.rowcount = 1
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        # Cancel task
        success = manager.cancel_task('test-task-123')
        
        # Verify result
        assert success is True
        
        # Verify Celery revoke was called
        mock_celery.control.revoke.assert_called_once_with('test-task-123', terminate=True)
        
        # Verify database update was called
        sql = cursor.execute.call_args[0][0]
        assert "UPDATE background_tasks" in sql
        assert "status = %s" in sql


def test_get_task_count_no_filters(mock_db_pool):
    """Test getting task count without filters"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock database response
    cursor.fetchone = Mock(return_value={'count': 42})
    
    # Get count
    count = manager.get_task_count()
    
    # Verify result
    assert count == 42
    
    # Verify SQL
    sql = cursor.execute.call_args[0][0]
    assert "SELECT COUNT(*) as count FROM background_tasks" in sql


def test_get_task_count_with_filters(mock_db_pool):
    """Test getting task count with filters"""
    pool, conn, cursor = mock_db_pool
    manager = BackgroundTaskManager(pool)
    
    # Mock database response
    cursor.fetchone = Mock(return_value={'count': 10})
    
    # Get count with filters
    count = manager.get_task_count(
        status=TaskStatus.PENDING,
        task_type=TaskType.EMAIL
    )
    
    # Verify result
    assert count == 10
    
    # Verify SQL includes WHERE clause
    sql = cursor.execute.call_args[0][0]
    assert "WHERE" in sql
    assert "status = %s" in sql
    assert "task_type = %s" in sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
