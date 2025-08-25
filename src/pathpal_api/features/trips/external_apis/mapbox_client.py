"""Async client for Mapbox APIs."""

import httpx

from ....settings import get_settings
from ..exceptions import MapboxAPIError, RouteCalculationError

settings = get_settings()


class MapboxClient:
    """Async client for Mapbox APIs."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
        self.api_key = settings.MAPBOX_API_KEY
        self.base_url = "https://api.mapbox.com"

    async def get_directions(
        self, coordinates: list[tuple[float, float]], profile: str = "walking"
    ) -> dict:
        """Get route directions from Mapbox Directions API v5."""
        if len(coordinates) < 2:
            raise RouteCalculationError("Need at least 2 coordinates for directions")

        # Format coordinates as "lon,lat;lon,lat"
        coords_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)

        url = f"{self.base_url}/directions/v5/mapbox/{profile}/{coords_str}"
        params = {
            "access_token": self.api_key,
            "geometries": "polyline",  # Return polyline-encoded geometry
            "overview": "full",
            "steps": "false",  # We don't need turn-by-turn for MVP
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("routes"):
                raise RouteCalculationError("No routes found")

            return data["routes"][0]  # Return first (best) route

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RouteCalculationError("Invalid coordinates or route not possible") from e
            raise MapboxAPIError(f"Mapbox API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise MapboxAPIError(f"Network error calling Mapbox: {str(e)}") from e

    async def geocode_forward(self, query: str, limit: int = 5) -> list[dict]:
        """Forward geocoding: convert place name to coordinates."""
        url = f"{self.base_url}/geocoding/v5/mapbox.places/{query}.json"
        params = {
            "access_token": self.api_key,
            "limit": limit,
            "types": "place,locality,neighborhood,address",
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("features", [])

        except httpx.HTTPStatusError as e:
            raise MapboxAPIError(f"Geocoding API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise MapboxAPIError(f"Network error calling geocoding: {str(e)}") from e
