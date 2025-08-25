"""Custom exceptions for authentication."""


class AuthException(Exception):
    """Base exception for authentication errors."""

    pass


class CredentialsException(AuthException):
    """Raised when credentials cannot be validated."""

    pass


class UserAlreadyExistsException(AuthException):
    """Raised when attempting to create a user that already exists."""

    pass


class UserNotFoundException(AuthException):
    """Raised when a user is not found."""

    pass


class InvalidTokenException(AuthException):
    """Raised when a JWT token is invalid or expired."""

    pass
