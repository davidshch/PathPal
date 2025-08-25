"""Test fixtures for trip functionality."""

from unittest.mock import AsyncMock

import httpx
import pytest

from pathpal_api.features.trips.external_apis.mapbox_client import MapboxClient


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient for testing."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mapbox_client(mock_http_client):
    """MapboxClient with mocked HTTP client."""
    return MapboxClient(mock_http_client)


@pytest.fixture
def sample_mapbox_route():
    """Sample Mapbox API route response."""
    return {
        "geometry": "sample_polyline_string",
        "distance": 1200.5,
        "duration": 900.0,
        "weight_name": "routability",
        "weight": 900.0,
    }


@pytest.fixture
def sample_geocoding_response():
    """Sample Mapbox geocoding API response."""
    return [
        {
            "geometry": {
                "coordinates": [-73.989, 40.733]  # [lon, lat]
            },
            "place_name": "Central Park, New York, NY",
            "properties": {},
        }
    ]
