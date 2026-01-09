"""
FinancialInstitution Pydantic schemas for API request/response handling.

This module provides:
- Institution creation and update schemas
- Institution response schemas
- Institution filtering and listing schemas
- Institution sort field enum
- SWIFT code and routing number validation
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.routing_number import ABARoutingNumber
from schwifty import BIC

from models import InstitutionType
from .common import SortOrder, SortParams
from .enums import FinancialInstitutionSortField


class FinancialInstitutionBase(BaseModel):
    """
    Base financial institution schema with common fields.

    Attributes:
        name: Official legal name of the institution
        short_name: Common/display name used in UI
        swift_code: BIC/SWIFT code for international transfers (optional)
        routing_number: ABA routing number for US banks (optional)
        country_code: ISO 3166-1 alpha-2 country code
        institution_type: Type of institution
        logo_url: URL to institution's logo image (optional)
        website_url: Official website URL (optional)
    """

    name: str = Field(
        min_length=1,
        max_length=200,
        description="Official legal name of the institution",
        examples=["Banco Santander, S.A."],
    )

    short_name: str = Field(
        min_length=1,
        max_length=100,
        description="Common/display name used in UI",
        examples=["Santander"],
    )

    swift_code: str | None = Field(
        default=None,
        min_length=8,
        max_length=11,
        description="BIC/SWIFT code (8 or 11 alphanumeric characters)",
        examples=["BSCHESMM"],
    )

    routing_number: str | None = Field(
        default=None,
        pattern=r"^\d{9}$",
        description="ABA routing number for US banks (9 digits)",
        examples=["021000021"],
    )

    country_code: CountryAlpha2 = Field(
        description="ISO 3166-1 alpha-2 country code",
        examples=["ES", "US", "GB"],
    )

    institution_type: InstitutionType = Field(
        description="Type of financial institution",
        examples=["bank", "credit_union", "brokerage", "fintech"],
    )

    logo_url: HttpUrl | None = Field(
        default=None,
        description="URL to institution's logo image",
        examples=["https://logo.clearbit.com/santander.com"],
    )

    website_url: HttpUrl | None = Field(
        default=None,
        description="Official website URL",
        examples=["https://www.santander.com"],
    )

    @field_validator("swift_code")
    @classmethod
    def validate_swift_code(cls, value: str | None) -> str | None:
        """
        Validate SWIFT/BIC code format using schwifty library.

        Validates that SWIFT code:
        - Is 8 or 11 characters
        - Contains valid country code
        - Follows BIC format rules

        Raises:
            ValueError: If SWIFT code format is invalid
        """
        if value is None:
            return None

        # Strip whitespace and convert to uppercase
        value = value.strip().upper()

        # Validate length
        if len(value) not in (8, 11):
            raise ValueError("SWIFT code must be 8 or 11 characters")

        # Validate using schwifty BIC validator
        try:
            BIC(value)
        except ValueError as e:
            raise ValueError(f"Invalid SWIFT/BIC code: {str(e)}")

        return value

    @field_validator("routing_number")
    @classmethod
    def validate_routing_number(cls, value: str | None) -> str | None:
        """
        Validate ABA routing number format using pydantic-extra-types.

        Validates that routing number:
        - Is exactly 9 digits
        - Contains only numeric characters
        - Passes ABA checksum validation

        Raises:
            ValueError: If routing number format is invalid
        """
        if value is None:
            return None

        # Strip whitespace
        value = value.strip()

        # Validate length and numeric
        if not value.isdigit():
            raise ValueError("Routing number must contain only digits")

        if len(value) != 9:
            raise ValueError("Routing number must be exactly 9 digits")

        # Validate using pydantic-extra-types ABA validator
        try:
            ABARoutingNumber(value)
        except ValueError as e:
            raise ValueError(f"Invalid ABA routing number: {str(e)}")

        return value

    @field_validator("name", "short_name")
    @classmethod
    def strip_and_validate_name(cls, value: str) -> str:
        """Strip whitespace from name fields and validate not empty."""
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or only whitespace")
        return value


class FinancialInstitutionCreate(FinancialInstitutionBase):
    """
    Schema for creating a financial institution.

    Used in POST /api/v1/financial-institutions requests.
    Requires all base fields with validation.

    Note:
        - At least one of swift_code or routing_number should be provided
        - SWIFT codes are for international institutions
        - Routing numbers are for US banks only
    """

    @field_validator("routing_number")
    @classmethod
    def validate_routing_for_us_only(cls, value: str | None, info) -> str | None:
        """Ensure routing numbers are only used for US institutions."""
        if value is not None:
            # Get country_code from validation context
            country_code = info.data.get("country_code")
            if country_code and str(country_code) != "US":
                raise ValueError(
                    "Routing numbers are only valid for US institutions (country_code='US')"
                )
        return value


class FinancialInstitutionUpdate(BaseModel):
    """
    Schema for updating a financial institution.

    Used in PATCH /api/v1/financial-institutions/{id} requests.
    All fields are optional to support partial updates.

    Attributes:
        name: New official name
        short_name: New display name
        swift_code: New SWIFT code
        routing_number: New routing number
        country_code: New country code
        institution_type: New institution type
        logo_url: New logo URL
        website_url: New website URL
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Official legal name of the institution",
    )

    short_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Common/display name used in UI",
    )

    swift_code: str | None = Field(
        default=None,
        min_length=8,
        max_length=11,
        description="BIC/SWIFT code (8 or 11 alphanumeric characters)",
    )

    routing_number: str | None = Field(
        default=None,
        pattern=r"^\d{9}$",
        description="ABA routing number for US banks (9 digits)",
    )

    country_code: CountryAlpha2 | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code",
    )

    institution_type: InstitutionType | None = Field(
        default=None,
        description="Type of financial institution",
    )

    logo_url: HttpUrl | None = Field(
        default=None,
        description="URL to institution's logo image",
    )

    website_url: HttpUrl | None = Field(
        default=None,
        description="Official website URL",
    )

    @field_validator("swift_code")
    @classmethod
    def validate_swift_code(cls, value: str | None) -> str | None:
        """Validate SWIFT/BIC code format if provided."""
        if value is None:
            return None

        value = value.strip().upper()

        if len(value) not in (8, 11):
            raise ValueError("SWIFT code must be 8 or 11 characters")

        try:
            BIC(value)
        except ValueError as e:
            raise ValueError(f"Invalid SWIFT/BIC code: {str(e)}")

        return value

    @field_validator("routing_number")
    @classmethod
    def validate_routing_number(cls, value: str | None) -> str | None:
        """Validate ABA routing number format if provided."""
        if value is None:
            return None

        value = value.strip()

        if not value.isdigit():
            raise ValueError("Routing number must contain only digits")

        if len(value) != 9:
            raise ValueError("Routing number must be exactly 9 digits")

        try:
            ABARoutingNumber(value)
        except ValueError as e:
            raise ValueError(f"Invalid ABA routing number: {str(e)}")

        return value

    @field_validator("name", "short_name")
    @classmethod
    def strip_and_validate_name(cls, value: str | None) -> str | None:
        """Strip whitespace from name fields and validate not empty if provided."""
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or only whitespace")
        return value


class FinancialInstitutionResponse(FinancialInstitutionBase):
    """
    Schema for financial institution response.

    Used in GET /api/v1/financial-institutions/{id} responses.
    Includes all base fields plus database metadata.

    Attributes:
        id: Unique identifier (UUID)
        created_at: When the record was created
        updated_at: When the record was last updated
    """

    id: uuid.UUID = Field(description="Unique identifier")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class FinancialInstitutionEmbeddedResponse(BaseModel):
    """
    Minimal financial institution representation for embedding.

    Used in Account and Card responses to show the institution
    without full details.
    """

    id: uuid.UUID = Field(description="Institution UUID")
    name: str = Field(description="Official institution name")
    short_name: str = Field(description="Display name")
    logo_url: str | None = Field(default=None, description="Logo URL")

    model_config = ConfigDict(from_attributes=True)


class FinancialInstitutionListResponse(BaseModel):
    """
    Schema for financial institution list item.

    Used in GET /api/v1/financial-institutions responses.
    Includes only essential fields for list display to reduce payload size.

    Attributes:
        id: Unique identifier
        name: Official legal name
        short_name: Display name
        swift_code: SWIFT code (optional)
        country_code: Country code
        institution_type: Institution type
        logo_url: Logo URL (optional)
    """

    id: uuid.UUID = Field(description="Unique identifier")
    name: str = Field(description="Official legal name")
    short_name: str = Field(description="Display name")
    swift_code: str | None = Field(description="SWIFT/BIC code")
    country_code: str = Field(description="ISO 3166-1 alpha-2 country code")
    institution_type: InstitutionType = Field(description="Institution type")
    logo_url: str | None = Field(description="Logo URL")

    model_config = ConfigDict(from_attributes=True)


class FinancialInstitutionFilterParams(BaseModel):
    """
    Schema for filtering financial institutions in list queries.

    Used as query parameters in GET /api/v1/financial-institutions requests.

    Attributes:
        country_code: Filter by country (2-letter ISO code)
        institution_type: Filter by institution type
        search: Search in name and short_name fields
    """

    country_code: CountryAlpha2 | None = Field(
        default=None,
        description="Filter by country (ISO 3166-1 alpha-2)",
    )

    institution_type: InstitutionType | None = Field(
        default=None,
        description="Filter by institution type",
    )

    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Search in name and short_name fields (case-insensitive)",
    )

    @field_validator("search")
    @classmethod
    def strip_search(cls, value: str | None) -> str | None:
        """Strip whitespace from search query."""
        if value is None:
            return None
        value = value.strip()
        return value if value else None


class FinancialInstitutionSortParams(SortParams[FinancialInstitutionSortField]):
    """
    Sorting parameters for financial institution list queries.

    Provides type-safe sorting with validation at schema level.
    Default sort: name ascending (alphabetical order).
    """

    sort_by: FinancialInstitutionSortField = Field(
        default=FinancialInstitutionSortField.NAME,
        description="Field to sort by",
    )
    sort_order: SortOrder = Field(
        default=SortOrder.ASC,
        description="Sort direction",
    )
