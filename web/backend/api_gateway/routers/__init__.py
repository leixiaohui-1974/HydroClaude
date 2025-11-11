"""
API routers for different endpoints
"""

# Use database version of simulation router
from .simulation_db import router as simulation_router

__all__ = ['simulation_router']
