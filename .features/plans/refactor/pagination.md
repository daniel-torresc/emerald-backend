# API Pagination Standardization - Implementation Plan

## 1. Executive Summary

This plan outlines the standardization of pagination across all list endpoints in the Emerald Finance Platform backend. Currently, only 44% of endpoints (4 of 9) follow the reference pagination pattern using `PaginationParams` and `PaginatedResponse[T]`. The remaining endpoints use inconsistent patterns (skip/limit, inline parameters, no pagination) that create API inconsistency and poor developer experience.

The goal is to standardize all paginated endpoints to use:
- **Input**: `PaginationParams = Depends()` with `page` (1-indexed) and `page_size` parameters
- **Output**: `PaginatedResponse[T]` with `{ data: [...], meta: { total, page, page_size, total_pages } }`

This refactoring will fix a critical bug in the admin audit logs endpoint (incorrect total count), eliminate code duplication, and create a consistent API surface for frontend consumers.

**Expected Outcomes:**
- 100% consistency across all paginated list endpoints
- Fixed pagination metadata bug in `GET /audit-logs/users`
- Reduced code duplication through centralized pagination logic
- Improved developer experience with predictable API responses
- Clean separation of filter parameters from pagination parameters

---

## 2. Technical Architecture

### 2.1 System Design Overview

The pagination standardization follows the existing layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (src/api/routes/)                                │
│  - Use PaginationParams = Depends() for pagination          │
│  - Use *FilterParams = Depends() for filtering              │
│  - Return PaginatedResponse[ItemType]                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer (src/services/)                              │
│  - Accept PaginationParams and FilterParams                 │
│  - Use pagination.offset property for SQL OFFSET            │
│  - Call repository for data + count                         │
│  - Construct and return PaginatedResponse                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Repository Layer (src/repositories/)                       │
│  - Provide count_filtered() methods for total count         │
│  - Accept offset/limit for pagination                       │
│  - Return data lists                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Decisions

**FastAPI Depends() Pattern**
- **Purpose**: Automatic query parameter injection and validation
- **Why this choice**: Already used in reference implementation, reduces boilerplate, provides automatic OpenAPI documentation
- **Alternatives considered**: Manual Query parameters (current inconsistent pattern) - rejected for code duplication

**PaginatedResponse[T] Generic**
- **Purpose**: Type-safe paginated response wrapper
- **Why this choice**: Already implemented in `src/schemas/common.py`, provides consistent structure
- **Alternatives considered**: Custom response schemas per endpoint - rejected for inconsistency

### 2.3 File Structure

Files to be modified/created:

```
src/
├── schemas/
│   ├── common.py           # Add offset property to PaginationParams
│   ├── account.py          # Add AccountFilterParams
│   ├── card.py             # Add CardFilterParams
│   ├── audit.py            # Add AuditLogFilterParams
│   └── transaction.py      # Extract TransactionFilterParams from TransactionSearchParams
├── api/routes/
│   ├── users.py            # Refactor to use PaginationParams = Depends()
│   ├── audit_logs.py       # Fix bug + refactor to use Depends()
│   ├── accounts.py         # Convert skip/limit to page/page_size
│   ├── cards.py            # Convert skip/limit to page/page_size
│   └── transactions.py     # Convert skip/limit to page/page_size
├── services/
│   ├── audit_service.py    # Add count_all_audit_logs method
│   ├── account_service.py  # Add list_accounts_paginated method
│   ├── card_service.py     # Add list_cards_paginated method
│   └── transaction_service.py # Update to use PaginationParams
└── repositories/
    └── audit_repository.py # Add count_all_logs method
tests/
└── integration/
    ├── test_account_routes.py    # Update pagination tests
    ├── test_card_routes.py       # Update pagination tests
    ├── test_transaction_api.py   # Update pagination tests
    └── test_audit_logs_routes.py # Add pagination tests (new file)
```

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: PaginationParams Enhancement

**Files Involved**:
- `src/schemas/common.py`

**Purpose**: Add utility property to eliminate duplicated offset calculation across services

**Implementation Requirements**:

1. **Core Logic**:
   - Add `offset` computed property: `(self.page - 1) * self.page_size`
   - Add `calculate_total_pages` static method for consistent calculation

2. **Data Handling**:
   - No changes to input validation (already correct)
   - Property is read-only, derived from existing fields

3. **Edge Cases & Error Handling**:
   - [x] page=1 returns offset=0
   - [x] page_size validation already handles >100 case

**Acceptance Criteria**:
- [x] `PaginationParams(page=1, page_size=20).offset == 0`
- [x] `PaginationParams(page=2, page_size=20).offset == 20`
- [x] `PaginationParams.calculate_total_pages(100, 20) == 5`
- [x] `PaginationParams.calculate_total_pages(0, 20) == 0`

---

#### Component: AuditLogFilterParams Schema

**Files Involved**:
- `src/schemas/audit.py`

**Purpose**: Extract filter parameters into dedicated schema for consistency with other endpoints

**Implementation Requirements**:

1. **Core Logic**:
   - Create `AuditLogFilterParams` with fields: `action`, `entity_type`, `status`, `start_date`, `end_date`
   - Use Pydantic validation for enum conversion

2. **Data Handling**:
   - Input: String query parameters for action/status (converted to enums)
   - Output: Typed enum values or None

3. **Testing Requirements**:
   - [x] Unit test: Valid action string converts to AuditAction enum
   - [x] Unit test: Invalid action string raises validation error
   - [x] Unit test: Optional fields default to None

**Acceptance Criteria**:
- [x] Schema accepts all documented filter parameters
- [x] Proper enum conversion for action and status fields
- [x] Works with `Depends()` injection in routes

---

#### Component: AccountFilterParams Schema

**Files Involved**:
- `src/schemas/account.py`

**Purpose**: Consolidate inline account filter parameters into a dedicated schema

**Implementation Requirements**:

1. **Core Logic**:
   - Create `AccountFilterParams` with fields: `account_type_id`, `financial_institution_id`
   - Use UUID type for ID fields with Query description

2. **Data Handling**:
   - Input: Optional UUID query parameters
   - Output: Typed UUID values or None

3. **Testing Requirements**:
   - [x] Unit test: Valid UUID string converts properly
   - [x] Unit test: Optional fields default to None

**Acceptance Criteria**:
- [x] Schema accepts documented filter parameters
- [x] Works with `Depends()` injection in routes

---

#### Component: CardFilterParams Schema

**Files Involved**:
- `src/schemas/card.py`

**Purpose**: Consolidate inline card filter parameters into a dedicated schema

**Implementation Requirements**:

1. **Core Logic**:
   - Create `CardFilterParams` with fields: `card_type`, `account_id`, `include_deleted`
   - Use CardType enum for card_type field

2. **Data Handling**:
   - Input: Optional CardType enum, UUID, boolean query parameters
   - Output: Typed values or defaults

3. **Testing Requirements**:
   - [x] Unit test: CardType enum validates correctly
   - [x] Unit test: include_deleted defaults to False

**Acceptance Criteria**:
- [x] Schema accepts documented filter parameters
- [x] Works with `Depends()` injection in routes

---

#### Component: TransactionFilterParams Schema

**Files Involved**:
- `src/schemas/transaction.py`

**Purpose**: Extract filter parameters from `TransactionSearchParams`, keeping pagination separate

**Implementation Requirements**:

1. **Core Logic**:
   - Create `TransactionFilterParams` with all current filter fields from `TransactionSearchParams`
   - Remove `skip` and `limit` fields (use `PaginationParams` instead)
   - Keep `sort_by` and `sort_order` in filter params (sorting is filtering concern)

2. **Data Handling**:
   - Input: All existing filter parameters (date_from, date_to, amount_min, etc.)
   - Output: Typed values for service layer

3. **Edge Cases & Error Handling**:
   - [x] date_from > date_to should still work (service handles logic)
   - [x] amount_min > amount_max should still work (service handles logic)

4. **Testing Requirements**:
   - [x] Unit test: All filter fields accept valid values
   - [x] Unit test: sort_by validates against allowed values
   - [x] Unit test: sort_order validates against asc/desc

**Acceptance Criteria**:
- [x] All filter fields from TransactionSearchParams are preserved
- [x] skip/limit fields are NOT in TransactionFilterParams
- [x] Works with `Depends()` injection in routes

**Implementation Notes**:
- Keep `TransactionSearchParams` temporarily for backward compatibility during migration
- Mark it as deprecated with a comment

---

#### Component: Audit Logs Route Refactoring

**Files Involved**:
- `src/api/routes/audit_logs.py`
- `src/services/audit_service.py`
- `src/repositories/audit_repository.py`

**Purpose**: Fix broken pagination in admin endpoint and standardize both audit log endpoints

**Implementation Requirements**:

1. **Core Logic - Route Layer**:
   - Replace inline `page`/`page_size` Query params with `PaginationParams = Depends()`
   - Add `AuditLogFilterParams = Depends()` for filter parameters
   - Remove manual offset calculation (use `pagination.offset`)
   - Remove manual total_pages calculation

2. **Core Logic - Service Layer**:
   - Add `count_all_audit_logs()` method to AuditService
   - Update `get_all_audit_logs()` to return tuple `(list[AuditLog], int)` like `get_user_audit_logs()`
   - Or create new `get_all_audit_logs_paginated()` that returns `PaginatedResponse`

3. **Core Logic - Repository Layer**:
   - Add `count_all_logs()` method to AuditLogRepository (mirrors `count_user_logs()`)

4. **Bug Fix**:
   - Current: `total = len(logs)` and `total_pages = 1 if logs else 0` (WRONG)
   - Fix: Use proper count query for total, calculate total_pages correctly

5. **Edge Cases & Error Handling**:
   - [x] Empty results: total=0, total_pages=0
   - [x] Filters applied: count should also apply filters
   - [x] Invalid enum values: return 422 validation error

6. **Testing Requirements**:
   - [x] Integration test: Pagination returns correct total count
   - [x] Integration test: Pagination returns correct total_pages
   - [x] Integration test: Page 2 returns different results than page 1
   - [x] Integration test: Filters affect total count correctly
   - [x] Integration test: Out-of-bounds page returns empty data with correct meta

**Acceptance Criteria**:
- [x] `GET /audit-logs/users` returns correct `total` (not just page count)
- [x] `GET /audit-logs/users` returns correct `total_pages`
- [x] Both endpoints use `PaginationParams = Depends()`
- [x] Both endpoints use `AuditLogFilterParams = Depends()`
- [x] No manual offset/total_pages calculations in routes

---

#### Component: Users Route Refactoring

**Files Involved**:
- `src/api/routes/users.py`

**Purpose**: Simplify route by using `Depends()` for pagination (minor refactor)

**Implementation Requirements**:

1. **Core Logic**:
   - Replace inline `page`/`page_size` Query params with `PaginationParams = Depends()`
   - Remove manual `PaginationParams` construction (line 199)
   - Change `UserFilterParams` to use `Depends()` injection

2. **Data Handling**:
   - No change to API contract (same query params)
   - No change to response format

3. **Testing Requirements**:
   - [x] Integration test: Existing pagination tests still pass
   - [x] Integration test: Verify response structure unchanged

**Acceptance Criteria**:
- [x] Route uses `pagination: PaginationParams = Depends()`
- [x] Route uses `filters: UserFilterParams = Depends()`
- [x] No manual PaginationParams construction
- [x] API contract unchanged (non-breaking)

---

#### Component: Accounts Route Migration

**Files Involved**:
- `src/api/routes/accounts.py`
- `src/services/account_service.py`

**Purpose**: Convert from skip/limit to page/page_size with PaginatedResponse

**Implementation Requirements**:

1. **Core Logic - Route Layer**:
   - Change response_model from `list[AccountListItem]` to `PaginatedResponse[AccountListItem]`
   - Replace `skip`/`limit` Query params with `PaginationParams = Depends()`
   - Add `AccountFilterParams = Depends()` for filter parameters
   - Update return statement to call paginated service method

2. **Core Logic - Service Layer**:
   - Add `list_accounts_paginated()` method that returns `PaginatedResponse[AccountListItem]`
   - Keep existing `list_accounts()` temporarily for backward compatibility
   - Implement count query for total

3. **Data Handling**:
   - Input change: `skip`/`limit` → `page`/`page_size`
   - Output change: `[...]` → `{ data: [...], meta: {...} }`

4. **Edge Cases & Error Handling**:
   - [x] Empty account list: return `{ data: [], meta: { total: 0, ... } }`
   - [x] Filter by non-existent account_type_id: return empty results
   - [x] Page beyond total: return empty data with correct total

5. **Testing Requirements**:
   - [x] Integration test: Default pagination (page=1, page_size=20)
   - [x] Integration test: Custom page size
   - [x] Integration test: Page navigation
   - [x] Integration test: Filters affect results and count
   - [x] Integration test: Response structure matches PaginatedResponse

**Acceptance Criteria**:
- [x] Query params are `page` and `page_size` (not skip/limit)
- [x] Response is `PaginatedResponse[AccountListItem]`
- [x] Default page_size is 20 (was also 20 with limit)
- [x] Total count is accurate

**Breaking Changes**:
- Query params rename: `skip`/`limit` → `page`/`page_size`
- Response structure change: array → object with data/meta

---

#### Component: Cards Route Migration

**Files Involved**:
- `src/api/routes/cards.py`
- `src/services/card_service.py`
- `src/repositories/card_repository.py`

**Purpose**: Convert from skip/limit to page/page_size with PaginatedResponse

**Implementation Requirements**:

1. **Core Logic - Route Layer**:
   - Change response_model from `list[CardListItem]` to `PaginatedResponse[CardListItem]`
   - Replace `skip`/`limit` Query params with `PaginationParams = Depends()`
   - Add `CardFilterParams = Depends()` for filter parameters
   - Update return statement

2. **Core Logic - Service Layer**:
   - Add `list_cards_paginated()` method returning `PaginatedResponse[CardListItem]`
   - Implement count query

3. **Core Logic - Repository Layer**:
   - Add `count_by_user()` method to CardRepository

4. **Data Handling**:
   - Input change: `skip`/`limit` → `page`/`page_size`
   - Output change: `[...]` → `{ data: [...], meta: {...} }`
   - Default page_size change: 100 → 20 (standardization)

5. **Edge Cases & Error Handling**:
   - [x] include_deleted=true: count and list should include deleted
   - [x] Filter by account_id user doesn't own: AuthorizationError
   - [x] Empty card list: return empty PaginatedResponse

6. **Testing Requirements**:
   - [x] Integration test: Default pagination
   - [x] Integration test: Filter by card_type
   - [x] Integration test: Filter by account_id
   - [x] Integration test: include_deleted behavior
   - [x] Integration test: Response structure

**Acceptance Criteria**:
- [x] Query params are `page` and `page_size`
- [x] Response is `PaginatedResponse[CardListItem]`
- [x] Default page_size is 20 (changed from 100)
- [x] Total count is accurate

**Breaking Changes**:
- Query params rename: `skip`/`limit` → `page`/`page_size`
- Default page size change: 100 → 20
- Response structure change: array → object with data/meta

---

#### Component: Transactions Route Migration

**Files Involved**:
- `src/api/routes/transactions.py`
- `src/services/transaction_service.py`
- `src/schemas/transaction.py`

**Purpose**: Convert from skip/limit to page/page_size and replace custom response with PaginatedResponse

**Implementation Requirements**:

1. **Core Logic - Route Layer**:
   - Change response_model from `TransactionListResponse` to `PaginatedResponse[TransactionResponse]`
   - Replace `TransactionSearchParams = Depends()` with separate:
     - `PaginationParams = Depends()`
     - `TransactionFilterParams = Depends()`
   - Update return statement

2. **Core Logic - Service Layer**:
   - Update `search_transactions()` to accept `PaginationParams` instead of skip/limit
   - Or create new `list_transactions_paginated()` method
   - Use `pagination.offset` for offset calculation

3. **Schema Changes**:
   - Create `TransactionFilterParams` (new)
   - Deprecate `TransactionSearchParams` (keep for now, mark deprecated)
   - `TransactionListResponse` can be removed after migration

4. **Data Handling**:
   - Input change: `skip`/`limit` → `page`/`page_size`
   - Output change: `{ items, total, skip, limit }` → `{ data, meta }`

5. **Edge Cases & Error Handling**:
   - [x] Fuzzy search with no matches: return empty results
   - [x] Date range with no transactions: return empty results
   - [x] Sort by invalid field: handled by schema validation

6. **Testing Requirements**:
   - [x] Integration test: Default pagination
   - [x] Integration test: Date range filtering
   - [x] Integration test: Amount range filtering
   - [x] Integration test: Fuzzy search
   - [x] Integration test: Sorting
   - [x] Integration test: Response structure matches PaginatedResponse

**Acceptance Criteria**:
- [x] Query params are `page` and `page_size`
- [x] Response is `PaginatedResponse[TransactionResponse]`
- [x] All existing filters still work
- [x] Sorting still works
- [x] Total count is accurate

**Breaking Changes**:
- Query params rename: `skip`/`limit` → `page`/`page_size`
- Response structure change: `{ items, total, skip, limit }` → `{ data, meta: { total, page, page_size, total_pages } }`

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Foundation & Bug Fix (Size: S, Priority: P0)

**Goal**: Fix critical bug in audit logs and add utility enhancements to pagination infrastructure

**Scope**:
- ✅ Include: PaginationParams enhancement, AuditLogFilterParams, audit repository count method, audit logs route fix
- ❌ Exclude: Other endpoint migrations, filter schemas for other entities

**Components to Implement**:
- [x] Add `offset` property to `PaginationParams`
- [x] Add `calculate_total_pages` static method to `PaginationParams`
- [x] Create `AuditLogFilterParams` schema
- [x] Add `count_all_logs()` to `AuditLogRepository`
- [x] Add `count_all_audit_logs()` to `AuditService`
- [x] Fix `GET /audit-logs/users` endpoint (correct total count)
- [x] Refactor both audit log endpoints to use `Depends()`

**Detailed Tasks**:

1. Enhance `PaginationParams` in `src/schemas/common.py`:
   ```python
   @property
   def offset(self) -> int:
       """Calculate SQL OFFSET from page number."""
       return (self.page - 1) * self.page_size

   @staticmethod
   def calculate_total_pages(total: int, page_size: int) -> int:
       """Calculate total pages from total count."""
       return (total + page_size - 1) // page_size if total > 0 else 0
   ```

2. Create `AuditLogFilterParams` in `src/schemas/audit.py`:
   ```python
   class AuditLogFilterParams(BaseModel):
       action: AuditAction | None = None
       entity_type: str | None = None
       status: AuditStatus | None = None
       start_date: datetime | None = None
       end_date: datetime | None = None
   ```

3. Add `count_all_logs()` to `src/repositories/audit_repository.py` (copy pattern from `count_user_logs`)

4. Add `count_all_audit_logs()` to `src/services/audit_service.py`

5. Refactor `src/api/routes/audit_logs.py`:
   - Import and use `PaginationParams = Depends()`
   - Import and use `AuditLogFilterParams = Depends()`
   - Fix `get_all_audit_logs` to use proper count

**Validation Criteria**:
- [x] All existing tests pass
- [x] `GET /audit-logs/users` returns correct total count
- [x] Both audit endpoints use standardized pagination

---

#### Phase 2: Non-Breaking Refactors (Size: S, Priority: P1)

**Goal**: Refactor endpoints that already use correct query params but with inline definitions

**Scope**:
- ✅ Include: Users route refactor
- ❌ Exclude: Endpoints with breaking changes

**Components to Implement**:
- [x] Refactor `GET /users` to use `PaginationParams = Depends()`
- [x] Refactor `GET /users` to use `UserFilterParams = Depends()`

**Detailed Tasks**:

1. Update `src/api/routes/users.py`:
   - Change signature from inline Query params to `pagination: PaginationParams = Depends()`
   - Change filter params to `filters: UserFilterParams = Depends()`
   - Remove manual `PaginationParams` construction

**Validation Criteria**:
- [x] All existing tests pass
- [x] API contract unchanged (same query params, same response)

---

#### Phase 3: Filter Schema Creation (Size: S, Priority: P2)

**Goal**: Create filter schemas for endpoints with breaking changes (preparation)

**Scope**:
- ✅ Include: AccountFilterParams, CardFilterParams, TransactionFilterParams
- ❌ Exclude: Route modifications

**Components to Implement**:
- [x] Create `AccountFilterParams` schema
- [x] Create `CardFilterParams` schema
- [x] Create `TransactionFilterParams` schema

**Detailed Tasks**:

1. Add to `src/schemas/account.py`:
   ```python
   class AccountFilterParams(BaseModel):
       account_type_id: uuid.UUID | None = Field(default=None, description="Filter by account type ID")
       financial_institution_id: uuid.UUID | None = Field(default=None, description="Filter by financial institution")
   ```

2. Add to `src/schemas/card.py`:
   ```python
   class CardFilterParams(BaseModel):
       card_type: CardType | None = Field(default=None, description="Filter by card type")
       account_id: uuid.UUID | None = Field(default=None, description="Filter by account ID")
       include_deleted: bool = Field(default=False, description="Include soft-deleted cards")
   ```

3. Add to `src/schemas/transaction.py`:
   ```python
   class TransactionFilterParams(BaseModel):
       # All fields from TransactionSearchParams except skip/limit
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

**Validation Criteria**:
- [x] All schemas pass validation tests
- [x] Schemas can be used with Depends()

---

#### Phase 4: Breaking Changes - Accounts (Size: M, Priority: P3)

**Goal**: Migrate accounts endpoint to standardized pagination

**Scope**:
- ✅ Include: Accounts route, service, tests
- ❌ Exclude: Other endpoints

**Components to Implement**:
- [x] Add count method to AccountRepository (if not exists)
- [x] Add `list_accounts_paginated()` to AccountService
- [x] Update accounts route to use PaginatedResponse
- [x] Update tests

**Detailed Tasks**:

1. Add to `src/repositories/account_repository.py` (if needed):
   ```python
   async def count_by_user(
       self,
       user_id: uuid.UUID,
       account_type_id: uuid.UUID | None = None,
       financial_institution_id: uuid.UUID | None = None,
   ) -> int:
       # Implementation
   ```

2. Add to `src/services/account_service.py`:
   ```python
   async def list_accounts_paginated(
       self,
       user_id: uuid.UUID,
       current_user: User,
       pagination: PaginationParams,
       filters: AccountFilterParams,
   ) -> PaginatedResponse[AccountListItem]:
       # Implementation using pagination.offset, count, PaginatedResponse
   ```

3. Update `src/api/routes/accounts.py`:
   - Change response_model to `PaginatedResponse[AccountListItem]`
   - Use `pagination: PaginationParams = Depends()`
   - Use `filters: AccountFilterParams = Depends()`
   - Call `list_accounts_paginated()`

4. Update `tests/integration/test_account_routes.py`:
   - Update all list endpoint tests for new response structure
   - Add pagination-specific tests

**Validation Criteria**:
- [x] All tests pass with new response structure
- [x] Pagination metadata is correct
- [x] Filters still work correctly

---

#### Phase 5: Breaking Changes - Cards (Size: M, Priority: P3)

**Goal**: Migrate cards endpoint to standardized pagination

**Scope**:
- ✅ Include: Cards route, service, repository, tests
- ❌ Exclude: Other endpoints

**Components to Implement**:
- [x] Add count method to CardRepository
- [x] Add `list_cards_paginated()` to CardService
- [x] Update cards route to use PaginatedResponse
- [x] Update tests

**Detailed Tasks**:

1. Add to `src/repositories/card_repository.py`:
   ```python
   async def count_by_user(
       self,
       user_id: uuid.UUID,
       card_type: CardType | None = None,
       account_id: uuid.UUID | None = None,
       include_deleted: bool = False,
   ) -> int:
       # Implementation
   ```

2. Add to `src/services/card_service.py`:
   ```python
   async def list_cards_paginated(
       self,
       current_user: User,
       pagination: PaginationParams,
       filters: CardFilterParams,
   ) -> PaginatedResponse[CardListItem]:
       # Implementation
   ```

3. Update `src/api/routes/cards.py`:
   - Change response_model to `PaginatedResponse[CardListItem]`
   - Use `pagination: PaginationParams = Depends()`
   - Use `filters: CardFilterParams = Depends()`

4. Update `tests/integration/test_card_routes.py`

**Validation Criteria**:
- [x] All tests pass
- [x] Default page_size is 20 (changed from 100)
- [x] Pagination metadata is correct

---

#### Phase 6: Breaking Changes - Transactions (Size: M, Priority: P3)

**Goal**: Migrate transactions endpoint to standardized pagination

**Scope**:
- ✅ Include: Transactions route, service, schema, tests
- ❌ Exclude: Other endpoints

**Components to Implement**:
- [x] Update transaction service to accept PaginationParams
- [x] Update transactions route
- [x] Update tests
- [x] Deprecate TransactionSearchParams (add comment)

**Detailed Tasks**:

1. Update `src/services/transaction_service.py`:
   - Modify `search_transactions()` to accept `PaginationParams` and `TransactionFilterParams`
   - Or create `list_transactions_paginated()` method

2. Update `src/api/routes/transactions.py`:
   - Change response_model to `PaginatedResponse[TransactionResponse]`
   - Use separate `PaginationParams` and `TransactionFilterParams`

3. Update `src/schemas/transaction.py`:
   - Add deprecation comment to `TransactionSearchParams`
   - Add deprecation comment to `TransactionListResponse`

4. Update `tests/integration/test_transaction_api.py`

**Validation Criteria**:
- [x] All tests pass
- [x] All filters still work
- [x] Sorting still works
- [x] Pagination metadata is correct

---

### 4.2 Implementation Sequence

```
Phase 1 (P0) - Foundation & Bug Fix
    ↓
Phase 2 (P1) - Non-Breaking Refactors
    ↓
Phase 3 (P2) - Filter Schema Creation
    ↓
Phase 4 (P3) ─┬─ Breaking Changes - Accounts
              │
Phase 5 (P3) ─┤  (Can run in parallel)
              │
Phase 6 (P3) ─┘─ Breaking Changes - Transactions
```

**Rationale for ordering**:
- Phase 1 first because: Fixes critical bug and establishes foundation utilities
- Phase 2 after Phase 1 because: Uses new PaginationParams features, validates approach
- Phase 3 before 4-6 because: Creates schemas needed for breaking changes
- Phases 4-6 can be parallel because: Independent endpoints, no cross-dependencies

---

## 5. Simplicity & Design Validation

**Simplicity Checklist**:
- [x] Is this the SIMPLEST solution? Yes - reuses existing patterns from reference implementation
- [x] Avoided premature optimization? Yes - no new libraries or complex abstractions
- [x] Aligns with existing patterns? Yes - follows financial_institutions reference exactly
- [x] Can deliver value incrementally? Yes - Phase 1 fixes bug immediately, other phases follow
- [x] Solving actual problem? Yes - standardization was explicitly requested

**Alternatives Considered**:

1. **API Versioning (v2)**: Create new versioned endpoints with new pagination
   - **Why not chosen**: Overhead of maintaining two versions, project is pre-production
   - **When to reconsider**: If external consumers depend on current API

2. **Backward Compatibility Shim**: Accept both skip/limit and page/page_size
   - **Why not chosen**: Adds complexity, delays full migration, confusing API
   - **When to reconsider**: If migration needs to be gradual for external consumers

3. **Keep Current Patterns**: Leave skip/limit endpoints as-is
   - **Why not chosen**: Inconsistency creates confusion, bug in audit logs needs fixing anyway

**Rationale**: The proposed approach is preferred because:
- Reuses proven patterns from existing codebase
- Minimizes new code (just consolidation)
- Single consistent API surface
- Direct path to fix critical bug

---

## 6. References & Related Documents

### Internal Documentation
- Feature description: `.features/descriptions/refactor/pagination.md`
- Backend standards: `.claude/standards/backend.md`
- API standards: `.claude/standards/api.md`

### Reference Implementation
- `src/api/routes/financial_institutions.py:86-121` - Reference route pattern
- `src/services/financial_institution_service.py:254-321` - Reference service pattern
- `src/schemas/common.py:19-77` - PaginationParams, PaginationMeta, PaginatedResponse

### Related Files
- `src/schemas/financial_institution.py:358-395` - FinancialInstitutionFilterParams (reference for filter schemas)

### External Resources
- FastAPI Dependency Injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- Pydantic Computed Fields: https://docs.pydantic.dev/latest/concepts/fields/#computed-fields
