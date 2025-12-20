"""
Unit tests for AuthService.

All tests are fully mocked - no database or external dependencies.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from jose import JWTError

from core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from models.refresh_token import RefreshToken
from models.user import User
from schemas.user import UserCreate
from services.auth_service import AuthService


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
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
def auth_service(mock_session, mock_user_repo, mock_token_repo):
    """Create AuthService with mocked dependencies."""
    with (
        patch("services.auth_service.UserRepository", return_value=mock_user_repo),
        patch(
            "services.auth_service.RefreshTokenRepository",
            return_value=mock_token_repo,
        ),
    ):
        service = AuthService(mock_session)
    return service


@pytest.fixture
def sample_user():
    """Create a sample User instance."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="$argon2id$v=19$m=65536,t=2,p=4$...",
        is_admin=False,
    )


class TestRegister:
    """Test the register method."""

    @pytest.mark.asyncio
    @patch("services.auth_service.hash_password")
    @patch("services.auth_service.create_access_token")
    @patch("services.auth_service.create_refresh_token")
    @patch("services.auth_service.hash_refresh_token")
    async def test_register_success(
        self,
        mock_hash_refresh,
        mock_create_refresh,
        mock_create_access,
        mock_hash_password,
        auth_service,
        mock_user_repo,
        mock_token_repo,
        mock_session,
    ):
        """Test successful user registration."""
        # Setup
        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser",
            password="SecureP@ss123",
        )

        mock_user_repo.email_exists.return_value = False
        mock_user_repo.username_exists.return_value = False
        mock_hash_password.return_value = "hashed_password"

        created_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            username=user_data.username,
            password_hash="hashed_password",
            is_admin=False,
        )
        mock_user_repo.create.return_value = created_user

        mock_create_access.return_value = "access_token_123"
        mock_create_refresh.return_value = "refresh_token_123"
        mock_hash_refresh.return_value = "refresh_token_hash"

        # Execute
        user, tokens = await auth_service.register(
            user_data,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Verify
        assert user == created_user
        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token == "refresh_token_123"

        mock_user_repo.email_exists.assert_called_once_with(user_data.email)
        mock_user_repo.username_exists.assert_called_once_with(user_data.username)
        mock_hash_password.assert_called_once_with(user_data.password)
        mock_user_repo.create.assert_called_once()
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_register_email_already_exists(self, auth_service, mock_user_repo):
        """Test registration with existing email."""
        # Setup
        user_data = UserCreate(
            email="existing@example.com",
            username="newuser",
            password="SecureP@ss123",
        )
        mock_user_repo.email_exists.return_value = True

        # Execute & Verify
        with pytest.raises(AlreadyExistsError, match="User with this email"):
            await auth_service.register(user_data)

        mock_user_repo.email_exists.assert_called_once_with(user_data.email)
        mock_user_repo.username_exists.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_username_already_exists(self, auth_service, mock_user_repo):
        """Test registration with existing username."""
        # Setup
        user_data = UserCreate(
            email="newuser@example.com",
            username="existing_user",
            password="SecureP@ss123",
        )
        mock_user_repo.email_exists.return_value = False
        mock_user_repo.username_exists.return_value = True

        # Execute & Verify
        with pytest.raises(AlreadyExistsError, match="User with this username"):
            await auth_service.register(user_data)

        mock_user_repo.username_exists.assert_called_once_with(user_data.username)


class TestLogin:
    """Test the login method."""

    @pytest.mark.asyncio
    @patch("services.auth_service.verify_password")
    @patch("services.auth_service.create_access_token")
    @patch("services.auth_service.create_refresh_token")
    @patch("services.auth_service.hash_refresh_token")
    async def test_login_success(
        self,
        mock_hash_refresh,
        mock_create_refresh,
        mock_create_access,
        mock_verify_password,
        auth_service,
        mock_user_repo,
        mock_token_repo,
        mock_session,
        sample_user,
    ):
        """Test successful login."""
        # Setup
        mock_user_repo.get_by_email.return_value = sample_user
        mock_verify_password.return_value = True
        mock_create_access.return_value = "access_token_123"
        mock_create_refresh.return_value = "refresh_token_123"
        mock_hash_refresh.return_value = "refresh_token_hash"

        # Execute
        user, tokens = await auth_service.login(
            email="test@example.com",
            password="correct_password",
            ip_address="192.168.1.1",
        )

        # Verify
        assert user == sample_user
        assert tokens.access_token == "access_token_123"

        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        mock_verify_password.assert_called_once_with(
            "correct_password", sample_user.password_hash
        )
        mock_user_repo.update_last_login.assert_called_once_with(sample_user.id)
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service, mock_user_repo):
        """Test login with non-existent email."""
        # Setup
        mock_user_repo.get_by_email.return_value = None

        # Execute & Verify
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="nonexistent@example.com",
                password="password",
            )

    @pytest.mark.asyncio
    @patch("services.auth_service.verify_password")
    async def test_login_wrong_password(
        self,
        mock_verify_password,
        auth_service,
        mock_user_repo,
        sample_user,
    ):
        """Test login with incorrect password."""
        # Setup
        mock_user_repo.get_by_email.return_value = sample_user
        mock_verify_password.return_value = False

        # Execute & Verify
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="test@example.com",
                password="wrong_password",
            )

    @pytest.mark.asyncio
    @patch("services.auth_service.verify_password")
    async def test_login_inactive_user(
        self,
        mock_verify_password,
        auth_service,
        mock_user_repo,
        sample_user,
    ):
        """Test login with inactive (soft-deleted) account.

        Soft-deleted users are filtered at the repository level,
        so get_by_email returns None for inactive users.
        """
        # Setup - soft-deleted users are filtered by repository
        mock_user_repo.get_by_email.return_value = None

        # Execute & Verify - returns invalid credentials, not account inactive
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="test@example.com",
                password="correct_password",
            )


class TestRefreshAccessToken:
    """Test the refresh_access_token method."""

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    @patch("services.auth_service.create_access_token")
    @patch("services.auth_service.create_refresh_token")
    async def test_refresh_token_success(
        self,
        mock_create_refresh,
        mock_create_access,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_user_repo,
        mock_token_repo,
        mock_session,
        sample_user,
    ):
        """Test successful token refresh."""
        # Setup
        token_family_id = uuid.uuid4()
        mock_decode.return_value = {"sub": str(sample_user.id), "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"

        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            token_hash="token_hash",
            token_family_id=token_family_id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
        )
        mock_token_repo.get_by_token_hash.return_value = db_token
        mock_user_repo.get_by_id.return_value = sample_user

        mock_create_access.return_value = "new_access_token"
        mock_create_refresh.return_value = "new_refresh_token"

        # Execute
        tokens = await auth_service.refresh_access_token(
            refresh_token="old_refresh_token",
            ip_address="192.168.1.1",
        )

        # Verify
        assert tokens.access_token == "new_access_token"
        assert tokens.refresh_token == "new_refresh_token"

        mock_decode.assert_called_once_with("old_refresh_token")
        mock_token_repo.revoke_token.assert_called_once_with(db_token.id)
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    async def test_refresh_token_invalid_jwt(self, mock_decode, auth_service):
        """Test refresh with invalid JWT."""
        # Setup
        mock_decode.side_effect = JWTError("Invalid token")

        # Execute & Verify
        with pytest.raises(InvalidTokenError, match="Invalid refresh token"):
            await auth_service.refresh_access_token(refresh_token="invalid_jwt")

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    async def test_refresh_token_wrong_type(
        self,
        mock_verify_type,
        mock_decode,
        auth_service,
    ):
        """Test refresh with access token instead of refresh token."""
        # Setup
        mock_decode.return_value = {"sub": "user_id", "type": "access"}
        mock_verify_type.return_value = False

        # Execute & Verify
        with pytest.raises(InvalidTokenError, match="not a refresh token"):
            await auth_service.refresh_access_token(refresh_token="access_token")

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    async def test_refresh_token_not_in_database(
        self,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_token_repo,
    ):
        """Test refresh with token not in database."""
        # Setup
        mock_decode.return_value = {"sub": "user_id", "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"
        mock_token_repo.get_by_token_hash.return_value = None

        # Execute & Verify
        with pytest.raises(InvalidTokenError, match="Invalid refresh token"):
            await auth_service.refresh_access_token(refresh_token="unknown_token")

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    async def test_refresh_token_reuse_detection(
        self,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_token_repo,
        mock_session,
    ):
        """Test token reuse detection (security feature)."""
        # Setup
        token_family_id = uuid.uuid4()
        mock_decode.return_value = {"sub": "user_id", "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"

        # Token is already revoked - indicates reuse
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            token_hash="token_hash",
            token_family_id=token_family_id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=True,  # Already revoked!
        )
        mock_token_repo.get_by_token_hash.return_value = db_token

        # Execute & Verify
        with pytest.raises(InvalidTokenError, match="compromised"):
            await auth_service.refresh_access_token(refresh_token="reused_token")

        # Should revoke entire token family
        mock_token_repo.revoke_token_family.assert_called_once_with(token_family_id)
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    async def test_refresh_token_expired(
        self,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_token_repo,
    ):
        """Test refresh with expired token."""
        # Setup
        mock_decode.return_value = {"sub": "user_id", "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"

        # Token expired 1 day ago
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            token_hash="token_hash",
            token_family_id=uuid.uuid4(),
            expires_at=datetime.now(UTC) - timedelta(days=1),
            is_revoked=False,
        )
        mock_token_repo.get_by_token_hash.return_value = db_token

        # Execute & Verify
        with pytest.raises(InvalidTokenError, match="expired"):
            await auth_service.refresh_access_token(refresh_token="expired_token")

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    async def test_refresh_token_inactive_user(
        self,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_user_repo,
        mock_token_repo,
        sample_user,
    ):
        """Test refresh with inactive (soft-deleted) user account.

        Soft-deleted users are filtered at repository level,
        so get_by_id returns None for inactive users.
        """
        # Setup
        mock_decode.return_value = {"sub": str(sample_user.id), "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"

        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            token_hash="token_hash",
            token_family_id=uuid.uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
        )
        mock_token_repo.get_by_token_hash.return_value = db_token
        # Soft-deleted users are filtered by repository
        mock_user_repo.get_by_id.return_value = None

        # Execute & Verify - returns invalid token
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_access_token(refresh_token="valid_token")


class TestLogout:
    """Test the logout method."""

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    async def test_logout_success(
        self,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_token_repo,
        mock_session,
    ):
        """Test successful logout."""
        # Setup
        mock_decode.return_value = {"sub": "user_id", "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"

        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            token_hash="token_hash",
            token_family_id=uuid.uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
        )
        mock_token_repo.get_by_token_hash.return_value = db_token

        # Execute
        await auth_service.logout(refresh_token="refresh_token_123")

        # Verify
        mock_decode.assert_called_once_with("refresh_token_123")
        mock_token_repo.revoke_token.assert_called_once_with(db_token.id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    async def test_logout_invalid_jwt(self, mock_decode, auth_service):
        """Test logout with invalid JWT."""
        # Setup
        mock_decode.side_effect = JWTError("Invalid token")

        # Execute & Verify
        with pytest.raises(InvalidTokenError):
            await auth_service.logout(refresh_token="invalid_jwt")

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    async def test_logout_wrong_token_type(
        self,
        mock_verify_type,
        mock_decode,
        auth_service,
    ):
        """Test logout with access token instead of refresh token."""
        # Setup
        mock_decode.return_value = {"sub": "user_id", "type": "access"}
        mock_verify_type.return_value = False

        # Execute & Verify
        with pytest.raises(InvalidTokenError, match="not a refresh token"):
            await auth_service.logout(refresh_token="access_token")

    @pytest.mark.asyncio
    @patch("services.auth_service.decode_token")
    @patch("services.auth_service.verify_token_type")
    @patch("services.auth_service.hash_refresh_token")
    async def test_logout_token_not_found(
        self,
        mock_hash_refresh,
        mock_verify_type,
        mock_decode,
        auth_service,
        mock_token_repo,
    ):
        """Test logout with token not in database."""
        # Setup
        mock_decode.return_value = {"sub": "user_id", "type": "refresh"}
        mock_verify_type.return_value = True
        mock_hash_refresh.return_value = "token_hash"
        mock_token_repo.get_by_token_hash.return_value = None

        # Execute & Verify
        with pytest.raises(InvalidTokenError):
            await auth_service.logout(refresh_token="unknown_token")


class TestChangePassword:
    """Test the change_password method."""

    @pytest.mark.asyncio
    @patch("services.auth_service.verify_password")
    @patch("services.auth_service.hash_password")
    async def test_change_password_success(
        self,
        mock_hash_password,
        mock_verify_password,
        auth_service,
        mock_user_repo,
        mock_token_repo,
        mock_session,
        sample_user,
    ):
        """Test successful password change."""
        # Setup
        original_password_hash = sample_user.password_hash
        mock_user_repo.get_by_id.return_value = sample_user
        mock_verify_password.return_value = True
        mock_hash_password.return_value = "new_hashed_password"
        mock_token_repo.revoke_user_tokens.return_value = 3  # Revoked 3 tokens

        # Execute
        await auth_service.change_password(
            user_id=sample_user.id,
            current_password="OldP@ss123",
            new_password="NewP@ss456",
        )

        # Verify
        mock_verify_password.assert_called_once_with(
            "OldP@ss123", original_password_hash
        )
        mock_hash_password.assert_called_once_with("NewP@ss456")
        assert sample_user.password_hash == "new_hashed_password"
        mock_token_repo.revoke_user_tokens.assert_called_once_with(sample_user.id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(
        self,
        auth_service,
        mock_user_repo,
    ):
        """Test password change with non-existent user."""
        # Setup
        mock_user_repo.get_by_id.return_value = None

        # Execute & Verify
        with pytest.raises(AuthenticationError, match="User not found"):
            await auth_service.change_password(
                user_id=uuid.uuid4(),
                current_password="password",
                new_password="new_password",
            )

    @pytest.mark.asyncio
    @patch("services.auth_service.verify_password")
    async def test_change_password_wrong_current_password(
        self,
        mock_verify_password,
        auth_service,
        mock_user_repo,
        sample_user,
    ):
        """Test password change with incorrect current password."""
        # Setup
        mock_user_repo.get_by_id.return_value = sample_user
        mock_verify_password.return_value = False

        # Execute & Verify
        with pytest.raises(
            InvalidCredentialsError, match="Current password is incorrect"
        ):
            await auth_service.change_password(
                user_id=sample_user.id,
                current_password="wrong_password",
                new_password="NewP@ss456",
            )


class TestGenerateTokens:
    """Test the _generate_tokens internal method."""

    @pytest.mark.asyncio
    @patch("services.auth_service.create_access_token")
    @patch("services.auth_service.create_refresh_token")
    @patch("services.auth_service.hash_refresh_token")
    async def test_generate_tokens_new_family(
        self,
        mock_hash_refresh,
        mock_create_refresh,
        mock_create_access,
        auth_service,
        mock_token_repo,
        mock_session,
        sample_user,
    ):
        """Test token generation with new token family."""
        # Setup
        mock_create_access.return_value = "access_token"
        mock_create_refresh.return_value = "refresh_token"
        mock_hash_refresh.return_value = "refresh_hash"

        # Execute
        tokens = await auth_service._generate_tokens(
            user=sample_user,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Verify
        assert tokens.access_token == "access_token"
        assert tokens.refresh_token == "refresh_token"
        assert tokens.token_type == "bearer"

        # Check access token claims
        access_call = mock_create_access.call_args[1]
        assert access_call["data"]["sub"] == str(sample_user.id)
        assert access_call["data"]["email"] == sample_user.email
        assert access_call["data"]["is_admin"] == sample_user.is_admin

        # Check refresh token storage
        mock_token_repo.create.assert_called_once()
        token_create_call = mock_token_repo.create.call_args[1]
        assert token_create_call["user_id"] == sample_user.id
        assert token_create_call["token_hash"] == "refresh_hash"

    @pytest.mark.asyncio
    @patch("services.auth_service.create_access_token")
    @patch("services.auth_service.create_refresh_token")
    @patch("services.auth_service.hash_refresh_token")
    async def test_generate_tokens_existing_family(
        self,
        mock_hash_refresh,
        mock_create_refresh,
        mock_create_access,
        auth_service,
        mock_token_repo,
        sample_user,
    ):
        """Test token generation with existing token family (rotation)."""
        # Setup
        existing_family_id = uuid.uuid4()
        mock_create_access.return_value = "access_token"
        mock_create_refresh.return_value = "refresh_token"
        mock_hash_refresh.return_value = "refresh_hash"

        # Execute
        await auth_service._generate_tokens(
            user=sample_user,
            token_family_id=existing_family_id,
        )

        # Verify
        token_create_call = mock_token_repo.create.call_args[1]
        assert token_create_call["token_family_id"] == existing_family_id

        # Check refresh token contains family ID
        refresh_call = mock_create_refresh.call_args[1]
        assert refresh_call["data"]["token_family_id"] == str(existing_family_id)
