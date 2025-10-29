---

description: Create a detailed implementation plan for a feature based on its description and, 
optionally, prior research findings. 
argument-hint: [feature-description-file] [research-file]

---

⚠️ Remember that **80% of human effort** is invested in this phase

## Planning Request

You are tasked with creating a detailed **implementation plan** for a project feature.

Read and analyze the **feature description file** carefully to fully understand the context, goals, 
and requirements.

If a **research file** is provided, also read it thoroughly and incorporate its findings, 
recommendations, and constraints into your plan.

If no research file is provided, proceed using only the feature description file as your source 
of information. 

- Feature description file: $1
- Research file (optional): $2

---

## Planning Objectives

Your goal is to produce a comprehensive implementation plan that will serve as a blueprint for 
development. This plan will be read by developers and other agents who will execute the 
implementation, so clarity, completeness, and actionability are essential. 

**CRITICAL: You are ONLY responsible for planning. Do NOT implement, code, or execute any part 
of the plan. Your deliverable is the plan document itself.**

Create a plan so detailed that implementation becomes trivial.

## Required Planning Components

### 1. Executive Summary

- Provide a concise overview of the idea/feature (2-3 paragraphs)
- Highlight the primary objectives and goals
- Expected outcomes and success criteria

### 2. Technical Architecture

#### 2.1 System Design Overview

- High-level architecture diagram
- Key components and their responsibilities
- Integration points with existing systems
- Data flow and state management approach

#### 2.2 Technology Decisions

For each significant technology choice:

**[Technology/Library Name]**
- **Purpose**: What it solves in this implementation
- **Why this choice**: Specific justification (performance, ecosystem, team familiarity, etc.)
- **Version**: Specific version and compatibility requirements
- **Alternatives considered**: What else was evaluated and why this won

#### 2.3 File Structure

**Directory Purpose**: [Explanation]

### 3. Implementation Specification

#### 3.1 Component Breakdown

For each significant component/module (not necessarily every file):

##### Component: [Component Name]

**Files Involved**:
- `path/to/main-file`
- `path/to/related-file`

**Purpose**: [What this component accomplishes in the system]

**Implementation Requirements**:
1. **Core Logic**:
   - Step 1: [Specific implementation detail]
   - Step 2: [Specific implementation detail]
   - Key algorithm or approach to use

2. **Data Handling**:
   - Input validation requirements
   - Expected input formats and types
   - Output format and structure
   - State management (if applicable)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: [Specific edge case]
   - [ ] Validate: [Specific validation]
   - [ ] Error: [Specific error scenario]

4. **Dependencies**:
   - Internal: [Other components this depends on]
   - External: [Libraries or APIs this uses]

5. **Testing Requirements**:
   - [ ] Unit test: [Specific test scenario with expected behavior]
   - [ ] Unit test: [Another specific test scenario]
   - [ ] Integration test: [How this works with other components]
   - [ ] E2E test: [User flow to test, if applicable]

**Acceptance Criteria**:
- [ ] [Specific, measurable criteria]
- [ ] [Another specific criteria]

**Implementation Notes**:
- [Any gotchas, best practices, or important considerations]

---

#### 3.2 Detailed File Specifications

> Use this section when file-level precision is needed (small features or critical files)

##### `path/to/specific-file`

**Purpose**: [Exact role of this file]

**Implementation**: [What needs to be implemented]

**Edge Cases**:
- When input is null: [Do this]
- When API fails: [Do this]
- When user is unauthorized: [Do this]

**Tests**:
- [ ] Test: Valid input returns expected output
- [ ] Test: Invalid input throws appropriate error
- [ ] Test: Handles timeout gracefully

### 4. Implementation Roadmap

> **Guidance**: Break work into phases ONLY if the feature is complex enough to warrant staged 
> delivery. For simple features, a single phase is perfectly fine. 

#### 4.1 Phase Breakdown

##### Phase 1: [Foundation/Core/MVP] (Size: M, Priority: P0)

**Goal**: [What value this phase delivers - be specific about user/system capability]

**Scope**: 
- ✅ Include: [What's in scope]
- ❌ Exclude: [What's explicitly out of scope for this phase]

**Components to Implement**:
- [ ] Component A: [Brief description]
- [ ] Component B: [Brief description]

**Detailed Tasks**:
1. [ ] Set up [specific infrastructure/configuration]
   - Create files: `X`, `Y`, `Z`
   - Install dependencies: `pkg1`, `pkg2`
   
2. [ ] Implement [specific feature]
   - Build component: [Name]
   - Add logic for: [Specific behavior]
   - Handle edge case: [Specific case]

3. [ ] Add tests
   - Unit tests for: [Component]
   - Integration test: [Specific flow]

4. [ ] Document
   - Update README with: [Specific section]
   - Add inline documentation for: [Complex parts]

**Dependencies**: 
- Requires: [What must exist before starting]
- Blocks: [What can't start until this is done]

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (minimum 80% coverage for new code)
- [ ] Feature works in [specific environment]
- [ ] Performance meets [specific metric]
- [ ] Code reviewed and approved
- [ ] Documentation updated

**Risk Factors**:
- [Potential blocker and mitigation strategy]

**Estimated Effort**: [X days/weeks for Y developer(s)]

##### Phase 2: [Enhancements/Optimization] (Size: S, Priority: P1)

[Same structure as Phase 1]

#### 4.2 Implementation Sequence
```
Phase 1 (P0, 2 weeks)
  ↓
Phase 2 (P1, 1 week) ← Can start after Phase 1 validation
  ↓
Phase 3 (P2, 1 week) ← Can run parallel with Phase 2
```

**Rationale for ordering**:
- Phase 1 first because: [Reason - e.g., it establishes core architecture]
- Phase 2 depends on Phase 1 because: [Specific dependency]
- Phase 3 can be parallel because: [Why it's independent]

**Quick Wins** (if applicable):
- [Something that can be delivered early for immediate value]

### 5. Simplicity & Design Validation

Before finalizing this plan, verify:

**Simplicity Checklist**:
- [ ] Is this the SIMPLEST solution that solves the problem?
- [ ] Have we avoided premature optimization?
- [ ] Does this align with existing patterns in the codebase?
- [ ] Can we deliver value in smaller increments?
- [ ] Are we solving the actual problem vs. a perceived problem?

**Alternatives Considered**:
- Alternative 1: [Brief description and why it wasn't chosen]
- Alternative 2: [Brief description and why it wasn't chosen]

**Rationale**: [Why the proposed approach is preferred]

### 6. References & Related Documents

- Provide links to relevant documentation, articles, or research
- Related design documents
- Competitor analysis
- Technical specifications or RFCs
- Relevant internal documentation
- External resources (articles, documentation, tutorials)

## Planning Guidelines

**Research Requirements**: Use web search to:
- Verify current best practices for the technologies involved
- Check for security considerations and common pitfalls
- Find reference implementations or patterns
- Validate technology choices and compatibility

1. **Be Comprehensive**: Cover all dimensions - technical, security, performance, testing 
2. **Be Specific**: Avoid vague statements; provide concrete phases, files, examples, and numbers 
3. **Be Actionable**: Every section should guide implementation decisions
4. **Be Realistic**: Honest about complexity, risks, and timeline
5. **Think Ahead**: Consider scalability, maintainability, and future enhancements
6. **Security-First**: Integrate security considerations throughout, not as an afterthought
7. **Test-Driven**: Plan for testing from the beginning

### Tone & Style

- **Precise**: Avoid ambiguity; be specific and concrete
- **Technical**: Appropriate technical depth for developers
- **Readable**: Clear and well-organized for easy navigation
- **Active Voice**: "Create the authentication service" not "The 
  authentication service should be created"
- **Examples**: Include examples where they could add clarity
- **Professional**: Maintain professional technical documentation standards

## Output Format

Structure your plan as a well-formatted markdown document with:

- Clear hierarchical headings
- Bullet points for readability
- Tables where appropriate
- Links to external resources

## Deliverable

Save your complete planning in a markdown file named:

**`.features/plans/YYYYMMDD_{short-informative-title}.md`**

Where:

- `YYYYMMDD` is today's date (e.g., 20251013)
- `{short-informative-title}` is a brief, descriptive name for the 
  idea/feature using lowercase with hyphens (e.g., "ai-powered-code-review", 
  "real-time-collaboration", "user-authentication-system")

Example filename: `20251013_ai-powered-code-review.md`

This file will be read by other team members and AI agents, so ensure it is:

- Self-contained and comprehensive
- Well-organized with clear sections
- Professional in tone
- Free of jargon (or with explanations where technical terms are necessary)

---

Begin your planning now and create the markdown file with your plan.
