### Testing Requirements

**MANDATORY: Minimum test coverage**
- Overall code coverage: 80% minimum
- Critical paths: 100% coverage (authentication, payments, data integrity)
- All public API endpoints: 100% coverage
- Business logic: 90% minimum coverage

### Backend Testing

**MANDATORY: Use pytest exclusively**
- Write tests for ALL new features
- Write tests for ALL bug fixes
- Use pytest fixtures for setup/teardown
- Use test database (SQLite or PostgreSQL)
- Mock external services
- Use dependency injection for testability

**MANDATORY: Test organization**
- Unit tests: Test individual functions/classes in isolation
- Integration tests: Test component interactions
- End-to-end tests: Test complete user flows
- Separate test files by module
- Name tests descriptively: `test_[function]_[scenario]_[expected_result]`

**MANDATORY: Test database**
- Use separate test database
- Reset database between tests
- Use transactions that rollback after each test
- Create database schema in test setup
- Use factories for test data creation

### Frontend Testing

**MANDATORY: Use Vitest + React Testing Library**
- Write tests for ALL components
- Test user interactions, not implementation details
- Test accessibility
- Mock API calls
- Use Testing Library queries (getByRole, getByText)
- Test error states
- Test loading states

### Integration Testing

**MANDATORY: Test critical user flows**
- Authentication flow (register, login, logout)
- CRUD operations for main resources
- Payment/transaction flows
- Error handling flows
- Permission checks

### Running Tests

**MANDATORY: Test execution requirements**
- Run tests before every commit
- Run full test suite before merge to main
- Tests must pass in CI/CD pipeline
- Failed tests block deployment
- Run tests with coverage reporting
- Fix broken tests immediately
