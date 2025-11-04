# Phase 2: Account Management

## Personal Finance Platform Backend

**Objective:** Build account creation, management, and sharing capabilities that form the foundation for transaction handling.

**Prerequisite:** Phase 1 (core architecture and authentication) must be complete.

---

## REQUIREMENTS

### 1. Account Model
- Account model with fields: id, user_id (owner), account_name, account_type, currency, opening_balance, current_balance, is_active, created_at, updated_at, deleted_at, created_by, updated_by
- Support account types: savings, credit_card, debit_card, loan, investment, other
- Each account belongs to a single user (owner)
- Account currency is immutable after creation
- Soft delete support (deleted_at field)

### 2. Account CRUD Operations
- Create account endpoint (authenticated user)
- Get account by ID endpoint (owner or user with access)
- List all accounts for authenticated user with pagination
- Update account endpoint (owner only): update name, is_active status
- Soft delete account endpoint (owner only): set deleted_at timestamp
- Accounts must not appear in normal queries when soft deleted
- Transaction history preserved after account deletion

### 3. Account Access & Sharing
- Account share model with fields: id, account_id, user_id (recipient), permission_level, created_at, updated_at, deleted_at, created_by
- Permission levels: owner, editor, viewer
- Owner can share account with other users
- Shared account access is revocable (soft delete the share)
- Users can only see accounts they own or have been granted access to
- Different users can have different permission levels on same account
- Audit log all access permission changes

### 4. Account Permissions
- Owner: full access (read, write, delete, manage sharing)
- Editor: read and write access, cannot delete or change sharing
- Viewer: read-only access
- Endpoint authorization must check permission level
- Audit trail of all permission changes

### 5. Balance Calculation
- Current account balance calculated from transactions (not manually set)
- Balance must be derived from: opening_balance + sum(all non-deleted transactions)
- Historical balance must be retrievable for any date
- Balance calculations must be accurate to 2 decimal places
- Balance updates trigger audit logging

### 6. Account Endpoints

#### POST /api/v1/accounts
- Create new account
- Required fields: account_name, account_type, currency, opening_balance
- Response: Created account object with id and timestamps
- Only authenticated users can create accounts
- Audit log account creation

#### GET /api/v1/accounts/{account_id}
- Get account details
- Response: Full account object including current_balance
- Authorization: Owner or user with access
- Return 404 if account not found or user has no access

#### GET /api/v1/accounts
- List all accounts for authenticated user
- Query parameters: skip, limit, is_active (filter), sort_by (name, created_at)
- Response: Paginated list with total count
- Include only accounts user owns or has access to
- Exclude soft-deleted accounts

#### PUT /api/v1/accounts/{account_id}
- Update account details
- Allowed fields: account_name, is_active
- Response: Updated account object
- Authorization: Owner only
- Audit log all changes

#### DELETE /api/v1/accounts/{account_id}
- Soft delete account
- Response: 204 No Content
- Authorization: Owner only
- Audit log deletion
- Preserve transaction history

### 7. Account Sharing Endpoints

#### POST /api/v1/accounts/{account_id}/share
- Share account with another user
- Request body: target_user_id, permission_level (owner/editor/viewer)
- Response: Share record with id and timestamps
- Authorization: Current owner only
- Cannot share with user who already has access (error)
- Cannot downgrade owner permission (error)
- Audit log share creation

#### GET /api/v1/accounts/{account_id}/share
- List users account is shared with
- Response: List of share records with user details
- Authorization: Owner or user with access (can only see their own entry)
- Include permission level and share timestamps

#### PUT /api/v1/accounts/{account_id}/share/{share_id}
- Update permission level for shared account
- Request body: permission_level
- Response: Updated share record
- Authorization: Current owner only
- Cannot change own owner permission (error)
- Audit log permission change

#### DELETE /api/v1/accounts/{account_id}/share/{share_id}
- Revoke account access from user
- Response: 204 No Content
- Authorization: Current owner only
- Soft delete the share record (set deleted_at)
- Audit log access revocation

### 8. Multi-Currency Support
- Each account has a single currency (e.g., USD, EUR, GBP)
- Currency is immutable after account creation
- Support all ISO 4217 currencies
- Store currency as code (3-letter, uppercase)

### 9. Data Integrity
- Account cannot be deleted if it has associated transactions (soft delete only)
- Account balance must always match calculation from transactions
- Sharing permissions must be checked before any account access
- Cannot share account with user that is deleted or inactive (validation)
- Deleted users cannot access shared accounts

### 10. Audit Logging
- Log account creation with account details
- Log account updates with old/new values
- Log account deletion
- Log all sharing operations (create, update, delete)
- Log all access permission changes
- All audit entries include user_id and timestamp

### 11. Validation
- Account name: 1-100 characters, required
- Account type: must be from defined list
- Currency: valid ISO 4217 code
- Opening balance: decimal number, can be negative
- User ID references must exist and not be deleted
- Account name must be unique per user (cannot have duplicate names for same user)

### 12. Error Handling
- 400: Account name already exists for user, invalid account type, invalid currency
- 401: Not authenticated
- 403: User does not have permission to access account, cannot share with that user
- 404: Account not found, user not found, share not found
- 422: Validation error (invalid balance, name too long, etc.)

### 13. Response Format
All account responses include:
- id (UUID)
- user_id
- account_name
- account_type
- currency
- opening_balance
- current_balance
- is_active
- created_at
- updated_at

Share responses include:
- id (UUID)
- account_id
- user_id
- permission_level
- created_at
- user object (username, email, full_name)

### 14. Testing
- Unit tests for account creation and validation
- Unit tests for balance calculation logic
- Unit tests for permission checking
- Integration tests for all account endpoints
- Integration tests for sharing and permission changes
- Test concurrent access scenarios
- Test soft delete behavior
- Test paginated list queries
- Minimum 80% code coverage for account-related code
- All tests pass

### 15. Documentation
- Document all account endpoints in OpenAPI
- Document permission levels and access control rules
- Document balance calculation logic
- Document multi-currency behavior
- Update README with account management section

---

## ACCEPTANCE CRITERIA

Phase 2 is complete when:

1. User can create accounts with name, type, currency, opening balance
2. User can list all their accounts with pagination
3. User can retrieve a specific account and see current balance
4. User can update account name and active status
5. User can soft delete their account (data preserved)
6. User can share account with another user and set permission level
7. User can list all users an account is shared with
8. User can change permission level for shared users
9. User can revoke access from shared users
10. Shared users can only access accounts shared with them
11. Different permission levels (owner, editor, viewer) work correctly
12. Only owners can modify or delete accounts
13. Only owners can manage account sharing
14. Current balance is calculated correctly from transactions (once transactions exist)
15. Audit logs all account operations and sharing changes
16. Validation prevents invalid data (bad currency, duplicate names, etc.)
17. Soft deleted accounts don't appear in normal queries
18. Account deletion preserves transaction history
19. All endpoints return proper error codes and messages
20. All tests pass with 80%+ coverage

---

## DEPENDENCIES

- Phase 1 (authentication, user management, audit logging) must be complete
- Transaction model exists (partial, for balance calculations)
- All endpoints require authentication