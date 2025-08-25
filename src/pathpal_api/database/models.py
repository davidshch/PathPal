"""SQLModel database models for PathPal API."""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    pass


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class TravelMode(str, Enum):
    """Supported travel modes for route calculation."""

    DRIVING = "driving"
    WALKING = "walking"
    CYCLING = "cycling"


class User(SQLModel, table=True):
    """User model for authentication and profiles."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=254)
    hashed_password: str = Field(max_length=128)
    full_name: str = Field(max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime | None = Field(default=None)

    # Relationships
    emergency_contacts: list["EmergencyContact"] = Relationship(back_populates="user")
    trips: list["Trip"] = Relationship(back_populates="owner")
    alerts: list["Alert"] = Relationship(back_populates="user")


class EmergencyContact(SQLModel, table=True):
    """Emergency contact model linked to users."""

    __tablename__ = "emergency_contacts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    contact_email: str = Field(max_length=254)
    created_at: datetime = Field(default_factory=utcnow)

    # Relationship back to user
    user: User = Relationship(back_populates="emergency_contacts")


class Trip(SQLModel, table=True):
    """Core trip model with route information."""

    __tablename__ = "trips"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="users.id")
    destination_name: str = Field(max_length=200)

    # Coordinates
    start_latitude: float = Field(ge=-90.0, le=90.0)
    start_longitude: float = Field(ge=-180.0, le=180.0)
    destination_latitude: float = Field(ge=-90.0, le=90.0)
    destination_longitude: float = Field(ge=-180.0, le=180.0)

    # Route information from Mapbox
    route_geometry: str = Field()  # Polyline-encoded route
    distance_meters: int = Field(ge=0)
    duration_seconds: int = Field(ge=0)
    travel_mode: TravelMode = Field(default=TravelMode.WALKING)

    # Trip metadata
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = Field(default=None)

    # Relationships
    owner: User = Relationship(back_populates="trips")
    participants: list["TripParticipant"] = Relationship(back_populates="trip")


class TripParticipant(SQLModel, table=True):
    """Join table for trip participants (buddy system)."""

    __tablename__ = "trip_participants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trip_id: UUID = Field(foreign_key="trips.id")
    user_id: UUID = Field(foreign_key="users.id")
    joined_at: datetime = Field(default_factory=utcnow)

    # Relationships
    trip: Trip = Relationship(back_populates="participants")
    user: User = Relationship()


class Alert(SQLModel, table=True):
    """Emergency alert record for tracking and debugging."""

    __tablename__ = "alerts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Location data
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

    # AI processing results
    transcript: str = Field(default="", max_length=5000)
    ai_analysis: str = Field(default="", max_length=1000)

    # Alert metadata
    contacts_notified: int = Field(ge=0)
    processing_status: str = Field(max_length=20)  # success, fallback, failed
    error_details: str | None = Field(default=None, max_length=1000)

    # Timestamps
    created_at: datetime = Field(default_factory=utcnow)
    processed_at: datetime | None = Field(default=None)

    # Relationships
    user: User = Relationship(back_populates="alerts")
