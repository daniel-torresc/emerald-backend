"""
Audit service for comprehensive audit logging.

This module provides:
- Audit log creation for authentication events
- Audit log creation for data modifications
- Audit log retrieval for users and admins
- GDPR-compliant data access tracking
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditAction, AuditLog, AuditStatus
from repositories.audit_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service class for audit logging operations.

    This service handles:
    - Authentication event logging (login, logout, password change)
    - Data modification logging (create, update, delete)
    - Audit log retrieval with filtering
    - User and admin access to audit logs

    All audit logs are immutable - they cannot be modified or deleted after creation.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AuditService.

        Args:
            session: Async database session
        """
        self.session = session
        self.audit_repo = AuditLogRepository(session)

    async def log_event(
        self,
        user_id: uuid.UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Log a generic audit event.

        This is the core method for creating audit logs. Use the specialized
        methods (log_login, log_data_change, etc.) for common scenarios.

        Args:
            user_id: User who performed the action (None for system actions)
            action: Type of action performed
            entity_type: Type of entity affected (e.g., "user", "transaction")
            entity_id: UUID of affected entity
            old_values: Values before the action (for UPDATE/DELETE)
            new_values: Values after the action (for CREATE/UPDATE)
            description: Human-readable description
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing
            status: Status of the action
            error_message: Error message if status is FAILURE
            extra_metadata: Additional context as JSONB

        Returns:
            Created AuditLog instance

        Example:
            audit_log = await audit_service.log_event(
                user_id=user.id,
                action=AuditAction.UPDATE,
                entity_type="user",
                entity_id=user.id,
                old_values={"email": "old@example.com"},
                new_values={"email": "new@example.com"},
                description="User email updated",
                ip_address="192.168.1.1",
                status=AuditStatus.SUCCESS,
            )
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
            extra_metadata=extra_metadata,
        )
        audit_log = await self.audit_repo.add(audit_log)
        await self.session.commit()

        logger.debug(
            f"Audit log created: user={user_id}, action={action.value}, "
            f"entity={entity_type}:{entity_id}, status={status.value}"
        )

        return audit_log

    async def log_login(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """
        Log user login attempt.

        Args:
            user_id: User who attempted to login
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing
            success: Whether login was successful
            error_message: Error message if login failed

        Returns:
            Created AuditLog instance

        Example:
            # Successful login
            await audit_service.log_login(
                user_id=user.id,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0...",
                success=True
            )

            # Failed login
            await audit_service.log_login(
                user_id=user.id,
                ip_address="192.168.1.1",
                success=False,
                error_message="Invalid credentials"
            )
        """
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        description = (
            "User logged in successfully" if success else "Login attempt failed"
        )

        return await self.log_event(
            user_id=user_id,
            action=action,
            entity_type="user",
            entity_id=user_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
        )

    async def log_logout(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """
        Log user logout.

        Args:
            user_id: User who logged out
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing

        Returns:
            Created AuditLog instance

        Example:
            await audit_service.log_logout(
                user_id=user.id,
                ip_address="192.168.1.1"
            )
        """
        return await self.log_event(
            user_id=user_id,
            action=AuditAction.LOGOUT,
            entity_type="user",
            entity_id=user_id,
            description="User logged out",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=AuditStatus.SUCCESS,
        )

    async def log_password_change(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """
        Log password change attempt.

        Args:
            user_id: User who changed their password
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing
            success: Whether password change was successful
            error_message: Error message if password change failed

        Returns:
            Created AuditLog instance

        Example:
            await audit_service.log_password_change(
                user_id=user.id,
                ip_address="192.168.1.1",
                success=True
            )
        """
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        description = (
            "User password changed successfully"
            if success
            else "Password change attempt failed"
        )

        return await self.log_event(
            user_id=user_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
        )

    async def log_token_refresh(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """
        Log token refresh attempt.

        Args:
            user_id: User who refreshed their token
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing
            success: Whether token refresh was successful
            error_message: Error message if token refresh failed

        Returns:
            Created AuditLog instance

        Example:
            await audit_service.log_token_refresh(
                user_id=user.id,
                ip_address="192.168.1.1",
                success=True
            )
        """
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        description = (
            "Token refreshed successfully"
            if success
            else "Token refresh attempt failed"
        )

        return await self.log_event(
            user_id=user_id,
            action=AuditAction.TOKEN_REFRESH,
            entity_type="user",
            entity_id=user_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
        )

    async def log_data_change(
        self,
        user_id: uuid.UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """
        Log data modification (create, update, delete).

        This method is used to track GDPR-compliant data modifications
        with before/after values.

        Args:
            user_id: User who performed the action
            action: Type of action (CREATE, UPDATE, DELETE)
            entity_type: Type of entity affected
            entity_id: UUID of affected entity
            old_values: Values before the action (for UPDATE/DELETE)
            new_values: Values after the action (for CREATE/UPDATE)
            description: Human-readable description
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing

        Returns:
            Created AuditLog instance

        Example:
            # Log user profile update
            await audit_service.log_data_change(
                user_id=current_user.id,
                action=AuditAction.UPDATE,
                entity_type="user",
                entity_id=target_user.id,
                old_values={"email": "old@example.com"},
                new_values={"email": "new@example.com"},
                description="User email updated",
                ip_address="192.168.1.1"
            )

            # Log account creation
            await audit_service.log_data_change(
                user_id=admin_user.id,
                action=AuditAction.CREATE,
                entity_type="account",
                entity_id=new_account.id,
                new_values={"name": "Savings", "balance": 1000.00},
                description="New account created"
            )
        """
        return await self.log_event(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=AuditStatus.SUCCESS,
        )

    async def get_user_audit_logs(
        self,
        user_id: uuid.UUID,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        status: AuditStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs for a specific user (GDPR right to access).

        This method is used for:
        - Users viewing their own audit logs
        - Admins viewing user's action history

        Args:
            user_id: UUID of the user
            action: Filter by action type
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            offset: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of AuditLog instances, total count)

        Example:
            # Get user's login history
            logs, total = await audit_service.get_user_audit_logs(
                user_id=user.id,
                action=AuditAction.LOGIN,
                offset=0,
                limit=20
            )
        """
        logs = await self.audit_repo.get_user_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

        total = await self.audit_repo.count_user_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        return logs, total

    async def get_all_audit_logs(
        self,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        status: AuditStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """
        Get all audit logs with filtering (admin only).

        Args:
            action: Filter by action type
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            offset: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of AuditLog instances, total count)

        Example:
            # Get all failed login attempts in last week
            logs, total = await audit_service.get_all_audit_logs(
                action=AuditAction.LOGIN_FAILED,
                start_date=datetime.now(UTC) - timedelta(days=7)
            )
        """
        logs = await self.audit_repo.get_all_logs(
            action=action,
            entity_type=entity_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

        total = await self.audit_repo.count_all_logs(
            action=action,
            entity_type=entity_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        return logs, total
