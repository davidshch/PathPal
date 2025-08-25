"""Password hashing and JWT token utilities."""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..settings import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# JWT Configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get user by ID from database."""
    from uuid import UUID

    from sqlalchemy import select

    # Convert string to UUID
    try:
        uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        return None

    statement = select(User).where(User.id == uuid_id)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    user = await get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user


async def authenticate_websocket_token(token: str) -> User:
    """Authenticate JWT token for WebSocket connections."""
    from ..database.connection import async_session
    from ..features.websockets.exceptions import WebSocketAuthError

    if not token:
        raise WebSocketAuthError("Token is required")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise WebSocketAuthError("Invalid token payload")
    except JWTError:
        raise WebSocketAuthError("Invalid token")

    # Get user from database
    async with async_session() as db:
        user = await get_user_by_id(db, user_id=user_id)
        if user is None:
            raise WebSocketAuthError("User not found")

    return user
