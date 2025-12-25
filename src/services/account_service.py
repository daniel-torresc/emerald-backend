"""
Account management service for CRUD operations.

This module provides:
- Create account with validation (unique name per user)
- Get account by ID (with permission check - Phase 2B)
- List user's accounts with pagination and filtering
- Update account (name, type, institution, metadata)
- Soft delete account
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.encryption import EncryptionService
from core.exceptions import (
    AlreadyExistsError,
    AuthorizationError,
    EncryptionError,
    NotFoundError,
    ValidationError,
)
from models import AuditAction
from models.account import Account, AccountShare
from models.enums import PermissionLevel
from models.user import User
from repositories import FinancialInstitutionRepository
from repositories.account_repository import AccountRepository
from repositories.account_share_repository import AccountShareRepository
from repositories.account_type_repository import AccountTypeRepository
from repositories.user_repository import UserRepository
from schemas.account import (
    AccountCreate,
    AccountFilterParams,
    AccountListItem,
    AccountUpdate,
)
from schemas.account_share import AccountShareCreate
from schemas.common import PaginatedResponse, PaginationMeta, PaginationParams
from services.audit_service import AuditService
from services.currency_service import CurrencyService
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)


class AccountService:
    """
    Service class for account management operations.

    This service handles:
    - Account creation with uniqueness validation
    - Account retrieval with permission checks (Phase 2A: owner only)
    - Account listing and filtering
    - Account updates (name, type, institution, metadata)
    - Account soft deletion

    All methods require an active database session.
    Audit logging is performed for all mutating operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AccountService with database session and encryption service.

        Args:
            session: Async database session
        """
        self.session = session
        self.account_repo = AccountRepository(session)
        self.account_type_repo = AccountTypeRepository(session)
        self.financial_institution_repo = FinancialInstitutionRepository(session)
        self.share_repo = AccountShareRepository(session)
        self.user_repo = UserRepository(session)
        self.permission_service = PermissionService(session)
        self.audit_service = AuditService(session)
        self.currency_service = CurrencyService(session)
        self.encryption_service = EncryptionService()

    async def create_account(
        self,
        user: User,
        data: AccountCreate,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Account:
        """
        Create new financial account for user.

        Creates an account with the specified details. The account name must be
        unique per user (case-insensitive). Currency is immutable after creation.
        Financial institution is mandatory (all accounts must be linked to an institution).

        Args:
            user: User who will own the account
            data: Account details
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Created Account instance with all fields populated

        Raises:
            AlreadyExistsError: If account name already exists for user
            NotFoundError: If user_id does not exist or account type not found
            ValidationError: If account type is inactive or institution not found or is not active
            AuthorizationError: If user cannot access the account type (custom type owned by another user)

        Example:
            account = await account_service.create_account(
                user=user,
                data=data
            )
        """
        # Validate account name uniqueness
        if await self.account_repo.exists_by_name(user.id, data.account_name):
            logger.warning(
                f"User {user.id} attempted to create account with duplicate name: {data.account_name}"
            )
            raise AlreadyExistsError(
                f"Account name '{data.account_name}' already exists. Please choose a different name."
            )

        # Validate account type exists and is active
        account_type = await self.account_type_repo.get_by_id(data.account_type_id)
        if not account_type:
            logger.warning(
                f"User {user.id} attempted to create account with non-existent "
                f"account type: {data.account_type_id}"
            )
            raise NotFoundError("Account type not found")

        # Note: All account types are system-wide and accessible to all users
        # No per-user custom types - all types are managed globally

        # Validate currency is supported (ISO 4217 currency codes)
        if not self.currency_service.is_supported(data.currency):
            supported_codes = ", ".join(self.currency_service.get_supported_codes())
            logger.warning(
                f"User {user.id} attempted to create account with unsupported currency: {data.currency}"
            )
            raise ValidationError(
                f"Unsupported currency code '{data.currency}'. "
                f"Supported currencies: {supported_codes}"
            )

        # Validate financial institution exists
        financial_institution = await self.financial_institution_repo.exists(
            data.financial_institution_id
        )
        if not financial_institution:
            logger.warning(
                f"User {user.id} attempted to create account with non existent "
                f"institution: {data.financial_institution_id}"
            )
            raise ValidationError(
                "Financial institution not found. "
                "Please select a different institution."
            )

        # Process IBAN if provided
        encrypted_iban = None
        iban_last_four = None
        if data.iban:
            try:
                # Encrypt full IBAN
                encrypted_iban = self.encryption_service.encrypt(data.iban)
                # Extract last 4 digits for display
                iban_last_four = data.iban[-4:] if len(data.iban) >= 4 else data.iban
                logger.info("IBAN encrypted successfully for account creation")
            except Exception as e:
                logger.error(f"IBAN encryption failed: {e}")
                raise EncryptionError("Failed to encrypt IBAN") from e

        # Create account
        # Phase 2: current_balance = opening_balance (no transactions yet)
        account = Account(
            user_id=user.id,
            financial_institution_id=data.financial_institution_id,
            account_name=data.account_name,
            account_type_id=data.account_type_id,
            currency=data.currency,
            opening_balance=data.opening_balance,
            current_balance=data.opening_balance,  # Initially same as opening balance
            color_hex=data.color_hex,
            icon_url=data.icon_url,
            iban=encrypted_iban,
            iban_last_four=iban_last_four,
            notes=data.notes,
            created_by=user.id,
            updated_by=user.id,
        )
        account = await self.account_repo.add(account)
        await self.session.commit()

        logger.info(
            f"Created account {account.id} ({account.account_name}) for user {user.id}"
        )

        # Log audit event
        await self.audit_service.log_event(
            user_id=user.id,
            action=AuditAction.CREATE,
            entity_type="account",
            entity_id=account.id,
            description=f"Created account '{account.account_name}' at {account.financial_institution.short_name} ({account.account_type.name}, {account.currency})",
            extra_metadata={
                "account_name": account.account_name,
                "account_type_id": str(data.account_type_id),
                "account_type_key": account.account_type.key,
                "account_type_name": account.account_type.name,
                "currency": account.currency,
                "opening_balance": str(data.opening_balance),
                "financial_institution_id": str(data.financial_institution_id),
                "financial_institution_name": account.financial_institution.short_name,
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

        Checks if user has access to the account (owner or shared with them).

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
            raise NotFoundError("Account")

        # Check if user has access (owner or shared with them)
        permission = await self.permission_service.get_user_permission(
            current_user.id, account_id
        )

        if permission is None:
            logger.warning(
                f"User {current_user.id} attempted to access account {account_id} without permission"
            )
            raise NotFoundError("Account")  # Don't reveal account exists

        return account

    async def list_user_accounts(
        self,
        user_id: uuid.UUID,
        current_user: User,
        pagination: PaginationParams,
        filters: AccountFilterParams,
    ) -> PaginatedResponse[AccountListItem]:
        """
        List all accounts for a user with pagination and filtering.

        Returns paginated response with metadata.

        Args:
            user_id: ID of the user whose accounts to list
            current_user: Currently authenticated user
            pagination: Pagination parameters (page, page_size)
            filters: Filter parameters (account_type_id, financial_institution_id)

        Returns:
            PaginatedResponse with AccountListItem instances and metadata

        Raises:
            PermissionError: If user attempts to list another user's accounts

        Example:
            response = await account_service.list_accounts_paginated(
                user_id=user.id,
                current_user=user,
                pagination=PaginationParams(page=1, page_size=20),
                filters=AccountFilterParams(account_type_id=checking_type_id)
            )
        """
        # User can only list their own accounts (admins can list any user's accounts)
        if user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to list accounts for user {user_id}"
            )
            raise PermissionError("You can only list your own accounts")

        # Get owned accounts
        owned_accounts = await self.account_repo.get_by_user(
            user_id=user_id,
            account_type_id=filters.account_type_id,
            financial_institution_id=filters.financial_institution_id,
        )

        # Get shared accounts (accounts where user has a share)
        shared_accounts = await self.account_repo.get_shared_with_user(
            user_id=user_id,
            account_type_id=filters.account_type_id,
            financial_institution_id=filters.financial_institution_id,
        )

        # Combine and deduplicate (in case user owns AND has a share on same account)
        account_ids_seen = {acc.id for acc in owned_accounts}
        all_accounts = list(owned_accounts)

        for shared_acc in shared_accounts:
            if shared_acc.id not in account_ids_seen:
                all_accounts.append(shared_acc)
                account_ids_seen.add(shared_acc.id)

        # Get total count
        total = len(all_accounts)

        # Apply pagination to combined results
        paginated_accounts = all_accounts[
            pagination.offset : pagination.offset + pagination.page_size
        ]

        # Convert to AccountListItem
        account_items = [
            AccountListItem.model_validate(account) for account in paginated_accounts
        ]

        # Calculate total pages
        total_pages = PaginationParams.calculate_total_pages(
            total, pagination.page_size
        )

        return PaginatedResponse(
            data=account_items,
            meta=PaginationMeta(
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
            ),
        )

    async def update_account(
        self,
        account_id: uuid.UUID,
        data: AccountUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Account:
        """
        Update account details.

        Updateable fields: account_name, account_type_id, financial_institution_id, color_hex, icon_url, notes
        Immutable fields: currency, balances, iban

        Phase 2A: Only owner can update.
        Phase 2B: Owner and editor can update.

        Args:
            account_id: ID of the account to update
            data: AccountUpdate schema with fields to update
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Updated Account instance

        Raises:
            NotFoundError: If account or account type not found or user has no access
            AlreadyExistsError: If new account name already exists for user
            ValidationError: If institution not found

        Example:
            account = await account_service.update_account(
                account_id=account.id,
                data=AccountUpdate(account_name="New Name"),
                current_user=user,
            )
        """
        # 1. Get account and check permission
        account = await self.get_account(account_id, current_user, request_id)

        # Phase 2A: Only owner can update
        if account.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to update account {account_id} without permission"
            )
            raise NotFoundError("Account")

        # 2. Get only provided fields
        update_dict = data.model_dump(exclude_unset=True)

        if not update_dict:
            return account  # Nothing to update

        # 3. Business validations (only for changing fields)
        if (
            "account_name" in update_dict
            and update_dict["account_name"] != account.account_name
        ):
            if await self.account_repo.exists_by_name(
                account.user_id, update_dict["account_name"], exclude_id=account_id
            ):
                logger.warning(
                    f"User {account.user_id} attempted to rename account to duplicate name: {update_dict['account_name']}"
                )
                raise AlreadyExistsError(
                    f"Account name '{update_dict['account_name']}' already exists. Please choose a different name."
                )

        if "account_type_id" in update_dict:
            account_type = await self.account_type_repo.get_by_id(
                update_dict["account_type_id"]
            )
            if not account_type:
                logger.warning(
                    f"User {current_user.id} attempted to update account {account_id} "
                    f"with non-existent account type: {update_dict['account_type_id']}"
                )
                raise NotFoundError("Account type not found")

        if "financial_institution_id" in update_dict:
            if not await self.financial_institution_repo.exists(
                update_dict["financial_institution_id"]
            ):
                logger.warning(
                    f"User {current_user.id} attempted to update account {account_id} "
                    f"with non existent institution: {update_dict['financial_institution_id']}"
                )
                raise ValidationError(
                    "Financial institution not found. "
                    "Please select a different institution."
                )

        # 4. Capture old values for audit
        old_values = {
            "account_name": account.account_name,
            "account_type_id": str(account.account_type_id)
            if account.account_type_id
            else None,
            "financial_institution_id": str(account.financial_institution_id)
            if account.financial_institution_id
            else None,
            "color_hex": account.color_hex,
            "icon_url": str(account.icon_url) if account.icon_url else None,
            "notes": account.notes,
        }

        # 5. Apply changes to model instance
        for key, value in update_dict.items():
            setattr(account, key, value)
        account.updated_by = current_user.id

        # 6. Persist
        account = await self.account_repo.update(account)

        # 7. Capture new values for audit
        new_values = {
            "account_name": account.account_name,
            "account_type_id": str(account.account_type_id)
            if account.account_type_id
            else None,
            "financial_institution_id": str(account.financial_institution_id)
            if account.financial_institution_id
            else None,
            "color_hex": account.color_hex,
            "icon_url": str(account.icon_url) if account.icon_url else None,
            "notes": account.notes,
        }

        logger.info(
            f"Updated account {account.id}: changed_fields={list(update_dict.keys())}"
        )

        # 8. Audit log with old/new values
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="account",
            entity_id=account.id,
            old_values=old_values,
            new_values=new_values,
            extra_metadata={"changed_fields": list(update_dict.keys())},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # 9. Commit transaction
        await self.session.commit()

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
            raise NotFoundError("Account")

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
                "account_type_id": str(account.account_type_id),
                "account_type_key": account.account_type.key,
                "account_type_name": account.account_type.name,
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

        return await self.account_repo.count_user_accounts(user_id)

    # =============================================================================
    # Account Sharing Methods (Phase 2B)
    # =============================================================================

    async def share_account(
        self,
        current_user: User,
        account_id: uuid.UUID,
        data: AccountShareCreate,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AccountShare:
        """
        Share account with another user.

        Creates a new AccountShare record granting access to target user.
        Only the account owner can share accounts.

        Args:
            current_user: Currently authenticated user (must be owner)
            account_id: ID of account to share
            data: Account share data
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Created AccountShare instance

        Raises:
            NotFoundError: If account or target user not found
            InsufficientPermissionsError: If current user is not owner
            ValidationError: If trying to share with self or grant owner permission
            AlreadyExistsError: If account already shared with target user

        Example:
            share = await account_service.share_account(
                account_id=account.id,
                target_user_id=partner.id,
                permission_level=PermissionLevel.EDITOR,
                current_user=owner
            )
        """
        # Verify account exists
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")

        # Check if current user is owner
        await self.permission_service.require_permission(
            current_user.id, account_id, PermissionLevel.owner
        )

        # Validate target user exists and is not deleted
        target_user = await self.user_repo.get_by_id(data.user_id)
        if not target_user:
            raise NotFoundError("User to share with not found")

        # Cannot share with self
        if data.user_id == current_user.id:
            raise ValidationError("Cannot share account with yourself")

        # Cannot grant owner permission (only one owner per account)
        if data.permission_level == PermissionLevel.owner:
            raise ValidationError(
                "Cannot grant owner permission. Each account has exactly one owner."
            )

        # Check if share already exists
        if await self.share_repo.exists_share(data.user_id, account_id):
            raise AlreadyExistsError(
                f"Account already shared with user {target_user.username}"
            )

        # Create share
        account_share = AccountShare(
            account_id=account_id,
            user_id=data.user_id,
            permission_level=data.permission_level,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        created_share = await self.share_repo.add(account_share)
        await self.session.commit()

        logger.info(
            f"User {current_user.id} shared account {account_id} with "
            f"user {data.user_id} ({data.permission_level.value})"
        )

        # Log audit event
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE,
            entity_type="account_share",
            entity_id=created_share.id,
            description=f"Shared account '{account.account_name}' with {target_user.username} ({data.permission_level.value})",
            extra_metadata={
                "account_id": str(account_id),
                "account_name": account.account_name,
                "target_user_id": str(data.user_id),
                "target_username": target_user.username,
                "permission_level": data.permission_level.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        return created_share

    async def list_shares(
        self,
        account_id: uuid.UUID,
        current_user: User,
    ) -> list[AccountShare]:
        """
        List all shares for an account.

        Owner sees all shares, non-owners see only their own share.

        Args:
            account_id: ID of the account
            current_user: Currently authenticated user

        Returns:
            List of AccountShare instances

        Raises:
            NotFoundError: If account not found or user has no access

        Example:
            shares = await account_service.list_shares(account.id, user)
        """
        # Verify user has access to account
        await self.permission_service.require_permission(
            current_user.id, account_id, PermissionLevel.viewer
        )

        # Get all shares for account
        shares = await self.share_repo.get_by_account(account_id)

        # If user is not owner, filter to show only their own share
        is_owner = await self.permission_service.is_owner(current_user.id, account_id)

        if not is_owner:
            shares = [s for s in shares if s.user_id == current_user.id]

        return shares

    async def update_share(
        self,
        account_id: uuid.UUID,
        share_id: uuid.UUID,
        permission_level: PermissionLevel,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AccountShare:
        """
        Update permission level for an account share.

        Only the account owner can update share permissions.

        Args:
            account_id: ID of the account
            share_id: ID of the share to update
            permission_level: New permission level
            current_user: Currently authenticated user (must be owner)
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Updated AccountShare instance

        Raises:
            NotFoundError: If account or share not found
            InsufficientPermissionsError: If current user is not owner
            ValidationError: If trying to grant owner permission or change own permission

        Example:
            updated_share = await account_service.update_share(
                account_id=account.id,
                share_id=share.id,
                permission_level=PermissionLevel.EDITOR,
                current_user=owner
            )
        """
        # Check if current user is owner
        await self.permission_service.require_permission(
            current_user.id, account_id, PermissionLevel.owner
        )

        # Get share
        share = await self.share_repo.get_by_id(share_id)
        if not share or share.account_id != account_id:
            raise NotFoundError("Share not found")

        # Cannot grant owner permission
        if permission_level == PermissionLevel.owner:
            raise ValidationError(
                "Cannot grant owner permission. Each account has exactly one owner."
            )

        # Cannot change own owner permission
        if (
            share.user_id == current_user.id
            and share.permission_level == PermissionLevel.owner
        ):
            raise ValidationError("Cannot change your own owner permission")

        # Store old permission for audit
        old_permission = share.permission_level

        # Capture old values for audit
        old_values = {"permission_level": old_permission.value}

        # Update permission
        share.permission_level = permission_level
        share.updated_by = current_user.id

        updated_share = await self.share_repo.update(share)

        # Capture new values for audit
        new_values = {"permission_level": updated_share.permission_level.value}

        logger.info(
            f"User {current_user.id} updated share {share_id} permission "
            f"from {old_permission.value} to {permission_level.value}"
        )

        # Log audit event with old/new values
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="account_share",
            entity_id=share_id,
            old_values=old_values,
            new_values=new_values,
            extra_metadata={
                "account_id": str(account_id),
                "share_user_id": str(share.user_id),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Commit transaction
        await self.session.commit()

        return updated_share

    async def revoke_share(
        self,
        account_id: uuid.UUID,
        share_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Revoke account access from a user.

        Soft deletes the AccountShare record. Only the account owner can revoke access.

        Args:
            account_id: ID of the account
            share_id: ID of the share to revoke
            current_user: Currently authenticated user (must be owner)
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Raises:
            NotFoundError: If account or share not found
            InsufficientPermissionsError: If current user is not owner
            ValidationError: If trying to revoke own owner permission

        Example:
            await account_service.revoke_share(
                account_id=account.id,
                share_id=share.id,
                current_user=owner
            )
        """
        # Check if current user is owner
        await self.permission_service.require_permission(
            current_user.id, account_id, PermissionLevel.owner
        )

        # Get share
        share = await self.share_repo.get_by_id(share_id)
        if not share or share.account_id != account_id:
            raise NotFoundError("Share not found")

        # Cannot revoke own owner permission
        if (
            share.user_id == current_user.id
            and share.permission_level == PermissionLevel.owner
        ):
            raise ValidationError("Cannot revoke your own owner permission")

        # Soft delete share
        await self.share_repo.soft_delete(share)

        logger.info(
            f"User {current_user.id} revoked share {share_id} "
            f"(user {share.user_id}, {share.permission_level.value})"
        )

        # Log audit event
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="account_share",
            entity_id=share_id,
            description=f"Revoked {share.permission_level.value} access from user",
            extra_metadata={
                "account_id": str(account_id),
                "revoked_user_id": str(share.user_id),
                "permission_level": share.permission_level.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def update_balance(
        self,
        account_id: uuid.UUID,
        delta: Decimal,
    ) -> Account:
        """
        Update account balance by delta amount.

        Used by TransactionService when creating/updating/deleting transactions.
        Uses SELECT ... FOR UPDATE to prevent race conditions.

        IMPORTANT: This method should be called within an explicit database transaction.

        Args:
            account_id: Account to update
            delta: Amount to add to current balance (can be negative)

        Returns:
            Updated account with new balance

        Raises:
            NotFoundError: If account not found

        Example:
            # Called from TransactionService within transaction
            async with db.begin():
                account = await account_service.update_balance(
                    account_id=account.id,
                    delta=transaction.amount,
                )
        """
        # Lock row for update
        account = await self.account_repo.get_for_update(account_id)

        if not account:
            logger.warning(f"Account {account_id} not found for balance update")
            raise NotFoundError("Account")

        # Update balance
        old_balance = account.current_balance
        account.current_balance += delta
        new_balance = account.current_balance

        logger.debug(
            f"Updated balance for account {account_id}: {old_balance} + {delta} = {new_balance}"
        )

        return account

    async def recalculate_balance(
        self,
        account_id: uuid.UUID,
        current_user: User,
    ) -> tuple[Decimal, Decimal]:
        """
        Recalculate account balance from scratch.

        Useful for:
        - Balance verification (compare cached vs calculated)
        - Balance repair after data issues
        - Administrative operations

        Args:
            account_id: Account to recalculate
            current_user: Currently authenticated user (for permission check)

        Returns:
            Tuple of (cached_balance, calculated_balance)

        Raises:
            NotFoundError: If account not found
            InsufficientPermissionsError: If user doesn't have access

        Example:
            cached, calculated = await account_service.recalculate_balance(
                account_id=account.id,
                current_user=admin_user,
            )
            if cached != calculated:
                print(f"Balance mismatch: cached={cached}, calculated={calculated}")
        """
        # Import here to avoid circular dependency
        from repositories.transaction_repository import TransactionRepository

        # Check permission (VIEWER or higher can view balance)
        await self.permission_service.require_permission(
            current_user.id, account_id, PermissionLevel.viewer
        )

        account = await self.account_repo.get_by_id(account_id)
        if not account:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError("Account")

        cached_balance = account.current_balance

        # Calculate from transactions
        transaction_repo = TransactionRepository(self.session)
        calculated_balance = await transaction_repo.calculate_account_balance(
            account_id
        )
        calculated_balance += account.opening_balance

        logger.info(
            f"Balance comparison for account {account_id}: "
            f"cached={cached_balance}, calculated={calculated_balance}, "
            f"match={cached_balance == calculated_balance}"
        )

        return cached_balance, calculated_balance

    async def verify_and_fix_balance(
        self,
        account_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Verify balance matches calculation. Fix if mismatch.

        Admin-only operation for balance repair.

        Args:
            account_id: Account to verify and fix
            current_user: Currently authenticated user (must be admin)
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Dictionary with verification results:
            {
                "account_id": str,
                "cached_balance": str,
                "calculated_balance": str,
                "mismatch": bool,
                "fixed": bool,
            }

        Raises:
            NotFoundError: If account not found
            AuthorizationError: If user is not admin

        Example:
            result = await account_service.verify_and_fix_balance(
                account_id=account.id,
                current_user=admin_user,
            )
            if result["fixed"]:
                print(f"Fixed balance mismatch: {result['cached_balance']} -> {result['calculated_balance']}")
        """
        # Admin-only operation
        if not current_user.is_admin:
            logger.warning(
                f"Non-admin user {current_user.id} attempted to verify/fix balance for account {account_id}"
            )
            raise AuthorizationError("Admin access required")

        # Recalculate balance
        cached, calculated = await self.recalculate_balance(account_id, current_user)

        mismatch = cached != calculated

        if mismatch:
            # Fix balance
            account = await self.account_repo.get_for_update(account_id)
            account.current_balance = calculated

            logger.warning(
                f"Balance mismatch repaired for account {account_id}: "
                f"{cached} -> {calculated}"
            )

            # Audit log
            await self.audit_service.log_event(
                user_id=current_user.id,
                action=AuditAction.UPDATE,
                entity_type="account",
                entity_id=account_id,
                description="Balance mismatch repaired",
                old_values={"current_balance": str(cached)},
                new_values={"current_balance": str(calculated)},
                extra_metadata={
                    "balance_delta": str(calculated - cached),
                    "reason": "administrative_repair",
                },
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )

        return {
            "account_id": str(account_id),
            "cached_balance": str(cached),
            "calculated_balance": str(calculated),
            "mismatch": mismatch,
            "fixed": mismatch,
        }
