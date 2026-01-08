"""
AccountShare model.
"""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account import Account
from .base import Base
from .enums import PermissionLevel
from .mixins import (
    AuditFieldsMixin,
    SoftDeleteMixin,
    TimestampMixin,
)
from .user import User

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
    account: Mapped[Account] = relationship(  # ty:ignore[unresolved-reference]
        "Account",
        back_populates="shares",
        foreign_keys=[account_id],
        lazy="selectin",
    )

    user: Mapped[User] = relationship(  # type: ignore
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
