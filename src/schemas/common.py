"""
Common Pydantic schemas for API request/response handling.

This module provides:
- Pagination parameters and response models
- Sorting parameters and enums
- Search result containers
- Common response wrappers
- Shared schema utilities
"""

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .enums import SortOrder

# Type variable for generic paginated responses
DataT = TypeVar("DataT")

# Type variable for the sort enum
SortFieldType = TypeVar("SortFieldType", bound=Enum)


class SortParams(BaseModel, Generic[SortFieldType]):
    """
    Common sorting parameters for list endpoints.

    Used via Depends() in routes alongside entity-specific FilterParams.
    The sort_by field should be validated against an entity-specific
    SortField enum in the route layer.

    Attributes:
        sort_order: Sort direction (ascending or descending)
    """

    sort_by: SortFieldType = Field(description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort direction")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sort_order": "desc",
            }
        }
    )


class SearchResult(BaseModel, Generic[DataT]):
    """
    Internal search result container.

    Used for service-to-route communication. Not exposed directly to API.
    Routes convert this to PaginatedResponse for HTTP responses.

    Type Parameters:
        DataT: Type of items in the items list (typically SQLAlchemy models)

    Attributes:
        items: List of model instances for current page
        total: Total count of items matching filters (without pagination)
    """

    items: list[DataT]
    total: int

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PaginationParams(BaseModel):
    """
    Query parameters for paginated list endpoints.

    Attributes:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
            }
        }
    )

    @property
    def offset(self) -> int:
        """
        Calculate SQL OFFSET from page number.

        Returns:
            Offset value for SQL query (0-indexed)

        Example:
            >>> params = PaginationParams(page=1, page_size=20)
            >>> params.offset
            0
            >>> params = PaginationParams(page=2, page_size=20)
            >>> params.offset
            20
        """
        return (self.page - 1) * self.page_size


class PaginationMeta(BaseModel):
    """
    Metadata for paginated responses.

    Attributes:
        total: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
    """

    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (
            (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 0
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        """Whether there is a next page."""
        return self.page < self.total_pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_previous(self) -> bool:
        """Whether there is a previous page."""
        return self.page > 1


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Generic paginated response wrapper.

    Used for all list endpoints that return paginated data.

    Type Parameters:
        DataT: Type of items in the data list

    Attributes:
        data: List of items for current page
        meta: Pagination metadata
    """

    data: list[DataT]
    meta: PaginationMeta


class ResponseMeta(BaseModel):
    """
    Metadata included in all API responses.

    Attributes:
        timestamp: ISO 8601 timestamp of the response
        request_id: Unique request identifier for tracing
    """

    timestamp: datetime = Field(description="Response timestamp (ISO 8601)")
    request_id: str | None = Field(
        default=None,
        description="Unique request ID for tracing",
    )


class SuccessResponse(BaseModel, Generic[DataT]):
    """
    Generic success response wrapper.

    Used for single-item endpoints and non-paginated responses.

    Type Parameters:
        DataT: Type of the data object

    Attributes:
        data: Response data
        meta: Response metadata
    """

    data: DataT
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    """
    Detailed error information for a specific field or validation error.

    Attributes:
        field: Field name that caused the error (optional)
        message: Human-readable error message
        code: Machine-readable error code (optional)
    """

    field: str | None = Field(default=None, description="Field with error")
    message: str = Field(description="Error message")
    code: str | None = Field(default=None, description="Error code")


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    Used for all error responses across the API.

    Attributes:
        error: Error information
        meta: Response metadata
    """

    class Error(BaseModel):
        """Nested error information."""

        code: str = Field(description="Error code (e.g., VALIDATION_ERROR)")
        message: str = Field(description="Human-readable error message")
        details: list[ErrorDetail] | None = Field(
            default=None,
            description="Detailed error information",
        )

    error: Error
    meta: ResponseMeta
