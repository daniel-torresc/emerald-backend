# Architecture Diagrams and Visual Representations

## Current Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Routes (HTTP)                     │
│  /api/v1/auth, /api/v1/accounts, /api/v1/users, etc.        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Dependency Injection Layer                │
│  get_db, get_current_user, get_auth_service, etc.           │
│  (Implicit composition via FastAPI Depends)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Services (Business Logic)           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐          │
│  │ AuthService │  │ UserService │  │AccountService│ ...     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘          │
│         │                │                │                   │
│  Services receive SQLAlchemy models, not domain objects       │
│  Services are tightly coupled to repository/ORM concerns      │
└────────────┬──────────────┬──────────────┬───────────────────┘
             │              │              │
             ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Repository Layer                           │
│                                                                │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │UserRepo    │ │AccountRepo   │ │TokenRepo     │ ...       │
│  │(extends    │ │(extends      │ │(extends      │             │
│  │BaseRepo[U])│ │BaseRepo[Acc])│ │BaseRepo[Tok])│             │
│  └────────────┘ └──────────────┘ └──────────────┘             │
│                                                                │
│  BaseRepository[T] provides generic CRUD via SQLAlchemy       │
│  Soft delete filtering built-in                              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  SQLAlchemy ORM Models                        │
│                                                                │
│  ┌───────────┐  ┌────────────┐  ┌──────────────┐              │
│  │User       │  │Account     │  │AuditLog      │              │
│  │Role       │  │AccountShare│  │RefreshToken  │              │
│  └───────────┘  └────────────┘  └──────────────┘              │
│                                                                │
│  Mixins: TimestampMixin, SoftDeleteMixin, AuditFieldsMixin   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              AsyncSession (SQLAlchemy 2.0)                   │
│              Connection Pool Management                       │
│              Transactions (Commit/Rollback)                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                        │
│                                                                │
│  Tables: users, roles, accounts, account_shares,             │
│          refresh_tokens, audit_logs, ...                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Create Account

```
HTTP POST /api/v1/accounts
    │
    ├─ Request parsing (AccountCreate schema)
    │
    ▼
[accounts.py route handler]
    │
    ├─ Extract: current_user, request_id, ip_address
    │
    ├─ Call: account_service.create_account(
    │         user_id, name, type, currency, balance,
    │         current_user, request_id, ip, ua)
    │
    ▼
[AccountService.create_account()]
    │
    ├─ Check uniqueness: account_repo.exists_by_name()
    │    (Query to DB)
    │
    ├─ Validate currency format (business logic)
    │
    ├─ Create: account_repo.create(
    │         user_id, name, type, currency, balance, ...)
    │    (Persists to DB)
    │
    ├─ Log audit: audit_service.log_event(...)
    │    (Persists audit entry)
    │
    ▼
[Route returns AccountResponse]
    │
    ├─ Convert SQLAlchemy Account to Pydantic AccountResponse
    │    (model_validate() called)
    │
    ▼
HTTP 201 Created
└─ Response JSON with account details
```

---

## Permission Check Flow

```
Route Dependency Chain:
┌─────────────────────────────────────────────────────────────┐
│ @app.post("/accounts")                                       │
│ async def create_account(                                    │
│     current_user: User = Depends(require_active_user),  ←┐  │
│     ...                                                     │  │
│ )                                                          │  │
└────────────────────────────────────────────────────────────│──┘
                                                              │
                                ┌─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│ async def require_active_user(                              │
│     current_user: User = Depends(get_current_user)  ←──────┤
│ ) → User:                                                   │
│     if not current_user.is_active:                          │
│         raise HTTPException(403, "Account inactive")        │
│     return current_user                                     │
└────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ async def get_current_user(                                 │
│     credentials: HTTPAuthorizationCredentials = Depends(...),│
│     db: AsyncSession = Depends(get_db)              ←───────┤
│ ) → User:                                                   │
│     # Extract Bearer token                                  │
│     # Decode JWT                                            │
│     # Extract user_id from token claims                     │
│     user_repo = UserRepository(db)                          │
│     user = await user_repo.get_with_roles(user_id)          │
│     return user                                             │
└────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ async def get_db(request: Request) → AsyncSession:          │
│     sessionmaker = request.app.state.sessionmaker           │
│     async with sessionmaker() as session:                   │
│         try:                                                │
│             yield session                                   │
│             await session.commit()                          │
│         except:                                             │
│             await session.rollback()                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Service Instantiation

```
Route Dependencies:
┌──────────────────────────────────────────────────┐
│ account_service: AccountService                   │
│   = Depends(get_account_service)                  │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│ def get_account_service(                          │
│     db: AsyncSession = Depends(get_db)            │
│ ) → AccountService:                               │
│     return AccountService(db)                     │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│ class AccountService:                             │
│     def __init__(self, db: AsyncSession):         │
│         self.db = db                              │
│         self.account_repo = AccountRepository(db) │
│         self.audit_service = AuditService(db)     │
└──────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    AccountRepo    AuditService    [db session]
         │
         ▼
    BaseRepository[Account]
         │
         ▼
    SQLAlchemy Models
```

---

## Transaction Lifecycle

```
HTTP Request arrives
    │
    ▼
get_db() dependency creates AsyncSession
    │
    ├─ sessionmaker() creates new connection from pool
    │
    ▼
Route handler executes
    │
    ├─ May call multiple services
    ├─ Services may execute multiple queries
    ├─ Services may persist multiple entities
    │
    ├─ No explicit commits in service code
    │  (except auth_service.register() has explicit commit)
    │
    ▼
Route handler returns response (normal flow)
    │
    ▼
get_db() context manager exit with NO EXCEPTION
    │
    ├─ await session.commit()  ✓
    │
    ├─ await session.close()
    │
    ├─ Return connection to pool
    │
    ▼
HTTP Response sent


BUT if exception raised in route:
    │
    ▼
get_db() context manager exit WITH EXCEPTION
    │
    ├─ except Exception:
    │
    ├─ await session.rollback()  ✓
    │
    ├─ await session.close()
    │
    ├─ Re-raise exception
    │
    ▼
Exception handler returns error response
```

---

## Model Relationships

```
┌──────────────────────────────────────────────────────────────┐
│                       User (SQLAlchemy)                       │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ id: UUID (PK)                                            ││
│  │ username: str (unique, index)                            ││
│  │ email: str (unique, index)                               ││
│  │ password_hash: str                                       ││
│  │ is_active: bool (index)                                  ││
│  │ is_admin: bool (index)                                   ││
│  │ last_login_at: datetime                                  ││
│  │ created_at, updated_at, deleted_at: datetime             ││
│  │ created_by, updated_by: UUID                             ││
│  │                                                          ││
│  │ roles: list[Role] ◄──────┐                              ││
│  │ (M-M via user_roles)     │                               ││
│  └──────────────────────────────────────────────────────────┘│
└───────────────────────────────────┬──────────────────────────┘
                                    │
                    ┌───────────────┘
                    │
        ┌───────────┴──────────┐
        │                      │
        ▼                      ▼
    user_roles         ┌──────────────────────┐
    junction           │  Role (SQLAlchemy)   │
    table              │  id: UUID (PK)       │
                       │  name: str (unique)  │
                       │  description: str    │
                       │  permissions: list   │
                       │  (JSONB array)       │
                       │  users: list[User]   │
                       └──────────────────────┘


┌──────────────────────────────────────────────────────────────┐
│                     Account (SQLAlchemy)                      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ id: UUID (PK)                                            ││
│  │ user_id: UUID (FK → User) ◄──────────┐                 ││
│  │ account_name: str                    │                  ││
│  │ account_type: AccountType (enum)     │                  ││
│  │ currency: str (ISO 4217)             │                  ││
│  │ opening_balance: Decimal(15,2)       │                  ││
│  │ current_balance: Decimal(15,2)       │                  ││
│  │ is_active: bool                      │                  ││
│  │ created_at, updated_at, deleted_at   │                  ││
│  │ created_by, updated_by: UUID         │                  ││
│  │                                      │                  ││
│  │ owner: User ◄─────────────────────────┘                 ││
│  │ shares: list[AccountShare]                              ││
│  │ (1-M, cascade delete)                                   ││
│  └──────────────────────────────────────────────────────────┘│
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               AccountShare (SQLAlchemy)                       │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ id: UUID (PK)                                            ││
│  │ account_id: UUID (FK → Account)                          ││
│  │ user_id: UUID (FK → User)                                ││
│  │ permission_level: PermissionLevel (enum)                 ││
│  │   - OWNER: full access                                   ││
│  │   - EDITOR: read/write                                   ││
│  │   - VIEWER: read-only                                    ││
│  │ created_at, updated_at, deleted_at: datetime             ││
│  │ created_by: UUID                                         ││
│  │                                                          ││
│  │ account: Account  (FK relationship)                      ││
│  │ user: User        (FK relationship)                      ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

---

## Service Dependencies Graph

```
                        ┌─────────────────┐
                        │   AuthService   │
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                        │
                    ▼                        ▼
            UserRepository          RefreshTokenRepository
                    │                        │
                    └────────────┬───────────┘
                                 │
                                 ▼
                          AsyncSession (DB)


                    ┌──────────────────────┐
                    │  AccountService      │
                    └────────┬─────────────┘
                             │
                 ┌───────────┴──────────┐
                 │                      │
                 ▼                      ▼
        AccountRepository        AuditService
                 │                      │
                 │         ┌────────────┘
                 │         │
                 └────┬────┘
                      │
                      ▼
               AsyncSession (DB)


                    ┌──────────────────────┐
                    │   UserService        │
                    └────────┬─────────────┘
                             │
                 ┌───────────┼──────────┐
                 │           │          │
                 ▼           ▼          ▼
        UserRepository TokenRepository AuditService
                 │           │          │
                 └───────────┼──────────┘
                             │
                             ▼
                      AsyncSession (DB)
```

---

## Coupling Points Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   HIGH COUPLING POINTS                        │
└──────────────────────────────────────────────────────────────┘

1. Service Returns SQLAlchemy Models
   ┌─────────────────────────────────────┐
   │ await account_service.create_account │
   │     returns Account (SQLAlchemy)     │  ← Tightly coupled
   └─────────────────────────────────────┘    to ORM

2. Services Instantiate Repositories
   ┌─────────────────────────────────────┐
   │ self.account_repo = AccountRepo(db)  │  ← No interface
   │                                       │    No mockability
   └─────────────────────────────────────┘

3. Domain Rules in Services
   ┌─────────────────────────────────────┐
   │ if account.user_id != current_user.id│  ← Permission check
   │     raise NotFoundError               │    mixed with ORM
   └─────────────────────────────────────┘

4. Validation Requires DB Query
   ┌─────────────────────────────────────┐
   │ if await repo.exists_by_name(...):   │  ← Cannot test
   │     raise AlreadyExistsError         │    without DB
   └─────────────────────────────────────┘

5. Session Management Implicit
   ┌─────────────────────────────────────┐
   │ await self.session.commit()          │  ← Explicit in some
   │                                       │    Implicit in others
   │ # Hidden in get_db() context mgr     │
   └─────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────┐
│                  MODERATE DECOUPLING                          │
└──────────────────────────────────────────────────────────────┘

1. Custom Exception Hierarchy
   ✓ Abstracted from HTTP status codes
   ✗ Still used directly in services

2. Pydantic Schemas
   ✓ Separate from SQLAlchemy models
   ✗ Conversion at route level inefficient

3. Configuration
   ✓ Externalized via Pydantic settings
   ✓ Not scattered throughout code


┌──────────────────────────────────────────────────────────────┐
│                     GOOD SEPARATION                           │
└──────────────────────────────────────────────────────────────┘

1. Routes from Business Logic
   ✓ Clear handler → service → repo layer

2. Security Functions
   ✓ In core/security.py (not scattered)

3. Middleware/Cross-Cutting
   ✓ Request ID, logging, headers isolated

4. Configuration
   ✓ core/config.py (Pydantic settings)
```

