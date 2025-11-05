"""Unit tests for UserValidationService domain service."""

import pytest

from app.domain.exceptions import InvalidPasswordError, InvalidUsernameError
from app.domain.services.user_validation_service import UserValidationService
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username


class TestPasswordStrengthValidation:
    """Test password strength validation."""

    def test_valid_password(self):
        """Test valid password passes validation."""
        # Should not raise
        UserValidationService.validate_password_strength("ValidPass123!")

    def test_password_too_short_raises_error(self):
        """Test password shorter than minimum raises error."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            UserValidationService.validate_password_strength("Short1!")
        assert "at least 8 characters" in str(exc_info.value)

    def test_password_too_long_raises_error(self):
        """Test password longer than maximum raises error."""
        with pytest.raises(InvalidPasswordError):
            UserValidationService.validate_password_strength("x" * 129)

    def test_password_missing_uppercase_raises_error(self):
        """Test password without uppercase raises error."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            UserValidationService.validate_password_strength("validpass123!")
        assert "uppercase letter" in str(exc_info.value)

    def test_password_missing_lowercase_raises_error(self):
        """Test password without lowercase raises error."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            UserValidationService.validate_password_strength("VALIDPASS123!")
        assert "lowercase letter" in str(exc_info.value)

    def test_password_missing_digit_raises_error(self):
        """Test password without digit raises error."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            UserValidationService.validate_password_strength("ValidPass!")
        assert "digit" in str(exc_info.value)

    def test_password_missing_special_char_raises_error(self):
        """Test password without special character raises error."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            UserValidationService.validate_password_strength("ValidPass123")
        assert "special character" in str(exc_info.value)

    def test_password_strength_requirements_enforced(self):
        """Test that all password strength requirements are enforced together."""
        # Valid strong password should pass all checks
        UserValidationService.validate_password_strength("MyStr0ng!Pass")


class TestUsernameValidation:
    """Test username validation."""

    def test_valid_username(self):
        """Test valid username passes validation."""
        username = Username("validuser")
        # Should not raise
        UserValidationService.validate_username_not_reserved(username)

    def test_reserved_username_raises_error(self):
        """Test reserved username raises error."""
        username = Username("admin")
        with pytest.raises(InvalidUsernameError) as exc_info:
            UserValidationService.validate_username_not_reserved(username)
        assert "reserved" in str(exc_info.value)

    def test_reserved_username_case_insensitive(self):
        """Test reserved username check is case-insensitive."""
        username = Username("admin")  # Will be normalized to lowercase
        with pytest.raises(InvalidUsernameError):
            UserValidationService.validate_username_not_reserved(username)


class TestEmailValidation:
    """Test email validation."""

    def test_valid_email(self):
        """Test valid email passes validation."""
        email = Email("user@gmail.com")
        # Should not raise
        UserValidationService.validate_email_not_disposable(email)

    def test_disposable_email_raises_error(self):
        """Test disposable email raises error."""
        email = Email("user@tempmail.com")
        with pytest.raises(InvalidPasswordError) as exc_info:
            UserValidationService.validate_email_not_disposable(email)
        assert "Disposable email" in str(exc_info.value)


class TestFullNameValidation:
    """Test full name validation."""

    def test_valid_full_name(self):
        """Test valid full name passes validation."""
        # Should not raise
        UserValidationService.validate_full_name("John Doe")

    def test_empty_full_name_raises_error(self):
        """Test empty full name raises error."""
        with pytest.raises(ValueError):
            UserValidationService.validate_full_name("")

    def test_full_name_too_short_raises_error(self):
        """Test full name too short raises error."""
        with pytest.raises(ValueError) as exc_info:
            UserValidationService.validate_full_name("A")
        assert "at least 2 characters" in str(exc_info.value)

    def test_full_name_too_long_raises_error(self):
        """Test full name too long raises error."""
        with pytest.raises(ValueError):
            UserValidationService.validate_full_name("x" * 201)

    def test_full_name_with_numbers_raises_error(self):
        """Test full name with numbers raises error."""
        with pytest.raises(ValueError):
            UserValidationService.validate_full_name("John123")

    def test_full_name_with_special_chars_raises_error(self):
        """Test full name with invalid special characters raises error."""
        with pytest.raises(ValueError):
            UserValidationService.validate_full_name("John@Doe")

    def test_full_name_with_hyphen_valid(self):
        """Test full name with hyphen is valid."""
        # Should not raise
        UserValidationService.validate_full_name("Mary-Jane")

    def test_full_name_with_apostrophe_valid(self):
        """Test full name with apostrophe is valid."""
        # Should not raise
        UserValidationService.validate_full_name("O'Brien")


class TestUserRegistrationValidation:
    """Test combined user registration validation."""

    def test_valid_registration(self):
        """Test valid registration data passes all checks."""
        email = Email("user@example.com")
        username = Username("validuser")
        password = "ValidPass123!"
        full_name = "John Doe"

        # Should not raise
        UserValidationService.validate_user_registration(
            email, username, password, full_name
        )

    def test_registration_with_reserved_username_raises_error(self):
        """Test registration with reserved username raises error."""
        email = Email("user@example.com")
        username = Username("admin")
        password = "ValidPass123!"
        full_name = "John Doe"

        with pytest.raises(InvalidUsernameError):
            UserValidationService.validate_user_registration(
                email, username, password, full_name
            )

    def test_registration_with_weak_password_raises_error(self):
        """Test registration with weak password raises error."""
        email = Email("user@example.com")
        username = Username("validuser")
        password = "weak"
        full_name = "John Doe"

        with pytest.raises(InvalidPasswordError):
            UserValidationService.validate_user_registration(
                email, username, password, full_name
            )

    def test_registration_with_disposable_email_raises_error(self):
        """Test registration with disposable email raises error."""
        email = Email("user@tempmail.com")
        username = Username("validuser")
        password = "ValidPass123!"
        full_name = "John Doe"

        with pytest.raises(InvalidPasswordError):
            UserValidationService.validate_user_registration(
                email, username, password, full_name
            )


class TestFullNameSanitization:
    """Test full name sanitization."""

    def test_sanitize_strips_whitespace(self):
        """Test sanitize strips leading/trailing whitespace."""
        result = UserValidationService.sanitize_full_name("  John Doe  ")
        assert result == "John Doe"

    def test_sanitize_normalizes_multiple_spaces(self):
        """Test sanitize normalizes multiple spaces to single space."""
        result = UserValidationService.sanitize_full_name("John    Doe")
        assert result == "John Doe"

    def test_sanitize_title_cases_name(self):
        """Test sanitize applies title case."""
        result = UserValidationService.sanitize_full_name("john doe")
        assert result == "John Doe"

    def test_sanitize_combined(self):
        """Test sanitize applies all transformations."""
        result = UserValidationService.sanitize_full_name("  john   doe  ")
        assert result == "John Doe"
