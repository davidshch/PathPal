"""Core business logic for trip management."""

from uuid import UUID

import polyline
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...database.models import Trip, TripParticipant, utcnow
from . import models as schemas
from .external_apis.geocoding import geocode_destination
from .external_apis.mapbox_client import MapboxClient


async def create_trip_with_route(
    db: AsyncSession, trip_create: schemas.TripCreate, user_id: UUID, mapbox_client: MapboxClient
) -> schemas.TripPublic:
    """Create trip and calculate route using Mapbox."""

    # Geocode destination if coordinates not provided
    if trip_create.destination_location:
        dest_lat = trip_create.destination_location.latitude
        dest_lon = trip_create.destination_location.longitude
    else:
        dest_lat, dest_lon = await geocode_destination(mapbox_client, trip_create.destination_name)

    # Prepare coordinates for Mapbox (lon, lat format)
    start_coords = (trip_create.start_location.longitude, trip_create.start_location.latitude)
    dest_coords = (dest_lon, dest_lat)

    # Get route from Mapbox
    route_data = await mapbox_client.get_directions(
        coordinates=[start_coords, dest_coords], profile=trip_create.travel_mode.value
    )

    # Create trip record
    trip = Trip(
        owner_id=user_id,
        destination_name=trip_create.destination_name,
        start_latitude=trip_create.start_location.latitude,
        start_longitude=trip_create.start_location.longitude,
        destination_latitude=dest_lat,
        destination_longitude=dest_lon,
        route_geometry=route_data["geometry"],
        distance_meters=int(route_data["distance"]),
        duration_seconds=int(route_data["duration"]),
        travel_mode=trip_create.travel_mode,
    )

    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    # Convert to public schema with participant count
    trip_dict = trip.__dict__.copy()
    trip_dict["participant_count"] = 0
    return schemas.TripPublic(**trip_dict)


async def get_user_trips(
    db: AsyncSession, user_id: UUID, page: int, page_size: int, active_only: bool = False
) -> schemas.TripList:
    """Get paginated list of user's trips."""
    query = select(Trip).where(Trip.owner_id == user_id)

    if active_only:
        query = query.where(Trip.is_active)

    query = query.order_by(Trip.created_at.desc())

    # Get total count
    count_query = select(func.count(Trip.id)).where(Trip.owner_id == user_id)
    if active_only:
        count_query = count_query.where(Trip.is_active)

    total = await db.scalar(count_query)

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    trips = result.scalars().all()

    # Convert to public schema with participant counts
    trip_publics = []
    for trip in trips:
        participant_count = await db.scalar(
            select(func.count(TripParticipant.id)).where(TripParticipant.trip_id == trip.id)
        )
        trip_dict = trip.__dict__.copy()
        trip_dict["participant_count"] = participant_count or 0
        trip_publics.append(schemas.TripPublic(**trip_dict))

    return schemas.TripList(trips=trip_publics, total=total, page=page, page_size=page_size)


async def get_trip_by_id(
    db: AsyncSession, trip_id: UUID, user_id: UUID
) -> schemas.TripPublic | None:
    """Get trip by ID if user has access."""
    query = select(Trip).where(
        Trip.id == trip_id,
        Trip.owner_id == user_id,  # Only owner can view for now
    )
    result = await db.execute(query)
    trip = result.scalar_one_or_none()

    if not trip:
        return None

    participant_count = await db.scalar(
        select(func.count(TripParticipant.id)).where(TripParticipant.trip_id == trip.id)
    )

    trip_dict = trip.__dict__.copy()
    trip_dict["participant_count"] = participant_count or 0
    return schemas.TripPublic(**trip_dict)


async def get_trip_route_geometry(
    db: AsyncSession, trip_id: UUID, user_id: UUID
) -> schemas.RouteGeometry | None:
    """Get decoded route geometry for map display."""
    trip = await get_trip_by_id(db, trip_id, user_id)
    if not trip:
        return None

    # Decode polyline to coordinates
    coordinates = polyline.decode(trip.route_geometry)
    return schemas.RouteGeometry(coordinates=coordinates)


async def complete_trip(
    db: AsyncSession, trip_id: UUID, user_id: UUID
) -> schemas.TripPublic | None:
    """Mark trip as completed."""
    query = select(Trip).where(Trip.id == trip_id, Trip.owner_id == user_id)
    result = await db.execute(query)
    trip = result.scalar_one_or_none()

    if not trip:
        return None

    trip.is_active = False
    trip.completed_at = utcnow()
    await db.commit()
    await db.refresh(trip)

    trip_dict = trip.__dict__.copy()
    trip_dict["participant_count"] = 0
    return schemas.TripPublic(**trip_dict)


async def manage_trip_participation(
    db: AsyncSession, trip_id: UUID, user_id: UUID, action: str
) -> schemas.TripPublic | None:
    """Join or leave a trip (buddy system)."""
    # First check if trip exists
    trip_query = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(trip_query)
    trip = result.scalar_one_or_none()

    if not trip:
        return None

    # Check existing participation
    participant_query = select(TripParticipant).where(
        TripParticipant.trip_id == trip_id, TripParticipant.user_id == user_id
    )
    result = await db.execute(participant_query)
    existing_participant = result.scalar_one_or_none()

    if action == "join":
        if not existing_participant:
            participant = TripParticipant(trip_id=trip_id, user_id=user_id)
            db.add(participant)
            await db.commit()
    elif action == "leave":
        if existing_participant:
            await db.delete(existing_participant)
            await db.commit()

    # Return updated trip with participant count
    participant_count = await db.scalar(
        select(func.count(TripParticipant.id)).where(TripParticipant.trip_id == trip_id)
    )

    trip_dict = trip.__dict__.copy()
    trip_dict["participant_count"] = participant_count or 0
    return schemas.TripPublic(**trip_dict)
