"""Custom exceptions for trip-related operations."""


class TripError(Exception):
    """Base exception for trip-related errors."""

    pass


class MapboxAPIError(TripError):
    """Raised when Mapbox API calls fail."""

    pass


class RouteCalculationError(TripError):
    """Raised when route calculation fails."""

    pass


class GeocodeError(TripError):
    """Raised when geocoding fails."""

    pass


class TripNotFoundError(TripError):
    """Raised when trip is not found."""

    pass


class UnauthorizedTripAccess(TripError):
    """Raised when user tries to access trip they don't own."""

    pass
