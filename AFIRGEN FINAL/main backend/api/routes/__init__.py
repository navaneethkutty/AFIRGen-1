"""
API routes module.

This module contains all API endpoint definitions organized by domain.
"""

from .fir_routes import router as fir_router
from .health_routes import router as health_router

__all__ = ["fir_router", "health_router"]
