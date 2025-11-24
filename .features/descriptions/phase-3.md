# Phase 3: Transaction Management
## Personal Finance Platform Backend

**Objective:** Build comprehensive transaction handling with CRUD operations, categorization support, and transaction splitting.

**Prerequisite:** Phase 1 (core architecture) and Phase 2 (account management) must be complete.

---

## REQUIREMENTS

### 1. Transaction Model
- Transaction model with fields: id, account_id, date, value_date, amount, currency, description, merchant, transaction_type, user_notes, created_at, updated_at, deleted_at, created_by, updated_by, parent_transaction_id (for splits)
- Transaction types: debit, credit, transfer, fee, interest, other
- Amount stored as decimal with 2 decimal places precision
- Currency must match account currency
- Soft delete support (deleted_at field)
- All transactions belong to an account
- Track who created and last updated the transaction

### 2. Transaction CRUD Operations
- Create transaction endpoint (authenticated user with account access)
- Get transaction by ID endpoint (user with account access)
- List transactions for account with pagination and filtering
- Update transaction endpoint (user who created it or admin)
- Delete transaction endpoint (soft delete)
- Deleted transactions do not appear in normal queries
- Transaction creation and modification timestamped
- User attribution tracked for all changes

### 3. Transaction Fields & Data
- Date: Transaction date (when transaction occurred)
- Value date: Date transaction value applied (can differ from date)
- Amount: Transaction amount (always positive or negative based on type)
- Currency: Currency of transaction (must match account)
- Description: Transaction description/narrative
- Merchant: Merchant name (separate from description)
- Transaction type: Debit, credit, transfer, fee, interest, other
- User notes: Optional user comments on transaction
- Tags: Free-form tags for transaction (multiple tags per transaction)
- Created by: User who created transaction
- Updated by: User who last modified transaction

### 4. Transaction Endpoints

#### POST /api/v1/accounts/{account_id}/transactions
- Create new transaction
- Required fields: date, amount, currency, description
- Optional fields: merchant, transaction_type, user_notes, tags, value_date
- Response: Created transaction object with id and timestamps
- Authorization: User with account access
- Validate currency matches account currency
- Audit log transaction creation
- Update account balance after creation

#### GET /api/v1/accounts/{account_id}/transactions/{transaction_id}
- Get transaction details
- Response: Full transaction object including all fields
- Authorization: User with account access
- Return 404 if transaction not found or user has no access

#### GET /api/v1/accounts/{account_id}/transactions
- List transactions for account
- Query parameters: skip, limit, date_from, date_to, amount_min, amount_max, description (search), merchant (search), tags, transaction_type, sort_by (date, amount, description)
- Response: Paginated list with total count
- Authorization: User with account access
- Exclude soft-deleted transactions
- Support combining multiple filters

#### PUT /api/v1/accounts/{account_id}/transactions/{transaction_id}
- Update transaction
- Allowed fields: date, amount, description, merchant, transaction_type, user_notes, value_date
- Response: Updated transaction object
- Authorization: User who created transaction or admin
- Cannot change currency or account
- Validate currency still matches account
- Audit log all changes with old/new values
- Update account balance after change

#### DELETE /api/v1/accounts/{account_id}/transactions/{transaction_id}
- Soft delete transaction
- Response: 204 No Content
- Authorization: User who created transaction or admin
- Audit log deletion
- Update account balance after deletion

### 5. Transaction Tags
- Transaction tags model with fields: id, transaction_id, tag, created_at
- Users can assign free-form tags to transactions
- Multiple tags per transaction allowed
- Tags are user-defined (no predefined list)
- Tags support filtering and searching
- Cannot delete tags (just remove from transaction)

#### POST /api/v1/accounts/{account_id}/transactions/{transaction_id}/tags
- Add tag to transaction
- Request body: tag (string)
- Response: Updated transaction with all tags
- Authorization: User with account access
- Audit log tag addition

#### DELETE /api/v1/accounts/{account_id}/transactions/{transaction_id}/tags/{tag}
- Remove tag from transaction
- Response: 204 No Content
- Authorization: User with account access
- Audit log tag removal

### 6. Transaction Splitting
- Split transaction model with fields: id, parent_transaction_id, child_transaction_id, amount, created_at, created_by
- Parent-child relationship maintained
- Each split independently supports categorization and tags
- Split amounts must total original transaction amount exactly
- Splits can be reversed or joined back together

#### POST /api/v1/accounts/{account_id}/transactions/{transaction_id}/split
- Split one transaction into multiple parts
- Request body: array of splits [{amount, description, merchant (optional)}, ...]
- Validate split amounts sum to original transaction amount
- Response: Parent transaction with child transactions listed
- Authorization: User who created transaction or admin
- Create child transactions for each split
- Mark original as parent
- Audit log split operation

#### GET /api/v1/accounts/{account_id}/transactions/{transaction_id}/splits
- Get all splits for a transaction
- Response: List of split transactions with relationship information
- Authorization: User with account access

#### DELETE /api/v1/accounts/{account_id}/transactions/{transaction_id}/split
- Reverse/unjoin split transactions back to parent
- Response: Parent transaction (splits removed)
- Authorization: User who created transaction or admin
- Delete all child transactions
- Restore original as single transaction
- Audit log join operation

### 7. Transaction Search & Filtering
- Support searching by date range (date_from, date_to)
- Support searching by amount range (amount_min, amount_max)
- Support searching by description keywords (partial match)
- Support searching by merchant keywords (partial match)
- Support filtering by tags (include any/all tags)
- Support filtering by transaction type
- Support filtering by categories (once categories exist in Phase 4)
- Support combining multiple filters
- Search must be performant even with large datasets
- Support fuzzy matching for merchant and description (handle typos)

### 8. Transaction Validation
- Date must be valid date (not in future by default, configurable)
- Value date must be valid date
- Amount must be non-zero decimal number
- Currency must be valid ISO code and match account currency
- Description: required, 1-500 characters
- Merchant: optional, 1-100 characters
- Transaction type must be from defined list
- User notes: optional, max 1000 characters
- Cannot create transaction for deleted account
- Cannot create transaction for account user doesn't have access to

### 9. Transaction Authorization
- User with "viewer" permission: can view transactions only
- User with "editor" permission: can create, view, and edit own transactions, cannot delete
- User with "owner" permission: can create, view, edit, delete all transactions
- User who created transaction can edit their own transaction (except owners override)
- Only owners can delete transactions
- Cannot modify transactions from other accounts

### 10. Data Integrity
- Account balance must be updated when transaction added/modified/deleted
- Transaction currency must match account currency (enforced at database level)
- Split transaction amounts must sum to parent amount
- Deleted transactions not included in balance calculations
- Parent-child relationships maintained for splits
- Can edit amount of split child transaction

### 11. Audit Logging
- Log transaction creation with all fields
- Log transaction updates with old/new values
- Log transaction deletion
- Log tag additions and removals
- Log split operations (split and join)
- All audit entries include user_id, action, entity_id, and timestamp

### 12. Error Handling
- 400: Invalid transaction type, currency mismatch, split amounts don't sum, amount is zero
- 401: Not authenticated
- 403: User does not have permission to access account, cannot edit/delete transaction
- 404: Account not found, transaction not found
- 422: Validation error (invalid date, description too long, etc.)
- 409: Split amounts don't total original transaction amount

### 13. Response Format
Transaction responses include:
- id (UUID)
- account_id
- date
- value_date
- amount
- currency
- description
- merchant
- transaction_type
- user_notes
- tags (array)
- parent_transaction_id (if part of split)
- child_transaction_ids (if parent of splits)
- created_at
- updated_at
- created_by (user id)
- updated_by (user id)

### 14. Performance Considerations
- Pagination required for large transaction lists
- Database indexes on: account_id, date, created_at, transaction_type
- Query optimization for date range searches
- Efficient tag filtering
- Balance calculation must not slow down with transaction volume

### 15. Testing
- Unit tests for transaction validation
- Unit tests for balance calculation logic
- Unit tests for tag management
- Unit tests for split transaction logic
- Integration tests for all transaction endpoints
- Integration tests for filtering and searching
- Integration tests for permission-based access
- Integration tests for audit logging
- Test soft delete behavior
- Test concurrent transaction creation
- Test split amount validation
- Test balance updates after modifications
- Minimum 80% code coverage for transaction-related code
- All tests pass

---

## ACCEPTANCE CRITERIA

Phase 3 is complete when:

1. User can create transactions with date, amount, description, merchant
2. User can retrieve a specific transaction with all details
3. User can list transactions with pagination
4. User can filter by date range, amount range, type, tags
5. User can search by description and merchant keywords
6. User can add and remove tags from transactions
7. Fuzzy matching works for merchant and description searches
8. User can update transaction details (except currency and account)
9. User can soft delete transactions
10. User can split one transaction into multiple transactions
11. User can reverse splits (join back to single transaction)
12. Split transactions maintain parent-child relationships
13. Split amounts are validated to sum to original amount
14. Each split independently supports tags and categorization (for Phase 4)
15. Deleted transactions do not appear in normal queries
16. Account balance is updated when transactions are added/modified/deleted
17. Permission levels are enforced (viewer, editor, owner)
18. Users can only access transactions in accounts they have access to
19. Audit logs all transaction operations and changes
20. Validation prevents invalid data (bad dates, currency mismatch, etc.)
21. Soft deleted transactions don't affect account balance
22. Multiple filters can be combined in queries
23. All endpoints return proper error codes and messages
24. All tests pass with 80%+ coverage

---

## DEPENDENCIES

- Phase 1 (authentication, user management, audit logging) must be complete
- Phase 2 (account management) must be complete
- Account model and endpoints fully functional
- Permission checking from Phase 2 working
- Audit logging system operational