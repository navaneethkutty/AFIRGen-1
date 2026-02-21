"""
Background Task Status API Endpoints

This module provides REST API endpoints for querying background task status.

Requirements: 4.6
Task: 6.2 Create background task manager
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from infrastructure.background_task_manager import (
    BackgroundTaskManager,
    TaskStatus,
    TaskType
)


# Pydantic models for API requests/responses
class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    task_name: str
    task_type: str
    priority: int
    status: str
    params: Optional[dict] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response model for task list"""
    tasks: List[TaskStatusResponse]
    total_count: int
    limit: int
    offset: int


class TaskCountResponse(BaseModel):
    """Response model for task count"""
    count: int
    status: Optional[str] = None
    task_type: Optional[str] = None


class EnqueueTaskRequest(BaseModel):
    """Request model for enqueueing a task"""
    task_name: str = Field(..., description="Celery task name")
    task_type: str = Field(..., description="Task type (email, report, analytics, cleanup)")
    params: dict = Field(default_factory=dict, description="Task parameters")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1-10)")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")


class EnqueueTaskResponse(BaseModel):
    """Response model for enqueued task"""
    task_id: str
    message: str


class CancelTaskResponse(BaseModel):
    """Response model for task cancellation"""
    task_id: str
    success: bool
    message: str


def create_task_router(task_manager: BackgroundTaskManager) -> APIRouter:
    """
    Create FastAPI router with task status endpoints.
    
    Args:
        task_manager: BackgroundTaskManager instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/tasks", tags=["Background Tasks"])
    
    @router.post("/enqueue", response_model=EnqueueTaskResponse, status_code=201)
    async def enqueue_task(request: EnqueueTaskRequest):
        """
        Enqueue a background task with priority support.
        
        Requirements: 4.1, 4.5
        """
        # Validate task type
        try:
            task_type_enum = TaskType(request.task_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task_type. Must be one of: {[t.value for t in TaskType]}"
            )
        
        try:
            # Enqueue task
            task_id = task_manager.enqueue_task(
                task_name=request.task_name,
                task_type=task_type_enum,
                params=request.params,
                priority=request.priority,
                max_retries=request.max_retries
            )
            
            return EnqueueTaskResponse(
                task_id=task_id,
                message=f"Task enqueued successfully with priority {request.priority}"
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {str(e)}")
    
    @router.get("/{task_id}", response_model=TaskStatusResponse)
    async def get_task_status(task_id: str):
        """
        Get status of a specific background task.
        
        Requirements: 4.4, 4.6
        """
        task = task_manager.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return TaskStatusResponse(**task)
    
    @router.get("/", response_model=TaskListResponse)
    async def list_tasks(
        status: Optional[str] = Query(None, description="Filter by task status"),
        task_type: Optional[str] = Query(None, description="Filter by task type"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
        offset: int = Query(0, ge=0, description="Number of tasks to skip")
    ):
        """
        List background tasks with optional filtering.
        
        Requirements: 4.6
        """
        # Validate and convert status filter
        status_enum = None
        if status:
            try:
                status_enum = TaskStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {[s.value for s in TaskStatus]}"
                )
        
        # Validate and convert task_type filter
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = TaskType(task_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid task_type. Must be one of: {[t.value for t in TaskType]}"
                )
        
        # Get tasks
        tasks = task_manager.list_tasks(
            status=status_enum,
            task_type=task_type_enum,
            limit=limit,
            offset=offset
        )
        
        # Get total count
        total_count = task_manager.get_task_count(
            status=status_enum,
            task_type=task_type_enum
        )
        
        return TaskListResponse(
            tasks=[TaskStatusResponse(**task) for task in tasks],
            total_count=total_count,
            limit=limit,
            offset=offset
        )
    
    @router.get("/count/all", response_model=TaskCountResponse)
    async def get_task_count(
        status: Optional[str] = Query(None, description="Filter by task status"),
        task_type: Optional[str] = Query(None, description="Filter by task type")
    ):
        """
        Get count of tasks matching filters.
        
        Requirements: 4.6
        """
        # Validate filters
        status_enum = None
        if status:
            try:
                status_enum = TaskStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {[s.value for s in TaskStatus]}"
                )
        
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = TaskType(task_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid task_type. Must be one of: {[t.value for t in TaskType]}"
                )
        
        count = task_manager.get_task_count(
            status=status_enum,
            task_type=task_type_enum
        )
        
        return TaskCountResponse(
            count=count,
            status=status,
            task_type=task_type
        )
    
    @router.post("/{task_id}/cancel", response_model=CancelTaskResponse)
    async def cancel_task(task_id: str):
        """
        Cancel a pending or running task.
        """
        success = task_manager.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found or already completed"
            )
        
        return CancelTaskResponse(
            task_id=task_id,
            success=True,
            message="Task cancelled successfully"
        )
    
    return router
