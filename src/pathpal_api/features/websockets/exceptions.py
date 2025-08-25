"""WebSocket-specific exceptions."""


class WebSocketError(Exception):
    """Base exception for WebSocket-related errors."""

    pass


class WebSocketAuthError(WebSocketError):
    """Raised when WebSocket authentication fails."""

    pass


class TripAccessError(WebSocketError):
    """Raised when user tries to access trip they don't have permission for."""

    pass


class ConnectionManagerError(WebSocketError):
    """Raised when connection management operations fail."""

    pass


class MessageProcessingError(WebSocketError):
    """Raised when message processing fails."""

    pass
