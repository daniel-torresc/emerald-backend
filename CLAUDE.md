# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Emerald Finance Platform - Backend**: A production-ready FastAPI backend for personal finance management with comprehensive authentication, audit logging, and admin-based access control.

**Tech Stack:**
- Python 3.13+, FastAPI 0.115+, SQLAlchemy 2.0 (async), PostgreSQL 16+, Redis 7+, Alembic
- Dependency management: `uv` (MANDATORY - never use pip/poetry)
- Password hashing: Argon2id (NIST-recommended)
- Authentication: JWT with access/refresh tokens, rotation, and reuse detection

## API Documentation

- **Swagger UI**: http://localhost:8000/docs (development only)
- **ReDoc**: http://localhost:8000/redoc (development only)
- **Base URL**: `http://localhost:8000/api/v1`

**Service Access:**
- API: http://localhost:8000
- pgAdmin: http://localhost:5050
- RedisInsight: http://localhost:5540
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Essential Commands

### Git Workflow
```bash
# Commit format: conventional commits
# feat: | fix: | docs: | refactor: | test: | chore: | perf: | ci:
git commit -m "feat: add transaction categorization"

# Pre-commit hooks (runs Ruff, Ty, checks)
uv run pre-commit install
uv run pre-commit run --all-files
```

### Development Setup
```bash
# Install dependencies
uv sync

# Start Docker services
docker-compose up -d

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

# Run single test function (fastest feedback)
uv run pytest tests/integration/test_auth_routes.py::test_login_success -v

# Run test class
uv run pytest tests/integration/test_auth_routes.py::TestRegistration -v

# Run with print statements visible
uv run pytest tests/integration/test_auth_routes.py::test_login_success -v -s

# Stop on first failure
uv run pytest tests/ -x
```

### Code Quality
```bash
# Format code (MANDATORY before commit)
uv run ruff format .

# Lint and auto-fix
uv run ruff check --fix .

# Type checking
uv run ty check src/

# Run all quality checks
uv run ruff format . && uv run ruff check --fix . && uv run ty check src/
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

---

# Reference Guide

This section provides a navigation map to implementation standards and best practices.

`TBD`

---

## Architecture Overview

### Layered Architecture

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
TBD
```

### Environment Variables
Located in `.env` (see `.env.example` for template):

---

## Troubleshooting

### "Module not found" errors
```bash
# Ensure dependencies are installed
uv sync

# Verify virtual environment
uv run which python
```

### Port conflicts (8000 already in use)
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```
