# Agent Instructions: Refactor FastAPI Application to Hexagonal Architecture

## Task Overview
Analyze the current FastAPI codebase and refactor it to implement Hexagonal Architecture (Ports and Adapters pattern) with complete database independence and the Unit of Work pattern.

## Primary Objectives

1. **Implement Hexagonal Architecture**
   - Separate the codebase into three distinct layers: Domain, Application, and Infrastructure
   - Ensure dependencies flow inward (Infrastructure → Application → Domain)
   - The Domain layer must have ZERO dependencies on external frameworks, databases, or libraries

2. **Achieve Database Independence**
   - Decouple all business logic from PostgreSQL/SQLAlchemy
   - Create abstractions that allow switching between SQL databases, MongoDB, APIs, or any other data source without changing business logic
   - Database-specific code must live only in the Infrastructure layer

3. **Implement Unit of Work Pattern**
   - All database operations must go through a Unit of Work
   - Ensure transactional consistency across multiple repository operations
   - Provide clear transaction boundaries for business operations

## Architectural Requirements

### Layer Separation

**Domain Layer (Core/Innermost)**
- Pure domain entities (no ORM decorators or database concerns)
- Value objects for business concepts
- Domain services containing business logic
- Domain-specific exceptions
- Must have NO external dependencies (no SQLAlchemy, no FastAPI, no database libraries)

**Application Layer (Use Cases)**
- Port interfaces (abstract classes/protocols) defining contracts:
  - Inbound ports: interfaces for driving the application (service interfaces)
  - Outbound ports: interfaces for driven adapters (repository interfaces, Unit of Work interface)
- Use cases orchestrating domain logic
- Data Transfer Objects (DTOs) for use case inputs/outputs
- Application-level exceptions

**Infrastructure Layer (Adapters)**
- Inbound adapters:
  - FastAPI routers and API schemas
  - API error handling and HTTP concerns
  - Dependency injection setup
- Outbound adapters:
  - Database-specific implementations (PostgreSQL repositories using SQLAlchemy)
  - SQLAlchemy models (ORM models stay here, not in domain)
  - Mappers to convert between domain entities and database models
  - Unit of Work implementation
  - External service integrations
- Configuration and settings management

### Unit of Work Pattern Requirements

- Create a `UnitOfWorkPort` interface in the Application layer
- Implement `PostgresUnitOfWork` in the Infrastructure layer
- The UoW must:
  - Manage database sessions/connections
  - Provide access to all repositories
  - Control transaction boundaries (commit/rollback)
  - Be usable as an async context manager
- All use cases must receive UoW as a dependency
- Repository instances must be created and managed by the UoW

### Repository Pattern Requirements

- Define repository port interfaces in Application layer (e.g., `UserRepositoryPort`, `TransactionRepositoryPort`)
- Implement concrete repositories in Infrastructure layer (e.g., `PostgresUserRepository`)
- Repositories must:
  - Work with domain entities (not database models)
  - Be injected via Unit of Work
  - Handle mapping between entities and models internally
  - Be swappable (easy to create MongoDB/API implementations)

### Dependency Injection Requirements

- Use dependency-injector
- Create dependency providers for:
  - Unit of Work instances
  - Current user authentication
  - Configuration/settings
- Dependencies must allow easy swapping of implementations
- Use cases should be instantiated with their dependencies in the API layer

## Specific Requirements

### Domain Entities
- Must be pure Python classes
- Must contain business logic methods
- Must use value objects for complex concepts (Money, Currency, etc.)
- Must have NO database or framework dependencies
- Must be fully testable without any infrastructure

### Mapping Strategy
- Create explicit mapper classes to convert:
  - Domain entities → Database models (for persistence)
  - Database models → Domain entities (for retrieval)
- Mappers live in Infrastructure layer
- Mappers handle all database-specific concerns

### API Layer
- FastAPI routers must be thin
- Routers must:
  - Validate HTTP requests using Pydantic schemas
  - Call appropriate use cases
  - Convert between API schemas and DTOs
  - Handle HTTP-specific concerns (status codes, headers)
  - Convert domain/application exceptions to HTTP responses
- API schemas (Pydantic models) are separate from domain entities and DTOs

### Use Cases
- Each use case is a single class with an `execute()` method
- Use cases orchestrate domain logic and coordinate repositories
- Use cases operate on domain entities
- Use cases use DTOs for inputs and outputs
- Use cases must be framework-agnostic

### Database Independence Validation
- Must be able to create a MongoDB implementation by only changing the Infrastructure layer
- Must be able to create an API-based implementation by only changing the Infrastructure layer
- Switching data sources must NOT require changes to Domain or Application layers

## Migration Strategy Requirements

You must refactor the existing code incrementally:

1. **Analyze Current State**
   - Identify all database-coupled code
   - Identify business logic mixed with infrastructure
   - Map current structure to target structure
   - Document dependencies that need to be broken

2. **Execute Refactoring in Phases**
   - Create the layered directory structure
   - Extract domain entities from SQLAlchemy models
   - Define port interfaces
   - Implement use cases
   - Create repository adapters and mappers
   - Implement Unit of Work
   - Refactor API routers to use dependency injection
   - Update all existing functionality to use new architecture

3. **Maintain Functionality**
   - All existing features must continue to work
   - Existing API contracts must be preserved
   - All business rules must be maintained

## Directory Structure Requirements

Create a clear directory structure that reflects the three layers:
```
app/
├── domain/                    # No external dependencies
│   ├── entities/
│   ├── value_objects/
│   ├── exceptions/
│   └── services/
├── application/               # Depends only on domain
│   ├── ports/
│   │   ├── inbound/
│   │   └── outbound/
│   ├── use_cases/
│   └── dto/
└── infrastructure/            # Depends on application and domain
    ├── adapters/
    │   ├── inbound/
    │   │   └── api/
    │   └── outbound/
    │       └── persistence/
    │           └── postgresql/
    └── config/
```

## Validation Requirements

After refactoring, the codebase must satisfy:

- [ ] Domain layer has zero imports from FastAPI, SQLAlchemy, or any external framework
- [ ] Domain entities are pure Python with business logic methods
- [ ] Application layer defines all port interfaces (repositories, UoW)
- [ ] Infrastructure layer implements all port interfaces
- [ ] All database operations go through Unit of Work
- [ ] All use cases receive UoW as dependency
- [ ] API routers use dependency injection
- [ ] Mappers exist to convert entities ↔ database models
- [ ] Can theoretically swap PostgreSQL for MongoDB by only changing Infrastructure layer
- [ ] All existing tests pass (after updating for new structure)
- [ ] Business logic is testable without any infrastructure

## Success Criteria

The refactoring is complete when:

1. **Separation of Concerns**: Domain, Application, and Infrastructure layers are clearly separated with proper dependency flow
2. **Database Independence**: Could switch from PostgreSQL to MongoDB, API, or any other data source by only modifying the Infrastructure layer
3. **Testability**: Domain logic can be tested without any database or framework dependencies
4. **Maintainability**: Clear boundaries between layers make the code easier to understand and modify
5. **Functionality Preserved**: All existing features work exactly as before
6. **Unit of Work**: All repository operations are managed through UoW with proper transaction boundaries
7. **Clean Dependencies**: No circular dependencies, clear dependency injection patterns

## Constraints and Notes

- Maintain async/await patterns throughout
- Keep all existing requirements from the project document
- Prioritize clean architecture over premature optimization
- Document any architectural decisions or trade-offs made during refactoring
- Ensure backward compatibility for existing API endpoints
- Update tests to reflect new architecture

---

**Begin by analyzing the current codebase structure and creating a refactoring plan before making any changes.**