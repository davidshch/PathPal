"""Integration tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test root endpoint."""
    response = await async_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "PathPal API is running"


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test health check endpoint."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient, sample_user_data):
    """Test successful user registration."""
    response = await async_client.post("/auth/register", json=sample_user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["full_name"] == sample_user_data["full_name"]
    assert "id" in data
    assert data["is_active"] is True
    assert "created_at" in data
    assert data["emergency_contacts"] == []
    # Password should not be in response
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_user_duplicate_email(async_client: AsyncClient, sample_user_data):
    """Test registration with duplicate email."""
    # Register first user
    response1 = await async_client.post("/auth/register", json=sample_user_data)
    assert response1.status_code == 201

    # Try to register with same email
    response2 = await async_client.post("/auth/register", json=sample_user_data)
    assert response2.status_code == 400
    data = response2.json()
    assert "already registered" in data["detail"]


@pytest.mark.asyncio
async def test_register_user_invalid_email(async_client: AsyncClient):
    """Test registration with invalid email."""
    invalid_user = {
        "email": "not-an-email",
        "password": "testpassword123",
        "full_name": "Test User",
    }

    response = await async_client.post("/auth/register", json=invalid_user)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_user_short_password(async_client: AsyncClient):
    """Test registration with password too short."""
    invalid_user = {
        "email": "test@example.com",
        "password": "short",  # Less than 8 characters
        "full_name": "Test User",
    }

    response = await async_client.post("/auth/register", json=invalid_user)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, sample_user_data):
    """Test successful user login."""
    # Register user first
    await async_client.post("/auth/register", json=sample_user_data)

    # Login
    login_data = {"username": sample_user_data["email"], "password": sample_user_data["password"]}
    response = await async_client.post("/auth/token", data=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, sample_user_data):
    """Test login with wrong password."""
    # Register user first
    await async_client.post("/auth/register", json=sample_user_data)

    # Try login with wrong password
    login_data = {"username": sample_user_data["email"], "password": "wrong_password"}
    response = await async_client.post("/auth/token", data=login_data)

    assert response.status_code == 401
    data = response.json()
    assert "Incorrect username or password" in data["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """Test login with nonexistent user."""
    login_data = {"username": "nonexistent@example.com", "password": "password123"}
    response = await async_client.post("/auth/token", data=login_data)

    assert response.status_code == 401
    data = response.json()
    assert "Incorrect username or password" in data["detail"]


@pytest.mark.asyncio
async def test_get_current_user_authenticated(async_client: AsyncClient, sample_user_data):
    """Test getting current user profile when authenticated."""
    # Register and login
    await async_client.post("/auth/register", json=sample_user_data)

    login_data = {"username": sample_user_data["email"], "password": sample_user_data["password"]}
    login_response = await async_client.post("/auth/token", data=login_data)
    token = login_response.json()["access_token"]

    # Get current user
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["full_name"] == sample_user_data["full_name"]
    assert data["is_active"] is True
    assert data["emergency_contacts"] == []


@pytest.mark.asyncio
async def test_get_current_user_no_token(async_client: AsyncClient):
    """Test getting current user without authentication token."""
    response = await async_client.get("/auth/me")

    assert response.status_code == 401
    data = response.json()
    assert "Not authenticated" in data["detail"]


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(async_client: AsyncClient):
    """Test getting current user with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = await async_client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "Could not validate credentials" in data["detail"]


@pytest.mark.asyncio
async def test_add_emergency_contact(async_client: AsyncClient, sample_user_data):
    """Test adding emergency contact."""
    # Register and login
    await async_client.post("/auth/register", json=sample_user_data)

    login_data = {"username": sample_user_data["email"], "password": sample_user_data["password"]}
    login_response = await async_client.post("/auth/token", data=login_data)
    token = login_response.json()["access_token"]

    # Add emergency contact
    contact_data = {"contact_email": "emergency@example.com"}
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.post(
        "/auth/me/emergency-contacts", json=contact_data, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "emergency@example.com" in data["emergency_contacts"]


@pytest.mark.asyncio
async def test_add_emergency_contact_unauthorized(async_client: AsyncClient):
    """Test adding emergency contact without authentication."""
    contact_data = {"contact_email": "emergency@example.com"}
    response = await async_client.post("/auth/me/emergency-contacts", json=contact_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_remove_emergency_contact(async_client: AsyncClient, sample_user_data):
    """Test removing emergency contact."""
    # Register and login
    await async_client.post("/auth/register", json=sample_user_data)

    login_data = {"username": sample_user_data["email"], "password": sample_user_data["password"]}
    login_response = await async_client.post("/auth/token", data=login_data)
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add emergency contact first
    contact_data = {"contact_email": "emergency@example.com"}
    await async_client.post("/auth/me/emergency-contacts", json=contact_data, headers=headers)

    # Remove emergency contact
    response = await async_client.delete(
        "/auth/me/emergency-contacts/emergency@example.com", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "emergency@example.com" not in data["emergency_contacts"]
