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
uv run alembic revision --autogenerate -m "Initial migration"
uv run alembic upgrade head

# 6. Run application
uv run uvicorn src.main:app --reload
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

## Environment Variables

See `.env.example` for all available configuration options.

**Key Variables:**
- `SECRET_KEY`: JWT signing key (generate with `openssl rand -hex 32`)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

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
