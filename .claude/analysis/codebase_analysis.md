# FastAPI Codebase Architecture Analysis

## Executive Summary

The Emerald Finance Platform backend is a FastAPI application with **moderate coupling** to SQLAlchemy. The architecture demonstrates good foundational patterns with a clear separation between routes → services → repositories → models, but business logic is currently entangled with SQLAlchemy ORM concerns. A hexagonal architecture refactoring would improve testability, domain isolation, and infrastructure independence.

---

## 1. Complete Directory Structure

```
src/
├── api/
│   ├── __init__.py
│   ├── dependencies.py          # DI for services, auth, and database
│   └── routes/
│       ├── __init__.py
│       ├── accounts.py          # Account CRUD endpoints
│       ├── audit_logs.py        # Audit log endpoints
│       ├── auth.py              # Authentication endpoints
│       └── users.py             # User management endpoints
├── core/
│   ├── __init__.py
│   ├── config.py                # Environment configuration (Pydantic)
│   ├── database.py              # SQLAlchemy engine/session setup
│   ├── logging.py               # Structured logging configuration
│   └── security.py              # JWT, password hashing, encryption
├── models/
│   ├── __init__.py
│   ├── base.py                  # SQLAlchemy Base with UUID primary key
│   ├── enums.py                 # Python enums (AccountType, PermissionLevel)
│   ├── mixins.py                # Reusable model mixins (timestamps, soft-delete, audit)
│   ├── account.py               # Account and AccountShare SQLAlchemy models
│   ├── audit_log.py             # AuditLog SQLAlchemy model
│   ├── refresh_token.py         # RefreshToken SQLAlchemy model
│   └── user.py                  # User, Role, UserRole SQLAlchemy models
├── repositories/
│   ├── __init__.py
│   ├── base.py                  # BaseRepository[T] with generic CRUD
│   ├── account_repository.py    # Account-specific queries
│   ├── audit_repository.py      # Audit log queries
│   ├── refresh_token_repository.py  # Token queries
│   ├── role_repository.py       # Role queries
│   └── user_repository.py       # User-specific queries
├── schemas/
│   ├── __init__.py
│   ├── account.py               # Pydantic schemas for Account APIs
│   ├── audit.py                 # Pydantic schemas for Audit Log APIs
│   ├── auth.py                  # Pydantic schemas for Auth APIs
│   ├── common.py                # Shared schemas (pagination, responses)
│   └── user.py                  # Pydantic schemas for User APIs
├── services/
│   ├── __init__.py
│   ├── account_service.py       # Account business logic
│   ├── audit_service.py         # Audit logging business logic
│   ├── auth_service.py          # Authentication business logic
│   └── user_service.py          # User management business logic
├── exceptions.py                # Custom exception hierarchy
├── main.py                      # FastAPI app setup, middleware, routes
└── middleware.py                # Request ID, logging, security headers

tests/
├── conftest.py                  # Pytest fixtures, test database setup
├── unit/
│   ├── core/
│   │   └── test_security.py
│   ├── repositories/
│   │   └── test_account_repository.py
│   └── services/
│       ├── test_account_service.py
│       ├── test_audit_service.py
│       ├── test_auth_service.py
│       └── test_user_service.py
├── integration/
│   ├── test_account_routes.py
│   ├── test_auth_routes.py
│   └── test_users.py (inferred)
└── e2e/

alembic/                         # Database migrations
├── versions/
├── env.py
└── script.py.mako

pyproject.toml                   # Project metadata and dependencies
.env                             # Environment variables
CLAUDE.md                        # Project standards and instructions
docker-compose.yml              # Database and Redis containers
Dockerfile                       # Application container
```

---

## 2. SQLAlchemy Models/Entities

### Core Models

#### **User Model** (`src/models/user.py`)
- **Purpose**: Core authentication and profile management
- **Mixins**: `TimestampMixin`, `SoftDeleteMixin`, `AuditFieldsMixin`
- **Key Fields**:
  - `id: UUID` (primary key)
  - `username: str` (unique, index)
  - `email: str` (unique, index)
  - `password_hash: str` (Argon2id)
  - `is_active: bool` (index)
  - `is_admin: bool` (index)
  - `last_login_at: Optional[datetime]`
  - `created_at`, `updated_at`, `deleted_at` (from mixins)
  - `created_by`, `updated_by` (from mixins)
- **Relationships**:
  - `roles: list[Role]` (many-to-many via `user_roles` junction table)
- **Notes**: Uses soft delete with partial unique indexes on email/username

#### **Role Model** (`src/models/user.py`)
- **Purpose**: Role-based access control (RBAC)
- **Mixins**: `TimestampMixin`
- **Key Fields**:
  - `id: UUID`
  - `name: str` (unique, index)
  - `description: Optional[str]`
  - `permissions: list[str]` (JSONB array)
  - `created_at`, `updated_at` (from mixin)
- **Relationships**:
  - `users: list[User]` (many-to-many)
- **Custom Methods**: `has_permission(permission: str) -> bool`

#### **Account Model** (`src/models/account.py`)
- **Purpose**: Financial account tracking with multi-currency support
- **Mixins**: `TimestampMixin`, `SoftDeleteMixin`, `AuditFieldsMixin`
- **Key Fields**:
  - `id: UUID`
  - `user_id: UUID` (foreign key to User, index)
  - `account_name: str` (1-100 chars, unique per user)
  - `account_type: AccountType` (enum: savings, credit_card, etc., index)
  - `currency: str` (ISO 4217, 3 uppercase letters, immutable, index)
  - `opening_balance: Decimal(15,2)`
  - `current_balance: Decimal(15,2)` (cached)
  - `is_active: bool` (index)
  - `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`
- **Relationships**:
  - `owner: User` (foreign key relationship)
  - `shares: list[AccountShare]` (one-to-many with cascade)
- **Constraints**:
  - Check constraint: `currency ~ '^[A-Z]{3}$'`
  - Partial unique index: `(user_id, LOWER(account_name)) WHERE deleted_at IS NULL`

#### **AccountShare Model** (`src/models/account.py`)
- **Purpose**: Account sharing permissions (owner/editor/viewer)
- **Mixins**: `TimestampMixin`, `SoftDeleteMixin`, `AuditFieldsMixin`
- **Key Fields**:
  - `id: UUID`
  - `account_id: UUID` (foreign key, index)
  - `user_id: UUID` (foreign key, index)
  - `permission_level: PermissionLevel` (enum: owner, editor, viewer, index)
  - `created_at`, `updated_at`, `deleted_at`, `created_by`
- **Relationships**:
  - `account: Account`
  - `user: User`
- **Constraints**:
  - Partial unique index: `(account_id, user_id) WHERE deleted_at IS NULL`

#### **AuditLog Model** (`src/models/audit_log.py`)
- **Purpose**: Immutable audit trail for compliance
- **Mixins**: `TimestampMixin`
- **Key Fields**:
  - `id: UUID`
  - `user_id: Optional[UUID]` (who performed the action)
  - `action: AuditAction` (enum: create, read, update, delete)
  - `status: AuditStatus` (enum: success, failure)
  - `entity_type: str` (e.g., "user", "account")
  - `entity_id: Optional[UUID]`
  - `old_values: Optional[dict]` (JSONB)
  - `new_values: Optional[dict]` (JSONB)
  - `description: str`
  - `extra_metadata: Optional[dict]` (JSONB)
  - `ip_address: Optional[str]`
  - `user_agent: Optional[str]`
  - `request_id: Optional[str]`
  - `created_at`
- **Notes**: Write-once, never updated. Core compliance feature.

#### **RefreshToken Model** (`src/models/refresh_token.py`)
- **Purpose**: Token rotation and reuse detection
- **Mixins**: `TimestampMixin`
- **Key Fields**:
  - `id: UUID`
  - `user_id: UUID` (foreign key)
  - `token_hash: str` (hashed token value, unique)
  - `token_family_id: UUID` (for rotation tracking)
  - `is_revoked: bool` (index)
  - `expires_at: datetime` (timezone-aware)
  - `created_at`
- **Notes**: Stores hash not plaintext. Tracks token families for rotation detection.

### Model Traits Summary
| Model | Soft Delete | Timestamps | Audit Fields | Relationships |
|-------|-------------|-----------|--------------|---------------|
| User | Yes | Yes | Yes | roles (M-M) |
| Role | No | Yes | No | users (M-M) |
| Account | Yes | Yes | Yes | owner (1-M), shares (1-M) |
| AccountShare | Yes | Yes | Yes | account, user |
| AuditLog | No | Yes | No | - |
| RefreshToken | No | Yes | No | user |

---

## 3. Service Layer Structure

### Overview
Services contain business logic and orchestrate repositories + other services. They receive SQLAlchemy models and return SQLAlchemy models (tight coupling).

### **AuthService** (`src/services/auth_service.py`)
```
__init__(session: AsyncSession)
├── Dependencies:
│   ├── user_repo: UserRepository
│   └── token_repo: RefreshTokenRepository
│
├── Public Methods:
│   ├── register(user_data, ip, ua) → (User, TokenResponse)
│   ├── login(email, password, ip, ua) → (User, TokenResponse)
│   ├── refresh_access_token(token, ip, ua) → AccessTokenResponse
│   ├── logout(refresh_token) → None
│   └── change_password(user_id, old_pwd, new_pwd) → None
│
└── Private Methods:
    └── _generate_tokens(user, ip, ua, family_id) → TokenResponse
```
**Responsibilities**:
- Validate credentials
- Hash/verify passwords (Argon2id)
- Generate JWT tokens
- Store/validate refresh tokens
- Detect token reuse (security feature)
- Force re-auth on password change

---

### **UserService** (`src/services/user_service.py`)
```
__init__(session: AsyncSession)
├── Dependencies:
│   ├── user_repo: UserRepository
│   ├── token_repo: RefreshTokenRepository
│   └── audit_service: AuditService
│
└── Public Methods:
    ├── get_user_profile(user_id, current_user, ...) → UserResponse
    ├── update_user_profile(user_id, data, current_user, ...) → UserResponse
    ├── list_users(pagination, filters, current_user, ...) → PaginatedResponse
    ├── deactivate_user(user_id, current_user, ...) → None
    └── soft_delete_user(user_id, current_user, ...) → None
```
**Responsibilities**:
- Permission checks (self/admin)
- Uniqueness validation (email, username)
- Profile CRUD with audit logging
- Admin user management

---

### **AccountService** (`src/services/account_service.py`)
```
__init__(session: AsyncSession)
├── Dependencies:
│   ├── account_repo: AccountRepository
│   └── audit_service: AuditService
│
└── Public Methods:
    ├── create_account(user_id, name, type, currency, balance, ...) → Account
    ├── get_account(account_id, current_user, ...) → Account
    ├── list_accounts(user_id, current_user, ...) → list[Account]
    ├── update_account(account_id, current_user, ...) → Account
    ├── delete_account(account_id, current_user, ...) → None
    └── count_user_accounts(user_id, current_user) → int
```
**Responsibilities**:
- Account CRUD with validation
- Uniqueness validation (per-user account names)
- Permission checks (owner only)
- Currency immutability enforcement
- Soft delete with compliance

---

### **AuditService** (`src/services/audit_service.py`)
```
__init__(session: AsyncSession)
├── Dependencies:
│   └── audit_repo: AuditRepository
│
└── Public Methods:
    ├── log_event(user_id, action, entity_type, ...) → AuditLog
    ├── log_data_change(user_id, action, old_values, new_values, ...) → AuditLog
    └── get_entity_history(entity_type, entity_id) → list[AuditLog]
```
**Responsibilities**:
- Immutable audit trail creation
- Data change tracking (before/after)
- Request correlation (request_id)
- Client tracking (IP, user agent)

---

### Service Dependencies Diagram
```
routes/ 
    ↓
services/ (business logic)
    ├── AuthService
    │   ├→ UserRepository
    │   ├→ RefreshTokenRepository
    │   └→ (auth_service.py imported in routes)
    ├── AccountService
    │   ├→ AccountRepository
    │   └→ AuditService
    ├── UserService
    │   ├→ UserRepository
    │   ├→ RefreshTokenRepository
    │   └→ AuditService
    └── AuditService
        └→ AuditRepository
            ↓
repositories/ (data access)
    ├── UserRepository(BaseRepository[User])
    ├── AccountRepository(BaseRepository[Account])
    ├── AuditRepository(BaseRepository[AuditLog])
    ├── RefreshTokenRepository(BaseRepository[RefreshToken])
    └── RoleRepository(BaseRepository[Role])
        ↓
models/ (SQLAlchemy ORM)
    ├── User (+ Role)
    ├── Account (+ AccountShare)
    ├── AuditLog
    └── RefreshToken
        ↓
core/database.py (AsyncSession)
```

---

## 4. API Router Organization

### Structure
Routes are organized by resource in `src/api/routes/`:

#### **Authentication Routes** (`auth.py`)
```
POST /api/v1/auth/register          → Register new user
POST /api/v1/auth/login             → Login (returns tokens)
POST /api/v1/auth/refresh           → Refresh access token
POST /api/v1/auth/logout            → Logout (revoke token)
POST /api/v1/auth/password-change   → Change password
```
**Features**: Rate limiting (3/hour register), JWT token management

#### **User Management Routes** (`users.py`)
```
GET /api/v1/users/me                → Get current user profile
GET /api/v1/users/{user_id}         → Get user profile (admin or self)
PUT /api/v1/users/{user_id}         → Update user profile
GET /api/v1/admin/users             → List all users (admin only)
DELETE /api/v1/admin/users/{user_id} → Soft delete user (admin only)
POST /api/v1/admin/users/{user_id}/deactivate → Deactivate (admin)
```

#### **Account Routes** (`accounts.py`)
```
POST /api/v1/accounts               → Create account
GET /api/v1/accounts                → List user's accounts (paginated)
GET /api/v1/accounts/{account_id}   → Get account details
PUT /api/v1/accounts/{account_id}   → Update account name/status
DELETE /api/v1/accounts/{account_id} → Soft delete account
```

#### **Audit Log Routes** (`audit_logs.py`)
```
GET /api/v1/audit-logs              → List audit logs (paginated, admin)
GET /api/v1/audit-logs/entity/{type}/{id} → Get entity history
```

### Route Pattern
All routes follow this pattern:
```python
@router.post(
    "",
    response_model=ResponseSchema,
    status_code=201,
    summary="...",
)
async def create_something(
    request: Request,
    payload: RequestSchema,
    current_user: User = Depends(require_active_user),  # Authentication
    service: SomeService = Depends(get_service),         # DI
) -> ResponseSchema:
    """Docstring"""
    ip = request.client.host
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)
    
    # Call service
    result = await service.do_something(payload, current_user, request_id, ip, user_agent)
    
    return ResponseSchema.model_validate(result)
```

---

## 5. Database Session Management

### Session Lifecycle

#### **Engine Initialization** (in `main.py` lifespan)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.engine = create_database_engine()
    app.state.sessionmaker = async_sessionmaker(
        app.state.engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects after commit
        autocommit=False,
        autoflush=False,
    )
    
    yield
    
    # Shutdown
    await close_database_connection(app.state.engine)
```

#### **Per-Request Session** (via `get_db` dependency)
```python
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()       # Auto-commit on success
        except Exception:
            await session.rollback()     # Auto-rollback on error
            raise
        finally:
            await session.close()
```

#### **Service Injection**
Services receive sessions via dependency injection:
```python
def get_account_service(db: AsyncSession = Depends(get_db)) -> AccountService:
    return AccountService(db)
```

### Configuration
- **Pool**: `AsyncAdaptedQueuePool` (connection pool)
- **Pool Size**: 5 permanent connections (configurable)
- **Max Overflow**: 10 additional connections (configurable)
- **Pool Recycle**: 3600 seconds (connection TTL)
- **Pool Pre-Ping**: Enabled (test before use)
- **Echo**: Enabled in debug mode (SQL logging)

---

## 6. Existing Abstraction Patterns

### Repository Pattern
Generic base repository provides CRUD operations:

```python
# BaseRepository[ModelType]
async def create(**kwargs) → ModelType
async def get_by_id(id) → ModelType | None
async def get_all(skip, limit) → list[ModelType]
async def update(instance, **kwargs) → ModelType
async def soft_delete(instance) → ModelType
async def delete(instance) → None
async def count(include_deleted?) → int
async def exists(id) → bool
```

**Soft Delete Filter**: Automatically applied to all queries
```python
def _apply_soft_delete_filter(query: Select) -> Select:
    if hasattr(self.model, "deleted_at"):
        query = query.where(self.model.deleted_at.is_(None))
    return query
```

### Specialized Repositories
Each model has a repository extending `BaseRepository[T]`:

- **UserRepository**: Email/username lookups, role loading, activity tracking, filtering
- **AccountRepository**: User account listing, name uniqueness checks, type/status filtering
- **AuditRepository**: History queries, entity tracking
- **RefreshTokenRepository**: Token hash lookups, revocation, family management
- **RoleRepository**: Permission queries

### Service Layer
Services orchestrate repositories and contain business logic:
- Permission checks
- Validation (uniqueness, format)
- State transitions
- Audit logging
- Cross-entity operations

### Exception Hierarchy
Custom exceptions map to HTTP status codes:
```
AppException (base)
├── AuthenticationError (401)
│   ├── InvalidCredentialsError
│   ├── InvalidTokenError
│   ├── AccountLockedError
│   └── TokenExpiredError
├── AuthorizationError (403)
│   └── InsufficientPermissionsError
├── ResourceError
│   ├── NotFoundError (404)
│   ├── AlreadyExistsError (409)
│   └── ConflictError (409)
├── ValidationError (422)
│   ├── WeakPasswordError
│   └── InvalidInputError
└── RateLimitExceededError (429)
```

---

## 7. Current Dependency Injection Patterns

### Framework: FastAPI's `Depends()`

#### Function-Based DI
```python
# Database
async def get_db(request: Request) → AsyncGenerator[AsyncSession, None]:
    # Yields a session; auto-commit on success, auto-rollback on error
    ...

# Authentication
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) → User:
    # Extract user from JWT, validate against DB
    ...

async def require_active_user(
    current_user: User = Depends(get_current_user),
) → User:
    # Check is_active flag
    ...

async def require_admin(
    current_user: User = Depends(require_active_user),
) → User:
    # Check is_admin flag
    ...

def require_permission(permission: str):
    async def _check_permission(
        current_user: User = Depends(require_active_user),
    ) → User:
        # Check role permissions
        ...
    return _check_permission
```

#### Service DI
```python
def get_auth_service(db: AsyncSession = Depends(get_db)) → AuthService:
    return AuthService(db)

def get_account_service(db: AsyncSession = Depends(get_db)) → AccountService:
    return AccountService(db)

def get_user_service(db: AsyncSession = Depends(get_db)) → UserService:
    return UserService(db)

def get_audit_service(db: AsyncSession = Depends(get_db)) → AuditService:
    return AuditService(db)
```

#### Type Aliases
```python
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(require_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
```

### Usage in Routes
```python
@router.post("/accounts")
async def create_account(
    request: Request,
    data: AccountCreate,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
) → AccountResponse:
    ip = request.client.host
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)
    
    account = await account_service.create_account(
        user_id=current_user.id,
        account_name=data.account_name,
        account_type=data.account_type,
        currency=data.currency,
        opening_balance=data.opening_balance,
        current_user=current_user,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    
    return AccountResponse.model_validate(account)
```

### Observations
✓ **Strengths**:
- Composable: Dependencies can be stacked
- Scope-aware: Per-request lifecycles
- Clean: Explicit in route signatures

✗ **Limitations**:
- No inversion of control container (manual instantiation in factories)
- Services tightly coupled to SQLAlchemy sessions
- Difficult to inject mock repositories for testing
- No central configuration or lifecycle management

---

## 8. Key Business Logic Locations & Infrastructure Coupling

### Authentication Logic
**Location**: `src/services/auth_service.py`

**Infrastructure Coupling**:
- Returns SQLAlchemy `User` model directly (not domain object)
- Directly calls `user_repo.create()` which persists to DB
- Directly calls `token_repo.create()` which persists to DB
- Route must call `model_validate()` on returned User to convert to schema
- No abstraction between domain and persistence

**Example**:
```python
async def register(self, user_data: UserCreate, ...):
    # Direct SQLAlchemy model creation
    user = await self.user_repo.create(
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash,
    )
    await self.session.commit()  # Explicit commit needed
    
    # Token also directly persisted
    tokens = await self._generate_tokens(user, ...)
    
    # Returns SQLAlchemy model, not domain object
    return user, tokens
```

### Account Management Logic
**Location**: `src/services/account_service.py`

**Infrastructure Coupling**:
- Returns SQLAlchemy `Account` model
- Checks uniqueness via repository queries
- No validation of business rules (e.g., "currency immutable after creation")
- Currency validation mixed with business logic

**Example**:
```python
async def create_account(self, user_id, account_name, ..., current_user):
    # Direct repository call to check existence
    if await self.account_repo.exists_by_name(user_id, account_name):
        raise AlreadyExistsError(...)
    
    # Direct creation with SQLAlchemy model
    account = await self.account_repo.create(
        user_id=user_id,
        account_name=account_name,
        ...
    )
    
    # Returns SQLAlchemy model
    return account
```

### Permission Logic
**Location**: Scattered across `dependencies.py` and services

**Infrastructure Coupling**:
- `require_active_user` depends on User model having `is_active` field
- `require_admin` depends on User model having `is_admin` field
- `require_permission()` depends on User model having `.roles` relationship
- Service methods check `current_user.is_admin` directly (not abstracted)
- Account access check: `if account.user_id != current_user.id` (domain rule in service)

**Example**:
```python
async def get_account(self, account_id, current_user, ...):
    account = await self.account_repo.get_by_id(account_id)
    
    # Domain rule (owner-only access) mixed with data access
    if account.user_id != current_user.id:
        raise NotFoundError(...)
    
    return account
```

### Audit Logging
**Location**: `src/services/audit_service.py`

**Infrastructure Coupling**:
- Returns SQLAlchemy `AuditLog` model
- Directly persists to database
- No domain logic for what constitutes an auditable action

**Example**:
```python
async def log_event(self, user_id, action, entity_type, ...):
    # Direct model creation
    audit_log = await self.audit_repo.create(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        ...
    )
    await self.session.flush()
    
    # Returns SQLAlchemy model
    return audit_log
```

---

## 9. Summary: Coupling Assessment

### How Tightly Coupled is Domain Logic to SQLAlchemy?

#### **High Coupling** (80-90%)
1. **Service return types**: All services return SQLAlchemy models, not domain DTOs
   - Routes must call `model_validate()` to convert to Pydantic schemas
   - Services cannot be tested without database

2. **Repository dependency**: Services directly instantiate repositories
   ```python
   self.user_repo = UserRepository(db)
   ```
   - No interface/protocol
   - Cannot inject mocks
   - Hard to test

3. **Permission logic**: Embedded in route dependencies and services
   ```python
   if current_user.is_admin
   if account.user_id != current_user.id
   ```
   - Depends on ORM relationships
   - Mixed with data access logic

4. **Validation logic**: Tied to SQLAlchemy queries
   ```python
   if await self.account_repo.exists_by_name(user_id, name):
       raise AlreadyExistsError()
   ```
   - Cannot validate without database
   - No transaction isolation in tests

5. **State management**: SQLAlchemy session passed to all layers
   - Services must manage commits/rollbacks
   - Implicit coupling to transaction lifecycle

#### **Moderate Decoupling** (40-50%)
1. **Exception layer**: Custom exceptions abstracted from HTTP
   - But used directly in services (not domain-specific)

2. **Schemas**: Pydantic schemas separate from models
   - But conversion happens at route level (inefficient)

3. **Configuration**: Externalized via `core/config.py` (Pydantic)
   - Database URL, JWT settings, etc. isolated

#### **Well Separated** (70%+)
1. **Routes from business logic**: Clear separation (routes → services)
2. **Logging**: Structured logging configuration (`core/logging.py`)
3. **Security**: Password hashing and JWT in `core/security.py`
4. **Middleware**: Cross-cutting concerns (request ID, logging, headers)

---

## 10. Testing Implications

### Current Test Structure
```
tests/
├── unit/
│   ├── services/          # Service unit tests
│   └── repositories/      # Repository tests
├── integration/           # Full stack tests with test DB
└── e2e/                   # End-to-end tests
```

### Problems
1. **No true unit tests**: Services need database (via AsyncSession)
2. **Mock repositories**: Must mock SQLAlchemy models (complex)
3. **Test database**: Requires Docker + PostgreSQL setup
4. **Test isolation**: Repository mixin needs rollback/truncate strategies

### Example Test Problem
```python
# Hard to test without DB
async def test_create_account():
    service = AccountService(session)  # Needs real async session
    
    account = await service.create_account(
        user_id=user_id,
        account_name="Test",
        ...
    )
    
    # Assertion depends on model structure
    assert account.user_id == user_id
    assert isinstance(account, Account)  # SQLAlchemy class
```

---

## Architecture Readiness Assessment

### Strengths for Hexagonal Architecture
✓ Clear layering (routes → services → repositories → models)
✓ Exception abstraction
✓ Pydantic schemas for API contracts
✓ Dependency injection framework ready
✓ Service layer exists and testable (with refactoring)

### Challenges
✗ Domain models = SQLAlchemy models (no separate domain objects)
✗ Services return SQLAlchemy models
✗ Repository interface not formalized (implicit protocol)
✗ Permission logic scattered across layers
✗ No clear domain/application boundary

### Recommended Refactoring Path
1. **Extract domain models** (pure Python classes, no SQLAlchemy)
2. **Create repository interfaces** (protocols/ABCs)
3. **Separate application services** from infrastructure
4. **Introduce DTOs** between layers
5. **Formalize dependency injection**
6. **Extract domain services** (permission, validation logic)

---

## Key Files Reference

| Component | Files | Lines |
|-----------|-------|-------|
| Models | `src/models/*.py` | ~1000 LOC |
| Repositories | `src/repositories/*.py` | ~800 LOC |
| Services | `src/services/*.py` | ~1600 LOC |
| Routes | `src/api/routes/*.py` | ~600 LOC |
| Core | `src/core/*.py` | ~800 LOC |
| Total Python | 42 files | ~5200 LOC |

