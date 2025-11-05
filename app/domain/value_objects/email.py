"""Email value object."""

import re
from dataclasses import dataclass

from app.domain.exceptions import InvalidEmailError


EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


@dataclass(frozen=True)
class Email:
    """
    Email value object with validation.

    Immutable value object representing an email address.
    Validates format and normalizes to lowercase.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate email format and normalize."""
        # Strip and normalize first
        normalized = self.value.strip().lower()

        if not normalized:
            raise InvalidEmailError("Email cannot be empty")

        if not EMAIL_REGEX.match(normalized):
            raise InvalidEmailError(self.value)

        # Set normalized value
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email(value={self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Email):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    @property
    def domain(self) -> str:
        """Extract domain part from email address."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part (before @) from email address."""
        return self.value.split("@")[0]
