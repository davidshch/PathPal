"""Unit tests for WebSocket ConnectionManager."""

from unittest.mock import AsyncMock, Mock

import pytest

from pathpal_api.features.websockets.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test cases for ConnectionManager."""

    def test_init(self):
        """Test ConnectionManager initialization."""
        manager = ConnectionManager()
        assert manager.trip_connections == {}
        assert manager.user_trip_mapping == {}

    @pytest.mark.asyncio
    async def test_connect_user_to_trip(self):
        """Test connecting a user to a trip."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        trip_id = "trip-123"
        user_id = "user-456"

        await manager.connect(websocket, trip_id, user_id)

        # Verify WebSocket was accepted
        websocket.accept.assert_called_once()

        # Verify connections are stored correctly
        assert trip_id in manager.trip_connections
        assert user_id in manager.trip_connections[trip_id]
        assert manager.trip_connections[trip_id][user_id] == websocket
        assert manager.user_trip_mapping[user_id] == trip_id

    @pytest.mark.asyncio
    async def test_connect_multiple_users_to_trip(self):
        """Test connecting multiple users to same trip."""
        manager = ConnectionManager()
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        trip_id = "trip-123"
        user1_id = "user-456"
        user2_id = "user-789"

        await manager.connect(websocket1, trip_id, user1_id)
        await manager.connect(websocket2, trip_id, user2_id)

        # Verify both users are in the same trip
        assert len(manager.trip_connections[trip_id]) == 2
        assert manager.trip_connections[trip_id][user1_id] == websocket1
        assert manager.trip_connections[trip_id][user2_id] == websocket2

    def test_disconnect_user(self):
        """Test disconnecting a user from a trip."""
        manager = ConnectionManager()
        trip_id = "trip-123"
        user_id = "user-456"
        websocket = Mock()

        # Manually set up connection
        manager.trip_connections[trip_id] = {user_id: websocket}
        manager.user_trip_mapping[user_id] = trip_id

        # Disconnect user
        manager.disconnect(user_id)

        # Verify user is removed
        assert user_id not in manager.user_trip_mapping
        assert trip_id not in manager.trip_connections  # Empty trip removed

    def test_disconnect_user_cleans_up_empty_trip(self):
        """Test that empty trips are cleaned up after last user disconnects."""
        manager = ConnectionManager()
        trip_id = "trip-123"
        user1_id = "user-456"
        user2_id = "user-789"
        websocket1 = Mock()
        websocket2 = Mock()

        # Set up two users in same trip
        manager.trip_connections[trip_id] = {user1_id: websocket1, user2_id: websocket2}
        manager.user_trip_mapping[user1_id] = trip_id
        manager.user_trip_mapping[user2_id] = trip_id

        # Disconnect first user
        manager.disconnect(user1_id)

        # Trip should still exist with second user
        assert trip_id in manager.trip_connections
        assert len(manager.trip_connections[trip_id]) == 1

        # Disconnect second user
        manager.disconnect(user2_id)

        # Trip should be cleaned up
        assert trip_id not in manager.trip_connections

    def test_disconnect_nonexistent_user(self):
        """Test disconnecting a user that doesn't exist."""
        manager = ConnectionManager()
        # Should not raise an error
        manager.disconnect("nonexistent-user")

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self):
        """Test sending personal message to connected user."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        trip_id = "trip-123"
        user_id = "user-456"
        message = "test message"

        # Set up connection
        manager.trip_connections[trip_id] = {user_id: websocket}
        manager.user_trip_mapping[user_id] = trip_id

        result = await manager.send_personal_message(message, user_id)

        assert result is True
        websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_user_not_connected(self):
        """Test sending message to user that's not connected."""
        manager = ConnectionManager()
        result = await manager.send_personal_message("test", "nonexistent-user")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_personal_message_websocket_error(self):
        """Test handling WebSocket error during personal message send."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.send_text.side_effect = Exception("Connection lost")
        trip_id = "trip-123"
        user_id = "user-456"

        # Set up connection
        manager.trip_connections[trip_id] = {user_id: websocket}
        manager.user_trip_mapping[user_id] = trip_id

        result = await manager.send_personal_message("test", user_id)

        assert result is False
        # User should be disconnected due to error
        assert user_id not in manager.user_trip_mapping

    @pytest.mark.asyncio
    async def test_broadcast_to_trip(self):
        """Test broadcasting message to all users in trip."""
        manager = ConnectionManager()
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        trip_id = "trip-123"
        user1_id = "user-456"
        user2_id = "user-789"
        message = "broadcast message"

        # Set up connections
        manager.trip_connections[trip_id] = {user1_id: websocket1, user2_id: websocket2}
        manager.user_trip_mapping[user1_id] = trip_id
        manager.user_trip_mapping[user2_id] = trip_id

        await manager.broadcast_to_trip(message, trip_id)

        # Both users should receive message
        websocket1.send_text.assert_called_once_with(message)
        websocket2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_trip_exclude_user(self):
        """Test broadcasting with excluded user."""
        manager = ConnectionManager()
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        trip_id = "trip-123"
        user1_id = "user-456"
        user2_id = "user-789"
        message = "broadcast message"

        # Set up connections
        manager.trip_connections[trip_id] = {user1_id: websocket1, user2_id: websocket2}

        await manager.broadcast_to_trip(message, trip_id, exclude_user=user1_id)

        # Only user2 should receive message
        websocket1.send_text.assert_not_called()
        websocket2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_trip(self):
        """Test broadcasting to trip that doesn't exist."""
        manager = ConnectionManager()
        # Should not raise error
        await manager.broadcast_to_trip("message", "nonexistent-trip")

    def test_get_trip_participants(self):
        """Test getting list of trip participants."""
        manager = ConnectionManager()
        trip_id = "trip-123"
        user1_id = "user-456"
        user2_id = "user-789"
        websocket1 = Mock()
        websocket2 = Mock()

        # Set up connections
        manager.trip_connections[trip_id] = {user1_id: websocket1, user2_id: websocket2}

        participants = manager.get_trip_participants(trip_id)

        assert len(participants) == 2
        assert user1_id in participants
        assert user2_id in participants

    def test_get_trip_participants_empty_trip(self):
        """Test getting participants for empty trip."""
        manager = ConnectionManager()
        participants = manager.get_trip_participants("nonexistent-trip")
        assert participants == []
