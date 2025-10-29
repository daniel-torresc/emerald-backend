
### Input Validation

**MANDATORY: Validate all inputs**
- Validate and sanitize ALL user inputs
- Use Pydantic schemas for validation
- Validate data types, formats, ranges
- Reject unexpected fields
- Implement maximum length limits
- Validate file uploads (type, size)
- Use parameterized queries (NEVER string concatenation)

### Data Protection

**MANDATORY: Protect sensitive data**
- Encrypt sensitive data at rest
- Use HTTPS/TLS for all data transmission
- NEVER log sensitive data (passwords, tokens, PII)
- Implement data masking for logs
- Use secure random number generation
- Implement secure session management
- Clear sensitive data from memory when done

### Dependencies

**MANDATORY: Manage dependencies securely**
- Audit dependencies regularly (weekly)
- Update dependencies to patch vulnerabilities
- Use dependency scanning in CI/CD
- Pin dependency versions
- Review licenses for legal compliance
- Remove unused dependencies

### Rate Limiting

**MANDATORY: Implement rate limiting**
- Limit API requests per IP/user
- Implement stricter limits for authentication endpoints
- Return 429 status with Retry-After header
- Log rate limit violations
- Consider distributed rate limiting for scaled deployments

### CORS Configuration

**MANDATORY: Configure CORS properly**
- Specify allowed origins explicitly (NEVER use *)
- Specify allowed methods
- Specify allowed headers
- Enable credentials only when necessary
- Set appropriate max age
