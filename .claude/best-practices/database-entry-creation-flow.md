# Database Entry Creation Flow

This document describes the recommended architecture for creating database entries through the API using a layered architecture pattern.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ROUTE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  Pydantic schema (auto-validated by FastAPI)                     │
│  DOES:      - Extract HTTP context (IP, user agent, request ID)             │
│             - Call service method                                           │
│             - Convert response to Pydantic schema                           │
│  RETURNS:   Pydantic response schema (JSON)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: Pydantic schema + context
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  Pydantic schema + current_user + HTTP context                   │
│  DOES:      - Business validation (permissions, uniqueness, rules)          │
│             - Instantiate SQLAlchemy model from schema fields               │
│             - Call repository.add()                                         │
│             - Commit transaction                                            │
│             - Audit logging                                                 │
│  RETURNS:   SQLAlchemy model instance                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: SQLAlchemy model instance
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  SQLAlchemy model instance                                       │
│  DOES:      - session.add(instance)                                         │
│             - session.flush()                                               │
│             - session.refresh(instance)                                     │
│  RETURNS:   SQLAlchemy model instance (with ID + timestamps populated)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Reference

| Layer | Input | Output | Responsibility |
|-------|-------|--------|----------------|
| **Route** | `EntityCreate` (Pydantic) | `EntityResponse` (Pydantic) | HTTP handling |
| **Service** | `EntityCreate` (Pydantic) | `Entity` (SQLAlchemy) | Business logic + model creation |
| **Repository** | `Entity` (SQLAlchemy) | `Entity` (SQLAlchemy) | Persistence only |

## Code Example

### 1. Pydantic Schemas

```python
# src/schemas/product.py

class ProductCreate(BaseModel):
    """Input schema for API validation."""
    name: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0)
    category_id: uuid.UUID


class ProductResponse(BaseModel):
    """Output schema for API responses."""
    id: uuid.UUID
    name: str
    price: Decimal
    category_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 2. SQLAlchemy Model

```python
# src/models/product.py

class Product(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))

    category: Mapped["Category"] = relationship(back_populates="products")
```

### 3. Route Layer

```python
# src/api/routes/products.py

@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,                    # Pydantic schema (validated)
    request: Request,
    current_user: CurrentUser,
    service: ProductServiceDep,
) -> ProductResponse:
    product = await service.create_product(
        data=data,                          # Pass schema to service
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return ProductResponse.model_validate(product)  # Convert to response
```

### 4. Service Layer

```python
# src/services/product_service.py

class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)

    async def create_product(
        self,
        data: ProductCreate,                # Pydantic schema
        current_user: User,
        ip_address: str | None = None,
    ) -> Product:
        # Business validation
        if not await self.category_repo.exists(data.category_id):
            raise NotFoundError("Category")

        # Instantiate SQLAlchemy model
        product = Product(                  # Create model instance
            name=data.name,
            price=data.price,
            category_id=data.category_id,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        # Persist via repository
        product = await self.product_repo.add(product)
        await self.session.commit()

        return product                      # Return model instance
```

### 5. Repository Layer

```python
# src/repositories/base.py

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def add(self, instance: ModelType) -> ModelType:
        """Persist a model instance."""
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
```

## Key Principles

### 1. Pydantic Schemas at API Boundary Only

Pydantic schemas handle HTTP request/response validation. They should not leak into service or repository layers.

### 2. Model Instantiation in Services

Services are responsible for creating SQLAlchemy model instances. This provides:

- **Type safety**: IDE catches typos like `naem=` vs `name=`
- **Business logic encapsulation**: Model construction is domain logic
- **Validation at the right layer**: Business rules are enforced in services

### 3. Repositories Only Persist

Repositories receive fully-constructed model instances and handle only:

- Adding to session
- Flushing to database
- Refreshing to get generated values (ID, timestamps)

### 4. Services Commit, Repositories Flush

- **`flush()`**: Sends SQL to database but doesn't commit (can rollback)
- **`commit()`**: Finalizes transaction

Services control transaction boundaries, allowing multiple repository operations to be atomic.

## Why Not `**kwargs` in Repository?

```python
# Bad: No type checking, typos fail at runtime
await repo.create(
    naem="Product",      # Typo not caught
    prcie=Decimal("10"), # Typo not caught
)

# Good: Type hints catch errors immediately
product = Product(
    naem="Product",      # IDE error: unexpected keyword argument
)
```

## Data Flow Summary

```
HTTP Request (JSON)
    │
    ▼
[Route] ─── validates via ──→ ProductCreate (Pydantic)
    │
    ▼
[Service] ─── creates ──→ Product (SQLAlchemy model)
    │
    ▼
[Repository] ─── persists ──→ Database INSERT
    │
    ▼
[Repository] ─── returns ──→ Product (with ID + timestamps)
    │
    ▼
[Service] ─── returns ──→ Product
    │
    ▼
[Route] ─── converts via ──→ ProductResponse (Pydantic)
    │
    ▼
HTTP Response (JSON)
```