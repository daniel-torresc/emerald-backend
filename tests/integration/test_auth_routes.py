"""
Integration tests for authentication routes.

Tests cover:
- User registration
- User login
- Token refresh
- User logout
- Password change
- Error cases and validation
"""

import pytest
from httpx import AsyncClient

from src.models.user import User


# ============================================================================
# Registration Tests
# ============================================================================
class TestRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "NewPass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["is_admin"] is False
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test registration with duplicate email fails."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "testuser@example.com",  # Already exists
                "username": "differentuser",
                "password": "NewPass123!",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "ALREADY_EXISTS"
        assert "email" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test registration with duplicate username fails."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "different@example.com",
                "username": "testuser",  # Already exists
                "password": "NewPass123!",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "ALREADY_EXISTS"
        assert "username" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password fails."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "weak",  # Too weak
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",  # Invalid format
                "username": "newuser",
                "password": "NewPass123!",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


# ============================================================================
# Login Tests
# ============================================================================
class TestLogin:
    """Test user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 900  # 15 minutes in seconds

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, async_client: AsyncClient):
        """Test login with non-existent email fails."""
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test login with wrong password fails."""
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "WrongPass123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, async_client: AsyncClient, inactive_user: User
    ):
        """Test login with inactive account fails.

        Note: Soft-deleted users are filtered at the repository level,
        so they return INVALID_CREDENTIALS instead of INACTIVE_ACCOUNT.
        This is more secure as it doesn't leak account status information.
        """
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "InactivePass123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        # Soft-deleted users are filtered at repository level
        assert data["error"]["code"] == "INVALID_CREDENTIALS"


# ============================================================================
# Token Refresh Tests
# ============================================================================
class TestTokenRefresh:
    """Test token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, async_client: AsyncClient, user_token: dict):
        """Test successful token refresh."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": user_token["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # New tokens should be different from old ones
        assert data["access_token"] != user_token["access_token"]
        assert data["refresh_token"] != user_token["refresh_token"]

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_refresh_access_token_fails(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test refresh with access token (wrong type) fails."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": user_token["access_token"]},  # Wrong token type
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_detection(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that reusing a refresh token revokes the entire token family."""
        # First refresh - should succeed
        response1 = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": user_token["refresh_token"]},
        )
        assert response1.status_code == 200

        # Try to reuse the old refresh token - should fail with reuse detection
        response2 = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": user_token["refresh_token"]},
        )
        assert response2.status_code == 401
        data = response2.json()
        assert data["error"]["code"] == "INVALID_TOKEN"


# ============================================================================
# Logout Tests
# ============================================================================
class TestLogout:
    """Test user logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, user_token: dict):
        """Test successful logout."""
        response = await async_client.post(
            "/api/auth/logout",
            json={"refresh_token": user_token["refresh_token"]},
        )

        assert response.status_code == 204

        # Try to use the refresh token after logout - should fail
        response2 = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": user_token["refresh_token"]},
        )
        assert response2.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, async_client: AsyncClient):
        """Test logout with invalid token fails."""
        response = await async_client.post(
            "/api/auth/logout",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401


# ============================================================================
# Password Change Tests
# ============================================================================
class TestPasswordChange:
    """Test password change endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, async_client: AsyncClient, test_user: User, user_token: dict
    ):
        """Test successful password change."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewTestPass456!",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 204

        # Login with new password should work
        login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "NewTestPass456!",
            },
        )
        assert login_response.status_code == 200

        # Old refresh token should be revoked
        refresh_response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": user_token["refresh_token"]},
        )
        assert refresh_response.status_code == 401

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test password change with wrong current password fails."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPass123!",
                "new_password": "NewTestPass456!",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_change_password_weak_new_password(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test password change with weak new password fails."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "weak",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_change_password_unauthenticated(self, async_client: AsyncClient):
        """Test password change without authentication fails."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewTestPass456!",
            },
        )

        assert response.status_code == 401


# ============================================================================
# Authorization Tests
# ============================================================================
class TestAuthorization:
    """Test authorization and access control."""

    @pytest.mark.asyncio
    async def test_access_with_valid_token(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that valid access token works for protected endpoints."""
        # Password change endpoint requires authentication
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewTestPass456!",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Should not be 401 (though it might be 400 for wrong password)
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_access_without_token(self, async_client: AsyncClient):
        """Test that protected endpoints reject requests without token."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewTestPass456!",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_with_invalid_token(self, async_client: AsyncClient):
        """Test that protected endpoints reject invalid tokens."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewTestPass456!",
            },
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401


# ============================================================================
# Integration Flow Tests
# ============================================================================
class TestAuthenticationFlows:
    """Test complete authentication flows."""

    @pytest.mark.asyncio
    async def test_full_user_lifecycle(self, async_client: AsyncClient):
        """Test complete user lifecycle: register → login → refresh → logout."""
        # 1. Register
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "lifecycle@example.com",
                "username": "lifecycleuser",
                "password": "LifeCycle123!",
            },
        )
        assert register_response.status_code == 201

        # 2. Login
        login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "lifecycle@example.com",
                "password": "LifeCycle123!",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()

        # 3. Refresh token
        refresh_response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()

        # 4. Logout
        logout_response = await async_client.post(
            "/api/auth/logout",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert logout_response.status_code == 204

        # 5. Verify token is revoked
        refresh_after_logout = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert refresh_after_logout.status_code == 401

    @pytest.mark.asyncio
    async def test_password_change_flow(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test password change flow: login → change password → login with new password."""
        # 1. Login with old password
        login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123!",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()

        # 2. Change password
        change_response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "ChangedPass456!",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert change_response.status_code == 204

        # 3. Old password should not work
        old_login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123!",
            },
        )
        assert old_login_response.status_code == 401

        # 4. New password should work
        new_login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "ChangedPass456!",
            },
        )
        assert new_login_response.status_code == 200
