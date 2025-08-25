"""Pydantic schemas for trip requests and responses."""

from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field


class TravelMode(str, Enum):
    DRIVING = "driving"
    WALKING = "walking"
    CYCLING = "cycling"


class Location(BaseModel):
    """Geographic location with validation."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class TripCreate(BaseModel):
    """Create new trip request."""

    destination_name: str = Field(..., min_length=1, max_length=200)
    destination_location: Location | None = None  # Optional - will geocode if None
    start_location: Location  # User's current location from mobile app
    travel_mode: TravelMode = TravelMode.WALKING


class TripPublic(BaseModel):
    """Public trip response with route information."""

    id: UUID4
    owner_id: UUID4
    destination_name: str

    # Locations
    start_latitude: float
    start_longitude: float
    destination_latitude: float
    destination_longitude: float

    # Route details
    route_geometry: str  # Polyline-encoded
    distance_meters: int
    duration_seconds: int
    travel_mode: TravelMode

    # Metadata
    is_active: bool
    created_at: datetime
    completed_at: datetime | None = None
    participant_count: int = 0  # Number of joined participants

    model_config = {"from_attributes": True}


class TripList(BaseModel):
    """Paginated list of trips."""

    trips: list[TripPublic]
    total: int
    page: int
    page_size: int


class RouteGeometry(BaseModel):
    """Decoded route geometry for client display."""

    coordinates: list[list[float]]  # [[lat, lon], [lat, lon], ...]


class TripParticipantRequest(BaseModel):
    """Request to join/leave trip."""

    action: str = Field(..., pattern="^(join|leave)$")
