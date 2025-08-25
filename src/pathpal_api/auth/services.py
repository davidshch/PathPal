"""Authentication service functions for database operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.models import EmergencyContact, User
from .schemas import UserCreate
from .security import get_password_hash, verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email address."""
    statement = select(User).where(User.email == email)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get user by ID with emergency contacts."""
    from uuid import UUID

    # Convert string to UUID
    try:
        uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        return None

    statement = (
        select(User).where(User.id == uuid_id).options(selectinload(User.emergency_contacts))
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_create.password)

    db_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        is_active=True,
        created_at=datetime.now(UTC),
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate user with email and password."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def add_emergency_contact(db: AsyncSession, user_id: str, contact_email: str) -> User:
    """Add emergency contact for user."""
    from uuid import UUID

    # Convert string to UUID
    try:
        uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError as e:
        raise ValueError("Invalid user ID format") from e

    # Check if contact already exists
    existing_result = await db.execute(
        select(EmergencyContact).where(
            EmergencyContact.user_id == uuid_id, EmergencyContact.contact_email == contact_email
        )
    )
    existing_contact = existing_result.scalar_one_or_none()

    if not existing_contact:
        emergency_contact = EmergencyContact(
            user_id=uuid_id, contact_email=contact_email, created_at=datetime.now(UTC)
        )
        db.add(emergency_contact)
        await db.commit()

    # Return updated user with emergency contacts
    updated_user = await get_user_by_id(db, user_id)
    return updated_user


async def remove_emergency_contact(db: AsyncSession, user_id: str, contact_email: str) -> User:
    """Remove emergency contact for user."""
    from uuid import UUID

    # Convert string to UUID
    try:
        uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError as e:
        raise ValueError("Invalid user ID format") from e

    statement = select(EmergencyContact).where(
        EmergencyContact.user_id == uuid_id, EmergencyContact.contact_email == contact_email
    )
    result = await db.execute(statement)
    contact = result.scalar_one_or_none()

    if contact:
        await db.delete(contact)
        await db.commit()

    # Return updated user with emergency contacts
    updated_user = await get_user_by_id(db, user_id)
    return updated_user
