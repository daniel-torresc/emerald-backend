"""Password hash value object."""

from dataclasses import dataclass

from app.domain.exceptions import InvalidPasswordError


@dataclass(frozen=True)
class PasswordHash:
    """
    Password hash value object.

    Immutable value object representing a hashed password.
    IMPORTANT: This should only contain hashed passwords, never plain text.
    Password hashing should be done in the infrastructure layer.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate password hash."""
        if not self.value:
            raise InvalidPasswordError("Password hash cannot be empty")

        if len(self.value) < 20:
            raise InvalidPasswordError(
                "Invalid password hash format (too short, likely not hashed)"
            )

        # Additional validation: ensure it looks like a hash (no spaces, sufficient length)
        if " " in self.value or "\n" in self.value or "\t" in self.value:
            raise InvalidPasswordError(
                "Invalid password hash format (contains whitespace)"
            )

    def __str__(self) -> str:
        return "***REDACTED***"  # Never expose the hash

    def __repr__(self) -> str:
        return "PasswordHash(***REDACTED***)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PasswordHash):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def matches_raw_value(self, raw_hash: str) -> bool:
        """
        Check if this hash matches the provided raw hash string.

        This is for internal domain use only. Password verification
        should be done in the infrastructure layer using proper
        password verification libraries.

        Args:
            raw_hash: The raw hash string to compare

        Returns:
            True if hashes match
        """
        return self.value == raw_hash
