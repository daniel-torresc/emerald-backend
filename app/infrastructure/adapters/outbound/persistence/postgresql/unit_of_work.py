"""
PostgreSQL implementation of Unit of Work pattern.

This module implements the Unit of Work pattern for managing database transactions
and coordinating repository operations.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.account_repository import (
    PostgresAccountRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.account_share_repository import (
    PostgresAccountShareRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.audit_log_repository import (
    PostgresAuditLogRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.role_repository import (
    PostgresRoleRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.user_repository import (
    PostgresUserRepository,
)


class PostgresUnitOfWork(UnitOfWorkPort):
    """
    PostgreSQL implementation of Unit of Work pattern.

    Manages database transactions and provides access to all repositories.
    All repositories share the same SQLAlchemy session, ensuring that all
    operations within a transaction are atomic.

    Usage:
        async with uow:
            # Begin transaction
            user = await uow.users.get_by_id(user_id)
            user.activate()
            await uow.users.update(user)

            account = await uow.accounts.get_by_id(account_id)
            account.deactivate()
            await uow.accounts.update(account)

            await uow.commit()
            # Transaction committed (or automatically on exit)

        # On exception, automatic rollback occurs

    Attributes:
        users: User repository
        accounts: Account repository
        roles: Role repository
        account_shares: Account share repository
        audit_logs: Audit log repository
        refresh_tokens: Refresh token repository
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Unit of Work with a database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session

        # Initialize all repositories with the shared session
        self.users = PostgresUserRepository(session)
        self.accounts = PostgresAccountRepository(session)
        self.roles = PostgresRoleRepository(session)
        self.account_shares = PostgresAccountShareRepository(session)
        self.audit_logs = PostgresAuditLogRepository(session)
        self.refresh_tokens = PostgresRefreshTokenRepository(session)

    async def __aenter__(self) -> "PostgresUnitOfWork":
        """
        Enter async context manager (begin transaction).

        The session is already created, so we just return self.
        The transaction boundary is managed by SQLAlchemy's session.

        Returns:
            Self (UnitOfWork instance)

        Example:
            async with uow:
                # Transaction starts here
                await uow.users.add(user)
                await uow.commit()
                # Transaction committed
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit context manager (commit or rollback).

        If an exception occurred during the context, rollback the transaction.
        Otherwise, commit the transaction.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred

        Example:
            async with uow:
                await uow.users.add(user)
                raise ValueError("Oops!")
                # Automatic rollback on exception
        """
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()
        else:
            # No exception, commit
            await self.commit()

    async def commit(self) -> None:
        """
        Commit the current transaction.

        All changes made through repositories will be persisted to the database.
        This flushes pending changes and commits the transaction.

        Example:
            async with uow:
                user = await uow.users.get_by_id(user_id)
                user.activate()
                await uow.users.update(user)
                await uow.commit()  # Explicit commit
        """
        await self._session.commit()

    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        All changes made through repositories will be discarded.
        The database state will remain unchanged.

        Example:
            async with uow:
                try:
                    user = await uow.users.get_by_id(user_id)
                    user.activate()
                    await uow.users.update(user)

                    # Something went wrong
                    if some_condition:
                        await uow.rollback()
                        return

                    await uow.commit()
                except Exception:
                    await uow.rollback()
                    raise
        """
        await self._session.rollback()

    async def close(self) -> None:
        """
        Close the database session.

        This should be called when the UnitOfWork is no longer needed.
        Typically not needed when using context managers.

        Example:
            uow = PostgresUnitOfWork(session)
            try:
                await uow.users.add(user)
                await uow.commit()
            finally:
                await uow.close()
        """
        await self._session.close()
