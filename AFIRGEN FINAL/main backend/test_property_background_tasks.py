"""
test_property_background_tasks.py
-----------------------------------------------------------------------------
Property-Based Tests for Background Task Processing
-----------------------------------------------------------------------------

Property tests for background task manager using Hypothesis to verify:
- Property 17: Async task queuing
- Property 19: Task status tracking
- Property 20: Task prioritization

Requirements Validated: 4.1, 4.4, 4.5 (Background Job Processing)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json
import time

from infrastructure.background_task_manager import (
    BackgroundTaskManager,
    TaskStatus,
    TaskType
)


# Helper function to create mock database pool
def create_mock_db_pool():
    """Create a mock database connection pool for testing"""
    pool = Mock()
    conn = Mock()
    cursor = Mock()
    
    # Setup cursor context manager
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.fetchone = Mock(return_value=None)
    cursor.fetchall = Mock(return_value=[])
    cursor.rowcount = 1
    
    # Setup connection
    conn.cursor = Mock(return_value=cursor)
    conn.autocommit = True
    conn.commit = Mock()
    conn.rollback = Mock()
    conn.close = Mock()
    
    pool.get_connection = Mock(return_value=conn)
    
    return pool, conn, cursor


# Feature: backend-optimization, Property 17: Async task queuing
@given(
    task_name=st.sampled_from([
        "afirgen_tasks.email.send_confirmation",
        "afirgen_tasks.reports.generate_pdf",
        "afirgen_tasks.analytics.update_dashboard",
        "afirgen_tasks.cleanup.archive_old_records"
    ]),
    task_type=st.sampled_from([TaskType.EMAIL, TaskType.REPORT, TaskType.ANALYTICS, TaskType.CLEANUP]),
    priority=st.integers(min_value=1, max_value=10),
    param_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    param_value=st.text(min_size=1, max_size=50)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_async_task_queuing(task_name, task_type, priority, param_key, param_value):
    """
    Property 17: For any non-critical task submitted to the Background_Processor,
    the task should be added to the queue and return immediately without blocking,
    and the task should execute asynchronously.
    
    **Validates: Requirements 4.1**
    
    This property verifies that:
    1. Task enqueueing returns immediately (non-blocking)
    2. Task is added to Celery queue
    3. Task ID is returned immediately
    4. Task metadata is stored in database
    5. Task status is initially PENDING
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    params = {param_key: param_value}
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        # Mock Celery task submission
        mock_result = Mock()
        mock_task_id = f"task-{task_name}-{priority}-{hash(param_value) % 10000}"
        mock_result.id = mock_task_id
        mock_celery.send_task = Mock(return_value=mock_result)
        
        # Measure time to enqueue (should be fast - non-blocking)
        start_time = time.time()
        task_id = manager.enqueue_task(
            task_name=task_name,
            task_type=task_type,
            params=params,
            priority=priority
        )
        elapsed_time = time.time() - start_time
        
        # Property assertions
        
        # 1. Task ID should be returned immediately
        assert task_id is not None, "Task ID should be returned"
        assert task_id == mock_task_id, "Task ID should match Celery task ID"
        
        # 2. Enqueueing should be fast (non-blocking) - under 100ms
        assert elapsed_time < 0.1, \
            f"Task enqueueing should be non-blocking (took {elapsed_time:.3f}s)"
        
        # 3. Task should be submitted to Celery
        mock_celery.send_task.assert_called_once()
        call_args = mock_celery.send_task.call_args
        assert call_args[0][0] == task_name, "Task name should match"
        assert call_args[1]['kwargs'] == params, "Task params should match"
        assert call_args[1]['priority'] == priority, "Task priority should match"
        assert call_args[1]['retry'] is True, "Task should have retry enabled"
        
        # 4. Task metadata should be stored in database
        cursor.execute.assert_called()
        sql = cursor.execute.call_args[0][0]
        assert "INSERT INTO background_tasks" in sql, \
            "Task metadata should be inserted into database"
        
        # 5. Verify task is stored with PENDING status
        sql_params = cursor.execute.call_args[0][1]
        assert sql_params[0] == task_id, "Task ID should be stored"
        assert sql_params[1] == task_name, "Task name should be stored"
        assert sql_params[2] == task_type.value, "Task type should be stored"
        assert sql_params[3] == priority, "Priority should be stored"
        assert sql_params[4] == TaskStatus.PENDING.value, \
            "Initial status should be PENDING"


@given(
    task_count=st.integers(min_value=2, max_value=10),
    task_type=st.sampled_from([TaskType.EMAIL, TaskType.REPORT, TaskType.ANALYTICS])
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_multiple_tasks_enqueue_independently(task_count, task_type):
    """
    Property 17 (extended): For any sequence of task submissions,
    each task should be enqueued independently without blocking others.
    
    **Validates: Requirements 4.1**
    
    This property verifies that multiple tasks can be enqueued
    concurrently without interference.
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        task_ids = []
        
        for i in range(task_count):
            # Mock unique task ID for each task
            mock_result = Mock()
            mock_result.id = f"task-{i}-{task_type.value}"
            mock_celery.send_task = Mock(return_value=mock_result)
            
            # Enqueue task
            task_id = manager.enqueue_task(
                task_name=f"afirgen_tasks.{task_type.value}.task_{i}",
                task_type=task_type,
                params={"index": i},
                priority=5
            )
            
            task_ids.append(task_id)
        
        # All tasks should have unique IDs
        assert len(task_ids) == task_count, \
            "All tasks should be enqueued"
        assert len(set(task_ids)) == task_count, \
            "All task IDs should be unique"
        
        # Database should have been called for each task
        assert cursor.execute.call_count >= task_count, \
            "Each task should be stored in database"


# Feature: backend-optimization, Property 19: Task status tracking
@given(
    task_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
    initial_status=st.sampled_from([TaskStatus.PENDING, TaskStatus.RUNNING]),
    final_status=st.sampled_from([TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_task_status_tracking(task_id, initial_status, final_status):
    """
    Property 19: For any background task that completes (successfully or with failure),
    the task status in the database should be updated to reflect the final state.
    
    **Validates: Requirements 4.4**
    
    This property verifies that:
    1. Task status can be updated in database
    2. Status transitions are recorded correctly
    3. Timestamps are set appropriately
    4. Final status reflects task outcome
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    # Mock successful update
    cursor.rowcount = 1
    
    # Prepare result or error based on final status
    result = None
    error_message = None
    
    if final_status == TaskStatus.COMPLETED:
        result = {"status": "success", "message": "Task completed"}
    elif final_status == TaskStatus.FAILED:
        error_message = "Task failed due to error"
    
    # Update task status
    success = manager.update_task_status(
        task_id=task_id,
        status=final_status,
        result=result,
        error_message=error_message
    )
    
    # Property assertions
    
    # 1. Update should succeed
    assert success is True, "Status update should succeed"
    
    # 2. Database update should be called
    cursor.execute.assert_called()
    sql = cursor.execute.call_args[0][0]
    assert "UPDATE background_tasks" in sql, \
        "Should update background_tasks table"
    assert "status = %s" in sql, \
        "Should update status field"
    
    # 3. Verify status value in parameters
    sql_params = cursor.execute.call_args[0][1]
    assert final_status.value in sql_params, \
        f"Status should be updated to {final_status.value}"
    
    # 4. Verify task_id in WHERE clause
    assert task_id in sql_params, \
        "Task ID should be in WHERE clause"
    
    # 5. Verify timestamp is set for final states
    if final_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        assert "completed_at = NOW()" in sql, \
            "Completed timestamp should be set for final states"
    
    # 6. Verify result is stored for completed tasks
    if final_status == TaskStatus.COMPLETED and result:
        assert "result = %s" in sql, \
            "Result should be stored for completed tasks"
        assert json.dumps(result) in sql_params, \
            "Result should be JSON-encoded"
    
    # 7. Verify error message is stored for failed tasks
    if final_status == TaskStatus.FAILED and error_message:
        assert "error_message = %s" in sql, \
            "Error message should be stored for failed tasks"
        assert error_message in sql_params, \
            "Error message should be in parameters"


@given(
    task_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
    status_sequence=st.lists(
        st.sampled_from([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED]),
        min_size=2,
        max_size=4
    )
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_task_status_transitions(task_id, status_sequence):
    """
    Property 19 (extended): For any sequence of status updates,
    each transition should be recorded in the database.
    
    **Validates: Requirements 4.4**
    
    This property verifies that task status can transition through
    multiple states and each transition is tracked.
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    # Mock successful updates
    cursor.rowcount = 1
    
    update_count = 0
    for status in status_sequence:
        success = manager.update_task_status(
            task_id=task_id,
            status=status
        )
        
        assert success is True, f"Status update to {status.value} should succeed"
        update_count += 1
    
    # All status transitions should be recorded
    assert cursor.execute.call_count >= update_count, \
        "Each status transition should result in database update"


@given(
    task_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
    task_name=st.text(min_size=5, max_size=50),
    task_type=st.sampled_from([TaskType.EMAIL, TaskType.REPORT, TaskType.ANALYTICS, TaskType.CLEANUP]),
    priority=st.integers(min_value=1, max_value=10),
    status=st.sampled_from([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_task_status_retrieval(task_id, task_name, task_type, priority, status):
    """
    Property 19 (extended): For any task stored in the database,
    retrieving its status should return complete task information.
    
    **Validates: Requirements 4.4, 4.6**
    
    This property verifies that task status can be queried and
    returns all relevant task metadata.
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    # Mock database response
    cursor.fetchone = Mock(return_value={
        'task_id': task_id,
        'task_name': task_name,
        'task_type': task_type.value,
        'priority': priority,
        'status': status.value,
        'params': '{"test": "data"}',
        'result': '{"status": "success"}' if status == TaskStatus.COMPLETED else None,
        'error_message': "Error occurred" if status == TaskStatus.FAILED else None,
        'retry_count': 0,
        'max_retries': 3,
        'created_at': datetime(2024, 1, 15, 10, 30, 0),
        'started_at': datetime(2024, 1, 15, 10, 30, 5) if status != TaskStatus.PENDING else None,
        'completed_at': datetime(2024, 1, 15, 10, 30, 10) if status in [TaskStatus.COMPLETED, TaskStatus.FAILED] else None
    })
    
    # Get task status
    task_status = manager.get_task_status(task_id)
    
    # Property assertions
    
    # 1. Task status should be returned
    assert task_status is not None, "Task status should be returned"
    
    # 2. All required fields should be present
    required_fields = [
        'task_id', 'task_name', 'task_type', 'priority', 'status',
        'params', 'retry_count', 'max_retries', 'created_at'
    ]
    for field in required_fields:
        assert field in task_status, f"Field '{field}' should be present"
    
    # 3. Task metadata should match
    assert task_status['task_id'] == task_id, "Task ID should match"
    assert task_status['task_name'] == task_name, "Task name should match"
    assert task_status['task_type'] == task_type.value, "Task type should match"
    assert task_status['priority'] == priority, "Priority should match"
    assert task_status['status'] == status.value, "Status should match"
    
    # 4. JSON fields should be parsed
    assert isinstance(task_status['params'], dict), "Params should be parsed as dict"
    
    # 5. Timestamps should be ISO formatted strings
    assert isinstance(task_status['created_at'], str), \
        "Timestamps should be ISO formatted strings"


# Feature: backend-optimization, Property 20: Task prioritization
@given(
    priorities=st.lists(
        st.integers(min_value=1, max_value=10),
        min_size=3,
        max_size=10,
        unique=False
    ),
    task_type=st.sampled_from([TaskType.EMAIL, TaskType.REPORT, TaskType.ANALYTICS])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_task_prioritization(priorities, task_type):
    """
    Property 20: For any set of queued background tasks with different priorities,
    higher priority tasks should be processed before lower priority tasks when
    workers are available.
    
    **Validates: Requirements 4.5**
    
    This property verifies that:
    1. Tasks are enqueued with correct priority
    2. Priority is passed to Celery
    3. Priority is stored in database
    4. Priority values are within valid range (1-10)
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        enqueued_tasks = []
        
        for i, priority in enumerate(priorities):
            # Mock Celery task submission
            mock_result = Mock()
            mock_result.id = f"task-{i}-priority-{priority}"
            mock_celery.send_task = Mock(return_value=mock_result)
            
            # Enqueue task with specific priority
            task_id = manager.enqueue_task(
                task_name=f"afirgen_tasks.{task_type.value}.task_{i}",
                task_type=task_type,
                params={"index": i},
                priority=priority
            )
            
            enqueued_tasks.append({
                'task_id': task_id,
                'priority': priority,
                'index': i
            })
            
            # Verify priority was passed to Celery
            call_args = mock_celery.send_task.call_args
            assert call_args[1]['priority'] == priority, \
                f"Task {i} should be enqueued with priority {priority}"
        
        # Property assertions
        
        # 1. All tasks should be enqueued
        assert len(enqueued_tasks) == len(priorities), \
            "All tasks should be enqueued"
        
        # 2. Each task should have correct priority
        for task, expected_priority in zip(enqueued_tasks, priorities):
            assert task['priority'] == expected_priority, \
                f"Task priority should be {expected_priority}"
        
        # 3. Verify priorities are within valid range
        for task in enqueued_tasks:
            assert 1 <= task['priority'] <= 10, \
                "Task priority should be between 1 and 10"


@given(
    high_priority=st.integers(min_value=7, max_value=10),
    low_priority=st.integers(min_value=1, max_value=3),
    task_type=st.sampled_from([TaskType.EMAIL, TaskType.REPORT, TaskType.ANALYTICS])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_priority_ordering(high_priority, low_priority, task_type):
    """
    Property 20 (extended): For any two tasks with different priorities,
    the higher priority task should be submitted with higher priority value.
    
    **Validates: Requirements 4.5**
    
    This property verifies that priority ordering is maintained
    when tasks are enqueued.
    """
    # Ensure priorities are different
    assume(high_priority > low_priority)
    
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        # Enqueue high priority task
        mock_result_high = Mock()
        mock_result_high.id = "high-priority-task"
        mock_celery.send_task = Mock(return_value=mock_result_high)
        
        high_task_id = manager.enqueue_task(
            task_name=f"afirgen_tasks.{task_type.value}.high_priority",
            task_type=task_type,
            params={"priority": "high"},
            priority=high_priority
        )
        
        high_priority_call = mock_celery.send_task.call_args[1]['priority']
        
        # Enqueue low priority task
        mock_result_low = Mock()
        mock_result_low.id = "low-priority-task"
        mock_celery.send_task = Mock(return_value=mock_result_low)
        
        low_task_id = manager.enqueue_task(
            task_name=f"afirgen_tasks.{task_type.value}.low_priority",
            task_type=task_type,
            params={"priority": "low"},
            priority=low_priority
        )
        
        low_priority_call = mock_celery.send_task.call_args[1]['priority']
        
        # Property assertions
        
        # 1. High priority task should have higher priority value
        assert high_priority_call > low_priority_call, \
            "High priority task should have higher priority value than low priority task"
        
        # 2. Priority values should match requested priorities
        assert high_priority_call == high_priority, \
            "High priority task should have correct priority"
        assert low_priority_call == low_priority, \
            "Low priority task should have correct priority"


@given(
    priority=st.integers(min_value=1, max_value=10),
    task_count=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_same_priority_tasks(priority, task_count):
    """
    Property 20 (extended): For any set of tasks with the same priority,
    all should be enqueued with that priority value.
    
    **Validates: Requirements 4.5**
    
    This property verifies that tasks with equal priority are
    handled consistently.
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    with patch('infrastructure.background_task_manager.celery_app') as mock_celery:
        priorities_used = []
        
        for i in range(task_count):
            mock_result = Mock()
            mock_result.id = f"task-{i}"
            mock_celery.send_task = Mock(return_value=mock_result)
            
            manager.enqueue_task(
                task_name=f"afirgen_tasks.email.task_{i}",
                task_type=TaskType.EMAIL,
                params={"index": i},
                priority=priority
            )
            
            # Capture priority used in Celery call
            call_priority = mock_celery.send_task.call_args[1]['priority']
            priorities_used.append(call_priority)
        
        # All tasks should have the same priority
        assert len(set(priorities_used)) == 1, \
            "All tasks with same priority should be enqueued with that priority"
        assert priorities_used[0] == priority, \
            f"All tasks should have priority {priority}"


@given(
    invalid_priority=st.sampled_from([0, -1, 11, 15, 100])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_invalid_priority_rejected(invalid_priority):
    """
    Property 20 (extended): For any priority value outside the valid range (1-10),
    task enqueueing should raise a ValueError.
    
    **Validates: Requirements 4.5**
    
    This property verifies that invalid priorities are rejected.
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    # Attempt to enqueue task with invalid priority
    with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
        manager.enqueue_task(
            task_name="afirgen_tasks.email.test",
            task_type=TaskType.EMAIL,
            params={"test": "data"},
            priority=invalid_priority
        )


@given(
    status_filter=st.sampled_from([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED]),
    task_type_filter=st.sampled_from([TaskType.EMAIL, TaskType.REPORT, TaskType.ANALYTICS, TaskType.CLEANUP])
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_task_listing_with_filters(status_filter, task_type_filter):
    """
    Property (additional): For any status and task type filters,
    the list_tasks method should query with correct WHERE clauses.
    
    **Validates: Requirements 4.6**
    
    This property verifies that task listing supports filtering
    by status and task type.
    """
    pool, conn, cursor = create_mock_db_pool()
    manager = BackgroundTaskManager(pool)
    
    # Mock empty result
    cursor.fetchall = Mock(return_value=[])
    
    # List tasks with filters
    tasks = manager.list_tasks(
        status=status_filter,
        task_type=task_type_filter,
        limit=100,
        offset=0
    )
    
    # Verify SQL query includes filters
    sql = cursor.execute.call_args[0][0]
    assert "WHERE" in sql, "Query should include WHERE clause"
    assert "status = %s" in sql, "Query should filter by status"
    assert "task_type = %s" in sql, "Query should filter by task type"
    
    # Verify parameters include filter values
    params = cursor.execute.call_args[0][1]
    assert status_filter.value in params, "Status filter should be in parameters"
    assert task_type_filter.value in params, "Task type filter should be in parameters"
    
    # Verify ordering by priority
    assert "ORDER BY priority DESC" in sql, \
        "Tasks should be ordered by priority (highest first)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
