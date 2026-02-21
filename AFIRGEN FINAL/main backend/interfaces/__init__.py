"""
Interfaces module for AFIRGen backend.

This module defines abstract base classes and interfaces for:
- Repository layer (database access)
- Cache layer (Redis caching)
- External services (model servers, etc.)

These interfaces establish clear contracts between layers and enable
dependency injection, testing, and maintainability.

Requirements: 8.3 - Define clear interfaces for database, cache, and external service interactions
"""

from .repository import IRepository
from .cache import ICacheManager
from .external_service import IExternalService, IModelServer

__all__ = [
    'IRepository',
    'ICacheManager',
    'IExternalService',
    'IModelServer',
]
