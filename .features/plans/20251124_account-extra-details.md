# Implementation Plan: Account Extra Details

## Executive Summary

This plan details the implementation of additional metadata fields for the Account model in the Emerald Finance Platform. The feature adds six new fields to enhance account management and user experience: visual identifiers (color, icon), bank information (bank name, IBAN, last four digits), and user notes.

**Primary Objectives:**
- Enable visual customization of accounts with color codes and icons
- Store bank information (bank name and encrypted IBAN) for user reference
- Provide a notes field for users to add personal descriptions and reminders
- Maintain strict security standards for sensitive data (encrypted IBAN storage)
- Ensure seamless integration with existing account management APIs

**Expected Outcomes:**
- Users can visually distinguish accounts with custom colors and icons
- Secure storage of sensitive bank information (IBAN encrypted at rest)
- Enhanced user experience with personal notes capability
- Full backward compatibility with existing account features
- Maintained 80%+ test coverage for all new functionality

**Success Criteria:**
- All new fields properly validated and stored in database
- IBAN encryption/decryption working correctly with AES-256-GCM
- API endpoints updated to accept and return new fields
- Comprehensive test coverage (80% minimum)
- Zero breaking changes to existing functionality
- Migration successfully updates existing accounts with default values

---

## 1. Technical Architecture

### 1.1 System Design Overview

```
┌─────────────────────────────────────────────────────┐
│  API Layer (routes/accounts.py)                     │
│  - Accepts new metadata fields in create/update     │
│  - Returns new fields in responses                  │
│  - Validates field formats (hex color, URLs)        │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Service Layer (account_service.py)                 │
│  - Validates IBAN format before encryption          │
│  - Extracts last 4 digits before encryption         │
│  - Calls encryption service for IBAN                │
│  - Handles business logic for field updates         │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Encryption Service (NEW: encryption_service.py)    │
│  - Encrypts/decrypts IBAN using AES-256-GCM         │
│  - Key derivation from SECRET_KEY + salt            │
│  - Authenticated encryption (integrity protection)  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Repository Layer (account_repository.py)           │
│  - Stores encrypted IBAN as TEXT                    │
│  - Stores metadata fields                           │
│  - No encryption logic (handled by service)         │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Database (PostgreSQL)                              │
│  - New columns in accounts table                    │
│  - IBAN stored as encrypted text                    │
│  - Color, icon, bank name, notes as plain text      │
└─────────────────────────────────────────────────────┘
```

**Key Components:**
- **API Layer**: Handles HTTP requests with new field validations
- **Service Layer**: Business logic, IBAN processing, encryption orchestration
- **Encryption Service**: Dedicated encryption/decryption for sensitive data
- **Repository Layer**: Database operations (no encryption logic)
- **Database Schema**: New columns with appropriate types and constraints

**Integration Points:**
- Existing account creation flow (POST /api/v1/accounts)
- Existing account update flow (PUT /api/v1/accounts/{id})
- Existing account retrieval (GET endpoints)
- Audit logging system (log field changes)
- Pydantic schema validation layer

**Data Flow:**

*Account Creation with IBAN:*
```
User Input (IBAN) → Validation → Extract Last 4 → Encrypt Full IBAN
→ Store Encrypted IBAN + Last 4 → Return Response (show last 4 only)
```

*Account Retrieval:*
```
Database Query → Return Encrypted IBAN + Last 4 + Metadata
→ Response (show last 4, never decrypt IBAN in GET)
```

### 1.2 Technology Decisions

#### Encryption Library: `cryptography` (Fernet)

**Purpose**: Encrypt IBAN for secure storage in the database

**Why this choice**:
- Already widely used in Python ecosystem for symmetric encryption
- Provides AES-128 in CBC mode with HMAC for integrity (secure by default)
- Built on top of `pyca/cryptography`, a well-audited library
- Simple API: `Fernet.encrypt()` and `Fernet.decrypt()`
- Handles key derivation, IV generation, and authentication automatically
- Recommended by [OWASP for application-level encryption](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

**Version**: `cryptography>=41.0.0` (latest stable as of 2025)

**Alternatives considered**:
- **PyCryptodome**: More comprehensive but overkill for this use case, requires more manual configuration
- **Database-level encryption (PostgreSQL pgcrypto)**: Less portable, harder to test, limited to PostgreSQL
- **HashiCorp Vault**: Over-engineered for this phase, adds operational complexity
- **AWS KMS / Cloud KMS**: Cloud vendor lock-in, not suitable for self-hosted deployments

**Rationale**: Fernet provides the right balance of security, simplicity, and portability. It's battle-tested, well-documented, and requires minimal code to implement correctly.

---

#### IBAN Validation Library: `schwifty`

**Purpose**: Validate IBAN format and checksum before storage

**Why this choice**:
- Specialized library for IBAN/BIC validation and manipulation
- Validates IBAN checksum algorithm (mod-97)
- Supports all SEPA countries and international formats
- Lightweight and focused (does one thing well)
- Actively maintained with good documentation

**Version**: `schwifty>=2023.11.0`

**Alternatives considered**:
- **python-stdnum**: More general (validates many identifiers), but heavier dependency
- **Manual regex validation**: Insufficient (doesn't validate checksum, error-prone)
- **No validation**: Unacceptable (would store invalid IBANs)

**Rationale**: Specialized tool for a specialized task. IBAN validation is complex (country-specific lengths, checksum algorithm), and `schwifty` handles all edge cases correctly.

---

#### Color Validation: `pydantic` with regex

**Purpose**: Validate hex color codes (e.g., #FF5733)

**Why this choice**:
- Pydantic already used extensively in the project
- Simple regex pattern for hex colors: `^#[0-9A-Fa-f]{6}$`
- No additional dependencies
- Native integration with FastAPI validation

**Alternatives considered**:
- **colour**: Full color library (overkill for validation)
- **webcolors**: Validates color names too (not needed)

---

#### Icon Storage: URL/Path (String)

**Purpose**: Store reference to account icon

**Why this choice**:
- Phase 1: Store URLs to icons (hosted separately or CDN)
- Phase 2: Support base64 data URIs for embedded icons (future)
- Phase 3: Upload to object storage (S3/MinIO) and store path (future)
- Flexible approach that supports multiple storage strategies
- Avoids storing binary data in PostgreSQL (performance)

**Validation**: URL format validation with Pydantic `AnyHttpUrl` type

---

### 1.3 File Structure

```
src/
├── models/
│   ├── account.py                    # [MODIFY] Add new columns to Account model
│   └── enums.py                      # [NO CHANGE] AccountType enum already exists
│
├── schemas/
│   └── account.py                    # [MODIFY] Add new fields to Pydantic schemas
│
├── services/
│   ├── account_service.py            # [MODIFY] Add encryption logic for IBAN
│   └── encryption_service.py         # [NEW] Dedicated encryption/decryption service
│
├── repositories/
│   └── account_repository.py         # [NO CHANGE] Inherits from BaseRepository
│
├── api/
│   └── routes/
│       └── accounts.py               # [MINOR MODIFY] No changes needed (uses schemas)
│
├── core/
│   ├── config.py                     # [MODIFY] Add ENCRYPTION_KEY config
│   └── security.py                   # [NO CHANGE] No changes needed
│
├── exceptions.py                     # [MODIFY] Add EncryptionError if needed
│
alembic/
└── versions/
    └── 4aabd1426c98_initial_schema.py  # [MODIFY] Update existing migration
│
tests/
├── unit/
│   └── services/
│       └── test_encryption_service.py  # [NEW] Encryption service tests
│
├── integration/
│   └── test_accounts_metadata.py       # [NEW] Integration tests for new fields
│
└── conftest.py                         # [MODIFY] Add fixtures for metadata tests
│
.env.example                            # [MODIFY] Add ENCRYPTION_KEY config
pyproject.toml                          # [MODIFY] Add cryptography and schwifty deps
```

**Directory Purpose:**
- `models/`: SQLAlchemy ORM models (database schema)
- `schemas/`: Pydantic schemas (API validation)
- `services/`: Business logic layer
- `repositories/`: Data access layer
- `api/routes/`: HTTP endpoint definitions
- `core/`: Core utilities (config, security, database)
- `alembic/versions/`: Database migrations
- `tests/`: All test files organized by type

---

## 2. Implementation Specification

### 2.1 Component Breakdown

---

#### Component: Encryption Service

**Files Involved**:
- `src/services/encryption_service.py` (NEW)

**Purpose**: Provides secure encryption/decryption for sensitive account data (IBAN). Centralizes all cryptographic operations to ensure consistent security practices across the application.

**Implementation Requirements**:

1. **Core Logic**:
   - Implement `EncryptionService` class with encrypt/decrypt methods
   - Use Fernet (AES-128-CBC + HMAC) from `cryptography` library
   - Derive encryption key from `SECRET_KEY` environment variable using PBKDF2
   - Handle encryption errors gracefully with custom `EncryptionError` exception
   - Log encryption operations (without logging plaintext data)

2. **Data Handling**:
   - **Input**: Plaintext string (e.g., IBAN: "DE89370400440532013000")
   - **Output**: Encrypted string (base64-encoded ciphertext with authentication tag)
   - **Key Derivation**:
     - Use PBKDF2-HMAC-SHA256 with 100,000 iterations
     - Static salt derived from `SECRET_KEY` (deterministic, same key every time)
     - Output 32-byte key for Fernet
   - **Encryption Format**: Fernet token (URL-safe base64 with timestamp and signature)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: `SECRET_KEY` not set → Raise `ValueError` at startup
   - [ ] Handle case: Invalid ciphertext during decryption → Raise `EncryptionError`
   - [ ] Handle case: Expired Fernet token (TTL check) → Option to set TTL or ignore
   - [ ] Handle case: Empty string input → Return empty string (don't encrypt)
   - [ ] Validate: Input is string type before encryption
   - [ ] Error logging: Log errors but NEVER log plaintext or keys

4. **Dependencies**:
   - External: `cryptography` library (Fernet)
   - Internal: `src.core.config.settings` (for SECRET_KEY)

5. **Testing Requirements**:
   - [ ] Unit test: Encrypt then decrypt returns original plaintext
   - [ ] Unit test: Same plaintext produces different ciphertexts (due to randomness)
   - [ ] Unit test: Decryption of tampered ciphertext raises EncryptionError
   - [ ] Unit test: Empty string handling
   - [ ] Unit test: Key derivation is deterministic (same SECRET_KEY = same key)
   - [ ] Integration test: Encrypt IBAN, store in DB, retrieve, decrypt successfully

**Acceptance Criteria**:
- [ ] Encryption is authenticated (Fernet provides HMAC)
- [ ] Decryption fails if ciphertext is tampered with
- [ ] Encryption key is derived securely from SECRET_KEY
- [ ] No plaintext or keys logged anywhere
- [ ] 100% test coverage for encryption service

**Implementation Notes**:
- Use Fernet over raw AES to avoid implementation errors (IV management, padding, authentication)
- Fernet tokens include timestamp, allowing optional TTL enforcement (not used in this phase)
- Consider rotating encryption keys in future phases (requires re-encryption of existing IBANs)
- IBAN encryption is one-way in typical usage (never decrypted in GET requests, only displayed as last 4 digits)

**Code Example (Simplified)**:
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class EncryptionService:
    def __init__(self, secret_key: str):
        # Derive encryption key from SECRET_KEY
        kdf = PBKDF2(algorithm=hashes.SHA256(), length=32, salt=b'emerald-iban-salt', iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

---

#### Component: Account Model Extensions

**Files Involved**:
- `src/models/account.py`

**Purpose**: Extend the Account SQLAlchemy model to include six new metadata columns for enhanced account management.

**Implementation Requirements**:

1. **Core Logic**:
   - Add six new mapped columns to `Account` class:
     - `color_hex`: String(7), nullable=False, default="#818E8F"
     - `icon_url`: String(500), nullable=True (no default)
     - `bank_name`: String(100), nullable=True
     - `iban`: Text, nullable=True (stores encrypted IBAN)
     - `iban_last_four`: String(4), nullable=True (for display)
     - `notes`: String(500), nullable=True
   - Update `__repr__` method to include bank_name if present
   - Add inline documentation explaining each field's purpose

2. **Data Handling**:
   - **color_hex**: Default gray color (#818E8F) for new accounts
   - **icon_url**: NULL allowed (optional icon)
   - **bank_name**: NULL allowed (user may not specify bank)
   - **iban**: Encrypted format (Fernet token ~200 chars), NULL allowed
   - **iban_last_four**: Extracted from IBAN before encryption (e.g., "3000")
   - **notes**: NULL allowed (optional user notes)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Invalid hex color → Validated by Pydantic schema (not model)
   - [ ] Handle case: Icon URL too long → Database enforces 500 char limit
   - [ ] Handle case: Bank name too long → Database enforces 100 char limit
   - [ ] Handle case: Notes too long → Database enforces 500 char limit
   - [ ] Handle case: IBAN stored without last_four → Application bug, prevent in service layer

4. **Dependencies**:
   - Internal: Inherits from `Base`, `TimestampMixin`, `SoftDeleteMixin`, `AuditFieldsMixin`

5. **Testing Requirements**:
   - [ ] Unit test: Account can be created with all new fields
   - [ ] Unit test: Default color_hex applied when not specified
   - [ ] Unit test: NULL values accepted for optional fields
   - [ ] Integration test: Account with metadata persisted correctly to database
   - [ ] Integration test: Account retrieval includes all metadata fields

**Acceptance Criteria**:
- [ ] All six fields added to Account model
- [ ] Default color applied automatically
- [ ] Optional fields accept NULL values
- [ ] Encrypted IBAN stored as TEXT (sufficient length)
- [ ] Model documentation updated

**Implementation Notes**:
- `iban` field uses TEXT instead of String to accommodate varying encryption output sizes
- `iban_last_four` is separate from `iban` for performance (no decryption needed for display)
- No database-level validation for hex colors or URLs (handled by Pydantic)
- Consider adding database index on `bank_name` if filtering by bank becomes common (future optimization)

**Code Example**:
```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text

class Account(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    # ... existing fields ...

    # Visual Customization
    color_hex: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#818E8F",
        comment="Hex color code for UI display (e.g., #FF5733)"
    )

    icon_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL or path to account icon"
    )

    # Bank Information
    bank_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Name of the financial institution"
    )

    iban: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted IBAN (full account number, encrypted at rest)"
    )

    iban_last_four: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        comment="Last 4 digits of IBAN for display purposes (plaintext)"
    )

    # User Notes
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="User's personal notes about the account"
    )
```

---

#### Component: Pydantic Schema Extensions

**Files Involved**:
- `src/schemas/account.py`

**Purpose**: Extend Pydantic schemas to validate and serialize new account metadata fields in API requests and responses.

**Implementation Requirements**:

1. **Core Logic**:
   - Update `AccountBase` schema: Add `bank_name`, `notes` (common fields for create/response)
   - Update `AccountCreate` schema: Add `iban`, `color_hex`, `icon_url` (creation-only fields)
   - Update `AccountUpdate` schema: Add `color_hex`, `icon_url`, `notes` (updateable fields)
   - Update `AccountResponse` schema: Add all six new fields
   - Update `AccountListItem` schema: Add `color_hex`, `icon_url`, `bank_name` (for list view)
   - Add custom validators for hex color and IBAN format

2. **Data Handling**:
   - **Input Validation (AccountCreate)**:
     - `iban`: Optional, validated with `schwifty.IBAN` if provided
     - `color_hex`: Optional, defaults to "#818E8F", validated with regex
     - `icon_url`: Optional, validated as URL format (Pydantic `HttpUrl`)
     - `bank_name`: Optional, max 100 chars
     - `notes`: Optional, max 500 chars

   - **Output Serialization (AccountResponse)**:
     - `iban`: NEVER include in response (security)
     - `iban_last_four`: Display last 4 digits only
     - `color_hex`, `icon_url`, `bank_name`, `notes`: Include as-is

3. **Edge Cases & Error Handling**:
   - [ ] Validate: color_hex matches regex `^#[0-9A-Fa-f]{6}$`
   - [ ] Validate: IBAN checksum using `schwifty` library (if provided)
   - [ ] Validate: icon_url is valid HTTP/HTTPS URL (if provided)
   - [ ] Error: Invalid hex color → Return 422 with message "Invalid hex color format"
   - [ ] Error: Invalid IBAN → Return 422 with message "Invalid IBAN format or checksum"
   - [ ] Handle: Empty string for optional fields → Convert to None

4. **Dependencies**:
   - External: `schwifty` (for IBAN validation)
   - Internal: `pydantic.BaseModel`, `pydantic.Field`, `pydantic.field_validator`

5. **Testing Requirements**:
   - [ ] Unit test: Valid hex color passes validation
   - [ ] Unit test: Invalid hex color fails validation (#GGGGGG, #12345, etc.)
   - [ ] Unit test: Valid IBAN passes validation (multiple country codes)
   - [ ] Unit test: Invalid IBAN fails validation (bad checksum, invalid format)
   - [ ] Unit test: icon_url validates as URL
   - [ ] Unit test: AccountResponse excludes `iban` field
   - [ ] Integration test: Create account with metadata via API returns all fields

**Acceptance Criteria**:
- [ ] All schemas updated with new fields
- [ ] Hex color validation working correctly
- [ ] IBAN validation working correctly
- [ ] IBAN field never exposed in API responses
- [ ] Schema documentation updated with examples

**Implementation Notes**:
- Use `schwifty.IBAN` for validation: `IBAN(value)` raises `ValueError` if invalid
- Consider adding custom validator to normalize IBAN (remove spaces/hyphens)
- `iban_last_four` is not accepted in create/update (computed by service layer)
- Use Pydantic `Field` with `examples` for better API documentation (OpenAPI/Swagger)

**Code Example**:
```python
from pydantic import BaseModel, Field, field_validator, HttpUrl
from schwifty import IBAN
import re

class AccountCreate(AccountBase):
    # ... existing fields ...

    iban: str | None = Field(
        default=None,
        description="IBAN (International Bank Account Number) - will be encrypted",
        examples=["DE89370400440532013000", "GB82 WEST 1234 5698 7654 32"]
    )

    color_hex: str = Field(
        default="#818E8F",
        description="Hex color code for account visualization (e.g., #FF5733)",
        examples=["#FF5733", "#3498DB"]
    )

    icon_url: HttpUrl | None = Field(
        default=None,
        description="URL to account icon image",
        examples=["https://cdn.example.com/icons/bank.png"]
    )

    bank_name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the financial institution",
        examples=["Chase Bank", "Bank of America"]
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Personal notes about the account",
        examples=["Joint account with spouse", "Savings for vacation"]
    )

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, value: str) -> str:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError("Color must be a valid hex code (e.g., #FF5733)")
        return value.upper()  # Normalize to uppercase

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            # Remove spaces and hyphens, validate
            normalized = value.replace(" ", "").replace("-", "")
            IBAN(normalized)  # Raises ValueError if invalid
            return normalized
        except ValueError as e:
            raise ValueError(f"Invalid IBAN: {str(e)}")

class AccountResponse(AccountBase):
    # ... existing fields ...

    color_hex: str
    icon_url: str | None
    bank_name: str | None
    iban_last_four: str | None  # Display only, NEVER full IBAN
    notes: str | None

    # Note: 'iban' field is intentionally excluded from response
```

---

#### Component: Account Service Extensions

**Files Involved**:
- `src/services/account_service.py`

**Purpose**: Extend account creation and update logic to handle new metadata fields, including IBAN encryption and last-four extraction.

**Implementation Requirements**:

1. **Core Logic**:
   - Inject `EncryptionService` into `AccountService.__init__`
   - Update `create_account` method:
     - Accept new parameters: `iban`, `color_hex`, `icon_url`, `bank_name`, `notes`
     - If IBAN provided: encrypt it, extract last 4 digits
     - Pass all new fields to `account_repo.create()`
   - Update `update_account` method:
     - Accept updateable fields: `color_hex`, `icon_url`, `notes`
     - IBAN and bank_name are immutable after creation (not updateable)
   - Add audit logging for new field changes

2. **Data Handling**:
   - **IBAN Processing**:
     1. Receive IBAN from request (already validated by Pydantic)
     2. Extract last 4 characters: `iban_last_four = iban[-4:]`
     3. Encrypt full IBAN: `encrypted_iban = encryption_service.encrypt(iban)`
     4. Store both `encrypted_iban` and `iban_last_four` in database
   - **Other Fields**: Pass through directly (already validated by Pydantic)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: IBAN provided but encryption fails → Raise `EncryptionError`, rollback transaction
   - [ ] Handle case: IBAN less than 4 characters (invalid, but check) → Caught by Pydantic validator
   - [ ] Handle case: User tries to update IBAN → Reject (immutable after creation)
   - [ ] Handle case: User tries to update bank_name → Reject (immutable after creation)
   - [ ] Handle case: color_hex update to invalid format → Caught by Pydantic validator
   - [ ] Validate: icon_url is safe (no script injection) → Pydantic HttpUrl handles this

4. **Dependencies**:
   - Internal: `EncryptionService`, `AccountRepository`, `AuditService`

5. **Testing Requirements**:
   - [ ] Unit test: Create account with IBAN encrypts and stores correctly
   - [ ] Unit test: Create account with metadata stores all fields
   - [ ] Unit test: Update account with color_hex changes color
   - [ ] Unit test: Update account with notes changes notes
   - [ ] Unit test: Attempt to update IBAN fails (immutable)
   - [ ] Unit test: IBAN last four extracted correctly
   - [ ] Integration test: End-to-end account creation with all metadata
   - [ ] Integration test: Audit log includes metadata field changes

**Acceptance Criteria**:
- [ ] IBAN encrypted before storage
- [ ] Last 4 digits extracted and stored separately
- [ ] All metadata fields stored correctly
- [ ] IBAN and bank_name immutable after creation
- [ ] color_hex, icon_url, notes updateable
- [ ] Audit logs track metadata changes

**Implementation Notes**:
- Never decrypt IBAN in normal operations (only for admin/support if needed in future)
- Consider adding validation to prevent storing same IBAN for multiple accounts (future phase)
- Audit log should include old and new values for changed fields
- Transaction rollback if encryption fails (database consistency)

**Code Example**:
```python
class AccountService:
    def __init__(self, session: AsyncSession, encryption_service: EncryptionService):
        # ... existing init ...
        self.encryption_service = encryption_service

    async def create_account(
        self,
        # ... existing params ...
        iban: str | None = None,
        color_hex: str = "#818E8F",
        icon_url: str | None = None,
        bank_name: str | None = None,
        notes: str | None = None,
    ) -> Account:
        # Check uniqueness (existing logic)
        # ...

        # Process IBAN if provided
        encrypted_iban = None
        iban_last_four = None
        if iban:
            try:
                encrypted_iban = self.encryption_service.encrypt(iban)
                iban_last_four = iban[-4:]  # Extract last 4 digits
            except Exception as e:
                logger.error(f"IBAN encryption failed: {e}")
                raise EncryptionError("Failed to encrypt IBAN")

        # Create account with all fields
        account = await self.account_repo.create(
            user_id=user_id,
            account_name=account_name,
            account_type=account_type,
            currency=currency,
            opening_balance=opening_balance,
            current_balance=opening_balance,
            color_hex=color_hex,
            icon_url=icon_url,
            bank_name=bank_name,
            iban=encrypted_iban,
            iban_last_four=iban_last_four,
            notes=notes,
            # ... audit fields ...
        )

        # Audit logging (include metadata)
        # ...

        return account

    async def update_account(
        self,
        # ... existing params ...
        color_hex: str | None = None,
        icon_url: str | None = None,
        notes: str | None = None,
    ) -> Account:
        # Note: IBAN and bank_name are NOT updateable
        # Get existing account
        # ...

        # Update only allowed fields
        update_data = {}
        if color_hex is not None:
            update_data["color_hex"] = color_hex
        if icon_url is not None:
            update_data["icon_url"] = icon_url
        if notes is not None:
            update_data["notes"] = notes

        # Perform update
        # ...
```

---

#### Component: Database Migration

**Files Involved**:
- `alembic/versions/4aabd1426c98_initial_schema.py`

**Purpose**: Update the existing migration to add six new columns to the `accounts` table. This approach avoids creating a new migration file and allows for a clean schema state.

**Implementation Requirements**:

1. **Core Logic**:
   - Modify the `upgrade()` function in the existing migration
   - Add six new columns to the `accounts` table creation statement
   - Add default value for `color_hex` column
   - Update the `downgrade()` function (columns will be dropped automatically with table)

2. **Data Handling**:
   - **Column Definitions**:
     ```python
     sa.Column('color_hex', sa.String(length=7), nullable=False, server_default='#818E8F')
     sa.Column('icon_url', sa.String(length=500), nullable=True)
     sa.Column('bank_name', sa.String(length=100), nullable=True)
     sa.Column('iban', sa.Text(), nullable=True)
     sa.Column('iban_last_four', sa.String(length=4), nullable=True)
     sa.Column('notes', sa.String(length=500), nullable=True)
     ```
   - **Placement**: Add after `is_active` column, before timestamp columns

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Migration run on existing database → Drop and recreate database (early development phase)
   - [ ] Handle case: Default color not applied → Server default ensures it
   - [ ] Validate: Column names don't conflict with PostgreSQL reserved words → All clear
   - [ ] Validate: Text type supports large encrypted IBANs → Yes (unlimited length)

4. **Dependencies**:
   - Alembic migration framework
   - SQLAlchemy column definitions

5. **Testing Requirements**:
   - [ ] Test: Run migration on fresh database succeeds
   - [ ] Test: Verify all columns created with correct types
   - [ ] Test: Verify default color_hex applied to new rows
   - [ ] Test: Verify NULL allowed for optional columns
   - [ ] Test: Downgrade migration removes columns correctly

**Acceptance Criteria**:
- [ ] All six columns added to accounts table
- [ ] Default color_hex value set correctly
- [ ] NULL constraints correct (optional fields nullable)
- [ ] Migration runs successfully without errors
- [ ] Downgrade works correctly

**Implementation Notes**:
- No data migration needed (no existing accounts in early development phase)
- If database has existing accounts, this approach will fail → Document requirement to drop/recreate
- Alternative for production: Create new migration with `ADD COLUMN` statements (future)
- Consider adding comments to columns for documentation (`comment='...'` parameter)

**Code Example**:
```python
# In 4aabd1426c98_initial_schema.py, within op.create_table('accounts', ...):

def upgrade() -> None:
    # ... existing table creation ...
    op.create_table(
        'accounts',
        # ... existing columns ...
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),

        # NEW: Account metadata fields
        sa.Column('color_hex', sa.String(length=7), nullable=False,
                  server_default='#818E8F',
                  comment='Hex color code for UI display'),
        sa.Column('icon_url', sa.String(length=500), nullable=True,
                  comment='URL or path to account icon'),
        sa.Column('bank_name', sa.String(length=100), nullable=True,
                  comment='Name of the financial institution'),
        sa.Column('iban', sa.Text(), nullable=True,
                  comment='Encrypted IBAN (full account number)'),
        sa.Column('iban_last_four', sa.String(length=4), nullable=True,
                  comment='Last 4 digits of IBAN for display'),
        sa.Column('notes', sa.String(length=500), nullable=True,
                  comment='User notes about the account'),

        # ... existing timestamp and audit columns ...
    )
```

---

#### Component: Configuration Updates

**Files Involved**:
- `src/core/config.py`
- `.env.example`

**Purpose**: Add configuration for encryption key derivation (uses existing SECRET_KEY, no new env var needed).

**Implementation Requirements**:

1. **Core Logic**:
   - NO new configuration needed
   - Encryption uses existing `SECRET_KEY` from settings
   - Document in comments that SECRET_KEY is used for IBAN encryption

2. **Data Handling**:
   - Encryption key derived from existing `SECRET_KEY` using PBKDF2
   - No additional environment variables required

3. **Edge Cases & Error Handling**:
   - [ ] Validate: SECRET_KEY is at least 32 characters (already enforced)
   - [ ] Handle case: SECRET_KEY changed after IBANs encrypted → Data loss (document in production notes)

4. **Dependencies**:
   - None (uses existing settings)

5. **Testing Requirements**:
   - [ ] Test: Encryption service initializes with SECRET_KEY
   - [ ] Test: Encryption deterministic with same SECRET_KEY

**Acceptance Criteria**:
- [ ] No new environment variables added
- [ ] Documentation updated to mention encryption usage
- [ ] Warning added about SECRET_KEY rotation implications

**Implementation Notes**:
- In production, SECRET_KEY rotation requires re-encryption of all IBANs (future feature)
- Consider adding dedicated `ENCRYPTION_KEY` in future for key rotation support
- Document in README.md that SECRET_KEY is used for IBAN encryption

---

### 2.2 Detailed File Specifications

#### `src/services/encryption_service.py`

**Purpose**: Centralized encryption/decryption service for sensitive data

**Implementation**:
```python
"""
Encryption service for sensitive data (IBAN, etc.).

Uses Fernet (AES-128-CBC + HMAC) for authenticated encryption.
Key is derived from SECRET_KEY using PBKDF2-HMAC-SHA256.
"""

import base64
import logging
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from src.core.config import settings
from src.exceptions import EncryptionError

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet (symmetric encryption) with key derived from SECRET_KEY.
    All encrypted data is authenticated (tamper-proof).
    """

    def __init__(self):
        """Initialize encryption service with derived key."""
        try:
            # Derive encryption key from SECRET_KEY using PBKDF2
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'emerald-iban-encryption-salt',  # Static salt
                iterations=100000  # OWASP recommended minimum
            )
            key_material = kdf.derive(settings.secret_key.encode())
            key = base64.urlsafe_b64encode(key_material)
            self.cipher = Fernet(key)
            logger.info("Encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise ValueError("Encryption service initialization failed")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt (e.g., IBAN)

        Returns:
            Encrypted string (base64-encoded Fernet token)

        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return ""

        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError("Failed to encrypt data")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Encrypted string (Fernet token)

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionError: If decryption fails (invalid token, tampered data)
        """
        if not ciphertext:
            return ""

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid or tampered ciphertext")
            raise EncryptionError("Failed to decrypt data (invalid or tampered)")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError("Failed to decrypt data")


# Singleton instance
encryption_service = EncryptionService()
```

**Edge Cases**:
- Empty string: Returns empty string (no encryption)
- Invalid ciphertext: Raises EncryptionError with clear message
- SECRET_KEY change: All existing ciphertexts become undecryptable (document this)

**Tests**:
- Encrypt then decrypt returns original
- Same plaintext produces different ciphertexts (Fernet includes random IV)
- Tampered ciphertext raises EncryptionError
- Empty string handled correctly

---

#### `src/exceptions.py`

**Purpose**: Add custom exception for encryption errors

**Implementation**:
```python
# Add to existing exceptions.py:

class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass
```

---

## 3. Implementation Roadmap

### 3.1 Phase Breakdown

#### Phase 1: Foundation & Encryption Service (Size: S, Priority: P0)

**Goal**: Establish encryption infrastructure and update database schema. This phase delivers the foundational components needed for secure IBAN storage without exposing any user-facing features yet.

**Scope**:
- ✅ Include: Encryption service, database migration, model updates
- ❌ Exclude: API integration, Pydantic schema updates (Phase 2)

**Components to Implement**:
- [ ] Encryption Service (NEW)
- [ ] Database Migration (MODIFY)
- [ ] Account Model (MODIFY)
- [ ] Configuration (DOCUMENT)

**Detailed Tasks**:

1. [ ] **Set up dependencies**
   - Add `cryptography>=41.0.0` to `pyproject.toml`
   - Add `schwifty>=2023.11.0` to `pyproject.toml`
   - Run `uv sync` to install dependencies
   - Verify imports work in Python REPL

2. [ ] **Implement EncryptionService**
   - Create `src/services/encryption_service.py`
   - Implement `__init__` with key derivation (PBKDF2)
   - Implement `encrypt(plaintext: str) -> str` method
   - Implement `decrypt(ciphertext: str) -> str` method
   - Add `EncryptionError` to `src/exceptions.py`
   - Add comprehensive docstrings and type hints

3. [ ] **Add unit tests for EncryptionService**
   - Create `tests/unit/services/test_encryption_service.py`
   - Test: Encrypt then decrypt returns original
   - Test: Same plaintext produces different ciphertexts
   - Test: Tampered ciphertext raises EncryptionError
   - Test: Empty string handling
   - Test: Key derivation is deterministic
   - Achieve 100% coverage for encryption service

4. [ ] **Update Account model**
   - Modify `src/models/account.py`
   - Add six new mapped columns (color_hex, icon_url, bank_name, iban, iban_last_four, notes)
   - Add inline documentation for each field
   - Update `__repr__` method to include bank_name

5. [ ] **Update database migration**
   - Modify `alembic/versions/4aabd1426c98_initial_schema.py`
   - Add six new columns to accounts table creation
   - Add server_default for color_hex
   - Add comments to columns
   - Test migration on fresh database

6. [ ] **Drop and recreate database**
   - Run `docker-compose down -v` (destroys data)
   - Run `docker-compose up -d`
   - Run `uv run alembic upgrade head`
   - Verify all columns created: `docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "\d accounts"`

**Dependencies**:
- Requires: Fresh database (or willingness to drop existing data)
- Blocks: Phase 2 (API integration depends on this)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (minimum 80% coverage for new code)
- [ ] Encryption service encrypts and decrypts correctly
- [ ] Database schema includes all new columns
- [ ] Migration runs successfully without errors
- [ ] Manual testing: Create account in Python REPL with new fields

**Risk Factors**:
- **Risk**: SECRET_KEY rotation breaks existing encrypted IBANs
  - **Mitigation**: Document clearly in README.md and code comments
  - **Future**: Implement key versioning and re-encryption mechanism
- **Risk**: Fernet token size larger than expected
  - **Mitigation**: Use TEXT column (unlimited size in PostgreSQL)

**Estimated Effort**: 1-2 days for 1 developer

---

#### Phase 2: API Integration & Validation (Size: M, Priority: P0)

**Goal**: Integrate new metadata fields into API layer with full validation. This phase makes the feature accessible to frontend applications with comprehensive input validation.

**Scope**:
- ✅ Include: Pydantic schemas, service layer updates, API endpoint integration
- ❌ Exclude: Frontend UI implementation (separate project)

**Components to Implement**:
- [ ] Pydantic Schemas (MODIFY)
- [ ] Account Service (MODIFY)
- [ ] API Routes (VERIFY)

**Detailed Tasks**:

1. [ ] **Update Pydantic schemas**
   - Modify `src/schemas/account.py`
   - Update `AccountCreate`: Add iban, color_hex, icon_url, bank_name, notes
   - Update `AccountUpdate`: Add color_hex, icon_url, notes (no iban/bank_name)
   - Update `AccountResponse`: Add color_hex, icon_url, bank_name, iban_last_four, notes (NO iban)
   - Update `AccountListItem`: Add color_hex, icon_url, bank_name
   - Add `@field_validator` for color_hex (regex pattern)
   - Add `@field_validator` for iban (schwifty validation)
   - Add Field examples for API documentation

2. [ ] **Update AccountService**
   - Modify `src/services/account_service.py`
   - Inject `EncryptionService` into `__init__`
   - Update `create_account` signature: Add new parameters
   - Implement IBAN encryption logic in create_account
   - Implement last-four extraction logic
   - Update `update_account` signature: Add updateable fields
   - Ensure IBAN and bank_name are immutable (not in update)
   - Update audit logging to include metadata changes

3. [ ] **Update dependency injection**
   - Modify `src/api/dependencies.py`
   - Update `get_account_service` to pass encryption_service
   - Ensure encryption_service is singleton

4. [ ] **Verify API routes**
   - Check `src/api/routes/accounts.py`
   - Verify routes automatically accept new schema fields (no changes needed)
   - Test with Swagger UI (http://localhost:8000/docs)

5. [ ] **Add integration tests**
   - Create `tests/integration/test_accounts_metadata.py`
   - Test: Create account with all metadata fields
   - Test: Create account with IBAN encrypts correctly
   - Test: Create account without optional fields (defaults applied)
   - Test: Update account with color_hex changes color
   - Test: Update account with notes changes notes
   - Test: Attempt to update IBAN fails (immutable)
   - Test: Invalid hex color rejected (422 error)
   - Test: Invalid IBAN rejected (422 error)
   - Test: API response includes iban_last_four but not iban
   - Test: List endpoint includes metadata fields

6. [ ] **Manual API testing**
   - Start dev server: `uv run uvicorn src.main:app --reload`
   - Test POST /api/v1/accounts with all metadata fields
   - Test PUT /api/v1/accounts/{id} with updateable fields
   - Test GET /api/v1/accounts/{id} returns metadata
   - Test GET /api/v1/accounts returns list with metadata
   - Verify IBAN never appears in responses

**Dependencies**:
- Requires: Phase 1 complete (encryption service, model updates)
- Blocks: Phase 3 (testing depends on API integration)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (minimum 80% coverage for new code)
- [ ] API accepts and returns all metadata fields
- [ ] IBAN validation working correctly
- [ ] Color validation working correctly
- [ ] IBAN encrypted before storage
- [ ] iban_last_four displayed correctly
- [ ] Immutability enforced (IBAN, bank_name)
- [ ] Swagger UI documentation updated with new fields

**Risk Factors**:
- **Risk**: Schwifty library incompatible with Python 3.13
  - **Mitigation**: Test installation first, use alternative library if needed
- **Risk**: Pydantic validation too strict (rejects valid IBANs)
  - **Mitigation**: Comprehensive test suite with real IBAN examples from multiple countries

**Estimated Effort**: 2-3 days for 1 developer

---

#### Phase 3: Testing & Documentation (Size: S, Priority: P1)

**Goal**: Achieve comprehensive test coverage and update all documentation. This phase ensures the feature is production-ready and well-documented for other developers.

**Scope**:
- ✅ Include: Unit tests, integration tests, documentation updates
- ❌ Exclude: Performance testing (future phase)

**Components to Implement**:
- [ ] Comprehensive test suite
- [ ] Documentation updates (README, API docs, code comments)

**Detailed Tasks**:

1. [ ] **Complete test coverage**
   - Run `uv run pytest tests/ --cov=src --cov-report=term-missing`
   - Identify uncovered lines
   - Add missing unit tests
   - Add missing integration tests
   - Target: 80% minimum coverage for new code
   - Target: 100% coverage for encryption service and IBAN handling

2. [ ] **Add edge case tests**
   - Test: IBAN with spaces and hyphens normalized correctly
   - Test: Maximum length values (500 char notes, 100 char bank_name)
   - Test: Unicode characters in notes and bank_name
   - Test: SQL injection attempts in notes field (Pydantic + SQLAlchemy should prevent)
   - Test: XSS attempts in icon_url (Pydantic HttpUrl should prevent)

3. [ ] **Add E2E tests**
   - Test: Complete user workflow - create account with IBAN, retrieve, update notes
   - Test: Create multiple accounts with different colors
   - Test: Filter accounts by bank_name (if filtering implemented)

4. [ ] **Update documentation**
   - Update `README.md`: Document new metadata fields
   - Update `CLAUDE.md`: Add section on encryption service
   - Update API documentation in route docstrings
   - Add migration notes (database recreation required)
   - Document IBAN security considerations
   - Document SECRET_KEY rotation implications

5. [ ] **Update .env.example**
   - Add comment explaining SECRET_KEY used for IBAN encryption
   - Add warning about key rotation

6. [ ] **Code quality checks**
   - Run `uv run ruff format .`
   - Run `uv run ruff check --fix .`
   - Run `uv run mypy src/`
   - Fix all type errors and linting issues

**Dependencies**:
- Requires: Phase 1 and Phase 2 complete
- Blocks: Nothing (feature complete after this phase)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (100% success rate)
- [ ] Test coverage ≥ 80% for new code
- [ ] Test coverage = 100% for encryption service
- [ ] No linting errors (Ruff)
- [ ] No type errors (MyPy)
- [ ] Documentation updated and accurate
- [ ] Code reviewed by peer (if applicable)

**Risk Factors**:
- **Risk**: Test coverage difficult to achieve
  - **Mitigation**: Focus on critical paths first (IBAN encryption, validation)
- **Risk**: Documentation out of sync with code
  - **Mitigation**: Review docs immediately after code changes

**Estimated Effort**: 1-2 days for 1 developer

---

### 3.2 Implementation Sequence

```
Phase 1: Foundation (P0, 1-2 days)
  - Encryption Service + Database Schema
  ↓
Phase 2: API Integration (P0, 2-3 days)
  - Pydantic Schemas + Service Layer + API Routes
  ↓
Phase 3: Testing & Docs (P1, 1-2 days)
  - Comprehensive Tests + Documentation Updates
```

**Rationale for ordering**:
- **Phase 1 first**: Establishes secure foundation (encryption) and database schema before exposing to API
- **Phase 2 depends on Phase 1**: Cannot integrate API without encryption service and database columns
- **Phase 3 last**: Testing and documentation require complete implementation to validate

**Total Estimated Effort**: 4-7 days for 1 developer (or 2-4 days with 2 developers working in parallel)

**Quick Wins**:
- After Phase 1: Encryption service can be tested in isolation (Python REPL)
- After Phase 2: Feature is fully functional and can be demoed to stakeholders
- After Phase 3: Feature is production-ready

---

## 4. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. We're adding fields to existing model rather than creating new tables (normalized approach)
  - Using proven encryption library (Fernet) instead of rolling our own crypto
  - Reusing existing SECRET_KEY instead of adding new encryption keys
  - No over-engineering: IBAN never decrypted in normal operations (display-only last 4 digits)

- [x] **Have we avoided premature optimization?**
  - Yes. No caching layer for metadata (not needed, fast reads)
  - No database indexes on new fields (optimize later if filtering by bank becomes common)
  - No key rotation mechanism (implement only if SECRET_KEY changes become common)
  - No separate key management system (KMS) for initial phase

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows 3-layer architecture: routes → services → repositories
  - Uses Pydantic for validation (consistent with existing account fields)
  - Uses SQLAlchemy mapped columns (consistent with Account model)
  - Service layer handles encryption (consistent with password hashing in auth)
  - Audit logging for changes (consistent with existing account operations)

- [x] **Can we deliver value in smaller increments?**
  - Yes. Three phases with independent value:
    - Phase 1: Encryption foundation (testable in isolation)
    - Phase 2: API integration (usable by frontend)
    - Phase 3: Production readiness (comprehensive testing)

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. Feature description explicitly requests these fields:
    - color_hex: For visual identification in UI (confirmed by "frontend designs show bank name")
    - bank_name: Track which bank (explicitly requested)
    - IBAN: Full account number for user reference (explicitly requested, encryption needed for PCI compliance)
    - iban_last_four: Display without decryption (UX best practice)
    - notes: Personal descriptions (common feature request)

### Alternatives Considered

**Alternative 1: Separate BankDetails table**
- **Description**: Create new `bank_details` table with one-to-one relationship to accounts
- **Pros**: Normalized schema, separates concerns
- **Cons**: Adds complexity (joins required), over-engineering for 6 fields
- **Why not chosen**: YAGNI (You Aren't Gonna Need It) - no benefit for 6 simple fields

**Alternative 2: JSONB column for all metadata**
- **Description**: Store all metadata in single `metadata` JSONB column
- **Pros**: Flexible schema, easy to add fields later
- **Cons**: Lose type safety, harder to query/filter, no schema validation at DB level
- **Why not chosen**: Type safety and explicit schema more important than flexibility

**Alternative 3: Encrypt all fields (color, notes, etc.)**
- **Description**: Encrypt all metadata, not just IBAN
- **Pros**: Maximum security
- **Cons**: Performance overhead, unnecessary (color/notes not sensitive)
- **Why not chosen**: Over-engineering, only IBAN needs encryption per compliance requirements

**Alternative 4: Store IBAN hash instead of encryption**
- **Description**: Hash IBAN (like passwords), never decrypt
- **Pros**: Simpler (no decryption logic)
- **Cons**: Cannot display IBAN if user forgets it, less useful
- **Why not chosen**: Need to support user retrieval of IBAN (future admin feature)

**Alternative 5: Use database-level encryption (pgcrypto)**
- **Description**: PostgreSQL pgcrypto extension for transparent encryption
- **Pros**: Encryption handled by database
- **Cons**: Less portable, harder to test, limited to PostgreSQL
- **Why not chosen**: Application-level encryption more portable and testable

### Rationale for Proposed Approach

**Why this approach is preferred**:
1. **Simplicity**: Adds columns to existing table (no new tables or complex joins)
2. **Security**: IBAN encrypted at application layer (portable, testable, secure)
3. **Performance**: No decryption in normal operations (display last 4 only)
4. **Maintainability**: Follows existing codebase patterns (3-layer architecture, Pydantic validation)
5. **Testability**: Encryption service testable in isolation
6. **Compliance**: Meets PCI DSS requirement for encrypted storage of full account numbers
7. **User Experience**: Last 4 digits displayed without decryption overhead

---

## 5. References & Related Documents

### Security & Encryption Best Practices

- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html) - Best practices for encrypting sensitive data
- [Best Practices for Secure Data Encryption in Financial Applications](https://medium.com/@puneett.bhatnagr/best-practices-for-secure-data-encryption-in-financial-applications-0ef8da344be3) - AES-256, TLS 1.3, and multi-layer encryption
- [Should IBAN and bank details be considered private data and encrypted?](https://security.stackexchange.com/questions/51543/should-iban-and-bank-details-be-considered-private-data-and-encrypted) - Discussion on IBAN encryption necessity
- [PSD2 Clarification on IBAN Protection Requirements](https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2020_5477) - European Banking Authority guidance on IBAN security

### Banking App UX Design

- [Top 15 Banking Apps with Exceptional UX Design (2025)](https://www.wavespace.agency/blog/banking-app-ux) - Industry-leading examples of account visualization
- [Banking App UI: Top 10 Best Practices in 2025](https://procreator.design/blog/banking-app-ui-top-best-practices/) - Visual customization trends
- [Top Mobile Banking Apps to Checkout in 2025](https://www.nimbleappgenie.com/blogs/top-mobile-banking-apps/) - Popular banks and their UI patterns

### Technical Documentation

- [Cryptography Library Documentation](https://cryptography.io/en/latest/) - Official documentation for Fernet encryption
- [Schwifty IBAN Validation](https://github.com/mdomke/schwifty) - Python library for IBAN validation
- [Pydantic Field Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Custom validation in Pydantic v2
- [SQLAlchemy Mapped Columns](https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html#orm-declarative-mapped-column) - SQLAlchemy 2.0 mapping syntax
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/) - Security patterns in FastAPI

### Related Internal Documentation

- `.claude/standards/backend.md` - Backend development standards for this project
- `.claude/standards/database.md` - Database migration and schema standards
- `.claude/standards/api.md` - API endpoint design standards
- `.claude/standards/testing.md` - Testing requirements and coverage standards
- `CLAUDE.md` - Project overview and architecture (this document)
- `README.md` - Getting started guide for developers

### Compliance & Regulations

- [PCI DSS Requirements for Account Data Storage](https://www.pcisecuritystandards.org/) - Payment Card Industry Data Security Standard
- [GDPR Data Protection Guidelines](https://gdpr.eu/) - European data protection regulations
- [SOX Compliance for Financial Records](https://www.soxlaw.com/) - 7-year record retention requirements

---

## Appendix: Testing Strategy

### Unit Tests

**Encryption Service Tests** (`tests/unit/services/test_encryption_service.py`):
- Test encrypt and decrypt roundtrip
- Test different plaintexts produce different ciphertexts
- Test tampered ciphertext raises error
- Test empty string handling
- Test key derivation determinism

**Schema Validation Tests** (`tests/unit/schemas/test_account_schemas.py`):
- Test valid hex color passes validation
- Test invalid hex colors fail (#GGGGGG, #12345, abc123)
- Test valid IBAN passes (multiple country codes)
- Test invalid IBAN fails (bad checksum, wrong format)
- Test IBAN normalization (spaces/hyphens removed)
- Test icon_url URL validation

### Integration Tests

**Account Metadata Tests** (`tests/integration/test_accounts_metadata.py`):
- Test create account with all metadata fields
- Test create account with IBAN (verify encryption)
- Test create account without optional fields (defaults)
- Test update account color_hex
- Test update account notes
- Test attempt to update IBAN (should fail)
- Test attempt to update bank_name (should fail)
- Test API response excludes full IBAN
- Test API response includes iban_last_four
- Test list endpoint includes metadata

### Test Coverage Goals

- **Overall**: 80% minimum for new code
- **Encryption Service**: 100% (critical security component)
- **Account Service (metadata logic)**: 90%+
- **Pydantic Validators**: 100% (all validation paths tested)
- **API Routes**: 80%+ (happy path + error cases)

---

## Appendix: Security Considerations

### IBAN Encryption

- **Algorithm**: Fernet (AES-128-CBC + HMAC-SHA256)
- **Key Derivation**: PBKDF2-HMAC-SHA256, 100,000 iterations
- **Authentication**: Built-in HMAC prevents tampering
- **Threat Model**: Protects against database compromise (encrypted at rest)

### What's Encrypted

- ✅ **Full IBAN**: Encrypted before storage
- ❌ **Last 4 Digits**: Plaintext (for display, not sensitive)
- ❌ **Bank Name**: Plaintext (public information)
- ❌ **Color/Icon**: Plaintext (not sensitive)
- ❌ **Notes**: Plaintext (user's own data, not regulated)

### Key Management

- **Current**: Derived from SECRET_KEY
- **Future**: Dedicated ENCRYPTION_KEY for key rotation
- **Rotation**: Requires re-encryption of all IBANs (not implemented in this phase)

### Compliance

- **PCI DSS**: Full account numbers must be encrypted ✅
- **GDPR**: User data protected with encryption ✅
- **PSD2**: IBAN protection measures implemented ✅

### Attack Vectors Considered

- **SQL Injection**: Prevented by SQLAlchemy ORM + Pydantic validation ✅
- **XSS in icon_url**: Prevented by Pydantic HttpUrl validation ✅
- **Tampering with encrypted IBAN**: Prevented by Fernet HMAC ✅
- **Database compromise**: IBAN remains encrypted at rest ✅
- **Man-in-the-middle**: HTTPS required in production ✅

---
