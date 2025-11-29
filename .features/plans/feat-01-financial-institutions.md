# Implementation Plan: Financial Institutions Master Data

**Feature ID**: feat-01-financial-institutions
**Phase**: 1 - Foundation
**Priority**: High
**Created**: 2025-11-27
**Status**: Ready for Implementation

---

## 1. Executive Summary

### Overview

This feature establishes a centralized repository of financial institutions (banks, credit unions, brokerages, and fintech companies) as master data for the Emerald Finance Platform. Currently, bank names are stored as free-text strings in the accounts table, leading to inconsistent data entry ("Chase", "chase", "Chase Bank", "JPMorgan Chase" all referring to the same institution). This foundational table will eliminate duplicate/inconsistent bank names, enable standardized institution data, support bank logos and metadata, and prepare the platform for future features like automated data enrichment and international bank support.

### Primary Objectives

1. **Create centralized financial institutions table** with proper identifiers (SWIFT codes, routing numbers) and metadata
2. **Establish institution type taxonomy** (bank, credit_union, brokerage, fintech, other) for categorization
3. **Seed database** with 100+ major financial institutions from US, UK, EU, and fintech companies
4. **Implement admin-only management API** for creating, updating, and deactivating institutions
5. **Provide public read API** for listing and searching institutions (paginated)
6. **Ensure data quality** through validation of SWIFT codes, routing numbers, and country codes

### Expected Outcomes

- **Standardized institution data**: Single source of truth for financial institutions
- **Improved data quality**: No duplicate or inconsistent bank names across users
- **International support**: SWIFT codes for global banks, routing numbers for US banks
- **Foundation for future features**: Prepares for account-to-institution linking (feat-02), logo display, and automated data enrichment
- **Admin capabilities**: Full CRUD operations on institutions for system administrators
- **User-facing search**: Users can search and select institutions when creating accounts (in feat-02)

### Success Criteria

- ✅ `financial_institutions` table created with all required columns, indexes, and constraints
- ✅ `InstitutionType` enum created with 5 values (bank, credit_union, brokerage, fintech, other)
- ✅ Seed script successfully populates initial institutions with accurate data
- ✅ All 5 API endpoints implemented and tested (list, get, create, update, deactivate)
- ✅ Admin authorization enforced (only admins can create/update/deactivate)
- ✅ All validation rules enforced (SWIFT format, routing number format, country code, uniqueness)
- ✅ Test coverage ≥ 80% for all new code
- ✅ No breaking changes to existing functionality
- ✅ Documentation updated (API docs, database schema docs)

---

## 2. Technical Architecture

### 2.1 System Design Overview

#### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│  API Layer (src/api/routes/financial_institutions.py)  │
│  - Admin: POST, PATCH, DELETE (is_active=false)        │
│  - Public: GET (list), GET /{id} (details)             │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼ calls
┌─────────────────────────────────────────────────────────┐
│  Service Layer (src/services/financial_institution_    │
│                 service.py)                             │
│  - Business logic: validation, duplicate checking       │
│  - SWIFT/routing number format validation               │
│  - Country code validation                              │
│  - Audit logging for all state changes                  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼ calls
┌─────────────────────────────────────────────────────────┐
│  Repository Layer (src/repositories/financial_         │
│                     institution_repository.py)          │
│  - Database queries: CRUD operations                    │
│  - Search by name/short_name (case-insensitive)         │
│  - Filter by country_code, institution_type             │
│  - Pagination support                                   │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼ persists to
┌─────────────────────────────────────────────────────────┐
│  Database (PostgreSQL)                                  │
│  - financial_institutions table                         │
│  - institution_type enum                                │
│  - Indexes: name, short_name, swift_code, routing_      │
│    number, country_code, institution_type, is_active    │
│  - Seed data: 100+ institutions                         │
└─────────────────────────────────────────────────────────┘
```

#### Key Components and Responsibilities

1. **Model Layer** (`src/models/financial_institution.py`)
   - Defines SQLAlchemy ORM model with all fields
   - Includes timestamp mixin for created_at/updated_at
   - No soft delete (institutions are deactivated via is_active flag)

2. **Enum** (`src/models/enums.py`)
   - `InstitutionType` enum with 5 values
   - Helper method `to_dict_list()` for API responses

3. **Repository Layer** (`src/repositories/financial_institution_repository.py`)
   - Extends `BaseRepository[FinancialInstitution]`
   - Custom queries: search by name, filter by type/country, check SWIFT/routing uniqueness
   - Pagination for list endpoints

4. **Service Layer** (`src/services/financial_institution_service.py`)
   - Validates SWIFT code format (8 or 11 alphanumeric, uppercase)
   - Validates routing number format (exactly 9 digits)
   - Validates country code (ISO 3166-1 alpha-2)
   - Checks uniqueness of SWIFT codes and routing numbers
   - Logs all state-changing operations to audit log

5. **Schema Layer** (`src/schemas/financial_institution.py`)
   - Request schemas: `FinancialInstitutionCreate`, `FinancialInstitutionUpdate`
   - Response schemas: `FinancialInstitutionResponse`, `FinancialInstitutionListItem`
   - Validation at Pydantic level for basic format checks

6. **API Layer** (`src/api/routes/financial_institutions.py`)
   - 5 endpoints: list (GET), get by ID (GET), create (POST), update (PATCH), deactivate (DELETE)
   - Admin-only: create, update, deactivate
   - Public/authenticated: list, get by ID

#### Integration Points

- **Audit Log**: All state-changing operations (create, update, deactivate) logged to `audit_logs` table
- **Admin Authorization**: Uses existing `require_admin` dependency for admin-only endpoints
- **Database Session**: Uses existing `get_db` dependency for session management
- **Future Integration**: This table will be referenced by `accounts.financial_institution_id` in feat-02

#### Data Flow

**Create Institution (Admin)**:
1. Admin sends POST /api/v1/financial-institutions with institution data
2. Route validates request via Pydantic schema
3. Service validates SWIFT/routing format, checks uniqueness, validates country code
4. Repository creates record in database
5. Service logs audit event (CREATE_FINANCIAL_INSTITUTION)
6. Route returns 201 Created with institution data

**List Institutions (Public)**:
1. User sends GET /api/v1/financial-institutions?country_code=US&type=bank
2. Route extracts query parameters
3. Service applies filters (country, type, is_active=true)
4. Repository executes paginated query with filters
5. Route returns 200 OK with paginated list

**Search Institutions (Public)**:
1. User sends GET /api/v1/financial-institutions?search=chase
2. Service performs case-insensitive search on name and short_name
3. Repository executes ILIKE query with search term
4. Route returns 200 OK with matching institutions

### 2.2 Technology Decisions

#### **Pydantic for Country Code Validation**

**Purpose**: Validate ISO 3166-1 alpha-2 country codes (e.g., "US", "GB", "DE")

**Why this choice**:
- Already using Pydantic extensively in the project
- Pydantic Extra Types provides `CountryAlpha2` type for ISO 3166-1 alpha-2 validation
- No additional dependencies beyond `pydantic-extra-types`
- Type-safe validation with clear error messages
- Integrates seamlessly with existing Pydantic schemas

**Version**: `pydantic-extra-types>=2.9.0` (compatible with Pydantic 2.x)

**Alternatives considered**:
- `pycountry`: More comprehensive but overkill for simple format validation
- `country-converter`: Designed for complex conversions, not simple validation
- Manual validation: Error-prone and doesn't cover edge cases

**Usage Example**:
```python
from pydantic import BaseModel
from pydantic_extra_types import CountryAlpha2

class FinancialInstitutionCreate(BaseModel):
    country_code: CountryAlpha2  # Validates "US", "GB", etc.
```

#### **Schwifty for SWIFT/BIC Code Validation**

**Purpose**: Validate SWIFT/BIC codes (8 or 11 alphanumeric characters)

**Why this choice**:
- Industry-standard library for IBAN and BIC validation
- Strict compliance with ISO 9362 (BIC/SWIFT standard)
- Raises `ValueError` for invalid codes (easy to handle)
- Actively maintained (latest update 2023.11.0)
- Supports both 8-character (head office) and 11-character (branch) codes
- Can enforce SWIFT compliance vs. ISO 9362:2022 (which allows numbers)

**Version**: `schwifty>=2023.11.0`

**Alternatives considered**:
- Manual regex validation: Doesn't validate country code component or checksums
- API-based validation: Adds latency and external dependency
- `pytekswift`: Less popular, less documentation

**Usage Example**:
```python
from schwifty import BIC

def validate_swift_code(swift_code: str) -> bool:
    try:
        BIC(swift_code)  # Raises ValueError if invalid
        return True
    except ValueError:
        return False
```

#### **Pydantic Extra Types for Routing Number Validation**

**Purpose**: Validate ABA routing numbers (9 digits with checksum)

**Why this choice**:
- Part of Pydantic Extra Types (same dependency as country codes)
- Implements checksum validation algorithm per ABA standard
- Type-safe validation in Pydantic schemas
- No additional dependencies

**Version**: `pydantic-extra-types>=2.9.0`

**Alternatives considered**:
- Manual checksum validation: Error-prone
- API-based validation: Expensive and adds latency
- Database lookup: Requires maintaining routing number database

**Usage Example**:
```python
from pydantic_extra_types.routing_number import ABARoutingNumber

class FinancialInstitutionCreate(BaseModel):
    routing_number: ABARoutingNumber | None = None
```

#### **PostgreSQL ENUM for Institution Types**

**Purpose**: Store institution type with database-level type safety

**Why this choice**:
- Already using PostgreSQL ENUMs for AccountType, TransactionType, etc.
- Database-level type safety (cannot insert invalid values)
- Smaller storage footprint than VARCHAR
- Fast equality comparisons
- Self-documenting schema

**Version**: PostgreSQL 16+

**Alternatives considered**:
- VARCHAR with CHECK constraint: More flexible but less type-safe
- Integer with lookup table: More complex, less readable

**Migration Strategy**:
- Create enum in dedicated migration (following project pattern)
- Add value using `ALTER TYPE ... ADD VALUE` if needed later

### 2.3 File Structure

```
src/
├── models/
│   ├── financial_institution.py    # NEW: SQLAlchemy model
│   └── enums.py                     # MODIFIED: Add InstitutionType enum
│
├── schemas/
│   └── financial_institution.py    # NEW: Pydantic request/response schemas
│
├── repositories/
│   └── financial_institution_repository.py  # NEW: Database operations
│
├── services/
│   └── financial_institution_service.py     # NEW: Business logic
│
├── api/
│   ├── routes/
│   │   └── financial_institutions.py        # NEW: API endpoints
│   └── dependencies.py              # MODIFIED: Add get_financial_institution_service
│
└── main.py                          # MODIFIED: Register financial_institutions router

alembic/
└── versions/
    ├── YYYYMMDD_add_institution_type_enum.py      # NEW: Create enum
    ├── YYYYMMDD_create_financial_institutions.py  # NEW: Create table
    └── YYYYMMDD_seed_financial_institutions.py    # NEW: Seed data

tests/
├── unit/
│   ├── test_financial_institution_service.py      # NEW: Service unit tests
│   └── test_financial_institution_repository.py   # NEW: Repository tests
│
└── integration/
    └── test_financial_institution_routes.py       # NEW: API integration tests

docs/
└── database-schema.md               # MODIFIED: Document new table
```

**Directory Purpose**:
- `src/models/`: SQLAlchemy ORM models and enums
- `src/schemas/`: Pydantic validation schemas for API
- `src/repositories/`: Database access layer (CRUD operations)
- `src/services/`: Business logic layer (validation, orchestration)
- `src/api/routes/`: FastAPI route definitions
- `alembic/versions/`: Database migrations
- `tests/`: Test suite (unit and integration)

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: InstitutionType Enum

**Files Involved**:
- `src/models/enums.py`

**Purpose**: Define institution type taxonomy for categorizing financial institutions

**Implementation Requirements**:

1. **Core Logic**:
   - Add `InstitutionType` enum class to `src/models/enums.py`
   - Inherit from `str, enum.Enum` for JSON serialization
   - Define 5 values: `bank`, `credit_union`, `brokerage`, `fintech`, `other`
   - Add docstring explaining each type with examples
   - Implement `to_dict_list()` class method for API responses

2. **Data Handling**:
   - Input: Enum value as string (e.g., "bank")
   - Output: Enum instance or dict list for API
   - Validation: Must be one of 5 defined values

3. **Edge Cases & Error Handling**:
   - [ ] Handle invalid enum value (raises `ValueError` automatically)
   - [ ] Ensure enum values are lowercase for consistency
   - [ ] Handle serialization to JSON (automatic with `str` inheritance)

4. **Dependencies**:
   - Internal: None
   - External: Python `enum` module

5. **Testing Requirements**:
   - [ ] Unit test: Verify all 5 enum values are defined
   - [ ] Unit test: `to_dict_list()` returns correct format
   - [ ] Unit test: Enum values are strings and lowercase
   - [ ] Unit test: Invalid value raises error

**Acceptance Criteria**:
- [ ] Enum defined with exactly 5 values
- [ ] Each value has clear docstring with examples
- [ ] `to_dict_list()` returns list of dicts with `key` and `label`
- [ ] All tests pass

**Implementation Notes**:
- Follow exact pattern of `AccountType` and `TransactionType` enums
- Keep docstring comprehensive (see `PermissionLevel` for example)
- Ensure consistency with database enum (created in migration)

---

#### Component: FinancialInstitution Model

**Files Involved**:
- `src/models/financial_institution.py`

**Purpose**: SQLAlchemy ORM model representing the financial_institutions table

**Implementation Requirements**:

1. **Core Logic**:
   - Create `FinancialInstitution` class extending `Base` and `TimestampMixin`
   - Define all columns: id (UUID), name, short_name, swift_code, routing_number, country_code, institution_type, logo_url, website_url, is_active
   - Set nullable constraints (name, short_name, country_code, institution_type, is_active are NOT NULL)
   - Define default values (is_active=True)
   - Add indexes on frequently queried columns
   - **Do NOT use SoftDeleteMixin** (institutions use is_active flag instead)

2. **Data Handling**:
   - Primary key: UUID auto-generated
   - Strings: VARCHAR with appropriate lengths (name: 200, short_name: 100, etc.)
   - Enum: institution_type references PostgreSQL ENUM
   - Boolean: is_active for marking defunct institutions
   - Timestamps: created_at, updated_at (from TimestampMixin)

3. **Edge Cases & Error Handling**:
   - [ ] Handle NULL values correctly (optional fields: swift_code, routing_number, logo_url, website_url)
   - [ ] Ensure unique constraints on swift_code and routing_number (partial unique index in migration)
   - [ ] Validate country_code length (exactly 2 characters)
   - [ ] Validate institution_type is valid enum value

4. **Dependencies**:
   - Internal: `Base`, `TimestampMixin`, `InstitutionType` enum
   - External: SQLAlchemy

5. **Testing Requirements**:
   - [ ] Unit test: Model instantiation with required fields
   - [ ] Unit test: Model instantiation with all fields
   - [ ] Unit test: Default values are set (is_active=True)
   - [ ] Unit test: Timestamps are auto-populated
   - [ ] Integration test: Insert and retrieve from database
   - [ ] Integration test: Unique constraint on swift_code
   - [ ] Integration test: Unique constraint on routing_number

**Acceptance Criteria**:
- [ ] Model defined with all 11 columns
- [ ] Proper nullable constraints and default values
- [ ] Timestamps auto-populated via mixin
- [ ] Model can be instantiated and persisted to database
- [ ] `__repr__` method returns useful string

**Implementation Notes**:
- Follow pattern from `User` model (see `src/models/user.py`)
- Use `Mapped[str]` type hints for all columns (SQLAlchemy 2.0 style)
- Index creation happens in migration, not in model (for maintainability)
- Do NOT add relationships yet (accounts table not modified in this feature)

---

#### Component: Pydantic Schemas

**Files Involved**:
- `src/schemas/financial_institution.py`

**Purpose**: Request/response validation schemas for API endpoints

**Implementation Requirements**:

1. **Core Logic**:
   - Create 5 schema classes:
     - `FinancialInstitutionBase`: Common fields (name, short_name, institution_type, country_code)
     - `FinancialInstitutionCreate`: For POST requests (all fields except id, timestamps)
     - `FinancialInstitutionUpdate`: For PATCH requests (all fields optional for partial updates)
     - `FinancialInstitutionResponse`: For GET responses (all fields including id, timestamps)
     - `FinancialInstitutionListItem`: For GET list responses (subset of fields for performance)

2. **Data Handling**:
   - Use `pydantic_extra_types.CountryAlpha2` for country_code validation
   - Use `pydantic_extra_types.routing_number.ABARoutingNumber` for routing_number validation
   - Use `pydantic.HttpUrl` for logo_url and website_url validation
   - Use `pydantic.Field` for constraints (min_length, max_length, description)
   - Use field validators for SWIFT code format validation
   - Strip whitespace from name and short_name fields
   - Uppercase country_code and swift_code

3. **Edge Cases & Error Handling**:
   - [ ] Validate name: 1-200 characters, required
   - [ ] Validate short_name: 1-100 characters, required
   - [ ] Validate swift_code: 8 or 11 alphanumeric, uppercase, optional
   - [ ] Validate routing_number: 9 digits with checksum, optional
   - [ ] Validate country_code: ISO 3166-1 alpha-2, uppercase, required
   - [ ] Validate institution_type: Must be valid InstitutionType enum value
   - [ ] Validate logo_url: Valid HTTP(S) URL, max 500 chars, optional
   - [ ] Validate website_url: Valid HTTP(S) URL, max 500 chars, optional
   - [ ] Validate is_active: Boolean, default True

4. **Dependencies**:
   - Internal: `InstitutionType` enum
   - External: `pydantic`, `pydantic_extra_types`

5. **Testing Requirements**:
   - [ ] Unit test: Valid create request passes validation
   - [ ] Unit test: Invalid SWIFT code fails validation
   - [ ] Unit test: Invalid routing number fails validation
   - [ ] Unit test: Invalid country code fails validation
   - [ ] Unit test: Invalid URL format fails validation
   - [ ] Unit test: Field length constraints enforced
   - [ ] Unit test: Update schema allows partial updates
   - [ ] Unit test: Response schema serializes from ORM model

**Acceptance Criteria**:
- [ ] All 5 schema classes defined with proper inheritance
- [ ] All validation rules enforced at Pydantic level
- [ ] Clear error messages for validation failures
- [ ] Schemas work with FastAPI automatic validation
- [ ] Response schemas serialize from ORM models (`from_attributes=True`)

**Implementation Notes**:
- Follow pattern from `src/schemas/user.py`
- Use `@field_validator` decorator for custom validation
- For SWIFT validation, call `schwifty.BIC()` and catch `ValueError`
- For list item schema, only include essential fields (id, name, short_name, institution_type, country_code, logo_url)

---

#### Component: Financial Institution Repository

**Files Involved**:
- `src/repositories/financial_institution_repository.py`

**Purpose**: Database access layer for financial institutions (CRUD + custom queries)

**Implementation Requirements**:

1. **Core Logic**:
   - Extend `BaseRepository[FinancialInstitution]`
   - Implement custom query methods:
     - `search_by_name(search_term, skip, limit)`: Case-insensitive search on name and short_name
     - `filter_institutions(country_code, institution_type, is_active, skip, limit)`: Multi-criteria filtering
     - `get_by_swift_code(swift_code)`: Find institution by SWIFT code
     - `get_by_routing_number(routing_number)`: Find institution by routing number
     - `swift_code_exists(swift_code, exclude_id)`: Check uniqueness
     - `routing_number_exists(routing_number, exclude_id)`: Check uniqueness
     - `count_filtered(country_code, institution_type, is_active)`: Count for pagination

2. **Data Handling**:
   - All queries filter by `is_active=True` by default (unless explicitly including inactive)
   - Search uses `ILIKE` for case-insensitive matching
   - Pagination uses `offset()` and `limit()`
   - Results ordered by `name` ascending

3. **Edge Cases & Error Handling**:
   - [ ] Handle None values in optional filter parameters
   - [ ] Handle empty search term (return all active institutions)
   - [ ] Handle case-insensitive search (convert to lowercase)
   - [ ] Handle pagination edge cases (skip > total, limit = 0)
   - [ ] Return empty list if no results (not None)

4. **Dependencies**:
   - Internal: `BaseRepository`, `FinancialInstitution` model
   - External: SQLAlchemy (`select`, `func`, `or_`)

5. **Testing Requirements**:
   - [ ] Unit test: Search by name returns matching institutions
   - [ ] Unit test: Search is case-insensitive
   - [ ] Unit test: Filter by country_code works
   - [ ] Unit test: Filter by institution_type works
   - [ ] Unit test: Filter by is_active works
   - [ ] Unit test: Pagination works correctly
   - [ ] Unit test: SWIFT code uniqueness check works
   - [ ] Unit test: Routing number uniqueness check works
   - [ ] Unit test: Count filtered returns correct total
   - [ ] Integration test: All queries work against real database

**Acceptance Criteria**:
- [ ] Repository extends BaseRepository correctly
- [ ] All 7 custom methods implemented and working
- [ ] Queries are efficient (use indexes)
- [ ] Pagination works with large datasets
- [ ] Uniqueness checks exclude specified ID (for updates)

**Implementation Notes**:
- Follow pattern from `UserRepository` (see `src/repositories/user_repository.py`)
- Use `query.where()` for filters, `query.order_by()` for sorting
- For search, use `or_(Institution.name.ilike(pattern), Institution.short_name.ilike(pattern))`
- For uniqueness checks, use same pattern as `email_exists()` in UserRepository

---

#### Component: Financial Institution Service

**Files Involved**:
- `src/services/financial_institution_service.py`

**Purpose**: Business logic layer for financial institution operations

**Implementation Requirements**:

1. **Core Logic**:
   - Implement service methods:
     - `create_institution(data, admin_user, request_id, ip_address, user_agent)`: Create new institution
     - `update_institution(id, data, admin_user, request_id, ip_address, user_agent)`: Update existing institution
     - `deactivate_institution(id, admin_user, request_id, ip_address, user_agent)`: Mark institution as inactive
     - `get_institution(id)`: Retrieve institution by ID
     - `list_institutions(country_code, institution_type, search, skip, limit)`: List with filters
     - `validate_swift_code(swift_code)`: Validate SWIFT/BIC format
     - `validate_routing_number(routing_number)`: Validate ABA routing number

2. **Data Handling**:
   - Validate all input data before database operations
   - Check uniqueness of SWIFT codes and routing numbers
   - Trim whitespace from name and short_name
   - Uppercase country_code and swift_code
   - Log all state-changing operations to audit log

3. **Edge Cases & Error Handling**:
   - [ ] Handle duplicate SWIFT code (raise AlreadyExistsError)
   - [ ] Handle duplicate routing number (raise AlreadyExistsError)
   - [ ] Handle invalid SWIFT format (raise ValidationError)
   - [ ] Handle invalid routing number (raise ValidationError)
   - [ ] Handle institution not found (raise NotFoundError)
   - [ ] Handle attempting to deactivate non-existent institution
   - [ ] Handle updating non-existent institution
   - [ ] Handle empty search term (return all active institutions)

4. **Dependencies**:
   - Internal: `FinancialInstitutionRepository`, `AuditService`, custom exceptions
   - External: `schwifty.BIC`, `pydantic_extra_types`

5. **Testing Requirements**:
   - [ ] Unit test: Create institution with valid data succeeds
   - [ ] Unit test: Create institution with duplicate SWIFT fails
   - [ ] Unit test: Create institution with invalid SWIFT format fails
   - [ ] Unit test: Update institution with valid data succeeds
   - [ ] Unit test: Update institution with duplicate routing number fails
   - [ ] Unit test: Deactivate institution sets is_active=False
   - [ ] Unit test: List institutions returns active only by default
   - [ ] Unit test: Search institutions filters correctly
   - [ ] Unit test: SWIFT validation catches invalid formats
   - [ ] Unit test: Routing number validation catches invalid checksums
   - [ ] Integration test: Create + retrieve + update + deactivate flow
   - [ ] Integration test: Audit log entries created for all operations

**Acceptance Criteria**:
- [ ] All 7 service methods implemented and tested
- [ ] All validation rules enforced before database operations
- [ ] Audit logging for all state-changing operations
- [ ] Clear error messages for all failure scenarios
- [ ] Business logic isolated from database and API layers

**Implementation Notes**:
- Follow pattern from `UserService` (see `src/services/user_service.py`)
- Use `schwifty.BIC(swift_code)` for SWIFT validation (raises ValueError if invalid)
- For routing number, use Pydantic validation in schemas
- For audit logging, create enum `AuditAction.CREATE_FINANCIAL_INSTITUTION`, `UPDATE_FINANCIAL_INSTITUTION`, `DEACTIVATE_FINANCIAL_INSTITUTION`
- Always check uniqueness BEFORE attempting insert/update

---

#### Component: API Routes

**Files Involved**:
- `src/api/routes/financial_institutions.py`
- `src/api/dependencies.py` (add service dependency)
- `src/main.py` (register router)

**Purpose**: FastAPI endpoints for financial institution management

**Implementation Requirements**:

1. **Core Logic**:
   - Implement 5 endpoints:
     - `GET /api/v1/financial-institutions`: List institutions (public, paginated)
     - `GET /api/v1/financial-institutions/{id}`: Get institution details (public)
     - `POST /api/v1/financial-institutions`: Create institution (admin only)
     - `PATCH /api/v1/financial-institutions/{id}`: Update institution (admin only)
     - `DELETE /api/v1/financial-institutions/{id}`: Deactivate institution (admin only)
   - Each endpoint extracts request ID, IP address, user agent from request
   - Admin endpoints use `require_admin` dependency
   - Public endpoints use `require_active_user` or no auth (depending on requirements)

2. **Data Handling**:
   - Request validation via Pydantic schemas (automatic)
   - Response serialization via Pydantic response_model
   - Query parameters: country_code, institution_type, search, skip, limit
   - Pagination: default limit=20, max limit=100
   - Return 201 Created for POST, 200 OK for GET/PATCH/DELETE

3. **Edge Cases & Error Handling**:
   - [ ] Handle invalid UUID format (422 Unprocessable Entity)
   - [ ] Handle institution not found (404 Not Found)
   - [ ] Handle duplicate SWIFT/routing (409 Conflict)
   - [ ] Handle invalid enum value (422 Unprocessable Entity)
   - [ ] Handle unauthorized access to admin endpoints (403 Forbidden)
   - [ ] Handle pagination out of range (return empty list)
   - [ ] Handle invalid query parameters (422 Unprocessable Entity)

4. **Dependencies**:
   - Internal: `get_financial_institution_service`, `require_admin`, `require_active_user`
   - External: FastAPI, Pydantic

5. **Testing Requirements**:
   - [ ] Integration test: List institutions returns 200 OK
   - [ ] Integration test: List with filters (country, type) works
   - [ ] Integration test: Search institutions works
   - [ ] Integration test: Pagination works (skip, limit)
   - [ ] Integration test: Get institution by ID returns 200 OK
   - [ ] Integration test: Get non-existent institution returns 404
   - [ ] Integration test: Create institution (admin) returns 201 Created
   - [ ] Integration test: Create institution (non-admin) returns 403 Forbidden
   - [ ] Integration test: Update institution (admin) returns 200 OK
   - [ ] Integration test: Deactivate institution (admin) sets is_active=False
   - [ ] Integration test: Duplicate SWIFT returns 409 Conflict
   - [ ] Integration test: Invalid SWIFT format returns 422 Unprocessable Entity

**Acceptance Criteria**:
- [ ] All 5 endpoints implemented with correct HTTP methods
- [ ] Authorization enforced (admin for create/update/delete)
- [ ] Request validation automatic via Pydantic
- [ ] Response models return correct data structure
- [ ] Error responses have clear messages and correct status codes
- [ ] Endpoints documented with OpenAPI (Swagger UI)

**Implementation Notes**:
- Follow pattern from `src/api/routes/users.py`
- Use `status.HTTP_201_CREATED` for POST, `status.HTTP_200_OK` for others
- Extract request context: `request_id=getattr(request.state, "request_id", None)`
- Use `Query()` for query parameters with defaults and validation
- For DELETE, implement as soft delete (set is_active=False), not physical delete

---

#### Component: Database Migrations

**Files Involved**:
- `alembic/versions/YYYYMMDD_add_institution_type_enum.py`
- `alembic/versions/YYYYMMDD_create_financial_institutions.py`
- `alembic/versions/YYYYMMDD_seed_financial_institutions.py`

**Purpose**: Create database schema and seed initial data

**Implementation Requirements**:

1. **Migration 1: Create InstitutionType Enum**
   - Create PostgreSQL enum `institution_type` with 5 values
   - Use `op.execute()` with explicit SQL
   - Add comprehensive docstring explaining enum evolution
   - Follow pattern from `9cfdc3051d85_create_enums_and_extensions.py`

2. **Migration 2: Create financial_institutions Table**
   - Create table with all 11 columns
   - Create primary key on `id`
   - Create indexes:
     - `ix_financial_institutions_name` (for searching)
     - `ix_financial_institutions_short_name` (for searching)
     - Partial unique index on `swift_code` (WHERE swift_code IS NOT NULL)
     - Partial unique index on `routing_number` (WHERE routing_number IS NOT NULL)
     - `ix_financial_institutions_country_code` (for filtering)
     - `ix_financial_institutions_institution_type` (for filtering)
     - `ix_financial_institutions_is_active` (for filtering)
   - Add check constraint: country_code length = 2
   - Add check constraint: routing_number length = 9 (if not NULL)
   - Add check constraint: swift_code length IN (8, 11) (if not NULL)

3. **Migration 3: Seed Initial Institutions**
   - Insert 100+ institutions with accurate data
   - US banks: Chase, Bank of America, Wells Fargo, Citibank, U.S. Bank, Goldman Sachs, Morgan Stanley, American Express, Fidelity, Vanguard (10+ total)
   - UK banks: HSBC, Barclays, Lloyds, Santander (UK operations) (4+ total)
   - European banks: Santander (Spain), BBVA, BNP Paribas, Société Générale, Deutsche Bank, Commerzbank, ING, Rabobank, UBS, Credit Suisse, UniCredit (11+ total)
   - Fintech: Revolut, N26, Wise (3+ total)
   - Each institution includes: name, short_name, institution_type, country_code, swift_code (if applicable), routing_number (US banks), logo_url (placeholder), website_url
   - Use `op.bulk_insert()` for performance
   - Idempotent: Check if seed data exists before inserting

4. **Data Handling**:
   - Use UUID v4 for all institution IDs
   - All seed SWIFT codes and routing numbers must be accurate (research required)
   - Logo URLs use placeholder service (e.g., `https://logo.clearbit.com/{domain}`)
   - All institutions marked as is_active=True
   - Timestamps set to migration execution time

5. **Edge Cases & Error Handling**:
   - [ ] Handle migration rollback (downgrade)
   - [ ] Handle re-running migration (idempotent seed)
   - [ ] Handle constraint violations during seed (skip duplicates)
   - [ ] Verify index creation doesn't fail on existing indexes

6. **Dependencies**:
   - Internal: None
   - External: Alembic, SQLAlchemy

7. **Testing Requirements**:
   - [ ] Test: Migration applies successfully
   - [ ] Test: Enum created with correct values
   - [ ] Test: Table created with correct columns
   - [ ] Test: All indexes created successfully
   - [ ] Test: Seed data inserted successfully
   - [ ] Test: Unique constraints enforced
   - [ ] Test: Downgrade removes table and enum
   - [ ] Test: Re-running seed migration is idempotent
   - [ ] Test: Can query institutions after migration

**Acceptance Criteria**:
- [ ] All 3 migrations created and tested
- [ ] Enum, table, and indexes created correctly
- [ ] 100+ institutions seeded with accurate data
- [ ] Migrations are reversible (downgrade works)
- [ ] Migrations are idempotent (can re-run safely)
- [ ] No breaking changes to existing schema

**Implementation Notes**:
- For partial unique indexes, use: `op.create_index('ix_name', 'table', ['column'], unique=True, postgresql_where=sa.text('column IS NOT NULL'))`
- For seed data, research actual SWIFT codes and routing numbers for accuracy
- Use JSON fixture file for seed data if list is very long (easier to maintain)
- Follow enum evolution guide from existing migration

---

#### Component: Audit Log Integration

**Files Involved**:
- `src/models/audit_log.py` (add new AuditAction enum values)
- `src/services/financial_institution_service.py` (log events)

**Purpose**: Log all state-changing operations for compliance and debugging

**Implementation Requirements**:

1. **Core Logic**:
   - Add 3 new `AuditAction` enum values:
     - `CREATE_FINANCIAL_INSTITUTION`
     - `UPDATE_FINANCIAL_INSTITUTION`
     - `DEACTIVATE_FINANCIAL_INSTITUTION`
   - Log events in service layer after successful database operations
   - Include user_id, action, status, resource_id, IP address, user agent

2. **Data Handling**:
   - Log successful operations with `AuditStatus.SUCCESS`
   - Log failed operations with `AuditStatus.FAILURE` and error details
   - Include institution ID in resource_id field
   - Include institution name in details field (for searchability)

3. **Edge Cases & Error Handling**:
   - [ ] Handle audit logging failure (log to application log but don't fail main operation)
   - [ ] Handle missing IP address or user agent (use None)

4. **Dependencies**:
   - Internal: `AuditService`, `AuditAction`, `AuditStatus`
   - External: None

5. **Testing Requirements**:
   - [ ] Integration test: Create institution logs audit event
   - [ ] Integration test: Update institution logs audit event
   - [ ] Integration test: Deactivate institution logs audit event
   - [ ] Integration test: Audit log includes correct user_id
   - [ ] Integration test: Audit log includes correct resource_id
   - [ ] Integration test: Failed operation logs FAILURE status

**Acceptance Criteria**:
- [ ] Audit log entries created for all state-changing operations
- [ ] Audit entries include all required fields
- [ ] Audit logging doesn't block main operations
- [ ] Audit log queryable by admin for compliance

**Implementation Notes**:
- Follow pattern from `UserService` audit logging
- Use `await audit_service.log_action(...)` after successful database commit
- Wrap audit logging in try/except to prevent failures from blocking operations

---

### 3.2 Detailed File Specifications

#### `src/models/enums.py`

**Purpose**: Add InstitutionType enum

**Implementation**:
```python
class InstitutionType(str, enum.Enum):
    """
    Financial institution types.

    Supported institution types for the platform. Used to categorize
    financial institutions for filtering and reporting.

    Attributes:
        bank: Traditional banks (commercial, retail, universal banks)
            Examples: JPMorgan Chase, Bank of America, HSBC, Deutsche Bank
        credit_union: Credit unions and cooperative banks
            Examples: Navy Federal Credit Union, State Employees' Credit Union
        brokerage: Investment firms and brokerage houses
            Examples: Fidelity Investments, Vanguard, Charles Schwab
        fintech: Financial technology companies
            Examples: Revolut, N26, Wise, Chime, Cash App
        other: Other financial institutions not covered above
            Examples: Payment processors, specialized lenders

    Usage:
        institution = FinancialInstitution(
            name="JPMorgan Chase Bank, N.A.",
            short_name="Chase",
            institution_type=InstitutionType.bank,
            ...
        )
    """

    bank = "bank"
    credit_union = "credit_union"
    brokerage = "brokerage"
    fintech = "fintech"
    other = "other"

    @classmethod
    def to_dict_list(cls) -> list[dict[str, str]]:
        """
        Return list of dicts with 'key' and 'label' for API responses.

        Returns:
            List of dictionaries with 'key' (enum value) and 'label' (display name)

        Example:
            [
                {"key": "bank", "label": "Bank"},
                {"key": "credit_union", "label": "Credit Union"},
                {"key": "brokerage", "label": "Brokerage"},
                {"key": "fintech", "label": "Fintech"},
                {"key": "other", "label": "Other"}
            ]
        """
        return [
            {"key": item.value, "label": item.value.replace("_", " ").title()}
            for item in cls
        ]
```

**Edge Cases**:
- Enum values must match database enum exactly
- Use lowercase with underscores for consistency

**Tests**:
- [ ] Test: All 5 values are defined
- [ ] Test: `to_dict_list()` returns correct format
- [ ] Test: Enum values are strings

---

#### `src/models/financial_institution.py`

**Purpose**: SQLAlchemy ORM model for financial_institutions table

**Implementation**: [Full model definition following User model pattern]

**Edge Cases**:
- No soft delete (use is_active flag instead)
- SWIFT and routing number can be NULL
- Country code must be exactly 2 characters

**Tests**:
- [ ] Test: Model instantiation with required fields
- [ ] Test: Default values applied (is_active=True)
- [ ] Test: Timestamps auto-populated

---

#### `src/schemas/financial_institution.py`

**Purpose**: Pydantic schemas for request/response validation

**Implementation**: [5 schema classes with validation]

**Edge Cases**:
- SWIFT code validation using schwifty library
- Routing number validation using pydantic-extra-types
- Country code validation using pydantic-extra-types
- URL validation for logo and website

**Tests**:
- [ ] Test: Valid data passes validation
- [ ] Test: Invalid SWIFT fails with clear error
- [ ] Test: Invalid routing number fails
- [ ] Test: Invalid country code fails

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Foundation & Data Model (Size: M, Priority: P0)

**Goal**: Establish database schema, enums, and ORM models to enable institution data storage

**Scope**:
- ✅ Include: InstitutionType enum, FinancialInstitution model, database migrations, seed data
- ❌ Exclude: API endpoints, business logic, validation beyond basic constraints

**Components to Implement**:
- [ ] InstitutionType enum in `src/models/enums.py`
- [ ] FinancialInstitution model in `src/models/financial_institution.py`
- [ ] Migration 1: Create institution_type enum
- [ ] Migration 2: Create financial_institutions table with indexes
- [ ] Migration 3: Seed 100+ institutions with accurate data

**Detailed Tasks**:

1. [ ] Add InstitutionType enum
   - Create enum class in `src/models/enums.py`
   - Add docstring with examples for each type
   - Implement `to_dict_list()` method
   - Write unit tests for enum

2. [ ] Create FinancialInstitution model
   - Define model class extending Base and TimestampMixin
   - Add all 11 columns with correct types and constraints
   - Add `__repr__` method
   - Write unit tests for model instantiation

3. [ ] Create enum migration
   - Generate migration: `uv run alembic revision -m "add institution type enum"`
   - Write upgrade: Create institution_type enum with 5 values
   - Write downgrade: Drop enum
   - Test migration forward and backward

4. [ ] Create table migration
   - Generate migration: `uv run alembic revision -m "create financial institutions table"`
   - Write upgrade: Create table with all columns
   - Add all 7 indexes (including partial unique indexes)
   - Add check constraints (country_code length, routing_number length, swift_code length)
   - Write downgrade: Drop table
   - Test migration forward and backward

5. [ ] Research and prepare seed data
   - Research SWIFT codes for international banks (Wikipedia, SWIFT.com)
   - Research ABA routing numbers for US banks (ABA.com, bank websites)
   - Compile list of 100+ institutions in JSON/Python dict format
   - Include: name, short_name, type, country, SWIFT, routing, logo URL, website URL
   - Verify data accuracy

6. [ ] Create seed migration
   - Generate migration: `uv run alembic revision -m "seed financial institutions"`
   - Write upgrade: Insert all institutions using `op.bulk_insert()`
   - Make idempotent (check if data exists before inserting)
   - Write downgrade: Delete seed data
   - Test seed migration

7. [ ] Verify schema
   - Run all migrations: `uv run alembic upgrade head`
   - Connect to database and verify table structure
   - Verify all indexes created
   - Verify seed data inserted
   - Query institutions to ensure data is correct

**Dependencies**:
- Requires: PostgreSQL 16+, Alembic installed
- Blocks: Phase 2 (cannot build API without database schema)

**Validation Criteria** (Phase complete when):
- [ ] All migrations run successfully without errors
- [ ] financial_institutions table exists with correct schema
- [ ] institution_type enum exists with 5 values
- [ ] All 7 indexes created successfully
- [ ] 100+ institutions seeded with accurate data
- [ ] Can query institutions from database
- [ ] Downgrade migrations work correctly
- [ ] All unit tests for enum and model pass

**Risk Factors**:
- **Risk**: Seed data research time-consuming
  - **Mitigation**: Start with 20-30 major institutions, expand iteratively
- **Risk**: SWIFT/routing number accuracy
  - **Mitigation**: Cross-reference multiple sources, mark uncertain data as needing review
- **Risk**: Partial unique index syntax issues
  - **Mitigation**: Test migration on local database first, review PostgreSQL docs

**Estimated Effort**: 2 days (1 developer)

---

#### Phase 2: Business Logic & Validation (Size: M, Priority: P0)

**Goal**: Implement repository and service layers with comprehensive validation

**Scope**:
- ✅ Include: Repository with custom queries, service with validation, audit logging integration
- ❌ Exclude: API endpoints (that's Phase 3)

**Components to Implement**:
- [ ] FinancialInstitutionRepository in `src/repositories/`
- [ ] FinancialInstitutionService in `src/services/`
- [ ] Pydantic schemas in `src/schemas/`
- [ ] Audit log integration (add new AuditAction values)

**Detailed Tasks**:

1. [ ] Install validation libraries
   - Add to `pyproject.toml`: `schwifty>=2023.11.0`, `pydantic-extra-types>=2.9.0`
   - Run `uv sync` to install dependencies
   - Verify imports work

2. [ ] Create Pydantic schemas
   - Create `src/schemas/financial_institution.py`
   - Implement 5 schema classes (Base, Create, Update, Response, ListItem)
   - Add SWIFT validation using schwifty
   - Add routing number validation using pydantic-extra-types
   - Add country code validation using pydantic-extra-types
   - Add URL validation for logo and website
   - Write unit tests for all schemas

3. [ ] Create repository
   - Create `src/repositories/financial_institution_repository.py`
   - Extend `BaseRepository[FinancialInstitution]`
   - Implement 7 custom methods (search, filter, get by SWIFT, get by routing, uniqueness checks, count)
   - Write unit tests for all repository methods
   - Write integration tests with real database

4. [ ] Create service
   - Create `src/services/financial_institution_service.py`
   - Implement 7 service methods (create, update, deactivate, get, list, validate SWIFT, validate routing)
   - Add SWIFT format validation using schwifty
   - Add routing number format validation
   - Add uniqueness checks before insert/update
   - Add audit logging for all state-changing operations
   - Write unit tests for all service methods
   - Write integration tests for complete flows

5. [ ] Add audit log enum values
   - Add `CREATE_FINANCIAL_INSTITUTION`, `UPDATE_FINANCIAL_INSTITUTION`, `DEACTIVATE_FINANCIAL_INSTITUTION` to `AuditAction` enum
   - Update migration to add these values to audit_action_enum (if needed)

6. [ ] Integration testing
   - Test create → retrieve → update → deactivate flow
   - Test validation errors (duplicate SWIFT, invalid format, etc.)
   - Test audit log entries created correctly
   - Test search and filtering queries
   - Verify all business rules enforced

**Dependencies**:
- Requires: Phase 1 complete (database schema exists)
- Blocks: Phase 3 (API needs service layer)

**Validation Criteria** (Phase complete when):
- [ ] Repository implements all 7 custom methods
- [ ] Service implements all 7 methods with validation
- [ ] SWIFT validation catches invalid formats (8/11 chars, alphanumeric)
- [ ] Routing number validation catches invalid checksums
- [ ] Uniqueness checks prevent duplicate SWIFT/routing numbers
- [ ] Audit log entries created for all state-changing operations
- [ ] All unit tests pass (80%+ coverage)
- [ ] All integration tests pass
- [ ] No database operations in service layer (all via repository)

**Risk Factors**:
- **Risk**: SWIFT validation library not working as expected
  - **Mitigation**: Test schwifty library thoroughly, have fallback regex validation
- **Risk**: Performance issues with search queries
  - **Mitigation**: Verify indexes are used (EXPLAIN ANALYZE), optimize queries if needed

**Estimated Effort**: 2 days (1 developer)

---

#### Phase 3: API Endpoints & Testing (Size: M, Priority: P0)

**Goal**: Expose financial institution functionality via REST API with full test coverage

**Scope**:
- ✅ Include: 5 API endpoints, authorization, integration tests, API documentation
- ❌ Exclude: Frontend integration (out of scope for backend)

**Components to Implement**:
- [ ] API routes in `src/api/routes/financial_institutions.py`
- [ ] Service dependency in `src/api/dependencies.py`
- [ ] Router registration in `src/main.py`
- [ ] Comprehensive integration tests

**Detailed Tasks**:

1. [ ] Create API routes file
   - Create `src/api/routes/financial_institutions.py`
   - Define router with prefix `/financial-institutions` and tag `["Financial Institutions"]`
   - Implement 5 endpoints (list, get by ID, create, update, deactivate)
   - Add OpenAPI documentation (summary, description, response models)
   - Use proper status codes (200, 201, 404, 409, 422)

2. [ ] Implement GET /api/v1/financial-institutions (list)
   - Query parameters: country_code, institution_type, search, skip, limit
   - Default: is_active=True, limit=20, skip=0
   - Response: Paginated list with metadata
   - No authentication required (public endpoint) OR require authenticated user (TBD)

3. [ ] Implement GET /api/v1/financial-institutions/{id} (details)
   - Path parameter: institution ID (UUID)
   - Response: Full institution details
   - Return 404 if not found
   - No authentication required (public endpoint) OR require authenticated user (TBD)

4. [ ] Implement POST /api/v1/financial-institutions (create)
   - Request body: FinancialInstitutionCreate schema
   - Authorization: Admin only (`require_admin` dependency)
   - Response: 201 Created with institution data
   - Validate uniqueness, format, etc. (via service)
   - Return 409 if duplicate SWIFT/routing

5. [ ] Implement PATCH /api/v1/financial-institutions/{id} (update)
   - Path parameter: institution ID (UUID)
   - Request body: FinancialInstitutionUpdate schema (partial)
   - Authorization: Admin only
   - Response: 200 OK with updated data
   - Return 404 if not found, 409 if duplicate

6. [ ] Implement DELETE /api/v1/financial-institutions/{id} (deactivate)
   - Path parameter: institution ID (UUID)
   - Authorization: Admin only
   - Response: 200 OK with success message
   - Sets is_active=False (soft delete)
   - Return 404 if not found

7. [ ] Add service dependency
   - Add `get_financial_institution_service()` to `src/api/dependencies.py`
   - Follow pattern from other service dependencies

8. [ ] Register router
   - Import router in `src/main.py`
   - Add to app: `app.include_router(financial_institutions.router, prefix="/api/v1")`

9. [ ] Write integration tests
   - Create `tests/integration/test_financial_institution_routes.py`
   - Test all 5 endpoints with various scenarios
   - Test authorization (admin vs. non-admin)
   - Test validation errors
   - Test pagination
   - Test search and filtering
   - Test error responses (404, 409, 422)
   - Aim for 100% coverage of API routes

10. [ ] Manual testing
    - Start dev server: `uv run uvicorn src.main:app --reload`
    - Open Swagger UI: http://localhost:8000/docs
    - Test all endpoints manually
    - Verify request/response formats
    - Verify error messages are user-friendly
    - Test with Postman or curl

11. [ ] Documentation
    - Update `docs/database-schema.md` with new table
    - Add API endpoint documentation to README (if applicable)
    - Ensure OpenAPI docs are complete and accurate

**Dependencies**:
- Requires: Phase 2 complete (service layer exists)
- Blocks: None (this is final phase)

**Validation Criteria** (Phase complete when):
- [ ] All 5 endpoints implemented and working
- [ ] Authorization enforced correctly (admin for create/update/delete)
- [ ] Request validation automatic via Pydantic
- [ ] Error responses have correct status codes and clear messages
- [ ] Swagger UI documents all endpoints with examples
- [ ] All integration tests pass
- [ ] Test coverage ≥ 80% for new code
- [ ] Manual testing confirms all endpoints work as expected
- [ ] Documentation updated

**Risk Factors**:
- **Risk**: Authorization issues (admin check not working)
  - **Mitigation**: Reuse existing `require_admin` dependency, test thoroughly
- **Risk**: Pagination edge cases
  - **Mitigation**: Test with empty results, large skip values, negative limits

**Estimated Effort**: 2 days (1 developer)

---

### 4.2 Implementation Sequence

```
Phase 1: Foundation & Data Model (P0, 2 days)
  ↓
Phase 2: Business Logic & Validation (P0, 2 days)
  ↓
Phase 3: API Endpoints & Testing (P0, 2 days)
```

**Rationale for ordering**:
- Phase 1 first because: Database schema must exist before building application logic
- Phase 2 depends on Phase 1 because: Cannot query institutions without table existing
- Phase 3 depends on Phase 2 because: API endpoints need service layer to delegate to
- Phases CANNOT run in parallel: Each phase builds on the previous one

**Total Estimated Effort**: 6 days (1 developer) or 3 days (2 developers working in sequence)

**Quick Wins**:
- After Phase 1: Database is ready, can manually query institutions via SQL
- After Phase 2: Business logic is complete, can use in Python scripts or tests
- After Phase 3: Full REST API available, can integrate with frontend

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Using a single table with an enum for institution types is simpler than a complex taxonomy system. No over-engineering with separate tables for countries, types, etc.

- [x] **Have we avoided premature optimization?**
  - Yes. Using standard indexes, no caching layer, no complex queries. Optimization can be added later if needed based on actual usage patterns.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows exact patterns from User model, UserRepository, UserService, user routes. Uses existing BaseRepository, existing dependencies, existing audit logging.

- [x] **Can we deliver value in smaller increments?**
  - Yes. Three clear phases: database → business logic → API. Each phase delivers standalone value.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. The feature description clearly identifies the problem (inconsistent bank names) and this solution directly addresses it with master data.

### Alternatives Considered

**Alternative 1: Store institution data in accounts table**
- **Description**: Continue storing bank names as free text in accounts table
- **Why not chosen**: Doesn't solve data inconsistency, no support for logos/metadata, doesn't scale internationally

**Alternative 2: Use external API for institution data**
- **Description**: Query external banking API (like Plaid, Finicity) for institution data
- **Why not chosen**: Adds external dependency, costs money, latency issues, doesn't work offline, vendor lock-in

**Alternative 3: Separate tables for countries, institution types**
- **Description**: Normalized design with separate reference tables
- **Why not chosen**: Over-engineering for this use case, adds complexity, JOIN queries slower, country codes are standard and rarely change

**Alternative 4: NoSQL document store for flexible schema**
- **Description**: Use MongoDB or similar for institution data
- **Why not chosen**: Rest of application uses PostgreSQL, adds complexity, ACID transactions needed for consistency, no benefit for structured data

**Rationale**: The proposed approach (single table with enum) is the simplest solution that meets all requirements while aligning with existing architecture patterns.

---

## 6. References & Related Documents

### External Resources

**Country Code Validation**:
- [Pydantic Extra Types - Country Validation](https://docs.pydantic.dev/latest/api/pydantic_extra_types_country/)
- [ISO 3166-1 alpha-2 on Wikipedia](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)

**SWIFT/BIC Code Validation**:
- [Schwifty Documentation - IBAN and BIC parsing](https://pythonhosted.org/schwifty/)
- [GitHub - mdomke/schwifty](https://github.com/mdomke/schwifty)
- [SWIFT Code Format Specification](https://www.iso.org/standard/60390.html)

**ABA Routing Number Validation**:
- [Pydantic Extra Types - Routing Numbers](https://docs.pydantic.dev/latest/api/pydantic_extra_types_routing_numbers/)
- [ABA Routing Number Format](https://en.wikipedia.org/wiki/ABA_routing_transit_number)

**PostgreSQL ENUM Best Practices**:
- [PostgreSQL ENUM Type Documentation](https://www.postgresql.org/docs/current/datatype-enum.html)
- [Alembic - Working with ENUMs](https://alembic.sqlalchemy.org/en/latest/cookbook.html#working-with-postgresql-enum-types)

**Financial Institution Data Sources** (for seed data research):
- [SWIFT Code Database](https://www.theswiftcodes.com/)
- [ABA Routing Number Lookup](https://www.aba.com/about-us/routing-number)
- [Wikipedia - List of largest banks](https://en.wikipedia.org/wiki/List_of_largest_banks)

### Internal Documentation

- Project CLAUDE.md: `/Users/danieltorres/Documents/emerald/emerald-backend/CLAUDE.md`
- Backend Standards: `.claude/standards/backend.md`
- Database Standards: `.claude/standards/database.md`
- API Standards: `.claude/standards/api.md`
- Testing Standards: `.claude/standards/testing.md`

### Related Design Documents

- Feature Description: `.features/descriptions/feat-01-financial-institutions.md`
- Database Schema Documentation: `docs/database-schema.md` (to be updated)
- Next Feature: `.features/descriptions/feat-02-link-accounts-to-institutions.md` (depends on this feature)

### Related Codebase Files

**Models to reference**:
- `src/models/user.py` - Pattern for model definition
- `src/models/enums.py` - Pattern for enum definition

**Repositories to reference**:
- `src/repositories/base.py` - Base repository to extend
- `src/repositories/user_repository.py` - Pattern for custom queries

**Services to reference**:
- `src/services/user_service.py` - Pattern for business logic and validation

**Routes to reference**:
- `src/api/routes/users.py` - Pattern for API endpoints and authorization

**Migrations to reference**:
- `alembic/versions/9cfdc3051d85_create_enums_and_extensions.py` - Pattern for creating enums

---

## Appendix: Seed Data Template

### Sample Seed Data Structure

```python
seed_institutions = [
    {
        "id": uuid.uuid4(),
        "name": "JPMorgan Chase Bank, N.A.",
        "short_name": "Chase",
        "institution_type": "bank",
        "country_code": "US",
        "swift_code": "CHASUS33",
        "routing_number": "021000021",
        "logo_url": "https://logo.clearbit.com/chase.com",
        "website_url": "https://www.chase.com",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    },
    {
        "id": uuid.uuid4(),
        "name": "Bank of America, N.A.",
        "short_name": "Bank of America",
        "institution_type": "bank",
        "country_code": "US",
        "swift_code": "BOFAUS3N",
        "routing_number": "026009593",
        "logo_url": "https://logo.clearbit.com/bankofamerica.com",
        "website_url": "https://www.bankofamerica.com",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    },
    # ... (98+ more institutions)
]
```

### Seed Data Checklist

For each institution, verify:
- [ ] Official name is accurate (check bank website)
- [ ] Short name is commonly used (check Google search results)
- [ ] Institution type is correct (bank, credit_union, brokerage, fintech, other)
- [ ] Country code is ISO 3166-1 alpha-2 (2 letters, uppercase)
- [ ] SWIFT code is accurate (8 or 11 characters, check SWIFT database)
- [ ] Routing number is accurate for US banks (9 digits, check ABA database)
- [ ] Logo URL is accessible (use Clearbit or similar service)
- [ ] Website URL is official domain

---

**End of Implementation Plan**

**Next Steps**:
1. Review this plan with team/stakeholders
2. Get approval to proceed
3. Begin Phase 1: Foundation & Data Model
4. Update this document with any changes or discoveries during implementation
