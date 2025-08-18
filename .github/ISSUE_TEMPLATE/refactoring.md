---
name: Refactoring Task
about: Address architecture compliance or code quality issues
title: '[REFACTOR] '
labels: refactoring
assignees: ''
---

## Current Issue
Description of what needs to be refactored (e.g., file too long, function too complex, over-engineered).

## Architecture Violations
- [ ] New file exceeds 450 lines (existing working files may be acceptable)
- [ ] Functions exceed 30 lines
- [ ] Cyclomatic complexity >10
- [ ] Over-engineering present
- [ ] Cross-service dependencies
- [ ] Other: ___

## Target State
What the code should look like after refactoring.

## Refactoring Requirements
- [ ] Maintain functionality
- [ ] Follow "simple > complex" principle
- [ ] Preserve existing tests
- [ ] No breaking changes to public APIs
- [ ] Single responsibility enforcement

## Files to Refactor
List specific files and what needs to change.

---
@claude refactor this code to meet Email Sync architecture standards
