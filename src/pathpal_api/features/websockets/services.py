"""Location sharing services and business logic."""

import logging
from datetime import datetime
from uuid import UUID

from .connection_manager import ConnectionManager
from .models import Location, MessageType, ParticipantLocationMessage

logger = logging.getLogger(__name__)


async def handle_location_update(
    trip_id: str,
    user_id: str,
    user_name: str,
    latitude: float,
    longitude: float,
    connection_manager: ConnectionManager,
) -> bool:
    """Process location update and broadcast to trip participants."""

    try:
        # Create participant location message
        location_message = ParticipantLocationMessage(
            type=MessageType.PARTICIPANT_LOCATION,
            user_id=user_id,
            full_name=user_name,
            location=Location(latitude=latitude, longitude=longitude),
        )

        # Broadcast to all participants except sender
        await connection_manager.broadcast_to_trip(
            location_message.model_dump_json(), trip_id, exclude_user=user_id
        )

        logger.debug(f"Location update broadcasted for user {user_id} in trip {trip_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to handle location update: {e}")
        return False


async def get_active_trip_participants(trip_id: str) -> int:
    """Get count of currently connected participants for a trip."""
    from .connection_manager import connection_manager

    return len(connection_manager.get_trip_participants(trip_id))


# Optional: Location history storage for future analytics
async def store_location_history(
    trip_id: UUID,
    user_id: UUID,
    latitude: float,
    longitude: float,
    timestamp: datetime | None = None,
) -> bool:
    """Store location point for trip analysis (future feature)."""
    # Implementation placeholder for location history
    # Could store in database for route analysis, safety insights, etc.
    logger.debug(f"Location history storage not implemented (trip: {trip_id})")
    return True
