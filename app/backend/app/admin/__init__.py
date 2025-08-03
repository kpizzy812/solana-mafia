"""
Admin dashboard API module for system monitoring and management.
"""

from .admin_auth import AdminAuth, require_admin_auth
from .monitoring import MonitoringService, get_monitoring_service
from .admin_routes import admin_router

__all__ = [
    "AdminAuth",
    "require_admin_auth", 
    "MonitoringService",
    "get_monitoring_service",
    "admin_router"
]