"""FastAPI routes for trip and route planning endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from ...auth.schemas import UserPublic
from ...auth.security import get_current_user
from ...database.connection import get_db
from . import models as schemas
from . import services
from .exceptions import GeocodeError, MapboxAPIError, RouteCalculationError
from .external_apis.mapbox_client import MapboxClient

router = APIRouter(prefix="/trips", tags=["Trips"])


def get_mapbox_client(request: Request) -> MapboxClient:
    """Dependency to get Mapbox client."""
    return MapboxClient(request.app.state.http_client)


@router.post("/", response_model=schemas.TripPublic, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_in: schemas.TripCreate,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    mapbox_client: MapboxClient = Depends(get_mapbox_client),
) -> schemas.TripPublic:
    """Create a new trip with route calculation."""
    try:
        trip = await services.create_trip_with_route(
            db=db, trip_create=trip_in, user_id=current_user.id, mapbox_client=mapbox_client
        )
        return trip
    except GeocodeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RouteCalculationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except MapboxAPIError as e:
        raise HTTPException(status_code=503, detail=f"External API error: {str(e)}") from e


@router.get("/", response_model=schemas.TripList)
async def list_trips(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
) -> schemas.TripList:
    """List user's trips with pagination."""
    trips = await services.get_user_trips(
        db=db, user_id=current_user.id, page=page, page_size=page_size, active_only=active_only
    )
    return trips


@router.get("/{trip_id}", response_model=schemas.TripPublic)
async def get_trip(
    trip_id: UUID,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.TripPublic:
    """Get specific trip details."""
    trip = await services.get_trip_by_id(db=db, trip_id=trip_id, user_id=current_user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.post("/{trip_id}/participants", response_model=schemas.TripPublic)
async def manage_trip_participant(
    trip_id: UUID,
    participant_request: schemas.TripParticipantRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.TripPublic:
    """Join or leave a trip (buddy system)."""
    trip = await services.manage_trip_participation(
        db=db, trip_id=trip_id, user_id=current_user.id, action=participant_request.action
    )
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.put("/{trip_id}/complete", response_model=schemas.TripPublic)
async def complete_trip(
    trip_id: UUID,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.TripPublic:
    """Mark trip as completed."""
    trip = await services.complete_trip(db=db, trip_id=trip_id, user_id=current_user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or not owned by user")
    return trip


@router.get("/{trip_id}/route/geometry", response_model=schemas.RouteGeometry)
async def get_route_geometry(
    trip_id: UUID,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.RouteGeometry:
    """Get decoded route geometry for map display."""
    geometry = await services.get_trip_route_geometry(
        db=db, trip_id=trip_id, user_id=current_user.id
    )
    if not geometry:
        raise HTTPException(status_code=404, detail="Trip not found")
    return geometry
