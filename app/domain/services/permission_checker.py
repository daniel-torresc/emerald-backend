"""Permission checker domain service."""

from uuid import UUID

from app.domain.entities.account import Account
from app.domain.entities.user import User
from app.domain.exceptions import (
    InsufficientPermissionsError,
    UnauthorizedAccessError,
)
from app.domain.value_objects.permission import Permission


class PermissionChecker:
    """
    Domain service for checking permissions and authorization.

    Centralizes permission checking logic to avoid scattering it
    across entities and ensure consistent enforcement.
    """

    @staticmethod
    def check_user_has_permission(user: User, permission: Permission) -> None:
        """
        Check if user has a specific permission.

        Args:
            user: User to check
            permission: Required permission

        Raises:
            InsufficientPermissionsError: If user lacks the permission
        """
        if not user.has_permission(permission):
            raise InsufficientPermissionsError(str(user.id), permission.value)

    @staticmethod
    def check_user_has_any_permission(
        user: User,
        permissions: list[Permission]
    ) -> None:
        """
        Check if user has any of the specified permissions.

        Args:
            user: User to check
            permissions: List of permissions (user needs at least one)

        Raises:
            InsufficientPermissionsError: If user lacks all permissions
        """
        if not user.has_any_permission(permissions):
            permission_names = ", ".join(p.value for p in permissions)
            raise InsufficientPermissionsError(
                str(user.id),
                f"one of: {permission_names}"
            )

    @staticmethod
    def check_user_has_all_permissions(
        user: User,
        permissions: list[Permission]
    ) -> None:
        """
        Check if user has all of the specified permissions.

        Args:
            user: User to check
            permissions: List of permissions (user needs all)

        Raises:
            InsufficientPermissionsError: If user lacks any permission
        """
        if not user.has_all_permissions(permissions):
            permission_names = ", ".join(p.value for p in permissions)
            raise InsufficientPermissionsError(
                str(user.id),
                f"all of: {permission_names}"
            )

    @staticmethod
    def check_user_can_access_account(user: User, account: Account) -> None:
        """
        Check if user can access a specific account.

        Args:
            user: User to check
            account: Account to access

        Raises:
            UnauthorizedAccessError: If user cannot access the account
        """
        if not user.can_access_account(account):
            raise UnauthorizedAccessError(
                str(user.id),
                f"account {account.id}"
            )

    @staticmethod
    def check_user_is_active(user: User) -> None:
        """
        Check if user account is active.

        Args:
            user: User to check

        Raises:
            UnauthorizedAccessError: If user is not active
        """
        if not user.is_active:
            raise UnauthorizedAccessError(
                str(user.id),
                "system (account inactive)"
            )

    @staticmethod
    def check_user_is_admin(user: User) -> None:
        """
        Check if user is an administrator.

        Args:
            user: User to check

        Raises:
            InsufficientPermissionsError: If user is not admin
        """
        if not user.is_admin:
            raise InsufficientPermissionsError(
                str(user.id),
                "admin privileges"
            )

    @staticmethod
    def check_account_is_active(account: Account) -> None:
        """
        Check if account is active.

        Args:
            account: Account to check

        Raises:
            UnauthorizedAccessError: If account is not active
        """
        if not account.is_active:
            raise UnauthorizedAccessError(
                "system",
                f"account {account.id} (account inactive)"
            )

    @staticmethod
    def user_can_modify_account(user: User, account: Account) -> bool:
        """
        Check if user can modify an account (owner only).

        Args:
            user: User to check
            account: Account to modify

        Returns:
            True if user is the owner and can modify
        """
        return account.is_owned_by(user.id)

    @staticmethod
    def check_user_can_modify_account(user: User, account: Account) -> None:
        """
        Check if user can modify an account (raises exception if not).

        Args:
            user: User to check
            account: Account to modify

        Raises:
            UnauthorizedAccessError: If user is not the owner
        """
        if not PermissionChecker.user_can_modify_account(user, account):
            raise UnauthorizedAccessError(
                str(user.id),
                f"modify account {account.id} (only owner can modify)"
            )

    @staticmethod
    def user_can_delete_account(user: User, account: Account) -> bool:
        """
        Check if user can delete an account (owner only).

        Args:
            user: User to check
            account: Account to delete

        Returns:
            True if user is the owner and can delete
        """
        return account.is_owned_by(user.id)

    @staticmethod
    def check_user_can_delete_account(user: User, account: Account) -> None:
        """
        Check if user can delete an account (raises exception if not).

        Args:
            user: User to check
            account: Account to delete

        Raises:
            UnauthorizedAccessError: If user is not the owner
        """
        if not PermissionChecker.user_can_delete_account(user, account):
            raise UnauthorizedAccessError(
                str(user.id),
                f"delete account {account.id} (only owner can delete)"
            )

    @staticmethod
    def user_can_share_account(user: User, account: Account) -> bool:
        """
        Check if user can share an account (owner only).

        Args:
            user: User to check
            account: Account to share

        Returns:
            True if user is the owner and can share
        """
        return account.is_owned_by(user.id)

    @staticmethod
    def check_user_can_share_account(user: User, account: Account) -> None:
        """
        Check if user can share an account (raises exception if not).

        Args:
            user: User to check
            account: Account to share

        Raises:
            UnauthorizedAccessError: If user is not the owner
        """
        if not PermissionChecker.user_can_share_account(user, account):
            raise UnauthorizedAccessError(
                str(user.id),
                f"share account {account.id} (only owner can share)"
            )
