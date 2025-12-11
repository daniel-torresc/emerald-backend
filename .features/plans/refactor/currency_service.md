# CurrencyService Refactoring - Implementation Plan

## 1. Executive Summary

This plan outlines the refactoring of the `CurrencyService` to align with the codebase's established architectural patterns while **fixing a critical data integrity gap**: AccountService currently accepts any 3-letter uppercase string as a currency code (e.g., "ZZZ", "ABC") instead of validating against supported ISO 4217 currencies.

The refactoring transforms the singleton-based `CurrencyService` into a properly injectable service that follows FastAPI's dependency injection patterns. This enables other services (AccountService, TransactionService) to validate currency codes against the supported list, closing the data integrity gap while maintaining architectural consistency.

**Primary Goals:**
1. Fix data integrity gap by enabling currency validation in AccountService
2. Separate Currency schema from service logic (proper schema/service separation)
3. Replace singleton pattern with FastAPI dependency injection
4. Maintain 100% backward compatibility with existing API responses
5. Maintain or exceed current test coverage (24 test cases)

**Expected Outcomes:**
- AccountService validates currencies against supported list (not just format)
- Currency creation blocked for unsupported codes (data quality)
- All routes use consistent `Depends(get_currency_service)` pattern
- Clear separation: `schemas/currency.py` for models, `services/currency_service.py` for logic

## 2. Technical Architecture

### 2.1 System Design Overview

**Current State:**
```
┌─────────────────────────────────────────────────────┐
│  metadata.py route                                  │
│  └── get_currency_service() [direct factory call]  │
│      └── CurrencyService singleton                  │
│          └── Currency model (in same file)         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  AccountService.create_account()                    │
│  └── Format validation ONLY (3 uppercase letters)  │
│      ❌ No validation against supported currencies │
└─────────────────────────────────────────────────────┘
```

**Target State:**
```
┌─────────────────────────────────────────────────────┐
│  schemas/currency.py                                │
│  └── Currency (Pydantic model)                     │
│  └── CurrencyResponse, CurrenciesResponse          │
└─────────────────────────────────────────────────────┘
                        │
                        ▼ imported by
┌─────────────────────────────────────────────────────┐
│  services/currency_service.py                       │
│  └── CurrencyService (injectable, non-singleton)   │
│      └── _currencies: list[Currency]               │
│      └── get_all(), get_by_code(), is_supported()  │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ metadata.py  │ │AccountService│ │dependencies  │
│ route via    │ │creates own   │ │.py factory   │
│ Depends()    │ │instance      │ │function      │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 Technology Decisions

**No Repository Layer**
- **Purpose**: N/A - deliberately omitted
- **Why this choice**: Currency data is static, hardcoded, and has no database persistence. A repository layer would be an abstraction over nothing (anti-pattern per research findings)
- **Alternatives considered**: Full 3-layer architecture with CurrencyRepository - rejected because it violates the principle that repositories abstract data access, not hardcoded lists

**Non-Singleton Service Pattern**
- **Purpose**: Enable proper dependency injection and testing
- **Why this choice**: Aligns with other services (AccountService, UserService), enables mocking in tests, follows FastAPI best practices
- **Alternatives considered**: Keep singleton but wrap with Depends() - rejected because singleton state persists across tests causing flaky behavior

**Optional Session Parameter**
- **Purpose**: Future-proof for potential database integration while maintaining current simplicity
- **Why this choice**: Consistent with service constructor signatures, enables CurrencyService to be used inside other services that already have sessions
- **Alternatives considered**: No session parameter - rejected because it breaks the pattern when AccountService needs to instantiate CurrencyService

### 2.3 File Structure

```
src/
├── schemas/
│   ├── __init__.py          # ADD: Currency, CurrencyResponse exports
│   ├── currency.py          # NEW: Currency Pydantic schemas
│   └── metadata.py          # UPDATE: Import Currency from schemas/currency.py
├── services/
│   ├── __init__.py          # UPDATE: Export CurrencyService
│   └── currency_service.py  # UPDATE: Remove singleton, remove Currency model
├── api/
│   ├── dependencies.py      # UPDATE: Add get_currency_service dependency
│   └── routes/
│       └── metadata.py      # UPDATE: Use Depends(get_currency_service)
tests/
├── unit/
│   └── test_currency_service.py  # UPDATE: Test non-singleton behavior
└── integration/
    └── test_account_routes.py    # UPDATE: Add currency validation tests
```

## 3. Implementation Specification

### 3.1 Component Breakdown

---

#### Component: Currency Schema

**Files Involved:**
- `src/schemas/currency.py` (NEW)
- `src/schemas/__init__.py` (UPDATE)
- `src/schemas/metadata.py` (UPDATE)

**Purpose:** Provide Pydantic models for currency data validation and serialization, separated from service logic.

**Implementation Requirements:**

1. **Core Logic:**
   - Create `Currency` Pydantic model with frozen config (immutable)
   - Fields: `code` (3 chars), `symbol` (min 1 char), `name` (min 1 char)
   - Keep existing `Currency.create()` factory method for code uppercase conversion
   - Create `CurrencyResponse` for single currency responses (future API endpoints)

2. **Data Handling:**
   - Model must be JSON serializable for API responses
   - `model_config = {"frozen": True}` for thread safety
   - Field descriptions for OpenAPI documentation

3. **Edge Cases & Error Handling:**
   - [x] Handle code validation (exactly 3 characters)
   - [x] Handle empty symbol/name rejection
   - [x] Pydantic validates automatically via Field constraints

4. **Dependencies:**
   - Internal: None (schema is standalone)
   - External: Pydantic v2

5. **Testing Requirements:**
   - [x] Unit test: Currency model creation with valid data succeeds
   - [x] Unit test: Currency model with invalid code length raises ValidationError
   - [x] Unit test: Currency model is frozen (immutable)
   - [x] Unit test: Currency.create() uppercases code

**Acceptance Criteria:**
- [x] Currency model has same behavior as current implementation
- [x] All existing tests pass without modification (import paths updated)
- [x] Model is importable from `src.schemas.currency`

**Implementation Notes:**
- Copy model from `currency_service.py`, do not modify behavior
- Update `metadata.py` import to use new location

---

#### Component: CurrencyService Refactoring

**Files Involved:**
- `src/services/currency_service.py` (UPDATE)
- `src/services/__init__.py` (UPDATE)

**Purpose:** Transform singleton service into injectable service that can be used across the application.

**Implementation Requirements:**

1. **Core Logic:**
   - Remove `__new__` singleton implementation
   - Add `__init__(self, session: AsyncSession | None = None)` constructor
   - Move `_initialize_currencies()` call to `__init__`
   - Keep all existing methods: `get_all()`, `get_by_code()`, `is_supported()`
   - Remove `get_currency_service()` factory function (moves to dependencies.py)

2. **Data Handling:**
   - `_currencies` becomes instance variable (not class variable)
   - `get_all()` still returns copy to prevent external modification
   - Session parameter stored but not used (for future extensibility)

3. **Edge Cases & Error Handling:**
   - [x] Handle None session gracefully (optional parameter)
   - [x] get_by_code() handles case-insensitive lookup
   - [x] is_supported() returns False for None/empty input

4. **Dependencies:**
   - Internal: `src.schemas.currency.Currency`
   - External: `sqlalchemy.ext.asyncio.AsyncSession` (type only)

5. **Testing Requirements:**
   - [x] Unit test: Service instantiation without session works
   - [x] Unit test: Service instantiation with session works
   - [x] Unit test: Multiple instances are NOT the same object (not singleton)
   - [x] Unit test: Each instance has its own currency list
   - [x] Unit test: get_all() returns list of 6 currencies
   - [x] Unit test: get_by_code() case-insensitive lookup works
   - [x] Unit test: is_supported() returns True for valid, False for invalid

**Acceptance Criteria:**
- [x] Service no longer uses singleton pattern
- [x] Service accepts optional AsyncSession parameter
- [x] All existing service methods work identically
- [x] Service exportable from `src.services`

**Implementation Notes:**
- Signature change: `CurrencyService()` → `CurrencyService(session=None)`
- This is a **breaking change** for direct instantiation - tests must be updated

---

#### Component: Dependency Injection Integration

**Files Involved:**
- `src/api/dependencies.py` (UPDATE)

**Purpose:** Provide FastAPI dependency for CurrencyService that follows established patterns.

**Implementation Requirements:**

1. **Core Logic:**
   - Add `get_currency_service()` function with `Depends(get_db)` pattern
   - Function returns `CurrencyService(session)` instance
   - Add import for `CurrencyService` at top of file

2. **Data Handling:**
   - Session passed to CurrencyService for pattern consistency
   - New instance created per request (not singleton)

3. **Edge Cases & Error Handling:**
   - [x] Database connection errors handled by get_db dependency

4. **Dependencies:**
   - Internal: `src.services.currency_service.CurrencyService`
   - External: FastAPI Depends

5. **Testing Requirements:**
   - [x] Integration test: Dependency returns CurrencyService instance
   - [x] Integration test: Route using dependency returns correct data

**Acceptance Criteria:**
- [x] `get_currency_service` follows same pattern as `get_account_service`
- [x] Function has proper docstring matching existing style
- [x] Import added to service imports section

**Implementation Notes:**
- Add to "Service Dependencies" section (after line 393)
- Follow exact docstring format of other `get_*_service` functions

---

#### Component: Route Migration

**Files Involved:**
- `src/api/routes/metadata.py` (UPDATE)

**Purpose:** Update currency endpoint to use proper dependency injection.

**Implementation Requirements:**

1. **Core Logic:**
   - Replace `get_currency_service()` direct call with `Depends(get_currency_service)`
   - Update import: remove `get_currency_service` from service import, add from dependencies
   - Add `currency_service` parameter to route function signature

2. **Data Handling:**
   - Response format unchanged
   - Currency list returned as-is

3. **Edge Cases & Error Handling:**
   - [x] No error handling needed (service doesn't throw)

4. **Dependencies:**
   - Internal: `src.api.dependencies.get_currency_service`
   - External: FastAPI Depends

5. **Testing Requirements:**
   - [x] Integration test: `/api/v1/metadata/currencies` returns same response
   - [x] Integration test: Response contains 6 currencies
   - [x] Integration test: Each currency has code, symbol, name

**Acceptance Criteria:**
- [x] Route uses `Depends(get_currency_service)` pattern
- [x] API response is byte-for-byte identical
- [x] OpenAPI docs unchanged

**Implementation Notes:**
- Simple refactor: add parameter, update import, remove direct call

---

#### Component: AccountService Currency Validation Integration

**Files Involved:**
- `src/services/account_service.py` (UPDATE)

**Purpose:** Fix data integrity gap by validating currencies against supported list.

**Implementation Requirements:**

1. **Core Logic:**
   - Add `self.currency_service = CurrencyService(session)` in `__init__`
   - Replace format-only validation (lines 163-170) with `is_supported()` check
   - Error message includes list of supported currencies

2. **Data Handling:**
   - Currency validation happens before database operations
   - Invalid currency raises ValidationError (not ValueError)

3. **Edge Cases & Error Handling:**
   - [x] Handle: Valid ISO 4217 code not in supported list (EUR valid code but might not be supported)
   - [x] Handle: Invalid format still caught (is_supported handles this)
   - [x] Handle: Empty/None currency (schema validation catches this first)

4. **Dependencies:**
   - Internal: `src.services.currency_service.CurrencyService`
   - External: None new

5. **Testing Requirements:**
   - [x] Unit test: create_account with supported currency (USD) succeeds
   - [x] Unit test: create_account with unsupported currency (ZZZ) raises ValidationError
   - [x] Unit test: Error message lists supported currencies
   - [x] Integration test: POST /accounts with invalid currency returns 422

**Acceptance Criteria:**
- [x] AccountService validates against CurrencyService.is_supported()
- [x] ValidationError raised for unsupported currencies
- [x] Error message is user-friendly with supported currency list
- [x] Existing accounts with supported currencies continue to work

**Implementation Notes:**
- Change `ValueError` to `ValidationError` for consistency
- This fixes the security/data integrity issue identified in research

---

### 3.2 Detailed File Specifications

#### `src/schemas/currency.py` (NEW)

**Purpose:** Pydantic schemas for currency data

**Implementation:**
```python
"""
Currency schemas for ISO 4217 currency data.

This module provides Pydantic schemas for:
- Currency model (code, symbol, name)
- Response schemas for currency endpoints
"""

from pydantic import BaseModel, Field


class Currency(BaseModel):
    """
    ISO 4217 currency representation.

    Immutable Pydantic model for currency data with validation.
    """

    code: str = Field(min_length=3, max_length=3, description="ISO 4217 currency code")
    symbol: str = Field(min_length=1, description="Currency symbol")
    name: str = Field(min_length=1, description="Full currency name")

    model_config = {"frozen": True}

    @classmethod
    def create(cls, code: str, symbol: str, name: str) -> "Currency":
        """
        Factory method for creating currency instances.

        Args:
            code: ISO 4217 code (converted to uppercase)
            symbol: Currency symbol
            name: Full currency name

        Returns:
            Currency instance
        """
        return cls(code=code.upper(), symbol=symbol, name=name)


class CurrencyResponse(BaseModel):
    """Response schema for single currency."""

    currency: Currency = Field(description="Currency data")


class CurrenciesResponse(BaseModel):
    """Response schema for currency list."""

    currencies: list[Currency] = Field(description="List of supported currencies")
```

**Tests:**
- [x] Test: Currency model creation succeeds
- [x] Test: Currency with invalid code raises error
- [x] Test: Currency.create() uppercases code

---

#### `src/services/currency_service.py` (UPDATED)

**Purpose:** Currency service without singleton pattern

**Implementation:**
```python
"""
Currency service for ISO 4217 currency data.

This module provides CurrencyService for managing currency list operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.currency import Currency


class CurrencyService:
    """
    Currency service providing ISO 4217 currency data.

    Injectable service that provides currency lookup and validation.
    Thread-safe due to immutable Currency models.
    """

    def __init__(self, session: AsyncSession | None = None):
        """
        Initialize CurrencyService.

        Args:
            session: Optional database session (for future use or
                     pattern consistency when used inside other services)
        """
        self.session = session
        self._currencies = self._initialize_currencies()

    def _initialize_currencies(self) -> list[Currency]:
        """Initialize currency list."""
        return [
            # North America
            Currency.create("USD", "$", "US Dollar"),
            # Europe
            Currency.create("EUR", "€", "Euro"),
            Currency.create("GBP", "£", "Pound Sterling"),
            Currency.create("CHF", "CHF", "Swiss Franc"),
            # Asia-Pacific
            Currency.create("JPY", "¥", "Japanese Yen"),
            Currency.create("CNY", "¥", "Chinese Yuan"),
        ]

    def get_all(self) -> list[Currency]:
        """
        Get all supported currencies.

        Returns:
            Copy of currency list to prevent external modification
        """
        return self._currencies.copy()

    def get_by_code(self, code: str) -> Currency | None:
        """
        Get currency by ISO 4217 code (case-insensitive).

        Args:
            code: ISO 4217 currency code

        Returns:
            Currency if found, None otherwise
        """
        code_upper = code.upper()
        return next((c for c in self._currencies if c.code == code_upper), None)

    def is_supported(self, code: str) -> bool:
        """
        Check if currency code is supported.

        Args:
            code: ISO 4217 currency code

        Returns:
            True if currency is supported, False otherwise
        """
        return self.get_by_code(code) is not None

    def get_supported_codes(self) -> list[str]:
        """
        Get list of supported currency codes.

        Returns:
            List of ISO 4217 currency codes
        """
        return [c.code for c in self._currencies]
```

**Tests:**
- [x] Test: Service without session works
- [x] Test: Service with session works
- [x] Test: Multiple instances are different objects
- [x] Test: get_all() returns 6 currencies
- [x] Test: get_supported_codes() returns code list

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Schema Separation (Size: S, Priority: P0)

**Goal:** Extract Currency schema to its own file without changing any behavior.

**Scope:**
- ✅ Include: Create `schemas/currency.py`, move Currency model
- ✅ Include: Update imports in `currency_service.py` and `metadata.py`
- ❌ Exclude: Any behavior changes to CurrencyService

**Components to Implement:**
- [x] `src/schemas/currency.py` - New file with Currency model
- [x] `src/schemas/__init__.py` - Add Currency exports
- [x] `src/schemas/metadata.py` - Update import path

**Detailed Tasks:**
1. [x] Create `src/schemas/currency.py`
   - Copy Currency class from `currency_service.py`
   - Add CurrencyResponse, CurrenciesResponse schemas
   - Add module docstring

2. [x] Update `src/schemas/__init__.py`
   - Add imports for Currency, CurrencyResponse, CurrenciesResponse
   - Add to `__all__` list

3. [x] Update `src/schemas/metadata.py`
   - Change import from `src.services.currency_service` to `src.schemas.currency`
   - Remove CurrenciesResponse if duplicated (use one from currency.py)

4. [x] Update `src/services/currency_service.py`
   - Remove Currency class definition
   - Add import from `src.schemas.currency`

5. [x] Run tests
   - All existing tests should pass
   - No new tests needed for this phase

**Dependencies:**
- Requires: None
- Blocks: Phase 2 (service refactoring)

**Validation Criteria:**
- [x] All tests pass (`uv run pytest tests/unit/test_currency_service.py`)
- [x] API response unchanged (`curl localhost:8000/api/v1/metadata/currencies`)
- [x] Type checking passes (`uv run mypy src/`)
- [x] Linting passes (`uv run ruff check src/`)

**Risk Factors:**
- Low risk: This is pure refactoring with no behavior change
- Mitigation: Run full test suite after each step

**Estimated Effort:** 30 minutes

---

#### Phase 2: Service Refactoring (Size: M, Priority: P0)

**Goal:** Convert CurrencyService from singleton to injectable service.

**Scope:**
- ✅ Include: Remove singleton pattern, add session parameter
- ✅ Include: Update test cases for new instantiation pattern
- ❌ Exclude: Integration with AccountService (Phase 3)

**Components to Implement:**
- [x] `src/services/currency_service.py` - Remove singleton, add constructor
- [x] `src/services/__init__.py` - Add CurrencyService export
- [x] `tests/unit/test_currency_service.py` - Update tests

**Detailed Tasks:**
1. [x] Update `src/services/currency_service.py`
   - Remove `_instance` class variable
   - Remove `__new__` method
   - Add `__init__(self, session: AsyncSession | None = None)`
   - Change `_currencies` to instance variable
   - Remove `get_currency_service()` function
   - Add `get_supported_codes()` helper method

2. [x] Update `src/services/__init__.py`
   - Add `CurrencyService` to imports
   - Add to `__all__` list

3. [x] Update `tests/unit/test_currency_service.py`
   - Remove singleton pattern tests
   - Add tests for non-singleton behavior
   - Update all test instantiations
   - Add test for session parameter

**Dependencies:**
- Requires: Phase 1 complete
- Blocks: Phase 3 (dependency injection)

**Validation Criteria:**
- [x] All updated tests pass
- [x] Type checking passes
- [x] Service can be imported from `src.services`

**Risk Factors:**
- Medium risk: Changes service instantiation pattern
- Mitigation: Comprehensive test coverage, run all tests

**Estimated Effort:** 1 hour

---

#### Phase 3: Dependency Injection Integration (Size: S, Priority: P0)

**Goal:** Add CurrencyService to FastAPI dependency system.

**Scope:**
- ✅ Include: Add get_currency_service to dependencies.py
- ✅ Include: Update metadata route to use Depends()
- ❌ Exclude: AccountService integration

**Components to Implement:**
- [x] `src/api/dependencies.py` - Add get_currency_service
- [x] `src/api/routes/metadata.py` - Update route

**Detailed Tasks:**
1. [x] Update `src/api/dependencies.py`
   - Add import for CurrencyService
   - Add `get_currency_service()` dependency function
   - Follow existing docstring pattern

2. [x] Update `src/api/routes/metadata.py`
   - Add import for `get_currency_service` from dependencies
   - Remove import of `get_currency_service` from services
   - Update `get_currencies()` route signature
   - Add `currency_service: CurrencyService = Depends(get_currency_service)`

3. [x] Run integration tests
   - Verify API response unchanged
   - Verify OpenAPI docs correct

**Dependencies:**
- Requires: Phase 2 complete
- Blocks: Phase 4 (currency validation)

**Validation Criteria:**
- [x] Route works with new dependency
- [x] API response byte-for-byte identical
- [x] Integration tests pass

**Risk Factors:**
- Low risk: Standard FastAPI pattern change
- Mitigation: Run integration tests

**Estimated Effort:** 30 minutes

---

#### Phase 4: Currency Validation Integration (Size: M, Priority: P1)

**Goal:** Fix data integrity gap by adding currency validation to AccountService.

**Scope:**
- ✅ Include: Add CurrencyService to AccountService
- ✅ Include: Replace format validation with is_supported() check
- ✅ Include: Add integration tests for validation
- ❌ Exclude: TransactionService changes (already validates against account)

**Components to Implement:**
- [x] `src/services/account_service.py` - Add currency validation
- [x] `tests/integration/test_account_routes.py` - Add validation tests

**Detailed Tasks:**
1. [x] Update `src/services/account_service.py`
   - Add import for CurrencyService
   - Add `self.currency_service = CurrencyService(session)` in `__init__`
   - Replace format validation (lines 163-170) with:
     ```python
     if not self.currency_service.is_supported(currency):
         supported = ", ".join(self.currency_service.get_supported_codes())
         raise ValidationError(
             f"Unsupported currency code '{currency}'. "
             f"Supported currencies: {supported}"
         )
     ```

2. [x] Add integration tests
   - Test: Create account with valid currency (USD) succeeds
   - Test: Create account with invalid currency (ZZZ) returns 422
   - Test: Error message includes supported currencies

**Dependencies:**
- Requires: Phase 3 complete
- Blocks: None

**Validation Criteria:**
- [x] Account creation with valid currency works
- [x] Account creation with invalid currency fails with 422
- [x] Error message is helpful
- [x] All existing tests still pass

**Risk Factors:**
- Medium risk: Changes validation behavior (intentionally)
- Mitigation: Ensure all tests updated, clear error messages

**Estimated Effort:** 1 hour

---

#### Phase 5: Test Suite Updates (Size: S, Priority: P1)

**Goal:** Ensure comprehensive test coverage for all changes.

**Scope:**
- ✅ Include: Update existing tests
- ✅ Include: Add new tests for validation
- ✅ Include: Verify 100% coverage maintained

**Components to Implement:**
- [x] `tests/unit/test_currency_service.py` - Full update
- [x] `tests/integration/test_metadata_routes.py` - Verify unchanged

**Detailed Tasks:**
1. [x] Update unit tests
   - Remove singleton tests
   - Add session parameter tests
   - Add get_supported_codes() test

2. [x] Verify integration tests
   - `/api/v1/metadata/currencies` returns correct data
   - Response format unchanged

3. [x] Run coverage report
   - `uv run pytest tests/ --cov=src --cov-report=term-missing`
   - Verify currency_service.py at 100%
   - Verify currency.py (schema) at 100%

**Dependencies:**
- Requires: Phase 4 complete
- Blocks: None

**Validation Criteria:**
- [x] All tests pass
- [x] Coverage >= 80% overall
- [x] Currency modules at 100%

**Risk Factors:**
- Low risk: Test-only changes
- Mitigation: None needed

**Estimated Effort:** 30 minutes

---

### 4.2 Implementation Sequence

```
Phase 1: Schema Separation (P0, 30 min)
  ↓
Phase 2: Service Refactoring (P0, 1 hour)
  ↓
Phase 3: Dependency Injection (P0, 30 min)
  ↓
Phase 4: Currency Validation (P1, 1 hour)
  ↓
Phase 5: Test Suite Updates (P1, 30 min)
```

**Total Estimated Effort:** ~3.5 hours

**Rationale for ordering:**
- Phase 1 first: Schema separation is zero-risk, establishes foundation
- Phase 2 depends on Phase 1: Service needs schemas in separate file
- Phase 3 depends on Phase 2: Can't add dependency until service refactored
- Phase 4 depends on Phase 3: AccountService needs injectable CurrencyService
- Phase 5 last: Final verification after all changes complete

**Quick Wins:**
- Phase 1 can be committed independently as "chore: separate currency schema"
- Each phase is independently committable and deployable

---

## 5. Simplicity & Design Validation

**Simplicity Checklist:**
- [x] Is this the SIMPLEST solution that solves the problem?
  - Yes: No repository layer (would be over-engineering)
  - Yes: Session parameter is optional (not forced)
- [x] Have we avoided premature optimization?
  - Yes: In-memory currency list is optimal, no caching needed
- [x] Does this align with existing patterns in the codebase?
  - Yes: Service follows AccountService pattern
  - Yes: Dependency injection follows existing services
- [x] Can we deliver value in smaller increments?
  - Yes: Each phase is independently valuable and deployable
- [x] Are we solving the actual problem vs. a perceived problem?
  - Yes: Fixes real data integrity gap (primary problem)
  - Yes: Achieves architectural consistency (secondary problem)

**Alternatives Considered:**

1. **Full Repository Layer (Option 1 from research)**
   - Rejected: Would create abstraction over nothing
   - Repository pattern is for database abstraction, not hardcoded lists

2. **Keep Singleton with Depends() Wrapper (Option 3 from research)**
   - Rejected: Singleton causes test flakiness
   - Doesn't fully enable cross-service usage

3. **Database Table for Currencies (research consideration)**
   - Rejected: Over-engineering for 6 static currencies
   - In-memory is faster (0 queries vs 1 query)
   - Currency list changes rarely (yearly at most)

4. **Eliminate Service Layer (Option 4 from research)**
   - Rejected: Loses encapsulation of currency operations
   - Makes cross-service validation harder

**Rationale:** The chosen approach (Option 2: Service with DI, no repository) provides:
- Architectural consistency without over-engineering
- Proper testability via dependency injection
- Cross-service currency validation capability
- Zero performance overhead (in-memory)

---

## 6. References & Related Documents

### Internal Documentation
- `.claude/standards/backend.md` - Service layer patterns
- `.claude/standards/api.md` - API endpoint standards
- `.claude/standards/testing.md` - Testing requirements
- `CLAUDE.md` - Project overview and commands

### Research Document
- `.features/research/refactor/currency_service.md` - Full research findings

### External Resources
- [Cosmic Python: Repository Pattern](https://www.cosmicpython.com/book/chapter_02_repository.html) - When to skip repositories
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/) - Official docs
- [Pydantic Frozen Models](https://docs.pydantic.dev/latest/concepts/models/#frozen) - Immutability

### Related Codebase Files
- `src/services/account_service.py` - Service pattern reference
- `src/api/dependencies.py` - Dependency injection patterns
- `src/schemas/account.py` - Schema pattern reference

---

**Document Version:** 1.0
**Created:** December 11, 2025
**Status:** Ready for Implementation
