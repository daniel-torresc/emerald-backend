# Database Entry Update Flow

This document describes the recommended architecture for updating database entries through the API using a layered architecture pattern.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ROUTE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  Pydantic update schema (all fields optional)                    │
│  DOES:      - Extract HTTP context (IP, user agent, request ID)             │
│             - Call service method                                           │
│             - Convert response to Pydantic schema                           │
│  RETURNS:   Pydantic response schema (JSON)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: Pydantic schema + entity ID + context
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  Pydantic schema + entity_id + current_user + HTTP context       │
│  DOES:      - Fetch existing entity from repository                         │
│             - Permission checks (ownership, admin, etc.)                    │
│             - Business validation (uniqueness, constraints)                 │
│             - Capture old values for audit                                  │
│             - Apply changes to model instance                               │
│             - Handle side effects (balance updates, cascades)               │
│             - Call repository.update()                                      │
│             - Capture new values for audit                                  │
│             - Log audit event                                               │
│             - Commit transaction                                            │
│  RETURNS:   SQLAlchemy model instance                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: SQLAlchemy model instance
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  SQLAlchemy model instance (already modified)                    │
│  DOES:      - session.flush()                                               │
│             - session.refresh(instance)                                     │
│  RETURNS:   SQLAlchemy model instance (with updated timestamps)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Reference

| Layer | Input | Output | Responsibility |
|-------|-------|--------|----------------|
| **Route** | `EntityUpdate` (Pydantic) | `EntityResponse` (Pydantic) | HTTP handling |
| **Service** | `EntityUpdate` (Pydantic) | `Entity` (SQLAlchemy) | Business logic + model mutation |
| **Repository** | `Entity` (SQLAlchemy) | `Entity` (SQLAlchemy) | Persistence only |

## Key Concept: Partial Updates with `exclude_unset`

The critical pattern for PATCH operations is using `model_dump(exclude_unset=True)`:

```python
# Request body: {"username": "newname"}  (email not provided)
update_data = UserUpdate(username="newname")

# WITHOUT exclude_unset - WRONG!
update_data.model_dump()
# Returns: {"username": "newname", "email": None, "full_name": None}
# This would overwrite email and full_name with None!

# WITH exclude_unset - CORRECT!
update_data.model_dump(exclude_unset=True)
# Returns: {"username": "newname"}
# Only updates what was explicitly provided
```

## Code Example

### 1. Pydantic Update Schema

```python
# src/schemas/product.py

class ProductUpdate(BaseModel):
    """All fields optional for partial updates (PATCH)."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price: Decimal | None = Field(default=None, gt=0)
    category_id: uuid.UUID | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        """Only validate if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Name cannot be empty")
        return value
```

**Key characteristics:**
- All fields have `default=None`
- Validators guard with `if value is not None`
- Immutable fields (id, created_at) are excluded entirely

### 2. Route Layer

```python
# src/api/routes/products.py

@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,                    # Pydantic schema (all optional)
    request: Request,
    current_user: CurrentUser,
    service: ProductServiceDep,
) -> ProductResponse:
    product = await service.update_product(
        product_id=product_id,
        data=data,                          # Pass full schema
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return ProductResponse.model_validate(product)
```

### 3. Service Layer

```python
# src/services/product_service.py

class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
        self.audit_service = AuditService(session)

    async def update_product(
        self,
        product_id: uuid.UUID,
        data: ProductUpdate,                # Pydantic schema
        current_user: User,
        ip_address: str | None = None,
    ) -> Product:
        # 1. Fetch existing entity
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product")

        # 2. Permission check
        if product.created_by != current_user.id and not current_user.is_admin:
            raise AuthorizationError("Not authorized to update this product")

        # 3. Business validation (only if field is changing)
        if data.category_id and data.category_id != product.category_id:
            if not await self.category_repo.exists(data.category_id):
                raise NotFoundError("Category")

        # 4. Capture old values for audit
        old_values = {
            "name": product.name,
            "price": str(product.price),
            "category_id": str(product.category_id),
        }

        # 5. Apply changes to model instance
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(product, key, value)

        product.updated_by = current_user.id

        # 6. Persist changes
        product = await self.product_repo.update(product)

        # 7. Capture new values for audit
        new_values = {
            "name": product.name,
            "price": str(product.price),
            "category_id": str(product.category_id),
        }

        # 8. Log audit event
        await self.audit_service.log_data_change(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="product",
            entity_id=product_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )

        await self.session.commit()
        return product
```

### 4. Repository Layer

```python
# src/repositories/base.py

class BaseRepository(Generic[ModelType]):
    async def update(self, instance: ModelType) -> ModelType:
        """Persist changes to an already-modified model instance."""
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
```

## Advanced Pattern: Distinguishing "Not Provided" vs "Explicitly None"

For nullable fields where you need to allow clearing the value, use a sentinel:

```python
# src/services/transaction_service.py

from dataclasses import dataclass

@dataclass
class _UNSET:
    """Sentinel to distinguish 'not provided' from 'explicitly None'."""
    pass

UNSET = _UNSET()
```

### Route with Sentinel

```python
@router.patch("/{transaction_id}")
async def update_transaction(
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
    request: Request,
    current_user: CurrentUser,
    service: TransactionServiceDep,
) -> TransactionResponse:
    # Check if card_id was explicitly provided in request body
    request_body = await request.json()
    card_id_param = data.card_id if "card_id" in request_body else UNSET

    return await service.update_transaction(
        transaction_id=transaction_id,
        card_id=card_id_param,              # UNSET, None, or UUID
        # ... other fields
    )
```

### Service with Sentinel

```python
async def update_transaction(
    self,
    transaction_id: uuid.UUID,
    card_id: uuid.UUID | None | _UNSET = UNSET,
    # ... other fields
) -> Transaction:
    existing = await self.transaction_repo.get_by_id(transaction_id)

    # Only update card_id if explicitly provided
    if not isinstance(card_id, _UNSET):
        if card_id is not None:
            # Validate the new card exists
            card = await self.card_repo.get_by_id(card_id)
            if not card:
                raise NotFoundError("Card")
        existing.card_id = card_id  # Can be None to clear
```

**Use cases:**
- `card_id` not in request body → Don't change (UNSET)
- `"card_id": null` in request body → Clear the value (None)
- `"card_id": "uuid..."` in request body → Set new value

## Side Effects Pattern: Balance Updates

When an update affects related data:

```python
async def update_transaction(
    self,
    transaction_id: uuid.UUID,
    amount: Decimal | None = None,
    # ...
) -> Transaction:
    existing = await self.transaction_repo.get_by_id(transaction_id)

    # Calculate balance delta before applying changes
    old_amount = existing.amount
    new_amount = amount if amount is not None else old_amount
    balance_delta = new_amount - old_amount

    # Apply the update
    if amount is not None:
        existing.amount = amount

    await self.transaction_repo.update(existing)

    # Apply side effect: update account balance
    if balance_delta != 0:
        account = await self.account_repo.get_by_id(existing.account_id)
        account.current_balance += balance_delta
        await self.account_repo.update(account)

    await self.session.commit()
    return existing
```

## Permission Check Patterns

### Simple Ownership Check

```python
if product.created_by != current_user.id and not current_user.is_admin:
    raise AuthorizationError("Not authorized")
```

### Multi-Level Permission Check

```python
is_creator = existing.created_by == current_user.id
is_admin = current_user.is_admin
is_owner = await self.permission_service.check_permission(
    user_id=current_user.id,
    account_id=existing.account_id,
    required_permission=PermissionLevel.owner,
)

if not (is_creator or is_admin or is_owner):
    raise AuthorizationError("Not authorized to update this resource")
```

## Uniqueness Validation Pattern

Only check uniqueness if the field is actually changing:

```python
# Check email uniqueness only if changing
if data.email and data.email != user.email:
    existing = await self.user_repo.get_by_email(data.email)
    if existing:
        raise AlreadyExistsError("User with this email already exists")

# Check username uniqueness only if changing
if data.username and data.username != user.username:
    existing = await self.user_repo.get_by_username(data.username)
    if existing:
        raise AlreadyExistsError("User with this username already exists")
```

## Audit Logging Pattern

Track what changed for compliance:

```python
# Capture before update
old_values = {
    "name": product.name,
    "price": str(product.price),
}

# Apply updates...

# Capture after update
new_values = {
    "name": product.name,
    "price": str(product.price),
}

# Log with comprehensive metadata
await self.audit_service.log_data_change(
    user_id=current_user.id,
    action=AuditAction.UPDATE,
    entity_type="product",
    entity_id=product_id,
    old_values=old_values,
    new_values=new_values,
    extra_metadata={
        "changed_fields": list(update_dict.keys()),
    },
    ip_address=ip_address,
    user_agent=user_agent,
    request_id=request_id,
)
```

## Data Flow Summary

```
HTTP PATCH Request (JSON with partial fields)
    │
    ▼
[Route] ─── validates via ──→ ProductUpdate (Pydantic, all optional)
    │
    ▼
[Service] ─── fetches ──→ Existing Product (SQLAlchemy model)
    │
    ├── Permission check
    ├── Business validation
    ├── Capture old values
    │
    ▼
[Service] ─── applies ──→ model_dump(exclude_unset=True)
    │                      │
    │                      ▼
    │                setattr(product, key, value) for each field
    │
    ▼
[Repository] ─── persists ──→ session.flush() + refresh()
    │
    ▼
[Service] ─── captures ──→ New values for audit
    │
    ├── Log audit event
    ├── Handle side effects
    ├── session.commit()
    │
    ▼
[Route] ─── converts via ──→ ProductResponse (Pydantic)
    │
    ▼
HTTP Response (JSON)
```

## Key Principles

1. **All update schema fields are optional** - Enables partial updates
2. **Use `exclude_unset=True`** - Only update provided fields
3. **Fetch before update** - Always get current state first
4. **Permission checks in service** - Not in routes or repositories
5. **Capture old/new values** - Required for audit compliance
6. **Services modify, repositories persist** - Clear separation
7. **Handle side effects atomically** - All changes in one transaction
8. **Use sentinels for nullable fields** - When null is a valid update value

## References

- [FastAPI Body Updates Documentation](https://fastapi.tiangolo.com/tutorial/body-updates/)
- [SQLModel Update Tutorial](https://sqlmodel.tiangolo.com/tutorial/fastapi/update/)
- [Pydantic Partial Update Models Guide](https://www.getorchestra.io/guides/pydantic-partial-update-models-in-fastapi-a-tutorial)
