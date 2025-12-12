"""
Unit tests for AuditService.

All tests are fully mocked - no database or external dependencies.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.models.audit_log import AuditAction, AuditLog, AuditStatus
from src.services.audit_service import AuditService


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_audit_repo():
    """Create a mock AuditLogRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def audit_service(mock_session, mock_audit_repo):
    """Create AuditService with mocked dependencies."""
    with patch(
        "src.services.audit_service.AuditLogRepository", return_value=mock_audit_repo
    ):
        service = AuditService(mock_session)
    return service


class TestLogEvent:
    """Test the core log_event method."""

    @pytest.mark.asyncio
    async def test_log_event_creates_audit_log(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test that log_event creates an audit log with all parameters."""
        # Setup
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=entity_id,
            status=AuditStatus.SUCCESS,
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_event(
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=entity_id,
            old_values={"email": "old@example.com"},
            new_values={"email": "new@example.com"},
            description="Email updated",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            status=AuditStatus.SUCCESS,
            error_message=None,
            extra_metadata={"source": "test"},
        )

        # Verify
        assert result == mock_audit_log
        mock_audit_repo.create.assert_called_once_with(
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=entity_id,
            old_values={"email": "old@example.com"},
            new_values={"email": "new@example.com"},
            description="Email updated",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            status=AuditStatus.SUCCESS,
            error_message=None,
            extra_metadata={"source": "test"},
        )
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_with_minimal_parameters(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test that log_event works with minimal required parameters."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
            status=AuditStatus.SUCCESS,
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_event(
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
        )

        # Verify
        assert result == mock_audit_log
        mock_audit_repo.create.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_with_null_user_id(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test that log_event handles system actions (NULL user_id)."""
        # Setup
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=None,
            action=AuditAction.CREATE,
            entity_type="system",
            status=AuditStatus.SUCCESS,
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_event(
            user_id=None,
            action=AuditAction.CREATE,
            entity_type="system",
            description="System automated action",
        )

        # Verify
        assert result == mock_audit_log
        assert result.user_id is None
        mock_audit_repo.create.assert_called_once()


class TestLogLogin:
    """Test the log_login method."""

    @pytest.mark.asyncio
    async def test_log_successful_login(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a successful login."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.SUCCESS,
            description="User logged in successfully",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_login(
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            success=True,
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.LOGIN
        assert call_args["status"] == AuditStatus.SUCCESS
        assert call_args["description"] == "User logged in successfully"

    @pytest.mark.asyncio
    async def test_log_failed_login(self, audit_service, mock_audit_repo, mock_session):
        """Test logging a failed login."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.LOGIN_FAILED,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.FAILURE,
            description="Login attempt failed",
            error_message="Invalid credentials",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_login(
            user_id=user_id,
            ip_address="192.168.1.1",
            success=False,
            error_message="Invalid credentials",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.LOGIN_FAILED
        assert call_args["status"] == AuditStatus.FAILURE
        assert call_args["description"] == "Login attempt failed"
        assert call_args["error_message"] == "Invalid credentials"


class TestLogLogout:
    """Test the log_logout method."""

    @pytest.mark.asyncio
    async def test_log_logout(self, audit_service, mock_audit_repo, mock_session):
        """Test logging a logout event."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.LOGOUT,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.SUCCESS,
            description="User logged out",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_logout(
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.LOGOUT
        assert call_args["status"] == AuditStatus.SUCCESS
        assert call_args["description"] == "User logged out"


class TestLogPasswordChange:
    """Test the log_password_change method."""

    @pytest.mark.asyncio
    async def test_log_successful_password_change(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a successful password change."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.SUCCESS,
            description="User password changed successfully",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_password_change(
            user_id=user_id,
            ip_address="192.168.1.1",
            success=True,
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.PASSWORD_CHANGE
        assert call_args["status"] == AuditStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_log_failed_password_change(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a failed password change."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.FAILURE,
            description="Password change attempt failed",
            error_message="Current password incorrect",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_password_change(
            user_id=user_id,
            success=False,
            error_message="Current password incorrect",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["status"] == AuditStatus.FAILURE
        assert call_args["error_message"] == "Current password incorrect"


class TestLogTokenRefresh:
    """Test the log_token_refresh method."""

    @pytest.mark.asyncio
    async def test_log_successful_token_refresh(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a successful token refresh."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.TOKEN_REFRESH,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.SUCCESS,
            description="Token refreshed successfully",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_token_refresh(
            user_id=user_id,
            ip_address="192.168.1.1",
            success=True,
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.TOKEN_REFRESH
        assert call_args["status"] == AuditStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_log_failed_token_refresh(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a failed token refresh."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.TOKEN_REFRESH,
            entity_type="user",
            entity_id=user_id,
            status=AuditStatus.FAILURE,
            description="Token refresh attempt failed",
            error_message="Invalid refresh token",
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_token_refresh(
            user_id=user_id,
            success=False,
            error_message="Invalid refresh token",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["status"] == AuditStatus.FAILURE


class TestLogDataChange:
    """Test the log_data_change method."""

    @pytest.mark.asyncio
    async def test_log_create_action(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a CREATE action."""
        # Setup
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.CREATE,
            entity_type="account",
            entity_id=entity_id,
            new_values={"name": "Savings", "balance": 1000.00},
            status=AuditStatus.SUCCESS,
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_data_change(
            user_id=user_id,
            action=AuditAction.CREATE,
            entity_type="account",
            entity_id=entity_id,
            new_values={"name": "Savings", "balance": 1000.00},
            description="Account created",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.CREATE
        assert call_args["new_values"] == {"name": "Savings", "balance": 1000.00}

    @pytest.mark.asyncio
    async def test_log_update_action(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging an UPDATE action with before/after values."""
        # Setup
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=entity_id,
            old_values={"email": "old@example.com"},
            new_values={"email": "new@example.com"},
            status=AuditStatus.SUCCESS,
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_data_change(
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=entity_id,
            old_values={"email": "old@example.com"},
            new_values={"email": "new@example.com"},
            description="Email updated",
            ip_address="192.168.1.1",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.UPDATE
        assert call_args["old_values"] == {"email": "old@example.com"}
        assert call_args["new_values"] == {"email": "new@example.com"}

    @pytest.mark.asyncio
    async def test_log_delete_action(
        self, audit_service, mock_audit_repo, mock_session
    ):
        """Test logging a DELETE action with old values."""
        # Setup
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        mock_audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=AuditAction.DELETE,
            entity_type="account",
            entity_id=entity_id,
            old_values={"name": "Savings", "balance": 1000.00},
            status=AuditStatus.SUCCESS,
        )
        mock_audit_repo.create.return_value = mock_audit_log

        # Execute
        result = await audit_service.log_data_change(
            user_id=user_id,
            action=AuditAction.DELETE,
            entity_type="account",
            entity_id=entity_id,
            old_values={"name": "Savings", "balance": 1000.00},
            description="Account deleted",
        )

        # Verify
        assert result == mock_audit_log
        call_args = mock_audit_repo.create.call_args[1]
        assert call_args["action"] == AuditAction.DELETE
        assert call_args["old_values"] == {"name": "Savings", "balance": 1000.00}


class TestGetUserAuditLogs:
    """Test the get_user_audit_logs method."""

    @pytest.mark.asyncio
    async def test_get_user_audit_logs_with_filters(
        self, audit_service, mock_audit_repo
    ):
        """Test getting user audit logs with filters."""
        # Setup
        user_id = uuid.uuid4()
        mock_logs = [
            AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=AuditAction.LOGIN,
                entity_type="user",
            ),
            AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=AuditAction.LOGIN,
                entity_type="user",
            ),
        ]
        mock_audit_repo.get_user_logs.return_value = mock_logs
        mock_audit_repo.count_user_logs.return_value = 25

        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        # Execute
        logs, total = await audit_service.get_user_audit_logs(
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
            status=AuditStatus.SUCCESS,
            start_date=start_date,
            end_date=end_date,
            skip=0,
            limit=20,
        )

        # Verify
        assert logs == mock_logs
        assert total == 25
        mock_audit_repo.get_user_logs.assert_called_once_with(
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
            status=AuditStatus.SUCCESS,
            start_date=start_date,
            end_date=end_date,
            skip=0,
            limit=20,
        )
        mock_audit_repo.count_user_logs.assert_called_once_with(
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
            status=AuditStatus.SUCCESS,
            start_date=start_date,
            end_date=end_date,
        )

    @pytest.mark.asyncio
    async def test_get_user_audit_logs_with_pagination(
        self, audit_service, mock_audit_repo
    ):
        """Test pagination of user audit logs."""
        # Setup
        user_id = uuid.uuid4()
        mock_logs = [
            AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=AuditAction.READ,
                entity_type="user",
            )
            for _ in range(10)
        ]
        mock_audit_repo.get_user_logs.return_value = mock_logs
        mock_audit_repo.count_user_logs.return_value = 100

        # Execute - second page
        logs, total = await audit_service.get_user_audit_logs(
            user_id=user_id,
            skip=10,
            limit=10,
        )

        # Verify
        assert len(logs) == 10
        assert total == 100
        mock_audit_repo.get_user_logs.assert_called_once()
        call_args = mock_audit_repo.get_user_logs.call_args[1]
        assert call_args["skip"] == 10
        assert call_args["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_user_audit_logs_no_results(self, audit_service, mock_audit_repo):
        """Test getting user audit logs when no results found."""
        # Setup
        user_id = uuid.uuid4()
        mock_audit_repo.get_user_logs.return_value = []
        mock_audit_repo.count_user_logs.return_value = 0

        # Execute
        logs, total = await audit_service.get_user_audit_logs(
            user_id=user_id,
            action=AuditAction.DELETE,
        )

        # Verify
        assert logs == []
        assert total == 0


class TestGetAllAuditLogs:
    """Test the get_all_audit_logs method."""

    @pytest.mark.asyncio
    async def test_get_all_audit_logs_with_filters(
        self, audit_service, mock_audit_repo
    ):
        """Test getting all audit logs with filters (admin only)."""
        # Setup
        mock_logs = [
            AuditLog(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                action=AuditAction.LOGIN_FAILED,
                entity_type="user",
            ),
            AuditLog(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                action=AuditAction.LOGIN_FAILED,
                entity_type="user",
            ),
        ]
        mock_audit_repo.get_all_logs.return_value = mock_logs
        mock_audit_repo.count_all_logs.return_value = len(mock_logs)

        start_date = datetime.now(UTC) - timedelta(days=7)

        # Execute
        logs, total = await audit_service.get_all_audit_logs(
            action=AuditAction.LOGIN_FAILED,
            status=AuditStatus.FAILURE,
            start_date=start_date,
            skip=0,
            limit=50,
        )

        # Verify
        assert logs == mock_logs
        assert total == len(mock_logs)
        mock_audit_repo.get_all_logs.assert_called_once_with(
            action=AuditAction.LOGIN_FAILED,
            entity_type=None,
            status=AuditStatus.FAILURE,
            start_date=start_date,
            end_date=None,
            skip=0,
            limit=50,
        )
        mock_audit_repo.count_all_logs.assert_called_once_with(
            action=AuditAction.LOGIN_FAILED,
            entity_type=None,
            status=AuditStatus.FAILURE,
            start_date=start_date,
            end_date=None,
        )

    @pytest.mark.asyncio
    async def test_get_all_audit_logs_no_filters(self, audit_service, mock_audit_repo):
        """Test getting all audit logs without filters."""
        # Setup
        mock_logs = [
            AuditLog(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                action=AuditAction.READ,
                entity_type="user",
            )
            for _ in range(100)
        ]
        mock_audit_repo.get_all_logs.return_value = mock_logs
        mock_audit_repo.count_all_logs.return_value = len(mock_logs)

        # Execute
        logs, total = await audit_service.get_all_audit_logs()

        # Verify
        assert len(logs) == 100
        assert total == 100
        mock_audit_repo.get_all_logs.assert_called_once()
        mock_audit_repo.count_all_logs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_audit_logs_by_entity_type(
        self, audit_service, mock_audit_repo
    ):
        """Test filtering all audit logs by entity type."""
        # Setup
        mock_logs = [
            AuditLog(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                action=AuditAction.CREATE,
                entity_type="transaction",
            ),
            AuditLog(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                action=AuditAction.UPDATE,
                entity_type="transaction",
            ),
        ]
        mock_audit_repo.get_all_logs.return_value = mock_logs
        mock_audit_repo.count_all_logs.return_value = len(mock_logs)

        # Execute
        logs, total = await audit_service.get_all_audit_logs(
            entity_type="transaction",
            skip=0,
            limit=20,
        )

        # Verify
        assert logs == mock_logs
        assert total == len(mock_logs)
        call_args = mock_audit_repo.get_all_logs.call_args[1]
        assert call_args["entity_type"] == "transaction"
        mock_audit_repo.count_all_logs.assert_called_once()
