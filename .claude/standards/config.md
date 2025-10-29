
### Environment Configuration

**MANDATORY: Use environment-specific configuration**
- Development (.env.development)
- Testing (.env.test)
- Staging (.env.staging)
- Production (.env.production)
- NEVER commit environment files to version control
- ALWAYS commit .env.example with documentation

### Configuration Values

**MANDATORY: Store in environment variables**
- Database connection strings
- API keys and secrets
- External service URLs
- Feature flags
- Security keys and tokens
- Service ports and hosts
- Logging levels
- Cache configuration

### Configuration Documentation

**MANDATORY: Document all configuration**
- List all required variables in .env.example
- Describe purpose of each variable
- Specify format and valid values
- Mark required vs optional
- Provide example values (non-sensitive)
- Document default values
