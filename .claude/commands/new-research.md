---

description: Conduct in-depth research on a feature and output your findings to a file.
argument-hint: [feature-description-file]

---

## Research Request

You are tasked with conducting thorough research on a project feature.

Feature description file: $1

Read and analyze the contents of this file carefully to fully understand the context, goals, and 
requirements before starting your research.

## Research Objectives

Your goal is to produce a comprehensive research document that will serve as a foundation for 
future planning and implementation. This research will be read by other team members and agents, 
so clarity and thoroughness are essential. 

## Required Research Components

### 1. Executive Summary

- Provide a concise overview of the idea/feature (2-3 paragraphs)
- Highlight the most critical findings upfront
- State the primary value proposition

### 2. Problem Space Analysis

- What problem does this idea/feature solve?
- Who experiences this problem? (target users/audience)
- What is the current state of solutions (if any)?
- What are the pain points with existing approaches?
- How significant/urgent is this problem?
- What metrics define "success"? (both user-facing and business metrics)

### 3. External Context

#### 3.1 Technical Landscape

- Research documentation for relevant libraries, frameworks, APIs
- Research current best practices and design patterns
- Research emerging technologies or trends shaping this area
- Research technical constraints or dependencies

#### 3.2 Market & Competitive Analysis

- Research similar solutions in the market
- Research key competitors or comparable products/features
- Research market size and adoption trends (if applicable)
- Research gaps in existing solutions
- Research unique differentiators or opportunities

### 4. Recommendations & Next Steps

- Is this idea/feature worth pursuing? (Yes/No/Conditional)
- Recommended approach or implementation strategy
- Immediate next steps
- Open questions that require further investigation

### 5. References & Resources

- Links to relevant documentation, articles, or research
- Competitor product pages or demos
- Technical specifications or standards
- Academic papers or case studies (if applicable)

## Research Guidelines

1. **Be Thorough**: Research deeply across all dimensions - technical, business, user experience,
   and competitive landscape
2. **Be Objective**: Present both opportunities and challenges fairly
3. **Be Specific**: Include concrete examples, numbers, and data where possible
4. **Be Actionable**: Provide clear recommendations
5. **Cite Sources**: Include links and references for all claims and data
6. **Think Critically**: Challenge assumptions and identify potential blind spots
7. **Consider Scale**: Think about how this would work at 10x, 100x, 1000x scale
8. **User-Centric**: Always consider the end-user perspective
9. **Web search**: Use web search extensively throughout your research
10. **Don't Code**: NEVER provide code 

### Format

- **Diagrams**: Use Mermaid, ASCII art, or clear text descriptions
- **Tables**: Use for comparisons, decision matrices, or structured data
- **Checklists**: Use `- [ ]` for task lists
- **Links**: Include working links to external resources

### Tone & Style

- **Precise**: Avoid ambiguity; be specific and concrete
- **Technical**: Appropriate technical depth for developers
- **Readable**: Clear and well-organized for easy navigation
- **Active Voice**: "Create the authentication service" not "The authentication service should 
  be created" 
- **Examples**: Include examples where they could add clarity
- **Professional**: Maintain professional technical documentation standards

## Output Format

Structure your research as a well-formatted markdown document with:

- Clear hierarchical headings
- Bullet points for readability
- Tables for comparisons where appropriate
- Links to external resources

## Deliverable

Save your complete planning in a markdown file under **`.features/research`** directory.

Name the file exactly the same as the feature description file.

This file will be read by other team members and AI agents, so ensure it is:

- Self-contained and comprehensive
- Well-organized with clear sections
- Professional in tone
- Free of jargon (or with explanations where technical terms are necessary)

---

Begin your research now and create the markdown file with your findings.
