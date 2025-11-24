# Personal Finance Platform - Backend Requirements

## 0. Project Overview

A backend API system for personal finance management that enables users to:
- Manage multiple bank accounts
- Import and track financial transactions
- Organize transactions with flexible categorization
- Automatically categorize transactions based on custom rules
- Generate financial analytics and insights
- Share account access with family members
- Maintain audit trails for accountability

**Scope:** Self-hosted backend providing data management and business logic
**Users:** 1-5 concurrent users initially
**Data Scale:** ~100 transactions per account per month (modest scale)

---

## 1. TECHNOLOGY STACK & DEPENDENCIES

### Core Backend
- **Framework:** FastAPI
- **Python Version:** 3.13+
- **ORM:** SQLAlchemy 
- **Database Driver:** psycopg-binary (PostgreSQL)
- **Migration Tool:** Alembic
- **Async-First Support**

### Authentication & Security
- **Password Hashing:** bcrypt 
- **JWT Tokens:** PyJWT
- **CORS:** fastapi-cors

### Data Processing
- **CSV Processing:** polars
- **Fuzzy Matching:** fuzzywuzzy
- **Regex:** Built-in (Python re module)

### Utilities
- **Validation:** pydantic
- **Date/Time:** python-dateutil
- **Environment Config:** pydantic-settings
- **Logging:** Built-in Python logging + structured logging (e.g., structlog)
- **Rate Limiting:** slowapi

### Development & Testing
- **Testing Framework:** pytest
- **Test Coverage:** pytest-cov
- **API Testing:** httpx
- **DB Testing:** pytest-asyncio
- **Linting:** black, flake8, isort

### Database
- **Primary DB:** PostgreSQL
- **Connection Pooling:** SQLAlchemy built-in with asyncio support (optional for future)

Use all Latest Stable Versions (LTS) for all the frameworks.

---

## 2. Authentication & User Management Requirements

### 2.1 User Registration & Authentication
- Users must be able to create new accounts with username and password
- Users must be able to log in with their credentials
- Authentication tokens must be issued upon successful login
- Tokens must have expiration to ensure security
- Users must be able to obtain new tokens when expired
- Users must be able to log out and invalidate their sessions
- Password must be securely hashed and never stored in plain text
- Passwords must have minimum security requirements

### 2.2 User Roles & Access Control
- System must support multiple user roles with different permission levels
- Admins must be able to manage system-level operations
- Users must only have access to their own data by default
- Users must be able to grant other users access to specific accounts
- Access permissions must be revocable at any time
- Users must have different permission levels (view-only, edit, full access)
- All permission changes must be traceable

### 2.3 User Data Management
- Users must be able to update their profile information
- Users must be able to change their password
- User accounts must support soft deletion (data retention)
- User account status must be trackable (active, inactive, deleted)

---

## 3. Account Management Requirements

### 3.1 Account Creation & Configuration
- Users must be able to create multiple accounts
- Each account must support different types (checking, savings, credit card, debit card, loan, etc.)
- Accounts must be associated with a specific currency
- Accounts must have an opening balance
- Accounts must record creation and modification timestamps
- Account names and identifying information must be customizable

### 3.2 Account Balance Tracking
- System must calculate and maintain current account balance
- Balance must be derived from transactions (not manually entered)
- Balance calculations must be accurate and up-to-date
- Historical balance information must be retrievable

### 3.3 Account Sharing & Permissions
- Account owners must be able to share accounts with other users
- Different permission levels must be assignable (owner, editor, viewer)
- Owners must be able to revoke access from other users
- Shared account access must be revocable at any time
- System must track who has access to each account
- Access changes must be auditable

### 3.4 Account Management
- Accounts must be updateable (name, details, metadata)
- Accounts must support soft deletion
- Deleted accounts must not appear in normal queries
- Account deletion must not lose transaction history

---

## 4. Transaction Management Requirements

### 4.1 Transaction Data Structure
- Transactions must store the following information:
  - Date of operation
  - Date of value
  - Amount (decimal precision)
  - Currency
  - Description/narrative
  - Merchant information (separate from description)
  - Transaction type (debit, credit, transfer, etc.)
  - User-provided comments/notes
  - Free-form tags
  - Associated account
  - Which user created/modified it

### 4.2 Transaction CRUD Operations
- Users must be able to create transactions manually
- Users must be able to view their transactions with full details
- Users must be able to edit transaction details
- Users must be able to delete transactions
- Deleted transactions must not appear in normal queries
- Transaction creation and modification must be timestamped
- User attribution must be tracked for all changes

### 4.3 Transaction Categorization
- Transactions must support multiple categories simultaneously
- Different categorization taxonomies must be applicable to same transaction
- Categories must be hierarchical (at least 2 levels)
- Categories must be customizable per user
- Predefined categories must be available
- Users must be able to show/hide predefined categories
- Users must be able to create custom categories
- Categories in use must not be deletable (prevent orphaning)
- Categories must be removable from transactions

### 4.4 Transaction Splitting
- Users must be able to split one transaction into multiple parts
- Split transactions must maintain a parent-child relationship
- Each split must independently support categorization and tags
- Split amounts must total the original transaction amount
- Split transactions must be reversible or joinable

### 4.5 Transaction Search & Filtering
- System must support searching transactions by:
  - Date range
  - Amount range
  - Description/merchant keywords
  - Tags
  - Categories
  - Account
  - Transaction type
- Search must support fuzzy matching (handle typos)
- Search must be real-time or near-real-time
- Multiple filters must be combinable
- Filter combinations must be saveable and reusable

---

## 5. CSV Import Requirements

### 5.1 CSV Upload & Processing
- Users must be able to upload CSV files containing transactions
- System must support different CSV formats from different banks
- Users must be able to specify which account the import targets
- CSV imports must be atomic (all or nothing)
- System must validate CSV data before importing

### 5.2 Column Mapping
- System must allow users to map CSV columns to transaction fields
- Column mapping must be selectable/configurable by user
- System must remember column mappings for future imports
- Different banks may have different column formats
- System must support dynamic column mapping (not hardcoded)

### 5.3 Duplicate Detection
- System must detect potential duplicate transactions during import
- Duplicates must be identified based on date, amount, and description similarity
- Users must be shown potential duplicates before import completion
- Users must be able to choose action for each duplicate (skip, import anyway, override)
- Duplicate detection must handle minor variations (typos, different formatting)

### 5.4 Import History & Rollback
- System must maintain import history with metadata
- Users must be able to view what was imported and when
- Users must be able to rollback an entire import
- Rollback must be safe and complete (remove all transactions from that import)
- Import status must be trackable (success, partial, failed)

### 5.5 Auto-Categorization During Import
- During import, system must apply auto-categorization rules
- Users must see preview of what will be auto-categorized
- Auto-categorization must be optional/confirmable

---

## 6. Categorization & Taxonomy Requirements

### 6.1 Taxonomy Structure
- System must support multiple independent taxonomies
- One taxonomy must be primary (main categories)
- Additional taxonomies must be secondary (for grouping purposes like "trips", "projects", "people")
- Both primary and secondary taxonomies must be hierarchical (2 levels)
- Both must be searchable and filterable

### 6.2 Primary Taxonomy (Categories)
- System must provide predefined category structure
- Users must be able to create custom categories
- Users must be able to show/hide predefined categories
- Predefined categories must not be editable
- Custom categories must be editable and deletable
- Categories must have associated metadata (color, icon for UI)

### 6.3 Secondary Taxonomies
- Users must be able to create custom secondary taxonomies
- Examples: "Trips", "Projects", "People Groups", "Spending Goals"
- Secondary taxonomies must have same hierarchical structure as primary
- Secondary taxonomies must be fully user-managed

### 6.4 Category/Taxonomy Management
- System must prevent deletion of categories/levels in use
- System must allow adding/removing categories to transactions
- System must allow moving/reorganizing hierarchy
- Multiple categories must be assignable to single transaction
- Different taxonomy types must be applicable simultaneously to same transaction

---

## 7. Auto-Categorization Rules Requirements

### 7.1 Rule Creation & Management
- Users must be able to create categorization rules
- Rules must support keyword matching
- Rules must support regex pattern matching
- Rules must have priority/order
- Rules must be assignable to specific accounts or all accounts
- Rules must be enable-able/disable-able without deletion
- Rules must be deletable

### 7.2 Rule Matching Logic
- Rules must match against transaction description and merchant
- Rules must support case-insensitive matching
- Rules must be applied in priority order
- Multiple rules may be tested but may stop at first match (configurable)
- Rules must be applicable retroactively to existing transactions

### 7.3 Rule Assignment
- Rules must be able to assign one or multiple categories
- Rules must be able to assign categories from different taxonomies
- Rules must work for both primary and secondary taxonomies
- Rule application must be previewable before execution

---

## 8. Analytics & Reporting Requirements

### 8.1 Spending Analysis
- System must calculate total spending by category
- System must calculate spending trends over time (daily, weekly, monthly, yearly)
- System must support custom date ranges for analysis
- System must calculate income vs expenses breakdown
- System must support filtering by:
  - Account
  - Category/taxonomy
  - Date ranges
  - Amount ranges

### 8.2 Analytics Calculations
- All calculations must be accurate to at least 2 decimal places
- Calculations must handle multiple currencies appropriately
- Calculations must be performant even with large transaction volumes
- Calculations must be repeatable (same inputs = same outputs)

### 8.3 Data Comparisons
- System must support month-over-month comparisons
- System must support year-over-year comparisons
- System must support period-over-period percentage changes
- Comparisons must be accurate and meaningful

---

## 9. Multi-Currency Requirements

### 9.1 Currency Support
- Each account must support a specific currency
- Transactions must include currency information
- System must differentiate between different currencies
- Transactions in different currencies must not be incorrectly combined

### 9.2 Currency Conversion
- Analytics must convert amounts to a common base currency for reporting
- Users must specify their preferred base currency
- Currency conversion rates must be obtainable (source TBD)
- Conversion must be accurate to at least 2 decimal places

---

## 10. Audit & Logging Requirements

### 10.1 Comprehensive Audit Trail
- System must log all user actions (create, read, update, delete)
- System must log authentication events (login, logout, failed attempts)
- System must log all data modifications
- System must log permission changes
- System must log rule creation/updates
- System must log CSV imports
- System must log category/taxonomy changes

### 10.2 Audit Log Details
- Each log entry must record:
  - Who performed the action (user attribution)
  - What changed (old value, new value)
  - When it happened (timestamp)
  - What type of action (create, update, delete, etc.)
  - Which entity was affected
  - Context (which account, transaction, etc.)

### 10.3 Audit Log Retention & Access
- Audit logs must be retained for minimum 1 year
- Users must be able to view logs of actions they performed
- Admins must be able to view all audit logs
- Audit logs must be immutable (cannot be edited or deleted)
- Logs must be queryable by date range, user, action type, entity type

---

## 11. Data Integrity Requirements

### 11.1 Soft Deletes
- Deleted entities must be marked as deleted (not physically removed)
- Deleted entities must not appear in normal queries
- Deleted entities must be traceable (when and who deleted)
- Deletion must be reversible or recoverable via audit logs

### 11.2 Referential Integrity
- Transactions must belong to valid accounts
- Categories must be assignable only if taxonomy exists
- Split transactions must maintain parent-child relationships
- Deleting parent entities must not orphan child entities

### 11.3 Data Consistency
- Account balances must always be consistent with transactions
- Transaction totals must match reported analytics
- Category/taxonomy consistency must be maintained

---

## 12. Performance & Scalability Requirements

### 12.1 Response Times
- API responses must be fast enough for good user experience
- Search queries must return results quickly
- Analytics calculations must complete in reasonable time
- Filtering and sorting must be responsive

### 12.2 Concurrent Users
- System must support 1-5 concurrent users without degradation
- System must handle requests from multiple users simultaneously
- Session management must prevent user data leakage

### 12.3 Data Volume Handling
- System must handle ~100 transactions per account per month (modest scale)
- System must handle multiple accounts per user
- System must handle complex filtering on large datasets

---

## 13. Security Requirements

### 13.1 Authentication Security
- Passwords must be securely hashed (not reversible)
- Authentication tokens must expire after defined period
- Refresh tokens must be available for obtaining new access tokens
- Sessions must be invalidatable
- Failed login attempts must be trackable

### 13.2 Authorization Security
- Users must only access their own data (unless explicitly shared)
- Admins must have system-wide access only to what they need
- Permission checks must happen on every data access
- Cross-user data access must be prevented
- Deleted data must not be accessible

### 13.3 Data Protection
- Sensitive data must not be exposed in error messages
- Sensitive data must not be logged
- Sensitive data must not be transmitted in plain text

### 13.4 Rate Limiting & Abuse Prevention
- System must implement rate limiting to prevent abuse
- Failed login attempts must be rate-limited
- API endpoints must have rate limits
- Rate limits must be per-user (not global)

---

## 14. Error Handling Requirements

### 14.1 Error Responses
- All errors must have meaningful error messages
- Error messages must not expose sensitive information
- Error messages must be consistent and structured
- Errors must have error codes for programmatic handling
- HTTP status codes must be appropriate for error type

### 14.2 Validation
- All user inputs must be validated
- Validation errors must be clear and actionable
- Invalid data must not be persisted
- Validation must occur before business logic execution

### 14.3 Edge Cases
- Concurrent updates must be handled (last-write-wins or conflicts)
- Partial failures must be handled gracefully
- Network timeouts must be handled
- Database connection failures must be handled

---

## 15. Integration Requirements

### 15.1 API Design
- API must be RESTful or similar standard
- API must use standard HTTP methods appropriately
- API endpoints must be discoverable and well-organized
- API must support standard content types (JSON)

### 15.2 Request/Response Contracts
- Request payloads must be validated before processing
- Response formats must be consistent
- Response payloads must include necessary data
- Error responses must follow consistent format

### 15.3 Pagination & Limits
- List endpoints must support pagination
- List endpoints must have configurable limits
- Pagination must be efficient
- Large datasets must be paginated (not returned all at once)

---

## 16. Data Retention Requirements

### 16.1 Data Preservation
- All user data must be preserved on soft delete
- Transaction history must be maintained even if account is deleted
- Audit logs must be preserved for 1 year minimum
- User can delete their own data if needed (future requirement)

### 16.2 Backup & Recovery
- System must be restorable from previous states (via audit logs)
- Data must be protected from accidental loss
- Backup strategy should be defined (manual export capability minimum)

---

## 17. Extensibility Requirements

### 17.1 Rule Engine Flexibility
- Auto-categorization rules must support new match types (future: AI-based)
- Rules must be composable (combine conditions)
- Rules must support more complex logic (future)

### 17.2 Analytics Extensibility
- Analytics framework must support new report types (future)
- Analytics must support additional groupings (future: by merchant, by tag, etc.)

### 17.3 Import Flexibility
- System must support new file formats (future: Excel, OFX, etc.)
- Column mapping must work with various formats
- Import process must be extensible for new bank formats

---

## 18. Documentation & Maintainability Requirements

### 18.1 API Documentation
- All endpoints must be documented
- Request/response examples must be provided
- Error cases must be documented
- API must be self-documenting or auto-generated

### 18.2 Code Quality
- Code must be maintainable and readable
- Business logic must be decoupled from infrastructure
- Testing must be comprehensive
- Documentation must be up-to-date with code

---

## 19. Testing Requirements

### 19.1 Unit Testing
- Core business logic must have unit tests
- Edge cases must be tested
- Error scenarios must be tested
- Target coverage: 80%+

### 19.2 Integration Testing
- API endpoints must be tested end-to-end
- Database interactions must be tested
- Business workflows must be tested
- Cross-system interactions must be tested

### 19.3 Test Data
- Test fixtures must be available for testing
- Sample data must be representative
- Tests must be isolated and repeatable

---

## 20. Deployment & Operations Requirements

### 20.1 Docker Support
- System must be containerizable
- Container must be self-contained (all dependencies included)
- Container must be configurable via environment variables

### 20.2 Configuration Management
- System must support environment-specific configuration
- Sensitive configuration must not be in code
- Configuration must be easy to change without rebuilding

### 20.3 Database Migrations
- Schema changes must be version-controlled
- Migrations must be forward-compatible
- Migrations must be reversible or trackable
- Migration history must be maintained

---

## 21. Monitoring & Observability Requirements

### 21.1 Logging
- Application must produce structured logs
- Logs must include relevant context (user, request ID, etc.)
- Logs must be queryable
- Different log levels must be supported

### 21.2 Health Monitoring
- System health must be checkable
- Critical services must be monitorable
- Failures must be detectable

---

## 22. Business Logic Requirements

### 22.1 Transaction Processing
- Transaction amounts must be precise (no floating-point errors)
- Multi-currency transactions must be handled correctly
- Split transactions must maintain total integrity
- Duplicate detection must be accurate

### 22.2 Rule Processing
- Rules must be applied deterministically
- Rule conflicts must be handled gracefully
- Rule performance must not degrade with rule count

### 22.3 Analytics Accuracy
- All calculations must be mathematically accurate
- Rounding must be consistent and documented
- Totals must match line items (no discrepancies)

---

## 23. Future Requirements (Out of Scope for MVP)

These are mentioned for architectural awareness:
- Investment account tracking with positions
- Budget tracking and alerts
- Bill payment tracking
- Recurring transactions
- Bank API integration (instead of CSV)
- Mobile app backend requirements
- Real-time notifications
- Subscription management
- Report generation and export (PDF, Excel)
- Forecasting and spending predictions

---

## 24. Non-Functional Requirements

### 24.1 Reliability
- System must have high availability for 1-5 users
- Data must not be lost in normal operation
- System must recover from failures gracefully

### 24.2 Maintainability
- Code must be easy to understand and modify
- Architecture must be clear and logical
- Changes must be implementable without large refactors

### 24.3 Usability (from API perspective)
- API must be intuitive to use
- Error messages must be helpful
- API must support common use cases directly

### 24.4 Compliance
- Data must be secure and private
- User data must be protected
- No unauthorized access to other users' data

---

## Summary of Key Requirements

**MUST HAVE:**
- User authentication and authorization
- Multi-account management
- Transaction CRUD with categorization
- CSV import with duplicate detection
- Auto-categorization rules
- Audit logging with 1-year retention
- Analytics (spending by category, trends)
- Multi-user access with permissions
- Soft deletes and data retention
- Security (rate limiting, hashing, validation)

**SHOULD HAVE:**
- Fuzzy search
- Regex-based rules
- Real-time filtering
- Export/rollback capabilities
- Dashboard customization support
- User settings and preferences

**NICE TO HAVE:**
- Advanced analytics (forecasting)
- Multi-currency conversion
- Historical data access
- API documentation automation
- Performance monitoring
