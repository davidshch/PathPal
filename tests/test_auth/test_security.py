"""Unit tests for authentication security functions."""

import pytest
from jose import jwt

from pathpal_api.auth.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from pathpal_api.settings import settings


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password123"
    hashed = get_password_hash(password)

    # Hash should be different from original password
    assert hashed != password
    assert len(hashed) > 0

    # Verification should work
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_password_hashing_same_password():
    """Test that same password produces different hashes (due to salt)."""
    password = "test_password123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Different hashes due to different salts
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_jwt_token_creation():
    """Test JWT token creation and validation."""
    test_data = {"sub": "test_user_id"}
    token = create_access_token(data=test_data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode token to verify contents
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == "test_user_id"
    assert "exp" in decoded


def test_jwt_token_with_custom_expiry():
    """Test JWT token creation with custom expiry."""
    from datetime import timedelta

    test_data = {"sub": "test_user_id"}
    expires_delta = timedelta(minutes=60)
    token = create_access_token(data=test_data, expires_delta=expires_delta)

    assert token is not None
    assert isinstance(token, str)

    # Decode and check expiry
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == "test_user_id"
    assert "exp" in decoded


def test_jwt_token_invalid_secret():
    """Test JWT token validation with wrong secret."""
    test_data = {"sub": "test_user_id"}
    token = create_access_token(data=test_data)

    # Should fail with wrong secret
    with pytest.raises(jwt.JWTError):
        jwt.decode(token, "wrong_secret", algorithms=[settings.JWT_ALGORITHM])


def test_password_edge_cases():
    """Test password hashing edge cases."""
    # Empty password
    empty_hash = get_password_hash("")
    assert verify_password("", empty_hash) is True
    assert verify_password("not_empty", empty_hash) is False

    # Very long password
    long_password = "a" * 1000
    long_hash = get_password_hash(long_password)
    assert verify_password(long_password, long_hash) is True
    assert verify_password("different", long_hash) is False

    # Special characters
    special_password = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    special_hash = get_password_hash(special_password)
    assert verify_password(special_password, special_hash) is True
