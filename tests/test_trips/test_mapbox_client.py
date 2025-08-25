"""Unit tests for Mapbox API client."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from pathpal_api.features.trips.exceptions import MapboxAPIError, RouteCalculationError


@pytest.mark.asyncio
async def test_get_directions_success(mapbox_client, sample_mapbox_route):
    """Test successful route calculation."""
    # Mock HTTP response - json() and raise_for_status() are synchronous in httpx
    mock_response = Mock()
    mock_response.json.return_value = {"routes": [sample_mapbox_route]}
    mock_response.raise_for_status.return_value = None
    mapbox_client.client.get = AsyncMock(return_value=mock_response)

    coordinates = [(-73.989, 40.733), (-73.985, 40.748)]
    result = await mapbox_client.get_directions(coordinates)

    assert result == sample_mapbox_route
    assert result["distance"] == 1200.5
    assert result["geometry"] == "sample_polyline_string"


@pytest.mark.asyncio
async def test_get_directions_no_routes(mapbox_client):
    """Test handling of no routes found."""
    mock_response = Mock()
    mock_response.json.return_value = {"routes": []}
    mock_response.raise_for_status.return_value = None
    mapbox_client.client.get = AsyncMock(return_value=mock_response)

    coordinates = [(-73.989, 40.733), (-73.985, 40.748)]

    with pytest.raises(RouteCalculationError, match="No routes found"):
        await mapbox_client.get_directions(coordinates)


@pytest.mark.asyncio
async def test_get_directions_insufficient_coordinates(mapbox_client):
    """Test error with insufficient coordinates."""
    coordinates = [(-73.989, 40.733)]  # Only one coordinate

    with pytest.raises(RouteCalculationError, match="Need at least 2 coordinates"):
        await mapbox_client.get_directions(coordinates)


@pytest.mark.asyncio
async def test_get_directions_api_error(mapbox_client):
    """Test handling of Mapbox API errors."""
    mock_response = AsyncMock()
    mock_response.status_code = 422
    mapbox_client.client.get.side_effect = httpx.HTTPStatusError(
        "Invalid coordinates", request=None, response=mock_response
    )

    coordinates = [(-73.989, 40.733), (-73.985, 40.748)]

    with pytest.raises(RouteCalculationError, match="Invalid coordinates"):
        await mapbox_client.get_directions(coordinates)


@pytest.mark.asyncio
async def test_get_directions_network_error(mapbox_client):
    """Test handling of network errors."""
    mapbox_client.client.get.side_effect = httpx.RequestError("Network error")

    coordinates = [(-73.989, 40.733), (-73.985, 40.748)]

    with pytest.raises(MapboxAPIError, match="Network error calling Mapbox"):
        await mapbox_client.get_directions(coordinates)


@pytest.mark.asyncio
async def test_geocode_forward_success(mapbox_client, sample_geocoding_response):
    """Test successful geocoding."""
    mock_response = Mock()
    mock_response.json.return_value = {"features": sample_geocoding_response}
    mock_response.raise_for_status.return_value = None
    mapbox_client.client.get = AsyncMock(return_value=mock_response)

    result = await mapbox_client.geocode_forward("Central Park")

    assert result == sample_geocoding_response
    assert len(result) == 1
    assert result[0]["place_name"] == "Central Park, New York, NY"


@pytest.mark.asyncio
async def test_geocode_forward_network_error(mapbox_client):
    """Test geocoding network error handling."""
    mapbox_client.client.get.side_effect = httpx.RequestError("Network error")

    with pytest.raises(MapboxAPIError, match="Network error calling geocoding"):
        await mapbox_client.geocode_forward("Central Park")
