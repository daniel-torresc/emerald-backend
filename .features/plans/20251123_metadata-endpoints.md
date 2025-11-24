from src.models import AccountType

# Implementation Plan: Metadata Endpoints

## Executive Summary

This plan outlines the implementation of three metadata endpoints that provide authoritative business data to the frontend application. These endpoints will serve as the single source of truth for dropdown options, enum values, and business configurations, eliminating hardcoded values in the frontend and ensuring synchronization between frontend and backend.

### Primary Objectives

1. **Implement `/api/metadata/account-types` endpoint** - Returns available account types with display-friendly labels
2. **Implement `/api/metadata/currencies` endpoint** - Returns supported currencies with symbols and names
3. **Implement `/api/metadata/transaction-types` endpoint** - Returns transaction types with labels
4. **Update database enums** - Align existing enums with new requirements (rename values, add/remove types)

### Expected Outcomes

- Frontend can dynamically fetch dropdown options without hardcoding
- Backend remains the single source of truth for business data
- Easy addition of new types/currencies without frontend changes
- Consistent naming across frontend and backend
- Improved maintainability and reduced coupling

### Success Criteria

- All three metadata endpoints return correct, well-structured data
- Database enums updated to match new requirements
- Enum migrations properly handle backward compatibility
- Test coverage ≥80% for all new code
- No breaking changes to existing endpoints
- Frontend can consume endpoints without modifications

---

## Technical Architecture

### 2.1 System Design Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Application                    │
│  (Fetches metadata on app load, populates dropdowns)        │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP GET requests
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              API Layer: /api/metadata/*                     │
│  Routes:                                                    │
│  - GET /api/metadata/account-types                          │
│  - GET /api/metadata/currencies                             │
│  - GET /api/metadata/transaction-types                      │
└──────────────────┬──────────────────────────────────────────┘
                   │ No service layer needed (read-only, static)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Python Enums (In-Memory)                       │
│  - AccountType enum (src/models/enums.py)                   │
│  - TransactionType enum (src/models/enums.py)               │
│  - Currency data (static list in src/core/constants.py)     │
└──────────────────┬──────────────────────────────────────────┘
                   │ Synchronized via migrations
                   ▼
┌─────────────────────────────────────────────────────────────┐
│         PostgreSQL Database (Enum Types)                    │
│  - accounttype enum (checking, savings, investment, other)  │
│  - transactiontype enum (income, expense, transfer)         │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**

1. **No database queries needed** - Metadata is static and served directly from Python enums
2. **No service layer** - Routes directly return enum data (simple read-only operations)
3. **No authentication required** - Metadata is public information needed before login
4. **Caching headers** - Endpoints return cache headers for client-side caching (1 day)
5. **Database enums synchronized** - Alembic migrations keep database enums in sync with Python enums

### 2.2 Technology Decisions

#### Python Enums (str, enum.Enum)

- **Purpose**: Define business enums (AccountType, TransactionType) with type safety
- **Why this choice**:
  - Already established pattern in codebase (`src/models/enums.py`)
  - String-based enums serialize naturally to JSON
  - Type-safe throughout codebase (mypy validation)
  - Easy to extend with helper methods (e.g., `.to_dict()`, `.label()`)
- **Version**: Python 3.13 standard library `enum` module
- **Alternatives considered**:
  - Database tables for enums - Rejected (overkill, adds unnecessary queries)
  - Hardcoded dictionaries - Rejected (no type safety, harder to maintain)

#### Currency Service Class (Singleton Pattern)

- **Purpose**: Provide comprehensive list of supported currencies through a service class
- **Why this choice**:
  - Encapsulates currency data and logic in a class (better OOP design)
  - Singleton pattern ensures single instance (memory efficient)
  - Easy to test and mock
  - Currency list initialized once on first access (lazy loading)
  - No global variables polluting module namespace
- **Version**: ISO 4217:2015 standard (178 active currencies)
- **Alternatives considered**:
  - Global variable list - Rejected (poor encapsulation, namespace pollution)
  - External API (e.g., fixer.io) - Rejected (adds external dependency, latency)
  - Database table - Rejected (unnecessary complexity for static data)

#### FastAPI Direct Response (No Service Layer)

- **Purpose**: Return enum metadata directly from route handlers
- **Why this choice**:
  - Metadata endpoints are simple read-only operations
  - No business logic required
  - Follows YAGNI (You Aren't Gonna Need It) principle
  - Reduces unnecessary abstraction layers
- **Alternatives considered**:
  - MetadataService class - Rejected (adds unnecessary complexity)
  - Repository pattern - Rejected (no database queries needed)

#### Alembic Migrations for Enum Updates

- **Purpose**: Update PostgreSQL enum types to match new requirements
- **Why this choice**:
  - Ensures database constraints match Python enums
  - Provides rollback capability
  - Documents schema evolution
  - Alembic already used for all schema changes
- **Version**: Alembic 1.13+ with PostgreSQL enum handling
- **Alternatives considered**:
  - Manual SQL scripts - Rejected (bypasses migration history)
  - Rebuild enums on startup - Rejected (dangerous, no rollback)

### 2.3 File Structure

```
src/
├── api/
│   └── routes/
│       └── metadata.py                 # NEW: Metadata endpoints
│
├── models/
│   └── enums.py                        # MODIFIED: Update AccountType, TransactionType
│
├── schemas/
│   └── metadata.py                     # NEW: Response schemas for metadata endpoints
│
├── services/
│   └── currency.py                     # NEW: Currency service class and models
│
└── main.py                             # MODIFIED: Register metadata router

alembic/versions/
└── 9cfdc3051d85_create_enums_and_extensions.py  # MODIFIED: Change enums and update database by rerunning alembic versions

tests/
├── unit/
│   ├── test_enums.py                   # NEW: Unit tests for enum methods
│   └── test_currency.py                # NEW: Unit tests for currency service
│
└── integration/
    └── test_metadata_routes.py         # NEW: Integration tests for endpoints
```

**Directory Purposes:**

- `src/api/routes/metadata.py`: API route handlers for metadata endpoints
- `src/schemas/metadata.py`: Pydantic response schemas ensuring consistent API contract
- `src/servuces/currency_service.py`: Currency service class with singleton pattern for currency data
- `alembic/versions/`: Database migration to update enum types
- `tests/`: Comprehensive test coverage for all metadata functionality

---

## Implementation Specification

### 3.1 Component Breakdown

#### Component: Enum Updates (AccountType, TransactionType)

**Files Involved**:
- `src/models/enums.py`
- `alembic/versions/<timestamp>_update_enums_for_metadata.py`

**Purpose**: Update existing enums to match new business requirements specified in feature description

**Current State Analysis**:
- `AccountType` currently has: `savings`, `credit_card`, `debit_card`, `loan`, `investment`, `other`
- `TransactionType` currently has: `debit`, `credit`, `transfer`, `fee`, `interest`, `other`

**Required Changes**:
- **AccountType** must support: `checking`, `savings`, `investment`, `other` (4 types)
  - Add: `checking` (new type)
  - Remove: `credit_card`, `debit_card`, `loan` (deprecated types)
  - Keep: `savings`, `investment`, `other`

- **TransactionType** must support: `income`, `expense`, `transfer` (3 types)
  - Add: `income`, `expense` (semantic equivalents of credit/debit)
  - Remove: `debit`, `credit`, `fee`, `interest`, `other` (deprecated types)
  - Keep: `transfer`

**Implementation Requirements**:

1. **Update Python Enums**:
   - Modify `AccountType` enum in `src/models/enums.py`:
     ```python
     class AccountType(str, enum.Enum):
         """Financial account types."""
         checking = "checking"      # NEW
         savings = "savings"         # EXISTING
         investment = "investment"   # EXISTING
         other = "other"             # EXISTING
     ```
   - Modify `TransactionType` enum in `src/models/enums.py`:
     ```python
     class TransactionType(str, enum.Enum):
         """Financial transaction types."""
         income = "income"       # NEW (replaces credit)
         expense = "expense"     # NEW (replaces debit)
         transfer = "transfer"   # EXISTING
     ```
   - Add helper method to both enums:
     ```python
     @classmethod
     def to_dict_list(cls) -> list[dict[str, str]]:
         """Return list of dicts with 'key' and 'label' for API responses."""
         return [{"key": item.value, "label": item.value.replace("_", " ").title()}
                 for item in cls]
     ```

2. **Database Migration Strategy**:

   **APPROACH**: Modify the existing `9cfdc3051d85_create_enums_and_extensions.py` migration file directly instead of creating a new migration. This migration hasn't been deployed to production yet, so we can safely update it.

   **CRITICAL**: PostgreSQL enums cannot have values removed directly. The existing migration creates the enums, so we'll update it to create them with the correct values from the start.

   **Changes to Migration File**:
   - Update `accounttype_enum` creation to use new values: `checking`, `savings`, `investment`, `other`
   - Update `transactiontype_enum` creation to use new values: `income`, `expense`, `transfer`
   - No data migration needed (since this is the initial schema creation)
   - Update downgrade to drop the correct enum values

   **If Migration Already Applied** (production scenario):
   - You would need to revert: `uv run alembic downgrade -1`
   - Delete existing migration file
   - Recreate with corrected enums
   - Re-apply: `uv run alembic upgrade head`

3. **Rollback Strategy**:
   - Since we're modifying the initial migration, rollback simply drops the enums (as already implemented in downgrade)
   - If migration was already applied in development, developers revert and reapply with updated values

**Edge Cases & Error Handling**:
- [ ] If migration already applied, handle revert and reapply process
- [ ] Validate that enum values match Python enum exactly (case-sensitive)
- [ ] Ensure enum member names are uppercase (Python convention)

**Dependencies**:
- Internal: `src/models/base.py` (Base class), `alembic` (migration framework)
- External: PostgreSQL 12+ (native enum support)

**Testing Requirements**:
- [ ] Unit test: `AccountType.to_dict_list()` returns correct format
- [ ] Unit test: `TransactionType.to_dict_list()` returns correct format
- [ ] Unit test: All enum values are lowercase strings
- [ ] Unit test: Enum member names are uppercase
- [ ] Integration test: Create account with `checking` type
- [ ] Integration test: Create transaction with `income` type

**Acceptance Criteria**:
- [ ] Python enums updated to match requirements exactly
- [ ] Existing migration file modified with correct enum values
- [ ] Migration can be applied cleanly on fresh database
- [ ] All tests pass (100% coverage for enum code)
- [ ] Database enum types match Python enum values exactly

**Implementation Notes**:
- Modifying existing migration is safe since it hasn't been deployed to production
- If migration was already applied locally, developers must revert and reapply
- Use `op.execute()` with raw SQL for enum creation (as already done in existing migration)
- Document in team chat/PR that existing migration was modified

---

#### Component: Currency Service

**Files Involved**:
- `src/servuces/currency_service.py` (NEW)

**Purpose**: Provide authoritative list of supported currencies with ISO 4217 codes, symbols, and names through a well-encapsulated service class

**Implementation Requirements**:

1. **Create Currency Pydantic Model**:
   - Define `Currency` Pydantic BaseModel for validation and serialization:
     ```python
     from pydantic import BaseModel, Field

     class Currency(BaseModel):
         """ISO 4217 currency representation."""
         code: str = Field(min_length=3, max_length=3, description="ISO 4217 currency code")
         symbol: str = Field(min_length=1, description="Currency symbol")
         name: str = Field(min_length=1, description="Full currency name")

         model_config = {"frozen": True}  # Immutable

         @classmethod
         def create(cls, code: str, symbol: str, name: str) -> "Currency":
             """Factory method for creating currency instances."""
             return cls(code=code.upper(), symbol=symbol, name=name)
     ```

2. **Create Currency Service (Singleton Pattern)**:
   - Implement `CurrencyService` class with singleton pattern:
     ```python
     from typing import ClassVar

     class CurrencyService:
         """
         Currency service providing ISO 4217 currency data.

         Singleton pattern ensures single instance of currency list in memory.
         """

         _instance: ClassVar["CurrencyService | None"] = None
         _currencies: list[Currency]

         def __new__(cls) -> "CurrencyService":
             if cls._instance is None:
                 cls._instance = super().__new__(cls)
                 cls._instance._initialize_currencies()
             return cls._instance

         def _initialize_currencies(self) -> None:
             """Initialize currency list. Called once on first instantiation."""
             self._currencies = [
                 Currency.create("USD", "$", "US Dollar"),
                 Currency.create("EUR", "€", "Euro"),
                 Currency.create("GBP", "£", "Pound Sterling"),
                 # ... more currencies (see detailed list below)
             ]

         def get_all(self) -> list[Currency]:
             """Get all supported currencies."""
             return self._currencies.copy()  # Return copy to prevent modification

         def get_by_code(self, code: str) -> Currency | None:
             """Get currency by ISO 4217 code (case-insensitive)."""
             code_upper = code.upper()
             return next((c for c in self._currencies if c.code == code_upper), None)

         def is_supported(self, code: str) -> bool:
             """Check if currency code is supported."""
             return self.get_by_code(code) is not None
     ```

3. **Currency Selection Criteria** (prioritize by usage):
   - Include top most used currencies (balance between coverage and simplicity)

4. **Detailed Currency List** (in `_initialize_currencies` method):
   ```python
   self._currencies = [
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
   ```

5. **Convenience Function** (module-level for easy access):
   ```python
   def get_currency_service() -> CurrencyService:
       """Get singleton instance of CurrencyService."""
       return CurrencyService()
   ```

**Edge Cases & Error Handling**:
- [ ] Handle unknown currency code lookup (return None from `get_by_code`)
- [ ] Handle case-insensitive currency code lookups (convert to uppercase in factory)
- [ ] Ensure all symbols are valid UTF-8 (Pydantic validates automatically)
- [ ] Validate no duplicate currency codes (test validates uniqueness)
- [ ] Singleton instance thread-safe (Python's `__new__` is thread-safe)

**Dependencies**:
- Internal: `pydantic` (BaseModel for Currency)
- External: None

**Testing Requirements**:
- [ ] Unit test: `CurrencyService()` returns same instance (singleton)
- [ ] Unit test: `get_all()` returns list of 30 currencies
- [ ] Unit test: `get_by_code("USD")` returns USD currency
- [ ] Unit test: `get_by_code("usd")` works (case-insensitive)
- [ ] Unit test: `get_by_code("INVALID")` returns None
- [ ] Unit test: `is_supported("EUR")` returns True
- [ ] Unit test: `is_supported("XXX")` returns False
- [ ] Unit test: `Currency` model validates correctly (frozen, proper fields)
- [ ] Unit test: All currency codes are 3 uppercase letters
- [ ] Unit test: No duplicate currency codes exist
- [ ] Unit test: `get_all()` returns copy (modifications don't affect internal list)

**Acceptance Criteria**:
- [ ] Currency service class implements singleton pattern correctly
- [ ] Currency list contains 30 major currencies
- [ ] All currencies use Pydantic BaseModel with validation
- [ ] Service methods work correctly
- [ ] 100% test coverage for currency module

**Implementation Notes**:
- Singleton pattern ensures only one currency list in memory
- Pydantic `frozen=True` makes Currency immutable (thread-safe)
- `get_all()` returns copy to prevent external modification
- Currency symbols properly encode with UTF-8 (Pydantic handles this)
- Consider alphabetical sorting by code for easier frontend dropdown rendering
- Future enhancement: Add `decimal_places` field to Currency model

---

#### Component: Metadata Response Schemas

**Files Involved**:
- `src/schemas/metadata.py` (NEW)

**Purpose**: Define Pydantic schemas for consistent, validated metadata API responses

**Implementation Requirements**:

1. **Account Type Schema**:
   ```python
   from pydantic import BaseModel, Field

   class AccountTypeItem(BaseModel):
       """Single account type metadata item."""
       key: str = Field(description="Account type key", examples=["checking", "savings"])
       label: str = Field(description="Display label", examples=["Checking", "Savings"])

   class AccountTypesResponse(BaseModel):
       """Response schema for GET /api/metadata/account-types"""
       account_types: list[AccountTypeItem] = Field(description="List of available account types")
   ```

2. **Currency Schema**:
   ```python
   class CurrencyItem(BaseModel):
       """Single currency metadata item."""
       code: str = Field(description="ISO 4217 currency code", examples=["USD", "EUR"])
       symbol: str = Field(description="Currency symbol", examples=["$", "€"])
       name: str = Field(description="Full currency name", examples=["US Dollar", "Euro"])

   class CurrenciesResponse(BaseModel):
       """Response schema for GET /api/metadata/currencies"""
       currencies: list[CurrencyItem] = Field(description="List of supported currencies")
   ```

3. **Transaction Type Schema**:
   ```python
   class TransactionTypeItem(BaseModel):
       """Single transaction type metadata item."""
       key: str = Field(description="Transaction type key", examples=["income", "expense"])
       label: str = Field(description="Display label", examples=["Income", "Expense"])

   class TransactionTypesResponse(BaseModel):
       """Response schema for GET /api/metadata/transaction-types"""
       transaction_types: list[TransactionTypeItem] = Field(description="List of transaction types")
   ```

4. **Schema Configuration**:
   - All schemas use `BaseModel` (not `from_attributes` since no ORM objects)
   - All fields required (no optional fields)
   - Include detailed descriptions for OpenAPI documentation
   - Include examples for Swagger UI

**Edge Cases & Error Handling**:
- [ ] Validate all required fields present (Pydantic handles automatically)
- [ ] Validate field types (str, list, etc.)
- [ ] Handle serialization of special Unicode characters in currency symbols

**Dependencies**:
- Internal: `pydantic` (already used throughout project)
- External: None

**Testing Requirements**:
- [ ] Unit test: AccountTypesResponse serializes correctly
- [ ] Unit test: CurrenciesResponse serializes correctly
- [ ] Unit test: TransactionTypesResponse serializes correctly
- [ ] Unit test: Schema validation rejects invalid data
- [ ] Unit test: Schema examples match actual data structure

**Acceptance Criteria**:
- [ ] Schemas match frontend requirements exactly
- [ ] OpenAPI documentation generated correctly
- [ ] All schemas validated by Pydantic
- [ ] Examples provided for all schemas

**Implementation Notes**:
- Keep schemas simple - no complex validation needed
- Use clear field names matching frontend expectations
- Follow existing schema patterns in `src/schemas/common.py`

---

#### Component: Metadata API Routes

**Files Involved**:
- `src/api/routes/metadata.py` (NEW)
- `src/main.py` (MODIFIED)

**Purpose**: Expose metadata endpoints for frontend consumption

**Implementation Requirements**:

1. **Create Metadata Router**:
   ```python
   """
   Metadata API endpoints.

   This module provides:
   - Account types metadata (for dropdowns)
   - Currency metadata (for dropdowns)
   - Transaction types metadata (for dropdowns)

   These endpoints serve as the authoritative source for business data,
   ensuring frontend and backend stay in sync.
   """

   import logging
   from fastapi import APIRouter
   from fastapi.responses import JSONResponse

   from src.models.enums import AccountType, TransactionType
   from src.services.currency_service import get_currency_service
   from src.schemas.metadata import (
       AccountTypesResponse,
       CurrenciesResponse,
       TransactionTypesResponse,
   )

   logger = logging.getLogger(__name__)

   router = APIRouter(prefix="/metadata", tags=["Metadata"])
   ```

2. **Implement GET /api/metadata/account-types**:
   ```python
   @router.get(
       "/account-types",
       response_model=AccountTypesResponse,
       summary="Get available account types",
       description="Returns list of supported account types for dropdowns and filters.",
   )
   async def get_account_types() -> AccountTypesResponse:
       """
       Get all available account types.

       Returns:
           AccountTypesResponse with list of account type objects

       Example Response:
           {
               "account_types": [
                   {"key": "checking", "label": "Checking"},
                   {"key": "savings", "label": "Savings"},
                   {"key": "investment", "label": "Investment"},
                   {"key": "other", "label": "Other"}
               ]
           }
       """
       return AccountTypesResponse(account_types=AccountType.to_dict_list())
   ```

3. **Implement GET /api/metadata/currencies**:
   ```python
   @router.get(
       "/currencies",
       response_model=CurrenciesResponse,
       summary="Get supported currencies",
       description="Returns list of supported currencies with ISO 4217 codes and symbols.",
   )
   async def get_currencies() -> CurrenciesResponse:
       """
       Get all supported currencies.

       Returns:
           CurrenciesResponse with list of currency objects (code, symbol, name)

       Example Response:
           {
               "currencies": [
                   {"code": "USD", "symbol": "$", "name": "US Dollar"},
                   {"code": "EUR", "symbol": "€", "name": "Euro"},
                   ...
               ]
           }
       """
       currency_service = get_currency_service()
       currencies = currency_service.get_all()
       return CurrenciesResponse(currencies=currencies)
   ```

4. **Implement GET /api/metadata/transaction-types**:
   ```python
   @router.get(
       "/transaction-types",
       response_model=TransactionTypesResponse,
       summary="Get available transaction types",
       description="Returns list of supported transaction types for filtering and creation.",
   )
   async def get_transaction_types() -> TransactionTypesResponse:
       """
       Get all available transaction types.

       Returns:
           TransactionTypesResponse with list of transaction type objects

       Example Response:
           {
               "transaction_types": [
                   {"key": "income", "label": "Income"},
                   {"key": "expense", "label": "Expense"},
                   {"key": "transfer", "label": "Transfer"}
               ]
           }
       """
       return TransactionTypesResponse(transaction_types=TransactionType..to_dict_list())
   ```

5. **Add Caching Headers** (Optional Enhancement):
   ```python
   # Add to each route decorator:
   responses={
       200: {"description": "Successful response"},
   },
   response_headers={
       "Cache-Control": "public, max-age=86400",  # 24 hours
   }
   ```

6. **Register Router in Main App**:
   ```python
   # In src/main.py, add to metadata_router:

   from src.api.routes import metadata  # Add import

   # In api_router includes section:
   api_router.include_router(metadata.router)
   ```

**Edge Cases & Error Handling**:
- [ ] Handle empty enum lists (should never happen, but defensive)
- [ ] Ensure Unicode symbols serialize correctly in JSON response
- [ ] Handle potential enum iteration errors (try/except with logging)

**Dependencies**:
- Internal: `AccountType`, `TransactionType`, `get_currency_service`, schemas
- External: `fastapi`

**Testing Requirements**:
- [ ] Integration test: GET /api/metadata/account-types returns 200
- [ ] Integration test: Response matches AccountTypesResponse schema
- [ ] Integration test: Response contains expected account types (checking, savings, investment, other)
- [ ] Integration test: GET /api/metadata/currencies returns 200
- [ ] Integration test: Response contains ≥30 currencies
- [ ] Integration test: Each currency has code, symbol, and name
- [ ] Integration test: GET /api/metadata/transaction-types returns 200
- [ ] Integration test: Response contains income, expense, transfer
- [ ] Integration test: All endpoints return valid JSON
- [ ] E2E test: Frontend can parse and use responses

**Acceptance Criteria**:
- [ ] All three endpoints return 200 OK
- [ ] Response format matches frontend expectations exactly
- [ ] Endpoints documented in Swagger UI
- [ ] No authentication required (public endpoints)
- [ ] Response time <50ms (in-memory data)
- [ ] Cache headers set appropriately

**Implementation Notes**:
- No rate limiting needed (read-only, cacheable, fast)
- No authentication needed (metadata is public information)
- Consider adding ETag headers for efficient caching
- Log each request at DEBUG level for monitoring

---

### 3.2 Detailed File Specifications

#### `src/servuces/currency_service.py` (NEW FILE)

**Purpose**: Currency service class with singleton pattern for managing ISO 4217 currency data

**Implementation**: (Full file content)

```python
"""
Currency service for ISO 4217 currency data.

This module provides:
- Currency Pydantic model for type-safe currency representation
- CurrencyService singleton for managing currency list
- Helper function for easy service access
"""

from typing import ClassVar

from pydantic import BaseModel, Field


class Currency(BaseModel):
    """
    ISO 4217 currency representation.

    Immutable Pydantic model for currency data with validation.
    """

    code: str = Field(min_length=3, max_length=3, description="ISO 4217 currency code")
    symbol: str = Field(min_length=1, description="Currency symbol")
    name: str = Field(min_length=1, description="Full currency name")

    model_config = {"frozen": True}  # Immutable for thread safety

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


class CurrencyService:
    """
    Currency service providing ISO 4217 currency data.

    Singleton pattern ensures single instance of currency list in memory.
    Thread-safe due to Python's __new__ implementation and immutable currencies.
    """

    _instance: ClassVar["CurrencyService | None"] = None
    _currencies: list[Currency]

    def __new__(cls) -> "CurrencyService":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_currencies()
        return cls._instance

    def _initialize_currencies(self) -> None:
        """Initialize currency list. Called once on first instantiation."""
        self._currencies = [
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


def get_currency_service() -> CurrencyService:
    """
    Get singleton instance of CurrencyService.

    Convenience function for easy access to currency service.

    Returns:
        CurrencyService singleton instance
    """
    return CurrencyService()
```

**Edge Cases**:
- Singleton already instantiated: Returns existing instance
- Unknown currency code: `get_by_code()` returns None
- Case mismatch: Factory method converts to uppercase

**Tests**:
- [ ] Test: `CurrencyService()` returns same instance twice
- [ ] Test: `get_all()` returns 30 currencies
- [ ] Test: `get_by_code("USD")` returns USD
- [ ] Test: `is_supported("EUR")` returns True

---

#### `src/models/enums.py`

**Purpose**: Define business enums with updated values matching requirements

**Implementation**:

1. Update `AccountType` enum (lines 16-47):
   ```python
   class AccountType(str, enum.Enum):
       """
       Financial account types.

       Supported account types for the platform. Updated to match
       business requirements: checking, savings, investment, other.

       Attributes:
           checking: Current/checking accounts for daily transactions
           savings: Savings accounts with positive balances
           investment: Investment or brokerage accounts
           other: User-defined account types not covered by standard types
       """

       checking = "checking"
       savings = "savings"
       investment = "investment"
       other = "other"

       @classmethod
       def to_dict_list(cls) -> list[dict[str, str]]:
           """Return list of dicts for API responses."""
           return [
               {"key": item.value, "label": item.value.replace("_", " ").title()}
               for item in cls
           ]
   ```

2. Update `TransactionType` enum (lines 114-171):
   ```python
   class TransactionType(str, enum.Enum):
       """
       Financial transaction types.

       Supported transaction types: income (money in), expense (money out),
       and transfer (between own accounts).

       Attributes:
           income: Money in - salary, deposits, refunds, transfers in
           expense: Money out - purchases, bills, withdrawals, payments
           transfer: Movement of money between user's own accounts
       """

       income = "income"
       expense = "expense"
       transfer = "transfer"

       @classmethod
       def to_dict_list(cls) -> list[dict[str, str]]:
           """Return list of dicts for API responses."""
           return [
               {"key": item.value, "label": item.value.replace("_", " ").title()}
               for item in cls
           ]
   ```

**Edge Cases**:
- Existing code referencing removed enum values will break (expected - breaking change)
- Old migration files still reference old enum values (okay - migrations are immutable)

**Tests**:
- [ ] Test: `AccountType.checking.value == "checking"`
- [ ] Test: `len(list(AccountType)) == 4`
- [ ] Test: `AccountType.to_dict_list()` returns correct format
- [ ] Test: `TransactionType.income.value == "income"`
- [ ] Test: `len(list(TransactionType)) == 3`
- [ ] Test: `TransactionType.to_dict_list()` returns correct format

---

#### `src/core/constants.py` (NEW FILE)

**Purpose**: Define currency constants and helper functions

**Implementation**: (Full file content as specified in Component section above)

**Edge Cases**:
- When currency code not found: Return None
- When case doesn't match: Convert to uppercase

**Tests**:
- [ ] Test: `len(SUPPORTED_CURRENCIES) >= 30`
- [ ] Test: All currencies have required fields
- [ ] Test: `get_currency_by_code("USD")` returns USD
- [ ] Test: `get_currency_by_code("invalid")` returns None

---

#### `src/schemas/metadata.py` (NEW FILE)

**Purpose**: Pydantic response schemas for metadata endpoints

**Implementation**: (Full schemas as specified in Component section above)

**Edge Cases**:
- Schema validation automatically handles missing fields
- Pydantic serialization handles Unicode correctly

**Tests**:
- [ ] Test: Valid data passes validation
- [ ] Test: Invalid data raises ValidationError
- [ ] Test: Serialization produces correct JSON structure

---

#### `src/api/routes/metadata.py` (NEW FILE)

**Purpose**: API route handlers for metadata endpoints

**Implementation**: (Full router implementation as specified in Component section above)

**Edge Cases**:
- Empty enum list: Should never happen, but log error if it does
- Unicode symbol encoding: FastAPI handles automatically

**Tests**:
- [ ] Test: GET /account-types returns 200
- [ ] Test: GET /currencies returns 200
- [ ] Test: GET /transaction-types returns 200
- [ ] Test: Response format matches schema

---

#### `alembic/versions/9cfdc3051d85_create_enums_and_extensions.py` (MODIFIED FILE)

**Purpose**: Update existing migration to create enums with correct values from the start

**Implementation Changes**:

Update lines 128-130 in the existing migration file:

```python
# BEFORE (old values):
accounttype_enum = postgresql.ENUM('savings', 'credit_card', 'debit_card', 'loan', 'investment', 'other', name='accounttype')
permissionlevel_enum = postgresql.ENUM('owner', 'editor', 'viewer', name='permissionlevel')
transactiontype_enum = postgresql.ENUM('debit', 'credit', 'transfer', 'fee', 'interest', 'other', name='transactiontype')

# AFTER (new values):
accounttype_enum = postgresql.ENUM('checking', 'savings', 'investment', 'other', name='accounttype')
permissionlevel_enum = postgresql.ENUM('owner', 'editor', 'viewer', name='permissionlevel')  # unchanged
transactiontype_enum = postgresql.ENUM('income', 'expense', 'transfer', name='transactiontype')
```

**Full Modified Section** (lines 117-136):

```python
# =========================================================================
# STEP 2: Create Enums (explicitly, before tables)
# =========================================================================
# Create all enum types first to ensure they exist before table creation
# Using checkfirst=True to avoid duplicate creation errors
audit_action_enum = postgresql.ENUM(
    'LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'PASSWORD_CHANGE', 'TOKEN_REFRESH',
    'CREATE', 'READ', 'UPDATE', 'DELETE',
    'PERMISSION_GRANT', 'PERMISSION_REVOKE', 'ROLE_ASSIGN', 'ROLE_REMOVE',
    'ACCOUNT_ACTIVATE', 'ACCOUNT_DEACTIVATE', 'ACCOUNT_LOCK', 'ACCOUNT_UNLOCK',
    'RATE_LIMIT_EXCEEDED', 'INVALID_TOKEN', 'PERMISSION_DENIED',
    'SPLIT_TRANSACTION', 'JOIN_TRANSACTION',
    name='audit_action_enum'
)
audit_status_enum = postgresql.ENUM('SUCCESS', 'FAILURE', 'PARTIAL', name='audit_status_enum')

# UPDATED: Changed to match new business requirements
accounttype_enum = postgresql.ENUM('checking', 'savings', 'investment', 'other', name='accounttype')
permissionlevel_enum = postgresql.ENUM('owner', 'editor', 'viewer', name='permissionlevel')
transactiontype_enum = postgresql.ENUM('income', 'expense', 'transfer', name='transactiontype')

audit_action_enum.create(op.get_bind(), checkfirst=True)
audit_status_enum.create(op.get_bind(), checkfirst=True)
accounttype_enum.create(op.get_bind(), checkfirst=True)
permissionlevel_enum.create(op.get_bind(), checkfirst=True)
transactiontype_enum.create(op.get_bind(), checkfirst=True)
```

**Migration Application Notes**:

If the migration has already been applied locally:
1. Revert the migration: `uv run alembic downgrade -1`
2. Modify the migration file as shown above
3. Reapply: `uv run alembic upgrade head`

If starting fresh (new database):
1. Just modify the file and run: `uv run alembic upgrade head`

**Edge Cases**:
- Migration already applied: Developers must revert, modify, and reapply
- New database: Migration applies cleanly with correct enum values
- Team coordination: Document in PR that migration file was modified

**Tests**:
- [ ] Test: Migration creates enums with correct values
- [ ] Test: Can create account with `checking` type
- [ ] Test: Can create transaction with `income` type
- [ ] Test: Migration downgrade drops enums successfully

---

## Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Database Schema Updates (Size: S, Priority: P0)

**Goal**: Update database enum types to support new account types and transaction types, ensuring data integrity is maintained during the transition.

**Scope**:
- ✅ Include: Python enum updates, database migration, data transformation
- ❌ Exclude: API endpoints, schemas, frontend integration

**Components to Implement**:
- [ ] Update Python enums in `src/models/enums.py`
- [ ] Modify existing Alembic migration `9cfdc3051d85_create_enums_and_extensions.py`
- [ ] Test migration on fresh database

**Detailed Tasks**:

1. [ ] Check if migration already applied
   - Run `uv run alembic current` to check current revision
   - If `9cfdc3051d85` is applied, run `uv run alembic downgrade -1` to revert
   - This allows us to modify the migration file safely

2. [ ] Update Python enums
   - Modify `AccountType` enum: add `CHECKING`, remove `credit_card`, `debit_card`, `loan`
   - Modify `TransactionType` enum: add `INCOME`, `EXPENSE`, remove `debit`, `credit`, `fee`, `interest`, `other`
   - Add `.to_dict_list()` classmethod to both enums
   - Update docstrings to reflect new values

3. [ ] Modify existing migration file
   - Edit `alembic/versions/9cfdc3051d85_create_enums_and_extensions.py`
   - Update line 128: `accounttype_enum = postgresql.ENUM('checking', 'savings', 'investment', 'other', name='accounttype')`
   - Update line 130: `transactiontype_enum = postgresql.ENUM('income', 'expense', 'transfer', name='transactiontype')`
   - Add comment noting the file was modified for metadata endpoints

4. [ ] Test migration locally
   - Drop database if needed: `docker exec emerald-postgres psql -U emerald_user -c "DROP DATABASE IF EXISTS emerald_db"`
   - Recreate database: `docker exec emerald-postgres psql -U emerald_user -c "CREATE DATABASE emerald_db"`
   - Run migrations: `uv run alembic upgrade head`
   - Verify enum values created correctly in database
   - Test creating account with `checking` type
   - Test creating transaction with `income` type

5. [ ] Update affected code
   - Search codebase for references to removed enum values
   - Update any hardcoded references (check test fixtures especially)
   - Update schemas and services to use new enum values

**Dependencies**:
- Requires: PostgreSQL 12+, Alembic installed, write access to database
- Blocks: Phase 2 (API endpoints depend on updated enums)

**Validation Criteria** (Phase complete when):
- [ ] Python enums updated to new values
- [ ] Existing migration file modified with correct enum values
- [ ] Migration runs successfully on fresh database
- [ ] Can create accounts with new `checking` type
- [ ] Can create transactions with new `income`/`expense` types
- [ ] All unit tests for enums pass
- [ ] No references to old enum values in codebase

**Risk Factors**:
- **Risk**: Team members have already applied the old migration
  - **Mitigation**: Document in PR that migration was modified; provide revert/reapply instructions
- **Risk**: Forgetting to update both Python enums and database migration
  - **Mitigation**: Test account/transaction creation to verify enum values match

**Estimated Effort**: 1 day (1 developer)

---

#### Phase 2: Currency Service & Schemas (Size: S, Priority: P0)

**Goal**: Create currency service class with singleton pattern and Pydantic schemas for all metadata endpoints.

**Scope**:
- ✅ Include: Currency service with singleton pattern, Pydantic Currency model, metadata schemas, comprehensive tests
- ❌ Exclude: API routes (covered in Phase 3)

**Components to Implement**:
- [ ] Create `src/servuces/currency_service.py` with Currency model and CurrencyService
- [ ] Create `src/schemas/metadata.py` with response schemas

**Detailed Tasks**:

1. [ ] Create currency service file
   - Create `src/servuces/currency_service.py`
   - Define `Currency` Pydantic BaseModel with `frozen=True`
   - Implement `Currency.create()` factory method
   - Implement `CurrencyService` class with singleton pattern
   - Add `_initialize_currencies()` method with 30 currencies
   - Implement `get_all()`, `get_by_code()`, `is_supported()` methods
   - Add `get_currency_service()` convenience function
   - Add comprehensive module docstring

2. [ ] Create metadata schemas file
   - Create `src/schemas/metadata.py`
   - Define `AccountTypeItem` and `AccountTypesResponse` schemas
   - Define `CurrencyItem` and `CurrenciesResponse` schemas
   - Define `TransactionTypeItem` and `TransactionTypesResponse` schemas
   - Add docstrings and field examples
   - Configure Pydantic settings

3. [ ] Write unit tests for currency service
   - Create `tests/unit/test_currency.py`
   - Test: `CurrencyService()` returns singleton (same instance)
   - Test: `get_all()` returns list of 30 currencies
   - Test: `get_all()` returns copy (modifications don't affect internal list)
   - Test: All currencies have required fields (code, symbol, name)
   - Test: No duplicate currency codes
   - Test: `get_by_code("USD")` returns USD currency object
   - Test: `get_by_code("usd")` works (case-insensitive)
   - Test: `get_by_code("INVALID")` returns None
   - Test: `is_supported("EUR")` returns True
   - Test: `is_supported("XXX")` returns False
   - Test: `Currency` model is frozen (immutable)
   - Test: `Currency.create()` converts code to uppercase

4. [ ] Write unit tests for schemas
   - Create `tests/unit/test_metadata_schemas.py`
   - Test: Valid data passes schema validation
   - Test: Invalid data raises ValidationError
   - Test: Schema serialization produces correct JSON
   - Test: All examples in schemas are valid

**Dependencies**:
- Requires: Phase 1 complete (updated enums used in schemas)
- Blocks: Phase 3 (routes depend on schemas)

**Validation Criteria** (Phase complete when):
- [ ] Currency service file created with singleton pattern
- [ ] Currency Pydantic model is frozen and validated
- [ ] Service contains 30+ currencies
- [ ] All service methods working correctly
- [ ] All metadata schemas defined
- [ ] Unit tests written and passing (100% coverage)
- [ ] Singleton pattern verified (same instance returned)
- [ ] Type hints validated by mypy
- [ ] Code formatted with Ruff

**Risk Factors**:
- **Risk**: Singleton pattern not thread-safe
  - **Mitigation**: Python's `__new__` is thread-safe; Currency objects are immutable (frozen)
- **Risk**: Unicode currency symbols don't serialize correctly
  - **Mitigation**: Pydantic handles UTF-8 encoding; test JSON serialization explicitly in unit tests
- **Risk**: Currency list incomplete for user needs
  - **Mitigation**: Start with 30 major currencies, easy to extend CurrencyService later

**Estimated Effort**: 0.5 days (1 developer)

---

#### Phase 3: Metadata API Endpoints (Size: M, Priority: P0)

**Goal**: Implement and test all three metadata API endpoints, ensuring they return correct data in the expected format.

**Scope**:
- ✅ Include: Route handlers, router registration, integration tests, API documentation
- ❌ Exclude: Frontend integration (handled by frontend team)

**Components to Implement**:
- [ ] Create `src/api/routes/metadata.py` with all three endpoints
- [ ] Register router in `src/main.py`
- [ ] Write comprehensive integration tests

**Detailed Tasks**:

1. [ ] Create metadata routes file
   - Create `src/api/routes/metadata.py`
   - Implement `GET /metadata/account-types` handler
   - Implement `GET /metadata/currencies` handler
   - Implement `GET /metadata/transaction-types` handler
   - Add comprehensive docstrings and OpenAPI metadata
   - Add appropriate logging (DEBUG level)

2. [ ] Register router in main app
   - Modify `src/main.py`
   - Import `metadata` router
   - Add `api_router.include_router(metadata.router)`
   - Verify router appears in Swagger UI

3. [ ] Write integration tests
   - Create `tests/integration/test_metadata_routes.py`
   - Test: GET /api/metadata/account-types returns 200
   - Test: account-types response matches schema
   - Test: account-types contains correct values (checking, savings, investment, other)
   - Test: GET /api/metadata/currencies returns 200
   - Test: currencies response matches schema
   - Test: currencies list has ≥30 items
   - Test: GET /api/metadata/transaction-types returns 200
   - Test: transaction-types response matches schema
   - Test: transaction-types contains income, expense, transfer
   - Test: All endpoints return valid JSON
   - Test: All endpoints have correct Content-Type header

4. [ ] Manual testing
   - Start dev server: `uv run uvicorn src.main:app --reload`
   - Test each endpoint with curl or browser
   - Verify Swagger UI documentation
   - Verify response format matches frontend expectations
   - Test response time (should be <50ms)

5. [ ] Update API documentation
   - Verify OpenAPI docs auto-generated correctly
   - Add usage examples to endpoint docstrings
   - Document response caching behavior

**Dependencies**:
- Requires: Phase 1 (enums) and Phase 2 (schemas) complete
- Blocks: Frontend integration (frontend team consumes endpoints)

**Validation Criteria** (Phase complete when):
- [ ] All three endpoints implemented and working
- [ ] Router registered in main app
- [ ] All integration tests passing (≥80% coverage)
- [ ] Swagger UI shows all three endpoints with correct documentation
- [ ] Manual testing confirms correct responses
- [ ] Response format matches frontend requirements exactly
- [ ] No authentication required (public endpoints)
- [ ] Response time <100ms (in-memory data)

**Risk Factors**:
- **Risk**: Response format doesn't match frontend expectations
  - **Mitigation**: Validate against frontend requirements document early
- **Risk**: Enum iteration fails unexpectedly
  - **Mitigation**: Add defensive error handling and logging

**Estimated Effort**: 1 day (1 developer)

---

#### Phase 4: Documentation & Deployment (Size: S, Priority: P1)

**Goal**: Finalize documentation, prepare for production deployment, and communicate completion to frontend team.

**Scope**:
- ✅ Include: Documentation updates, deployment preparation, frontend team notification
- ❌ Exclude: Actual production deployment (handled by DevOps)

**Components to Implement**:
- [ ] Update project documentation
- [ ] Prepare deployment checklist
- [ ] Notify frontend team

**Detailed Tasks**:

1. [ ] Update documentation
   - Update `CLAUDE.md` with new enum values
   - Document metadata endpoints in API section
   - Add migration notes for team
   - Update changelog/release notes

2. [ ] Create deployment checklist
   - [ ] All tests passing (unit + integration)
   - [ ] Code coverage ≥80%
   - [ ] Migration tested on staging database
   - [ ] Rollback procedure documented
   - [ ] Maintenance window scheduled (for enum migration)
   - [ ] Monitoring alerts configured (if needed)

3. [ ] Prepare migration for production
   - Test migration on copy of production data
   - Document expected downtime (enum swap)
   - Create rollback plan
   - Notify stakeholders of maintenance window

4. [ ] Notify frontend team
   - Share API endpoint URLs
   - Share example responses
   - Share OpenAPI/Swagger documentation link
   - Confirm response format matches their expectations
   - Coordinate integration testing

**Dependencies**:
- Requires: Phases 1-3 complete
- Blocks: Production deployment

**Validation Criteria** (Phase complete when):
- [ ] Documentation updated and accurate
- [ ] Deployment checklist completed
- [ ] Migration tested on staging environment
- [ ] Frontend team notified and has endpoint details
- [ ] Rollback procedure documented
- [ ] Code merged to main branch
- [ ] Ready for production deployment

**Risk Factors**:
- **Risk**: Migration causes unexpected downtime
  - **Mitigation**: Test on production copy, schedule maintenance window
- **Risk**: Frontend integration discovers format mismatch
  - **Mitigation**: Provide endpoints early for frontend testing

**Estimated Effort**: 0.5 days (1 developer)

---

### 4.2 Implementation Sequence

```
Phase 1: Database Schema Updates (P0, 1 day)
  ↓
Phase 2: Currency Constants & Schemas (P0, 0.5 days) ← Can start after Phase 1
  ↓
Phase 3: Metadata API Endpoints (P0, 1 day) ← Requires Phases 1 & 2
  ↓
Phase 4: Documentation & Deployment (P1, 0.5 days) ← Requires Phase 3
```

**Total Estimated Time**: 3 days (1 developer, sequential)

**Rationale for ordering**:
- **Phase 1 first** because enum updates are foundational - all other components depend on updated enums
- **Phase 2 after Phase 1** because schemas reference the updated enums
- **Phase 3 after Phases 1 & 2** because routes depend on both enums and schemas
- **Phase 4 last** because documentation and deployment require all implementation complete

**Parallel Opportunities**:
- Phase 2 tasks (currency constants and schemas) could be partially parallelized (different developers)
- Testing can happen incrementally as each component completes

**Quick Wins**:
- **Currency constants** can be created first (no dependencies) - provides immediate value for testing
- **Schemas** can be validated independently before routes exist
- **Migration can be tested** on development databases before routes are ready

---

## Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Using in-memory enums and constants avoids unnecessary database queries and caching complexity. No service layer needed for simple read-only operations.

- [x] **Have we avoided premature optimization?**
  - Yes. No caching layer, no CDN, no background workers. Simple HTTP endpoints returning static data. Can add optimizations later if needed.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows existing FastAPI route patterns, Pydantic schema patterns, and Alembic migration patterns already established in the project.

- [x] **Can we deliver value in smaller increments?**
  - Yes. Phased approach allows endpoints to be deployed independently. Phase 1 provides foundation, Phase 3 provides immediate value to frontend.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. Feature description explicitly requests these three endpoints to eliminate hardcoded frontend values. This directly solves that problem.

### Alternatives Considered

**Alternative 1: Database Tables for Metadata**
- **Description**: Create `account_types`, `transaction_types`, and `currencies` tables with CRUD operations
- **Why not chosen**:
  - Massive overkill for static data that rarely changes
  - Adds database queries, migrations complexity, and caching needs
  - Increases test complexity (need test data fixtures)
  - No business requirement for dynamic enum management
  - Violates YAGNI principle

**Alternative 2: External Currency API**
- **Description**: Fetch currency data from external service (e.g., fixer.io, exchangerate-api.io)
- **Why not chosen**:
  - Adds external dependency and potential failure point
  - Adds latency (network request per call)
  - Requires API key management
  - ISO 4217 is stable - no need for real-time updates
  - Overkill for simple dropdown population

**Alternative 3: GraphQL Schema with Metadata Queries**
- **Description**: Expose metadata via GraphQL schema instead of REST endpoints
- **Why not chosen**:
  - Project uses REST architecture consistently
  - GraphQL would be inconsistent with existing patterns
  - Adds complexity (new framework, client changes)
  - REST perfectly adequate for this use case
  - Would require significant frontend changes

**Alternative 4: Keep Enums in Frontend**
- **Description**: Continue hardcoding enums in frontend, sync manually
- **Why not chosen**:
  - This is the problem we're solving (frontend/backend desync)
  - Violates "backend as source of truth" principle
  - Requires coordination for every enum change
  - Error-prone and maintenance burden
  - Feature description explicitly rejects this approach

**Rationale**: The proposed REST endpoints with in-memory data provide the simplest, most maintainable solution that aligns with existing architecture and directly solves the stated problem without unnecessary complexity.

---

## References & Related Documents

### Internal Documentation
- **Feature Description**: `.features/descriptions/metadata-endpoints.md` - Original requirements
- **Backend Standards**: `.claude/standards/backend.md` - Layered architecture, code quality
- **API Standards**: `.claude/standards/api.md` - REST conventions, response formats
- **Database Standards**: `.claude/standards/database.md` - Migration best practices
- **Testing Standards**: `.claude/standards/testing.md` - Coverage requirements
- **Project README**: `CLAUDE.md` - Setup, commands, architecture overview

### External Resources

#### ISO 4217 Currency Codes
- [ISO 4217 Official Standard](https://www.iso.org/iso-4217-currency-codes.html) - Authoritative currency code standard
- [IBAN Currency Code List](https://www.iban.com/currency-codes) - Comprehensive currency reference
- [Wikipedia ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) - Currency code reference

#### Python & FastAPI
- [Python Enum Documentation](https://docs.python.org/3/library/enum.html) - Official enum module docs
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Framework documentation
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/) - Schema validation

#### PostgreSQL Enums
- [PostgreSQL Enum Types](https://www.postgresql.org/docs/current/datatype-enum.html) - Official enum type docs
- [Alembic Enum Evolution](https://alembic.sqlalchemy.org/en/latest/ops.html#enum-operations) - Alembic enum operations
- [SQLAlchemy Enum Best Practices](https://www.pythontutorials.net/blog/best-way-to-do-enum-in-sqlalchemy/) - Enum integration patterns

#### Best Practices
- [REST API Design Best Practices](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/) - REST conventions
- [API Versioning Best Practices](https://www.freecodecamp.org/news/rest-api-best-practices-rest-endpoint-design-examples/) - Versioning strategies
- [Python Type Hints Best Practices](https://realpython.com/python-type-checking/) - Type safety

### Related Project Files
- `src/models/enums.py` - Existing enum definitions
- `src/schemas/common.py` - Existing schema patterns
- `alembic/versions/9cfdc3051d85_create_enums_and_extensions.py` - Enum creation migration
- `src/api/routes/health.py` - Example simple route pattern

### Testing References
- `tests/conftest.py` - Test fixtures and setup
- `tests/integration/test_auth_routes.py` - Example integration tests
- Pytest documentation - Testing framework

---

## Success Metrics

### Technical Metrics
- [ ] All 3 metadata endpoints implemented and functional
- [ ] Test coverage ≥80% for all new code
- [ ] Migration tested on staging environment
- [ ] Response time <100ms for all endpoints
- [ ] Zero production errors in first week

### Business Metrics
- [ ] Frontend team successfully integrates endpoints
- [ ] Frontend removes all hardcoded enum values
- [ ] Zero frontend/backend desync issues after deployment
- [ ] Ability to add new account types without frontend changes

### Quality Metrics
- [ ] All code review feedback addressed
- [ ] Documentation complete and accurate
- [ ] Rollback procedure tested and documented
- [ ] Monitoring and alerting configured (if needed)

---

## Post-Implementation Considerations

### Future Enhancements

1. **Add More Currencies** (Low Priority)
   - Easy to add - just update `SUPPORTED_CURRENCIES` list
   - No database changes needed
   - Consider adding less common currencies on request

2. **Add Metadata Versioning** (Medium Priority)
   - If enums change frequently, consider version parameter: `/metadata/account-types?v=2`
   - Allows gradual frontend migration to new enum values
   - Requires version tracking and compatibility layer

3. **Add Caching Headers** (Low Priority)
   - Add ETag support for client caching validation
   - Add `Cache-Control: public, max-age=86400` headers
   - Reduces server load for repeated requests

4. **Internationalization (i18n)** (Future)
   - Add `Accept-Language` header support
   - Return localized labels (e.g., "Checking" → "Corriente" for Spanish)
   - Store translations in separate constants file

5. **Add Metadata Last-Modified Timestamp** (Future)
   - Return when metadata was last updated
   - Helps frontend determine when to refresh cache
   - Could be stored in config or computed from migration timestamp

### Maintenance Notes

- **Adding New Account Types**:
  1. Update `AccountType` enum in `src/models/enums.py`
  2. Create migration to add value to database enum: `ALTER TYPE accounttype ADD VALUE 'new_type'`
  3. No API changes needed (automatic via enum iteration)

- **Adding New Transaction Types**:
  - Same process as account types
  - Ensure new type semantics are clear (income vs. expense vs. transfer)

- **Adding New Currencies**:
  - Update `SUPPORTED_CURRENCIES` in `src/core/constants.py`
  - No migration needed (not stored in database)
  - Verify currency code follows ISO 4217 standard

- **Removing Enum Values**:
  - **BREAKING CHANGE** - requires migration like Phase 1
  - Must migrate existing data first
  - Coordinate with frontend team for removal

### Monitoring & Observability

**Recommended Monitoring** (Post-Deployment):
- Monitor endpoint response times (should be <50ms consistently)
- Monitor error rates (should be 0% - these are simple endpoints)
- Monitor cache hit rates (if caching added)
- Log any enum iteration errors (defensive logging)

**Alerts** (if needed):
- Alert if response time >200ms (indicates performance issue)
- Alert if any 5xx errors occur (should never happen)

### Security Considerations

- **No authentication required**: Metadata is public, non-sensitive business data
- **No rate limiting needed**: Fast, cacheable, read-only endpoints
- **No injection risks**: No user input, no database queries
- **CORS allowed**: Frontend needs cross-origin access (already configured)

### Performance Considerations

- **Expected load**: Very low (frontend fetches once on app load)
- **Response size**: Small (~1-5KB per endpoint)
- **Database impact**: Zero (no database queries)
- **Memory impact**: Negligible (static constants)
- **Scalability**: Excellent (stateless, cacheable, in-memory)

---

## Conclusion

This implementation plan provides a comprehensive, production-ready approach to implementing metadata endpoints for the Emerald Finance Platform backend. By following established patterns, maintaining simplicity, and ensuring thorough testing, we deliver a robust solution that serves as the authoritative source for business metadata while enabling the frontend to remain decoupled and maintainable.

The phased approach ensures incremental value delivery, with each phase building on the previous one while maintaining rollback capability. The total implementation time of ~3 days represents a balanced approach between speed and quality, with comprehensive testing and documentation ensuring long-term maintainability.

**Key Takeaways**:
1. Simple, in-memory data serving (no unnecessary complexity)
2. Follows existing codebase patterns (maintainability)
3. Comprehensive migration strategy (data integrity)
4. Thorough testing plan (quality assurance)
5. Clear documentation (team alignment)
6. Future-proof design (easy to extend)
