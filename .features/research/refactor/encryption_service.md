# Research: Encryption Service Refactoring

## Executive Summary

The Emerald Backend project currently has an `encryption_service.py` file located in `src/services/` that handles sensitive data encryption (IBAN, card numbers, etc.) using Fernet symmetric encryption. This service is a **generic, reusable utility** with no project-specific business logic or dependencies on other services, making its current placement architecturally inconsistent with the layered architecture principles adopted by the project.

**Key Findings:**

1. **Architectural Misalignment**: The encryption service is a technical infrastructure concern, not a business logic service, yet it's placed alongside domain services like `AuthService`, `AccountService`, and `TransactionService`.

2. **Recommended Action**: **Move the encryption service to `src/core/`** alongside `security.py`, where other security-related utilities (password hashing, JWT management) already reside. This is the most pragmatic and architecturally sound option.

3. **Primary Value Proposition**: Proper organization improves code maintainability, aligns with industry best practices for layered architectures, and makes the codebase more intuitive for developers familiar with FastAPI/Python conventions.

---

## 1. Problem Space Analysis

### 1.1 What Problem Does This Refactoring Solve?

**Current State Issues:**

- **Conceptual Misalignment**: The `src/services/` directory is designated for **business logic services** that orchestrate repositories, coordinate transactions, and implement domain-specific rules. The encryption service contains none of these characteristics.

- **Developer Confusion**: New developers (or AI agents) examining the codebase might expect all services in `src/services/` to follow similar patterns (dependency injection with database sessions, repository coordination, audit logging). The encryption service breaks these expectations.

- **Reusability Ambiguity**: The encryption service is a pure utility that could theoretically be extracted and used in other Python projects. Its current location doesn't signal this reusability.

- **Inconsistent Security Utilities**: Security-related utilities are split between `src/core/security.py` (password hashing, JWT) and `src/services/encryption_service.py` (data encryption), creating an inconsistent organization pattern.

### 1.2 Who Experiences This Problem?

**Target Audience:**

- **Backend Developers**: Those maintaining or extending the Emerald Backend codebase who need to quickly understand architectural patterns and locate relevant code.

- **New Team Members**: Developers onboarding to the project who rely on intuitive folder structures to understand separation of concerns.

- **Future Maintainers**: Developers tasked with refactoring, testing, or extracting components for reuse in other projects.

- **AI Development Assistants**: Tools like Claude Code that rely on architectural patterns and conventions to provide accurate recommendations.

### 1.3 Current State of Solutions

**Existing Pattern in the Codebase:**

The Emerald Backend currently follows a **strict 3-layer architecture**:

```
┌─────────────────────────────────────────┐
│  API Layer (src/api/routes/)            │
│  - HTTP request/response handling       │
│  - NO business logic or database ops    │
└─────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Service Layer (src/services/)          │
│  - ALL business logic                   │
│  - Transaction coordination             │
│  - Orchestration between repositories   │
│  - NO HTTP concerns or direct DB        │
└─────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Repository Layer (src/repositories/)   │
│  - ALL database operations (CRUD)       │
│  - NO business logic                    │
└─────────────────────────────────────────┘
```

**Existing Core Layer (`src/core/`):**

The `core/` directory currently contains:
- `config.py` - Application configuration (Pydantic settings)
- `security.py` - Security utilities (Argon2id password hashing, JWT creation/validation, refresh token hashing)
- `database.py` - Database session management and connection pooling
- `logging.py` - Structured logging configuration

**Current Services in `src/services/`:**

| Service | Purpose | Dependencies |
|---------|---------|--------------|
| `auth_service.py` | User registration, login, token management | UserRepository, RefreshTokenRepository, AuditService |
| `user_service.py` | User CRUD operations | UserRepository, AuditService |
| `account_service.py` | Account management | AccountRepository, AccountTypeRepository, EncryptionService |
| `transaction_service.py` | Transaction operations | TransactionRepository, AccountRepository |
| `card_service.py` | Card management | CardRepository, AccountRepository, EncryptionService |
| `audit_service.py` | Audit logging | AuditLogRepository |
| `encryption_service.py` | **Data encryption/decryption** | **None (only settings.secret_key)** |
| `currency_service.py` | ISO 4217 currency data | **None (singleton with static data)** |

**Key Observation**: Both `encryption_service.py` and `currency_service.py` are **stateless utilities** with no database dependencies, unlike all other services.

### 1.4 Pain Points with Current Approach

1. **Violation of Single Responsibility Principle**: The `services/` directory mixes domain orchestration services with technical utilities.

2. **Import Inconsistency**: Services import encryption from `src.services.encryption_service` while they import security utilities from `src.core.security`.

3. **Testing Complexity**: Unit tests must mock database sessions for most services, but not for encryption service, creating inconsistent test patterns.

4. **Circular Dependency Risk**: As the project grows, having infrastructure concerns in the service layer increases the risk of circular imports.

### 1.5 Problem Significance and Urgency

**Significance:**

- **Medium**: This is a refactoring task that improves code organization but doesn't fix a critical bug or add new features.
- The issue will compound as the codebase grows and more services are added.
- Early refactoring (Phase 1.2) is less disruptive than refactoring in later phases.

**Urgency:**

- **Low to Medium**: Not blocking current development, but addressing it now prevents future technical debt.
- Current usage is limited to 2 services (`account_service.py` and `card_service.py`), making refactoring relatively straightforward.

### 1.6 Success Metrics

**User-Facing Metrics:**

- Developers can locate security-related utilities (password hashing, JWT, encryption) in a single logical location (`src/core/`)
- New contributors understand the distinction between domain services and infrastructure utilities within 1 review of the folder structure

**Technical Metrics:**

- All imports of encryption service come from `src.core.encryption` (or similar)
- Service layer (`src/services/`) contains only classes that depend on repositories
- Test patterns are consistent: services with database operations use session fixtures, core utilities don't

---

## 2. External Context

### 2.1 Technical Landscape

#### 2.1.1 FastAPI Layered Architecture Best Practices (2025)

**Industry Standards:**

Based on comprehensive research of current FastAPI best practices, the consensus for 2025 is:

1. **Layered Architecture is Mandatory for Production**:
   - [Building Production-Ready FastAPI Applications (Oct 2025)](https://medium.com/@abhinav.dobhal/building-production-ready-fastapi-applications-with-service-layer-architecture-in-2025-f3af8a6ac563) emphasizes that "building scalable, maintainable FastAPI applications requires adopting layered architecture with a service layer as essential rather than optional."

2. **Separation of Concerns**:
   - [FastAPI for Scalable Microservices](https://webandcrafts.com/blog/fastapi-scalable-microservices) recommends "organizing code into distinct layers (API, data access, and business logic) which creates modularity and makes every layer evolve independently."

3. **Service Layer Responsibilities**:
   - The service layer is the "heart of the application, containing all business logic and transaction management" ([DEV Community - Layered Architecture](https://dev.to/markoulis/layered-architecture-dependency-injection-a-recipe-for-clean-and-testable-fastapi-code-3ioo))

4. **Core vs Infrastructure Distinction**:
   - The `core/` directory typically contains "application settings, configuration files (config.py), and security utilities (security.py)" ([How to Structure FastAPI Projects](https://medium.com/@amirm.lavasani/how-to-structure-your-fastapi-projects-0219a6600a8f))
   - Core contains "core functionality such as application configurations and security utilities"

#### 2.1.2 Python Project Structure Standards

**Core vs Utils vs Common vs Services:**

Research into Python project organization patterns reveals:

1. **Core Directory Purpose** ([Hitchhiker's Guide to Python](https://docs.python-guide.org/writing/structure/)):
   - Contains "business logic that is reusable across services"
   - Houses "core logic" that is fundamental to the application

2. **Utils Directory Purpose** ([Python Project Best Practices](https://dagster.io/blog/python-project-best-practices)):
   - For "tiny helpers like logging, timers, and similar utility functions"
   - Generic helper functions without business logic

3. **Services Directory Purpose**:
   - Contains "service layer logic that coordinates business logic and external interactions"
   - Implements use cases and orchestrates repositories

**Recommended Structure for Enterprise Python Projects:**

```
project/
├── src/
│   ├── core/              # Core configurations & security
│   │   ├── config.py
│   │   ├── security.py
│   │   └── encryption.py  # ← Encryption utilities belong here
│   ├── domain/            # Business entities (models)
│   ├── services/          # Business logic orchestration
│   ├── repositories/      # Data access layer
│   ├── api/              # API routes
│   └── main.py
```

#### 2.1.3 Encryption Service Placement in Clean/Hexagonal Architecture

**Domain-Driven Design Principles:**

Research into DDD and clean architecture patterns provides clear guidance:

1. **Infrastructure vs Domain Concerns** ([Dan Does Code - Clean Architecture Layers](https://www.dandoescode.com/blog/unpacking-the-layers-of-clean-architecture-domain-application-and-infrastructure-services)):
   - "Infrastructure services typically talk to external resources and are not part of the primary problem domain"
   - Test: "If you remove this service, will it affect the execution of the domain model? If it affects the domain model, it's probably a Domain Service; if it simply affects the application, then it is probably an Infrastructure Service"

2. **Encryption as Infrastructure Concern** ([Domain Application Infrastructure Services Pattern](https://badia-kharroubi.gitbooks.io/microservices-architecture/content/patterns/tactical-patterns/domain-application-infrastructure-services-pattern.html)):
   - Infrastructure services handle "cross-cutting concerns like emailing and logging"
   - "Infrastructure Services are operations that fulfill infrastructure concerns"

3. **Placement in Layered Architecture** ([Layered Architecture in DDD](https://www.tony.lat/layered-architecture-in-domain-driven-design)):
   - Infrastructure layer "provides technical services such as persistence, messaging, and security"
   - Contains "loggers, cryptography utilities, search engines"

**Verdict**: Encryption is definitively an **infrastructure/technical concern**, not a domain service.

#### 2.1.4 Fernet Cryptography Best Practices

**Key Management and Architecture Patterns:**

1. **Key Management Best Practices** ([Fernet in Python: Comprehensive Guide](https://coderivers.org/blog/fernet-python/)):
   - Always use `Fernet.generate_key()` for cryptographically secure keys
   - Store keys in environment variables: `os.environ.get('FERNET_KEY')` rather than hardcoding
   - Consider secrets management tools like HashiCorp Vault for production

2. **Key Rotation** ([Cryptography.io Fernet Documentation](https://cryptography.io/en/latest/fernet/)):
   - "Token rotation is a best practice and manner of cryptographic hygiene"
   - Use `MultiFernet.rotate()` to support multiple keys during rotation periods

3. **SQLAlchemy Integration Pattern** ([Encryption at Rest with SQLAlchemy](https://blog.miguelgrinberg.com/post/encryption-at-rest-with-sqlalchemy)):
   - Miguel Grinberg (Flask creator) recommends creating a **custom SQLAlchemy type** that wraps Fernet
   - Encryption service should be a **utility layer** separate from ORM models
   - "Fernet is ideal for encrypting data that easily fits in memory"

4. **2025 Security Trends** ([Architectural Patterns for Securing Data](https://www.glukhov.org/post/2025/11/securing-information-at-rest-in-transit-at-runtime/)):
   - Transparent Data Encryption (TDE) uses two-tier key architecture
   - Best practices include "encrypting sensitive data at rest and in transit, and rotating keys"
   - Quantum-resistant cryptography (CRYSTALS-Kyber, CRYSTALS-Dilithium) emerging for future-proofing

**Current Implementation Analysis:**

The Emerald Backend's `EncryptionService` follows most best practices:
- ✅ Uses Fernet (AES-128-CBC + HMAC) for authenticated encryption
- ✅ Derives key from `SECRET_KEY` using PBKDF2-HMAC-SHA256 with 100,000 iterations
- ✅ Provides simple encrypt/decrypt interface
- ⚠️ Uses static salt (acceptable for single-tenant applications, could be enhanced with per-record salts for multi-tenant)
- ⚠️ No key rotation support (could be added with MultiFernet in future)

### 2.2 Market & Competitive Analysis

#### 2.2.1 Similar Solutions in FastAPI Ecosystem

**Analysis of Popular FastAPI Projects:**

| Project | Encryption Placement | Notes |
|---------|---------------------|-------|
| [fastapi-clean-example (ivan-borovets)](https://github.com/ivan-borovets/fastapi-clean-example) | `infrastructure/adapters/` | Separates infrastructure concerns from application layer |
| [fastapi-best-architecture](https://github.com/fastapi-practices/fastapi_best_architecture) | `common/security/` | Groups all security utilities together |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | `core/security.py` | Official FastAPI template places all security in core |

**Key Observation**: **100% of reviewed projects** place encryption/security utilities outside the service layer, typically in `core/`, `common/`, or `infrastructure/`.

#### 2.2.2 Key Competitors & Comparable Patterns

**Django Framework Pattern:**

Django's recommended structure separates:
- `core/` or `common/` - Cross-cutting concerns (encryption, security)
- `apps/<app_name>/services/` - Business logic specific to each app
- `utils/` - Generic helpers

**Flask Best Practices:**

Miguel Grinberg's Flask Mega-Tutorial recommends:
- `app/core/` - Configuration and security
- `app/services/` - Business logic
- Encryption should be a "service" in the architectural sense (infrastructure), not in the directory sense

**Enterprise Java Spring Boot (for comparison):**

Spring Boot's layered architecture:
- `config/` - Security configuration and encryption utilities
- `service/` - Business services (annotated with `@Service`)
- `util/` - Helper classes

**Pattern Consensus**: Across all major web frameworks, **encryption utilities belong in configuration/core/security layers**, not business service layers.

#### 2.2.3 Market Gaps and Opportunities

**Gap Identified**:

Most FastAPI tutorials and templates don't provide clear guidance on **where to place infrastructure utilities** in a layered architecture. This creates confusion for developers coming from other frameworks.

**Opportunity**:

By properly organizing the Emerald Backend codebase, it can serve as a **reference implementation** demonstrating:
- Clear separation of infrastructure utilities (`core/`) vs domain services (`services/`)
- Scalable patterns for managing sensitive data encryption
- Best practices for FastAPI layered architecture in financial applications

### 2.3 Technical Constraints and Dependencies

**Current Dependencies:**

```python
# encryption_service.py dependencies
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from src.core.config import settings
from src.core.exceptions import EncryptionError
```

**Key Constraint**: The encryption service **already depends on `src.core.config`**, making it natural to move it to `src.core/`.

**Current Consumers:**

```python
# Files importing EncryptionService
src/services/account_service.py
src/services/card_service.py
tests/unit/services/test_encryption_service.py
```

**Migration Impact**: Only 2 production files need import path updates, making this a low-risk refactoring.

---

## 3. Comparison of Placement Options

### Option 1: Move to `src/core/` (RECOMMENDED)

**Structure:**
```
src/core/
├── config.py
├── security.py       # Password hashing, JWT, refresh token hashing
├── encryption.py     # Data encryption (Fernet) ← NEW
├── database.py
└── logging.py
```

**Pros:**
- ✅ **Logical Grouping**: All security-related utilities (password hashing, JWT, data encryption) in one location
- ✅ **Matches Existing Pattern**: `security.py` already exists in `core/` with similar utility functions
- ✅ **Aligns with FastAPI Best Practices**: Matches official FastAPI template and community conventions
- ✅ **Minimal Refactoring**: Only need to move 1 file and update 2 imports
- ✅ **Clear Semantics**: `core/` signals "fundamental infrastructure" to developers
- ✅ **Dependency Consistency**: Already imports from `src.core.config`, stays in same package

**Cons:**
- ⚠️ `core/` might become crowded as more utilities are added (can be addressed later with `core/security/` subdirectory if needed)

**Implementation Effort**: **Low** (1-2 hours)

**Recommended Import Pattern:**
```python
# Before
from src.services.encryption_service import EncryptionService

# After
from src.core.encryption import EncryptionService
```

---

### Option 2: Create `src/infrastructure/` Layer

**Structure:**
```
src/infrastructure/
├── encryption.py
├── cache.py           # Future: Redis caching utilities
└── external/          # Future: Third-party API clients
```

**Pros:**
- ✅ **Clean Architecture Compliance**: Explicitly separates infrastructure concerns
- ✅ **Scalability**: Provides a home for future infrastructure services (caching, message queues, external APIs)
- ✅ **DDD Alignment**: Matches Domain-Driven Design patterns from enterprise architecture

**Cons:**
- ❌ **Over-Engineering for Current Scope**: Project doesn't yet have enough infrastructure services to justify a separate layer
- ❌ **Inconsistency**: Security utilities (password hashing, JWT) would still be in `core/`, splitting related concerns
- ❌ **Learning Curve**: Developers must learn distinction between `core/` and `infrastructure/`
- ❌ **More Refactoring**: Would eventually require moving `security.py` to maintain consistency

**Implementation Effort**: **Medium** (3-4 hours, plus future consolidation)

**Verdict**: **Too early** to introduce this layer. Consider this in Phase 2 or 3 when adding external service integrations.

---

### Option 3: Create `src/utils/` Directory

**Structure:**
```
src/utils/
├── encryption.py
├── validators.py      # Future: Custom validation functions
└── formatters.py      # Future: Data formatting utilities
```

**Pros:**
- ✅ **Common Pattern**: `utils/` is a familiar directory in Python projects
- ✅ **Flexibility**: Can house various small helper functions

**Cons:**
- ❌ **Semantic Ambiguity**: "Utils" is a vague term that becomes a catch-all for miscellaneous code
- ❌ **Doesn't Match Current Structure**: Project already has `core/` for cross-cutting concerns
- ❌ **Security Split**: Would separate encryption (`utils/`) from password hashing and JWT (`core/security.py`)
- ❌ **Anti-Pattern**: Many seasoned developers avoid `utils/` directories as they tend to become disorganized

**Implementation Effort**: **Low** (2-3 hours)

**Verdict**: **Not recommended**. `utils/` directories often become dumping grounds for disparate code.

---

### Option 4: Keep in `src/services/` with Namespace Separation

**Structure:**
```
src/services/
├── domain/           # Business logic services
│   ├── auth_service.py
│   ├── account_service.py
│   └── ...
└── infrastructure/   # Infrastructure services
    └── encryption_service.py
```

**Pros:**
- ✅ **Preserves Location**: No file moves required
- ✅ **Explicit Categorization**: Subdirectories clarify service types

**Cons:**
- ❌ **Confusing Semantics**: "Infrastructure services" in the "services" directory is contradictory
- ❌ **Doesn't Solve Root Problem**: Still mixing infrastructure and domain concerns
- ❌ **High Refactoring Cost**: All existing services would need to move to `domain/` subdirectory
- ❌ **Import Complexity**: Longer import paths (`src.services.domain.auth_service`)

**Implementation Effort**: **High** (6-8 hours to move all services)

**Verdict**: **Not recommended**. Adds complexity without clear benefits.

---

### Decision Matrix

| Criteria | Option 1: `core/` | Option 2: `infrastructure/` | Option 3: `utils/` | Option 4: Stay in `services/` |
|----------|------------------|-----------------------------|--------------------|------------------------------|
| **Alignment with Best Practices** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Consistency with Existing Code** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Implementation Effort** | ⭐⭐⭐⭐⭐ (Low) | ⭐⭐⭐ (Medium) | ⭐⭐⭐⭐ (Low) | ⭐⭐⭐⭐⭐ (None) |
| **Scalability** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Developer Intuitiveness** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Security Utilities Co-location** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ |
| **Total Score** | **28/30** | **19/30** | **16/30** | **16/30** |

**Winner**: **Option 1 - Move to `src/core/`**

---

## 4. Recommendations & Next Steps

### 4.1 Is This Refactoring Worth Pursuing?

**YES - Conditionally Recommended**

**Justification:**
1. **Improves Code Quality**: Aligns the codebase with FastAPI best practices and clean architecture principles
2. **Low Risk, High Return**: Minimal refactoring effort (2 files, ~30 minutes) with significant organizational benefits
3. **Prevents Future Debt**: Addressing this now is easier than after 10+ services depend on incorrect import paths
4. **Educational Value**: Establishes clear precedent for where to place future infrastructure utilities

**Condition**: Should be completed **before Phase 1.3** to avoid disrupting feature development.

### 4.2 Recommended Approach

**Primary Recommendation: Move to `src/core/encryption.py`**

**Step-by-Step Implementation:**

1. **Move File**
   ```bash
   git mv src/services/encryption_service.py src/core/encryption.py
   ```

2. **Update Imports**
   - In `src/services/account_service.py`:
     ```python
     # Before
     from src.services.encryption_service import EncryptionService

     # After
     from src.core.encryption import EncryptionService
     ```
   - In `src/services/card_service.py`: Same change

3. **Update Service Layer Exports**
   - Remove `EncryptionService` from `src/services/__init__.py`

4. **Update Core Layer Exports**
   - Add `EncryptionService` to `src/core/__init__.py` (if exists) or create it:
     ```python
     from src.core.encryption import EncryptionService

     __all__ = ["EncryptionService"]
     ```

5. **Update Tests**
   - Move test file: `tests/unit/services/test_encryption_service.py` → `tests/unit/core/test_encryption.py`
   - Update import in test file

6. **Update Documentation**
   - Update `CLAUDE.md` to reflect new location
   - Add comment in `src/core/encryption.py` documenting why it's in `core/`

7. **Verify No Regressions**
   ```bash
   uv run pytest tests/unit/core/test_encryption.py
   uv run pytest tests/  # Full test suite
   uv run mypy src/
   uv run ruff check .
   ```

### 4.3 Alternative Recommendation (If Primary is Rejected)

**Fallback: Rename to Clarify Intent**

If moving the file is deemed too disruptive, at minimum:

1. Rename `encryption_service.py` to `encryption_utility.py` to signal it's not a domain service
2. Add docstring clarifying it's a reusable utility
3. Update `CLAUDE.md` with guidance to NOT follow this pattern for future services

**Rationale**: This preserves location but improves semantic clarity.

### 4.4 Immediate Next Steps

**Phase 1: Planning (15 minutes)**
- [ ] Review this research document with team/stakeholders
- [ ] Confirm approval to proceed with recommended approach
- [ ] Schedule refactoring in current sprint (before Phase 1.3 features)

**Phase 2: Implementation (30 minutes)**
- [ ] Create feature branch: `refactor/move-encryption-to-core`
- [ ] Move file and update imports per step-by-step plan
- [ ] Run full test suite and linting
- [ ] Update documentation

**Phase 3: Review & Deploy (15 minutes)**
- [ ] Create pull request with detailed description
- [ ] Peer review (should be quick, mechanical changes only)
- [ ] Merge to main branch
- [ ] Verify CI/CD pipeline passes

**Total Effort**: ~1 hour

### 4.5 Open Questions Requiring Further Investigation

1. **Key Rotation Strategy**: Should we implement `MultiFernet` key rotation before Phase 2?
   - **Impact**: Low (current implementation works fine)
   - **Recommendation**: Defer to Phase 2 unless compliance requires it

2. **Per-Record Encryption Keys**: Should sensitive data use unique keys per record?
   - **Impact**: High (database schema changes, migration complexity)
   - **Recommendation**: Research in Phase 2 when implementing multi-tenant features

3. **Future Infrastructure Layer**: When should we introduce `src/infrastructure/`?
   - **Recommendation**: Phase 3, when adding external service integrations (email, SMS, etc.)

4. **Quantum-Resistant Cryptography**: Should we plan migration to post-quantum algorithms?
   - **Impact**: Low (NIST standards still maturing, Fernet is secure for 5+ years)
   - **Recommendation**: Monitor NIST PQC standards, re-evaluate in 2026

---

## 5. References & Resources

### Academic & Technical Documentation

1. **Python Cryptography Library - Fernet**
   - Official Docs: https://cryptography.io/en/latest/fernet/
   - Key Management: https://cryptography.io/en/latest/fernet/#key-rotation

2. **NIST Cryptography Standards**
   - PBKDF2 Recommendations: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf
   - Post-Quantum Cryptography: https://csrc.nist.gov/projects/post-quantum-cryptography

### Architecture Patterns & Best Practices

3. **FastAPI Layered Architecture**
   - [Building Production-Ready FastAPI Applications (2025)](https://medium.com/@abhinav.dobhal/building-production-ready-fastapi-applications-with-service-layer-architecture-in-2025-f3af8a6ac563)
   - [FastAPI Best Practices Repository](https://github.com/zhanymkanov/fastapi-best-practices)
   - [Layered Architecture Guide](https://dev.to/markoulis/layered-architecture-dependency-injection-a-recipe-for-clean-and-testable-fastapi-code-3ioo)

4. **Clean Architecture & DDD**
   - [Unpacking Clean Architecture Layers](https://www.dandoescode.com/blog/unpacking-the-layers-of-clean-architecture-domain-application-and-infrastructure-services)
   - [Domain-Application-Infrastructure Pattern](https://badia-kharroubi.gitbooks.io/microservices-architecture/content/patterns/tactical-patterns/domain-application-infrastructure-services-pattern.html)
   - [Microsoft - DDD Microservices](https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice)

5. **Python Project Structure**
   - [Structuring Your Project - Hitchhiker's Guide](https://docs.python-guide.org/writing/structure/)
   - [Python Project Best Practices - Dagster](https://dagster.io/blog/python-project-best-practices)
   - [FastAPI Project Structure Guide](https://medium.com/@amirm.lavasani/how-to-structure-your-fastapi-projects-0219a6600a8f)

### Security & Encryption

6. **Data Encryption at Rest**
   - [Architectural Patterns for Securing Data (2025)](https://www.glukhov.org/post/2025/11/securing-information-at-rest-in-transit-at-runtime/)
   - [Encryption at Rest with SQLAlchemy - Miguel Grinberg](https://blog.miguelgrinberg.com/post/encryption-at-rest-with-sqlalchemy)
   - [Fernet Python Guide - CodeRivers](https://coderivers.org/blog/fernet-python/)

7. **FastAPI Security Best Practices**
   - [How to Secure FastAPI APIs](https://escape.tech/blog/how-to-secure-fastapi-api/)
   - [Security in FastAPI - Best Practices](https://dev.to/jnikenoueba/security-in-fastapi-best-practices-to-protect-your-application-part-i-409f)

### Example Implementations

8. **Reference Projects**
   - [fastapi-clean-example (ivan-borovets)](https://github.com/ivan-borovets/fastapi-clean-example) - Practical Clean Architecture with FastAPI
   - [fastapi-best-architecture](https://github.com/fastapi-practices/fastapi_best_architecture) - Enterprise FastAPI architecture
   - [Official FastAPI Full-Stack Template](https://github.com/fastapi/full-stack-fastapi-template) - FastAPI's official project template

### Industry Standards & Compliance

9. **OWASP Standards**
   - OWASP Top 10 2023: https://owasp.org/www-project-top-ten/
   - Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html

10. **Financial Services Compliance**
    - PCI DSS 4.0 (Payment Card Industry): https://www.pcisecuritystandards.org/
    - SOX Data Retention: https://www.sec.gov/about/offices/ocie/risk-alert-091913.pdf

---

## Appendix A: Current vs Proposed File Structure

### Current Structure
```
src/
├── api/
│   └── routes/
├── core/
│   ├── config.py
│   ├── security.py       # Password hashing, JWT
│   ├── database.py
│   └── logging.py
├── models/
├── repositories/
├── schemas/
└── services/
    ├── auth_service.py
    ├── user_service.py
    ├── account_service.py
    ├── transaction_service.py
    ├── card_service.py
    ├── audit_service.py
    ├── encryption_service.py  # ← CURRENT LOCATION
    └── currency_service.py
```

### Proposed Structure
```
src/
├── api/
│   └── routes/
├── core/
│   ├── config.py
│   ├── security.py           # Password hashing, JWT
│   ├── encryption.py         # Data encryption (Fernet) ← NEW LOCATION
│   ├── database.py
│   └── logging.py
├── models/
├── repositories/
├── schemas/
└── services/
    ├── auth_service.py
    ├── user_service.py
    ├── account_service.py
    ├── transaction_service.py
    ├── card_service.py
    ├── audit_service.py
    └── currency_service.py   # Note: Should also be moved, but out of scope
```

---

## Appendix B: Implementation Checklist

```markdown
## Refactoring Checklist

### Pre-Implementation
- [ ] Review research document
- [ ] Get approval from tech lead/team
- [ ] Create feature branch: `refactor/move-encryption-to-core`
- [ ] Ensure all tests pass on main branch

### Implementation
- [ ] Move file: `git mv src/services/encryption_service.py src/core/encryption.py`
- [ ] Update import in `src/services/account_service.py`
- [ ] Update import in `src/services/card_service.py`
- [ ] Remove `EncryptionService` from `src/services/__init__.py`
- [ ] Add `EncryptionService` to `src/core/__init__.py` (create if needed)
- [ ] Move test: `git mv tests/unit/services/test_encryption_service.py tests/unit/core/test_encryption.py`
- [ ] Update test import path

### Validation
- [ ] Run encryption tests: `uv run pytest tests/unit/core/test_encryption.py -v`
- [ ] Run full test suite: `uv run pytest tests/`
- [ ] Run type checking: `uv run mypy src/`
- [ ] Run linting: `uv run ruff check .`
- [ ] Run formatting: `uv run ruff format .`

### Documentation
- [ ] Update `CLAUDE.md` with new encryption service location
- [ ] Add inline comment in `src/core/encryption.py` explaining placement
- [ ] Update this research document status to "Implemented"

### Review & Merge
- [ ] Create pull request with descriptive title and link to research
- [ ] Request peer review
- [ ] Address review comments if any
- [ ] Merge to main branch
- [ ] Verify CI/CD pipeline success
- [ ] Close related issues/tasks

### Post-Implementation
- [ ] Monitor for any import errors in production logs
- [ ] Update team wiki/onboarding docs (if exists)
- [ ] Consider whether `currency_service.py` should also be moved (separate task)
```

---

## Document Metadata

- **Author**: Claude Code (AI Research Assistant)
- **Created**: 2025-12-11
- **Status**: Draft - Pending Review
- **Related Files**:
  - `.features/descriptions/refactor/encryption_service.md` (Feature request)
  - `src/services/encryption_service.py` (Current location)
  - `src/core/security.py` (Related security utilities)
- **Estimated Implementation Time**: 1 hour
- **Risk Level**: Low
- **Priority**: Medium (should complete before Phase 1.3)
