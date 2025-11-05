# Hexagonal Architecture Refactoring Implementation Plan

**Project**: Emerald Finance Platform Backend
**Date**: November 5, 2025
**Estimated Duration**: 14-19 days (2-3 weeks)
**Complexity**: High

---

## 1. Executive Summary

### Overview

This plan details the refactoring of the Emerald Finance Platform backend from its current layered architecture to a comprehensive **Hexagonal Architecture** (Ports and Adapters pattern) with complete database independence and the Unit of Work pattern. The refactoring will transform a tightly-coupled FastAPI application into a clean, testable, and maintainable system with clear separation of concerns.

### Primary Objectives

1. **Achieve Database Independence**: Decouple all business logic from PostgreSQL/SQLAlchemy, enabling easy migration to any data source (MongoDB, API, in-memory) without changing domain or application logic
2. **Implement True Hexagonal Architecture**: Establish three distinct layers (Domain, Application, Infrastructure) with proper dependency flow (Infrastructure → Application → Domain)
3. **Enable Pure Domain Testing**: Make business logic testable without any infrastructure dependencies
4. **Implement Unit of Work Pattern**: Ensure transactional consistency across multiple repository operations with clear transaction boundaries
5. **Maintain 100% Functionality**: Preserve all existing features and API contracts while improving architecture

### Current State Assessment

**Strengths**:
- Clear 5-layer structure (Routes → DI → Services → Repositories → Models)
- Good separation between routes and business logic
- Comprehensive audit logging and security practices
- Full async/await implementation
- Strong type hints and Pydantic validation

**Challenges**:
- **80-90% coupling to SQLAlchemy**: Services return ORM models, business logic intertwined with persistence
- **No domain layer**: Domain models are SQLAlchemy models (no separation)
- **Implicit repository interfaces**: Hard to mock, no formal contracts
- **Services create repositories**: Manual instantiation, no dependency injection for repos
- **Validation requires database**: Cannot test domain logic in isolation

### Expected Outcomes

**After refactoring**:
- Domain logic testable in <100ms without database (vs. current ~2-5s per test)
- Business rules centralized in domain services (vs. scattered across layers)
- Infrastructure swappable (PostgreSQL → MongoDB requires only Infrastructure layer changes)
- Test coverage improved from ~70% to 90%+ with faster suite execution
- Clear architectural boundaries enable easier onboarding and maintenance
- Foundation for microservices extraction if needed in future

### Success Criteria

- [ ] Domain layer has zero imports from FastAPI, SQLAlchemy, or any external framework
- [ ] All domain logic testable without database (100+ pure unit tests)
- [ ] Repository interfaces formalized with Protocol/ABC
- [ ] All database operations managed through Unit of Work
- [ ] Services return DTOs, not ORM models
- [ ] Can create MongoDB implementation by changing only Infrastructure layer
- [ ] All existing API tests pass without modification
- [ ] Test suite execution time reduced by 60%+ for unit tests
- [ ] Code coverage increases to 90%+

---

## 2. Technical Architecture

### 2.1 System Design Overview

#### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                         │
│  (Adapters - Framework & Technology Specific)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  INBOUND ADAPTERS              OUTBOUND ADAPTERS                 │
│  ┌──────────────────┐         ┌──────────────────────────┐      │
│  │ FastAPI Routers  │         │ PostgreSQL Repositories  │      │
│  │ API Schemas      │         │ SQLAlchemy Models        │      │
│  │ HTTP Exception   │         │ Entity ↔ Model Mappers   │      │
│  │ Handlers         │         │ Unit of Work (Postgres)  │      │
│  │ Dependency Setup │         │ External API Clients     │      │
│  └────────┬─────────┘         └────────┬─────────────────┘      │
│           │                            │                         │
└───────────┼────────────────────────────┼─────────────────────────┘
            │                            │
            ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  (Use Cases & Port Interfaces - Framework Agnostic)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PORT INTERFACES                USE CASES                        │
│  ┌────────────────────┐        ┌──────────────────────┐         │
│  │ Inbound Ports      │        │ RegisterUserUseCase  │         │
│  │ - Service Ifaces   │        │ CreateAccountUseCase │         │
│  │                    │        │ AuthenticateUser...  │         │
│  │ Outbound Ports     │        │ TransferFunds...     │         │
│  │ - Repository Ifaces│        │                      │         │
│  │ - UnitOfWork Iface │        │ DTOs (Input/Output)  │         │
│  └────────────────────┘        └──────────┬───────────┘         │
│                                           │                      │
└───────────────────────────────────────────┼──────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                              │
│  (Core Business Logic - Zero External Dependencies)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ENTITIES                 VALUE OBJECTS       DOMAIN SERVICES    │
│  ┌────────────┐          ┌────────────┐     ┌────────────────┐  │
│  │ User       │          │ Email      │     │ Permission     │  │
│  │ Account    │          │ Money      │     │ Checker        │  │
│  │ Role       │          │ Currency   │     │ Account Sharing│  │
│  │ AccountShr │          │ Username   │     │ Service        │  │
│  └────────────┘          └────────────┘     └────────────────┘  │
│                                                                   │
│  DOMAIN EXCEPTIONS                                                │
│  ┌───────────────────────────────────────────────────────┐       │
│  │ InsufficientPermissionsError, InvalidEmailError, etc. │       │
│  └───────────────────────────────────────────────────────┘       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### Dependency Flow

```
Infrastructure Layer
    ↓ depends on
Application Layer
    ↓ depends on
Domain Layer (depends on NOTHING)
```

**Critical Rule**: Dependencies ONLY flow inward. The Domain layer is completely isolated and has zero knowledge of Application or Infrastructure layers.

### 2.2 Technology Decisions

#### **Python 3.13+**
- **Purpose**: Core programming language for entire application
- **Why this choice**:
  - LTS version with improved async performance
  - Enhanced type system for better domain modeling
  - Project already standardized on Python
  - Excellent support for async/await patterns
- **Version**: 3.13+ (latest stable LTS)
- **Alternatives considered**:
  - Staying on Python 3.11: Rejected due to performance improvements in 3.13
  - Python 3.12: Considered but 3.13 offers better async performance

#### **FastAPI 0.115+**
- **Purpose**: HTTP adapter (inbound) in Infrastructure layer
- **Why this choice**:
  - Current framework, minimizes migration risk
  - Excellent async support
  - Built-in dependency injection for Infrastructure layer
  - Auto-generated OpenAPI docs
- **Version**: 0.115+ (latest stable)
- **Alternatives considered**: None - changing framework would add unnecessary risk

#### **SQLAlchemy 2.0+**
- **Purpose**: PostgreSQL adapter (outbound) in Infrastructure layer
- **Why this choice**:
  - Current ORM, minimizes migration risk
  - Excellent async support with AsyncSession
  - Flexible enough for complex queries
  - Will be confined to Infrastructure layer only
- **Version**: 2.0+ with async extensions
- **Alternatives considered**: None for initial refactoring, but architecture will support swapping

#### **Pydantic 2.x**
- **Purpose**: Used in two places:
  1. API schemas in Infrastructure layer (HTTP request/response validation)
  2. DTOs in Application layer (use case inputs/outputs)
- **Why this choice**:
  - Current validation library
  - Fast and type-safe
  - Clear separation: API schemas ≠ DTOs
- **Version**: 2.x latest stable
- **Alternatives considered**:
  - Dataclasses for DTOs: Rejected due to lack of validation
  - attrs: Rejected due to team familiarity with Pydantic

#### **dependency-injector 4.x**
- **Purpose**: IoC container for advanced dependency injection scenarios
- **Why this choice**:
  - FastAPI's Depends() leaks into layers (couples to FastAPI)
  - Need framework-agnostic DI for Application layer
  - Supports factory patterns and scoped lifetimes
  - Popular in Python DDD/Clean Architecture projects
- **Version**: 4.x latest stable
- **Alternatives considered**:
  - Python-inject: Less active maintenance
  - Pinject: Google's library but less Pythonic
  - FastAPI Depends() only: Rejected due to coupling

#### **pytest 8.x + pytest-asyncio**
- **Purpose**: Testing framework for all test types
- **Why this choice**:
  - Current test framework
  - Excellent async support
  - Rich fixture system for test data
  - Large plugin ecosystem
- **Version**: 8.x latest stable
- **Alternatives considered**: None - pytest is industry standard

#### **factory_boy 3.x**
- **Purpose**: Test data generation for domain entities and DTOs
- **Why this choice**:
  - Cleaner than manual fixture creation
  - Supports relationships and sequences
  - Can generate both domain entities and DTOs
- **Version**: 3.x latest stable
- **Alternatives considered**:
  - Faker only: Too low-level for complex objects
  - Manual fixtures: Too much boilerplate

### 2.3 File Structure

```
emerald-backend/
├── alembic/                         # Database migrations (Infrastructure)
│   └── versions/
│
├── app/
│   ├── domain/                      # DOMAIN LAYER (NO external dependencies)
│   │   ├── __init__.py
│   │   │
│   │   ├── entities/                # Pure Python domain entities
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # User entity with business logic
│   │   │   ├── account.py           # Account entity with business rules
│   │   │   ├── role.py              # Role entity
│   │   │   ├── account_share.py     # AccountShare entity
│   │   │   └── audit_log.py         # AuditLog entity (immutable)
│   │   │
│   │   ├── value_objects/           # Immutable value objects
│   │   │   ├── __init__.py
│   │   │   ├── email.py             # Email with validation
│   │   │   ├── username.py          # Username with validation
│   │   │   ├── money.py             # Money with currency
│   │   │   ├── currency.py          # Currency enum
│   │   │   ├── permission.py        # Permission enum/class
│   │   │   └── password_hash.py     # Password hash (not plain password)
│   │   │
│   │   ├── services/                # Domain services (business logic)
│   │   │   ├── __init__.py
│   │   │   ├── permission_checker.py    # Centralized permission logic
│   │   │   ├── account_sharing_service.py # Account sharing rules
│   │   │   └── user_validation_service.py # Complex user validations
│   │   │
│   │   └── exceptions/              # Domain-specific exceptions
│   │       ├── __init__.py
│   │       ├── base.py              # Base domain exception
│   │       ├── user_exceptions.py   # User domain errors
│   │       ├── account_exceptions.py # Account domain errors
│   │       └── permission_exceptions.py # Permission errors
│   │
│   ├── application/                 # APPLICATION LAYER (depends only on domain)
│   │   ├── __init__.py
│   │   │
│   │   ├── ports/                   # Port interfaces (contracts)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── inbound/             # Driving ports (service interfaces)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_service_port.py
│   │   │   │   ├── user_service_port.py
│   │   │   │   ├── account_service_port.py
│   │   │   │   └── audit_service_port.py
│   │   │   │
│   │   │   └── outbound/            # Driven ports (repository interfaces)
│   │   │       ├── __init__.py
│   │   │       ├── unit_of_work_port.py    # UoW interface
│   │   │       ├── user_repository_port.py
│   │   │       ├── account_repository_port.py
│   │   │       ├── role_repository_port.py
│   │   │       ├── account_share_repository_port.py
│   │   │       ├── audit_log_repository_port.py
│   │   │       └── refresh_token_repository_port.py
│   │   │
│   │   ├── use_cases/               # Use case implementations
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── auth/                # Authentication use cases
│   │   │   │   ├── __init__.py
│   │   │   │   ├── register_user.py
│   │   │   │   ├── authenticate_user.py
│   │   │   │   ├── refresh_token.py
│   │   │   │   ├── logout_user.py
│   │   │   │   └── change_password.py
│   │   │   │
│   │   │   ├── users/               # User management use cases
│   │   │   │   ├── __init__.py
│   │   │   │   ├── get_user_profile.py
│   │   │   │   ├── update_user_profile.py
│   │   │   │   ├── delete_user.py
│   │   │   │   └── list_users.py     # Admin only
│   │   │   │
│   │   │   ├── accounts/            # Account management use cases
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_account.py
│   │   │   │   ├── get_account.py
│   │   │   │   ├── update_account.py
│   │   │   │   ├── delete_account.py
│   │   │   │   ├── list_user_accounts.py
│   │   │   │   └── share_account.py
│   │   │   │
│   │   │   └── audit/               # Audit use cases
│   │   │       ├── __init__.py
│   │   │       ├── create_audit_log.py
│   │   │       └── query_audit_logs.py
│   │   │
│   │   ├── dto/                     # Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── auth_dto.py          # RegisterUserInput, LoginOutput, etc.
│   │   │   ├── user_dto.py          # UserProfileOutput, UpdateUserInput
│   │   │   ├── account_dto.py       # AccountOutput, CreateAccountInput
│   │   │   └── audit_dto.py         # AuditLogOutput, QueryAuditInput
│   │   │
│   │   └── exceptions.py            # Application-level exceptions
│   │
│   └── infrastructure/              # INFRASTRUCTURE LAYER (depends on app + domain)
│       ├── __init__.py
│       │
│       ├── adapters/
│       │   ├── __init__.py
│       │   │
│       │   ├── inbound/             # Driving adapters
│       │   │   ├── __init__.py
│       │   │   │
│       │   │   └── api/             # FastAPI HTTP adapter
│       │   │       ├── __init__.py
│       │   │       ├── main.py      # FastAPI app creation
│       │   │       ├── dependencies.py # DI setup
│       │   │       │
│       │   │       ├── routes/      # API endpoint definitions
│       │   │       │   ├── __init__.py
│       │   │       │   ├── auth.py
│       │   │       │   ├── users.py
│       │   │       │   ├── accounts.py
│       │   │       │   └── audit_logs.py
│       │   │       │
│       │   │       ├── schemas/     # Pydantic API schemas (NOT DTOs)
│       │   │       │   ├── __init__.py
│       │   │       │   ├── auth_schemas.py
│       │   │       │   ├── user_schemas.py
│       │   │       │   ├── account_schemas.py
│       │   │       │   └── audit_schemas.py
│       │   │       │
│       │   │       └── exception_handlers.py # Convert domain exceptions → HTTP
│       │   │
│       │   └── outbound/            # Driven adapters
│       │       ├── __init__.py
│       │       │
│       │       └── persistence/
│       │           ├── __init__.py
│       │           │
│       │           └── postgresql/  # PostgreSQL implementation
│       │               ├── __init__.py
│       │               │
│       │               ├── models/  # SQLAlchemy ORM models
│       │               │   ├── __init__.py
│       │               │   ├── base.py
│       │               │   ├── user_model.py
│       │               │   ├── account_model.py
│       │               │   ├── role_model.py
│       │               │   ├── account_share_model.py
│       │               │   ├── audit_log_model.py
│       │               │   └── refresh_token_model.py
│       │               │
│       │               ├── repositories/ # Repository implementations
│       │               │   ├── __init__.py
│       │               │   ├── base_repository.py
│       │               │   ├── user_repository.py
│       │               │   ├── account_repository.py
│       │               │   ├── role_repository.py
│       │               │   ├── account_share_repository.py
│       │               │   ├── audit_log_repository.py
│       │               │   └── refresh_token_repository.py
│       │               │
│       │               ├── mappers/     # Entity ↔ Model mappers
│       │               │   ├── __init__.py
│       │               │   ├── user_mapper.py
│       │               │   ├── account_mapper.py
│       │               │   ├── role_mapper.py
│       │               │   ├── account_share_mapper.py
│       │               │   ├── audit_log_mapper.py
│       │               │   └── refresh_token_mapper.py
│       │               │
│       │               ├── unit_of_work.py # PostgresUnitOfWork implementation
│       │               └── session.py      # Database session management
│       │
│       └── config/                  # Configuration
│           ├── __init__.py
│           ├── settings.py          # Pydantic Settings
│           ├── di_container.py      # Dependency injection container
│           ├── logging.py           # Logging configuration
│           └── security.py          # Security utilities (hashing, JWT)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures
│   │
│   ├── unit/                        # Pure unit tests (NO database)
│   │   ├── __init__.py
│   │   ├── domain/                  # Domain layer tests
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   └── services/
│   │   │
│   │   └── application/             # Application layer tests (mocked repos)
│   │       ├── use_cases/
│   │       └── dto/
│   │
│   ├── integration/                 # Tests with real database
│   │   ├── __init__.py
│   │   ├── repositories/            # Repository integration tests
│   │   └── use_cases/               # Use cases with real repos
│   │
│   ├── e2e/                         # End-to-end API tests
│   │   ├── __init__.py
│   │   ├── test_auth_flow.py
│   │   ├── test_account_management.py
│   │   └── test_user_management.py
│   │
│   └── factories/                   # Test data factories
│       ├── __init__.py
│       ├── domain_factories.py      # Domain entity factories
│       ├── dto_factories.py         # DTO factories
│       └── model_factories.py       # SQLAlchemy model factories
│
├── docs/
│   └── architecture/
│       ├── hexagonal-architecture.md
│       ├── domain-model.md
│       └── adr/                     # Architecture Decision Records
│
├── .env.example
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Domain Entities

**Files Involved**:
- `app/domain/entities/user.py`
- `app/domain/entities/account.py`
- `app/domain/entities/role.py`
- `app/domain/entities/account_share.py`
- `app/domain/entities/audit_log.py`

**Purpose**: Pure Python classes representing core business concepts with business logic methods, completely independent of any framework or database.

**Implementation Requirements**:

1. **Core Logic**:
   - Create pure Python classes (no SQLAlchemy decorators)
   - Use dataclasses or regular classes with `__init__`
   - All fields are value objects or primitives (after value object extraction)
   - Business logic methods live on entities (e.g., `user.can_access_account(account)`)
   - Entities are mutable (have unique identity)
   - Rich domain model (behavior + data together)

2. **Data Handling**:
   - Input: Constructor parameters (primitives, value objects, other entities)
   - Output: Entity instance with business methods
   - State: Internal state managed through methods
   - No database concerns (no `id`, `created_at` management)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Invalid state transitions (e.g., can't activate already-active user)
   - [ ] Validate: Business rules (e.g., account must have owner)
   - [ ] Error: Raise domain exceptions (not ValueError/TypeError)
   - [ ] Validate inputs through value objects (not in entity)

4. **Dependencies**:
   - Internal: Value objects from `domain/value_objects/`
   - Internal: Domain exceptions from `domain/exceptions/`
   - External: **NONE** (zero imports from SQLAlchemy, FastAPI, or any library)

5. **Testing Requirements**:
   - [ ] Unit test: User entity creation with valid data
   - [ ] Unit test: Account ownership check returns correct boolean
   - [ ] Unit test: Role has permission check works for various permissions
   - [ ] Unit test: Account share expiration detection
   - [ ] Unit test: Entity equality based on identity (id), not field values
   - [ ] Integration test: N/A (pure domain, no integration needed)

**Example - User Entity**:
```python
# app/domain/entities/user.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.exceptions.permission_exceptions import InsufficientPermissionsError


@dataclass
class User:
    """Pure domain entity representing a user."""

    id: UUID
    email: Email
    username: Username
    password_hash: PasswordHash
    full_name: str
    is_active: bool
    is_admin: bool
    roles: list['Role'] = field(default_factory=list)
    created_at: Optional[datetime] = None  # Set by infrastructure
    updated_at: Optional[datetime] = None  # Set by infrastructure
    deleted_at: Optional[datetime] = None  # Soft delete

    def activate(self) -> None:
        """Activate this user account."""
        if self.is_active:
            raise ValueError("User is already active")
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate this user account."""
        if not self.is_active:
            raise ValueError("User is already inactive")
        self.is_active = False

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission through roles."""
        if self.is_admin:
            return True
        return any(role.has_permission(permission) for role in self.roles)

    def can_access_account(self, account: 'Account') -> bool:
        """Check if user can access an account (owner or shared)."""
        return account.user_id == self.id or account.is_shared_with(self.id)

    def change_password(self, new_password_hash: PasswordHash) -> None:
        """Change user password."""
        self.password_hash = new_password_hash

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)
```

**Acceptance Criteria**:
- [ ] All 5 domain entities created as pure Python classes
- [ ] Zero imports from SQLAlchemy, FastAPI, or external libraries
- [ ] Business logic methods on entities (not scattered in services)
- [ ] All entities have comprehensive unit tests (no database required)
- [ ] Entities use value objects for complex types (Email, Money, etc.)

**Implementation Notes**:
- Start with User and Account entities (most complex)
- Use dataclasses for cleaner syntax (or regular classes if mutability concerns)
- Keep entities focused on business rules, not persistence concerns
- Test each entity in isolation before moving to next component

---

#### Component: Value Objects

**Files Involved**:
- `app/domain/value_objects/email.py`
- `app/domain/value_objects/username.py`
- `app/domain/value_objects/money.py`
- `app/domain/value_objects/currency.py`
- `app/domain/value_objects/permission.py`
- `app/domain/value_objects/password_hash.py`

**Purpose**: Immutable objects representing concepts that are defined by their value, not identity (e.g., two Email objects with same address are identical).

**Implementation Requirements**:

1. **Core Logic**:
   - Immutable (frozen dataclasses or properties without setters)
   - Validation in constructor (fail fast)
   - Equality based on value, not identity
   - No business logic (only validation and value behavior)

2. **Data Handling**:
   - Input: Raw primitive value (str, int, etc.)
   - Output: Validated, immutable value object
   - State: Immutable after creation

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Invalid email format → raise InvalidEmailError
   - [ ] Handle case: Username too short/long → raise InvalidUsernameError
   - [ ] Handle case: Negative money amount → raise InvalidMoneyError
   - [ ] Validate: Currency code is valid ISO 4217
   - [ ] Error: Raise domain exceptions (InvalidValueError subclasses)

4. **Dependencies**:
   - Internal: Domain exceptions
   - External: Standard library only (re, enum, dataclasses)

5. **Testing Requirements**:
   - [ ] Unit test: Valid email creates Email object
   - [ ] Unit test: Invalid email raises InvalidEmailError
   - [ ] Unit test: Two emails with same address are equal
   - [ ] Unit test: Money arithmetic (add, subtract)
   - [ ] Unit test: Currency comparison and validation
   - [ ] Unit test: Password hash cannot be created from plain password (security)

**Example - Email Value Object**:
```python
# app/domain/value_objects/email.py
import re
from dataclasses import dataclass

from app.domain.exceptions.user_exceptions import InvalidEmailError


EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


@dataclass(frozen=True)
class Email:
    """Email value object with validation."""

    value: str

    def __post_init__(self) -> None:
        """Validate email format."""
        if not EMAIL_REGEX.match(self.value):
            raise InvalidEmailError(f"Invalid email format: {self.value}")

        # Normalize to lowercase
        object.__setattr__(self, 'value', self.value.lower())

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Email):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
```

**Acceptance Criteria**:
- [ ] All 6 value objects created and validated
- [ ] All value objects are immutable (frozen dataclasses)
- [ ] Validation happens in constructor (fail fast)
- [ ] Value objects have comprehensive unit tests
- [ ] Equality based on value, not identity

---

#### Component: Repository Port Interfaces

**Files Involved**:
- `app/application/ports/outbound/user_repository_port.py`
- `app/application/ports/outbound/account_repository_port.py`
- `app/application/ports/outbound/role_repository_port.py`
- `app/application/ports/outbound/account_share_repository_port.py`
- `app/application/ports/outbound/audit_log_repository_port.py`
- `app/application/ports/outbound/refresh_token_repository_port.py`

**Purpose**: Define contracts (interfaces) for data access without implementation details. Application layer depends on these interfaces, Infrastructure layer implements them.

**Implementation Requirements**:

1. **Core Logic**:
   - Use `typing.Protocol` or `abc.ABC` for interfaces
   - Define all CRUD operations needed by use cases
   - Work with domain entities (not database models)
   - Return domain entities or None
   - Accept domain entities as parameters
   - All methods are async

2. **Data Handling**:
   - Input: Domain entities, UUIDs, query parameters
   - Output: Domain entities, lists of entities, or None
   - No database-specific types in signatures (no SQLAlchemy types)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Entity not found → return None (don't raise)
   - [ ] Handle case: Duplicate unique field → raise domain exception
   - [ ] Validate: Repository method signatures match use case needs
   - [ ] Error: Let infrastructure implementation handle database errors

4. **Dependencies**:
   - Internal: Domain entities
   - External: typing.Protocol or abc.ABC only

5. **Testing Requirements**:
   - [ ] Unit test: Mock implementations for use case tests
   - [ ] Unit test: InMemory implementations for fast testing
   - [ ] Integration test: PostgreSQL implementations against real DB

**Example - UserRepositoryPort**:
```python
# app/application/ports/outbound/user_repository_port.py
from typing import Protocol, Optional
from uuid import UUID

from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username


class UserRepositoryPort(Protocol):
    """Repository interface for User entity."""

    async def add(self, user: User) -> User:
        """Add a new user to the repository."""
        ...

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Retrieve user by ID."""
        ...

    async def get_by_email(self, email: Email) -> Optional[User]:
        """Retrieve user by email address."""
        ...

    async def get_by_username(self, username: Username) -> Optional[User]:
        """Retrieve user by username."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> list[User]:
        """List users with pagination."""
        ...

    async def update(self, user: User) -> User:
        """Update existing user."""
        ...

    async def delete(self, user_id: UUID) -> None:
        """Hard delete user (use soft delete in practice)."""
        ...

    async def soft_delete(self, user_id: UUID) -> None:
        """Soft delete user (set deleted_at)."""
        ...

    async def exists_by_email(self, email: Email) -> bool:
        """Check if user with email exists."""
        ...

    async def exists_by_username(self, username: Username) -> bool:
        """Check if user with username exists."""
        ...
```

**Acceptance Criteria**:
- [ ] All 6 repository ports defined with Protocol or ABC
- [ ] All methods work with domain entities (not models)
- [ ] All methods are async
- [ ] Ports cover all use case needs
- [ ] Documentation for each method is clear

---

#### Component: Unit of Work Port & Implementation

**Files Involved**:
- `app/application/ports/outbound/unit_of_work_port.py` (interface)
- `app/infrastructure/adapters/outbound/persistence/postgresql/unit_of_work.py` (implementation)

**Purpose**: Manage transaction boundaries and coordinate repository operations. Ensure atomic commits/rollbacks across multiple repositories.

**Implementation Requirements**:

1. **Core Logic**:
   - UoW port defines interface in Application layer
   - PostgresUnitOfWork implements interface in Infrastructure layer
   - Provide access to all repositories
   - Manage database session lifecycle
   - Async context manager (`async with uow:`)
   - Commit on successful exit, rollback on exception

2. **Data Handling**:
   - Input: Database connection settings (from config)
   - Output: Repository instances with shared session
   - State: Manages transaction state (active, committed, rolled back)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Exception during transaction → automatic rollback
   - [ ] Handle case: Nested transactions → use savepoints if needed
   - [ ] Handle case: Connection errors → raise infrastructure exception
   - [ ] Validate: All repos share same session
   - [ ] Error: Re-raise domain exceptions, wrap database exceptions

4. **Dependencies**:
   - Internal: All repository ports (Application layer)
   - Internal: All repository implementations (Infrastructure layer)
   - External: SQLAlchemy AsyncSession (Infrastructure only)

5. **Testing Requirements**:
   - [ ] Unit test: UoW commits on successful completion
   - [ ] Unit test: UoW rolls back on exception
   - [ ] Integration test: Multiple repo operations in single transaction
   - [ ] Integration test: Rollback undoes all operations
   - [ ] Integration test: Nested UoW usage (if supported)

**Example - UnitOfWorkPort**:
```python
# app/application/ports/outbound/unit_of_work_port.py
from typing import Protocol

from app.application.ports.outbound.user_repository_port import UserRepositoryPort
from app.application.ports.outbound.account_repository_port import AccountRepositoryPort
from app.application.ports.outbound.role_repository_port import RoleRepositoryPort
from app.application.ports.outbound.account_share_repository_port import AccountShareRepositoryPort
from app.application.ports.outbound.audit_log_repository_port import AuditLogRepositoryPort
from app.application.ports.outbound.refresh_token_repository_port import RefreshTokenRepositoryPort


class UnitOfWorkPort(Protocol):
    """Unit of Work interface for managing transactions."""

    users: UserRepositoryPort
    accounts: AccountRepositoryPort
    roles: RoleRepositoryPort
    account_shares: AccountShareRepositoryPort
    audit_logs: AuditLogRepositoryPort
    refresh_tokens: RefreshTokenRepositoryPort

    async def __aenter__(self) -> 'UnitOfWorkPort':
        """Enter async context manager (begin transaction)."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager (commit or rollback)."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
```

**Example - PostgresUnitOfWork Implementation**:
```python
# app/infrastructure/adapters/outbound/persistence/postgresql/unit_of_work.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.user_repository import PostgresUserRepository
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.account_repository import PostgresAccountRepository
# ... other repository imports


class PostgresUnitOfWork:
    """PostgreSQL implementation of Unit of Work."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> 'PostgresUnitOfWork':
        """Create session and repository instances."""
        self._session = self._session_factory()

        # Initialize all repositories with shared session
        self.users = PostgresUserRepository(self._session)
        self.accounts = PostgresAccountRepository(self._session)
        self.roles = PostgresRoleRepository(self._session)
        self.account_shares = PostgresAccountShareRepository(self._session)
        self.audit_logs = PostgresAuditLogRepository(self._session)
        self.refresh_tokens = PostgresRefreshTokenRepository(self._session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Commit or rollback and close session."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

        await self._session.close()

    async def commit(self) -> None:
        """Commit transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback transaction."""
        await self._session.rollback()
```

**Acceptance Criteria**:
- [ ] UnitOfWorkPort interface defined in Application layer
- [ ] PostgresUnitOfWork implements interface in Infrastructure layer
- [ ] All repositories accessible through UoW
- [ ] Automatic commit on success, rollback on exception
- [ ] Integration tests verify transactional behavior
- [ ] Use cases receive UoW through dependency injection

---

#### Component: Entity-Model Mappers

**Files Involved**:
- `app/infrastructure/adapters/outbound/persistence/postgresql/mappers/user_mapper.py`
- `app/infrastructure/adapters/outbound/persistence/postgresql/mappers/account_mapper.py`
- (... 4 more mapper files)

**Purpose**: Bidirectional conversion between domain entities and database models. Isolates ORM concerns from domain.

**Implementation Requirements**:

1. **Core Logic**:
   - Each mapper handles one entity ↔ model pair
   - `to_entity(model)` converts SQLAlchemy model → domain entity
   - `to_model(entity)` converts domain entity → SQLAlchemy model
   - Handle nested objects (e.g., User has list of Roles)
   - Mappers live in Infrastructure layer only

2. **Data Handling**:
   - Input: Either domain entity or database model
   - Output: Opposite type (entity or model)
   - Handle None values gracefully
   - Map value objects to primitives and back

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Model has None relationships → empty list in entity
   - [ ] Handle case: Entity has value objects → convert to primitives for model
   - [ ] Handle case: Timestamps (model has, entity might not)
   - [ ] Validate: All fields mapped correctly
   - [ ] Error: Raise infrastructure exception if mapping fails

4. **Dependencies**:
   - Internal: Domain entities
   - Internal: SQLAlchemy models
   - Internal: Value objects
   - External: None

5. **Testing Requirements**:
   - [ ] Unit test: to_entity() creates valid domain entity
   - [ ] Unit test: to_model() creates valid SQLAlchemy model
   - [ ] Unit test: Roundtrip (entity → model → entity) preserves data
   - [ ] Unit test: Value objects converted correctly
   - [ ] Integration test: Mapper used in repository operations

**Example - UserMapper**:
```python
# app/infrastructure/adapters/outbound/persistence/postgresql/mappers/user_mapper.py
from typing import Optional

from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username
from app.domain.value_objects.password_hash import PasswordHash
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import UserModel
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.role_mapper import RoleMapper


class UserMapper:
    """Mapper between User entity and UserModel."""

    @staticmethod
    def to_entity(model: UserModel) -> User:
        """Convert SQLAlchemy model to domain entity."""
        return User(
            id=model.id,
            email=Email(model.email),
            username=Username(model.username),
            password_hash=PasswordHash(model.password_hash),
            full_name=model.full_name,
            is_active=model.is_active,
            is_admin=model.is_admin,
            roles=[RoleMapper.to_entity(role) for role in model.roles],
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: User, existing_model: Optional[UserModel] = None) -> UserModel:
        """Convert domain entity to SQLAlchemy model."""
        if existing_model:
            # Update existing model
            existing_model.email = entity.email.value
            existing_model.username = entity.username.value
            existing_model.password_hash = entity.password_hash.value
            existing_model.full_name = entity.full_name
            existing_model.is_active = entity.is_active
            existing_model.is_admin = entity.is_admin
            return existing_model
        else:
            # Create new model
            return UserModel(
                id=entity.id,
                email=entity.email.value,
                username=entity.username.value,
                password_hash=entity.password_hash.value,
                full_name=entity.full_name,
                is_active=entity.is_active,
                is_admin=entity.is_admin,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                deleted_at=entity.deleted_at,
            )
```

**Acceptance Criteria**:
- [ ] All 6 mappers implemented (User, Account, Role, etc.)
- [ ] Bidirectional mapping (entity ↔ model) working
- [ ] Value objects converted to/from primitives
- [ ] Nested objects handled correctly
- [ ] Comprehensive unit tests for all mappers

---

#### Component: Use Cases

**Files Involved**:
- `app/application/use_cases/auth/register_user.py`
- `app/application/use_cases/auth/authenticate_user.py`
- `app/application/use_cases/accounts/create_account.py`
- (... ~15 use case files total)

**Purpose**: Orchestrate domain logic to fulfill specific user intentions. One use case per user action. Framework-agnostic, testable without infrastructure.

**Implementation Requirements**:

1. **Core Logic**:
   - Each use case is a class with `execute()` method
   - Receives UnitOfWork through constructor (DI)
   - Receives input as DTO
   - Returns output as DTO (or None)
   - Orchestrates domain entities and services
   - Manages transaction through UoW
   - No HTTP concerns (no status codes, headers)

2. **Data Handling**:
   - Input: DTO (Pydantic model) + context (e.g., current_user_id)
   - Output: DTO (Pydantic model) or None
   - State: Stateless (no instance variables except dependencies)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Entity not found → raise NotFoundError
   - [ ] Handle case: Unauthorized access → raise UnauthorizedError
   - [ ] Handle case: Business rule violation → raise domain exception
   - [ ] Validate: Input DTO is valid (Pydantic handles this)
   - [ ] Error: Raise domain/application exceptions (not HTTP exceptions)

4. **Dependencies**:
   - Internal: UnitOfWorkPort (Application layer)
   - Internal: Domain entities and services
   - Internal: DTOs (Application layer)
   - Internal: Domain exceptions
   - External: None (framework-agnostic)

5. **Testing Requirements**:
   - [ ] Unit test: Successful execution returns expected DTO
   - [ ] Unit test: Invalid input raises appropriate exception
   - [ ] Unit test: Unauthorized access raises UnauthorizedError
   - [ ] Unit test: Business rule violation raises domain exception
   - [ ] Integration test: Use case with real repositories and database
   - [ ] E2E test: Through API endpoint

**Example - CreateAccountUseCase**:
```python
# app/application/use_cases/accounts/create_account.py
from uuid import UUID, uuid4
from datetime import datetime

from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.application.dto.account_dto import CreateAccountInput, AccountOutput
from app.domain.entities.account import Account
from app.domain.value_objects.money import Money
from app.domain.value_objects.currency import Currency
from app.domain.exceptions.account_exceptions import AccountAlreadyExistsError


class CreateAccountUseCase:
    """Use case for creating a new financial account."""

    def __init__(self, uow: UnitOfWorkPort):
        self.uow = uow

    async def execute(
        self,
        input_dto: CreateAccountInput,
        current_user_id: UUID
    ) -> AccountOutput:
        """
        Create a new account for the current user.

        Args:
            input_dto: Account creation data
            current_user_id: ID of user creating the account

        Returns:
            Created account data

        Raises:
            AccountAlreadyExistsError: If account with same name exists for user
        """
        async with self.uow:
            # Check if account with same name already exists
            existing = await self.uow.accounts.find_by_user_and_name(
                user_id=current_user_id,
                name=input_dto.name
            )
            if existing:
                raise AccountAlreadyExistsError(
                    f"Account with name '{input_dto.name}' already exists"
                )

            # Create domain entity
            account = Account(
                id=uuid4(),
                user_id=current_user_id,
                name=input_dto.name,
                description=input_dto.description,
                balance=Money(amount=0, currency=Currency.USD),  # Start at zero
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deleted_at=None,
            )

            # Persist through repository
            saved_account = await self.uow.accounts.add(account)

            # Commit transaction
            await self.uow.commit()

            # Convert to output DTO
            return AccountOutput.from_entity(saved_account)
```

**Acceptance Criteria**:
- [ ] All 15+ use cases implemented
- [ ] Each use case is framework-agnostic
- [ ] All use cases receive UoW through constructor
- [ ] All use cases work with DTOs (input/output)
- [ ] Comprehensive unit tests with mocked repositories
- [ ] Integration tests with real database

---

#### Component: PostgreSQL Repository Implementations

**Files Involved**:
- `app/infrastructure/adapters/outbound/persistence/postgresql/repositories/user_repository.py`
- (... 5 more repository files)

**Purpose**: Implement repository port interfaces using PostgreSQL + SQLAlchemy. Handle all database operations and mapping.

**Implementation Requirements**:

1. **Core Logic**:
   - Implement repository port interface
   - Use SQLAlchemy AsyncSession for queries
   - Use mappers to convert model ↔ entity
   - Handle soft deletes transparently
   - Eager load relationships when needed
   - Return domain entities, not models

2. **Data Handling**:
   - Input: Domain entities, query parameters
   - Output: Domain entities or None
   - Use mappers for all conversions
   - Handle pagination correctly

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Entity not found → return None
   - [ ] Handle case: Unique constraint violation → raise domain exception
   - [ ] Handle case: Database connection error → raise infrastructure exception
   - [ ] Validate: Soft deletes filtered automatically
   - [ ] Error: Map SQLAlchemy exceptions to domain exceptions

4. **Dependencies**:
   - Internal: Repository port interface
   - Internal: SQLAlchemy models
   - Internal: Mappers
   - Internal: Domain entities
   - External: SQLAlchemy

5. **Testing Requirements**:
   - [ ] Unit test: Repository methods with mock session
   - [ ] Integration test: Repository against real PostgreSQL database
   - [ ] Integration test: Soft delete filtering works
   - [ ] Integration test: Eager loading avoids N+1 queries
   - [ ] Integration test: Concurrent access handling

**Example - PostgresUserRepository**:
```python
# app/infrastructure/adapters/outbound/persistence/postgresql/repositories/user_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.ports.outbound.user_repository_port import UserRepositoryPort
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import UserModel
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.user_mapper import UserMapper


class PostgresUserRepository:
    """PostgreSQL implementation of UserRepositoryPort."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, user: User) -> User:
        """Add a new user."""
        model = UserMapper.to_model(user)
        self._session.add(model)
        await self._session.flush()  # Get ID generated
        return UserMapper.to_entity(model)

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        stmt = (
            select(UserModel)
            .where(and_(
                UserModel.id == user_id,
                UserModel.deleted_at.is_(None)  # Soft delete filter
            ))
            .options(selectinload(UserModel.roles))  # Eager load roles
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return UserMapper.to_entity(model)

    async def get_by_email(self, email: Email) -> Optional[User]:
        """Get user by email."""
        stmt = (
            select(UserModel)
            .where(and_(
                UserModel.email == email.value,
                UserModel.deleted_at.is_(None)
            ))
            .options(selectinload(UserModel.roles))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return UserMapper.to_entity(model)

    async def update(self, user: User) -> User:
        """Update existing user."""
        # Load existing model
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        existing_model = result.scalar_one()

        # Update model using mapper
        updated_model = UserMapper.to_model(user, existing_model=existing_model)
        await self._session.flush()

        return UserMapper.to_entity(updated_model)

    async def exists_by_email(self, email: Email) -> bool:
        """Check if user with email exists."""
        stmt = select(UserModel.id).where(and_(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None)
        ))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ... other methods
```

**Acceptance Criteria**:
- [ ] All 6 repositories implement their port interfaces
- [ ] All repositories use mappers for entity ↔ model conversion
- [ ] Soft delete filtering applied automatically
- [ ] Eager loading used to prevent N+1 queries
- [ ] Integration tests verify all repository operations

---

#### Component: FastAPI Routes (Inbound Adapters)

**Files Involved**:
- `app/infrastructure/adapters/inbound/api/routes/auth.py`
- `app/infrastructure/adapters/inbound/api/routes/users.py`
- `app/infrastructure/adapters/inbound/api/routes/accounts.py`
- `app/infrastructure/adapters/inbound/api/routes/audit_logs.py`

**Purpose**: Thin HTTP layer that converts HTTP requests to use case calls and DTOs to HTTP responses. All HTTP concerns isolated here.

**Implementation Requirements**:

1. **Core Logic**:
   - Define FastAPI route decorators
   - Validate HTTP requests with Pydantic schemas (API schemas, not DTOs)
   - Convert API schemas → DTOs
   - Call appropriate use case
   - Convert DTOs → API schemas
   - Handle HTTP-specific concerns (status codes, headers)
   - Convert domain exceptions → HTTP exceptions

2. **Data Handling**:
   - Input: HTTP request (JSON, query params, path params)
   - Output: HTTP response (JSON, status code)
   - Convert API schemas ↔ DTOs explicitly

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Validation error → 422 Unprocessable Entity
   - [ ] Handle case: NotFoundError → 404 Not Found
   - [ ] Handle case: UnauthorizedError → 401 Unauthorized
   - [ ] Handle case: PermissionError → 403 Forbidden
   - [ ] Validate: API schemas validate HTTP payloads
   - [ ] Error: Exception handlers convert domain errors to HTTP

4. **Dependencies**:
   - Internal: Use cases (Application layer)
   - Internal: DTOs (Application layer)
   - Internal: API schemas (Infrastructure layer)
   - External: FastAPI

5. **Testing Requirements**:
   - [ ] Unit test: Route converts request to DTO correctly
   - [ ] Unit test: Route converts DTO to response correctly
   - [ ] Integration test: Route with mock use case
   - [ ] E2E test: Full request through API with real database

**Example - Account Routes**:
```python
# app/infrastructure/adapters/inbound/api/routes/accounts.py
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, status, Request

from app.infrastructure.adapters.inbound.api.schemas.account_schemas import (
    CreateAccountRequest,
    AccountResponse,
    UpdateAccountRequest,
)
from app.infrastructure.adapters.inbound.api.dependencies import (
    get_current_user_id,
    get_create_account_use_case,
    get_get_account_use_case,
    get_update_account_use_case,
)
from app.application.use_cases.accounts.create_account import CreateAccountUseCase
from app.application.use_cases.accounts.get_account import GetAccountUseCase
from app.application.dto.account_dto import CreateAccountInput


router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account"
)
async def create_account(
    request: Request,
    payload: CreateAccountRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    use_case: Annotated[CreateAccountUseCase, Depends(get_create_account_use_case)],
) -> AccountResponse:
    """
    Create a new financial account for the current user.

    - **name**: Account name (must be unique for user)
    - **description**: Optional account description
    """
    # Convert API schema to DTO
    input_dto = CreateAccountInput(
        name=payload.name,
        description=payload.description,
    )

    # Execute use case
    output_dto = await use_case.execute(input_dto, current_user_id)

    # Convert DTO to API response
    return AccountResponse(
        id=output_dto.id,
        user_id=output_dto.user_id,
        name=output_dto.name,
        description=output_dto.description,
        balance=output_dto.balance,
        currency=output_dto.currency,
        is_active=output_dto.is_active,
        created_at=output_dto.created_at,
        updated_at=output_dto.updated_at,
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account details"
)
async def get_account(
    account_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    use_case: Annotated[GetAccountUseCase, Depends(get_get_account_use_case)],
) -> AccountResponse:
    """Get details of a specific account."""
    output_dto = await use_case.execute(account_id, current_user_id)

    return AccountResponse(
        id=output_dto.id,
        user_id=output_dto.user_id,
        name=output_dto.name,
        description=output_dto.description,
        balance=output_dto.balance,
        currency=output_dto.currency,
        is_active=output_dto.is_active,
        created_at=output_dto.created_at,
        updated_at=output_dto.updated_at,
    )
```

**Acceptance Criteria**:
- [ ] All existing endpoints migrated to new structure
- [ ] Routes are thin (no business logic)
- [ ] API schemas separate from DTOs
- [ ] Exception handlers convert domain errors to HTTP
- [ ] E2E tests pass for all endpoints

---

### 3.2 Dependency Injection Setup

#### Component: DI Container

**Files Involved**:
- `app/infrastructure/config/di_container.py`
- `app/infrastructure/adapters/inbound/api/dependencies.py`

**Purpose**: Configure dependency injection for the entire application, providing framework-agnostic DI that doesn't leak into Application layer.

**Implementation Requirements**:

1. **Core Logic**:
   - Use `dependency-injector` library for IoC container
   - Configure providers for all dependencies
   - Support different configurations per environment (dev, prod, test)
   - Integrate with FastAPI's `Depends()` at API boundary only

2. **Providers to Configure**:
   - Database session factory
   - Unit of Work instances
   - Use case instances
   - Current user extraction
   - Settings and configuration

3. **Example - DI Container**:
```python
# app/infrastructure/config/di_container.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.infrastructure.config.settings import Settings
from app.infrastructure.adapters.outbound.persistence.postgresql.unit_of_work import PostgresUnitOfWork
from app.application.use_cases.accounts.create_account import CreateAccountUseCase
# ... other use case imports


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""

    # Configuration
    config = providers.Configuration()

    # Settings
    settings = providers.Singleton(Settings)

    # Database
    engine = providers.Singleton(
        create_async_engine,
        settings.provided.DATABASE_URL,
        echo=settings.provided.DEBUG,
    )

    session_factory = providers.Singleton(
        async_sessionmaker,
        engine,
        expire_on_commit=False,
    )

    # Unit of Work
    unit_of_work = providers.Factory(
        PostgresUnitOfWork,
        session_factory=session_factory,
    )

    # Use Cases
    create_account_use_case = providers.Factory(
        CreateAccountUseCase,
        uow=unit_of_work,
    )

    # ... other use cases
```

**Acceptance Criteria**:
- [ ] DI container configured with all dependencies
- [ ] Use cases instantiated with correct dependencies
- [ ] Easy to swap implementations (e.g., for testing)
- [ ] No FastAPI dependencies in Application layer

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Foundation & Domain Layer (Size: L, Priority: P0)

**Goal**: Establish pure domain layer with zero external dependencies, creating the architectural foundation.

**Duration**: 4-5 days

**Scope**:
- ✅ Include: Domain entities, value objects, domain services, domain exceptions
- ❌ Exclude: Application layer, infrastructure, database integration

**Components to Implement**:
- [ ] Domain entities (User, Account, Role, AccountShare, AuditLog)
- [ ] Value objects (Email, Username, Money, Currency, Permission, PasswordHash)
- [ ] Domain services (PermissionChecker, AccountSharingService, UserValidationService)
- [ ] Domain exceptions hierarchy

**Detailed Tasks**:

1. [ ] Create directory structure for domain layer
   - Create `app/domain/entities/`, `value_objects/`, `services/`, `exceptions/`
   - Add `__init__.py` files with proper exports

2. [ ] Implement value objects (Day 1)
   - Email with regex validation
   - Username with length validation
   - Money with currency support
   - Currency enum (ISO 4217 codes)
   - Permission enum/class
   - PasswordHash (immutable, cannot be created from plain text)
   - Write unit tests for each value object (~50 tests total)

3. [ ] Implement domain entities (Day 2-3)
   - User entity with business methods
   - Account entity with ownership logic
   - Role entity with permission checking
   - AccountShare entity with expiration logic
   - AuditLog entity (immutable)
   - Write unit tests for each entity (~100 tests total)

4. [ ] Implement domain services (Day 3-4)
   - PermissionChecker: Centralized permission logic
   - AccountSharingService: Account sharing business rules
   - UserValidationService: Complex user validations
   - Write unit tests for each service (~30 tests total)

5. [ ] Implement domain exceptions (Day 4)
   - Base domain exception
   - User domain exceptions (InvalidEmailError, etc.)
   - Account domain exceptions
   - Permission domain exceptions
   - Write tests for exception hierarchy

6. [ ] Verify domain layer isolation (Day 5)
   - Run import analysis (no SQLAlchemy, FastAPI, etc.)
   - Run all domain tests (should be fast, <1 second)
   - Verify 100% test coverage for domain layer
   - Document domain model in `docs/architecture/domain-model.md`

**Dependencies**:
- Requires: None (this is the foundation)
- Blocks: All other phases depend on this

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (180+ pure unit tests)
- [ ] Domain layer has zero external dependencies (verified with import checker)
- [ ] Test execution time <1 second for entire domain test suite
- [ ] Code coverage 100% for domain layer
- [ ] Documentation complete

**Risk Factors**:
- **Value object design complexity**: Mitigation - Start simple, refactor later
- **Entity business logic unclear**: Mitigation - Refer to current service code for rules
- **Over-engineering domain services**: Mitigation - Extract only complex logic, keep entities rich

**Estimated Effort**: 4-5 days for 1 developer

---

#### Phase 2: Application Layer & Ports (Size: M, Priority: P0)

**Goal**: Define contracts (ports) and implement use cases, making business logic testable without infrastructure.

**Duration**: 3-4 days

**Scope**:
- ✅ Include: Repository ports, UoW port, use cases, DTOs, application exceptions
- ❌ Exclude: Infrastructure implementations (PostgreSQL, FastAPI routes)

**Components to Implement**:
- [ ] Repository port interfaces (Protocol or ABC)
- [ ] Unit of Work port interface
- [ ] Data Transfer Objects (DTOs)
- [ ] Use case implementations
- [ ] Application exceptions

**Detailed Tasks**:

1. [ ] Define repository port interfaces (Day 1)
   - UserRepositoryPort with all CRUD methods
   - AccountRepositoryPort
   - RoleRepositoryPort
   - AccountShareRepositoryPort
   - AuditLogRepositoryPort
   - RefreshTokenRepositoryPort
   - Use `typing.Protocol` for structural typing
   - Document each method with docstrings

2. [ ] Define Unit of Work port interface (Day 1)
   - UnitOfWorkPort with repository properties
   - Async context manager protocol
   - Commit/rollback methods
   - Document transaction semantics

3. [ ] Create DTOs for all use cases (Day 2)
   - Auth DTOs (RegisterUserInput, LoginOutput, etc.)
   - User DTOs (UserProfileOutput, UpdateUserInput, etc.)
   - Account DTOs (AccountOutput, CreateAccountInput, etc.)
   - Audit DTOs (AuditLogOutput, QueryAuditInput, etc.)
   - Use Pydantic for validation
   - Separate input and output DTOs

4. [ ] Implement authentication use cases (Day 2-3)
   - RegisterUserUseCase
   - AuthenticateUserUseCase
   - RefreshTokenUseCase
   - LogoutUserUseCase
   - ChangePasswordUseCase
   - Write unit tests with mocked repositories (~40 tests)

5. [ ] Implement user management use cases (Day 3)
   - GetUserProfileUseCase
   - UpdateUserProfileUseCase
   - DeleteUserUseCase
   - ListUsersUseCase (admin)
   - Write unit tests with mocked repositories (~30 tests)

6. [ ] Implement account management use cases (Day 3-4)
   - CreateAccountUseCase
   - GetAccountUseCase
   - UpdateAccountUseCase
   - DeleteAccountUseCase
   - ListUserAccountsUseCase
   - ShareAccountUseCase
   - Write unit tests with mocked repositories (~40 tests)

7. [ ] Implement audit use cases (Day 4)
   - CreateAuditLogUseCase
   - QueryAuditLogsUseCase
   - Write unit tests (~10 tests)

8. [ ] Create application exceptions (Day 4)
   - NotFoundError
   - UnauthorizedError
   - ForbiddenError
   - AlreadyExistsError
   - ValidationError (application-level)

**Dependencies**:
- Requires: Phase 1 (Domain layer) complete
- Blocks: Phase 3 (Infrastructure adapters)

**Validation Criteria** (Phase complete when):
- [ ] All repository ports defined with complete interfaces
- [ ] All 15+ use cases implemented
- [ ] All use cases have unit tests with mocked repositories (120+ tests)
- [ ] Test execution time <5 seconds (no database)
- [ ] Code coverage 90%+ for application layer
- [ ] Use cases are framework-agnostic (no FastAPI imports)

**Risk Factors**:
- **DTO proliferation**: Mitigation - Reuse DTOs where possible, use inheritance
- **Mock complexity**: Mitigation - Create simple in-memory repository implementations for tests
- **Use case granularity**: Mitigation - One use case per user action, not per CRUD operation

**Estimated Effort**: 3-4 days for 1 developer

---

#### Phase 3: Infrastructure - PostgreSQL Adapters (Size: L, Priority: P0)

**Goal**: Implement outbound adapters (repositories, UoW, mappers) using PostgreSQL, maintaining database isolation.

**Duration**: 4-5 days

**Scope**:
- ✅ Include: SQLAlchemy models, mappers, repository implementations, UoW implementation
- ❌ Exclude: API routes (separate phase)

**Components to Implement**:
- [ ] SQLAlchemy models (ORM models, not domain entities)
- [ ] Entity ↔ Model mappers
- [ ] PostgreSQL repository implementations
- [ ] PostgreSQL Unit of Work implementation
- [ ] Database session management

**Detailed Tasks**:

1. [ ] Create SQLAlchemy models (Day 1)
   - UserModel (keep existing, move to new location)
   - AccountModel
   - RoleModel
   - AccountShareModel
   - AuditLogModel
   - RefreshTokenModel
   - Move to `app/infrastructure/adapters/outbound/persistence/postgresql/models/`
   - Remove business logic (pure data models)

2. [ ] Implement mappers (Day 1-2)
   - UserMapper (entity ↔ model)
   - AccountMapper
   - RoleMapper
   - AccountShareMapper
   - AuditLogMapper
   - RefreshTokenMapper
   - Handle value object conversions
   - Write unit tests for each mapper (~40 tests)

3. [ ] Implement repository base class (Day 2)
   - Generic BaseRepository with common CRUD operations
   - Soft delete filtering
   - Pagination support
   - Use mappers for conversions

4. [ ] Implement specialized repositories (Day 2-3)
   - PostgresUserRepository
   - PostgresAccountRepository
   - PostgresRoleRepository
   - PostgresAccountShareRepository
   - PostgresAuditLogRepository
   - PostgresRefreshTokenRepository
   - Use eager loading to avoid N+1 queries
   - Write integration tests for each repository (~60 tests with DB)

5. [ ] Implement Unit of Work (Day 3-4)
   - PostgresUnitOfWork with async context manager
   - Initialize all repositories with shared session
   - Commit/rollback logic
   - Write integration tests (~20 tests)

6. [ ] Update database session management (Day 4)
   - Create session factory in `session.py`
   - Configure connection pooling
   - Integration with UoW

7. [ ] Update Alembic migrations (Day 4-5)
   - No schema changes needed (models same)
   - Verify migrations still work
   - Update import paths if needed

8. [ ] Integration testing (Day 5)
   - Test all repositories against real PostgreSQL
   - Test UoW transaction behavior (commit/rollback)
   - Test concurrent access
   - Verify no N+1 query problems

**Dependencies**:
- Requires: Phase 2 (Application layer) complete
- Blocks: Phase 4 (API adapters)

**Validation Criteria** (Phase complete when):
- [ ] All repository port interfaces implemented
- [ ] All mappers bidirectional and tested
- [ ] Unit of Work manages transactions correctly
- [ ] Integration tests pass (120+ tests with DB)
- [ ] No N+1 query problems (verified with query logs)
- [ ] Code coverage 85%+ for infrastructure persistence layer

**Risk Factors**:
- **Mapper complexity**: Mitigation - Start with simple entities, add complexity incrementally
- **Transaction management bugs**: Mitigation - Comprehensive rollback tests
- **Performance regression**: Mitigation - Benchmark queries, use eager loading

**Estimated Effort**: 4-5 days for 1 developer

---

#### Phase 4: Infrastructure - API Adapters (Size: M, Priority: P0)

**Goal**: Refactor FastAPI routes to use new use cases, DTOs, and dependency injection.

**Duration**: 2-3 days

**Scope**:
- ✅ Include: FastAPI routes, API schemas, exception handlers, DI setup
- ❌ Exclude: New API features (focus on existing endpoints)

**Components to Implement**:
- [ ] API schemas (Pydantic models for HTTP, separate from DTOs)
- [ ] Exception handlers (domain → HTTP)
- [ ] Refactored routes using use cases
- [ ] Dependency injection setup
- [ ] DI container configuration

**Detailed Tasks**:

1. [ ] Set up DI container (Day 1)
   - Install `dependency-injector`
   - Create `Container` in `di_container.py`
   - Configure providers for UoW, use cases, settings
   - Write tests for DI container

2. [ ] Create API schemas (Day 1)
   - Auth API schemas (separate from DTOs)
   - User API schemas
   - Account API schemas
   - Audit API schemas
   - Use Pydantic with examples for OpenAPI docs

3. [ ] Create exception handlers (Day 1)
   - Global exception handler
   - Domain exception → HTTP mapping
   - NotFoundError → 404
   - UnauthorizedError → 401
   - PermissionError → 403
   - AlreadyExistsError → 409
   - ValidationError → 422
   - Write tests for exception handlers

4. [ ] Refactor authentication routes (Day 2)
   - Register endpoint using RegisterUserUseCase
   - Login endpoint using AuthenticateUserUseCase
   - Refresh endpoint using RefreshTokenUseCase
   - Logout endpoint using LogoutUserUseCase
   - Change password endpoint using ChangePasswordUseCase
   - Convert API schemas ↔ DTOs
   - Update E2E tests

5. [ ] Refactor user routes (Day 2)
   - Profile endpoints using user use cases
   - Admin endpoints using user use cases
   - Update E2E tests

6. [ ] Refactor account routes (Day 3)
   - CRUD endpoints using account use cases
   - List endpoints with pagination
   - Update E2E tests

7. [ ] Refactor audit routes (Day 3)
   - Query endpoints using audit use cases
   - Update E2E tests

8. [ ] Update dependencies.py (Day 3)
   - Integrate DI container with FastAPI
   - get_current_user_id using JWT utilities
   - Use case factories using DI container
   - Clean up old dependency functions

**Dependencies**:
- Requires: Phase 3 (PostgreSQL adapters) complete
- Blocks: None (this completes core refactoring)

**Validation Criteria** (Phase complete when):
- [ ] All existing API endpoints migrated
- [ ] All E2E tests pass (40+ API tests)
- [ ] API contracts unchanged (backward compatible)
- [ ] Exception handling consistent
- [ ] DI container working correctly
- [ ] OpenAPI docs still accurate

**Risk Factors**:
- **Breaking API contracts**: Mitigation - Run all existing E2E tests
- **DI complexity**: Mitigation - Keep DI at infrastructure boundary only
- **Testing gaps**: Mitigation - Verify E2E test coverage before starting

**Estimated Effort**: 2-3 days for 1 developer

---

#### Phase 5: Testing & Verification (Size: M, Priority: P1)

**Goal**: Comprehensive testing, refactor existing tests, verify architecture compliance.

**Duration**: 2-3 days

**Scope**:
- ✅ Include: Test refactoring, architecture validation, documentation
- ❌ Exclude: New features

**Detailed Tasks**:

1. [ ] Refactor existing tests (Day 1)
   - Separate unit tests (no DB) from integration tests (with DB)
   - Move tests to correct directories (unit/, integration/, e2e/)
   - Create in-memory repository implementations for unit tests
   - Update fixtures and factories

2. [ ] Create test factories (Day 1)
   - Domain entity factories using factory_boy
   - DTO factories
   - SQLAlchemy model factories
   - Write tests for factories

3. [ ] Add missing unit tests (Day 2)
   - Domain layer: Verify 100% coverage
   - Application layer: Verify 90%+ coverage
   - Target: 200+ pure unit tests (no DB)

4. [ ] Add missing integration tests (Day 2)
   - Repository operations
   - UoW transaction behavior
   - Use cases with real database
   - Target: 150+ integration tests

5. [ ] Architecture validation (Day 3)
   - Write import checker script
   - Verify domain layer has zero external dependencies
   - Verify application layer only depends on domain
   - Verify infrastructure layer depends on both
   - Add to CI pipeline

6. [ ] Performance testing (Day 3)
   - Benchmark unit test suite (<5s target)
   - Benchmark integration test suite (<30s target)
   - Benchmark E2E test suite (<60s target)
   - Identify and fix slow tests

7. [ ] Documentation (Day 3)
   - Update README with new architecture
   - Create hexagonal architecture diagram
   - Document migration process
   - Create ADR (Architecture Decision Record)

**Dependencies**:
- Requires: Phase 4 (API adapters) complete
- Blocks: None (final phase)

**Validation Criteria** (Phase complete when):
- [ ] 200+ pure unit tests (no DB, <5s execution)
- [ ] 150+ integration tests (<30s execution)
- [ ] 40+ E2E tests (<60s execution)
- [ ] Overall code coverage 90%+
- [ ] Architecture compliance verified (automated check)
- [ ] Documentation complete and accurate

**Risk Factors**:
- **Test complexity**: Mitigation - Use factories for test data
- **Slow test suite**: Mitigation - Parallelize tests, optimize fixtures
- **Documentation drift**: Mitigation - Generate diagrams from code where possible

**Estimated Effort**: 2-3 days for 1 developer

---

### 4.2 Implementation Sequence

```
Phase 1: Foundation & Domain Layer (P0, 4-5 days)
    ↓ (must complete before next)
Phase 2: Application Layer & Ports (P0, 3-4 days)
    ↓ (must complete before next)
Phase 3: Infrastructure - PostgreSQL Adapters (P0, 4-5 days)
    ↓ (must complete before next)
Phase 4: Infrastructure - API Adapters (P0, 2-3 days)
    ↓ (must complete before next)
Phase 5: Testing & Verification (P1, 2-3 days)
```

**Total Duration**: 15-20 days (3-4 weeks)

**Rationale for ordering**:
- **Phase 1 first**: Domain layer is the foundation, everything depends on it
- **Phase 2 depends on Phase 1**: Use cases need domain entities
- **Phase 3 depends on Phase 2**: Repository implementations need port interfaces
- **Phase 4 depends on Phase 3**: API routes need working use cases and repositories
- **Phase 5 last**: Comprehensive testing after all components implemented

**Quick Wins** (if applicable):
- After Phase 2: Domain and application layers fully testable without database
- After Phase 3: Can test full stack except API layer
- After Phase 4: All existing features working with new architecture

**Parallel Work Opportunities**:
- None for initial refactoring (phases are sequential due to dependencies)
- After Phase 2 complete: Can start API schema design (Phase 4) while implementing Phase 3

---

## 5. Simplicity & Design Validation

### Simplicity Checklist:

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes: Hexagonal architecture is a proven pattern for database independence
  - No over-engineering: Not adding microservices, event sourcing, or CQRS unless needed
  - Incremental: Refactoring existing code, not rewriting from scratch

- [x] **Have we avoided premature optimization?**
  - Yes: Focusing on architecture and testability, not performance
  - No premature caching or complex performance optimizations
  - Will profile and optimize only if issues arise

- [x] **Does this align with existing patterns in the codebase?**
  - Yes: Current layered structure (Routes → Services → Repositories) is similar
  - Evolution, not revolution: Building on existing patterns
  - Async/await patterns preserved throughout

- [x] **Can we deliver value in smaller increments?**
  - Yes: 5 phases with clear validation criteria
  - Each phase deliverable and testable independently
  - Functionality preserved throughout refactoring

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes: Current 80-90% coupling to SQLAlchemy prevents testing without DB
  - Yes: Business logic mixed with persistence is hard to maintain
  - Yes: Cannot swap data sources without changing multiple layers
  - Requirements come from explicit feature description file

### Alternatives Considered:

**Alternative 1: Keep Current Layered Architecture**
- **Description**: Improve current structure without full hexagonal refactoring
- **Pros**: Less work, less risk, familiar to team
- **Cons**: Still tightly coupled to database, cannot test without infrastructure, harder to maintain
- **Why not chosen**: Does not achieve database independence or pure domain testing goals

**Alternative 2: Microservices Architecture**
- **Description**: Split into multiple services with separate databases
- **Pros**: Better scalability, independent deployment
- **Cons**: Much higher complexity, distributed system challenges, premature for current scale
- **Why not chosen**: Over-engineering for current needs, can extract microservices later from hexagonal architecture

**Alternative 3: Event-Driven Architecture**
- **Description**: Use event sourcing and CQRS with event bus
- **Pros**: Audit trail, scalability, temporal queries
- **Cons**: Extremely complex, steep learning curve, harder to debug
- **Why not chosen**: Overkill for current requirements, adds unnecessary complexity

**Alternative 4: Keep SQLAlchemy models as domain entities**
- **Description**: Use SQLAlchemy models directly in domain, add business logic to them
- **Pros**: Less mapping code, less duplication
- **Cons**: Domain tightly coupled to database, cannot test without DB, hard to switch data sources
- **Why not chosen**: Does not achieve database independence goal

### Rationale for Hexagonal Architecture:

1. **Database Independence**: Can swap PostgreSQL for MongoDB/API by changing only Infrastructure layer
2. **Testability**: Domain and application logic testable in <100ms without database
3. **Maintainability**: Clear boundaries between layers, easier to understand and modify
4. **Industry Standard**: Proven pattern used by many successful projects
5. **Incremental Adoption**: Can refactor in phases without breaking existing functionality
6. **Future-Proof**: Enables microservices extraction, multiple UIs, batch processing without changes to core logic

---

## 6. References & Related Documents

### Internal Documentation:
- `.claude/analysis/SUMMARY.md` - Current codebase analysis
- `.claude/analysis/codebase_analysis.md` - Detailed component breakdown
- `.claude/analysis/architecture_diagrams.md` - Current architecture diagrams
- `.claude/standards/backend.md` - Backend development standards
- `.claude/standards/testing.md` - Testing standards
- `.features/descriptions/hexagonal-architecture.md` - Original feature requirements

### External Resources:

**Hexagonal Architecture (Ports & Adapters)**:
- [Alistair Cockburn - Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Original pattern description
- [Netflix Tech Blog - Ready for changes with Hexagonal Architecture](https://netflixtechblog.com/ready-for-changes-with-hexagonal-architecture-b315ec967749)
- [Herberto Graça - DDD, Hexagonal, Onion, Clean, CQRS](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/)

**Unit of Work Pattern**:
- [Cosmic Python - Unit of Work Pattern](https://www.cosmicpython.com/book/chapter_06_uow.html) - Comprehensive Python implementation
- [Martin Fowler - Unit of Work](https://martinfowler.com/eaaCatalog/unitOfWork.html) - Pattern description
- [Architecture Patterns with Python - O'Reilly](https://www.oreilly.com/library/view/architecture-patterns-with/9781492052197/) - Complete book on patterns

**Domain-Driven Design**:
- [Eric Evans - Domain-Driven Design (Blue Book)](https://www.domainlanguage.com/ddd/) - DDD bible
- [Vaughn Vernon - Implementing Domain-Driven Design (Red Book)](https://www.informit.com/store/implementing-domain-driven-design-9780321834577) - Practical DDD
- [Domain-Driven Design Distilled](https://www.informit.com/store/domain-driven-design-distilled-9780134434421) - Quick DDD intro

**Python Implementation Examples**:
- [Cosmic Python - Architecture Patterns with Python](https://www.cosmicpython.com/) - Free online book
- [GitHub: ivan-borovets/fastapi-clean-example](https://github.com/ivan-borovets/fastapi-clean-example) - FastAPI Clean Architecture
- [GitHub: NEONKID/fastapi-ddd-example](https://github.com/NEONKID/fastapi-ddd-example) - FastAPI DDD with async
- [GitHub: GArmane/python-fastapi-hex-todo](https://github.com/GArmane/python-fastapi-hex-todo) - Hexagonal FastAPI example

**Testing & Clean Code**:
- [Growing Object-Oriented Software, Guided by Tests](http://www.growing-object-oriented-software.com/) - TDD with mocks
- [Working Effectively with Legacy Code - Michael Feathers](https://www.oreilly.com/library/view/working-effectively-with/0131177052/) - Refactoring strategies
- [Pytest Documentation](https://docs.pytest.org/) - Pytest best practices

**SQLAlchemy & Async Python**:
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) - ORM and async patterns
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI best practices
- [Real Python - Async IO in Python](https://realpython.com/async-io-python/) - Async patterns

**Dependency Injection**:
- [Dependency Injector Documentation](https://python-dependency-injector.ets-labs.org/) - Python DI container
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/) - FastAPI's built-in DI

### Videos & Talks:
- [Ian Cooper - TDD, Where Did It All Go Wrong](https://www.youtube.com/watch?v=EZ05e7EMOLM) - Testing best practices
- [Robert C. Martin - Clean Architecture and Design](https://www.youtube.com/watch?v=2dKZ-dWaCiU) - Architecture principles
- [Kevlin Henney - The Art of Code](https://www.youtube.com/watch?v=gdSlcxxYAA8) - Clean code principles

---

**Document Version**: 1.0
**Last Updated**: November 5, 2025
**Status**: Ready for Implementation
**Approvers**: [To be filled by team]
**Next Review Date**: After Phase 1 completion

---

## Appendix A: Glossary

**Domain Layer**: Core business logic with zero external dependencies. Contains entities, value objects, and domain services.

**Application Layer**: Use cases and port interfaces. Orchestrates domain logic. Depends only on domain layer.

**Infrastructure Layer**: Framework and technology-specific code. Adapters for databases, APIs, HTTP. Depends on application and domain layers.

**Entity**: Object with unique identity (e.g., User, Account). Mutable and contains business logic.

**Value Object**: Object defined by its value, not identity (e.g., Email, Money). Immutable.

**Port**: Interface defining a contract. Inbound ports (service interfaces) or outbound ports (repository interfaces).

**Adapter**: Implementation of a port. Inbound adapters (API routes) or outbound adapters (repositories).

**Use Case**: Single user action orchestrated by application layer (e.g., "Register User", "Create Account").

**DTO (Data Transfer Object)**: Simple object for passing data between layers. Contains no business logic.

**Unit of Work**: Manages transaction boundaries and coordinates repository operations.

**Repository**: Abstraction for data access. Works with domain entities, hides database details.

**Mapper**: Converts between domain entities and database models (or DTOs and API schemas).

**Aggregate**: Cluster of entities and value objects treated as a single unit for data changes.

**Domain Service**: Business logic that doesn't naturally fit in an entity or value object.

---

## Appendix B: Migration Checklist

Use this checklist during implementation to ensure nothing is missed:

### Phase 1: Domain Layer
- [ ] Directory structure created
- [ ] All 6 value objects implemented and tested
- [ ] All 5 domain entities implemented and tested
- [ ] 3 domain services implemented and tested
- [ ] Domain exceptions created
- [ ] Zero external dependencies verified
- [ ] 100% test coverage achieved
- [ ] Documentation complete

### Phase 2: Application Layer
- [ ] All 6 repository ports defined
- [ ] Unit of Work port defined
- [ ] All DTOs created
- [ ] All 15+ use cases implemented
- [ ] Application exceptions created
- [ ] All use cases tested with mocks
- [ ] Framework-agnostic verified
- [ ] 90%+ test coverage achieved

### Phase 3: PostgreSQL Adapters
- [ ] All SQLAlchemy models moved/updated
- [ ] All 6 mappers implemented and tested
- [ ] Base repository created
- [ ] All 6 specialized repositories implemented
- [ ] Unit of Work implemented
- [ ] Session management updated
- [ ] Migrations verified
- [ ] Integration tests pass
- [ ] No N+1 queries verified

### Phase 4: API Adapters
- [ ] DI container configured
- [ ] All API schemas created
- [ ] Exception handlers implemented
- [ ] Auth routes refactored
- [ ] User routes refactored
- [ ] Account routes refactored
- [ ] Audit routes refactored
- [ ] dependencies.py updated
- [ ] All E2E tests pass

### Phase 5: Testing & Verification
- [ ] Tests reorganized (unit/integration/e2e)
- [ ] Test factories created
- [ ] Missing unit tests added
- [ ] Missing integration tests added
- [ ] Architecture compliance verified
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] ADR created

### Final Verification
- [ ] All existing API tests pass
- [ ] All new tests pass
- [ ] Code coverage 90%+
- [ ] Domain layer has zero external dependencies
- [ ] Test suite fast (<100s total)
- [ ] Documentation complete
- [ ] Team review completed
- [ ] Deployment plan ready
