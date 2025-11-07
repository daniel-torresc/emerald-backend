"""User validation domain service."""

import re

from app.domain.exceptions import InvalidPasswordError, InvalidUsernameError
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username


class UserValidationService:
    """
    Domain service for complex user validation rules.

    Handles validation logic that goes beyond simple value object
    validation, such as password strength requirements and
    username blacklists.
    """

    # Common usernames that should not be allowed
    RESERVED_USERNAMES = {
        "admin", "administrator", "root", "system", "api", "www",
        "mail", "support", "help", "info", "contact", "sales",
        "noreply", "no-reply", "postmaster", "webmaster", "hostmaster",
        "test", "demo", "guest", "user", "moderator", "mod",
    }

    # Password strength requirements
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL_CHAR = True
    SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;:,.<>?"

    @classmethod
    def validate_password_strength(cls, plain_password: str) -> None:
        """
        Validate that a plain password meets strength requirements.

        This should be called BEFORE hashing the password.

        Args:
            plain_password: Plain text password to validate

        Raises:
            InvalidPasswordError: If password doesn't meet requirements
        """
        if len(plain_password) < cls.MIN_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long"
            )

        if len(plain_password) > cls.MAX_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"Password must be at most {cls.MAX_PASSWORD_LENGTH} characters long"
            )

        if cls.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", plain_password):
            raise InvalidPasswordError(
                "Password must contain at least one uppercase letter"
            )

        if cls.REQUIRE_LOWERCASE and not re.search(r"[a-z]", plain_password):
            raise InvalidPasswordError(
                "Password must contain at least one lowercase letter"
            )

        if cls.REQUIRE_DIGIT and not re.search(r"\d", plain_password):
            raise InvalidPasswordError(
                "Password must contain at least one digit"
            )

        if cls.REQUIRE_SPECIAL_CHAR:
            if not any(char in cls.SPECIAL_CHARS for char in plain_password):
                raise InvalidPasswordError(
                    f"Password must contain at least one special character: {cls.SPECIAL_CHARS}"
                )

        # Check for common weak passwords
        if cls._is_common_password(plain_password):
            raise InvalidPasswordError(
                "Password is too common. Please choose a more secure password."
            )

    @staticmethod
    def _is_common_password(password: str) -> bool:
        """
        Check if password is in list of common weak passwords.

        Args:
            password: Password to check

        Returns:
            True if password is common/weak
        """
        # Common weak passwords (add more as needed)
        common_passwords = {
            "password", "password123", "12345678", "qwerty", "abc123",
            "letmein", "welcome", "monkey", "password1", "123456789",
            "password!", "Password1", "Password123", "Welcome1",
        }
        return password.lower() in common_passwords

    @classmethod
    def validate_username_not_reserved(cls, username: Username) -> None:
        """
        Validate that username is not a reserved system username.

        Args:
            username: Username to validate

        Raises:
            InvalidUsernameError: If username is reserved
        """
        if username.value.lower() in cls.RESERVED_USERNAMES:
            raise InvalidUsernameError(
                username.value,
                "This username is reserved and cannot be used"
            )

    @staticmethod
    def validate_email_not_disposable(email: Email) -> None:
        """
        Validate that email is not from a disposable email provider.

        This is a simplified check. In production, you'd use a service
        or comprehensive list of disposable email domains.

        Args:
            email: Email to validate

        Raises:
            InvalidPasswordError: If email is from disposable provider
        """
        # Common disposable email domains (add more as needed)
        disposable_domains = {
            "tempmail.com", "throwaway.email", "guerrillamail.com",
            "10minutemail.com", "mailinator.com", "trashmail.com",
            "yopmail.com", "temp-mail.org", "getnada.com",
        }

        if email.domain in disposable_domains:
            raise InvalidPasswordError(
                "Disposable email addresses are not allowed"
            )

    @staticmethod
    def validate_full_name(full_name: str) -> None:
        """
        Validate user's full name.

        Args:
            full_name: Full name to validate

        Raises:
            ValueError: If full name is invalid
        """
        if not full_name or not full_name.strip():
            raise ValueError("Full name cannot be empty")

        if len(full_name) < 2:
            raise ValueError("Full name must be at least 2 characters long")

        if len(full_name) > 200:
            raise ValueError("Full name cannot exceed 200 characters")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s'-]+$", full_name):
            raise ValueError(
                "Full name can only contain letters, spaces, hyphens, and apostrophes"
            )

    @classmethod
    def validate_user_registration(
        cls,
        email: Email,
        username: Username,
        plain_password: str,
        full_name: str,
    ) -> None:
        """
        Validate all user registration inputs together.

        Convenience method that runs all validation checks.

        Args:
            email: Email address
            username: Username
            plain_password: Plain text password
            full_name: Full name

        Raises:
            Various validation exceptions if any check fails
        """
        # Email is already validated by Email value object
        cls.validate_email_not_disposable(email)

        # Username is already validated by Username value object
        cls.validate_username_not_reserved(username)

        # Validate password strength
        cls.validate_password_strength(plain_password)

        # Validate full name
        cls.validate_full_name(full_name)

    @staticmethod
    def sanitize_full_name(full_name: str) -> str:
        """
        Sanitize and normalize full name.

        Args:
            full_name: Full name to sanitize

        Returns:
            Sanitized full name
        """
        # Strip whitespace
        sanitized = full_name.strip()

        # Normalize multiple spaces to single space
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Capitalize each word (basic title case)
        sanitized = sanitized.title()

        return sanitized
