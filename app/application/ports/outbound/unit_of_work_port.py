"""Unit of Work port interface."""

from typing import Protocol

from app.application.ports.outbound.account_repository_port import (
    AccountRepositoryPort,
)
from app.application.ports.outbound.account_share_repository_port import (
    AccountShareRepositoryPort,
)
from app.application.ports.outbound.audit_log_repository_port import (
    AuditLogRepositoryPort,
)
from app.application.ports.outbound.refresh_token_repository_port import (
    RefreshTokenRepositoryPort,
)
from app.application.ports.outbound.role_repository_port import RoleRepositoryPort
from app.application.ports.outbound.user_repository_port import UserRepositoryPort


class UnitOfWorkPort(Protocol):
    """
    Unit of Work interface for managing transactions.

    The Unit of Work pattern maintains a list of objects affected by a business
    transaction and coordinates the writing out of changes. It ensures that all
    repository operations within a transaction are committed or rolled back together.

    Usage:
        async with uow:
            user = await uow.users.get_by_id(user_id)
            user.activate()
            await uow.users.update(user)
            await uow.commit()  # Commit is automatic on exit, but can be explicit

        # On exception, automatic rollback occurs
    """

    users: UserRepositoryPort
    accounts: AccountRepositoryPort
    roles: RoleRepositoryPort
    account_shares: AccountShareRepositoryPort
    audit_logs: AuditLogRepositoryPort
    refresh_tokens: RefreshTokenRepositoryPort

    async def __aenter__(self) -> "UnitOfWorkPort":
        """
        Enter async context manager (begin transaction).

        Returns:
            Self (UnitOfWorkPort instance)
        """
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit context manager (commit or rollback).

        If an exception occurred, the transaction is rolled back.
        Otherwise, the transaction is committed.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        ...

    async def commit(self) -> None:
        """
        Commit the current transaction.

        All changes made through repositories will be persisted.
        """
        ...

    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        All changes made through repositories will be discarded.
        """
        ...
