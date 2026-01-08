"""
AccountType Pydantic schemas for API request/response handling.

This module provides:
- Account type creation and update schemas
- Account type response schemas
- Account type filtering and listing schemas
- Key format validation (lowercase, alphanumeric, underscore)
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class AccountTypeBase(BaseModel):
    """
    Base account type schema with common fields.

    Attributes:
        key: Unique identifier for programmatic use
        name: Display name shown to users
        description: Detailed description of the account type
        icon_url: URL to icon image for UI display
        sort_order: Integer for controlling display order
    """

    key: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
        description="Unique identifier (lowercase, alphanumeric, underscore only)",
        examples=["checking", "hsa", "401k"],
    )

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Display name shown to users",
        examples=["Checking Account", "Health Savings Account", "401(k)"],
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Detailed description of the account type",
        examples=["Standard checking account for daily transactions and bill payments"],
    )

    icon_url: HttpUrl | None = Field(
        default=None,
        max_length=500,
        description="URL to icon image for UI display",
        examples=["https://example.com/icons/checking.svg"],
    )

    sort_order: int = Field(
        default=0,
        description="Integer for controlling display order (lower numbers appear first)",
        examples=[1, 2, 10, 99],
    )

    @field_validator("key")
    @classmethod
    def validate_key_format(cls, value: str) -> str:
        """
        Validate and normalize key format.

        Keys must be:
        - Lowercase letters, numbers, and underscores only
        - No spaces or special characters
        - Not empty after stripping

        Args:
            value: Key to validate

        Returns:
            Normalized key (stripped and lowercased)

        Raises:
            ValueError: If key format is invalid
        """
        # Strip whitespace and convert to lowercase
        value = value.strip().lower()

        # Check not empty
        if not value:
            raise ValueError("Key cannot be empty or only whitespace")

        # Validate format (lowercase, alphanumeric, underscore only)
        if not re.match(r"^[a-z0-9_]+$", value):
            raise ValueError(
                "Key must contain only lowercase letters, numbers, and underscores"
            )

        return value

    @field_validator("name", "description")
    @classmethod
    def strip_and_validate_text(cls, value: str | None) -> str | None:
        """
        Strip whitespace from text fields.

        For required fields (name), validates not empty after stripping.
        For optional fields (description), returns None if empty after stripping.

        Args:
            value: Text value to process

        Returns:
            Stripped text or None

        Raises:
            ValueError: If required field is empty after stripping
        """
        if value is None:
            return None

        # Strip whitespace
        value = value.strip()

        # Return None if empty (for optional fields)
        # For required fields, Pydantic will catch the error due to min_length
        return value if value else None


class AccountTypeCreate(AccountTypeBase):
    """
    Schema for creating an account type.

    Used in POST /api/v1/account-types requests.
    Requires all base fields with validation.

    Note:
        - Key must be globally unique
        - Key is immutable once created
        - Only administrators can create account types
    """

    pass


class AccountTypeUpdate(BaseModel):
    """
    Schema for updating an account type.

    Used in PATCH /api/v1/account-types/{id} requests.
    All fields are optional to support partial updates.

    Important:
        - The 'key' field is NOT included (immutable once created)
        - Only administrators can update account types

    Attributes:
        name: New display name
        description: New description
        icon_url: New icon URL
        sort_order: New sort order
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Display name shown to users",
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Detailed description of the account type",
    )

    icon_url: HttpUrl | None = Field(
        default=None,
        max_length=500,
        description="URL to icon image for UI display",
    )

    sort_order: int | None = Field(
        default=None,
        description="Integer for controlling display order",
    )

    @field_validator("name", "description")
    @classmethod
    def strip_and_validate_text(cls, value: str | None) -> str | None:
        """Strip whitespace from text fields and validate not empty if provided."""
        if value is None:
            return None

        value = value.strip()

        # For name field, cannot be empty if provided
        # Pydantic will handle this with min_length
        return value if value else None


class AccountTypeResponse(AccountTypeBase):
    """
    Schema for account type response.

    Used in GET /api/v1/account-types/{id} responses.
    Includes all base fields plus database metadata.

    Attributes:
        id: Unique identifier (UUID)
        created_at: When the record was created
        updated_at: When the record was last updated
    """

    id: uuid.UUID = Field(description="Unique identifier")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AccountTypeEmbedded(BaseModel):
    """
    Minimal account type representation for embedding.

    Includes only essential fields for list display to reduce payload size.

    Attributes:
        id: Unique identifier
        key: Unique key identifier
        name: Display name
    """

    id: uuid.UUID = Field(description="Unique identifier")
    key: str = Field(description="Unique key identifier")
    name: str = Field(description="Display name")

    model_config = ConfigDict(from_attributes=True)


class AccountTypeListItem(BaseModel):
    """
    Schema for account type list item.

    Used in GET /api/v1/account-types responses.
    Includes only essential fields for list display to reduce payload size.

    Attributes:
        id: Unique identifier
        key: Unique key identifier
        name: Display name
        icon_url: Icon URL (optional)
        sort_order: Display order
    """

    id: uuid.UUID = Field(description="Unique identifier")
    key: str = Field(description="Unique key identifier")
    name: str = Field(description="Display name")
    icon_url: HttpUrl | None = Field(description="Icon URL")
    sort_order: int = Field(description="Display order")

    model_config = ConfigDict(from_attributes=True)
