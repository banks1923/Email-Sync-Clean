# Docstring Coverage Analysis Report
==================================================

## Overall Statistics
- **Total Python files analyzed**: 148
- **Total items (modules, classes, functions)**: 1475
- **Items with docstrings**: 1371
- **Overall coverage**: 92.9%

## Coverage by Directory

### tools/docs
- **Files**: 2
- **Items**: 21 total, 14 documented
- **Coverage**: 66.7%

### tools/preflight
- **Files**: 1
- **Items**: 6 total, 4 documented
- **Coverage**: 66.7%

### infrastructure/mcp_config
- **Files**: 2
- **Items**: 20 total, 14 documented
- **Coverage**: 70.0%

### utilities/maintenance
- **Files**: 2
- **Items**: 26 total, 20 documented
- **Coverage**: 76.9%

### shared/migrations
- **Files**: 1
- **Items**: 9 total, 7 documented
- **Coverage**: 77.8%

### config
- **Files**: 1
- **Items**: 18 total, 15 documented
- **Coverage**: 83.3%

### pdf
- **Files**: 10
- **Items**: 125 total, 109 documented
- **Coverage**: 87.2%

### utilities/timeline
- **Files**: 2
- **Items**: 16 total, 14 documented
- **Coverage**: 87.5%

### scripts
- **Files**: 10
- **Items**: 65 total, 58 documented
- **Coverage**: 89.2%

### scripts/archived_document_ai
- **Files**: 8
- **Items**: 56 total, 50 documented
- **Coverage**: 89.3%

### infrastructure/mcp_servers
- **Files**: 2
- **Items**: 20 total, 18 documented
- **Coverage**: 90.0%

### utilities/verification
- **Files**: 3
- **Items**: 20 total, 18 documented
- **Coverage**: 90.0%

### entity/extractors
- **Files**: 6
- **Items**: 64 total, 58 documented
- **Coverage**: 90.6%

### tools/codemods
- **Files**: 3
- **Items**: 23 total, 21 documented
- **Coverage**: 91.3%

### gmail
- **Files**: 6
- **Items**: 71 total, 65 documented
- **Coverage**: 91.5%

### .
- **Files**: 1
- **Items**: 12 total, 11 documented
- **Coverage**: 91.7%

### entity
- **Files**: 3
- **Items**: 37 total, 34 documented
- **Coverage**: 91.9%

### tools
- **Files**: 3
- **Items**: 26 total, 24 documented
- **Coverage**: 92.3%

### pdf/ocr
- **Files**: 9
- **Items**: 69 total, 64 documented
- **Coverage**: 92.8%

### tools/cli
- **Files**: 2
- **Items**: 17 total, 16 documented
- **Coverage**: 94.1%

### entity/processors
- **Files**: 1
- **Items**: 18 total, 17 documented
- **Coverage**: 94.4%

### shared
- **Files**: 19
- **Items**: 254 total, 241 documented
- **Coverage**: 94.9%

### scripts/archived_document_ai_attempts
- **Files**: 2
- **Items**: 37 total, 36 documented
- **Coverage**: 97.3%

### tools/scripts
- **Files**: 10
- **Items**: 47 total, 46 documented
- **Coverage**: 97.9%

### tools/scripts/cli
- **Files**: 11
- **Items**: 78 total, 77 documented
- **Coverage**: 98.7%

### bench
- **Files**: 1
- **Items**: 4 total, 4 documented
- **Coverage**: 100.0%

### email_parsing
- **Files**: 1
- **Items**: 24 total, 24 documented
- **Coverage**: 100.0%

### infrastructure/documents
- **Files**: 5
- **Items**: 49 total, 49 documented
- **Coverage**: 100.0%

### infrastructure/documents/processors
- **Files**: 4
- **Items**: 36 total, 36 documented
- **Coverage**: 100.0%

### infrastructure/pipelines
- **Files**: 1
- **Items**: 12 total, 12 documented
- **Coverage**: 100.0%

### legal_evidence
- **Files**: 3
- **Items**: 28 total, 28 documented
- **Coverage**: 100.0%

### legal_intelligence
- **Files**: 1
- **Items**: 32 total, 32 documented
- **Coverage**: 100.0%

### search_intelligence
- **Files**: 4
- **Items**: 56 total, 56 documented
- **Coverage**: 100.0%

### shared/archive/cli
- **Files**: 1
- **Items**: 5 total, 5 documented
- **Coverage**: 100.0%

### summarization
- **Files**: 1
- **Items**: 17 total, 17 documented
- **Coverage**: 100.0%

### tests
- **Files**: 2
- **Items**: 10 total, 10 documented
- **Coverage**: 100.0%

### tools/linting
- **Files**: 1
- **Items**: 6 total, 6 documented
- **Coverage**: 100.0%

### utilities
- **Files**: 1
- **Items**: 10 total, 10 documented
- **Coverage**: 100.0%

### utilities/deduplication
- **Files**: 1
- **Items**: 20 total, 20 documented
- **Coverage**: 100.0%

### utilities/embeddings
- **Files**: 1
- **Items**: 11 total, 11 documented
- **Coverage**: 100.0%

## Detailed File Analysis

### scripts/batch_process_pdfs.py
- **Coverage**: 33.3% (1/3)
- **Module docstring**: ✗ (none)
- **Functions missing docstrings**:
  - `process_pdf()` (line 39)

### tools/scripts/export_documents.py
- **Coverage**: 50.0% (1/2)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `main()` (line 21)

### pdf/wiring.py
- **Coverage**: 50.0% (5/10)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `make_ocr()` (line 33)
  - `make_validator()` (line 37)
  - `make_health_monitor()` (line 41)
  - `make_error_recovery()` (line 45)
  - `make_summarizer()` (line 49)

### scripts/get_emails.py
- **Coverage**: 50.0% (1/2)
- **Module docstring**: ✗ (none)

### infrastructure/mcp_config/config.py
- **Coverage**: 53.8% (7/13)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `MCPConfig`: ✓ (brief)
  - `MCPConfig`: ✗ (none)
    - Missing docstrings: get_mcp_servers, get_claude_desktop_servers, validate_config, check_security
  - `Config`: ✗ (none)

### tools/docs/audit.py
- **Coverage**: 60.0% (9/15)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ServiceLineCount`: ✗ (none)
  - `FileExistenceCheck`: ✗ (none)
  - `TestPathMapping`: ✗ (none)
  - `AuditReport`: ✗ (none)
  - `DocumentationAuditor`: ✗ (none)

### pdf/main.py
- **Coverage**: 65.2% (15/23)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `PDFService`: ✓ (detailed)
    - Missing docstrings: validator, ocr, summarizer, health_monitor, error_recovery

### tools/preflight/vector_parity_check.py
- **Coverage**: 66.7% (4/6)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `main()` (line 113)

### shared/retry_helper.py
- **Coverage**: 66.7% (4/6)
- **Module docstring**: ✓ (brief)
- **Functions missing docstrings**:
  - `decorator()` (line 32)
  - `wrapper()` (line 34)

### scripts/parse_all_emails.py
- **Coverage**: 66.7% (2/3)
- **Module docstring**: ✓ (brief)
- **Functions missing docstrings**:
  - `main()` (line 143)

### scripts/archived_document_ai/document_ai_manager.py
- **Coverage**: 66.7% (2/3)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `main()` (line 55)

### scripts/archived_document_ai/batch_process_documents.py
- **Coverage**: 66.7% (2/3)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `main()` (line 85)

### utilities/maintenance/vector_maintenance.py
- **Coverage**: 72.2% (13/18)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `VectorMaintenance`: ✓ (brief)

### utilities/verification/preflight_check.py
- **Coverage**: 75.0% (3/4)
- **Module docstring**: ✓ (brief)
- **Functions missing docstrings**:
  - `main()` (line 94)

### scripts/archived_document_ai/process_single_document.py
- **Coverage**: 75.0% (3/4)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `main()` (line 134)

### gmail/config.py
- **Coverage**: 75.0% (3/4)
- **Module docstring**: ✗ (none)
- **Classes**:
  - `GmailConfig`: ✓ (brief)

### shared/migrations/migrate.py
- **Coverage**: 77.8% (7/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `MigrationRunner`: ✓ (brief)
- **Functions missing docstrings**:
  - `main()` (line 122)

### entity/extractors/base_extractor.py
- **Coverage**: 80.0% (8/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `BaseExtractor`: ✓ (brief)

### gmail/oauth.py
- **Coverage**: 80.0% (4/5)
- **Module docstring**: ✗ (none)
- **Classes**:
  - `GmailAuth`: ✓ (brief)

### tools/docs/update_counts.py
- **Coverage**: 83.3% (5/6)
- **Module docstring**: ✓ (detailed)
- **Functions missing docstrings**:
  - `remove_transcription()` (line 104)

### config/settings.py
- **Coverage**: 83.3% (15/18)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DatabaseSettings`: ✓ (none)
  - `GmailSettings`: ✓ (brief)
  - `EntitySettings`: ✓ (brief)
    - Missing docstrings: validate_confidence
  - `VectorSettings`: ✓ (brief)
  - `APISettings`: ✓ (brief)
  - `PathSettings`: ✓ (brief)
  - `LoggingSettings`: ✓ (none)
  - `SystemSettings`: ✓ (brief)
  - `Settings`: ✓ (brief)
  - `SemanticSettings`: ✓ (brief)
  - `Config`: ✗ (none)
  - `Config`: ✗ (none)

### shared/thread_manager.py
- **Coverage**: 83.3% (10/12)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ThreadService`: ✓ (brief)
- **Functions missing docstrings**:
  - `sort_key()` (line 147)

### scripts/live_health_dashboard.py
- **Coverage**: 83.3% (10/12)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `LiveHealthDashboard`: ✗ (none)

### tools/preflight.py
- **Coverage**: 84.6% (11/13)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PreflightChecker`: ✓ (brief)
- **Functions missing docstrings**:
  - `main()` (line 420)

### tools/scripts/cli/entity_handler.py
- **Coverage**: 85.7% (6/7)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `EntityHandler`: ✓ (brief)

### entity/config.py
- **Coverage**: 85.7% (6/7)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EntityConfig`: ✓ (brief)

### pdf/ocr/validator.py
- **Coverage**: 85.7% (6/7)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PDFValidator`: ✓ (brief)

### pdf/ocr/postprocessor.py
- **Coverage**: 85.7% (6/7)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `OCRPostprocessor`: ✓ (brief)

### shared/unified_ingestion.py
- **Coverage**: 85.7% (6/7)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `UnifiedIngestionService`: ✓ (brief)

### utilities/timeline/database.py
- **Coverage**: 85.7% (6/7)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `TimelineDatabase`: ✓ (brief)

### pdf/pdf_health.py
- **Coverage**: 87.5% (7/8)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PDFHealthManager`: ✓ (brief)

### utilities/maintenance/schema_maintenance.py
- **Coverage**: 87.5% (7/8)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `SchemaMaintenance`: ✓ (brief)

### scripts/archived_document_ai/simple_legal_cleaner.py
- **Coverage**: 87.5% (7/8)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SimpleLegalCleaner`: ✓ (brief)

### gmail/main.py
- **Coverage**: 87.5% (14/16)
- **Module docstring**: ✗ (none)
- **Classes**:
  - `GmailService`: ✓ (brief)
- **Functions missing docstrings**:
  - `main()` (line 714)

### entity/database.py
- **Coverage**: 88.2% (15/17)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EntityDatabase`: ✗ (none)

### tools/cli/quarantine_handler.py
- **Coverage**: 88.9% (8/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `QuarantineHandler`: ✓ (brief)

### pdf/ocr/ocr_engine.py
- **Coverage**: 88.9% (8/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `OCREngine`: ✓ (brief)

### shared/simple_quarantine_manager.py
- **Coverage**: 88.9% (8/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `SimpleQuarantineManager`: ✓ (brief)

### shared/health_check.py
- **Coverage**: 88.9% (8/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `HealthCheck`: ✓ (brief)

### utilities/timeline/main.py
- **Coverage**: 88.9% (8/9)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `TimelineService`: ✓ (brief)

### tools/codemods/replace_content_id_sql.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SqlStringRewriter`: ✓ (brief)

### tools/codemods/centralize_config.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ConfigCentralizationTransformer`: ✓ (brief)

### entity/extractors/spacy_extractor.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `SpacyExtractor`: ✓ (brief)

### entity/extractors/combined_extractor.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `CombinedExtractor`: ✓ (brief)

### pdf/ocr/enhanced_ocr_coordinator.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `EnhancedOCRCoordinator`: ✓ (detailed)

### shared/content_quality_scorer.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ValidationStatus`: ✓ (brief)
  - `QualityMetrics`: ✓ (brief)
  - `ContentQualityScorer`: ✓ (brief)

### shared/simple_upload_processor.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SimpleUploadProcessor`: ✓ (brief)

### infrastructure/mcp_servers/legal_intelligence_mcp.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `LegalIntelligenceServer`: ✓ (brief)

### infrastructure/mcp_servers/search_intelligence_mcp.py
- **Coverage**: 90.0% (9/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SearchIntelligenceMCPServer`: ✓ (brief)

### pdf/pdf_processor.py
- **Coverage**: 90.9% (10/11)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PDFProcessor`: ✓ (brief)

### pdf/pdf_storage_enhanced.py
- **Coverage**: 90.9% (10/11)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EnhancedPDFStorage`: ✓ (brief)

### scripts/archived_document_ai/document_ai_enhanced.py
- **Coverage**: 90.9% (10/11)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DocumentResult`: ✓ (brief)
  - `EnhancedDocumentProcessor`: ✓ (brief)

### analyze_docstring_coverage.py
- **Coverage**: 91.7% (11/12)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `FunctionInfo`: ✓ (brief)
  - `ClassInfo`: ✓ (brief)
  - `ModuleInfo`: ✓ (brief)
  - `DocstringAnalyzer`: ✓ (brief)

### pdf/ocr/enhanced_ocr_engine.py
- **Coverage**: 91.7% (11/12)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `EnhancedOCREngine`: ✓ (detailed)

### utilities/verification/verify_semantic_wiring.py
- **Coverage**: 91.7% (11/12)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SemanticWiringVerifier`: ✓ (brief)

### scripts/verify_semantic_wiring.py
- **Coverage**: 91.7% (11/12)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SemanticWiringVerifier`: ✓ (brief)

### entity/extractors/relationship_extractor.py
- **Coverage**: 92.3% (12/13)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `RelationshipExtractor`: ✓ (brief)

### shared/unified_entity_processor.py
- **Coverage**: 92.3% (12/13)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `UnifiedEntityProcessor`: ✓ (brief)

### scripts/archived_document_ai/process_legal_docs_fixed.py
- **Coverage**: 92.9% (13/14)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ProcessingMetrics`: ✓ (brief)
    - Missing docstrings: latency_ms
  - `DocumentAIProcessor`: ✓ (brief)

### entity/extractors/legal_extractor.py
- **Coverage**: 93.3% (14/15)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `LegalExtractor`: ✓ (brief)

### shared/email_cleaner.py
- **Coverage**: 93.3% (14/15)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EmailCleaner`: ✓ (brief)

### gmail/storage.py
- **Coverage**: 93.3% (14/15)
- **Module docstring**: ✗ (none)
- **Classes**:
  - `EmailStorage`: ✓ (brief)

### gmail/gmail_api.py
- **Coverage**: 94.1% (16/17)
- **Module docstring**: ✗ (none)
- **Classes**:
  - `GmailAPI`: ✓ (brief)

### entity/processors/entity_normalizer.py
- **Coverage**: 94.4% (17/18)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EntityNormalizer`: ✓ (brief)

### scripts/archived_document_ai_attempts/process_legal_docs_enhanced.py
- **Coverage**: 97.0% (32/33)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `ProcessingState`: ✓ (brief)
  - `StateManager`: ✓ (brief)
  - `PDFSplitter`: ✓ (brief)
  - `EnhancedDocumentAIProcessor`: ✓ (brief)

### shared/simple_db.py
- **Coverage**: 97.1% (67/69)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DBMetrics`: ✓ (brief)
  - `SimpleDB`: ✓ (brief)

### bench/bench_simpledb.py
- **Coverage**: 100.0% (4/4)
- **Module docstring**: ✓ (brief)

### tools/diag_wiring.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (detailed)

### tools/migrate_simple_file_processing.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (detailed)

### tools/linting/check_schema_compliance.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (detailed)

### tools/cli/evidence_handler.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (brief)

### tools/scripts/extract_timeline.py
- **Coverage**: 100.0% (4/4)
- **Module docstring**: ✓ (brief)

### tools/scripts/make_helpers.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (brief)

### tools/scripts/reindex_qdrant_points.py
- **Coverage**: 100.0% (4/4)
- **Module docstring**: ✓ (detailed)

### tools/scripts/check_qdrant_documents.py
- **Coverage**: 100.0% (2/2)
- **Module docstring**: ✓ (brief)

### tools/scripts/backfill_content_id.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (detailed)

### tools/scripts/run_service_test.py
- **Coverage**: 100.0% (15/15)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ServiceTestHarness`: ✓ (brief)

### tools/scripts/sync_vector_store.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (detailed)

### tools/scripts/check_documents_in_vector.py
- **Coverage**: 100.0% (2/2)
- **Module docstring**: ✓ (brief)

### tools/scripts/process_embeddings.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (detailed)

### tools/scripts/cli/timeline_handler.py
- **Coverage**: 100.0% (2/2)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/process_handler.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/cli_main.py
- **Coverage**: 100.0% (11/11)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/search_handler.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/docs_handler.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/legal_handler.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/info_handler.py
- **Coverage**: 100.0% (4/4)
- **Module docstring**: ✓ (brief)

### tools/scripts/cli/service_locator.py
- **Coverage**: 100.0% (12/12)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ServiceLocator`: ✓ (detailed)

### tools/scripts/cli/upload_handler.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (detailed)

### tools/scripts/cli/intelligence_handler.py
- **Coverage**: 100.0% (13/13)
- **Module docstring**: ✓ (brief)

### tools/codemods/consolidate_search.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (brief)

### legal_intelligence/main.py
- **Coverage**: 100.0% (32/32)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `LegalIntelligenceService`: ✓ (brief)

### entity/main.py
- **Coverage**: 100.0% (13/13)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EntityService`: ✓ (detailed)

### entity/extractors/extractor_factory.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ExtractorFactory`: ✓ (brief)

### summarization/engine.py
- **Coverage**: 100.0% (17/17)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `TFIDFSummarizer`: ✓ (brief)
  - `TextRankSummarizer`: ✓ (brief)
  - `DocumentSummarizer`: ✓ (brief)

### tests/simple_mcp_validation.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (detailed)

### tests/run_mcp_tests.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (detailed)

### pdf/database_error_recovery.py
- **Coverage**: 100.0% (23/23)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `AlertSeverity`: ✓ (brief)
  - `DatabaseAlert`: ✓ (brief)
  - `DatabaseErrorRecovery`: ✓ (detailed)

### pdf/pdf_idempotent_writer.py
- **Coverage**: 100.0% (9/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `IdempotentPDFWriter`: ✓ (brief)

### pdf/pdf_validator.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PDFValidator`: ✓ (brief)

### pdf/database_health_monitor.py
- **Coverage**: 100.0% (16/16)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `DatabaseMetrics`: ✓ (brief)
  - `OperationMetric`: ✓ (brief)
  - `DatabaseHealthMonitor`: ✓ (detailed)

### pdf/pdf_processor_enhanced.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EnhancedPDFProcessor`: ✓ (brief)

### pdf/ocr/page_processor.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PageByPageProcessor`: ✓ (brief)

### pdf/ocr/ocr_coordinator.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `OCRCoordinator`: ✓ (brief)

### pdf/ocr/loader.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PDFLoader`: ✓ (brief)

### pdf/ocr/rasterizer.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `PDFRasterizer`: ✓ (brief)

### shared/html_cleaner.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (brief)

### shared/simple_file_processor.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (detailed)

### shared/loguru_config.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (brief)

### shared/date_utils.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (detailed)

### shared/naming_utils.py
- **Coverage**: 100.0% (40/40)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `MarkdownNamingUtils`: ✓ (brief)
  - `CollisionResolver`: ✓ (brief)
  - `FilenameValidator`: ✓ (brief)

### shared/email_parser.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `QuotedMessage`: ✓ (brief)

### shared/snippet_utils.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (brief)

### shared/error_handler.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ErrorHandler`: ✓ (brief)

### shared/file_operations.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `FileOperations`: ✓ (brief)

### shared/archive/cli/dedup_handler.py
- **Coverage**: 100.0% (5/5)
- **Module docstring**: ✓ (brief)

### search_intelligence/basic_search.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (detailed)

### search_intelligence/similarity.py
- **Coverage**: 100.0% (14/14)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DocumentSimilarityAnalyzer`: ✓ (brief)
  - `DocumentClusterer`: ✓ (brief)

### search_intelligence/duplicate_detector.py
- **Coverage**: 100.0% (14/14)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DuplicateDetector`: ✓ (brief)

### search_intelligence/main.py
- **Coverage**: 100.0% (20/20)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SearchIntelligenceService`: ✓ (brief)

### utilities/semantic_pipeline.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `SemanticPipeline`: ✓ (brief)

### utilities/embeddings/embedding_service.py
- **Coverage**: 100.0% (11/11)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EmbeddingService`: ✓ (brief)

### utilities/deduplication/near_duplicate_detector.py
- **Coverage**: 100.0% (20/20)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `MinHasher`: ✓ (brief)
  - `LSHIndex`: ✓ (brief)
  - `NearDuplicateDetector`: ✓ (brief)

### utilities/verification/verify_chain.py
- **Coverage**: 100.0% (4/4)
- **Module docstring**: ✓ (detailed)

### scripts/backup_database.py
- **Coverage**: 100.0% (11/11)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `DatabaseBackup`: ✓ (brief)

### scripts/system_health_graph.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (brief)

### scripts/parse_messages.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EmailBatchProcessor`: ✓ (brief)

### scripts/backfill_semantic.py
- **Coverage**: 100.0% (3/3)
- **Module docstring**: ✓ (brief)

### scripts/setup_semantic_schema.py
- **Coverage**: 100.0% (2/2)
- **Module docstring**: ✓ (brief)

### scripts/archived_document_ai/setup_bigquery.py
- **Coverage**: 100.0% (2/2)
- **Module docstring**: ✓ (brief)

### scripts/archived_document_ai/process_legal_docs_v2.py
- **Coverage**: 100.0% (11/11)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `DocumentAIProcessor`: ✓ (brief)

### scripts/archived_document_ai_attempts/execute_email_cleanup.py
- **Coverage**: 100.0% (4/4)
- **Module docstring**: ✓ (detailed)

### legal_evidence/evidence_tracker.py
- **Coverage**: 100.0% (12/12)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `EvidenceTracker`: ✓ (brief)

### legal_evidence/report_generator.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `LegalReportGenerator`: ✓ (brief)

### legal_evidence/thread_analyzer.py
- **Coverage**: 100.0% (9/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ThreadAnalyzer`: ✓ (brief)

### email_parsing/message_deduplicator.py
- **Coverage**: 100.0% (24/24)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `MessageBoundary`: ✓ (brief)
  - `ParsedMessage`: ✓ (brief)
  - `MessageDeduplicator`: ✓ (brief)

### infrastructure/pipelines/service_orchestrator.py
- **Coverage**: 100.0% (12/12)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `ServiceOrchestrator`: ✓ (detailed)

### infrastructure/mcp_config/generate.py
- **Coverage**: 100.0% (7/7)
- **Module docstring**: ✓ (detailed)

### infrastructure/documents/document_converter.py
- **Coverage**: 100.0% (13/13)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DocumentConverter`: ✓ (brief)

### infrastructure/documents/lifecycle_manager.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DocumentLifecycleManager`: ✓ (brief)

### infrastructure/documents/format_detector.py
- **Coverage**: 100.0% (9/9)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `FormatDetector`: ✓ (brief)

### infrastructure/documents/document_pipeline.py
- **Coverage**: 100.0% (6/6)
- **Module docstring**: ✓ (detailed)
- **Classes**:
  - `DocumentPipeline`: ✓ (brief)

### infrastructure/documents/naming_convention.py
- **Coverage**: 100.0% (13/13)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `NamingConvention`: ✓ (brief)

### infrastructure/documents/processors/text_processor.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `TextProcessor`: ✓ (brief)

### infrastructure/documents/processors/base_processor.py
- **Coverage**: 100.0% (8/8)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `BaseProcessor`: ✓ (brief)

### infrastructure/documents/processors/markdown_processor.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `MarkdownProcessor`: ✓ (brief)

### infrastructure/documents/processors/docx_processor.py
- **Coverage**: 100.0% (10/10)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `DocxProcessor`: ✓ (brief)

### gmail/validators.py
- **Coverage**: 100.0% (14/14)
- **Module docstring**: ✓ (brief)
- **Classes**:
  - `EmailValidator`: ✓ (brief)
  - `DateValidator`: ✓ (brief)
  - `InputSanitizer`: ✓ (brief)
  - `LimitValidator`: ✓ (brief)

## Critical Modules Needing Attention

**scripts/batch_process_pdfs.py** (33.3% coverage)
Missing: Module docstring, Function `process_pdf()`

## Documentation Quality Analysis

**Docstring Quality Distribution:**
- **None**: 109 items
- **Brief**: 1033 items
- **Detailed**: 333 items

## Examples of Good Documentation

- Module: diag_wiring.py
- Module: migrate_simple_file_processing.py
- Module: check_schema_compliance.py
- Module: update_counts.py
- Module: export_documents.py
- Module: reindex_qdrant_points.py
- Module: backfill_content_id.py
- Module: sync_vector_store.py
- Module: process_embeddings.py
- Module: entity_handler.py

## Recommendations

### Priority 1: Core Service APIs
Focus on documenting public APIs in these critical modules:
- **shared/simple_db.py**: 97.1% coverage
- **gmail/gmail_api.py**: 94.1% coverage
- **pdf/main.py**: 65.2% coverage
- **search_intelligence/main.py**: 100.0% coverage
- **legal_intelligence/main.py**: 100.0% coverage

### Priority 2: Documentation Standards
- Add module-level docstrings explaining purpose and usage
- Document all public classes and their purpose
- Add Args/Returns sections to complex functions
- Include usage examples for main entry points

### Priority 3: Focus Areas