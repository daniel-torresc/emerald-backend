# Implementation Plan: Encryption Service Refactoring

## 1. Executive Summary

This plan details the relocation of `encryption_service.py` from `src/services/` to `src/core/` in the Emerald Backend project. The encryption service is a generic, reusable utility that handles sensitive data encryption (IBAN, etc.) using Fernet symmetric encryption. Its current placement in the services directory is architecturally inconsistent with the project's strict 3-layer architecture, where `src/services/` is reserved for business logic services that depend on repositories.

The primary objective is to improve code organization by co-locating all security-related utilities (password hashing, JWT management, and data encryption) in `src/core/`, aligning with FastAPI best practices and established patterns in the codebase. This refactoring is low-risk, affects only 3 files that need import updates, and can be completed in approximately 30-45 minutes.

Expected outcomes include: improved developer onboarding experience, consistent import patterns for security utilities, and clearer separation between infrastructure utilities and domain services.

---

## 2. Technical Architecture

### 2.1 System Design Overview

**Current Architecture Problem:**

```
src/
├── core/
│   ├── config.py
│   ├── security.py       # Password hashing, JWT ← Security utilities HERE
│   ├── database.py
│   └── logging.py
└── services/
    ├── auth_service.py        # Business logic ✓
    ├── account_service.py     # Business logic ✓
    ├── encryption_service.py  # Infrastructure utility ✗ MISPLACED
    └── ...
```

**Proposed Architecture:**

```
src/
├── core/
│   ├── config.py
│   ├── security.py       # Password hashing, JWT
│   ├── encryption.py     # Data encryption (Fernet) ← MOVED HERE
│   ├── database.py
│   └── logging.py
└── services/
    ├── auth_service.py        # Business logic ✓
    ├── account_service.py     # Business logic ✓
    └── ...                    # All services depend on repositories
```

**Key Components:**

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `encryption.py` | `src/core/` | Fernet encryption/decryption for sensitive data |
| `security.py` | `src/core/` | Password hashing (Argon2id), JWT creation/validation |
| `account_service.py` | `src/services/` | Business logic consumer of encryption |

**Data Flow:**

```
AccountService (src/services/)
      │
      │ imports
      ▼
EncryptionService (src/core/encryption.py)
      │
      │ uses
      ▼
Settings.secret_key (src/core/config.py)
```

### 2.2 Technology Decisions

**[File Location: `src/core/encryption.py`]**
- **Purpose**: Houses the EncryptionService class alongside other security utilities
- **Why this choice**:
  - Co-locates all security-related code (encryption, password hashing, JWT)
  - Matches existing pattern where `security.py` already lives in `core/`
  - Aligns with FastAPI community conventions and official templates
  - EncryptionService already imports from `src.core.config`, making it natural
- **Alternatives considered**:
  - `src/utils/encryption.py` - Rejected: "utils" directories become disorganized catch-alls
  - `src/infrastructure/` - Rejected: Over-engineering for current scope, would require moving `security.py` too
  - Keep in `src/services/` with subdirectories - Rejected: Adds complexity without solving the core issue

### 2.3 File Structure

**Files to Modify:**

```
src/
├── core/
│   ├── __init__.py          # UPDATE: Add EncryptionService export
│   └── encryption.py        # NEW: Move from services/encryption_service.py
└── services/
    ├── __init__.py          # UPDATE: Remove EncryptionService export
    ├── account_service.py   # UPDATE: Change import path
    └── encryption_service.py # DELETE: After moving to core/

tests/
└── unit/
    ├── core/
    │   └── test_encryption.py  # NEW: Move from services/
    └── services/
        └── test_encryption_service.py  # DELETE: After moving
```

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Encryption Service Relocation

**Files Involved:**
- `src/services/encryption_service.py` (source)
- `src/core/encryption.py` (destination)

**Purpose**: Move the encryption utility to its architecturally correct location.

**Implementation Requirements:**

1. **Core Logic**:
   - Rename file from `encryption_service.py` to `encryption.py` (simpler naming, matches `security.py`)
   - No code changes required inside the file
   - File already has correct imports from `src.core.config`

2. **Data Handling**:
   - No changes to encryption/decryption logic
   - No changes to key derivation (PBKDF2-HMAC-SHA256)
   - No changes to Fernet token format

3. **Edge Cases & Error Handling**:
   - [x] Verify file compiles after move (import path self-references if any)
   - [x] Ensure logger name updates correctly (`__name__` will change)

4. **Dependencies**:
   - Internal: `src.core.config.settings` (already correct)
   - External: `cryptography.fernet`, `cryptography.hazmat.primitives`

5. **Testing Requirements**:
   - [x] Unit test: All existing tests pass after import path update
   - [x] Unit test: Verify encryption/decryption still works
   - [x] Integration test: AccountService can encrypt/decrypt IBAN

**Acceptance Criteria**:
- [x] File exists at `src/core/encryption.py`
- [x] File removed from `src/services/encryption_service.py`
- [x] `uv run mypy src/` passes with no errors
- [x] All 11 encryption tests pass

**Implementation Notes**:
- Use `git mv` to preserve file history
- The class name `EncryptionService` remains unchanged (familiar to existing code)

---

#### Component: Import Path Updates

**Files Involved:**
- `src/services/__init__.py`
- `src/services/account_service.py`
- `src/core/__init__.py`

**Purpose**: Update all import statements to reference new location.

**Implementation Requirements:**

1. **Core Logic - `src/services/account_service.py`**:
   ```python
   # Before (line 35)
   from src.services.encryption_service import EncryptionService

   # After
   from src.core.encryption import EncryptionService
   ```

2. **Core Logic - `src/services/__init__.py`**:
   - Remove line: `from src.services.encryption_service import EncryptionService`
   - Remove `"EncryptionService"` from `__all__` list

3. **Core Logic - `src/core/__init__.py`**:
   - Add import: `from src.core.encryption import EncryptionService`
   - Add `"EncryptionService"` to `__all__` list under `# Security - Encryption` section

4. **Edge Cases & Error Handling**:
   - [x] Verify no circular imports introduced
   - [x] Verify no other files import from old path (grep confirmed only account_service.py)

5. **Testing Requirements**:
   - [x] Unit test: `from src.core import EncryptionService` works
   - [x] Unit test: `from src.services import EncryptionService` fails (intentionally)
   - [x] Integration test: AccountService initialization succeeds

**Acceptance Criteria**:
- [x] `EncryptionService` importable from `src.core`
- [x] `EncryptionService` NOT exported from `src.services`
- [x] `uv run ruff check .` passes with no import errors

---

#### Component: Test File Relocation

**Files Involved:**
- `tests/unit/services/test_encryption_service.py` (source)
- `tests/unit/core/test_encryption.py` (destination)

**Purpose**: Move tests to match new source file location.

**Implementation Requirements:**

1. **Core Logic**:
   - Move file to `tests/unit/core/` directory
   - Rename to `test_encryption.py` (matches source file naming)
   - Update import statement:
     ```python
     # Before
     from src.services.encryption_service import EncryptionService

     # After
     from src.core.encryption import EncryptionService
     ```

2. **Edge Cases & Error Handling**:
   - [x] Verify `tests/unit/core/__init__.py` exists (it does)
   - [x] Verify pytest discovers tests in new location

3. **Testing Requirements**:
   - [x] All 11 existing tests pass in new location
   - [x] Test discovery works: `uv run pytest tests/unit/core/test_encryption.py -v`

**Acceptance Criteria**:
- [x] Test file exists at `tests/unit/core/test_encryption.py`
- [x] Old test file removed from `tests/unit/services/`
- [x] All 11 tests pass

---

### 3.2 Detailed File Specifications

#### `src/core/encryption.py`

**Purpose**: Central location for data encryption utilities.

**Implementation**: Direct copy of `src/services/encryption_service.py` with no code changes.

**Contents** (129 lines, unchanged):
- `EncryptionService` class with `__init__`, `encrypt`, `decrypt` methods
- Key derivation using PBKDF2-HMAC-SHA256 (100,000 iterations)
- Fernet encryption (AES-128-CBC + HMAC)
- Proper error handling with `EncryptionError` exception

**Edge Cases**: Already handled in existing implementation.

**Tests**: Covered by existing test suite (11 tests).

---

#### `src/core/__init__.py`

**Purpose**: Export EncryptionService alongside other security utilities.

**Implementation**:

```python
# Add after line 27 (after verify_refresh_token_hash import)
from src.core.encryption import EncryptionService

# Update __all__ list - add after line 52 (after "verify_refresh_token_hash")
    # Security - Encryption
    "EncryptionService",
```

**Edge Cases**:
- Import order matters for avoiding circular imports (encryption has no internal deps)

**Tests**:
- Verify `from src.core import EncryptionService` works

---

#### `src/services/__init__.py`

**Purpose**: Remove EncryptionService from services exports.

**Implementation**:

```python
# Remove line 13
from src.services.encryption_service import EncryptionService  # DELETE

# Remove from __all__ (line 24)
    "EncryptionService",  # DELETE
```

**Edge Cases**:
- Ensure no services still import from `src.services.encryption_service`

**Tests**:
- Verify `from src.services import EncryptionService` raises ImportError

---

#### `src/services/account_service.py`

**Purpose**: Update import to use new location.

**Implementation**:

```python
# Change line 35
# Before
from src.services.encryption_service import EncryptionService

# After
from src.core.encryption import EncryptionService
```

**Edge Cases**:
- None (simple import path change)

**Tests**:
- AccountService instantiation works
- Account creation with IBAN encryption works

---

#### `tests/unit/core/test_encryption.py`

**Purpose**: Test file in correct location matching source.

**Implementation**:

```python
# Change line 11
# Before
from src.services.encryption_service import EncryptionService

# After
from src.core.encryption import EncryptionService
```

**Edge Cases**:
- Ensure `tests/unit/core/__init__.py` exists (it does)

**Tests**:
- All 11 existing tests pass

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Move Encryption Service (Size: XS, Priority: P0)

**Goal**: Relocate the encryption service to `src/core/` with all imports updated and tests passing.

**Scope**:
- Include: File move, import updates, test relocation, linting, type checking
- Exclude: Code changes to encryption logic, documentation updates to CLAUDE.md

**Components to Implement**:
- [x] Move `encryption_service.py` to `src/core/encryption.py`
- [x] Update `src/core/__init__.py` exports
- [x] Update `src/services/__init__.py` exports
- [x] Update `src/services/account_service.py` import
- [x] Move test file to `tests/unit/core/test_encryption.py`

**Detailed Tasks**:

1. [ ] **Move encryption service file**
   - Command: `git mv src/services/encryption_service.py src/core/encryption.py`
   - Verify file exists in new location

2. [ ] **Update core module exports**
   - Edit `src/core/__init__.py`:
     - Add import: `from src.core.encryption import EncryptionService`
     - Add to `__all__`: `"EncryptionService"`

3. [ ] **Update services module exports**
   - Edit `src/services/__init__.py`:
     - Remove import line for EncryptionService
     - Remove from `__all__` list

4. [ ] **Update account service import**
   - Edit `src/services/account_service.py`:
     - Change: `from src.services.encryption_service import EncryptionService`
     - To: `from src.core.encryption import EncryptionService`

5. [ ] **Move test file**
   - Command: `git mv tests/unit/services/test_encryption_service.py tests/unit/core/test_encryption.py`
   - Edit test file: Update import path

6. [ ] **Run validation suite**
   - `uv run pytest tests/unit/core/test_encryption.py -v`
   - `uv run pytest tests/`
   - `uv run mypy src/`
   - `uv run ruff check .`
   - `uv run ruff format .`

**Dependencies**:
- Requires: No dependencies (can start immediately)
- Blocks: Nothing (standalone refactoring)

**Validation Criteria** (Phase complete when):
- [x] All 11 encryption tests pass
- [x] Full test suite passes
- [x] MyPy type checking passes
- [x] Ruff linting passes
- [x] No import errors at runtime

**Risk Factors**:
- Low risk: Only 3 files need import updates
- Mitigation: Run full test suite before committing

**Estimated Effort**: 30-45 minutes for 1 developer

### 4.2 Implementation Sequence

```
Step 1: Move file with git mv (preserves history)
   ↓
Step 2: Update src/core/__init__.py (add export)
   ↓
Step 3: Update src/services/__init__.py (remove export)
   ↓
Step 4: Update src/services/account_service.py (fix import)
   ↓
Step 5: Move and update test file
   ↓
Step 6: Run validation suite
   ↓
Step 7: Commit with conventional commit message
```

**Rationale for ordering**:
- Step 1 first: File must exist before updating exports
- Steps 2-4 together: Import changes are interdependent
- Step 5 after source changes: Tests validate the new structure
- Step 6 validates everything works

---

## 5. Simplicity & Design Validation

**Simplicity Checklist**:
- [x] Is this the SIMPLEST solution that solves the problem? **Yes** - single file move with minimal import updates
- [x] Have we avoided premature optimization? **Yes** - no code changes, only organizational
- [x] Does this align with existing patterns in the codebase? **Yes** - matches `security.py` pattern
- [x] Can we deliver value in smaller increments? **No** - this is already atomic
- [x] Are we solving the actual problem vs. a perceived problem? **Yes** - architectural inconsistency is real

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Create `src/utils/` | "utils" directories become disorganized over time |
| Create `src/infrastructure/` | Over-engineering for current scope |
| Keep in `services/` with subdirectories | Adds complexity without solving the issue |
| Rename to `encryption_utility.py` | Still in wrong location, only cosmetic |

**Rationale**: Moving to `src/core/` is the simplest solution that:
1. Requires no code changes
2. Aligns with existing `security.py` pattern
3. Matches FastAPI community conventions
4. Minimizes import path changes (only 3 files)

---

## 6. References & Related Documents

### Internal Documentation
- Feature description: `.features/descriptions/refactor/encryption_service.md`
- Research document: `.features/research/encryption_service.md`
- Project standards: `.claude/standards/backend.md`
- Main project guide: `CLAUDE.md`

### External Resources
- [FastAPI Full-Stack Template](https://github.com/fastapi/full-stack-fastapi-template) - Official template places security in `core/`
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) - Community conventions
- [Cryptography.io Fernet](https://cryptography.io/en/latest/fernet/) - Fernet encryption documentation
- [OWASP Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

### Related Existing Files
- `src/core/security.py` - Pattern to follow (security utilities in core)
- `src/core/__init__.py` - Will be updated to export EncryptionService
- `src/services/account_service.py` - Primary consumer of EncryptionService

---

## Appendix A: Execution Commands

```bash
# Step 1: Move encryption service
git mv src/services/encryption_service.py src/core/encryption.py

# Step 2-4: Edit files (use editor or Edit tool)
# - src/core/__init__.py
# - src/services/__init__.py
# - src/services/account_service.py

# Step 5: Move test file
git mv tests/unit/services/test_encryption_service.py tests/unit/core/test_encryption.py

# Step 6: Validation
uv run pytest tests/unit/core/test_encryption.py -v
uv run pytest tests/
uv run mypy src/
uv run ruff check .
uv run ruff format .

# Step 7: Commit
git add .
git commit -m "refactor: move encryption service to core module

Move EncryptionService from src/services/ to src/core/ to properly
align with the project's layered architecture. The encryption service
is an infrastructure utility, not a business logic service, and belongs
alongside other security utilities (password hashing, JWT) in core/.

Changes:
- Move src/services/encryption_service.py -> src/core/encryption.py
- Update exports in src/core/__init__.py and src/services/__init__.py
- Update import in src/services/account_service.py
- Move test file to tests/unit/core/test_encryption.py

No functional changes to encryption logic.

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Appendix B: Verification Checklist

```markdown
## Pre-Implementation
- [ ] Read this plan document
- [ ] Confirm current branch is clean (`git status`)
- [ ] Create feature branch: `git checkout -b refactor/move-encryption-to-core`

## Implementation
- [ ] Move file: `git mv src/services/encryption_service.py src/core/encryption.py`
- [ ] Edit `src/core/__init__.py`:
  - [ ] Add import: `from src.core.encryption import EncryptionService`
  - [ ] Add to __all__: `"EncryptionService"`
- [ ] Edit `src/services/__init__.py`:
  - [ ] Remove import line
  - [ ] Remove from __all__
- [ ] Edit `src/services/account_service.py`:
  - [ ] Change import path
- [ ] Move test: `git mv tests/unit/services/test_encryption_service.py tests/unit/core/test_encryption.py`
- [ ] Edit test file import path

## Validation
- [ ] Run encryption tests: `uv run pytest tests/unit/core/test_encryption.py -v`
- [ ] Run full tests: `uv run pytest tests/`
- [ ] Run type checking: `uv run mypy src/`
- [ ] Run linting: `uv run ruff check .`
- [ ] Run formatting: `uv run ruff format .`

## Commit & Merge
- [ ] Stage changes: `git add .`
- [ ] Commit with conventional message
- [ ] Push branch
- [ ] Create pull request
- [ ] Merge after review
```

---

## Document Metadata

- **Author**: Claude Code
- **Created**: 2025-12-11
- **Status**: Ready for Implementation
- **Estimated Effort**: 30-45 minutes
- **Risk Level**: Low
- **Priority**: Medium (should complete before adding more infrastructure utilities)
