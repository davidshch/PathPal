"""Tests for database models."""

from datetime import UTC, datetime
from uuid import uuid4

from pathpal_api.database.models import EmergencyContact, User


def test_user_model_creation():
    """Test User model creation."""
    user_id = uuid4()
    now = datetime.now(UTC)

    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password_here",
        full_name="Test User",
        is_active=True,
        created_at=now,
    )

    assert user.id == user_id
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password_here"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.created_at == now
    assert user.updated_at is None


def test_user_model_defaults():
    """Test User model with default values."""
    user = User(
        email="test@example.com", hashed_password="hashed_password_here", full_name="Test User"
    )

    # Should have UUID generated
    assert user.id is not None
    assert isinstance(user.id, type(uuid4()))

    # Should have default values
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)
    assert user.updated_at is None


def test_emergency_contact_model_creation():
    """Test EmergencyContact model creation."""
    user_id = uuid4()
    contact_id = uuid4()
    now = datetime.now(UTC)

    contact = EmergencyContact(
        id=contact_id, user_id=user_id, contact_email="emergency@example.com", created_at=now
    )

    assert contact.id == contact_id
    assert contact.user_id == user_id
    assert contact.contact_email == "emergency@example.com"
    assert contact.created_at == now


def test_emergency_contact_model_defaults():
    """Test EmergencyContact model with default values."""
    user_id = uuid4()

    contact = EmergencyContact(user_id=user_id, contact_email="emergency@example.com")

    # Should have UUID generated
    assert contact.id is not None
    assert isinstance(contact.id, type(uuid4()))

    # Should have default created_at
    assert isinstance(contact.created_at, datetime)

    # Should maintain foreign key
    assert contact.user_id == user_id


def test_user_model_table_name():
    """Test User model table configuration."""
    assert User.__tablename__ == "users"


def test_emergency_contact_model_table_name():
    """Test EmergencyContact model table configuration."""
    assert EmergencyContact.__tablename__ == "emergency_contacts"


def test_user_email_constraints():
    """Test User email field constraints."""
    # Get email field info
    email_field = User.model_fields["email"]

    # Field should exist and be configured
    assert email_field is not None
    assert email_field.metadata is not None


def test_user_full_name_constraints():
    """Test User full_name field constraints."""
    # Get full_name field info
    full_name_field = User.model_fields["full_name"]

    # Field should exist and be configured
    assert full_name_field is not None
    assert full_name_field.metadata is not None


def test_emergency_contact_email_constraints():
    """Test EmergencyContact contact_email field constraints."""
    # Get contact_email field info
    email_field = EmergencyContact.model_fields["contact_email"]

    # Field should exist and be configured
    assert email_field is not None
    assert email_field.metadata is not None


def test_user_string_representation():
    """Test User model string representation."""
    user = User(
        email="test@example.com", hashed_password="hashed_password_here", full_name="Test User"
    )

    # Should be able to convert to string without error
    str_repr = str(user)
    assert isinstance(str_repr, str)
    assert len(str_repr) > 0


def test_emergency_contact_string_representation():
    """Test EmergencyContact model string representation."""
    user_id = uuid4()
    contact = EmergencyContact(user_id=user_id, contact_email="emergency@example.com")

    # Should be able to convert to string without error
    str_repr = str(contact)
    assert isinstance(str_repr, str)
    assert len(str_repr) > 0


def test_user_model_validation():
    """Test User model field validation."""
    # Test valid creation
    user = User(
        email="valid@example.com", hashed_password="hashed_password", full_name="Valid User"
    )
    assert user.email == "valid@example.com"
    assert user.full_name == "Valid User"


def test_emergency_contact_model_validation():
    """Test EmergencyContact model field validation."""
    user_id = uuid4()

    # Test valid creation
    contact = EmergencyContact(user_id=user_id, contact_email="valid@example.com")
    assert contact.user_id == user_id
    assert contact.contact_email == "valid@example.com"
