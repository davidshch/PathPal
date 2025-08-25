"""Integration tests for emergency alert API endpoints."""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from pathpal_api.auth.security import get_current_user
from pathpal_api.database.models import Alert, EmergencyContact, User
from pathpal_api.main import app


@pytest.fixture
def sample_audio_content():
    """Sample audio file content for testing."""
    return b"fake_wav_audio_data_for_testing"


@pytest.fixture
def mock_authentication():
    """Mock authentication for alert handler tests."""
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    mock_user = User(
        id=user_id,
        email="test@example.com",
        full_name="Test User",
        hashed_password="fake_hash",
        is_active=True,
    )

    def mock_get_current_user_func():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_func
    yield mock_user
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user_with_contacts(db_session):
    """Create mock user with emergency contacts."""
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(
        id=user_id,
        email="test@example.com",
        full_name="Test User",
        hashed_password="fake_hash",
        is_active=True,
    )

    contact1 = EmergencyContact(
        id=UUID("223e4567-e89b-12d3-a456-426614174000"),
        user_id=user_id,
        contact_email="emergency1@example.com",
    )

    contact2 = EmergencyContact(
        id=UUID("323e4567-e89b-12d3-a456-426614174000"),
        user_id=user_id,
        contact_email="emergency2@example.com",
    )

    return user, [contact1, contact2]


@pytest.mark.asyncio
async def test_create_emergency_alert_success(
    async_client: AsyncClient, mock_user_with_contacts, sample_audio_content
):
    """Test successful emergency alert creation."""
    user, contacts = mock_user_with_contacts

    # Override authentication
    def mock_get_current_user():
        return user

    # Mock external dependencies
    with patch("pathpal_api.features.alerts.services.process_emergency_alert") as mock_process:
        with patch("pathpal_api.auth.security.get_current_user", return_value=user):
            # Mock file upload
            files = {"audio_file": ("emergency.wav", sample_audio_content, "audio/wav")}
            form_data = {
                "latitude": 40.7580,
                "longitude": -73.9855,
            }

            response = await async_client.post("/alerts/emergency", files=files, data=form_data)

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "processing"
            assert data["message"] == "Emergency alert received and being processed"
            assert data["user_id"] == str(user.id)
            assert "location" in data
            assert data["location"]["latitude"] == 40.7580
            assert data["location"]["longitude"] == -73.9855


@pytest.mark.asyncio
async def test_create_alert_invalid_audio_format(
    async_client: AsyncClient, mock_user_with_contacts
):
    """Test alert creation with invalid audio format."""
    user, _ = mock_user_with_contacts

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        files = {"audio_file": ("document.pdf", b"fake_pdf_data", "application/pdf")}
        form_data = {"latitude": 40.7580, "longitude": -73.9855}

        response = await async_client.post("/alerts/emergency", files=files, data=form_data)

        assert response.status_code == 400
        assert "Invalid audio file" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_alert_empty_audio_file(async_client: AsyncClient, mock_user_with_contacts):
    """Test alert creation with empty audio file."""
    user, _ = mock_user_with_contacts

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        files = {"audio_file": ("empty.wav", b"", "audio/wav")}
        form_data = {"latitude": 40.7580, "longitude": -73.9855}

        response = await async_client.post("/alerts/emergency", files=files, data=form_data)

        assert response.status_code == 400
        assert "Empty audio file" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_alert_file_too_large(async_client: AsyncClient, mock_user_with_contacts):
    """Test alert creation with audio file exceeding size limit."""
    user, _ = mock_user_with_contacts

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        # Create 26MB fake audio data (exceeds 25MB limit)
        large_audio_data = b"x" * (26 * 1024 * 1024)
        files = {"audio_file": ("large.wav", large_audio_data, "audio/wav")}
        form_data = {"latitude": 40.7580, "longitude": -73.9855}

        response = await async_client.post("/alerts/emergency", files=files, data=form_data)

        assert response.status_code == 413
        assert "too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_alert_invalid_coordinates(
    async_client: AsyncClient, mock_user_with_contacts, sample_audio_content
):
    """Test alert creation with invalid coordinates."""
    user, _ = mock_user_with_contacts

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        files = {"audio_file": ("emergency.wav", sample_audio_content, "audio/wav")}

        # Test invalid latitude
        form_data = {"latitude": 95.0, "longitude": -73.9855}
        response = await async_client.post("/alerts/emergency", files=files, data=form_data)
        assert response.status_code == 422  # Validation error

        # Test invalid longitude
        form_data = {"latitude": 40.7580, "longitude": -185.0}
        response = await async_client.post("/alerts/emergency", files=files, data=form_data)
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_alert_unauthenticated(async_client: AsyncClient, sample_audio_content):
    """Test alert creation without authentication."""
    files = {"audio_file": ("emergency.wav", sample_audio_content, "audio/wav")}
    form_data = {"latitude": 40.7580, "longitude": -73.9855}

    response = await async_client.post("/alerts/emergency", files=files, data=form_data)

    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_get_alert_history_success(
    async_client: AsyncClient, mock_user_with_contacts, db_session
):
    """Test getting user's alert history."""
    user, contacts = mock_user_with_contacts

    # Add some test alerts to database
    alert1 = Alert(
        user_id=user.id,
        latitude=40.7580,
        longitude=-73.9855,
        transcript="Help me!",
        ai_analysis="User needs assistance",
        contacts_notified=2,
        processing_status="success",
    )

    alert2 = Alert(
        user_id=user.id,
        latitude=40.7581,
        longitude=-73.9856,
        transcript="Emergency",
        ai_analysis="Critical situation",
        contacts_notified=2,
        processing_status="fallback",
    )

    db_session.add(alert1)
    db_session.add(alert2)
    await db_session.commit()

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        response = await async_client.get("/alerts/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Check alert data structure
        alert_data = data[0]  # Most recent first
        assert "id" in alert_data
        assert "latitude" in alert_data
        assert "longitude" in alert_data
        assert "transcript" in alert_data
        assert "ai_analysis" in alert_data
        assert "contacts_notified" in alert_data
        assert "processing_status" in alert_data
        assert "created_at" in alert_data


@pytest.mark.asyncio
async def test_get_alert_history_with_limit(
    async_client: AsyncClient, mock_user_with_contacts, db_session
):
    """Test getting user's alert history with limit parameter."""
    user, _ = mock_user_with_contacts

    # Add multiple alerts
    for i in range(5):
        alert = Alert(
            user_id=user.id,
            latitude=40.7580 + i * 0.001,
            longitude=-73.9855 + i * 0.001,
            transcript=f"Alert {i}",
            ai_analysis=f"Analysis {i}",
            contacts_notified=1,
            processing_status="success",
        )
        db_session.add(alert)

    await db_session.commit()

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        response = await async_client.get("/alerts/history?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


@pytest.mark.asyncio
async def test_get_alert_history_empty(async_client: AsyncClient, mock_user_with_contacts):
    """Test getting alert history when user has no alerts."""
    user, _ = mock_user_with_contacts

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        response = await async_client.get("/alerts/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


@pytest.mark.asyncio
async def test_get_alert_history_unauthenticated(async_client: AsyncClient):
    """Test getting alert history without authentication."""
    response = await async_client.get("/alerts/history")

    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_valid_audio_file_types(async_client: AsyncClient, mock_user_with_contacts):
    """Test that various valid audio file types are accepted."""
    user, _ = mock_user_with_contacts

    valid_audio_types = [
        ("test.wav", "audio/wav"),
        ("test.mp3", "audio/mpeg"),
        ("test.mp4", "audio/mp4"),
        ("test.webm", "audio/webm"),
    ]

    with patch("pathpal_api.auth.security.get_current_user", return_value=user):
        with patch("pathpal_api.features.alerts.services.process_emergency_alert"):
            for filename, content_type in valid_audio_types:
                files = {"audio_file": (filename, b"fake_audio_data", content_type)}
                form_data = {"latitude": 40.7580, "longitude": -73.9855}

                response = await async_client.post("/alerts/emergency", files=files, data=form_data)

                assert response.status_code == 202, f"Failed for {content_type}"
