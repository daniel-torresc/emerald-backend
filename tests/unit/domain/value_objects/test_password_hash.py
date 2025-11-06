"""Unit tests for PasswordHash value object."""

import pytest

from app.domain.exceptions import InvalidPasswordError
from app.domain.value_objects.password_hash import PasswordHash


class TestPasswordHashCreation:
    """Test PasswordHash creation."""

    def test_create_valid_password_hash(self):
        """Test creating password hash with valid value."""
        hash_value = "$2b$12$" + "x" * 50  # Simulated bcrypt hash
        password_hash = PasswordHash(hash_value)
        assert password_hash.value == hash_value

    def test_empty_hash_raises_error(self):
        """Test empty hash raises error."""
        with pytest.raises(InvalidPasswordError):
            PasswordHash("")

    def test_too_short_hash_raises_error(self):
        """Test hash that's too short raises error."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            PasswordHash("short")
        assert "too short" in str(exc_info.value)

    def test_hash_with_whitespace_raises_error(self):
        """Test hash with whitespace raises error."""
        with pytest.raises(InvalidPasswordError):
            PasswordHash("hash value with spaces")

    def test_hash_with_newline_raises_error(self):
        """Test hash with newline raises error."""
        with pytest.raises(InvalidPasswordError):
            PasswordHash("hash\nwith\nnewline")


class TestPasswordHashSecurity:
    """Test PasswordHash security features."""

    def test_str_redacts_hash(self):
        """Test __str__ never exposes the hash."""
        password_hash = PasswordHash("$2b$12$" + "x" * 50)
        assert str(password_hash) == "***REDACTED***"

    def test_repr_redacts_hash(self):
        """Test __repr__ never exposes the hash."""
        password_hash = PasswordHash("$2b$12$" + "x" * 50)
        assert "REDACTED" in repr(password_hash)
        assert "$2b$12$" not in repr(password_hash)


class TestPasswordHashEquality:
    """Test PasswordHash equality."""

    def test_equal_hashes_are_equal(self):
        """Test hashes with same value are equal."""
        hash1 = PasswordHash("$2b$12$" + "x" * 50)
        hash2 = PasswordHash("$2b$12$" + "x" * 50)
        assert hash1 == hash2

    def test_different_hashes_not_equal(self):
        """Test hashes with different values are not equal."""
        hash1 = PasswordHash("$2b$12$" + "x" * 50)
        hash2 = PasswordHash("$2b$12$" + "y" * 50)
        assert hash1 != hash2

    def test_matches_raw_value(self):
        """Test matches_raw_value method."""
        hash_value = "$2b$12$" + "x" * 50
        password_hash = PasswordHash(hash_value)
        assert password_hash.matches_raw_value(hash_value) is True
        assert password_hash.matches_raw_value("different") is False


class TestPasswordHashImmutability:
    """Test PasswordHash is immutable."""

    def test_cannot_change_value(self):
        """Test hash value cannot be changed."""
        password_hash = PasswordHash("$2b$12$" + "x" * 50)
        with pytest.raises(AttributeError):
            password_hash.value = "new_hash"  # type: ignore
