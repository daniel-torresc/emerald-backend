"""
Transaction Pydantic schemas for API request/response handling.

This module provides:
- Transaction creation and update schemas
- Transaction response schemas
- Transaction list and pagination schemas
- Transaction split schemas
- Transaction sort field enum
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import CardType, TransactionReviewStatus
from .card import CardEmbeddedResponse
from .common import SortOrder, SortParams
from .enums import TransactionSortField


class TransactionBase(BaseModel):
    """
    Base transaction schema with common fields.

    Attributes:
        transaction_date: Date when transaction occurred
        amount: Transaction amount (positive or negative, non-zero)
        currency: ISO 4217 currency code (must match account)
        original_description: Original transaction description (immutable, 1-500 chars)
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

    original_description: str = Field(
        min_length=1,
        max_length=500,
        description="Original transaction description (immutable after creation)",
        examples=["Grocery shopping at Whole Foods", "Salary deposit", "Electric bill"],
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

    @field_validator("original_description")
    @classmethod
    def validate_original_description(cls, value: str) -> str:
        """Validate and trim original description."""
        value = value.strip()
        if not value:
            raise ValueError("Original description cannot be empty or only whitespace")
        return value


class TransactionCreate(TransactionBase):
    """
    Schema for transaction creation.

    Attributes:
        transaction_date: Date when transaction occurred
        amount: Transaction amount
        currency: Currency code
        original_description: Original transaction description (immutable)
        merchant: Merchant name (optional, 1-100 chars)
        value_date: Date transaction value applied (optional)
        comments: User comments (optional, max 1000 chars)
        review_status: Review status (defaults to to_review)
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

    comments: str | None = Field(
        default=None,
        max_length=1000,
        description="User comments on transaction",
        examples=["Split with roommate", "Business expense - reimbursable"],
    )

    review_status: TransactionReviewStatus = Field(
        default=TransactionReviewStatus.to_review,
        description="Review status of transaction",
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

    @field_validator("comments")
    @classmethod
    def validate_comments(cls, value: str | None) -> str | None:
        """Validate and trim comments."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value


class TransactionUpdate(BaseModel):
    """
    Schema for updating transaction.

    All fields are optional to support partial updates (PATCH).
    Currency, account_id, and original_description cannot be changed.

    Note: original_description is intentionally NOT included as it is immutable
    after creation. Use user_description for user-editable description.

    Attributes:
        transaction_date: New date (optional)
        amount: New amount (optional)
        user_description: New user description (optional)
        merchant: New merchant (optional)
        comments: New comments (optional)
        review_status: New review status (optional)
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

    user_description: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="New user description (user-editable)",
    )

    merchant: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New merchant name",
    )

    comments: str | None = Field(
        default=None,
        max_length=1000,
        description="New user comments",
    )

    review_status: TransactionReviewStatus | None = Field(
        default=None,
        description="New review status",
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

    @field_validator("user_description")
    @classmethod
    def validate_user_description(cls, value: str | None) -> str | None:
        """Validate user description if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("User description cannot be empty")
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

    @field_validator("comments")
    @classmethod
    def validate_comments(cls, value: str | None) -> str | None:
        """Validate comments if provided."""
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
        original_description: Original description (immutable)
        user_description: User-editable description
        merchant: Merchant name
        comments: User comments
        review_status: Review status
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

    card: CardEmbeddedResponse | None = Field(
        default=None,
        description="Card details if card was used for this transaction",
    )

    user_description: str | None = Field(
        default=None,
        description="User-editable description",
    )

    merchant: str | None = Field(
        default=None,
        description="Merchant name",
    )

    value_date: date | None = Field(
        default=None,
        description="Date transaction value applied",
    )

    comments: str | None = Field(
        default=None,
        description="User comments",
    )

    review_status: TransactionReviewStatus = Field(
        description="Review status of transaction",
    )

    parent_transaction_id: uuid.UUID | None = Field(
        default=None,
        description="Parent transaction UUID if this is a split child",
    )

    parent_transaction: "TransactionEmbeddedResponse | None" = Field(
        default=None,
        description="Parent transaction if this is a split child",
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
    def convert_card(cls, card) -> CardEmbeddedResponse | None:
        """
        Convert Card model to CardEmbedded or None.

        Handles the card relationship from SQLAlchemy, converting
        the Card model object to the CardEmbedded schema for API responses.
        """
        if card is None:
            return None
        if hasattr(card, "id"):  # SQLAlchemy model
            return CardEmbeddedResponse.model_validate(card)
        return card

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """
    Lighter schema for transaction list responses.

    Includes only essential fields for list display.

    Attributes:
        id: Transaction UUID
        transaction_date: Transaction date
        amount: Transaction amount
        currency: Currency code
        original_description: Original description
        user_description: User-editable description
        merchant: Merchant name
        card: Card details if card was used
        review_status: Review status
        is_split_parent: Whether has children
        is_split_child: Whether is split child
    """

    id: uuid.UUID
    transaction_date: date
    amount: Decimal
    currency: str
    original_description: str
    user_description: str | None = None
    merchant: str | None = None
    card: CardEmbeddedResponse | None = None
    review_status: TransactionReviewStatus
    is_split_parent: bool = False
    is_split_child: bool = False

    @field_validator("card", mode="before")
    @classmethod
    def convert_card(cls, card) -> CardEmbeddedResponse | None:
        """Convert Card model to CardEmbedded or None."""
        if card is None:
            return None
        if hasattr(card, "id"):  # SQLAlchemy model
            return CardEmbeddedResponse.model_validate(card)
        return card

    model_config = ConfigDict(from_attributes=True)


class TransactionEmbeddedResponse(BaseModel):
    """
    Lighter schema for transaction embedded responses.

    Includes only essential fields for list display.

    Attributes:
        id: Transaction UUID
        transaction_date: Transaction date
        amount: Transaction amount
        currency: Currency code
        original_description: Original description
        user_description: User-editable description
        merchant: Merchant name
        card: Card details if card was used
        review_status: Review status
    """

    id: uuid.UUID
    transaction_date: date
    amount: Decimal
    currency: str
    original_description: str
    user_description: str | None = None
    merchant: str | None = None
    card: CardEmbeddedResponse | None = None
    review_status: TransactionReviewStatus


class TransactionFilterParams(BaseModel):
    """
    Query parameters for filtering transactions.

    All fields are optional - if not provided, no filter is applied.
    Pagination and sorting are handled separately via PaginationParams and SortParams.

    Attributes:
        date_from: Filter from this date (inclusive)
        date_to: Filter to this date (inclusive)
        amount_min: Minimum amount (inclusive)
        amount_max: Maximum amount (inclusive)
        description: Fuzzy search on description (both original and user)
        merchant: Fuzzy search on merchant
        review_status: Filter by review status
        card_id: Filter by specific card UUID
        card_type: Filter by card type (credit_card or debit_card)
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
        description="Fuzzy search on description (original and user)",
    )

    merchant: str | None = Field(
        default=None,
        max_length=100,
        description="Fuzzy search on merchant (handles typos)",
    )

    review_status: TransactionReviewStatus | None = Field(
        default=None,
        description="Filter by review status",
    )

    card_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by specific card UUID",
    )

    card_type: CardType | None = Field(
        default=None,
        description="Filter by card type (credit_card or debit_card)",
    )

    account_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by specific account UUID",
    )


class TransactionSortParams(SortParams[TransactionSortField]):
    """
    Sorting parameters for transaction list queries.

    Provides type-safe sorting with validation at schema level.
    Default sort: transaction_date descending (newest first).
    """

    sort_by: TransactionSortField = Field(
        default=TransactionSortField.TRANSACTION_DATE,
        description="Field to sort by",
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort direction",
    )


class TransactionSplitCreateItem(BaseModel):
    """
    Schema for a single split item.

    Attributes:
        amount: Split amount
        user_description: Split user description
        merchant: Split merchant (optional)
        comments: Split comments (optional)
    """

    amount: Decimal = Field(
        description="Split amount (must sum to parent amount)",
        examples=["-30.00", "-20.50"],
    )

    user_description: str = Field(
        min_length=1,
        max_length=500,
        description="User description for this split",
        examples=["Groceries", "Household items"],
    )

    merchant: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Merchant name for this split",
    )

    comments: str | None = Field(
        default=None,
        max_length=1000,
        description="Comments for this split",
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

    @field_validator("user_description")
    @classmethod
    def validate_user_description(cls, value: str) -> str:
        """Validate user description."""
        value = value.strip()
        if not value:
            raise ValueError("User description cannot be empty")
        return value


class TransactionSplitCreate(BaseModel):
    """
    Schema for splitting a transaction.

    Attributes:
        splits: List of split items (min 2, amounts must sum to parent)
    """

    splits: list[TransactionSplitCreateItem] = Field(
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
    def validate_splits(
        cls, value: list[TransactionSplitCreateItem]
    ) -> list[TransactionSplitCreateItem]:
        """Validate at least 2 splits."""
        if len(value) < 2:
            raise ValueError("At least 2 splits are required")
        return value
