# Implementation Plan: Remove Role-Based Authorization System

**Date**: 2025-11-26
**Feature**: Remove Role-Based Authorization (RBAC)
**Status**: Planning Complete
**Complexity**: Medium
**Estimated Effort**: 3-4 days (1 developer)

---

## Executive Summary

This plan outlines the complete removal of the role-based authorization (RBAC) system from the Emerald Finance Platform backend. The current system uses a complex role-permission model with many-to-many relationships, dedicated repositories, services, and API endpoints. This will be replaced with a simpler authorization model using only the existing `is_admin` boolean flag on the User model.

### Primary Objectives

1. **Simplify Authorization**: Replace complex role-permission system with simple boolean flag
2. **Reduce Codebase Complexity**: Remove ~1,500+ lines of role-related code across 10+ files
3. **Maintain Admin Functionality**: Preserve all admin capabilities using `is_admin` flag
4. **Ensure Data Integrity**: Safely migrate database without data loss
5. **Preserve Audit Trail**: Maintain all existing audit logs (immutable requirement)

### Expected Outcomes

- **Simpler Authorization Model**: Single boolean check instead of role aggregation
- **Reduced Maintenance Burden**: Fewer files, models, and dependencies to maintain
- **Improved Performance**: No JOIN queries to fetch user roles/permissions
- **Preserved Functionality**: All admin operations continue to work
- **Clean Codebase**: Complete removal of unused role infrastructure

### Success Criteria

- ✅ All role-related database tables removed (roles, user_roles)
- ✅ All role-related code files deleted (repositories, services, routes, schemas)
- ✅ All tests passing with 80%+ coverage
- ✅ Superuser creation still works via migration
- ✅ Admin endpoints protected by `is_admin` flag only
- ✅ No broken imports or references to role code
- ✅ Audit logs remain intact and accessible

---

## Technical Architecture

### 2.1 System Design Overview

**Current Architecture** (Before):
```
┌─────────────────────────────────────────────────┐
│  User Model                                     │
│  - id, email, is_admin                          │
│  - roles: Mapped[list[Role]]  ← REMOVE          │
└─────────────────────────────────────────────────┘
            │
            │ Many-to-Many
            ▼
┌─────────────────────────────────────────────────┐
│  user_roles Junction Table  ← REMOVE            │
│  - user_id, role_id, assigned_at, assigned_by   │
└─────────────────────────────────────────────────┘
            │
            │
            ▼
┌─────────────────────────────────────────────────┐
│  Role Model  ← REMOVE                           │
│  - id, name, description                        │
│  - permissions: JSONB array                     │
└─────────────────────────────────────────────────┘

Authorization Flow:
Request → JWT → get_current_user() → require_permission() →
  → Fetch user.roles → Aggregate permissions → Check permission
```

**New Architecture** (After):
```
┌─────────────────────────────────────────────────┐
│  User Model                                     │
│  - id, email, is_admin                          │
│  (roles relationship removed)                   │
└─────────────────────────────────────────────────┘

Authorization Flow:
Request → JWT → get_current_user() → require_admin() →
  → Check is_admin flag → Allow/Deny
```

**Key Integration Points**:
- `src/api/dependencies.py`: Authorization dependencies
- `src/api/routes/users.py`: Admin-protected endpoints
- `alembic/versions/`: Database migrations
- `tests/conftest.py`: Test fixtures

**Data Flow Changes**:
- **Before**: User → roles → permissions (multi-step aggregation)
- **After**: User → is_admin (single boolean check)

---

### 2.2 Technology Decisions

#### **Alembic Migration Strategy**

**Purpose**: Safely remove database tables and relationships without data loss

**Why this choice**:
- Alembic is already the established migration tool in the project
- Supports both upgrade and downgrade paths for rollback capability
- Can handle complex foreign key constraint removal
- Integrates with async SQLAlchemy 2.0

**Version**: Alembic 1.13+ (current project version)

**Alternatives considered**:
- ❌ Manual SQL scripts: Less safe, no version tracking
- ❌ Raw PostgreSQL DROP: No rollback capability
- ✅ Alembic: Industry standard, safe, reversible

**Implementation notes**:
- Use `op.drop_constraint()` before `op.drop_table()` (order matters)
- Must specify constraint names explicitly for PostgreSQL
- Downgrade path recreates tables for rollback (data loss on downgrade)

#### **FastAPI Dependency Injection Pattern**

**Purpose**: Replace `require_permission()` factory with simple `require_admin()` dependency

**Why this choice**:
- Follows existing pattern in `src/api/dependencies.py`
- Type-safe with `Annotated[User, Depends(require_admin)]`
- Integrates with OpenAPI documentation
- No middleware required (simpler than middleware approach)

**Version**: FastAPI 0.115+ (current project version)

**Alternatives considered**:
- ❌ Custom middleware: Harder to apply selectively per endpoint
- ❌ Decorator pattern: Doesn't integrate with FastAPI dependency system
- ✅ Depends() pattern: FastAPI best practice, already used in project

**Reference**: [FastAPI Middleware vs Dependencies](https://fastapi.tiangolo.com/tutorial/middleware/)

---

### 2.3 File Structure

**Files to DELETE** (9 files):
```
src/
├── repositories/
│   └── role_repository.py              ← DELETE ENTIRE FILE
├── services/
│   └── admin_service.py                ← DELETE ENTIRE FILE (675 lines)
├── api/
│   └── routes/
│       └── admin.py                    ← DELETE ENTIRE FILE (340 lines)
└── schemas/
    └── admin.py                        ← DELETE ENTIRE FILE (263 lines)

tests/
├── integration/
│   └── test_admin_routes.py            ← DELETE ENTIRE FILE
└── e2e/
    └── test_admin_workflow.py          ← DELETE ENTIRE FILE

alembic/versions/
├── 9cfdc3051d85_create_enums_and_extensions.py  ← MODIFY (remove role audit actions)
└── 4aabd1426c98_initial_schema.py               ← MODIFY (remove role tables)
```

**Files to MODIFY** (11 files):
```
src/
├── models/
│   ├── user.py                         ← Remove Role model, user_roles table, roles relationship
│   └── __init__.py                     ← Remove Role, user_roles exports
├── repositories/
│   ├── user_repository.py              ← Remove selectinload(User.roles), get_with_roles()
│   └── __init__.py                     ← Remove RoleRepository export
├── services/
│   └── user_service.py                 ← Remove get_with_roles() call
├── api/
│   ├── dependencies.py                 ← Remove require_permission() factory
│   └── routes/
│       └── users.py                    ← Keep require_admin() usage (no changes needed)
├── core/
│   └── config.py                       ← Remove superadmin_permissions field
└── models/
    └── enums.py                        ← Remove ROLE_ASSIGN, ROLE_REMOVE from AuditAction

tests/
└── conftest.py                         ← Keep admin_user, admin_token fixtures (no changes)

alembic/versions/
└── <new>_remove_role_tables.py         ← CREATE NEW MIGRATION
```

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Database Migration

**Files Involved**:
- `alembic/versions/<new>_remove_role_tables.py` (new migration)
- `alembic/versions/9cfdc3051d85_create_enums_and_extensions.py` (modify)
- `alembic/versions/4aabd1426c98_initial_schema.py` (modify - optional)

**Purpose**: Remove `roles` and `user_roles` tables from PostgreSQL database while preserving User table and is_admin flag

**Implementation Requirements**:

1. **Core Logic**:
   - Create new Alembic migration: `uv run alembic revision -m "remove_role_tables"`
   - Drop foreign key constraints BEFORE dropping tables (order matters)
   - Drop `user_roles` table first (depends on both users and roles)
   - Drop `roles` table second
   - Remove role-related enum values from `audit_action_enum`

2. **Migration Order** (in upgrade()):
   ```python
   def upgrade() -> None:
       # Step 1: Drop foreign key constraints from user_roles
       op.drop_constraint('user_roles_user_id_fkey', 'user_roles', type_='foreignkey')
       op.drop_constraint('user_roles_role_id_fkey', 'user_roles', type_='foreignkey')
       op.drop_constraint('user_roles_assigned_by_fkey', 'user_roles', type_='foreignkey')

       # Step 2: Drop junction table
       op.drop_table('user_roles')

       # Step 3: Drop roles table
       op.drop_table('roles')

       # Step 4: Remove enum values from audit_action_enum
       # Note: PostgreSQL doesn't support DROP VALUE from enum - must recreate enum
       op.execute("ALTER TYPE audit_action_enum RENAME TO audit_action_enum_old")
       op.execute("""
           CREATE TYPE audit_action_enum AS ENUM (
               'USER_REGISTER', 'USER_LOGIN', 'USER_LOGOUT', 'USER_UPDATE',
               'USER_DELETE', 'USER_ACTIVATE', 'USER_DEACTIVATE',
               'PASSWORD_CHANGE', 'PASSWORD_RESET_REQUEST', 'PASSWORD_RESET_COMPLETE',
               'TOKEN_REFRESH', 'TOKEN_REVOKE', 'EMAIL_VERIFY', 'EMAIL_CHANGE',
               'ACCOUNT_CREATE', 'ACCOUNT_UPDATE', 'ACCOUNT_DELETE',
               'PERMISSION_GRANT', 'PERMISSION_REVOKE',
               'ADMIN_CREATE', 'ADMIN_UPDATE', 'ADMIN_DELETE'
           )
       """)
       op.execute("""
           ALTER TABLE audit_logs
           ALTER COLUMN action TYPE audit_action_enum
           USING action::text::audit_action_enum
       """)
       op.execute("DROP TYPE audit_action_enum_old")
   ```

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Migration runs when roles table doesn't exist (already removed)
       - Use `if_exists=True` in drop_table operations
   - [ ] Handle case: Existing audit logs reference ROLE_ASSIGN/ROLE_REMOVE actions
       - Audit logs are immutable - keep old enum values in existing logs
       - Only prevent NEW logs from using role actions
   - [ ] Handle case: Migration downgrade (rollback)
       - Recreate tables but data will be lost (acceptable - warn in docstring)
   - [ ] Validate: No foreign keys remain pointing to roles table
       - Check information_schema.table_constraints after migration

4. **Dependencies**:
   - **Internal**: Depends on `4aabd1426c98_initial_schema.py` (created tables)
   - **External**: PostgreSQL 16+, Alembic 1.13+

5. **Testing Requirements**:
   - [ ] Unit test: Migration upgrade completes without errors
   - [ ] Unit test: Migration downgrade recreates tables (empty)
   - [ ] Unit test: Enum values removed from audit_action_enum
   - [ ] Integration test: Existing audit logs remain intact after migration
   - [ ] Integration test: Can still create users with is_admin=True
   - [ ] E2E test: Run full migration history on clean database

**Acceptance Criteria**:
- [ ] `uv run alembic upgrade head` completes successfully
- [ ] `\dt` in PostgreSQL shows no `roles` or `user_roles` tables
- [ ] `\dT+ audit_action_enum` shows no ROLE_ASSIGN/ROLE_REMOVE values
- [ ] `SELECT COUNT(*) FROM audit_logs` returns same count before/after migration
- [ ] Users table still has `is_admin` column

**Implementation Notes**:
- PostgreSQL doesn't allow removing enum values - must recreate entire enum type
- Use `RENAME TO` and `DROP TYPE` pattern to avoid constraint violations
- Always test migrations on a database copy before production deployment
- Consider adding migration that archives role data before deletion (optional)

**Reference**: [Alembic Foreign Key Constraints](https://alembic.sqlalchemy.org/en/latest/ops.html), [PostgreSQL Enum Modification](https://stackoverflow.com/questions/42911904/dropping-foreign-keys-in-alembic-downgrade)

---

#### Component: SQLAlchemy Models

**Files Involved**:
- `src/models/user.py` (modify - remove Role model, user_roles table, roles relationship)
- `src/models/__init__.py` (modify - remove exports)
- `src/models/enums.py` (modify - remove audit actions)

**Purpose**: Remove Role ORM model and user-role relationship from SQLAlchemy models

**Implementation Requirements**:

1. **Core Logic** (in `src/models/user.py`):
   - **DELETE lines 32-63**: `user_roles` Table definition
     ```python
     # DELETE THIS BLOCK
     user_roles = Table(
         "user_roles",
         Base.metadata,
         Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")),
         Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE")),
         # ... rest of table definition
     )
     ```

   - **DELETE lines 152-159** in User model: `roles` relationship
     ```python
     # DELETE THIS LINE FROM User CLASS
     roles: Mapped[list["Role"]] = relationship(
         "Role",
         secondary=user_roles,
         lazy="selectin",
         back_populates="users",
     )
     ```

   - **DELETE lines 174-260**: Entire `Role` class definition
     ```python
     # DELETE ENTIRE CLASS
     class Role(Base, SoftDeleteMixin, TimestampMixin):
         """Role model with JSONB permissions array."""
         # ... entire class
     ```

2. **Data Handling** (in `src/models/__init__.py`):
   - Remove imports: `from src.models.user import Role, User, user_roles`
   - Update to: `from src.models.user import User`
   - Remove from `__all__`: `"Role"`, `"user_roles"`
   - Keep: `"User"` (still needed)

3. **Enum Updates** (in `src/models/enums.py`):
   - Remove from `AuditAction` enum:
     ```python
     # DELETE THESE TWO LINES
     ROLE_ASSIGN = "ROLE_ASSIGN"
     ROLE_REMOVE = "ROLE_REMOVE"
     ```

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: Existing code tries to access `user.roles`
       - Will raise `AttributeError` - caught in testing phase
   - [ ] Handle case: Import of `Role` model elsewhere
       - Will raise `ImportError` - caught by type checker (mypy)
   - [ ] Validate: All foreign key references to roles removed
       - No other models should have `ForeignKey("roles.id")`

5. **Dependencies**:
   - **Internal**: Must run database migration first
   - **External**: SQLAlchemy 2.0 (async)

6. **Testing Requirements**:
   - [ ] Unit test: User model can be instantiated without roles
   - [ ] Unit test: User model has `is_admin` attribute
   - [ ] Unit test: Accessing `user.roles` raises AttributeError
   - [ ] Unit test: Import `from src.models import Role` raises ImportError
   - [ ] Integration test: Can create user in database without role assignment

**Acceptance Criteria**:
- [ ] `uv run ruff check .` passes (no import errors)
- [ ] `uv run mypy src/` passes (no type errors referencing Role)
- [ ] User model has no `roles` relationship
- [ ] Role model completely removed from codebase
- [ ] `from src.models import Role` raises ImportError

**Implementation Notes**:
- Delete code in order: relationship → table → model (reverse dependency order)
- Use `git grep -n "\.roles"` to find all attribute access points
- The User model keeps all other fields (is_admin, email, etc.)

---

#### Component: Repository Layer

**Files Involved**:
- `src/repositories/role_repository.py` ← DELETE ENTIRE FILE
- `src/repositories/user_repository.py` ← MODIFY
- `src/repositories/__init__.py` ← MODIFY

**Purpose**: Remove role repository and clean up user repository role references

**Implementation Requirements**:

1. **Core Logic**:
   - **DELETE FILE**: `src/repositories/role_repository.py` (entire 130-line file)
   - **MODIFY**: `src/repositories/user_repository.py`
     - Remove `.options(selectinload(User.roles))` from queries (lines 58, 84)
     - Delete `get_with_roles()` method (lines 99-112)
   - **MODIFY**: `src/repositories/__init__.py`
     - Remove import: `from src.repositories.role_repository import RoleRepository`
     - Remove from `__all__`: `"RoleRepository"`

2. **Specific Changes in `user_repository.py`**:
   ```python
   # BEFORE (line 58):
   result = await self.session.execute(
       select(User)
       .options(selectinload(User.roles))  # ← REMOVE THIS LINE
       .where(User.email == email, User.deleted_at.is_(None))
   )

   # AFTER:
   result = await self.session.execute(
       select(User)
       .where(User.email == email, User.deleted_at.is_(None))
   )

   # DELETE ENTIRE METHOD (lines 99-112):
   async def get_with_roles(self, user_id: uuid.UUID) -> User | None:
       """Fetch user with roles eagerly loaded."""
       # DELETE THIS ENTIRE METHOD
   ```

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Code calls `user_repository.get_with_roles()`
       - Will raise `AttributeError` - find all calls and replace with `get_by_id()`
   - [ ] Handle case: Queries try to join on roles
       - Will cause SQLAlchemy error - caught in testing
   - [ ] Validate: No RoleRepository imports remain
       - Run `grep -r "RoleRepository" src/` → should return 0 results

4. **Dependencies**:
   - **Internal**: Depends on models being updated first (Role removed)
   - **External**: SQLAlchemy 2.0 async

5. **Testing Requirements**:
   - [ ] Unit test: UserRepository.get_by_email() returns user without roles
   - [ ] Unit test: UserRepository has no get_with_roles() method
   - [ ] Unit test: Import RoleRepository raises ImportError
   - [ ] Integration test: UserRepository methods work without role loading

**Acceptance Criteria**:
- [ ] File `src/repositories/role_repository.py` deleted
- [ ] `grep -r "selectinload(User.roles)" src/` returns 0 results
- [ ] `grep -r "get_with_roles" src/` returns 0 results
- [ ] `uv run mypy src/` passes (no RoleRepository references)

**Implementation Notes**:
- Use `git rm` to delete file (proper Git history)
- Search for `RoleRepository` usage before deleting: `git grep -n RoleRepository`
- Removing selectinload improves performance (fewer JOINs)

---

#### Component: Service Layer

**Files Involved**:
- `src/services/admin_service.py` ← DELETE ENTIRE FILE (675 lines)
- `src/services/user_service.py` ← MODIFY

**Purpose**: Remove admin service that managed role assignment and clean up user service role calls

**Implementation Requirements**:

1. **Core Logic**:
   - **DELETE FILE**: `src/services/admin_service.py` (entire 675-line file)
     - Removes: `create_admin_user()`, `update_admin_user()`, `delete_admin_user()`
     - Removes: `reset_admin_password()`, `update_admin_permissions()`
     - Removes: All role aggregation logic

   - **MODIFY**: `src/services/user_service.py`
     - Remove `get_with_roles()` call in `get_user_profile()` (line 99)
     - Replace with standard `get_by_id()` call

2. **Specific Changes in `user_service.py`**:
   ```python
   # BEFORE (line 99):
   user = await self.user_repository.get_with_roles(user_id)

   # AFTER:
   user = await self.user_repository.get_by_id(user_id)
   ```

3. **Admin User Management Strategy**:
   - **Old approach**: AdminService with role assignment
   - **New approach**: Use standard UserService + `is_admin=True`
   - **No new code needed**: Existing user CRUD operations handle admin users
   - **Superuser creation**: Still handled in migration (no service needed)

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: Code tries to import AdminService
       - Will raise `ImportError` - find all imports
   - [ ] Handle case: Admin-specific endpoints need service
       - Use UserService instead (supports is_admin flag)
   - [ ] Handle case: Permission updates requested
       - No longer supported - document as breaking change

5. **Dependencies**:
   - **Internal**: Depends on admin.py routes being deleted first
   - **External**: None (deleting code)

6. **Testing Requirements**:
   - [ ] Unit test: Import AdminService raises ImportError
   - [ ] Unit test: UserService.get_user_profile() works without get_with_roles()
   - [ ] Integration test: Can create admin users via UserService
   - [ ] E2E test: Admin users can still access protected endpoints

**Acceptance Criteria**:
- [ ] File `src/services/admin_service.py` deleted
- [ ] `grep -r "AdminService" src/` returns 0 results
- [ ] `grep -r "get_with_roles" src/services/` returns 0 results
- [ ] UserService methods work for both admin and regular users

**Implementation Notes**:
- AdminService was only used by admin routes (being deleted)
- UserService already handles is_admin flag checks
- No replacement service needed - existing code sufficient

---

#### Component: API Routes

**Files Involved**:
- `src/api/routes/admin.py` ← DELETE ENTIRE FILE (340 lines)
- `src/api/routes/users.py` ← NO CHANGES (already uses require_admin correctly)
- `src/main.py` ← MODIFY (remove admin router registration)

**Purpose**: Remove admin-specific API endpoints that managed roles/permissions

**Implementation Requirements**:

1. **Core Logic**:
   - **DELETE FILE**: `src/api/routes/admin.py` (entire 340-line file)
     - Removes endpoints:
       - `POST /admin/users` (create admin)
       - `GET /admin/users` (list admins)
       - `GET /admin/users/{user_id}` (get admin details)
       - `PUT /admin/users/{user_id}` (update admin)
       - `DELETE /admin/users/{user_id}` (delete admin)
       - `PUT /admin/users/{user_id}/password` (reset password)
       - `PUT /admin/users/{user_id}/permissions` (update permissions)

   - **MODIFY**: `src/main.py`
     - Remove import: `from src.api.routes import admin`
     - Remove router registration: `app.include_router(admin.router)`

2. **Endpoint Migration Strategy**:

   | Old Admin Endpoint | Replacement Strategy |
   |--------------------|----------------------|
   | `POST /admin/users` | Not needed - superuser created in migration |
   | `GET /admin/users` | Use `GET /users?is_admin=true` (add filter) |
   | `GET /admin/users/{id}` | Use `GET /users/{id}` (existing endpoint) |
   | `PUT /admin/users/{id}` | Use `PUT /users/{id}` (existing endpoint) |
   | `DELETE /admin/users/{id}` | Use `DELETE /users/{id}` (existing endpoint) |
   | `PUT /admin/users/{id}/password` | Use `PUT /users/password` (existing endpoint) |
   | `PUT /admin/users/{id}/permissions` | **NOT REPLACED** - no longer needed |

3. **users.py Route Protection** (NO CHANGES NEEDED):
   - Already uses `Depends(require_admin)` correctly:
     - Line 176: `list_users()` ← protected ✅
     - Line 227: `deactivate_user()` ← protected ✅
     - Line 269: `delete_user()` ← protected ✅

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: Frontend tries to call `/admin/*` endpoints
       - Will return 404 - document as breaking change for frontend
   - [ ] Handle case: Tests reference admin endpoints
       - Will fail - update or delete tests
   - [ ] Validate: No other routers import admin routes
       - Check all files in `src/api/routes/`

5. **Dependencies**:
   - **Internal**: Depends on admin service being deleted
   - **External**: FastAPI 0.115+

6. **Testing Requirements**:
   - [ ] Unit test: `GET /admin/users` returns 404
   - [ ] Unit test: Import admin router raises ImportError
   - [ ] Integration test: `GET /users` works for admin user
   - [ ] E2E test: Admin can still access protected user endpoints

**Acceptance Criteria**:
- [ ] File `src/api/routes/admin.py` deleted
- [ ] `grep -r "admin.router" src/main.py` returns 0 results
- [ ] `curl http://localhost:8000/api/v1/admin/users` returns 404
- [ ] `GET /users` endpoint still works for admin users

**Implementation Notes**:
- Document breaking change: admin endpoints removed
- Frontend must migrate to using `/users` endpoints instead
- OpenAPI docs will automatically remove `/admin` endpoints

---

#### Component: Authorization Dependencies

**Files Involved**:
- `src/api/dependencies.py` (modify - remove require_permission factory)

**Purpose**: Remove complex permission-based authorization and keep simple admin check

**Implementation Requirements**:

1. **Core Logic**:
   - **DELETE lines 208-266**: Entire `require_permission()` factory function
     ```python
     # DELETE THIS ENTIRE FUNCTION
     def require_permission(permission: str) -> Callable:
         """Factory function that creates a permission-checking dependency."""
         # ... 58 lines of role aggregation logic
     ```

   - **KEEP lines 170-205**: `require_admin()` dependency (no changes)
     ```python
     # KEEP THIS - IT'S ALREADY CORRECT
     async def require_admin(
         current_user: User = Depends(get_current_user),
     ) -> User:
         """Dependency that requires admin privileges."""
         if not current_user.is_admin:
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN,
                 detail="Admin privileges required",
             )
         return current_user
     ```

   - **KEEP line 423**: `AdminUser = Annotated[User, Depends(require_admin)]` (no changes)

2. **Migration Strategy for Existing Usages**:

   | Old Pattern | New Pattern |
   |-------------|-------------|
   | `Depends(require_permission("users:read:all"))` | `Depends(require_admin)` |
   | `Depends(require_permission("users:write:all"))` | `Depends(require_admin)` |
   | `Depends(require_permission("audit_logs:read"))` | `Depends(require_admin)` |
   | `AdminUser` annotation | `AdminUser` (no change) |

3. **Search and Replace Strategy**:
   ```bash
   # Find all usages of require_permission
   git grep -n "require_permission"

   # Expected results: Only in permission_service.py (account permissions - different concept)
   # If found in route files, replace with require_admin
   ```

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: Code tries to call `require_permission("some:permission")`
       - Will raise `NameError` - caught by type checker and tests
   - [ ] Handle case: Import require_permission
       - Will raise `ImportError` - caught by linter
   - [ ] Validate: No granular permission checks remain
       - All admin operations use simple is_admin boolean

5. **Dependencies**:
   - **Internal**: Depends on admin routes being deleted (main usage)
   - **External**: FastAPI 0.115+

6. **Testing Requirements**:
   - [ ] Unit test: require_admin() raises 403 for non-admin user
   - [ ] Unit test: require_admin() allows admin user
   - [ ] Unit test: Import require_permission raises NameError
   - [ ] Integration test: Admin-protected endpoints work with require_admin

**Acceptance Criteria**:
- [ ] `grep -r "require_permission" src/api/` returns 0 results (except comments)
- [ ] `grep -r "def require_permission" src/` returns 0 results
- [ ] require_admin() function still exists and works
- [ ] AdminUser type alias still exists

**Implementation Notes**:
- `require_permission()` was only used in admin.py (being deleted)
- No other routes use granular permissions
- `permission_service.py` handles ACCOUNT sharing permissions (different - keep it)

---

#### Component: Pydantic Schemas

**Files Involved**:
- `src/schemas/admin.py` ← DELETE ENTIRE FILE (263 lines)

**Purpose**: Remove all admin-specific request/response schemas for role management

**Implementation Requirements**:

1. **Core Logic**:
   - **DELETE FILE**: `src/schemas/admin.py` (entire 263-line file)
     - Removes schemas:
       - `CreateAdminUserRequest` (with permissions field)
       - `UpdateAdminUserRequest`
       - `ResetPasswordRequest`
       - `UpdatePermissionsRequest` (permissions list)
       - `AdminUserResponse` (includes permissions)
       - `AdminUserListItem`
       - `AdminUserFilterParams`

2. **Schema Migration Strategy**:

   | Deleted Admin Schema | Replacement |
   |----------------------|-------------|
   | `AdminUserResponse` | Use `UserResponse` (from `src/schemas/user.py`) |
   | `CreateAdminUserRequest` | Not needed (superuser in migration) |
   | `UpdateAdminUserRequest` | Use `UpdateUserRequest` |
   | `UpdatePermissionsRequest` | **No replacement** - permissions removed |

3. **No Changes Needed** in `src/schemas/user.py`:
   - `UserResponse` already includes `is_admin` field ✅
   - `CreateUserRequest` supports `is_admin` parameter ✅
   - `UpdateUserRequest` supports updating user details ✅

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: Code imports admin schemas
       - Will raise `ImportError` - find all imports
   - [ ] Handle case: API returns AdminUserResponse
       - Already deleted with admin routes
   - [ ] Validate: No schema references permissions field
       - Check all Pydantic models for `permissions:` field

5. **Dependencies**:
   - **Internal**: Depends on admin routes being deleted (main usage)
   - **External**: Pydantic 2.x

6. **Testing Requirements**:
   - [ ] Unit test: Import AdminUserResponse raises ImportError
   - [ ] Unit test: UserResponse schema works for admin users
   - [ ] Integration test: User endpoints return UserResponse for admins
   - [ ] E2E test: No validation errors from missing admin schemas

**Acceptance Criteria**:
- [ ] File `src/schemas/admin.py` deleted
- [ ] `grep -r "AdminUserResponse" src/` returns 0 results
- [ ] `grep -r "from src.schemas.admin" src/` returns 0 results
- [ ] UserResponse schema includes is_admin field

**Implementation Notes**:
- Admin schemas were only used by admin routes (being deleted)
- Standard user schemas already support admin flag
- No new schemas needed

---

#### Component: Configuration

**Files Involved**:
- `src/core/config.py` (modify - remove superadmin_permissions)
- `.env.example` (modify - remove SUPERADMIN_PERMISSIONS)

**Purpose**: Remove permissions-related configuration while keeping superuser creation settings

**Implementation Requirements**:

1. **Core Logic** (in `src/core/config.py`):
   - **DELETE lines 144-151**: `superadmin_permissions` field
     ```python
     # DELETE THESE LINES
     superadmin_permissions: List[str] = Field(
         default=[
             "users:read:all",
             "users:write:all",
             "audit_logs:read:all",
         ],
         description="List of permissions granted to superadmin user",
     )
     ```

   - **KEEP**: All other superadmin fields
     - `superadmin_username` ✅
     - `superadmin_email` ✅
     - `superadmin_password` ✅
     - `superadmin_full_name` ✅

2. **Environment File Updates** (in `.env.example`):
   - **DELETE line**: `SUPERADMIN_PERMISSIONS=users:read:all,users:write:all,audit_logs:read:all`
   - **KEEP**: All other SUPERADMIN_* variables

3. **Migration Script Updates** (in new migration):
   - Superuser creation logic simplified:
     ```python
     # OLD (in 4aabd1426c98_initial_schema.py):
     # 1. Create user
     # 2. Create or get "admin" role
     # 3. Insert into user_roles junction table
     # 4. Create audit log

     # NEW (in new migration):
     # 1. Create user with is_admin=True
     # 2. Create audit log
     # (No role assignment needed)
     ```

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: .env file still has SUPERADMIN_PERMISSIONS
       - Will be ignored by Pydantic (extra="ignore" in config)
   - [ ] Handle case: Migration tries to read settings.superadmin_permissions
       - Will raise `AttributeError` - update migration code
   - [ ] Validate: All superuser functionality works without permissions
       - Test admin can access all protected endpoints

5. **Dependencies**:
   - **Internal**: Depends on migration updates
   - **External**: Pydantic Settings

6. **Testing Requirements**:
   - [ ] Unit test: Settings model doesn't have superadmin_permissions field
   - [ ] Unit test: Settings loads successfully with old .env (ignored)
   - [ ] Integration test: Superuser created with is_admin=True only
   - [ ] E2E test: Admin user can access all endpoints without permissions

**Acceptance Criteria**:
- [ ] `grep -r "superadmin_permissions" src/` returns 0 results
- [ ] `grep -r "SUPERADMIN_PERMISSIONS" .env.example` returns 0 results
- [ ] Settings model has no permissions-related fields
- [ ] Superuser still created correctly in migration

**Implementation Notes**:
- Keep all other SUPERADMIN_* settings (needed for user creation)
- Pydantic `extra="ignore"` handles old .env files gracefully
- Document in migration docstring that permissions are removed

---

#### Component: Test Suite

**Files Involved**:
- `tests/integration/test_admin_routes.py` ← DELETE ENTIRE FILE
- `tests/e2e/test_admin_workflow.py` ← DELETE ENTIRE FILE
- `tests/conftest.py` ← KEEP (admin fixtures still useful)

**Purpose**: Remove tests for deleted admin endpoints while preserving admin user test fixtures

**Implementation Requirements**:

1. **Core Logic**:
   - **DELETE FILE**: `tests/integration/test_admin_routes.py`
     - Removes tests for all `/admin/*` endpoints

   - **DELETE FILE**: `tests/e2e/test_admin_workflow.py`
     - Removes end-to-end admin permission workflows

   - **KEEP**: `tests/conftest.py` fixtures (NO CHANGES)
     - `admin_user()` fixture ← still useful for testing admin access
     - `admin_token()` fixture ← still useful for auth testing
     - `admin_headers()` fixture ← still useful for API testing

2. **Test Coverage Strategy**:

   | Deleted Test | Replacement Coverage |
   |--------------|----------------------|
   | `test_create_admin_user()` | Not needed (superuser in migration) |
   | `test_list_admin_users()` | Use `test_list_users()` with is_admin filter |
   | `test_update_admin_permissions()` | **No replacement** - feature removed |
   | `test_admin_access_protected_endpoint()` | Keep in existing route tests |

3. **Existing Tests to Verify** (should still pass):
   - `tests/integration/test_auth_routes.py` ← admin login tests
   - `tests/integration/test_users.py` ← admin accessing user endpoints
   - All tests using `admin_user` or `admin_token` fixtures

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: Tests import admin routes
       - Will raise `ImportError` - delete those tests
   - [ ] Handle case: Tests expect permissions in response
       - Will fail validation - update assertions
   - [ ] Validate: All remaining tests pass with 80%+ coverage
       - Run `uv run pytest tests/ --cov=src`

5. **Dependencies**:
   - **Internal**: Depends on admin routes/services being deleted
   - **External**: pytest, pytest-asyncio

6. **Testing Requirements** (Meta - testing the tests):
   - [ ] Run `uv run pytest tests/` - all tests pass
   - [ ] Run `uv run pytest --cov=src --cov-report=term-missing` - 80%+ coverage
   - [ ] Run `uv run pytest -k admin` - only conftest fixtures remain (no test failures)
   - [ ] Integration test: admin_user fixture still works
   - [ ] E2E test: Admin user can authenticate and access protected endpoints

**Acceptance Criteria**:
- [ ] Files `test_admin_routes.py` and `test_admin_workflow.py` deleted
- [ ] `uv run pytest tests/` completes with 0 failures
- [ ] Test coverage remains above 80%
- [ ] `admin_user`, `admin_token`, `admin_headers` fixtures still work
- [ ] No test imports from deleted admin modules

**Implementation Notes**:
- Keep admin fixtures in conftest.py - widely used in other tests
- Run tests after EACH file deletion to catch broken imports early
- Document in PR: "Admin endpoint tests removed - functionality migrated to user endpoints"

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Database Migration (Size: M, Priority: P0)

**Goal**: Safely remove role-related database tables and enum values while preserving all existing data in Users and audit_logs tables

**Scope**:
- ✅ Include: Migration to drop roles, user_roles tables, update enums
- ✅ Include: Preserve all existing audit log records
- ✅ Include: Keep is_admin flag and user data intact
- ❌ Exclude: Application code changes (next phase)
- ❌ Exclude: Test updates (next phase)

**Components to Implement**:
- [ ] Create Alembic migration for table removal
- [ ] Update audit_action_enum to remove role values
- [ ] Test migration upgrade/downgrade

**Detailed Tasks**:

1. [ ] Create new Alembic migration file
   - Run: `uv run alembic revision -m "remove_role_based_authorization_tables"`
   - File created: `alembic/versions/<timestamp>_remove_role_based_authorization_tables.py`

2. [ ] Implement upgrade() function
   - Step 1: Drop foreign key constraints from user_roles table
     - Drop: `user_roles_user_id_fkey`
     - Drop: `user_roles_role_id_fkey`
     - Drop: `user_roles_assigned_by_fkey`
   - Step 2: Drop user_roles junction table
     - Use: `op.drop_table('user_roles', if_exists=True)`
   - Step 3: Drop roles table
     - Use: `op.drop_table('roles', if_exists=True)`
   - Step 4: Recreate audit_action_enum without ROLE_ASSIGN/ROLE_REMOVE
     - Rename old enum: `ALTER TYPE audit_action_enum RENAME TO audit_action_enum_old`
     - Create new enum without role values
     - Alter audit_logs table to use new enum
     - Drop old enum type

3. [ ] Implement downgrade() function (for rollback)
   - Recreate roles table (empty - data lost on downgrade)
   - Recreate user_roles table (empty)
   - Recreate audit_action_enum with role values
   - Add warning in docstring: "Data loss on downgrade - roles not recovered"

4. [ ] Test migration on development database
   - Run: `uv run alembic upgrade head`
   - Verify: `\dt` shows no roles/user_roles tables
   - Verify: `SELECT COUNT(*) FROM audit_logs` matches pre-migration count
   - Verify: `\dT+ audit_action_enum` shows no ROLE_ASSIGN/ROLE_REMOVE

5. [ ] Test migration rollback
   - Run: `uv run alembic downgrade -1`
   - Verify: Tables recreated (empty)
   - Run: `uv run alembic upgrade head` (re-apply)

6. [ ] Document migration in commit message
   - Use: `git commit -m "feat: remove role-based authorization database tables"`

**Dependencies**:
- Requires: PostgreSQL 16+ running
- Requires: Database backup before migration
- Blocks: All subsequent phases (code changes depend on this)

**Validation Criteria** (Phase complete when):
- [ ] Migration runs successfully without errors
- [ ] All tests pass (existing tests - no changes yet)
- [ ] roles and user_roles tables removed from database
- [ ] audit_logs table intact with all historical records
- [ ] Users table intact with is_admin flag working
- [ ] Rollback (downgrade) works without errors

**Risk Factors**:
- **Risk**: Audit logs reference deleted enum values
  - **Mitigation**: Only prevent NEW logs, keep old enum values in existing records
- **Risk**: Other tables have foreign keys to roles
  - **Mitigation**: Search codebase first - only user_roles has FK (verified in audit)
- **Risk**: Production data loss on failure
  - **Mitigation**: ALWAYS backup database before migration, test on staging first

**Estimated Effort**: 1 day (includes testing and validation)

---

#### Phase 2: Code Removal (Size: L, Priority: P0)

**Goal**: Remove all role-related code files and references from the application codebase

**Scope**:
- ✅ Include: Delete 9 files (repositories, services, routes, schemas, tests)
- ✅ Include: Remove role references from models, dependencies, config
- ✅ Include: Update imports and exports
- ❌ Exclude: Test updates (next phase - these need code to exist first)
- ❌ Exclude: Documentation updates (final phase)

**Components to Implement**:
- [ ] Models: Remove Role model, user_roles table, relationships
- [ ] Repositories: Delete RoleRepository, clean UserRepository
- [ ] Services: Delete AdminService, clean UserService
- [ ] Routes: Delete admin.py, update main.py
- [ ] Dependencies: Remove require_permission()
- [ ] Schemas: Delete admin.py
- [ ] Config: Remove superadmin_permissions

**Detailed Tasks**:

1. [ ] Remove database models
   - Edit: `src/models/user.py`
     - Delete lines 32-63: user_roles Table
     - Delete lines 152-159: roles relationship in User model
     - Delete lines 174-260: Role class
   - Edit: `src/models/enums.py`
     - Delete: `ROLE_ASSIGN = "ROLE_ASSIGN"` from AuditAction enum
     - Delete: `ROLE_REMOVE = "ROLE_REMOVE"` from AuditAction enum
   - Edit: `src/models/__init__.py`
     - Remove import: `Role, user_roles`
     - Remove from __all__: `"Role"`, `"user_roles"`
   - Verify: `uv run ruff check src/models/` passes

2. [ ] Remove repository layer
   - Delete: `src/repositories/role_repository.py` (entire file)
   - Edit: `src/repositories/user_repository.py`
     - Remove: `.options(selectinload(User.roles))` from lines 58, 84
     - Delete: `get_with_roles()` method (lines 99-112)
   - Edit: `src/repositories/__init__.py`
     - Remove import: `RoleRepository`
     - Remove from __all__: `"RoleRepository"`
   - Verify: `uv run ruff check src/repositories/` passes

3. [ ] Remove service layer
   - Delete: `src/services/admin_service.py` (entire 675-line file)
   - Edit: `src/services/user_service.py`
     - Replace: `get_with_roles(user_id)` → `get_by_id(user_id)` (line 99)
   - Verify: `uv run ruff check src/services/` passes

4. [ ] Remove API routes
   - Delete: `src/api/routes/admin.py` (entire 340-line file)
   - Edit: `src/main.py`
     - Remove import: `from src.api.routes import admin`
     - Remove: `app.include_router(admin.router)` line
   - Edit: `src/api/routes/users.py` (NO CHANGES - already correct)
   - Verify: `uv run ruff check src/api/` passes

5. [ ] Remove authorization dependencies
   - Edit: `src/api/dependencies.py`
     - Delete lines 208-266: `require_permission()` factory function
     - Keep: `require_admin()` function (lines 170-205)
     - Keep: `AdminUser` type alias (line 423)
   - Verify: `grep -r "require_permission" src/api/routes/` returns 0 results
   - Verify: `uv run ruff check src/api/` passes

6. [ ] Remove schemas
   - Delete: `src/schemas/admin.py` (entire 263-line file)
   - Verify: `uv run ruff check src/schemas/` passes

7. [ ] Remove configuration
   - Edit: `src/core/config.py`
     - Delete lines 144-151: `superadmin_permissions` field
     - Keep all other superadmin_* fields
   - Edit: `.env.example`
     - Remove: `SUPERADMIN_PERMISSIONS=...` line
   - Verify: `uv run python -c "from src.core.config import settings; print(settings.superadmin_email)"`

8. [ ] Run code quality checks
   - Run: `uv run ruff format .` (auto-format)
   - Run: `uv run ruff check --fix .` (auto-fix lints)
   - Run: `uv run mypy src/` (type checking)
   - Fix any remaining type errors

9. [ ] Commit code removal
   - Run: `git add -A`
   - Run: `git commit -m "feat: remove role-based authorization code"`

**Dependencies**:
- Requires: Phase 1 complete (database migration applied)
- Blocks: Phase 3 (tests need code removed first)

**Validation Criteria** (Phase complete when):
- [ ] All 9 files deleted successfully
- [ ] No import errors when running `uv run python -c "from src.main import app"`
- [ ] `uv run ruff check .` passes with 0 errors
- [ ] `uv run mypy src/` passes with 0 errors
- [ ] `grep -r "Role\b" src/ --include="*.py"` returns 0 results (except "UserRole" in permission_service)
- [ ] `grep -r "require_permission" src/` returns 0 results (except account permissions)

**Risk Factors**:
- **Risk**: Breaking imports in other files
  - **Mitigation**: Run ruff and mypy after each file deletion
- **Risk**: Tests start failing
  - **Mitigation**: Expected - will fix in Phase 3
- **Risk**: Missing role references in obscure files
  - **Mitigation**: Use grep extensively to find all references

**Estimated Effort**: 1-2 days (includes validation and fixing import errors)

---

#### Phase 3: Test Suite Updates (Size: M, Priority: P0)

**Goal**: Update test suite to reflect removed role functionality and ensure 80%+ coverage

**Scope**:
- ✅ Include: Delete admin-specific test files
- ✅ Include: Update remaining tests that reference roles
- ✅ Include: Verify all tests pass
- ✅ Include: Ensure coverage stays above 80%
- ❌ Exclude: New feature tests (no new features added)

**Components to Implement**:
- [ ] Delete admin test files
- [ ] Update conftest.py (keep admin fixtures)
- [ ] Fix broken tests referencing roles
- [ ] Verify coverage targets

**Detailed Tasks**:

1. [ ] Delete admin-specific test files
   - Delete: `tests/integration/test_admin_routes.py` (entire file)
   - Delete: `tests/e2e/test_admin_workflow.py` (entire file)
   - Verify: `git status` shows files deleted

2. [ ] Update test fixtures (if needed)
   - Edit: `tests/conftest.py`
     - Keep: `admin_user()` fixture (lines 258-280) - still useful
     - Keep: `admin_token()` fixture (lines 347-375) - still useful
     - Keep: `admin_headers()` fixture (lines 378-385) - still useful
   - No changes expected - fixtures use is_admin flag, not roles

3. [ ] Find and fix broken tests
   - Run: `uv run pytest tests/ -v`
   - Expected failures: Tests importing admin routes/services
   - For each failure:
     - If test is admin-specific: delete it
     - If test can be adapted: update to use standard user endpoints
     - If test fixture is broken: fix import or remove role reference

4. [ ] Verify test coverage
   - Run: `uv run pytest tests/ --cov=src --cov-report=term-missing`
   - Target: ≥80% overall coverage
   - If coverage drops below 80%:
     - Identify uncovered lines in report
     - Add tests for critical paths
     - Focus on auth, user management, audit logging

5. [ ] Run all test types
   - Unit tests: `uv run pytest tests/unit/ -v`
   - Integration tests: `uv run pytest tests/integration/ -v`
   - E2E tests: `uv run pytest tests/e2e/ -v`
   - All should pass with 0 failures

6. [ ] Test admin functionality manually
   - Start server: `uv run uvicorn src.main:app --reload`
   - Create admin user (already in DB from migration)
   - Test: `POST /api/v1/auth/login` with admin credentials
   - Test: `GET /api/v1/users` with admin token (should work)
   - Test: `GET /api/v1/users` with regular user token (should fail with 403)
   - Verify: Admin can access protected endpoints

7. [ ] Commit test updates
   - Run: `git add tests/`
   - Run: `git commit -m "test: update test suite after role removal"`

**Dependencies**:
- Requires: Phase 2 complete (code removed)
- Blocks: Phase 4 (documentation references working code)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass: `uv run pytest tests/` shows 0 failures
- [ ] Coverage ≥80%: `--cov-report` shows overall percentage
- [ ] No skipped tests: All tests run successfully
- [ ] Admin fixtures still work in conftest.py
- [ ] Manual testing confirms admin access control works

**Risk Factors**:
- **Risk**: Coverage drops below 80%
  - **Mitigation**: Add targeted tests for uncovered critical paths
- **Risk**: Many tests fail due to role references
  - **Mitigation**: Delete admin-specific tests, adapt others to use is_admin
- **Risk**: Admin functionality broken but tests pass
  - **Mitigation**: Include manual testing checklist

**Estimated Effort**: 1 day (includes fixing failures and improving coverage)

---

#### Phase 4: Documentation & Cleanup (Size: S, Priority: P1)

**Goal**: Update documentation to reflect simplified authorization model and clean up any remaining references

**Scope**:
- ✅ Include: Update README.md, CLAUDE.md, database-schema.md
- ✅ Include: Remove old feature documentation referencing roles
- ✅ Include: Final verification with fresh database
- ❌ Exclude: Frontend documentation (separate repo)

**Components to Implement**:
- [ ] Update project documentation
- [ ] Clean up old feature docs
- [ ] Final end-to-end verification

**Detailed Tasks**:

1. [ ] Update CLAUDE.md
   - Edit: `CLAUDE.md`
     - Update "Architecture Overview" section to remove role layer
     - Update "Common Development Tasks" to remove "Adding a Role"
     - Update "Standards Compliance" to remove auth.md references (if role-specific)
     - Update "Superuser Creation" to document is_admin-only approach
   - Verify: Document accurately reflects current architecture

2. [ ] Update README.md
   - Edit: `README.md`
     - Update "Features" section to remove "Role-Based Access Control"
     - Update to: "Admin authorization via is_admin flag"
     - Update API documentation links (no /admin endpoints)
     - Update "Authentication" section to remove permission examples
   - Verify: README matches actual functionality

3. [ ] Update database schema documentation
   - Edit: `docs/database-schema.md`
     - Remove: roles table documentation
     - Remove: user_roles junction table documentation
     - Update: User model to show is_admin flag only
     - Update: ERD diagram to remove role relationships
   - Verify: Schema docs match actual database structure

4. [ ] Clean up old feature documentation
   - Search: `.features/` directory for role references
   - Update or delete:
     - `.features/research/20251029_personal-finance-platform-phase1-foundation.md`
     - `.features/research/20251103_account-management-system.md`
     - Any plans referencing RBAC
   - Add note: "DEPRECATED: Role-based authorization removed in v0.2.0"

5. [ ] Remove old migration references (optional)
   - Edit: `alembic/versions/4aabd1426c98_initial_schema.py`
     - Add comment: "# DEPRECATED: Roles tables removed in <new_migration>"
     - Keep code for historical reference (don't delete)
   - Edit: `alembic/versions/9cfdc3051d85_create_enums_and_extensions.py`
     - Add comment: "# DEPRECATED: Role audit actions removed"

6. [ ] Final end-to-end verification
   - Reset database: `docker-compose down -v && docker-compose up -d`
   - Run migrations: `uv run alembic upgrade head`
   - Verify superuser created with is_admin=True
   - Start server: `uv run uvicorn src.main:app --reload`
   - Test complete user flow:
     - ✅ Register new user
     - ✅ Login as regular user
     - ✅ Try to access admin endpoint (should fail)
     - ✅ Login as admin (superuser)
     - ✅ Access admin-protected endpoints (should succeed)
     - ✅ View audit logs
   - Run full test suite: `uv run pytest tests/ --cov=src`

7. [ ] Create summary of changes
   - Document:
     - Files deleted (9 files, ~1,500 lines)
     - Migration impact (2 tables removed)
     - API changes (7 endpoints removed)
     - Breaking changes for frontend
   - Add to PR description or CHANGELOG.md

8. [ ] Commit documentation updates
   - Run: `git add docs/ README.md CLAUDE.md .features/`
   - Run: `git commit -m "docs: update documentation after role removal"`

**Dependencies**:
- Requires: Phase 3 complete (all tests passing)
- Blocks: None (final phase)

**Validation Criteria** (Phase complete when):
- [ ] All documentation accurately reflects current system
- [ ] No references to roles in public documentation
- [ ] Fresh database migration works end-to-end
- [ ] Manual testing checklist 100% complete
- [ ] CHANGELOG.md updated with breaking changes

**Risk Factors**:
- **Risk**: Documentation becomes inconsistent
  - **Mitigation**: Systematic review of all docs in docs/, README, CLAUDE.md
- **Risk**: Missing role references in obscure docs
  - **Mitigation**: `grep -r "role" docs/ .features/` and review each hit

**Estimated Effort**: 0.5 days (documentation and final verification)

---

### 4.2 Implementation Sequence

```
Phase 1: Database Migration (P0, 1 day)
  │
  ├─ Create migration file
  ├─ Drop foreign keys
  ├─ Drop tables (user_roles → roles)
  ├─ Update audit_action_enum
  └─ Test upgrade/downgrade
  ↓
Phase 2: Code Removal (P0, 1-2 days)
  │
  ├─ Remove models (Role, user_roles)
  ├─ Delete repositories (RoleRepository)
  ├─ Delete services (AdminService)
  ├─ Delete routes (admin.py)
  ├─ Remove dependencies (require_permission)
  ├─ Delete schemas (admin.py)
  ├─ Remove config (superadmin_permissions)
  └─ Run linters/type checkers
  ↓
Phase 3: Test Suite Updates (P0, 1 day)
  │
  ├─ Delete admin test files
  ├─ Fix broken tests
  ├─ Verify coverage ≥80%
  └─ Manual testing
  ↓
Phase 4: Documentation & Cleanup (P1, 0.5 days)
  │
  ├─ Update CLAUDE.md, README.md
  ├─ Update database docs
  ├─ Clean up feature docs
  ├─ Final E2E verification
  └─ Create change summary
```

**Total Estimated Effort**: 3.5-4.5 days (1 developer)

**Rationale for ordering**:
- **Phase 1 first** because: Database schema changes must happen before code removal (avoid FK constraint errors)
- **Phase 2 depends on Phase 1** because: Code references tables that must be removed first
- **Phase 3 depends on Phase 2** because: Tests import code that must be deleted first
- **Phase 4 depends on Phase 3** because: Documentation should reflect working, tested code
- **No parallelization** possible: Each phase strictly depends on previous completion

**Quick Wins**:
- After Phase 1: Database simplified (performance improvement from fewer JOINs)
- After Phase 2: Codebase smaller (easier to maintain)
- After Phase 3: Confidence in changes (all tests passing)

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - YES: Replacing complex role-permission model with single boolean flag
  - This is as simple as authorization can get while maintaining admin functionality

- [x] **Have we avoided premature optimization?**
  - YES: Not adding any new features or abstractions
  - Pure deletion of unused complexity

- [x] **Does this align with existing patterns in the codebase?**
  - YES: `is_admin` flag already exists and is used
  - `require_admin()` dependency already exists and works correctly
  - Following FastAPI dependency injection pattern

- [x] **Can we deliver value in smaller increments?**
  - NO: This change is atomic - can't have partial role removal
  - Must complete all phases for system to work correctly
  - But phases are ordered to minimize breakage

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - YES: User explicitly requested role removal
  - Feature description clearly states: "Remove all user role-related code"
  - Simplifying authorization is the stated goal

### Alternatives Considered

**Alternative 1: Keep roles but simplify to single "admin" role**
- **Description**: Keep role infrastructure but only use one role
- **Pros**: Less code churn, easier rollback
- **Cons**: Still maintains complexity of role system for no benefit
- **Why not chosen**: Doesn't achieve goal of simplification

**Alternative 2: Replace with permission flags on User model**
- **Description**: Add boolean flags like `can_manage_users`, `can_view_audit_logs`
- **Pros**: More granular than single is_admin flag
- **Cons**: Reintroduces complexity without role infrastructure
- **Why not chosen**: User wants simplification, not reimplementation

**Alternative 3: Use middleware for admin authorization**
- **Description**: Replace `require_admin()` dependency with middleware
- **Pros**: Could apply to all routes automatically
- **Cons**: Less flexible, harder to apply selectively, doesn't integrate with OpenAPI
- **Why not chosen**: FastAPI best practice is dependencies over middleware for auth

**Alternative 4: Gradual deprecation over multiple releases**
- **Description**: Mark roles as deprecated, remove in future version
- **Pros**: Gives users time to migrate
- **Cons**: Maintains complexity longer, requires deprecation warnings
- **Why not chosen**: This is a backend system, no external API users to migrate

### Rationale

**Why the proposed approach is preferred**:

1. **Minimal Complexity**: Single `is_admin` boolean is simplest possible authorization
2. **Complete Removal**: Eliminates all role-related code (~1,500 lines deleted)
3. **Performance**: Removes JOIN queries to roles table (faster auth checks)
4. **Maintainability**: Fewer models, services, and endpoints to maintain
5. **Clear Migration Path**: Four sequential phases with clear validation criteria
6. **Preserves Functionality**: Admin capabilities remain intact via `is_admin` flag
7. **Backward Compatible Data**: Audit logs preserved, user data intact
8. **Reversible**: Migration includes downgrade path (though data loss on rollback)

---

## 6. References & Related Documents

### Technical Documentation

- [Alembic Operations Reference](https://alembic.sqlalchemy.org/en/latest/ops.html) - Official documentation for migration operations
- [SQLAlchemy 2.0 Migration Guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html) - Async ORM patterns
- [FastAPI Dependencies Tutorial](https://fastapi.tiangolo.com/tutorial/dependencies/) - Dependency injection patterns
- [FastAPI Middleware vs Dependencies](https://stackoverflow.com/questions/66632841/fastapi-dependency-vs-middleware) - Architecture decision rationale

### Migration Best Practices

- [Dropping Foreign Keys in Alembic](https://stackoverflow.com/questions/42911904/dropping-foreign-keys-in-alembic-downgrade) - Constraint removal patterns
- [Alembic with Async SQLAlchemy](https://dev.to/matib/alembic-with-async-sqlalchemy-1ga) - Async migration patterns
- [Handling Data in Alembic Migrations](https://hevalhazalkurt.com/blog/handling-data-in-alembic-migrations-when-schema-changes-arent-enough/) - Data preservation strategies

### Project-Specific Documents

- **Internal Standards**:
  - `.claude/standards/backend.md` - Backend architecture standards
  - `.claude/standards/database.md` - Database design standards
  - `.claude/standards/api.md` - API endpoint standards
  - `.claude/standards/testing.md` - Test coverage requirements

- **Related Features**:
  - `.features/descriptions/feat-002-remove-roles.md` - Original feature request
  - `.features/plans/20251117_remove-bootstrap-endpoint.md` - Similar cleanup work
  - `docs/database-schema.md` - Current database structure (to be updated)

### External Resources

- [PostgreSQL Enum Type Modification](https://www.postgresql.org/docs/current/sql-altertype.html) - Official PostgreSQL docs
- [FastAPI Auth with Dependency Injection](https://www.propelauth.com/post/fastapi-auth-with-dependency-injection) - Best practices
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html) - Security standards (Argon2id validation)

### Security Considerations

- **OWASP RBAC Removal Guidelines**: When removing RBAC, ensure fallback authorization is secure
- **Audit Logging Requirements**: GDPR/SOX require immutable audit trails (preserved in this plan)
- **Migration Safety**: Always backup before destructive migrations

---

## Implementation Notes

### Pre-Implementation Checklist

Before starting Phase 1, verify:

- [ ] PostgreSQL database backup created
- [ ] All tests currently passing (`uv run pytest tests/`)
- [ ] Current git branch is clean (`git status`)
- [ ] Development environment running (`docker-compose ps`)
- [ ] Migrations up to date (`uv run alembic current`)

### During Implementation

- **Run tests after EACH phase**: Don't wait until the end
- **Commit after EACH phase**: Enables easy rollback if needed
- **Document breaking changes**: Keep running list for PR description
- **Grep extensively**: Use `grep -r "pattern" src/` to find hidden references

### Post-Implementation Verification

After Phase 4 completion:

- [ ] Fresh database migration: `docker-compose down -v && uv run alembic upgrade head`
- [ ] All tests pass: `uv run pytest tests/ --cov=src`
- [ ] Coverage ≥80%: Check `--cov-report` output
- [ ] No role references: `grep -r "\brole\b" src/ --include="*.py"` (except account permissions)
- [ ] Linters pass: `uv run ruff check . && uv run mypy src/`
- [ ] Server starts: `uv run uvicorn src.main:app`
- [ ] Admin login works: `curl -X POST http://localhost:8000/api/v1/auth/login`

### Rollback Plan

If critical issues discovered during implementation:

1. **After Phase 1 (migration applied)**:
   - Run: `uv run alembic downgrade -1`
   - Recreates tables (data lost - restore from backup)

2. **After Phase 2 (code removed)**:
   - Run: `git revert HEAD` (restore deleted code)
   - Run: `uv run alembic downgrade -1`

3. **After Phase 3+ (tests updated)**:
   - Full rollback: `git reset --hard <commit-before-phase1>`
   - Restore database from backup

---

## Summary

This plan provides a comprehensive roadmap to remove the role-based authorization system from the Emerald Finance Platform backend. By following the four sequential phases - Database Migration, Code Removal, Test Updates, and Documentation - the implementation will be safe, systematic, and reversible.

**Key Deliverables**:
- 9 files deleted (~1,500 lines removed)
- 2 database tables removed (roles, user_roles)
- 7 API endpoints removed (/admin/*)
- Simplified authorization using single `is_admin` flag
- All tests passing with ≥80% coverage
- Updated documentation reflecting new architecture

**Success Metrics**:
- Zero role-related code in codebase
- All admin functionality preserved
- Performance improvement from fewer JOINs
- Reduced maintenance burden
- Clean, understandable authorization model

This plan is ready for implementation by any developer familiar with the codebase standards outlined in `.claude/standards/`.

---

**Plan created**: 2025-11-26
**Estimated completion**: 3.5-4.5 days (1 developer)
**Risk level**: Low (reversible migrations, comprehensive testing)
**Breaking changes**: Yes (admin API endpoints removed - frontend impact)
