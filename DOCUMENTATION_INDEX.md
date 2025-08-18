# Documentation Index

Complete guide to all documentation in the Email Sync system.

## Core Documentation

### Essential Files (Start Here)
- **[README.md](README.md)** - User guide, installation, and usage
- **[CLAUDE.md](CLAUDE.md)** - Development guide and system overview
- **[CHANGELOG.md](CHANGELOG.md)** - Recent changes and updates

### Technical References
- **[Docs/SERVICE_ARCHITECTURE.md](Docs/SERVICE_ARCHITECTURE.md)** - Clean services architecture
- **[Docs/PROJECT_PHILOSOPHY.md](Docs/PROJECT_PHILOSOPHY.md)** - Core principles
- **[Docs/CODE_QUALITY.md](Docs/CODE_QUALITY.md)** - Quality standards
- **[refactor-tracking/MIGRATION_GUIDE.md](refactor-tracking/MIGRATION_GUIDE.md)** - Migration from old services

## Feature Documentation

### MCP & Agents
- **[Docs/AGENT_REFERENCE.md](Docs/AGENT_REFERENCE.md)** - Complete agent reference
- **[Docs/MCP_TOOLS_REFERENCE.md](Docs/MCP_TOOLS_REFERENCE.md)** - MCP tools and setup
- **[mcp_server/CLAUDE.md](mcp_server/CLAUDE.md)** - MCP server architecture
- **[agent_framework/CLAUDE.md](agent_framework/CLAUDE.md)** - Agent framework details

### Quick Start Guides
Located in `Docs/QUICK_START_GUIDES/`:
- **[VSEARCH.md](Docs/QUICK_START_GUIDES/VSEARCH.md)** - Search CLI usage
- **[VECTOR_SEARCH_CHEATSHEET.md](Docs/QUICK_START_GUIDES/VECTOR_SEARCH_CHEATSHEET.md)** - AI search cheat sheet
- **[LEGAL_BERT_DOCUMENTATION.md](Docs/QUICK_START_GUIDES/LEGAL_BERT_DOCUMENTATION.md)** - Legal BERT embeddings
- **[DEVELOPER_COMMANDS.md](Docs/QUICK_START_GUIDES/DEVELOPER_COMMANDS.md)** - Common commands
- **[PRE_COMMIT_HOOKS.md](Docs/QUICK_START_GUIDES/PRE_COMMIT_HOOKS.md)** - Git hooks setup

## Service Documentation

### Clean Services (New Architecture)
- **[services/README.md](services/README.md)** - Clean services overview
- **[services/embeddings/](services/embeddings/)** - EmbeddingService (~100 lines)
- **[services/vector_store/](services/vector_store/)** - VectorStore (~150 lines)
- **[services/search/](services/search/)** - SearchService (~200 lines)

### Core Service Implementations
Each service has detailed documentation:
- **[src/app/core/services/gmail/CLAUDE.md](src/app/core/services/gmail/CLAUDE.md)** - Gmail service
- **[src/app/core/services/pdf/CLAUDE.md](src/app/core/services/pdf/CLAUDE.md)** - PDF processing
- **[src/app/core/services/transcription/CLAUDE.md](src/app/core/services/transcription/CLAUDE.md)** - Transcription
- **[src/app/core/services/search/CLAUDE.md](src/app/core/services/search/CLAUDE.md)** - Search orchestration

## Development Resources

### Testing
- **[tests/README.md](tests/README.md)** - Testing guide and philosophy
- **[Docs/WORK_IN_PROGRESS_DOCS/TESTING_IMPLEMENTATION_PLAN.md](Docs/WORK_IN_PROGRESS_DOCS/TESTING_IMPLEMENTATION_PLAN.md)** - Test expansion plan

### Work in Progress
- **[Docs/WORK_IN_PROGRESS_DOCS/FEATURES_TODO_LIST](Docs/WORK_IN_PROGRESS_DOCS/FEATURES_TODO_LIST)** - Active feature work

### Component Documentation
- **[shared/CLAUDE.md](shared/CLAUDE.md)** - Shared components
- **[scripts/cli/CLAUDE.md](scripts/cli/CLAUDE.md)** - CLI architecture
- **[src/app/core/pipelines/CLAUDE.md](src/app/core/pipelines/CLAUDE.md)** - Processing pipelines

## Finding Documentation

### By User Type
- **End Users**: Start with README.md
- **Developers**: Start with CLAUDE.md, then SERVICE_ARCHITECTURE.md
- **Contributors**: Read PROJECT_PHILOSOPHY.md first

### By Topic
- **Search**: VSEARCH.md, VECTOR_SEARCH_CHEATSHEET.md
- **Embeddings**: LEGAL_BERT_DOCUMENTATION.md, services/embeddings/
- **Architecture**: SERVICE_ARCHITECTURE.md, PROJECT_PHILOSOPHY.md
- **Testing**: tests/README.md
- **MCP/Agents**: AGENT_REFERENCE.md, MCP_TOOLS_REFERENCE.md

### By Task
- **Setting up**: README.md → Installation section
- **Searching**: VSEARCH.md, VECTOR_SEARCH_CHEATSHEET.md
- **Developing**: CLAUDE.md, DEVELOPER_COMMANDS.md
- **Testing**: tests/README.md
- **Migrating**: MIGRATION_GUIDE.md

## Documentation Standards

### File Naming
- `README.md` - Overview and usage
- `CLAUDE.md` - Technical development guide
- `*_GUIDE.md` - How-to guides
- `*_REFERENCE.md` - API references

### Content Structure
1. **Overview** - What and why
2. **Quick Start** - Get running fast
3. **Details** - Complete information
4. **Examples** - Real usage
5. **Troubleshooting** - Common issues

### Maintenance
- Update docs with code changes
- Remove outdated information
- Keep examples working
- Test code snippets

## Documentation Status

### Up to Date ✅
- README.md
- CLAUDE.md
- CHANGELOG.md
- SERVICE_ARCHITECTURE.md
- AGENT_REFERENCE.md
- MCP_TOOLS_REFERENCE.md
- This index

### Active Development 🔄
- Testing implementation plan
- Feature TODO list

### Service-Specific 📁
- Each service maintains its own CLAUDE.md
- Updated with service changes
- Contains implementation details

---

*Last updated: 2025-08-13 - Documentation consolidation completed*
