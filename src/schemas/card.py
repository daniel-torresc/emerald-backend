"""
Pydantic schemas for card management.

This module defines request and response schemas for card operations:
- CardBase: Common fields shared across schemas
- CardCreate: Schema for POST /api/v1/cards
- CardUpdate: Schema for PATCH /api/v1/cards/{id}
- CardResponse: Schema for GET /api/v1/cards/{id}
- CardListItem: Schema for GET /api/v1/cards (list endpoint)
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.models.enums import CardType
from src.schemas import FinancialInstitutionListItem
from src.schemas.account import AccountListItem


class CardBase(BaseModel):
    """
    Base schema with common card fields.

    Contains fields that are shared across create and response schemas.
    All fields except card_type and name are optional.
    """

    name: str = Field(
        min_length=1,
        max_length=100,
        description="User-friendly display name for the card",
        examples=["Chase Sapphire Reserve", "Work Amex", "Chase Checking Debit"],
    )
    card_type: CardType = Field(description="Type of card (credit_card or debit_card)")
    last_four_digits: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}$",
        description="Last 4 digits of card number (exactly 4 numeric digits)",
        examples=["4242", "1234"],
    )
    card_network: str | None = Field(
        default=None,
        max_length=50,
        description="Payment network (Visa, Mastercard, Amex, Discover, etc.)",
        examples=["Visa", "Mastercard", "American Express"],
    )
    expiry_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Expiration month (1-12)",
        examples=[12, 6],
    )
    expiry_year: int | None = Field(
        default=None,
        description="Expiration year (four-digit format)",
        examples=[2027, 2026],
    )
    credit_limit: Decimal | None = Field(
        default=None,
        gt=0,
        description="Maximum credit available (primarily for credit cards)",
        examples=["25000.00", "10000.00"],
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="User's personal notes about the card",
        examples=["Primary travel rewards card", "For business expenses only"],
    )


class CardCreate(CardBase):
    """
    Schema for creating a new card (POST /api/v1/cards).

    Requires account_id to link the card to an account.
    Financial institution is optional.
    """

    account_id: uuid.UUID = Field(
        description="UUID of the account this card belongs to (REQUIRED)"
    )
    financial_institution_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the financial institution that issued the card (optional)",
    )

    @model_validator(mode="after")
    def validate_expiry_coupling(self) -> "CardCreate":
        """
        Ensure expiry_month and expiry_year are both provided or both omitted.

        If one is provided without the other, raise a validation error.
        This prevents incomplete expiration date information.

        Raises:
            ValueError: If only one of expiry_month or expiry_year is provided
        """
        if (self.expiry_month is None) != (self.expiry_year is None):
            raise ValueError(
                "Both expiry_month and expiry_year must be provided together, or both omitted"
            )
        return self

    @field_validator("expiry_year")
    @classmethod
    def validate_expiry_year(cls, value: int | None) -> int | None:
        """
        Validate expiration year is within reasonable range.

        Args:
            value: Year value to validate (or None)

        Returns:
            The validated year value (or None)

        Raises:
            ValueError: If year is not between 2000 and 2100
        """
        if value is None:
            return None
        if value < 2000 or value > 2100:
            raise ValueError("Expiry year must be between 2000 and 2100")
        return value


class CardUpdate(BaseModel):
    """
    Schema for updating an existing card (PATCH /api/v1/cards/{id}).

    All fields are optional for partial updates.
    card_type and account_id are NOT included (immutable after creation).
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User-friendly display name for the card",
    )
    last_four_digits: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}$",
        description="Last 4 digits of card number",
    )
    card_network: str | None = Field(
        default=None,
        max_length=50,
        description="Payment network",
    )
    expiry_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Expiration month (1-12)",
    )
    expiry_year: int | None = Field(
        default=None,
        description="Expiration year (four-digit format)",
    )
    credit_limit: Decimal | None = Field(
        default=None,
        gt=0,
        description="Maximum credit available",
    )
    financial_institution_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the financial institution",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="User's personal notes",
    )

    @field_validator("expiry_year")
    @classmethod
    def validate_expiry_year(cls, value: int | None) -> int | None:
        """Validate expiration year is within reasonable range."""
        if value is None:
            return None
        if value < 2000 or value > 2100:
            raise ValueError("Expiry year must be between 2000 and 2100")
        return value


class CardResponse(BaseModel):
    """
    Schema for card GET responses (GET /api/v1/cards/{id}).

    Returns complete card details including relationships.
    """

    id: uuid.UUID = Field(description="Unique identifier for the card")
    name: str = Field(description="User-friendly display name")
    card_type: CardType = Field(description="Type of card")
    last_four_digits: str | None = Field(
        description="Last 4 digits of card number (for identification only)"
    )
    card_network: str | None = Field(description="Payment network")
    expiry_month: int | None = Field(description="Expiration month (1-12)")
    expiry_year: int | None = Field(description="Expiration year")
    credit_limit: Decimal | None = Field(description="Maximum credit available")
    notes: str | None = Field(description="User's personal notes")

    # Relationships (always present for required FK, optional for nullable FK)
    account: AccountListItem = Field(
        description="Account this card is linked to (always present)"
    )
    financial_institution: FinancialInstitutionListItem | None = Field(
        description="Financial institution that issued the card (optional)"
    )

    # Timestamps
    created_at: datetime = Field(description="When the card was created")
    updated_at: datetime = Field(description="When the card was last updated")

    model_config = ConfigDict(from_attributes=True)


class CardListItem(BaseModel):
    """
    Schema for card list items (GET /api/v1/cards).

    Simplified card representation for list endpoints.
    Includes minimal relationship data for efficiency.
    """

    id: uuid.UUID = Field(description="Unique identifier for the card")
    name: str = Field(description="User-friendly display name")
    card_type: CardType = Field(description="Type of card")
    last_four_digits: str | None = Field(description="Last 4 digits of card number")
    card_network: str | None = Field(description="Payment network")

    # Simplified relationships
    account: AccountListItem = Field(description="Account this card is linked to")
    financial_institution: FinancialInstitutionListItem | None = Field(
        description="Financial institution that issued the card"
    )

    model_config = ConfigDict(from_attributes=True)


class CardFilterParams(BaseModel):
    """
    Query parameters for filtering cards.

    All fields are optional - if not provided, no filter is applied.

    Attributes:
        card_type: Filter by card type (credit_card or debit_card)
        account_id: Filter by account ID
        include_deleted: Include soft-deleted cards in results
    """

    card_type: CardType | None = Field(
        default=None,
        description="Filter by card type (credit_card or debit_card)",
    )

    account_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by account ID",
    )

    include_deleted: bool = Field(
        default=False,
        description="Include soft-deleted cards in results",
    )
