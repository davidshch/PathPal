"""WebSocket real-time location sharing feature module."""

from .connection_manager import connection_manager
from .handlers import router

__all__ = ["connection_manager", "router"]
