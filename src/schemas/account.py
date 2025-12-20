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

from schemas.account_type import AccountTypeListItem
from schemas.financial_institution import FinancialInstitutionResponse


class AccountBase(BaseModel):
    """
    Base account schema with common fields.

    Attributes:
        account_name: Descriptive name for the account
        currency: ISO 4217 currency code (3 uppercase letters)
        notes: User's personal notes about the account (optional)
    """

    account_name: str = Field(
        min_length=1,
        max_length=100,
        description="Account name (1-100 characters, unique per user)",
        examples=["Chase Checking", "Discover Card", "Emergency Fund"],
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (3 uppercase letters)",
        examples=["USD", "EUR", "GBP"],
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
        account_type_id: Account type UUID (must reference active account type)
        currency: ISO 4217 currency code (immutable after creation)
        financial_institution_id: Financial institution ID (REQUIRED, must reference active institution)
        opening_balance: Initial balance (can be negative for loans/credit cards)
        iban: Full IBAN (will be encrypted, immutable after creation)
        color_hex: Hex color code for UI display
        icon_url: URL to account icon
        notes: User notes
    """

    account_type_id: uuid.UUID = Field(
        description="Account type ID (must reference active account type)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    financial_institution_id: uuid.UUID = Field(
        description="Financial institution ID (required, must reference active institution)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

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

    Updateable fields: account_name, account_type_id, financial_institution_id, color_hex, icon_url, notes
    Immutable fields: currency, balances, iban

    All fields are optional to support partial updates (PATCH).

    Attributes:
        account_name: New account name (optional)
        account_type_id: New account type ID (optional, must be active and accessible)
        financial_institution_id: New institution ID (optional, must be active)
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

    account_type_id: uuid.UUID | None = Field(
        default=None,
        description="New account type ID (optional, must reference active account type)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    financial_institution_id: uuid.UUID | None = Field(
        default=None,
        description="New financial institution ID (optional, must reference active institution)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
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

    @field_validator("account_type_id")
    @classmethod
    def validate_account_type_id(cls, value: uuid.UUID | None) -> uuid.UUID | None:
        """Validate account type ID if provided."""
        if value is not None and value == uuid.UUID(
            "00000000-0000-0000-0000-000000000000"
        ):
            raise ValueError("Account type ID cannot be nil UUID")
        return value

    @field_validator("financial_institution_id")
    @classmethod
    def validate_financial_institution_id(
        cls, value: uuid.UUID | None
    ) -> uuid.UUID | None:
        """Validate institution ID if provided."""
        if value is not None and value == uuid.UUID(
            "00000000-0000-0000-0000-000000000000"
        ):
            raise ValueError("Financial institution ID cannot be nil UUID")
        return value


class AccountResponse(AccountBase):
    """
    Schema for account response.

    Returns full account details including balances and metadata.

    SECURITY NOTE: Full IBAN is NEVER returned (only last 4 digits).

    Attributes:
        id: Account UUID
        user_id: Owner's user ID
        account_type_id: Account type ID
        account_type: Account type details (key, name, icon, etc.)
        financial_institution_id: Financial institution ID
        financial_institution: Financial institution details (name, logo, etc.)
        account_name: Account name
        currency: Currency code
        notes: User notes
        opening_balance: Initial balance
        current_balance: Current calculated balance
        color_hex: Hex color code
        icon_url: Icon URL
        iban_last_four: Last 4 digits of IBAN (for display)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: uuid.UUID = Field(description="Account unique identifier")
    user_id: uuid.UUID = Field(description="Owner's user ID")

    account_type_id: uuid.UUID = Field(description="Account type ID")
    account_type: AccountTypeListItem = Field(
        description="Account type details (key, name, icon, etc.)"
    )

    financial_institution_id: uuid.UUID = Field(description="Financial institution ID")
    financial_institution: FinancialInstitutionResponse = Field(
        description="Financial institution details (name, logo, etc.)"
    )

    opening_balance: Decimal = Field(description="Initial account balance")
    current_balance: Decimal = Field(
        description="Current account balance (calculated from transactions in Phase 3)"
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
    Includes visual metadata (color, icon, institution) for UI display.

    Attributes:
        id: Account UUID
        account_name: Account name
        account_type_id: Account type ID
        account_type: Account type details
        currency: Currency code
        current_balance: Current balance
        color_hex: Hex color code
        icon_url: Icon URL
        financial_institution_id: Institution ID
        financial_institution: Full institution details
        created_at: Creation timestamp
    """

    id: uuid.UUID
    account_name: str
    account_type_id: uuid.UUID
    account_type: AccountTypeListItem
    currency: str
    current_balance: Decimal
    color_hex: str
    icon_url: str | None
    financial_institution_id: uuid.UUID
    financial_institution: FinancialInstitutionResponse
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountFilterParams(BaseModel):
    """
    Schema for account filtering parameters.

    Used for query parameters in list endpoints.

    Attributes:
        account_type_id: Filter by account type ID (None = all types)
        financial_institution_id: Filter by institution (None = all)
    """

    account_type_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by account type ID",
    )

    financial_institution_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by financial institution",
    )
