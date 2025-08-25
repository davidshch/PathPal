"""Integration tests for trip API handlers."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from pathpal_api.auth.schemas import UserPublic
from pathpal_api.auth.security import get_current_user
from pathpal_api.features.trips import models as schemas
from pathpal_api.features.trips.exceptions import GeocodeError, RouteCalculationError
from pathpal_api.main import app


@pytest.fixture(autouse=True)
def setup_http_client():
    """Setup HTTP client for all tests."""
    from unittest.mock import AsyncMock

    mock_http_client = AsyncMock()
    app.state.http_client = mock_http_client
    yield
    if hasattr(app.state, "http_client"):
        delattr(app.state, "http_client")


@pytest.fixture
def mock_authentication():
    """Mock authentication for trip handler tests."""

    mock_user = UserPublic(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        created_at="2024-01-01T12:00:00",
    )

    def mock_get_current_user_func():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_func
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_trip_success(async_client: AsyncClient, mock_authentication):
    """Test successful trip creation."""
    trip_data = {
        "destination_name": "Central Park",
        "start_location": {"latitude": 40.733, "longitude": -73.989},
        "travel_mode": "walking",
    }

    # Mock the service call
    with patch("pathpal_api.features.trips.services.create_trip_with_route") as mock_create:
        mock_trip = schemas.TripPublic(
            id=uuid4(),
            owner_id=uuid4(),
            destination_name="Central Park",
            start_latitude=40.733,
            start_longitude=-73.989,
            destination_latitude=40.748,
            destination_longitude=-73.985,
            route_geometry="encoded_polyline",
            distance_meters=1200,
            duration_seconds=900,
            travel_mode=schemas.TravelMode.WALKING,
            is_active=True,
            created_at="2024-01-01T12:00:00",
            participant_count=0,
        )
        mock_create.return_value = mock_trip

        response = await async_client.post("/trips/", json=trip_data)

        assert response.status_code == 201
        data = response.json()
        assert data["destination_name"] == "Central Park"
        assert data["distance_meters"] == 1200
        assert data["travel_mode"] == "walking"


@pytest.mark.asyncio
async def test_create_trip_geocoding_error(async_client: AsyncClient):
    """Test trip creation with geocoding failure."""
    trip_data = {
        "destination_name": "NonexistentPlace12345",
        "start_location": {"latitude": 40.733, "longitude": -73.989},
        "travel_mode": "walking",
    }

    with patch("pathpal_api.features.trips.services.create_trip_with_route") as mock_create:
        mock_create.side_effect = GeocodeError("Could not find location")

        response = await async_client.post("/trips/", json=trip_data)

        assert response.status_code == 400
        assert "Could not find location" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_trip_route_calculation_error(async_client: AsyncClient):
    """Test trip creation with route calculation failure."""
    trip_data = {
        "destination_name": "Unreachable Location",
        "start_location": {"latitude": 40.733, "longitude": -73.989},
        "travel_mode": "walking",
    }

    with patch("pathpal_api.features.trips.services.create_trip_with_route") as mock_create:
        mock_create.side_effect = RouteCalculationError("No routes found")

        response = await async_client.post("/trips/", json=trip_data)

        assert response.status_code == 422
        assert "No routes found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_trip_unauthorized(async_client: AsyncClient):
    """Test trip creation without authentication."""
    trip_data = {
        "destination_name": "Central Park",
        "start_location": {"latitude": 40.733, "longitude": -73.989},
        "travel_mode": "walking",
    }

    response = await async_client.post("/trips/", json=trip_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_trips_success(async_client: AsyncClient):
    """Test successful trip listing."""
    with patch("pathpal_api.features.trips.services.get_user_trips") as mock_get_trips:
        mock_trip_list = schemas.TripList(
            trips=[
                schemas.TripPublic(
                    id=uuid4(),
                    owner_id=uuid4(),
                    destination_name="Trip 1",
                    start_latitude=40.733,
                    start_longitude=-73.989,
                    destination_latitude=40.748,
                    destination_longitude=-73.985,
                    route_geometry="encoded_polyline",
                    distance_meters=1200,
                    duration_seconds=900,
                    travel_mode=schemas.TravelMode.WALKING,
                    is_active=True,
                    created_at="2024-01-01T12:00:00",
                    participant_count=2,
                )
            ],
            total=1,
            page=1,
            page_size=20,
        )
        mock_get_trips.return_value = mock_trip_list

        response = await async_client.get("/trips/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["trips"]) == 1
        assert data["trips"][0]["destination_name"] == "Trip 1"
        assert data["trips"][0]["participant_count"] == 2


@pytest.mark.asyncio
async def test_list_trips_with_pagination(async_client: AsyncClient):
    """Test trip listing with pagination parameters."""
    with patch("pathpal_api.features.trips.services.get_user_trips") as mock_get_trips:
        mock_trip_list = schemas.TripList(trips=[], total=0, page=2, page_size=10)
        mock_get_trips.return_value = mock_trip_list

        response = await async_client.get(
            "/trips/?page=2&page_size=10&active_only=true",
        )

        assert response.status_code == 200
        # Verify the service was called with correct parameters
        mock_get_trips.assert_called_once()
        call_args = mock_get_trips.call_args[1]
        assert call_args["page"] == 2
        assert call_args["page_size"] == 10
        assert call_args["active_only"]


@pytest.mark.asyncio
async def test_get_trip_success(async_client: AsyncClient):
    """Test successful single trip retrieval."""
    trip_id = uuid4()

    with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
        mock_trip = schemas.TripPublic(
            id=trip_id,
            owner_id=uuid4(),
            destination_name="Test Trip",
            start_latitude=40.733,
            start_longitude=-73.989,
            destination_latitude=40.748,
            destination_longitude=-73.985,
            route_geometry="encoded_polyline",
            distance_meters=1200,
            duration_seconds=900,
            travel_mode=schemas.TravelMode.WALKING,
            is_active=True,
            created_at="2024-01-01T12:00:00",
            participant_count=0,
        )
        mock_get_trip.return_value = mock_trip

        response = await async_client.get(f"/trips/{trip_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(trip_id)
        assert data["destination_name"] == "Test Trip"


@pytest.mark.asyncio
async def test_get_trip_not_found(async_client: AsyncClient):
    """Test single trip retrieval when trip not found."""
    trip_id = uuid4()

    with patch("pathpal_api.features.trips.services.get_trip_by_id") as mock_get_trip:
        mock_get_trip.return_value = None

        response = await async_client.get(f"/trips/{trip_id}")

        assert response.status_code == 404
        assert "Trip not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_complete_trip_success(async_client: AsyncClient):
    """Test successful trip completion."""
    trip_id = uuid4()

    with patch("pathpal_api.features.trips.services.complete_trip") as mock_complete:
        mock_trip = schemas.TripPublic(
            id=trip_id,
            owner_id=uuid4(),
            destination_name="Completed Trip",
            start_latitude=40.733,
            start_longitude=-73.989,
            destination_latitude=40.748,
            destination_longitude=-73.985,
            route_geometry="encoded_polyline",
            distance_meters=1200,
            duration_seconds=900,
            travel_mode=schemas.TravelMode.WALKING,
            is_active=False,  # Should be marked inactive
            created_at="2024-01-01T12:00:00",
            completed_at="2024-01-01T13:00:00",
            participant_count=0,
        )
        mock_complete.return_value = mock_trip

        response = await async_client.put(f"/trips/{trip_id}/complete")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(trip_id)
        assert not data["is_active"]
        assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_route_geometry_success(async_client: AsyncClient):
    """Test successful route geometry retrieval."""
    trip_id = uuid4()

    with patch("pathpal_api.features.trips.services.get_trip_route_geometry") as mock_geometry:
        mock_geometry.return_value = schemas.RouteGeometry(
            coordinates=[[40.733, -73.989], [40.748, -73.985]]
        )

        response = await async_client.get(f"/trips/{trip_id}/route/geometry")

        assert response.status_code == 200
        data = response.json()
        assert "coordinates" in data
        assert len(data["coordinates"]) == 2
        assert data["coordinates"][0] == [40.733, -73.989]
