"""Unit tests for Username value object."""

import pytest

from app.domain.exceptions import InvalidUsernameError
from app.domain.value_objects.username import Username


class TestUsernameCreation:
    """Test Username value object creation."""

    def test_create_valid_username(self):
        """Test creating username with valid value."""
        username = Username("testuser")
        assert username.value == "testuser"

    def test_username_normalized_to_lowercase(self):
        """Test username is normalized to lowercase."""
        username = Username("TestUser")
        assert username.value == "testuser"

    def test_username_strips_whitespace(self):
        """Test username strips whitespace."""
        username = Username("  testuser  ")
        assert username.value == "testuser"

    def test_username_with_numbers(self):
        """Test username with numbers is valid."""
        username = Username("user123")
        assert username.value == "user123"

    def test_username_with_underscore(self):
        """Test username with underscore is valid."""
        username = Username("test_user")
        assert username.value == "test_user"

    def test_username_with_hyphen(self):
        """Test username with hyphen is valid."""
        username = Username("test-user")
        assert username.value == "test-user"


class TestUsernameValidation:
    """Test Username validation."""

    def test_empty_username_raises_error(self):
        """Test empty username raises error."""
        with pytest.raises(InvalidUsernameError):
            Username("")

    def test_username_too_short_raises_error(self):
        """Test username shorter than minimum raises error."""
        with pytest.raises(InvalidUsernameError) as exc_info:
            Username("ab")
        assert "at least 3 characters" in str(exc_info.value)

    def test_username_too_long_raises_error(self):
        """Test username longer than maximum raises error."""
        with pytest.raises(InvalidUsernameError) as exc_info:
            Username("a" * 31)
        assert "at most 30 characters" in str(exc_info.value)

    def test_username_with_spaces_raises_error(self):
        """Test username with spaces raises error."""
        with pytest.raises(InvalidUsernameError) as exc_info:
            Username("test user")
        assert "letters, numbers, hyphens, and underscores" in str(exc_info.value)

    def test_username_with_special_chars_raises_error(self):
        """Test username with special characters raises error."""
        with pytest.raises(InvalidUsernameError):
            Username("test@user")

    def test_username_with_dots_raises_error(self):
        """Test username with dots raises error."""
        with pytest.raises(InvalidUsernameError):
            Username("test.user")

    def test_username_minimum_length_is_valid(self):
        """Test username with minimum length is valid."""
        username = Username("abc")
        assert username.value == "abc"

    def test_username_maximum_length_is_valid(self):
        """Test username with maximum length is valid."""
        username = Username("a" * 30)
        assert len(username.value) == 30


class TestUsernameEquality:
    """Test Username equality and hashing."""

    def test_equal_usernames_are_equal(self):
        """Test usernames with same value are equal."""
        username1 = Username("testuser")
        username2 = Username("testuser")
        assert username1 == username2

    def test_usernames_with_different_case_are_equal(self):
        """Test usernames are case-insensitive."""
        username1 = Username("TestUser")
        username2 = Username("testuser")
        assert username1 == username2

    def test_different_usernames_are_not_equal(self):
        """Test usernames with different values are not equal."""
        username1 = Username("user1")
        username2 = Username("user2")
        assert username1 != username2

    def test_username_not_equal_to_string(self):
        """Test username is not equal to string."""
        username = Username("testuser")
        assert username != "testuser"

    def test_username_hash(self):
        """Test username can be hashed."""
        username = Username("testuser")
        hash_value = hash(username)
        assert isinstance(hash_value, int)

    def test_usernames_can_be_used_in_set(self):
        """Test usernames can be used in sets."""
        username1 = Username("testuser")
        username2 = Username("testuser")
        username3 = Username("otheruser")
        username_set = {username1, username2, username3}
        assert len(username_set) == 2


class TestUsernameStringRepresentation:
    """Test Username string representation."""

    def test_str_returns_value(self):
        """Test __str__ returns username value."""
        username = Username("testuser")
        assert str(username) == "testuser"

    def test_repr_shows_class_and_value(self):
        """Test __repr__ shows class name and value."""
        username = Username("testuser")
        assert repr(username) == "Username(value='testuser')"


class TestUsernameImmutability:
    """Test Username is immutable."""

    def test_cannot_change_value(self):
        """Test username value cannot be changed."""
        username = Username("testuser")
        with pytest.raises(AttributeError):
            username.value = "otheruser"  # type: ignore
