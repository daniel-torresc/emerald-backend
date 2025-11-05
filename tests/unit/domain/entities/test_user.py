"""Unit tests for User entity."""

from uuid import uuid4

import pytest

from app.domain.entities.account import Account
from app.domain.entities.role import Role
from app.domain.entities.user import User
from app.domain.exceptions import InvalidUserStateTransitionError
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.email import Email
from app.domain.value_objects.money import Money
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.permission import Permission
from app.domain.value_objects.username import Username


class TestUserCreation:
    """Test User entity creation."""

    def test_create_user_minimal(self):
        """Test creating user with minimal data."""
        user_id = uuid4()
        email = Email("test@example.com")
        username = Username("testuser")
        password_hash = PasswordHash("$2b$12$" + "x" * 50)

        user = User(
            id=user_id,
            email=email,
            username=username,
            password_hash=password_hash,
            full_name="Test User"
        )

        assert user.id == user_id
        assert user.email == email
        assert user.username == username
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_admin is False
        assert len(user.roles) == 0

    def test_empty_full_name_raises_error(self):
        """Test empty full name raises error."""
        with pytest.raises(ValueError):
            User(
                id=uuid4(),
                email=Email("test@example.com"),
                username=Username("testuser"),
                password_hash=PasswordHash("$2b$12$" + "x" * 50),
                full_name=""
            )

    def test_full_name_too_long_raises_error(self):
        """Test full name exceeding max length raises error."""
        with pytest.raises(ValueError):
            User(
                id=uuid4(),
                email=Email("test@example.com"),
                username=Username("testuser"),
                password_hash=PasswordHash("$2b$12$" + "x" * 50),
                full_name="x" * 201
            )


class TestUserActivation:
    """Test User activation/deactivation."""

    def test_activate_inactive_user(self):
        """Test activating an inactive user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_active=False
        )
        user.activate()
        assert user.is_active is True

    def test_activate_already_active_raises_error(self):
        """Test activating already active user raises error."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_active=True
        )
        with pytest.raises(InvalidUserStateTransitionError):
            user.activate()

    def test_deactivate_active_user(self):
        """Test deactivating an active user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_active=True
        )
        user.deactivate()
        assert user.is_active is False

    def test_deactivate_already_inactive_raises_error(self):
        """Test deactivating already inactive user raises error."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_active=False
        )
        with pytest.raises(InvalidUserStateTransitionError):
            user.deactivate()


class TestUserAdminPrivileges:
    """Test User admin privilege management."""

    def test_make_admin(self):
        """Test granting admin privileges."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=False
        )
        user.make_admin()
        assert user.is_admin is True

    def test_make_admin_already_admin_raises_error(self):
        """Test making already admin user raises error."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=True
        )
        with pytest.raises(InvalidUserStateTransitionError):
            user.make_admin()

    def test_revoke_admin(self):
        """Test revoking admin privileges."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=True
        )
        user.revoke_admin()
        assert user.is_admin is False

    def test_revoke_admin_not_admin_raises_error(self):
        """Test revoking admin from non-admin raises error."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=False
        )
        with pytest.raises(InvalidUserStateTransitionError):
            user.revoke_admin()


class TestUserUpdates:
    """Test User update methods."""

    def test_change_password(self):
        """Test changing user password."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        new_hash = PasswordHash("$2b$12$" + "y" * 50)
        user.change_password(new_hash)
        assert user.password_hash == new_hash

    def test_update_full_name(self):
        """Test updating full name."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Old Name"
        )
        user.update_full_name("New Name")
        assert user.full_name == "New Name"

    def test_update_email(self):
        """Test updating email."""
        user = User(
            id=uuid4(),
            email=Email("old@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        new_email = Email("new@example.com")
        user.update_email(new_email)
        assert user.email == new_email

    def test_update_username(self):
        """Test updating username."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("olduser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        new_username = Username("newuser")
        user.update_username(new_username)
        assert user.username == new_username

    def test_record_login(self):
        """Test recording user login."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        user.record_login()
        assert user.last_login_at is not None


class TestUserRoles:
    """Test User role management."""

    def test_add_role(self):
        """Test adding role to user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        role = Role(id=uuid4(), name="Editor", description="Editor role")
        user.add_role(role)
        assert role in user.roles

    def test_add_duplicate_role_raises_error(self):
        """Test adding duplicate role raises error."""
        role = Role(id=uuid4(), name="Editor", description="Editor role")
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        with pytest.raises(ValueError):
            user.add_role(role)

    def test_remove_role(self):
        """Test removing role from user."""
        role = Role(id=uuid4(), name="Editor", description="Editor role")
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        user.remove_role(role)
        assert role not in user.roles

    def test_has_role_true(self):
        """Test has_role returns True when user has role."""
        role = Role(id=uuid4(), name="Editor", description="Editor role")
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role]
        )
        assert user.has_role("Editor") is True

    def test_has_role_false(self):
        """Test has_role returns False when user lacks role."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        assert user.has_role("Editor") is False


class TestUserPermissions:
    """Test User permission checking."""

    def test_has_permission_admin_always_true(self):
        """Test admin user has all permissions."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=True
        )
        assert user.has_permission(Permission.USER_READ) is True
        assert user.has_permission(Permission.ACCOUNT_DELETE) is True

    def test_has_permission_through_role(self):
        """Test user has permission through role."""
        role = Role(
            id=uuid4(),
            name="Editor",
            description="Editor role",
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
        assert user.has_permission(Permission.USER_READ) is True
        assert user.has_permission(Permission.USER_WRITE) is True

    def test_has_permission_false(self):
        """Test user lacks permission."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        assert user.has_permission(Permission.USER_WRITE) is False

    def test_get_all_permissions_admin(self):
        """Test get_all_permissions for admin returns all."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            is_admin=True
        )
        perms = user.get_all_permissions()
        assert len(perms) > 0
        assert Permission.USER_READ in perms

    def test_get_all_permissions_from_roles(self):
        """Test get_all_permissions aggregates from all roles."""
        role1 = Role(
            id=uuid4(),
            name="Role1",
            description="Role 1",
            permissions=[Permission.USER_READ]
        )
        role2 = Role(
            id=uuid4(),
            name="Role2",
            description="Role 2",
            permissions=[Permission.ACCOUNT_READ]
        )
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User",
            roles=[role1, role2]
        )
        perms = user.get_all_permissions()
        assert Permission.USER_READ in perms
        assert Permission.ACCOUNT_READ in perms


class TestUserAccountAccess:
    """Test User account access checking."""

    def test_can_access_owned_account(self):
        """Test user can access owned account."""
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
        assert user.can_access_account(account) is True

    def test_can_access_shared_account(self):
        """Test user can access shared account."""
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
        assert user.can_access_account(account) is True


class TestUserDeletion:
    """Test User soft deletion."""

    def test_soft_delete(self):
        """Test soft deleting user."""
        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Test User"
        )
        user.soft_delete()
        assert user.is_deleted() is True
        assert user.deleted_at is not None
        assert user.is_active is False


class TestUserEquality:
    """Test User equality."""

    def test_users_with_same_id_are_equal(self):
        """Test users with same ID are equal."""
        user_id = uuid4()
        user1 = User(
            id=user_id,
            email=Email("test1@example.com"),
            username=Username("user1"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="User One"
        )
        user2 = User(
            id=user_id,
            email=Email("test2@example.com"),
            username=Username("user2"),
            password_hash=PasswordHash("$2b$12$" + "y" * 50),
            full_name="User Two"
        )
        assert user1 == user2
