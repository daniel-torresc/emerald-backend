# Entity Search and List Implementation Guide

This document describes the recommended patterns for implementing entity search/list operations in a layered architecture (API → Service → Repository) with FastAPI and SQLAlchemy.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ROUTE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  - FilterParams (Pydantic - entity-specific filters)             │
│             - PaginationParams (Pydantic - common page/size)                │
│             - SortParams (Pydantic - common sort_by/sort_order)             │
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
│             - Build SQLAlchemy filter expressions from FilterParams         │
│             - Call repository.list_and_count()                              │
│  RETURNS:   SearchResult(items=list[Model], total=int)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: SQLAlchemy filters + offset + limit + order_by
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  - filters: list[ColumnElement] (SQLAlchemy expressions)         │
│             - offset: int                                                   │
│             - limit: int                                                    │
│             - order_by: list[ColumnElement] (SQLAlchemy expressions)        │
│  DOES:      - Build SELECT query with filters                               │
│             - Execute count query (without limit/offset)                    │
│             - Execute data query (with limit/offset/order)                  │
│  RETURNS:   SearchResult(items=list[Model], total=int)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Reference

| Layer | Input | Output | Responsibility |
|-------|-------|--------|----------------|
| **Route** | FilterParams, PaginationParams, SortParams | PaginatedResponse(data, meta) | HTTP handling, response assembly |
| **Service** | FilterParams, PaginationParams, SortParams | SearchResult(items, total) | Business logic, filter building |
| **Repository** | SQLAlchemy filters, offset, limit, order_by | SearchResult(items, total) | Query execution, data retrieval |

## Complete Example: Product Search

### 1. Common Schemas (Shared Across Entities)

```python
# src/schemas/common.py

from typing import Generic, TypeVar
from pydantic import BaseModel, Field, computed_field
from enum import Enum


T = TypeVar("T")


class SortOrder(str, Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @computed_field
    @property
    def offset(self) -> int:
        """Calculate offset from page and size."""
        return (self.page - 1) * self.size


class SortParams(BaseModel):
    """Common sorting parameters."""
    sort_by: str | None = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort direction")


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

    @computed_field  # included in serialization
    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 0


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


class SearchResult(BaseModel, Generic[T]):
    """Internal search result container (not exposed to API)."""
    items: list[T]
    total: int
```

### 2. Entity-Specific Filter Schema

```python
# src/schemas/product.py

from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class ProductFilterParams(BaseModel):
    """
    Entity-specific filter parameters for products.
    
    Guidelines:
    - All fields optional (filters are optional)
    - No pagination or sorting fields (handled by common schemas)
    - Use clear, descriptive field names
    - Validate ranges and formats
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

### 3. Entity Sort Fields Enum

```python
# src/schemas/product.py

from enum import Enum


class ProductSortField(str, Enum):
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

### 4. API Route Layer

```python
# src/api/routes/products.py

from fastapi import APIRouter, Depends
from src.schemas.product import (
    ProductFilterParams,
    ProductListResponse,
    ProductSortField,
)
from src.schemas.common import (
    PaginationParams,
    SortParams,
    PaginatedResponse,
)
from src.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductListResponse])
async def list_products(
    # Entity-specific filters
    filters: ProductFilterParams = Depends(),
    
    # Common pagination
    pagination: PaginationParams = Depends(),
    
    # Common sorting
    sorting: SortParams = Depends(),
    
    # Dependencies
    service: ProductService = Depends(get_product_service),
) -> PaginatedResponse[ProductListResponse]:
    """
    List products with filtering, sorting, and pagination.
    
    Query Parameters:
    - Filters: search, category_id, min_price, max_price, is_active, etc.
    - Pagination: page, size
    - Sorting: sort_by, sort_order
    """
    # Validate sort field
    if sorting.sort_by and sorting.sort_by not in ProductSortField.__members__.values():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field. Allowed: {', '.join(ProductSortField.__members__.values())}"
        )
    
    # Call service
    result = await service.list_products(
        filters=filters,
        pagination=pagination,
        sorting=sorting,
    )

    # Build response
    return PaginatedResponse(
        data=[ProductListResponse.model_validate(p) for p in result.items],
        meta=PaginationMeta(
            total=result.total,
            page=pagination.page,
            page_size=pagination.size,
        ),
    )
```

### 5. Service Layer

```python
# src/services/product_service.py

from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.product import Product
from src.repositories.product_repository import ProductRepository
from src.schemas.product import ProductFilterParams, ProductSortField
from src.schemas.common import PaginationParams, SortParams, SearchResult, SortOrder


class ProductService:
    """
    Product business logic and filter building.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ProductRepository(session)
    
    async def list_products(
        self,
        filters: ProductFilterParams,
        pagination: PaginationParams,
        sorting: SortParams,
    ) -> SearchResult[Product]:
        """
        List products with filtering, sorting, and pagination.
        
        Responsibilities:
        - Build SQLAlchemy filter expressions from Pydantic FilterParams
        - Apply business logic (e.g., filter by user permissions)
        - Build order_by expressions
        - Call repository with SQLAlchemy expressions
        """
        # Build filter expressions
        filter_expressions = self._build_filters(filters)
        
        # Build order_by expressions
        order_by_expressions = self._build_order_by(sorting)
        
        # Call repository
        result = await self.repository.list_and_count(
            filters=filter_expressions,
            offset=pagination.offset,
            limit=pagination.size,
            order_by=order_by_expressions,
        )
        
        return result
    
    def _build_filters(self, params: ProductFilterParams) -> list:
        """
        Convert Pydantic FilterParams to SQLAlchemy filter expressions.
        
        Guidelines:
        - Return a list of SQLAlchemy ColumnElement (filter conditions)
        - Only add filters for non-None values
        - Use appropriate SQLAlchemy operators (==, >=, <=, like, ilike, in_, etc.)
        - Combine related conditions (e.g., range filters)
        """
        filters = []
        
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
    
    def _build_order_by(self, params: SortParams) -> list:
        """
        Convert SortParams to SQLAlchemy order_by expressions.
        
        Guidelines:
        - Return a list of SQLAlchemy ColumnElement (order by clauses)
        - Validate sort field against allowed enum
        - Apply sort direction (asc/desc)
        - Provide default sorting if not specified
        """
        order_by = []
        
        if params.sort_by:
            # Get the model column
            sort_column = getattr(Product, params.sort_by)
            
            # Apply sort direction
            if params.sort_order == SortOrder.ASC:
                order_by.append(asc(sort_column))
            else:
                order_by.append(desc(sort_column))
        else:
            # Default sorting: newest first
            order_by.append(desc(Product.created_at))
        
        # Add secondary sort for consistency (especially for pagination)
        order_by.append(desc(Product.id))
        
        return order_by
```

### 6. Repository Layer

```python
# src/repositories/product_repository.py

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.product import Product
from src.schemas.common import SearchResult


class ProductRepository:
    """
    Product data access layer.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def list_and_count(
        self,
        filters: list | None = None,
        offset: int = 0,
        limit: int = 20,
        order_by: list | None = None,
    ) -> SearchResult[Product]:
        """
        Retrieve products with filtering, pagination, and total count.
        
        Returns:
            SearchResult containing:
            - items: List of Product models
            - total: Total count of items matching filters (without pagination)
        
        Guidelines:
        - Execute count query FIRST (without limit/offset for accurate total)
        - Execute data query SECOND (with limit/offset/order_by)
        - Both queries use the same base filters for consistency
        - Use efficient count query (avoid subqueries when possible)
        """
        filters = filters or []
        order_by = order_by or []
        
        # Build base query with filters
        base_query = select(Product)
        
        # Apply filters
        if filters:
            base_query = base_query.where(and_(*filters))
        
        # --- COUNT QUERY (without limit/offset) ---
        # Build count query from base query
        count_query = (
            select(func.count())
            .select_from(Product)
        )
        
        # Apply same filters to count query
        if filters:
            count_query = count_query.where(and_(*filters))
        
        # Execute count query
        total = await self.session.scalar(count_query)
        
        # --- DATA QUERY (with limit/offset/order_by) ---
        data_query = base_query
        
        # Apply ordering
        if order_by:
            data_query = data_query.order_by(*order_by)
        
        # Apply pagination
        data_query = data_query.offset(offset).limit(limit)
        
        # Execute data query
        result = await self.session.execute(data_query)
        items = result.scalars().all()
        
        return SearchResult(
            items=list(items),
            total=total or 0,
        )
```

### 7. Advanced Repository Pattern (with Joins)

```python
# src/repositories/product_repository.py (advanced)

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from src.models.product import Product
from src.models.category import Category


class ProductRepository:
    """Product data access with relationship loading."""
    
    async def list_and_count(
        self,
        filters: list | None = None,
        offset: int = 0,
        limit: int = 20,
        order_by: list | None = None,
        load_relationships: bool = False,
    ) -> SearchResult[Product]:
        """
        Retrieve products with optional relationship loading.
        
        Args:
            filters: SQLAlchemy filter expressions
            offset: Number of items to skip
            limit: Maximum number of items to return
            order_by: SQLAlchemy order by expressions
            load_relationships: If True, eagerly load related entities
        """
        filters = filters or []
        order_by = order_by or []
        
        # Count query (no joins needed for count)
        count_query = (
            select(func.count())
            .select_from(Product)
        )
        
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total = await self.session.scalar(count_query)
        
        # Data query
        data_query = select(Product)
        
        # Apply filters
        if filters:
            data_query = data_query.where(and_(*filters))
        
        # Eagerly load relationships if requested
        if load_relationships:
            data_query = data_query.options(
                selectinload(Product.category),  # One-to-many: separate query
                selectinload(Product.tags),      # Many-to-many: separate query
            )
        
        # Apply ordering
        if order_by:
            data_query = data_query.order_by(*order_by)
        
        # Apply pagination
        data_query = data_query.offset(offset).limit(limit)
        
        # Execute
        result = await self.session.execute(data_query)
        items = result.unique().scalars().all()  # unique() needed when using joinedload
        
        return SearchResult(
            items=list(items),
            total=total or 0,
        )
```

## Advanced Patterns

### Pattern 1: Full-Text Search (PostgreSQL)

```python
# Service layer
from sqlalchemy import func, cast, String

def _build_filters(self, params: ProductFilterParams) -> list:
    filters = []
    
    if params.search:
        # PostgreSQL full-text search
        search_vector = func.to_tsvector('english', 
            func.concat(Product.name, ' ', Product.description)
        )
        search_query = func.plainto_tsquery('english', params.search)
        filters.append(search_vector.op('@@')(search_query))
    
    return filters
```

### Pattern 2: Filtering by Related Entity Fields

```python
# Service layer
from sqlalchemy import exists
from src.models.category import Category

def _build_filters(self, params: ProductFilterParams) -> list:
    filters = []
    
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
    category_ids: list[UUID] | None = Field(None, max_length=10, description="Filter by multiple categories")
    tags: list[str] | None = Field(None, max_length=20, description="Filter by tag names")

# Service layer
def _build_filters(self, params: ProductFilterParams) -> list:
    filters = []
    
    # IN filter for category IDs
    if params.category_ids:
        filters.append(Product.category_id.in_(params.category_ids))
    
    # Filter products having ALL specified tags
    if params.tags:
        for tag_name in params.tags:
            filters.append(
                Product.tags.any(Tag.name == tag_name)
            )
    
    return filters
```

### Pattern 4: NULL Handling

```python
# Filter schema
class ProductFilterParams(BaseModel):
    has_discount: bool | None = Field(None, description="True=has discount, False=no discount, None=all")

# Service layer
def _build_filters(self, params: ProductFilterParams) -> list:
    filters = []
    
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

### Pattern 5: Dynamic Filter Building (Advanced)

```python
# src/repositories/base.py

from typing import TypeVar, Generic
from sqlalchemy import select, func, and_

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository with reusable list_and_count.
    """
    
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def list_and_count(
        self,
        filters: list | None = None,
        offset: int = 0,
        limit: int = 20,
        order_by: list | None = None,
    ) -> SearchResult[ModelType]:
        """Generic list and count for any model."""
        filters = filters or []
        order_by = order_by or []
        
        # Count
        count_query = select(func.count()).select_from(self.model)
        if filters:
            count_query = count_query.where(and_(*filters))
        total = await self.session.scalar(count_query)
        
        # Data
        data_query = select(self.model)
        if filters:
            data_query = data_query.where(and_(*filters))
        if order_by:
            data_query = data_query.order_by(*order_by)
        data_query = data_query.offset(offset).limit(limit)
        
        result = await self.session.execute(data_query)
        items = result.scalars().all()
        
        return SearchResult(items=list(items), total=total or 0)


# Usage
class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)
```

## Key Principles

### 1. Separation of Concerns

Each layer has a clear responsibility:
- **Route**: HTTP request/response handling, parameter extraction
- **Service**: Business logic, filter expression building, permissions
- **Repository**: Data access, query execution

### 2. Type Safety Throughout

- **Route**: Pydantic schemas validate input
- **Service**: Builds type-safe SQLAlchemy expressions
- **Repository**: Returns strongly-typed SearchResult

### 3. Filter Building in Service Layer

```python
# Good: Service builds SQLAlchemy expressions
filters = [Product.price >= params.min_price]
await repository.list_and_count(filters=filters)

# Bad: Passing Pydantic schema to repository
await repository.list_and_count(params=params)  # Repository shouldn't know about Pydantic
```

### 4. Efficient Count Queries

```python
# Good: Simple count without subquery
count_query = select(func.count()).select_from(Product).where(and_(*filters))

# Bad: Count with unnecessary complexity
count_query = select(func.count()).select_from(
    select(Product).where(and_(*filters)).subquery()
)
```

### 5. Consistent Sorting for Pagination

```python
# Good: Always include secondary sort for deterministic pagination
order_by = [desc(Product.created_at), desc(Product.id)]

# Bad: Single field sort can cause inconsistent pagination
order_by = [desc(Product.created_at)]
```

## Common Mistakes to Avoid

### ❌ Mistake 1: Passing Pydantic Schemas to Repository

```python
# Bad
async def list_products(filters: ProductFilterParams):
    return await repository.list_and_count(filters=filters)

# Good
async def list_products(filters: ProductFilterParams):
    filter_expressions = self._build_filters(filters)
    return await repository.list_and_count(filters=filter_expressions)
```

### ❌ Mistake 2: Count Query with Limit/Offset

```python
# Bad: Count query has limit/offset (wrong total count)
count_query = select(func.count()).select_from(Product).limit(20)

# Good: Count query has NO limit/offset
count_query = select(func.count()).select_from(Product)
```

### ❌ Mistake 3: Different Filters for Count and Data

```python
# Bad: Different filters lead to inconsistent counts
count_total = await session.scalar(select(func.count()).select_from(Product))
items = await session.scalars(
    select(Product).where(Product.is_active == True).limit(20)
)

# Good: Same filters for both queries
filters = [Product.is_active == True]
count_query = select(func.count()).select_from(Product).where(and_(*filters))
data_query = select(Product).where(and_(*filters)).limit(20)
```

### ❌ Mistake 4: Not Using Enums for Sort Fields

```python
# Bad: SQL injection risk, no validation
sort_by = params.sort_by  # User can pass anything!
query = query.order_by(text(f"{sort_by} DESC"))

# Good: Whitelisted enum, no injection risk
if params.sort_by not in ProductSortField.__members__.values():
    raise ValueError("Invalid sort field")
sort_column = getattr(Product, params.sort_by)
query = query.order_by(desc(sort_column))
```

### ❌ Mistake 5: Forgetting to Handle None in Range Filters

```python
# Bad: Will filter out NULL values unintentionally
filters.append(Product.discount >= params.min_discount)  # Excludes NULL

# Good: Only filter if value is provided
if params.min_discount is not None:
    filters.append(Product.discount >= params.min_discount)
```

### ❌ Mistake 6: N+1 Query Problem

```python
# Bad: Lazy loading causes N+1 queries
products = await repository.list_and_count(...)
for product in products.items:
    print(product.category.name)  # Triggers separate query per product!

# Good: Eager loading
products = await repository.list_and_count(
    load_relationships=True  # Uses selectinload/joinedload
)
for product in products.items:
    print(product.category.name)  # No additional queries
```

## Performance Optimization

### 1. Index Sort and Filter Columns

```python
# src/models/product.py

from sqlalchemy import Index

class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)  # Frequently filtered
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), index=True)  # Frequently sorted
    created_at: Mapped[datetime] = mapped_column(index=True)  # Default sort
    
    # Composite index for common filter combinations
    __table_args__ = (
        Index('ix_product_category_active', 'category_id', 'is_active'),
    )
```

### 2. Use Appropriate Loading Strategy

```python
# Selectinload: Best for one-to-many (separate query, IN clause)
query.options(selectinload(Product.tags))

# Joinedload: Best for many-to-one (LEFT OUTER JOIN)
query.options(joinedload(Product.category))

# Avoid: Lazy loading in loops (N+1 problem)
```

### 3. Limit Result Set Size

```python
# Always enforce max page size
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)  # Max 100 items per page
```

## Summary Table

| Aspect | Route | Service | Repository |
|--------|-------|---------|------------|
| Input | Pydantic schemas | Pydantic schemas | SQLAlchemy expressions |
| Output | Pydantic response | SearchResult[Model] | SearchResult[Model] |
| Filter Building | ❌ | ✅ | ❌ |
| Query Execution | ❌ | ❌ | ✅ |
| Business Logic | ❌ | ✅ | ❌ |
| Validation | HTTP params | Business rules | None (trusts service) |

## Checklist for New Search Endpoint

- [ ] Create entity-specific `FilterParams` schema (no pagination/sort fields)
- [ ] Create entity-specific `SortField` enum
- [ ] Create entity-specific `ListResponse` schema (simplified)
- [ ] Implement `_build_filters()` in service layer
- [ ] Implement `_build_order_by()` in service layer
- [ ] Use `list_and_count()` in repository (or create it if using BaseRepository)
- [ ] Add route with proper `Depends()` for all parameter types
- [ ] Validate sort fields in route or service
- [ ] Add indexes on frequently filtered/sorted columns
- [ ] Write unit tests for filter building
- [ ] Write integration tests for repository
- [ ] Test pagination edge cases (empty results, last page)