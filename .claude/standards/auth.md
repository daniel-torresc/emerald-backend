### Authentication Method

**MANDATORY: Use JWT tokens**
- Implement access token + refresh token pattern
- Access token expiration: 15 minutes
- Refresh token expiration: 7 days
- Store tokens securely (HttpOnly cookies or secure storage)
- NEVER store tokens in localStorage for sensitive applications

### Password Security

**MANDATORY: Follow password security standards**
- Hash passwords with bcrypt (cost factor: 12)
- NEVER store plain text passwords
- Minimum password length: 8 characters
- Require: uppercase, lowercase, digit, special character
- Implement password strength validation
- Rate limit login attempts (5 attempts per 15 minutes)
- Lock account after excessive failed attempts
- Implement "forgot password" flow with time-limited tokens

### Token Standards

**MANDATORY: JWT token structure**
- Include: user_id, role, permissions, expiration, token type
- Sign with strong secret key (minimum 256 bits)
- Use HS256 or RS256 algorithm
- Validate token signature on every request
- Check token expiration
- Implement token refresh endpoint
- Invalidate tokens on logout
- Implement token blacklist for revoked tokens

### Authorization Patterns

**MANDATORY: Implement Role-Based Access Control (RBAC)**
- Define clear roles: admin, user, guest, etc.
- Assign permissions to roles, not users
- Check permissions at endpoint level
- Use dependency injection for permission checks
- Implement fine-grained permissions when needed
- Document required permissions for each endpoint
- Return 403 for insufficient permissions
- Return 401 for missing authentication

### Security Headers

**MANDATORY: Implement security headers**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy`: Define strict CSP
- `Strict-Transport-Security`: Enable HSTS
- `X-XSS-Protection: 1; mode=block`
- Remove server version headers
