"""
Financial institution management service for CRUD operations.

This module provides:
- Create financial institution (admin only)
- Get financial institution details
- List/search financial institutions with filters
- Update financial institution (admin only)
- Deactivate financial institution (admin only)

All state-changing operations are logged to audit trail.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AlreadyExistsError, NotFoundError
from models import AuditAction, FinancialInstitution, User
from repositories import FinancialInstitutionRepository
from schemas import (
    FinancialInstitutionCreate,
    FinancialInstitutionFilterParams,
    FinancialInstitutionSortParams,
    FinancialInstitutionUpdate,
    PaginationParams,
)
from .audit_service import AuditService

logger = logging.getLogger(__name__)


class FinancialInstitutionService:
    """
    Service class for financial institution management operations.

    This service handles:
    - Institution creation (with uniqueness validation)
    - Institution retrieval by ID, SWIFT code, or routing number
    - Institution listing and searching with filters
    - Institution updates (with conflict checks)
    - Institution deactivation (soft disable)

    All methods require an active database session.
    Admin-only operations: create, update, deactivate
    Authenticated user operations: get, list (all authenticated users can access)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize FinancialInstitutionService with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.institution_repo = FinancialInstitutionRepository(session)
        self.audit_service = AuditService(session)

    async def create_institution(
        self,
        data: FinancialInstitutionCreate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> FinancialInstitution:
        """
        Create a new financial institution (admin only).

        Validates uniqueness of SWIFT code and routing number before creation.
        Logs creation to audit trail.

        Args:
            data: Institution creation data
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            FinancialInstitutionResponse with created institution data

        Raises:
            AlreadyExistsError: If SWIFT code or routing number already exists

        Example:
            institution = await service.create_institution(
                data=FinancialInstitutionCreate(
                    name="Banco Santander, S.A.",
                    short_name="Santander",
                    swift_code="BSCHESMM",
                    country_code="ES",
                    institution_type=InstitutionType.bank
                ),
                current_user=admin_user
            )
        """
        # Check for duplicate SWIFT code
        if data.swift_code:
            exists = await self.institution_repo.exists_by_swift_code(data.swift_code)
            if exists:
                logger.warning(
                    f"Institution creation failed: SWIFT code {data.swift_code} already exists"
                )
                raise AlreadyExistsError(
                    f"Institution with SWIFT code {data.swift_code} already exists"
                )

        # Check for duplicate routing number
        if data.routing_number:
            exists = await self.institution_repo.exists_by_routing_number(
                data.routing_number
            )
            if exists:
                logger.warning(
                    f"Institution creation failed: Routing number {data.routing_number} already exists"
                )
                raise AlreadyExistsError(
                    f"Institution with routing number {data.routing_number} already exists"
                )

        # Create institution
        institution = FinancialInstitution(
            name=data.name,
            short_name=data.short_name,
            swift_code=data.swift_code,
            routing_number=data.routing_number,
            country_code=data.country_code,
            institution_type=data.institution_type,
            logo_url=str(data.logo_url) if data.logo_url else None,
            website_url=str(data.website_url) if data.website_url else None,
        )
        institution = await self.institution_repo.create(institution)

        # Commit transaction
        await self.session.commit()

        logger.info(
            f"Institution created: {institution.id} ({institution.short_name}) by admin {current_user.id}"
        )

        # Log to audit trail
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE_FINANCIAL_INSTITUTION,
            entity_type="financial_institution",
            entity_id=institution.id,
            new_values={
                "institution_name": institution.short_name,
                "swift_code": institution.swift_code,
                "country_code": institution.country_code,
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return institution

    async def get_institution(
        self,
        institution_id: uuid.UUID,
    ) -> FinancialInstitution:
        """
        Get financial institution by ID.

        Available to all authenticated users.
        Returns institution regardless of is_active status.

        Args:
            institution_id: Institution UUID

        Returns:
            FinancialInstitutionResponse with institution data

        Raises:
            NotFoundError: If institution not found

        Example:
            institution = await service.get_institution(institution_id)
        """
        institution = await self.institution_repo.get_by_id(institution_id)

        if not institution:
            raise NotFoundError(f"Institution with ID {institution_id} not found")

        return institution

    async def get_by_swift_code(
        self,
        swift_code: str,
    ) -> FinancialInstitution:
        """
        Get financial institution by SWIFT/BIC code.

        Available to all authenticated users.
        Useful for institution lookup by identifier.

        Args:
            swift_code: SWIFT/BIC code (case-insensitive)

        Returns:
            FinancialInstitution with institution data

        Raises:
            NotFoundError: If institution not found

        Example:
            institution = await service.get_by_swift_code("BSCHESMM")
        """
        institution = await self.institution_repo.get_by_swift_code(swift_code)

        if not institution:
            raise NotFoundError(f"Institution with SWIFT code {swift_code} not found")

        return institution

    async def get_by_routing_number(
        self,
        routing_number: str,
    ) -> FinancialInstitution:
        """
        Get financial institution by ABA routing number.

        Available to all authenticated users.
        Useful for US bank lookup.

        Args:
            routing_number: ABA routing number (9 digits)

        Returns:
            FinancialInstitutionResponse with institution data

        Raises:
            NotFoundError: If institution not found

        Example:
            institution = await service.get_by_routing_number("021000021")
        """
        institution = await self.institution_repo.get_by_routing_number(routing_number)

        if not institution:
            raise NotFoundError(
                f"Institution with routing number {routing_number} not found"
            )

        return institution

    async def list_institutions(
        self,
        filters: FinancialInstitutionFilterParams,
        pagination: PaginationParams,
        sorting: FinancialInstitutionSortParams,
    ) -> tuple[list[FinancialInstitution], int]:
        """
        List financial institutions with pagination and filtering.

        Available to all authenticated users.
        Returns active institutions by default.
        Supports filtering by country, type, and search query.

        Args:
            filters: Filter parameters (country_code, institution_type, search)
            pagination: Pagination parameters (page, per_page)
            sorting: Sort parameters (sort_by, sort_order)

        Returns:
            PaginatedResponse with list of institutions and metadata

        Example:
            # Get active Spanish banks
            result = await service.list_institutions(
                filters=FinancialInstitutionFilterParams(
                    country_code="ES",
                    institution_type=InstitutionType.bank
                ),
                pagination=PaginationParams(page=1, page_size=20),
                sorting=FinancialInstitutionSortParams()
            )
        """
        financial_institutions = await self.institution_repo.list_all(
            filter_params=filters,
            pagination_params=pagination,
            sort_params=sorting,
        )

        return financial_institutions

    async def update_institution(
        self,
        institution_id: uuid.UUID,
        data: FinancialInstitutionUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> FinancialInstitution:
        """
        Update financial institution (admin only).

        Validates uniqueness constraints if SWIFT code or routing number changed.
        Logs update to audit trail.

        Args:
            institution_id: Institution UUID to update
            data: Update data (partial update supported)
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            FinancialInstitution with updated institution data

        Raises:
            NotFoundError: If institution not found
            AlreadyExistsError: If new SWIFT code or routing number already exists

        Example:
            institution = await service.update_institution(
                institution_id=uuid.UUID("..."),
                data=FinancialInstitutionUpdate(
                    is_active=False
                ),
                current_user=admin_user
            )
        """
        # 1. Get existing institution
        institution = await self.institution_repo.get_by_id(institution_id)
        if not institution:
            raise NotFoundError(f"Institution with ID {institution_id} not found")

        # 2. Get only provided fields
        update_dict = data.model_dump(exclude_unset=True)

        if not update_dict:
            return institution

        # 3. Business validations (only for changing fields)
        if (
            "swift_code" in update_dict
            and update_dict["swift_code"] != institution.swift_code
        ):
            exists = await self.institution_repo.exists_by_swift_code(
                update_dict["swift_code"]
            )
            if exists:
                raise AlreadyExistsError(
                    f"Institution with SWIFT code {update_dict['swift_code']} already exists"
                )

        if (
            "routing_number" in update_dict
            and update_dict["routing_number"] != institution.routing_number
        ):
            exists = await self.institution_repo.exists_by_routing_number(
                update_dict["routing_number"]
            )
            if exists:
                raise AlreadyExistsError(
                    f"Institution with routing number {update_dict['routing_number']} already exists"
                )

        # 4. Capture old values for audit
        old_values = {
            "name": institution.name,
            "short_name": institution.short_name,
            "swift_code": institution.swift_code,
            "routing_number": institution.routing_number,
            "country_code": institution.country_code,
            "institution_type": institution.institution_type.value
            if institution.institution_type
            else None,
            "logo_url": institution.logo_url,
            "website_url": institution.website_url,
        }

        # 5. Apply changes to model instance
        for key, value in update_dict.items():
            # Handle URL conversions to string
            if key in ("logo_url", "website_url") and value is not None:
                value = str(value)
            setattr(institution, key, value)

        # 6. Persist
        await self.institution_repo.update(institution)

        # 7. Capture new values for audit
        new_values = {
            "name": institution.name,
            "short_name": institution.short_name,
            "swift_code": institution.swift_code,
            "routing_number": institution.routing_number,
            "country_code": institution.country_code,
            "institution_type": institution.institution_type.value
            if institution.institution_type
            else None,
            "logo_url": institution.logo_url,
            "website_url": institution.website_url,
        }

        logger.info(
            f"Institution updated: {institution.id} ({institution.short_name}) by admin {current_user.id}"
        )

        # 8. Log to audit trail with old/new values
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE_FINANCIAL_INSTITUTION,
            entity_type="financial_institution",
            entity_id=institution.id,
            old_values=old_values,
            new_values=new_values,
            extra_metadata={
                "institution_name": institution.short_name,
                "changed_fields": list(update_dict.keys()),
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # 9. Commit transaction
        await self.session.commit()

        return institution

    async def delete_institution(
        self,
        institution_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Delete financial institution (admin only).

        Soft deletes the institution (sets deleted_at timestamp).
        Institution is preserved for historical references but filtered from queries.

        Logs deletion to audit trail.

        Args:
            institution_id: Institution UUID to delete
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Raises:
            NotFoundError: If institution not found

        Example:
            await service.delete_institution(
                institution_id=uuid.UUID("..."),
                current_user=admin_user
            )
        """
        # Get institution
        institution = await self.institution_repo.get_by_id(institution_id)
        if not institution:
            raise NotFoundError(f"Institution with ID {institution_id} not found")

        # Store details for audit log before deletion
        institution_name = institution.short_name
        institution_swift = institution.swift_code

        # Soft delete
        await self.institution_repo.delete(institution)

        # Commit transaction
        await self.session.commit()

        logger.info(
            f"Institution deleted: {institution_id} ({institution_name}) by admin {current_user.id}"
        )

        # Log to audit trail
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="financial_institution",
            entity_id=institution_id,
            extra_metadata={
                "institution_name": institution_name,
                "swift_code": institution_swift,
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
