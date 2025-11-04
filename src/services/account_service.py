"""
Account management service for CRUD operations.

This module provides:
- Create account with validation (unique name per user)
- Get account by ID (with permission check - Phase 2B)
- List user's accounts with pagination and filtering
- Update account (name and is_active)
- Soft delete account
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import AlreadyExistsError, NotFoundError
from src.models.account import Account
from src.models.audit_log import AuditAction
from src.models.enums import AccountType
from src.models.user import User
from src.repositories.account_repository import AccountRepository
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AccountService:
    """
    Service class for account management operations.

    This service handles:
    - Account creation with uniqueness validation
    - Account retrieval with permission checks (Phase 2A: owner only)
    - Account listing and filtering
    - Account updates (name and is_active)
    - Account soft deletion

    All methods require an active database session.
    Audit logging is performed for all mutating operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize AccountService with database session.

        Args:
            db: Async database session
        """
        self.db = db
        self.account_repo = AccountRepository(db)
        self.audit_service = AuditService(db)

    async def create_account(
        self,
        user_id: uuid.UUID,
        account_name: str,
        account_type: AccountType,
        currency: str,
        opening_balance: Decimal,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Account:
        """
        Create new financial account for user.

        Creates an account with the specified details. The account name must be
        unique per user (case-insensitive). Currency is immutable after creation.

        Args:
            user_id: ID of user who will own the account
            account_name: Descriptive account name (1-100 characters, unique per user)
            account_type: Type of account (savings, credit_card, etc.)
            currency: ISO 4217 currency code (3 uppercase letters)
            opening_balance: Initial account balance (can be negative for loans)
            current_user: Currently authenticated user (for audit logging)
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Created Account instance with all fields populated

        Raises:
            AlreadyExistsError: If account name already exists for user
            NotFoundError: If user_id does not exist (foreign key constraint)

        Example:
            account = await account_service.create_account(
                user_id=user.id,
                account_name="Chase Checking",
                account_type=AccountType.SAVINGS,
                currency="USD",
                opening_balance=Decimal("1000.00"),
                current_user=user
            )
        """
        # Validate account name uniqueness
        if await self.account_repo.exists_by_name(user_id, account_name):
            logger.warning(
                f"User {user_id} attempted to create account with duplicate name: {account_name}"
            )
            raise AlreadyExistsError(
                f"Account name '{account_name}' already exists. Please choose a different name."
            )

        # Validate currency format (ISO 4217: 3 uppercase letters)
        if not (len(currency) == 3 and currency.isalpha() and currency.isupper()):
            logger.warning(
                f"User {user_id} attempted to create account with invalid currency: {currency}"
            )
            raise ValueError(
                f"Invalid currency code '{currency}'. Must be 3 uppercase letters (e.g., USD, EUR, GBP)"
            )

        # Create account
        # Phase 2: current_balance = opening_balance (no transactions yet)
        account = await self.account_repo.create(
            user_id=user_id,
            account_name=account_name,
            account_type=account_type,
            currency=currency,
            opening_balance=opening_balance,
            current_balance=opening_balance,  # Initially same as opening balance
            is_active=True,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        logger.info(
            f"Created account {account.id} ({account.account_name}) for user {user_id}"
        )

        # Log audit event
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE,
            entity_type="account",
            entity_id=account.id,
            description=f"Created account '{account.account_name}' ({account.account_type.value}, {account.currency})",
            extra_metadata={
                "account_name": account.account_name,
                "account_type": account.account_type.value,
                "currency": account.currency,
                "opening_balance": str(opening_balance),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        return account

    async def get_account(
        self,
        account_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
    ) -> Account:
        """
        Get account by ID.

        Phase 2A: Only account owner can access.
        Phase 2B: Will check permission level (owner, editor, viewer).

        Args:
            account_id: ID of the account to retrieve
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation

        Returns:
            Account instance

        Raises:
            NotFoundError: If account not found or user has no access

        Example:
            account = await account_service.get_account(account_id, current_user)
        """
        account = await self.account_repo.get_by_id(account_id)

        if not account:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError(f"Account")

        # Phase 2A: Only owner can access
        # Phase 2B: Will use PermissionService to check access level
        if account.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to access account {account_id} without permission"
            )
            raise NotFoundError(f"Account")  # Don't reveal account exists

        return account

    async def list_accounts(
        self,
        user_id: uuid.UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
        account_type: AccountType | None = None,
    ) -> list[Account]:
        """
        List all accounts for a user with pagination and filtering.

        Phase 2A: User can only list their own accounts.
        Phase 2B: Will also include accounts shared with the user.

        Args:
            user_id: ID of the user whose accounts to list
            current_user: Currently authenticated user
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (max 100)
            is_active: Filter by active status (None = all)
            account_type: Filter by account type (None = all types)

        Returns:
            List of Account instances

        Raises:
            PermissionError: If user attempts to list another user's accounts

        Example:
            accounts = await account_service.list_accounts(
                user_id=user.id,
                current_user=user,
                is_active=True,
                limit=20
            )
        """
        # Phase 2A: User can only list their own accounts
        # Phase 2B: Admins can list any user's accounts
        if user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to list accounts for user {user_id}"
            )
            raise PermissionError("You can only list your own accounts")

        # Enforce maximum limit
        if limit > 100:
            limit = 100

        accounts = await self.account_repo.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            is_active=is_active,
            account_type=account_type,
        )

        return accounts

    async def update_account(
        self,
        account_id: uuid.UUID,
        current_user: User,
        account_name: str | None = None,
        is_active: bool | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Account:
        """
        Update account details.

        Only account name and is_active can be updated.
        Currency, balances, and account_type are immutable.

        Phase 2A: Only owner can update.
        Phase 2B: Owner and editor can update (owner can change is_active).

        Args:
            account_id: ID of the account to update
            current_user: Currently authenticated user
            account_name: New account name (optional, validates uniqueness)
            is_active: New active status (optional)
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Updated Account instance

        Raises:
            NotFoundError: If account not found or user has no access
            AlreadyExistsError: If new account name already exists for user

        Example:
            account = await account_service.update_account(
                account_id=account.id,
                current_user=user,
                account_name="New Name",
                is_active=True
            )
        """
        # Get account and check permission
        account = await self.get_account(account_id, current_user, request_id)

        # Phase 2A: Only owner can update
        if account.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to update account {account_id} without permission"
            )
            raise NotFoundError(f"Account")

        # Track changes for audit log
        changes = {}

        # Update account name if provided
        if account_name is not None and account_name != account.account_name:
            # Validate name uniqueness
            if await self.account_repo.exists_by_name(
                account.user_id, account_name, exclude_id=account_id
            ):
                logger.warning(
                    f"User {account.user_id} attempted to rename account to duplicate name: {account_name}"
                )
                raise AlreadyExistsError(
                    f"Account name '{account_name}' already exists. Please choose a different name."
                )

            changes["account_name"] = {
                "old": account.account_name,
                "new": account_name,
            }
            account.account_name = account_name

        # Update is_active if provided
        if is_active is not None and is_active != account.is_active:
            changes["is_active"] = {
                "old": account.is_active,
                "new": is_active
            }
            account.is_active = is_active

        # If no changes, return account as-is
        if not changes:
            return account

        # Update audit fields
        account.updated_by = current_user.id

        # Save changes
        account = await self.account_repo.update(account)

        logger.info(f"Updated account {account.id}: {changes}")

        # Log audit event
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="account",
            entity_id=account.id,
            description=f"Updated account '{account.account_name}'",
            extra_metadata={"changes": changes},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        return account

    async def delete_account(
        self,
        account_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Soft delete account.

        Sets deleted_at timestamp. Account is excluded from normal queries but
        transaction history is preserved for regulatory compliance.

        Phase 2A: Only owner can delete.
        Phase 2B: Only owner can delete (editors and viewers cannot).

        Args:
            account_id: ID of the account to delete
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Raises:
            NotFoundError: If account not found or user has no access

        Example:
            await account_service.delete_account(account_id, current_user)
        """
        # Get account and check permission
        account = await self.get_account(account_id, current_user, request_id)

        # Phase 2A: Only owner can delete
        if account.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to delete account {account_id} without permission"
            )
            raise NotFoundError(f"Account")

        # Soft delete account
        await self.account_repo.soft_delete(account)

        logger.info(f"Soft deleted account {account.id} ({account.account_name})")

        # Log audit event
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="account",
            entity_id=account.id,
            description=f"Deleted account '{account.account_name}'",
            extra_metadata={
                "account_name": account.account_name,
                "account_type": account.account_type.value,
                "currency": account.currency,
                "final_balance": str(account.current_balance),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def count_user_accounts(
        self,
        user_id: uuid.UUID,
        current_user: User,
    ) -> int:
        """
        Count total accounts for a user.

        Args:
            user_id: ID of the user
            current_user: Currently authenticated user

        Returns:
            Total count of active accounts

        Raises:
            PermissionError: If user attempts to count another user's accounts

        Example:
            count = await account_service.count_user_accounts(user.id, user)
        """
        # User can only count their own accounts
        if user_id != current_user.id and not current_user.is_admin:
            raise PermissionError("You can only count your own accounts")

        return await self.account_repo.count_user_accounts(user_id, is_active=True)
