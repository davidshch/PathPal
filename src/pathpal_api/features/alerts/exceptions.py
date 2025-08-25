"""Alert-specific exception classes."""


class AlertProcessingError(Exception):
    """Base exception for alert processing failures."""

    pass


class OpenAIServiceError(Exception):
    """Base exception for OpenAI service failures."""

    pass


class TranscriptionError(OpenAIServiceError):
    """Raised when audio transcription fails."""

    pass


class AnalysisError(OpenAIServiceError):
    """Raised when emergency analysis fails."""

    pass


class EmailNotificationError(Exception):
    """Raised when email notification fails."""

    pass


class AudioValidationError(Exception):
    """Raised when audio file validation fails."""

    pass
