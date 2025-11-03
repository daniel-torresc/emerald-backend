# Objective

Refactor the database module to eliminate global state

## Context

The `!src/core/database.py` file currently contains a global `engine` variable. Global variables 
are considered an anti-pattern in Python software engineering as they: 

- Make code harder to test (difficult to mock or isolate dependencies)
- Reduce modularity and reusability
- Create hidden dependencies that are not explicit in function signatures
- Make concurrent execution and state management problematic
- Complicate debugging and code reasoning

## Task

Review the current implementation of the `engine` variable in `!src/core/database.py` and 
refactor the codebase to eliminate this global state. 

## Deliverables

- Identify all locations where the global `engine` variable is referenced
- Propose and implement a refactoring strategy that removes global state
- Update all dependent code to use the new approach
- Ensure existing functionality remains intact
