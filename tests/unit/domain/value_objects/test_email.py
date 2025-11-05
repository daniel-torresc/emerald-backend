"""Unit tests for Email value object."""

import pytest

from app.domain.exceptions import InvalidEmailError
from app.domain.value_objects.email import Email


class TestEmailCreation:
    """Test Email value object creation."""

    def test_create_valid_email(self):
        """Test creating email with valid address."""
        email = Email("test@example.com")
        assert email.value == "test@example.com"

    def test_email_normalized_to_lowercase(self):
        """Test email is normalized to lowercase."""
        email = Email("Test@Example.COM")
        assert email.value == "test@example.com"

    def test_email_strips_whitespace(self):
        """Test email strips leading/trailing whitespace."""
        email = Email("  test@example.com  ")
        assert email.value == "test@example.com"

    def test_create_email_with_subdomain(self):
        """Test creating email with subdomain."""
        email = Email("user@mail.example.com")
        assert email.value == "user@mail.example.com"

    def test_create_email_with_plus_sign(self):
        """Test creating email with plus sign."""
        email = Email("user+tag@example.com")
        assert email.value == "user+tag@example.com"

    def test_create_email_with_dots(self):
        """Test creating email with dots in local part."""
        email = Email("first.last@example.com")
        assert email.value == "first.last@example.com"


class TestEmailValidation:
    """Test Email validation."""

    def test_empty_email_raises_error(self):
        """Test empty email raises InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("")

    def test_email_without_at_raises_error(self):
        """Test email without @ raises error."""
        with pytest.raises(InvalidEmailError):
            Email("testexample.com")

    def test_email_without_domain_raises_error(self):
        """Test email without domain raises error."""
        with pytest.raises(InvalidEmailError):
            Email("test@")

    def test_email_without_local_part_raises_error(self):
        """Test email without local part raises error."""
        with pytest.raises(InvalidEmailError):
            Email("@example.com")

    def test_email_without_tld_raises_error(self):
        """Test email without TLD raises error."""
        with pytest.raises(InvalidEmailError):
            Email("test@example")

    def test_email_with_spaces_raises_error(self):
        """Test email with spaces raises error."""
        with pytest.raises(InvalidEmailError):
            Email("test user@example.com")

    def test_email_with_invalid_characters_raises_error(self):
        """Test email with invalid characters raises error."""
        with pytest.raises(InvalidEmailError):
            Email("test@exa mple.com")


class TestEmailProperties:
    """Test Email properties."""

    def test_domain_property(self):
        """Test domain property extraction."""
        email = Email("user@example.com")
        assert email.domain == "example.com"

    def test_local_part_property(self):
        """Test local_part property extraction."""
        email = Email("user@example.com")
        assert email.local_part == "user"

    def test_domain_with_subdomain(self):
        """Test domain property with subdomain."""
        email = Email("user@mail.example.com")
        assert email.domain == "mail.example.com"


class TestEmailEquality:
    """Test Email equality and hashing."""

    def test_equal_emails_are_equal(self):
        """Test two emails with same value are equal."""
        email1 = Email("test@example.com")
        email2 = Email("test@example.com")
        assert email1 == email2

    def test_emails_with_different_case_are_equal(self):
        """Test emails are case-insensitive."""
        email1 = Email("Test@Example.com")
        email2 = Email("test@example.com")
        assert email1 == email2

    def test_different_emails_are_not_equal(self):
        """Test emails with different values are not equal."""
        email1 = Email("test1@example.com")
        email2 = Email("test2@example.com")
        assert email1 != email2

    def test_email_not_equal_to_string(self):
        """Test email is not equal to string."""
        email = Email("test@example.com")
        assert email != "test@example.com"

    def test_email_hash(self):
        """Test email can be hashed."""
        email = Email("test@example.com")
        hash_value = hash(email)
        assert isinstance(hash_value, int)

    def test_emails_can_be_used_in_set(self):
        """Test emails can be used in sets."""
        email1 = Email("test@example.com")
        email2 = Email("test@example.com")
        email3 = Email("other@example.com")
        email_set = {email1, email2, email3}
        assert len(email_set) == 2  # email1 and email2 are same


class TestEmailStringRepresentation:
    """Test Email string representation."""

    def test_str_returns_value(self):
        """Test __str__ returns email value."""
        email = Email("test@example.com")
        assert str(email) == "test@example.com"

    def test_repr_shows_class_and_value(self):
        """Test __repr__ shows class name and value."""
        email = Email("test@example.com")
        assert repr(email) == "Email(value='test@example.com')"


class TestEmailImmutability:
    """Test Email is immutable."""

    def test_cannot_change_value(self):
        """Test email value cannot be changed after creation."""
        email = Email("test@example.com")
        with pytest.raises(AttributeError):
            email.value = "other@example.com"  # type: ignore
