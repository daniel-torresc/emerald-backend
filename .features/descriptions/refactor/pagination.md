# API Pagination Standardization Report

## Executive Summary

This report documents a comprehensive review of all list endpoints in the Emerald Finance Platform backend to assess pagination implementation consistency. The analysis identified **9 list endpoints** across **7 route files**, revealing **three distinct pagination patterns** in use:

| Pattern | Parameter Style | Response Format | Endpoints Using |
|---------|-----------------|-----------------|-----------------|
| **Standard (Reference)** | `page` + `page_size` via `PaginationParams` | `PaginatedResponse[T]` | 4 endpoints |
| **Legacy Skip/Limit** | `skip` + `limit` inline | `list[T]` or custom | 3 endpoints |
| **No Pagination** | None | `list[T]` | 2 endpoints |

**Key Finding**: Only **4 of 9 endpoints (44%)** follow the reference pagination pattern. The remaining 5 endpoints need standardization to ensure API consistency and improve developer experience.

---

## Table of Contents

1. [Reference Implementation](#1-reference-implementation)
2. [Current State Inventory](#2-current-state-inventory)
3. [Endpoint Categorization](#3-endpoint-categorization)
4. [Detailed Analysis by Endpoint](#4-detailed-analysis-by-endpoint)
5. [Common Issues and Anti-patterns](#5-common-issues-and-anti-patterns)
6. [Action Plan](#6-action-plan)
7. [Implementation Checklist](#7-implementation-checklist)
8. [Migration Considerations](#8-migration-considerations)

---

## 1. Reference Implementation

### 1.1 PaginationParams Schema

**Location**: `src/schemas/common.py:19-42`

```python
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
```

### 1.2 PaginationMeta Schema

**Location**: `src/schemas/common.py:45-59`

```python
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
```

### 1.3 PaginatedResponse Schema

**Location**: `src/schemas/common.py:62-77`

```python
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
```

### 1.4 Reference Route Implementation

**Location**: `src/api/routes/financial_institutions.py:86-121`

```python
@router.get(
    "",
    response_model=PaginatedResponse[FinancialInstitutionListItem],
    summary="List financial institutions",
    description="List financial institutions with optional filtering and pagination",
)
async def list_institutions(
    pagination: PaginationParams = Depends(),
    filters: FinancialInstitutionFilterParams = Depends(),
    current_user: User = Depends(require_active_user),
    service: FinancialInstitutionService = Depends(get_financial_institution_service),
) -> PaginatedResponse[FinancialInstitutionListItem]:
    """..."""
    return await service.list_institutions(
        pagination=pagination,
        filters=filters,
    )
```

### 1.5 Reference Service Implementation

**Location**: `src/services/financial_institution_service.py:254-321`

```python
async def list_institutions(
    self,
    pagination: PaginationParams,
    filters: FinancialInstitutionFilterParams,
) -> PaginatedResponse[FinancialInstitutionListItem]:
    # Calculate offset
    offset = (pagination.page - 1) * pagination.page_size

    # Get institutions
    institutions = await self.institution_repo.search(
        query_text=filters.search,
        country_code=str(filters.country_code) if filters.country_code else None,
        institution_type=filters.institution_type,
        limit=pagination.page_size,
        offset=offset,
    )

    # Get total count
    total_count = await self.institution_repo.count_filtered(
        query_text=filters.search,
        country_code=str(filters.country_code) if filters.country_code else None,
        institution_type=filters.institution_type,
    )

    # Convert to list items
    items = [
        FinancialInstitutionListItem.model_validate(inst) for inst in institutions
    ]

    # Calculate pagination metadata
    total_pages = (
        (total_count + pagination.page_size - 1) // pagination.page_size
        if total_count > 0
        else 0
    )

    metadata = PaginationMeta(
        page=pagination.page,
        page_size=pagination.page_size,
        total=total_count,
        total_pages=total_pages,
    )

    return PaginatedResponse(data=items, meta=metadata)
```

### 1.6 Key Features of Reference Pattern

| Feature | Implementation |
|---------|----------------|
| **Parameter injection** | `PaginationParams = Depends()` - automatic query param binding |
| **1-indexed pages** | `page` starts at 1, not 0 |
| **Offset calculation** | `(page - 1) * page_size` |
| **Default page size** | 20 items per page |
| **Maximum page size** | 100 items (enforced via validator) |
| **Total count query** | Separate count query for accurate metadata |
| **Response structure** | `{ data: [...], meta: { total, page, page_size, total_pages } }` |

---

## 2. Current State Inventory

### 2.1 Complete Endpoint List

| # | Route | Method | File | Function | Response Type | Pagination |
|---|-------|--------|------|----------|---------------|------------|
| 1 | `/api/v1/financial-institutions` | GET | `financial_institutions.py` | `list_institutions` | `PaginatedResponse[FinancialInstitutionListItem]` | `PaginationParams` |
| 2 | `/api/v1/users` | GET | `users.py` | `list_users` | `PaginatedResponse[UserListItem]` | `page`/`page_size` inline |
| 3 | `/api/v1/audit-logs/users/me` | GET | `audit_logs.py` | `get_current_user_audit_logs` | `PaginatedResponse[AuditLogResponse]` | `page`/`page_size` inline |
| 4 | `/api/v1/audit-logs/users` | GET | `audit_logs.py` | `get_all_audit_logs` | `PaginatedResponse[AuditLogResponse]` | `page`/`page_size` inline |
| 5 | `/api/v1/accounts` | GET | `accounts.py` | `list_accounts` | `list[AccountListItem]` | `skip`/`limit` inline |
| 6 | `/api/v1/cards` | GET | `cards.py` | `list_cards` | `list[CardListItem]` | `skip`/`limit` inline |
| 7 | `/api/v1/accounts/{id}/transactions` | GET | `transactions.py` | `list_transactions` | `TransactionListResponse` | `skip`/`limit` via schema |
| 8 | `/api/v1/accounts/{id}/shares` | GET | `account_shares.py` | `list_shares` | `list[AccountShareResponse]` | None |
| 9 | `/api/v1/account-types` | GET | `account_types.py` | `list_account_types` | `list[AccountTypeListItem]` | None |

### 2.2 Statistics

- **Total list endpoints**: 9
- **Using `PaginatedResponse`**: 4 (44%)
- **Using `PaginationParams` dependency**: 1 (11%)
- **Using skip/limit pattern**: 3 (33%)
- **No pagination**: 2 (22%)

---

## 3. Endpoint Categorization

### Category A: Fully Compliant (1 endpoint)

Uses `PaginationParams` as dependency AND returns `PaginatedResponse[T]`.

| Endpoint | File | Notes |
|----------|------|-------|
| `GET /api/v1/financial-institutions` | `financial_institutions.py` | **Reference implementation** |

### Category B: Partial Implementation (3 endpoints)

Uses `PaginatedResponse[T]` but defines pagination params inline instead of using `PaginationParams`.

| Endpoint | File | Current Pattern | Issue |
|----------|------|-----------------|-------|
| `GET /api/v1/users` | `users.py` | `page`/`page_size` inline, constructs `PaginationParams` manually | Extra boilerplate, not using `Depends()` |
| `GET /api/v1/audit-logs/users/me` | `audit_logs.py` | `page`/`page_size` inline, manual offset calculation | Duplicated pagination logic |
| `GET /api/v1/audit-logs/users` | `audit_logs.py` | `page`/`page_size` inline, manual offset calculation | Duplicated logic + **broken total count** |

### Category C: Legacy Skip/Limit Pattern (3 endpoints)

Uses `skip`/`limit` parameters and returns plain `list[T]` or custom response.

| Endpoint | File | Current Pattern | Impact |
|----------|------|-----------------|--------|
| `GET /api/v1/accounts` | `accounts.py` | `skip`/`limit` inline, returns `list[AccountListItem]` | No pagination metadata |
| `GET /api/v1/cards` | `cards.py` | `skip`/`limit` inline, returns `list[CardListItem]` | No pagination metadata |
| `GET /api/v1/accounts/{id}/transactions` | `transactions.py` | `skip`/`limit` in `TransactionSearchParams`, custom `TransactionListResponse` | Custom response schema |

### Category D: No Pagination (2 endpoints)

Returns full dataset without any pagination support.

| Endpoint | File | Justification |
|----------|------|---------------|
| `GET /api/v1/accounts/{id}/shares` | `account_shares.py` | Limited dataset (typically <10 shares per account) |
| `GET /api/v1/account-types` | `account_types.py` | Reference data (typically <20 types total) |

---

## 4. Detailed Analysis by Endpoint

### 4.1 `GET /api/v1/users` - Category B

**File**: `src/api/routes/users.py:150-212`

**Current Implementation**:
```python
@router.get(
    "",
    response_model=PaginatedResponse[UserListItem],
)
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    is_superuser: bool | None = Query(default=None, ...),
    search: str | None = Query(default=None, ...),
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserListItem]:
    pagination = PaginationParams(page=page, page_size=page_size)
    filters = UserFilterParams(is_superuser=is_superuser, search=search)
    return await user_service.list_users(pagination=pagination, filters=filters, ...)
```

**Issues**:
1. Manually defines `page` and `page_size` instead of using `PaginationParams = Depends()`
2. Manually constructs `PaginationParams` object
3. Duplicate validation logic (already in `PaginationParams`)

**Proposed Change**:
```python
@router.get(
    "",
    response_model=PaginatedResponse[UserListItem],
)
async def list_users(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: UserFilterParams = Depends(),
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserListItem]:
    return await user_service.list_users(pagination=pagination, filters=filters, ...)
```

**Breaking Changes**: None (query params remain `page` and `page_size`)

---

### 4.2 `GET /api/v1/audit-logs/users/me` - Category B

**File**: `src/api/routes/audit_logs.py:30-112`

**Current Implementation**:
```python
async def get_current_user_audit_logs(
    request: Request,
    page: int = Query(default=1, ge=1, ...),
    page_size: int = Query(default=20, ge=1, le=100, ...),
    action: str | None = Query(...),
    # ... other filters
):
    logs, total = await audit_service.get_user_audit_logs(
        user_id=current_user.id,
        skip=(page - 1) * page_size,  # Manual offset calculation
        limit=page_size,
        ...
    )
    total_pages = (total + page_size - 1) // page_size  # Manual calculation
    return PaginatedResponse(
        data=log_responses,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )
```

**Issues**:
1. Manual offset calculation duplicated from reference
2. Manual total_pages calculation duplicated
3. Not using `PaginationParams` dependency

**Proposed Change**:
```python
async def get_current_user_audit_logs(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: AuditLogFilterParams = Depends(),  # New filter params schema
    current_user: User = Depends(require_active_user),
    audit_service: AuditService = Depends(get_audit_service),
) -> PaginatedResponse[AuditLogResponse]:
    return await audit_service.get_user_audit_logs_paginated(
        user_id=current_user.id,
        pagination=pagination,
        filters=filters,
    )
```

**Breaking Changes**: None (query params remain the same)

---

### 4.3 `GET /api/v1/audit-logs/users` - Category B (with bugs)

**File**: `src/api/routes/audit_logs.py:115-199`

**Current Implementation**:
```python
async def get_all_audit_logs(...):
    logs = await audit_service.get_all_audit_logs(
        skip=(page - 1) * page_size,
        limit=page_size,
        ...
    )
    # BUG: Total count is wrong - returns only current page count!
    total = len(logs)  # INCORRECT
    total_pages = 1 if logs else 0  # INCORRECT
```

**Issues**:
1. **Bug**: `total` is set to `len(logs)` which is the current page count, not total
2. **Bug**: `total_pages` is hardcoded to 1, breaking pagination metadata
3. TODO comment acknowledges missing count method
4. Same duplication issues as other audit endpoint

**Proposed Change**:
```python
# In AuditService - add count method
async def count_all_audit_logs(self, filters: AuditLogFilterParams) -> int:
    return await self.audit_repo.count_filtered(...)

# In route - use proper pagination
async def get_all_audit_logs(
    pagination: PaginationParams = Depends(),
    filters: AuditLogFilterParams = Depends(),
    ...
) -> PaginatedResponse[AuditLogResponse]:
    return await audit_service.get_all_audit_logs_paginated(pagination, filters)
```

**Breaking Changes**: API response will now have correct `total` and `total_pages` values (improvement, not breakage)

---

### 4.4 `GET /api/v1/accounts` - Category C

**File**: `src/api/routes/accounts.py:124-198`

**Current Implementation**:
```python
@router.get("", response_model=list[AccountListItem])
async def list_accounts(
    request: Request,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
    skip: Annotated[int, Query(ge=0, ...)] = 0,
    limit: Annotated[int, Query(ge=1, le=100, ...)] = 20,
    account_type_id: Annotated[uuid.UUID | None, Query(...)] = None,
    financial_institution_id: Annotated[uuid.UUID | None, Query(...)] = None,
) -> list[AccountListItem]:
    accounts = await account_service.list_accounts(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        ...
    )
    return [AccountListItem.model_validate(account) for account in accounts]
```

**Issues**:
1. Uses 0-indexed `skip` instead of 1-indexed `page`
2. Returns plain list without pagination metadata
3. Clients cannot know total count or total pages
4. Filter params defined inline instead of in a schema

**Proposed Change**:
```python
@router.get("", response_model=PaginatedResponse[AccountListItem])
async def list_accounts(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: AccountFilterParams = Depends(),  # New schema
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
) -> PaginatedResponse[AccountListItem]:
    return await account_service.list_accounts_paginated(
        user_id=current_user.id,
        pagination=pagination,
        filters=filters,
    )
```

**Breaking Changes**:
- Query params change from `skip`/`limit` to `page`/`page_size`
- Response structure changes from `[...]` to `{ data: [...], meta: {...} }`

---

### 4.5 `GET /api/v1/cards` - Category C

**File**: `src/api/routes/cards.py:25-84`

**Current Implementation**:
```python
@router.get("", response_model=list[CardListItem])
async def list_cards(
    card_type: CardType | None = Query(default=None, ...),
    account_id: uuid.UUID | None = Query(default=None, ...),
    include_deleted: bool = Query(default=False, ...),
    skip: int = Query(default=0, ge=0, ...),
    limit: int = Query(default=100, ge=1, le=100, ...),
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> list[CardListItem]:
    return await service.list_cards(
        current_user=current_user,
        skip=skip,
        limit=limit,
        ...
    )
```

**Issues**:
1. Uses 0-indexed `skip` instead of 1-indexed `page`
2. Default limit is 100 (differs from standard 20)
3. Returns plain list without pagination metadata
4. `include_deleted` filter is unusual (soft-delete bypass)

**Proposed Change**:
```python
@router.get("", response_model=PaginatedResponse[CardListItem])
async def list_cards(
    pagination: PaginationParams = Depends(),
    filters: CardFilterParams = Depends(),  # New schema with card_type, account_id, include_deleted
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> PaginatedResponse[CardListItem]:
    return await service.list_cards_paginated(
        current_user=current_user,
        pagination=pagination,
        filters=filters,
    )
```

**Breaking Changes**:
- Query params change from `skip`/`limit` to `page`/`page_size`
- Default page size changes from 100 to 20
- Response structure changes from `[...]` to `{ data: [...], meta: {...} }`

---

### 4.6 `GET /api/v1/accounts/{account_id}/transactions` - Category C

**File**: `src/api/routes/transactions.py:110-187`

**Current Implementation**:
```python
@router.get(
    "/accounts/{account_id}/transactions",
    response_model=TransactionListResponse,
)
async def list_transactions(
    request: Request,
    account_id: uuid.UUID = Path(...),
    search_params: TransactionSearchParams = Depends(),  # Has skip/limit
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionListResponse:
    transactions, total = await transaction_service.search_transactions(...)
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        skip=search_params.skip,
        limit=search_params.limit,
    )
```

**Custom Response Schema** (`src/schemas/transaction.py:440-456`):
```python
class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    skip: int
    limit: int
```

**Issues**:
1. Custom `TransactionListResponse` instead of `PaginatedResponse`
2. Uses `skip`/`limit` instead of `page`/`page_size`
3. Missing `total_pages` in response
4. `TransactionSearchParams` has pagination mixed with filters

**Proposed Change**:

1. Create separate `TransactionFilterParams`:
```python
class TransactionFilterParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    description: str | None = None
    merchant: str | None = None
    transaction_type: TransactionType | None = None
    card_id: uuid.UUID | None = None
    card_type: CardType | None = None
    sort_by: str = "transaction_date"
    sort_order: str = "desc"
```

2. Update route:
```python
@router.get(
    "/accounts/{account_id}/transactions",
    response_model=PaginatedResponse[TransactionResponse],
)
async def list_transactions(
    account_id: uuid.UUID = Path(...),
    pagination: PaginationParams = Depends(),
    filters: TransactionFilterParams = Depends(),
    ...
) -> PaginatedResponse[TransactionResponse]:
    return await transaction_service.list_transactions_paginated(
        account_id=account_id,
        pagination=pagination,
        filters=filters,
        ...
    )
```

**Breaking Changes**:
- Query params change from `skip`/`limit` to `page`/`page_size`
- Response structure changes significantly (different field names and structure)
- `TransactionSearchParams` becomes `TransactionFilterParams`

---

### 4.7 `GET /api/v1/accounts/{account_id}/shares` - Category D

**File**: `src/api/routes/account_shares.py:93-137`

**Current Implementation**:
```python
@router.get("/{account_id}/shares", response_model=list[AccountShareResponse])
async def list_shares(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> list[AccountShareResponse]:
    shares = await account_service.list_shares(account_id=account_id, current_user=current_user)
    return [AccountShareResponse.model_validate(share) for share in shares]
```

**Justification for No Pagination**:
- Account shares are limited by business rules (typically <10 per account)
- Full list is needed for UI display (permission management)
- Adding pagination would over-engineer for this use case

**Recommendation**: **Keep as-is**. No changes needed.

---

### 4.8 `GET /api/v1/account-types` - Category D

**File**: `src/api/routes/account_types.py:81-101`

**Current Implementation**:
```python
@router.get("", response_model=list[AccountTypeListItem])
async def list_account_types(
    current_user: User = Depends(require_active_user),
    service: AccountTypeService = Depends(get_account_type_service),
) -> list[AccountTypeListItem]:
    return await service.list_account_types()
```

**Justification for No Pagination**:
- Account types are system reference data (typically <20 types)
- Full list needed for dropdown menus
- Static data rarely grows beyond pagination threshold

**Recommendation**: **Keep as-is**. No changes needed.

---

## 5. Common Issues and Anti-patterns

### 5.1 Duplicated Pagination Logic

**Problem**: Multiple endpoints implement the same offset and total_pages calculations:
```python
offset = (page - 1) * page_size
total_pages = (total + page_size - 1) // page_size
```

**Solution**: Use `PaginationParams` dependency and helper utility:
```python
# In src/schemas/common.py
class PaginationParams(BaseModel):
    ...
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

def calculate_total_pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total > 0 else 0
```

### 5.2 Inconsistent Parameter Names

| Endpoint | Page Param | Size Param |
|----------|------------|------------|
| Financial Institutions | `page` | `page_size` |
| Users | `page` | `page_size` |
| Audit Logs | `page` | `page_size` |
| Accounts | `skip` | `limit` |
| Cards | `skip` | `limit` |
| Transactions | `skip` | `limit` |

**Solution**: Standardize all endpoints to use `page` and `page_size`.

### 5.3 Mixed Response Structures

| Pattern | Structure | Endpoints |
|---------|-----------|-----------|
| `PaginatedResponse` | `{ data: [...], meta: { total, page, page_size, total_pages } }` | 4 |
| Plain list | `[...]` | 3 |
| Custom | `{ items: [...], total, skip, limit }` | 1 |

**Solution**: Use `PaginatedResponse[T]` for all paginated endpoints.

### 5.4 Broken Total Count (Audit Logs Admin)

**Problem**: `get_all_audit_logs` returns incorrect `total` and `total_pages`:
```python
total = len(logs)  # Returns page count, not total count!
total_pages = 1 if logs else 0  # Always 0 or 1!
```

**Solution**: Add `count_all_audit_logs()` method to `AuditService` and `AuditLogRepository`.

### 5.5 Filter Parameters Mixed with Pagination

**Problem**: `TransactionSearchParams` combines filtering and pagination:
```python
class TransactionSearchParams(BaseModel):
    date_from: date | None = None  # Filter
    skip: int = 0  # Pagination
    limit: int = 20  # Pagination
```

**Solution**: Separate into `TransactionFilterParams` and use `PaginationParams` for pagination.

---

## 6. Action Plan

### 6.1 Priority Matrix

| Priority | Endpoint | Category | Complexity | Impact |
|----------|----------|----------|------------|--------|
| **P1 - Critical** | `GET /audit-logs/users` | B (buggy) | Medium | Fixes broken pagination |
| **P2 - High** | `GET /users` | B | Low | Already close to compliant |
| **P2 - High** | `GET /audit-logs/users/me` | B | Medium | Duplicated logic |
| **P3 - Medium** | `GET /accounts/{id}/transactions` | C | High | Breaking change |
| **P3 - Medium** | `GET /accounts` | C | Medium | Breaking change |
| **P3 - Medium** | `GET /cards` | C | Medium | Breaking change |
| **P4 - Low** | `GET /accounts/{id}/shares` | D | N/A | Keep as-is |
| **P4 - Low** | `GET /account-types` | D | N/A | Keep as-is |

### 6.2 Phased Implementation

#### Phase 1: Fix Critical Bug + Low-Hanging Fruit
- Fix `GET /audit-logs/users` total count bug
- Refactor `GET /users` to use `PaginationParams = Depends()`
- Refactor `GET /audit-logs/users/me` to use `PaginationParams = Depends()`

#### Phase 2: Create New Filter Schemas
- Create `AccountFilterParams` schema
- Create `CardFilterParams` schema
- Create `TransactionFilterParams` schema (extract from `TransactionSearchParams`)
- Create `AuditLogFilterParams` schema

#### Phase 3: Migrate Skip/Limit Endpoints (Breaking Changes)
- Migrate `GET /accounts` to page/page_size
- Migrate `GET /cards` to page/page_size
- Migrate `GET /accounts/{id}/transactions` to page/page_size
- Deprecate `TransactionListResponse` in favor of `PaginatedResponse`

### 6.3 Utility Enhancements

Add helper property/method to `PaginationParams`:

```python
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        """Calculate SQL OFFSET from page number."""
        return (self.page - 1) * self.page_size

    @staticmethod
    def calculate_total_pages(total: int, page_size: int) -> int:
        """Calculate total pages from total count."""
        return (total + page_size - 1) // page_size if total > 0 else 0
```

---

## 7. Implementation Checklist

### Per-Endpoint Checklist

For each endpoint being standardized:

- [ ] Update route handler signature to accept `PaginationParams = Depends()`
- [ ] Create or update filter params schema (if filters exist)
- [ ] Update filter params to use `Depends()` injection
- [ ] Modify service method to accept `PaginationParams`
- [ ] Update service to use `pagination.offset` property
- [ ] Add/verify `count_*` method in repository for total count
- [ ] Update response model to `PaginatedResponse[ItemType]`
- [ ] Calculate `total_pages` using helper function
- [ ] Return `PaginatedResponse(data=items, meta=PaginationMeta(...))`
- [ ] Update endpoint OpenAPI documentation
- [ ] Add/update integration tests for pagination behavior
- [ ] Test edge cases: empty results, first page, last page, out of bounds
- [ ] Document breaking changes (if any)

### New Files to Create

- [ ] `src/schemas/account.py` - Add `AccountFilterParams`
- [ ] `src/schemas/card.py` - Add `CardFilterParams`
- [ ] `src/schemas/audit.py` - Add `AuditLogFilterParams`
- [ ] `src/schemas/transaction.py` - Add `TransactionFilterParams` (modify existing)

### Repository Methods to Add

- [ ] `AuditLogRepository.count_filtered()` - for total count queries
- [ ] (Others may already exist - verify before implementation)

---

## 8. Migration Considerations

### 8.1 Breaking Changes Summary

| Endpoint | Change Type | Impact |
|----------|-------------|--------|
| `GET /accounts` | Parameter rename + response restructure | **BREAKING** |
| `GET /cards` | Parameter rename + response restructure + default change | **BREAKING** |
| `GET /transactions` | Parameter rename + response restructure | **BREAKING** |
| `GET /users` | None | Non-breaking |
| `GET /audit-logs/*` | None (fix bug) | Non-breaking (improvement) |

### 8.2 Migration Strategies

#### Option A: API Versioning (Recommended for Production)
- Keep `/api/v1/*` with current behavior
- Introduce `/api/v2/*` with standardized pagination
- Deprecate v1 endpoints with sunset date
- Allow clients to migrate at their pace

#### Option B: Query Parameter Aliases (Gradual Migration)
- Accept both `skip`/`limit` AND `page`/`page_size` temporarily
- Log deprecation warnings for old params
- Remove old params after migration period

#### Option C: Big Bang (Development/Early Stage Only)
- Update all endpoints simultaneously
- Update all clients simultaneously
- Suitable only if API is not yet in production

### 8.3 Backward Compatibility Shim (if needed)

```python
# Temporary compatibility layer
def pagination_compat(
    page: int | None = Query(None),
    page_size: int | None = Query(None),
    skip: int | None = Query(None),  # Deprecated
    limit: int | None = Query(None),  # Deprecated
) -> PaginationParams:
    """Support both old and new pagination params during migration."""
    if skip is not None or limit is not None:
        logger.warning("skip/limit params are deprecated, use page/page_size")
        page = (skip or 0) // (limit or 20) + 1
        page_size = limit or 20
    return PaginationParams(page=page or 1, page_size=page_size or 20)
```

However, it is not needed.

### 8.4 Testing Requirements

For each migrated endpoint:
1. Test default pagination (page=1, page_size=20)
2. Test custom page size
3. Test page navigation (page 2, page 3, etc.)
4. Test last page (partial results)
5. Test out-of-bounds page (empty results, correct metadata)
6. Test with filters applied
7. Test total count accuracy
8. Verify OpenAPI schema matches implementation

### 8.5 Documentation Updates

- Update API documentation (Swagger/OpenAPI)
- Update README/CLAUDE.md if pagination standards are documented
- Create migration guide for API consumers
- Update Postman/Insomnia collections

---

## Appendix A: Current vs Proposed Response Structures

### Current Structures

**Financial Institutions / Users / Audit Logs (Standard)**:
```json
{
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

**Accounts / Cards (Plain List)**:
```json
[
  { "id": "...", ... },
  { "id": "...", ... }
]
```

**Transactions (Custom)**:
```json
{
  "items": [...],
  "total": 100,
  "skip": 0,
  "limit": 20
}
```

### Proposed Structure (All Endpoints)

```json
{
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

## Appendix B: File Locations Reference

| Component | Location |
|-----------|----------|
| `PaginationParams` | `src/schemas/common.py:19-42` |
| `PaginationMeta` | `src/schemas/common.py:45-59` |
| `PaginatedResponse` | `src/schemas/common.py:62-77` |
| Reference route | `src/api/routes/financial_institutions.py:86-121` |
| Reference service | `src/services/financial_institution_service.py:254-321` |
| Users route | `src/api/routes/users.py:150-212` |
| Audit logs route | `src/api/routes/audit_logs.py` |
| Accounts route | `src/api/routes/accounts.py:124-198` |
| Cards route | `src/api/routes/cards.py:25-84` |
| Transactions route | `src/api/routes/transactions.py:110-187` |
| Account shares route | `src/api/routes/account_shares.py:93-137` |
| Account types route | `src/api/routes/account_types.py:81-101` |
| `TransactionSearchParams` | `src/schemas/transaction.py:543-635` |
| `TransactionListResponse` | `src/schemas/transaction.py:440-456` |
