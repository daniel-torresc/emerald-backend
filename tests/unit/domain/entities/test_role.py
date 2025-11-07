"""Unit tests for Role entity."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.entities.role import Role
from app.domain.value_objects.permission import Permission


class TestRoleCreation:
    """Test Role entity creation."""

    def test_create_role_with_minimal_data(self):
        """Test creating role with minimal required data."""
        role_id = uuid4()
        role = Role(
            id=role_id,
            name="User",
            description="Standard user role"
        )
        assert role.id == role_id
        assert role.name == "User"
        assert role.description == "Standard user role"
        assert role.permissions == []
        assert role.is_system_role is False

    def test_create_role_with_permissions(self):
        """Test creating role with permissions."""
        role = Role(
            id=uuid4(),
            name="Editor",
            description="Can edit content",
            permissions=[Permission.USER_READ, Permission.USER_WRITE]
        )
        assert len(role.permissions) == 2
        assert Permission.USER_READ in role.permissions

    def test_create_system_role(self):
        """Test creating system role."""
        role = Role(
            id=uuid4(),
            name="Admin",
            description="Administrator",
            is_system_role=True
        )
        assert role.is_system_role is True

    def test_empty_name_raises_error(self):
        """Test empty name raises error."""
        with pytest.raises(ValueError) as exc_info:
            Role(id=uuid4(), name="", description="Test")
        assert "name cannot be empty" in str(exc_info.value)

    def test_name_too_long_raises_error(self):
        """Test name exceeding max length raises error."""
        with pytest.raises(ValueError):
            Role(id=uuid4(), name="x" * 101, description="Test")


class TestRolePermissions:
    """Test Role permission management."""

    def test_has_permission_true(self):
        """Test has_permission returns True for granted permission."""
        role = Role(
            id=uuid4(),
            name="Editor",
            description="Editor role",
            permissions=[Permission.USER_READ]
        )
        assert role.has_permission(Permission.USER_READ) is True

    def test_has_permission_false(self):
        """Test has_permission returns False for non-granted permission."""
        role = Role(
            id=uuid4(),
            name="Reader",
            description="Reader role",
            permissions=[Permission.USER_READ]
        )
        assert role.has_permission(Permission.USER_WRITE) is False

    def test_add_permission(self):
        """Test adding permission to role."""
        role = Role(id=uuid4(), name="Test", description="Test")
        role.add_permission(Permission.USER_READ)
        assert Permission.USER_READ in role.permissions

    def test_add_duplicate_permission_ignored(self):
        """Test adding duplicate permission is ignored."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ]
        )
        role.add_permission(Permission.USER_READ)
        assert role.permissions.count(Permission.USER_READ) == 1

    def test_remove_permission(self):
        """Test removing permission from role."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ, Permission.USER_WRITE]
        )
        role.remove_permission(Permission.USER_READ)
        assert Permission.USER_READ not in role.permissions
        assert Permission.USER_WRITE in role.permissions

    def test_remove_nonexistent_permission_ignored(self):
        """Test removing non-existent permission is ignored."""
        role = Role(id=uuid4(), name="Test", description="Test")
        role.remove_permission(Permission.USER_READ)  # Should not raise

    def test_grant_permissions(self):
        """Test granting multiple permissions."""
        role = Role(id=uuid4(), name="Test", description="Test")
        role.grant_permissions([Permission.USER_READ, Permission.USER_WRITE])
        assert len(role.permissions) == 2

    def test_revoke_permissions(self):
        """Test revoking multiple permissions."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ, Permission.USER_WRITE]
        )
        role.revoke_permissions([Permission.USER_READ])
        assert Permission.USER_READ not in role.permissions
        assert Permission.USER_WRITE in role.permissions


class TestRolePermissionChecks:
    """Test Role permission checking methods."""

    def test_has_any_permission_true(self):
        """Test has_any_permission returns True when role has one."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ]
        )
        assert role.has_any_permission([Permission.USER_READ, Permission.USER_WRITE]) is True

    def test_has_any_permission_false(self):
        """Test has_any_permission returns False when role has none."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ]
        )
        assert role.has_any_permission([Permission.ACCOUNT_READ, Permission.ACCOUNT_WRITE]) is False

    def test_has_all_permissions_true(self):
        """Test has_all_permissions returns True when role has all."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ, Permission.USER_WRITE]
        )
        assert role.has_all_permissions([Permission.USER_READ, Permission.USER_WRITE]) is True

    def test_has_all_permissions_false(self):
        """Test has_all_permissions returns False when role lacks one."""
        role = Role(
            id=uuid4(),
            name="Test",
            description="Test",
            permissions=[Permission.USER_READ]
        )
        assert role.has_all_permissions([Permission.USER_READ, Permission.USER_WRITE]) is False

    def test_is_admin_role_true(self):
        """Test is_admin_role returns True for admin."""
        role = Role(
            id=uuid4(),
            name="Admin",
            description="Admin",
            permissions=[Permission.ADMIN_FULL_ACCESS]
        )
        assert role.is_admin_role() is True

    def test_is_admin_role_false(self):
        """Test is_admin_role returns False for non-admin."""
        role = Role(
            id=uuid4(),
            name="User",
            description="User",
            permissions=[Permission.USER_READ]
        )
        assert role.is_admin_role() is False


class TestRoleEquality:
    """Test Role equality and hashing."""

    def test_roles_with_same_id_are_equal(self):
        """Test roles with same ID are equal."""
        role_id = uuid4()
        role1 = Role(id=role_id, name="Test1", description="Test")
        role2 = Role(id=role_id, name="Test2", description="Test")
        assert role1 == role2

    def test_roles_with_different_ids_not_equal(self):
        """Test roles with different IDs are not equal."""
        role1 = Role(id=uuid4(), name="Test", description="Test")
        role2 = Role(id=uuid4(), name="Test", description="Test")
        assert role1 != role2

    def test_role_hash(self):
        """Test role can be hashed."""
        role = Role(id=uuid4(), name="Test", description="Test")
        hash_value = hash(role)
        assert isinstance(hash_value, int)

    def test_roles_can_be_used_in_set(self):
        """Test roles can be used in sets."""
        role_id = uuid4()
        role1 = Role(id=role_id, name="Test", description="Test")
        role2 = Role(id=role_id, name="Test", description="Test")
        role3 = Role(id=uuid4(), name="Other", description="Test")
        role_set = {role1, role2, role3}
        assert len(role_set) == 2


class TestRoleStringRepresentation:
    """Test Role string representation."""

    def test_repr_contains_role_info(self):
        """Test __repr__ contains role information."""
        role = Role(
            id=uuid4(),
            name="Editor",
            description="Editor role",
            permissions=[Permission.USER_READ]
        )
        repr_str = repr(role)
        assert "Role" in repr_str
        assert "Editor" in repr_str
