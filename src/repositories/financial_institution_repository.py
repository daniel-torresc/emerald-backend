"""
Financial institution repository for database operations.

This module provides database operations for the FinancialInstitution model,
including searches by SWIFT code, routing number, and filtering by country/type.
"""

from sqlalchemy import asc, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FinancialInstitution
from schemas import (
    FinancialInstitutionFilterParams,
    FinancialInstitutionSortParams,
    PaginationParams,
    SortOrder,
)
from .base import BaseRepository


class FinancialInstitutionRepository(BaseRepository[FinancialInstitution]):
    """
    Repository for FinancialInstitution model operations.

    Extends BaseRepository with institution-specific queries:
    - SWIFT code lookups (for institution identification)
    - Routing number lookups (for US banks)
    - Country and type filtering (for dropdown menus)
    - Search by name (for autocomplete)

    Note:
        FinancialInstitution uses soft delete pattern via SoftDeleteMixin.
        Soft-deleted institutions are automatically filtered out by BaseRepository.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize FinancialInstitutionRepository.

        Args:
            session: Async database session
        """
        super().__init__(FinancialInstitution, session)

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    async def get_by_swift_code(self, swift_code: str) -> FinancialInstitution | None:
        """
        Get financial institution by SWIFT/BIC code.

        SWIFT codes are unique identifiers for international institutions.
        Case-insensitive search (stored uppercase in DB).

        Args:
            swift_code: SWIFT/BIC code (8 or 11 characters)

        Returns:
            FinancialInstitution instance or None if not found

        Example:
            institution = await repo.get_by_swift_code("BSCHESMM")
        """
        query = select(FinancialInstitution).where(
            FinancialInstitution.swift_code == swift_code.upper()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_routing_number(
        self, routing_number: str
    ) -> FinancialInstitution | None:
        """
        Get financial institution by ABA routing number.

        Routing numbers are unique identifiers for US banks.

        Args:
            routing_number: ABA routing number (9 digits)

        Returns:
            FinancialInstitution instance or None if not found

        Example:
            institution = await repo.get_by_routing_number("021000021")
        """
        query = select(FinancialInstitution).where(
            FinancialInstitution.routing_number == routing_number
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists_by_swift_code(self, swift_code: str) -> bool:
        """
        Check if an institution with the given SWIFT code already exists.

        Case-insensitive check.

        Args:
            swift_code: SWIFT/BIC code to check

        Returns:
            True if exists, False otherwise

        Example:
            exists = await repo.exists_by_swift_code("BSCHESMM")
            if exists:
                raise ConflictError("Institution already exists")
        """
        record = await self.get_by_swift_code(swift_code=swift_code)
        return record is not None

    async def exists_by_routing_number(self, routing_number: str) -> bool:
        """
        Check if an institution with the given routing number already exists.

        Args:
            routing_number: ABA routing number to check

        Returns:
            True if exists, False otherwise

        Example:
            exists = await repo.exists_by_routing_number("021000021")
            if exists:
                raise ConflictError("Institution already exists")
        """
        record = await self.get_by_routing_number(routing_number=routing_number)
        return record is not None

    # ========================================================================
    # USER PARAM METHODS
    # ========================================================================

    async def list_all(
        self,
        filter_params: FinancialInstitutionFilterParams,
        sort_params: FinancialInstitutionSortParams,
        pagination_params: PaginationParams,
    ) -> tuple[list[FinancialInstitution], int]:
        """
        Search and filter financial institutions.

        Args:
            filter_params:
            sort_params:
            pagination_params:

        Returns:
            List of matching FinancialInstitution instances
        """
        filters = []

        # Apply text search (if provided)
        if filter_params.search:
            search_pattern = f"%{filter_params.search}%"
            filters.append(
                or_(
                    FinancialInstitution.name.ilike(search_pattern),
                    FinancialInstitution.short_name.ilike(search_pattern),
                )
            )

        # Apply country filter (if provided)
        if filter_params.country_code:
            filters.append(
                FinancialInstitution.country_code == filter_params.country_code
            )

        # Apply institution type filter (if provided)
        if filter_params.institution_type:
            filters.append(
                FinancialInstitution.institution_type == filter_params.institution_type
            )

        order_by = []

        # Get the model column from enum value
        sort_column = getattr(FinancialInstitution, sort_params.sort_by.value)

        # Apply sort direction
        if sort_params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort by id for deterministic pagination
        order_by.append(desc(FinancialInstitution.id))

        return await self._list_and_count(
            filters=filters,
            order_by=order_by,
            offset=pagination_params.offset,
            limit=pagination_params.page_size,
        )
