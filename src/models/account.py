"""
Account and AccountShare models.

This module defines:
- Account: Financial account model (savings, credit card, loan, investment, etc.)
- AccountShare: Account sharing permissions (owner, editor, viewer)

Architecture:
- Each account belongs to one user (owner via user_id foreign key)
- Accounts can be shared with multiple users (many-to-many via AccountShare)
- Each share has a permission level (owner, editor, viewer)
- Soft delete support for regulatory compliance (7+ year retention)
- Balance tracking with opening_balance and current_balance
- Multi-currency support with ISO 4217 codes

Balance Calculation:
- Phase 2: current_balance = opening_balance (no transactions yet)
- Phase 3: current_balance = opening_balance + SUM(transactions)
- current_balance is cached for performance, calculated from transactions

Soft Delete:
- Deleted accounts have deleted_at set
- Deleted accounts excluded from normal queries (repository filters)
- Transaction history preserved after account deletion
- Account name freed for reuse after soft delete (partial unique index)
"""

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import PermissionLevel
from models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin


# =============================================================================
# Account Model
# =============================================================================


class Account(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    Financial account model.

    Represents a user's financial account (savings, credit card, loan, investment, etc.).
    Supports balance tracking, multi-currency, soft delete, and account sharing.

    Attributes:
        id: UUID primary key
        user_id: Owner of the account (foreign key to users)
        financial_institution_id: Financial institution ID (foreign key to financial_institutions, mandatory)
        account_name: User-defined descriptive name (1-100 chars, unique per user)
        account_type_id: Foreign key to account_types (system or user-defined type)
        currency: ISO 4217 currency code (3 uppercase letters, immutable)
        opening_balance: Initial account balance (can be negative for loans)
        current_balance: Current account balance (cached, calculated from transactions)
        created_at: When account was created
        updated_at: When account was last updated
        deleted_at: When account was soft-deleted (NULL if active)
        created_by: User who created the account
        updated_by: User who last updated the account

    Relationships:
        owner: User object who owns this account (via user_id)
        financial_institution: FinancialInstitution object (via financial_institution_id, eager-loaded)
        account_type: AccountType object (via account_type_id, eager-loaded)
        shares: List of AccountShare objects (who has access and permission level)

    Validation:
        - account_name: 1-100 characters, required, unique per user (case-insensitive)
        - account_type_id: Must reference an active account type (system or user's custom type)
        - currency: Must match ISO 4217 format (3 uppercase letters, e.g., USD, EUR, GBP)
        - opening_balance: Decimal(15,2), can be negative
        - current_balance: Decimal(15,2), can be negative
        - Currency is immutable after creation (enforced in service layer)

    Soft Delete:
        Deleted accounts remain in database with deleted_at set.
        This preserves:
        - Transaction history (required for compliance)
        - Audit trail
        - Ability to undo deletion

    Multi-Currency:
        - Each account has exactly one currency
        - Currency cannot be changed after creation (prevents accidental conversions)
        - Supports all ISO 4217 currency codes
        - Balance calculations respect currency (no automatic conversions)

    Account Sharing:
        - Accounts can be shared with multiple users via AccountShare
        - Each share has a permission level (owner, editor, viewer)
        - Only owner can manage sharing (create/update/delete shares)
        - Permission checks happen in service layer (PermissionService)

    Indexes:
        Defined in migration for performance:
        - user_id (for listing user's accounts)
        - account_type_id (for filtering by type)
        - currency (for filtering by currency)
        - deleted_at (for soft delete filtering)
        - Partial unique index on (user_id, LOWER(account_name)) WHERE deleted_at IS NULL

    Example:
        account = Account(
            user_id=user.id,
            financial_institution_id=institution.id,
            account_name="Chase Savings",
            account_type_id=savings_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            created_by=user.id,
            updated_by=user.id,
        )
    """

    __tablename__ = "accounts"

    # Ownership
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Financial Institution (Mandatory FK to master data)
    financial_institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Financial institution this account belongs to (mandatory)",
    )

    # Account Details
    account_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    account_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to account_types table",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        index=True,
    )

    # Balance Tracking
    # Decimal(15, 2) allows balances up to 999,999,999,999.99
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    # Account Metadata (Visual Customization & Bank Information)
    color_hex: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#818E8F",
        comment="Hex color code for UI display (e.g., #FF5733)",
    )

    icon_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL or path to account icon",
    )

    iban: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted IBAN (full account number, encrypted at rest)",
    )

    iban_last_four: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        comment="Last 4 digits of IBAN for display purposes (plaintext)",
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="User's personal notes about the account",
    )

    # Relationships
    owner: Mapped["User"] = relationship(  # type: ignore
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    financial_institution: Mapped["FinancialInstitution"] = relationship(  # type: ignore
        "FinancialInstitution",
        foreign_keys=[financial_institution_id],
        lazy="selectin",  # Async-safe eager loading to prevent N+1 queries
        back_populates="accounts",
    )

    account_type: Mapped["AccountType"] = relationship(  # type: ignore
        "AccountType",
        foreign_keys=[account_type_id],
        lazy="selectin",  # Async-safe eager loading to prevent N+1 queries
    )

    shares: Mapped[list["AccountShare"]] = relationship(
        "AccountShare",
        back_populates="account",
        foreign_keys="AccountShare.account_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    cards: Mapped[list["Card"]] = relationship(  # type: ignore
        "Card",
        back_populates="account",
        foreign_keys="Card.account_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Table-level constraints
    __table_args__ = (
        # Currency must be valid ISO 4217 code (3 uppercase letters)
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_accounts_currency_format",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Account."""
        return (
            f"Account(id={self.id}, name={self.account_name}, "
            f"type={self.account_type.key}, balance={self.current_balance} {self.currency}, "
            f"institution={self.financial_institution.short_name})"
        )


# =============================================================================
# AccountShare Model
# =============================================================================


class AccountShare(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    Account sharing permissions model.

    Links users to accounts they have access to with specific permission levels.
    Implements role-based access control (RBAC) for account sharing.

    Attributes:
        id: UUID primary key
        account_id: Account being shared (foreign key to accounts)
        user_id: User being granted access (foreign key to users)
        permission_level: Level of access (owner, editor, viewer)
        created_at: When share was created
        updated_at: When share was last updated
        deleted_at: When share was revoked (NULL if active)
        created_by: User who created the share (who granted access)

    Relationships:
        account: Account object being shared
        user: User object who has access

    Permission Levels:
        - OWNER: Full access (read, write, delete, manage sharing)
          * Only one owner per account (the creator)
          * Owner permission cannot be changed or revoked
          * Owner can grant/revoke access for other users

        - EDITOR: Read/write access (cannot delete or manage sharing)
          * Can view and update account details
          * Cannot delete account or change sharing
          * Suitable for partners managing shared finances

        - VIEWER: Read-only access
          * Can only view account details and balance
          * Cannot modify anything
          * Suitable for financial advisors or accountants

    Soft Delete (Revocation):
        - Revoking access sets deleted_at (soft delete)
        - Preserves revocation history for audit trail
        - Deleted shares excluded from permission checks
        - User immediately loses access when share deleted

    Uniqueness:
        - One active share per user per account (enforced by unique index)
        - Same user can have multiple shares if previous ones revoked
        - Partial unique index: (account_id, user_id) WHERE deleted_at IS NULL

    Permission Checking:
        Permission checks happen in PermissionService:
        1. Look up user's share for the account
        2. Check if share exists and is not deleted
        3. Verify permission level meets requirement
        4. Hierarchy: OWNER > EDITOR > VIEWER

    Audit Trail:
        All sharing operations are audited:
        - Share creation (who shared with whom, what permission)
        - Permission updates (old level → new level)
        - Access revocation (who revoked, when)

    Indexes:
        Defined in migration for performance:
        - account_id (for listing account's shares)
        - user_id (for listing user's shared accounts)
        - Composite index on (account_id, user_id, deleted_at) for permission lookups
        - Partial unique index on (account_id, user_id) WHERE deleted_at IS NULL

    Example:
        # Owner creates account and gets automatic owner share
        owner_share = AccountShare(
            account_id=account.id,
            user_id=owner.id,
            permission_level=PermissionLevel.OWNER,
            created_by=owner.id,
        )

        # Owner shares account with partner (editor)
        partner_share = AccountShare(
            account_id=account.id,
            user_id=partner.id,
            permission_level=PermissionLevel.EDITOR,
            created_by=owner.id,
        )

        # Owner shares account with advisor (viewer)
        advisor_share = AccountShare(
            account_id=account.id,
            user_id=advisor.id,
            permission_level=PermissionLevel.VIEWER,
            created_by=owner.id,
        )
    """

    __tablename__ = "account_shares"

    # Relationships
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Permission
    permission_level: Mapped[PermissionLevel] = mapped_column(
        nullable=False,
        index=True,
    )

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="shares",
        foreign_keys=[account_id],
        lazy="selectin",
    )

    user: Mapped["User"] = relationship(  # type: ignore
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of AccountShare."""
        return (
            f"AccountShare(id={self.id}, account_id={self.account_id}, "
            f"user_id={self.user_id}, permission={self.permission_level.value})"
        )
