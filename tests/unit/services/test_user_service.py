"""
Unit tests for UserService.

All tests are fully mocked - no database or external dependencies.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import (
    AlreadyExistsError,
    InsufficientPermissionsError,
    NotFoundError,
)
from src.models.audit_log import AuditAction
from src.models.user import User
from src.schemas.common import PaginationParams
from src.schemas.user import UserFilterParams, UserUpdate
from src.services.user_service import UserService


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user_repo():
    """Create a mock UserRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_token_repo():
    """Create a mock RefreshTokenRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service():
    """Create a mock AuditService."""
    service = AsyncMock()
    return service


@pytest.fixture
def user_service(mock_session, mock_user_repo, mock_token_repo, mock_audit_service):
    """Create UserService with mocked dependencies."""
    with patch("src.services.user_service.UserRepository", return_value=mock_user_repo), \
         patch("src.services.user_service.RefreshTokenRepository", return_value=mock_token_repo), \
         patch("src.services.user_service.AuditService", return_value=mock_audit_service):
        service = UserService(mock_session)
    return service


@pytest.fixture
def regular_user():
    """Create a regular (non-admin) User instance."""
    from datetime import UTC, datetime
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="regular_user",
        password_hash="$argon2id$v=19$m=65536,t=2,p=4$...",
        is_active=True,
        is_admin=False,
    )
    # Set required timestamp fields
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


@pytest.fixture
def admin_user():
    """Create an admin User instance."""
    from datetime import UTC, datetime
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="admin_user",
        password_hash="$argon2id$v=19$m=65536,t=2,p=4$...",
        is_active=True,
        is_admin=True,
    )
    # Set required timestamp fields
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


class TestGetUserProfile:
    """Test the get_user_profile method."""

    @pytest.mark.asyncio
    async def test_get_own_profile(
        self,
        user_service,
        mock_user_repo,
        mock_audit_service,
        regular_user,
    ):
        """Test user viewing their own profile."""
        # Setup
        mock_user_repo.get_with_roles.return_value = regular_user

        # Execute
        result = await user_service.get_user_profile(
            user_id=regular_user.id,
            current_user=regular_user,
        )

        # Verify
        assert result.id == regular_user.id
        mock_user_repo.get_with_roles.assert_called_once_with(regular_user.id)
        # Should not log audit event when viewing own profile
        mock_audit_service.log_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_view_other_profile(
        self,
        user_service,
        mock_user_repo,
        mock_audit_service,
        admin_user,
        regular_user,
    ):
        """Test admin viewing another user's profile."""
        # Setup
        mock_user_repo.get_with_roles.return_value = regular_user

        # Execute
        result = await user_service.get_user_profile(
            user_id=regular_user.id,
            current_user=admin_user,
            ip_address="192.168.1.1",
        )

        # Verify
        assert result.id == regular_user.id
        # Should log audit event when admin views other profile
        mock_audit_service.log_event.assert_called_once()
        call_args = mock_audit_service.log_event.call_args[1]
        assert call_args["action"] == AuditAction.READ
        assert call_args["entity_id"] == regular_user.id

    @pytest.mark.asyncio
    async def test_user_cannot_view_other_profile(
        self,
        user_service,
        regular_user,
    ):
        """Test non-admin user cannot view another user's profile."""
        # Setup
        other_user_id = uuid.uuid4()

        # Execute & Verify
        with pytest.raises(InsufficientPermissionsError):
            await user_service.get_user_profile(
                user_id=other_user_id,
                current_user=regular_user,
            )

    @pytest.mark.asyncio
    async def test_get_profile_user_not_found(
        self,
        user_service,
        mock_user_repo,
        regular_user,
    ):
        """Test viewing profile of non-existent user."""
        # Setup
        mock_user_repo.get_with_roles.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError):
            await user_service.get_user_profile(
                user_id=regular_user.id,
                current_user=regular_user,
            )


class TestUpdateUserProfile:
    """Test the update_user_profile method."""

    @pytest.mark.asyncio
    async def test_update_own_profile(
        self,
        user_service,
        mock_user_repo,
        mock_audit_service,
        regular_user,
    ):
        """Test user updating their own profile."""
        # Setup
        update_data = UserUpdate(full_name="Updated Name")
        mock_user_repo.get_by_id.return_value = regular_user

        # Create mock updated user
        updated_user = MagicMock(spec=User)
        updated_user.id = regular_user.id
        updated_user.email = regular_user.email
        updated_user.username = regular_user.username
        updated_user.full_name = "Updated Name"
        updated_user.is_active = regular_user.is_active
        updated_user.is_admin = regular_user.is_admin
        updated_user.created_at = regular_user.created_at
        updated_user.updated_at = regular_user.updated_at
        updated_user.last_login_at = None
        updated_user.deleted_at = None
        updated_user.roles = []
        mock_user_repo.update.return_value = updated_user

        # Execute
        result = await user_service.update_user_profile(
            user_id=regular_user.id,
            update_data=update_data,
            current_user=regular_user,
        )

        # Verify
        assert result.id == regular_user.id
        mock_user_repo.update.assert_called_once()
        mock_audit_service.log_data_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_email_uniqueness_check(
        self,
        user_service,
        mock_user_repo,
        regular_user,
    ):
        """Test that email uniqueness is validated."""
        # Setup
        update_data = UserUpdate(email="existing@example.com")
        mock_user_repo.get_by_id.return_value = regular_user

        existing_user = User(id=uuid.uuid4(), email="existing@example.com", username="other")
        mock_user_repo.get_by_email.return_value = existing_user

        # Execute & Verify
        with pytest.raises(AlreadyExistsError, match="Email .* already registered"):
            await user_service.update_user_profile(
                user_id=regular_user.id,
                update_data=update_data,
                current_user=regular_user,
            )

    @pytest.mark.asyncio
    async def test_update_username_uniqueness_check(
        self,
        user_service,
        mock_user_repo,
        regular_user,
    ):
        """Test that username uniqueness is validated."""
        # Setup
        update_data = UserUpdate(username="existing_username")
        mock_user_repo.get_by_id.return_value = regular_user

        existing_user = User(id=uuid.uuid4(), email="other@example.com", username="existing_username")
        mock_user_repo.get_by_username.return_value = existing_user

        # Execute & Verify
        with pytest.raises(AlreadyExistsError, match="Username .* already taken"):
            await user_service.update_user_profile(
                user_id=regular_user.id,
                update_data=update_data,
                current_user=regular_user,
            )

    @pytest.mark.asyncio
    async def test_admin_update_other_profile(
        self,
        user_service,
        mock_user_repo,
        mock_audit_service,
        admin_user,
        regular_user,
    ):
        """Test admin updating another user's profile."""
        # Setup
        update_data = UserUpdate(full_name="Admin Updated")
        mock_user_repo.get_by_id.return_value = regular_user

        # Create mock updated user
        updated_user = MagicMock(spec=User)
        updated_user.id = regular_user.id
        updated_user.email = regular_user.email
        updated_user.username = regular_user.username
        updated_user.full_name = "Admin Updated"
        updated_user.is_active = regular_user.is_active
        updated_user.is_admin = regular_user.is_admin
        updated_user.created_at = regular_user.created_at
        updated_user.updated_at = regular_user.updated_at
        updated_user.last_login_at = None
        updated_user.deleted_at = None
        updated_user.roles = []
        mock_user_repo.update.return_value = updated_user

        # Execute
        result = await user_service.update_user_profile(
            user_id=regular_user.id,
            update_data=update_data,
            current_user=admin_user,
        )

        # Verify
        assert result.id == regular_user.id
        mock_audit_service.log_data_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_profile(
        self,
        user_service,
        regular_user,
    ):
        """Test non-admin user cannot update another user's profile."""
        # Setup
        other_user_id = uuid.uuid4()
        update_data = UserUpdate(full_name="Hacker")

        # Execute & Verify
        with pytest.raises(InsufficientPermissionsError):
            await user_service.update_user_profile(
                user_id=other_user_id,
                update_data=update_data,
                current_user=regular_user,
            )

    @pytest.mark.asyncio
    async def test_update_profile_user_not_found(
        self,
        user_service,
        mock_user_repo,
        regular_user,
    ):
        """Test updating non-existent user."""
        # Setup
        update_data = UserUpdate(full_name="Updated")
        mock_user_repo.get_by_id.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError):
            await user_service.update_user_profile(
                user_id=regular_user.id,
                update_data=update_data,
                current_user=regular_user,
            )


class TestListUsers:
    """Test the list_users method."""

    @pytest.mark.asyncio
    async def test_list_users_as_admin(
        self,
        user_service,
        mock_user_repo,
        mock_audit_service,
        admin_user,
    ):
        """Test admin listing users."""
        from datetime import UTC, datetime
        # Setup
        pagination = PaginationParams(page=1, page_size=20)
        filters = UserFilterParams()

        # Create mock users with all required fields
        mock_users = []
        for i in range(20):
            user = User(
                id=uuid.uuid4(),
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash="hash",
                is_active=True,
                is_admin=False,
            )
            user.created_at = datetime.now(UTC)
            user.updated_at = datetime.now(UTC)
            mock_users.append(user)

        mock_user_repo.filter_users.return_value = mock_users
        mock_user_repo.count_filtered.return_value = 100

        # Execute
        result = await user_service.list_users(
            pagination=pagination,
            filters=filters,
            current_user=admin_user,
        )

        # Verify
        assert len(result.data) == 20
        assert result.meta.total == 100
        assert result.meta.page == 1
        assert result.meta.page_size == 20
        assert result.meta.total_pages == 5

        mock_user_repo.filter_users.assert_called_once()
        mock_audit_service.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_users_with_filters(
        self,
        user_service,
        mock_user_repo,
        admin_user,
    ):
        """Test listing users with filters."""
        # Setup
        pagination = PaginationParams(page=1, page_size=10)
        filters = UserFilterParams(is_active=True, is_superuser=False, search="john")

        mock_user_repo.filter_users.return_value = []
        mock_user_repo.count_filtered.return_value = 0

        # Execute
        await user_service.list_users(
            pagination=pagination,
            filters=filters,
            current_user=admin_user,
        )

        # Verify
        call_args = mock_user_repo.filter_users.call_args[1]
        assert call_args["is_active"] == True
        assert call_args["is_admin"] == False
        assert call_args["search"] == "john"

    @pytest.mark.asyncio
    async def test_list_users_not_admin(
        self,
        user_service,
        regular_user,
    ):
        """Test non-admin user cannot list users."""
        # Setup
        pagination = PaginationParams(page=1, page_size=20)
        filters = UserFilterParams()

        # Execute & Verify
        with pytest.raises(InsufficientPermissionsError, match="Administrator privileges required"):
            await user_service.list_users(
                pagination=pagination,
                filters=filters,
                current_user=regular_user,
            )


class TestDeactivateUser:
    """Test the deactivate_user method."""

    @pytest.mark.asyncio
    async def test_deactivate_user_as_admin(
        self,
        user_service,
        mock_user_repo,
        mock_token_repo,
        mock_audit_service,
        admin_user,
        regular_user,
    ):
        """Test admin deactivating a user."""
        # Setup
        mock_user_repo.get_by_id.return_value = regular_user

        # Execute
        await user_service.deactivate_user(
            user_id=regular_user.id,
            current_user=admin_user,
        )

        # Verify
        mock_user_repo.update.assert_called_once_with(regular_user, is_active=False)
        mock_token_repo.revoke_user_tokens.assert_called_once_with(regular_user.id)
        mock_audit_service.log_data_change.assert_called_once()

        call_args = mock_audit_service.log_data_change.call_args[1]
        assert call_args["action"] == AuditAction.UPDATE
        assert call_args["old_values"] == {"is_active": True}
        assert call_args["new_values"] == {"is_active": False}

    @pytest.mark.asyncio
    async def test_deactivate_user_not_admin(
        self,
        user_service,
        regular_user,
    ):
        """Test non-admin user cannot deactivate users."""
        # Execute & Verify
        with pytest.raises(InsufficientPermissionsError, match="Administrator privileges required"):
            await user_service.deactivate_user(
                user_id=uuid.uuid4(),
                current_user=regular_user,
            )

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(
        self,
        user_service,
        mock_user_repo,
        admin_user,
    ):
        """Test deactivating non-existent user."""
        # Setup
        mock_user_repo.get_by_id.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError):
            await user_service.deactivate_user(
                user_id=uuid.uuid4(),
                current_user=admin_user,
            )


class TestSoftDeleteUser:
    """Test the soft_delete_user method."""

    @pytest.mark.asyncio
    async def test_soft_delete_user_as_admin(
        self,
        user_service,
        mock_user_repo,
        mock_token_repo,
        mock_audit_service,
        admin_user,
        regular_user,
    ):
        """Test admin soft deleting a user."""
        from datetime import UTC, datetime
        # Setup
        mock_user_repo.get_by_id.return_value = regular_user

        # Create mock deleted user
        deleted_user = MagicMock(spec=User)
        deleted_user.id = regular_user.id
        deleted_user.email = regular_user.email
        deleted_user.username = regular_user.username
        deleted_user.deleted_at = datetime.now(UTC)
        mock_user_repo.soft_delete.return_value = deleted_user

        # Execute
        await user_service.soft_delete_user(
            user_id=regular_user.id,
            current_user=admin_user,
        )

        # Verify
        mock_user_repo.soft_delete.assert_called_once_with(regular_user)
        mock_token_repo.revoke_user_tokens.assert_called_once_with(regular_user.id)
        mock_audit_service.log_data_change.assert_called_once()

        call_args = mock_audit_service.log_data_change.call_args[1]
        assert call_args["action"] == AuditAction.DELETE

    @pytest.mark.asyncio
    async def test_soft_delete_user_not_admin(
        self,
        user_service,
        regular_user,
    ):
        """Test non-admin user cannot soft delete users."""
        # Execute & Verify
        with pytest.raises(InsufficientPermissionsError, match="Administrator privileges required"):
            await user_service.soft_delete_user(
                user_id=uuid.uuid4(),
                current_user=regular_user,
            )

    @pytest.mark.asyncio
    async def test_soft_delete_user_not_found(
        self,
        user_service,
        mock_user_repo,
        admin_user,
    ):
        """Test soft deleting non-existent user."""
        # Setup
        mock_user_repo.get_by_id.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError):
            await user_service.soft_delete_user(
                user_id=uuid.uuid4(),
                current_user=admin_user,
            )
