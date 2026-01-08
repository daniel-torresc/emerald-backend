"""
Transaction management service for CRUD operations and business logic.

This module provides:
- Create transaction with permission checks and balance updates
- Get transaction by ID with permission checks
- List and search transactions with advanced filters
- Update transaction with balance delta calculation
- Delete transaction (soft delete) with balance updates
- Split transaction into multiple parts
- Join split transactions back together
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from models import AuditAction, PermissionLevel, Transaction, User
from repositories import AccountRepository, CardRepository, TransactionRepository
from schemas import (
    PaginationParams,
    TransactionCreate,
    TransactionFilterParams,
    TransactionSortParams,
    TransactionUpdate,
)
from .audit_service import AuditService
from .currency_service import CurrencyService
from .permission_service import PermissionService

logger = logging.getLogger(__name__)


class TransactionService:
    """
    Service class for transaction management operations.

    This service handles:
    - Transaction CRUD with permission checks
    - Balance calculations and updates
    - Transaction splitting and joining
    - Advanced search and filtering

    All methods require an active database session.
    Audit logging is performed for all mutating operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize TransactionService with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.account_repo = AccountRepository(session)
        self.card_repo = CardRepository(session)
        self.permission_service = PermissionService(session)
        self.currency_service = CurrencyService(session)
        self.audit_service = AuditService(session)

    async def create_transaction(
        self,
        account_id: uuid.UUID,
        data: TransactionCreate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Transaction:
        """
        Create new transaction with validation and balance update.

        Steps:
        1. Check user has account access (EDITOR or OWNER permission)
        2. Get account and verify currency matches
        3. Verify account is not deleted and is active
        4. Create transaction in database
        5. Update account balance (in same transaction)
        6. Log audit entry
        8. Return created transaction

        Args:
            account_id: Account to add transaction to
            data: Transaction to create
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Created Transaction instance with all fields populated

        Raises:
            NotFoundError: If account not found
            AuthorizationError: If user doesn't have permission
            ValidationError: If currency mismatch or invalid data
        """
        # Validate permissions (EDITOR or OWNER can create transactions)
        has_permission = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=account_id,
            required_permission=PermissionLevel.editor,
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} attempted to create transaction for account {account_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to create transactions for this account"
            )

        # Get account and validate
        account = await self.account_repo.get_by_id(account_id)
        if account is None:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError("Account")

        # Validate currency is supported
        if not self.currency_service.is_supported(data.currency):
            supported_codes = ", ".join(self.currency_service.get_supported_codes())
            logger.warning(
                f"User {current_user.id} attempted to create transaction with unsupported currency: {data.currency}"
            )
            raise ValidationError(
                f"Unsupported currency code '{data.currency}'. "
                f"Supported currencies: {supported_codes}"
            )

        # Validate currency matches account
        if data.currency != account.currency:
            logger.warning(
                f"Currency mismatch: transaction={data.currency}, account={account.currency}"
            )
            raise ValidationError(
                f"Transaction currency ({data.currency}) must match account currency ({account.currency})"
            )

        # Validate amount is non-zero
        if data.amount == 0:
            raise ValidationError("Transaction amount cannot be zero")

        # Validate card if provided
        if data.card_id is not None:
            card = await self.card_repo.get_by_id_for_user(
                card_id=data.card_id,
                user_id=current_user.id,
            )
            if card is None:
                logger.warning(
                    f"Card {data.card_id} not found or unauthorized for user {current_user.id}"
                )
                raise NotFoundError("Card")

        transaction = Transaction(
            account_id=account_id,
            transaction_date=data.transaction_date,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            merchant=data.merchant,
            card_id=data.card_id,
            transaction_type=data.transaction_type,
            user_notes=data.user_notes,
            value_date=data.value_date,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        transaction = await self.transaction_repo.create(transaction)

        # Update account balance with row lock
        account = await self.account_repo.get_for_update(account_id)
        old_balance = account.current_balance
        account.current_balance += data.amount
        new_balance = account.current_balance

        logger.info(
            f"Created transaction {transaction.id} for account {account_id}, "
            f"updated balance: {old_balance} -> {new_balance}"
        )

        await self.session.commit()

        # Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE,
            entity_type="transaction",
            entity_id=transaction.id,
            description=f"Created transaction: {data.description} ({data.amount} {data.currency})",
            new_values={
                "transaction_date": str(data.transaction_date),
                "amount": str(data.amount),
                "currency": data.currency,
                "description": data.description,
                "merchant": data.merchant,
                "card_id": str(data.card_id) if data.card_id else None,
                "transaction_type": data.transaction_type.value,
            },
            extra_metadata={
                "account_id": str(account_id),
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Refresh to get card relationships
        await self.session.refresh(transaction, ["card"])
        return transaction

    async def get_transaction(
        self,
        transaction_id: uuid.UUID,
        current_user: User,
    ) -> Transaction:
        """
        Get transaction by ID with permission check.

        Args:
            transaction_id: UUID of the transaction
            current_user: Currently authenticated user

        Returns:
            Transaction instance with all relationships loaded

        Raises:
            NotFoundError: If transaction not found
            AuthorizationError: If user doesn't have account access

        Example:
            transaction = await transaction_service.get_transaction(
                transaction_id=transaction_id,
                current_user=user,
            )
        """
        transaction = await self.transaction_repo.get_by_id(transaction_id)

        if transaction is None:
            logger.warning(f"Transaction {transaction_id} not found")
            raise NotFoundError("Transaction")

        # Check user has account access (VIEWER or higher)
        has_permission = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=transaction.account_id,
            required_permission=PermissionLevel.viewer,
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} attempted to access transaction {transaction_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to view this transaction"
            )

        return transaction

    async def list_user_transactions(
        self,
        account_id: uuid.UUID,
        current_user: User,
        pagination: PaginationParams,
        filters: TransactionFilterParams,
        sorting: TransactionSortParams,
    ) -> tuple[list[Transaction], int]:
        """
        Search transactions with pagination and filters.

        Args:
            account_id: Account to search in
            current_user: Currently authenticated user
            pagination: Pagination parameters (page, page_size)
            filters: Filter parameters (dates, amounts, description, etc.)
            sorting: Sort parameters (sort_by, sort_order)

        Returns:
            PaginatedResponse with TransactionResponse objects and metadata

        Raises:
            AuthorizationError: If user doesn't have account access

        Example:
            response = await transaction_service.search(
                account_id=account.id,
                current_user=user,
                pagination=PaginationParams(page=1, page_size=20),
                filters=TransactionFilterParams(
                    description="grocery",
                    amount_min=Decimal("10.00")
                ),
                sorting=TransactionSortParams()
            )
        """
        # Check user has account access (VIEWER or higher)
        has_permission = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=account_id,
            required_permission=PermissionLevel.viewer,
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} attempted to search transactions for account {account_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to view transactions for this account"
            )

        user_transactions = await self.transaction_repo.list_for_user(
            user_id=current_user.id,
            filter_params=filters,
            pagination_params=pagination,
            sort_params=sorting,
        )

        return user_transactions

    async def update_transaction(
        self,
        transaction_id: uuid.UUID,
        data: TransactionUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Transaction:
        """
        Update transaction with permission check and balance recalculation.

        Steps:
        1. Get existing transaction
        2. Check user can edit (creator, admin, or account owner)
        3. Validate provided fields
        4. Calculate balance delta if amount changing
        5. Apply changes and persist
        6. Update account balance by delta
        7. Log audit with old/new values
        8. Commit transaction

        Args:
            transaction_id: UUID of transaction to update
            data: TransactionUpdate schema with fields to update
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Updated Transaction instance

        Raises:
            NotFoundError: If transaction or card not found
            AuthorizationError: If user doesn't have edit permission
            ValidationError: If amount is zero

        Example:
            transaction = await transaction_service.update_transaction(
                transaction_id=transaction.id,
                data=TransactionUpdate(amount=Decimal("-60.00")),
                current_user=user,
            )
        """
        # 1. Get existing transaction
        existing = await self.transaction_repo.get_by_id(transaction_id)
        if existing is None:
            logger.warning(f"Transaction {transaction_id} not found")
            raise NotFoundError("Transaction")

        # 2. Permission check: creator, admin, or account owner
        is_creator = existing.created_by == current_user.id
        is_admin = current_user.is_admin
        is_owner = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=existing.account_id,
            required_permission=PermissionLevel.owner,
        )

        if not (is_creator or is_admin or is_owner):
            logger.warning(
                f"User {current_user.id} attempted to update transaction {transaction_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to edit this transaction"
            )

        # 3. Get only provided fields
        update_dict = data.model_dump(exclude_unset=True)

        if not update_dict:
            return existing  # Nothing to update

        # 4. Business validations
        if "amount" in update_dict and update_dict["amount"] == 0:
            raise ValidationError("Transaction amount cannot be zero")

        # Validate card if being updated
        # card_id can be:
        #   - Not in update_dict: don't update card (leave as is)
        #   - UUID in update_dict: validate and set to this card
        #   - None in update_dict: clear the card (set to NULL)
        if "card_id" in update_dict:
            new_card_id = update_dict["card_id"]
            if new_card_id is not None:  # UUID provided, validate it
                card = await self.card_repo.get_by_id_for_user(
                    card_id=new_card_id,
                    user_id=current_user.id,
                )
                if card is None:
                    logger.warning(
                        f"Card {new_card_id} not found or unauthorized for user {current_user.id}"
                    )
                    raise NotFoundError("Card")
            # If card_id is None, we allow it (clearing the card)

        # 5. Calculate balance delta before applying changes
        old_amount = existing.amount
        new_amount = update_dict.get("amount", old_amount)
        balance_delta = new_amount - old_amount

        # 6. Capture old values for audit
        old_values = {
            "transaction_date": str(existing.transaction_date),
            "amount": str(existing.amount),
            "description": existing.description,
            "merchant": existing.merchant,
            "card_id": str(existing.card_id) if existing.card_id else None,
            "transaction_type": existing.transaction_type.value,
            "user_notes": existing.user_notes,
            "value_date": str(existing.value_date) if existing.value_date else None,
        }

        # 7. Apply changes to model instance
        for key, value in update_dict.items():
            setattr(existing, key, value)
        existing.updated_by = current_user.id

        # 8. Persist
        updated = await self.transaction_repo.update(existing)

        # 9. Capture new values for audit
        new_values = {
            "transaction_date": str(updated.transaction_date),
            "amount": str(updated.amount),
            "description": updated.description,
            "merchant": updated.merchant,
            "card_id": str(updated.card_id) if updated.card_id else None,
            "transaction_type": updated.transaction_type.value,
            "user_notes": updated.user_notes,
            "value_date": str(updated.value_date) if updated.value_date else None,
        }

        # 10. Update balance if amount changed
        if balance_delta != Decimal(0):
            account = await self.account_repo.get_for_update(existing.account_id)
            old_balance = account.current_balance
            account.current_balance += balance_delta
            new_balance = account.current_balance

            logger.info(
                f"Updated transaction {transaction_id}, "
                f"balance delta: {balance_delta}, "
                f"new balance: {old_balance} -> {new_balance}"
            )

        # 11. Audit log with old/new values
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="transaction",
            entity_id=transaction_id,
            old_values=old_values,
            new_values=new_values,
            extra_metadata={
                "account_id": str(existing.account_id),
                "balance_delta": str(balance_delta),
                "changed_fields": list(update_dict.keys()),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # 12. Commit transaction
        await self.session.commit()

        return updated

    async def delete_transaction(
        self,
        transaction_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Soft delete transaction and update account balance.

        Only owners can delete transactions.
        Deleting a parent deletes all children (cascade).

        Args:
            transaction_id: UUID of transaction to delete
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If transaction not found
            AuthorizationError: If user doesn't have delete permission

        Example:
            deleted = await transaction_service.delete_transaction(
                transaction_id=transaction.id,
                current_user=user,
            )
        """
        # Get existing transaction
        existing = await self.transaction_repo.get_by_id(transaction_id)
        if existing is None:
            logger.warning(f"Transaction {transaction_id} not found")
            raise NotFoundError("Transaction")

        # Permission check (only OWNER can delete)
        has_permission = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=existing.account_id,
            required_permission=PermissionLevel.owner,
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} attempted to delete transaction {transaction_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to delete this transaction"
            )

        # Use database transaction for atomicity
        # Transaction managed by caller
        # If parent, delete all children first
        if await self.transaction_repo.has_children(transaction_id):
            children = await self.transaction_repo.get_children(transaction_id)
            for child in children:
                await self.transaction_repo.soft_delete(child)
            logger.info(
                f"Deleted {len(children)} child transactions of {transaction_id}"
            )

        # Delete transaction (soft delete)
        deleted = await self.transaction_repo.soft_delete(existing)

        if not deleted:
            return False

        # Update balance (subtract amount since it's now excluded)
        account = await self.account_repo.get_for_update(existing.account_id)
        old_balance = account.current_balance
        account.current_balance -= existing.amount
        new_balance = account.current_balance

        logger.info(
            f"Deleted transaction {transaction_id}, "
            f"updated balance: {old_balance} -> {new_balance}"
        )

        # Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="transaction",
            entity_id=transaction_id,
            description=f"Deleted transaction: {existing.description}",
            old_values={
                "transaction_date": str(existing.transaction_date),
                "amount": str(existing.amount),
                "description": existing.description,
            },
            extra_metadata={
                "account_id": str(existing.account_id),
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        return True

    async def split_transaction(
        self,
        transaction_id: uuid.UUID,
        splits: list[dict],
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> list[Transaction]:
        """
        Split transaction into multiple child transactions.

        Validation:
        1. Sum of split amounts must equal parent amount
        2. User must be creator, owner, or admin
        3. Parent cannot already be a child
        4. At least 2 splits required

        Process:
        1. Create child transactions with parent_transaction_id set
        2. Each child inherits: account_id, currency, transaction_date, value_date
        3. Each child has individual: amount, description, merchant
        4. Balance update is net-zero (total in = total out)

        Args:
            transaction_id: UUID of transaction to split
            splits: List of split dictionaries with amount, description, merchant, user_notes
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (parent transaction, list of child transactions)

        Raises:
            NotFoundError: If transaction not found
            AuthorizationError: If user doesn't have permission
            ValidationError: If split validation fails

        Example:
            parent, children = await transaction_service.split_transaction(
                transaction_id=transaction.id,
                splits=[
                    {"amount": Decimal("-30.00"), "description": "Groceries"},
                    {"amount": Decimal("-20.50"), "description": "Household items"},
                ],
                current_user=user,
            )
        """
        # Get parent transaction
        parent = await self.transaction_repo.get_by_id(transaction_id)
        if parent is None:
            logger.warning(f"Transaction {transaction_id} not found")
            raise NotFoundError("Transaction")

        # Validation: Cannot split a child transaction
        if parent.parent_transaction_id is not None:
            raise ValidationError("Cannot split a child transaction")

        # Validation: At least 2 splits required
        if len(splits) < 2:
            raise ValidationError("At least 2 splits are required")

        # Validation: Split amounts must sum to parent amount
        total_amount_splits = sum(Decimal(str(s["amount"])) for s in splits)
        if total_amount_splits != parent.amount:
            logger.warning(
                f"Split amounts ({total_amount_splits}) don't equal parent amount ({parent.amount})"
            )
            raise ValidationError(
                f"Split amounts ({total_amount_splits}) must equal parent amount ({parent.amount})"
            )

        # Permission check (EDITOR or higher can split)
        has_permission = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=parent.account_id,
            required_permission=PermissionLevel.editor,
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} attempted to split transaction {transaction_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to split this transaction"
            )

        # Use database transaction for atomicity
        # Transaction managed by caller
        children = []
        for split_data in splits:
            child = Transaction(
                account_id=parent.account_id,
                parent_transaction_id=parent.id,
                transaction_date=parent.transaction_date,
                value_date=parent.value_date,
                amount=Decimal(str(split_data["amount"])),
                currency=parent.currency,
                description=split_data["description"],
                merchant=split_data.get("merchant"),
                transaction_type=parent.transaction_type,
                user_notes=split_data.get("user_notes"),
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            created_child = await self.transaction_repo.create(child)
            children.append(created_child)

        logger.info(f"Split transaction {transaction_id} into {len(children)} children")

        # No balance update needed (parent still exists, children don't add new amounts)
        await self.session.commit()

        # Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.SPLIT_TRANSACTION,
            entity_type="transaction",
            entity_id=parent.id,
            description=f"Split transaction into {len(children)} parts",
            new_values={
                "children": [str(c.id) for c in children],
                "split_details": [
                    {"amount": str(s["amount"]), "description": s["description"]}
                    for s in splits
                ],
            },
            extra_metadata={
                "account_id": str(parent.account_id),
                "parent_amount": str(parent.amount),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Refresh parent to load children
        await self.session.refresh(parent, ["child_transactions"])
        return children

    async def join_split_transaction(
        self,
        transaction_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Transaction:
        """
        Reverse a split by deleting all children.

        Parent transaction remains as single transaction.

        Args:
            transaction_id: UUID of parent transaction
            current_user: Currently authenticated user
            request_id: Optional request ID for correlation
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Parent transaction

        Raises:
            NotFoundError: If transaction not found
            AuthorizationError: If user doesn't have permission
            ValidationError: If transaction has no splits

        Example:
            parent = await transaction_service.join_split_transaction(
                transaction_id=parent_transaction.id,
                current_user=user,
            )
        """
        # Get parent transaction
        parent = await self.transaction_repo.get_by_id(transaction_id)
        if parent is None:
            logger.warning(f"Transaction {transaction_id} not found")
            raise NotFoundError("Transaction")

        # Validation: Transaction must have children
        if not await self.transaction_repo.has_children(transaction_id):
            raise ValidationError("Transaction has no splits to join")

        # Permission check (EDITOR or higher can join)
        has_permission = await self.permission_service.check_permission(
            user_id=current_user.id,
            account_id=parent.account_id,
            required_permission=PermissionLevel.editor,
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} attempted to join split transaction {transaction_id} without permission"
            )
            raise AuthorizationError(
                "You don't have permission to join this split transaction"
            )

        # Use database transaction for atomicity
        # Transaction managed by caller
        children = await self.transaction_repo.get_children(transaction_id)

        # Delete all children
        for child in children:
            await self.transaction_repo.delete(child)

        logger.info(
            f"Joined split transaction {transaction_id}, deleted {len(children)} children"
        )

        # No balance update (children never affected balance independently)

        # Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.JOIN_TRANSACTION,
            entity_type="transaction",
            entity_id=parent.id,
            description=f"Joined {len(children)} split transactions back to parent",
            old_values={
                "children": [str(c.id) for c in children],
            },
            extra_metadata={
                "account_id": str(parent.account_id),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Refresh to update children relationship
        await self.session.refresh(parent, ["child_transactions"])
        return parent
