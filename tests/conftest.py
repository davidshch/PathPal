"""Shared pytest fixtures for PathPal API tests."""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from pathpal_api.auth.security import get_current_user
from pathpal_api.database.connection import get_db
from pathpal_api.database.models import User
from pathpal_api.main import app

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

# Create test session factory
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function")
async def db_session():
    """Create test database session."""
    async with test_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    # Clean up database after each test
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="function")
def override_get_db(db_session: AsyncSession):
    """Override get_db dependency."""

    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture(scope="function")
def client(override_get_db):
    """Create test client with database override."""
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(override_get_db):
    """Create async HTTP client for testing."""
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Create mock user for testing."""
    return User(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="test@example.com",
        full_name="Test User",
        hashed_password="fake_hash",
        is_active=True,
    )


@pytest.fixture
def authenticated_client(mock_user):
    """Create authenticated test client."""

    def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {"email": "test@example.com", "password": "testpassword123", "full_name": "Test User"}
