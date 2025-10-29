# Frontend Development Standards

## Framework Requirements

**MANDATORY: Use React with TypeScript exclusively**
- React 18+ (latest stable version)
- TypeScript 5+ (latest stable version)
- Vite as build tool
- NEVER use JavaScript - TypeScript only
- Use functional components exclusively
- Use hooks exclusively (no class components)

## Package Manager

**MANDATORY: Use pnpm exclusively**
- Initialize projects with `pnpm create vite`
- Install dependencies with `pnpm add <package>`
- ALWAYS commit `pnpm-lock.yaml`
- NEVER use npm or yarn
- Run scripts with `pnpm run <script>`

## Project Structure

**MANDATORY: Follow this structure**

```
frontend/
├── src/
│   ├── api/                 # API client and endpoints
│   │   ├── client.ts        # Axios instance configuration
│   │   ├── types.ts         # API response types
│   │   └── [resource].ts    # Resource-specific endpoints
│   ├── components/          # React components
│   │   ├── common/          # Shared components
│   │   └── features/        # Feature-specific components
│   ├── hooks/               # Custom React hooks
│   ├── pages/               # Page components
│   ├── services/            # Business logic (non-API)
│   ├── store/               # State management
│   ├── types/               # TypeScript types and interfaces
│   ├── utils/               # Utility functions
│   ├── config.ts            # Configuration
│   ├── App.tsx
│   └── main.tsx
├── public/
├── .env                     # Environment variables (gitignored)
├── .env.example             # Example environment variables
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Type Safety & Validation

**MANDATORY: Use Zod for runtime validation**
- Define Zod schemas for ALL API responses
- Use Zod schemas for form validation
- Infer TypeScript types from Zod schemas with `z.infer`
- Validate ALL data from external sources
- Create separate schemas for different use cases (create, update, response)
- NEVER trust external data without validation

## API Client Standards

**MANDATORY: Use Axios with typed responses**
- Create single Axios instance in `src/api/client.ts`
- Configure base URL from environment variables
- Set default timeout (10 seconds)
- Add request interceptor for authentication tokens
- Add response interceptor for error handling
- Create typed API functions for each endpoint
- Parse and validate responses with Zod schemas
- Handle errors consistently across all API calls
- Implement retry logic with exponential backoff
- Handle network errors separately from API errors

## State Management

**MANDATORY: Follow these state management rules**
- Use React Context + hooks for simple, local state
- Use Zustand for complex, global client state
- Use TanStack Query (React Query) for server state (data fetching, caching)
- NEVER use Redux
- Implement persistence with Zustand middleware when needed
- Keep state normalized (avoid nested data structures)
- Create separate stores for different domains
- Use selectors to access state
- NEVER mutate state directly

## Routing

**MANDATORY: Use React Router v6+**
- Define routes in single routes config file
- Use typed route parameters with TypeScript
- Implement protected routes wrapper component
- Use nested routes for shared layouts
- Lazy load route components with React.lazy
- Handle 404 pages gracefully
- Use loader functions for data fetching when appropriate

## Forms

**MANDATORY: Use React Hook Form with Zod**
- Combine React Hook Form with Zod for validation
- Use zodResolver from @hookform/resolvers/zod
- Implement proper error display for each field
- Handle loading/submitting states
- Reset forms after successful submission
- Provide immediate validation feedback
- Disable submit button during submission

## Styling Standards

**MANDATORY: Use Tailwind CSS exclusively**
- Use Tailwind utility classes as primary styling method (95% of styling)
- Configure Tailwind with project design tokens in `tailwind.config.js`
- Use class-variance-authority (CVA) for component variants
- Create design system components with CVA
- Use Tailwind's responsive utilities (mobile-first)
- NEVER use inline styles
- CSS Modules acceptable ONLY for: complex animations, third-party component overrides, global styles
- Follow mobile-first approach

## Environment Variables

**MANDATORY: Prefix with VITE_**
- ALL environment variables must start with `VITE_`
- Store in `.env` file (add to .gitignore)
- Access via `import.meta.env.VITE_*`
- Create typed config object in `src/config.ts`
- NEVER hardcode API URLs or configuration
- ALWAYS provide `.env.example` with dummy values
- Document each variable's purpose

## Component Standards

**MANDATORY: Follow these component rules**
- Use TypeScript interfaces for ALL props
- Export named components (prefer over default exports, except for React.lazy)
- Use React.FC type for functional components
- Use React.memo for expensive components only
- Extract complex logic into custom hooks
- Keep components under 200 lines (split if larger)
- One component per file
- Use descriptive prop names
- Document complex components with JSDoc comments
- Implement proper prop destructuring

## Import Standards

**MANDATORY: Follow import order**
1. React and external libraries
2. Internal types and interfaces
3. Internal components
4. Internal hooks
5. Internal utilities
6. Styles

**Use absolute imports with path aliases**
- Configure in `tsconfig.json` and `vite.config.ts`
- Example: `@/components`, `@/hooks`, `@/utils`

## Error Handling

**MANDATORY: Implement error boundaries**
- Wrap major app sections with error boundaries
- Create custom ErrorBoundary component
- Log errors to monitoring service (e.g., Sentry)
- Provide user-friendly error UI with recovery options
- Implement error reset mechanism
- Use try-catch for async operations
- Display toast notifications for API errors

## Code Quality Tools

**MANDATORY: Configure linting and formatting**
- ESLint with TypeScript parser (@typescript-eslint/parser)
- Prettier for code formatting
- Configure pre-commit hooks with husky + lint-staged
- Use `@typescript-eslint/recommended` and `@typescript-eslint/recommended-requiring-type-checking`
- Add custom rules for imports, naming conventions
- Run checks in CI/CD pipeline
- Use `eslint-plugin-react-hooks` for hooks rules
- Configure import sorting with eslint-plugin-import

## Testing Standards

**MANDATORY: Testing requirements**
- Vitest for unit and integration tests
- React Testing Library for component tests
- Mock Service Worker (MSW) for API mocking
- Test critical user flows and business logic
- Minimum 70% coverage for utilities and hooks
- NEVER test implementation details
- Test user behavior and outcomes
- Write tests alongside features (not after)
- Use data-testid sparingly (prefer accessible queries)

## Performance Optimization

**MANDATORY: Performance standards**
- Code splitting with React.lazy and Suspense
- Lazy load route components
- Optimize images (use WebP format, lazy loading, proper sizing)
- Implement virtual scrolling for long lists (react-window or react-virtuoso)
- Use useMemo for expensive calculations only
- Use useCallback for callbacks passed to memoized children only
- Monitor bundle size with vite-plugin-bundle-analyzer
- Keep initial bundle under 200KB gzipped
- Implement proper loading states and skeletons
- Use dynamic imports for heavy dependencies

## Accessibility Standards

**MANDATORY: Accessibility requirements**
- Use semantic HTML elements (header, nav, main, article, etc.)
- All interactive elements must be keyboard accessible
- Proper ARIA labels where semantic HTML insufficient
- Maintain minimum 4.5:1 contrast ratio (WCAG AA)
- Test with screen reader (NVDA, JAWS, or VoiceOver)
- Implement focus management for modals and dialogs
- Provide skip navigation links
- Ensure form inputs have associated labels
- Support reduced motion preferences

## Security Practices

**MANDATORY: Security standards**
- Sanitize user inputs (use DOMPurify for HTML content)
- Use HTTPS exclusively in production
- Implement Content Security Policy (CSP) headers
- NEVER store sensitive data in localStorage
- Use httpOnly cookies for authentication tokens when possible
- Validate file uploads (type, size, content)
- Set proper CORS policies on backend
- Escape output to prevent XSS
- Keep dependencies updated (use Dependabot)
- Never commit secrets, API keys, or .env files

## Assets & Constants

**MANDATORY: Asset management**
- Store static assets in `public/` directory
- Create `src/constants/` for magic numbers and strings
- Use TypeScript enums or const objects for fixed value sets
- Optimize SVGs before importing (remove unnecessary metadata)
- Use TypeScript const assertions for readonly data
- Import types separately from values when using type-only imports

## Git & Version Control

**MANDATORY: Version control standards**
- Use conventional commits format:
  - `feat:` new features
  - `fix:` bug fixes
  - `docs:` documentation
  - `refactor:` code refactoring
  - `test:` adding tests
  - `chore:` maintenance tasks
- Branch naming conventions:
  - `feature/description`
  - `bugfix/description`
  - `hotfix/description`
- Squash commits before merging to main
- Write meaningful commit messages (what and why)
- NEVER commit secrets, .env files, or sensitive data
- Include comprehensive .gitignore:
  ```
  node_modules/
  dist/
  .env
  .env.local
  *.log
  .DS_Store
  coverage/
  ```
- Review PRs for code quality, not just functionality
