"""
API module for AFIRGen backend.

This module contains API endpoint definitions.
"""

from .task_endpoints import create_task_router

__all__ = ["create_task_router"]
