"""Pydantic models for alert requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Response model for emergency alert creation."""

    message: str = Field(..., description="Status message for the alert")
    status: str = Field(
        ..., description="Processing status: processing, success, fallback, or failed"
    )
    user_id: str = Field(..., description="UUID of the user who triggered the alert")
    location: dict[str, float] = Field(..., description="Location coordinates")


class AlertHistoryResponse(BaseModel):
    """Response model for alert history."""

    id: UUID = Field(..., description="Alert ID")
    latitude: float = Field(..., description="Alert latitude coordinate")
    longitude: float = Field(..., description="Alert longitude coordinate")
    transcript: str = Field(..., description="Audio transcription (may be empty)")
    ai_analysis: str = Field(..., description="AI situation analysis")
    contacts_notified: int = Field(..., description="Number of contacts notified")
    processing_status: str = Field(..., description="Processing status")
    error_details: str | None = Field(default=None, description="Error details if any")
    created_at: datetime = Field(..., description="When alert was created")
    processed_at: datetime | None = Field(default=None, description="When alert was processed")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
