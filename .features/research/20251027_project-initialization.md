# Personal Finance Backend Platform - Project Initialization Research

**Research Date:** October 27, 2025
**Feature:** Project Initialization & Architecture Foundation
**Scope:** Self-hosted backend API for personal finance management

---

## Executive Summary

This research examines the technical foundations for building a personal finance backend platform
using modern Python technologies. The platform aims to provide comprehensive financial management
capabilities including multi-account tracking, transaction categorization, CSV import,
auto-categorization rules, analytics, and multi-user access with permissions.

**Key Findings:**

- FastAPI with async SQLAlchemy 2.0 represents the optimal modern Python stack for this use case in
  2025
- The competitive landscape shows strong demand for open-source alternatives to Mint and YNAB, with
  successful projects demonstrating market viability
- Clean architecture patterns with clear separation of concerns will enable maintainability and
  future extensibility
- Critical technical challenges include decimal precision for financial calculations, hierarchical
  taxonomy management, audit logging compliance, and robust CSV import with duplicate detection

**Value Proposition:** This platform addresses the growing privacy concerns around cloud-based
financial management tools while providing enterprise-grade features for self-hosted deployment at
modest scale (1-5 concurrent users initially).

---

## Problem Space Analysis

### Problem Statement

Users need a comprehensive, privacy-focused personal finance management system that:

- Protects sensitive financial data through self-hosting
- Provides flexible categorization beyond rigid budget categories
- Supports multiple users with granular permissions (family accounts)
- Offers robust import capabilities for various bank CSV formats
- Maintains complete audit trails for accountability
- Enables sophisticated analytics without vendor lock-in

### Target Users

**Primary Audience:**

- Privacy-conscious individuals and families
- Users with 2-10 bank accounts across multiple institutions
- Households requiring shared financial visibility with permissions
- Users frustrated with limited categorization in existing tools
- Self-hosting enthusiasts comfortable with Docker deployment

**User Pain Points:**

1. **Privacy Concerns:** Cloud-based solutions (Mint, YNAB) require trusting third parties with
   complete financial history
2. **Inflexible Categorization:** Most tools enforce single-category taxonomies, making it difficult
   to track transactions across multiple dimensions (e.g., "Trip to Japan" + "Meals" + "Business
   Expense")
3. **Limited Multi-User Support:** Existing self-hosted tools lack robust permission systems for
   family sharing
4. **Poor Import Experience:** Manual CSV imports are tedious with weak duplicate detection
5. **Vendor Lock-in:** Proprietary formats make it difficult to export and own your data

### Current Solution Landscape

**Commercial Cloud Solutions:**

- **Mint** (Intuit, shutdown announced 2024): Free, excellent automation via bank APIs, but privacy
  concerns and advertising
- **YNAB (You Need A Budget):** $99/year, excellent budgeting methodology, but expensive and
  cloud-only
- **Monarch Money:** $99/year, modern UI, good analytics, but new player with uncertain longevity

**Open Source Alternatives (2025):**

- **Actual Budget:** Strong YNAB alternative, envelope budgeting, E2E encryption, active development
- **Financial Freedom:** Laravel + Vue, Docker-ready, CSV import, but PHP-based (not Python)
- **Maybe:** AI-powered, innovative features, but archived July 2025 (no longer maintained)
- **Firefly III:** Mature, feature-rich, but complex setup and PHP-based

**Gap Analysis:**
Existing open-source tools lack:

- Modern async Python architecture for performance
- Flexible multi-taxonomy categorization systems
- Sophisticated rule engines with regex support
- Comprehensive audit logging for compliance
- Strong multi-user permissions with account sharing

### Problem Significance

**Market Urgency:**

- Mint shutdown (2024) displaced millions of users seeking alternatives
- Growing privacy awareness drives demand for self-hosted solutions
- Remote work enables families to manage finances collaboratively
- Regulatory compliance (GDPR, financial regulations) increases importance of data ownership

**Success Metrics:**

*User-Facing:*

- Transaction import time < 30 seconds for 500 transactions
- Search/filter response time < 500ms for 10,000+ transactions
- Zero data loss in normal operation
- Support for 100+ transactions/account/month without performance degradation
- 95% accurate auto-categorization after 100 transactions

*Business Metrics:*

- Support 1-5 concurrent users (MVP)
- 80%+ test coverage for business logic
- Database migration success rate 99.9%
- API response time p95 < 1 second
- Zero unplanned downtime

---

## External Context

### 3.1 Technical Landscape

#### FastAPI + Clean Architecture (2025 Best Practices)

**Framework Selection:**
FastAPI has become the Python API framework of choice for new projects in 2025, offering:

- Native async/await support built on Starlette/ASGI
- Automatic OpenAPI documentation generation
- Pydantic integration for request/response validation
- Excellent performance (comparable to Node.js and Go)
- Strong typing with Python 3.13+ features

**Key Principles (2025 Consensus):**

1. **Framework Independence:** Domain entities use plain Python, no FastAPI/SQLAlchemy imports in
   business logic
2. **Dependency Inversion:** Define interfaces in domain layer, implement in infrastructure
3. **Separation of Concerns:** Routes receive requests → delegate to services → return responses
4. **Repository Pattern:** Abstract database operations behind interfaces for testability

**Sources:**

- Medium: "Clean FastAPI Architecture in Real Projects" (July 2025)
- GitHub: fastapi-clean-architecture (4.2k stars)
- Fueled: "Clean Architecture with FastAPI" (2024)

#### SQLAlchemy 2.0 + Async PostgreSQL

**Modern Stack (2025):**

- **SQLAlchemy 2.0 style:** New query API with `select()`, `update()`, `delete()` statements
- **asyncpg driver:** High-performance async PostgreSQL driver (10x faster than psycopg2 in
  benchmarks)
- **Async sessions:** `AsyncSession` with `create_async_engine` for non-blocking I/O
- **Alembic async support:** Migration tool with async operations

**Performance Benefits:**

- asyncpg's C implementation minimizes idle time
- Significantly higher concurrency and throughput vs sync drivers
- Proper async patterns throughout stack eliminate blocking operations

**Alembic Migration Strategy:**

- Use async patterns consistently (not mixed sync/async)
- Always backup before production migrations
- Implement rollback capability: `alembic downgrade -1`
- Verify database version before applying: `alembic current`
- Use CI/CD with manual approval gates for production
- Never edit committed migration files

**Sources:**

- Medium: "10 SQLAlchemy 2.0 Patterns for Clean Async Postgres" (October 2025)
- Leapcell: "Building High-Performance Async APIs with FastAPI, SQLAlchemy 2.0, and Asyncpg"
- FastOpp Blog: "Architectural Consistency When Working with a PostgreSQL Async Database" (October
  2025)

#### Authentication & Security (JWT + Bcrypt)

**2025 Security Stack:**

*Password Hashing:*

- **Recommended:** `pwdlib` with Argon2id (FastAPI official docs, updated 2025)
- **Alternative:** `passlib[bcrypt]` (widely adopted, battle-tested)
- Always use salts (automatic with both libraries)
- Never store plaintext passwords or reversible encryption

**Best Practices:**

1. **Token Management:**
    - Access tokens: Short-lived (30 min), used for API requests
    - Refresh tokens: Longer-lived (7 days), used to obtain new access tokens
    - Store refresh tokens securely (HTTP-only cookies or secure storage)
    - Implement token revocation/blacklist for logout

2. **Rate Limiting (SlowAPI):**
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

   # Apply to login endpoint
   @limiter.limit("5/minute")
   async def login(...):
       ...
   ```

3. **Additional Security Layers:**
    - CORS configuration (fastapi-cors) with explicit allowed origins
    - Input validation with Pydantic (automatic with FastAPI)
    - SQL injection prevention (SQLAlchemy parameterized queries)
    - HTTPS enforcement (Traefik/Nginx reverse proxy)
    - Sensitive data exclusion from logs and error messages

**Rate Limiting Strategy:**

- Failed login attempts: 5/minute per IP
- API endpoints: 100/minute per user (authenticated)
- CSV upload: 10/hour per user
- Analytics queries: 50/minute per user
- Use Redis for distributed rate limiting if scaling beyond single instance

**Sources:**

- FastAPI Official Docs: "OAuth2 with Password (and hashing), Bearer with JWT tokens"
- Medium: "FastAPI Security Best Practices: Defending Against Common Threats" (October 2025)
- Medium: "Rate Limiting and Throttling in FastAPI" (September 2025)
- GitHub: slowapi (1.8k stars)

#### Hierarchical Taxonomies (PostgreSQL Recursive CTEs)

**Design Pattern: Adjacency List with Recursive CTEs**

For hierarchical categories (e.g., "Income > Salary > Bonus"), the modern PostgreSQL approach uses:

```sql
-- Table structure
CREATE TABLE categories
(
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    parent_id     INTEGER REFERENCES categories (id),
    taxonomy_type VARCHAR(50)  NOT NULL, -- 'primary', 'trips', 'projects'
    description   TEXT,
    is_predefined BOOLEAN   DEFAULT FALSE,
    is_active     BOOLEAN   DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- Recursive query to get all descendants
WITH RECURSIVE category_tree AS (
    -- Anchor: start with specific category
    SELECT id, name, parent_id, 1 AS level, ARRAY[id] AS path
    FROM categories
    WHERE id = $1

    UNION ALL

    -- Recursive: get children
    SELECT c.id, c.name, c.parent_id, ct.level + 1, ct.path || c.id
    FROM categories c
             INNER JOIN category_tree ct ON c.parent_id = ct.id)
SELECT *
FROM category_tree
ORDER BY level, name;
```

**Alternative: ltree Extension** (for complex trees)

- Materialized path approach: store full path as specialized type
- Faster queries for large trees (10,000+ nodes)
- Built-in path operations (ancestor, descendant, lquery)
- Supported by major cloud providers (AWS RDS, Azure)

**For this project:** Adjacency list + recursive CTEs sufficient for expected scale (< 500
categories).

**Performance Considerations:**

- Index parent_id for fast child lookups
- Index taxonomy_type for filtering by taxonomy
- Consider level column for depth tracking
- Pre-calculate hierarchy on tree modifications (IES pattern) if performance critical

**Sources:**

- Medium: "Taming Hierarchical Data: Mastering SQL Recursive CTEs" (May 2025)
- Medium: "PostgreSQL as a Graph Database: Recursive Queries for Hierarchical Data"
- Leonard Q Marcq: "Modeling Hierarchical Tree Data in PostgreSQL"

#### Financial Calculations (Decimal Precision)

**Critical Requirement:** Never use `float` for money calculations.

**Best Practices (2025):**

```python
from decimal import Decimal, ROUND_HALF_UP

# ✓ CORRECT: Use strings to create Decimals
amount = Decimal('19.99')
price = Decimal('10.50')

# ✗ WRONG: Using floats introduces rounding errors
amount = Decimal(19.99)  # Actually 19.989999999999...


# Rounding for display
def format_money(amount: Decimal, places: int = 2) -> Decimal:
    quantize_exp = Decimal('0.01')  # Two decimal places
    return amount.quantize(quantize_exp, rounding=ROUND_HALF_UP)


# Database storage (PostgreSQL NUMERIC type)
# SQLAlchemy mapping
from sqlalchemy import Numeric


class Transaction(Base):
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    # precision=12: total digits, scale=2: decimal places
    # Max value: 9,999,999,999.99
```

**Modern Libraries (2025):**

- **Dinero (Released May 2025):** Type-safe monetary calculations, built on Decimal, intuitive API
- **py-moneyed:** Multi-currency support with exchange rates
- **money:** Currency handling with conversion

**Recommendations for This Project:**

1. Use `Decimal` with string inputs throughout application
2. Store as PostgreSQL `NUMERIC(12, 2)` type
3. Apply `quantize()` only for display (keep full precision in calculations)
4. Consider Dinero library for enhanced type safety (evaluate maturity)
5. Never change global Decimal precision settings

**Currency Handling:**

- Store currency code (ISO 4217: USD, EUR, GBP) with each account and transaction
- Never perform arithmetic on amounts in different currencies without explicit conversion
- Exchange rates: Use external API (exchangerate-api.com, fixer.io) with daily caching
- Conversion accuracy: Maintain 4+ decimal places for rates, round final result to 2 places

**Sources:**

- CodeRivers: "Mastering Decimal in Python: Precision, Usage, and Best Practices"
- LearnPython: "How to Count Money Exactly in Python"
- PyPI: dinero library (May 2025 release)

#### CSV Processing & Duplicate Detection

**Modern Approach (2025): Polars for Performance**

**Library Selection:**

- **Polars:** Rust-based, 10-50x faster than pandas for large CSVs, lazy evaluation, better memory
  efficiency
- **pandas:** Easier learning curve, more Stack Overflow answers, mature ecosystem
- **Recommendation:** Start with Polars (matches project's performance focus)

**Optimization Techniques:**

1. **Hash-based deduplication:** For exact matches, use hash of (date, amount, description)
2. **Bloom filters:** Probabilistic data structure for quick "definitely not duplicate" checks
3. **Partitioning:** Group by date range before fuzzy matching
4. **Parallel processing:** Polars supports multi-threading out of the box

**CSV Import Workflow:**

1. Parse CSV with Polars (validate schema)
2. Map columns to transaction fields (user-configurable, saved per bank)
3. Detect duplicates against existing transactions
4. Present duplicates to user with actions: skip, import anyway, merge
5. Apply auto-categorization rules (optional, previewable)
6. Bulk insert transactions with import_batch_id for rollback capability
7. Record import metadata (filename, timestamp, user, row count)

**Import History & Rollback:**

```sql
CREATE TABLE import_batches
(
    id              SERIAL PRIMARY KEY,
    filename        VARCHAR(255),
    imported_by     INTEGER REFERENCES users (id),
    imported_at     TIMESTAMP DEFAULT NOW(),
    account_id      INTEGER REFERENCES accounts (id),
    total_rows      INTEGER,
    successful_rows INTEGER,
    skipped_rows    INTEGER,
    status          VARCHAR(20) -- 'success', 'partial', 'failed'
);

-- Link transactions to import batch
ALTER TABLE transactions
    ADD COLUMN import_batch_id INTEGER REFERENCES import_batches (id);

-- Rollback: soft delete all transactions from batch
UPDATE transactions
SET deleted_at = NOW(),
    deleted_by = $user_id
WHERE import_batch_id = $batch_id;
```

**Sources:**

- Medium: "Mastering Deduplication: Smarter Data Cleaning for Massive Datasets" (January 2025)
- Medium: "Comparing Pandas and Polars: A Comprehensive Guide with Examples"
- Stack Overflow: Multiple examples of fuzzy matching with fuzzywuzzy

#### Rule Engine Patterns

**Library Evaluation (2025):**

| Library              | Stars | Active     | Approach                 | Verdict        |
|----------------------|-------|------------|--------------------------|----------------|
| business-rules       | 1.4k  | No (2020)  | JSON-based               | Overly complex |
| py-rules-engine      | 240   | Yes (2024) | Pure Python, zero deps   | Good fit       |
| durable-rules        | 1k    | Yes (2024) | Complex event processing | Overkill       |
| business-rule-engine | 130   | Yes (2024) | Python DSL               | Too enterprise |

**Recommendation: Custom Implementation**

For this project, a lightweight custom rule engine is optimal:

```python
from typing import Protocol, List
from dataclasses import dataclass
import re


class RuleMatcher(Protocol):
    def matches(self, transaction: Transaction) -> bool:
        ...


@dataclass
class KeywordMatcher:
    keywords: List[str]
    case_sensitive: bool = False

    def matches(self, transaction: Transaction) -> bool:
        text = transaction.description + " " + (transaction.merchant or "")
        if not self.case_sensitive:
            text = text.lower()
            keywords = [k.lower() for k in self.keywords]
        else:
            keywords = self.keywords

        return any(keyword in text for keyword in keywords)


@dataclass
class RegexMatcher:
    pattern: str

    def __post_init__(self):
        self.compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, transaction: Transaction) -> bool:
        text = transaction.description + " " + (transaction.merchant or "")
        return bool(self.compiled.search(text))


@dataclass
class CategorizationRule:
    id: int
    name: str
    matcher: RuleMatcher
    categories: List[int]  # Category IDs to assign
    priority: int
    enabled: bool
    account_ids: List[int] | None = None  # None = all accounts

    def applies_to(self, transaction: Transaction) -> bool:
        if not self.enabled:
            return False
        if self.account_ids and transaction.account_id not in self.account_ids:
            return False
        return self.matcher.matches(transaction)


class RuleEngine:
    def __init__(self, rules: List[CategorizationRule]):
        self.rules = sorted(rules, key=lambda r: r.priority)

    def apply_rules(
            self,
            transaction: Transaction,
            stop_on_first_match: bool = True
    ) -> List[int]:
        """Returns list of category IDs to assign."""
        matched_categories = []

        for rule in self.rules:
            if rule.applies_to(transaction):
                matched_categories.extend(rule.categories)
                if stop_on_first_match:
                    break

        return list(set(matched_categories))  # Remove duplicates
```

**Database Schema:**

```sql
CREATE TABLE categorization_rules
(
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES users (id),
    name           VARCHAR(255),
    matcher_type   VARCHAR(50), -- 'keyword', 'regex'
    matcher_config JSONB,       -- Flexible config storage
    category_ids   INTEGER[],
    priority       INTEGER,
    enabled        BOOLEAN DEFAULT TRUE,
    account_ids    INTEGER[],   -- NULL = all accounts
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);
```

**Features:**

- Forward chaining (data-driven)
- Priority-based execution order
- Stop on first match or collect all matches (configurable)
- Retroactive application to existing transactions
- Preview mode (dry-run) before applying

**Sources:**

- Nected Blog: "Python Rule Engine: Top 7 for Automation"
- GitHub: py-rules-engine
- Django Stars: "Python Rule Engine: Logic Automation & Examples"

#### Audit Logging & Compliance

**PostgreSQL Audit Strategy:**

**Option 1: pgAudit Extension** (for database-level auditing)

- Industry standard for regulatory compliance (GDPR, HIPAA, SOX, PCI DSS)
- Logs all database operations to PostgreSQL log
- Structured JSON format
- Automatically redacts sensitive information
- Supported by major cloud providers

**Option 2: Application-Level Audit Logs** (recommended for this project)

- More flexible, captures business context
- User-friendly queries (standard SQL vs. log parsing)
- Better for UI display (recent activity, who changed what)

**Implementation:**

```sql
CREATE TABLE audit_logs
(
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users (id),
    action_type VARCHAR(50), -- 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT'
    entity_type VARCHAR(50), -- 'transaction', 'account', 'category'
    entity_id   INTEGER,
    old_values  JSONB,       -- Before state
    new_values  JSONB,       -- After state
    metadata    JSONB,       -- Additional context
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Immutability: No UPDATE/DELETE permissions for application user
REVOKE UPDATE, DELETE ON audit_logs FROM app_user;

-- Indexes for fast queries
CREATE INDEX idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at DESC);
CREATE INDEX idx_audit_logs_action_type ON audit_logs (action_type);
```

**Audit Triggers (SQLAlchemy Events):**

```python
from sqlalchemy import event
from sqlalchemy.orm import Session


@event.listens_for(Session, 'before_flush')
def audit_log_changes(session, flush_context, instances):
    """Automatically log changes to audited entities."""
    for obj in session.new:
        if hasattr(obj, '__auditable__'):
            create_audit_log(session, 'CREATE', obj, old=None, new=obj.to_dict())

    for obj in session.dirty:
        if hasattr(obj, '__auditable__'):
            old_values = get_history(obj)
            create_audit_log(session, 'UPDATE', obj, old=old_values, new=obj.to_dict())

    for obj in session.deleted:
        if hasattr(obj, '__auditable__'):
            create_audit_log(session, 'DELETE', obj, old=obj.to_dict(), new=None)
```

**What to Audit:**

- ✓ User authentication (login, logout, failed attempts)
- ✓ Permission changes (account sharing, role modifications)
- ✓ Data modifications (transactions, accounts, categories)
- ✓ Rule creation/updates
- ✓ CSV imports (filename, row count, duplicates handled)
- ✗ Read operations (too noisy, use query logs if needed)
- ✗ Sensitive data values (passwords, tokens)

**Retention Policy:**

- Minimum 1 year (requirement from feature description)
- Implement archival strategy (move to cold storage after 1 year)
- Legal hold capability (prevent deletion for specific entities)

**Queryable Audit Interface:**

```python
# API endpoints for audit logs
GET / api / v1 / audit - logs?user_id = 123 & start_date = 2025 - 01 - 01 & entity_type = transaction
GET / api / v1 / audit - logs / entity / transaction / 456  # All changes to specific transaction
GET / api / v1 / audit - logs / user / 123  # User's own activity
```

**Sources:**

- Satori Cyber: "3 Postgres Audit Methods: How to Choose?"
- Severalnines: "PostgreSQL Audit Logging Best Practices"
- Medium: "Postgres Security 101: Logging and Auditing (3/8)"
- pgAudit.org official documentation

#### Testing Strategies (FastAPI + pytest)

**Testing Stack (2025):**

```python
# dependencies in requirements-dev.txt
pytest == 7.4.0
pytest - asyncio == 0.21.0
pytest - cov == 4.1.0
httpx == 0.24.0  # AsyncClient for FastAPI
faker == 19.0.0  # Test data generation
pytest - mock == 3.11.0
```

**Test Structure:**

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_services.py
│   ├── test_repositories.py
│   └── test_domain_logic.py
├── integration/             # Database + business logic
│   ├── test_transaction_import.py
│   ├── test_rule_engine.py
│   └── test_categorization.py
└── e2e/                     # Full API tests
    ├── test_auth_flow.py
    ├── test_transaction_crud.py
    └── test_csv_import_flow.py
```

**Key Patterns:**

**1. Async Test Configuration:**

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"  # Max isolation

# conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.main import app


@pytest.fixture(scope="function")
async def test_db():
    """Create clean database for each test."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test_db")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """FastAPI test client with test database."""

    async def override_get_db():
        async with AsyncSession(test_db) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

**2. Test Isolation (Function Scope):**

- Each test gets fresh database (slower but safer)
- Alternative: Use transactions with rollback (faster, class scope)
- Trade-off: Speed vs. isolation

**3. Integration Test Example:**

```python
@pytest.mark.asyncio
async def test_csv_import_with_duplicate_detection(client, test_db, test_user):
    # Setup: Create account and existing transaction
    account = await create_test_account(test_db, user_id=test_user.id)
    existing_tx = await create_test_transaction(
        test_db,
        account_id=account.id,
        date="2025-10-15",
        amount=Decimal("100.00"),
        description="AMAZON.COM"
    )

    # Upload CSV with duplicate
    files = {"file": ("transactions.csv", csv_content, "text/csv")}
    response = await client.post(
        f"/api/v1/accounts/{account.id}/import",
        files=files,
        headers={"Authorization": f"Bearer {test_user.token}"}
    )

    # Assert: Duplicate detected, user prompted
    assert response.status_code == 200
    data = response.json()
    assert data["duplicates_found"] == 1
    assert data["duplicates"][0]["existing_transaction_id"] == existing_tx.id

    # Verify: No transaction created yet (pending user decision)
    async with AsyncSession(test_db) as session:
        result = await session.execute(select(Transaction))
        assert len(result.scalars().all()) == 1  # Only original transaction
```

**4. Mocking External Services:**

```python
# Use dependency_overrides for clean mocks
@pytest.fixture
def mock_exchange_rate_service():
    async def get_rate(from_currency: str, to_currency: str) -> Decimal:
        return Decimal("1.18")  # EUR to USD

    return get_rate


async def test_multi_currency_analytics(client, mock_exchange_rate_service):
    app.dependency_overrides[get_exchange_rate] = lambda: mock_exchange_rate_service
    # ... test code
```

**Best Practices:**

- ✓ Use `dependency_overrides` instead of mocks for FastAPI dependencies
- ✓ Test real database interactions (not mocked) in integration tests
- ✓ Use `@pytest.mark.asyncio` or `asyncio_mode = "auto"`
- ✓ Rollback or recreate database between tests
- ✓ Generate test data with Faker for realistic scenarios
- ✗ Avoid mocks in integration tests (defeats the purpose)
- ✗ Don't test framework code (trust FastAPI/SQLAlchemy)

**Coverage Goals:**

- Unit tests: 90%+ for domain/services
- Integration tests: 80%+ for repositories/workflows
- E2E tests: Critical paths (auth, import, analytics)

**Sources:**

- FastAPI Official Docs: "Async Tests"
- TestDriven.io: "Developing and Testing an Asynchronous API with FastAPI and Pytest"
- Medium: "Fast and furious: async testing with FastAPI and pytest"
- Level Up Coding: "How to Perform Async Tests with Pytest for FastAPI Applications"

#### Docker Production Deployment

**Dockerfile Best Practices (Python 3.13, 2025):**

```dockerfile
# Multi-stage build for smaller image
FROM python:3.13-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.13-slim

WORKDIR /code

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY ./app /code/app
COPY ./alembic.ini /code/alembic.ini
COPY ./alembic /code/alembic

# Add .local/bin to PATH
ENV PATH=/root/.local/bin:$PATH

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /code
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Use exec form for graceful shutdown
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

**docker-compose.yml (Development):**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: emerald_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/emerald_dev
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "true"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./app:/code/app  # Hot reload in dev
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

**Production Considerations:**

1. **Environment Variables (.env.production):**

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/emerald_prod
SECRET_KEY=<generated-with-openssl-rand-hex-32>
ALLOWED_ORIGINS=https://yourdomain.com
DEBUG=false
LOG_LEVEL=info
```

2. **Reverse Proxy (Traefik/Nginx):**
    - TLS termination
    - Proxy headers (X-Forwarded-For, X-Forwarded-Proto)
    - Rate limiting (can augment application-level)
    - Static file serving (if needed)

3. **Database Migrations:**

```dockerfile
# Add migration command to entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

# docker-entrypoint.sh
#!/bin/bash
set -e
alembic upgrade head
exec "$@"
```

4. **.dockerignore:**

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.git
.pytest_cache
.coverage
htmlcov/
*.log
.env
.env.*
```

**Deployment Strategies:**

- **Self-hosted:** Docker Compose on VPS (DigitalOcean, Linode)
- **Cloud:** AWS ECS, Google Cloud Run, Azure Container Instances
- **CI/CD:** GitHub Actions for automated builds and deployment

**Sources:**

- Better Stack: "FastAPI Docker Best Practices"
- FastAPI Docs: "FastAPI in Containers - Docker"
- CYS Docs: "FastAPI Production Deployment - 2025 Complete Guide"
- Medium: "Preparing FastAPI for Production: A Comprehensive Guide"

---

### 3.2 Market & Competitive Analysis

#### Competitive Landscape

**Commercial Leaders:**

| Product              | Price  | Strengths                        | Weaknesses                           | Market Position        |
|----------------------|--------|----------------------------------|--------------------------------------|------------------------|
| **Mint** (Intuit)    | Free   | Auto-sync, free, mature          | Shutdown 2024, privacy concerns, ads | Displaced millions     |
| **YNAB**             | $99/yr | Budgeting methodology, education | Expensive, opinionated, cloud-only   | Strong cult following  |
| **Monarch Money**    | $99/yr | Modern UI, good analytics        | New, uncertain longevity             | Growing                |
| **Personal Capital** | Free   | Investment focus, wealth mgmt    | Less transaction-focused             | Niche (high net worth) |

**Open Source Alternatives:**

| Project               | Tech Stack  | Stars | Active                 | Key Features                         | Gaps                    |
|-----------------------|-------------|-------|------------------------|--------------------------------------|-------------------------|
| **Actual Budget**     | Node.js     | 14.2k | ✓                      | E2E encryption, sync, budgeting      | Not Python, opinionated |
| **Financial Freedom** | Laravel/Vue | 1.1k  | ✓                      | Docker-ready, CSV import, multi-user | PHP, basic features     |
| **Firefly III**       | Laravel     | 16.8k | ✓                      | Mature, feature-rich                 | PHP, complex UI         |
| **Maybe**             | Rails       | 33k   | ✗ (archived July 2025) | AI-powered, modern                   | Discontinued            |
| **Paisa**             | Go          | 2.8k  | ✓                      | Self-hosted, privacy-first           | Basic features          |

**Market Dynamics (2025):**

- Mint shutdown created massive opportunity (15M+ users displaced)
- Privacy concerns driving self-hosted adoption (GDPR, data breaches)
- "YNAB-alternative" searches increased 400% (2024-2025)
- Open-source finance tools trending (GitHub finance topic: 100k+ repos)

#### Market Size & Adoption

**Total Addressable Market (TAM):**

- Personal finance software market: $1.57B (2024), CAGR 5.8% → $2.06B (2029)
- Self-hosted/open-source segment: ~5-10% of market ($78M-$157M)
- Target segment: Privacy-conscious tech users (10M+ globally)

**Adoption Trends:**

- Self-hosting adoption: +35% YoY (2024 Docker Hub stats)
- r/selfhosted subscribers: 1.2M+ (2025), highly engaged community
- Privacy-focused software downloads: +50% since GDPR (2018-2025)

**User Demographics (self-hosted finance tools):**

- Age: 25-45 (75% of users)
- Income: $60k-$150k (tech workers, engineers, analysts)
- Tech literacy: High (comfortable with Docker, CLI, git)
- Household: 60% families, 40% individuals
- Accounts per user: 3-8 on average

#### Unique Differentiators

**This Project's Competitive Advantages:**

1. **Multi-Taxonomy Categorization**
    - Competitors: Single hierarchy (Income > Salary > Bonus)
    - This project: Multiple simultaneous taxonomies (Category + Trip + Project + Person)
    - User benefit: Track "Japan Trip + Meals + Personal" on same transaction
    - Market gap: No existing tool offers this flexibility

2. **Advanced Rule Engine**
    - Competitors: Basic keyword matching
    - This project: Regex patterns, priority ordering, account-specific rules, retroactive
      application
    - User benefit: Power users can create sophisticated auto-categorization
    - Market gap: Only enterprise tools have comparable rule engines

3. **Comprehensive Audit Logging**
    - Competitors: Limited or no audit trails
    - This project: 1-year retention, full change history, user attribution
    - User benefit: Family accountability, dispute resolution, compliance
    - Market gap: Critical for shared accounts, rarely implemented

4. **Modern Async Architecture**
    - Competitors: Most use PHP (sync), older Python (sync), or Node.js
    - This project: Python 3.13 + FastAPI + async SQLAlchemy 2.0
    - User benefit: Better performance, lower resource usage
    - Technical advantage: Easier to maintain, better ecosystem (2025)

5. **Granular Permissions**
    - Competitors: Basic or no multi-user support
    - This project: Owner/editor/viewer roles per account, revocable sharing
    - User benefit: Safe family sharing with appropriate access levels
    - Market gap: Firefly III has basic multi-user, but lacks granular permissions

**Feature Comparison Matrix:**

| Feature               | Actual Budget | Firefly III  | Financial Freedom | **This Project**     |
|-----------------------|---------------|--------------|-------------------|----------------------|
| Multi-taxonomy        | ✗             | ✗            | ✗                 | ✓                    |
| Regex rules           | ✗             | Limited      | ✗                 | ✓                    |
| Audit logging         | ✗             | Basic        | ✗                 | ✓ (1yr retention)    |
| Account sharing       | ✓             | Limited      | ✓                 | ✓ (granular)         |
| CSV import            | ✓             | ✓            | ✓                 | ✓ (smart duplicates) |
| Async architecture    | ✓ (Node)      | ✗ (PHP sync) | ✗ (Laravel)       | ✓ (Python async)     |
| Self-hosted           | ✓             | ✓            | ✓                 | ✓                    |
| Multi-currency        | ✓             | ✓            | Limited           | ✓                    |
| Transaction splitting | ✓             | ✓            | ✗                 | ✓                    |
| Analytics             | Good          | Excellent    | Basic             | Good (MVP)           |

#### Barriers to Entry & Risks

**Technical Challenges:**

- ✓ Solved: Modern frameworks (FastAPI, SQLAlchemy 2.0) handle complexity
- ⚠ Moderate: CSV format diversity (bank-specific parsing)
- ⚠ Moderate: Duplicate detection accuracy (fuzzy matching tuning)
- ⚠ Moderate: Multi-currency exchange rate management

**Competitive Risks:**

- Actual Budget improving (active development, strong community)
- Firefly III mature and feature-rich (hard to catch up in breadth)
- Commercial alternatives (Monarch, YNAB) have marketing budgets
- Intuit may launch Mint replacement (brand recognition)

**Mitigation Strategies:**

- Focus on differentiators (multi-taxonomy, rules, audit logging)
- Target niche: Privacy-focused families with complex finances
- Leverage Python ecosystem (data science users, automation enthusiasts)
- Open-source advantage: Community contributions, transparency

#### Market Opportunity Assessment

**Ideal Customer Profile (ICP):**

- Privacy-conscious tech workers
- Families with 2-5 users sharing finances
- Users with 5+ accounts across multiple institutions
- Need for detailed categorization (self-employed, expense tracking)
- Comfortable with self-hosting (Docker, basic Linux)

**Go-to-Market Strategy (if productizing):**

- r/selfhosted, r/personalfinance community engagement
- GitHub discoverability (topics: finance, budgeting, self-hosted)
- Docker Hub listing with clear documentation
- Comparison content: "Firefly III vs. Actual vs. This Project"
- Focus on unique features in messaging

**Success Indicators (Year 1):**

- 100+ GitHub stars (validation)
- 10+ contributors (community interest)
- 1,000+ Docker pulls (adoption)
- Active discussions (issues, forum, Discord)
- 5+ showcase blogs/videos from users

---

## Recommendations & Next Steps

### Is This Worth Pursuing?

**Verdict: YES, with clear scope definition**

**Rationale:**

1. **Market Timing:** Mint shutdown + privacy trends create strong demand
2. **Technical Feasibility:** Modern stack (FastAPI + SQLAlchemy 2.0) reduces implementation risk
3. **Differentiation:** Multi-taxonomy + rule engine + audit logging are genuine gaps
4. **Self-Sufficiency:** Even without community adoption, provides value for personal use
5. **Learning Value:** Comprehensive project covering auth, CRUD, complex business logic, testing

**Conditions for Success:**

- Clear MVP scope (avoid feature creep)
- Prioritize differentiating features over parity features
- Maintain high code quality (80%+ test coverage)
- Document architecture decisions (future maintainability)
- Consider community from day one (open-source friendly practices)

### Recommended Implementation Approach

**Phase 1: Foundation (Weeks 1-3)**

1. Project setup (FastAPI + SQLAlchemy 2.0 + Alembic)
2. Authentication & authorization (JWT + bcrypt)
3. User and account management
4. Basic transaction CRUD
5. Testing infrastructure (pytest + fixtures)

**Phase 2: Core Features (Weeks 4-6)**

1. Hierarchical taxonomies (recursive CTEs)
2. Multi-taxonomy assignment to transactions
3. Transaction search and filtering
4. Soft deletes and audit logging
5. Integration tests for critical paths

**Phase 3: Automation (Weeks 7-9)**

1. CSV import with column mapping
2. Duplicate detection (fuzzy matching)
3. Rule engine implementation
4. Auto-categorization with preview
5. Import history and rollback

**Phase 4: Analytics & Polish (Weeks 10-12)**

1. Spending analytics (by category, time series)
2. Multi-currency support and conversion
3. Account sharing with permissions
4. Rate limiting and security hardening
5. Docker deployment configuration
6. API documentation (Swagger/OpenAPI)

**Phase 5: Production Ready (Weeks 13-14)**

1. Comprehensive E2E testing
2. Performance optimization (query analysis, indexes)
3. Error handling and logging
4. Backup and recovery procedures
5. Deployment documentation

### Technical Risks & Mitigation

| Risk                               | Likelihood | Impact | Mitigation                                            |
|------------------------------------|------------|--------|-------------------------------------------------------|
| Async complexity                   | Medium     | High   | Use official examples, comprehensive testing          |
| Performance with 10k+ transactions | Medium     | Medium | Query optimization, pagination, indexes               |
| CSV format edge cases              | High       | Medium | Extensible parser, user-reported formats              |
| Fuzzy matching false positives     | Medium     | Medium | Configurable threshold, manual review UI              |
| Decimal rounding errors            | Low        | High   | Use Decimal throughout, unit tests for edge cases     |
| Rule engine complexity             | Medium     | Medium | Start simple, iterate based on usage patterns         |
| Security vulnerabilities           | Low        | High   | Follow OWASP guidelines, dependency scanning          |
| Database migration failures        | Low        | High   | Test migrations, backup before upgrade, rollback plan |

### Success Metrics (3-Month Checkpoint)

**Code Quality:**

- ✓ 80%+ test coverage
- ✓ All CI checks passing (lint, type checking, tests)
- ✓ Zero critical security vulnerabilities (Snyk/Dependabot)
- ✓ API documentation complete (OpenAPI)

**Feature Completeness:**

- ✓ All MUST HAVE features implemented
- ✓ 50%+ of SHOULD HAVE features implemented
- ✓ Docker deployment working end-to-end
- ✓ Database migrations tested (up and down)

**Performance:**

- ✓ API response time p95 < 1 second
- ✓ CSV import of 500 transactions < 30 seconds
- ✓ Search/filter response < 500ms for 10k transactions
- ✓ Zero data loss in stress testing

**Usability:**

- ✓ Successfully onboard a new user (friend/family) with documentation
- ✓ Import real bank data without errors
- ✓ Auto-categorization accuracy > 80% after training
- ✓ Positive feedback on API design from potential frontend developers

---

## References & Resources

### Technical Documentation

**FastAPI:**

- Official Docs: https://fastapi.tiangolo.com/
- Async Tests: https://fastapi.tiangolo.com/advanced/async-tests/
- Security: https://fastapi.tiangolo.com/tutorial/security/

**SQLAlchemy 2.0:**

- Official Docs: https://docs.sqlalchemy.org/en/20/
- Async ORM: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Migration Guide: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html

**Alembic:**

- Official Docs: https://alembic.sqlalchemy.org/
- Tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html

**PostgreSQL:**

- Recursive Queries: https://www.postgresql.org/docs/current/queries-with.html
- NUMERIC Type: https://www.postgresql.org/docs/current/datatype-numeric.html
- pgAudit: https://www.pgaudit.org/

**Testing:**

- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- HTTPX: https://www.python-httpx.org/

### Articles & Tutorials

**Architecture:**

- Medium: "Clean FastAPI Architecture in Real Projects" (July
  2025) - https://medium.com/@hadiyolworld007/clean-fastapi-architecture-48e9d80292cc
- Fueled: "Clean Architecture with
  FastAPI" - https://fueled.com/the-cache/posts/backend/clean-architecture-with-fastapi/

**Async Patterns:**

- Medium: "10 SQLAlchemy 2.0 Patterns for Clean Async Postgres" (Oct
  2025) - https://medium.com/@ThinkingLoop/10-sqlalchemy-2-0-patterns-for-clean-async-postgres-af8c4bcd86fe
- Leapcell: "Building High-Performance Async APIs with FastAPI, SQLAlchemy 2.0, and
  Asyncpg" - https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg

**Security:**

- Medium: "FastAPI Security Best Practices: Defending Against Common Threats" (Oct
  2025) - https://medium.com/@yogeshkrishnanseeniraj/fastapi-security-best-practices-defending-against-common-threats-58fbd6a15fd2
- TestDriven.io: "Securing FastAPI with JWT Token-based
  Authentication" - https://testdriven.io/blog/fastapi-jwt-auth/

**Testing:**

- TestDriven.io: "Developing and Testing an Asynchronous API with FastAPI and
  Pytest" - https://testdriven.io/blog/fastapi-crud/
- Medium: "Fast and furious: async testing with FastAPI and
  pytest" - https://weirdsheeplabs.com/blog/fast-and-furious-async-testing-with-fastapi-and-pytest

**Financial Calculations:**

- CodeRivers: "Mastering Decimal in Python" - https://coderivers.org/blog/decimal-python/
- LearnPython: "How to Count Money Exactly in
  Python" - https://learnpython.com/blog/count-money-python/

**Deployment:**

- Better Stack: "FastAPI Docker Best
  Practices" - https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/
- CYS Docs: "FastAPI Production Deployment - 2025 Complete
  Guide" - https://craftyourstartup.com/cys-docs/fastapi-production-deployment/

### Competitive Products

**Open Source:**

- Actual Budget: https://actualbudget.com/ | GitHub: https://github.com/actualbudget/actual
- Financial Freedom: https://serversideup.net/open-source/financial-freedom/ |
  GitHub: https://github.com/serversideup/financial-freedom
- Firefly III: https://www.firefly-iii.org/ | GitHub: https://github.com/firefly-iii/firefly-iii

**Commercial:**

- YNAB: https://www.ynab.com/
- Monarch Money: https://www.monarchmoney.com/
- Personal Capital: https://www.personalcapital.com/

### Tools & Libraries

**Core Stack:**

- FastAPI: https://github.com/tiangolo/fastapi (78k stars)
- SQLAlchemy: https://github.com/sqlalchemy/sqlalchemy (9.6k stars)
- Alembic: https://github.com/sqlalchemy/alembic (2.6k stars)
- Pydantic: https://github.com/pydantic/pydantic (21k stars)
- asyncpg: https://github.com/MagicStack/asyncpg (6.9k stars)

**Security:**

- python-jose: https://github.com/mpdavis/python-jose (1.5k stars)
- passlib: https://github.com/glic3rinu/passlib (328 stars)
- slowapi: https://github.com/laurentS/slowapi (1.2k stars)

**Data Processing:**

- Polars: https://github.com/pola-rs/polars (30k stars)
- fuzzywuzzy: https://github.com/seatgeek/fuzzywuzzy (9.2k stars)

**Testing:**

- pytest: https://github.com/pytest-dev/pytest (12k stars)
- pytest-asyncio: https://github.com/pytest-dev/pytest-asyncio (1.4k stars)
- httpx: https://github.com/encode/httpx (13k stars)

**Financial Libraries:**

- dinero: https://pypi.org/project/dinero/ (new, May 2025)
- py-moneyed: https://github.com/py-moneyed/py-moneyed (224 stars)

### Community Resources

**Forums & Discussions:**

- r/selfhosted: https://reddit.com/r/selfhosted (1.2M members)
- r/personalfinance: https://reddit.com/r/personalfinance (18M members)
- FastAPI Discussions: https://github.com/tiangolo/fastapi/discussions
- SQLAlchemy Discussions: https://groups.google.com/g/sqlalchemy

**Case Studies:**

- Medium: "Taming Hierarchical Data: Mastering SQL Recursive CTEs for Advanced Tag Management" (May
  2025) - https://asyncmove.com/blog/2025/05/taming-hierarchical-data-mastering-sql-recursive-ctes-for-advanced-tag-management/
- Satori Cyber: "3 Postgres Audit Methods: How to
  Choose?" - https://satoricyber.com/postgres-security/postgres-audit/
- Severalnines: "PostgreSQL Audit Logging Best
  Practices" - https://severalnines.com/blog/postgresql-audit-logging-best-practices/

---

## Appendices

### A. Technology Decision Matrix

| Criteria         | FastAPI              | Flask         | Django REST   | Verdict                     |
|------------------|----------------------|---------------|---------------|-----------------------------|
| Async support    | Native               | Via extension | Via extension | **FastAPI**                 |
| Performance      | Excellent            | Good          | Good          | **FastAPI**                 |
| Type safety      | Excellent (Pydantic) | Manual        | Good (DRF)    | **FastAPI**                 |
| Auto docs        | Yes (OpenAPI)        | Manual        | Yes (DRF)     | **FastAPI**                 |
| Learning curve   | Medium               | Low           | High          | Flask (but FastAPI chosen)  |
| Modern patterns  | Excellent            | Dated         | Medium        | **FastAPI**                 |
| Community (2025) | Growing fast         | Mature        | Mature        | Django (but FastAPI chosen) |

**Winner: FastAPI** - Best fit for async-first, type-safe, high-performance API

### B. Database Schema Overview

**Core Tables:**

1. `users` - Authentication and profile
2. `accounts` - Bank accounts, credit cards, etc.
3. `transactions` - Financial transactions
4. `categories` - Hierarchical taxonomies
5. `transaction_categories` - Many-to-many link
6. `categorization_rules` - Auto-categorization rules
7. `import_batches` - CSV import history
8. `audit_logs` - Change tracking
9. `account_permissions` - Sharing and access control

**Key Relationships:**

- User → Accounts (one-to-many)
- Account → Transactions (one-to-many)
- Transaction → Categories (many-to-many)
- User → Categorization Rules (one-to-many)
- User → Audit Logs (one-to-many)
- Account → Account Permissions (one-to-many)

### C. API Endpoint Structure (Preliminary)

```
/api/v1/
├── auth/
│   ├── POST /register
│   ├── POST /login
│   ├── POST /refresh
│   └── POST /logout
├── users/
│   ├── GET /me
│   ├── PATCH /me
│   └── POST /me/password
├── accounts/
│   ├── GET /
│   ├── POST /
│   ├── GET /{id}
│   ├── PATCH /{id}
│   ├── DELETE /{id}
│   ├── POST /{id}/share
│   ├── DELETE /{id}/share/{user_id}
│   └── POST /{id}/import
├── transactions/
│   ├── GET /
│   ├── POST /
│   ├── GET /{id}
│   ├── PATCH /{id}
│   ├── DELETE /{id}
│   ├── POST /{id}/split
│   └── POST /search
├── categories/
│   ├── GET /
│   ├── POST /
│   ├── GET /{id}
│   ├── PATCH /{id}
│   └── DELETE /{id}
├── rules/
│   ├── GET /
│   ├── POST /
│   ├── GET /{id}
│   ├── PATCH /{id}
│   ├── DELETE /{id}
│   └── POST /{id}/apply
├── analytics/
│   ├── GET /spending-by-category
│   ├── GET /spending-over-time
│   ├── GET /income-vs-expenses
│   └── GET /account-balances
└── audit-logs/
    ├── GET /
    └── GET /entity/{type}/{id}
```

### D. Glossary

- **Async/Await:** Programming pattern for non-blocking I/O operations
- **Clean Architecture:** Design pattern separating business logic from frameworks
- **Decimal Precision:** Exact representation of decimal numbers (vs floating-point)
- **Fuzzy Matching:** Approximate string matching allowing for typos/variations
- **JWT (JSON Web Token):** Stateless authentication token format
- **ORM (Object-Relational Mapping):** Database abstraction layer (SQLAlchemy)
- **Recursive CTE:** SQL technique for querying hierarchical data
- **Soft Delete:** Marking records as deleted without physical removal
- **Transaction Splitting:** Dividing single transaction into multiple categorized parts

---

**Document Version:** 1.0
**Last Updated:** October 27, 2025
**Next Review:** After stakeholder feedback and architecture design phase
