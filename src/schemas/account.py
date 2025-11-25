"""
Account Pydantic schemas for API request/response handling.

This module provides:
- Account creation and update schemas
- Account response schemas
- Account filtering schemas
"""

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl, field_validator
from schwifty import IBAN

from src.models.enums import AccountType


class AccountBase(BaseModel):
    """
    Base account schema with common fields.

    Attributes:
        account_name: Descriptive name for the account
        account_type: Type of account (savings, credit_card, etc.)
        currency: ISO 4217 currency code (3 uppercase letters)
        bank_name: Name of the financial institution (optional)
        notes: User's personal notes about the account (optional)
    """

    account_name: str = Field(
        min_length=1,
        max_length=100,
        description="Account name (1-100 characters, unique per user)",
        examples=["Chase Checking", "Discover Card", "Emergency Fund"],
    )

    account_type: AccountType = Field(
        description="Type of financial account",
        examples=[AccountType.savings, AccountType.checking],
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (3 uppercase letters)",
        examples=["USD", "EUR", "GBP"],
    )

    bank_name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the financial institution",
        examples=["Chase Bank", "Bank of America", "Wells Fargo"],
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Personal notes about the account",
        examples=[
            "Joint account with spouse",
            "Savings for vacation",
            "Emergency fund",
        ],
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """
        Validate currency format (ISO 4217).

        Must be exactly 3 uppercase letters.
        """
        if not (len(value) == 3 and value.isalpha() and value.isupper()):
            raise ValueError(
                "Currency must be a valid ISO 4217 code (3 uppercase letters, e.g., USD, EUR, GBP)"
            )
        return value

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, value: str) -> str:
        """
        Validate account name.

        Trims whitespace and ensures it's not empty after trimming.
        """
        value = value.strip()
        if not value:
            raise ValueError("Account name cannot be empty or only whitespace")
        return value


class AccountCreate(AccountBase):
    """
    Schema for account creation.

    Attributes:
        account_name: Name of the account
        account_type: Type of account
        currency: ISO 4217 currency code (immutable after creation)
        opening_balance: Initial balance (can be negative for loans/credit cards)
        bank_name: Bank institution name (immutable after creation)
        iban: Full IBAN (will be encrypted, immutable after creation)
        color_hex: Hex color code for UI display
        icon_url: URL to account icon
        notes: User notes
    """

    opening_balance: Decimal = Field(
        description="Initial account balance (can be negative for loans/credit cards)",
        examples=["1000.00", "-500.00", "0.00"],
    )

    iban: str | None = Field(
        default=None,
        description="IBAN (International Bank Account Number) - will be encrypted",
        examples=["DE89370400440532013000", "GB82 WEST 1234 5698 7654 32"],
    )

    color_hex: str = Field(
        default="#818E8F",
        description="Hex color code for account visualization (e.g., #FF5733)",
        examples=["#FF5733", "#3498DB", "#2ECC71"],
    )

    icon_url: HttpUrl | None = Field(
        default=None,
        description="URL to account icon image",
        examples=["https://cdn.example.com/icons/bank.png"],
    )

    @field_validator("opening_balance")
    @classmethod
    def validate_opening_balance(cls, value: Decimal) -> Decimal:
        """
        Validate opening balance precision.

        Must have maximum 2 decimal places and fit in NUMERIC(15,2).
        """
        # Check precision (2 decimal places max)
        if value.as_tuple().exponent < -2:
            raise ValueError("Balance must have at most 2 decimal places")

        # Check range (fits in NUMERIC(15,2): -999,999,999,999.99 to 999,999,999,999.99)
        if abs(value) >= Decimal("10") ** 13:
            raise ValueError("Balance is too large (max ±999,999,999,999.99)")

        return value

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, value: str) -> str:
        """
        Validate hex color format.

        Must be #RRGGBB (7 characters: # + 6 hex digits).
        """
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError("Color must be a valid hex code (e.g., #FF5733, #3498DB)")
        return value.upper()  # Normalize to uppercase

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, value: str | None) -> str | None:
        """
        Validate IBAN format and checksum.

        Uses schwifty library for comprehensive IBAN validation.
        """
        if value is None:
            return None

        try:
            # Remove spaces and hyphens, normalize
            normalized = value.replace(" ", "").replace("-", "").upper()

            # Validate using schwifty
            IBAN(normalized)

            return normalized
        except Exception as e:
            raise ValueError(f"Invalid IBAN: {str(e)}") from e

    @field_validator("icon_url")
    @classmethod
    def validate_icon_url(cls, value: HttpUrl | str | None) -> str | None:
        """Convert HttpUrl to string if provided."""
        if value is None:
            return None
        return str(value)


class AccountUpdate(BaseModel):
    """
    Schema for updating account information.

    Updateable fields: account_name, is_active, color_hex, icon_url, notes
    Immutable fields: currency, balances, account_type, bank_name, iban

    All fields are optional to support partial updates (PATCH).

    Attributes:
        account_name: New account name (optional)
        is_active: New active status (optional)
        color_hex: New hex color code (optional)
        icon_url: New icon URL (optional)
        notes: New notes (optional)
    """

    account_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New account name",
        examples=["Renamed Account"],
    )

    is_active: bool | None = Field(
        default=None,
        description="Active status (inactive accounts hidden by default)",
        examples=[True, False],
    )

    color_hex: str | None = Field(
        default=None,
        description="Hex color code for account visualization",
        examples=["#FF5733", "#3498DB"],
    )

    icon_url: HttpUrl | None = Field(
        default=None,
        description="URL to account icon image",
        examples=["https://cdn.example.com/icons/bank.png"],
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Personal notes about the account",
        examples=["Updated notes"],
    )

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, value: str | None) -> str | None:
        """Validate account name if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Account name cannot be empty or only whitespace")
        return value

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, value: str | None) -> str | None:
        """Validate hex color format if provided."""
        if value is not None:
            if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
                raise ValueError(
                    "Color must be a valid hex code (e.g., #FF5733, #3498DB)"
                )
            return value.upper()
        return value

    @field_validator("icon_url")
    @classmethod
    def validate_icon_url(cls, value: HttpUrl | str | None) -> str | None:
        """Convert HttpUrl to string if provided."""
        if value is None:
            return None
        return str(value)


class AccountResponse(AccountBase):
    """
    Schema for account response.

    Returns full account details including balances and metadata.

    SECURITY NOTE: Full IBAN is NEVER returned (only last 4 digits).

    Attributes:
        id: Account UUID
        user_id: Owner's user ID
        account_name: Account name
        account_type: Account type
        currency: Currency code
        bank_name: Bank institution name
        notes: User notes
        opening_balance: Initial balance
        current_balance: Current calculated balance
        is_active: Active status
        color_hex: Hex color code
        icon_url: Icon URL
        iban_last_four: Last 4 digits of IBAN (for display)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: uuid.UUID = Field(description="Account unique identifier")
    user_id: uuid.UUID = Field(description="Owner's user ID")

    opening_balance: Decimal = Field(description="Initial account balance")
    current_balance: Decimal = Field(
        description="Current account balance (calculated from transactions in Phase 3)"
    )

    is_active: bool = Field(
        description="Whether account is active (inactive accounts hidden by default)"
    )

    # Metadata fields
    color_hex: str = Field(description="Hex color code for UI display")
    icon_url: str | None = Field(description="URL to account icon")
    iban_last_four: str | None = Field(
        description="Last 4 digits of IBAN for display (never full IBAN)"
    )

    created_at: datetime = Field(description="When account was created")
    updated_at: datetime = Field(description="When account was last updated")

    model_config = {"from_attributes": True}


class AccountListItem(BaseModel):
    """
    Schema for account list item (optimized response).

    Lighter version of AccountResponse for list endpoints.
    Includes visual metadata (color, icon, bank_name) for UI display.

    Attributes:
        id: Account UUID
        account_name: Account name
        account_type: Account type
        currency: Currency code
        current_balance: Current balance
        is_active: Active status
        color_hex: Hex color code
        icon_url: Icon URL
        bank_name: Bank name
        created_at: Creation timestamp
    """

    id: uuid.UUID
    account_name: str
    account_type: AccountType
    currency: str
    current_balance: Decimal
    is_active: bool
    color_hex: str
    icon_url: str | None
    bank_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountFilterParams(BaseModel):
    """
    Schema for account filtering parameters.

    Used for query parameters in list endpoints.

    Attributes:
        is_active: Filter by active status (None = all)
        account_type: Filter by account type (None = all types)
    """

    is_active: bool | None = Field(
        default=None,
        description="Filter by active status (true=active, false=inactive, null=all)",
    )

    account_type: AccountType | None = Field(
        default=None,
        description="Filter by account type",
    )
