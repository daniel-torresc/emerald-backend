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

```bash
# Run tests
uv run pytest --cov=src

# Format code
uv run ruff format .

# Lint code
uv run ruff check --fix .

# Type checking
uv run mypy src/
```

## Phase Roadmap

- ✅ **Phase 1.1**: Foundation & Database (COMPLETE)
- 🔄 **Phase 1.2**: Authentication & Security (NEXT)
- ⏳ **Phase 1.3**: User Management & Testing

## Documentation

Full documentation available in `docs/` directory.

## License

[Your License Here]
