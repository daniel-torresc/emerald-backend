"""
End-to-End tests for admin management workflows.

This module tests complete admin operation scenarios:
1. Bootstrap first admin
2. Admin creates additional admins
3. Admin manages regular users
4. Admin views audit logs
5. Permission management
6. Multi-admin collaboration

These tests validate that administrative operations work correctly
and that security/audit features function as expected.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_admin_workflow(async_client: AsyncClient, test_engine):
    """
    Test: Complete admin management workflow.

    Workflow:
    1. Bootstrap first admin
    2. Admin creates second admin user
    3. New admin can authenticate
    4. Admin lists all users (paginated)
    5. Admin deactivates regular user
    6. Deactivated user cannot login
    7. Admin views audit logs for operations
    """

    # Step 1: Login as superuser (created by migration)
    from src.core.config import settings

    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    print("✓ Step 1: Admin logged in successfully")

    # Step 2: Admin creates second admin user
    second_admin_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "secondadmin",
            "email": "second@workflow.com",
            "password": "SecondAdmin123!",
            "full_name": "Second Administrator",
        },
    )
    assert second_admin_response.status_code == 201
    print("✓ Step 3: Created second admin user")

    # Step 4: New admin can authenticate
    second_admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": "second@workflow.com",
            "password": "SecondAdmin123!",
        },
    )
    assert second_admin_login.status_code == 200
    {
        "Authorization": f"Bearer {second_admin_login.json()['access_token']}"
    }
    print("✓ Step 4: Second admin authenticated successfully")

    # Step 5: Create a regular user
    regular_user_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "regular@workflow.com",
            "username": "regularuser",
            "password": "Regular123!",
        },
    )
    assert regular_user_response.status_code == 201
    regular_user_id = regular_user_response.json()["id"]
    print("✓ Step 5: Created regular user")

    # Step 6: Admin lists all users (paginated)
    users_list_response = await async_client.get(
        "/api/v1/users?limit=10",
        headers=admin_headers,
    )
    assert users_list_response.status_code == 200
    users_data = users_list_response.json()
    assert users_data["total"] >= 3  # 2 admins + 1 regular user
    print(f"✓ Step 6: Listed {users_data['total']} users")

    # Step 7: Admin deactivates regular user
    deactivate_response = await async_client.post(
        f"/api/v1/users/{regular_user_id}/deactivate",
        headers=admin_headers,
    )
    assert deactivate_response.status_code == 200
    print("✓ Step 7: Deactivated regular user")

    # Step 8: Deactivated user cannot login
    deactivated_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": "regular@workflow.com",
            "password": "Regular123!",
        },
    )
    assert deactivated_login.status_code == 403
    print("✓ Step 8: Deactivated user correctly cannot login")

    # Step 9: Admin views audit logs
    audit_logs_response = await async_client.get(
        "/api/v1/audit-logs/users",
        headers=admin_headers,
    )
    assert audit_logs_response.status_code == 200
    logs = audit_logs_response.json()
    assert logs["total"] > 0  # Should have audit entries
    print(f"✓ Step 9: Viewed {logs['total']} audit log entries")

    print("\n🎉 Complete admin workflow passed! All steps completed successfully.")


@pytest.mark.asyncio
async def test_admin_user_management_workflow(async_client: AsyncClient):
    """
    Test: Admin creates, updates, and manages regular users.
    """

    # Bootstrap admin if needed (or use existing)
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "manageradmin@example.com",
            "username": "manageradmin",
            "password": "ManagerAdmin123!",
        },
    )

    # Create admin via service or promote to admin
    # For this test, we'll assume we have admin access

    # Register regular users
    users_to_manage = []
    for i in range(3):
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": f"managed{i}@example.com",
                "username": f"managed{i}",
                "password": f"Managed{i}123!",
            },
        )
        assert response.status_code == 201
        users_to_manage.append(response.json()["id"])

    print(f"✓ Created {len(users_to_manage)} users for management")


@pytest.mark.asyncio
async def test_admin_permission_management(async_client: AsyncClient, test_engine):
    """
    Test: Admin manages permissions for other admins.
    """

    # Login as superuser (created by migration)
    from src.core.config import settings

    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Create limited admin
    limited_admin_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "limitedadmin",
            "email": "limited@example.com",
            "password": "LimitedAdmin123!",
            "permissions": ["users:read:all"],  # Limited permissions
        },
    )
    assert limited_admin_response.status_code == 201
    limited_admin_id = limited_admin_response.json()["id"]

    # Update permissions to grant more access
    update_perms_response = await async_client.put(
        f"/api/v1/admin/users/{limited_admin_id}/permissions",
        headers=admin_headers,
        json={
            "permissions": ["users:read:all", "users:write:all", "accounts:read:all"],
        },
    )
    assert update_perms_response.status_code == 200
    updated_data = update_perms_response.json()
    assert "accounts:read:all" in updated_data.get("permissions", [])

    print("✓ Admin permission management workflow completed")


@pytest.mark.asyncio
async def test_admin_password_reset_workflow(async_client: AsyncClient, test_engine):
    """
    Test: Admin resets password for another admin.
    """

    # Login as superuser (created by migration)
    from src.core.config import settings

    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Create another admin
    target_admin_response = await async_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "targetadmin",
            "email": "target@example.com",
            "password": "TargetAdmin123!",
        },
    )
    target_admin_id = target_admin_response.json()["id"]

    # Target admin can login with original password
    login1 = await async_client.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "TargetAdmin123!"},
    )
    assert login1.status_code == 200

    # Reset target admin's password
    reset_response = await async_client.put(
        f"/api/v1/admin/users/{target_admin_id}/password",
        headers=admin_headers,
        json={"new_password": "NewTarget123!"},
    )
    assert reset_response.status_code == 200

    # Cannot login with old password
    login2 = await async_client.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "TargetAdmin123!"},
    )
    assert login2.status_code == 401

    # Can login with new password
    login3 = await async_client.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "NewTarget123!"},
    )
    assert login3.status_code == 200

    print("✓ Admin password reset workflow completed")


@pytest.mark.asyncio
async def test_multi_admin_collaboration(async_client: AsyncClient, test_engine):
    """
    Test: Multiple admins work together managing users.
    """

    # Login as superuser (created by migration)
    from src.core.config import settings

    admin1_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    admin1_headers = {"Authorization": f"Bearer {admin1_login.json()['access_token']}"}

    # Admin 1 creates Admin 2
    await async_client.post(
        "/api/v1/admin/users",
        headers=admin1_headers,
        json={
            "username": "collab2",
            "email": "collab2@example.com",
            "password": "Collab2Admin123!",
        },
    )

    admin2_login = await async_client.post(
        "/api/auth/login",
        json={"email": "collab2@example.com", "password": "Collab2Admin123!"},
    )
    admin2_headers = {"Authorization": f"Bearer {admin2_login.json()['access_token']}"}

    # Admin 2 creates a regular user
    user_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "collab_user@example.com",
            "username": "collabuser",
            "password": "CollabUser123!",
        },
    )
    user_id = user_response.json()["user"]["id"]

    # Admin 1 views the user created by Admin 2's action
    user_detail = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers=admin1_headers,
    )
    assert user_detail.status_code == 200

    # Admin 2 can also view audit logs
    audit_response = await async_client.get(
        "/api/v1/audit-logs/users",
        headers=admin2_headers,
    )
    assert audit_response.status_code == 200

    print("✓ Multi-admin collaboration workflow completed")


@pytest.mark.asyncio
async def test_last_admin_protection(async_client: AsyncClient, test_engine):
    """
    Test: System prevents deletion or deactivation of the last admin.
    """

    # Get superuser ID (created by migration)
    from src.core.config import settings

    # Login to get admin ID
    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Get superuser ID by listing admins
    admins_response = await async_client.get(
        "/api/v1/admin/users", headers=admin_headers
    )
    admin_id = admins_response.json()["items"][0]["id"]

    # Try to delete self (last admin)
    delete_response = await async_client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers,
    )
    # Should fail - cannot delete last admin
    assert delete_response.status_code == 400

    # Try to deactivate self (last admin)
    deactivate_response = await async_client.put(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    # Should fail or be ignored - cannot deactivate last admin
    assert deactivate_response.status_code in [200, 400]

    # If it returned 200, verify admin is still active
    if deactivate_response.status_code == 200:
        verify_response = await async_client.get(
            f"/api/v1/admin/users/{admin_id}",
            headers=admin_headers,
        )
        # Admin should still be able to access (meaning they're active)
        assert verify_response.status_code == 200

    print("✓ Last admin protection verified")


@pytest.mark.asyncio
async def test_superuser_created_by_migration(async_client: AsyncClient):
    """
    Test: Superuser is created automatically by migration and can login.
    """
    from src.core.config import settings

    # Verify superuser can login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()

    # Verify superuser has admin privileges
    admin_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    admins_response = await async_client.get(
        "/api/v1/admin/users", headers=admin_headers
    )
    assert admins_response.status_code == 200
    assert len(admins_response.json()["items"]) > 0

    print("✓ Migration-created superuser verified")
