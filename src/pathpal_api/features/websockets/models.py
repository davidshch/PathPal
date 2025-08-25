"""Pydantic models for WebSocket message schemas."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""

    LOCATION_UPDATE = "location_update"
    PARTICIPANT_LOCATION = "participant_location"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    CONNECTION_ACK = "connection_ack"
    ERROR = "error"


class Location(BaseModel):
    """Geographic coordinates."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class LocationUpdateMessage(BaseModel):
    """Incoming location update from client."""

    type: Literal[MessageType.LOCATION_UPDATE]
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class ParticipantLocationMessage(BaseModel):
    """Outgoing participant location broadcast."""

    type: Literal[MessageType.PARTICIPANT_LOCATION]
    user_id: str
    full_name: str
    location: Location


class ParticipantJoinedMessage(BaseModel):
    """Notification when participant joins trip."""

    type: Literal[MessageType.PARTICIPANT_JOINED]
    user_id: str
    full_name: str
    participant_count: int


class ParticipantLeftMessage(BaseModel):
    """Notification when participant leaves trip."""

    type: Literal[MessageType.PARTICIPANT_LEFT]
    user_id: str
    full_name: str
    participant_count: int


class ConnectionAckMessage(BaseModel):
    """Connection acknowledgment with trip info."""

    type: Literal[MessageType.CONNECTION_ACK]
    trip_id: str
    participant_count: int
    message: str


class ErrorMessage(BaseModel):
    """Error message for client."""

    type: Literal[MessageType.ERROR]
    error: str
    detail: str = ""


# Union type for all possible outgoing messages
OutgoingMessage = (
    ParticipantLocationMessage
    | ParticipantJoinedMessage
    | ParticipantLeftMessage
    | ConnectionAckMessage
    | ErrorMessage
)
