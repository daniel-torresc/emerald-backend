# Personal Finance Backend - Project Initialization Implementation Plan

**Date:** October 27, 2025
**Feature:** Complete backend system initialization and foundation
**Status:** Planning Phase
**Version:** 1.0

---

## Executive Summary

This plan outlines the complete implementation of a personal finance management backend system using modern Python technologies. The platform will provide comprehensive financial management capabilities including multi-account tracking, transaction categorization with flexible multi-taxonomy support, CSV import with intelligent duplicate detection, rule-based auto-categorization, analytics, and multi-user access with granular permissions.

### Primary Objectives

1. **Privacy-First Architecture**: Self-hosted solution that gives users complete control over their financial data
2. **Flexible Categorization**: Multi-taxonomy system allowing simultaneous categorization across multiple dimensions (Categories + Trips + Projects + People)
3. **Intelligent Automation**: Sophisticated rule engine with regex support for automatic transaction categorization
4. **Comprehensive Audit Trail**: Complete change history with 1-year retention for accountability and compliance
5. **Family-Friendly Sharing**: Granular permission system enabling safe account sharing with appropriate access levels

### Expected Outcomes

**Technical Outcomes:**
- Production-ready FastAPI backend with 80%+ test coverage
- Async-first architecture using SQLAlchemy 2.0 and asyncpg
- Comprehensive API documentation via OpenAPI/Swagger
- Docker-ready deployment configuration
- Database migration system with rollback capability

**Business Outcomes:**
- Support 1-5 concurrent users with sub-second response times
- Handle 100+ transactions per account per month without performance degradation
- Achieve 80%+ auto-categorization accuracy after initial training
- Zero data loss in normal operation
- Complete audit trail for all user actions

### Success Criteria

- ✓ All MUST HAVE features implemented and tested
- ✓ API response time p95 < 1 second
- ✓ CSV import of 500 transactions completes in < 30 seconds
- ✓ 80%+ code coverage for business logic
- ✓ All security best practices implemented (OWASP guidelines)
- ✓ Successfully onboard a new user with documentation alone
- ✓ Import real bank data without errors

---

## Research Context

### Key Research Findings

The research phase (documented in `.features/research/20251027_project-initialization.md`) revealed several critical insights:

**1. Market Opportunity**
- Mint shutdown (2024) displaced 15M+ users seeking alternatives
- Growing privacy concerns drive demand for self-hosted solutions
- Existing open-source tools lack modern Python architecture and flexible categorization
- Total addressable market: $78M-$157M in self-hosted segment

**2. Technical Architecture Decisions**
- **FastAPI + SQLAlchemy 2.0**: Modern async-first stack provides optimal performance
- **PostgreSQL Recursive CTEs**: Efficient solution for hierarchical taxonomies
- **Polars over Pandas**: 10-50x faster CSV processing for import operations
- **Custom Rule Engine**: Lightweight implementation preferred over heavyweight libraries
- **Application-Level Audit Logging**: More flexible than database-level pgAudit

**3. Competitive Differentiation**
- Multi-taxonomy categorization (unique in market)
- Advanced regex-based rule engine with retroactive application
- Comprehensive audit logging with user attribution
- Modern async Python architecture (vs PHP in Firefly III, Laravel in Financial Freedom)
- Granular account-level permissions (beyond basic multi-user)

**4. Critical Technical Challenges**
- Decimal precision for financial calculations (use `Decimal` throughout)
- Fuzzy matching for duplicate detection (balance precision vs false positives)
- Hierarchical taxonomy performance (recursive CTEs with proper indexing)
- Async complexity management (comprehensive testing required)
- CSV format diversity (extensible parser architecture)

### Research-Backed Recommendations

**Security (High Priority):**
- Use Argon2id for password hashing (preferred) or bcrypt as fallback
- Implement token refresh mechanism (15-min access, 7-day refresh)
- Rate limiting via SlowAPI: 5 login attempts/min, 100 API requests/min per user
- CORS with explicit allowed origins (no wildcards in production)

**Performance (Medium Priority):**
- asyncpg driver provides 10x performance over sync psycopg2
- Database connection pooling with proper sizing (10-20 connections for 1-5 users)
- Eager loading via joinedload/selectinload to prevent N+1 queries
- Pagination default 20 items, max 100 items

**Data Integrity (High Priority):**
- Use PostgreSQL NUMERIC(12, 2) for all monetary amounts
- Implement soft deletes with deleted_at timestamp
- Application-level audit logging in dedicated table
- Immutable audit logs (revoke UPDATE/DELETE permissions)

**Testing Strategy:**
- pytest-asyncio with function-level database isolation
- Use dependency_overrides for clean mocking
- Factory pattern (faker) for test data generation
- Target: 90% unit test coverage, 80% integration coverage

---

## Technical Architecture

### 3.1 System Design Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│                    (Future: React Frontend)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST API
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                           │
│  ┌────────────┬──────────────┬─────────────┬──────────────────┐ │
│  │ Middleware │ Auth Layer   │ Rate Limiter│ CORS Handler     │ │
│  └────────────┴──────────────┴─────────────┴──────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    API Routes Layer                          │ │
│  │  /auth  /users  /accounts  /transactions  /categories       │ │
│  │  /rules  /analytics  /import  /audit-logs                   │ │
│  └────────────────────────┬────────────────────────────────────┘ │
└───────────────────────────┼──────────────────────────────────────┘
                            │ Depends()
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service Layer (Business Logic)                │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────────┐ │
│  │ User Svc │ Auth Svc │ Acct Svc │ Txn Svc  │ Category Svc   │ │
│  │ Rule Svc │ Import   │ Analytics│ Audit Svc│ Permission Svc │ │
│  └──────────┴──────────┴──────────┴──────────┴────────────────┘ │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Repository Layer (Data Access)                      │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────────┐ │
│  │ User Repo│ Acct Repo│ Txn Repo │ Cat Repo │ Rule Repo      │ │
│  │ Import   │ Audit    │ Base Repo│          │                │ │
│  └──────────┴──────────┴──────────┴──────────┴────────────────┘ │
└───────────────────────────┼──────────────────────────────────────┘
                            │ SQLAlchemy 2.0 (async)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│  Tables: users, accounts, transactions, categories,              │
│          transaction_categories, categorization_rules,           │
│          import_batches, audit_logs, account_permissions         │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Principles:**

1. **Clean Architecture**: Strict separation of concerns across layers
2. **Dependency Inversion**: Routes → Services → Repositories (unidirectional)
3. **Framework Independence**: Business logic independent of FastAPI/SQLAlchemy
4. **Async-First**: All I/O operations use async/await patterns
5. **Repository Pattern**: Abstract all database operations behind interfaces

**Data Flow Example (Create Transaction):**

```
1. Client → POST /api/v1/transactions
2. Route Handler validates request (Pydantic schema)
3. Route calls TransactionService.create_transaction()
4. Service validates business rules (e.g., account exists, user has permission)
5. Service calls TransactionRepository.create()
6. Repository executes SQL INSERT via SQLAlchemy
7. Service logs audit entry via AuditService
8. Service applies auto-categorization rules via RuleEngine
9. Response flows back: Repository → Service → Route → Client
```

### 3.2 Technology Decisions

#### **FastAPI** (v0.115+)

**Purpose**: Primary API framework for all HTTP endpoints

**Why this choice:**
- Native async/await support built on Starlette ASGI
- Automatic OpenAPI documentation generation (Swagger UI)
- Pydantic integration for request/response validation
- Excellent performance (comparable to Node.js/Go)
- Strong typing with Python 3.13+ features
- Active development and strong community (78k+ GitHub stars)

**Version**: Latest stable (0.115+ as of Oct 2025)

**Alternatives considered:**
- Flask: Mature but lacks native async and auto-documentation
- Django REST Framework: Heavy, not async-first, steeper learning curve
- Verdict: FastAPI provides optimal balance of performance, developer experience, and modern features

#### **SQLAlchemy 2.0** + **asyncpg**

**Purpose**: Async ORM and PostgreSQL driver for all database operations

**Why this choice:**
- SQLAlchemy 2.0 new query API with improved type safety
- Native async support via AsyncSession
- asyncpg driver provides 10x performance over sync drivers
- Comprehensive ORM features (relationships, eager loading, migrations)
- Industry standard with extensive documentation

**Version**: SQLAlchemy 2.0+, asyncpg latest stable

**Alternatives considered:**
- psycopg2: Synchronous, blocks event loop, slower
- Django ORM: Tied to Django framework, less flexible
- Tortoise ORM: Less mature, smaller ecosystem
- Verdict: SQLAlchemy 2.0 + asyncpg is the gold standard for async Python

#### **Alembic** (v1.13+)

**Purpose**: Database migration management

**Why this choice:**
- Official migration tool for SQLAlchemy
- Autogenerate migrations from model changes
- Full async support in recent versions
- Rollback capabilities essential for production safety
- Version control for database schema

**Version**: Latest stable

**Alternatives considered:**
- Flyway: Java-based, not Python-native
- Manual SQL scripts: Error-prone, no version tracking
- Verdict: Alembic is the standard choice for SQLAlchemy projects

#### **Pydantic v2** + **Pydantic Settings**

**Purpose**: Data validation and configuration management

**Why this choice:**
- Built into FastAPI for request/response validation
- V2 offers significant performance improvements (5-50x faster)
- Type-safe configuration via Pydantic Settings
- Excellent validation error messages
- Computed fields and field validators

**Version**: Pydantic v2.x latest, Pydantic Settings latest

**Alternatives considered:**
- Marshmallow: Slower, not FastAPI-native
- Cerberus: Less feature-rich
- Verdict: Pydantic v2 is industry standard for FastAPI

#### **Polars** (v0.19+)

**Purpose**: High-performance CSV processing for transaction import

**Why this choice:**
- 10-50x faster than pandas for large CSVs
- Rust-based implementation for performance
- Lazy evaluation reduces memory usage
- Multi-threaded by default
- Modern API with better ergonomics

**Version**: Latest stable

**Alternatives considered:**
- pandas: Slower, higher memory usage, but more mature
- csv module: Too low-level for complex parsing
- Verdict: Polars provides necessary performance for 500+ transaction imports

#### **bcrypt** via **passlib**

**Purpose**: Password hashing

**Why this choice:**
- Battle-tested, widely adopted standard
- Configurable cost factor (use 12 for balance)
- Resistant to rainbow table and GPU attacks
- Passlib provides clean API

**Version**: Latest stable

**Alternatives considered:**
- Argon2id: Newer, slightly better, but bcrypt more proven
- PBKDF2: Older, less resistant to hardware attacks
- Verdict: bcrypt via passlib is the reliable choice (Argon2id for future consideration)

#### **PyJWT**

**Purpose**: JWT token generation and validation

**Why this choice:**
- Lightweight, focused on JWT specifically
- Active maintenance and security updates
- Support for multiple algorithms (HS256, RS256)
- Clean API for encoding/decoding

**Version**: Latest stable

**Alternatives considered:**
- python-jose: More features but heavier
- authlib: Full OAuth library, overkill for JWT-only
- Verdict: PyJWT provides exactly what's needed without bloat

#### **SlowAPI**

**Purpose**: Rate limiting for API endpoints

**Why this choice:**
- FastAPI-specific rate limiting library
- Simple decorator-based API
- Per-IP and per-user rate limiting
- Redis backend optional for distributed systems

**Version**: Latest stable

**Alternatives considered:**
- fastapi-limiter: Similar features, less active
- Custom middleware: Reinventing the wheel
- Verdict: SlowAPI is purpose-built for FastAPI

#### **pytest** + **pytest-asyncio** + **pytest-cov**

**Purpose**: Testing framework and coverage reporting

**Why this choice:**
- Industry standard for Python testing
- Excellent async support via pytest-asyncio
- Powerful fixture system
- Comprehensive coverage reporting
- Large ecosystem of plugins

**Version**: Latest stable versions

**Alternatives considered:**
- unittest: Less feature-rich, verbose syntax
- nose2: Less active development
- Verdict: pytest is the de facto standard

#### **uv**

**Purpose**: Dependency management and package installation

**Why this choice:**
- Project standard (per backend.md requirements)
- Fast Rust-based package installer
- Modern alternative to pip/poetry
- Lockfile support for reproducible builds

**Version**: Latest stable

**Alternatives considered:**
- pip: Slower, no built-in lockfile
- poetry: Slower than uv, more complex
- Verdict: uv is mandated by project standards

### 3.3 File Structure

```
emerald-backend/
├── alembic/                          # Database migrations
│   ├── versions/                     # Migration version files
│   │   └── {timestamp}_{description}.py
│   ├── env.py                        # Alembic environment config
│   └── script.py.mako                # Migration template
│
├── src/
│   ├── api/                          # API layer (HTTP interface)
│   │   ├── routes/                   # Endpoint definitions ONLY
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # POST /login, /register, /refresh, /logout
│   │   │   ├── users.py              # GET/PATCH /me, POST /me/password
│   │   │   ├── accounts.py           # CRUD + POST /{id}/share, /{id}/import
│   │   │   ├── transactions.py       # CRUD + POST /search, /{id}/split
│   │   │   ├── categories.py         # CRUD for hierarchical taxonomies
│   │   │   ├── rules.py              # CRUD + POST /{id}/apply (retroactive)
│   │   │   ├── analytics.py          # GET /spending-by-category, /trends
│   │   │   ├── import_csv.py         # POST /import (CSV processing)
│   │   │   └── audit_logs.py         # GET / (with filters)
│   │   └── dependencies.py           # Shared dependencies (get_current_user, etc.)
│   │
│   ├── services/                     # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py           # Authentication logic, token management
│   │   ├── user_service.py           # User CRUD, password changes
│   │   ├── account_service.py        # Account CRUD, sharing, balance calculation
│   │   ├── transaction_service.py    # Transaction CRUD, splitting, validation
│   │   ├── category_service.py       # Taxonomy management, hierarchy operations
│   │   ├── rule_service.py           # Rule CRUD, application logic
│   │   ├── rule_engine.py            # Core rule matching engine
│   │   ├── import_service.py         # CSV processing, duplicate detection
│   │   ├── analytics_service.py      # Spending analysis, trend calculations
│   │   ├── audit_service.py          # Audit log creation and querying
│   │   └── permission_service.py     # Authorization checks, access control
│   │
│   ├── repositories/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py                   # Generic CRUD repository
│   │   ├── user_repository.py        # User database operations
│   │   ├── account_repository.py     # Account database operations
│   │   ├── transaction_repository.py # Transaction database operations
│   │   ├── category_repository.py    # Category/taxonomy operations + CTEs
│   │   ├── rule_repository.py        # Rule database operations
│   │   ├── import_repository.py      # Import batch tracking
│   │   ├── audit_repository.py       # Audit log operations
│   │   └── permission_repository.py  # Account permission operations
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                   # Base model with common fields
│   │   ├── mixins.py                 # Timestamp, soft delete mixins
│   │   ├── user.py                   # User model
│   │   ├── account.py                # Account model
│   │   ├── transaction.py            # Transaction model (+ split relationships)
│   │   ├── category.py               # Category model (self-referential)
│   │   ├── transaction_category.py   # Many-to-many association
│   │   ├── rule.py                   # Categorization rule model
│   │   ├── import_batch.py           # CSV import tracking
│   │   ├── audit_log.py              # Audit log model (immutable)
│   │   └── account_permission.py     # Account sharing permissions
│   │
│   ├── schemas/                      # Pydantic schemas (validation)
│   │   ├── __init__.py
│   │   ├── user.py                   # UserCreate, UserUpdate, UserResponse
│   │   ├── auth.py                   # LoginRequest, TokenResponse, RefreshRequest
│   │   ├── account.py                # AccountCreate, AccountUpdate, AccountResponse
│   │   ├── transaction.py            # TransactionCreate, Update, Response, Split
│   │   ├── category.py               # CategoryCreate, Update, Response, Tree
│   │   ├── rule.py                   # RuleCreate, Update, Response, Apply
│   │   ├── analytics.py              # AnalyticsRequest, SpendingResponse, TrendResponse
│   │   ├── import_csv.py             # ImportRequest, ColumnMapping, ImportResponse
│   │   ├── audit_log.py              # AuditLogResponse, AuditQuery
│   │   └── common.py                 # Pagination, ErrorResponse, SuccessResponse
│   │
│   ├── core/                         # Core configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic Settings (env vars)
│   │   ├── security.py               # Password hashing, JWT utilities
│   │   ├── database.py               # Async engine, session management
│   │   ├── logging.py                # Logging configuration
│   │   └── constants.py              # App-wide constants (roles, permissions)
│   │
│   ├── utils/                        # Utility functions
│   │   ├── __init__.py
│   │   ├── decimal_utils.py          # Decimal precision helpers
│   │   ├── fuzzy_matcher.py          # Duplicate detection logic
│   │   └── date_utils.py             # Date/time utilities
│   │
│   ├── exceptions.py                 # Custom exception hierarchy
│   ├── middleware.py                 # Custom middleware (correlation ID, logging)
│   └── main.py                       # FastAPI app initialization
│
├── tests/
│   ├── unit/                         # Fast, isolated tests
│   │   ├── services/
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_transaction_service.py
│   │   │   ├── test_rule_engine.py
│   │   │   └── ...
│   │   ├── repositories/
│   │   │   └── test_category_repository.py (CTE logic)
│   │   └── utils/
│   │       ├── test_decimal_utils.py
│   │       └── test_fuzzy_matcher.py
│   │
│   ├── integration/                  # Database + business logic
│   │   ├── test_transaction_import.py
│   │   ├── test_rule_application.py
│   │   ├── test_account_sharing.py
│   │   └── test_audit_logging.py
│   │
│   ├── e2e/                          # Full API tests
│   │   ├── test_auth_flow.py
│   │   ├── test_transaction_crud.py
│   │   ├── test_csv_import_flow.py
│   │   └── test_analytics_api.py
│   │
│   ├── fixtures/                     # Test data
│   │   ├── sample_transactions.csv
│   │   └── factories.py              # Factory pattern for test data
│   │
│   └── conftest.py                   # Shared pytest fixtures
│
├── docs/                             # Documentation
│   ├── architecture/
│   │   ├── ADR-001-tech-stack.md     # Architecture decision records
│   │   ├── ADR-002-multi-taxonomy.md
│   │   └── database-schema.md
│   ├── api/
│   │   └── examples.md               # API usage examples
│   └── deployment/
│       ├── docker-setup.md
│       └── production-checklist.md
│
├── logs/                             # Log files (gitignored)
│   ├── app.log
│   └── error.log
│
├── .env.example                      # Example environment variables
├── .env                              # Actual env vars (gitignored)
├── .gitignore
├── .pre-commit-config.yaml           # Pre-commit hooks config
├── alembic.ini                       # Alembic configuration
├── docker-compose.yml                # Development environment
├── Dockerfile                        # Production container
├── logging_config.yaml               # Logging configuration
├── pyproject.toml                    # Project metadata + dependencies
├── uv.lock                           # Locked dependencies
└── README.md                         # Project documentation
```

**Directory Purpose Explanations:**

- **alembic/**: Database version control - all schema changes tracked here
- **src/api/routes/**: HTTP layer only - request validation, response formatting
- **src/services/**: Business logic - all rules, calculations, workflows
- **src/repositories/**: Data access - all SQL queries, database operations
- **src/models/**: Database schema - SQLAlchemy ORM models
- **src/schemas/**: API contracts - Pydantic validation schemas
- **src/core/**: Configuration - settings, security, database connection
- **tests/**: Three-tier testing - unit (fast), integration (DB), e2e (full API)

---

## Implementation Specification

### 4.1 Component Breakdown

This section details the implementation requirements for each major component of the system. Components are organized by functional domain.

---

#### Component: **Authentication & User Management**

**Files Involved:**
- `src/api/routes/auth.py` - Auth endpoints
- `src/api/routes/users.py` - User management endpoints
- `src/services/auth_service.py` - Authentication business logic
- `src/services/user_service.py` - User management business logic
- `src/repositories/user_repository.py` - User data access
- `src/models/user.py` - User database model
- `src/schemas/auth.py` - Auth request/response schemas
- `src/schemas/user.py` - User schemas
- `src/core/security.py` - Password hashing, JWT utilities

**Purpose**: Handle user registration, authentication, authorization, and profile management

**Implementation Requirements:**

1. **Core Logic**:
   - Implement user registration with email/password
   - Hash passwords using bcrypt (cost factor 12)
   - Generate JWT access tokens (15-min expiry) and refresh tokens (7-day expiry)
   - Validate tokens on protected endpoints
   - Implement token refresh mechanism
   - Store refresh tokens in database with user association
   - Implement logout by invalidating refresh tokens
   - Support password change with old password verification
   - Implement role-based access control (admin, user roles)

2. **Data Handling**:
   - **Input validation**:
     - Email: valid format, unique in database
     - Password: minimum 8 chars, uppercase, lowercase, digit, special char
     - Username: 3-50 chars, alphanumeric + underscore/hyphen
   - **Expected input formats**:
     - Registration: `{email, username, password, password_confirm}`
     - Login: `{email, password}`
     - Refresh: `{refresh_token}`
   - **Output format**:
     - Token response: `{access_token, refresh_token, token_type, expires_in}`
     - User response: `{id, email, username, role, created_at}` (no password)
   - **State management**:
     - Track user status (active, inactive, locked)
     - Track failed login attempts for rate limiting
     - Store refresh tokens with expiry

3. **Edge Cases & Error Handling**:
   - [ ] Handle duplicate email registration (409 Conflict)
   - [ ] Handle invalid credentials (401 Unauthorized)
   - [ ] Handle expired tokens (401 with specific error code)
   - [ ] Handle invalid token signatures (401)
   - [ ] Handle account lockout after 5 failed attempts in 15 minutes
   - [ ] Handle password validation failures (422 Unprocessable Entity)
   - [ ] Handle concurrent login attempts
   - [ ] Handle token refresh with expired refresh token

4. **Dependencies**:
   - Internal: AuditService (log auth events), PermissionService
   - External: bcrypt (passlib), PyJWT, Pydantic validators

5. **Testing Requirements**:
   - [ ] Unit test: Password hashing is not reversible
   - [ ] Unit test: Valid password passes validation
   - [ ] Unit test: Invalid passwords fail validation with specific errors
   - [ ] Unit test: JWT token generation includes correct claims
   - [ ] Unit test: JWT token validation rejects expired tokens
   - [ ] Integration test: User registration creates database record
   - [ ] Integration test: Login with valid credentials returns tokens
   - [ ] Integration test: Login with invalid credentials fails
   - [ ] Integration test: Token refresh extends session
   - [ ] Integration test: Logout invalidates refresh token
   - [ ] E2E test: Complete registration → login → access protected endpoint → refresh → logout flow

**Acceptance Criteria**:
- [ ] Users can register with email and password
- [ ] Passwords are hashed and never stored in plain text
- [ ] Users can log in and receive JWT tokens
- [ ] Access tokens expire after 15 minutes
- [ ] Refresh tokens work for 7 days
- [ ] Failed login attempts are rate-limited (5/15min)
- [ ] All auth events are logged in audit trail
- [ ] Token validation happens on every protected endpoint
- [ ] Users can change their password

**Implementation Notes**:
- Use FastAPI's `Depends()` for authentication dependency injection
- Create `get_current_user` dependency for protected routes
- Store refresh tokens in database for revocation capability
- Implement correlation ID in auth logs for tracking
- Use HTTP-only cookies for refresh tokens (more secure than localStorage)

---

#### Component: **Account Management**

**Files Involved:**
- `src/api/routes/accounts.py`
- `src/services/account_service.py`
- `src/services/permission_service.py`
- `src/repositories/account_repository.py`
- `src/repositories/permission_repository.py`
- `src/models/account.py`
- `src/models/account_permission.py`
- `src/schemas/account.py`

**Purpose**: Manage bank accounts, calculate balances, and handle account sharing with permissions

**Implementation Requirements:**

1. **Core Logic**:
   - Create accounts with type (checking, savings, credit card, etc.), currency, opening balance
   - Calculate current balance from transaction history
   - Support multiple accounts per user
   - Implement account sharing with owner/editor/viewer roles
   - Allow account owners to revoke access from other users
   - Soft delete accounts (mark deleted_at, keep transaction history)
   - Validate user permissions before any account operations

2. **Data Handling**:
   - **Input validation**:
     - Account name: 1-100 chars, required
     - Account type: enum (checking, savings, credit_card, debit_card, loan, investment)
     - Currency: ISO 4217 code (USD, EUR, GBP, etc.)
     - Opening balance: Decimal, default 0.00
   - **Expected input formats**:
     - Create: `{name, type, currency, opening_balance?, description?}`
     - Share: `{user_id, permission_level}` where permission_level in [owner, editor, viewer]
   - **Output format**:
     - Account response: `{id, name, type, currency, current_balance, opening_balance, created_at, updated_at, permissions: [{user_id, permission_level}]}`
   - **State management**:
     - Current balance calculated on-demand from transactions
     - Cache balance in account table (updated via trigger on transaction changes)
     - Track account status (active, closed, deleted)

3. **Edge Cases & Error Handling**:
   - [ ] Handle account access by unauthorized user (403 Forbidden)
   - [ ] Handle sharing with non-existent user (404 Not Found)
   - [ ] Handle duplicate sharing (user already has access)
   - [ ] Handle owner trying to remove themselves (prevent orphaned account)
   - [ ] Handle balance calculation with no transactions (return opening_balance)
   - [ ] Handle account deletion with existing transactions (soft delete only)
   - [ ] Handle permission inheritance (editor can't grant owner permission)
   - [ ] Handle currency mismatch in transaction import

4. **Dependencies**:
   - Internal: PermissionService, TransactionRepository (for balance), AuditService
   - External: None specific

5. **Testing Requirements**:
   - [ ] Unit test: Balance calculation with mixed debit/credit transactions
   - [ ] Unit test: Permission validation for different roles (owner/editor/viewer)
   - [ ] Unit test: Soft delete preserves transaction history
   - [ ] Integration test: Create account and verify database record
   - [ ] Integration test: Share account and verify permission created
   - [ ] Integration test: Revoke access and verify permission removed
   - [ ] Integration test: Calculate balance matches sum of transactions
   - [ ] Integration test: User can only access accounts they own or have permission for
   - [ ] E2E test: Create account → add transactions → verify balance → share with user → revoke access

**Acceptance Criteria**:
- [ ] Users can create multiple accounts with different types and currencies
- [ ] Account balances are calculated accurately from transactions
- [ ] Account owners can share accounts with specific permission levels
- [ ] Shared users see accounts in their account list
- [ ] Viewers can read but not modify account data
- [ ] Editors can add/edit transactions but not share account
- [ ] Owners can revoke access at any time
- [ ] Deleted accounts don't appear in queries but preserve history
- [ ] All permission changes are audited

**Implementation Notes**:
- Use database trigger to update account.current_balance on transaction insert/update/delete
- Implement permission checks as a dependency: `Depends(check_account_permission(AccountPermission.EDITOR))`
- Cache balance to avoid recalculation on every request
- Consider PostgreSQL materialized view for complex balance queries

---

#### Component: **Transaction Management**

**Files Involved:**
- `src/api/routes/transactions.py`
- `src/services/transaction_service.py`
- `src/repositories/transaction_repository.py`
- `src/models/transaction.py`
- `src/models/transaction_category.py`
- `src/schemas/transaction.py`

**Purpose**: Handle transaction CRUD, categorization, splitting, and search/filtering

**Implementation Requirements:**

1. **Core Logic**:
   - Create transactions manually or via CSV import
   - Store operation date, value date, amount (Decimal), currency, description, merchant
   - Support transaction types (debit, credit, transfer, etc.)
   - Implement transaction splitting (parent-child relationship)
   - Assign multiple categories from different taxonomies to single transaction
   - Support user comments/notes separate from description
   - Implement free-form tags
   - Track who created/modified each transaction
   - Soft delete transactions
   - Implement search with fuzzy matching

2. **Data Handling**:
   - **Input validation**:
     - Amount: Decimal, required, non-zero
     - Currency: must match account currency
     - Operation date: date format, required
     - Description: 1-500 chars
     - Merchant: 0-200 chars, optional
     - Split amounts: must sum to parent amount
   - **Expected input formats**:
     - Create: `{account_id, operation_date, value_date?, amount, currency, description, merchant?, type, tags?, categories?, comment?}`
     - Split: `{splits: [{amount, description, categories?, tags?}]}`
   - **Output format**:
     - Transaction response: `{id, account_id, operation_date, value_date, amount, currency, description, merchant, type, categories: [{id, name, taxonomy_type}], tags, comment, created_by, created_at, updated_at, parent_id?, children?: [...]}`
   - **State management**:
     - Track split relationships (parent_id references parent transaction)
     - Maintain category assignments in junction table
     - Store original description + merchant separately

3. **Edge Cases & Error Handling**:
   - [ ] Handle transaction creation for account user doesn't have access to (403)
   - [ ] Handle amount with more than 2 decimal places (round to 2)
   - [ ] Handle currency mismatch with account (400 Bad Request)
   - [ ] Handle split with amounts not summing to parent (422 Validation Error)
   - [ ] Handle splitting an already-split transaction (prevent nested splits)
   - [ ] Handle category assignment to non-existent category (404)
   - [ ] Handle deletion of transaction with split children (delete or prevent)
   - [ ] Handle search with no results (return empty array, not error)
   - [ ] Handle concurrent updates to same transaction (optimistic locking)

4. **Dependencies**:
   - Internal: AccountService (verify access), CategoryService (validate categories), RuleEngine (auto-categorization), AuditService
   - External: fuzzywuzzy (search)

5. **Testing Requirements**:
   - [ ] Unit test: Decimal precision maintained through calculations
   - [ ] Unit test: Split amounts validation (must equal parent)
   - [ ] Unit test: Fuzzy search matches typos
   - [ ] Unit test: Date range filtering works correctly
   - [ ] Integration test: Create transaction updates account balance
   - [ ] Integration test: Assign multiple categories to transaction
   - [ ] Integration test: Split transaction creates children with parent reference
   - [ ] Integration test: Delete transaction soft-deletes record
   - [ ] Integration test: Search by description returns relevant results
   - [ ] Integration test: Filter by date range, amount range, categories works
   - [ ] E2E test: Create → categorize → split → search → delete transaction flow

**Acceptance Criteria**:
- [ ] Transactions store all required fields accurately
- [ ] Decimal precision is maintained (no floating-point errors)
- [ ] Transactions can be assigned to multiple categories from different taxonomies
- [ ] Transaction splitting maintains amount integrity
- [ ] Split transactions reference parent correctly
- [ ] Search returns relevant results with fuzzy matching
- [ ] Filtering by date range, amount range, categories works
- [ ] All transaction operations are audited
- [ ] Soft-deleted transactions don't appear in queries
- [ ] Transaction creation/modification triggers account balance update

**Implementation Notes**:
- Use PostgreSQL NUMERIC(12, 2) for amount storage
- Create Decimal from strings to avoid floating-point errors: `Decimal('19.99')`
- Implement search as separate endpoint: `POST /api/v1/transactions/search` with filter criteria
- Use SQLAlchemy's `relationship()` for parent-child split relationship
- Index: account_id, operation_date, deleted_at for query performance
- Consider full-text search index on description + merchant for faster search

---

#### Component: **Hierarchical Taxonomy & Categorization**

**Files Involved:**
- `src/api/routes/categories.py`
- `src/services/category_service.py`
- `src/repositories/category_repository.py`
- `src/models/category.py`
- `src/schemas/category.py`

**Purpose**: Manage hierarchical taxonomies (primary categories + secondary taxonomies like trips, projects) and category assignments

**Implementation Requirements:**

1. **Core Logic**:
   - Support multiple independent taxonomies (primary, trips, projects, people, etc.)
   - Implement 2-level hierarchy (parent → child) using adjacency list
   - Provide predefined primary categories (Income, Expenses, etc.)
   - Allow users to create custom categories in any taxonomy
   - Prevent deletion of predefined categories
   - Prevent deletion of categories in use
   - Allow users to show/hide predefined categories
   - Retrieve full category tree using PostgreSQL recursive CTEs
   - Support moving categories within hierarchy

2. **Data Handling**:
   - **Input validation**:
     - Name: 1-100 chars, required, unique within taxonomy + parent
     - Taxonomy type: enum (primary, trips, projects, people, etc.)
     - Parent ID: must exist in same taxonomy, prevent circular references
     - Is predefined: boolean, cannot be changed after creation
   - **Expected input formats**:
     - Create: `{name, taxonomy_type, parent_id?, description?, color?, icon?}`
     - Update: `{name?, description?, color?, icon?, is_active?}`
   - **Output format**:
     - Category response: `{id, name, taxonomy_type, parent_id, is_predefined, is_active, description, color, icon, level, path: [ancestor_ids], children?: [...]}`
     - Tree response: Nested structure with children
   - **State management**:
     - Track hierarchy using parent_id (self-referential foreign key)
     - Calculate level and path on query (via CTE)
     - Track active/inactive status for hiding

3. **Edge Cases & Error Handling**:
   - [ ] Handle circular reference in hierarchy (prevent A → B → A)
   - [ ] Handle deletion of category with children (cascade or prevent)
   - [ ] Handle deletion of category in use by transactions (prevent)
   - [ ] Handle updating predefined category (only allow name/description)
   - [ ] Handle category depth > 2 levels (prevent or allow based on decision)
   - [ ] Handle duplicate names within same parent (prevent)
   - [ ] Handle orphaned categories (parent deleted) - shouldn't happen with FK constraint
   - [ ] Handle recursive CTE performance with large trees (10,000+ categories)

4. **Dependencies**:
   - Internal: TransactionRepository (check category usage), AuditService
   - External: None specific

5. **Testing Requirements**:
   - [ ] Unit test: Recursive CTE retrieves full tree correctly
   - [ ] Unit test: Level calculation works for nested categories
   - [ ] Unit test: Path array contains all ancestors
   - [ ] Unit test: Circular reference detection prevents invalid hierarchies
   - [ ] Integration test: Create category with parent creates correct hierarchy
   - [ ] Integration test: Delete category in use is prevented
   - [ ] Integration test: Retrieve category tree returns nested structure
   - [ ] Integration test: Hide category removes from user's view
   - [ ] Integration test: Move category updates all descendants
   - [ ] E2E test: Create taxonomy → add categories → assign to transaction → verify hierarchy

**Acceptance Criteria**:
- [ ] Users can create custom categories in any taxonomy
- [ ] Hierarchies support 2 levels (configurable if needed)
- [ ] Category trees are retrieved efficiently via recursive CTEs
- [ ] Predefined categories cannot be deleted
- [ ] Categories in use cannot be deleted
- [ ] Users can hide predefined categories
- [ ] Multiple taxonomies work independently
- [ ] Category paths and levels are calculated correctly
- [ ] All category operations are audited

**Implementation Notes**:
- Use PostgreSQL recursive CTE for tree queries (example in research doc)
- Index parent_id and taxonomy_type for performance
- Consider materialized path (ltree extension) if tree queries become slow
- Implement cascade logic carefully: delete category → reassign or prevent if transactions exist
- Cache category trees in memory for frequently accessed taxonomies
- SQL for recursive query:
  ```sql
  WITH RECURSIVE category_tree AS (
    SELECT id, name, parent_id, 1 AS level, ARRAY[id] AS path
    FROM categories WHERE parent_id IS NULL AND taxonomy_type = 'primary'
    UNION ALL
    SELECT c.id, c.name, c.parent_id, ct.level + 1, ct.path || c.id
    FROM categories c
    INNER JOIN category_tree ct ON c.parent_id = ct.id
  )
  SELECT * FROM category_tree ORDER BY path;
  ```

---

#### Component: **Rule Engine & Auto-Categorization**

**Files Involved:**
- `src/api/routes/rules.py`
- `src/services/rule_service.py`
- `src/services/rule_engine.py`
- `src/repositories/rule_repository.py`
- `src/models/rule.py`
- `src/schemas/rule.py`

**Purpose**: Automatic transaction categorization based on user-defined keyword and regex rules

**Implementation Requirements:**

1. **Core Logic**:
   - Create rules with keyword or regex matchers
   - Match against transaction description + merchant fields
   - Support case-insensitive matching
   - Execute rules in priority order
   - Support account-specific rules or global rules
   - Enable/disable rules without deletion
   - Assign one or multiple categories per rule
   - Support retroactive application to existing transactions
   - Preview rule application before executing (dry-run mode)
   - Stop on first match or collect all matches (configurable)

2. **Data Handling**:
   - **Input validation**:
     - Name: 1-100 chars, descriptive rule name
     - Matcher type: enum (keyword, regex)
     - Matcher config: JSON with keywords array or regex pattern
     - Categories: array of category IDs (must exist)
     - Priority: integer, higher = earlier execution
     - Account IDs: array (empty = all accounts)
   - **Expected input formats**:
     - Create: `{name, matcher_type, matcher_config: {keywords: []} | {pattern: ''}, category_ids: [], priority, enabled, account_ids?}`
     - Apply: `{transaction_ids?: [], account_ids?: [], dry_run: bool}`
   - **Output format**:
     - Rule response: `{id, name, matcher_type, matcher_config, category_ids, priority, enabled, account_ids, created_at}`
     - Apply result: `{transactions_matched: int, categories_assigned: int, preview?: [{transaction_id, matched_categories}]}`
   - **State management**:
     - Store matcher config as JSONB for flexibility
     - Track rule application history (optional)
     - Compile regex patterns on rule load (cache)

3. **Edge Cases & Error Handling**:
   - [ ] Handle invalid regex pattern (compile error → 400 Bad Request)
   - [ ] Handle rule matching no transactions (return 0 matches, not error)
   - [ ] Handle rule assigning to deleted category (prevent or cascade)
   - [ ] Handle conflicting rules (multiple rules match same transaction)
   - [ ] Handle rule priority ties (use ID as tiebreaker)
   - [ ] Handle retroactive application to 10,000+ transactions (batch processing)
   - [ ] Handle rule matching transaction from account user doesn't own (skip)
   - [ ] Handle special regex characters in keywords (escape properly)

4. **Dependencies**:
   - Internal: TransactionRepository, CategoryService, AuditService
   - External: re (Python regex), fuzzywuzzy (optional for fuzzy keyword matching)

5. **Testing Requirements**:
   - [ ] Unit test: Keyword matcher matches case-insensitively
   - [ ] Unit test: Regex matcher matches pattern correctly
   - [ ] Unit test: Rules execute in priority order
   - [ ] Unit test: Stop-on-first-match prevents multiple rule application
   - [ ] Unit test: Account-specific rules only apply to correct accounts
   - [ ] Integration test: Create rule and apply to transaction auto-categorizes
   - [ ] Integration test: Retroactive application categorizes existing transactions
   - [ ] Integration test: Dry-run mode doesn't modify transactions
   - [ ] Integration test: Disabled rules don't apply
   - [ ] Integration test: Multiple categories assigned when rule specifies
   - [ ] E2E test: Create rule → import transactions → verify auto-categorization → edit rule → reapply

**Acceptance Criteria**:
- [ ] Users can create keyword and regex-based rules
- [ ] Rules match against description and merchant fields
- [ ] Rules execute in priority order
- [ ] Rules can be enabled/disabled without deletion
- [ ] Rules can assign multiple categories
- [ ] Rules can be account-specific or global
- [ ] Retroactive application works for existing transactions
- [ ] Dry-run mode allows preview before applying
- [ ] Invalid regex patterns are rejected with helpful errors
- [ ] All rule applications are audited

**Implementation Notes**:
- Implement as Protocol-based design (research example in doc)
- Compile regex patterns once and cache in memory
- For retroactive application, batch process transactions (e.g., 100 at a time) to avoid memory issues
- Consider rule engine architecture:
  ```python
  class RuleMatcher(Protocol):
      def matches(self, transaction: Transaction) -> bool: ...

  class KeywordMatcher:
      keywords: List[str]
      case_sensitive: bool = False

  class RegexMatcher:
      pattern: str
      compiled: re.Pattern

  class RuleEngine:
      rules: List[CategorizationRule]  # sorted by priority

      def apply_rules(self, transaction, stop_on_first=True) -> List[int]:
          # Return category IDs to assign
  ```
- Index: user_id, enabled for fast rule retrieval
- Log each rule application for debugging

---

#### Component: **CSV Import & Duplicate Detection**

**Files Involved:**
- `src/api/routes/import_csv.py`
- `src/services/import_service.py`
- `src/repositories/import_repository.py`
- `src/models/import_batch.py`
- `src/schemas/import_csv.py`
- `src/utils/fuzzy_matcher.py`

**Purpose**: Import transactions from bank CSV files with column mapping, duplicate detection, and rollback capability

**Implementation Requirements:**

1. **Core Logic**:
   - Parse CSV files using Polars for performance
   - Allow user to map CSV columns to transaction fields
   - Save column mappings per bank for reuse
   - Detect duplicates using hash-based exact match + fuzzy matching
   - Present duplicates to user with skip/import/merge options
   - Apply auto-categorization rules during import (optional)
   - Bulk insert transactions with import_batch_id
   - Track import metadata (filename, row count, success/failure)
   - Support import rollback (soft delete all transactions from batch)
   - Validate CSV data before importing (atomic operation)

2. **Data Handling**:
   - **Input validation**:
     - File: CSV format, max size 10MB
     - Column mapping: Required fields (date, amount, description)
     - Account ID: must exist and user must have editor permission
     - Duplicate strategy: enum (skip, import_anyway, merge)
   - **Expected input formats**:
     - Import: `multipart/form-data` with CSV file + `{account_id, column_mapping: {date: 'Transaction Date', amount: 'Amount', description: 'Description', ...}, apply_rules: bool, duplicate_strategy: 'skip'}`
   - **Output format**:
     - Preview: `{rows_parsed: int, sample_transactions: [5], duplicates_detected: int, duplicates: [{csv_row, existing_transaction_id, similarity_score}]}`
     - Result: `{import_batch_id, total_rows, successful_rows, skipped_rows, failed_rows, status}`
   - **State management**:
     - Two-phase import: 1) Parse & detect duplicates (preview), 2) Confirm & import
     - Track import batch in database for rollback
     - Store column mappings for reuse

3. **Edge Cases & Error Handling**:
   - [ ] Handle malformed CSV (missing columns, invalid encoding) → 400 Bad Request
   - [ ] Handle empty CSV → 422 Validation Error
   - [ ] Handle file size > 10MB → 413 Payload Too Large
   - [ ] Handle invalid date formats (provide format hints) → validation error
   - [ ] Handle amount parsing errors (commas, currency symbols) → auto-clean
   - [ ] Handle duplicate detection timeout (>500 transactions) → batch processing
   - [ ] Handle partial import failure (rollback entire batch)
   - [ ] Handle concurrent imports to same account (queue or lock)
   - [ ] Handle CSV with no matching column headers → user must map manually

4. **Dependencies**:
   - Internal: TransactionService, RuleEngine (optional), AccountService (permission check), AuditService
   - External: polars (CSV parsing), fuzzywuzzy (duplicate detection)

5. **Testing Requirements**:
   - [ ] Unit test: CSV parsing extracts correct fields
   - [ ] Unit test: Duplicate detection identifies exact matches (100% similarity)
   - [ ] Unit test: Duplicate detection identifies fuzzy matches (>90% similarity)
   - [ ] Unit test: Column mapping transforms CSV rows to transaction objects
   - [ ] Unit test: Amount parsing handles various formats ($1,234.56, 1234.56, etc.)
   - [ ] Integration test: Import CSV creates transactions in database
   - [ ] Integration test: Duplicate detection prevents reimporting same transactions
   - [ ] Integration test: Rollback deletes all transactions from batch
   - [ ] Integration test: Auto-categorization applies during import
   - [ ] Integration test: Import updates account balance correctly
   - [ ] E2E test: Upload CSV → preview → confirm → verify transactions → rollback

**Acceptance Criteria**:
- [ ] CSV files up to 10MB are processed successfully
- [ ] Column mapping allows flexible CSV format support
- [ ] Duplicate detection identifies both exact and fuzzy matches
- [ ] Import is atomic (all or nothing on failure)
- [ ] Import batch tracking enables rollback
- [ ] Auto-categorization can be applied during import
- [ ] Import completes in < 30 seconds for 500 transactions
- [ ] User receives clear error messages for invalid data
- [ ] All imports are audited with metadata

**Implementation Notes**:
- Use Polars for CSV parsing (10-50x faster than pandas):
  ```python
  import polars as pl
  df = pl.read_csv(file, encoding='utf-8')
  ```
- Duplicate detection algorithm:
  1. Hash-based exact match: `hash(date + amount + description)` → O(n) lookup
  2. Fuzzy match: fuzzywuzzy ratio on description for same date/amount → O(n²) but partitioned by date
- Implement two-phase commit: preview returns potential duplicates, user confirms, then import
- Store import_batch_id on transactions for rollback: `UPDATE transactions SET deleted_at = NOW() WHERE import_batch_id = ?`
- Index: import_batch_id for fast rollback queries
- Consider using background task for large imports (FastAPI BackgroundTasks)
- Save column mappings in user preferences or separate table for reuse

---

#### Component: **Analytics & Reporting**

**Files Involved:**
- `src/api/routes/analytics.py`
- `src/services/analytics_service.py`
- `src/repositories/transaction_repository.py` (aggregate queries)
- `src/schemas/analytics.py`

**Purpose**: Generate financial insights including spending by category, trends over time, and income vs expenses

**Implementation Requirements:**

1. **Core Logic**:
   - Calculate total spending by category (primary and secondary taxonomies)
   - Calculate spending trends over time (daily, weekly, monthly, yearly)
   - Support custom date ranges
   - Calculate income vs expenses breakdown
   - Support filtering by account, category, date range, amount range
   - Handle multi-currency accounts (convert to base currency)
   - Calculate month-over-month and year-over-year comparisons
   - Calculate percentage changes between periods
   - Generate account balance history over time

2. **Data Handling**:
   - **Input validation**:
     - Date range: start_date, end_date (ISO format)
     - Group by: enum (day, week, month, year)
     - Account IDs: array (empty = all accessible accounts)
     - Category IDs: array (empty = all)
     - Base currency: ISO 4217 code
   - **Expected input formats**:
     - Analytics query: `{start_date, end_date, account_ids?, category_ids?, group_by: 'month', base_currency?: 'USD'}`
   - **Output format**:
     - Spending by category: `{categories: [{category_id, category_name, total_amount, percentage, transaction_count}], total_spending}`
     - Trends: `{periods: [{period_start, period_end, income, expenses, net, transaction_count}]}`
     - Comparison: `{current_period: {...}, previous_period: {...}, change_amount, change_percentage}`
   - **State management**:
     - Calculate on-demand (no caching for MVP)
     - Use database aggregation (SUM, GROUP BY) for performance

3. **Edge Cases & Error Handling**:
   - [ ] Handle date range with no transactions → return zero amounts, not error
   - [ ] Handle empty account list → return 400 Bad Request
   - [ ] Handle invalid date range (start > end) → 422 Validation Error
   - [ ] Handle multi-currency without base currency specified → require or use account currency
   - [ ] Handle division by zero in percentage calculations (previous period = 0)
   - [ ] Handle large date ranges (>5 years) → warn or limit
   - [ ] Handle category tree aggregation (include child categories)
   - [ ] Handle deleted transactions (exclude from calculations)

4. **Dependencies**:
   - Internal: TransactionRepository (aggregate queries), CategoryService (tree traversal), AccountService (permission checks)
   - External: None specific (currency conversion API for future)

5. **Testing Requirements**:
   - [ ] Unit test: Spending calculation sums correctly
   - [ ] Unit test: Percentage calculation handles zero denominator
   - [ ] Unit test: Date grouping (monthly) groups correctly
   - [ ] Unit test: Income vs expenses categorization is correct
   - [ ] Integration test: Spending by category matches transaction data
   - [ ] Integration test: Trends over time reflect actual transaction dates
   - [ ] Integration test: Filtering by account returns correct subset
   - [ ] Integration test: Multi-currency aggregation (future)
   - [ ] E2E test: Request analytics → verify calculations → filter by category → verify subset

**Acceptance Criteria**:
- [ ] Spending by category calculates accurately
- [ ] Trends over time group by specified period correctly
- [ ] Income vs expenses breakdown is accurate
- [ ] Filtering by account, category, date range works
- [ ] Percentage calculations handle edge cases (zero, negative)
- [ ] Analytics queries complete in < 2 seconds for 10,000 transactions
- [ ] Multi-currency support (convert to base currency)
- [ ] All calculations use Decimal precision

**Implementation Notes**:
- Use database aggregation for performance:
  ```sql
  SELECT c.id, c.name, SUM(t.amount) as total
  FROM transactions t
  JOIN transaction_categories tc ON t.id = tc.transaction_id
  JOIN categories c ON tc.category_id = c.id
  WHERE t.account_id = ANY($account_ids)
    AND t.operation_date BETWEEN $start_date AND $end_date
    AND t.deleted_at IS NULL
  GROUP BY c.id, c.name
  ORDER BY total DESC;
  ```
- For category tree aggregation, use recursive CTE to get all descendant categories, then SUM
- Consider caching analytics results in Redis for frequently requested ranges (future optimization)
- Handle Decimal precision: all amounts as Decimal, format to 2 decimal places for display
- For multi-currency, integrate with external API (exchangerate-api.com) or manual rate entry (future)

---

#### Component: **Audit Logging**

**Files Involved:**
- `src/api/routes/audit_logs.py`
- `src/services/audit_service.py`
- `src/repositories/audit_repository.py`
- `src/models/audit_log.py`
- `src/schemas/audit_log.py`

**Purpose**: Comprehensive audit trail for all user actions, data modifications, and permission changes

**Implementation Requirements:**

1. **Core Logic**:
   - Log all user authentication events (login, logout, failed attempts)
   - Log all data modifications (create, update, delete) with old and new values
   - Log permission changes (account sharing, role modifications)
   - Log rule creation/updates and application
   - Log CSV imports with metadata
   - Log category/taxonomy changes
   - Include user attribution (who), timestamp (when), action type, entity type, entity ID
   - Store before/after state as JSONB
   - Make audit logs immutable (no UPDATE/DELETE permissions)
   - Retain logs for minimum 1 year

2. **Data Handling**:
   - **Input validation**:
     - Query filters: user_id, action_type, entity_type, start_date, end_date
   - **Expected input formats**:
     - Query: `{user_id?, action_type?, entity_type?, start_date?, end_date?, page, page_size}`
   - **Output format**:
     - Audit log: `{id, user_id, action_type, entity_type, entity_id, old_values, new_values, metadata, ip_address, user_agent, created_at}`
     - List response: Paginated with metadata
   - **State management**:
     - Write-only table (no updates after creation)
     - Index on user_id, entity_type, created_at for query performance
     - Partition by month for large datasets (future optimization)

3. **Edge Cases & Error Handling**:
   - [ ] Handle audit log write failure (don't block main operation, log error)
   - [ ] Handle large old_values/new_values (truncate or store reference)
   - [ ] Handle sensitive data in audit logs (exclude passwords, tokens)
   - [ ] Handle audit log query with no results (return empty array)
   - [ ] Handle audit log retention (archive after 1 year)
   - [ ] Handle concurrent audit log writes (database handles with transactions)
   - [ ] Handle audit log disk space (monitor and alert)

4. **Dependencies**:
   - Internal: Used by all services (UserService, AccountService, etc.)
   - External: None specific

5. **Testing Requirements**:
   - [ ] Unit test: Audit log creation includes all required fields
   - [ ] Unit test: Sensitive data is excluded from logs
   - [ ] Integration test: User action creates audit log entry
   - [ ] Integration test: Audit logs are immutable (update fails)
   - [ ] Integration test: Query audit logs by user returns correct entries
   - [ ] Integration test: Query audit logs by date range filters correctly
   - [ ] E2E test: Perform action → verify audit log created → query logs → verify details

**Acceptance Criteria**:
- [ ] All user actions are logged automatically
- [ ] Audit logs include who, what, when, and before/after state
- [ ] Audit logs are immutable after creation
- [ ] Sensitive data is excluded from logs
- [ ] Users can query their own audit logs
- [ ] Admins can query all audit logs
- [ ] Audit logs are retained for 1+ years
- [ ] Audit log writes don't block main operations

**Implementation Notes**:
- Implement via SQLAlchemy event listeners:
  ```python
  @event.listens_for(Session, 'before_flush')
  def audit_log_changes(session, flush_context, instances):
      for obj in session.new:
          if hasattr(obj, '__auditable__'):
              create_audit_log('CREATE', obj, old=None, new=obj.to_dict())
  ```
- Revoke UPDATE/DELETE permissions from application database user:
  ```sql
  REVOKE UPDATE, DELETE ON audit_logs FROM app_user;
  ```
- Exclude sensitive fields in to_dict() method:
  ```python
  def to_dict(self, exclude_sensitive=True):
      data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
      if exclude_sensitive:
          data.pop('password_hash', None)
          data.pop('refresh_token', None)
      return data
  ```
- Use JSONB for old_values/new_values for flexible schema
- Add indexes: `CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);`
- Consider partitioning by month for > 1M audit logs

---

## Implementation Roadmap

### Phase Breakdown

Given the comprehensive scope, the implementation is divided into 5 phases with clear dependencies and validation criteria. Each phase delivers working, tested functionality.

---

#### Phase 1: Foundation & Authentication (Size: L, Priority: P0)

**Duration**: 2-3 weeks
**Goal**: Establish project structure, database foundation, and secure authentication system

**Scope**:
- ✅ Include:
  - Complete project setup with uv, FastAPI, SQLAlchemy 2.0
  - Database configuration with PostgreSQL + asyncpg
  - Alembic migration system
  - User model with authentication
  - JWT-based auth system (access + refresh tokens)
  - Password hashing with bcrypt
  - Basic error handling and logging
  - Testing infrastructure (pytest + fixtures)
  - Development Docker environment

- ❌ Exclude:
  - Account management (Phase 2)
  - Transaction features (Phase 2)
  - Import functionality (Phase 3)
  - Analytics (Phase 4)

**Components to Implement:**
- [ ] Project structure setup
- [ ] Core configuration (Settings, logging, database)
- [ ] User model and repository
- [ ] Authentication service and routes
- [ ] Security utilities (password hashing, JWT)
- [ ] Base repository pattern
- [ ] Custom exceptions
- [ ] Middleware (correlation ID, logging)
- [ ] Health check endpoint

**Detailed Tasks:**

1. [ ] **Initialize project structure**
   - Run `uv init` to create project
   - Create directory structure per backend standards
   - Set up `.gitignore`, `.env.example`
   - Create `pyproject.toml` with dependencies
   - Run `uv add` for all required packages
   - Run `uv lock` to generate lockfile

2. [ ] **Configure core infrastructure**
   - Create `src/core/config.py` with PydanticSettings
   - Create `src/core/database.py` with async engine and session
   - Create `src/core/logging.py` with structured logging configuration
   - Create `logging_config.yaml` with console and file handlers
   - Create `src/core/security.py` with password and JWT utilities
   - Create `src/core/constants.py` for app-wide constants

3. [ ] **Set up database with Alembic**
   - Run `alembic init alembic`
   - Configure `alembic.ini` for async migrations
   - Update `alembic/env.py` for async operation
   - Create base model: `src/models/base.py` with id, created_at, updated_at
   - Create mixins: `src/models/mixins.py` for timestamps and soft delete
   - Create `users` table migration with all required fields

4. [ ] **Implement authentication system**
   - Create `src/models/user.py` (User model with password_hash, role, etc.)
   - Create `src/repositories/base.py` (generic CRUD repository)
   - Create `src/repositories/user_repository.py` (user-specific queries)
   - Create `src/schemas/auth.py` (LoginRequest, TokenResponse, etc.)
   - Create `src/schemas/user.py` (UserCreate, UserResponse, etc.)
   - Create `src/services/auth_service.py` (registration, login, token logic)
   - Create `src/services/user_service.py` (user management)
   - Create `src/api/dependencies.py` (get_current_user dependency)
   - Create `src/api/routes/auth.py` (POST /register, /login, /refresh, /logout)
   - Create `src/api/routes/users.py` (GET/PATCH /me, POST /me/password)

5. [ ] **Set up error handling and middleware**
   - Create `src/exceptions.py` with custom exception classes
   - Implement global exception handler in `src/main.py`
   - Create `src/middleware.py` with correlation ID middleware
   - Configure CORS middleware
   - Add logging middleware for request/response

6. [ ] **Initialize testing infrastructure**
   - Create `tests/conftest.py` with shared fixtures
   - Create test database fixture (async)
   - Create test client fixture (httpx AsyncClient)
   - Create user factory for test data
   - Write unit tests for auth_service (password hashing, token generation)
   - Write integration tests for user_repository (CRUD operations)
   - Write E2E tests for auth routes (registration → login → refresh → logout)

7. [ ] **Configure development environment**
   - Create `docker-compose.yml` with PostgreSQL service
   - Create `.env.example` with all required environment variables
   - Create `README.md` with setup instructions
   - Document API endpoints in route docstrings
   - Configure pre-commit hooks (Black, Ruff, MyPy)

8. [ ] **Implement health check**
   - Create GET `/health` endpoint (always 200)
   - Create GET `/health/ready` endpoint (checks database connection)
   - Include version, build info in health response

**Dependencies**: None (first phase)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (minimum 80% coverage)
- [ ] User registration creates account successfully
- [ ] Login returns valid JWT tokens
- [ ] Token refresh extends session
- [ ] Protected endpoints require authentication
- [ ] Database migrations run successfully (up and down)
- [ ] Docker environment starts cleanly
- [ ] Pre-commit hooks run without errors
- [ ] Health check endpoints work
- [ ] Logging captures all requests with correlation IDs

**Risk Factors**:
- Async SQLAlchemy configuration complexity → Mitigation: Use official examples, comprehensive testing
- JWT security vulnerabilities → Mitigation: Follow OWASP guidelines, use established libraries

**Estimated Effort**: 2-3 weeks for 1 developer

---

#### Phase 2: Core Features - Accounts & Transactions (Size: L, Priority: P0)

**Duration**: 3-4 weeks
**Goal**: Implement account management, transaction CRUD, hierarchical categories, and basic audit logging

**Scope**:
- ✅ Include:
  - Account model and CRUD operations
  - Account sharing with permissions (owner/editor/viewer)
  - Transaction model with all fields
  - Transaction CRUD operations
  - Transaction splitting functionality
  - Hierarchical category/taxonomy system (recursive CTEs)
  - Multi-taxonomy support (primary + secondary)
  - Category assignment to transactions
  - Basic audit logging for all operations
  - Decimal precision for financial amounts

- ❌ Exclude:
  - CSV import (Phase 3)
  - Auto-categorization rules (Phase 3)
  - Analytics (Phase 4)
  - Advanced search (Phase 3)

**Components to Implement:**
- [ ] Account management with permissions
- [ ] Transaction management
- [ ] Hierarchical taxonomies
- [ ] Multi-category assignment
- [ ] Audit logging system
- [ ] Balance calculation

**Detailed Tasks:**

1. [ ] **Implement account system**
   - Create `src/models/account.py` (Account model)
   - Create `src/models/account_permission.py` (permission junction table)
   - Create migration for accounts and permissions tables
   - Create `src/repositories/account_repository.py`
   - Create `src/repositories/permission_repository.py`
   - Create `src/schemas/account.py` (AccountCreate, Update, Response)
   - Create `src/services/account_service.py` (CRUD + balance calculation)
   - Create `src/services/permission_service.py` (authorization checks)
   - Create `src/api/routes/accounts.py` (CRUD + POST /{id}/share)
   - Implement balance calculation from transactions
   - Add database trigger to update account balance on transaction changes
   - Write tests for account CRUD and permission checks

2. [ ] **Implement transaction system**
   - Create `src/models/transaction.py` (Transaction model with split support)
   - Create migration for transactions table
   - Create `src/repositories/transaction_repository.py`
   - Create `src/schemas/transaction.py` (TransactionCreate, Update, Response, Split)
   - Create `src/services/transaction_service.py` (CRUD + splitting logic)
   - Create `src/api/routes/transactions.py` (CRUD + POST /{id}/split)
   - Create `src/utils/decimal_utils.py` (Decimal helpers)
   - Implement transaction splitting with parent-child relationships
   - Validate split amounts sum to parent amount
   - Write tests for transaction operations including splits

3. [ ] **Implement hierarchical taxonomies**
   - Create `src/models/category.py` (Category model with self-referential FK)
   - Create `src/models/transaction_category.py` (many-to-many association)
   - Create migration for categories and transaction_categories tables
   - Create `src/repositories/category_repository.py` with recursive CTE queries
   - Create `src/schemas/category.py` (CategoryCreate, Update, Response, Tree)
   - Create `src/services/category_service.py` (CRUD + tree operations)
   - Create `src/api/routes/categories.py`
   - Implement recursive CTE for tree retrieval
   - Support multiple independent taxonomies (primary, trips, projects, etc.)
   - Seed predefined primary categories
   - Prevent deletion of categories in use
   - Write tests for category hierarchy operations

4. [ ] **Implement audit logging**
   - Create `src/models/audit_log.py` (Audit log model)
   - Create migration for audit_logs table with immutability constraints
   - Create `src/repositories/audit_repository.py`
   - Create `src/schemas/audit_log.py` (AuditLogResponse, AuditQuery)
   - Create `src/services/audit_service.py` (log creation and querying)
   - Create `src/api/routes/audit_logs.py` (GET / with filters)
   - Implement SQLAlchemy event listeners for automatic logging
   - Integrate audit logging into all services
   - Ensure sensitive data is excluded from logs
   - Write tests for audit log creation and querying

5. [ ] **Implement category assignment**
   - Add category assignment logic to transaction service
   - Support multiple categories from different taxonomies
   - Add category removal from transactions
   - Update transaction response schema to include categories
   - Write tests for multi-taxonomy assignment

6. [ ] **Integration and testing**
   - Write integration tests for complete workflows:
     - Create account → add transaction → assign categories → verify balance
     - Share account → verify permissions → revoke access
     - Split transaction → verify parent-child relationship → verify balance
   - Write E2E tests for all routes
   - Verify audit logs are created for all operations
   - Test Decimal precision with edge cases

**Dependencies**: Phase 1 (authentication and infrastructure)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (80%+ coverage)
- [ ] Users can create and manage multiple accounts
- [ ] Account sharing with permissions works correctly
- [ ] Transactions store all required fields with Decimal precision
- [ ] Transaction splitting maintains amount integrity
- [ ] Category hierarchies work with recursive CTEs
- [ ] Multiple categories can be assigned to transactions
- [ ] Audit logs capture all operations
- [ ] Account balances calculate correctly from transactions
- [ ] Database migrations are reversible
- [ ] No performance issues with 1,000+ transactions

**Risk Factors**:
- Recursive CTE performance with large category trees → Mitigation: Proper indexing, consider ltree for future
- Decimal precision errors → Mitigation: Comprehensive unit tests, use string input for Decimal creation
- Complex permission logic → Mitigation: Clear permission service, thorough testing

**Estimated Effort**: 3-4 weeks for 1 developer

---

#### Phase 3: Automation - CSV Import & Rules (Size: L, Priority: P1)

**Duration**: 2-3 weeks
**Goal**: Enable transaction import from CSV files and automatic categorization via rules

**Scope**:
- ✅ Include:
  - CSV upload and parsing (Polars)
  - Column mapping configuration
  - Duplicate detection (hash + fuzzy matching)
  - Import preview with duplicate resolution
  - Import batch tracking and rollback
  - Rule engine implementation (keyword + regex)
  - Rule CRUD and priority management
  - Retroactive rule application
  - Auto-categorization during import
  - Transaction search with fuzzy matching

- ❌ Exclude:
  - Analytics (Phase 4)
  - Multi-currency conversion (Phase 4)
  - Advanced rule types (future)

**Components to Implement:**
- [ ] CSV import service
- [ ] Duplicate detection
- [ ] Rule engine
- [ ] Auto-categorization
- [ ] Transaction search

**Detailed Tasks:**

1. [ ] **Implement CSV parsing and column mapping**
   - Install and configure Polars: `uv add polars`
   - Create `src/models/import_batch.py` (import tracking model)
   - Create migration for import_batches table
   - Add import_batch_id to transactions table
   - Create `src/repositories/import_repository.py`
   - Create `src/schemas/import_csv.py` (ImportRequest, ColumnMapping, ImportResponse)
   - Create `src/services/import_service.py` (CSV parsing logic)
   - Implement Polars-based CSV parsing
   - Implement column mapping (user-configurable)
   - Handle various CSV formats and encodings
   - Validate CSV data before import
   - Write tests for CSV parsing with various formats

2. [ ] **Implement duplicate detection**
   - Create `src/utils/fuzzy_matcher.py` (duplicate detection algorithms)
   - Install fuzzywuzzy: `uv add fuzzywuzzy python-Levenshtein`
   - Implement hash-based exact match (date + amount + description)
   - Implement fuzzy matching for similar transactions
   - Create duplicate resolution UI contract (skip/import/merge)
   - Write tests for duplicate detection accuracy

3. [ ] **Implement import workflow**
   - Create `src/api/routes/import_csv.py` (POST /api/v1/accounts/{id}/import)
   - Implement two-phase import: preview → confirm
   - Store import batch metadata
   - Link transactions to import batch
   - Implement import rollback (soft delete batch transactions)
   - Handle import errors gracefully (atomic operation)
   - Write integration tests for complete import flow
   - Write E2E tests for CSV upload → preview → confirm → rollback

4. [ ] **Implement rule engine**
   - Create `src/models/rule.py` (Categorization rule model)
   - Create migration for categorization_rules table
   - Create `src/repositories/rule_repository.py`
   - Create `src/schemas/rule.py` (RuleCreate, Update, Response, Apply)
   - Create `src/services/rule_engine.py` (matching logic)
   - Implement KeywordMatcher and RegexMatcher classes
   - Implement priority-based rule execution
   - Support account-specific and global rules
   - Implement enable/disable without deletion
   - Write tests for rule matching logic

5. [ ] **Implement rule management and application**
   - Create `src/services/rule_service.py` (CRUD + application logic)
   - Create `src/api/routes/rules.py` (CRUD + POST /{id}/apply)
   - Implement retroactive rule application
   - Implement dry-run mode for preview
   - Integrate rule engine with import service
   - Handle rule conflicts (multiple matches)
   - Write integration tests for rule application
   - Write E2E tests for create rule → apply → verify categorization

6. [ ] **Implement transaction search**
   - Add search endpoint: POST /api/v1/transactions/search
   - Implement fuzzy matching on description/merchant
   - Support filtering by date range, amount range, categories, tags
   - Support multiple combined filters
   - Implement pagination for search results
   - Write tests for search functionality

**Dependencies**: Phase 2 (accounts, transactions, categories)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (80%+ coverage)
- [ ] CSV import handles 500+ transactions in < 30 seconds
- [ ] Duplicate detection identifies exact and fuzzy matches
- [ ] Import is atomic (all or nothing on failure)
- [ ] Import rollback removes all batch transactions
- [ ] Rules match transactions correctly (keyword and regex)
- [ ] Rules execute in priority order
- [ ] Retroactive rule application works for existing transactions
- [ ] Auto-categorization applies during import
- [ ] Search returns relevant results with fuzzy matching
- [ ] Column mappings can be saved and reused
- [ ] Import errors provide clear, actionable messages

**Risk Factors**:
- CSV format diversity → Mitigation: Extensible parser, user feedback for new formats
- Fuzzy matching false positives → Mitigation: Configurable threshold, user review required
- Performance with large imports → Mitigation: Batch processing, background tasks

**Estimated Effort**: 2-3 weeks for 1 developer

---

#### Phase 4: Analytics & Polish (Size: M, Priority: P1)

**Duration**: 2 weeks
**Goal**: Provide financial insights, multi-currency support, and production-ready features

**Scope**:
- ✅ Include:
  - Spending analytics by category
  - Spending trends over time
  - Income vs expenses breakdown
  - Custom date range support
  - Filtering by account, category, date
  - Month-over-month and year-over-year comparisons
  - Multi-currency support (conversion to base currency)
  - Rate limiting (SlowAPI)
  - Security hardening (headers, CORS, validation)
  - API documentation improvements

- ❌ Exclude:
  - Advanced forecasting (future)
  - Budget tracking (future)
  - Report export (PDF, Excel) (future)

**Components to Implement:**
- [ ] Analytics service and routes
- [ ] Multi-currency conversion
- [ ] Rate limiting
- [ ] Security enhancements
- [ ] API documentation

**Detailed Tasks:**

1. [ ] **Implement analytics calculations**
   - Create `src/schemas/analytics.py` (AnalyticsRequest, SpendingResponse, TrendResponse)
   - Create `src/services/analytics_service.py` (calculation logic)
   - Create `src/api/routes/analytics.py`
   - Implement spending by category (with hierarchy aggregation)
   - Implement spending trends over time (daily/weekly/monthly/yearly)
   - Implement income vs expenses breakdown
   - Implement custom date range support
   - Implement filtering by account, category, amount
   - Write tests for analytics calculations

2. [ ] **Implement comparisons and insights**
   - Implement month-over-month comparison
   - Implement year-over-year comparison
   - Calculate percentage changes between periods
   - Handle edge cases (division by zero, etc.)
   - Write tests for comparison logic

3. [ ] **Implement multi-currency support**
   - Add base_currency field to user preferences
   - Integrate with currency exchange API (or manual rate entry for MVP)
   - Implement currency conversion in analytics calculations
   - Handle conversion accuracy (4+ decimal places for rates)
   - Write tests for multi-currency calculations

4. [ ] **Implement rate limiting**
   - Install SlowAPI: `uv add slowapi`
   - Configure rate limiter in `src/main.py`
   - Apply rate limits to sensitive endpoints:
     - Login: 5 attempts/15 minutes per IP
     - API endpoints: 100 requests/minute per user
     - CSV import: 10 uploads/hour per user
     - Analytics: 50 requests/minute per user
   - Add rate limit headers to responses
   - Write tests for rate limiting behavior

5. [ ] **Security hardening**
   - Add security headers middleware (CSP, X-Frame-Options, etc.)
   - Review and strengthen CORS configuration
   - Add request size limits
   - Implement file upload validation (type, size, content)
   - Review all endpoints for authorization checks
   - Run security scanner (Bandit)
   - Address any security findings

6. [ ] **Improve API documentation**
   - Add detailed docstrings to all endpoints
   - Add request/response examples to schemas using Pydantic Field
   - Document error responses for each endpoint
   - Document authentication requirements
   - Document rate limits
   - Create API usage examples in `docs/api/examples.md`
   - Verify Swagger UI is complete and accurate

**Dependencies**: Phase 3 (transactions, categories, import)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (80%+ coverage)
- [ ] Analytics queries complete in < 2 seconds for 10,000 transactions
- [ ] Spending by category calculations are accurate
- [ ] Trends over time reflect actual transaction data
- [ ] Multi-currency conversion works correctly
- [ ] Rate limiting blocks excessive requests
- [ ] Security headers are present in all responses
- [ ] CORS is configured with explicit allowed origins
- [ ] API documentation is complete and accurate
- [ ] No security vulnerabilities found in scan

**Risk Factors**:
- Analytics performance with large datasets → Mitigation: Database aggregation, proper indexing
- Currency conversion API availability → Mitigation: Fallback to manual rate entry for MVP

**Estimated Effort**: 2 weeks for 1 developer

---

#### Phase 5: Production Ready (Size: M, Priority: P0)

**Duration**: 1-2 weeks
**Goal**: Ensure production readiness with comprehensive testing, deployment configuration, and documentation

**Scope**:
- ✅ Include:
  - Comprehensive E2E testing
  - Performance testing and optimization
  - Database query optimization (EXPLAIN ANALYZE)
  - Production Docker configuration
  - Deployment documentation
  - Database backup/restore procedures
  - Monitoring and observability setup
  - Error handling review
  - Security review and penetration testing
  - Load testing

- ❌ Exclude:
  - CI/CD pipeline (can be added post-MVP)
  - Advanced monitoring (Prometheus, Grafana) (future enhancement)

**Components to Implement:**
- [ ] Production deployment
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Monitoring

**Detailed Tasks:**

1. [ ] **Complete E2E test coverage**
   - Write E2E tests for all critical user flows:
     - Registration → login → create account → import CSV → categorize → analytics → logout
     - Account sharing workflow
     - Rule creation and application workflow
     - Transaction splitting workflow
   - Test all error scenarios
   - Test edge cases
   - Achieve 80%+ overall code coverage

2. [ ] **Performance testing and optimization**
   - Run load tests with k6 or Locust (simulate 5 concurrent users)
   - Identify slow queries with EXPLAIN ANALYZE
   - Add database indexes where needed
   - Optimize N+1 query issues
   - Verify API response times meet targets (p95 < 1 second)
   - Test CSV import with 500+ transactions
   - Optimize analytics queries if needed

3. [ ] **Production Docker configuration**
   - Create production `Dockerfile` with multi-stage build
   - Create production `docker-compose.yml`
   - Create `docker-entrypoint.sh` for migration automation
   - Create `.dockerignore` file
   - Configure non-root user for security
   - Add health check to Dockerfile
   - Document Docker deployment in `docs/deployment/docker-setup.md`

4. [ ] **Database and backup procedures**
   - Document backup strategy (pg_dump)
   - Create backup scripts
   - Document restore procedure
   - Test backup and restore
   - Document migration rollback procedure
   - Create production database checklist

5. [ ] **Monitoring and observability**
   - Implement Prometheus metrics endpoint (optional for MVP)
   - Configure structured logging for production
   - Set up log rotation (10MB max, 5 backups)
   - Document monitoring approach
   - Create runbook for common issues

6. [ ] **Security review**
   - Run Bandit security scanner: `uv add --dev bandit`
   - Run dependency vulnerability check: `uv add --dev safety`
   - Review all authentication and authorization code
   - Review all input validation
   - Review error messages for information leakage
   - Test SQL injection vectors (should be protected by SQLAlchemy)
   - Test XSS vectors
   - Document security best practices for deployment

7. [ ] **Documentation completion**
   - Update README.md with complete setup instructions
   - Document all environment variables in `.env.example`
   - Create architecture documentation in `docs/architecture/`
   - Document database schema with ER diagram
   - Create API usage guide with examples
   - Document deployment procedures
   - Create troubleshooting guide
   - Document testing procedures

8. [ ] **Final integration testing**
   - Run full test suite on production-like environment
   - Verify all migrations work forward and backward
   - Test with real bank CSV files
   - Onboard a test user with documentation only
   - Verify all acceptance criteria from all phases

**Dependencies**: Phases 1-4 (all features implemented)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (80%+ coverage achieved)
- [ ] Load testing shows acceptable performance (5 concurrent users)
- [ ] All API endpoints respond in < 1 second (p95)
- [ ] CSV import of 500 transactions completes in < 30 seconds
- [ ] Docker deployment works end-to-end
- [ ] Database backup and restore procedures tested
- [ ] Security scan shows no critical vulnerabilities
- [ ] Documentation allows new user to set up and use system
- [ ] All production checklist items completed
- [ ] Zero known critical bugs

**Risk Factors**:
- Undiscovered performance issues → Mitigation: Comprehensive load testing
- Security vulnerabilities → Mitigation: Multiple security reviews and scanning

**Estimated Effort**: 1-2 weeks for 1 developer

---

### Implementation Sequence

```
Phase 1 (P0, 2-3 weeks): Foundation & Authentication
  ↓
Phase 2 (P0, 3-4 weeks): Core Features (Accounts & Transactions)
  ↓
Phase 3 (P1, 2-3 weeks): Automation (CSV Import & Rules)
  ↓
Phase 4 (P1, 2 weeks): Analytics & Polish
  ↓
Phase 5 (P0, 1-2 weeks): Production Ready
```

**Total Estimated Timeline**: 10-14 weeks (2.5-3.5 months) for 1 developer

**Rationale for ordering**:

- **Phase 1 first**: Establishes foundation (auth, database, project structure) required by all other phases
- **Phase 2 next**: Core domain models (accounts, transactions, categories) are prerequisites for automation and analytics
- **Phase 3 after Phase 2**: Import and rules depend on transaction and category systems being in place
- **Phase 4 after Phase 3**: Analytics calculations require complete transaction data including categorization
- **Phase 5 last**: Production readiness requires all features implemented for comprehensive testing

**Parallel Work Opportunities** (if multiple developers):
- During Phase 2: One dev on accounts/permissions, another on transactions/categories
- During Phase 3: One dev on CSV import, another on rule engine
- During Phase 4: One dev on analytics, another on security/rate limiting

**Quick Wins**:
- Health check endpoint (Phase 1) - immediate deployment verification
- Basic transaction CRUD (Phase 2) - early value for manual entry
- Simple keyword rules (Phase 3) - before complex regex support

---

## Simplicity & Design Validation

### Simplicity Checklist

- [✓] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Using proven technologies (FastAPI, SQLAlchemy, PostgreSQL) with standard patterns
  - Avoiding over-engineering (e.g., custom rule engine vs. heavyweight business rule frameworks)
  - Starting with essential features, deferring nice-to-haves

- [✓] **Have we avoided premature optimization?**
  - Yes. Using database-level aggregation and indexing only where needed
  - Deferring caching layer until performance testing shows need
  - Simple duplicate detection algorithm (hash + fuzzy) rather than ML-based

- [✓] **Does this align with existing patterns in the codebase?**
  - Yes. Following project standards from `.claude/standards/`
  - Using consistent layering (routes → services → repositories)
  - Following FastAPI and SQLAlchemy best practices

- [✓] **Can we deliver value in smaller increments?**
  - Yes. Five phases with clear value delivery at each stage
  - Phase 1 delivers authentication (user can register/login)
  - Phase 2 delivers core features (user can manage finances manually)
  - Phase 3 delivers automation (user can import and auto-categorize)
  - Phase 4 delivers insights (user can analyze spending)
  - Phase 5 delivers production readiness

- [✓] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. Based on comprehensive requirements document and market research
  - Addressing real user needs (privacy, flexible categorization, family sharing)
  - Validated by competitive analysis showing gaps in existing solutions

### Alternatives Considered

**Alternative 1: Microservices Architecture**
- **Description**: Separate services for auth, transactions, analytics, import
- **Why not chosen**:
  - Adds complexity (service discovery, inter-service communication)
  - Not needed for 1-5 concurrent users
  - Harder to develop and test
  - Monolith-first approach allows future extraction if needed

**Alternative 2: GraphQL instead of REST**
- **Description**: Use GraphQL for flexible querying
- **Why not chosen**:
  - REST is simpler and more familiar
  - Auto-generated OpenAPI documentation with FastAPI
  - GraphQL adds complexity (schema design, N+1 query issues, caching)
  - REST meets all requirements adequately

**Alternative 3: NoSQL (MongoDB) instead of PostgreSQL**
- **Description**: Use document database for flexible schema
- **Why not chosen**:
  - Financial data requires ACID guarantees
  - Hierarchical categories need recursive queries (PostgreSQL CTEs)
  - PostgreSQL's JSONB provides flexibility where needed
  - Decimal precision critical for financial calculations

**Alternative 4: Heavyweight Rule Engine (Drools-like)**
- **Description**: Use enterprise-grade business rule engine
- **Why not chosen**:
  - Overkill for keyword/regex matching
  - Adds dependency and complexity
  - Custom implementation is 100 lines vs. thousands
  - Easy to extend custom solution if needed

**Alternative 5: Client-Side Categorization (Frontend)**
- **Description**: Move rule engine and duplicate detection to frontend
- **Why not chosen**:
  - Backend provides single source of truth
  - Enables retroactive application across all user sessions
  - Backend processing more performant for bulk operations
  - Centralized logic easier to maintain and test

### Rationale for Chosen Approach

**Why this implementation plan is optimal**:

1. **Proven Technology Stack**: FastAPI + SQLAlchemy + PostgreSQL is battle-tested, well-documented, and has strong community support
2. **Clean Architecture**: Separation of concerns enables testing, maintenance, and future changes
3. **Incremental Delivery**: Five phases allow early feedback and course correction
4. **Performance First**: Async-first architecture and database optimization built in from start
5. **Security by Design**: Authentication, authorization, audit logging integrated from Phase 1
6. **Test Coverage**: 80%+ coverage ensures reliability and enables refactoring confidence
7. **Production Ready**: Phase 5 ensures deployment readiness, not afterthought
8. **Extensibility**: Repository pattern, service layer, and clean interfaces allow future enhancements without major refactoring

---

## References & Related Documents

### Internal Documentation

- **Feature Description**: `.features/descriptions/20251027_project-initialization.md`
- **Research Document**: `.features/research/20251027_project-initialization.md`
- **Project Standards**:
  - Backend Standards: `.claude/standards/backend.md`
  - API Standards: `.claude/standards/api.md`
  - Database Standards: `.claude/standards/database.md`
  - Auth Standards: `.claude/standards/auth.md`
  - Testing Standards: `.claude/standards/testing.md`

### External Resources

**FastAPI & Python:**
- FastAPI Official Docs: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 Docs: https://docs.sqlalchemy.org/en/20/
- Alembic Tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Pydantic V2 Docs: https://docs.pydantic.dev/latest/

**Architecture & Patterns:**
- Medium: "Clean FastAPI Architecture in Real Projects" (July 2025)
- Fueled: "Clean Architecture with FastAPI"
- FastAPI Clean Architecture GitHub: https://github.com/zhanymkanov/fastapi-best-practices

**Database & Performance:**
- Medium: "10 SQLAlchemy 2.0 Patterns for Clean Async Postgres" (October 2025)
- PostgreSQL Recursive Queries Docs: https://www.postgresql.org/docs/current/queries-with.html
- Medium: "Taming Hierarchical Data: Mastering SQL Recursive CTEs" (May 2025)

**Security:**
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- FastAPI Security Tutorial: https://fastapi.tiangolo.com/tutorial/security/
- Medium: "FastAPI Security Best Practices" (October 2025)

**Testing:**
- pytest-asyncio Docs: https://pytest-asyncio.readthedocs.io/
- TestDriven.io: "Developing and Testing an Asynchronous API with FastAPI and Pytest"

**Deployment:**
- Better Stack: "FastAPI Docker Best Practices"
- FastAPI in Containers: https://fastapi.tiangolo.com/deployment/docker/

**Financial Calculations:**
- Python Decimal Module: https://docs.python.org/3/library/decimal.html
- CodeRivers: "Mastering Decimal in Python"

**Competitive Products:**
- Actual Budget: https://actualbudget.com/
- Firefly III: https://www.firefly-iii.org/
- Financial Freedom: https://serversideup.net/open-source/financial-freedom/

---

## Appendices

### A. Database Schema Overview

See separate document: `.features/plans/20251027_project-initialization-database-schema.md`

### B. API Endpoint Structure

See separate document: `.features/plans/20251027_project-initialization-api-endpoints.md`

### C. Environment Variables

See separate document: `.features/plans/20251027_project-initialization-environment-variables.md`

---

**Document Version:** 1.0
**Last Updated:** October 27, 2025
**Next Review:** After Phase 1 completion
**Status:** Ready for Implementation

