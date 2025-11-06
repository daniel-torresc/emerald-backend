"""
Mapper between Account domain entity and AccountModel database model.

This mapper handles bidirectional conversion:
- to_entity(): Convert SQLAlchemy model → Domain entity
- to_model(): Convert Domain entity → SQLAlchemy model

The mapper lives in the Infrastructure layer and knows about both:
- Domain entities (app.domain.entities.account.Account)
- Database models (app.infrastructure...models.account_model.AccountModel)
"""

from typing import Optional

from app.domain.entities.account import Account
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.money import Money
from app.infrastructure.adapters.outbound.persistence.postgresql.models.account_model import (
    AccountModel,
)


class AccountMapper:
    """
    Mapper between Account entity and AccountModel.

    Handles conversion between:
    - Pure domain entity (Account) with Money value object
    - SQLAlchemy ORM model (AccountModel) with Decimal and currency string
    """

    @staticmethod
    def to_entity(model: AccountModel) -> Account:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: AccountModel from database

        Returns:
            Account domain entity

        Example:
            account_model = session.get(AccountModel, account_id)
            account_entity = AccountMapper.to_entity(account_model)
        """
        # Create Money value object from balance and currency
        balance = Money(
            amount=model.current_balance,
            currency=Currency(model.currency),
        )

        # Extract shared user IDs from shares
        shared_with_user_ids = [share.user_id for share in model.shares if share.deleted_at is None]

        return Account(
            id=model.id,
            user_id=model.user_id,
            name=model.account_name,
            description=model.account_name,  # Using account_name as description fallback
            balance=balance,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            shared_with_user_ids=shared_with_user_ids,
        )

    @staticmethod
    def to_model(entity: Account, existing_model: Optional[AccountModel] = None) -> AccountModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: Account domain entity
            existing_model: Optional existing model to update (for updates)

        Returns:
            AccountModel for database persistence

        Example:
            # Create new model
            account_entity = Account(...)
            account_model = AccountMapper.to_model(account_entity)
            session.add(account_model)

            # Update existing model
            account_entity.name = "New Name"
            updated_model = AccountMapper.to_model(account_entity, existing_model)
            session.flush()
        """
        if existing_model:
            # Update existing model (for UPDATE operations)
            existing_model.account_name = entity.name
            existing_model.current_balance = entity.balance.amount
            existing_model.currency = entity.balance.currency.value
            existing_model.is_active = entity.is_active
            existing_model.updated_at = entity.updated_at if entity.updated_at else existing_model.updated_at
            existing_model.deleted_at = entity.deleted_at
            return existing_model
        else:
            # Create new model (for INSERT operations)
            # Note: We need to import AccountType enum
            from app.infrastructure.adapters.outbound.persistence.postgresql.models.enums import (
                AccountType,
            )

            return AccountModel(
                id=entity.id,
                user_id=entity.user_id,
                account_name=entity.name,
                account_type=AccountType.SAVINGS,  # Default type, should be passed or determined
                currency=entity.balance.currency.value,
                opening_balance=entity.balance.amount,
                current_balance=entity.balance.amount,
                is_active=entity.is_active,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                deleted_at=entity.deleted_at,
            )
