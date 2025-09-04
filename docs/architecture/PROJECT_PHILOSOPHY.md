# Project Philosophy

## Personal Project Guidelines

order
- *Maintainable, Valuable, Actionable insights for strategy and drafting of email replys is required.* 

## Core Principles

### 0. **Architecture Limits (ENFORCED)**
- Target <550 lines for new files; existing working files guided by functionality
- Target <35 lines per function
- Target cyclomatic complexity of <15
- These are soft LIMITS to prevent drift

### 1. **Keep It Simple**
- Single-user system, no need for complex scaling
- SQLite works great for this use case
- Local file storage is sufficient
- Direct solutions over abstract ones

### 2. **YAGNI (You Ain't Gonna Need It)**
- No abstract base classes unless absolutely necessary
- No factory patterns for 2-3 implementations
- No dependency injection frameworks
- No microservices or event buses

### 3. **Practical Solutions**
- Working code beats perfect abstractions
- Config files and constants are fine
- Document any hardcoded values
- Simple patterns that work

### 4. **Maintenance Over Features**
- Code should be readable in 6 months
- Comments explain WHY, not WHAT
- Delete unused code immediately
- Refactor when it hurts, not before

### 5. **Direct Over Indirect**
- Import and use directly, avoid wrappers
- One clear way to do things
- Explicit is better than implicit
- Flat is better than nested

## Anti-Patterns to Avoid

 **Over-Engineering**
- Complex patterns for simple problems
- Abstract factories when if/else works

Note on pragmatic seams: We use tiny, patchable factory hooks only where tests must inject services cleanly (e.g., MCP servers, Legal Intelligence shims). These are minimal and avoid adding complexity to runtime code paths.
- Deep inheritance hierarchies
- Multiple layers of indirection

 **Unnecessary Abstraction**
- Wrapping standard library without adding value
- Interfaces for single implementations
- Building frameworks instead of solving problems
- Adding complexity for hypothetical future needs

 **Premature Optimization**
- Caching before measuring
- Async everything
- Complex connection pooling for local services
- Micro-optimizations over readability

## Good Patterns That Work

WORKING: **Simple Functions**
- Pure functions where possible
- Clear input/output
- Single responsibility
- Under 35 lines (ENFORCED)
- Cyclomatic complexity < 10 (ENFORCED)

WORKING: **Flat Structure**
- Services at top level
- Minimal nesting
- Direct imports
- Clear file purposes

WORKING: **Standard Library First**
- Use built-in solutions
- Avoid heavy frameworks
- Minimal dependencies
- Well-known libraries only

WORKING: **Practical Error Handling**
- Return {"success": bool, "error": str}
- Log and continue when reasonable
- Fail fast when corrupted
- User-friendly messages

## Recent Achievements

### Architecture Compliance (Aug 2025)
- **PDF Service**: Refactored 606-line file into 6 modular components
- **Vector Service**: Split 865-line service into clean modules
- **Job Queue**: Built from scratch with all components <450 lines
- **Function Decomposition**: Major functions split into <30 line helpers

### Pipeline Architecture
- **Transactional Safety**: PDF→OCR→Vector with rollback
- **Job Queue**: Priority-based async processing
- **Modular OCR**: 6 focused components, each with single responsibility
- **Clean Separation**: Services independent, pipelines coordinate

## Summary

The architecture limits help keep the project manageable and prevent it from becoming too complex to maintain. The goal is a system that works reliably for its intended purpose - searching emails, documents, and transcripts with good performance on standard hardware.
