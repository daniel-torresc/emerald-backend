"""Unit tests for Permission value object."""

import pytest

from app.domain.value_objects.permission import Permission


class TestPermission:
    """Test Permission enum."""

    def test_permission_values(self):
        """Test permission enum values."""
        assert Permission.USER_READ.value == "user:read"
        assert Permission.ACCOUNT_WRITE.value == "account:write"
        assert Permission.ADMIN_FULL_ACCESS.value == "admin:full_access"

    def test_str_returns_value(self):
        """Test __str__ returns permission value."""
        assert str(Permission.USER_READ) == "user:read"

    def test_resource_property(self):
        """Test resource property extracts resource name."""
        assert Permission.USER_READ.resource == "user"
        assert Permission.ACCOUNT_WRITE.resource == "account"
        assert Permission.ADMIN_FULL_ACCESS.resource == "admin"

    def test_action_property(self):
        """Test action property extracts action."""
        assert Permission.USER_READ.action == "read"
        assert Permission.ACCOUNT_WRITE.action == "write"
        assert Permission.ADMIN_FULL_ACCESS.action == "full_access"

    def test_is_admin_permission(self):
        """Test is_admin_permission method."""
        assert Permission.ADMIN_FULL_ACCESS.is_admin_permission() is True
        assert Permission.ROLE_MANAGE.is_admin_permission() is True
        assert Permission.USER_READ.is_admin_permission() is False

    def test_from_string_valid(self):
        """Test from_string with valid permission."""
        perm = Permission.from_string("user:read")
        assert perm == Permission.USER_READ

    def test_from_string_invalid_raises_error(self):
        """Test from_string with invalid permission raises error."""
        with pytest.raises(ValueError):
            Permission.from_string("invalid:permission")

    def test_all_permissions(self):
        """Test all_permissions returns all permissions."""
        all_perms = Permission.all_permissions()
        assert len(all_perms) > 0
        assert Permission.USER_READ in all_perms

    def test_user_permissions(self):
        """Test user_permissions returns only user permissions."""
        user_perms = Permission.user_permissions()
        assert Permission.USER_READ in user_perms
        assert Permission.USER_WRITE in user_perms
        assert Permission.ACCOUNT_READ not in user_perms

    def test_account_permissions(self):
        """Test account_permissions returns only account permissions."""
        account_perms = Permission.account_permissions()
        assert Permission.ACCOUNT_READ in account_perms
        assert Permission.ACCOUNT_WRITE in account_perms
        assert Permission.USER_READ not in account_perms

    def test_admin_permissions(self):
        """Test admin_permissions returns only admin permissions."""
        admin_perms = Permission.admin_permissions()
        assert Permission.ADMIN_FULL_ACCESS in admin_perms
        assert Permission.ROLE_MANAGE in admin_perms
        assert Permission.USER_READ not in admin_perms
