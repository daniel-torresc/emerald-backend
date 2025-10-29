
### Git Workflow

**MANDATORY: Use Git Flow branching model**
- `main`: Production-ready code only
- `develop`: Integration branch for features
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Production hotfixes
- `release/*`: Release preparation

### Commit Standards

**MANDATORY: Follow conventional commits**
- Format: `<type>(<scope>): <description>`
- Types: feat, fix, docs, style, refactor, test, chore
- Use imperative mood: "add feature" not "added feature"
- Keep first line under 72 characters
- Add detailed description in body when needed
- Reference issue numbers

### Branch Naming

**MANDATORY: Use descriptive branch names**
- Format: `<type>/<ticket-id>-<short-description>`
- Use lowercase and hyphens
- Examples: `feature/USR-123-add-user-profile`, `bugfix/PAY-456-fix-payment-error`

### Pull Request Standards

**MANDATORY: Pull request requirements**
- Create PR from feature branch to develop
- Write descriptive PR title and description
- Reference related issues
- Include testing instructions
- Request review from at least 1 team member
- Address all review comments
- Ensure CI/CD passes
- Squash commits before merge (when appropriate)
