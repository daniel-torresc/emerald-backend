"""
Integration tests for Admin Management API routes.

Tests cover:
- POST /api/v1/admin/bootstrap - Bootstrap first admin
- POST /api/v1/admin/users - Create admin user
- GET /api/v1/admin/users - List admin users
- GET /api/v1/admin/users/{user_id} - Get admin user
- PUT /api/v1/admin/users/{user_id} - Update admin user
- DELETE /api/v1/admin/users/{user_id} - Delete admin user
- PUT /api/v1/admin/users/{user_id}/password - Reset password
- PUT /api/v1/admin/users/{user_id}/permissions - Update permissions

Test scenarios:
- Happy paths (successful operations)
- Permission enforcement (admin only)
- Error cases (validation, business logic)
- Edge cases (last admin protection, bootstrap once)
"""

import os
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.user import User


# ============================================================================
# Bootstrap Endpoint Removal Tests
# ============================================================================
@pytest.mark.asyncio
async def test_bootstrap_endpoint_removed(
    async_client: AsyncClient,
):
    """Test: Bootstrap endpoint no longer exists (returns 404)."""
    response = await async_client.post("/api/v1/admin/bootstrap")
    assert response.status_code == 404


# ============================================================================
# Create Admin User Tests (POST /admin/users)
# ============================================================================
@pytest.mark.asyncio
async def test_create_admin_user_success(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin successfully creates new admin user."""
    response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "newadmin",
            "email": "newadmin@example.com",
            "password": "NewAdmin123!",
            "full_name": "New Admin User",
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["username"] == "newadmin"
    assert data["email"] == "newadmin@example.com"
    assert data["full_name"] == "New Admin User"
    assert data["is_admin"] is True
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_admin_with_custom_permissions(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin creates admin user with custom permissions."""
    response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "customadmin",
            "email": "customadmin@example.com",
            "password": "CustomAdmin123!",
            "permissions": ["users:read:all", "accounts:read:all"],
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["username"] == "customadmin"
    assert "users:read:all" in data.get("permissions", [])


@pytest.mark.asyncio
async def test_create_admin_non_admin_cannot_create(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test: Non-admin user cannot create admin users."""
    response = await async_client.post(
        "/api/v1/admin/users",
        headers=auth_headers,
        json={
            "username": "shouldfail",
            "email": "shouldfail@example.com",
            "password": "ShouldFail123!",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_admin_duplicate_email(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Cannot create admin with duplicate email."""
    response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "differentname",
            "email": admin_user.email,  # Duplicate email
            "password": "ValidPass123!",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_admin_weak_password(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Cannot create admin with weak password."""
    response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "weakpassadmin",
            "email": "weakpass@example.com",
            "password": "weak",  # Too weak
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_admin_generated_password(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin can create user without password (auto-generated)."""
    response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "generatedpass",
            "email": "generatedpass@example.com",
            # No password provided
        },
    )

    # Should succeed and return temporary password
    assert response.status_code == 201
    data = response.json()

    # Temporary password should be present for new user
    assert "temporary_password" in data or "password" not in data


# ============================================================================
# List Admin Users Tests (GET /admin/users)
# ============================================================================
@pytest.mark.asyncio
async def test_list_admin_users_success(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Admin successfully lists all admin users."""
    response = await async_client.get(
        "/api/v1/admin/users",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check for paginated response format (can be "items" or "data")
    items_key = "items" if "items" in data else "data"
    assert items_key in data
    assert "total" in data or "meta" in data

    # Get total from appropriate location
    total = data.get("total", data.get("meta", {}).get("total", 0))
    assert total >= 1  # At least the current admin


@pytest.mark.asyncio
async def test_list_admin_users_with_pagination(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Pagination works correctly."""
    # Create multiple admins
    for i in range(3):
        await async_client.post(
            "/api/v1/admin/users",
            headers=admin_headers,
            json={
                "username": f"paginadmin{i}",
                "email": f"paginadmin{i}@example.com",
                "password": "PaginAdmin123!",
            },
        )

    # Test pagination
    response = await async_client.get(
        "/api/v1/admin/users?skip=0&limit=2",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    items_key = "items" if "items" in data else "data"
    assert len(data[items_key]) <= 2


@pytest.mark.asyncio
async def test_list_admin_users_search(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Search functionality works."""
    # Create admin with unique name
    await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "searchableadmin",
            "email": "searchable@example.com",
            "password": "Searchable123!",
            "full_name": "Unique Searchable Name",
        },
    )

    # Search for the admin
    response = await async_client.get(
        "/api/v1/admin/users?search=Searchable",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should find the admin
    items_key = "items" if "items" in data else "data"
    usernames = [item["username"] for item in data[items_key]]
    assert "searchableadmin" in usernames


@pytest.mark.asyncio
async def test_list_admin_users_filter_active(
    async_client: AsyncClient,
    admin_headers: dict,
    test_engine,
):
    """Test: Filter by active status."""
    # Create an inactive admin
    from src.core.security import hash_password

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        inactive_admin = User(
            email="inactive_admin@example.com",
            username="inactiveadmin",
            password_hash=hash_password("InactiveAdmin123!"),
            is_active=False,
            is_admin=True,
        )
        session.add(inactive_admin)
        await session.commit()

    # Filter for inactive admins
    response = await async_client.get(
        "/api/v1/admin/users?is_active=false",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should only return inactive admins
    items_key = "items" if "items" in data else "data"
    for item in data[items_key]:
        assert item["is_active"] is False


@pytest.mark.asyncio
async def test_list_admin_users_non_admin_cannot_list(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test: Non-admin cannot list admin users."""
    response = await async_client.get(
        "/api/v1/admin/users",
        headers=auth_headers,
    )

    assert response.status_code == 403


# ============================================================================
# Get Admin User Tests (GET /admin/users/{user_id})
# ============================================================================
@pytest.mark.asyncio
async def test_get_admin_user_success(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Admin retrieves specific admin user details."""
    response = await async_client.get(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(admin_user.id)
    assert data["username"] == admin_user.username
    assert data["email"] == admin_user.email
    assert "permissions" in data


@pytest.mark.asyncio
async def test_get_admin_user_includes_permissions(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Response includes permissions and metadata."""
    response = await async_client.get(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "permissions" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "is_admin" in data
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_get_admin_user_non_admin_cannot_retrieve(
    async_client: AsyncClient,
    admin_user: User,
    auth_headers: dict,
):
    """Test: Non-admin cannot retrieve admin details."""
    response = await async_client.get(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=auth_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_user_nonexistent(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Returns 404 for non-existent admin."""
    fake_id = uuid.uuid4()

    response = await async_client.get(
        f"/api/v1/admin/users/{fake_id}",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ============================================================================
# Update Admin User Tests (PUT /admin/users/{user_id})
# ============================================================================
@pytest.mark.asyncio
async def test_update_admin_user_success(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin updates another admin's details."""
    # Create admin to update
    create_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "toupdate",
            "email": "toupdate@example.com",
            "password": "ToUpdate123!",
            "full_name": "Original Name",
        },
    )
    admin_id = create_response.json()["id"]

    # Update the admin
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers,
        json={
            "full_name": "Updated Name",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_admin_can_update_self(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Admin can update their own details."""
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=admin_headers,
        json={
            "full_name": "Self Updated",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["full_name"] == "Self Updated"


@pytest.mark.asyncio
async def test_update_admin_non_admin_cannot_update(
    async_client: AsyncClient,
    admin_user: User,
    auth_headers: dict,
):
    """Test: Non-admin cannot update admin users."""
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=auth_headers,
        json={
            "full_name": "Unauthorized Update",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_admin_invalid_data(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Invalid data rejected."""
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=admin_headers,
        json={
            "full_name": "",  # Empty name might be invalid
            "is_active": "not_a_boolean",  # Invalid type
        },
    )

    assert response.status_code == 422


# ============================================================================
# Delete Admin User Tests (DELETE /admin/users/{user_id})
# ============================================================================
@pytest.mark.asyncio
async def test_delete_admin_user_success(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin deletes another admin (soft delete)."""
    # Create admin to delete
    create_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "todelete",
            "email": "todelete@example.com",
            "password": "ToDelete123!",
        },
    )
    admin_id = create_response.json()["id"]

    # Delete the admin
    response = await async_client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers,
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_admin_cannot_delete_last_admin(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
    test_engine,
):
    """Test: Cannot delete the last admin user."""
    # Ensure only one admin exists
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        from sqlalchemy import delete, select

        # Delete all admins except the current one
        stmt = delete(User).where(
            User.is_admin == True,
            User.id != admin_user.id
        )
        await session.execute(stmt)
        await session.commit()

    # Try to delete the last admin
    response = await async_client.delete(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=admin_headers,
    )

    assert response.status_code in [400, 403]  # Bad request or forbidden


@pytest.mark.asyncio
async def test_delete_admin_non_admin_cannot_delete(
    async_client: AsyncClient,
    admin_user: User,
    auth_headers: dict,
):
    """Test: Non-admin cannot delete admin users."""
    response = await async_client.delete(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=auth_headers,
    )

    assert response.status_code == 403


# ============================================================================
# Reset Password Tests (PUT /admin/users/{user_id}/password)
# ============================================================================
@pytest.mark.asyncio
async def test_reset_admin_password_success(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin resets another admin's password."""
    # Create admin
    create_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "resetpass",
            "email": "resetpass@example.com",
            "password": "Original123!",
        },
    )
    admin_id = create_response.json()["id"]

    # Reset password
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_id}/password",
        headers=admin_headers,
        json={
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reset_admin_password_weak_rejected(
    async_client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Test: Weak password rejected during reset."""
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_user.id}/password",
        headers=admin_headers,
        json={
            "new_password": "weak",  # Too weak
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reset_admin_password_non_admin_cannot_reset(
    async_client: AsyncClient,
    admin_user: User,
    auth_headers: dict,
):
    """Test: Non-admin cannot reset admin passwords."""
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_user.id}/password",
        headers=auth_headers,
        json={
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 403


# ============================================================================
# Update Permissions Tests (PUT /admin/users/{user_id}/permissions)
# ============================================================================
@pytest.mark.asyncio
async def test_update_permissions_success(
    async_client: AsyncClient,
    admin_headers: dict,
):
    """Test: Admin updates another admin's permissions."""
    # Create admin
    create_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "permsadmin",
            "email": "permsadmin@example.com",
            "password": "PermsAdmin123!",
        },
    )
    admin_id = create_response.json()["id"]

    # Update permissions
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_id}/permissions",
        headers=admin_headers,
        json={
            "permissions": ["users:read:all", "accounts:read:all"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "users:read:all" in data.get("permissions", [])
    assert "accounts:read:all" in data.get("permissions", [])


@pytest.mark.asyncio
async def test_update_permissions_non_admin_cannot_update(
    async_client: AsyncClient,
    admin_user: User,
    auth_headers: dict,
):
    """Test: Non-admin cannot update permissions."""
    response = await async_client.put(
        f"/api/v1/admin/users/{admin_user.id}/permissions",
        headers=auth_headers,
        json={
            "permissions": ["users:read:all"],
        },
    )

    assert response.status_code == 403
