# Implementation Plan: Eliminate Global Database Engine

**Date**: 2025-11-03
**Priority**: P0 (Critical Technical Debt)
**Estimated Effort**: 4-6 hours (1 developer)
**Risk Level**: Medium

---

## 1. Executive Summary

This hotfix addresses a critical anti-pattern in the codebase: the use of a global `engine` variable in `src/core/database.py` (line 75). Global variables introduce significant technical debt by making code harder to test, reducing modularity, creating hidden dependencies, complicating concurrent execution, and making debugging more difficult.

The current implementation creates a global `AsyncEngine` instance at module import time, which is then used by `AsyncSessionLocal` and referenced in the `close_database_connection()` function. While the application currently works, this pattern violates several software engineering principles and creates maintenance challenges.

### Primary Objectives

1. **Eliminate global state**: Remove the global `engine` variable from `src/core/database.py`
2. **Implement proper lifecycle management**: Use FastAPI's lifespan context manager to manage engine creation and disposal
3. **Maintain backward compatibility**: Ensure all existing functionality continues to work without breaking changes
4. **Improve testability**: Make the database engine more easily mockable and testable

### Expected Outcomes

- Zero global variables in the database module
- Explicit engine lifecycle management through FastAPI's application state
- All tests passing with no behavioral changes
- Improved code maintainability and testability
- Foundation for future multi-database support

### Success Criteria

- [ ] No global `engine` variable in `src/core/database.py`
- [ ] All existing tests pass without modification
- [ ] `close_database_connection()` works correctly during application shutdown
- [ ] Health check endpoint still functions properly
- [ ] No breaking changes to public API

---

## 2. Technical Architecture

### 2.1 System Design Overview

The refactoring follows the **Application State Pattern** recommended by FastAPI for managing stateful resources like database engines. This pattern uses FastAPI's `app.state` to store application-wide resources that need to be initialized during startup and cleaned up during shutdown.

**Current Architecture (Problematic)**:

```
Module Import Time
    ↓
Create Global Engine (database.py:75)
    ↓
Create SessionMaker (database.py:82-88)
    ↓
FastAPI Application Startup
    ↓
[Engine already exists]
    ↓
Application Running
    ↓
Application Shutdown
    ↓
close_database_connection() accesses global engine
```

**New Architecture (Proposed)**:

```
FastAPI Application Startup
    ↓
lifespan() context manager
    ↓
Create Engine & Store in app.state
    ↓
Create SessionMaker with app.state.engine
    ↓
Application Running (engine accessed via app.state)
    ↓
Application Shutdown
    ↓
lifespan() cleanup: dispose engine from app.state
```

**Key Components and Responsibilities**:

| Component | Current Responsibility | New Responsibility |
|-----------|----------------------|-------------------|
| `create_database_engine()` | Called at module import | Called during lifespan startup |
| `engine` variable | Global module variable | Stored in `app.state.engine` |
| `AsyncSessionLocal` | Created with global engine | Created with engine from dependency |
| `get_db()` | Yields session from global sessionmaker | Yields session from request-scoped sessionmaker |
| `close_database_connection()` | Accesses global engine | Receives engine as parameter |
| `lifespan()` | Only logs and calls close function | Creates and manages engine lifecycle |

**Integration Points**:

1. **FastAPI Application** (`src/main.py`): Lifespan context manager manages engine
2. **Health Checks** (`src/main.py:260-298`): Access engine via `request.app.state.engine`
3. **Public API** (`src/core/__init__.py`): Remove `engine` from exports
4. **Tests** (`tests/conftest.py`): Already create independent engines, no changes needed

### 2.2 Technology Decisions

**FastAPI Lifespan Context Manager**
- **Purpose**: Manage resource initialization and cleanup with async support
- **Why this choice**:
  - Built-in FastAPI feature designed for this exact use case
  - Provides proper async/await support for engine disposal
  - Ensures cleanup happens even if exceptions occur
  - Standard pattern recommended in FastAPI documentation
- **Version**: FastAPI 0.100+ (current project uses compatible version)
- **Alternatives considered**:
  - Startup/shutdown events (deprecated in FastAPI 0.100+)
  - Global singleton pattern (this is what we're eliminating)
  - Dependency injection container (overkill for single engine)

**FastAPI Application State**
- **Purpose**: Store application-wide resources that need to persist across requests
- **Why this choice**:
  - Thread-safe and request-isolated
  - Built-in FastAPI feature with no external dependencies
  - Accessible from anywhere via request or app object
  - Clean and explicit resource management
- **Alternatives considered**:
  - Context variables (more complex, harder to test)
  - Class-based state management (unnecessary complexity)
  - Keep global variable (defeats the purpose of this refactoring)

**Dependency Injection Pattern**
- **Purpose**: Provide database sessions to routes and services
- **Why this choice**:
  - Already implemented in the codebase via `get_db()`
  - Natural fit with FastAPI's dependency system
  - Easy to mock in tests
  - Explicit dependencies in function signatures
- **Version**: Current implementation, no changes needed
- **Alternatives considered**: None - current pattern is already optimal

### 2.3 File Structure

The refactoring involves minimal file changes to reduce risk:

```
src/
├── core/
│   ├── __init__.py           # Remove 'engine' from exports
│   ├── database.py           # Main refactoring target
│   └── config.py             # No changes needed
├── main.py                   # Update lifespan manager
└── api/
    └── ...                   # No changes needed

tests/
├── conftest.py               # No changes needed (already creates test engines)
└── ...                       # No changes needed

alembic/
└── env.py                    # No changes needed (creates own engine)
```

**File Purpose**:

- `src/core/database.py`: Core database functionality - remove global engine, update functions
- `src/main.py`: Application entry point - update lifespan to manage engine
- `src/core/__init__.py`: Public API - remove engine export
- Tests and Alembic: No changes needed (already independent)

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Database Engine Lifecycle Management

**Files Involved**:
- `src/core/database.py`
- `src/main.py`

**Purpose**: Manage the creation, storage, and disposal of the database engine through the application lifecycle instead of at module import time.

**Implementation Requirements**:

1. **Core Logic**:
   - Remove global `engine` variable instantiation (database.py:75)
   - Remove global `AsyncSessionLocal` instantiation (database.py:82-88)
   - Update `get_db()` to create sessionmaker on-demand or use app state
   - Update `close_database_connection()` to accept engine as parameter
   - Add engine initialization to `lifespan()` context manager in main.py

2. **Data Handling**:
   - Engine created once during startup
   - Engine stored in `app.state.engine`
   - Engine disposed during shutdown
   - Sessions created per-request via dependency injection (no change)
   - All existing session commit/rollback behavior preserved

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Engine creation fails during startup → Log error and raise exception (fail fast)
   - [ ] Handle case: Engine is None in `close_database_connection()` → Log warning and return early
   - [ ] Handle case: Dispose fails during shutdown → Log error but don't crash
   - [ ] Handle case: Multiple dispose calls → Engine should handle gracefully (SQLAlchemy built-in)
   - [ ] Validate: `get_db()` called before app startup → Should not occur in normal flow, but document requirement
   - [ ] Error: Database connection fails during startup → FastAPI will fail to start (acceptable behavior)

4. **Dependencies**:
   - Internal:
     - `src.core.config.settings` (database URL and pool settings)
     - FastAPI application instance (`app`)
   - External:
     - `sqlalchemy.ext.asyncio` (AsyncEngine, create_async_engine, async_sessionmaker)
     - `fastapi` (Request object for accessing app.state)

5. **Testing Requirements**:
   - [ ] Unit test: `create_database_engine()` returns valid AsyncEngine
   - [ ] Unit test: `create_database_engine()` uses settings correctly
   - [ ] Unit test: `close_database_connection()` handles None engine gracefully
   - [ ] Integration test: Application startup creates engine successfully
   - [ ] Integration test: Application shutdown disposes engine
   - [ ] Integration test: `get_db()` yields working sessions
   - [ ] E2E test: Health check endpoint works after refactoring

**Acceptance Criteria**:
- [ ] No global variables in `src/core/database.py`
- [ ] Engine created during app startup, not at import time
- [ ] Engine accessible via `app.state.engine` or request dependency
- [ ] All existing tests pass without modification
- [ ] Application starts and stops cleanly
- [ ] No memory leaks (engine properly disposed)

**Implementation Notes**:
- FastAPI's lifespan context manager guarantees cleanup even on exceptions
- `app.state` is a `State` instance from Starlette, which is a simple attribute holder
- Sessions are already per-request scoped, so no changes needed there
- The global `AsyncSessionLocal` can be replaced with a function that creates it on-demand

---

#### Component: Session Factory Management

**Files Involved**:
- `src/core/database.py`

**Purpose**: Replace the global `AsyncSessionLocal` sessionmaker with a pattern that doesn't depend on global state.

**Implementation Requirements**:

1. **Core Logic**:
   - Remove global `AsyncSessionLocal` variable
   - Create a function `get_sessionmaker(engine: AsyncEngine)` that returns a configured sessionmaker
   - Update `get_db()` to get engine from request context and create sessionmaker
   - Alternative: Create sessionmaker during startup and store in app.state alongside engine

2. **Data Handling**:
   - Input: AsyncEngine instance (from app.state)
   - Output: Configured async_sessionmaker
   - Configuration: Same settings as current (expire_on_commit=False, autocommit=False, autoflush=False)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Engine not available → Raise descriptive error
   - [ ] Validate: Sessionmaker configuration matches current behavior
   - [ ] Error: Session creation fails → Let SQLAlchemy error propagate (current behavior)

4. **Dependencies**:
   - Internal: Engine from `app.state` or dependency parameter
   - External: `sqlalchemy.ext.asyncio.async_sessionmaker`, `sqlalchemy.ext.asyncio.AsyncSession`

5. **Testing Requirements**:
   - [ ] Unit test: `get_sessionmaker()` returns properly configured sessionmaker
   - [ ] Unit test: Sessions from new sessionmaker have correct settings
   - [ ] Integration test: `get_db()` dependency works in FastAPI routes

**Acceptance Criteria**:
- [ ] No global `AsyncSessionLocal` variable
- [ ] Sessionmaker created with same configuration as before
- [ ] All routes using `Depends(get_db)` work correctly
- [ ] Session behavior (commit, rollback, close) unchanged

**Implementation Notes**:
- Two viable approaches:
  1. Create sessionmaker during startup, store in `app.state.sessionmaker`
  2. Create sessionmaker on-demand in `get_db()` (minimal overhead)
- Approach 1 is simpler and recommended (one-time setup)
- Sessionmaker is lightweight and thread-safe, so either approach works

---

#### Component: Health Check Database Access

**Files Involved**:
- `src/core/database.py` (check_database_connection function)
- `src/main.py` (readiness_check endpoint)

**Purpose**: Update health check functions to work without global engine while maintaining functionality.

**Implementation Requirements**:

1. **Core Logic**:
   - `check_database_connection()` currently uses global `AsyncSessionLocal`
   - Option A: Accept sessionmaker as parameter
   - Option B: Accept engine as parameter and create sessionmaker internally
   - Option C: Pass request object and access app.state from it
   - Update `/health/ready` endpoint to pass appropriate parameter

2. **Data Handling**:
   - Input: Sessionmaker or Engine
   - Output: Boolean (True if healthy, False otherwise)
   - No changes to error handling or logging

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Database unreachable → Return False (current behavior)
   - [ ] Handle case: Sessionmaker is None → Return False with warning log
   - [ ] Error: Any exception during health check → Catch and return False (current behavior)

4. **Dependencies**:
   - Internal: App state (via request or direct parameter)
   - External: SQLAlchemy AsyncSession

5. **Testing Requirements**:
   - [ ] Unit test: Health check returns True with valid database
   - [ ] Unit test: Health check returns False when database unreachable
   - [ ] Integration test: `/health/ready` endpoint returns correct status

**Acceptance Criteria**:
- [ ] Health check function works without global state
- [ ] `/health/ready` endpoint functionality preserved
- [ ] Error handling and logging behavior unchanged

**Implementation Notes**:
- Simplest approach: Pass `request` to `check_database_connection()` and access `request.app.state.sessionmaker`
- Alternative: Use a background dependency that provides sessionmaker
- Health checks should not fail app startup, only report status

---

### 3.2 Detailed File Specifications

#### `src/core/database.py`

**Purpose**: Provide database connection and session management without global state

**Implementation Changes**:

**Change 1**: Remove global engine and sessionmaker (lines 74-88)

**Before**:
```python
# Global engine instance
engine: AsyncEngine = create_database_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
```

**After**:
```python
# Engine and sessionmaker are now managed via FastAPI app.state
# No global instances - use get_db() dependency for sessions
```

**Change 2**: Update `get_db()` to use app state (lines 95-123)

**Before**:
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**After**:
```python
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to provide database session to FastAPI routes.

    Gets the sessionmaker from app state and yields a session.

    Args:
        request: FastAPI request object (provides access to app.state)

    Yields:
        AsyncSession: Database session for the request

    Raises:
        Exception: Re-raises any exception after rolling back transaction
    """
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Change 3**: Update `check_database_connection()` (lines 129-145)

**Before**:
```python
async def check_database_connection() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
```

**After**:
```python
async def check_database_connection(sessionmaker: async_sessionmaker) -> bool:
    """
    Check if database connection is healthy.

    Used for health check endpoints to verify database connectivity.

    Args:
        sessionmaker: AsyncSessionMaker from app.state

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with sessionmaker() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
```

**Change 4**: Update `close_database_connection()` (lines 151-162)

**Before**:
```python
async def close_database_connection() -> None:
    global engine  # TODO Change to not use global variables
    if engine:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
```

**After**:
```python
async def close_database_connection(engine: AsyncEngine | None) -> None:
    """
    Close database engine and dispose of connection pool.

    Should be called on application shutdown to gracefully close
    all database connections.

    Args:
        engine: The AsyncEngine to dispose. If None, logs warning and returns.
    """
    if engine is None:
        logger.warning("close_database_connection called with None engine")
        return

    try:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")
        # Don't raise - we're shutting down anyway
```

**Edge Cases**:
- When engine is None: Log warning and return early (defensive programming)
- When dispose fails: Log error but don't crash (shutdown should continue)
- When sessionmaker not in app.state: Will raise AttributeError (fail fast - configuration error)

**Tests**:
- [ ] Test: `get_db()` with valid app state yields working session
- [ ] Test: `get_db()` commits on success
- [ ] Test: `get_db()` rolls back on exception
- [ ] Test: `check_database_connection()` returns True with valid DB
- [ ] Test: `check_database_connection()` returns False on connection error
- [ ] Test: `close_database_connection()` handles None gracefully
- [ ] Test: `close_database_connection()` logs success on normal disposal

---

#### `src/main.py`

**Purpose**: Update lifespan manager to create and manage database engine

**Implementation Changes**:

**Change 1**: Update lifespan context manager (lines 52-69)

**Before**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database connection initialization
    - Resource cleanup on shutdown
    """
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")
    await close_database_connection()
```

**After**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database engine creation and storage in app.state
    - Session factory creation
    - Resource cleanup on shutdown
    """
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    # Create database engine and store in app state
    logger.info("Initializing database engine...")
    app.state.engine = create_database_engine()

    # Create sessionmaker and store in app state
    app.state.sessionmaker = async_sessionmaker(
        app.state.engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Database engine initialized successfully")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")
    await close_database_connection(app.state.engine)
    app.state.engine = None
    app.state.sessionmaker = None
```

**Change 2**: Update readiness check endpoint (lines 276-298)

**Before**:
```python
@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    # TODO: Add database connectivity check
    # TODO: Add Redis connectivity check

    return {
        "status": "ready",
        "app": settings.app_name,
        "version": settings.version,
        "checks": {
            "database": "ok" if await check_database_connection() else "ko",
            "redis": "ok",  # Placeholder
        },
    }
```

**After**:
```python
@app.get("/health/ready", tags=["Health"])
async def readiness_check(request: Request):
    """
    Readiness check endpoint.

    Checks if the application is ready to serve requests.
    This verifies database connectivity and other critical dependencies.

    Returns:
        Detailed readiness status
    """
    # Check database connection
    sessionmaker = request.app.state.sessionmaker
    db_healthy = await check_database_connection(sessionmaker)

    return {
        "status": "ready" if db_healthy else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "checks": {
            "database": "ok" if db_healthy else "ko",
            "redis": "ok",  # Placeholder - TODO: Add Redis check
        },
    }
```

**Change 3**: Update imports (lines 1-31)

**Before**:
```python
from src.core.database import check_database_connection, close_database_connection
```

**After**:
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.database import (
    check_database_connection,
    close_database_connection,
    create_database_engine,
)
```

**Edge Cases**:
- When engine creation fails during startup: Exception propagates, app fails to start (correct behavior)
- When disposal fails during shutdown: Exception logged but app continues shutdown
- When sessionmaker accessed before startup: AttributeError (configuration error - should never happen in production)

**Tests**:
- [ ] Test: App starts successfully and creates engine
- [ ] Test: App.state.engine is AsyncEngine instance
- [ ] Test: App.state.sessionmaker is async_sessionmaker instance
- [ ] Test: App shutdown disposes engine and clears state
- [ ] Test: Readiness endpoint returns correct status

---

#### `src/core/__init__.py`

**Purpose**: Remove engine from public API exports

**Implementation Changes**:

**Change 1**: Remove engine from imports and exports (lines 8-14, 30-38)

**Before**:
```python
from src.core.database import (
    AsyncSessionLocal,
    check_database_connection,
    close_database_connection,
    engine,
    get_db,
)

__all__ = [
    # Config
    "settings",
    # Database
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "check_database_connection",
    "close_database_connection",
    ...
]
```

**After**:
```python
from src.core.database import (
    check_database_connection,
    close_database_connection,
    create_database_engine,
    get_db,
)

__all__ = [
    # Config
    "settings",
    # Database
    "create_database_engine",
    "get_db",
    "check_database_connection",
    "close_database_connection",
    ...
]
```

**Rationale**:
- `engine` should not be part of the public API - it's managed internally by the app
- `AsyncSessionLocal` is removed as it's created internally and accessed via `get_db()`
- `create_database_engine` is exported for testing and explicit engine creation if needed

**Edge Cases**:
- If any code imports `engine` from `src.core`, it will fail at import time (breaking change detection)
- No known usages outside of `database.py` and `main.py`

**Tests**:
- [ ] Test: Importing from `src.core` doesn't include `engine`
- [ ] Test: `create_database_engine` is accessible from `src.core`

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

This is a simple hotfix that can be completed in a single phase. However, for clarity and risk management, the tasks are broken down into discrete steps that can be validated incrementally.

#### Phase 1: Global Variable Elimination (Size: S, Priority: P0)

**Goal**: Replace global engine and sessionmaker with FastAPI app state management while maintaining 100% backward compatibility in behavior.

**Scope**:
- ✅ Include: All changes to `src/core/database.py`, `src/main.py`, and `src/core/__init__.py`
- ✅ Include: Running existing test suite to verify no regressions
- ✅ Include: Manual verification of health check endpoints
- ❌ Exclude: New features or additional refactoring
- ❌ Exclude: Test file modifications (they already create independent engines)
- ❌ Exclude: Performance optimization

**Components to Implement**:
- [ ] Database engine lifecycle management
- [ ] Session factory management
- [ ] Health check database access
- [ ] Public API cleanup

**Detailed Tasks**:

1. [ ] Update `src/core/database.py`
   - Remove global `engine` variable (line 75)
   - Remove global `AsyncSessionLocal` variable (lines 82-88)
   - Update `get_db()` to accept `Request` and use `request.app.state.sessionmaker`
   - Update `check_database_connection()` to accept sessionmaker parameter
   - Update `close_database_connection()` to accept engine parameter with None handling
   - Update docstrings to reflect new behavior
   - Remove global variable TODO comment (line 158)

2. [ ] Update `src/main.py`
   - Add imports: `AsyncSession`, `async_sessionmaker`, `create_database_engine`
   - Update `lifespan()` to create engine and store in `app.state.engine`
   - Update `lifespan()` to create sessionmaker and store in `app.state.sessionmaker`
   - Update `lifespan()` cleanup to pass `app.state.engine` to `close_database_connection()`
   - Update `readiness_check()` to accept `Request` parameter
   - Update `readiness_check()` to pass sessionmaker to `check_database_connection()`
   - Update return status to "degraded" if database is unhealthy

3. [ ] Update `src/core/__init__.py`
   - Remove `engine` from imports
   - Remove `AsyncSessionLocal` from imports
   - Add `create_database_engine` to imports
   - Update `__all__` exports list accordingly

4. [ ] Run test suite
   - Run unit tests: `uv run pytest tests/unit -v`
   - Run integration tests: `uv run pytest tests/integration -v`
   - Run all tests: `uv run pytest tests/ -v`
   - Verify 100% of existing tests pass

5. [ ] Manual verification
   - Start application: `uv run python -m uvicorn src.main:app --reload`
   - Test `/health` endpoint
   - Test `/health/ready` endpoint
   - Test login endpoint (requires database access)
   - Verify clean shutdown with Ctrl+C

6. [ ] Code review and cleanup
   - Review all changes for consistency
   - Ensure all docstrings are updated
   - Verify no TODO comments remain related to this issue
   - Check for any lingering global variable patterns

**Dependencies**:
- Requires: Access to development database
- Requires: Redis running (for rate limiting in integration tests)
- Blocks: None - this is a self-contained refactoring

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (100% pass rate)
- [ ] No global variables in `src/core/database.py`
- [ ] Application starts without errors
- [ ] Application shuts down cleanly with proper disposal logs
- [ ] Health check endpoints return correct responses
- [ ] Database connections are properly closed (verify via PostgreSQL pg_stat_activity)
- [ ] Code reviewed and approved
- [ ] No TODOs related to global variables remain

**Risk Factors**:
- **Risk**: Breaking change to `get_db()` signature affects all routes
  - **Mitigation**: FastAPI automatically injects `Request` - no route changes needed
  - **Validation**: Run full test suite before and after

- **Risk**: Tests fail due to missing app.state setup
  - **Mitigation**: Tests already create independent engines via `test_engine` fixture
  - **Validation**: Review `tests/conftest.py` to confirm test isolation

- **Risk**: Engine not disposed properly during shutdown
  - **Mitigation**: Use try-except in disposal code with logging
  - **Validation**: Check PostgreSQL connections after app shutdown

- **Risk**: Health check fails if called before app fully initialized
  - **Mitigation**: FastAPI ensures lifespan completes before accepting requests
  - **Validation**: Test health endpoint immediately after startup

**Estimated Effort**: 4-6 hours for 1 developer

**Breakdown**:
- Code changes: 2 hours
- Testing: 1-2 hours
- Manual verification: 1 hour
- Documentation and review: 1 hour

---

### 4.2 Implementation Sequence

```
Task 1: Update src/core/database.py (60 min)
  ↓
Task 2: Update src/main.py (45 min)
  ↓
Task 3: Update src/core/__init__.py (15 min)
  ↓
Task 4: Run test suite (30-60 min)
  ↓
Task 5: Manual verification (30 min)
  ↓
Task 6: Code review and cleanup (30 min)
```

**Rationale for ordering**:
- Database module first because it defines the new interfaces
- Main app second to implement the lifespan changes
- Init cleanup third as it's the simplest change
- Testing and verification at the end to validate everything works together

**Quick Wins**: None - this is a small refactoring that should be completed in one session

**Implementation Tips**:
1. Make all code changes first, then test (avoid partial states)
2. Keep the old code commented out initially for easy rollback if needed
3. Use git commits after each task for easy rollback points
4. Run tests frequently during development to catch issues early
5. Use `git diff` to review all changes before final testing

---

## 5. Simplicity & Design Validation

### Simplicity Checklist:

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. We're using FastAPI's built-in `app.state` and lifespan manager, which are designed exactly for this use case. No external libraries or complex patterns needed.

- [x] **Have we avoided premature optimization?**
  - Yes. We're not adding caching, connection pooling changes, or other optimizations. Only removing the global variable and using app state.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. The project already uses FastAPI, dependency injection via `Depends()`, and Pydantic settings. This solution uses the same patterns.

- [x] **Can we deliver value in smaller increments?**
  - No. This refactoring must be atomic - we can't have a partially migrated state. However, the entire change is small enough to complete in one session.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. Global variables are a well-documented anti-pattern that causes real issues:
    - Makes testing harder (hard to mock global engine)
    - Creates hidden dependencies
    - Complicates lifecycle management
    - The TODO comment in the code acknowledges this is a known issue

### Alternatives Considered:

**Alternative 1: Keep global variable, improve lifecycle management**
- **Description**: Keep the global `engine` but add better initialization and disposal logic
- **Why not chosen**: Doesn't solve the fundamental problem of global state. Still hard to test and creates hidden dependencies. The TODO comment indicates the team already knows this needs to change.

**Alternative 2: Dependency injection container (python-dependency-injector)**
- **Description**: Use a DI container library to manage engine lifecycle
- **Why not chosen**: Overkill for a single resource. Adds external dependency. FastAPI already provides everything we need via `app.state` and `Depends()`.

**Alternative 3: Context variables (contextvars)**
- **Description**: Use Python's `contextvars` to manage engine per-context
- **Why not chosen**: More complex than needed. `contextvars` is great for request-scoped state, but the engine is application-scoped. `app.state` is simpler and more explicit.

**Alternative 4: Singleton class with lazy initialization**
- **Description**: Wrap engine in a singleton class that initializes on first use
- **Why not chosen**: Still global state, just hidden in a class. Doesn't solve testability or lifecycle management issues. More complex than `app.state`.

### Rationale:

The **FastAPI app.state pattern** is chosen because:

1. **Built-in and standard**: No external dependencies, recommended by FastAPI docs
2. **Explicit lifecycle**: Lifespan context manager makes initialization and cleanup obvious
3. **Easy to test**: Tests can override `app.state` or create independent apps
4. **Thread-safe**: Starlette's `State` class is safe for concurrent access
5. **Minimal changes**: Requires updating only 3 files with clear, focused changes
6. **Backward compatible**: Existing code using `Depends(get_db)` doesn't change
7. **Future-proof**: Easy to extend for multiple databases or other stateful resources

This solution is the **minimum change** required to eliminate global state while following FastAPI best practices.

---

## 6. References & Related Documents

### FastAPI Documentation
- [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) - Official FastAPI guide on startup/shutdown
- [Application State](https://www.starlette.io/applications/#storing-state-on-the-app-instance) - Starlette documentation on app.state
- [Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/) - FastAPI dependency system

### SQLAlchemy Documentation
- [Async Engine](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncEngine) - AsyncEngine API reference
- [Async Sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncio-scoped-session) - Async session management patterns
- [Engine Disposal](https://docs.sqlalchemy.org/en/20/core/connections.html#engine-disposal) - Best practices for disposing engines

### Best Practices Articles
- [Using Global Variables in Python Functions: Best Practices and Alternatives](https://www.fromdev.com/2025/04/using-global-variables-in-python-functions-best-practices-and-alternatives.html)
- [FastAPI with Async SQLAlchemy, SQLModel, and Alembic](https://testdriven.io/blog/fastapi-sqlmodel/)
- [Why are global variables evil?](https://stackoverflow.com/questions/19158339/why-are-global-variables-evil)

### Internal Documentation
- `src/core/database.py` - Current database implementation with TODO comment
- `tests/conftest.py` - Test fixtures showing proper engine management patterns
- `alembic/env.py` - Migration environment showing independent engine creation

### Related Design Patterns
- **Dependency Injection Pattern**: Used throughout the codebase via FastAPI's `Depends()`
- **Application State Pattern**: Managing application-wide resources in web frameworks
- **Lifespan Context Manager Pattern**: Resource initialization and cleanup in async Python

### Security Considerations
- No security implications - this refactoring doesn't change authentication, authorization, or data handling
- Connection pooling and security settings remain unchanged
- Database credentials still managed via environment variables through Pydantic settings

### Performance Considerations
- **No performance impact**: Engine is still created once at startup
- Sessionmaker creation is negligible (lightweight factory object)
- `app.state` access is a simple attribute lookup (no overhead)
- Connection pooling behavior remains identical

### Testing Strategy
- **Unit tests**: Test individual functions with mocked dependencies
- **Integration tests**: Test FastAPI routes with real database (existing test suite)
- **Manual testing**: Verify health checks and application lifecycle
- **No new tests needed**: Existing tests already create independent engines properly

### Migration Notes
- **Breaking changes**: None for public API - `Depends(get_db)` still works
- **Internal breaking changes**: Direct imports of `engine` or `AsyncSessionLocal` will fail (no known usages)
- **Rollback plan**: Revert commits if tests fail - no database migrations or data changes involved

---

## Appendix: Code Diff Summary

### File: `src/core/database.py`

**Lines removed**: ~15 lines
**Lines added**: ~20 lines
**Net change**: +5 lines

**Key changes**:
- Remove: `engine: AsyncEngine = create_database_engine()` (line 75)
- Remove: `AsyncSessionLocal = async_sessionmaker(...)` (lines 82-88)
- Modify: `async def get_db()` → `async def get_db(request: Request)`
- Modify: `async def check_database_connection()` → `async def check_database_connection(sessionmaker: async_sessionmaker)`
- Modify: `async def close_database_connection()` → `async def close_database_connection(engine: AsyncEngine | None)`
- Remove: `global engine` statement and TODO comment (line 158)

### File: `src/main.py`

**Lines removed**: ~5 lines
**Lines added**: ~20 lines
**Net change**: +15 lines

**Key changes**:
- Add imports: `AsyncSession`, `async_sessionmaker`, `create_database_engine`
- Modify: `async def lifespan(app: FastAPI)` - add engine and sessionmaker initialization
- Modify: `async def readiness_check()` → `async def readiness_check(request: Request)`
- Update: `close_database_connection()` call to pass engine parameter

### File: `src/core/__init__.py`

**Lines removed**: ~3 lines
**Lines added**: ~2 lines
**Net change**: -1 line

**Key changes**:
- Remove: `engine` from imports and `__all__`
- Remove: `AsyncSessionLocal` from imports and `__all__`
- Add: `create_database_engine` to imports and `__all__`

**Total Impact**: ~20 lines net addition across 3 files, ~40 lines modified

---

## Summary

This implementation plan provides a comprehensive blueprint for eliminating global variables from the database module. The refactoring is:

- **Low risk**: Only 3 files modified, existing tests provide safety net
- **High value**: Removes technical debt, improves testability and maintainability
- **Quick to implement**: 4-6 hours total effort
- **Standards-compliant**: Uses FastAPI best practices and recommended patterns

By following this plan, the codebase will have zero global variables in the database module, explicit lifecycle management through FastAPI's lifespan system, and a more maintainable architecture that follows Python and FastAPI best practices.
