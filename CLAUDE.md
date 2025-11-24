# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Emerald Finance Platform - Backend**: A production-ready FastAPI backend for personal finance management with comprehensive authentication, audit logging, and role-based access control.

**Tech Stack:**
- Python 3.13+, FastAPI 0.115+, SQLAlchemy 2.0 (async), PostgreSQL 16+, Redis 7+, Alembic
- Dependency management: `uv` (MANDATORY - never use pip/poetry)
- Password hashing: Argon2id (NIST-recommended)
- Authentication: JWT with access/refresh tokens, rotation, and reuse detection

## Essential Commands

### Development Setup
```bash
# Install dependencies (ALWAYS use uv)
uv sync

# Start Docker services (PostgreSQL + Redis)
docker-compose up -d

# Run database migrations
uv run alembic upgrade head

# Start development server (auto-reload)
uv run uvicorn src.main:app --reload

# Check service status
docker-compose ps
curl http://localhost:8000/health
```

### Testing
```bash
# Run all tests
uv run pytest tests/

# Run with coverage (target: 80% minimum)
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/integration/test_auth_routes.py

# Run specific test method
uv run pytest tests/integration/test_auth_routes.py::TestRegistration::test_register_success

# Run in parallel (faster)
uv run pytest tests/ -n auto
```

### Code Quality
```bash
# Format code (MANDATORY before commit)
uv run ruff format .

# Lint and auto-fix
uv run ruff check --fix .

# Type checking
uv run mypy src/

# Run all quality checks
uv run ruff format . && uv run ruff check --fix . && uv run mypy src/
```

### Database Migrations
```bash
# Create new migration (auto-generate from model changes)
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Check current migration
uv run alembic current

# View migration history
uv run alembic history

# Downgrade one migration (CAUTION: deletes data)
uv run alembic downgrade -1

# Verify database structure
docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "\dt"
```

### Git Workflow
```bash
# Commit format: conventional commits
# feat: | fix: | docs: | refactor: | test: | chore: | perf: | ci:
git commit -m "feat: add transaction categorization"

# Pre-commit hooks (runs Ruff, MyPy, checks)
uv run pre-commit install
uv run pre-commit run --all-files
```

## Architecture Overview

### Layered Architecture (MANDATORY Separation)

This project follows strict **3-layer architecture** with clear boundaries:

```
┌─────────────────────────────────────────────────────┐
│  API Layer (src/api/routes/)                        │
│  - HTTP request/response handling ONLY              │
│  - Route definitions and decorators                 │
│  - Input validation (Pydantic schemas)              │
│  - Status codes, headers                            │
│  - NO business logic                                │
│  - NO database operations                           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼ calls services
┌─────────────────────────────────────────────────────┐
│  Service Layer (src/services/)                      │
│  - ALL business logic lives here                    │
│  - Complex validations and computations             │
│  - Transaction coordination                         │
│  - Orchestration between repositories               │
│  - NO HTTP concerns                                 │
│  - NO direct database queries                       │
└─────────────────────────────────────────────────────┘
                        │
                        ▼ calls repositories
┌─────────────────────────────────────────────────────┐
│  Repository Layer (src/repositories/)               │
│  - ALL database operations (CRUD)                   │
│  - Query construction with SQLAlchemy               │
│  - Soft delete filtering                            │
│  - Generic base repository (BaseRepository)         │
│  - NO business logic                                │
└─────────────────────────────────────────────────────┘
```

**Critical Rules:**
1. **Routes NEVER call repositories directly** - always go through services
2. **Services NEVER handle HTTP concerns** - return domain objects, let routes handle responses
3. **Repositories NEVER contain business logic** - only data access
4. **Dependencies flow downward** - routes → services → repositories → models

### Project Structure
```
src/
├── api/
│   ├── routes/          # Endpoint definitions (auth.py, users.py, etc.)
│   └── dependencies.py  # Shared dependencies (get_current_user, etc.)
├── services/            # Business logic (auth_service.py, user_service.py)
├── repositories/        # Database operations (user_repository.py, base.py)
├── models/              # SQLAlchemy ORM models (user.py, transaction.py)
├── schemas/             # Pydantic validation schemas (requests/responses)
├── core/
│   ├── config.py        # PydanticSettings configuration
│   ├── security.py      # JWT, password hashing, Argon2id
│   ├── database.py      # Async session management, connection pooling
│   └── logging.py       # Structured logging setup
├── exceptions.py        # Custom exception hierarchy
├── middleware.py        # Request ID, logging, security headers
└── main.py             # FastAPI app setup, lifespan, routes
```

### Key Patterns

#### 1. Generic Repository Pattern
All repositories inherit from `BaseRepository[ModelType]` which provides:
- Automatic soft-delete filtering
- Common CRUD operations: `create()`, `get_by_id()`, `get_all()`, `update()`, `delete()`
- Pagination support: `get_paginated()`
- Async/await throughout

**Example:**
```python
class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        # Custom query methods here
        ...
```

#### 2. Dependency Injection
FastAPI dependencies in `src/api/dependencies.py`:
- `get_db()`: Provides async database session
- `get_current_user()`: Validates JWT and returns authenticated user
- `get_current_admin()`: Enforces admin role requirement
- `get_<service_name>()`: Factory functions for service instances

**Example:**
```python
@router.get("/me")
async def get_profile(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    # Route logic here
```

#### 3. Soft Deletes
All models with `deleted_at` field (using `SoftDeleteMixin`):
- Records are never physically deleted
- `deleted_at` timestamp marks deletion
- `BaseRepository` automatically filters out deleted records
- Required for compliance (7-year SOX/GDPR retention)

#### 4. Audit Logging
**Every** state-changing operation is logged to `audit_logs` table:
- Who performed the action (`user_id`)
- What action (`AuditAction` enum: CREATE, UPDATE, DELETE, LOGIN, etc.)
- When (`timestamp`)
- IP address, user agent, request ID
- Status (SUCCESS/FAILURE)
- Immutable audit trail (GDPR-compliant)

**Example:**
```python
await audit_service.log_action(
    db=db,
    user_id=user.id,
    action=AuditAction.USER_UPDATE,
    status=AuditStatus.SUCCESS,
    ip_address=request.client.host,
)
```

#### 5. JWT Authentication
Two-token system with refresh token rotation:
- **Access tokens**: 30-minute expiry, stateless JWT
- **Refresh tokens**: 7-day expiry, stored hashed in database
- **Token rotation**: New refresh token issued on every refresh (old one invalidated)
- **Reuse detection**: If invalidated token is used → revoke entire token family (security)
- Tokens stored in `refresh_tokens` table with `token_family` for tracking

#### 6. Rate Limiting
Redis-backed rate limiting with `slowapi`:
- Global default: `RATE_LIMIT_DEFAULT` (e.g., "100/minute")
- Endpoint-specific limits defined in routes:
  - Register: `RATE_LIMIT_REGISTER` (3/hour)
  - Login: `RATE_LIMIT_LOGIN` (10/minute)
  - Sensitive endpoints: custom limits
- Rate limit by IP address (`get_remote_address`)

#### 7. Async Everything
- **MANDATORY**: Use `async`/`await` for all I/O operations
- Database: `AsyncSession`, `async_sessionmaker`
- All repositories and services are async
- FastAPI routes use `async def`
- Use `asyncio.gather()` for parallel operations

## Configuration

### Environment Variables
Located in `.env` (see `.env.example` for template):

**Critical variables:**
```bash
# Security (REQUIRED)
SECRET_KEY=<generate with: openssl rand -hex 32>
SUPERADMIN_EMAIL=admin@example.com
SUPERADMIN_PASSWORD=<strong password>

# Database
DATABASE_URL=postgresql+asyncpg://emerald_user:emerald_password@localhost:5432/emerald_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development  # development | staging | production
DEBUG=true              # Enable SQL logging, Swagger docs
```

### Superuser Creation
**Superuser is created automatically during migrations** (not via API):
1. Set `SUPERADMIN_*` variables in `.env`
2. Run `uv run alembic upgrade head`
3. Migration creates admin if none exists (idempotent)
4. Login via `/api/v1/auth/login` with configured credentials

## Standards Compliance

This project follows **strict standards** defined in `.claude/standards/` directory:

**When working on this codebase, you MUST:**
1. **Read the relevant standard file first** before implementing:
   - Backend work: `.claude/standards/backend.md`
   - Database changes: `.claude/standards/database.md`
   - API endpoints: `.claude/standards/api.md`
   - Authentication: `.claude/standards/auth.md`
   - Testing: `.claude/standards/testing.md`

2. **Never deviate from standards** without explicit approval

3. **Key standards summary:**
   - Use `uv` exclusively (never pip/poetry)
   - Follow 3-layer architecture strictly (routes → services → repositories)
   - Use Pydantic for all validation
   - Use SQLAlchemy 2.0 async throughout
   - Test coverage: 80% minimum
   - Type hints required on all functions
   - Use Ruff for formatting/linting
   - Conventional commits (feat:, fix:, etc.)

## Common Development Tasks

### Adding a New API Endpoint
1. **Read standards**: `.claude/standards/api.md` and `.claude/standards/backend.md`
2. Create/update Pydantic schema in `src/schemas/`
3. Add business logic to service in `src/services/`
4. Add database operations to repository in `src/repositories/`
5. Create route in `src/api/routes/`
6. Register router in `src/main.py` (if new route file)
7. Write tests in `tests/integration/`
8. Add audit logging if state-changing operation
9. Run code quality checks before commit

### Adding a Database Model
1. **Read standards**: `.claude/standards/database.md`
2. Create model in `src/models/` (inherit from `Base` or use mixins)
3. Add enums to `src/models/enums.py` if needed
4. Create Pydantic schemas in `src/schemas/`
5. Create repository in `src/repositories/` (extend `BaseRepository`)
6. Generate migration: `uv run alembic revision --autogenerate -m "add model"`
7. **Review migration carefully** - Alembic can miss things
8. Test migration: `uv run alembic upgrade head`
9. Create service layer if needed
10. Add tests

### Running Single Test During Development
```bash
# Run single test function (fastest feedback)
uv run pytest tests/integration/test_auth_routes.py::test_login_success -v

# Run test class
uv run pytest tests/integration/test_auth_routes.py::TestRegistration -v

# Run with print statements visible
uv run pytest tests/integration/test_auth_routes.py::test_login_success -v -s

# Stop on first failure
uv run pytest tests/ -x
```

### Debugging Database Issues
```bash
# Connect to PostgreSQL
docker exec -it emerald-postgres psql -U emerald_user -d emerald_db

# View tables
\dt

# View table structure
\d users

# View enums
\dT+

# View indexes
\di

# Run query
SELECT * FROM users WHERE email = 'admin@example.com';
```

### Redis Debugging
```bash
# Connect to Redis CLI
docker exec -it emerald-redis redis-cli

# View all keys (rate limit data)
KEYS *

# Get rate limit counter
GET rate_limit:<ip_address>:<endpoint>

# Monitor real-time commands
MONITOR

# Clear all data (CAUTION)
FLUSHALL
```

## Testing Strategy

### Test Structure
```
tests/
├── conftest.py         # Shared fixtures (async_client, test_user, etc.)
├── unit/               # Isolated component tests (services, utils)
├── integration/        # API endpoint tests with database
└── e2e/                # Complete user workflows
```

### Important Fixtures (in `conftest.py`)
- `async_client`: HTTP client for testing API endpoints
- `test_user`: Pre-created regular user
- `admin_user`: Pre-created admin user
- `user_token`: Valid access/refresh tokens for test_user
- Database automatically rolls back after each test

### Coverage Requirements
- **Overall**: 80% minimum
- **Critical paths** (auth, transactions): 100%
- **Public API endpoints**: 100%
- **Business logic**: 90% minimum

## API Documentation

- **Swagger UI**: http://localhost:8000/docs (development only)
- **ReDoc**: http://localhost:8000/redoc (development only)
- **Base URL**: `http://localhost:8000/api/v1`

**Service Access:**
- API: http://localhost:8000
- pgAdmin: http://localhost:5050 (admin@example.com / admin)
- RedisInsight: http://localhost:5540
- PostgreSQL: localhost:5432 (emerald_user / emerald_password)
- Redis: localhost:6379 (no password)

## Important Notes

### Database Migrations
- **NEVER** edit migrations after they're committed
- **ALWAYS** review auto-generated migrations - Alembic can miss constraints, indexes, and complex changes
- Test migrations on a copy of production data before deploying
- Migrations are **idempotent** - superuser creation skipped if admin exists

### Security Considerations
- All passwords hashed with Argon2id (memory-hard, NIST-recommended)
- JWT tokens use HS256 with secret key rotation support
- Refresh token rotation prevents token theft
- Rate limiting prevents brute force attacks
- Audit logs are immutable (GDPR compliance)
- Soft deletes enable data retention (7-year SOX/GDPR)

### Performance
- Connection pooling: 5 permanent + 10 overflow connections
- Redis caching for rate limiting and sessions
- Async I/O throughout prevents blocking
- Pagination on all list endpoints (default 20, max 100)
- Indexes on frequently queried columns (email, username, foreign keys)

### Logging
- Structured JSON logs with correlation IDs
- Separate files: `app.log` (all logs), `error.log` (errors only)
- Rotating file handlers (10MB max, 5 backups)
- **NEVER log** passwords, tokens, or PII
- Log all exceptions with `exc_info=True`

## Troubleshooting

### "Module not found" errors
```bash
# Ensure dependencies are installed
uv sync

# Verify virtual environment
uv run which python
```

### Migration conflicts
```bash
# Check current state
uv run alembic current

# Force stamp to latest
uv run alembic stamp head

# Or reset database (DELETES ALL DATA)
docker-compose down -v
docker-compose up -d
uv run alembic upgrade head
```

### Rate limiting errors in tests
```bash
# Restart Redis (clears rate limit counters)
docker-compose restart redis
```

### Port conflicts (8000 already in use)
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

## Phase Roadmap
- ✅ Phase 1.1: Foundation & Database (COMPLETE)
- 🔄 Phase 1.2: Authentication & Security (NEXT)
- ⏳ Phase 1.3: User Management & Testing
