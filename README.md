# Emerald Finance Platform - Backend

A production-ready FastAPI backend for a personal finance management platform with comprehensive authentication, audit logging, and role-based access control.

## Features (Phase 1.1 Complete)

- ✅ **Async-First Architecture**: FastAPI + SQLAlchemy 2.0 with asyncpg
- ✅ **Argon2id Password Hashing**: NIST-recommended, memory-hard algorithm
- ✅ **JWT Authentication**: Access/refresh tokens with rotation and reuse detection
- ✅ **Role-Based Access Control**: Flexible RBAC with JSONB permissions
- ✅ **Comprehensive Audit Logging**: GDPR-compliant immutable audit trail
- ✅ **Soft Deletes**: Data retention for compliance (7-year SOX/GDPR)
- ✅ **Connection Pooling**: Optimized database performance
- ✅ **Structured Logging**: JSON logs with rotation and correlation IDs

## Tech Stack

- **Python**: 3.13+
- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 16+ (async with asyncpg)
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **Password Hashing**: Argon2id
- **Dependency Management**: uv

## Quick Start

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY (use: openssl rand -hex 32)

# 4. Start services
docker-compose up -d

# 5. Run migrations
uv run alembic upgrade head

# 6. Start application
uv run uvicorn src.main:app --reload

# 7. Bootstrap first admin (via API)
# See "Admin Management" section below for details
```

Visit http://localhost:8000/docs for API documentation.

## 🌐 Service Access Points

After starting the application, you can access the following services:

| Service | Port | URL | Purpose | Credentials |
|---------|------|-----|---------|-------------|
| **FastAPI API** | 8000 | http://localhost:8000 | REST API endpoints | N/A |
| **Swagger UI** | 8000 | http://localhost:8000/docs | Interactive API documentation | N/A |
| **ReDoc** | 8000 | http://localhost:8000/redoc | Alternative API documentation | N/A |
| **pgAdmin** | 5050 | http://localhost:5050 | PostgreSQL web interface | Email: `admin@example.com`<br>Password: `admin` |
| **RedisInsight** | 5540 | http://localhost:5540 | Redis web interface | No password required |
| **PostgreSQL** | 5432 | `localhost:5432` | Database (direct connection) | User: `emerald_user`<br>Password: `emerald_password`<br>Database: `emerald_db` |
| **Redis** | 6379 | `localhost:6379` | Cache/Rate limiter (direct) | No password |

### 🔧 Setting Up Database Access

#### pgAdmin Setup:
1. Open http://localhost:5050
2. Login with credentials above
3. Right-click "Servers" → "Register" → "Server..."
4. **General Tab**: Name: `Emerald Database`
5. **Connection Tab**:
   - Host: `postgres` (Docker network name)
   - Port: `5432`
   - Database: `emerald_db`
   - Username: `emerald_user`
   - Password: `emerald_password`
   - ☑️ Save password
6. Click "Save"

#### RedisInsight Setup:
1. Open http://localhost:5540
2. Click "Add Redis Database"
3. Connection settings:
   - Host: `redis` (Docker network name)
   - Port: `6379`
   - Name: `Emerald Redis`
4. Click "Add Redis Database"

### 📊 Useful Redis Commands

```bash
# Connect to Redis CLI
docker exec -it emerald-redis redis-cli

# View all keys (rate limiting data)
KEYS *

# Get value of a key
GET key_name

# Check time-to-live (TTL) of a key
TTL key_name

# Monitor Redis commands in real-time
MONITOR

# Get Redis statistics
INFO stats

# Count total keys
DBSIZE
```

## Running & Stopping the Application

### Start the Application

```bash
# 1. Start Docker services (PostgreSQL & Redis)
docker-compose up -d

# 2. Run the FastAPI application
uv run uvicorn src.main:app --reload

# The application will be available at:
# - API: http://localhost:8000
# - Swagger UI: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

### Stop the Application

```bash
# 1. Stop the FastAPI application
# Press Ctrl+C in the terminal where uvicorn is running

# 2. Stop Docker services
docker-compose down

# To also remove volumes (WARNING: deletes database data):
docker-compose down -v
```

### Production Mode

```bash
# Run without auto-reload (production)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Run in background
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Stop background process
# Find the process ID
ps aux | grep uvicorn
# Kill the process
kill <PID>
```

### Check Service Status

```bash
# Check Docker services
docker-compose ps

# Check application health
curl http://localhost:8000/health

# View application logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Running with PyCharm (for debugging)

#### Method 1: Using PyCharm Run Configuration

1. **Create a new Run Configuration:**
   - Go to `Run` → `Edit Configurations...`
   - Click `+` → `Python`
   - Configure as follows:
     ```
     Name: FastAPI App
     Script path: <path-to-uv>/bin/uvicorn
     Parameters: src.main:app --reload --host 0.0.0.0 --port 8000
     Working directory: /Users/danieltorres/Documents/emerald/emerald-backend
     Environment variables: (load from .env or set manually)
     Python interpreter: Select your uv-managed Python interpreter
     ```

2. **Find uvicorn path:**
   ```bash
   uv run which uvicorn
   # Or
   uv run python -c "import uvicorn; print(uvicorn.__file__)"
   ```

3. **Set breakpoints** in your code and click the Debug button (🐛)

#### Method 2: Using PyCharm Python Script Configuration

1. **Create a new Python configuration:**
   - Go to `Run` → `Edit Configurations...`
   - Click `+` → `Python`
   - Configure as follows:
     ```
     Name: FastAPI Debug
     Module name: uvicorn
     Parameters: src.main:app --reload --host 0.0.0.0 --port 8000
     Working directory: /Users/danieltorres/Documents/emerald/emerald-backend
     Python interpreter: Select your uv-managed Python interpreter
     ```

2. **Set environment variables** (optional):
   - Click `Environment variables` → `...`
   - Add variables from your `.env` file or check `Load from file` and select `.env`

3. **Run/Debug** the configuration with breakpoints

#### Method 3: Quick Debug Script

Create a `debug.py` file in the project root:

```python
"""Debug entry point for PyCharm."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
```

Then simply right-click `debug.py` → `Debug 'debug'` in PyCharm.

#### Setting up Python Interpreter

1. **Configure uv interpreter:**
   - Go to `File` → `Settings` → `Project: emerald-backend` → `Python Interpreter`
   - Click `Add Interpreter` → `Add Local Interpreter`
   - Select `Virtualenv Environment` → `Existing`
   - Navigate to your uv virtual environment:
     ```bash
     # Find the path
     uv run which python
     # Example: /Users/danieltorres/Documents/emerald/emerald-backend/.venv/bin/python
     ```
   - Select the Python binary from the `.venv/bin/` directory

2. **Verify dependencies are loaded:**
   - PyCharm should detect all packages installed via `uv sync`

#### Debug Tips

- **Set breakpoints** by clicking in the left gutter of the code editor
- **View variables** in the Debug panel when execution pauses
- **Step through code** using F8 (Step Over), F7 (Step Into), Shift+F8 (Step Out)
- **Evaluate expressions** in the Debug Console
- **Hot reload** works with `--reload` flag - code changes auto-restart the server

## 👨‍💼 Admin Management

The platform includes a comprehensive admin management system for user administration and system operations.

### Initial Superuser Setup

The initial superuser is created **automatically during database migration**. No manual API calls or bootstrap steps are needed.

**⚠️ IMPORTANT: Configure environment variables BEFORE running migrations**

Superuser credentials are read from `.env` file:

```bash
# Edit .env file (REQUIRED before running migrations)
SUPERADMIN_USERNAME="admin"
SUPERADMIN_EMAIL="admin@example.com"
SUPERADMIN_PASSWORD="YourSecureP@ss123!"  # CHANGE THIS!
SUPERADMIN_FULL_NAME="System Administrator"
```

**Migration creates the superuser:**

```bash
# Run database migrations (creates schema AND superuser)
uv run alembic upgrade head
```

**Important:**
- Superuser is created automatically when running `alembic upgrade head`
- Migration is **idempotent** - if an admin already exists, creation is skipped
- Password is NEVER stored in plain text - hashed with Argon2id
- After creation, you can change the password via PUT `/admin/users/{id}/password`
- Use the admin API (with authentication) to create additional admins

**Verify superuser was created:**
```bash
# Login as superuser
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"YourSecureP@ss123!"}'
```

### Admin API Endpoints

Once you have an admin account, you can manage admin users via authenticated endpoints:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/admin/users` | POST | Create new admin user | ✅ Admin |
| `/api/v1/admin/users` | GET | List all admin users (paginated) | ✅ Admin |
| `/api/v1/admin/users/{id}` | GET | Get admin user details | ✅ Admin |
| `/api/v1/admin/users/{id}` | PUT | Update admin user | ✅ Admin |
| `/api/v1/admin/users/{id}` | DELETE | Delete admin user (soft delete) | ✅ Admin |
| `/api/v1/admin/users/{id}/password` | PUT | Reset admin password | ✅ Admin |
| `/api/v1/admin/users/{id}/permissions` | PUT | Update admin permissions | ✅ Admin |

**Admin Safeguards:**
- Cannot delete yourself
- Cannot delete the last admin user
- Cannot remove your own admin privileges
- All admin operations are fully audited

### Admin Authentication

All admin endpoints require:
1. Valid JWT access token (from `/api/v1/auth/login`)
2. Admin role (`is_admin = true`)

**Complete workflow example:**
```bash
# Step 1: Configure .env with superuser credentials (before migrations)
# Edit .env file:
# SUPERADMIN_USERNAME="admin"
# SUPERADMIN_EMAIL="admin@example.com"
# SUPERADMIN_PASSWORD="SecureP@ss123"

# Step 2: Run migrations (creates database AND superuser automatically)
uv run alembic upgrade head

# Step 3: Login as superuser
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"SecureP@ss123"}'

# Step 4: Use access token for admin operations
curl http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer <access_token>"

# Step 5: Create another admin (requires auth)
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin2","email":"admin2@example.com","password":"Admin2Pass123!"}'

# Step 6: Change admin password if needed (requires auth)
curl -X PUT http://localhost:8000/api/v1/admin/users/<admin_id>/password \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"new_password":"NewSecureP@ss456"}'
```

## Database Migrations

The project uses Alembic for database schema migrations. Migrations are version-controlled SQL scripts that modify your database schema over time.

### Quick Start

```bash
# Apply all pending migrations (most common)
uv run alembic upgrade head

# Check current migration status
uv run alembic current

# View migration history
uv run alembic history
```

### Common Migration Commands

#### Upgrading Database

```bash
# Upgrade to latest migration
uv run alembic upgrade head

# Upgrade to specific revision
uv run alembic upgrade <revision_id>
# Example: uv run alembic upgrade 4aabd1426c98

# Upgrade by relative steps (e.g., upgrade 2 versions)
uv run alembic upgrade +2
```

#### Downgrading Database

```bash
# Downgrade one migration
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade <revision_id>

# Downgrade to base (removes everything - USE WITH CAUTION)
uv run alembic downgrade base
```

**⚠️ WARNING**: Downgrading deletes data. Always backup before downgrading in production!

#### Checking Status

```bash
# Show current database revision
uv run alembic current

# Show migration history
uv run alembic history

# Show detailed migration info
uv run alembic show <revision_id>

# Preview SQL without executing (dry run)
uv run alembic upgrade head --sql
```

#### Creating New Migrations

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "description of changes"

# Create empty migration template (for manual SQL)
uv run alembic revision -m "description"
```

**Best Practices for Creating Migrations:**
1. Always review auto-generated migrations before applying
2. Test migrations on development database first
3. Never edit applied migrations (create new ones instead)
4. Use descriptive migration messages

### Reset Database (Development Only)

To completely reset your database schema from scratch:

```bash
# Step 1: Downgrade to base (removes all tables/data)
uv run alembic downgrade base

# Step 2: Upgrade to latest
uv run alembic upgrade head

# Step 3: Bootstrap admin (if needed)
curl -X POST http://localhost:8000/api/v1/admin/bootstrap
```

**Alternative: Nuclear option** (deletes Docker volumes):
```bash
docker-compose down -v  # WARNING: Deletes ALL data including volumes
docker-compose up -d
uv run alembic upgrade head
```

### Verifying Migrations

After running migrations, verify the database structure:

```bash
# Check all tables exist (should show 10 tables)
docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "\dt"

# Check enums exist
docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "\dT+"

# Check pg_trgm extension
docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "SELECT * FROM pg_extension WHERE extname = 'pg_trgm';"
```

**Expected Tables:**
- `users` - User accounts
- `roles` - User roles
- `user_roles` - User-role associations
- `refresh_tokens` - JWT refresh tokens
- `audit_logs` - Audit trail
- `bootstrap_state` - Bootstrap tracking
- `accounts` - Financial accounts
- `account_shares` - Account sharing
- `transactions` - Financial transactions
- `transaction_tags` - Transaction tags

### Migration Troubleshooting

#### Problem: "Target database is not up to date"
```bash
# Check what revision the database thinks it's at
uv run alembic current

# Force stamp database to specific version (fixes mismatch)
uv run alembic stamp head
```

#### Problem: "Can't locate revision identified by '...'"
```bash
# Clear version table and re-stamp
docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "DROP TABLE IF EXISTS alembic_version;"
uv run alembic upgrade head
```

#### Problem: Migration fails midway
```bash
# Alembic tracks partial migrations - check current state
uv run alembic current

# If stuck, manually fix the issue and resume
uv run alembic upgrade head

# Or rollback and retry
uv run alembic downgrade -1
uv run alembic upgrade head
```

#### Problem: Schema out of sync with models
```bash
# Generate migration to sync schema with models
uv run alembic revision --autogenerate -m "sync schema with models"

# Review the generated migration carefully!
# Then apply it
uv run alembic upgrade head
```

### Migration File Structure

```
alembic/
├── env.py                 # Alembic environment configuration
├── script.py.mako        # Migration template
└── versions/             # Migration files
    └── 4aabd1426c98_initial_schema.py  # Current migration
```

### Production Migration Workflow

For production deployments:

1. **Test migrations locally first**
   ```bash
   uv run alembic upgrade head
   ```

2. **Backup production database**
   ```bash
   pg_dump -U user -d dbname > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Apply migrations with zero downtime**
   ```bash
   # Use blue-green deployment or rolling updates
   # Apply backward-compatible migrations first
   uv run alembic upgrade head
   ```

4. **Verify migration success**
   ```bash
   uv run alembic current
   # Check application logs for errors
   ```

5. **Rollback plan** (if issues occur)
   ```bash
   uv run alembic downgrade -1
   # Restore from backup if needed
   ```

## Environment Variables

See `.env.example` for all available configuration options.

**Key Variables:**
- `SECRET_KEY`: JWT signing key (generate with `openssl rand -hex 32`)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `INITIAL_ADMIN_*`: Bootstrap environment variables (optional, see Admin Management section)

## Development

### Running Tests

The project uses pytest for testing with comprehensive coverage tracking.

#### Prerequisites

Before running tests, ensure:
1. Docker services are running (PostgreSQL and Redis)
2. Dependencies are installed

```bash
# Start Docker services
docker-compose up -d

# Verify services are running
docker-compose ps
```

#### Basic Test Commands

```bash
# Run all tests
uv run pytest tests/

# Run tests with verbose output
uv run pytest tests/ -v

# Run tests with coverage report
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run tests with coverage JSON output
uv run pytest tests/ --cov=src --cov-report=json

# Run specific test file
uv run pytest tests/integration/test_auth_routes.py

# Run specific test class
uv run pytest tests/integration/test_auth_routes.py::TestRegistration

# Run specific test method
uv run pytest tests/integration/test_auth_routes.py::TestRegistration::test_register_success

# Run tests and stop on first failure
uv run pytest tests/ -x

# Run tests in parallel (faster)
uv run pytest tests/ -n auto
```

#### Test Coverage Requirements

- **Overall code coverage**: 80% minimum
- **Critical paths**: 100% coverage (authentication, payments, data integrity)
- **All public API endpoints**: 100% coverage
- **Business logic**: 90% minimum coverage

#### Current Test Status

```bash
# Check current coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# View coverage by module
uv run pytest tests/ --cov=src --cov-report=term

# Generate HTML coverage report
uv run pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

**Current Coverage**: 67% (Target: 80%)

#### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── integration/             # Integration tests (API routes, DB)
│   └── test_auth_routes.py  # Authentication endpoint tests
├── unit/                    # Unit tests (isolated components)
│   ├── core/
│   └── services/
└── e2e/                     # End-to-end tests (complete workflows)
```

#### Common Test Issues & Solutions

1. **Rate Limiting Errors (429)**
   - The test fixtures automatically clear Redis between tests
   - If you see rate limit errors, ensure Redis is running:
     ```bash
     docker-compose restart redis
     ```

2. **Database Connection Errors**
   - Ensure PostgreSQL is running:
     ```bash
     docker-compose ps postgres
     docker-compose restart postgres
     ```
   - Check database configuration in `.env` matches `docker-compose.yml`

3. **Test Database Cleanup**
   - Tests automatically clean up data after each test
   - To manually clean test database:
     ```bash
     docker exec -it emerald-postgres psql -U emerald_user -d emerald_db_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
     ```

4. **Port Conflicts**
   - If tests fail with "address already in use":
     ```bash
     # Check what's using the port
     lsof -i :8000
     # Kill the process if needed
     kill -9 <PID>
     ```

#### Writing New Tests

Follow these guidelines when adding tests:

1. **Unit Tests**: Test individual functions/classes in isolation
   ```python
   # tests/unit/services/test_auth_service.py
   import pytest
   from src.services.auth_service import AuthService

   @pytest.mark.asyncio
   async def test_hash_password():
       service = AuthService()
       hashed = service.hash_password("TestPass123!")
       assert hashed != "TestPass123!"
   ```

2. **Integration Tests**: Test component interactions
   ```python
   # tests/integration/test_user_routes.py
   @pytest.mark.asyncio
   async def test_get_user(async_client: AsyncClient, test_user: User):
       response = await async_client.get(f"/api/v1/users/{test_user.id}")
       assert response.status_code == 200
   ```

3. **Use Fixtures**: Leverage existing fixtures in `conftest.py`
   - `async_client`: HTTP client for API testing
   - `test_user`: Pre-created test user
   - `admin_user`: Pre-created admin user
   - `user_token`: Authentication tokens for test user

4. **Test Naming**: Use descriptive names
   ```
   test_[function]_[scenario]_[expected_result]
   Example: test_login_invalid_password_returns_401
   ```

#### Continuous Integration

Tests are automatically run in CI/CD:
- All tests must pass before merge
- Coverage must not decrease
- Failed tests block deployment

#### Code Quality Commands

```bash
# Format code (auto-fix)
uv run ruff format .

# Lint code (auto-fix)
uv run ruff check --fix .

# Lint without auto-fix
uv run ruff check .

# Type checking
uv run mypy src/

# Run all quality checks
uv run ruff format . && uv run ruff check --fix . && uv run mypy src/ && uv run pytest tests/ --cov=src
```

#### Pre-commit Hooks

Install pre-commit hooks to automatically run checks:

```bash
# Install hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files

# Update hooks
uv run pre-commit autoupdate
```

The hooks will run on every commit and ensure:
- Code is formatted with Ruff
- Linting passes
- No trailing whitespace
- Files end with newline
- YAML/JSON syntax is valid

## Phase Roadmap

- ✅ **Phase 1.1**: Foundation & Database (COMPLETE)
- 🔄 **Phase 1.2**: Authentication & Security (NEXT)
- ⏳ **Phase 1.3**: User Management & Testing

## Documentation

Full documentation available in `docs/` directory.

## License

[Your License Here]
