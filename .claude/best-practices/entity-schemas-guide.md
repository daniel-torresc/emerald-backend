# Entity Schema Patterns Guide

This document describes the recommended patterns for creating Pydantic schemas for different entity operations in FastAPI applications.

## Schema Types Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCHEMA HIERARCHY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EntityBase                    ← Shared fields across all schemas           │
│    ├── EntityCreate            ← POST /entities (input)                     │
│    ├── EntityUpdate            ← PATCH /entities/{id} (input)               │
│    ├── EntityResponse          ← Single entity response                     │
│    ├── EntityEmbedded          ← Nested in other responses                  │
│    └── EntityListItem          ← GET /entities (paginated list)             │
│                                                                             │
│  EntityFilterParams            ← GET /entities?filter (query params)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Reference

| Schema Type | Purpose | Used In | Required Fields | Optional Fields |
|-------------|---------|---------|-----------------|-----------------|
| **EntityBase** | Shared field definitions | All schemas | Core business fields | - |
| **EntityCreate** | Create operations | `POST /entities` | All required business fields | Optional business fields |
| **EntityUpdate** | Update operations | `PATCH /entities/{id}` | None (all optional) | All business fields |
| **EntityResponse** | Full entity with metadata | Single GET, POST, PATCH responses | All fields | - |
| **EntityEmbedded** | Nested in other entities | Related entity responses | `id`, `name` (minimal) | Optional display fields |
| **EntityListItem** | Simplified entity for lists | `GET /entities` items | Subset of entity fields | Optional fields |
| **EntityFilterParams** | Query filtering | `GET /entities?...` | None (all optional) | Entity-specific filter fields |

## Complete Example: Product Entity

### 1. Base Schema (Shared Fields)

```python
# src/schemas/product.py

from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    """
    Base schema containing shared fields across all product schemas.
    
    Guidelines:
    - Include only business-domain fields (not IDs, timestamps, audit fields)
    - Define validation rules once (reused by all schemas)
    - No fields should be marked as required here (let inheriting schemas decide)
    """
    name: str = Field(min_length=1, max_length=100, description="Product name")
    description: str | None = Field(None, max_length=500)
    price: Decimal = Field(gt=0, decimal_places=2, description="Price in USD")
    sku: str = Field(min_length=3, max_length=50, pattern=r"^[A-Z0-9-]+$")
    stock_quantity: int = Field(ge=0, description="Available stock")
    is_active: bool = Field(default=True)
    category_id: UUID
```

### 2. Create Schema (Input)

```python
class ProductCreate(ProductBase):
    """
    Schema for creating a new product via POST /products.
    
    Guidelines:
    - Inherits all fields from ProductBase
    - Make required fields explicit (remove defaults if needed)
    - Never include auto-generated fields (id, timestamps, audit fields)
    - Client cannot set created_by/updated_by (comes from current_user)
    """
    # All fields inherited from ProductBase
    # Override defaults if needed:
    is_active: bool = True  # Explicit default for new products
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Wireless Mouse",
                "description": "Ergonomic wireless mouse with USB receiver",
                "price": "29.99",
                "sku": "MOUSE-WL-001",
                "stock_quantity": 150,
                "is_active": True,
                "category_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )
```

### 3. Update Schema (Partial Input)

```python
class ProductUpdate(BaseModel):
    """
    Schema for updating a product via PATCH /products/{id}.
    
    Guidelines:
    - All fields are optional (partial updates)
    - Do NOT inherit from ProductBase (prevents required field issues)
    - Repeat field definitions with same validation rules
    - Use None as default to distinguish "not provided" from "set to null"
    - Never allow updating id, created_at, created_by
    """
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: Decimal | None = Field(None, gt=0, decimal_places=2)
    sku: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[A-Z0-9-]+$")
    stock_quantity: int | None = Field(None, ge=0)
    is_active: bool | None = None
    category_id: UUID | None = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": "34.99",
                "stock_quantity": 200,
                "is_active": False
            }
        }
    )
```

### 4. Response Schema (Full Output)

```python
from datetime import datetime


class ProductResponse(ProductBase):
    """
    Schema for product responses (GET, POST, PATCH).
    
    Guidelines:
    - Inherits business fields from ProductBase
    - Adds auto-generated fields (id, timestamps, audit)
    - Always use model_config with from_attributes=True
    - Include all fields client needs to display/process the entity
    """
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    
    # Related entities (if needed)
    category: "CategoryEmbedded | None" = None
    
    model_config = ConfigDict(
        from_attributes=True,  # Required for SQLAlchemy model conversion
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Wireless Mouse",
                "description": "Ergonomic wireless mouse with USB receiver",
                "price": "29.99",
                "sku": "MOUSE-WL-001",
                "stock_quantity": 150,
                "is_active": True,
                "category_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "created_by": "123e4567-e89b-12d3-a456-426614174002",
                "updated_by": "123e4567-e89b-12d3-a456-426614174002"
            }
        }
    )
```

### 5. Embedded Schema (Minimal Nested Response)

```python
class ProductEmbedded(BaseModel):
    """
    Minimal product representation for embedding in other entities.
    
    Guidelines:
    - Include only essential fields (usually id + display name)
    - Keep payload small (used in lists/nested objects)
    - No timestamps or audit fields
    - Add critical business fields if needed (e.g., price for order items)
    """
    id: UUID
    name: str
    sku: str
    price: Decimal  # Included because often needed in order contexts
    
    model_config = ConfigDict(from_attributes=True)
```

### 6. List Response Schema (Simplified for Lists)

```python
from pydantic import computed_field


class ProductListItem(BaseModel):
    """
    Simplified product representation for GET /products (list view).
    
    Guidelines:
    - Include only fields needed for list display (lighter than full Response)
    - Typically: id, name, key business fields, no timestamps/audit
    - Don't include pagination metadata (handled by common wrapper)
    - Can include computed/aggregated fields specific to list view
    """
    id: UUID
    name: str
    sku: str
    price: Decimal
    stock_quantity: int
    is_active: bool
    category: CategoryEmbedded
    
    # Optional: List-specific computed fields
    @computed_field
    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity < 10
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Wireless Mouse",
                "sku": "MOUSE-WL-001",
                "price": "29.99",
                "stock_quantity": 150,
                "is_active": True,
                "category": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Electronics"
                },
                "is_low_stock": False
            }
        }
    )
```

### 7. Filter Parameters Schema (Query String)

```python
class ProductFilterParams(BaseModel):
    """
    Schema for filtering products via query parameters.
    
    Guidelines:
    - All fields optional (filters are optional)
    - Include only entity-specific filter fields
    - Pagination (page, size) and sorting (sort_by, sort_order) handled by common schema
    - Use clear, descriptive field names
    """
    # Entity-specific filters only
    search: str | None = Field(None, max_length=100, description="Search in name/description")
    category_id: UUID | None = Field(None, description="Filter by category")
    min_price: Decimal | None = Field(None, ge=0, description="Minimum price")
    max_price: Decimal | None = Field(None, ge=0, description="Maximum price")
    is_active: bool | None = Field(None, description="Filter by active status")
    in_stock: bool | None = Field(None, description="Only show products with stock > 0")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search": "mouse",
                "category_id": "123e4567-e89b-12d3-a456-426614174000",
                "min_price": "10.00",
                "max_price": "50.00",
                "is_active": True,
                "in_stock": True
            }
        }
    )
```

## Usage in Routes

```python
# src/api/routes/products.py

from fastapi import APIRouter, Query, Depends
from src.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListItem,
    ProductFilterParams,
)
from src.schemas.common import PaginatedResponse, PaginationParams, SortParams, PaginationMeta

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,  # Input validation
    service: ProductServiceDep,
    current_user: CurrentUser,
) -> ProductResponse:
    """Create a new product."""
    product = await service.create_product(data, current_user)
    return ProductResponse.model_validate(product)


@router.get("", response_model=PaginatedResponse[ProductListItem])
async def list_products(
    filters: ProductFilterParams = Depends(),      # Entity-specific filters
    pagination: PaginationParams = Depends(),      # Common pagination (page, size)
    sorting: SortParams = Depends(),               # Common sorting (sort_by, sort_order)
    service: ProductServiceDep,
) -> PaginatedResponse[ProductListItem]:
    """List products with filtering, sorting, and pagination."""
    result = await service.list_products(filters, pagination, sorting)
    
    return PaginatedResponse(
        data=[ProductListItem.model_validate(p) for p in result.items],
        meta=PaginationMeta(
            total=result.total,
            page=pagination.page,
            page_size=pagination.page_size,
        ),
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    service: ProductServiceDep,
) -> ProductResponse:
    """Get a single product by ID."""
    product = await service.get_product(product_id)
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,  # Partial update
    service: ProductServiceDep,
    current_user: CurrentUser,
) -> ProductResponse:
    """Update a product (partial update)."""
    product = await service.update_product(product_id, data, current_user)
    return ProductResponse.model_validate(product)
```

## Advanced Patterns

### Pattern 1: Nested Entity Responses

```python
# When ProductResponse includes related entities
class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    # ... other fields
    
    # Use Embedded schemas for related entities
    category: CategoryEmbedded
    supplier: SupplierEmbedded | None = None
    tags: list[TagEmbedded] = []
    
    model_config = ConfigDict(from_attributes=True)
```

### Pattern 2: Computed Fields

```python
from pydantic import computed_field


class ProductResponse(ProductBase):
    id: UUID
    # ... other fields
    
    @computed_field
    @property
    def total_value(self) -> Decimal:
        """Computed: price * stock_quantity."""
        return self.price * Decimal(self.stock_quantity)
    
    @computed_field
    @property
    def is_low_stock(self) -> bool:
        """Computed: stock below threshold."""
        return self.stock_quantity < 10
    
    model_config = ConfigDict(from_attributes=True)
```

### Pattern 3: Conditional Fields (Field Visibility)

```python
class ProductResponse(ProductBase):
    id: UUID
    # ... other fields
    
    # Sensitive field only visible to admins (handled in route layer)
    cost_price: Decimal | None = Field(None, description="Only visible to admins")
    supplier_id: UUID | None = Field(None, description="Only visible to admins")
    
    model_config = ConfigDict(from_attributes=True)


# In route
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    service: ProductServiceDep,
    current_user: CurrentUser,
) -> ProductResponse:
    product = await service.get_product(product_id)
    response = ProductResponse.model_validate(product)
    
    # Hide sensitive fields for non-admins
    if not current_user.is_admin:
        response.cost_price = None
        response.supplier_id = None
    
    return response
```

### Pattern 4: Bulk Operations

```python
class ProductBulkCreate(BaseModel):
    """Schema for bulk product creation."""
    products: list[ProductCreate] = Field(min_length=1, max_length=100)


class ProductBulkCreateResponse(BaseModel):
    """Response for bulk creation."""
    created: list[ProductResponse]
    failed: list[dict] = Field(default_factory=list)
    total_created: int
    total_failed: int
```

### Pattern 5: Import/Export Schemas

```python
class ProductExport(BaseModel):
    """Flat schema for CSV/Excel export."""
    id: UUID
    name: str
    sku: str
    price: Decimal
    stock_quantity: int
    category_name: str  # Flattened from relation
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductImport(BaseModel):
    """Schema for CSV/Excel import (no UUIDs)."""
    name: str
    sku: str
    price: Decimal
    stock_quantity: int
    category_name: str  # Resolved to category_id in service
    is_active: bool = True
```

## Key Principles

### 1. Single Responsibility

Each schema has one clear purpose:
- **Create**: Validates input for new entities
- **Update**: Validates partial updates
- **Response**: Serializes entities for output
- **Embedded**: Minimal representation for nesting
- **Filter**: Validates query parameters

### 2. Don't Repeat Validation Rules

```python
# Bad: Repeating validation in multiple schemas
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)  # Duplicated!

# Good: Define once in Base, reuse
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ProductCreate(ProductBase):
    pass  # Inherits validation

class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)  # Still need to repeat for optional
```

### 3. Update Schemas Are Always Optional

```python
# Bad: Required fields in update schema
class ProductUpdate(ProductBase):
    name: str  # Forces client to send even if not updating

# Good: All fields optional
class ProductUpdate(BaseModel):
    name: str | None = None  # Client only sends what changes
```

### 4. Never Expose Implementation Details

```python
# Bad: Exposing database/internal fields
class ProductResponse(BaseModel):
    id: UUID
    name: str
    _sa_instance_state: Any  # SQLAlchemy internal - NEVER expose!
    password_hash: str  # Sensitive - NEVER expose!

# Good: Only business-relevant fields
class ProductResponse(BaseModel):
    id: UUID
    name: str
    # Only public, safe fields
```

### 5. Use `from_attributes=True` for Database Models

```python
# Required for converting SQLAlchemy models to Pydantic
class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)  # Essential!

# Usage
product = await session.get(Product, product_id)
return ProductResponse.model_validate(product)  # Works because of from_attributes
```

## Common Mistakes to Avoid

### ❌ Mistake 1: Using Create schema for Updates

```python
# Bad
@router.patch("/{id}")
async def update(id: UUID, data: ProductCreate):  # Wrong schema!
    # Forces client to send ALL fields, not just changes
```

### ❌ Mistake 2: Including Auto-Generated Fields in Input

```python
# Bad
class ProductCreate(BaseModel):
    id: UUID  # Server generates this!
    created_at: datetime  # Server generates this!
    name: str
```

### ❌ Mistake 3: Forgetting `from_attributes` on Response Schemas

```python
# Bad
class ProductResponse(BaseModel):
    id: UUID
    name: str
    # Missing: model_config = ConfigDict(from_attributes=True)

# This will fail:
product = await session.get(Product, id)
return ProductResponse.model_validate(product)  # Error!
```

### ❌ Mistake 4: Deeply Nested Responses

```python
# Bad: Causes N+1 queries and huge payloads
class ProductResponse(BaseModel):
    id: UUID
    category: CategoryResponse  # Full category
        supplier: SupplierResponse  # Full supplier
            country: CountryResponse  # Full country
                continent: ContinentResponse  # Too deep!

# Good: Use embedded schemas, limit nesting
class ProductResponse(BaseModel):
    id: UUID
    category: CategoryEmbedded  # Just id + name
```

### ❌ Mistake 5: No Examples in Schemas

```python
# Bad: No documentation
class ProductCreate(BaseModel):
    name: str
    price: Decimal

# Good: Include examples
class ProductCreate(BaseModel):
    name: str
    price: Decimal
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "Widget", "price": "19.99"}
        }
    )
```

## File Organization

```
src/
├── schemas/
│   ├── __init__.py
│   ├── product.py              # All product schemas
│   │   ├── ProductBase
│   │   ├── ProductCreate
│   │   ├── ProductUpdate
│   │   ├── ProductResponse
│   │   ├── ProductEmbedded
│   │   ├── ProductListItem
│   │   └── ProductFilterParams
│   ├── category.py             # All category schemas
│   ├── common.py               # Shared schemas (PaginatedResponse, etc.)
│   └── enums.py                # Shared enums (SortOrder, etc.)
```

## Schema Checklist

When creating a new entity, ensure you have:

- [ ] **Base schema** with shared field definitions
- [ ] **Create schema** for POST operations (required fields only)
- [ ] **Update schema** for PATCH operations (all fields optional)
- [ ] **Response schema** with all fields including auto-generated ones
- [ ] **Embedded schema** for use in related entity responses
- [ ] **List response schema** using generic pagination wrapper
- [ ] **Filter params schema** for query string parameters
- [ ] `model_config = ConfigDict(from_attributes=True)` on response schemas
- [ ] Examples in `json_schema_extra` for API documentation
- [ ] Validation rules on all input schemas
- [ ] No auto-generated fields (id, timestamps) in Create/Update schemas

## Summary

| Schema | Inherits From | All Fields Optional? | Includes Auto-Generated? | `from_attributes`? | Notes |
|--------|---------------|---------------------|-------------------------|--------------------|-------|
| Base | `BaseModel` | N/A (defines validation) | ❌ | ❌ | Shared field definitions |
| Create | `Base` | ❌ (required fields) | ❌ | ❌ | POST input validation |
| Update | `BaseModel` | ✅ | ❌ | ❌ | PATCH partial updates |
| Response | `Base` | ❌ | ✅ | ✅ | Full entity with metadata |
| Embedded | `BaseModel` | ❌ | ❌ | ✅ | Minimal for nesting |
| ListItem | `BaseModel` | ❌ | ❌ | ✅ | Simplified for lists (no pagination metadata) |
| FilterParams | `BaseModel` | ✅ | ❌ | ❌ | Entity filters only (no pagination/sort) |
