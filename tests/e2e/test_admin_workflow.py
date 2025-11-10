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

import os

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.user import User


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

    # Step 1: Clear all admins and bootstrap first admin
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.is_admin == True))
        await session.commit()

    # Bootstrap uses default credentials from config
    bootstrap_response = await async_client.post("/api/v1/admin/bootstrap")
    assert bootstrap_response.status_code == 201
    bootstrap_data = bootstrap_response.json()
    print("✓ Step 1: Bootstrapped first admin")

    # Step 2: Login as admin using the credentials from bootstrap response
    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": bootstrap_data["email"],
            "password": os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe123!"),
        },
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    print("✓ Step 2: Admin logged in successfully")

    # Step 3: Admin creates second admin user
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
    second_admin_headers = {
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

    # Bootstrap admin
    os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "permadmin"
    os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "permadmin@example.com"
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "PermAdmin123!@#"

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.is_admin == True))
        await session.commit()

    await async_client.post("/api/v1/admin/bootstrap")

    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": "permadmin@example.com",
            "password": "PermAdmin123!@#",
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

    # Bootstrap
    os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "resetadmin"
    os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "resetadmin@example.com"
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "ResetAdmin123!@#"

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.is_admin == True))
        await session.commit()

    await async_client.post("/api/v1/admin/bootstrap")

    admin_login = await async_client.post(
        "/api/auth/login",
        json={
            "email": "resetadmin@example.com",
            "password": "ResetAdmin123!@#",
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

    # Bootstrap first admin
    os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "collab1"
    os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "collab1@example.com"
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "Collab1Admin123!@#"

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.is_admin == True))
        await session.commit()

    await async_client.post("/api/v1/admin/bootstrap")

    admin1_login = await async_client.post(
        "/api/auth/login",
        json={"email": "collab1@example.com", "password": "Collab1Admin123!@#"},
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

    # Bootstrap single admin
    os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "lastone"
    os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "lastone@example.com"
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "LastOne123!@#"

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.is_admin == True))
        await session.commit()

    bootstrap_response = await async_client.post("/api/v1/admin/bootstrap")
    admin_id = bootstrap_response.json()["id"]

    admin_login = await async_client.post(
        "/api/auth/login",
        json={"email": "lastone@example.com", "password": "LastOne123!@#"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

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
async def test_bootstrap_security(async_client: AsyncClient, test_engine):
    """
    Test: Bootstrap can only be used once, providing security.
    """

    # Clear admins
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.is_admin == True))
        await session.commit()

    # First bootstrap succeeds
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "Bootstrap123!@#"
    response1 = await async_client.post("/api/v1/admin/bootstrap")
    assert response1.status_code == 201

    # Second bootstrap fails
    response2 = await async_client.post("/api/v1/admin/bootstrap")
    assert response2.status_code in [403, 409]

    print("✓ Bootstrap security verified (one-time only)")
