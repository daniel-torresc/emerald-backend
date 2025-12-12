"""
Common Pydantic schemas for API request/response handling.

This module provides:
- Pagination parameters and response models
- Common response wrappers
- Shared schema utilities
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

# Type variable for generic paginated responses
DataT = TypeVar("DataT")


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

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, value: int) -> int:
        """Ensure page_size doesn't exceed maximum allowed value."""
        if value > 100:
            return 100
        return value

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

    @staticmethod
    def calculate_total_pages(total: int, page_size: int) -> int:
        """
        Calculate total pages from total count.

        Args:
            total: Total number of items
            page_size: Number of items per page

        Returns:
            Total number of pages (0 if no items)

        Example:
            >>> PaginationParams.calculate_total_pages(100, 20)
            5
            >>> PaginationParams.calculate_total_pages(95, 20)
            5
            >>> PaginationParams.calculate_total_pages(0, 20)
            0
        """
        return (total + page_size - 1) // page_size if total > 0 else 0


class PaginationMeta(BaseModel):
    """
    Metadata for paginated responses.

    Attributes:
        total: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")


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
