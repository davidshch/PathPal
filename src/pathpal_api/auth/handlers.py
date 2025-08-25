"""FastAPI authentication route handlers."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from . import schemas, security, services

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)
) -> schemas.UserPublic:
    """Register a new user account."""
    # Check if user already exists
    existing_user = await services.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    user = await services.create_user(db, user_create=user_in)

    # Create response without emergency contacts (new user has none)
    return schemas.UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        emergency_contacts=[],
    )


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> schemas.Token:
    """Authenticate user and return JWT access token."""
    user = await services.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token)


@router.get("/me", response_model=schemas.UserPublic)
async def read_users_me(
    current_user: User = Depends(security.get_current_user), db: AsyncSession = Depends(get_db)
) -> schemas.UserPublic:
    """Get current user profile."""
    # Get user with emergency contacts
    user_with_contacts = await services.get_user_by_id(db, str(current_user.id))
    if not user_with_contacts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Convert emergency contacts to email list
    emergency_emails = [contact.contact_email for contact in user_with_contacts.emergency_contacts]

    # Create response with emergency contacts
    return schemas.UserPublic(
        id=user_with_contacts.id,
        email=user_with_contacts.email,
        full_name=user_with_contacts.full_name,
        is_active=user_with_contacts.is_active,
        created_at=user_with_contacts.created_at,
        emergency_contacts=emergency_emails,
    )


@router.post("/me/emergency-contacts", response_model=schemas.UserPublic)
async def add_emergency_contact(
    contact_request: schemas.EmergencyContactRequest,
    current_user: User = Depends(security.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.UserPublic:
    """Add emergency contact for current user."""
    updated_user = await services.add_emergency_contact(
        db, user_id=str(current_user.id), contact_email=contact_request.contact_email
    )

    # Convert emergency contacts to email list
    emergency_emails = [contact.contact_email for contact in updated_user.emergency_contacts]

    # Create response with emergency contacts
    return schemas.UserPublic(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        emergency_contacts=emergency_emails,
    )


@router.delete("/me/emergency-contacts/{contact_email}")
async def remove_emergency_contact(
    contact_email: str,
    current_user: User = Depends(security.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.UserPublic:
    """Remove emergency contact for current user."""
    updated_user = await services.remove_emergency_contact(
        db, user_id=str(current_user.id), contact_email=contact_email
    )

    # Convert emergency contacts to email list
    emergency_emails = [contact.contact_email for contact in updated_user.emergency_contacts]

    # Create response with emergency contacts
    return schemas.UserPublic(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        emergency_contacts=emergency_emails,
    )
