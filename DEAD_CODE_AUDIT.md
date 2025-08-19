# Dead Code Audit Report

Generated: 2025-08-18
Tool: vulture
Confidence levels: 60% (may include false positives), 90%+, 100%

## Summary

- **Total Issues**: 330+ unused code elements
- **File Categories**: 45+ files affected
- **Primary Areas**: MCP servers, test fixtures, CLI handlers, database methods

## Issues by Category

### High Confidence (90%+)
These are very likely unused and safe to remove:

#### Import Issues
- `vector_debug_fix.py:20` - unused import 'EmailDatabase' (90% confidence)

#### Test Variables
- `tests/smoke/test_system_health.py:110` - unused variable 'mock_env' (100% confidence)
- `tests/utilities/test_embedding_service.py:263` - unused variable 'attention_mask' (100% confidence)
- `tests/transcription_service/test_integration.py:218` - unused variable 'should_store' (60% confidence)

### MCP Server Handlers (60% confidence) - ✅ CONFIRMED FALSE POSITIVES
**ANALYSIS COMPLETE**: These are functional handlers registered via decorators - **NO ACTION NEEDED**:

#### Legal Intelligence MCP
- `infrastructure/mcp_servers/legal_intelligence_mcp.py:675` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/legal_intelligence_mcp.py:797` - unused function 'handle_call_tool'

#### Search Intelligence MCP  
- `infrastructure/mcp_servers/search_intelligence_mcp.py:429` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/search_intelligence_mcp.py:583` - unused function 'handle_call_tool'

#### Other MCP Servers
- `infrastructure/mcp_servers/docs_mcp_server.py:140` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/docs_mcp_server.py:167` - unused function 'handle_call_tool'
- `infrastructure/mcp_servers/entity_mcp_server.py:184` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/entity_mcp_server.py:253` - unused function 'handle_call_tool'
- `infrastructure/mcp_servers/legal_mcp_server.py:418` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/legal_mcp_server.py:485` - unused function 'handle_call_tool'
- `infrastructure/mcp_servers/search_mcp_server.py:200` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/search_mcp_server.py:268` - unused function 'handle_call_tool'
- `infrastructure/mcp_servers/timeline_mcp_server.py:348` - unused function 'handle_list_tools'
- `infrastructure/mcp_servers/timeline_mcp_server.py:436` - unused function 'handle_call_tool'

### Entity Processing (60% confidence)
Potential API methods - **REVIEW CAREFULLY**:

#### Entity Database
- `entity/database.py:184` - unused method 'get_entities_by_type'
- `entity/database.py:242` - unused method 'get_consolidated_entity'

#### Entity Extractors
- `entity/extractors/combined_extractor.py:212` - unused method 'get_extractor_info'
- `entity/extractors/extractor_factory.py:130` - unused method 'validate_extractor_config'
- `entity/extractors/extractor_factory.py:162` - unused variable 'EntityExtractor'
- `entity/extractors/legal_extractor.py:320` - unused method 'get_legal_role_types'
- `entity/extractors/relationship_extractor.py:302` - unused method 'get_relationship_types'
- `entity/extractors/spacy_extractor.py:158` - unused method 'extract_entities_batch'
- `entity/extractors/spacy_extractor.py:213` - unused method 'get_model_info'
- `entity/main.py:318` - unused method 'extract_entities_batch'

#### Entity Processors
- `entity/processors/entity_normalizer.py:56` - unused attribute 'role_synonyms'

### Gmail Service (60% confidence)
- `gmail/oauth.py:69` - unused method 'is_authenticated'
- `gmail/storage.py:329` - unused attribute 'row_factory'
- `gmail/storage.py:346` - unused attribute 'row_factory'
- `gmail/validators.py:118` - unused method 'validate_email_size'
- `gmail/validators.py:169` - unused method 'validate_date_range'
- `gmail/validators.py:247` - unused method 'validate_query_limit'

### Document Processing Infrastructure
#### Document Pipeline
- `infrastructure/documents/document_pipeline.py:41` - unused class 'DocumentPipeline'
- `infrastructure/documents/document_pipeline.py:247` - unused method 'process_directory'
- `infrastructure/documents/document_pipeline.py:297` - unused method 'get_pipeline_stats'

#### Format Detection
- `infrastructure/documents/format_detector.py:139` - unused method 'get_supported_extensions'
- `infrastructure/documents/format_detector.py:143` - unused method 'get_format_info'

#### Lifecycle Management
- `infrastructure/documents/lifecycle_manager.py:149` - unused method 'list_files'
- `infrastructure/documents/lifecycle_manager.py:157` - unused method 'get_file_path'

#### Naming Convention
- `infrastructure/documents/naming_convention.py:35` - unused method 'raw_name'
- `infrastructure/documents/naming_convention.py:144` - unused method 'extract_metadata_from_name'

#### Document Processors
- `infrastructure/documents/processors/docx_processor.py:244` - unused method 'extract_comments'
- `infrastructure/documents/processors/markdown_processor.py:210` - unused method 'extract_links'
- `infrastructure/documents/processors/markdown_processor.py:224` - unused method 'extract_headings'
- `infrastructure/documents/processors/text_processor.py:23` - unused attribute 'supported_encodings'

### Pipeline Infrastructure
- `infrastructure/pipelines/data_pipeline.py:104` - unused method 'prepare_for_export'
- `infrastructure/pipelines/data_pipeline.py:143` - unused method 'get_pipeline_stats'
- `infrastructure/pipelines/data_pipeline.py:154` - unused method 'cleanup_export'
- `infrastructure/pipelines/orchestrator.py:243` - unused method 'process_raw_document'
- `infrastructure/pipelines/orchestrator.py:345` - unused method 'process_staged_document'
- `infrastructure/pipelines/orchestrator.py:423` - unused method 'export_document'

### Knowledge Graph
- `knowledge_graph/graph_queries.py:102` - unused method 'format_bfs_results'
- `knowledge_graph/main.py:163` - unused method 'find_document_cluster'
- `knowledge_graph/main.py:281` - unused method 'build_topic_hierarchy'
- `knowledge_graph/similarity_analyzer.py:90` - unused method 'get_similarity_stats'
- `knowledge_graph/similarity_analyzer.py:124` - unused method 'find_outliers'
- `knowledge_graph/topic_clustering.py:177` - unused method 'get_cluster_keywords'
- `knowledge_graph/topic_clustering.py:222` - unused method 'export_clusters'

### PDF Service
- `pdf/ocr/ocr_coordinator.py:166` - unused method 'get_ocr_stats'
- `pdf/ocr/ocr_engine.py:214` - unused method 'get_engine_info'
- `pdf/ocr/page_processor.py:268` - unused method 'get_processing_stats'
- `pdf/pdf_processor_enhanced.py:277` - unused method 'get_processor_stats'
- `pdf/pdf_storage_enhanced.py:196` - unused method 'get_storage_stats'

### Search Intelligence
- `search_intelligence/duplicate_detector.py:151` - unused method 'get_duplicate_stats'
- `search_intelligence/main.py:254` - unused method 'batch_similarity_search'
- `search_intelligence/similarity.py:143` - unused method 'get_similarity_distribution'

### Legal Intelligence
- `legal_intelligence/main.py:78` - unused method 'extract_legal_timeline'
- `legal_intelligence/main.py:132` - unused method 'analyze_case_strength'
- `legal_intelligence/main.py:287` - unused method 'generate_legal_summary'

### Summarization
- `summarization/engine.py:258` - unused method 'get_summary_stats'
- `summarization/engine.py:295` - unused method 'export_summaries'

### Transcription
- `transcription/main.py:80` - unused method 'process_directory'
- `transcription/providers/base_provider.py:90` - unused method 'get_legal_prompt'
- `transcription/providers/base_provider.py:154` - unused method 'calculate_basic_stats'
- `transcription/providers/base_provider.py:183` - unused method 'export_to_csv'

### Utilities
#### Archive Management
- `utilities/enhanced_archive_manager.py:126` - unused method 'organize_by_date'
- `utilities/enhanced_archive_manager.py:210` - unused method 'cleanup_orphaned_links'

#### Timeline
- `utilities/timeline/database.py:112` - unused method 'create_event_relationship'
- `utilities/timeline/database.py:137` - unused method 'get_related_events'

#### Vector Store
- `utilities/vector_store/__init__.py:68` - unused method 'batch_upsert'

### CLI Tools and Scripts
#### CLI Handlers
- `tools/cli/dedup_handler.py:18` - unused function 'find_duplicates_command'
- `tools/cli/dedup_handler.py:108` - unused function 'compare_documents_command'
- `tools/cli/dedup_handler.py:181` - unused function 'deduplicate_database_command'
- `tools/cli/dedup_handler.py:300` - unused function 'build_duplicate_index_command'
- `tools/cli/health_monitor.py:514` - unused function 'health_check_command'

#### Script CLI Handlers
- `tools/scripts/cli/hybrid_handler.py:15` - unused class 'HybridModeHandler'
- `tools/scripts/cli/hybrid_handler.py:31` - unused method 'merge_results'
- `tools/scripts/cli/hybrid_handler.py:217` - unused method 'get_merge_stats'
- `tools/scripts/cli/intelligence_handler.py:119` - unused function 'duplicates_command'
- `tools/scripts/cli/intelligence_handler.py:150` - unused function 'entities_command'
- `tools/scripts/cli/intelligence_handler.py:176` - unused function 'intel_summarize_command'
- `tools/scripts/cli/legal_handler.py:22` - unused function 'process_legal_case'
- `tools/scripts/cli/legal_handler.py:78` - unused function 'generate_legal_timeline'
- `tools/scripts/cli/legal_handler.py:130` - unused function 'build_legal_graph'
- `tools/scripts/cli/legal_handler.py:191` - unused function 'search_legal'
- `tools/scripts/cli/legal_handler.py:328` - unused function 'summarize_legal_docs'

#### Service Locator
- `tools/scripts/cli/service_locator.py:42` - unused method 'get_gmail_service'
- `tools/scripts/cli/service_locator.py:48` - unused method 'get_pdf_service'
- `tools/scripts/cli/service_locator.py:60` - unused method 'get_entity_service'
- `tools/scripts/cli/service_locator.py:66` - unused method 'get_timeline_service'
- `tools/scripts/cli/service_locator.py:72` - unused method 'get_notes_service'
- `tools/scripts/cli/service_locator.py:78` - unused method 'get_service_health_status'

#### Migration Scripts
- `tools/scripts/legal_timeline_export.py:21` - unused attribute 'row_factory'
- `tools/scripts/migrate_to_loguru_bowler.py:64` - unused method 'migrate_imports'

### Test Infrastructure
#### Shared Test Infrastructure
- `shared/simple_db.py:487` - unused method 'get_collection_stats'
- `shared/simple_db.py:510` - unused method 'export_to_json'

#### Test Fixtures and Utilities
- `tests/integration/test_helpers.py:144` - unused function 'wait_for_processing'
- `tests/pdf_service/conftest.py:194` - unused function 'temp_pdf_files'
- `tests/pdf_service/conftest.py:231` - unused function 'malformed_pdf_test_cases'
- `tests/pdf_service/conftest.py:282` - unused function 'sample_document_hashes'
- `tests/pdf_service/conftest.py:300` - unused function 'pdf_processing_mock_data'
- `tests/pdf_service/conftest.py:329` - unused function 'database_migration_scenarios'
- `tests/pdf_service/conftest.py:406` - unused function 'populated_test_database'
- `tests/pdf_service/conftest.py:442` - unused function 'database_error_scenarios'
- `tests/pdf_service/test_large_pdf_handling.py:25` - unused method 'large_pdf_path'
- `tests/shared_test_fixtures.py:33` - unused method 'get_embeddings'
- `tests/shared_test_fixtures.py:52` - unused attribute 'row_factory'
- `tests/shared_test_fixtures.py:132` - unused method 'get_email_by_id'
- `tests/smoke/conftest.py:32` - unused function 'mock_env'
- `tests/test_timeline_extractor.py:43` - unused attribute 'sample_email_text'
- `tests/timeline/conftest.py:333` - unused function 'sample_timeline_events'
- `tests/timeline/conftest.py:403` - unused function 'timeline_error_scenarios'
- `tests/timeline/conftest.py:452` - unused function 'date_filtering_test_data'

## Recommended Actions

### Immediate (High Confidence)
1. **Remove unused imports** - `vector_debug_fix.py:20`
2. **Remove unused test variables** - Variables with 100% confidence

### Review Required (API/Interface Methods)
1. ~~**MCP Server Handlers** - Verify these aren't called via reflection~~ ✅ **CONFIRMED FUNCTIONAL**
2. **Entity Extraction Methods** - May be part of public API
3. **Database Methods** - Could be used by external tools
4. **Service Locator Methods** - May be used for dependency injection

### Systematic Cleanup Areas
1. **Test Fixtures** - Remove unused test infrastructure
2. **CLI Handlers** - Remove unused command functions
3. **Stats/Info Methods** - Many get_*_stats methods unused
4. **Export Methods** - Several export functions unused

### False Positive Risk
- Database `row_factory` attributes (SQLite3 callback)
- Test fixtures (may be used by pytest discovery)
- ~~MCP server handlers (called via protocol dispatch)~~ ✅ **CONFIRMED - ALL FUNCTIONAL**
- CLI command functions (called via argument parsing)

## Next Steps
1. Start with 100% confidence items
2. ~~Verify MCP server handlers are actually unused~~ ✅ **COMPLETED - ALL FUNCTIONAL**
3. Review API methods for external usage
4. Consider adding `# pragma: no cover` for intentionally unused code
5. Remove dead code systematically by category