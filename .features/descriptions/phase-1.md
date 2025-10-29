# Phase 1: Core Architecture & Foundation

## Personal Finance Platform Backend

**Objective:** Build a production-ready foundation FastAPI project with authentication, user 
management, and core infrastructure.

---

## REQUIREMENTS

### 1. Project Setup

- FastAPI application with Python 3.13+
- PostgreSQL database with async support
- Environment-based configuration (local, development, staging, production)
- Docker containerization for local development
- All dependencies pinned to latest stable versions

### 2. Database & Models

- User model with fields: id, username, email, password_hash, full_name, is_active, is_admin,
  created_at, updated_at, deleted_at, created_by, updated_by, last_login_at
- Use a role-permission junction table rather than storing permissions directly on users.
- Audit log model with fields: id, user_id, action, entity_type, entity_id, old_values, new_values,
  description, ip_address, user_agent, status, error_message, created_at, metadata
- All models support soft deletes (deleted_at field)
- All models include created_at, updated_at, created_by, updated_by timestamps
- Alembic migrations configured and ready for schema changes
- Database connection pooling and async support

### 3. Authentication System

- User registration endpoint
- User login endpoint with JWT token generation
- Token refresh endpoint (access token: 30 min, refresh token: 7 days)
- Logout endpoint
- Password change endpoint
- JWT token validation and extraction from requests
- Bcrypt password hashing with salt rounds = 12
- Password requirements: minimum 8 characters, at least 1 uppercase, 1 lowercase, 1 digit, 1 
  special character

### 4. User Management

- Get current user profile endpoint
- Update current user profile endpoint
- Get specific user endpoint (admin or self)
- List all users endpoint (admin only, with pagination and filtering)
- Deactivate user endpoint (set is_active = false)
- Soft delete user endpoint (set deleted_at timestamp)

### 5. Authorization & Access Control

- Role-based access control
- Endpoint protection requiring authentication
- Admin-only endpoint protection
- Rate limiting on sensitive endpoints (login: 5 attempts per 15 min, password change: 3 per hour,
  token refresh: 10 per hour)

### 6. Error Handling

- Custom application exceptions
- Global error handler middleware returning consistent error format
- Proper HTTP status codes (200, 201, 400, 401, 403, 404, 422, 423, 429, 500)
- Error responses with machine-readable error codes and human-readable messages
- Request ID tracking for debugging

### 7. Audit Logging

- Log all user actions (create, read, update, delete, login, logout)
- Log authentication events with success/failure status
- Log all data modifications with old and new values
- Log permission changes
- Immutable audit logs (cannot be edited or deleted)
- Audit logs queryable by user, action type, entity type, date range
- Admin endpoint to view all audit logs
- User endpoint to view own audit logs

### 8. API Structure

- RESTful API with versioning (/api/v1)
- Consistent response format with timestamp and request_id
- Paginated list responses with total count
- OpenAPI/Swagger documentation auto-generated

### 9. Security

- No hardcoded secrets
- All configuration via environment variables and PydanticSettings
- CORS properly configured
- Request logging with sensitive data sanitization (passwords excluded)
- Secure session management

### 10. Testing

- Unit tests for authentication logic
- Unit tests for user management logic
- Integration tests for all endpoints
- Test fixtures and test database setup
- Minimum 80% code coverage
- All tests pass

### 11. Documentation

- README with setup instructions
- Docstrings for all functions and classes
- .env.example documenting all configuration variables
- API documentation accessible via Swagger/ReDoc
