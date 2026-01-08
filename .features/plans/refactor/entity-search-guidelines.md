# Entity Search and List Implementation Refactoring Plan

## Executive Summary

This plan outlines a comprehensive refactoring of the entity search/list implementation across the Emerald Finance Platform backend. The goal is to standardize all list/search operations to follow the patterns defined in `.claude/best-practices/entity-search-guide.md`.

**Primary Objectives:**
- Standardize filter building in repository layer (not services)
- Implement consistent `build_filters()` and `build_order_by()` methods across all repositories
- Add entity-specific `SortParams` classes with typed sort field enums
- Remove redundant code and ensure consistent patterns across all entities
- Ensure BaseRepository provides generic `list()` and `count()` methods

**Expected Outcomes:**
- Clean separation: routes handle HTTP, services handle business logic, repositories handle query building
- All entities use the same search/list pattern
- Type-safe sorting with entity-specific sort field enums
- Reduced code duplication
- Easier maintenance and future entity additions

## Technical Architecture

### 2.1 System Design Overview

The refactored architecture follows the pattern from the entity-search-guide:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ROUTE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  - FilterParams (Pydantic - entity-specific filters)             │
│             - PaginationParams (Pydantic - common page/page_size)           │
│             - SortParams (Pydantic - entity-specific sort_by enum)          │
│  DOES:      - Extract query parameters via Depends()                        │
│             - Call service.list_xxx() / service.count_xxx()                 │
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
│             - Call repository.build_filters() with user context             │
│             - Call repository.build_order_by()                              │
│             - Call repository.list() and repository.count()                 │
│  RETURNS:   list[Model] and count separately                                │
│  NOTE:      NO SQLAlchemy imports - delegates query building to repository  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: filters list + order_by list + offset/limit
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  - FilterParams (Pydantic schema)                                │
│             - SortParams (Pydantic schema)                                  │
│             - user_id (optional, for ownership filtering)                   │
│  DOES:      - build_filters(): Convert FilterParams to SQLAlchemy list      │
│             - build_order_by(): Convert SortParams to SQLAlchemy order      │
│             - list(): Execute data query with filters/order/pagination      │
│             - count(): Execute count query with filters                     │
│             - Automatically filter soft-deleted records                     │
│  RETURNS:   list[Model] from list(), int from count()                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Current State vs Target State

| Aspect | Current State | Target State |
|--------|--------------|--------------|
| **Filter building** | Mixed (some in service, some in repo) | All in repository via `build_filters()` |
| **Sorting** | Inconsistent (some entities lack sorting) | All entities have `XxxSortParams` with typed enum |
| **Base repository** | Basic CRUD, no generic list/count with filters | Generic `list()` and `count()` accepting filter/order lists |
| **Service layer** | Contains SQLAlchemy imports in some cases | No SQLAlchemy imports, delegates to repository |
| **Pattern consistency** | Each entity has different patterns | Single pattern across all entities |

### 2.3 Entities to Refactor

| Entity | Filter Schema | Sort Enum | Sort Params | Current Issues |
|--------|---------------|-----------|-------------|----------------|
| **Transaction** | `TransactionFilterParams` ✓ | `TransactionSortField` ✓ | Missing `TransactionSortParams` | Filter logic in repo, needs sort params class |
| **Account** | `AccountFilterParams` ✓ | `AccountSortField` ✓ | Missing `AccountSortParams` | No sorting in list endpoint, manual list logic |
| **Card** | `CardFilterParams` ✓ | `CardSortField` ✓ | Missing `CardSortParams` | No sorting in list endpoint |
| **User** | `UserFilterParams` ✓ | `UserSortField` ✓ | Missing `UserSortParams` | Filter in service, needs refactor |
| **FinancialInstitution** | `FinancialInstitutionFilterParams` ✓ | `FinancialInstitutionSortField` ✓ | Missing `FinancialInstitutionSortParams` | No sorting in list endpoint |
| **AuditLog** | `AuditLogFilterParams` ✓ | `AuditLogSortField` ✓ | Missing `AuditLogSortParams` | Needs standardization |

## Implementation Specification

### 3.1 Component: Common Schemas Enhancement

**Files Involved:**
- `src/schemas/common.py`
- `src/schemas/enums.py` (create if needed)

**Purpose:** Ensure the base `SortParams` and common schemas are properly defined for type-safe sorting.

**Implementation Requirements:**

1. **Verify/Update `SortParams` in common.py:**
   - Ensure `SortParams[SortFieldType]` is generic and accepts entity-specific enum
   - Confirm `SortOrder` enum exists with `ASC`/`DESC`
   - No changes needed if already correct (current implementation looks good)

2. **Create `src/schemas/enums.py`:**
   - Move `SortOrder` enum here for better organization
   - Export all sort-related enums from this file

**Edge Cases:**
- Ensure backward compatibility with existing imports

**Tests:**
- [ ] Unit test: `SortParams` accepts entity-specific enum
- [ ] Unit test: `SortOrder` serializes correctly

**Acceptance Criteria:**
- [ ] `SortParams[T]` is generic and type-safe
- [ ] `SortOrder` enum is accessible from `schemas.enums`

---

### 3.2 Component: BaseRepository Enhancement

**Files Involved:**
- `src/repositories/base.py`

**Purpose:** Add generic `list()` and `count()` methods that accept pre-built filter and order_by lists. Add abstract methods for `build_filters()` and `build_order_by()`.

**Implementation Requirements:**

1. **Add abstract method signatures:**
   ```python
   from abc import ABC, abstractmethod
   from pydantic import BaseModel
   from sqlalchemy import ColumnElement, UnaryExpression
   from schemas.common import SortParams

   @abstractmethod
   def build_filters(
       self,
       params: BaseModel,
       user_id: UUID | None = None,
   ) -> list[ColumnElement[bool]]:
       """Convert Pydantic FilterParams to SQLAlchemy filter expressions."""
       raise NotImplementedError()

   @abstractmethod
   def build_order_by(
       self,
       params: SortParams,
   ) -> list[UnaryExpression]:
       """Convert SortParams to SQLAlchemy order_by expressions."""
       raise NotImplementedError()
   ```

2. **Add generic `list()` method:**
   ```python
   async def list(
       self,
       filters: list[ColumnElement[bool]],
       order_by: list[UnaryExpression],
       offset: int,
       limit: int,
       load_options: list[Load] | None = None,
   ) -> list[ModelType]:
       query = select(self.model)
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
   ```

3. **Add generic `count()` method with filters:**
   ```python
   async def count_filtered(
       self,
       filters: list[ColumnElement[bool]],
   ) -> int:
       query = select(func.count()).select_from(self.model)
       query = self._apply_soft_delete_filter(query)

       if filters:
           query = query.where(and_(*filters))

       return await self.session.scalar(query) or 0
   ```

**Edge Cases:**
- Empty filter list should return all non-deleted records
- Empty order_by list should use default model ordering (or id)

**Tests:**
- [ ] Unit test: `list()` with empty filters returns all records
- [ ] Unit test: `list()` applies filters correctly
- [ ] Unit test: `list()` applies ordering correctly
- [ ] Unit test: `count_filtered()` with filters returns correct count

**Acceptance Criteria:**
- [ ] `BaseRepository` has abstract `build_filters()` and `build_order_by()`
- [ ] Generic `list()` and `count_filtered()` methods work with any filter/order lists
- [ ] Soft delete filtering is automatic

---

### 3.3 Component: Entity-Specific Sort Params Classes

**Files Involved:**
- `src/schemas/transaction.py`
- `src/schemas/account.py`
- `src/schemas/card.py`
- `src/schemas/user.py`
- `src/schemas/financial_institution.py`
- `src/schemas/audit.py`

**Purpose:** Create entity-specific `XxxSortParams` classes that inherit from `SortParams[XxxSortField]` with default values.

**Implementation Requirements:**

For each entity, add a `XxxSortParams` class:

1. **TransactionSortParams:**
   ```python
   class TransactionSortParams(SortParams[TransactionSortField]):
       sort_by: TransactionSortField = Field(
           TransactionSortField.TRANSACTION_DATE,
           description="Field to sort by"
       )
   ```

2. **AccountSortParams:**
   ```python
   class AccountSortParams(SortParams[AccountSortField]):
       sort_by: AccountSortField = Field(
           AccountSortField.CREATED_AT,
           description="Field to sort by"
       )
   ```

3. **CardSortParams:**
   ```python
   class CardSortParams(SortParams[CardSortField]):
       sort_by: CardSortField = Field(
           CardSortField.CREATED_AT,
           description="Field to sort by"
       )
   ```

4. **UserSortParams:**
   ```python
   class UserSortParams(SortParams[UserSortField]):
       sort_by: UserSortField = Field(
           UserSortField.CREATED_AT,
           description="Field to sort by"
       )
   ```

5. **FinancialInstitutionSortParams:**
   ```python
   class FinancialInstitutionSortParams(SortParams[FinancialInstitutionSortField]):
       sort_by: FinancialInstitutionSortField = Field(
           FinancialInstitutionSortField.NAME,
           description="Field to sort by"
       )
   ```

6. **AuditLogSortParams:**
   ```python
   class AuditLogSortParams(SortParams[AuditLogSortField]):
       sort_by: AuditLogSortField = Field(
           AuditLogSortField.CREATED_AT,
           description="Field to sort by"
       )
   ```

**Edge Cases:**
- Ensure default sort field makes sense for each entity

**Tests:**
- [ ] Unit test: Each `XxxSortParams` has correct default values
- [ ] Unit test: Invalid sort field raises validation error

**Acceptance Criteria:**
- [ ] All 6 entities have entity-specific `XxxSortParams` class
- [ ] Each has sensible default sort field
- [ ] Type validation works (invalid enum values rejected)

---

### 3.4 Component: Repository Refactoring

**Files Involved:**
- `src/repositories/transaction_repository.py`
- `src/repositories/account_repository.py`
- `src/repositories/card_repository.py`
- `src/repositories/user_repository.py`
- `src/repositories/financial_institution_repository.py`
- `src/repositories/audit_log_repository.py`

**Purpose:** Implement `build_filters()` and `build_order_by()` methods in each repository.

#### 3.4.1 TransactionRepository

**Implementation:**
```python
def build_filters(
    self,
    params: TransactionFilterParams,
    account_id: UUID | None = None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if account_id is not None:
        filters.append(Transaction.account_id == account_id)

    if params.date_from is not None:
        filters.append(Transaction.transaction_date >= params.date_from)

    if params.date_to is not None:
        filters.append(Transaction.transaction_date <= params.date_to)

    if params.amount_min is not None:
        filters.append(Transaction.amount >= params.amount_min)

    if params.amount_max is not None:
        filters.append(Transaction.amount <= params.amount_max)

    if params.description:
        # Fuzzy search using pg_trgm similarity
        filters.append(
            func.similarity(Transaction.description, params.description) > 0.3
        )

    if params.merchant:
        filters.append(
            func.similarity(Transaction.merchant, params.merchant) > 0.3
        )

    if params.transaction_type is not None:
        filters.append(Transaction.transaction_type == params.transaction_type)

    if params.card_id is not None:
        filters.append(Transaction.card_id == params.card_id)

    if params.card_type is not None:
        filters.append(Transaction.card.has(Card.card_type == params.card_type))

    return filters

def build_order_by(
    self,
    params: TransactionSortParams,
) -> list[UnaryExpression]:
    order_by: list[UnaryExpression] = []

    sort_column = getattr(Transaction, params.sort_by.value)

    if params.sort_order == SortOrder.ASC:
        order_by.append(asc(sort_column))
    else:
        order_by.append(desc(sort_column))

    # Secondary sort for deterministic pagination
    order_by.append(desc(Transaction.id))

    return order_by
```

**Changes from current:**
- Remove `search_transactions()` method (use generic `list()` instead)
- Keep specialized methods like `get_children()`, `get_parent()`, etc.

#### 3.4.2 AccountRepository

**Implementation:**
```python
def build_filters(
    self,
    params: AccountFilterParams,
    user_id: UUID | None = None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if user_id is not None:
        filters.append(Account.user_id == user_id)

    if params.account_type_id is not None:
        filters.append(Account.account_type_id == params.account_type_id)

    if params.financial_institution_id is not None:
        filters.append(Account.financial_institution_id == params.financial_institution_id)

    return filters

def build_order_by(
    self,
    params: AccountSortParams,
) -> list[UnaryExpression]:
    order_by: list[UnaryExpression] = []

    sort_column = getattr(Account, params.sort_by.value)

    if params.sort_order == SortOrder.ASC:
        order_by.append(asc(sort_column))
    else:
        order_by.append(desc(sort_column))

    order_by.append(desc(Account.id))

    return order_by

def build_load_options(self) -> list[Load]:
    """Eager load institution and account type for list responses."""
    return [
        selectinload(Account.financial_institution),
        selectinload(Account.account_type),
    ]
```

#### 3.4.3 CardRepository

**Implementation:**
```python
def build_filters(
    self,
    params: CardFilterParams,
    user_id: UUID | None = None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if user_id is not None:
        # Cards are linked via account ownership
        filters.append(Card.account.has(Account.user_id == user_id))

    if params.card_type is not None:
        filters.append(Card.card_type == params.card_type)

    if params.account_id is not None:
        filters.append(Card.account_id == params.account_id)

    return filters

def build_order_by(
    self,
    params: CardSortParams,
) -> list[UnaryExpression]:
    order_by: list[UnaryExpression] = []

    sort_column = getattr(Card, params.sort_by.value)

    if params.sort_order == SortOrder.ASC:
        order_by.append(asc(sort_column))
    else:
        order_by.append(desc(sort_column))

    order_by.append(desc(Card.id))

    return order_by
```

#### 3.4.4 UserRepository

**Implementation:**
```python
def build_filters(
    self,
    params: UserFilterParams,
    user_id: UUID | None = None,  # Not used for users, but keep signature consistent
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if params.is_superuser is not None:
        filters.append(User.is_admin == params.is_superuser)

    if params.search:
        search_term = f"%{params.search}%"
        filters.append(
            or_(
                User.email.ilike(search_term),
                User.username.ilike(search_term),
            )
        )

    return filters

def build_order_by(
    self,
    params: UserSortParams,
) -> list[UnaryExpression]:
    order_by: list[UnaryExpression] = []

    sort_column = getattr(User, params.sort_by.value)

    if params.sort_order == SortOrder.ASC:
        order_by.append(asc(sort_column))
    else:
        order_by.append(desc(sort_column))

    order_by.append(desc(User.id))

    return order_by
```

#### 3.4.5 FinancialInstitutionRepository

**Implementation:**
```python
def build_filters(
    self,
    params: FinancialInstitutionFilterParams,
    user_id: UUID | None = None,  # Not used, but keep signature consistent
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if params.country_code is not None:
        filters.append(FinancialInstitution.country_code == params.country_code)

    if params.institution_type is not None:
        filters.append(FinancialInstitution.institution_type == params.institution_type)

    if params.search:
        search_term = f"%{params.search}%"
        filters.append(
            or_(
                FinancialInstitution.name.ilike(search_term),
                FinancialInstitution.short_name.ilike(search_term),
            )
        )

    return filters

def build_order_by(
    self,
    params: FinancialInstitutionSortParams,
) -> list[UnaryExpression]:
    order_by: list[UnaryExpression] = []

    sort_column = getattr(FinancialInstitution, params.sort_by.value)

    if params.sort_order == SortOrder.ASC:
        order_by.append(asc(sort_column))
    else:
        order_by.append(desc(sort_column))

    order_by.append(desc(FinancialInstitution.id))

    return order_by
```

#### 3.4.6 AuditLogRepository

**Implementation:**
```python
def build_filters(
    self,
    params: AuditLogFilterParams,
    user_id: UUID | None = None,  # Can be used to filter by actor
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []

    if params.user_id is not None:
        filters.append(AuditLog.user_id == params.user_id)

    if params.action is not None:
        filters.append(AuditLog.action == params.action)

    if params.entity_type is not None:
        filters.append(AuditLog.entity_type == params.entity_type)

    if params.entity_id is not None:
        filters.append(AuditLog.entity_id == params.entity_id)

    if params.status is not None:
        filters.append(AuditLog.status == params.status)

    if params.start_date is not None:
        filters.append(AuditLog.created_at >= params.start_date)

    if params.end_date is not None:
        filters.append(AuditLog.created_at <= params.end_date)

    return filters

def build_order_by(
    self,
    params: AuditLogSortParams,
) -> list[UnaryExpression]:
    order_by: list[UnaryExpression] = []

    sort_column = getattr(AuditLog, params.sort_by.value)

    if params.sort_order == SortOrder.ASC:
        order_by.append(asc(sort_column))
    else:
        order_by.append(desc(sort_column))

    order_by.append(desc(AuditLog.id))

    return order_by
```

**Edge Cases:**
- Handle None values in filter params gracefully (only add filter if value is not None)
- Ensure fuzzy search thresholds are consistent (0.3 for pg_trgm similarity)

**Tests:**
- [ ] Unit test: `build_filters()` returns empty list when no params set
- [ ] Unit test: `build_filters()` returns correct filters for each param
- [ ] Unit test: `build_order_by()` returns correct ASC/DESC ordering
- [ ] Integration test: Full list query with filters works correctly

**Acceptance Criteria:**
- [ ] All 6 repositories implement `build_filters()` and `build_order_by()`
- [ ] No SQLAlchemy code in service layer
- [ ] Consistent pattern across all repositories

---

### 3.5 Component: Service Layer Refactoring

**Files Involved:**
- `src/services/transaction_service.py`
- `src/services/account_service.py`
- `src/services/card_service.py`
- `src/services/user_service.py`
- `src/services/financial_institution_service.py`
- `src/services/audit_log_service.py`

**Purpose:** Refactor service list methods to delegate filter/order building to repository.

**Implementation Pattern (same for all services):**

```python
async def list_xxx(
    self,
    current_user: User,
    filters: XxxFilterParams,
    pagination: PaginationParams,
    sorting: XxxSortParams,
) -> list[Xxx]:
    """
    List xxx with filtering, sorting, and pagination.

    Args:
        current_user: Authenticated user (for permission checks)
        filters: Filter parameters
        pagination: Pagination parameters
        sorting: Sort parameters

    Returns:
        List of Xxx models
    """
    # 1. Permission check (entity-specific)
    # ...

    # 2. Build filters and order_by via repository
    filter_list = self.xxx_repo.build_filters(
        params=filters,
        user_id=current_user.id,  # Or None for admin-level queries
    )
    order_by = self.xxx_repo.build_order_by(params=sorting)

    # 3. Execute query
    return await self.xxx_repo.list(
        filters=filter_list,
        order_by=order_by,
        offset=pagination.offset,
        limit=pagination.page_size,
        load_options=self.xxx_repo.build_load_options(),  # If needed
    )

async def count_xxx(
    self,
    current_user: User,
    filters: XxxFilterParams,
) -> int:
    """Count xxx with filtering."""
    # Permission check...

    filter_list = self.xxx_repo.build_filters(
        params=filters,
        user_id=current_user.id,
    )

    return await self.xxx_repo.count_filtered(filters=filter_list)
```

**Changes per service:**

1. **TransactionService:**
   - Refactor `search()` to use the pattern above
   - Remove direct SQLAlchemy imports if any
   - Add `count_transactions()` method

2. **AccountService:**
   - Refactor `list_user_accounts()` to use the pattern
   - Handle owned + shared accounts (may need two queries)
   - Add sorting support
   - Add `count_user_accounts()` using new pattern

3. **CardService:**
   - Refactor `list_cards()` to use the pattern
   - Add sorting support

4. **UserService:**
   - Refactor `list_users()` to use the pattern
   - Already has filtering, just standardize to use repository methods

5. **FinancialInstitutionService:**
   - Refactor `list_institutions()` to use the pattern
   - Add sorting support

6. **AuditLogService:**
   - If exists, refactor list method
   - If not, this is likely in routes directly - create service method

**Edge Cases:**
- AccountService: Handle combined owned + shared accounts list
- Handle cases where user_id is not applicable (admin queries)

**Tests:**
- [ ] Unit test: Service calls repository `build_filters()` correctly
- [ ] Unit test: Service calls repository `build_order_by()` correctly
- [ ] Integration test: Full list operation returns correct data

**Acceptance Criteria:**
- [ ] No SQLAlchemy imports in service files
- [ ] All list methods follow the same pattern
- [ ] Permission checks remain in service layer

---

### 3.6 Component: API Routes Refactoring

**Files Involved:**
- `src/api/routes/transactions.py`
- `src/api/routes/accounts.py`
- `src/api/routes/cards.py`
- `src/api/routes/users.py`
- `src/api/routes/financial_institutions.py`
- `src/api/routes/audit_logs.py`

**Purpose:** Update routes to use entity-specific `XxxSortParams` and build responses consistently.

**Implementation Pattern:**

```python
@router.get("", response_model=PaginatedResponse[XxxListItem])
async def list_xxx(
    current_user: CurrentUser,
    filters: XxxFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
    sorting: XxxSortParams = Depends(),
    service: XxxService = Depends(get_xxx_service),
) -> PaginatedResponse[XxxListItem]:
    """List xxx with filtering, sorting, and pagination."""

    # Get data and count
    items = await service.list_xxx(
        current_user=current_user,
        filters=filters,
        pagination=pagination,
        sorting=sorting,
    )

    count = await service.count_xxx(
        current_user=current_user,
        filters=filters,
    )

    # Build response
    return PaginatedResponse(
        data=[XxxListItem.model_validate(item) for item in items],
        meta=PaginationMeta(
            total=count,
            page=pagination.page,
            page_size=pagination.page_size,
        ),
    )
```

**Changes per route:**

1. **transactions.py:**
   - Change `SortParams` to `TransactionSortParams`
   - Ensure filter/pagination/sorting are all separate Depends()

2. **accounts.py:**
   - Add `AccountSortParams` parameter
   - Update endpoint to use new service methods

3. **cards.py:**
   - Add `CardSortParams` parameter

4. **users.py:**
   - Add `UserSortParams` parameter

5. **financial_institutions.py:**
   - Add `FinancialInstitutionSortParams` parameter

6. **audit_logs.py:**
   - Add `AuditLogSortParams` parameter

**Edge Cases:**
- Ensure query parameter names don't conflict (sort_by vs filter fields)

**Tests:**
- [ ] Integration test: Route accepts all query parameters correctly
- [ ] Integration test: Route returns correct response format
- [ ] Integration test: Invalid sort field returns 422

**Acceptance Criteria:**
- [ ] All list routes accept entity-specific `XxxSortParams`
- [ ] Routes use `Depends()` for all parameter types
- [ ] Response format is consistent (`PaginatedResponse[XxxListItem]`)

---

### 3.7 Code to Remove

**Purpose:** Clean up deprecated/redundant methods and schemas.

**Items to Remove:**

1. **TransactionRepository:**
   - Remove `search_transactions()` method (replaced by generic `list()`)
   - Keep `get_by_account_id()`, `get_children()`, etc. (specialized queries)

2. **AccountRepository:**
   - Remove `get_by_user()` method (replaced by `build_filters() + list()`)
   - Keep `get_by_name()`, `exists_by_name()`, etc.

3. **FinancialInstitutionRepository:**
   - Remove `search()` and `search_count()` (replaced by generic methods)
   - Keep `get_by_swift_code()`, `get_by_routing_number()`, etc.

4. **UserRepository:**
   - Remove `filter_users()` and `count_filtered()` (replaced by generic methods)

5. **CardRepository:**
   - Remove `search_by_user()` and `search_count_by_user()` (replaced by generic methods)

**Acceptance Criteria:**
- [ ] No dead code remains
- [ ] All tests still pass after removal

---

## Implementation Roadmap

### Phase 1: Foundation (Size: M, Priority: P0)

**Goal:** Set up base infrastructure for the new pattern.

**Scope:**
- ✅ Include: BaseRepository enhancements, SortParams classes creation
- ❌ Exclude: Service/route refactoring

**Components to Implement:**
- [ ] Update `BaseRepository` with `list()`, `count_filtered()`, abstract methods
- [ ] Create all 6 entity-specific `XxxSortParams` classes
- [ ] Create `src/schemas/enums.py` if beneficial

**Detailed Tasks:**
1. [ ] Update `src/repositories/base.py`:
   - Add imports for `ColumnElement`, `UnaryExpression`, `and_`, `Load`
   - Add abstract `build_filters()` method signature
   - Add abstract `build_order_by()` method signature
   - Add `list()` method implementation
   - Add `count_filtered()` method implementation

2. [ ] Update `src/schemas/transaction.py`:
   - Add `TransactionSortParams` class with default `TRANSACTION_DATE`

3. [ ] Update `src/schemas/account.py`:
   - Add `AccountSortParams` class with default `CREATED_AT`

4. [ ] Update `src/schemas/card.py`:
   - Add `CardSortParams` class with default `CREATED_AT`

5. [ ] Update `src/schemas/user.py`:
   - Add `UserSortParams` class with default `CREATED_AT`

6. [ ] Update `src/schemas/financial_institution.py`:
   - Add `FinancialInstitutionSortParams` class with default `NAME`

7. [ ] Update `src/schemas/audit.py`:
   - Add `AuditLogSortParams` class with default `CREATED_AT`

**Validation Criteria:**
- [ ] All new schema classes are importable
- [ ] BaseRepository abstract methods are defined
- [ ] Code lints and type checks pass

**Estimated Effort:** ~2 hours

---

### Phase 2: Repository Implementation (Size: L, Priority: P0)

**Goal:** Implement `build_filters()` and `build_order_by()` in all repositories.

**Scope:**
- ✅ Include: All 6 repository implementations
- ❌ Exclude: Service changes (repositories still expose old methods)

**Components to Implement:**
- [ ] TransactionRepository `build_filters()` and `build_order_by()`
- [ ] AccountRepository `build_filters()` and `build_order_by()`
- [ ] CardRepository `build_filters()` and `build_order_by()`
- [ ] UserRepository `build_filters()` and `build_order_by()`
- [ ] FinancialInstitutionRepository `build_filters()` and `build_order_by()`
- [ ] AuditLogRepository `build_filters()` and `build_order_by()`

**Detailed Tasks:**
1. [ ] Implement TransactionRepository methods
2. [ ] Implement AccountRepository methods (include `build_load_options()`)
3. [ ] Implement CardRepository methods (include `build_load_options()`)
4. [ ] Implement UserRepository methods
5. [ ] Implement FinancialInstitutionRepository methods
6. [ ] Implement AuditLogRepository methods (create file if not exists)

**Validation Criteria:**
- [ ] All repositories implement abstract methods
- [ ] Unit tests pass for filter/order building
- [ ] Existing functionality still works (old methods still exist)

**Estimated Effort:** ~4 hours

---

### Phase 3: Service Refactoring (Size: L, Priority: P0)

**Goal:** Refactor service list methods to use new repository pattern.

**Scope:**
- ✅ Include: All 6 service list methods
- ❌ Exclude: Route changes

**Components to Implement:**
- [ ] TransactionService `search()` refactor
- [ ] AccountService `list_user_accounts()` refactor
- [ ] CardService `list_cards()` refactor
- [ ] UserService `list_users()` refactor
- [ ] FinancialInstitutionService `list_institutions()` refactor
- [ ] AuditLogService list method (create if needed)

**Detailed Tasks:**
1. [ ] Refactor TransactionService.search() to use build_filters/build_order_by
2. [ ] Refactor AccountService.list_user_accounts() (handle owned + shared)
3. [ ] Refactor CardService.list_cards()
4. [ ] Refactor UserService.list_users()
5. [ ] Refactor FinancialInstitutionService.list_institutions()
6. [ ] Create or refactor audit log listing

**Validation Criteria:**
- [ ] No SQLAlchemy imports in service files (except for type hints if needed)
- [ ] All list methods follow the same pattern
- [ ] Integration tests pass

**Estimated Effort:** ~4 hours

---

### Phase 4: Route Updates (Size: M, Priority: P0)

**Goal:** Update API routes to use entity-specific sort params.

**Scope:**
- ✅ Include: All list route endpoints
- ❌ Exclude: N/A

**Components to Implement:**
- [ ] Update transactions route
- [ ] Update accounts route
- [ ] Update cards route
- [ ] Update users route
- [ ] Update financial_institutions route
- [ ] Update audit_logs route

**Detailed Tasks:**
1. [ ] Update `src/api/routes/transactions.py`:
   - Import `TransactionSortParams`
   - Change `SortParams` dependency to `TransactionSortParams`

2. [ ] Update `src/api/routes/accounts.py`:
   - Import `AccountSortParams`
   - Add sorting parameter to list endpoint

3. [ ] Update `src/api/routes/cards.py`:
   - Import `CardSortParams`
   - Add sorting parameter to list endpoint

4. [ ] Update `src/api/routes/users.py`:
   - Import `UserSortParams`
   - Add/update sorting parameter

5. [ ] Update `src/api/routes/financial_institutions.py`:
   - Import `FinancialInstitutionSortParams`
   - Add sorting parameter

6. [ ] Update `src/api/routes/audit_logs.py`:
   - Import `AuditLogSortParams`
   - Add/update sorting parameter

**Validation Criteria:**
- [ ] All routes accept proper sorting parameters
- [ ] Swagger docs show correct enum values for sort_by
- [ ] Integration tests pass with sorting

**Estimated Effort:** ~2 hours

---

### Phase 5: Cleanup (Size: S, Priority: P1)

**Goal:** Remove deprecated methods and ensure clean codebase.

**Scope:**
- ✅ Include: Remove old repository methods
- ❌ Exclude: N/A

**Components to Implement:**
- [ ] Remove deprecated repository methods
- [ ] Update any remaining references

**Detailed Tasks:**
1. [ ] Remove `TransactionRepository.search_transactions()` if fully replaced
2. [ ] Remove `AccountRepository.get_by_user()` if fully replaced
3. [ ] Remove `FinancialInstitutionRepository.search()` and `search_count()`
4. [ ] Remove `UserRepository.filter_users()` and `count_filtered()`
5. [ ] Remove `CardRepository.search_by_user()` and `search_count_by_user()`
6. [ ] Run full test suite to ensure nothing breaks
7. [ ] Update any documentation

**Validation Criteria:**
- [ ] No dead code
- [ ] All tests pass
- [ ] Code coverage maintained at 80%+

**Estimated Effort:** ~1 hour

---

### Implementation Sequence

```
Phase 1 (P0, ~2h): Foundation
  ↓
Phase 2 (P0, ~4h): Repository Implementation
  ↓
Phase 3 (P0, ~4h): Service Refactoring
  ↓
Phase 4 (P0, ~2h): Route Updates
  ↓
Phase 5 (P1, ~1h): Cleanup
```

**Rationale for ordering:**
- Phase 1 establishes the base patterns (must come first)
- Phase 2 implements repository methods that services will call
- Phase 3 depends on Phase 2 (services use repository methods)
- Phase 4 depends on Phase 3 (routes call service methods)
- Phase 5 cleanup happens last after everything is working

**Total Estimated Effort:** ~13 hours

---

## Simplicity & Design Validation

**Simplicity Checklist:**
- [x] Is this the SIMPLEST solution? Yes - follows established patterns from the guide
- [x] Have we avoided premature optimization? Yes - no caching or complex features
- [x] Does this align with existing patterns? Yes - extends existing BaseRepository
- [x] Can we deliver value in smaller increments? Yes - phased approach
- [x] Are we solving the actual problem? Yes - standardizing search/list across entities

**Alternatives Considered:**

1. **Keep current mixed approach:**
   - Pro: No refactoring effort
   - Con: Inconsistent patterns, harder to maintain, code duplication
   - Decision: Rejected - technical debt will grow

2. **Create separate SearchRepository class:**
   - Pro: Complete separation of concerns
   - Con: More files, more indirection, overkill for current needs
   - Decision: Rejected - simpler to add methods to existing repositories

3. **Use a query builder library (e.g., SQLAlchemy-Filters):**
   - Pro: More features out of the box
   - Con: External dependency, learning curve, less control
   - Decision: Rejected - our pattern is sufficient and keeps control

**Rationale:** The proposed approach follows the established guide, minimizes external dependencies, and provides a clear migration path with backward compatibility during transition.

---

## References & Related Documents

- `.claude/best-practices/entity-search-guide.md` - The canonical guide this plan implements
- `.claude/standards/backend.md` - Backend development standards
- FastAPI dependency injection documentation
- SQLAlchemy 2.0 async query patterns
- Pydantic v2 generic models documentation
