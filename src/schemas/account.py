"""
Account Pydantic schemas for API request/response handling.

This module provides:
- Account creation and update schemas
- Account response schemas
- Account filtering schemas
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from src.models.enums import AccountType


class AccountBase(BaseModel):
    """
    Base account schema with common fields.

    Attributes:
        account_name: Descriptive name for the account
        account_type: Type of account (savings, credit_card, etc.)
        currency: ISO 4217 currency code (3 uppercase letters)
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
    """

    opening_balance: Decimal = Field(
        description="Initial account balance (can be negative for loans/credit cards)",
        examples=["1000.00", "-500.00", "0.00"],
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


class AccountUpdate(BaseModel):
    """
    Schema for updating account information.

    Only account_name and is_active can be updated.
    Currency, balances, and account_type are immutable.

    All fields are optional to support partial updates (PATCH).

    Attributes:
        account_name: New account name (optional)
        is_active: New active status (optional)
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

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, value: str | None) -> str | None:
        """Validate account name if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Account name cannot be empty or only whitespace")
        return value


class AccountResponse(AccountBase):
    """
    Schema for account response.

    Returns full account details including balances and metadata.

    Attributes:
        id: Account UUID
        user_id: Owner's user ID
        account_name: Account name
        account_type: Account type
        currency: Currency code
        opening_balance: Initial balance
        current_balance: Current calculated balance
        is_active: Active status
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

    created_at: datetime = Field(description="When account was created")
    updated_at: datetime = Field(description="When account was last updated")

    model_config = {"from_attributes": True}


class AccountListItem(BaseModel):
    """
    Schema for account list item (optimized response).

    Lighter version of AccountResponse for list endpoints.
    Excludes some fields for performance.

    Attributes:
        id: Account UUID
        account_name: Account name
        account_type: Account type
        currency: Currency code
        current_balance: Current balance
        is_active: Active status
        created_at: Creation timestamp
    """

    id: uuid.UUID
    account_name: str
    account_type: AccountType
    currency: str
    current_balance: Decimal
    is_active: bool
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
