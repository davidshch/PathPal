"""WebSocket handlers for real-time location sharing."""

import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ...auth.security import authenticate_websocket_token
from ...database.connection import async_session
from ...features.trips.services import get_trip_by_id
from .connection_manager import connection_manager
from .exceptions import TripAccessError, WebSocketAuthError
from .models import LocationUpdateMessage, MessageType
from .services import handle_location_update

router = APIRouter(prefix="/ws", tags=["WebSockets"])
logger = logging.getLogger(__name__)


@router.websocket("/{trip_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    trip_id: str,
    token: str = Query(..., description="JWT authentication token"),
):
    """WebSocket endpoint for real-time location sharing within a trip."""

    try:
        # Authenticate user
        user = await authenticate_websocket_token(token)
        user_id = str(user.id)

        # Verify user has access to this trip
        async with async_session() as db:
            trip = await get_trip_by_id(db, trip_id, user.id)
            if not trip:
                await websocket.close(code=4003, reason="Trip not found or access denied")
                return

            if not trip.is_active:
                await websocket.close(code=4004, reason="Trip is not active")
                return

        # Connect to WebSocket
        await connection_manager.connect(websocket, trip_id, user_id)

        # Send connection acknowledgment
        participant_count = len(connection_manager.get_trip_participants(trip_id))
        ack_message = {
            "type": MessageType.CONNECTION_ACK,
            "trip_id": trip_id,
            "participant_count": participant_count,
            "message": f"Connected to trip: {trip.destination_name}",
        }
        await websocket.send_text(json.dumps(ack_message))

        # Notify other participants
        join_message = {
            "type": MessageType.PARTICIPANT_JOINED,
            "user_id": user_id,
            "full_name": user.full_name,
            "participant_count": participant_count,
        }
        await connection_manager.broadcast_to_trip(
            json.dumps(join_message), trip_id, exclude_user=user_id
        )

        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Validate message type
                if message_data.get("type") == MessageType.LOCATION_UPDATE:
                    location_msg = LocationUpdateMessage(**message_data)

                    # Process location update
                    await handle_location_update(
                        trip_id=trip_id,
                        user_id=user_id,
                        user_name=user.full_name,
                        latitude=location_msg.latitude,
                        longitude=location_msg.longitude,
                        connection_manager=connection_manager,
                    )
                else:
                    error_msg = {
                        "type": MessageType.ERROR,
                        "error": "Unknown message type",
                        "detail": f"Received: {message_data.get('type')}",
                    }
                    await websocket.send_text(json.dumps(error_msg))

            except json.JSONDecodeError:
                error_msg = {"type": MessageType.ERROR, "error": "Invalid JSON format"}
                await websocket.send_text(json.dumps(error_msg))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                error_msg = {
                    "type": MessageType.ERROR,
                    "error": "Message processing failed",
                    "detail": str(e),
                }
                await websocket.send_text(json.dumps(error_msg))

    except WebSocketAuthError as e:
        await websocket.close(code=4001, reason=f"Authentication failed: {str(e)}")
    except TripAccessError as e:
        await websocket.close(code=4003, reason=str(e))
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from trip {trip_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        # Clean up connection
        if "user_id" in locals():
            connection_manager.disconnect(user_id)

            # Notify remaining participants
            try:
                remaining_count = len(connection_manager.get_trip_participants(trip_id))
                if remaining_count > 0:
                    leave_message = {
                        "type": MessageType.PARTICIPANT_LEFT,
                        "user_id": user_id,
                        "full_name": user.full_name,
                        "participant_count": remaining_count,
                    }
                    await connection_manager.broadcast_to_trip(json.dumps(leave_message), trip_id)
            except Exception as e:
                logger.error(f"Error notifying participant leave: {e}")
