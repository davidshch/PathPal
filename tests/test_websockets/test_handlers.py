"""Integration tests for WebSocket handlers."""

import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from pathpal_api.database.models import TravelMode, Trip, User
from pathpal_api.features.websockets.models import MessageType
from pathpal_api.main import app


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password="fake_hash",
        is_active=True,
    )


@pytest.fixture
def sample_trip(sample_user):
    """Create a sample active trip for testing."""
    return Trip(
        id=uuid4(),
        owner_id=sample_user.id,
        destination_name="Central Park",
        start_latitude=40.7589,
        start_longitude=-73.9851,
        destination_latitude=40.7812,
        destination_longitude=-73.9665,
        route_geometry="sample_polyline",
        distance_meters=1500,
        duration_seconds=1200,
        travel_mode=TravelMode.WALKING,
        is_active=True,
    )


@pytest.fixture
def valid_jwt_token():
    """Return a valid JWT token for testing."""
    return "valid_jwt_token_here"


@pytest.fixture
def ws_client():
    """WebSocket test client."""
    return TestClient(app)


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_connection_success(
        self, ws_client, valid_jwt_token, sample_trip, sample_user
    ):
        """Test successful WebSocket connection with valid authentication."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                with ws_client.websocket_connect(
                    f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                ) as websocket:
                    # Should receive connection acknowledgment
                    data = websocket.receive_text()
                    message = json.loads(data)

                    assert message["type"] == MessageType.CONNECTION_ACK
                    assert message["trip_id"] == str(sample_trip.id)
                    assert message["participant_count"] == 1
                    assert "Connected to trip: Central Park" in message["message"]

    @pytest.mark.asyncio
    async def test_websocket_invalid_token(self, ws_client):
        """Test WebSocket connection with invalid token."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            from pathpal_api.features.websockets.exceptions import WebSocketAuthError

            mock_auth.side_effect = WebSocketAuthError("Invalid token")

            with pytest.raises(Exception):  # WebSocket connection should fail
                with ws_client.websocket_connect("/ws/test-trip-id?token=invalid"):
                    pass

    @pytest.mark.asyncio
    async def test_websocket_trip_not_found(self, ws_client, valid_jwt_token, sample_user):
        """Test WebSocket connection to non-existent trip."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = None  # Trip not found

                with pytest.raises(Exception):  # Should close with error code
                    with ws_client.websocket_connect(
                        f"/ws/nonexistent-trip?token={valid_jwt_token}"
                    ):
                        pass

    @pytest.mark.asyncio
    async def test_websocket_inactive_trip(
        self, ws_client, valid_jwt_token, sample_trip, sample_user
    ):
        """Test WebSocket connection to inactive trip."""

        # Make trip inactive
        sample_trip.is_active = False

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                with pytest.raises(Exception):  # Should close with error code
                    with ws_client.websocket_connect(
                        f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                    ):
                        pass

    @pytest.mark.asyncio
    async def test_location_update_message(
        self, ws_client, valid_jwt_token, sample_trip, sample_user
    ):
        """Test sending location update message."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                with ws_client.websocket_connect(
                    f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                ) as websocket:
                    # Receive connection ack
                    websocket.receive_text()

                    # Send location update
                    location_update = {
                        "type": MessageType.LOCATION_UPDATE,
                        "latitude": 40.7580,
                        "longitude": -73.9855,
                    }
                    websocket.send_text(json.dumps(location_update))

                    # No direct response expected for location updates
                    # The message should be processed successfully

    @pytest.mark.asyncio
    async def test_invalid_message_type(self, ws_client, valid_jwt_token, sample_trip, sample_user):
        """Test sending message with invalid type."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                with ws_client.websocket_connect(
                    f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                ) as websocket:
                    # Receive connection ack
                    websocket.receive_text()

                    # Send invalid message type
                    invalid_message = {"type": "invalid_type", "data": "test"}
                    websocket.send_text(json.dumps(invalid_message))

                    # Should receive error message
                    response = websocket.receive_text()
                    error_message = json.loads(response)

                    assert error_message["type"] == MessageType.ERROR
                    assert "Unknown message type" in error_message["error"]

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, ws_client, valid_jwt_token, sample_trip, sample_user):
        """Test sending invalid JSON message."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                with ws_client.websocket_connect(
                    f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                ) as websocket:
                    # Receive connection ack
                    websocket.receive_text()

                    # Send invalid JSON
                    websocket.send_text("invalid json")

                    # Should receive error message
                    response = websocket.receive_text()
                    error_message = json.loads(response)

                    assert error_message["type"] == MessageType.ERROR
                    assert error_message["error"] == "Invalid JSON format"

    @pytest.mark.asyncio
    async def test_location_update_invalid_coordinates(
        self, ws_client, valid_jwt_token, sample_trip, sample_user
    ):
        """Test location update with invalid coordinates."""

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            mock_auth.return_value = sample_user

            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                with ws_client.websocket_connect(
                    f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                ) as websocket:
                    # Receive connection ack
                    websocket.receive_text()

                    # Send location update with invalid latitude (> 90)
                    invalid_location = {
                        "type": MessageType.LOCATION_UPDATE,
                        "latitude": 91.0,  # Invalid - exceeds max latitude
                        "longitude": -73.9855,
                    }
                    websocket.send_text(json.dumps(invalid_location))

                    # Should receive error message
                    response = websocket.receive_text()
                    error_message = json.loads(response)

                    assert error_message["type"] == MessageType.ERROR
                    assert "Message processing failed" in error_message["error"]


class TestWebSocketBroadcasting:
    """Test cases for WebSocket message broadcasting."""

    @pytest.mark.asyncio
    async def test_multiple_users_same_trip(
        self, ws_client, valid_jwt_token, sample_trip, sample_user
    ):
        """Test multiple users connected to same trip."""

        # Create second user
        user2 = User(
            id=uuid4(),
            email="test2@example.com",
            full_name="Test User 2",
            hashed_password="fake_hash",
            is_active=True,
        )

        with patch("pathpal_api.auth.security.authenticate_websocket_token") as mock_auth:
            with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
                mock_get_trip.return_value = sample_trip

                # Mock auth to return different users for different calls
                mock_auth.side_effect = [sample_user, user2]

                with ws_client.websocket_connect(
                    f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                ) as ws1:
                    with ws_client.websocket_connect(
                        f"/ws/{sample_trip.id}?token={valid_jwt_token}"
                    ) as ws2:
                        # Both should receive connection acks
                        ack1 = json.loads(ws1.receive_text())
                        ack2 = json.loads(ws2.receive_text())

                        assert ack1["type"] == MessageType.CONNECTION_ACK
                        assert ack2["type"] == MessageType.CONNECTION_ACK

                        # User 1 should receive notification that user 2 joined
                        join_msg = json.loads(ws1.receive_text())
                        assert join_msg["type"] == MessageType.PARTICIPANT_JOINED
                        assert join_msg["user_id"] == str(user2.id)
                        assert join_msg["participant_count"] == 2
