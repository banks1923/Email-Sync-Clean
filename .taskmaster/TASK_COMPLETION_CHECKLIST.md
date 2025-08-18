# Task Completion Checklist

## Before Marking Any Task as "Done"

### 1. Functional Verification ✅
- [ ] Feature produces actual output/results
- [ ] Data flows end-to-end through the system
- [ ] Results are persisted (database, files, etc.)
- [ ] No silent failures in logs

### 2. Integration Testing ✅
- [ ] Run a real-world test case
- [ ] Verify data appears where expected
- [ ] Check database tables contain data
- [ ] Confirm files are created/moved as designed

### 3. Evidence Collection ✅
- [ ] Screenshot or copy of actual output
- [ ] Database query showing records created
- [ ] Log entries showing successful processing
- [ ] Test script that validates the feature

### 4. Documentation Accuracy ✅
- [ ] Documentation matches actual behavior
- [ ] No claims of features that don't work
- [ ] Examples can be run successfully
- [ ] Error scenarios are documented

## Task Status Guidelines

### Use "in-progress" when:
- Structure/skeleton is created
- Tests are written but not passing
- Integration is partial
- Feature works in isolation but not integrated

### Use "done" ONLY when:
- Feature works end-to-end
- Data is actually produced and saved
- Integration tests pass
- Real usage scenario succeeds

## Red Flags 🚩
- Empty database tables after "processing"
- Unused directories/files
- Try/except blocks without logging
- "Should work" without verification
- Documentation before implementation

## Verification Commands

### For Database Features:
```bash
# Check if tables have data
sqlite3 emails.db "SELECT COUNT(*) FROM document_summaries;"
sqlite3 emails.db "SELECT COUNT(*) FROM document_intelligence;"
sqlite3 emails.db "SELECT COUNT(*) FROM relationship_cache;"
```

### For File Pipeline:
```bash
# Check if directories are used
ls -la data/raw/ data/staged/ data/processed/
find data/ -type f -name "*.pdf" -o -name "*.txt"
```

### For Integration:
```bash
# Process a real document and verify
scripts/vsearch upload test.pdf
sqlite3 emails.db "SELECT * FROM document_summaries ORDER BY created_at DESC LIMIT 1;"
```

## Task Master Commands for Better Tracking

### Add verification notes to tasks:
```bash
task-master update-subtask --id=<task.subtask> --prompt="Add verification: Must see data in X table after Y operation"
```

### Create test subtasks:
```bash
task-master add-task --prompt="Create integration test that verifies Task X produces real data"
```

### Document failures:
```bash
task-master update-task --id=<task> --prompt="Found issue: Feature creates structure but doesn't save data. Need to fix save operation."
```

## Recovery Process for Incomplete Tasks

1. **Revert Status**: Mark task as "in-progress"
2. **Add Fix Subtasks**: Create specific subtasks for missing functionality
3. **Create Tests First**: Write tests that fail until feature works
4. **Verify with Data**: Only mark done when data is produced
5. **Document Evidence**: Add proof of working feature to task notes
