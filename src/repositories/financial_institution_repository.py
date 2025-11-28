"""
Financial institution repository for database operations.

This module provides database operations for the FinancialInstitution model,
including searches by SWIFT code, routing number, and filtering by country/type.
"""


from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.financial_institution import FinancialInstitution
from src.models.enums import InstitutionType
from src.repositories.base import BaseRepository


class FinancialInstitutionRepository(BaseRepository[FinancialInstitution]):
    """
    Repository for FinancialInstitution model operations.

    Extends BaseRepository with institution-specific queries:
    - SWIFT code lookups (for institution identification)
    - Routing number lookups (for US banks)
    - Country and type filtering (for dropdown menus)
    - Search by name (for autocomplete)

    Note:
        This repository does NOT use soft delete filtering because
        FinancialInstitution uses is_active flag instead.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize FinancialInstitutionRepository.

        Args:
            session: Async database session
        """
        super().__init__(FinancialInstitution, session)

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

    async def search(
        self,
        query_text: str | None = None,
        country_code: str | None = None,
        institution_type: InstitutionType | None = None,
        is_active: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> list[FinancialInstitution]:
        """
        Search and filter financial institutions.

        Supports:
        - Text search in name and short_name (case-insensitive, partial match)
        - Country filtering
        - Institution type filtering
        - Active status filtering (default: active only)
        - Pagination

        Args:
            query_text: Search term for name/short_name (optional)
            country_code: ISO 3166-1 alpha-2 country code (optional)
            institution_type: Institution type filter (optional)
            is_active: Active status filter (default: True)
            limit: Maximum number of results (default: 20, max: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            List of matching FinancialInstitution instances

        Example:
            # Search for Spanish banks
            institutions = await repo.search(
                country_code="ES",
                institution_type=InstitutionType.bank,
                is_active=True,
                limit=10
            )

            # Search by name
            institutions = await repo.search(
                query_text="Santander",
                limit=5
            )
        """
        # Start with base query
        query = select(FinancialInstitution)

        # Apply text search (if provided)
        if query_text:
            search_pattern = f"%{query_text}%"
            query = query.where(
                or_(
                    FinancialInstitution.name.ilike(search_pattern),
                    FinancialInstitution.short_name.ilike(search_pattern),
                )
            )

        # Apply country filter (if provided)
        if country_code:
            query = query.where(FinancialInstitution.country_code == country_code)

        # Apply institution type filter (if provided)
        if institution_type:
            query = query.where(
                FinancialInstitution.institution_type == institution_type
            )

        # Apply active status filter (if provided)
        if is_active is not None:
            query = query.where(FinancialInstitution.is_active == is_active)

        # Order by short_name alphabetically
        query = query.order_by(FinancialInstitution.short_name)

        # Apply pagination
        query = query.limit(min(limit, 100)).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        query_text: str | None = None,
        country_code: str | None = None,
        institution_type: InstitutionType | None = None,
        is_active: bool | None = True,
    ) -> int:
        """
        Count institutions matching filters.

        Used for pagination metadata.

        Args:
            query_text: Search term for name/short_name (optional)
            country_code: ISO 3166-1 alpha-2 country code (optional)
            institution_type: Institution type filter (optional)
            is_active: Active status filter (default: True)

        Returns:
            Total count of matching institutions

        Example:
            total = await repo.count_filtered(
                country_code="ES",
                is_active=True
            )
        """
        # Start with base query
        query = select(func.count()).select_from(FinancialInstitution)

        # Apply text search (if provided)
        if query_text:
            search_pattern = f"%{query_text}%"
            query = query.where(
                or_(
                    FinancialInstitution.name.ilike(search_pattern),
                    FinancialInstitution.short_name.ilike(search_pattern),
                )
            )

        # Apply country filter (if provided)
        if country_code:
            query = query.where(FinancialInstitution.country_code == country_code)

        # Apply institution type filter (if provided)
        if institution_type:
            query = query.where(
                FinancialInstitution.institution_type == institution_type
            )

        # Apply active status filter (if provided)
        if is_active is not None:
            query = query.where(FinancialInstitution.is_active == is_active)

        # Execute count query
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_all_active(self) -> list[FinancialInstitution]:
        """
        Get all active financial institutions.

        Ordered by short_name alphabetically.
        Useful for dropdown menus and selection lists.

        Returns:
            List of all active FinancialInstitution instances

        Example:
            institutions = await repo.get_all_active()
        """
        query = (
            select(FinancialInstitution)
            .where(FinancialInstitution.is_active)
            .order_by(FinancialInstitution.short_name)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

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
        query = select(FinancialInstitution.id).where(
            FinancialInstitution.swift_code == swift_code.upper()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

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
        query = select(FinancialInstitution.id).where(
            FinancialInstitution.routing_number == routing_number
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    def _apply_soft_delete_filter(self, query: Select) -> Select:
        """
        Override base method - FinancialInstitution uses is_active, not soft delete.

        This method is intentionally a no-op because FinancialInstitution
        does not use the SoftDeleteMixin pattern.

        Args:
            query: SQLAlchemy select statement

        Returns:
            Original query unchanged
        """
        return query
