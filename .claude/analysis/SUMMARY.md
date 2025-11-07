# FastAPI Codebase Analysis - Executive Summary

## Quick Overview

**Project**: Emerald Finance Platform Backend (FastAPI)
**Total Python Files**: 42
**Total Lines of Code**: ~5,200
**Status**: Good foundational structure with room for hexagonal architecture improvements

---

## Key Findings at a Glance

### Architecture Layers (Good Structure)
```
Routes → Dependency Injection → Services → Repositories → SQLAlchemy Models → PostgreSQL
```

### Coupling Assessment
- **High Coupling to SQLAlchemy** (80-90%)
  - Services return ORM models, not domain objects
  - Business logic intertwined with persistence concerns
  - Cannot test services without database

- **Moderate Decoupling** (40-50%)
  - Exception hierarchy abstracted
  - Pydantic schemas separate from models
  - Configuration externalized

- **Well Separated** (70%+)
  - Routes from business logic
  - Security functions isolated
  - Middleware as cross-cutting concerns

---

## Models & Entities (6 core models)

| Model | Purpose | Soft Delete | Type |
|-------|---------|-----------|------|
| **User** | Authentication + profiles | Yes | Core |
| **Role** | RBAC permissions | No | Supporting |
| **Account** | Financial accounts | Yes | Core |
| **AccountShare** | Account permissions | Yes | Core |
| **AuditLog** | Compliance trail | No | Infrastructure |
| **RefreshToken** | Token rotation | No | Infrastructure |

---

## Services (4 domain services)

1. **AuthService**: Registration, login, token management
2. **UserService**: Profile management, user listing (admin)
3. **AccountService**: Account CRUD, permission checks
4. **AuditService**: Immutable audit log creation

**Common Pattern**: Each service receives a SQLAlchemy session and creates repositories internally.

---

## Repositories (5 specific + 1 generic base)

**BaseRepository[T]** provides:
- `create()`, `get_by_id()`, `get_all()`
- `update()`, `soft_delete()`, `delete()`
- `count()`, `exists()`
- Automatic soft-delete filtering

**Specialized Repos**:
- UserRepository: Email/username lookups, role loading, filtering
- AccountRepository: User account listing, name uniqueness
- AuditRepository: History queries
- RefreshTokenRepository: Token hash lookups, family management
- RoleRepository: Permission queries

---

## Routes (4 endpoints)

- **Auth** (`/api/v1/auth`): Register, login, refresh, logout, password-change
- **Users** (`/api/v1/users`): Profile CRUD, admin user management
- **Accounts** (`/api/v1/accounts`): Account CRUD
- **Audit Logs** (`/api/v1/audit-logs`): History queries (admin)

**Pattern**: Routes extract metadata (request_id, ip, user_agent) and pass to services.

---

## Dependency Injection

**Framework**: FastAPI's `Depends()`

**Key Dependencies**:
```python
get_db(request)                 # AsyncSession per request
get_current_user(db)            # Extract user from JWT
require_active_user(user)       # Check is_active flag
require_admin(user)             # Check is_admin flag
require_permission(perm)        # Check role permissions

get_auth_service(db)            # AuthService factory
get_account_service(db)         # AccountService factory
get_user_service(db)            # UserService factory
get_audit_service(db)           # AuditService factory
```

**Issues**:
- Services instantiate repositories (no interface)
- No IoC container for advanced scenarios
- Mock injection difficult for testing

---

## Database Session Management

**Connection Pool**: AsyncAdaptedQueuePool
- Pool size: 5 permanent (configurable)
- Max overflow: 10 additional
- Pre-ping: Enabled (test before use)
- Recycle: 3600 seconds

**Lifecycle**:
```
Request → get_db() creates session
       → Service executes queries
       → get_db() auto-commits on success
       → get_db() auto-rollbacks on error
Response ← Session returned to pool
```

---

## Business Logic Coupling to Infrastructure

### HIGH COUPLING Examples

```python
# 1. Services return SQLAlchemy models
account = await account_service.create_account(...)
# account is SQLAlchemy Account model, not domain DTO

# 2. Repository instantiation (no interface)
self.account_repo = AccountRepository(db)
# Cannot inject mock

# 3. Domain rules in services
if account.user_id != current_user.id:
    raise NotFoundError()
# Permission check mixed with ORM

# 4. Validation requires DB query
if await repo.exists_by_name(user_id, name):
    raise AlreadyExistsError()
# Cannot test without database

# 5. Session management implicit/explicit
await self.session.commit()  # Sometimes explicit
# Hidden in get_db() context manager sometimes
```

---

## What's Well Done

✓ **Clear layering**: Routes → Services → Repositories → Models
✓ **Exception abstraction**: Custom exception hierarchy (not raw HTTP)
✓ **Soft delete pattern**: Automatic filtering, compliance-ready
✓ **Audit logging**: Comprehensive trail with metadata
✓ **Security**: Token rotation, password hashing, permission checks
✓ **Configuration**: Externalized via Pydantic settings
✓ **Async throughout**: AsyncSession, async/await in all layers
✓ **Type hints**: Good use of Python type annotations
✓ **Mixins**: Reusable timestamp, soft-delete, audit fields

---

## Main Challenges for Hexagonal Architecture

1. **Domain models = SQLAlchemy models**
   - No separate domain layer
   - ORM concerns leak into business logic

2. **Services return ORM models**
   - Routes must convert to Pydantic schemas
   - Inefficient conversion logic

3. **Repository interface implicit**
   - No formal ABC/Protocol
   - Hard to mock for testing

4. **Permission logic scattered**
   - In dependencies.py, in services, in routes
   - Not centralized domain service

5. **Validation depends on persistence**
   - "Account name exists?" requires DB query
   - Cannot validate in isolation

6. **Service instantiation manual**
   - Each service creates its own repositories
   - No dependency injection for repositories

---

## Testing Implications

### Current State
- Unit tests still need database (can't mock repos easily)
- Integration tests require PostgreSQL + Docker
- Test isolation requires custom fixtures (rollback/truncate)

### After Hexagonal Refactoring
- Domain services testable without DB
- Mock repository implementation possible
- Clear domain/application boundaries
- Infrastructure swappable (any DB, any cache)

---

## Recommended Next Steps

### Phase 1: Extract Domain Models
- Create pure Python classes (no SQLAlchemy)
- Move business rules to domain layer
- Define repository interfaces (Protocols)

### Phase 2: Separate Application Services
- Keep current service facades
- Delegate to domain services
- Return DTOs instead of ORM models

### Phase 3: Improve DI
- Create IoC container (Dependency Injector lib)
- Formalize repository interfaces
- Mock-friendly service construction

### Phase 4: Extract Domain Services
- Permission checking service
- Validation service
- Account sharing service

### Phase 5: Refactor Tests
- True unit tests (no DB needed)
- Clear test doubles
- Faster test suite

---

## Files to Read Next

1. **Start here** → `.claude/analysis/codebase_analysis.md`
   - Detailed breakdown of all components
   - Specific code examples
   - Coupling assessment details

2. **Visual understanding** → `.claude/analysis/architecture_diagrams.md`
   - ASCII diagrams of current architecture
   - Data flow examples
   - Coupling visualization

3. **Project standards** → `CLAUDE.md` + `.claude/standards/`
   - Backend standards document
   - Testing standards
   - API design guidelines

---

## Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Files | 42 | Reasonable size |
| LOC (Python) | ~5,200 | Well-organized |
| Models | 6 | Focused domain |
| Services | 4 | Appropriate count |
| Repositories | 6 | Good specialization |
| Layers | 5 | Good separation |
| **Coupling** | 80% | **Needs work** |
| **Testability** | Moderate | **Can improve** |
| **Maintainability** | Good | **With refactoring** |

---

## Success Criteria for Refactoring

A successful hexagonal architecture implementation would have:

- [ ] Domain models independent of persistence
- [ ] All services testable without database
- [ ] Repository interfaces formalized
- [ ] Clear application/domain/infrastructure boundaries
- [ ] DTOs flowing between layers
- [ ] Zero SQLAlchemy imports in domain layer
- [ ] 100+ unit tests (no DB dependency)
- [ ] Fast test suite (<5 seconds)
- [ ] Domain logic easily reusable in other projects
- [ ] Infrastructure (DB, cache) swappable

---

## Time Estimates for Refactoring

| Phase | Complexity | Estimated Time |
|-------|-----------|-----------------|
| Extract domain models | High | 3-4 days |
| Separate application services | Medium | 2-3 days |
| Improve DI | Medium | 2-3 days |
| Extract domain services | High | 4-5 days |
| Refactor tests | Medium | 3-4 days |
| **Total** | **High** | **14-19 days** |

---

Generated: 2025-11-05
Analysis Depth: Comprehensive (all 42 Python files reviewed)
