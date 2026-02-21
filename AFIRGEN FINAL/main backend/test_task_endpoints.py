"""
Unit tests for Background Task API Endpoints.

Tests task status query endpoints.

Requirements: 4.6
Task: 6.2 Create background task manager
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from api.task_endpoints import create_task_router
from infrastructure.background_task_manager import (
    BackgroundTaskManager,
    TaskStatus,
    TaskType
)


@pytest.fixture
def mock_task_manager():
    """Create mock task manager"""
    return Mock(spec=BackgroundTaskManager)


@pytest.fixture
def test_app(mock_task_manager):
    """Create test FastAPI app with task router"""
    app = FastAPI()
    router = create_task_router(mock_task_manager)
    app.include_router(router)
    return app, mock_task_manager


@pytest.fixture
def client(test_app):
    """Create test client"""
    app, manager = test_app
    return TestClient(app), manager


def test_enqueue_task_success(client):
    """Test successful task enqueueing via API"""
    test_client, manager = client
    
    # Mock enqueue_task to return task ID
    manager.enqueue_task = Mock(return_value="task-123")
    
    # Make request
    response = test_client.post(
        "/api/tasks/enqueue",
        json={
            "task_name": "afirgen_tasks.email.send_confirmation",
            "task_type": "email",
            "params": {"fir_id": "fir_123"},
            "priority": 5,
            "max_retries": 3
        }
    )
    
    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == "task-123"
    assert "enqueued successfully" in data["message"]
    
    # Verify manager was called correctly
    manager.enqueue_task.assert_called_once()
    call_args = manager.enqueue_task.call_args[1]
    assert call_args["task_name"] == "afirgen_tasks.email.send_confirmation"
    assert call_args["task_type"] == TaskType.EMAIL
    assert call_args["priority"] == 5


def test_enqueue_task_invalid_type(client):
    """Test enqueueing task with invalid type"""
    test_client, manager = client
    
    # Make request with invalid task type
    response = test_client.post(
        "/api/tasks/enqueue",
        json={
            "task_name": "test_task",
            "task_type": "invalid_type",
            "params": {},
            "priority": 5
        }
    )
    
    # Verify error response
    assert response.status_code == 400
    assert "Invalid task_type" in response.json()["detail"]


def test_enqueue_task_invalid_priority(client):
    """Test enqueueing task with invalid priority"""
    test_client, manager = client
    
    # Make request with priority too high
    response = test_client.post(
        "/api/tasks/enqueue",
        json={
            "task_name": "test_task",
            "task_type": "email",
            "params": {},
            "priority": 15  # Invalid: > 10
        }
    )
    
    # Verify validation error
    assert response.status_code == 422


def test_get_task_status_found(client):
    """Test getting task status when task exists"""
    test_client, manager = client
    
    # Mock get_task_status to return task data
    manager.get_task_status = Mock(return_value={
        "task_id": "task-123",
        "task_name": "afirgen_tasks.email.send_confirmation",
        "task_type": "email",
        "priority": 5,
        "status": "completed",
        "params": {"fir_id": "fir_123"},
        "result": {"status": "success"},
        "error_message": None,
        "retry_count": 0,
        "max_retries": 3,
        "created_at": "2024-01-15T10:30:00",
        "started_at": "2024-01-15T10:30:05",
        "completed_at": "2024-01-15T10:30:10"
    })
    
    # Make request
    response = test_client.get("/api/tasks/task-123")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-123"
    assert data["status"] == "completed"
    assert data["result"]["status"] == "success"


def test_get_task_status_not_found(client):
    """Test getting task status when task doesn't exist"""
    test_client, manager = client
    
    # Mock get_task_status to return None
    manager.get_task_status = Mock(return_value=None)
    
    # Make request
    response = test_client.get("/api/tasks/nonexistent-task")
    
    # Verify error response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_tasks_no_filters(client):
    """Test listing tasks without filters"""
    test_client, manager = client
    
    # Mock list_tasks and get_task_count
    manager.list_tasks = Mock(return_value=[
        {
            "task_id": "task-1",
            "task_name": "afirgen_tasks.email.send_confirmation",
            "task_type": "email",
            "priority": 5,
            "status": "completed",
            "params": {},
            "result": {},
            "error_message": None,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": "2024-01-15T10:30:00",
            "started_at": "2024-01-15T10:30:05",
            "completed_at": "2024-01-15T10:30:10"
        },
        {
            "task_id": "task-2",
            "task_name": "afirgen_tasks.reports.generate_pdf",
            "task_type": "report",
            "priority": 7,
            "status": "running",
            "params": {},
            "result": None,
            "error_message": None,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": "2024-01-15T10:31:00",
            "started_at": "2024-01-15T10:31:05",
            "completed_at": None
        }
    ])
    manager.get_task_count = Mock(return_value=2)
    
    # Make request
    response = test_client.get("/api/tasks/")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["total_count"] == 2
    assert data["limit"] == 100
    assert data["offset"] == 0


def test_list_tasks_with_status_filter(client):
    """Test listing tasks with status filter"""
    test_client, manager = client
    
    # Mock list_tasks and get_task_count
    manager.list_tasks = Mock(return_value=[])
    manager.get_task_count = Mock(return_value=0)
    
    # Make request with status filter
    response = test_client.get("/api/tasks/?status=completed")
    
    # Verify response
    assert response.status_code == 200
    
    # Verify manager was called with correct filter
    manager.list_tasks.assert_called_once()
    call_args = manager.list_tasks.call_args[1]
    assert call_args["status"] == TaskStatus.COMPLETED


def test_list_tasks_with_type_filter(client):
    """Test listing tasks with type filter"""
    test_client, manager = client
    
    # Mock list_tasks and get_task_count
    manager.list_tasks = Mock(return_value=[])
    manager.get_task_count = Mock(return_value=0)
    
    # Make request with type filter
    response = test_client.get("/api/tasks/?task_type=email")
    
    # Verify response
    assert response.status_code == 200
    
    # Verify manager was called with correct filter
    manager.list_tasks.assert_called_once()
    call_args = manager.list_tasks.call_args[1]
    assert call_args["task_type"] == TaskType.EMAIL


def test_list_tasks_with_pagination(client):
    """Test listing tasks with pagination parameters"""
    test_client, manager = client
    
    # Mock list_tasks and get_task_count
    manager.list_tasks = Mock(return_value=[])
    manager.get_task_count = Mock(return_value=150)
    
    # Make request with pagination
    response = test_client.get("/api/tasks/?limit=50&offset=100")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 50
    assert data["offset"] == 100
    assert data["total_count"] == 150
    
    # Verify manager was called with correct pagination
    manager.list_tasks.assert_called_once()
    call_args = manager.list_tasks.call_args[1]
    assert call_args["limit"] == 50
    assert call_args["offset"] == 100


def test_list_tasks_invalid_status(client):
    """Test listing tasks with invalid status filter"""
    test_client, manager = client
    
    # Make request with invalid status
    response = test_client.get("/api/tasks/?status=invalid_status")
    
    # Verify error response
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_get_task_count_no_filters(client):
    """Test getting task count without filters"""
    test_client, manager = client
    
    # Mock get_task_count
    manager.get_task_count = Mock(return_value=42)
    
    # Make request
    response = test_client.get("/api/tasks/count/all")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 42
    assert data["status"] is None
    assert data["task_type"] is None


def test_get_task_count_with_filters(client):
    """Test getting task count with filters"""
    test_client, manager = client
    
    # Mock get_task_count
    manager.get_task_count = Mock(return_value=10)
    
    # Make request with filters
    response = test_client.get("/api/tasks/count/all?status=pending&task_type=email")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 10
    assert data["status"] == "pending"
    assert data["task_type"] == "email"
    
    # Verify manager was called with correct filters
    manager.get_task_count.assert_called_once()
    call_args = manager.get_task_count.call_args[1]
    assert call_args["status"] == TaskStatus.PENDING
    assert call_args["task_type"] == TaskType.EMAIL


def test_cancel_task_success(client):
    """Test successful task cancellation"""
    test_client, manager = client
    
    # Mock cancel_task to return success
    manager.cancel_task = Mock(return_value=True)
    
    # Make request
    response = test_client.post("/api/tasks/task-123/cancel")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-123"
    assert data["success"] is True
    assert "cancelled successfully" in data["message"]


def test_cancel_task_not_found(client):
    """Test cancelling non-existent task"""
    test_client, manager = client
    
    # Mock cancel_task to return failure
    manager.cancel_task = Mock(return_value=False)
    
    # Make request
    response = test_client.post("/api/tasks/nonexistent-task/cancel")
    
    # Verify error response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
