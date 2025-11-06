"""Username value object."""

import re
from dataclasses import dataclass

from app.domain.exceptions import InvalidUsernameError


USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")
MIN_LENGTH = 3
MAX_LENGTH = 30


@dataclass(frozen=True)
class Username:
    """
    Username value object with validation.

    Immutable value object representing a username.
    Validates length and allowed characters.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate username."""
        # Strip and normalize first
        normalized = self.value.strip().lower()

        if not normalized:
            raise InvalidUsernameError(normalized, "Username cannot be empty")

        if len(normalized) < MIN_LENGTH:
            raise InvalidUsernameError(
                normalized,
                f"Username must be at least {MIN_LENGTH} characters long"
            )

        if len(normalized) > MAX_LENGTH:
            raise InvalidUsernameError(
                normalized,
                f"Username must be at most {MAX_LENGTH} characters long"
            )

        if not USERNAME_REGEX.match(normalized):
            raise InvalidUsernameError(
                normalized,
                "Username can only contain letters, numbers, hyphens, and underscores"
            )

        # Set normalized value
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Username(value={self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Username):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
