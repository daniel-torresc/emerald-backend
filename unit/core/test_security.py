"""
Unit tests for security utilities (password hashing, JWT tokens).

All tests are fully mocked - no database or external dependencies.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jose import JWTError

from src.core import security


class TestPasswordHashing:
    """Test password hashing with Argon2id."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "TestPassword123!"
        hashed = security.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2id$")

    def test_hash_password_different_for_same_password(self):
        """Test that hashing the same password twice produces different hashes (due to salt)."""
        password = "TestPassword123!"
        hash1 = security.hash_password(password)
        hash2 = security.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct_password(self):
        """Test that verify_password returns True for correct password."""
        password = "TestPassword123!"
        hashed = security.hash_password(password)

        assert security.verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test that verify_password returns False for incorrect password."""
        password = "TestPassword123!"
        hashed = security.hash_password(password)

        assert security.verify_password("WrongPassword123!", hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test that verify_password returns False for invalid hash."""
        assert security.verify_password("password", "invalid_hash") is False

    def test_verify_password_handles_verify_mismatch_error(self):
        """Test that verify_password returns False for password mismatch."""
        # Create a real hash
        hashed = security.hash_password("correct_password")

        # Try to verify with wrong password (triggers VerifyMismatchError internally)
        assert security.verify_password("wrong_password", hashed) is False

    def test_verify_password_handles_invalid_hash_error(self):
        """Test that verify_password returns False for malformed hash."""
        # Use a completely invalid hash (triggers InvalidHashError internally)
        assert security.verify_password("password", "not_a_valid_argon2_hash") is False


class TestPasswordStrengthValidation:
    """Test password strength validation."""

    def test_validate_strong_password(self):
        """Test that a strong password passes validation."""
        is_valid, error = security.validate_password_strength("StrongP@ss123")

        assert is_valid is True
        assert error is None

    def test_validate_too_short_password(self):
        """Test that a password < 8 characters fails."""
        is_valid, error = security.validate_password_strength("Short1!")

        assert is_valid is False
        assert error == "Password must be at least 8 characters long"

    def test_validate_no_uppercase(self):
        """Test that a password without uppercase fails."""
        is_valid, error = security.validate_password_strength("weakp@ss123")

        assert is_valid is False
        assert error == "Password must contain at least one uppercase letter"

    def test_validate_no_lowercase(self):
        """Test that a password without lowercase fails."""
        is_valid, error = security.validate_password_strength("WEAKP@SS123")

        assert is_valid is False
        assert error == "Password must contain at least one lowercase letter"

    def test_validate_no_digit(self):
        """Test that a password without a digit fails."""
        is_valid, error = security.validate_password_strength("WeakPassword!")

        assert is_valid is False
        assert error == "Password must contain at least one digit"

    def test_validate_no_special_character(self):
        """Test that a password without special characters fails."""
        is_valid, error = security.validate_password_strength("WeakPassword123")

        assert is_valid is False
        assert error == "Password must contain at least one special character"

    def test_validate_all_special_characters_allowed(self):
        """Test that all documented special characters are accepted."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        for char in special_chars:
            password = f"Pass123{char}word"
            is_valid, error = security.validate_password_strength(password)
            assert is_valid is True, f"Character '{char}' should be valid"


class TestJWTAccessToken:
    """Test JWT access token creation and validation."""

    def test_create_access_token_structure(self):
        """Test that create_access_token generates correct structure."""
        # Create token
        token = security.create_access_token({"sub": "user_123"})

        # Decode token
        payload = security.decode_token(token)

        assert payload["sub"] == "user_123"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_default_expiration(self):
        """Test that access token uses default expiration from settings."""
        # Create token (uses default 15 minutes from settings)
        before_creation = datetime.now(UTC)
        token = security.create_access_token({"sub": "user_123"})
        after_creation = datetime.now(UTC)

        # Decode token
        payload = security.decode_token(token)

        # Check expiration is approximately 15 minutes from now
        # JWT timestamps are in seconds, so we add 1 second tolerance
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_exp_min = before_creation + timedelta(minutes=15) - timedelta(seconds=1)
        expected_exp_max = after_creation + timedelta(minutes=15) + timedelta(seconds=1)

        assert expected_exp_min <= exp_time <= expected_exp_max

    def test_create_access_token_custom_expiration(self):
        """Test that access token can use custom expiration."""
        # Create token with custom expiration (2 hours)
        custom_delta = timedelta(hours=2)
        before_creation = datetime.now(UTC)
        token = security.create_access_token(
            {"sub": "user_123"},
            expires_delta=custom_delta
        )
        after_creation = datetime.now(UTC)

        # Decode token
        payload = security.decode_token(token)

        # Check expiration is approximately 2 hours from now
        # JWT timestamps are in seconds, so we add 1 second tolerance
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_exp_min = before_creation + custom_delta - timedelta(seconds=1)
        expected_exp_max = after_creation + custom_delta + timedelta(seconds=1)

        assert expected_exp_min <= exp_time <= expected_exp_max

    def test_create_access_token_includes_jti(self):
        """Test that access token includes unique jti (JWT ID)."""
        token1 = security.create_access_token({"sub": "user_123"})
        token2 = security.create_access_token({"sub": "user_123"})

        payload1 = security.decode_token(token1)
        payload2 = security.decode_token(token2)

        # JTI should be different for each token
        assert "jti" in payload1
        assert "jti" in payload2
        assert payload1["jti"] != payload2["jti"]

    def test_create_access_token_preserves_custom_claims(self):
        """Test that custom claims are preserved in token."""
        token = security.create_access_token({
            "sub": "user_123",
            "role": "admin",
            "permissions": ["read", "write"]
        })

        payload = security.decode_token(token)

        assert payload["sub"] == "user_123"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestJWTRefreshToken:
    """Test JWT refresh token creation and validation."""

    def test_create_refresh_token_structure(self):
        """Test that create_refresh_token generates correct structure."""
        # Create token
        token = security.create_refresh_token({"sub": "user_123"})

        # Decode token
        payload = security.decode_token(token)

        assert payload["sub"] == "user_123"
        assert payload["type"] == "refresh"
        assert "jti" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token_default_expiration(self):
        """Test that refresh token uses default expiration from settings."""
        # Create token (uses default 7 days from settings)
        before_creation = datetime.now(UTC)
        token = security.create_refresh_token({"sub": "user_123"})
        after_creation = datetime.now(UTC)

        # Decode token
        payload = security.decode_token(token)

        # Check expiration is approximately 7 days from now
        # JWT timestamps are in seconds, so we add 1 second tolerance
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_exp_min = before_creation + timedelta(days=7) - timedelta(seconds=1)
        expected_exp_max = after_creation + timedelta(days=7) + timedelta(seconds=1)

        assert expected_exp_min <= exp_time <= expected_exp_max

    def test_create_refresh_token_includes_jti(self):
        """Test that refresh token includes unique jti (JWT ID)."""
        token1 = security.create_refresh_token({"sub": "user_123"})
        token2 = security.create_refresh_token({"sub": "user_123"})

        payload1 = security.decode_token(token1)
        payload2 = security.decode_token(token2)

        # JTI should be different for each token
        assert "jti" in payload1
        assert "jti" in payload2
        assert payload1["jti"] != payload2["jti"]


class TestDecodeToken:
    """Test JWT token decoding and validation."""

    def test_decode_valid_token(self):
        """Test that decode_token successfully decodes valid token."""
        token = security.create_access_token({"sub": "user_123"})
        payload = security.decode_token(token)

        assert payload["sub"] == "user_123"
        assert payload["type"] == "access"

    @patch("src.core.security.jwt.decode")
    def test_decode_invalid_token_raises_error(self, mock_decode):
        """Test that decode_token raises JWTError for invalid token."""
        mock_decode.side_effect = JWTError("Invalid token")

        with pytest.raises(JWTError):
            security.decode_token("invalid_token")

    @patch("src.core.security.jwt.decode")
    @patch("src.core.security.logger")
    def test_decode_logs_jwt_errors(self, mock_logger, mock_decode):
        """Test that decode_token logs JWTError."""
        mock_decode.side_effect = JWTError("Token expired")

        with pytest.raises(JWTError):
            security.decode_token("expired_token")

        mock_logger.warning.assert_called_once()
        assert "JWT decode error" in str(mock_logger.warning.call_args)


class TestVerifyTokenType:
    """Test token type verification."""

    def test_verify_access_token_type(self):
        """Test that access token type is verified correctly."""
        token_data = {"type": "access"}

        assert security.verify_token_type(token_data, "access") is True
        assert security.verify_token_type(token_data, "refresh") is False

    def test_verify_refresh_token_type(self):
        """Test that refresh token type is verified correctly."""
        token_data = {"type": "refresh"}

        assert security.verify_token_type(token_data, "refresh") is True
        assert security.verify_token_type(token_data, "access") is False

    def test_verify_missing_type_returns_false(self):
        """Test that missing type returns False."""
        token_data = {"sub": "user_123"}

        assert security.verify_token_type(token_data, "access") is False


class TestRefreshTokenHashing:
    """Test refresh token hashing with SHA-256."""

    def test_hash_refresh_token_returns_string(self):
        """Test that hash_refresh_token returns a hex string."""
        token = "test_token_123"
        hashed = security.hash_refresh_token(token)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex digest is 64 characters

    def test_hash_refresh_token_deterministic(self):
        """Test that hashing the same token produces the same hash."""
        token = "test_token_123"
        hash1 = security.hash_refresh_token(token)
        hash2 = security.hash_refresh_token(token)

        assert hash1 == hash2

    def test_hash_different_tokens_produce_different_hashes(self):
        """Test that different tokens produce different hashes."""
        token1 = "test_token_123"
        token2 = "test_token_456"

        hash1 = security.hash_refresh_token(token1)
        hash2 = security.hash_refresh_token(token2)

        assert hash1 != hash2

    def test_verify_refresh_token_hash_correct_token(self):
        """Test that verify_refresh_token_hash returns True for correct token."""
        token = "test_token_123"
        token_hash = security.hash_refresh_token(token)

        assert security.verify_refresh_token_hash(token, token_hash) is True

    def test_verify_refresh_token_hash_incorrect_token(self):
        """Test that verify_refresh_token_hash returns False for incorrect token."""
        token = "test_token_123"
        wrong_token = "wrong_token_456"
        token_hash = security.hash_refresh_token(token)

        assert security.verify_refresh_token_hash(wrong_token, token_hash) is False


class TestTokenUniqueness:
    """Test that tokens are unique even when created simultaneously."""

    def test_access_tokens_created_simultaneously_are_unique(self):
        """Test that access tokens created at the same time have unique hashes."""
        # Create multiple tokens for the same user at the same time
        tokens = [
            security.create_access_token({"sub": "user_123"})
            for _ in range(10)
        ]

        # Hash each token
        hashes = [security.hash_refresh_token(token) for token in tokens]

        # All hashes should be unique (due to jti)
        assert len(set(hashes)) == 10

    def test_refresh_tokens_created_simultaneously_are_unique(self):
        """Test that refresh tokens created at the same time have unique hashes."""
        # Create multiple tokens for the same user at the same time
        tokens = [
            security.create_refresh_token({"sub": "user_123"})
            for _ in range(10)
        ]

        # Hash each token
        hashes = [security.hash_refresh_token(token) for token in tokens]

        # All hashes should be unique (due to jti)
        assert len(set(hashes)) == 10
