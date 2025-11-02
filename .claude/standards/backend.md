# Python Backend Development Standards

## Dependency Management

**MANDATORY: Use `uv` exclusively**
- Initialize all projects with `uv init`
- Add dependencies with `uv add <package>` only
- Add development dependencies with `uv add --dev <package>`
- Lock dependencies with `uv lock` after every dependency change
- ALWAYS commit both `pyproject.toml` and `uv.lock` files
- NEVER use pip, poetry, or any other dependency manager
- Update dependencies monthly and test thoroughly

## Framework Requirements

**MANDATORY: Use FastAPI exclusively for API development**
- Use FastAPI for all REST API endpoints
- Use Uvicorn as the ASGI server
- Always use async/await for I/O operations
- Enable automatic API documentation (Swagger UI at `/docs`) conditionally:
  - Enable in development environment
  - Disable in production environment
  - Configure with: `FastAPI(docs_url="/docs" if settings.DEBUG else None, redoc_url="/redoc" if settings.DEBUG else None)`

## Version Management

**MANDATORY: Use LTS versions exclusively**
- Python: Use latest stable LTS version (minimum 3.13)
- FastAPI: Use latest stable version
- Pydantic: Use v2.x latest stable
- Pydantic Settings: Use latest stable
- SQLAlchemy: Use 2.0+ with async support
- Alembic: Use latest stable for migrations
- Review and update dependencies monthly
- Test all updates in development environment first
- Document breaking changes in CHANGELOG.md

## Project Structure

**MANDATORY: Follow this structure**
```
project/
├── alembic/              # Database migrations
│   └── versions/
├── src/
│   ├── api/
│   │   ├── routes/      # API endpoint definitions ONLY
│   │   │   ├── __init__.py
│   │   │   ├── users.py
│   │   │   └── auth.py
│   │   └── dependencies.py  # Shared dependencies
│   ├── services/        # Business logic layer
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── auth_service.py
│   ├── repositories/    # Database operations
│   │   ├── __init__.py
│   │   ├── base.py     # Generic repository
│   │   └── user_repository.py
│   ├── models/          # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── user.py
│   ├── schemas/         # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── auth.py
│   ├── core/            # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py   # Settings
│   │   ├── security.py # Auth utilities
│   │   ├── database.py # Database connection
│   │   └── logging.py  # Logging configuration
│   ├── exceptions.py    # Custom exceptions
│   ├── middleware.py    # Custom middleware
│   └── main.py         # FastAPI application
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── conftest.py
├── docs/               # Architecture documentation
├── logs/               # Log files (in .gitignore)
├── .env.example
├── .env               # In .gitignore
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── logging_config.yaml
├── pyproject.toml
├── uv.lock
└── README.md
```

## Separation of Concerns

**MANDATORY: Strictly separate layers**

### Route Files (api/routes/)
- ONLY define endpoint decorators and route handlers
- ONLY handle HTTP request/response
- ONLY call service layer methods
- NO business logic allowed
- NO database operations allowed
- NO complex computations allowed
- Validate request data with Pydantic schemas
- Handle HTTP-specific concerns (status codes, headers)

### Service Files (services/)
- ALL business logic must be in service classes
- All data validation beyond schema validation
- All complex computations and algorithms
- Coordinate between multiple repositories
- Handle transaction management
- Services should be dependency-injectable
- Services call repositories, routes call services

### Repository Files (repositories/)
- ALL database operations through repositories
- Repositories handle CRUD operations only
- Use async methods for all database operations
- Implement generic base repository for common operations
- One repository per model/aggregate
- Return domain models, not ORM objects

## Schema Validation

**MANDATORY: Use Pydantic for ALL data validation**
- Create Pydantic schemas for every request and response
- Define separate schemas for: Create, Update, Response, and internal models
- Use field validators for complex validation logic
- Use `model_config` with `from_attributes=True` for ORM models
- NEVER trust unvalidated data
- Validate at API boundaries (requests/responses)
- Use Pydantic V2 features (computed fields, field validators)
- Define schema inheritance hierarchy to reduce duplication

## Database Standards

**MANDATORY: Use SQLAlchemy 2.0+ with async support**
- Use declarative base with mapped_column for all models
- Define models in `models/` directory
- One model per file for complex models
- Use Alembic for all database migrations
- NEVER modify migrations after they're committed
- Use async session management with context managers
- Implement proper connection pooling
- Use relationship() for model relationships
- Add indexes for frequently queried columns
- Use UTC for all timestamps
- Define __repr__ methods for debugging

**MANDATORY: Repository Pattern**
- Create repository classes in `repositories/` directory
- All database queries must go through repositories
- Repositories handle CRUD operations only
- Use async methods for all database operations
- Implement generic base repository for common operations
- Use select() with options() for eager loading
- Avoid N+1 queries (use joinedload or selectinload)

**MANDATORY: Migrations**
- Generate migrations with: `alembic revision --autogenerate -m "description"`
- Review ALL auto-generated migrations before committing
- Test migrations on copy of production data
- Provide both upgrade and downgrade paths
- Never delete old migrations
- Keep migrations atomic and reversible
- Use batch operations for large table modifications
- Add data migrations separately from schema migrations

## Configuration Management

**MANDATORY: Use PydanticSettings exclusively**
- ALL configuration must use `PydanticSettings`
- Create a single `Settings` class in `core/config.py`
- Load from `.env` files
- Use type hints for all settings
- Provide sensible defaults where appropriate
- NEVER hardcode configuration values
- ALWAYS provide `.env.example`
- Document every environment variable
- Implement environment-specific settings (dev, staging, prod)
- Use nested settings models for grouped configuration

**MANDATORY: Environment variables in .env file**
- Store ALL environment-specific configuration in `.env`
- NEVER commit `.env` to version control
- ALWAYS commit `.env.example` with documentation
- Use UPPER_CASE for environment variable names
- Group related variables with comments
- Include example values in `.env.example`

## Logging Standards

**MANDATORY: Use Python's builtin logging module**
- Configure logging in `core/logging.py` or `logging_config.yaml`
- Create separate formatters for: console, file, and JSON
- Implement rotating file handlers (max 10MB, 5 backups)
- Create separate log files for: app.log (all logs) and error.log (errors only)
- Log levels: DEBUG for development, INFO for production
- Use structured logging with proper context
- Include timestamp, logger name, level, function name, and line number in logs
- Create logs/ directory in project root (add to .gitignore)
- NEVER log sensitive information (passwords, tokens, PII)

**MANDATORY: Logger usage**
- Import logger: `logger = logging.getLogger(__name__)`
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log all exceptions with `exc_info=True`
- Log important business events at INFO level
- Log all external API calls with request/response summary
- Log all database operations at DEBUG level
- Include correlation IDs in all logs
- Add contextual information to logs (user_id, request_id, etc.)

## Error Handling

**MANDATORY: Custom exception hierarchy**
- Create custom exception classes in `exceptions.py`
- Inherit from base exception class for app-specific exceptions
- Define exceptions for: NotFound, Unauthorized, Forbidden, BadRequest, ValidationError, etc.
- Include error codes and user-friendly messages
- Use FastAPI exception handlers to convert to HTTP responses
- Implement global exception handler for unexpected errors

**MANDATORY: Exception handling**
- Use try-except blocks for all external calls (database, APIs, file operations)
- Log all exceptions with full traceback
- NEVER expose internal error details to clients
- Return consistent error response format with: error code, message, details
- Use appropriate HTTP status codes
- Handle validation errors from Pydantic
- Catch and handle database-specific exceptions
- Provide helpful error messages for debugging in development
- Sanitize error messages in production

## Security Standards

**MANDATORY: Authentication & Authorization**
- Use OAuth2 with JWT tokens for authentication
- Use python-jose or PyJWT for JWT handling
- Use passlib with bcrypt for password hashing
- NEVER store passwords in plain text
- Implement token refresh mechanism
- Token expiry: 30 minutes (access), 7 days (refresh)
- Use FastAPI Depends() for authentication dependencies
- Implement role-based access control (RBAC) when needed
- Store refresh tokens securely (database, not JWT)
- If using Bearer token authentication, implement a security scheme configuration (HTTPBearer, OAuth2PasswordBearer)

**MANDATORY: Security best practices**
- Enable CORS with explicit allowed origins (NO "*" in production)
- Use HTTPS only in production
- Implement rate limiting (slowapi or fastapi-limiter)
- Sanitize all user inputs
- Use parameterized queries (SQLAlchemy handles this)
- Implement request size limits
- Add security headers (Content-Security-Policy, X-Frame-Options, etc.)
- Validate file uploads (type, size, content)
- Use environment variables for secrets
- Rotate secrets regularly
- Implement CSRF protection for state-changing operations
- Use secure session cookies (httpOnly, secure, sameSite)

**MANDATORY: Sensitive data**
- NEVER log passwords, tokens, or API keys
- NEVER commit secrets to version control
- Use encryption for sensitive data at rest
- Mask sensitive data in logs and responses
- Implement audit logging for sensitive operations
- Follow principle of least privilege
- Sanitize error messages to prevent information leakage

## API Design Standards

**MANDATORY: RESTful conventions**
- Use HTTP methods correctly: GET, POST, PUT, PATCH, DELETE
- Use plural nouns for resources: `/users`, `/posts`
- Use nested routes for relationships: `/users/{id}/posts`
- Use query parameters for filtering, sorting, pagination
- Return appropriate status codes:
  - 200: Success (GET, PUT, PATCH)
  - 201: Created (POST)
  - 204: No Content (DELETE)
  - 400: Bad Request
  - 401: Unauthorized
  - 403: Forbidden
  - 404: Not Found
  - 422: Validation Error
  - 429: Too Many Requests
  - 500: Internal Server Error

**MANDATORY: Response format**
- Use consistent response structure across all endpoints
- Return paginated lists with metadata: data, total, page, per_page, total_pages
- Use ISO 8601 for dates (UTC timezone)
- Use snake_case for JSON keys
- Include resource links when appropriate (HATEOAS principle)
- Return created resource in POST responses
- Use partial responses for PATCH operations

**MANDATORY: API versioning**
- Version API via URL path: `/api/v1/users`
- Maintain backward compatibility within major versions
- Document breaking changes in CHANGELOG.md
- Deprecate old versions gracefully (minimum 6 months notice)
- Use deprecation headers to warn clients
- Support multiple versions simultaneously during transition

**MANDATORY: Request/Response handling**
- Implement request validation with Pydantic
- Use background tasks for long-running operations
- Implement idempotency for non-GET requests
- Support content negotiation (JSON primary, others optional)
- Compress large responses (gzip middleware)
- Implement ETag for caching when appropriate

## Testing Standards

**MANDATORY: Use pytest exclusively**
- Pytest for all tests (unit, integration, e2e)
- Use pytest-asyncio for async tests
- Use pytest-cov for coverage reports
- Minimum 80% code coverage for services and repositories
- Use fixtures for common test data
- Mock external dependencies (APIs, databases in unit tests)
- Use TestClient from FastAPI for API tests
- Create conftest.py for shared fixtures
- Use factories (factory_boy) for test data generation

**MANDATORY: Test structure**
- Organize tests in: unit/, integration/, e2e/ directories
- Mirror application structure in test directories
- Keep test files close to code they test conceptually
- Name test files: `test_<module>.py`
- Name test functions: `test_<function>_<scenario>_<expected_outcome>`

**MANDATORY: Test practices**
- Follow Arrange-Act-Assert (AAA) pattern
- One logical assertion per test (related assertions OK)
- Use descriptive test names that explain behavior
- Test happy path AND error cases
- Test edge cases and boundary conditions
- NEVER test framework code (FastAPI, SQLAlchemy)
- Use parametrize for testing multiple inputs
- Clean up test data after each test
- Use database transactions and rollback in integration tests
- Mock time-dependent code for deterministic tests

## Performance Optimization

**MANDATORY: Database optimization**
- Use select() with options() for eager loading relationships
- Implement database connection pooling with proper sizing
- Use indexes on foreign keys and frequently queried fields
- Avoid N+1 queries (use joinedload or selectinload)
- Use database-level constraints for data integrity
- Implement query result caching for expensive queries (Redis)
- Use bulk operations for multiple inserts/updates
- Monitor slow queries and optimize with EXPLAIN
- Use database-specific features (PostgreSQL JSONB, full-text search)

**MANDATORY: API optimization**
- Implement response caching with Redis for read-heavy endpoints
- Use background tasks for non-critical operations (Celery or FastAPI BackgroundTasks)
- Implement pagination for all list endpoints (default 20 items, max 100)
- Use async everywhere for I/O operations
- Implement request timeout (30 seconds default)
- Stream large responses when possible
- Compress responses (gzip middleware)
- Use connection pooling for external HTTP clients
- Implement circuit breakers for external service calls
- Profile code to identify bottlenecks (cProfile, py-spy)

## Async Best Practices

**MANDATORY: Async/await usage**
- Use async for all I/O operations (database, HTTP, file operations)
- Use asyncio.gather() for parallel async operations
- NEVER use blocking operations in async functions
- Use async context managers for resource management
- Use async generators for streaming data
- Configure proper connection pool sizes for async databases
- Use asyncio.create_task() for fire-and-forget operations
- Handle async timeouts with asyncio.wait_for()
- Use async locks for shared resource access
- Avoid mixing sync and async code (use asyncio.to_thread() when necessary)

## Code Style

**MANDATORY: Follow these style rules**
- Use Black for code formatting (line length 100)
- Use Ruff for linting (replaces flake8, isort, etc.)
- Use MyPy for type checking with strict mode
- ALWAYS prefer classes to single functions
- Type hint ALL function signatures (args and return types)
- Use descriptive variable names (no single letters except in loops)
- Maximum function length: 50 lines
- Maximum file length: 500 lines
- Use docstrings (Google style) for all public functions and classes
- Follow PEP 8 naming conventions
- Use type aliases for complex type hints
- Avoid nested functions deeper than 2 levels
- Extract magic numbers into named constants

**MANDATORY: Type hints**
- Use type hints for all function parameters and return values
- Use Optional[T] for nullable values
- Use Union types or | operator for multiple types
- Use generics (TypeVar) for reusable code
- Use Protocol for structural typing
- Use Literal for fixed value sets
- Avoid using Any unless absolutely necessary

## Documentation

**MANDATORY: Code documentation**
- Use docstrings (Google style) for all public functions and classes
- Include type hints in function signatures
- Document complex business logic with inline comments
- Document WHY not WHAT in comments
- Keep README.md updated with:
  - Project description and purpose
  - Setup instructions (step by step)
  - Environment variables documentation
  - API overview and key endpoints
  - Development workflow
  - Deployment instructions
  - Troubleshooting guide

**MANDATORY: API documentation**
- FastAPI auto-generates OpenAPI docs (Swagger UI)
- Add descriptions to all endpoints using docstrings
- Add examples to Pydantic schemas using Field(examples=[...])
- Document all error responses
- Include authentication requirements
- Document rate limits and pagination
- Maintain API changelog with breaking changes
- Version documentation with API versions

**MANDATORY: Architecture documentation**
- Document architectural decisions in `docs/` directory (ADR format)
- Create sequence diagrams for complex flows
- Document database schema with ER diagrams
- Keep deployment documentation updated
- Document environment setup for different platforms
- Create runbooks for common operations
- Document monitoring and alerting setup

## Monitoring & Observability

**MANDATORY: Health checks**
- Implement `/health` endpoint (always returns 200)
- Implement `/health/ready` endpoint (checks database, cache, external services)
- Include version information in health response
- Include build timestamp and commit hash
- Return degraded state if non-critical services are down

**MANDATORY: Metrics**
- Use prometheus_client for metrics collection
- Track request count, response time, error rate by endpoint
- Monitor database connection pool usage
- Track business metrics (signups, transactions, etc.)
- Expose metrics endpoint: `/metrics`
- Use labels for grouping metrics (endpoint, method, status)
- Monitor memory usage and garbage collection

**MANDATORY: Distributed tracing**
- Add correlation IDs to all requests (generate at entry point)
- Pass correlation IDs to external services in headers
- Include correlation ID in all logs
- Use OpenTelemetry for distributed tracing (recommended)
- Instrument database queries and external API calls
- Add custom spans for important business operations

**MANDATORY: Alerting**
- Set up alerts for: high error rates, slow responses, service unavailability
- Alert on security events (failed auth attempts, rate limit hits)
- Configure different alert levels (warning, critical)
- Include runbook links in alerts
- Avoid alert fatigue with proper thresholds

## Development Workflow

**MANDATORY: Pre-commit hooks**
- Use pre-commit framework
- Run Black for formatting
- Run Ruff for linting
- Run MyPy for type checking
- Check for secrets in commits (detect-secrets)
- Run quick tests on commit
- Validate commit message format
- Check for merge conflicts

**MANDATORY: Git practices**
- Use conventional commits (feat:, fix:, docs:, refactor:, test:, chore:, perf:, ci:)
- Branch naming: feature/description, bugfix/description, hotfix/description
- Squash commits before merging to main
- Write meaningful commit messages (what and why)
- NEVER commit .env, logs/, __pycache__/, or .pytest_cache/
- Keep commits atomic and focused on single change
- Rebase feature branches on main regularly
- Use .gitignore comprehensively

**MANDATORY: Code review**
- All code must be reviewed before merging
- Check for: logic errors, security issues, test coverage, documentation, performance
- Review tests alongside implementation
- Run full test suite in CI/CD
- No merge with failing tests or linting errors
- Check for proper error handling
- Verify logging is appropriate
- Ensure database migrations are reviewed

**MANDATORY: CI/CD pipeline**
- Run linting (Ruff, Black, MyPy) on every commit
- Run full test suite with coverage report
- Build Docker image and push to registry
- Run security scanning (Bandit, Safety)
- Deploy to staging automatically on merge to main
- Require manual approval for production deployments
- Run database migrations automatically
- Perform smoke tests after deployment

## Dependency Security

**MANDATORY: Security practices**
- Run `uv lock` after adding dependencies
- Review dependency licenses before adding
- Use `pip-audit` or `safety` to check for vulnerabilities
- Update dependencies monthly and test thoroughly
- Pin exact versions in `uv.lock`
- Avoid dependencies with known security issues
- Review dependency tree for unexpected packages
- Use dependabot or similar for automated security updates

## Environment Management

**MANDATORY: Environment separation**
- Maintain separate configurations for: development, staging, production
- Use environment-specific `.env` files (`.env.dev`, `.env.staging`, `.env.prod`)
- NEVER use production credentials in development
- Use different databases for each environment
- Test migrations in staging before production
- Use feature flags for gradual rollouts
- Implement blue-green or canary deployments
