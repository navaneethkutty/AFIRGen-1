"""
Repository layer for database access with optimization patterns.

This module provides the repository pattern implementation with:
- Selective column retrieval
- Cursor-based pagination
- Optimized joins with index hints
- Database-level aggregation

Requirements: 1.3, 1.4, 1.5, 1.6
"""

from .base_repository import BaseRepository, PaginatedResult, CursorInfo
from .fir_repository import FIRRepository

__all__ = [
    'BaseRepository',
    'PaginatedResult',
    'CursorInfo',
    'FIRRepository',
]
