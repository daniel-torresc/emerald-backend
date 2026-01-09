"""
Transaction model.

This module defines:
- Transaction: Financial transaction model (debits, credits, transfers, fees, etc.)

Architecture:
- Each transaction belongs to one account (via account_id foreign key)
- Transactions can optionally reference a card (via card_id foreign key)
- Transactions support parent-child relationships for splitting (via parent_transaction_id)
- Soft delete support for audit trail and regulatory compliance
- Balance tracking integrated with account current_balance

Transaction-Card Relationship:
- Transactions can optionally reference which card was used (card_id foreign key)
- card_id is nullable - not all transactions use cards (cash, bank transfer, etc.)
- If card is soft-deleted, card_id is set to NULL (preserve transaction, clear card reference)
- Enables spending analysis by card

Transaction Splitting:
- Parent transactions can be split into multiple child transactions
- Child transactions have parent_transaction_id set to parent.id
- Split amounts must sum to parent amount exactly
- Splits can be reversed (joined) to restore parent as standalone

Balance Calculation:
- Account balance updates automatically when transactions created/updated/deleted
- current_balance = opening_balance + SUM(transactions WHERE deleted_at IS NULL)
- Balance updates are atomic (transaction + balance update in same DB transaction)
- Soft deleted transactions do not affect balance

Soft Delete:
- Deleted transactions have deleted_at set
- Deleted transactions excluded from normal queries (repository filters)
- Transaction history preserved for compliance (7+ year retention)
- Deleting parent transaction cascades to children
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account import Account
from .base import Base
from .card import Card
from .enums import TransactionReviewStatus
from .mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin

# =============================================================================
# Transaction Model
# =============================================================================


class Transaction(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    Financial transaction model.

    Represents a single financial transaction (debit, credit, transfer, fee, etc.).
    Supports parent-child relationships for splits, and soft delete for audit trail.

    Attributes:
        id: UUID primary key
        account_id: Account this transaction belongs to (foreign key to accounts)
        card_id: Card used for this transaction (foreign key to cards, optional)
        parent_transaction_id: Parent transaction if this is a split (foreign key to transactions)
        transaction_date: Transaction date (when transaction occurred)
        value_date: Date transaction value applied (can differ from date)
        amount: Transaction amount (positive or negative, non-zero)
        currency: ISO 4217 currency code (3 uppercase letters, must match account)
        original_description: Original transaction description as imported (immutable, 1-500 chars)
        user_description: User-editable description (defaults to original, 1-500 chars)
        merchant: Merchant name (1-100 chars, optional)
        comments: Optional user comments (max 1000 chars)
        review_status: Review status (to_review, reviewed)
        created_at: When transaction was created
        updated_at: When transaction was last updated
        deleted_at: When transaction was soft-deleted (NULL if active)
        created_by: User who created the transaction
        updated_by: User who last updated the transaction

    Relationships:
        account: Account object this transaction belongs to
        card: Card object used for this transaction (optional)
        parent_transaction: Parent transaction if this is a split child
        child_transactions: List of child transactions if this is a split parent

    Validation:
        - transaction_date: Valid date, configurable if future dates allowed
        - value_date: Valid date if provided
        - amount: Decimal(15,2), can be zero (e.g., fee waivers, promotional credits)
        - currency: Must match account.currency (enforced in service layer)
        - currency: Must match ISO 4217 format (3 uppercase letters)
        - original_description: 1-500 characters, required, immutable after creation
        - user_description: 1-500 characters, optional, user-editable
        - merchant: 1-100 characters if provided
        - review_status: Must be valid TransactionReviewStatus enum value
        - comments: Max 1000 characters

    Review Status:
        - TO_REVIEW: Transaction needs user review (default for new transactions)
        - REVIEWED: Transaction has been reviewed by user

    Transaction Splitting:
        Parent transaction:
            - Has child_transactions relationship populated
            - parent_transaction_id is NULL
            - Original amount preserved
            - Can query children via transaction.child_transactions

        Child transaction:
            - Has parent_transaction_id set to parent.id
            - Inherits: account_id, currency, date, value_date, original_description
            - Independent: amount, user_description, merchant
            - Can be queried via transaction.parent_transaction

        Validation:
            - Sum of child amounts must equal parent amount exactly
            - Cannot split a child transaction (no nested splits)
            - At least 2 splits required
            - Splits validated in service layer

    Soft Delete:
        - Deleted transactions remain in database with deleted_at set
        - Deleted transactions excluded from balance calculations
        - Deleted transactions excluded from normal queries
        - Deleting parent transaction deletes all children (cascade)

    Balance Updates:
        - Creating transaction: current_balance += amount
        - Updating transaction: current_balance += (new_amount - old_amount)
        - Deleting transaction: current_balance -= amount
        - Splitting transaction: No balance change (parent still exists)
        - All balance updates atomic (same DB transaction)

    Fuzzy Search:
        - PostgreSQL pg_trgm extension enables fuzzy text search
        - Merchant and description indexed with GIN trigram indexes
        - Finds matches with 1-2 character typos
        - Configurable similarity threshold (default 0.3)

    Indexes:
        Defined in migration for performance:
        - account_id (for listing account's transactions)
        - transaction_date (for date range queries)
        - review_status (for filtering by status)
        - parent_transaction_id (for split queries, partial WHERE NOT NULL)
        - deleted_at (for soft delete filtering)
        - Composite: (account_id, transaction_date) for common queries
        - Composite: (account_id, deleted_at) for balance calculations
        - GIN: merchant (for fuzzy search)
        - GIN: original_description (for fuzzy search)

    Example:
        # Simple transaction
        transaction = Transaction(
            account_id=account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.25"),
            currency="USD",
            original_description="Grocery Shopping",
            user_description="Weekly groceries at Whole Foods",
            merchant="Whole Foods",
            review_status=TransactionReviewStatus.to_review,
            created_by=user.id,
            updated_by=user.id,
        )

        # Split transaction child
        child = Transaction(
            account_id=account.id,
            parent_transaction_id=parent.id,
            transaction_date=parent.transaction_date,
            amount=Decimal("-30.00"),
            currency="USD",
            original_description=parent.original_description,
            user_description="Groceries",
            review_status=TransactionReviewStatus.to_review,
            created_by=user.id,
            updated_by=user.id,
        )
    """

    __tablename__ = "transactions"

    # Relationships
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Transaction Details
    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    value_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    original_description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    user_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    merchant: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    review_status: Mapped[TransactionReviewStatus] = mapped_column(
        nullable=False,
        default=TransactionReviewStatus.to_review,
        index=True,
    )

    # Relationships
    account: Mapped[Account] = relationship(  # type: ignore
        "Account",
        foreign_keys=[account_id],
        lazy="selectin",
    )

    card: Mapped[Card | None] = relationship(  # type: ignore
        "Card",
        foreign_keys=[card_id],
        lazy="selectin",
    )

    parent_transaction: Mapped["Transaction | None"] = relationship(
        "Transaction",
        remote_side="Transaction.id",
        foreign_keys=[parent_transaction_id],
        lazy="selectin",
        back_populates="child_transactions",
    )

    child_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys=[parent_transaction_id],
        lazy="selectin",
        back_populates="parent_transaction",
        cascade="all, delete-orphan",
    )

    # Table-level constraints
    __table_args__ = (
        # Currency must be valid ISO 4217 code (3 uppercase letters)
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_transactions_currency_format",
        ),
        # Note: Zero-amount transactions are allowed (e.g., fee waivers, promotional credits, adjustments)
    )

    @property
    def is_split_parent(self) -> bool:
        """Check if this transaction has child splits."""
        return len([c for c in self.child_transactions if c.deleted_at is None]) > 0

    @property
    def is_split_child(self) -> bool:
        """Check if this transaction is part of a split."""
        return self.parent_transaction_id is not None

    def __repr__(self) -> str:
        """String representation of Transaction."""
        return (
            f"Transaction(id={self.id}, account_id={self.account_id}, "
            f"transaction_date={self.transaction_date}, amount={self.amount} {self.currency}, "
            f"status={self.review_status.value})"
        )
