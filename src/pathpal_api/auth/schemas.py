"""Pydantic schemas for authentication API requests and responses."""

from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=50)


class UserPublic(BaseModel):
    """Public user information schema."""

    id: UUID4
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    emergency_contacts: list[EmailStr] = []

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token data schema."""

    user_id: str | None = None


class EmergencyContactRequest(BaseModel):
    """Schema for adding emergency contact."""

    contact_email: EmailStr


class EmergencyContactResponse(BaseModel):
    """Schema for emergency contact response."""

    id: UUID4
    contact_email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True
