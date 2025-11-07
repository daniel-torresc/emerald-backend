# Phase 4.5: Admin Management & Operations
## Personal Finance Platform Backend

**Objective:** Build admin creation, management, and system-wide operational capabilities to support system administration and operations.

---

## REQUIREMENTS

### 1. Admin User Creation

#### Initial System Bootstrap
- Provide a mechanism to create admin users via command-line
- First admin user can be created via:
  - Command-line (for automated deployment): `uv python -m app.cli create-admin --username admin --email admin@example.com --password <password>`
  - Environment variables on first startup: INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD
- After first admin created, bootstrap mechanism is disabled

#### Admin Creation by Existing Admin
- POST /api/v1/admin/users
- Create new admin user
- Request body: username, email, password (optional, generated if not provided), full_name, permissions (optional)
- Response: Created admin user with temporary password (if generated)
- Authorization: Admin only
- Validate username/email unique
- Audit log admin user creation
- Send notification to created user (if email enabled in future)

### 2. Admin User Management

#### GET /api/v1/admin/users
- List all admin users
- Query parameters: skip, limit, search (username/email), sort_by (username, created_at)
- Response: Paginated list of admin users with their permissions
- Authorization: Admin only
- Include: username, email, full_name, is_active, created_at, last_login_at, permissions

#### GET /api/v1/admin/users/{user_id}
- Get specific admin user details
- Response: Full admin user object with all details
- Authorization: Admin only or user viewing themselves
- Return 404 if user is not admin

#### PUT /api/v1/admin/users/{user_id}
- Update admin user
- Allowed fields: full_name, is_active
- Cannot change username or email via this endpoint
- Response: Updated admin user
- Authorization: Admin only or user updating themselves
- Audit log changes

#### DELETE /api/v1/admin/users/{user_id}
- Soft delete admin user
- Response: 204 No Content
- Authorization: Admin only (cannot delete self)
- Cannot delete if it's the last admin (validation error)
- Set deleted_at timestamp
- Audit log deletion

#### PUT /api/v1/admin/users/{user_id}/password
- Reset admin user password
- Request body: new_password (optional, generated if not provided)
- Response: Confirmation with temporary password (if generated)
- Authorization: Admin only (can reset others, own password via /auth/change-password)
- Audit log password reset
- User must change password on next login (future enhancement)

#### PUT /api/v1/admin/users/{user_id}/permissions
- Modify admin user permissions
- Request body: permissions (array of permission strings)
- Response: Updated admin user with new permissions
- Authorization: Admin only
- Cannot remove own admin privilege (validation error)
- Audit log permission changes

### 3. Admin Permissions & Roles
- Admin role: Full system access (all operations)
- Future: Support fine-grained permissions (e.g., view-only auditor, user manager, etc.)
- For now: All admins have full admin access
- Admins can:
  - View all users in system
  - Deactivate/reactivate user accounts
  - Delete user accounts (soft delete)
  - Reset user passwords
  - View all audit logs
  - Query system statistics
  - Manage other admin users
  - Access admin operations endpoints

### 4. System Statistics & Monitoring

#### GET /api/v1/admin/statistics
- Get system-wide statistics
- No query parameters
- Response:
  ```json
  {
    "total_users": number,
    "active_users": number,
    "total_accounts": number,
    "total_transactions": number,
    "total_imports": number,
    "database_size_mb": number,
    "system_uptime_hours": number,
    "last_import_timestamp": "ISO8601",
    "last_user_created_timestamp": "ISO8601"
  }
  ```
- Authorization: Admin only
- No audit log needed (read-only)

#### GET /api/v1/admin/statistics/users
- Get detailed user statistics
- Response:
  ```json
  {
    "total_users": number,
    "active_users": number,
    "inactive_users": number,
    "deleted_users": number,
    "admin_users": number,
    "new_users_last_7_days": number,
    "new_users_last_30_days": number,
    "users_never_logged_in": number
  }
  ```
- Authorization: Admin only

#### GET /api/v1/admin/statistics/accounts
- Get detailed account statistics
- Response:
  ```json
  {
    "total_accounts": number,
    "by_type": {
      "checking": number,
      "savings": number,
      "credit_card": number,
      ...
    },
    "by_currency": {
      "USD": number,
      "EUR": number,
      ...
    },
    "shared_accounts": number,
    "deleted_accounts": number
  }
  ```
- Authorization: Admin only

#### GET /api/v1/admin/statistics/transactions
- Get detailed transaction statistics
- Response:
  ```json
  {
    "total_transactions": number,
    "total_amount_by_currency": {
      "USD": number,
      "EUR": number,
      ...
    },
    "by_type": {
      "debit": number,
      "credit": number,
      "transfer": number,
      ...
    },
    "split_transactions": number,
    "deleted_transactions": number,
    "transactions_last_7_days": number
  }
  ```
- Authorization: Admin only

#### GET /api/v1/admin/statistics/imports
- Get detailed import statistics
- Response:
  ```json
  {
    "total_imports": number,
    "successful_imports": number,
    "failed_imports": number,
    "total_rows_imported": number,
    "total_duplicates_detected": number,
    "imports_last_7_days": number
  }
  ```
- Authorization: Admin only

### 5. Audit Log Viewing

#### GET /api/v1/admin/audit-logs
- View all system audit logs
- Query parameters: skip, limit, user_id (filter), action (filter), entity_type (filter), entity_id (filter), date_from, date_to, sort_by (created_at, user_id)
- Response: Paginated list of audit logs
- Authorization: Admin only
- Include all fields: user_id, action, entity_type, entity_id, old_values, new_values, timestamp, ip_address, user_agent

#### GET /api/v1/admin/audit-logs/export
- Export audit logs to CSV or JSON
- Query parameters: format (csv/json), filters (same as above)
- Response: File download (CSV or JSON)
- Authorization: Admin only
- Useful for compliance and external audits

### 6. User Account Management (Admin)

#### GET /api/v1/admin/users/{user_id}/accounts
- View all accounts owned by or shared with specific user
- Response: List of accounts with user's permission level
- Authorization: Admin only
- Include: account details, permission level, owner info

#### GET /api/v1/admin/users/{user_id}/transactions
- View all transactions across all accounts accessible to user
- Query parameters: account_id (optional filter), skip, limit, date_range
- Response: Paginated list of transactions
- Authorization: Admin only

#### PUT /api/v1/admin/users/{user_id}/deactivate
- Deactivate user account
- Response: 200 with confirmation
- Authorization: Admin only
- Sets is_active = false
- User cannot login after deactivation
- Audit log deactivation

#### PUT /api/v1/admin/users/{user_id}/reactivate
- Reactivate user account
- Response: 200 with confirmation
- Authorization: Admin only
- Sets is_active = true
- User can login again
- Audit log reactivation

#### DELETE /api/v1/admin/users/{user_id}
- Soft delete user account (admin version)
- Response: 204 No Content
- Authorization: Admin only
- Different from user self-deletion (admin can delete any user)
- Set deleted_at timestamp, preserve all data
- Audit log deletion

### 7. System Health & Diagnostics

#### GET /api/v1/admin/health
- Check system health and status
- Response:
  ```json
  {
    "status": "healthy" | "degraded" | "unhealthy",
    "timestamp": "ISO8601",
    "database": {
      "connected": boolean,
      "response_time_ms": number
    },
    "uptime_seconds": number,
    "version": "string"
  }
  ```
- Authorization: Admin only
- No audit log (monitoring endpoint)

#### GET /api/v1/admin/database-info
- Get database statistics and info
- Response:
  ```json
  {
    "total_size_mb": number,
    "tables": {
      "users": {
        "row_count": number,
        "size_mb": number
      },
      ...
    },
    "backup_status": "string" (if applicable),
    "replication_status": "string" (if applicable)
  }
  ```
- Authorization: Admin only
- No audit log (monitoring endpoint)

### 8. System Configuration & Maintenance

#### GET /api/v1/admin/config
- Get current system configuration (non-sensitive)
- Response: Public configuration values (not passwords/secrets)
- Authorization: Admin only
- Include: environment, version, feature flags, rate limit settings

#### POST /api/v1/admin/maintenance/cleanup-deleted
- Run cleanup job to remove old soft-deleted data
- Request body: entity_type (users, accounts, transactions, all), days_before (default 90)
- Response: Cleanup summary (records deleted)
- Authorization: Admin only
- Permanently deletes soft-deleted data older than specified days
- Audit log cleanup operation
- Can be run manually or scheduled

#### POST /api/v1/admin/maintenance/rebuild-balances
- Rebuild all account balances from transactions
- Response: Summary of accounts rebuilt
- Authorization: Admin only
- Recalculates balances for all accounts
- Useful if balance calculation logic changes or data integrity issue detected
- Audit log rebuild operation

### 9. User Onboarding & Support

#### POST /api/v1/admin/users/{user_id}/reset-password-token
- Generate password reset token for user (admin sends reset link)
- Response: Reset link (or token for frontend to construct link)
- Authorization: Admin only
- Token valid for 24 hours
- Audit log token generation

#### PUT /api/v1/admin/users/{user_id}/unlock
- Unlock user account if locked due to failed login attempts
- Response: 200 with confirmation
- Authorization: Admin only
- Clears failed login count
- Audit log unlock

### 10. Bulk Operations

#### POST /api/v1/admin/users/bulk-deactivate
- Deactivate multiple users at once
- Request body: user_ids (array)
- Response: List of deactivated users
- Authorization: Admin only
- Cannot deactivate self
- Cannot deactivate if would leave zero active admins (validation)
- Audit log each deactivation

#### POST /api/v1/admin/users/bulk-delete
- Soft delete multiple users at once
- Request body: user_ids (array)
- Response: List of deleted users
- Authorization: Admin only
- Cannot delete self
- Cannot delete if would leave zero admins (validation)
- Audit log each deletion

### 11. Error Handling
- 400: Cannot delete last admin, invalid permissions, user already admin
- 401: Not authenticated
- 403: Not admin, insufficient permissions, cannot perform action on self
- 404: Admin user not found, user not found
- 409: Bootstrap already performed, username/email already exists
- 422: Validation error
- 410: Bootstrap endpoint no longer available

### 12. Authorization & Access Control
- All admin endpoints require admin role
- Cannot delete own admin privilege
- Cannot be last admin in system
- Admin can view all user data but limited by audit permissions
- All admin actions logged to audit trail
- Rate limiting does not apply to admin endpoints

### 13. Response Format
Admin user responses include:
- id (UUID)
- username
- email
- full_name
- is_active
- is_admin
- permissions (array of permission strings)
- created_at
- updated_at
- last_login_at

Statistics responses include aggregate counts and breakdowns

### 14. Testing
- Unit tests for admin user creation
- Unit tests for permission checks
- Integration tests for all admin endpoints
- Integration tests for statistics calculations
- Integration tests for audit log viewing
- Integration tests for bulk operations
- Integration tests for bootstrap mechanism
- Test that last admin cannot be deleted
- Test that bootstrap only works once
- Test that admin cannot delete self
- Test concurrent admin operations
- Minimum 80% code coverage for admin code
- All tests pass

### 15. Documentation
- Document all admin endpoints in OpenAPI
- Document bootstrap process for deployment
- Document admin permissions and access control
- Document statistics endpoints
- Document audit log structure
- Document maintenance operations
- Add admin section to README

### 16. Security Considerations
- Admin password must meet same security requirements as regular users
- Admin operations must be fully audited
- Admin endpoints protected with authentication and admin role check
- Rate limiting not applied to admins (or very high limit)
- Admin tokens may have longer expiration (configurable)
- No admin functions callable by non-admins

---

## ACCEPTANCE CRITERIA

Phase is complete when:

1. System has mechanism to create first admin user
2. Only one admin user can be created at bootstrap
3. Existing admins can create new admin users
4. Admin users can be deactivated/reactivated
5. Admin users can be soft deleted
6. Admin passwords can be reset
7. Admin cannot delete themselves
8. System prevents deleting last admin
9. All admin users can be listed
10. System provides user statistics (active, inactive, deleted, etc.)
11. System provides account statistics by type and currency
12. System provides transaction statistics
13. System provides import statistics
14. All audit logs can be viewed by admins with flexible filtering
15. Audit logs can be exported to CSV or JSON
16. Admins can view all transactions of any user
17. Admins can deactivate/reactivate any user
18. Admins can soft delete any user
19. System health check endpoint works
20. Database info endpoint returns statistics
21. Config endpoint returns public configuration
22. Cleanup job can remove old soft-deleted data
23. Balance rebuild job recalculates all account balances
24. Bulk deactivation works for multiple users
25. Bulk deletion works for multiple users
26. All admin operations are fully audited
27. Admin-only endpoints reject non-admin requests
28. All endpoints return proper error codes and messages
29. Bootstrap endpoint documented for deployment
30. All tests pass with 80%+ coverage
