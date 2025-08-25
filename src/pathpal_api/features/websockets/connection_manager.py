"""WebSocket connection management for real-time location sharing."""

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by trip ID."""

    def __init__(self):
        # trip_id -> {user_id: websocket}
        self.trip_connections: dict[str, dict[str, WebSocket]] = {}
        self.user_trip_mapping: dict[str, str] = {}  # user_id -> trip_id

    async def connect(self, websocket: WebSocket, trip_id: str, user_id: str):
        """Accept WebSocket connection and add to trip group."""
        await websocket.accept()

        if trip_id not in self.trip_connections:
            self.trip_connections[trip_id] = {}

        self.trip_connections[trip_id][user_id] = websocket
        self.user_trip_mapping[user_id] = trip_id

        logger.info(f"User {user_id} connected to trip {trip_id}")

    def disconnect(self, user_id: str):
        """Remove user connection and clean up."""
        trip_id = self.user_trip_mapping.pop(user_id, None)
        if not trip_id:
            return

        if trip_id in self.trip_connections:
            self.trip_connections[trip_id].pop(user_id, None)

            # Clean up empty trip rooms
            if not self.trip_connections[trip_id]:
                del self.trip_connections[trip_id]

        logger.info(f"User {user_id} disconnected from trip {trip_id}")

    async def send_personal_message(self, message: str, user_id: str):
        """Send message to specific user."""
        trip_id = self.user_trip_mapping.get(user_id)
        if not trip_id:
            return False

        websocket = self.trip_connections.get(trip_id, {}).get(user_id)
        if websocket:
            try:
                await websocket.send_text(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                self.disconnect(user_id)
        return False

    async def broadcast_to_trip(self, message: str, trip_id: str, exclude_user: str = None):
        """Broadcast message to all users in a trip except excluded user."""
        if trip_id not in self.trip_connections:
            return

        disconnected_users = []
        connections = self.trip_connections[trip_id].copy()

        for user_id, websocket in connections.items():
            if user_id == exclude_user:
                continue

            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
                disconnected_users.append(user_id)

        # Clean up failed connections
        for user_id in disconnected_users:
            self.disconnect(user_id)

    def get_trip_participants(self, trip_id: str) -> list[str]:
        """Get list of connected user IDs for a trip."""
        return list(self.trip_connections.get(trip_id, {}).keys())


# Singleton instance
connection_manager = ConnectionManager()
