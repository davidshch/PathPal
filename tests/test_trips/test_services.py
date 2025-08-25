"""Unit tests for trip services."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from pathpal_api.database.models import TravelMode, Trip, utcnow
from pathpal_api.features.trips import models as schemas
from pathpal_api.features.trips import services
from pathpal_api.features.trips.exceptions import GeocodeError


@pytest.mark.asyncio
async def test_create_trip_with_route_success():
    """Test successful trip creation with route calculation."""
    # Mock dependencies
    mock_db = AsyncMock()
    mock_mapbox_client = AsyncMock()
    user_id = uuid4()

    # Mock geocoding response
    with patch("pathpal_api.features.trips.services.geocode_destination") as mock_geocode:
        mock_geocode.return_value = (40.748, -73.985)  # lat, lon

        # Mock route calculation
        mock_route_data = {"geometry": "sample_encoded_polyline", "distance": 1200, "duration": 900}
        mock_mapbox_client.get_directions.return_value = mock_route_data

        # Mock database operations
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create trip request
        trip_request = schemas.TripCreate(
            destination_name="Central Park",
            start_location=schemas.Location(latitude=40.733, longitude=-73.989),
            travel_mode=schemas.TravelMode.WALKING,
        )

        result = await services.create_trip_with_route(
            db=mock_db, trip_create=trip_request, user_id=user_id, mapbox_client=mock_mapbox_client
        )

        # Verify the result
        assert isinstance(result, schemas.TripPublic)
        assert result.destination_name == "Central Park"
        assert result.owner_id == user_id
        assert result.distance_meters == 1200
        assert result.duration_seconds == 900
        assert result.travel_mode == schemas.TravelMode.WALKING

        # Verify geocoding was called
        mock_geocode.assert_called_once_with(mock_mapbox_client, "Central Park")

        # Verify route calculation was called with correct coordinates
        mock_mapbox_client.get_directions.assert_called_once()
        call_args = mock_mapbox_client.get_directions.call_args
        coordinates = call_args[1]["coordinates"]
        assert coordinates == [(-73.989, 40.733), (-73.985, 40.748)]  # lon, lat format


@pytest.mark.asyncio
async def test_create_trip_with_provided_coordinates():
    """Test trip creation with explicitly provided destination coordinates."""
    mock_db = AsyncMock()
    mock_mapbox_client = AsyncMock()
    user_id = uuid4()

    # Mock route calculation
    mock_route_data = {"geometry": "sample_encoded_polyline", "distance": 800, "duration": 600}
    mock_mapbox_client.get_directions.return_value = mock_route_data

    # Mock database operations
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Create trip request with explicit coordinates
    trip_request = schemas.TripCreate(
        destination_name="Custom Location",
        destination_location=schemas.Location(latitude=40.750, longitude=-73.980),
        start_location=schemas.Location(latitude=40.733, longitude=-73.989),
        travel_mode=schemas.TravelMode.CYCLING,
    )

    with patch("pathpal_api.features.trips.services.geocode_destination") as mock_geocode:
        await services.create_trip_with_route(
            db=mock_db, trip_create=trip_request, user_id=user_id, mapbox_client=mock_mapbox_client
        )

        # Verify geocoding was NOT called
        mock_geocode.assert_not_called()

        # Verify route calculation used provided coordinates
        mock_mapbox_client.get_directions.assert_called_once()
        call_args = mock_mapbox_client.get_directions.call_args
        coordinates = call_args[1]["coordinates"]
        assert coordinates == [(-73.989, 40.733), (-73.980, 40.750)]


@pytest.mark.asyncio
async def test_create_trip_geocoding_failure():
    """Test trip creation when geocoding fails."""
    mock_db = AsyncMock()
    mock_mapbox_client = AsyncMock()
    user_id = uuid4()

    # Mock geocoding failure
    with patch("pathpal_api.features.trips.services.geocode_destination") as mock_geocode:
        mock_geocode.side_effect = GeocodeError("Location not found")

        trip_request = schemas.TripCreate(
            destination_name="Nonexistent Place",
            start_location=schemas.Location(latitude=40.733, longitude=-73.989),
            travel_mode=schemas.TravelMode.WALKING,
        )

        with pytest.raises(GeocodeError, match="Location not found"):
            await services.create_trip_with_route(
                db=mock_db,
                trip_create=trip_request,
                user_id=user_id,
                mapbox_client=mock_mapbox_client,
            )


@pytest.mark.asyncio
async def test_get_user_trips_pagination():
    """Test paginated trip listing."""
    mock_db = AsyncMock()
    user_id = uuid4()

    # Mock database query results
    mock_trips = [
        Trip(
            id=uuid4(),
            owner_id=user_id,
            destination_name="Trip 1",
            start_latitude=40.733,
            start_longitude=-73.989,
            destination_latitude=40.748,
            destination_longitude=-73.985,
            route_geometry="encoded_polyline",
            distance_meters=1200,
            duration_seconds=900,
            travel_mode=TravelMode.WALKING,
            is_active=True,
            created_at=utcnow(),
        )
    ]

    # Mock database operations
    from unittest.mock import Mock

    mock_scalars = Mock()  # scalars() result should be synchronous
    mock_scalars.all.return_value = mock_trips
    mock_execute_result = Mock()  # Make execute result synchronous too
    mock_execute_result.scalars.return_value = mock_scalars
    mock_db.scalar = AsyncMock(side_effect=[10, 0])  # Total count, then participant count
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    result = await services.get_user_trips(
        db=mock_db, user_id=user_id, page=1, page_size=20, active_only=False
    )

    assert isinstance(result, schemas.TripList)
    assert result.total == 10
    assert result.page == 1
    assert result.page_size == 20
    assert len(result.trips) == 1
    assert result.trips[0].destination_name == "Trip 1"


@pytest.mark.asyncio
async def test_complete_trip_success():
    """Test successful trip completion."""
    mock_db = AsyncMock()
    user_id = uuid4()
    trip_id = uuid4()

    # Mock trip
    mock_trip = Trip(
        id=trip_id,
        owner_id=user_id,
        destination_name="Test Trip",
        start_latitude=40.733,
        start_longitude=-73.989,
        destination_latitude=40.748,
        destination_longitude=-73.985,
        route_geometry="encoded_polyline",
        distance_meters=1200,
        duration_seconds=900,
        travel_mode=TravelMode.WALKING,
        is_active=True,
        created_at=utcnow(),
    )

    # Mock database operations
    from unittest.mock import Mock

    mock_execute_result = Mock()
    mock_execute_result.scalar_one_or_none.return_value = mock_trip
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await services.complete_trip(db=mock_db, trip_id=trip_id, user_id=user_id)

    assert isinstance(result, schemas.TripPublic)
    assert result.id == trip_id
    assert not result.is_active  # Should be marked as inactive
    assert result.completed_at is not None


@pytest.mark.asyncio
async def test_complete_trip_not_found():
    """Test trip completion when trip not found."""
    mock_db = AsyncMock()
    user_id = uuid4()
    trip_id = uuid4()

    # Mock no trip found
    from unittest.mock import Mock

    mock_execute_result = Mock()
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    result = await services.complete_trip(db=mock_db, trip_id=trip_id, user_id=user_id)

    assert result is None
