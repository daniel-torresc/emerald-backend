"""
Transaction Pydantic schemas for API request/response handling.

This module provides:
- Transaction creation and update schemas
- Transaction response schemas
- Transaction list and pagination schemas
- Transaction split schemas
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from src.models.enums import CardType, TransactionType


class CardEmbedded(BaseModel):
    """
    Minimal card representation embedded in transaction responses.

    This schema provides essential card details without requiring
    a separate API call. Used in transaction responses to show
    which card was used for payment.

    Attributes:
        id: Card UUID
        name: Card display name
        card_type: Type of card (credit_card or debit_card)
        last_four_digits: Last 4 digits of card number
        card_network: Card network (Visa, Mastercard, etc.)
    """

    id: uuid.UUID = Field(description="Card UUID")
    name: str = Field(description="Card display name")
    card_type: CardType = Field(description="Type of card")
    last_four_digits: str | None = Field(
        default=None,
        description="Last 4 digits of card number",
    )
    card_network: str | None = Field(
        default=None,
        description="Card network (Visa, Mastercard, Amex, etc.)",
    )

    model_config = {"from_attributes": True}


class TransactionBase(BaseModel):
    """
    Base transaction schema with common fields.

    Attributes:
        transaction_date: Date when transaction occurred
        amount: Transaction amount (positive or negative, non-zero)
        currency: ISO 4217 currency code (must match account)
        description: Transaction description (1-500 chars)
        transaction_type: Type of transaction (debit, credit, etc.)
    """

    transaction_date: date = Field(
        description="Date when transaction occurred",
        examples=["2025-01-15"],
    )

    amount: Decimal = Field(
        description="Transaction amount (positive or negative, non-zero)",
        examples=["-50.25", "1000.00", "-15.99"],
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (must match account)",
        examples=["USD", "EUR", "GBP"],
    )

    description: str = Field(
        min_length=1,
        max_length=500,
        description="Transaction description",
        examples=["Grocery shopping at Whole Foods", "Salary deposit", "Electric bill"],
    )

    transaction_type: TransactionType = Field(
        description="Type of transaction",
        examples=[TransactionType.income, TransactionType.expense],
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """Validate currency format (ISO 4217)."""
        if not (len(value) == 3 and value.isalpha() and value.isupper()):
            raise ValueError(
                "Currency must be a valid ISO 4217 code (3 uppercase letters, e.g., USD, EUR, GBP)"
            )
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate amount is non-zero and has correct precision."""
        # Check non-zero
        if value == 0:
            raise ValueError("Transaction amount cannot be zero")

        # Check precision (2 decimal places max)
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount must have at most 2 decimal places")

        # Check range (fits in NUMERIC(15,2))
        if abs(value) >= Decimal("10") ** 13:
            raise ValueError("Amount is too large (max ±999,999,999,999.99)")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        """Validate and trim description."""
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be empty or only whitespace")
        return value


class TransactionCreate(TransactionBase):
    """
    Schema for transaction creation.

    Attributes:
        transaction_date: Date when transaction occurred
        amount: Transaction amount
        currency: Currency code
        description: Transaction description
        transaction_type: Transaction type
        merchant: Merchant name (optional, 1-100 chars)
        value_date: Date transaction value applied (optional)
        user_notes: User comments (optional, max 1000 chars)
        card_id: Card used for transaction (optional)
    """

    merchant: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Merchant name",
        examples=["Whole Foods", "Shell Gas Station", "Amazon"],
    )

    card_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the card used for this transaction (optional)",
    )

    value_date: date | None = Field(
        default=None,
        description="Date transaction value applied (can differ from transaction_date)",
        examples=["2025-01-16"],
    )

    user_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="User comments on transaction",
        examples=["Split with roommate", "Business expense - reimbursable"],
    )

    @field_validator("merchant")
    @classmethod
    def validate_merchant(cls, value: str | None) -> str | None:
        """Validate and trim merchant name."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value

    @field_validator("user_notes")
    @classmethod
    def validate_user_notes(cls, value: str | None) -> str | None:
        """Validate and trim user notes."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value


class TransactionUpdate(BaseModel):
    """
    Schema for updating transaction.

    All fields are optional to support partial updates (PATCH).
    Currency and account_id cannot be changed.

    Attributes:
        transaction_date: New date (optional)
        amount: New amount (optional)
        description: New description (optional)
        merchant: New merchant (optional)
        transaction_type: New type (optional)
        user_notes: New notes (optional)
        value_date: New value date (optional)
        card_id: Card used for transaction (optional)
    """

    transaction_date: date | None = Field(
        default=None,
        description="New transaction date",
    )

    card_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the card used for this transaction (optional)",
    )

    amount: Decimal | None = Field(
        default=None,
        description="New transaction amount (non-zero)",
    )

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="New description",
    )

    merchant: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New merchant name",
    )

    transaction_type: TransactionType | None = Field(
        default=None,
        description="New transaction type",
    )

    user_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="New user notes",
    )

    value_date: date | None = Field(
        default=None,
        description="New value date",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal | None) -> Decimal | None:
        """Validate amount if provided."""
        if value is not None:
            if value == 0:
                raise ValueError("Transaction amount cannot be zero")
            if value.as_tuple().exponent < -2:
                raise ValueError("Amount must have at most 2 decimal places")
            if abs(value) >= Decimal("10") ** 13:
                raise ValueError("Amount is too large")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        """Validate description if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Description cannot be empty")
        return value

    @field_validator("merchant")
    @classmethod
    def validate_merchant(cls, value: str | None) -> str | None:
        """Validate merchant if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value

    @field_validator("user_notes")
    @classmethod
    def validate_user_notes(cls, value: str | None) -> str | None:
        """Validate user notes if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value


class TransactionResponse(TransactionBase):
    """
    Schema for transaction response.

    Includes all transaction fields plus metadata.

    Attributes:
        id: Transaction UUID
        account_id: Account UUID
        card_id: Card UUID if card was used
        transaction_date: Transaction date
        value_date: Value date
        amount: Transaction amount
        currency: Currency code
        description: Description
        merchant: Merchant name
        transaction_type: Transaction type
        user_notes: User notes
        parent_transaction_id: Parent UUID if split child
        is_split_parent: Whether transaction has children
        is_split_child: Whether transaction is a split child
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created
        updated_by: User who last updated
    """

    id: uuid.UUID = Field(description="Transaction UUID")

    account_id: uuid.UUID = Field(description="Account UUID")

    card_id: uuid.UUID | None = Field(
        default=None,
        description="Card UUID if card was used for this transaction",
    )

    card: CardEmbedded | None = Field(
        default=None,
        description="Card details if card was used for this transaction",
    )

    merchant: str | None = Field(
        default=None,
        description="Merchant name",
    )

    value_date: date | None = Field(
        default=None,
        description="Date transaction value applied",
    )

    user_notes: str | None = Field(
        default=None,
        description="User comments",
    )

    parent_transaction_id: uuid.UUID | None = Field(
        default=None,
        description="Parent transaction UUID if this is a split child",
    )

    is_split_parent: bool = Field(
        default=False,
        description="Whether this transaction has child splits",
    )

    is_split_child: bool = Field(
        default=False,
        description="Whether this transaction is part of a split",
    )

    created_at: datetime = Field(description="Creation timestamp (UTC)")

    updated_at: datetime = Field(description="Last update timestamp (UTC)")

    created_by: uuid.UUID = Field(description="User who created transaction")

    updated_by: uuid.UUID = Field(description="User who last updated transaction")

    @field_validator("card", mode="before")
    @classmethod
    def convert_card(cls, card) -> CardEmbedded | None:
        """
        Convert Card model to CardEmbedded or None.

        Handles the card relationship from SQLAlchemy, converting
        the Card model object to the CardEmbedded schema for API responses.
        """
        if card is None:
            return None
        if hasattr(card, "id"):  # SQLAlchemy model
            return CardEmbedded.model_validate(card)
        return card

    model_config = {"from_attributes": True}


class TransactionListItem(BaseModel):
    """
    Lighter schema for transaction list responses.

    Includes only essential fields for list display.

    Attributes:
        id: Transaction UUID
        transaction_date: Transaction date
        amount: Transaction amount
        currency: Currency code
        description: Description
        merchant: Merchant name
        card: Card details if card was used
        transaction_type: Transaction type
        is_split_parent: Whether has children
        is_split_child: Whether is split child
    """

    id: uuid.UUID
    transaction_date: date
    amount: Decimal
    currency: str
    description: str
    merchant: str | None = None
    card: CardEmbedded | None = None
    transaction_type: TransactionType
    is_split_parent: bool = False
    is_split_child: bool = False

    @field_validator("card", mode="before")
    @classmethod
    def convert_card(cls, card) -> CardEmbedded | None:
        """Convert Card model to CardEmbedded or None."""
        if card is None:
            return None
        if hasattr(card, "id"):  # SQLAlchemy model
            return CardEmbedded.model_validate(card)
        return card

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """
    Response schema for transaction list endpoint.

    Attributes:
        items: List of transactions
        total: Total count of transactions
        skip: Number of records skipped
        limit: Maximum records returned
    """

    items: list[TransactionResponse] = Field(
        description="List of transactions for current page"
    )
    total: int = Field(description="Total count of transactions matching filters")
    skip: int = Field(description="Number of records skipped (pagination)")
    limit: int = Field(description="Maximum records returned")


class SplitItem(BaseModel):
    """
    Schema for a single split item.

    Attributes:
        amount: Split amount
        description: Split description
        merchant: Split merchant (optional)
        user_notes: Split notes (optional)
    """

    amount: Decimal = Field(
        description="Split amount (must sum to parent amount)",
        examples=["-30.00", "-20.50"],
    )

    description: str = Field(
        min_length=1,
        max_length=500,
        description="Split description",
        examples=["Groceries", "Household items"],
    )

    merchant: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Merchant name for this split",
    )

    user_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Notes for this split",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate split amount."""
        if value == 0:
            raise ValueError("Split amount cannot be zero")
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount must have at most 2 decimal places")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        """Validate description."""
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be empty")
        return value


class TransactionSplitRequest(BaseModel):
    """
    Schema for splitting a transaction.

    Attributes:
        splits: List of split items (min 2, amounts must sum to parent)
    """

    splits: list[SplitItem] = Field(
        min_length=2,
        description="List of splits (must sum to parent amount)",
        examples=[
            [
                {"amount": "-30.00", "description": "Groceries"},
                {"amount": "-20.50", "description": "Household items"},
            ]
        ],
    )

    @field_validator("splits")
    @classmethod
    def validate_splits(cls, value: list[SplitItem]) -> list[SplitItem]:
        """Validate at least 2 splits."""
        if len(value) < 2:
            raise ValueError("At least 2 splits are required")
        return value


class TransactionSearchParams(BaseModel):
    """
    DEPRECATED: Use TransactionFilterParams + PaginationParams instead.

    Query parameters for transaction search/filtering.

    All fields are optional - if not provided, no filter is applied.

    Attributes:
        date_from: Filter from this date (inclusive)
        date_to: Filter to this date (inclusive)
        amount_min: Minimum amount (inclusive)
        amount_max: Maximum amount (inclusive)
        description: Fuzzy search on description
        merchant: Fuzzy search on merchant
        transaction_type: Filter by type
        card_id: Filter by specific card UUID
        card_type: Filter by card type (credit_card or debit_card)
        sort_by: Sort field (transaction_date, amount, description, created_at)
        sort_order: Sort order (asc or desc)
        skip: Number of records to skip
        limit: Maximum records to return
    """

    date_from: date | None = Field(
        default=None,
        description="Filter from this date (inclusive)",
    )

    date_to: date | None = Field(
        default=None,
        description="Filter to this date (inclusive)",
    )

    amount_min: Decimal | None = Field(
        default=None,
        description="Minimum amount (inclusive)",
    )

    amount_max: Decimal | None = Field(
        default=None,
        description="Maximum amount (inclusive)",
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Fuzzy search on description (handles typos)",
    )

    merchant: str | None = Field(
        default=None,
        max_length=100,
        description="Fuzzy search on merchant (handles typos)",
    )

    transaction_type: TransactionType | None = Field(
        default=None,
        description="Filter by transaction type",
    )

    card_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by specific card UUID",
    )

    card_type: CardType | None = Field(
        default=None,
        description="Filter by card type (credit_card or debit_card)",
    )

    sort_by: str = Field(
        default="transaction_date",
        pattern="^(transaction_date|amount|description|created_at)$",
        description="Sort field",
    )

    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order",
    )

    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip (pagination)",
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum records to return (max 100)",
    )


class TransactionFilterParams(BaseModel):
    """
    Query parameters for filtering transactions.

    All fields are optional - if not provided, no filter is applied.
    Pagination is handled separately via PaginationParams.

    Attributes:
        date_from: Filter from this date (inclusive)
        date_to: Filter to this date (inclusive)
        amount_min: Minimum amount (inclusive)
        amount_max: Maximum amount (inclusive)
        description: Fuzzy search on description
        merchant: Fuzzy search on merchant
        transaction_type: Filter by type
        card_id: Filter by specific card UUID
        card_type: Filter by card type (credit_card or debit_card)
        sort_by: Sort field (transaction_date, amount, description, created_at)
        sort_order: Sort order (asc or desc)
    """

    date_from: date | None = Field(
        default=None,
        description="Filter from this date (inclusive)",
    )

    date_to: date | None = Field(
        default=None,
        description="Filter to this date (inclusive)",
    )

    amount_min: Decimal | None = Field(
        default=None,
        description="Minimum amount (inclusive)",
    )

    amount_max: Decimal | None = Field(
        default=None,
        description="Maximum amount (inclusive)",
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Fuzzy search on description (handles typos)",
    )

    merchant: str | None = Field(
        default=None,
        max_length=100,
        description="Fuzzy search on merchant (handles typos)",
    )

    transaction_type: TransactionType | None = Field(
        default=None,
        description="Filter by transaction type",
    )

    card_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by specific card UUID",
    )

    card_type: CardType | None = Field(
        default=None,
        description="Filter by card type (credit_card or debit_card)",
    )

    sort_by: str = Field(
        default="transaction_date",
        pattern="^(transaction_date|amount|description|created_at)$",
        description="Sort field",
    )

    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order",
    )
