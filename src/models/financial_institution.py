"""
FinancialInstitution model.

This module defines:
- FinancialInstitution: Financial institutions master data (banks, credit unions, brokerages, fintech)

Architecture:
- Centralized repository of financial institutions
- Used by accounts to link to standardized institution data
- Supports SWIFT codes (international) and routing numbers (US)
- Uses is_active flag instead of soft delete (institutions can be deactivated)
"""

from typing import Optional

from sqlalchemy import Boolean, Enum as SQLEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import InstitutionType
from src.models.mixins import TimestampMixin


class FinancialInstitution(Base, TimestampMixin):
    """
    Financial institution model for master data management.

    Represents banks, credit unions, brokerages, and fintech companies.
    This is master data used to standardize institution information across
    all user accounts.

    Attributes:
        id: UUID primary key
        name: Official legal name of the institution (max 200 chars)
        short_name: Common/display name used in UI (max 100 chars)
        swift_code: BIC/SWIFT code for international transfers (8 or 11 chars, optional)
        routing_number: ABA routing number for US banks (9 digits, optional)
        country_code: ISO 3166-1 alpha-2 country code (2 chars, e.g., "US", "GB")
        institution_type: Type of institution (bank, credit_union, brokerage, fintech, other)
        logo_url: URL to institution's logo image (max 500 chars, optional)
        website_url: Official website URL (max 500 chars, optional)
        is_active: Whether the institution is operational (default: True)
        created_at: When the institution record was created (auto-set)
        updated_at: When the institution record was last updated (auto-updated)

    Unique Constraints:
        - swift_code must be unique (if provided) - enforced via partial unique index
        - routing_number must be unique (if provided) - enforced via partial unique index

    Indexes:
        - name (for searching)
        - short_name (for searching)
        - swift_code (partial unique: WHERE swift_code IS NOT NULL)
        - routing_number (partial unique: WHERE routing_number IS NOT NULL)
        - country_code (for filtering by country)
        - institution_type (for filtering by type)
        - is_active (for filtering active institutions)

    Note:
        This model does NOT use SoftDeleteMixin. Instead, defunct institutions
        are marked with is_active=False. This is because:
        - Institution data is master data, not transactional data
        - Historical references to institutions must remain valid
        - Deactivated institutions should still be viewable in historical contexts
    """

    __tablename__ = "financial_institutions"

    # Identification fields
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,  # Index for searching by name
        comment="Official legal name of the institution",
    )

    short_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # Index for searching by short name
        comment="Common/display name used in UI",
    )

    # Banking identifiers
    swift_code: Mapped[Optional[str]] = mapped_column(
        String(11),
        nullable=True,
        comment="BIC/SWIFT code (8 or 11 alphanumeric characters)",
    )

    routing_number: Mapped[Optional[str]] = mapped_column(
        String(9),
        nullable=True,
        comment="ABA routing number for US banks (9 digits)",
    )

    # Geographic information
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,  # Index for filtering by country
        comment="ISO 3166-1 alpha-2 country code (e.g., US, GB, DE)",
    )

    # Institution classification
    institution_type: Mapped[InstitutionType] = mapped_column(
        SQLEnum(
            InstitutionType,
            name="institution_type",
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,  # Index for filtering by type
        comment="Type of financial institution",
    )

    # Metadata
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to institution's logo image",
    )

    website_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Official website URL",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,  # Index for filtering active institutions
        comment="Whether the institution is operational",
    )

    # Relationships
    accounts: Mapped[list["Account"]] = relationship(  # type: ignore
        "Account",
        back_populates="financial_institution",
        foreign_keys="Account.financial_institution_id",
        lazy="select",  # Don't eager load accounts from institution side (rarely needed)
    )

    # Unique constraints and additional indexes created in migration
    # Partial unique indexes:
    # - CREATE UNIQUE INDEX financial_institutions_swift_code_unique
    #   ON financial_institutions(swift_code) WHERE swift_code IS NOT NULL
    # - CREATE UNIQUE INDEX financial_institutions_routing_number_unique
    #   ON financial_institutions(routing_number) WHERE routing_number IS NOT NULL

    def __repr__(self) -> str:
        """String representation of FinancialInstitution."""
        return (
            f"FinancialInstitution(id={self.id}, "
            f"short_name={self.short_name}, "
            f"type={self.institution_type.value}, "
            f"country={self.country_code})"
        )
