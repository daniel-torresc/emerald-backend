"""
Account type management service for CRUD operations.

This module provides:
- Create account type (admin only)
- Get account type details
- List/search account types with filters
- Update account type (admin only)
- Deactivate account type (admin only)

All state-changing operations are logged to audit trail.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import AlreadyExistsError, NotFoundError
from src.models import AuditAction
from src.models.user import User
from src.repositories.account_type_repository import AccountTypeRepository
from src.schemas.account_type import (
    AccountTypeCreate,
    AccountTypeListItem,
    AccountTypeResponse,
    AccountTypeUpdate,
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AccountTypeService:
    """
    Service class for account type management operations.

    This service handles:
    - Account type creation (with uniqueness validation)
    - Account type retrieval by ID or key
    - Account type listing (all, active only, ordered)
    - Account type updates (with key immutability)
    - Account type deactivation (soft disable)

    All methods require an active database session.
    Admin-only operations: create, update, deactivate
    Authenticated user operations: get, list (all authenticated users can access)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AccountTypeService with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.account_type_repo = AccountTypeRepository(session)
        self.audit_service = AuditService(session)

    async def create_account_type(
        self,
        data: AccountTypeCreate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AccountTypeResponse:
        """
        Create a new account type (admin only).

        Validates uniqueness of key before creation.
        Logs creation to audit trail.

        Args:
            data: Account type creation data
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AccountTypeResponse with created account type data

        Raises:
            AlreadyExistsError: If key already exists

        Example:
            account_type = await service.create_account_type(
                data=AccountTypeCreate(
                    key="hsa",
                    name="Health Savings Account",
                    description="Tax-advantaged medical savings account",
                    sort_order=4
                ),
                current_user=admin_user
            )
        """
        # Check for duplicate key
        exists = await self.account_type_repo.exists_by_key(data.key)
        if exists:
            logger.warning(
                f"Account type creation failed: key '{data.key}' already exists"
            )
            raise AlreadyExistsError(
                f"Account type with key '{data.key}' already exists"
            )

        # Create account type
        account_type = await self.account_type_repo.create(
            key=data.key,
            name=data.name,
            description=data.description,
            icon_url=data.icon_url,
            sort_order=data.sort_order,
        )

        # Commit transaction
        await self.session.commit()

        logger.info(
            f"Account type created: {account_type.id} ('{account_type.key}') by admin {current_user.id}"
        )

        # Log to audit trail
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE_ACCOUNT_TYPE,
            entity_type="account_type",
            entity_id=account_type.id,
            new_values={
                "key": account_type.key,
                "name": account_type.name,
                "sort_order": account_type.sort_order,
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return AccountTypeResponse.model_validate(account_type)

    async def get_account_type(
        self,
        account_type_id: uuid.UUID,
    ) -> AccountTypeResponse:
        """
        Get account type by ID.

        Available to all authenticated users.
        Returns account type regardless of is_active status.

        Args:
            account_type_id: Account type UUID

        Returns:
            AccountTypeResponse with account type data

        Raises:
            NotFoundError: If account type not found

        Example:
            account_type = await service.get_account_type(account_type_id)
        """
        account_type = await self.account_type_repo.get_by_id(account_type_id)

        if not account_type:
            raise NotFoundError(f"Account type with ID {account_type_id} not found")

        return AccountTypeResponse.model_validate(account_type)

    async def get_by_key(
        self,
        key: str,
    ) -> AccountTypeResponse:
        """
        Get account type by key.

        Available to all authenticated users.
        Useful for account type lookup by identifier.

        Args:
            key: Account type key (case-insensitive)

        Returns:
            AccountTypeResponse with account type data

        Raises:
            NotFoundError: If account type not found

        Example:
            account_type = await service.get_by_key("checking")
        """
        account_type = await self.account_type_repo.get_by_key(key)

        if not account_type:
            raise NotFoundError(f"Account type with key '{key}' not found")

        return AccountTypeResponse.model_validate(account_type)

    async def list_account_types(
        self,
    ) -> list[AccountTypeListItem]:
        """
        List all account types.

        Available to all authenticated users.
        Returns all account types ordered by sort_order, then name.

        Returns:
            List of AccountTypeListItem instances

        Example:
            # Get all types
            types = await service.list_account_types()
        """
        account_types = await self.account_type_repo.get_all_ordered()

        return [
            AccountTypeListItem.model_validate(account_type)
            for account_type in account_types
        ]

    async def update_account_type(
        self,
        account_type_id: uuid.UUID,
        data: AccountTypeUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AccountTypeResponse:
        """
        Update account type (admin only).

        Key field is immutable and cannot be changed.
        Logs update to audit trail.

        Args:
            account_type_id: Account type UUID to update
            data: Update data (partial update supported)
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AccountTypeResponse with updated account type data

        Raises:
            NotFoundError: If account type not found

        Example:
            account_type = await service.update_account_type(
                account_type_id=uuid.UUID("..."),
                data=AccountTypeUpdate(
                    is_active=False
                ),
                current_user=admin_user
            )
        """
        # Get existing account type
        account_type = await self.account_type_repo.get_by_id(account_type_id)
        if not account_type:
            raise NotFoundError(f"Account type with ID {account_type_id} not found")

        # Track what changed (for audit log)
        changes = {}

        # Update fields (key is immutable, not included in AccountTypeUpdate schema)
        if data.name is not None:
            changes["name"] = {"old": account_type.name, "new": data.name}
            account_type.name = data.name

        if data.description is not None:
            changes["description"] = {
                "old": account_type.description,
                "new": data.description,
            }
            account_type.description = data.description

        if data.icon_url is not None:
            changes["icon_url"] = {"old": account_type.icon_url, "new": data.icon_url}
            account_type.icon_url = data.icon_url

        if data.sort_order is not None:
            changes["sort_order"] = {
                "old": account_type.sort_order,
                "new": data.sort_order,
            }
            account_type.sort_order = data.sort_order

        # Commit transaction
        await self.session.commit()
        await self.session.refresh(account_type)

        logger.info(
            f"Account type updated: {account_type.id} ('{account_type.key}') by admin {current_user.id}"
        )

        # Log to audit trail
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE_ACCOUNT_TYPE,
            entity_type="account_type",
            entity_id=account_type.id,
            extra_metadata={
                "key": account_type.key,
                "name": account_type.name,
                "changes": changes,
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return AccountTypeResponse.model_validate(account_type)

    async def delete_account_type(
        self,
        account_type_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Delete account type (admin only).

        Hard deletes the account type from database. Can only delete if no accounts
        reference this type (enforced by foreign key constraint).

        Logs deletion to audit trail.

        Args:
            account_type_id: Account type UUID to delete
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Raises:
            NotFoundError: If account type not found

        Example:
            await service.delete_account_type(
                account_type_id=uuid.UUID("..."),
                current_user=admin_user
            )
        """
        # Get account type
        account_type = await self.account_type_repo.get_by_id(account_type_id)
        if not account_type:
            raise NotFoundError(f"Account type with ID {account_type_id} not found")

        # Store details for audit log before deletion
        account_type_key = account_type.key
        account_type_name = account_type.name

        # Hard delete
        await self.account_type_repo.delete(account_type)

        # Commit transaction
        await self.session.commit()

        logger.info(
            f"Account type deleted: {account_type_id} ('{account_type_key}') by admin {current_user.id}"
        )

        # Log to audit trail
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="account_type",
            entity_id=account_type_id,
            extra_metadata={
                "key": account_type_key,
                "name": account_type_name,
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
