"""
Card model for credit and debit cards.

This module defines the Card SQLAlchemy model representing user cards
(credit cards or debit cards) within the system. Each card MUST be linked
to an account, and optionally to a financial institution.

Cards are user-owned data through account ownership. If a user owns the account,
they own all cards linked to that account.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import CardType
from src.models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.financial_institution import FinancialInstitution


class Card(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    User card (credit or debit) linked to an account.

    Each card represents a physical or virtual payment card that a user owns.
    Cards MUST be linked to an account - credit cards link to credit card accounts,
    debit cards link to checking/savings accounts.

    User ownership is derived from account ownership - if you own the account,
    you own the cards linked to it. No separate user_id is needed on cards.

    Attributes:
        id: UUID primary key
        account_id: UUID foreign key to accounts table (REQUIRED, RESTRICT on delete)
        financial_institution_id: UUID foreign key to financial_institutions (optional, SET NULL on delete)
        card_type: CardType enum (credit_card or debit_card)
        name: Display name for the card (e.g., "Chase Sapphire Reserve")
        last_four_digits: Last 4 digits of card number (for identification only)
        card_network: Payment network (Visa, Mastercard, Amex, Discover)
        expiry_month: Expiration month (1-12)
        expiry_year: Expiration year (four-digit format)
        credit_limit: Maximum credit available (primarily for credit cards)
        notes: User's personal notes about the card
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
        created_by: User who created the record (from AuditFieldsMixin)
        updated_by: User who last updated the record (from AuditFieldsMixin)
        created_at: Timestamp when created (from TimestampMixin)
        updated_at: Timestamp when last updated (from TimestampMixin)

    Relationships:
        account: The account this card is linked to (REQUIRED relationship)
        financial_institution: The institution that issued the card (optional)

    Constraints:
        - account_id CANNOT be null (every card must belong to an account)
        - account_id has RESTRICT on delete (cannot delete account with cards)
        - financial_institution_id has SET NULL on delete (preserve card if institution deleted)
        - expiry_month must be between 1 and 12 (if provided)
        - last_four_digits must be exactly 4 numeric digits (if provided)
        - credit_limit must be positive (if provided)

    Security Notes:
        - NEVER store full card numbers - only last 4 digits for identification
        - NEVER store CVV/security codes - these must never touch the database
        - Last 4 digits are for user identification only, not for payment processing

    Example:
        card = Card(
            account_id=uuid.uuid4(),
            card_type=CardType.credit_card,
            name="Chase Sapphire Reserve",
            last_four_digits="4242",
            card_network="Visa",
            expiry_month=12,
            expiry_year=2027,
            credit_limit=Decimal("25000.00"),
            financial_institution_id=chase_institution_id,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    """

    __tablename__ = "cards"

    # Primary Key (inherited from Base)
    id: Mapped[uuid.UUID]

    # REQUIRED Foreign Key - every card must belong to an account
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Optional Foreign Key - issuing institution
    financial_institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Card Type (REQUIRED)
    card_type: Mapped[CardType] = mapped_column(
        SQLEnum(CardType, name="card_type", create_constraint=True),
        nullable=False,
        index=True,
    )

    # Display name (REQUIRED)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Card identification (all optional)
    last_four_digits: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_network: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Credit limit (typically for credit cards only)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[account_id],
        lazy="selectin",
        back_populates="cards",
    )

    financial_institution: Mapped["FinancialInstitution | None"] = relationship(
        "FinancialInstitution",
        foreign_keys=[financial_institution_id],
        lazy="selectin",
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "(expiry_month IS NULL) OR (expiry_month >= 1 AND expiry_month <= 12)",
            name="ck_cards_expiry_month_range",
        ),
        CheckConstraint(
            "(last_four_digits IS NULL) OR (last_four_digits ~ '^[0-9]{4}$')",
            name="ck_cards_last_four_digits_format",
        ),
        CheckConstraint(
            "(credit_limit IS NULL) OR (credit_limit > 0)",
            name="ck_cards_credit_limit_positive",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the Card."""
        return f"Card(id={self.id}, name={self.name!r}, type={self.card_type.value})"
