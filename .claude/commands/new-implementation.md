---

description: Create a detailed implementation plan for a feature based on its description and, 
optionally, prior research findings. 
argument-hint: [description-file] [research-file] [plan-file] [additional-details]

---

## Implementation Request

You are tasked with implementing a project feature.

Before you begin, carefully read and analyze all provided files to fully understand the context, 
objectives, and detailed implementation steps. 

You must always read the **feature description file** and the **implementation plan file**.  
If a **research file** is provided, also read it and take into account any relevant insights, 
recommendations, or constraints documented there. 

Your implementation must strictly follow the plan and remain aligned with the feature’s original 
goals and requirements. 

- **Feature description file:** $1  
- **Research file (optional):** $2
- **Implementation plan file:** $3  

$4

---

## Strategy by Size

### 🔹 XS/S Tasks (< 200 lines)

**Mode:** 100% automated

**Process:**
1. Implement all changes sequentially
2. Run tests
3. Generate PR automatically

**Does not require active supervision.**

---

### 🔸 M/L Tasks (5-10+ files)

**Mode:** Active supervision

**Process:**
1. **CONFIRM WITH HUMAN before starting**
2. Implement file by file according to plan order
3. **After each file:**
   - Show summary of changes
   - Wait for confirmation or adjustments
4. Run tests after critical components

**Human can press ESC to stop.**

---

## Strict Rules

1. **Follow the plan to the letter**
   - If something isn't in the plan → DON'T improvise
   - If a problem arises → STOP and consult

2. **Sequential implementation**
   - One file at a time
   - Respect specified order
   - Don't skip steps

3. **Continuous self-validation**
   - Tests after each change
   - Verify nothing breaks
   - Confirm correct imports

4. **Clear communication**
   - Announce which file you're modifying
   - Summarize changes after each file
   - Report any deviation

5. **Tools $ MCPs**: 
   - Use the tools or MCPs available to validate implementation (e.g. "playwright" for frontend 
     checks, etc.)  

## Communication Format

**When starting a file:**
```
🔧 Modifying: src/components/NewComponent.tsx
Purpose: [from plan]
```

**When completing a file:**
```
✅ Completed: src/components/NewComponent.tsx

Changes made:
- Created component with userId and onComplete props
- Implemented loading/error/data state
- Added edge cases for invalid userId

Tests: ✅ Passing
```

## Deliverable

Your main deliverable is the plan implementation, with testing and PR ready to be merged to `main`.

However, it's useful to also save a summary of the process carried out in your implementation. 
Do it when I tell you that everything is correct and that we can end the session. Ask me for 
confirmation. When approved save this summary in a markdown file named:

**`.features/implementation/YYYYMMDD_{short-informative-title}.md`**

Where:

- `YYYYMMDD` is today's date (e.g., 20251013)
- `{short-informative-title}` is a brief, descriptive name for the 
  idea/feature using lowercase with hyphens (e.g., "ai-powered-code-review", 
  "real-time-collaboration", "user-authentication-system")

Example filename: `20251013_ai-powered-code-review.md`

## Post-Implementation

1. **Human performs manual testing**
2. **Superficial code review** (20% of time)
   - Focus on integration, not details
3. **If plan was perfect → code will be correct**
