# Implementation Plan: Personal Finance Platform - Phase 1 Foundation

**Date:** October 29, 2025  
**Project:** Emerald Personal Finance Platform - Backend Foundation  
**Feature Description:** `.features/descriptions/phase-1.md`  
**Research Document:** `.features/research/20251029_personal-finance-platform-phase1-foundation.md`  
**Plan Version:** 1.0  
**Status:** Ready for Implementation

---

## 1. Executive Summary

This implementation plan details the construction of a production-grade FastAPI backend foundation for the Emerald personal finance platform. Phase 1 establishes the core infrastructure including user management, JWT-based authentication with refresh token rotation, role-based access control (RBAC), comprehensive audit logging, and security measures required for a financial application.

### Primary Objectives

1. **Secure Authentication System**: Implement JWT-based authentication with access/refresh token pattern, refresh token rotation, and Argon2id password hashing
2. **User Management**: Full CRUD operations with soft deletes, role-based permissions, and profile management
3. **Audit Logging**: Comprehensive, immutable logging of all data modifications and authentication events for compliance (GDPR, potential PCI DSS)
4. **Production-Ready Infrastructure**: Async-first FastAPI application with PostgreSQL, proper error handling, rate limiting, and 80%+ test coverage
5. **Security-First Design**: Rate limiting, RBAC, security headers, input validation, and defense-in-depth architecture

### Expected Outcomes

- **Functional**: Users can register, login, manage profiles, and perform authenticated operations
- **Security**: Bank-grade security with comprehensive audit trails, rate limiting, and proper authorization
- **Performance**: Async architecture supporting 2-5x throughput compared to synchronous alternatives
- **Maintainability**: Clean architecture with separated concerns (routes → services → repositories → models)
- **Testability**: 80%+ code coverage with unit, integration, and e2e tests

### Success Criteria

- All Phase 1 requirements implemented and tested (see Section 11)
- 80%+ test coverage across services and repositories
- All security requirements met (Argon2id hashing, JWT rotation, rate limiting, RBAC)
- API response times: p95 <200ms, p99 <500ms (local development)
- Complete API documentation via Swagger/ReDoc
- Production-ready Docker containerization

---

## 2. Research Context Summary

This implementation incorporates findings from comprehensive research (`.features/research/20251029_personal-finance-platform-phase1-foundation.md`).

### Key Research-Backed Decisions

**Technology Stack Validation**:
- FastAPI 0.115+ with async SQLAlchemy 2.0 delivers 2-5x throughput improvement
- PostgreSQL 16+ with asyncpg driver provides best performance for async operations
- Stack is battle-tested in production (Netflix, Uber, Microsoft use FastAPI)

**Argon2id Over bcrypt** (Critical Decision):
- **NIST-recommended** for password hashing (2025 standard)
- **OWASP primary choice** for new implementations
- **Memory-hard**: 64MB vs bcrypt's 4KB (resistant to GPU/ASGI attacks)
- Configuration: `time_cost=2`, `memory_cost=65536`, `parallelism=4`

**JWT Refresh Token Rotation**:
- Access tokens: 15-30 minutes (balance security and UX)
- Refresh tokens: 7 days with rotation on every use
- Reuse detection via `token_family_id` (invalidate chain on compromise)
- Storage: HttpOnly cookies (web) to prevent XSS attacks

**Audit Logging for GDPR Compliance**:
- Log all data access and modifications with before/after values
- 7-year retention for financial data (SOX compliance)
- Immutable logs (write-once, no updates/deletes)
- Users can view their own audit logs (GDPR right to access)

**Rate Limiting Strategy**:
- Login: 5 attempts / 15 minutes (brute force prevention)
- Registration: 3 attempts / hour (spam prevention)
- Password change: 3 attempts / hour (unauthorized change prevention)
- Token refresh: 10 attempts / hour (token exhaustion prevention)
- General API: 100 requests / minute per user (fair usage)

**Soft Delete Pattern**:
- Regulatory requirement: Must retain data for 7+ years
- Accidental deletion recovery capability
- Implemented via `deleted_at` timestamp with partial unique indexes

---

## 3. Technical Architecture

### 3.1 System Design Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Client (Web/Mobile)                       │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTPS
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Middleware Layer                          │  │
│  │  • CORS          • Request ID    • Audit Logging      │  │
│  │  • Rate Limiting • Error Handler • Security Headers   │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Route Layer (HTTP)                        │  │
│  │  /api/v1/auth/*  │  /api/v1/users/*                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │          Service Layer (Business Logic)                │  │
│  │  AuthService  │  UserService  │  AuditService          │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │       Repository Layer (Database Operations)           │  │
│  │  UserRepo  │  AuditRepo  │  RefreshTokenRepo           │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │            Model Layer (SQLAlchemy ORM)                │  │
│  │  User  │  Role  │  UserRole  │  AuditLog  │  Token    │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────┬────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌──────────────────────┐        ┌──────────────────────┐
│  PostgreSQL 16+      │        │   Redis 7+           │
│  • Users             │        │   • Rate limiting    │
│  • Roles/Permissions │        │   • Token blacklist  │
│  • Audit Logs        │        │   • Session cache    │
│  • Refresh Tokens    │        └──────────────────────┘
└──────────────────────┘
```

### 3.2 Layer Responsibilities

**Route Layer** (`src/api/routes/`):
- HTTP request/response handling ONLY
- Validate request schemas via Pydantic
- Call service methods
- Format responses
- **NO business logic, NO database operations**

**Service Layer** (`src/services/`):
- ALL business logic and orchestration
- Validate business rules
- Coordinate multiple repositories
- Handle transaction management
- Example: `AuthService` handles registration logic, password validation, token generation

**Repository Layer** (`src/repositories/`):
- Database operations ONLY (CRUD)
- Query database using SQLAlchemy
- Return domain models, not ORM objects
- Handle soft delete filtering

**Model Layer** (`src/models/`):
- Database schema definition via SQLAlchemy ORM
- Define tables, columns, relationships, constraints
- Use mixins for reusable patterns (timestamps, soft delete)

### 3.3 Data Flow Example: User Login

```
1. POST /api/v1/auth/login
   ├─→ Middleware: Request ID generation, rate limiting check
   ├─→ Route: Validate LoginRequest schema (email, password)
   ├─→ Service: AuthService.login()
   │   ├─→ Repository: UserRepository.get_by_email()
   │   │   └─→ Database: SELECT * FROM users WHERE email = ?
   │   ├─→ Security: Verify password hash (Argon2id)
   │   ├─→ Security: Generate access token (JWT, 15 min expiry)
   │   ├─→ Security: Generate refresh token (JWT, 7 days expiry)
   │   ├─→ Repository: RefreshTokenRepository.create()
   │   │   └─→ Database: INSERT INTO refresh_tokens
   │   └─→ Service: AuditService.log_login()
   │       └─→ Database: INSERT INTO audit_logs
   └─→ Response: {access_token, refresh_token, user_data}
```

---

## 4. Technology Stack

| Layer | Technology | Version | Justification |
|-------|------------|---------|---------------|
| **Language** | Python | 3.13+ | LTS with async support, rich ecosystem |
| **Framework** | FastAPI | 0.115+ | Best async API framework, auto docs |
| **Database** | PostgreSQL | 16+ | Most advanced open-source RDBMS |
| **ORM** | SQLAlchemy | 2.0+ | Industry standard with async support |
| **DB Driver** | asyncpg | 0.29+ | Fastest async PostgreSQL driver |
| **Migrations** | Alembic | 1.13+ | SQLAlchemy-native migrations |
| **Validation** | Pydantic | 2.9+ | Built into FastAPI, 5-50x faster than v1 |
| **Password Hash** | argon2-cffi | 23.1+ | **NIST-recommended**, memory-hard |
| **JWT** | python-jose | 3.3+ | Full-featured JWT library |
| **Rate Limiting** | slowapi | 0.1.9+ | Redis-backed, FastAPI-compatible |
| **Testing** | pytest | 8.3+ | Industry standard |
| **Async Testing** | pytest-asyncio | 0.23+ | Async test support |
| **Coverage** | pytest-cov | Latest | Coverage reporting |
| **Dependency Mgmt** | uv | Latest | 10-100x faster than pip |
| **ASGI Server** | Uvicorn + Gunicorn | Latest | Production-grade server |
| **Container** | Docker + Compose | Latest | Local dev + deployment |

### Why Argon2id Over bcrypt (Critical Decision)

**Research Findings (2025)**:
- **NIST-recommended**: Official standard for password hashing
- **OWASP primary choice**: Recommended for all new implementations
- **Memory-hard**: 64MB memory usage vs bcrypt's 4KB (resistant to GPU/ASIC attacks)
- **Quantum-resistant properties**: More future-proof than bcrypt
- **Bcrypt limitations**: 
  - Fixed 4KB memory (vulnerable to FPGA attacks)
  - 72-character password limit
  - Less resistant to modern hardware attacks

**Configuration**:
```python
PasswordHasher(
    time_cost=2,        # 2 iterations
    memory_cost=65536,  # 64 MB memory
    parallelism=4,      # 4 parallel threads
    hash_len=32,        # 32-byte output
    salt_len=16         # 16-byte salt
)
```

---

## 5. File Structure

```
emerald-backend/
├── alembic/                          # Database migrations
│   ├── versions/
│   │   └── 001_create_initial_tables.py
│   ├── env.py
│   └── script.py.mako
│
├── src/
│   ├── api/
│   │   ├── routes/                   # HTTP route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # Auth endpoints
│   │   │   └── users.py             # User endpoints
│   │   └── dependencies.py           # Shared dependencies
│   │
│   ├── services/                     # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   └── audit_service.py
│   │
│   ├── repositories/                 # Database operations
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user_repository.py
│   │   ├── role_repository.py
│   │   ├── refresh_token_repository.py
│   │   └── audit_repository.py
│   │
│   ├── models/                       # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mixins.py
│   │   ├── user.py
│   │   ├── refresh_token.py
│   │   └── audit_log.py
│   │
│   ├── schemas/                      # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── user.py
│   │   ├── auth.py
│   │   └── audit.py
│   │
│   ├── core/                         # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── database.py
│   │   └── logging.py
│   │
│   ├── exceptions.py
│   ├── middleware.py
│   └── main.py
│
├── tests/
│   ├── unit/
│   │   ├── services/
│   │   └── core/
│   ├── integration/
│   ├── e2e/
│   ├── factories.py
│   └── conftest.py
│
├── logs/                             # In .gitignore
├── docs/
├── .env.example
├── .env                              # In .gitignore
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── logging_config.yaml
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 6. Implementation Roadmap

### Overview

Phase 1 is divided into 3 sub-phases over 6 weeks:

```
Week 1-2: Foundation & Database (Phase 1.1)
    ↓
Week 3-4: Authentication & Security (Phase 1.2)
    ↓
Week 5-6: User Management & Testing (Phase 1.3)
```

---

### Phase 1.1: Foundation & Database Setup (Weeks 1-2)

**Goal**: Establish project structure, database models, and core infrastructure

**Scope**:
- ✅ Project initialization with uv
- ✅ Database models with mixins (User, Role, UserRole, RefreshToken, AuditLog)
- ✅ Initial Alembic migration
- ✅ Core configuration (Settings, Database, Logging)
- ✅ Docker Compose setup (PostgreSQL + Redis)
- ❌ Authentication (deferred to Phase 1.2)
- ❌ API endpoints (deferred to Phase 1.2)

**Detailed Tasks**:

1. **Project Setup** (Day 1-2):
   - [ ] Initialize project: `uv init`
   - [ ] Add dependencies to `pyproject.toml`:
     ```toml
     dependencies = [
         "fastapi[standard]>=0.115.0",
         "sqlalchemy[asyncio]>=2.0.0",
         "asyncpg>=0.29.0",
         "alembic>=1.13.0",
         "pydantic>=2.9.0",
         "pydantic-settings>=2.5.0",
         "argon2-cffi>=23.1.0",
         "python-jose[cryptography]>=3.3.0",
         "slowapi>=0.1.9",
         "redis>=5.0.0",
         "python-multipart>=0.0.6",
     ]
     dev-dependencies = [
         "pytest>=8.3.0",
         "pytest-asyncio>=0.23.0",
         "pytest-cov>=5.0.0",
         "httpx>=0.27.0",
         "ruff>=0.6.0",
         "mypy>=1.11.0",
         "pre-commit>=3.8.0",
     ]
     ```
   - [ ] Lock dependencies: `uv lock`
   - [ ] Create project structure (all directories from Section 5)
   - [ ] Create `.gitignore` (exclude `.env`, `logs/`, `__pycache__/`, `.pytest_cache/`)
   - [ ] Create `.env.example` with all required variables documented

2. **Core Configuration** (Day 2-3):
   - [ ] **File**: `src/core/config.py`
     - [ ] Create `Settings` class with `PydanticSettings`
     - [ ] Load from `.env` file
     - [ ] Required settings: `APP_NAME`, `VERSION`, `DEBUG`, `ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `CORS_ORIGINS`, `RATE_LIMIT_ENABLED`
   - [ ] **File**: `src/core/database.py`
     - [ ] Create async engine with connection pooling
     - [ ] Configure: `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=3600`
     - [ ] Create `AsyncSessionLocal` factory
     - [ ] Define `get_db()` dependency
   - [ ] **File**: `src/core/logging.py`
     - [ ] Configure structured logging (JSON for production, console for dev)
     - [ ] Rotating file handlers: `logs/app.log`, `logs/error.log`
     - [ ] Include: timestamp, level, logger, function, line, request_id

3. **Database Models** (Day 3-5):
   - [ ] **File**: `src/models/base.py`
     - [ ] Create `Base` declarative base
     - [ ] Define `id` as UUID primary key
   - [ ] **File**: `src/models/mixins.py`
     - [ ] `TimestampMixin`: `created_at`, `updated_at`
     - [ ] `SoftDeleteMixin`: `deleted_at`
     - [ ] `AuditFieldsMixin`: `created_by`, `updated_by`
   - [ ] **File**: `src/models/user.py`
     - [ ] `User` model with all fields from requirements
     - [ ] `Role` model with JSONB permissions
     - [ ] `UserRole` junction table
     - [ ] Relationships and constraints
   - [ ] **File**: `src/models/refresh_token.py`
     - [ ] `RefreshToken` model with token_family_id
     - [ ] Store hashed tokens (SHA-256)
   - [ ] **File**: `src/models/audit_log.py`
     - [ ] `AuditLog` model with JSONB old_values/new_values
     - [ ] All required indexes

4. **Database Migrations** (Day 5-6):
   - [ ] Initialize Alembic: `alembic init alembic`
   - [ ] Configure `alembic/env.py` for async
   - [ ] Import all models in `env.py`
   - [ ] Generate initial migration: `alembic revision --autogenerate -m "Create initial tables"`
   - [ ] **Review migration carefully**:
     - [ ] Verify all columns and types
     - [ ] Check indexes (foreign keys, unique, query columns)
     - [ ] Add partial unique indexes for soft delete: `CREATE UNIQUE INDEX users_email_unique ON users(email) WHERE deleted_at IS NULL`
   - [ ] Add `updated_at` trigger function and apply to all tables
   - [ ] Add database constraint to prevent audit log updates/deletes
   - [ ] Test migration: `alembic upgrade head`
   - [ ] Test downgrade: `alembic downgrade -1`
   - [ ] Test upgrade again: `alembic upgrade head`

5. **Docker Setup** (Day 6-7):
   - [ ] **File**: `docker-compose.yml`
     - [ ] PostgreSQL 16 service (port 5432)
     - [ ] Redis 7 service (port 6379)
     - [ ] Volume mounts for data persistence
   - [ ] **File**: `Dockerfile`
     - [ ] Multi-stage build (builder + runtime)
     - [ ] Install uv and dependencies
     - [ ] Copy source code
     - [ ] Expose port 8000
     - [ ] Command: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
   - [ ] Test: `docker-compose up -d`
   - [ ] Verify PostgreSQL connection
   - [ ] Run migrations in container

6. **Security Utilities** (Day 7-8):
   - [ ] **File**: `src/core/security.py`
     - [ ] Password hashing with Argon2id:
       ```python
       pwd_hasher = PasswordHasher(
           time_cost=2,
           memory_cost=65536,
           parallelism=4,
           hash_len=32,
           salt_len=16
       )
       ```
     - [ ] `hash_password(password: str) -> str`
     - [ ] `verify_password(password: str, hashed: str) -> bool`
     - [ ] `validate_password_strength(password: str) -> None`
     - [ ] JWT token generation: `create_access_token()`, `create_refresh_token()`
     - [ ] JWT token validation: `decode_token()`, `verify_token_type()`
     - [ ] Refresh token hashing: `hash_refresh_token()` (SHA-256)

7. **Custom Exceptions** (Day 8-9):
   - [ ] **File**: `src/exceptions.py`
     - [ ] `AppException` base class with status_code, error_code, details
     - [ ] Authentication exceptions: `InvalidCredentialsError`, `InvalidTokenError`, `TokenExpiredError`, `AccountLockedError`
     - [ ] Authorization exceptions: `InsufficientPermissionsError`
     - [ ] Resource exceptions: `NotFoundError`, `AlreadyExistsError`
     - [ ] Validation exceptions: `ValidationError`, `WeakPasswordError`
     - [ ] `RateLimitExceededError`

8. **Repository Layer** (Day 9-10):
   - [ ] **File**: `src/repositories/base.py`
     - [ ] Generic `BaseRepository[ModelType]`
     - [ ] Methods: `create()`, `get_by_id()`, `get_all()`, `update()`, `soft_delete()`, `count()`
     - [ ] Automatic soft delete filtering
   - [ ] **File**: `src/repositories/user_repository.py`
     - [ ] `UserRepository` extends `BaseRepository[User]`
     - [ ] Methods: `get_by_email()`, `get_by_username()`, `get_with_roles()`, `update_last_login()`, `filter_users()`
   - [ ] **File**: `src/repositories/role_repository.py`
     - [ ] `RoleRepository` extends `BaseRepository[Role]`
     - [ ] Methods: `get_by_name()`, `get_user_permissions()`
   - [ ] **File**: `src/repositories/refresh_token_repository.py`
     - [ ] `RefreshTokenRepository` extends `BaseRepository[RefreshToken]`
     - [ ] Methods: `get_by_token_hash()`, `revoke_token()`, `revoke_user_tokens()`, `revoke_token_family()`, `delete_expired_tokens()`
   - [ ] **File**: `src/repositories/audit_repository.py`
     - [ ] `AuditLogRepository` (create-only, no base class)
     - [ ] Methods: `create()`, `get_user_logs()`, `get_entity_logs()`, `count_user_logs()`

**Dependencies**: None (initial phase)

**Validation Criteria** (Phase 1.1 complete when):
- [ ] All database models defined with proper relationships
- [ ] Initial migration creates all tables with correct schema
- [ ] Docker Compose starts PostgreSQL + Redis successfully
- [ ] Core configuration loads from `.env` file
- [ ] Security utilities hash/verify passwords correctly
- [ ] Repository layer performs CRUD operations
- [ ] All code passes linting (Ruff) and type checking (MyPy)

**Risk Factors**:
- **Alembic migration complexity**: Partial unique indexes are PostgreSQL-specific
  - *Mitigation*: Test migrations on clean database, review autogenerated SQL
- **Async configuration**: Async SQLAlchemy setup has gotchas
  - *Mitigation*: Follow official documentation, use asyncpg driver
- **Argon2 configuration**: Incorrect settings can impact performance
  - *Mitigation*: Use OWASP-recommended settings from research

**Estimated Effort**: 2 weeks (1 developer, 80 hours)

---

### Phase 1.2: Authentication & Security (Weeks 3-4)

**Goal**: Implement secure authentication with JWT tokens, refresh token rotation, and rate limiting

**Scope**:
- ✅ Authentication service (registration, login, token refresh, logout)
- ✅ JWT token generation and validation
- ✅ Refresh token rotation with reuse detection
- ✅ Rate limiting on authentication endpoints
- ✅ Middleware (request ID, security headers, error handling)
- ✅ Authentication endpoints
- ❌ User management endpoints (deferred to Phase 1.3)
- ❌ Comprehensive testing (deferred to Phase 1.3)

**Detailed Tasks**:

1. **Pydantic Schemas** (Day 1-2):
   - [ ] **File**: `src/schemas/common.py`
     - [ ] `PaginationParams`: page, page_size (max 100)
     - [ ] `PaginatedResponse[T]`: Generic paginated response with meta
   - [ ] **File**: `src/schemas/user.py`
     - [ ] `UserBase`, `UserCreate`, `UserUpdate`, `UserPasswordChange`
     - [ ] `UserResponse`, `UserListItem`
     - [ ] Validation: email (EmailStr), username (alphanumeric + _ -), password (min 8 chars)
   - [ ] **File**: `src/schemas/auth.py`
     - [ ] `LoginRequest`: email, password
     - [ ] `TokenResponse`: access_token, refresh_token, token_type, expires_in, user
     - [ ] `RefreshTokenRequest`: refresh_token
     - [ ] `AccessTokenResponse`: access_token, token_type, expires_in
   - [ ] **File**: `src/schemas/audit.py`
     - [ ] `AuditLogResponse`: All audit log fields
     - [ ] `AuditLogFilter`: Filters for querying

2. **Authentication Service** (Day 2-5):
   - [ ] **File**: `src/services/auth_service.py`
     - [ ] `register()`:
       - [ ] Validate password strength
       - [ ] Check email/username uniqueness
       - [ ] Hash password with Argon2id
       - [ ] Create user in database
       - [ ] Assign default "user" role
       - [ ] Log audit event
       - [ ] Return user (no tokens yet)
     - [ ] `login()`:
       - [ ] Get user by email
       - [ ] Verify password
       - [ ] Check account locked status
       - [ ] Update last_login_at
       - [ ] Get user permissions from roles
       - [ ] Generate access token (15 min expiry, include permissions)
       - [ ] Generate refresh token (7 days expiry, new token_family_id)
       - [ ] Store hashed refresh token in database
       - [ ] Log successful login audit event
       - [ ] Return TokenResponse
     - [ ] `refresh_access_token()`:
       - [ ] Decode refresh token
       - [ ] Verify token type = "refresh"
       - [ ] Get refresh token from database by hash
       - [ ] Check token not expired
       - [ ] Check token not revoked
       - [ ] **Reuse detection**: If token already used (revoked), revoke entire token family
       - [ ] Revoke old refresh token
       - [ ] Generate new access token
       - [ ] Generate new refresh token (same token_family_id)
       - [ ] Store new refresh token
       - [ ] Log token refresh audit event
       - [ ] Return new tokens
     - [ ] `logout()`:
       - [ ] Decode refresh token
       - [ ] Revoke refresh token in database
       - [ ] Log logout audit event
     - [ ] `change_password()`:
       - [ ] Get user
       - [ ] Verify current password
       - [ ] Validate new password strength
       - [ ] Hash new password
       - [ ] Update user password_hash
       - [ ] Revoke all refresh tokens (force re-login)
       - [ ] Log password change audit event

3. **Audit Service** (Day 5-6):
   - [ ] **File**: `src/services/audit_service.py`
     - [ ] `log_event()`:
       - [ ] Create audit log entry
       - [ ] Capture: user_id, action, entity_type, entity_id, old_values, new_values, ip_address, user_agent, request_id
       - [ ] Handle system events (user_id = None)
     - [ ] `log_login()`, `log_logout()`, `log_password_change()` convenience methods
     - [ ] `log_data_change()`: Capture before/after values
     - [ ] `get_user_audit_logs()`: Query user's own logs with filters
     - [ ] `get_all_audit_logs()`: Admin-only, query all logs

4. **Middleware** (Day 6-7):
   - [ ] **File**: `src/middleware.py`
     - [ ] `RequestIDMiddleware`:
       - [ ] Generate UUID for each request
       - [ ] Store in `request.state.request_id`
       - [ ] Add to response headers: `X-Request-ID`
     - [ ] `SecurityHeadersMiddleware`:
       - [ ] Add headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Strict-Transport-Security`, `Content-Security-Policy`, `Referrer-Policy`
       - [ ] Remove `Server` header
     - [ ] `RequestLoggingMiddleware`:
       - [ ] Log request: method, path, client_ip, user_agent, request_id
       - [ ] Log response: status_code, duration_ms, request_id
     - [ ] `setup_exception_handlers()`:
       - [ ] Handle `AppException`: Convert to JSON error response
       - [ ] Handle `Exception`: Log critical error, sanitize message in production

5. **FastAPI Dependencies** (Day 7-8):
   - [ ] **File**: `src/api/dependencies.py`
     - [ ] `get_db()`: Database session dependency (already in database.py)
     - [ ] `get_current_user()`:
       - [ ] Extract token from Authorization header
       - [ ] Decode and validate access token
       - [ ] Verify token type = "access"
       - [ ] Get user from database
       - [ ] Return user
     - [ ] `require_active_user()`:
       - [ ] Depends on `get_current_user()`
       - [ ] Check `user.is_active == True`
       - [ ] Raise exception if inactive
     - [ ] `require_admin()`:
       - [ ] Depends on `get_current_user()`
       - [ ] Check `user.is_admin == True`
       - [ ] Raise exception if not admin
     - [ ] `require_permission(permission: str)`:
       - [ ] Get user permissions from roles
       - [ ] Check if user has required permission
       - [ ] Raise exception if insufficient

6. **Authentication Routes** (Day 8-10):
   - [ ] **File**: `src/api/routes/auth.py`
     - [ ] `POST /api/v1/auth/register`:
       - [ ] Rate limit: 3/hour per IP
       - [ ] Validate `UserCreate` schema
       - [ ] Call `auth_service.register()`
       - [ ] Return 201 Created with UserResponse
     - [ ] `POST /api/v1/auth/login`:
       - [ ] Rate limit: 5/15min per IP
       - [ ] Validate `LoginRequest` schema
       - [ ] Call `auth_service.login()`
       - [ ] Return 200 OK with TokenResponse
     - [ ] `POST /api/v1/auth/refresh`:
       - [ ] Rate limit: 10/hour per user
       - [ ] Validate `RefreshTokenRequest` schema
       - [ ] Call `auth_service.refresh_access_token()`
       - [ ] Return 200 OK with AccessTokenResponse
     - [ ] `POST /api/v1/auth/logout`:
       - [ ] Requires authentication
       - [ ] Validate `RefreshTokenRequest` schema
       - [ ] Call `auth_service.logout()`
       - [ ] Return 204 No Content
     - [ ] `POST /api/v1/auth/change-password`:
       - [ ] Rate limit: 3/hour per user
       - [ ] Requires authentication
       - [ ] Validate `UserPasswordChange` schema
       - [ ] Call `auth_service.change_password()`
       - [ ] Return 200 OK

7. **Rate Limiting Setup** (Day 10):
   - [ ] Install and configure slowapi
   - [ ] Configure Redis backend for distributed rate limiting
   - [ ] Apply rate limits to authentication endpoints
   - [ ] Custom error handler for rate limit exceeded (429 status)

8. **Main Application** (Day 10-11):
   - [ ] **File**: `src/main.py`
     - [ ] Create FastAPI app with metadata
     - [ ] Add middleware (RequestID → Logging → Security → CORS)
     - [ ] Setup exception handlers
     - [ ] Include auth router
     - [ ] Configure CORS with explicit origins from settings
     - [ ] Disable Swagger in production (`docs_url=None if not settings.DEBUG`)
     - [ ] Add health check endpoint: `GET /health`

9. **Integration Testing** (Day 11-12):
   - [ ] **File**: `tests/integration/test_auth_routes.py`
     - [ ] Test user registration (success, duplicate email, weak password)
     - [ ] Test login (success, invalid credentials, inactive account)
     - [ ] Test token refresh (success, expired token, revoked token, reuse detection)
     - [ ] Test logout (success, invalid token)
     - [ ] Test password change (success, wrong current password, weak new password)
     - [ ] Test rate limiting on each endpoint

10. **Documentation** (Day 12):
    - [ ] Update README with:
      - [ ] Setup instructions
      - [ ] Environment variables
      - [ ] Running with Docker Compose
      - [ ] API endpoints overview
    - [ ] Verify Swagger docs are accurate and complete

**Dependencies**: Requires Phase 1.1 completion

**Validation Criteria** (Phase 1.2 complete when):
- [ ] User can register with valid email/password
- [ ] User can login and receive access + refresh tokens
- [ ] Access token expires after 15 minutes
- [ ] Refresh token rotates on use (new token issued)
- [ ] Refresh token reuse detection works (revokes token family)
- [ ] Rate limiting prevents brute force attacks
- [ ] All authentication events logged to audit_logs
- [ ] Security headers present in all responses
- [ ] Integration tests pass with 80%+ coverage

**Risk Factors**:
- **Token rotation complexity**: Reuse detection logic is critical
  - *Mitigation*: Thorough testing of rotation scenarios, including concurrent requests
- **Rate limiting in development**: Redis required for distributed rate limiting
  - *Mitigation*: Use in-memory fallback for local dev, Redis for staging/production
- **Password hashing performance**: Argon2id can be slow
  - *Mitigation*: Use background tasks for registration if needed, tune parameters

**Estimated Effort**: 2 weeks (1 developer, 80 hours)

---

### Phase 1.3: User Management & Testing (Weeks 5-6)

**Goal**: Implement user management, audit log endpoints, and achieve 80%+ test coverage

**Scope**:
- ✅ User management service (CRUD operations)
- ✅ User management endpoints
- ✅ Audit log query endpoints
- ✅ Comprehensive unit tests (services, repositories)
- ✅ Integration tests (all endpoints)
- ✅ End-to-end tests (complete user flows)
- ✅ 80%+ code coverage

**Detailed Tasks**:

1. **User Management Service** (Day 1-3):
   - [ ] **File**: `src/services/user_service.py`
     - [ ] `get_user_profile()`:
       - [ ] Get user by ID
       - [ ] Check permissions (admin or self)
       - [ ] Return UserResponse
     - [ ] `update_user_profile()`:
       - [ ] Get user by ID
       - [ ] Check permissions (admin or self)
       - [ ] Validate update data
       - [ ] Check email/username uniqueness (if changed)
       - [ ] Update user
       - [ ] Log audit event
       - [ ] Return updated UserResponse
     - [ ] `list_users()`:
       - [ ] Require admin permission
       - [ ] Apply filters (is_active, is_admin, search)
       - [ ] Paginate results
       - [ ] Return PaginatedResponse[UserListItem]
     - [ ] `deactivate_user()`:
       - [ ] Require admin permission
       - [ ] Set is_active = False
       - [ ] Revoke all refresh tokens
       - [ ] Log audit event
     - [ ] `soft_delete_user()`:
       - [ ] Require admin permission
       - [ ] Set deleted_at timestamp
       - [ ] Revoke all refresh tokens
       - [ ] Log audit event

2. **User Management Routes** (Day 3-5):
   - [ ] **File**: `src/api/routes/users.py`
     - [ ] `GET /api/v1/users/me`:
       - [ ] Requires authentication
       - [ ] Call `user_service.get_user_profile(current_user.id)`
       - [ ] Return UserResponse
     - [ ] `PATCH /api/v1/users/me`:
       - [ ] Requires authentication
       - [ ] Validate `UserUpdate` schema
       - [ ] Call `user_service.update_user_profile()`
       - [ ] Return UserResponse
     - [ ] `GET /api/v1/users/{user_id}`:
       - [ ] Requires admin OR self
       - [ ] Call `user_service.get_user_profile(user_id)`
       - [ ] Return UserResponse
     - [ ] `GET /api/v1/users`:
       - [ ] Requires admin
       - [ ] Validate `PaginationParams` and filters
       - [ ] Call `user_service.list_users()`
       - [ ] Return PaginatedResponse[UserListItem]
     - [ ] `POST /api/v1/users/{user_id}/deactivate`:
       - [ ] Requires admin
       - [ ] Call `user_service.deactivate_user()`
       - [ ] Return 204 No Content
     - [ ] `DELETE /api/v1/users/{user_id}`:
       - [ ] Requires admin
       - [ ] Call `user_service.soft_delete_user()`
       - [ ] Return 204 No Content

3. **Audit Log Routes** (Day 5-6):
   - [ ] **File**: `src/api/routes/audit.py` (add to `src/api/routes/users.py` or separate file)
     - [ ] `GET /api/v1/audit-logs/me`:
       - [ ] Requires authentication
       - [ ] Validate `AuditLogFilter`
       - [ ] Call `audit_service.get_user_audit_logs(current_user.id)`
       - [ ] Return PaginatedResponse[AuditLogResponse]
     - [ ] `GET /api/v1/audit-logs`:
       - [ ] Requires admin
       - [ ] Validate `AuditLogFilter`
       - [ ] Call `audit_service.get_all_audit_logs()`
       - [ ] Return PaginatedResponse[AuditLogResponse]

4. **Unit Tests - Core** (Day 6-7):
   - [ ] **File**: `tests/unit/core/test_security.py`
     - [ ] Test password hashing (hash produces different outputs with same input)
     - [ ] Test password verification (valid password verifies, invalid doesn't)
     - [ ] Test password strength validation (all requirements enforced)
     - [ ] Test access token generation (contains correct claims, expires in 15 min)
     - [ ] Test refresh token generation (contains correct claims, expires in 7 days)
     - [ ] Test token decoding (valid token decodes, expired raises error)
     - [ ] Test refresh token hashing (produces consistent SHA-256 hash)

5. **Unit Tests - Services** (Day 7-10):
   - [ ] **File**: `tests/unit/services/test_auth_service.py`
     - [ ] Test registration:
       - [ ] Success: User created, password hashed, default role assigned
       - [ ] Duplicate email: Raises AlreadyExistsError
       - [ ] Weak password: Raises WeakPasswordError
     - [ ] Test login:
       - [ ] Success: Returns tokens, updates last_login_at
       - [ ] Invalid credentials: Raises InvalidCredentialsError
       - [ ] Inactive user: Raises AuthenticationError
     - [ ] Test token refresh:
       - [ ] Success: New tokens issued, old revoked
       - [ ] Expired token: Raises TokenExpiredError
       - [ ] Revoked token: Raises InvalidTokenError
       - [ ] Reuse detection: Revokes token family
     - [ ] Test logout:
       - [ ] Success: Refresh token revoked
     - [ ] Test password change:
       - [ ] Success: Password updated, all tokens revoked
       - [ ] Wrong current password: Raises InvalidCredentialsError
       - [ ] Weak new password: Raises WeakPasswordError
   - [ ] **File**: `tests/unit/services/test_user_service.py`
     - [ ] Test get_user_profile (success, not found, permission denied)
     - [ ] Test update_user_profile (success, duplicate email, permission denied)
     - [ ] Test list_users (success, filters applied, pagination)
     - [ ] Test deactivate_user (success, tokens revoked)
     - [ ] Test soft_delete_user (success, deleted_at set)
   - [ ] **File**: `tests/unit/services/test_audit_service.py`
     - [ ] Test log_event (audit log created with all fields)
     - [ ] Test get_user_audit_logs (filters applied, pagination)

6. **Integration Tests** (Day 10-12):
   - [ ] **File**: `tests/integration/test_user_routes.py`
     - [ ] Test GET /users/me (authenticated user gets profile)
     - [ ] Test PATCH /users/me (user updates own profile)
     - [ ] Test GET /users/{id} (admin gets any user, user gets self)
     - [ ] Test GET /users (admin lists users with filters/pagination)
     - [ ] Test POST /users/{id}/deactivate (admin deactivates user)
     - [ ] Test DELETE /users/{id} (admin soft deletes user)
     - [ ] Test unauthorized access (401/403 errors)
   - [ ] **File**: `tests/integration/test_audit_routes.py`
     - [ ] Test GET /audit-logs/me (user gets own audit logs)
     - [ ] Test GET /audit-logs (admin gets all audit logs with filters)

7. **End-to-End Tests** (Day 12-13):
   - [ ] **File**: `tests/e2e/test_user_lifecycle.py`
     - [ ] Complete user flow:
       1. Register new user
       2. Login (receive tokens)
       3. Access protected endpoint with access token
       4. Access token expires (simulate with time travel or short expiry)
       5. Refresh access token
       6. Update user profile
       7. Change password (all tokens revoked)
       8. Login again with new password
       9. Logout
       10. Attempt to use revoked refresh token (should fail)
     - [ ] Admin flow:
       1. Admin lists all users
       2. Admin views specific user
       3. Admin deactivates user
       4. User cannot login (inactive)
       5. Admin reactivates user
       6. User can login again

8. **Test Fixtures** (Day 13):
   - [ ] **File**: `tests/conftest.py`
     - [ ] `test_db()`: Create test database, run migrations, yield session, rollback
     - [ ] `test_app()`: Create FastAPI TestClient with test database
     - [ ] `test_user()`: Create test user in database
     - [ ] `admin_user()`: Create admin user in database
     - [ ] `auth_headers()`: Generate valid access token for user
     - [ ] `admin_auth_headers()`: Generate valid access token for admin
   - [ ] **File**: `tests/factories.py`
     - [ ] Use Factory Boy for test data generation
     - [ ] `UserFactory`: Generate random users
     - [ ] `RoleFactory`: Generate roles with permissions
     - [ ] `AuditLogFactory`: Generate audit logs

9. **Coverage Analysis** (Day 13-14):
   - [ ] Run: `pytest --cov=src --cov-report=html --cov-report=term`
   - [ ] Review coverage report
   - [ ] Identify gaps (aim for 80%+ overall, 90%+ services)
   - [ ] Write additional tests for uncovered code
   - [ ] Focus on critical paths (authentication, permissions, data integrity)

10. **Documentation & Polish** (Day 14):
    - [ ] Update README:
      - [ ] Complete setup instructions
      - [ ] Environment variable documentation
      - [ ] API endpoint documentation (or link to Swagger)
      - [ ] Testing instructions
      - [ ] Deployment guide (basic Docker instructions)
    - [ ] Create CHANGELOG.md
    - [ ] Create `.env.example` with all variables documented
    - [ ] Add docstrings to all public functions/classes (Google style)
    - [ ] Run linting and fix issues: `ruff check --fix`
    - [ ] Run type checking and fix issues: `mypy src/`

**Dependencies**: Requires Phase 1.2 completion

**Validation Criteria** (Phase 1.3 complete when):
- [ ] All user management endpoints implemented and tested
- [ ] Audit log endpoints return correct data with filters
- [ ] 80%+ overall test coverage
- [ ] 90%+ coverage for services and repositories
- [ ] All tests pass (unit + integration + e2e)
- [ ] API documentation complete (Swagger/README)
- [ ] Code passes linting (Ruff) and type checking (MyPy)
- [ ] README has complete setup and usage instructions

**Risk Factors**:
- **Test coverage gaps**: Complex permission logic may have edge cases
  - *Mitigation*: Parametrize tests for multiple scenarios, use coverage report to identify gaps
- **Test database setup**: Async tests with database can be tricky
  - *Mitigation*: Use well-tested pytest-asyncio fixtures, rollback transactions after each test
- **E2E test flakiness**: Time-based token expiry can cause flaky tests
  - *Mitigation*: Use short token expiry for tests, or mock datetime

**Estimated Effort**: 2 weeks (1 developer, 80 hours)

---

## 7. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Simplest solution**: Async FastAPI + SQLAlchemy + PostgreSQL is the standard, proven stack (not over-engineered)
- [x] **No premature optimization**: Connection pooling and caching only where needed (database, rate limiting)
- [x] **Aligned with existing patterns**: Follows FastAPI best practices and layered architecture
- [x] **Incremental delivery**: 3 phases allow delivering value progressively
- [x] **Solving actual problem**: User management and authentication are foundational requirements for any application

### Alternatives Considered

**Alternative 1: Synchronous approach (Django + DRF)**
- **Why not chosen**: 
  - Slower performance (no async support)
  - Overkill for API-only backend (includes templating, admin UI)
  - Less suitable for high-concurrency scenarios

**Alternative 2: Microservices from day 1**
- **Why not chosen**:
  - Premature optimization (no scale requirements yet)
  - Adds complexity (inter-service communication, distributed transactions)
  - Harder to iterate and change

**Alternative 3: bcrypt instead of Argon2id**
- **Why not chosen**:
  - bcrypt is older standard (still secure but not best-in-class)
  - NIST and OWASP recommend Argon2id for new implementations
  - Argon2id is more resistant to modern attacks (GPU/ASIC)

**Rationale for Chosen Approach**:
- **Monolithic async architecture**: Simpler to develop, deploy, and debug while maintaining excellent performance
- **Argon2id**: Follows latest security standards (NIST, OWASP 2025 recommendations)
- **Layered architecture**: Clear separation of concerns (routes, services, repositories) makes code maintainable and testable
- **Phase-based delivery**: Allows validating foundation before building financial features

---

## 8. API Design Standards

### 8.1 Endpoint Structure

All endpoints follow RESTful conventions with URL versioning:

```
/api/v1/auth/register       POST    - Register new user
/api/v1/auth/login          POST    - Login with email/password
/api/v1/auth/refresh        POST    - Refresh access token
/api/v1/auth/logout         POST    - Logout (revoke refresh token)
/api/v1/auth/change-password POST   - Change password

/api/v1/users               GET     - List all users (admin, paginated)
/api/v1/users/me            GET     - Get current user profile
/api/v1/users/me            PATCH   - Update current user profile
/api/v1/users/{id}          GET     - Get specific user (admin or self)
/api/v1/users/{id}/deactivate POST  - Deactivate user (admin)
/api/v1/users/{id}          DELETE  - Soft delete user (admin)

/api/v1/audit-logs/me       GET     - Get current user's audit logs
/api/v1/audit-logs          GET     - Get all audit logs (admin)

/health                     GET     - Health check
/health/ready               GET     - Readiness check (DB + Redis)
```

### 8.2 Response Format

**Success Response**:
```json
{
  "data": { /* resource or array */ },
  "meta": {
    "timestamp": "2025-10-29T12:34:56.789Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Paginated List Response**:
```json
{
  "data": [ /* array of resources */ ],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "timestamp": "2025-10-29T12:34:56.789Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Error Response**:
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {}
  },
  "meta": {
    "timestamp": "2025-10-29T12:34:56.789Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 8.3 HTTP Status Codes

- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST (resource created)
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Duplicate resource (email, username)
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected error

### 8.4 Authentication

**Bearer Token in Authorization Header**:
```
Authorization: Bearer <access_token>
```

**Token Response Format**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { /* UserResponse */ }
}
```

---

## 9. Security Architecture

### 9.1 Defense-in-Depth Layers

```
1. Network Layer
   ├─ HTTPS/TLS 1.3
   ├─ Firewall (only 80/443 exposed)
   └─ DDoS protection (Cloudflare)

2. Application Layer
   ├─ Rate limiting (slowapi + Redis)
   ├─ Input validation (Pydantic)
   ├─ CORS (explicit allowed origins)
   └─ Security headers

3. Authentication Layer
   ├─ JWT with short expiry (15 min)
   ├─ Refresh token rotation
   ├─ Argon2id password hashing
   └─ Account locking (failed attempts)

4. Authorization Layer
   ├─ RBAC (role-based access control)
   ├─ Permission checking on every protected endpoint
   └─ Audit logging of access attempts

5. Data Layer
   ├─ Encryption at rest (database-level)
   ├─ Soft deletes (data recovery)
   └─ Immutable audit logs

6. Monitoring & Response
   ├─ Security event logging
   ├─ Anomaly detection
   └─ Incident response plan
```

### 9.2 Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### 9.3 Rate Limiting

| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| `/auth/login` | 5 / 15 min per IP | Prevent brute force |
| `/auth/register` | 3 / hour per IP | Prevent spam accounts |
| `/auth/change-password` | 3 / hour per user | Prevent unauthorized changes |
| `/auth/refresh` | 10 / hour per user | Prevent token exhaustion |
| General API | 100 / min per user | Fair usage |

---

## 10. Testing Strategy

### 10.1 Testing Pyramid

```
       /\
      /  \  E2E Tests (10%)
     /____\
    /      \
   / Integ- \ Integration Tests (30%)
  /  ration  \
 /____________\
/              \
|  Unit Tests  | Unit Tests (60%)
|    (60%)     |
```

### 10.2 Coverage Requirements

- **Overall**: 80% minimum
- **Services**: 90%+ (business logic critical)
- **Repositories**: 85%+ (database operations critical)
- **Routes**: 70%+ (often thin wrappers)
- **Models**: Minimal (mostly framework code)

### 10.3 Test Organization

```
tests/
├── unit/                     # Fast, isolated tests
│   ├── services/            # Business logic tests
│   └── core/                # Utility tests
├── integration/             # Tests with database
│   ├── test_auth_routes.py
│   └── test_user_routes.py
├── e2e/                     # Complete user flows
│   └── test_user_lifecycle.py
├── factories.py             # Factory Boy factories
└── conftest.py             # Shared fixtures
```

### 10.4 Key Test Scenarios

**Authentication**:
- Registration with valid/invalid data
- Login with correct/incorrect credentials
- Token refresh with valid/expired/revoked tokens
- Refresh token rotation and reuse detection
- Password change with validation
- Rate limiting on auth endpoints

**Authorization**:
- User can access own profile
- User cannot access other user's profile
- Admin can access any user's profile
- Admin can list all users
- User cannot list all users (403)

**Audit Logging**:
- All data changes logged
- Authentication events logged (login, logout, password change)
- User can view own audit logs
- Admin can view all audit logs

**Soft Delete**:
- Deleted users excluded from queries
- Email/username can be reused after soft delete
- Audit logs preserved for deleted users

---

## 11. Success Criteria & Acceptance

### 11.1 Functional Requirements

**Authentication**:
- [ ] User can register with email/password
- [ ] User cannot register with duplicate email/username
- [ ] User cannot register with weak password
- [ ] User can login with email/password
- [ ] User cannot login with invalid credentials
- [ ] User receives access token (15 min expiry) and refresh token (7 days expiry)
- [ ] User can refresh access token with refresh token
- [ ] Refresh token is rotated on use (new token issued, old revoked)
- [ ] Refresh token reuse is detected (entire family revoked)
- [ ] User can logout (refresh token revoked)
- [ ] User can change password (all refresh tokens revoked)

**User Management**:
- [ ] User can view own profile
- [ ] User can update own profile (username, email, full_name)
- [ ] User cannot update to duplicate email/username
- [ ] Admin can list all users with pagination
- [ ] Admin can filter users (is_active, is_admin, search)
- [ ] Admin can view any user's profile
- [ ] Admin can deactivate user (user cannot login)
- [ ] Admin can soft delete user (deleted_at set)

**Audit Logging**:
- [ ] All user registrations logged
- [ ] All login attempts logged (success and failure)
- [ ] All logout events logged
- [ ] All password changes logged
- [ ] All user profile updates logged
- [ ] All user deactivations logged
- [ ] All user deletions logged
- [ ] User can view own audit logs
- [ ] Admin can view all audit logs
- [ ] Audit logs cannot be modified or deleted

**Rate Limiting**:
- [ ] Login endpoint limited to 5 attempts per 15 minutes
- [ ] Registration endpoint limited to 3 attempts per hour
- [ ] Password change endpoint limited to 3 attempts per hour
- [ ] Token refresh endpoint limited to 10 attempts per hour
- [ ] Rate limit returns 429 status with retry_after

### 11.2 Non-Functional Requirements

**Performance**:
- [ ] API response time p95 < 200ms (local development)
- [ ] API response time p99 < 500ms (local development)
- [ ] Database queries optimized (no N+1 queries)
- [ ] Connection pooling configured correctly

**Security**:
- [ ] Passwords hashed with Argon2id (time_cost=2, memory_cost=65536)
- [ ] JWT tokens signed with HS256 and strong secret (256+ bits)
- [ ] Access tokens expire in 15 minutes
- [ ] Refresh tokens expire in 7 days
- [ ] Refresh token rotation implemented
- [ ] Refresh token reuse detection implemented
- [ ] Rate limiting prevents brute force attacks
- [ ] Security headers present in all responses
- [ ] CORS configured with explicit allowed origins
- [ ] No sensitive data logged (passwords, tokens, PII)
- [ ] SQL injection prevented (SQLAlchemy parameterized queries)
- [ ] XSS prevented (Pydantic validation, CSP headers)

**Testing**:
- [ ] 80%+ overall code coverage
- [ ] 90%+ coverage for services
- [ ] 85%+ coverage for repositories
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All e2e tests pass
- [ ] Tests run in CI/CD pipeline

**Documentation**:
- [ ] README with setup instructions
- [ ] README with environment variables documented
- [ ] README with API endpoints overview
- [ ] README with testing instructions
- [ ] .env.example with all variables documented
- [ ] API documentation via Swagger/ReDoc
- [ ] Code docstrings for all public functions/classes

**Code Quality**:
- [ ] Code passes linting (Ruff)
- [ ] Code passes type checking (MyPy)
- [ ] No hardcoded secrets or configuration
- [ ] Consistent code style (Black formatter)
- [ ] Clear separation of concerns (layered architecture)

**Deployment**:
- [ ] Application runs in Docker containers
- [ ] Docker Compose setup for local development
- [ ] Database migrations documented and tested
- [ ] Logs written to rotating log files
- [ ] Environment variables properly configured

### 11.3 Phase Completion Criteria

**Phase 1.1 Complete**:
- [ ] All database models defined
- [ ] Initial migration creates tables correctly
- [ ] Docker Compose starts PostgreSQL + Redis
- [ ] Core configuration loads from .env
- [ ] Security utilities work (password hashing, JWT)
- [ ] Repository layer performs CRUD operations

**Phase 1.2 Complete**:
- [ ] User registration works
- [ ] User login returns JWT tokens
- [ ] Token refresh rotates tokens correctly
- [ ] Reuse detection revokes token family
- [ ] Rate limiting prevents abuse
- [ ] All auth events logged to audit_logs
- [ ] Integration tests pass

**Phase 1.3 Complete**:
- [ ] User management endpoints work
- [ ] Audit log endpoints work
- [ ] 80%+ test coverage achieved
- [ ] All tests pass
- [ ] Documentation complete

---

## 12. References & Resources

### 12.1 Official Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [Argon2 Specification](https://github.com/P-H-C/phc-winner-argon2)
- [JWT Best Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)

### 12.2 Security Standards

- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [NIST Password Guidelines (SP 800-63B)](https://pages.nist.gov/800-63-3/sp800-63b.html)

### 12.3 Best Practice Guides

- [FastAPI Best Practices (GitHub)](https://github.com/zhanymkanov/fastapi-best-practices)
- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [PostgreSQL Connection Pooling Best Practices](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-connection-pooling-best-practices)
- [JWT Security Best Practices (Auth0)](https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-token-best-practices)

### 12.4 Research Sources (Used in This Plan)

- `.features/research/20251029_personal-finance-platform-phase1-foundation.md` (comprehensive research document)
- Web search: FastAPI 0.115 best practices 2025
- Web search: JWT refresh token rotation best practices 2025
- Web search: Argon2id vs bcrypt 2025
- Web search: FastAPI dependency injection testing 2025

---

## 13. Conclusion

This implementation plan provides a comprehensive blueprint for building a production-grade FastAPI backend foundation for the Emerald personal finance platform. The plan is structured to deliver value incrementally over 6 weeks across 3 phases:

**Phase 1.1 (Weeks 1-2)**: Foundation & Database
- Project setup, database models, migrations, core configuration

**Phase 1.2 (Weeks 3-4)**: Authentication & Security
- JWT authentication, refresh token rotation, rate limiting, middleware

**Phase 1.3 (Weeks 5-6)**: User Management & Testing
- User CRUD, audit logs, comprehensive tests, 80%+ coverage

### Key Takeaways

1. **Security-First**: Argon2id password hashing, JWT refresh token rotation with reuse detection, rate limiting, and comprehensive audit logging meet bank-grade security standards

2. **Research-Backed**: All major technical decisions (Argon2id over bcrypt, JWT rotation strategy, rate limits) are based on 2025 best practices from NIST, OWASP, and industry research

3. **Production-Ready**: Async-first architecture, proper error handling, structured logging, Docker containerization, and 80%+ test coverage ensure production readiness

4. **Maintainable**: Layered architecture (routes → services → repositories → models) with clear separation of concerns makes code easy to understand, test, and modify

5. **Compliant**: Comprehensive audit logging with immutability, soft deletes, and 7-year retention meet GDPR and SOX requirements for financial applications

### Next Steps

1. **Review this plan** with technical lead and product owner
2. **Clarify any ambiguities** or open questions
3. **Set up development environment** (GitHub repo, CI/CD pipeline, cloud accounts)
4. **Begin Phase 1.1 implementation** following the detailed task breakdown

This plan is ready for implementation. All components are specified in detail with clear acceptance criteria, test requirements, and implementation notes. The 6-week timeline is realistic for a single experienced developer, with built-in validation points at each phase boundary.

---

**Plan Status**: ✅ **Ready for Implementation**
**Next Action**: Schedule Phase 1 kickoff meeting

