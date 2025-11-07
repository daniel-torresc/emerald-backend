"""Unit tests for PermissionChecker domain service."""

from uuid import uuid4

import pytest

from app.domain.entities.account import Account
from app.domain.entities.role import Role
from app.domain.entities.user import User
from app.domain.exceptions import (
    InsufficientPermissionsError,
    UnauthorizedAccessError,
)
from app.domain.services.permission_checker import PermissionChecker
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.email import Email
from app.domain.value_objects.money import Money
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.permission import Permission
from app.domain.value_objects.username import Username


class TestPermissionCheckerUserPermissions:
    """Test PermissionChecker user permission checks."""

    def test_check_user_has_permission_success(self):
        """Test check passes when user has permission."""
        role = Role(
            id=uuid4(),
            name="Editor",
            description="Editor",
            permissions=[Permission.USER_READ]
        )
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        # Should not raise
        PermissionChecker.check_user_has_permission(user, Permission.USER_READ)

    def test_check_user_has_permission_raises_error(self):
        """Test check raises error when user lacks permission."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        with pytest.raises(InsufficientPermissionsError):
            PermissionChecker.check_user_has_permission(user, Permission.USER_WRITE)

    def test_check_user_has_any_permission_success(self):
        """Test check passes when user has at least one permission."""
        role = Role(
            id=uuid4(),
            name="Reader",
            description="Reader",
            permissions=[Permission.USER_READ]
        )
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        # Should not raise
        PermissionChecker.check_user_has_any_permission(
            user,
            [Permission.USER_READ, Permission.USER_WRITE]
        )

    def test_check_user_has_any_permission_raises_error(self):
        """Test check raises error when user has none of permissions."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        with pytest.raises(InsufficientPermissionsError):
            PermissionChecker.check_user_has_any_permission(
                user,
                [Permission.USER_WRITE, Permission.ACCOUNT_WRITE]
            )

    def test_check_user_has_all_permissions_success(self):
        """Test check passes when user has all permissions."""
        role = Role(
            id=uuid4(),
            name="Editor",
            description="Editor",
            permissions=[Permission.USER_READ, Permission.USER_WRITE]
        )
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        # Should not raise
        PermissionChecker.check_user_has_all_permissions(
            user,
            [Permission.USER_READ, Permission.USER_WRITE]
        )

    def test_check_user_has_all_permissions_raises_error(self):
        """Test check raises error when user lacks any permission."""
        role = Role(
            id=uuid4(),
            name="Reader",
            description="Reader",
            permissions=[Permission.USER_READ]
        )
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        with pytest.raises(InsufficientPermissionsError):
            PermissionChecker.check_user_has_all_permissions(
                user,
                [Permission.USER_READ, Permission.USER_WRITE]
            )


class TestPermissionCheckerAccountAccess:
    """Test PermissionChecker account access checks."""

    def test_check_user_can_access_account_owner(self):
        """Test check passes for account owner."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        # Should not raise
        PermissionChecker.check_user_can_access_account(user, account)

    def test_check_user_can_access_account_shared(self):
        """Test check passes for shared account."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            shared_with_user_ids=[user_id]
        )
        # Should not raise
        PermissionChecker.check_user_can_access_account(user, account)

    def test_check_user_can_access_account_raises_error(self):
        """Test check raises error for unauthorized access."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        with pytest.raises(UnauthorizedAccessError):
            PermissionChecker.check_user_can_access_account(user, account)


class TestPermissionCheckerUserStatus:
    """Test PermissionChecker user status checks."""

    def test_check_user_is_active_success(self):
        """Test check passes for active user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_active=True
        )
        # Should not raise
        PermissionChecker.check_user_is_active(user)

    def test_check_user_is_active_raises_error(self):
        """Test check raises error for inactive user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_active=False
        )
        with pytest.raises(UnauthorizedAccessError):
            PermissionChecker.check_user_is_active(user)

    def test_check_user_is_admin_success(self):
        """Test check passes for admin user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=True
        )
        # Should not raise
        PermissionChecker.check_user_is_admin(user)

    def test_check_user_is_admin_raises_error(self):
        """Test check raises error for non-admin user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=False
        )
        with pytest.raises(InsufficientPermissionsError):
            PermissionChecker.check_user_is_admin(user)


class TestPermissionCheckerAccountStatus:
    """Test PermissionChecker account status checks."""

    def test_check_account_is_active_success(self):
        """Test check passes for active account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            is_active=True
        )
        # Should not raise
        PermissionChecker.check_account_is_active(account)

    def test_check_account_is_active_raises_error(self):
        """Test check raises error for inactive account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            is_active=False
        )
        with pytest.raises(UnauthorizedAccessError):
            PermissionChecker.check_account_is_active(account)


class TestPermissionCheckerAccountOperations:
    """Test PermissionChecker account operation checks."""

    def test_user_can_modify_account_owner(self):
        """Test owner can modify account."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        assert PermissionChecker.user_can_modify_account(user, account) is True

    def test_user_can_modify_account_non_owner(self):
        """Test non-owner cannot modify account."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        assert PermissionChecker.user_can_modify_account(user, account) is False

    def test_check_user_can_modify_account_raises_error(self):
        """Test check raises error for non-owner modification."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        with pytest.raises(UnauthorizedAccessError):
            PermissionChecker.check_user_can_modify_account(user, account)

    def test_check_user_can_delete_account_success(self):
        """Test owner can delete account."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        # Should not raise
        PermissionChecker.check_user_can_delete_account(user, account)

    def test_check_user_can_share_account_success(self):
        """Test owner can share account."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        # Should not raise
        PermissionChecker.check_user_can_share_account(user, account)
