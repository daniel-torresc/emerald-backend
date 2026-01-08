# Entity Search and List Implementation Guide

This document describes the recommended patterns for implementing entity search/list operations in a
layered architecture (API → Service → Repository) with FastAPI and SQLAlchemy.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ROUTE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  - FilterParams (Pydantic - entity-specific filters)             │
│             - PaginationParams (Pydantic - common page/page_size)           │
│             - SortParams (Pydantic - entity-specific sort_by enum)          │
│  DOES:      - Extract query parameters via Depends()                        │
│             - Call service.list_products()                                  │
│             - Build paginated response with data and meta                   │
│  RETURNS:   PaginatedResponse(data=[...], meta=PaginationMeta(...))         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: FilterParams + PaginationParams + SortParams
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  FilterParams + PaginationParams + SortParams                    │
│  DOES:      - Business-level validation (e.g., user permissions)            │
│             - Apply business rules (e.g., tenant filtering)                 │
│             - Orchestrate repository calls                                  │
│  RETURNS:   SearchResult(items=list[Model], total=int)                      │
│  NOTE:      NO SQLAlchemy imports - delegates query building to repository  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: FilterParams + PaginationParams + SortParams
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  - FilterParams (Pydantic schema)                                │
│             - PaginationParams (Pydantic schema)                            │
│             - SortParams (Pydantic schema)                                  │
│  DOES:      - Convert FilterParams to SQLAlchemy expressions                │
│             - Convert SortParams to SQLAlchemy order_by                     │
│             - Execute count query (without limit/offset)                    │
│             - Execute data query (with limit/offset/order)                  │
│             - Automatically filter soft-deleted records                     │
│  RETURNS:   SearchResult(items=list[Model], total=int)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why Filter Building Belongs in Repository

The repository layer is responsible for **all data access concerns**, including:

1. **SQLAlchemy is a persistence detail** - Services shouldn't know about ColumnElement, or_, desc,
   etc.
2. **Easier to swap ORMs** - Only repository changes if you switch from SQLAlchemy to another ORM
3. **Repository already knows the model** - Adding filter knowledge is natural
4. **Cleaner service layer** - Services focus on business logic and orchestration
5. **Pydantic schemas are domain contracts** - They represent application-level filter definitions,
   not HTTP-specific concerns

## Quick Reference

| Layer          | Input            | Output                        | Responsibility                   |
|----------------|------------------|-------------------------------|----------------------------------|
| **Route**      | Query params     | PaginatedResponse(data, meta) | HTTP handling, response assembly |
| **Service**    | Pydantic schemas | SearchResult(items, total)    | Business logic, orchestration    |
| **Repository** | Pydantic schemas | SearchResult(items, total)    | Filter building, query execution |

## Complete Example: Product Search

### 1. Common Schemas (Shared Across Entities)

```python
# src/schemas/enums.py

import enum


class SortOrder(str, enum.Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"


class ProductSortField(str, enum.Enum):
    """
    Allowed sort fields for products.

    Guidelines:
    - Only include sortable fields
    - Use database column names (not Python attribute names if different)
    - Prevents SQL injection by whitelisting allowed fields
    """
    NAME = "name"
    PRICE = "price"
    STOCK_QUANTITY = "stock_quantity"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
```

```python
# src/schemas/common.py

import enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

from schemas.enums import SortOrder

T = TypeVar("T")

# Define the type variable for the enum
SortFieldType = TypeVar('SortFieldType', bound=enum.Enum)


class SortParams(BaseModel, Generic[SortFieldType]):
    """
    Entity-specific sorting parameters for products.

    Guidelines:
    - Each entity has its own SortParams with typed enum
    - Validation happens at schema level, not in route
    - Default sort field and order are entity-specific
    """
    sort_by: SortFieldType
    sort_order: SortOrder = Field(
        SortOrder.DESC,
        description="Sort direction"
    )


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    @computed_field
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
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

    @computed_field
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 0

    @computed_field
    @property
    def has_next(self) -> bool:
        """Whether there is a next page."""
        return self.page < self.total_pages

    @computed_field
    @property
    def has_previous(self) -> bool:
        """Whether there is a previous page."""
        return self.page > 1


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Used for all list endpoints that return paginated data.

    Type Parameters:
        T: Type of items in the data list

    Attributes:
        data: List of items for current page
        meta: Pagination metadata
    """
    data: list[T]
    meta: PaginationMeta
```

### 2. Entity-Specific Filter Schema

```python
# src/schemas/product.py

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductFilterParams(BaseModel):
    """
    Entity-specific filter parameters for products.

    Guidelines:
    - All fields optional (filters are optional)
    - No pagination or sorting fields (handled by common schemas)
    - Use clear, descriptive field names
    - Validate ranges and formats
    - Add model_validator for cross-field validation
    """
    # Text search
    search: str | None = Field(None, max_length=100, description="Search in name/description")

    # Exact match filters
    category_id: UUID | None = Field(None, description="Filter by category")
    is_active: bool | None = Field(None, description="Filter by active status")

    # Range filters
    min_price: Decimal | None = Field(None, ge=0, description="Minimum price")
    max_price: Decimal | None = Field(None, ge=0, description="Maximum price")
    min_stock: int | None = Field(None, ge=0, description="Minimum stock quantity")
    max_stock: int | None = Field(None, ge=0, description="Maximum stock quantity")

    # Boolean flags
    in_stock: bool | None = Field(None, description="Only products with stock > 0")
    on_sale: bool | None = Field(None, description="Only products with discount > 0")

    # Date range filters
    created_after: datetime | None = Field(None, description="Created after this date")
    created_before: datetime | None = Field(None, description="Created before this date")

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        """Validate that min values don't exceed max values."""
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("min_price cannot exceed max_price")

        if self.min_stock is not None and self.max_stock is not None:
            if self.min_stock > self.max_stock:
                raise ValueError("min_stock cannot exceed max_stock")

        if self.created_after is not None and self.created_before is not None:
            if self.created_after > self.created_before:
                raise ValueError("created_after cannot be later than created_before")

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search": "wireless",
                "category_id": "123e4567-e89b-12d3-a456-426614174000",
                "min_price": "10.00",
                "max_price": "100.00",
                "is_active": True,
                "in_stock": True
            }
        }
    )
```

### 3. Entity-Specific Sort Schema

```python
# src/schemas/product.py

from pydantic import Field
from schemas.common import SortParams
from schemas.enums import ProductSortField


class ProductSortParams(SortParams[ProductSortField]):
    """
    Entity-specific sorting parameters for products.

    Guidelines:
    - Each entity has its own SortParams with typed enum
    - Validation happens at schema level, not in route
    - Default sort field and order are entity-specific
    """
    sort_by: ProductSortField = Field(
        ProductSortField.CREATED_AT,
        description="Field to sort by"
    )
```

### 4. API Route Layer

```python
# src/api/routes/products.py

from fastapi import APIRouter, Depends
from schemas.product import (
    ProductFilterParams,
    ProductListItem,
    ProductSortParams,
)
from services.product_service import ProductService

from api.dependencies import CurrentUser, get_product_service
from schemas.common import (PaginatedResponse, PaginationMeta, PaginationParams)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductListItem])
async def list_products(
        current_user: CurrentUser,
        # Entity-specific filters
        filters: ProductFilterParams = Depends(),
        # Common pagination
        pagination: PaginationParams = Depends(),
        # Entity-specific sorting (typed enum validates at schema level)
        sorting: ProductSortParams = Depends(),
        # Dependencies
        service: ProductService = Depends(get_product_service),
) -> PaginatedResponse[ProductListItem]:
    """
    List products with filtering, sorting, and pagination.

    Query Parameters:
    - Filters: search, category_id, min_price, max_price, is_active, etc.
    - Pagination: page, page_size
    - Sorting: sort_by (name|price|stock_quantity|created_at|updated_at), sort_order (asc|desc)

    Returns:
    - data: List of products for current page
    - meta: Pagination metadata (total, page, page_size, total_pages, has_next, has_previous)
    """
    products = await service.list_products(
        current_user=current_user,
        filters=filters,
        pagination=pagination,
        sorting=sorting,
    )

    count = await service.count_products(
        current_user=current_user,
        filters=filters,
    )

    # Build response
    return PaginatedResponse(
        data=[ProductListItem.model_validate(p) for p in products],
        meta=PaginationMeta(
            total=count,
            page=pagination.page,
            page_size=pagination.page_size,
        ),
    )
```

### 5. Service Layer

```python
# src/services/product_service.py

from uuid import UUID
import logging

from models.product import Product
from repositories.product_repository import ProductRepository
from schemas.product import ProductFilterParams, ProductSortParams
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class ProductService:
    """
    Product business logic.

    NOTE: No SQLAlchemy imports here! All query building is delegated to repository.
    Service focuses on:
    - Business validation
    - Permission checks
    - Orchestration
    - Adding business-level filter constraints
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ProductRepository(session)

    async def list_products(
            self,
            current_user: User,
            filters: ProductFilterParams,
            pagination: PaginationParams,
            sorting: ProductSortParams,
    ) -> list[Product]:
        """
        List products with filtering, sorting, and pagination.

        Args:
            current_user: User logged in
            filters: User-provided filter parameters
            pagination: Pagination parameters
            sorting: Sort parameters

        Returns:
            Product items
        """
        filters = self.repository.build_filters(params=filters, user_id=current_user.id)
        order_by = self.repository.build_order_by(params=sorting)

        return await self.repository.list(
            filters=filters,
            order_by=order_by,
            offset=pagination.offset,
            limit=pagination.page_size,
            # If load_options needed, call build_load_options method from repository
        )

    async def list_products_for_user(
            self,
            current_user: User,
            user_id: UUID,
            filters: ProductFilterParams,
            pagination: PaginationParams,
            sorting: ProductSortParams,
    ) -> list[Product]:
        """
        List products visible to a specific user.

        Business logic example: non-admin users only see their own products.

        Args:
            current_user: User logged in
            user_id: User to list products from
            filters: User-provided filter parameters
            pagination: Pagination parameters
            sorting: Sort parameters
        """
        # User can only list their own products (admins can list any user's products)
        if user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to list products for user {user_id}"
            )
            raise PermissionError("You can only list your own products")

        filters = self.repository.build_filters(params=filters, user_id=user_id)
        order_by = self.repository.build_order_by(params=sorting)

        return await self.repository.list(
            filters=filters,
            order_by=order_by,
            offset=pagination.offset,
            limit=pagination.page_size,
            # If load_options needed, call build_load_options method from repository
        )

    async def count_products(
            self,
            current_user: User,
            filters: ProductFilterParams,
    ) -> int:
        """
        Count products with filtering.

        Args:
            current_user: User logged in
            filters: User-provided filter parameters

        Returns:
            Total count
        """
        filters = self.repository.build_filters(params=filters, user_id=current_user.id)

        return await self.repository.count(filters=filters)

    async def count_products_for_user(
            self,
            current_user: User,
            user_id: UUID,
            filters: ProductFilterParams,
    ) -> int:
        """
        Count products visible to a specific user.

        Business logic example: non-admin users only see their own products.

        Args:
            current_user: User logged in
            user_id: User to list products from
            filters: User-provided filter parameters
        """
        # User can only list their own products (admins can list any user's accounts)
        if user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to list accounts for user {user_id}"
            )
            raise PermissionError("You can only list your own accounts")

        filters = self.repository.build_filters(params=filters, user_id=user_id)

        return await self.repository.count(filters=filters)
```

### 6. Repository Layer (Base)

```python
# src/repositories/base.py

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, UnaryExpression, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load

from schemas.common import SortParams

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType], ABC):
    """
    Generic base repository with common query functionality.

    Provides:
    - Automatic soft-delete filtering (if model has deleted_at)
    - Common CRUD operations
    - Base query building utilities
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def _apply_soft_delete_filter(self, query: Select[Any]) -> Select[Any]:
        """
        Apply soft delete filter to query if model supports it.

        Args:
            query: SQLAlchemy select statement

        Returns:
            Query with soft delete filter applied
        """
        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        return query

    @abstractmethod
    def build_filters(
            self,
            params: BaseModel,
            user_id: UUID | None = None,
    ) -> list[ColumnElement[bool]]:
        raise NotImplementedError()

    @abstractmethod
    def build_order_by(
            self,
            params: SortParams,
    ) -> list[UnaryExpression]:
        raise NotImplementedError()

    async def list(
            self,
            filters: list[ColumnElement[bool]],
            order_by: list[UnaryExpression],
            offset: int,
            limit: int,
            load_options: list[Load] | None = None,
    ):
        query = select(self.model)

        # Apply soft-delete filter
        query = self._apply_soft_delete_filter(query)

        if load_options:
            query = query.options(*load_options)

        if filters:
            query = query.where(and_(*filters))

        if order_by:
            query = query.order_by(*order_by)

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
            self,
            filters: list[ColumnElement[bool]],
    ) -> int:
        query = select(func.count()).select_from(self.model)

        # Apply soft-delete filter
        query = self._apply_soft_delete_filter(query)

        if filters:
            query = query.where(and_(*filters))

        return await self.session.scalar(query) or 0
```

### 7. Repository Layer (Entity-Specific)

```python
# src/repositories/product_repository.py

from uuid import UUID

from models.product import Product
from schemas.product import ProductFilterParams, ProductSortField, ProductSortParams
from sqlalchemy import ColumnElement, UnaryExpression, asc, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.base import BaseRepository
from schemas import SortOrder


class ProductRepository(BaseRepository[Product]):
    """
    Product data access layer.

    Responsibilities:
    - Convert Pydantic filter schemas to SQLAlchemy expressions
    - Convert Pydantic sort schemas to SQLAlchemy order_by
    - Execute queries with proper soft-delete handling
    - Eager load relationships when needed
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    def build_filters(
            self,
            params: ProductFilterParams,
            user_id: UUID | None = None,
    ) -> list[ColumnElement[bool]]:
        """
        Convert Pydantic FilterParams to SQLAlchemy filter expressions.

        Guidelines:
        - Return a list of SQLAlchemy ColumnElement[bool]
        - Only add filters for non-None values
        - Use appropriate operators (==, >=, <=, ilike, in_, etc.)
        """
        filters: list[ColumnElement[bool]] = []

        # Business-level filter (passed from service)
        if user_id is not None:
            filters.append(Product.user_id == user_id)

        # Text search (ILIKE for case-insensitive partial match)
        if params.search:
            search_term = f"%{params.search}%"
            filters.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.sku.ilike(search_term),
                )
            )

        # Exact match filters
        if params.category_id is not None:
            filters.append(Product.category_id == params.category_id)

        if params.is_active is not None:
            filters.append(Product.is_active == params.is_active)

        # Range filters (price)
        if params.min_price is not None:
            filters.append(Product.price >= params.min_price)

        if params.max_price is not None:
            filters.append(Product.price <= params.max_price)

        # Range filters (stock)
        if params.min_stock is not None:
            filters.append(Product.stock_quantity >= params.min_stock)

        if params.max_stock is not None:
            filters.append(Product.stock_quantity <= params.max_stock)

        # Boolean flag filters (computed conditions)
        if params.in_stock is True:
            filters.append(Product.stock_quantity > 0)
        elif params.in_stock is False:
            filters.append(Product.stock_quantity == 0)

        if params.on_sale is True:
            filters.append(Product.discount > 0)
        elif params.on_sale is False:
            filters.append(Product.discount == 0)

        # Date range filters
        if params.created_after is not None:
            filters.append(Product.created_at >= params.created_after)

        if params.created_before is not None:
            filters.append(Product.created_at <= params.created_before)

        return filters

    def build_order_by(
            self,
            params: ProductSortParams,
    ) -> list[UnaryExpression]:
        """
        Convert SortParams to SQLAlchemy order_by expressions.

        Guidelines:
        - Return a list of SQLAlchemy UnaryExpression
        - Use enum value to get column via getattr
        - Always add secondary sort by id for deterministic pagination
        """
        order_by: list[UnaryExpression] = []

        # Get the model column from enum value
        sort_column = getattr(Product, params.sort_by.value)

        # Apply sort direction
        if params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort for deterministic pagination
        order_by.append(desc(Product.id))

        return order_by

    def build_load_options(self):
        pass  # implement if required
```

## Advanced Patterns

### Pattern 1: Full-Text Search (PostgreSQL)

```python
# In repository build_filters method
from sqlalchemy import func

def build_filters(self, params: ProductFilterParams, ...) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if params.search:
        # PostgreSQL full-text search
        search_vector = func.to_tsvector(
            'english',
            func.concat(Product.name, ' ', Product.description)
        )
        search_query = func.plainto_tsquery('english', params.search)
        filters.append(search_vector.op('@@')(search_query))

    return filters
```

### Pattern 2: Filtering by Related Entity Fields

```python
# In repository build_filters method
from models.category import Category

def build_filters(self, params: ProductFilterParams, ...) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    # Filter by category name (not just ID)
    if params.category_name:
        filters.append(
            Product.category.has(
                Category.name.ilike(f"%{params.category_name}%")
            )
        )

    # Filter products that have at least one tag
    if params.has_tags is True:
        filters.append(Product.tags.any())
    elif params.has_tags is False:
        filters.append(~Product.tags.any())

    return filters
```

### Pattern 3: IN Filters (Multiple Values)

```python
# Filter schema
class ProductFilterParams(BaseModel):
    category_ids: list[UUID] | None = Field(
        None, max_length=10, description="Filter by multiple categories"
    )
    tags: list[str] | None = Field(
        None, max_length=20, description="Filter by tag names"
    )

# In repository _build_filters method
from models.tag import Tag

def build_filters(self, params: ProductFilterParams, ...) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    # IN filter for category IDs
    if params.category_ids:
        filters.append(Product.category_id.in_(params.category_ids))

    # Filter products having ALL specified tags
    if params.tags:
        for tag_name in params.tags:
            filters.append(Product.tags.any(Tag.name == tag_name))

    return filters
```

### Pattern 4: NULL Handling

```python
# Filter schema
class ProductFilterParams(BaseModel):
    has_discount: bool | None = Field(
        None, description="True=has discount, False=no discount, None=all"
    )

# In repository _build_filters method
def build_filters(self, params: ProductFilterParams, ...) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    # Explicit NULL checks
    if params.has_discount is True:
        filters.append(Product.discount_percentage.is_not(None))
        filters.append(Product.discount_percentage > 0)
    elif params.has_discount is False:
        filters.append(
            or_(
                Product.discount_percentage.is_(None),
                Product.discount_percentage == 0,
            )
        )

    return filters
```
