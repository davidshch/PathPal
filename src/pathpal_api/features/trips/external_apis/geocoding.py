"""Geocoding utilities for trip destinations."""

from ..exceptions import GeocodeError
from .mapbox_client import MapboxClient


async def geocode_destination(
    mapbox_client: MapboxClient, destination_name: str
) -> tuple[float, float]:
    """Geocode a destination name to coordinates."""
    features = await mapbox_client.geocode_forward(destination_name, limit=1)

    if not features:
        raise GeocodeError(f"Could not find location for: {destination_name}")

    coordinates = features[0]["geometry"]["coordinates"]  # [lon, lat]
    return coordinates[1], coordinates[0]  # Return as (lat, lon)
