"""Account sharing domain service."""

from datetime import datetime
from uuid import UUID, uuid4

from app.domain.entities.account import Account
from app.domain.entities.account_share import AccountShare
from app.domain.entities.user import User
from app.domain.exceptions import AccountShareError
from app.domain.value_objects.permission import Permission


class AccountSharingService:
    """
    Domain service for managing account sharing business rules.

    Handles the complex logic around sharing accounts between users,
    including validation, permission management, and expiration.
    """

    @staticmethod
    def create_account_share(
        account: Account,
        sharing_user: User,
        recipient_user_id: UUID,
        permissions: list[Permission],
        can_view: bool = True,
        can_edit: bool = False,
        can_delete: bool = False,
        expires_at: datetime | None = None,
    ) -> AccountShare:
        """
        Create a new account share.

        Args:
            account: Account to share
            sharing_user: User who is sharing the account
            recipient_user_id: User ID to share with
            permissions: List of permissions to grant
            can_view: Whether recipient can view account
            can_edit: Whether recipient can edit account
            can_delete: Whether recipient can delete account
            expires_at: Optional expiration datetime

        Returns:
            New AccountShare entity

        Raises:
            AccountShareError: If share cannot be created
        """
        # Validate sharing user is the owner
        if not account.is_owned_by(sharing_user.id):
            raise AccountShareError(
                "Only the account owner can share the account"
            )

        # Validate not sharing with self
        if recipient_user_id == sharing_user.id:
            raise AccountShareError(
                "Cannot share account with yourself"
            )

        # Validate not already shared
        if account.is_shared_with(recipient_user_id):
            raise AccountShareError(
                "Account is already shared with this user"
            )

        # Validate expiration is in the future
        if expires_at is not None and expires_at < datetime.utcnow():
            raise AccountShareError(
                "Expiration date must be in the future"
            )

        # Validate at least view permission is granted
        if not can_view and not can_edit and not can_delete:
            raise AccountShareError(
                "Must grant at least one permission (view, edit, or delete)"
            )

        # Create the share
        account_share = AccountShare(
            id=uuid4(),
            account_id=account.id,
            shared_by_user_id=sharing_user.id,
            shared_with_user_id=recipient_user_id,
            permissions=permissions,
            can_view=can_view,
            can_edit=can_edit,
            can_delete=can_delete,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            revoked_at=None,
        )

        # Add to account's shared users list
        account.share_with_user(recipient_user_id)

        return account_share

    @staticmethod
    def revoke_account_share(
        account_share: AccountShare,
        account: Account,
        revoking_user: User,
    ) -> None:
        """
        Revoke an account share.

        Args:
            account_share: Share to revoke
            account: Account being shared
            revoking_user: User revoking the share

        Raises:
            AccountShareError: If share cannot be revoked
        """
        # Validate revoking user is the owner
        if not account.is_owned_by(revoking_user.id):
            raise AccountShareError(
                "Only the account owner can revoke shares"
            )

        # Validate share is for this account
        if account_share.account_id != account.id:
            raise AccountShareError(
                "Share does not belong to this account"
            )

        # Validate share is not already revoked
        if account_share.is_revoked():
            raise AccountShareError(
                "Share is already revoked"
            )

        # Revoke the share
        account_share.revoke()

        # Remove from account's shared users list
        account.unshare_with_user(account_share.shared_with_user_id)

    @staticmethod
    def update_share_permissions(
        account_share: AccountShare,
        account: Account,
        updating_user: User,
        new_permissions: list[Permission],
        can_view: bool | None = None,
        can_edit: bool | None = None,
        can_delete: bool | None = None,
    ) -> None:
        """
        Update permissions on an existing share.

        Args:
            account_share: Share to update
            account: Account being shared
            updating_user: User updating the share
            new_permissions: New permissions list
            can_view: New can_view value (optional)
            can_edit: New can_edit value (optional)
            can_delete: New can_delete value (optional)

        Raises:
            AccountShareError: If permissions cannot be updated
        """
        # Validate updating user is the owner
        if not account.is_owned_by(updating_user.id):
            raise AccountShareError(
                "Only the account owner can update share permissions"
            )

        # Validate share is active
        if not account_share.is_active():
            raise AccountShareError(
                "Cannot update permissions on inactive share"
            )

        # Update basic permissions
        if can_view is not None:
            account_share.can_view = can_view
        if can_edit is not None:
            account_share.can_edit = can_edit
        if can_delete is not None:
            account_share.can_delete = can_delete

        # Validate at least one permission is granted
        if not account_share.can_view and not account_share.can_edit and not account_share.can_delete:
            raise AccountShareError(
                "Must grant at least one permission (view, edit, or delete)"
            )

        # Update granular permissions
        account_share.permissions = new_permissions

    @staticmethod
    def extend_share_expiration(
        account_share: AccountShare,
        account: Account,
        extending_user: User,
        new_expiration: datetime,
    ) -> None:
        """
        Extend the expiration date of a share.

        Args:
            account_share: Share to extend
            account: Account being shared
            extending_user: User extending the share
            new_expiration: New expiration datetime

        Raises:
            AccountShareError: If expiration cannot be extended
        """
        # Validate extending user is the owner
        if not account.is_owned_by(extending_user.id):
            raise AccountShareError(
                "Only the account owner can extend share expiration"
            )

        # Validate share is active
        if not account_share.is_active():
            raise AccountShareError(
                "Cannot extend expiration on inactive share"
            )

        # Extend expiration (this validates the date internally)
        try:
            account_share.extend_expiration(new_expiration)
        except ValueError as e:
            raise AccountShareError(str(e))

    @staticmethod
    def make_share_permanent(
        account_share: AccountShare,
        account: Account,
        updating_user: User,
    ) -> None:
        """
        Remove expiration from a share, making it permanent.

        Args:
            account_share: Share to make permanent
            account: Account being shared
            updating_user: User making the share permanent

        Raises:
            AccountShareError: If share cannot be made permanent
        """
        # Validate updating user is the owner
        if not account.is_owned_by(updating_user.id):
            raise AccountShareError(
                "Only the account owner can make shares permanent"
            )

        # Validate share is active
        if not account_share.is_active():
            raise AccountShareError(
                "Cannot make inactive share permanent"
            )

        # Make permanent
        account_share.make_permanent()

    @staticmethod
    def validate_share_access(
        account_share: AccountShare,
        required_permission: Permission,
    ) -> bool:
        """
        Validate that a share grants access to a specific permission.

        Args:
            account_share: Share to validate
            required_permission: Permission needed

        Returns:
            True if share grants the permission
        """
        return (
            account_share.is_active() and
            account_share.has_permission(required_permission)
        )

    @staticmethod
    def check_share_is_active(account_share: AccountShare) -> None:
        """
        Check if a share is currently active.

        Args:
            account_share: Share to check

        Raises:
            AccountShareError: If share is not active
        """
        if not account_share.is_active():
            if account_share.is_revoked():
                raise AccountShareError("Share has been revoked")
            elif account_share.is_expired():
                raise AccountShareError("Share has expired")
            else:
                raise AccountShareError("Share is not active")
