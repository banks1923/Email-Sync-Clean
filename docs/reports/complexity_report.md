## Code Complexity Report - 

### Cyclomatic Complexity
knowledge_graph/similarity_integration.py
    M 322:4 SimilarityIntegration._find_connected_cluster - B (8)
    M 130:4 SimilarityIntegration.update_existing_relationships - B (7)
    C 20:0 SimilarityIntegration - B (6)
    M 30:4 SimilarityIntegration.discover_and_store_similarities - B (6)
    M 350:4 SimilarityIntegration._calculate_cluster_similarity - B (6)
    M 200:4 SimilarityIntegration.get_similarity_network_stats - A (5)
    M 262:4 SimilarityIntegration.find_similarity_clusters - A (5)
    M 96:4 SimilarityIntegration.find_and_link_similar_content - A (3)
    M 308:4 SimilarityIntegration._get_content_ids - A (3)
    F 369:0 get_similarity_integration - A (1)
    M 25:4 SimilarityIntegration.__init__ - A (1)
knowledge_graph/timeline_relationships.py
    M 67:4 TimelineRelationships._extract_pdf_date - B (7)
    M 32:4 TimelineRelationships.extract_content_dates - A (5)
    M 90:4 TimelineRelationships._extract_transcript_date - A (5)
    M 119:4 TimelineRelationships._parse_date_patterns - A (5)
    M 220:4 TimelineRelationships._calculate_temporal_strength - A (5)
    M 283:4 TimelineRelationships.find_temporal_cluster - A (5)
    C 22:0 TimelineRelationships - A (4)
    M 253:4 TimelineRelationships._process_time_window - A (4)
    M 405:4 TimelineRelationships.extract_legal_dates - A (4)
    M 482:4 TimelineRelationships._calculate_temporal_clustering - A (4)
    M 55:4 TimelineRelationships._extract_email_date - A (3)
    M 105:4 TimelineRelationships._parse_date_string - A (3)
    M 178:4 TimelineRelationships._create_sequential_relationships - A (3)
    M 206:4 TimelineRelationships._get_all_content_dates - A (3)
    M 318:4 TimelineRelationships._determine_temporal_relationship - A (3)
    M 331:4 TimelineRelationships.get_timeline_context - A (3)
    M 360:4 TimelineRelationships._find_timeline_position - A (3)
    M 469:4 TimelineRelationships._get_date_range_stats - A (3)
    M 507:4 TimelineRelationships._count_temporal_clusters - A (3)
    M 147:4 TimelineRelationships.create_temporal_relationships - A (2)
    M 239:4 TimelineRelationships._create_concurrent_relationships - A (2)
    M 369:4 TimelineRelationships._get_before_content - A (2)
    M 387:4 TimelineRelationships._get_after_content - A (2)
    M 454:4 TimelineRelationships._get_relationship_counts - A (2)
    F 520:0 get_timeline_relationships - A (1)
    M 27:4 TimelineRelationships.__init__ - A (1)
    M 436:4 TimelineRelationships.get_temporal_statistics - A (1)
knowledge_graph/topic_clustering.py
    M 118:4 TopicClusteringService._generate_cluster_label - B (9)
    M 361:4 TopicClusteringService._find_best_cluster - B (9)
    M 214:4 TopicClusteringService._extract_entities_from_content - B (7)
    C 26:0 TopicClusteringService - A (5)
    M 77:4 TopicClusteringService._get_content_embeddings - A (5)
    M 170:4 TopicClusteringService.calculate_entity_cooccurrence - A (5)
    M 235:4 TopicClusteringService._filter_cooccurrence_matrix - A (5)
    M 301:4 TopicClusteringService.update_clusters_incrementally - A (5)
    M 333:4 TopicClusteringService._get_existing_clusters - A (5)
    M 148:4 TopicClusteringService._store_cluster_relationships - A (4)
    M 96:4 TopicClusteringService._organize_clusters - A (3)
    M 255:4 TopicClusteringService._store_cooccurrence_relationships - A (3)
    M 430:4 TopicClusteringService.get_topic_statistics - A (3)
    M 39:4 TopicClusteringService.perform_hierarchical_clustering - A (2)
    M 286:4 TopicClusteringService._get_top_cooccurrences - A (2)
    M 404:4 TopicClusteringService._add_to_cluster - A (2)
    F 465:0 get_topic_clustering_service - A (1)
    M 32:4 TopicClusteringService.__init__ - A (1)
knowledge_graph/main.py
    M 205:4 KnowledgeGraphService.get_edges_by_node - B (6)
    M 409:4 KnowledgeGraphService._breadth_first_search - A (5)
    M 432:4 KnowledgeGraphService._add_neighbors_to_queue - A (5)
    M 130:4 KnowledgeGraphService.get_node_by_content - A (4)
    M 142:4 KnowledgeGraphService.get_node - A (4)
    M 155:4 KnowledgeGraphService.add_edge - A (4)
    M 279:4 KnowledgeGraphService.batch_add_nodes - A (4)
    M 304:4 KnowledgeGraphService.batch_add_edges - A (4)
    C 19:0 KnowledgeGraphService - A (3)
    M 188:4 KnowledgeGraphService._get_or_create_node - A (3)
    M 338:4 KnowledgeGraphService.get_graph_stats - A (3)
    M 381:4 KnowledgeGraphService.get_metadata - A (3)
    M 394:4 KnowledgeGraphService.find_shortest_path - A (3)
    M 29:4 KnowledgeGraphService._ensure_schema - A (2)
    M 93:4 KnowledgeGraphService._create_indexes - A (2)
    M 108:4 KnowledgeGraphService.add_node - A (2)
    M 229:4 KnowledgeGraphService.get_related_content - A (2)
    M 244:4 KnowledgeGraphService._build_related_content_query - A (2)
    M 266:4 KnowledgeGraphService._build_related_content_params - A (2)
    M 368:4 KnowledgeGraphService.set_metadata - A (2)
    F 454:0 get_knowledge_graph_service - A (1)
    M 24:4 KnowledgeGraphService.__init__ - A (1)
    M 40:4 KnowledgeGraphService._create_tables - A (1)
    M 48:4 KnowledgeGraphService._create_nodes_table - A (1)
    M 63:4 KnowledgeGraphService._create_edges_table - A (1)
    M 80:4 KnowledgeGraphService._create_metadata_table - A (1)
knowledge_graph/similarity_analyzer.py
    M 111:4 SimilarityAnalyzer.batch_compute_similarities - B (6)
    M 57:4 SimilarityAnalyzer.compute_similarity - A (5)
    M 265:4 SimilarityAnalyzer.precompute_similarities - A (5)
    M 291:4 SimilarityAnalyzer.get_similarity_distribution - A (5)
    C 20:0 SimilarityAnalyzer - A (4)
    M 149:4 SimilarityAnalyzer.find_similar_content - A (4)
    M 98:4 SimilarityAnalyzer._cosine_similarity - A (3)
    M 171:4 SimilarityAnalyzer._get_cached_similarity - A (3)
    M 245:4 SimilarityAnalyzer.clear_cache - A (2)
    F 314:0 get_similarity_analyzer - A (1)
    M 25:4 SimilarityAnalyzer.__init__ - A (1)
    M 32:4 SimilarityAnalyzer._setup_cache_table - A (1)
    M 194:4 SimilarityAnalyzer._cache_similarity - A (1)
    M 215:4 SimilarityAnalyzer._hash_content_pair - A (1)
    M 224:4 SimilarityAnalyzer.get_cache_stats - A (1)
knowledge_graph/graph_queries.py
    M 507:4 GraphQueryService.export_for_visualization - C (14)
    M 202:4 GraphQueryService.calculate_pagerank - C (13)
    M 129:4 GraphQueryService.find_all_paths - C (12)
    M 419:4 GraphQueryService.discover_entity_networks - B (10)
    M 566:4 GraphQueryService._format_for_d3 - B (10)
    M 336:4 GraphQueryService.get_timeline_context - B (9)
    M 35:4 GraphQueryService.breadth_first_traversal - B (7)
    C 22:0 GraphQueryService - B (6)
    M 285:4 GraphQueryService.find_related_content - B (6)
    M 102:4 GraphQueryService.format_bfs_results - A (5)
    M 77:4 GraphQueryService._get_neighbors - A (3)
    M 260:4 GraphQueryService.get_top_nodes_by_pagerank - A (3)
    M 488:4 GraphQueryService._get_edge_between_contents - A (3)
    F 649:0 get_graph_query_service - A (2)
    M 27:4 GraphQueryService.__init__ - A (1)
    M 71:4 GraphQueryService._get_node_by_content - A (1)
    M 190:4 GraphQueryService._get_edges_for_node - A (1)
    M 623:4 GraphQueryService._format_node_for_export - A (1)
    M 636:4 GraphQueryService._format_edge_for_export - A (1)
tools/linting/check_schema_compliance.py
    F 18:0 check_content_id_usage - C (13)
    F 149:0 main - B (10)
    F 90:0 check_uuid_consistency - B (7)
    F 114:0 run_libcst_idempotency_check - B (7)
    F 65:0 check_business_key_patterns - B (6)
tools/cli/vsearch
    F 28:0 search_command - B (7)
    F 100:0 display_keyword_results - B (7)
    F 66:0 display_results - B (6)
    F 134:0 info_command - B (6)
    F 217:0 main - B (6)
    F 182:0 upload_command - A (5)
tools/scripts/extract_timeline.py
    F 60:0 main - C (17)
    F 26:0 find_exported_documents - A (5)
    F 44:0 process_documents - A (3)
tools/scripts/export_documents.py
    F 26:0 export_all_documents - B (10)
    F 88:0 main - B (9)
tools/scripts/run_full_system
    M 384:4 SystemRunner.cleanup_old_data - C (12)
    M 107:4 SystemRunner.start_qdrant - B (10)
    M 340:4 SystemRunner.process_pipeline_documents - B (10)
    M 54:4 SystemRunner.check_prerequisites - B (9)
    C 28:0 SystemRunner - B (7)
    M 232:4 SystemRunner.generate_summaries - B (7)
    M 197:4 SystemRunner.generate_embeddings - B (6)
    M 512:4 SystemRunner.run - B (6)
    M 292:4 SystemRunner.populate_vector_store - A (5)
    M 433:4 SystemRunner.check_mcp_servers - A (5)
    M 465:4 SystemRunner.generate_report - A (5)
    M 169:4 SystemRunner.sync_emails - A (3)
    M 269:4 SystemRunner.test_search - A (3)
    M 499:4 SystemRunner.cleanup - A (3)
    F 568:0 main - A (1)
    M 31:4 SystemRunner.__init__ - A (1)
tools/scripts/check_qdrant_documents.py
    F 16:0 check_qdrant_documents - B (9)
tools/scripts/setup_wizard
    M 104:4 SetupWizard.setup_gmail - B (9)
    M 255:4 SetupWizard.setup_qdrant - B (7)
    M 183:4 SetupWizard.configure_senders - B (6)
    M 467:4 SetupWizard.run - A (5)
    F 526:0 main - A (4)
    C 24:0 SetupWizard - A (4)
    M 66:4 SetupWizard.check_python_version - A (3)
    M 76:4 SetupWizard.install_dependencies - A (3)
    M 336:4 SetupWizard.initialize_database - A (3)
    M 393:4 SetupWizard.run_first_sync - A (3)
    M 31:4 SetupWizard.welcome - A (2)
    M 355:4 SetupWizard.setup_mcp_servers - A (2)
    M 27:4 SetupWizard.__init__ - A (1)
    M 431:4 SetupWizard.create_shortcuts - A (1)
    M 458:4 SetupWizard.save_configuration - A (1)
tools/scripts/sync_vector_store.py
    F 134:0 main - B (10)
    F 76:0 remove_orphaned_vectors - B (6)
    F 25:0 get_orphaned_vectors - A (5)
    F 108:0 verify_synchronization - A (3)
tools/scripts/vsearch
    F 298:0 main - D (30)
    F 175:0 health_command - C (17)
    F 99:0 display_search_results - B (9)
    F 76:0 _format_filter_info - B (8)
    F 22:0 search_command - B (7)
    F 134:0 _format_score_info - B (7)
    F 157:0 _get_content_preview - A (5)
    F 222:0 info_command - A (4)
    F 268:0 upload_command - A (4)
tools/scripts/check_documents_in_vector.py
    F 15:0 check_document_vectors - C (13)
tools/scripts/process_embeddings.py
    F 19:0 process_all_embeddings - C (15)
    F 141:0 main - A (2)
tools/scripts/test_fast
    F 30:0 main - A (3)
    F 13:0 run_command - A (2)
tools/scripts/cli/timeline_handler.py
    F 14:0 show_timeline - B (8)
tools/scripts/cli/process_handler.py
    F 17:0 process_emails - A (5)
    F 49:0 embed_content - A (5)
tools/scripts/cli/cli_main.py
    F 154:0 _handle_docs - A (5)
    F 203:0 main - A (4)
    F 166:0 _handle_upload - A (3)
    F 177:0 route_command - A (2)
    F 35:0 setup_search_commands - A (1)
    F 58:0 setup_process_commands - A (1)
    F 79:0 setup_upload_commands - A (1)
    F 94:0 setup_info_commands - A (1)
    F 100:0 setup_timeline_commands - A (1)
    F 119:0 setup_notes_commands - A (1)
    F 139:0 setup_docs_commands - A (1)
tools/scripts/cli/search_handler.py
    F 17:0 search_emails - C (11)
    F 96:0 search_multi_content - B (10)
    F 196:0 display_unified_search_results - B (8)
    F 150:0 display_unified_results - A (5)
    F 233:0 display_results - A (5)
    F 167:0 _display_single_unified_result - A (4)
tools/scripts/cli/docs_handler.py
    F 72:0 show_docs_content - D (22)
    F 33:0 show_docs_overview - C (14)
    F 135:0 show_docs_summary - B (10)
    F 10:0 find_documentation_files - B (6)
    F 170:0 list_services_with_docs - B (6)
tools/scripts/cli/legal_handler.py
    F 327:0 summarize_legal_docs - C (17)
    F 190:0 search_legal - C (13)
    F 263:0 predict_missing_documents - C (12)
    F 21:0 process_legal_case - B (10)
    F 77:0 generate_legal_timeline - B (8)
    F 129:0 build_legal_graph - B (8)
tools/scripts/cli/info_handler.py
    F 166:0 show_transcription_stats - C (12)
    F 25:0 show_info - C (11)
    F 119:0 show_pdf_stats - B (8)
tools/scripts/cli/service_locator.py
    F 88:0 get_locator - A (2)
    C 20:0 ServiceLocator - A (2)
    M 30:4 ServiceLocator.__init__ - A (1)
    M 33:4 ServiceLocator.get_vector_service - A (1)
    M 40:4 ServiceLocator.get_search_service - A (1)
    M 46:4 ServiceLocator.get_gmail_service - A (1)
    M 51:4 ServiceLocator.get_pdf_service - A (1)
    M 58:4 ServiceLocator.get_entity_service - A (1)
    M 63:4 ServiceLocator.get_timeline_service - A (1)
    M 68:4 ServiceLocator.get_notes_service - A (1)
    M 73:4 ServiceLocator.get_service_health_status - A (1)
    M 78:4 ServiceLocator.is_service_healthy - A (1)
tools/scripts/cli/upload_handler.py
    F 42:0 upload_directory - A (4)
    F 88:0 process_uploads - A (4)
    F 112:0 process_pdf_uploads - A (4)
    F 20:0 upload_pdf - A (3)
    F 66:0 transcribe_file - A (3)
tools/scripts/cli/notes_handler.py
    F 48:0 show_notes_for_content - B (7)
    F 14:0 create_note - A (5)
tools/scripts/cli/intelligence_handler.py
    F 308:0 _display_duplicate_results - C (13)
    F 349:0 _display_entity_results - B (9)
    F 384:0 _display_summary_results - B (9)
    F 269:0 _display_cluster_results - B (6)
    F 24:0 smart_search_command - A (5)
    F 81:0 cluster_command - A (5)
    F 119:0 duplicates_command - A (5)
    F 150:0 entities_command - A (5)
    F 176:0 intel_summarize_command - A (5)
    F 212:0 _display_search_results - A (5)
    F 54:0 similarity_command - A (4)
    F 244:0 _display_similarity_results - A (3)
tools/codemods/replace_content_id_sql.py
    F 224:0 main - C (16)
    F 204:0 find_python_files - B (8)
    F 156:0 transform_file - B (7)
    M 105:4 SqlStringRewriter.leave_SimpleString - B (7)
    C 76:0 SqlStringRewriter - A (5)
    M 87:4 SqlStringRewriter._rewrite_sql - A (5)
    M 129:4 SqlStringRewriter.leave_FormattedString - A (5)
    M 79:4 SqlStringRewriter.__init__ - A (1)
    M 83:4 SqlStringRewriter._is_sql_string - A (1)
tools/codemods/consolidate_search.py
    F 32:0 consolidate_search - C (15)
    F 10:0 update_imports_in_file - A (3)
tools/codemods/centralize_config.py
    F 97:0 transform_file - B (8)
    F 192:0 main - A (5)
    M 19:4 ConfigCentralizationTransformer.leave_SimpleStatementLine - A (5)
    M 42:4 ConfigCentralizationTransformer._transform_assignment - A (5)
    F 142:0 find_python_files - A (4)
    C 13:0 ConfigCentralizationTransformer - A (4)
    F 168:0 move_files_to_config - A (3)
    M 81:4 ConfigCentralizationTransformer.leave_SimpleString - A (3)
    M 16:4 ConfigCentralizationTransformer.__init__ - A (1)
config/settings.py
    C 60:0 EntitySettings - A (3)
    C 14:0 DatabaseSettings - A (2)
    M 95:4 EntitySettings.validate_confidence - A (2)
    C 131:0 PathSettings - A (2)
    M 27:4 DatabaseSettings.validate_db_paths - A (1)
    C 34:0 GmailSettings - A (1)
    C 101:0 VectorSettings - A (1)
    C 119:0 APISettings - A (1)
    M 157:4 PathSettings.ensure_directories_exist - A (1)
    C 163:0 LoggingSettings - A (1)
    C 176:0 Settings - A (1)
legal_intelligence/__init__.py
    F 10:0 get_legal_intelligence_service - A (1)
legal_intelligence/main.py
    M 492:4 LegalIntelligenceService._calculate_missing_confidence - B (9)
    M 424:4 LegalIntelligenceService._determine_case_type - B (8)
    M 317:4 LegalIntelligenceService._build_case_relationships - B (6)
    M 406:4 LegalIntelligenceService._identify_document_types - B (6)
    M 607:4 LegalIntelligenceService._classify_date_type - B (6)
    M 692:4 LegalIntelligenceService._extract_themes - B (6)
    M 131:4 LegalIntelligenceService.predict_missing_documents - A (5)
    M 278:4 LegalIntelligenceService._generate_case_timeline - A (5)
    C 23:0 LegalIntelligenceService - A (4)
    M 61:4 LegalIntelligenceService.process_case - A (4)
    M 225:4 LegalIntelligenceService._get_case_documents - A (4)
    M 244:4 LegalIntelligenceService._extract_case_entities - A (4)
    M 624:4 LegalIntelligenceService._identify_timeline_gaps - A (4)
    M 664:4 LegalIntelligenceService._calculate_document_similarity - A (4)
    M 729:4 LegalIntelligenceService._detect_anomalies - A (4)
    M 753:4 LegalIntelligenceService._analyze_document_flow - A (4)
    M 778:4 LegalIntelligenceService._identify_single_doc_type - A (4)
    M 110:4 LegalIntelligenceService.analyze_document_patterns - A (3)
    M 533:4 LegalIntelligenceService._consolidate_entities - A (3)
    M 553:4 LegalIntelligenceService._group_entities_by_type - A (3)
    M 567:4 LegalIntelligenceService._identify_key_parties - A (3)
    M 650:4 LegalIntelligenceService._identify_milestones - A (3)
    M 791:4 LegalIntelligenceService._summarize_patterns - A (3)
    M 185:4 LegalIntelligenceService.generate_case_timeline - A (2)
    M 204:4 LegalIntelligenceService.build_relationship_graph - A (2)
    M 378:4 LegalIntelligenceService._analyze_document_patterns - A (2)
    M 579:4 LegalIntelligenceService._extract_dates_from_document - A (2)
    F 809:0 get_legal_intelligence_service - A (1)
    M 29:4 LegalIntelligenceService.__init__ - A (1)
    M 446:4 LegalIntelligenceService._get_expected_document_sequence - A (1)
    M 517:4 LegalIntelligenceService._get_missing_reason - A (1)
entity/config.py
    M 39:4 EntityConfig._validate_config - B (7)
    C 10:0 EntityConfig - A (3)
    M 15:4 EntityConfig.__init__ - A (1)
    M 20:4 EntityConfig._load_config - A (1)
    M 72:4 EntityConfig.get - A (1)
    M 78:4 EntityConfig.is_valid - A (1)
entity/database.py
    M 18:4 EntityDatabase._ensure_entities_table - B (7)
    M 261:4 EntityDatabase.search_consolidated_entities - A (5)
    C 12:0 EntityDatabase - A (4)
    M 127:4 EntityDatabase.store_entities - A (4)
    M 225:4 EntityDatabase.store_consolidated_entity - A (4)
    M 381:4 EntityDatabase.get_entity_statistics - A (4)
    M 203:4 EntityDatabase.count_entities - A (3)
    M 321:4 EntityDatabase.get_entity_relationships - A (3)
    M 341:4 EntityDatabase.get_knowledge_graph - A (3)
    M 178:4 EntityDatabase.get_entities_for_email - A (2)
    M 191:4 EntityDatabase.get_entities_by_type - A (2)
    M 213:4 EntityDatabase.count_entities_by_type - A (2)
    M 249:4 EntityDatabase.get_consolidated_entity - A (2)
    M 286:4 EntityDatabase.store_entity_relationship - A (2)
    M 13:4 EntityDatabase.__init__ - A (1)
    M 168:4 EntityDatabase._generate_entity_id - A (1)
entity/main.py
    M 79:4 EntityService.extract_email_entities - C (18)
    M 318:4 EntityService.extract_entities_batch - B (7)
    C 22:0 EntityService - B (6)
    M 61:4 EntityService._validate_service - A (5)
    M 222:4 EntityService.get_entity_stats - A (5)
    M 29:4 EntityService.__init__ - A (4)
    M 183:4 EntityService.process_emails - A (3)
    M 255:4 EntityService.search_entities - A (3)
    M 276:4 EntityService.get_entity_relationships - A (3)
    M 297:4 EntityService.get_knowledge_graph - A (3)
    M 210:4 EntityService.get_entities_for_email - A (2)
    F 366:0 get_entity_service - A (1)
entity/processors/entity_normalizer.py
    M 258:4 EntityNormalizer._parse_person_name - B (10)
    M 213:4 EntityNormalizer._person_similarity - B (7)
    M 62:4 EntityNormalizer.deduplicate_entities - B (6)
    M 142:4 EntityNormalizer._simple_deduplicate - A (5)
    M 311:4 EntityNormalizer._is_initial_match - A (5)
    C 13:0 EntityNormalizer - A (4)
    M 173:4 EntityNormalizer._find_best_match - A (4)
    M 340:4 EntityNormalizer._merge_entities - A (4)
    M 117:4 EntityNormalizer._deduplicate_by_type - A (3)
    M 196:4 EntityNormalizer._calculate_similarity - A (3)
    M 294:4 EntityNormalizer._normalize_organization_name - A (2)
    M 18:4 EntityNormalizer.__init__ - A (1)
    M 22:4 EntityNormalizer._initialize_patterns - A (1)
    M 243:4 EntityNormalizer._organization_similarity - A (1)
    M 322:4 EntityNormalizer._create_consolidated_entity - A (1)
    M 368:4 EntityNormalizer._generate_consolidated_id - A (1)
    M 380:4 EntityNormalizer._get_entity_key - A (1)
entity/extractors/legal_extractor.py
    M 190:4 LegalExtractor._extract_legal_roles - A (5)
    M 98:4 LegalExtractor.extract_entities - A (4)
    M 141:4 LegalExtractor._extract_case_numbers - A (4)
    C 15:0 LegalExtractor - A (3)
    M 166:4 LegalExtractor._extract_courts - A (3)
    M 229:4 LegalExtractor._extract_legal_concepts - A (3)
    M 259:4 LegalExtractor._extract_statutes - A (3)
    M 20:4 LegalExtractor.__init__ - A (1)
    M 26:4 LegalExtractor._initialize_patterns - A (1)
    M 283:4 LegalExtractor._normalize_case_number - A (1)
    M 292:4 LegalExtractor._normalize_statute - A (1)
    M 302:4 LegalExtractor.is_available - A (1)
    M 308:4 LegalExtractor.get_supported_entity_types - A (1)
    M 320:4 LegalExtractor.get_legal_role_types - A (1)
entity/extractors/extractor_factory.py
    M 91:4 ExtractorFactory.get_best_available_extractor - B (8)
    C 14:0 ExtractorFactory - A (5)
    M 53:4 ExtractorFactory.get_available_extractors - A (4)
    M 131:4 ExtractorFactory.validate_extractor_config - A (3)
    M 30:4 ExtractorFactory.create_extractor - A (2)
entity/extractors/spacy_extractor.py
    M 51:4 SpacyExtractor.extract_entities - A (5)
    M 158:4 SpacyExtractor.extract_entities_batch - A (5)
    C 13:0 SpacyExtractor - A (4)
    M 25:4 SpacyExtractor._initialize_model - A (4)
    M 101:4 SpacyExtractor._get_entity_confidence - A (4)
    M 123:4 SpacyExtractor.is_available - A (2)
    M 129:4 SpacyExtractor.get_supported_entity_types - A (2)
    M 213:4 SpacyExtractor.get_model_info - A (2)
    M 18:4 SpacyExtractor.__init__ - A (1)
entity/extractors/base_extractor.py
    M 73:4 BaseExtractor.filter_entities - A (5)
    M 52:4 BaseExtractor.validate_text - A (4)
    C 10:0 BaseExtractor - A (3)
    M 15:4 BaseExtractor.__init__ - A (1)
    M 20:4 BaseExtractor.extract_entities - A (1)
    M 41:4 BaseExtractor.is_available - A (1)
    M 47:4 BaseExtractor.get_supported_entity_types - A (1)
    M 67:4 BaseExtractor.normalize_entity - A (1)
    M 97:4 BaseExtractor.__str__ - A (1)
entity/extractors/relationship_extractor.py
    M 77:4 RelationshipExtractor.extract_relationships - B (7)
    M 129:4 RelationshipExtractor._analyze_entity_pair - B (7)
    M 187:4 RelationshipExtractor._calculate_confidence - B (6)
    M 269:4 RelationshipExtractor._find_matching_entities - B (6)
    M 230:4 RelationshipExtractor.extract_email_header_relationships - A (5)
    C 14:0 RelationshipExtractor - A (4)
    M 214:4 RelationshipExtractor._deduplicate_relationships - A (4)
    M 19:4 RelationshipExtractor.__init__ - A (1)
    M 25:4 RelationshipExtractor._initialize_patterns - A (1)
    M 290:4 RelationshipExtractor.is_available - A (1)
    M 296:4 RelationshipExtractor.get_supported_entity_types - A (1)
    M 302:4 RelationshipExtractor.get_relationship_types - A (1)
entity/extractors/combined_extractor.py
    M 62:4 CombinedExtractor.extract_entities - B (10)
    C 17:0 CombinedExtractor - B (6)
    M 42:4 CombinedExtractor._validate_extractors - B (6)
    M 131:4 CombinedExtractor._deduplicate_entities - B (6)
    M 198:4 CombinedExtractor.get_supported_entity_types - A (5)
    M 212:4 CombinedExtractor.get_extractor_info - A (5)
    M 22:4 CombinedExtractor.__init__ - A (3)
    M 158:4 CombinedExtractor._entities_overlap - A (3)
    M 192:4 CombinedExtractor.is_available - A (1)
summarization/engine.py
    M 209:4 TextRankSummarizer.extract_sentences - C (14)
    M 327:4 DocumentSummarizer.extract_summary - C (12)
    M 386:4 DocumentSummarizer.summarize_batch - B (9)
    C 315:0 DocumentSummarizer - B (8)
    M 107:4 TFIDFSummarizer.extract_keywords_batch - B (7)
    C 157:0 TextRankSummarizer - B (6)
    M 185:4 TextRankSummarizer.split_sentences - B (6)
    M 59:4 TFIDFSummarizer.extract_keywords - A (5)
    C 23:0 TFIDFSummarizer - A (4)
    M 171:4 TextRankSummarizer._get_embedding_service - A (3)
    F 440:0 get_document_summarizer - A (2)
    M 291:4 TextRankSummarizer._tfidf_similarity - A (2)
    M 28:4 TFIDFSummarizer.__init__ - A (1)
    M 39:4 TFIDFSummarizer.preprocess_text - A (1)
    M 162:4 TextRankSummarizer.__init__ - A (1)
    M 320:4 DocumentSummarizer.__init__ - A (1)
pdf/database_error_recovery.py
    M 88:4 DatabaseErrorRecovery.execute_with_retry - C (12)
    M 229:4 DatabaseErrorRecovery.restore_from_backup - B (10)
    M 517:4 DatabaseErrorRecovery._list_available_backups - B (7)
    M 481:4 DatabaseErrorRecovery._cleanup_old_backups - B (6)
    C 42:0 DatabaseErrorRecovery - A (5)
    M 179:4 DatabaseErrorRecovery.create_backup - A (5)
    M 445:4 DatabaseErrorRecovery._send_alert - A (5)
    M 321:4 DatabaseErrorRecovery.get_recovery_status - A (4)
    M 389:4 DatabaseErrorRecovery._reset_circuit_breaker - A (4)
    M 350:4 DatabaseErrorRecovery._is_circuit_open - A (3)
    M 366:4 DatabaseErrorRecovery._record_failure - A (3)
    M 507:4 DatabaseErrorRecovery._verify_database_integrity - A (3)
    M 296:4 DatabaseErrorRecovery.get_degraded_mode_response - A (2)
    M 406:4 DatabaseErrorRecovery._get_circuit_recovery_time - A (2)
    M 415:4 DatabaseErrorRecovery._handle_database_locked_error - A (2)
    M 436:4 DatabaseErrorRecovery._handle_disk_io_error - A (2)
    M 498:4 DatabaseErrorRecovery._verify_backup_integrity - A (2)
    C 20:0 AlertSeverity - A (1)
    C 30:0 DatabaseAlert - A (1)
    M 54:4 DatabaseErrorRecovery.__init__ - A (1)
    M 317:4 DatabaseErrorRecovery.add_alert_callback - A (1)
    M 426:4 DatabaseErrorRecovery._handle_missing_table_error - A (1)
pdf/pdf_processor.py
    M 32:4 PDFProcessor.extract_text_from_pdf - B (6)
    M 60:4 PDFProcessor.chunk_text - A (5)
    M 80:4 PDFProcessor._find_chunk_end - A (4)
    C 15:0 PDFProcessor - A (3)
    M 23:4 PDFProcessor.validate_dependencies - A (2)
    M 98:4 PDFProcessor._find_sentence_break - A (2)
    M 105:4 PDFProcessor._find_paragraph_break - A (2)
    M 112:4 PDFProcessor._find_word_break - A (2)
    M 18:4 PDFProcessor.__init__ - A (1)
    M 119:4 PDFProcessor._calculate_next_start - A (1)
pdf/main.py
    M 273:4 PDFService._process_pdf_internal - C (15)
    M 139:4 PDFService.upload_single_pdf - C (13)
    M 45:4 PDFService.__init__ - A (5)
    M 88:4 PDFService._get - A (5)
    C 37:0 PDFService - A (4)
    M 230:4 PDFService._prepare_pdf_files - A (4)
    M 216:4 PDFService.upload_directory - A (3)
    M 254:4 PDFService._update_results - A (3)
    M 266:4 PDFService.get_pdf_stats - A (3)
    M 244:4 PDFService._process_pdf_files - A (2)
    M 75:4 PDFService.from_db_path - A (1)
    M 104:4 PDFService.validator - A (1)
    M 108:4 PDFService.ocr - A (1)
    M 112:4 PDFService.summarizer - A (1)
    M 116:4 PDFService.pipeline - A (1)
    M 120:4 PDFService.exporter - A (1)
    M 124:4 PDFService.health_monitor - A (1)
    M 128:4 PDFService.error_recovery - A (1)
    M 132:4 PDFService.health_manager - A (1)
    M 135:4 PDFService.health_check - A (1)
    M 388:4 PDFService._handle_database_alert - A (1)
    M 394:4 PDFService.create_database_backup - A (1)
    M 398:4 PDFService.get_recovery_status - A (1)
pdf/pdf_validator.py
    M 28:4 PDFValidator.check_resource_limits - A (4)
    C 15:0 PDFValidator - A (3)
    M 18:4 PDFValidator.validate_pdf_file - A (3)
    M 56:4 PDFValidator.check_system_health - A (2)
    M 75:4 PDFValidator.get_resource_constants - A (1)
pdf/pdf_health.py
    M 48:4 PDFHealthManager._evaluate_service_health - A (5)
    C 9:0 PDFHealthManager - A (3)
    M 19:4 PDFHealthManager.perform_health_check - A (3)
    M 32:4 PDFHealthManager._gather_health_metrics - A (2)
    M 12:4 PDFHealthManager.__init__ - A (1)
    M 64:4 PDFHealthManager._build_health_response - A (1)
    M 81:4 PDFHealthManager._build_error_response - A (1)
pdf/database_health_monitor.py
    M 377:4 DatabaseHealthMonitor._determine_health_status - C (13)
    M 332:4 DatabaseHealthMonitor._analyze_recent_performance - B (10)
    M 172:4 DatabaseHealthMonitor.get_performance_report - B (7)
    M 471:4 DatabaseHealthMonitor._analyze_operations_by_type - B (7)
    C 45:0 DatabaseHealthMonitor - B (6)
    M 249:4 DatabaseHealthMonitor._get_current_metrics - B (6)
    M 131:4 DatabaseHealthMonitor.track_operation - A (4)
    M 212:4 DatabaseHealthMonitor._test_database_connection - A (3)
    M 466:4 DatabaseHealthMonitor._get_recent_metrics - A (3)
    M 79:4 DatabaseHealthMonitor.health_check - A (2)
    M 295:4 DatabaseHealthMonitor._check_disk_space - A (2)
    M 315:4 DatabaseHealthMonitor._get_disk_metrics - A (2)
    C 20:0 DatabaseMetrics - A (1)
    C 35:0 OperationMetric - A (1)
    M 57:4 DatabaseHealthMonitor.__init__ - A (1)
pdf/pdf_storage_enhanced.py
    M 57:4 EnhancedPDFStorage.store_chunks_with_metadata - C (11)
    M 21:4 EnhancedPDFStorage._get_db - A (5)
    C 14:0 EnhancedPDFStorage - A (4)
    M 148:4 EnhancedPDFStorage.get_enhanced_pdf_stats - A (4)
    M 254:4 EnhancedPDFStorage.find_pdf_files - A (4)
    M 35:4 EnhancedPDFStorage.hash_file - A (2)
    M 43:4 EnhancedPDFStorage.is_duplicate - A (2)
    M 210:4 EnhancedPDFStorage._collect_document_stats - A (2)
    M 236:4 EnhancedPDFStorage.store_chunks - A (2)
    M 17:4 EnhancedPDFStorage.__init__ - A (1)
pdf/pdf_processor_enhanced.py
    M 50:4 EnhancedPDFProcessor.extract_and_chunk_pdf - C (11)
    C 22:0 EnhancedPDFProcessor - A (4)
    M 38:4 EnhancedPDFProcessor.validate_dependencies - A (3)
    M 121:4 EnhancedPDFProcessor.extract_text_from_pdf - A (3)
    M 25:4 EnhancedPDFProcessor.__init__ - A (2)
    M 116:4 EnhancedPDFProcessor.should_use_ocr - A (1)
    M 130:4 EnhancedPDFProcessor.chunk_text - A (1)
pdf/wiring.py
    F 98:0 get_pdf_service - A (2)
    F 19:0 build_pdf_service - A (1)
    F 113:0 reset_pdf_service - A (1)
pdf/ocr/validator.py
    M 57:4 PDFValidator.is_scanned_pdf - B (8)
    M 107:4 PDFValidator.should_use_ocr - A (4)
    C 15:0 PDFValidator - A (3)
    M 36:4 PDFValidator._check_ocr_dependencies - A (2)
    M 47:4 PDFValidator._check_cv2_dependencies - A (2)
    M 18:4 PDFValidator.__init__ - A (1)
    M 21:4 PDFValidator._check_dependencies - A (1)
    M 25:4 PDFValidator.validate_dependencies - A (1)
pdf/ocr/ocr_engine.py
    M 120:4 OCREngine.extract_text_from_image - B (8)
    C 26:0 OCREngine - A (4)
    M 33:4 OCREngine.enhance_image_for_ocr - A (4)
    M 70:4 OCREngine._enhance_with_cv2 - A (3)
    M 94:4 OCREngine._get_skew_angle - A (3)
    M 176:4 OCREngine.validate_ocr_setup - A (3)
    M 107:4 OCREngine._rotate_image - A (2)
    M 29:4 OCREngine.__init__ - A (1)
pdf/ocr/postprocessor.py
    M 86:4 OCRPostprocessor.validate_ocr_quality - B (9)
    M 54:4 OCRPostprocessor.merge_page_texts - B (7)
    C 9:0 OCRPostprocessor - B (6)
    M 132:4 OCRPostprocessor.extract_metadata_hints - B (6)
    M 21:4 OCRPostprocessor.clean_ocr_text - A (3)
    M 12:4 OCRPostprocessor.__init__ - A (1)
pdf/ocr/page_processor.py
    M 32:4 PageByPageProcessor.process_large_pdf - B (9)
    C 15:0 PageByPageProcessor - B (6)
    M 128:4 PageByPageProcessor.process_with_generator - B (6)
    M 18:4 PageByPageProcessor.__init__ - A (1)
pdf/ocr/ocr_coordinator.py
    M 59:4 OCRCoordinator._extract_with_ocr - B (6)
    C 16:0 OCRCoordinator - A (4)
    M 27:4 OCRCoordinator.process_pdf_with_ocr - A (4)
    M 19:4 OCRCoordinator.__init__ - A (1)
    M 108:4 OCRCoordinator.validate_setup - A (1)
pdf/ocr/loader.py
    M 41:4 PDFLoader.validate_pdf_file - B (7)
    C 12:0 PDFLoader - A (5)
    M 23:4 PDFLoader.find_pdf_files - A (5)
    M 15:4 PDFLoader.hash_file - A (2)
    M 72:4 PDFLoader.get_pdf_info - A (2)
pdf/ocr/rasterizer.py
    C 17:0 PDFRasterizer - A (3)
    M 30:4 PDFRasterizer.convert_pdf_to_images - A (3)
    M 88:4 PDFRasterizer.validate_settings - A (3)
    M 20:4 PDFRasterizer.__init__ - A (1)
    M 63:4 PDFRasterizer.convert_single_page - A (1)
    M 67:4 PDFRasterizer.estimate_memory_usage - A (1)
shared/original_file_manager.py
    M 128:4 OriginalFileManager.organize_file - B (10)
    M 303:4 OriginalFileManager.cleanup_broken_links - A (5)
    M 341:4 OriginalFileManager.create_link_or_copy - A (5)
    C 21:0 OriginalFileManager - A (4)
    M 70:4 OriginalFileManager.create_date_directory - A (4)
    M 215:4 OriginalFileManager.create_hard_link - A (4)
    M 288:4 OriginalFileManager.verify_link - A (3)
    M 102:4 OriginalFileManager.get_file_hash - A (2)
    M 110:4 OriginalFileManager.check_duplicate - A (2)
    M 257:4 OriginalFileManager.create_soft_link - A (2)
    M 371:4 OriginalFileManager._create_email_thread_directory - A (2)
    F 394:0 get_original_file_manager - A (1)
    M 24:4 OriginalFileManager.__init__ - A (1)
    M 43:4 OriginalFileManager._ensure_hash_table - A (1)
    M 56:4 OriginalFileManager._ensure_links_table - A (1)
shared/html_cleaner.py
    F 133:0 format_as_clean_markdown - B (9)
    F 96:0 remove_email_boilerplate - B (7)
    F 10:0 clean_html_content - B (6)
    F 62:0 extract_email_content - A (4)
shared/loguru_config.py
    F 32:0 setup_logging - C (14)
    F 23:0 filter_sensitive - A (2)
    F 137:0 get_logger - A (1)
    F 142:0 setup_service_logging - A (1)
shared/date_utils.py
    F 10:0 parse_relative_date - C (17)
    F 143:0 parse_date_from_filename - B (10)
    F 82:0 parse_date_filter - A (5)
    F 120:0 get_date_range - A (5)
shared/service_interfaces.py
    C 10:0 IEmbedder - A (2)
    C 36:0 IServiceResponse - A (2)
    C 49:0 IService - A (2)
    C 63:0 OCRPort - A (2)
    C 68:0 PDFValidatorPort - A (2)
    C 73:0 HealthMonitorPort - A (2)
    C 78:0 ErrorRecoveryPort - A (2)
    C 85:0 SummarizerPort - A (2)
    C 90:0 ExporterPort - A (2)
    C 95:0 PipelinePort - A (2)
    C 102:0 PDFHealthManagerPort - A (2)
    C 5:0 FeatureUnavailable - A (1)
    M 14:4 IEmbedder.generate_embedding - A (1)
    M 25:4 IEmbedder.generate_batch_embeddings - A (1)
    M 40:4 IServiceResponse.to_dict - A (1)
    M 53:4 IService.health_check - A (1)
    M 65:4 OCRPort.process_pdf_with_ocr - A (1)
    M 70:4 PDFValidatorPort.validate_pdf_path - A (1)
    M 75:4 HealthMonitorPort.get_health_metrics - A (1)
    M 80:4 ErrorRecoveryPort.create_backup - A (1)
    M 81:4 ErrorRecoveryPort.get_recovery_status - A (1)
    M 82:4 ErrorRecoveryPort.add_alert_callback - A (1)
    M 87:4 SummarizerPort.extract_summary - A (1)
    M 92:4 ExporterPort.save_to_export - A (1)
    M 97:4 PipelinePort.add_to_raw - A (1)
    M 98:4 PipelinePort.move_to_staged - A (1)
    M 99:4 PipelinePort.move_to_processed - A (1)
    M 104:4 PDFHealthManagerPort.perform_health_check - A (1)
shared/naming_utils.py
    M 278:4 MarkdownNamingUtils.is_valid_markdown_filename - B (9)
    M 651:4 FilenameValidator._validate_windows - B (7)
    M 214:4 MarkdownNamingUtils.generate_email_thread_filename - B (6)
    C 17:0 MarkdownNamingUtils - A (5)
    M 56:4 MarkdownNamingUtils.slugify - A (5)
    M 136:4 MarkdownNamingUtils.truncate_filename - A (5)
    M 175:4 MarkdownNamingUtils.generate_document_filename - A (5)
    M 326:4 MarkdownNamingUtils.generate_unique_filename - A (5)
    M 440:4 MarkdownNamingUtils.find_similar_filenames - A (5)
    M 474:4 MarkdownNamingUtils._calculate_similarity - A (5)
    M 621:4 FilenameValidator.validate_filename - A (5)
    M 101:4 MarkdownNamingUtils.sanitize_filename - A (4)
    M 398:4 MarkdownNamingUtils.resolve_thread_collision - A (4)
    C 577:0 FilenameValidator - A (4)
    M 684:4 FilenameValidator._validate_macos - A (4)
    M 716:4 FilenameValidator.validate_path_length - A (4)
    M 745:4 FilenameValidator.validate_characters - A (4)
    M 256:4 MarkdownNamingUtils.extract_date_from_filename - A (3)
    M 360:4 MarkdownNamingUtils._resolve_with_counter - A (3)
    C 504:0 CollisionResolver - A (3)
    M 552:4 CollisionResolver.suggest_resolution_strategies - A (3)
    M 702:4 FilenameValidator._validate_linux - A (3)
    M 375:4 MarkdownNamingUtils._resolve_with_timestamp - A (2)
    M 507:4 CollisionResolver.__init__ - A (2)
    M 512:4 CollisionResolver.resolve_collision - A (2)
    M 533:4 CollisionResolver.check_potential_duplicates - A (2)
    M 781:4 FilenameValidator.suggest_fixes - A (2)
    F 809:0 slugify_text - A (1)
    F 814:0 sanitize_filename - A (1)
    F 819:0 generate_document_name - A (1)
    F 824:0 generate_email_name - A (1)
    F 829:0 resolve_collision - A (1)
    F 834:0 check_for_duplicates - A (1)
    F 839:0 validate_filename - A (1)
    F 844:0 suggest_filename_fixes - A (1)
    M 52:4 MarkdownNamingUtils.__init__ - A (1)
    M 314:4 MarkdownNamingUtils.check_collision - A (1)
    M 388:4 MarkdownNamingUtils._resolve_with_hash - A (1)
    M 617:4 FilenameValidator.__init__ - A (1)
shared/retry_helper.py
    F 12:0 retry_on_failure - A (1)
    F 68:0 retry_database - A (1)
    F 77:0 retry_network - A (1)
shared/simple_db.py
    M 441:4 SimpleDB.search_content - C (16)
    M 548:4 SimpleDB.batch_insert - C (15)
    M 340:4 SimpleDB.update_content - B (10)
    M 214:4 SimpleDB.add_content - B (9)
    M 513:4 SimpleDB.get_content_stats - B (9)
    M 692:4 SimpleDB.batch_add_content - B (9)
    M 1220:4 SimpleDB.get_relationship_cache - B (8)
    M 1570:4 SimpleDB.validate_pipeline_directories - B (8)
    M 1601:4 SimpleDB.get_pipeline_stats - B (8)
    M 179:4 SimpleDB.fetch - B (7)
    M 880:4 SimpleDB.create_intelligence_tables - B (7)
    M 1147:4 SimpleDB.get_document_summary - B (7)
    M 148:4 SimpleDB.execute - B (6)
    M 1067:4 SimpleDB.get_document_summaries - B (6)
    M 1628:4 SimpleDB.db_maintenance - B (6)
    C 44:0 SimpleDB - A (5)
    M 106:4 SimpleDB._ensure_data_directories - A (5)
    M 787:4 SimpleDB.batch_add_document_chunk - A (5)
    M 1116:4 SimpleDB.get_document_intelligence - A (5)
    M 1524:4 SimpleDB.get_cache_statistics - A (5)
    M 1688:4 SimpleDB.batch_add_summaries - A (5)
    M 72:4 SimpleDB._configure_connection - A (4)
    M 999:4 SimpleDB.migrate_schema - A (4)
    M 1017:4 SimpleDB.get_schema_version - A (4)
    M 1175:4 SimpleDB.get_intelligence_by_id - A (4)
    C 27:0 DBMetrics - A (3)
    M 274:4 SimpleDB.upsert_content - A (3)
    M 1043:4 SimpleDB.add_document_summary - A (3)
    M 1191:4 SimpleDB.add_relationship_cache - A (3)
    M 1359:4 SimpleDB.get_cached_similarity - A (3)
    M 1477:4 SimpleDB.get_cached_search_results - A (3)
    M 35:4 DBMetrics.report - A (2)
    M 63:4 SimpleDB._initialize_pragmas - A (2)
    M 132:4 SimpleDB.durable_txn - A (2)
    M 208:4 SimpleDB.fetch_one - A (2)
    M 919:4 SimpleDB._create_inline_intelligence_schema - A (2)
    M 1301:4 SimpleDB.get_cached_result - A (2)
    M 1320:4 SimpleDB.cache_document_similarity - A (2)
    M 1416:4 SimpleDB.get_cached_entities - A (2)
    M 1435:4 SimpleDB.cache_search_results - A (2)
    M 29:4 DBMetrics.__init__ - A (1)
    M 47:4 SimpleDB.__init__ - A (1)
    M 374:4 SimpleDB.delete_content - A (1)
    M 380:4 SimpleDB.add_thread_tracking - A (1)
    M 392:4 SimpleDB.get_thread_status - A (1)
    M 399:4 SimpleDB.list_processed_threads - A (1)
    M 406:4 SimpleDB.add_document_chunk - A (1)
    M 437:4 SimpleDB.get_content - A (1)
    M 1036:4 SimpleDB._set_schema_version - A (1)
    M 1094:4 SimpleDB.add_document_intelligence - A (1)
    M 1167:4 SimpleDB.get_summaries_for_document - A (1)
    M 1171:4 SimpleDB.get_intelligence_for_document - A (1)
    M 1261:4 SimpleDB.clean_expired_cache - A (1)
    M 1272:4 SimpleDB.cache_computation_result - A (1)
    M 1381:4 SimpleDB.cache_entity_extraction - A (1)
    M 1505:4 SimpleDB.invalidate_cache_for_content - A (1)
shared/snippet_utils.py
    F 10:0 extract_snippet - C (11)
    F 63:0 highlight_keywords - B (7)
    F 123:0 _calculate_snippet_score - B (7)
    F 181:0 format_search_result - B (6)
    F 98:0 rank_snippets - A (5)
    F 158:0 get_cached_snippet - A (4)
    F 150:0 _cached_snippet_extraction - A (1)
shared/health_check.py
    M 21:4 HealthCheck.check_database - B (6)
    M 126:4 HealthCheck.check_all - B (6)
    C 15:0 HealthCheck - A (5)
    M 96:4 HealthCheck.check_models - A (4)
    M 50:4 HealthCheck.check_qdrant - A (3)
    M 75:4 HealthCheck.check_gmail - A (3)
    F 155:0 run_health_check - A (1)
    M 18:4 HealthCheck.__init__ - A (1)
shared/error_handler.py
    M 91:4 ErrorHandler.get_recovery_suggestion - C (12)
    C 9:0 ErrorHandler - B (9)
    M 53:4 ErrorHandler.format_user_message - B (9)
    M 19:4 ErrorHandler.handle - A (3)
shared/file_operations.py
    C 12:0 FileOperations - A (3)
    M 57:4 FileOperations.delete_file - A (3)
    M 94:4 FileOperations.sanitize_path - A (3)
    M 128:4 FileOperations.get_file_size - A (3)
    M 15:4 FileOperations.move_file - A (2)
    M 36:4 FileOperations.copy_file - A (2)
    M 76:4 FileOperations.create_directory - A (2)
    M 120:4 FileOperations.file_exists - A (2)
    M 124:4 FileOperations.directory_exists - A (2)
shared/archive/cli/dedup_handler.py
    F 181:0 deduplicate_database_command - D (22)
    F 18:0 find_duplicates_command - C (18)
    F 108:0 compare_documents_command - B (9)
    F 300:0 build_duplicate_index_command - A (5)
search_intelligence/basic_search.py
    F 192:0 _merge_results_rrf - B (10)
    F 162:0 _enrich_vector_results - B (6)
    F 144:0 _build_vector_filters - A (5)
    F 17:0 search - A (4)
    F 66:0 semantic_search - A (3)
    F 125:0 _keyword_search - A (3)
    F 109:0 vector_store_available - A (2)
search_intelligence/similarity.py
    M 233:4 DocumentClusterer.find_content_clusters - B (7)
    M 105:4 DocumentSimilarityAnalyzer._get_document_vector - B (6)
    C 169:0 DocumentClusterer - B (6)
    M 178:4 DocumentClusterer.cluster_documents - B (6)
    M 287:4 DocumentClusterer.store_cluster_relationships - B (6)
    C 23:0 DocumentSimilarityAnalyzer - A (5)
    M 34:4 DocumentSimilarityAnalyzer.find_similar_documents - A (5)
    F 318:0 cluster_similar_content - A (4)
    M 77:4 DocumentSimilarityAnalyzer.compute_pairwise_similarity - A (4)
    M 137:4 DocumentSimilarityAnalyzer._get_document_content - A (4)
    M 159:4 DocumentSimilarityAnalyzer._extract_text - A (4)
    M 172:4 DocumentClusterer.__init__ - A (2)
    M 26:4 DocumentSimilarityAnalyzer.__init__ - A (1)
search_intelligence/__init__.py
    F 13:0 get_search_intelligence_service - A (2)
search_intelligence/duplicate_detector.py
    M 301:4 DuplicateDetector._group_similar_documents - C (12)
    M 219:4 DuplicateDetector._detect_semantic_duplicates - C (11)
    M 358:4 DuplicateDetector.remove_duplicates - C (11)
    C 23:0 DuplicateDetector - B (7)
    M 268:4 DuplicateDetector._get_document_embedding - B (7)
    M 37:4 DuplicateDetector.detect_duplicates - B (6)
    M 106:4 DuplicateDetector._get_documents_to_check - B (6)
    M 165:4 DuplicateDetector._detect_exact_duplicates - A (5)
    M 190:4 DuplicateDetector._compute_document_hash - A (5)
    M 142:4 DuplicateDetector._get_document - A (3)
    M 429:4 DuplicateDetector.find_duplicate_emails - A (3)
    F 460:0 detect_all_duplicates - A (1)
    M 26:4 DuplicateDetector.__init__ - A (1)
search_intelligence/main.py
    M 474:4 SearchIntelligenceService.detect_duplicates - C (18)
    M 410:4 SearchIntelligenceService.cluster_similar_content - B (10)
    M 241:4 SearchIntelligenceService.analyze_document_similarity - B (8)
    M 365:4 SearchIntelligenceService.auto_summarize_document - B (8)
    C 27:0 SearchIntelligenceService - B (6)
    M 295:4 SearchIntelligenceService.extract_and_cache_entities - B (6)
    M 124:4 SearchIntelligenceService.smart_search_with_preprocessing - A (5)
    M 183:4 SearchIntelligenceService._enhance_search_results - A (5)
    M 325:4 SearchIntelligenceService._get_cached_entities - A (4)
    M 30:4 SearchIntelligenceService.__init__ - A (3)
    M 171:4 SearchIntelligenceService._expand_query - A (3)
    M 203:4 SearchIntelligenceService._calculate_recency_score - A (3)
    M 222:4 SearchIntelligenceService._rerank_results - A (3)
    M 86:4 SearchIntelligenceService.unified_search - A (2)
    M 115:4 SearchIntelligenceService._preprocess_and_expand_query - A (2)
    M 156:4 SearchIntelligenceService._preprocess_query - A (2)
    M 348:4 SearchIntelligenceService._cache_entities - A (2)
utilities/archive_manager.py
    M 165:4 ArchiveManager.list_archives - C (12)
    M 82:4 ArchiveManager.archive_batch - B (7)
    C 17:0 ArchiveManager - B (6)
    M 130:4 ArchiveManager.retrieve_archived - A (5)
    M 225:4 ArchiveManager.cleanup_old_archives - A (5)
    M 301:4 ArchiveManager._generate_archive_name - A (5)
    M 252:4 ArchiveManager.promote_to_yearly - A (4)
    M 33:4 ArchiveManager.archive_file - A (3)
    M 280:4 ArchiveManager.get_archive_stats - A (3)
    F 324:0 get_archive_manager - A (1)
    M 20:4 ArchiveManager.__init__ - A (1)
utilities/enhanced_archive_manager.py
    M 321:4 EnhancedArchiveManager._get_link_stats - B (7)
    M 126:4 EnhancedArchiveManager.organize_by_date - A (5)
    M 221:4 EnhancedArchiveManager._calculate_space_savings - A (5)
    M 290:4 EnhancedArchiveManager._get_space_savings_stats - A (5)
    C 19:0 EnhancedArchiveManager - A (4)
    M 62:4 EnhancedArchiveManager.archive_file - A (4)
    M 259:4 EnhancedArchiveManager._update_space_savings_record - A (3)
    M 210:4 EnhancedArchiveManager.cleanup_orphaned_links - A (2)
    M 354:4 EnhancedArchiveManager._update_space_savings_after_cleanup - A (2)
    F 364:0 get_enhanced_archive_manager - A (1)
    M 30:4 EnhancedArchiveManager.__init__ - A (1)
    M 47:4 EnhancedArchiveManager._ensure_space_savings_table - A (1)
    M 179:4 EnhancedArchiveManager.check_duplicate - A (1)
    M 191:4 EnhancedArchiveManager.get_archive_stats - A (1)
utilities/embeddings/embedding_service.py
    M 80:4 EmbeddingService.batch_encode - B (6)
    C 13:0 EmbeddingService - A (3)
    M 30:4 EmbeddingService._get_device - A (3)
    M 58:4 EmbeddingService.encode - A (3)
    F 128:0 get_embedding_service - A (2)
    M 41:4 EmbeddingService._load_model - A (2)
    M 19:4 EmbeddingService.__init__ - A (1)
    M 105:4 EmbeddingService.get_dimensions - A (1)
    M 111:4 EmbeddingService.get_embedding - A (1)
    M 117:4 EmbeddingService.get_embeddings - A (1)
utilities/deduplication/near_duplicate_detector.py
    M 288:4 NearDuplicateDetector.batch_deduplicate - B (9)
    M 71:4 MinHasher.compute_signature - B (6)
    M 155:4 LSHIndex.find_similar - B (6)
    M 260:4 NearDuplicateDetector.find_all_duplicates - A (5)
    C 116:0 LSHIndex - A (4)
    C 196:0 NearDuplicateDetector - A (4)
    F 366:0 get_duplicate_detector - A (3)
    C 14:0 MinHasher - A (3)
    M 215:4 NearDuplicateDetector.add_document - A (3)
    F 374:0 test_duplicate_detection - A (2)
    M 32:4 MinHasher._generate_permutations - A (2)
    M 45:4 MinHasher._shingle_text - A (2)
    M 100:4 MinHasher.jaccard_similarity - A (2)
    M 132:4 LSHIndex.add - A (2)
    M 233:4 NearDuplicateDetector.check_duplicate - A (2)
    M 17:4 MinHasher.__init__ - A (1)
    M 119:4 LSHIndex.__init__ - A (1)
    M 199:4 NearDuplicateDetector.__init__ - A (1)
    M 348:4 NearDuplicateDetector.get_similarity - A (1)
utilities/vector_store/__init__.py
    M 68:4 VectorStore.batch_upsert - B (6)
    M 86:4 VectorStore.search - A (4)
    M 100:4 VectorStore._build_filter - A (4)
    F 161:0 get_vector_store - A (3)
    C 23:0 VectorStore - A (3)
    M 57:4 VectorStore.upsert - A (3)
    M 113:4 VectorStore.get - A (3)
    M 35:4 VectorStore._connect - A (2)
    M 45:4 VectorStore._ensure_collection - A (2)
    M 26:4 VectorStore.__init__ - A (1)
    M 125:4 VectorStore.delete - A (1)
    M 129:4 VectorStore.delete_many - A (1)
    M 133:4 VectorStore.count - A (1)
    M 138:4 VectorStore.clear - A (1)
    M 143:4 VectorStore.get_collection_stats - A (1)
utilities/notes/main.py
    M 143:4 NotesService.search_notes - B (9)
    C 15:0 NotesService - A (5)
    M 116:4 NotesService.get_notes_for_content - A (5)
    M 24:4 NotesService._ensure_notes_tables - A (3)
    M 68:4 NotesService.create_note - A (3)
    M 95:4 NotesService.link_note_to_content - A (2)
    M 18:4 NotesService.__init__ - A (1)
utilities/maintenance/update_simpledb_schema_refs.py
    F 75:0 update_table_creation - C (15)
    F 220:0 main - B (8)
    F 13:0 update_simpledb_references - B (6)
    F 123:0 add_upsert_method - A (5)
utilities/maintenance/verify_vector_sync.py
    F 10:0 verify_sync - B (8)
utilities/maintenance/migrate_emails_to_content.py
    F 17:0 migrate_emails_to_content - C (15)
    F 147:0 verify_migration - A (4)
    F 193:0 main - A (4)
utilities/maintenance/reconcile_qdrant_vectors.py
    M 203:4 QdrantReconciliation._migrate_vector_ids - C (12)
    M 282:4 QdrantReconciliation._create_missing_vectors - C (11)
    F 382:0 main - B (7)
    C 32:0 QdrantReconciliation - B (6)
    M 49:4 QdrantReconciliation.run_reconciliation - B (6)
    M 336:4 QdrantReconciliation._verify_reconciliation - B (6)
    M 120:4 QdrantReconciliation._analyze_current_state - A (4)
    M 182:4 QdrantReconciliation._remove_orphaned_vectors - A (4)
    M 89:4 QdrantReconciliation._export_audit_log - A (3)
    M 108:4 QdrantReconciliation._log_action - A (3)
    M 35:4 QdrantReconciliation.__init__ - A (1)
utilities/maintenance/fix_content_schema.py
    M 173:4 ContentSchemaMigration._phase2_fix_foreign_keys - C (12)
    M 433:4 ContentSchemaMigration._dry_run_analysis - C (12)
    M 85:4 ContentSchemaMigration._phase1_schema_evolution - B (10)
    C 23:0 ContentSchemaMigration - B (8)
    M 259:4 ContentSchemaMigration._phase3_migrate_emails - B (8)
    M 41:4 ContentSchemaMigration.run_migration - B (6)
    M 330:4 ContentSchemaMigration._phase4_reconcile_qdrant - A (5)
    M 367:4 ContentSchemaMigration._phase5_verify_migration - A (5)
    F 488:0 main - A (2)
    M 26:4 ContentSchemaMigration.__init__ - A (1)
utilities/maintenance/sync_emails_to_qdrant.py
    F 12:0 main - B (8)
utilities/maintenance/sync_missing_vectors.py
    F 30:0 list_qdrant_ids - B (8)
    F 58:0 sync_missing_vectors - B (8)
    F 19:0 string_to_uuid - A (1)
    F 25:0 encode_point_id - A (1)
    F 149:0 main - A (1)
utilities/timeline/database.py
    M 65:4 TimelineDatabase.get_timeline_events - B (9)
    M 137:4 TimelineDatabase.get_related_events - B (6)
    C 13:0 TimelineDatabase - A (5)
    M 19:4 TimelineDatabase.create_timeline_event - A (4)
    M 112:4 TimelineDatabase.create_event_relationship - A (3)
    M 16:4 TimelineDatabase.__init__ - A (1)
utilities/timeline/main.py
    M 66:4 TimelineService.sync_emails_to_timeline - B (6)
    M 102:4 TimelineService.sync_documents_to_timeline - A (5)
    M 137:4 TimelineService.get_timeline_view - A (5)
    C 13:0 TimelineService - A (4)
    M 22:4 TimelineService._ensure_timeline_tables - A (3)
    M 175:4 TimelineService._create_timeline_event - A (2)
    F 207:0 get_timeline_service - A (1)
    M 16:4 TimelineService.__init__ - A (1)
utilities/entities/main.py
    F 112:0 extract_and_cache_entities - B (7)
    F 77:0 get_cached_entities - A (4)
    F 24:0 extract_entities - A (3)
    F 53:0 cache_entities - A (2)
infrastructure/pipelines/data_pipeline.py
    M 108:4 DataPipelineOrchestrator._move_between_stages - B (6)
    M 41:4 DataPipelineOrchestrator.add_to_raw - A (5)
    M 135:4 DataPipelineOrchestrator.get_stage_files - A (5)
    M 143:4 DataPipelineOrchestrator.get_pipeline_stats - A (5)
    C 21:0 DataPipelineOrchestrator - A (4)
    M 154:4 DataPipelineOrchestrator.cleanup_export - A (4)
    M 72:4 DataPipelineOrchestrator.move_to_processed - A (3)
    M 36:4 DataPipelineOrchestrator._validate_directories - A (2)
    M 84:4 DataPipelineOrchestrator.move_to_quarantine - A (2)
    M 24:4 DataPipelineOrchestrator.__init__ - A (1)
    M 68:4 DataPipelineOrchestrator.move_to_staged - A (1)
    M 104:4 DataPipelineOrchestrator.prepare_for_export - A (1)
infrastructure/pipelines/timeline_extractor.py
    M 181:4 TimelineExtractor._calculate_confidence - C (13)
    M 346:4 TimelineExtractor.generate_markdown_timeline - C (12)
    M 254:4 TimelineExtractor.generate_timeline_summary - C (11)
    M 217:4 TimelineExtractor._deduplicate_events - B (9)
    C 19:0 TimelineExtractor - B (6)
    M 164:4 TimelineExtractor._classify_event_type - B (6)
    M 492:4 TimelineExtractor.store_events_in_database - B (6)
    M 145:4 TimelineExtractor._parse_date - A (5)
    M 64:4 TimelineExtractor.extract_dates_from_text - A (4)
    M 118:4 TimelineExtractor.extract_dates_from_file - A (4)
    M 320:4 TimelineExtractor.group_events_by_date - A (4)
    M 302:4 TimelineExtractor.filter_events_by_confidence - A (3)
    M 474:4 TimelineExtractor._clean_context_for_display - A (3)
    M 30:4 TimelineExtractor.__init__ - A (2)
    M 557:4 TimelineExtractor._get_importance_score - A (2)
    M 250:4 TimelineExtractor._confidence_score - A (1)
    M 469:4 TimelineExtractor._get_confidence_badge - A (1)
infrastructure/pipelines/document_exporter.py
    M 54:4 DocumentExporter.format_as_markdown - D (22)
    C 21:0 DocumentExporter - B (6)
    M 148:4 DocumentExporter.save_to_export - A (5)
    M 32:4 DocumentExporter.get_next_counter - A (3)
    M 183:4 DocumentExporter._update_manifest - A (2)
    M 24:4 DocumentExporter.__init__ - A (1)
    M 136:4 DocumentExporter.generate_filename - A (1)
infrastructure/pipelines/__init__.py
    F 15:0 get_pipeline_orchestrator - A (2)
    F 35:0 reset_pipeline_orchestrator - A (1)
infrastructure/pipelines/intelligence.py
    M 91:4 DocumentIntelligence.extract_entities - C (13)
    M 149:4 DocumentIntelligence.build_relationships - B (9)
    M 215:4 DocumentIntelligence.extract_all - B (9)
    C 14:0 DocumentIntelligence - A (5)
    M 28:4 DocumentIntelligence.summarizer - A (3)
    M 57:4 DocumentIntelligence.extract_summary - A (3)
    M 40:4 DocumentIntelligence.entity_extractor - A (2)
    M 49:4 DocumentIntelligence.db - A (2)
    M 17:4 DocumentIntelligence.__init__ - A (1)
    M 23:4 DocumentIntelligence.set_entity_extractor - A (1)
infrastructure/pipelines/orchestrator.py
    M 423:4 PipelineOrchestrator.export_document - B (10)
    M 51:4 PipelineOrchestrator.move_to_stage - B (6)
    M 243:4 PipelineOrchestrator.process_raw_document - A (5)
    C 19:0 PipelineOrchestrator - A (4)
    M 345:4 PipelineOrchestrator.process_staged_document - A (4)
    M 479:4 PipelineOrchestrator.save_document_to_stage - A (4)
    M 122:4 PipelineOrchestrator.update_metadata - A (3)
    M 159:4 PipelineOrchestrator.get_metadata - A (3)
    M 181:4 PipelineOrchestrator.list_documents - A (3)
    M 34:4 PipelineOrchestrator._validate_and_create_folders - A (2)
    M 90:4 PipelineOrchestrator.create_metadata - A (2)
    M 203:4 PipelineOrchestrator.quarantine_document - A (2)
    M 230:4 PipelineOrchestrator.get_stage_stats - A (2)
    M 303:4 PipelineOrchestrator.stage_document - A (2)
    M 24:4 PipelineOrchestrator.__init__ - A (1)
    M 41:4 PipelineOrchestrator.generate_pipeline_id - A (1)
infrastructure/pipelines/formats.py
    C 18:0 MarkdownFormatter - A (5)
    M 60:4 MarkdownFormatter.parse - A (4)
    C 91:0 JSONCompanionFormatter - A (4)
    M 22:4 MarkdownFormatter.format - A (3)
    M 95:4 JSONCompanionFormatter.format - A (3)
    C 143:0 UnifiedDocumentFormatter - A (3)
    M 151:4 UnifiedDocumentFormatter.format_document - A (3)
    M 192:4 UnifiedDocumentFormatter.save_formatted_document - A (3)
    M 127:4 JSONCompanionFormatter.parse - A (2)
    F 231:0 get_document_formatter - A (1)
    M 146:4 UnifiedDocumentFormatter.__init__ - A (1)
infrastructure/pipelines/processors.py
    C 59:0 EmailProcessor - B (8)
    M 62:4 EmailProcessor.process - B (7)
    M 115:4 EmailProcessor.validate - B (6)
    C 138:0 PDFProcessor - A (4)
    M 141:4 PDFProcessor.process - A (4)
    M 175:4 PDFProcessor.validate - A (4)
    C 226:0 TranscriptionProcessor - A (3)
    M 229:4 TranscriptionProcessor.process - A (3)
    M 260:4 TranscriptionProcessor.validate - A (3)
    F 300:0 get_processor - A (2)
    C 15:0 DocumentProcessor - A (2)
    M 19:4 DocumentProcessor.process - A (1)
    M 31:4 DocumentProcessor.validate - A (1)
    M 42:4 DocumentProcessor.extract_metadata - A (1)
    M 198:4 PDFProcessor._clean_pdf_artifacts - A (1)
    M 279:4 TranscriptionProcessor._format_timestamps - A (1)
infrastructure/mcp_servers/legal_intelligence_mcp.py
    F 541:0 legal_relationship_discovery - E (34)
    F 106:0 legal_timeline_events - D (30)
    F 297:0 legal_document_analysis - D (23)
    F 416:0 legal_case_tracking - D (21)
    F 208:0 legal_knowledge_graph - C (19)
    F 42:0 legal_extract_entities - C (15)
    C 690:0 LegalIntelligenceServer - A (2)
    F 35:0 set_service_factories - A (1)
    F 876:0 main - A (1)
    M 693:4 LegalIntelligenceServer.__init__ - A (1)
    M 697:4 LegalIntelligenceServer.setup_tools - A (1)
infrastructure/mcp_servers/search_intelligence_mcp.py
    F 149:0 search_entities - C (17)
    F 361:0 search_process_all - C (17)
    F 298:0 search_cluster - C (15)
    F 44:0 search_smart - C (12)
    F 230:0 search_summarize - B (10)
    F 102:0 search_similar - B (8)
    C 443:0 SearchIntelligenceMCPServer - A (2)
    F 36:0 set_service_factories - A (1)
    F 667:0 main - A (1)
    M 446:4 SearchIntelligenceMCPServer.__init__ - A (1)
    M 450:4 SearchIntelligenceMCPServer.setup_tools - A (1)
infrastructure/documents/document_converter.py
    M 258:4 DocumentConverter.convert_directory - B (10)
    M 222:4 DocumentConverter._clean_text_for_markdown - B (8)
    M 49:4 DocumentConverter.convert_pdf_to_markdown - B (7)
    M 114:4 DocumentConverter._extract_text_from_pdf - B (7)
    C 31:0 DocumentConverter - B (6)
    M 155:4 DocumentConverter._generate_metadata - A (4)
    M 34:4 DocumentConverter.__init__ - A (3)
    M 195:4 DocumentConverter._calculate_file_hash - A (3)
    M 207:4 DocumentConverter._format_as_markdown - A (3)
    M 327:4 DocumentConverter.validate_setup - A (3)
    F 358:0 get_document_converter - A (2)
    F 20:0 set_pdf_service_factories - A (1)
infrastructure/documents/lifecycle_manager.py
    M 131:4 DocumentLifecycleManager.get_folder_stats - B (6)
    M 55:4 DocumentLifecycleManager.move_to_processed - A (5)
    M 107:4 DocumentLifecycleManager._move_file - A (5)
    M 149:4 DocumentLifecycleManager.list_files - A (5)
    C 24:0 DocumentLifecycleManager - A (4)
    M 27:4 DocumentLifecycleManager.__init__ - A (3)
    M 157:4 DocumentLifecycleManager.get_file_path - A (3)
    M 45:4 DocumentLifecycleManager._ensure_folders_exist - A (2)
    M 51:4 DocumentLifecycleManager.move_to_staged - A (1)
    M 92:4 DocumentLifecycleManager.move_to_export - A (1)
    M 96:4 DocumentLifecycleManager.quarantine_file - A (1)
infrastructure/documents/format_detector.py
    M 99:4 FormatDetector._is_text_file - B (6)
    M 43:4 FormatDetector.detect_format - A (5)
    M 77:4 FormatDetector._detect_by_content - A (4)
    C 14:0 FormatDetector - A (3)
    M 94:4 FormatDetector._detect_by_extension - A (1)
    M 126:4 FormatDetector.is_supported_format - A (1)
    M 139:4 FormatDetector.get_supported_extensions - A (1)
    M 143:4 FormatDetector.get_format_info - A (1)
infrastructure/documents/document_pipeline.py
    M 77:4 DocumentPipeline.process_document - C (11)
    M 248:4 DocumentPipeline.process_directory - B (8)
    C 40:0 DocumentPipeline - B (6)
    M 177:4 DocumentPipeline._save_processed_content - A (5)
    M 43:4 DocumentPipeline.__init__ - A (3)
    M 215:4 DocumentPipeline._store_in_database - A (2)
    M 298:4 DocumentPipeline.get_pipeline_stats - A (1)
infrastructure/documents/naming_convention.py
    M 144:4 NamingConvention.extract_metadata_from_name - B (9)
    M 184:4 NamingConvention.validate_name - B (6)
    C 12:0 NamingConvention - A (3)
    M 20:4 NamingConvention._load_counter - A (3)
    M 39:4 NamingConvention.staged_name - A (3)
    M 85:4 NamingConvention.export_name - A (3)
    M 15:4 NamingConvention.__init__ - A (1)
    M 29:4 NamingConvention._save_counter - A (1)
    M 35:4 NamingConvention.raw_name - A (1)
    M 68:4 NamingConvention.processed_name - A (1)
    M 107:4 NamingConvention.quarantine_name - A (1)
    M 123:4 NamingConvention._clean_string - A (1)
infrastructure/documents/processors/email_thread_processor.py
    M 300:4 EmailThreadProcessor._format_thread_to_markdown - C (14)
    M 138:4 EmailThreadProcessor._generate_thread_metadata - B (8)
    M 355:4 EmailThreadProcessor._format_message_as_markdown - B (8)
    M 449:4 EmailThreadProcessor.process_threads_by_query - B (8)
    C 25:0 EmailThreadProcessor - B (6)
    M 88:4 EmailThreadProcessor._fetch_thread_messages - B (6)
    M 398:4 EmailThreadProcessor._generate_filename - B (6)
    M 43:4 EmailThreadProcessor.process_thread - A (5)
    M 239:4 EmailThreadProcessor._process_large_thread - A (4)
    M 433:4 EmailThreadProcessor._create_slug - A (4)
    M 197:4 EmailThreadProcessor._extract_email_address - A (3)
    M 210:4 EmailThreadProcessor._process_single_thread - A (3)
    M 516:4 EmailThreadProcessor.validate_setup - A (3)
    F 549:0 get_email_thread_processor - A (2)
    M 28:4 EmailThreadProcessor.__init__ - A (2)
    M 121:4 EmailThreadProcessor._sort_chronologically - A (2)
    M 290:4 EmailThreadProcessor._split_messages - A (2)
infrastructure/documents/processors/text_processor.py
    M 127:4 TextProcessor.extract_metadata - C (12)
    C 16:0 TextProcessor - B (6)
    M 171:4 TextProcessor.validate_content - B (6)
    M 25:4 TextProcessor.extract_text - A (5)
    M 93:4 TextProcessor._normalize_text - A (5)
    M 66:4 TextProcessor._detect_encoding - A (4)
    M 19:4 TextProcessor.__init__ - A (1)
infrastructure/documents/processors/base_processor.py
    M 112:4 BaseProcessor.validate_content - B (6)
    M 91:4 BaseProcessor.calculate_metrics - A (4)
    C 14:0 BaseProcessor - A (3)
    M 21:4 BaseProcessor.process - A (3)
    M 17:4 BaseProcessor.__init__ - A (1)
    M 58:4 BaseProcessor.extract_text - A (1)
    M 71:4 BaseProcessor.extract_metadata - A (1)
infrastructure/documents/processors/markdown_processor.py
    M 77:4 MarkdownProcessor.extract_metadata - B (7)
    C 17:0 MarkdownProcessor - A (3)
    M 51:4 MarkdownProcessor._parse_frontmatter - A (3)
    M 113:4 MarkdownProcessor._analyze_structure - A (3)
    M 224:4 MarkdownProcessor.extract_headings - A (3)
    M 25:4 MarkdownProcessor.extract_text - A (2)
    M 20:4 MarkdownProcessor.__init__ - A (1)
    M 164:4 MarkdownProcessor.process_to_plain_text - A (1)
    M 210:4 MarkdownProcessor.extract_links - A (1)
infrastructure/documents/processors/docx_processor.py
    M 149:4 DocxProcessor.extract_metadata - C (12)
    M 200:4 DocxProcessor._get_document_stats - C (11)
    M 117:4 DocxProcessor._extract_headers_footers - B (9)
    C 23:0 DocxProcessor - B (8)
    M 35:4 DocxProcessor.extract_text - B (8)
    M 87:4 DocxProcessor._extract_tables - B (6)
    M 244:4 DocxProcessor.extract_comments - A (4)
    M 273:4 DocxProcessor.validate_content - A (4)
    M 26:4 DocxProcessor.__init__ - A (2)
gmail/config.py
    C 1:0 GmailConfig - A (3)
    M 20:4 GmailConfig.build_query - A (2)
    M 4:4 GmailConfig.__init__ - A (1)
gmail/gmail_api.py
    M 235:4 GmailAPI.get_history - C (11)
    M 112:4 GmailAPI.parse_message - B (9)
    M 144:4 GmailAPI._extract_content_from_part - B (7)
    M 160:4 GmailAPI._extract_from_parts - B (7)
    M 305:4 GmailAPI.extract_message_ids_from_history - B (6)
    C 16:0 GmailAPI - A (5)
    M 54:4 GmailAPI.get_messages - A (5)
    M 85:4 GmailAPI.get_message_detail - A (5)
    M 181:4 GmailAPI._extract_content - A (4)
    M 211:4 GmailAPI.get_profile - A (4)
    M 330:4 GmailAPI.get_attachments - A (4)
    M 29:4 GmailAPI.connect - A (2)
    M 196:4 GmailAPI._parse_date - A (2)
    M 19:4 GmailAPI.__init__ - A (1)
    M 45:4 GmailAPI._execute_with_timeout - A (1)
    M 140:4 GmailAPI._decode_body_data - A (1)
gmail/validators.py
    M 50:4 EmailValidator.validate_email_address - C (12)
    C 186:0 InputSanitizer - B (8)
    M 190:4 InputSanitizer.sanitize_search_query - B (8)
    C 9:0 EmailValidator - B (7)
    C 138:0 DateValidator - B (6)
    M 145:4 DateValidator.validate_iso_datetime - B (6)
    C 241:0 LimitValidator - B (6)
    M 20:4 EmailValidator.extract_email_from_header - A (5)
    M 119:4 EmailValidator.validate_email_size - A (5)
    M 217:4 InputSanitizer.sanitize_filename - A (5)
    M 248:4 LimitValidator.validate_query_limit - A (5)
    M 95:4 EmailValidator.validate_email_header - A (4)
    M 170:4 DateValidator.validate_date_range - A (4)
gmail/storage.py
    M 230:4 EmailStorage.save_emails_batch - B (9)
    M 89:4 EmailStorage.generate_content_hash - A (5)
    M 142:4 EmailStorage._validate_and_sanitize_data - A (5)
    C 16:0 EmailStorage - A (4)
    M 116:4 EmailStorage._validate_email_addresses - A (4)
    M 207:4 EmailStorage.save_email - A (4)
    M 424:4 EmailStorage.save_attachments - A (4)
    M 106:4 EmailStorage._validate_required_fields - A (3)
    M 160:4 EmailStorage._insert_email_to_db - A (3)
    M 352:4 EmailStorage.update_sync_state - A (3)
    M 319:4 EmailStorage.get_emails - A (2)
    M 343:4 EmailStorage.get_sync_state - A (2)
    M 19:4 EmailStorage.__init__ - A (1)
    M 28:4 EmailStorage.init_db - A (1)
gmail/main.py
    M 438:4 GmailService._fetch_and_save_messages - C (12)
    M 552:4 GmailService._process_email_summaries - C (12)
    M 340:4 GmailService._process_thread_batch - C (11)
    M 214:4 GmailService.sync_incremental - B (8)
    C 28:0 GmailService - B (7)
    M 59:4 GmailService.sync_emails - A (5)
    M 101:4 GmailService._sync_emails_batch - A (5)
    M 155:4 GmailService._sync_emails_single - A (5)
    M 319:4 GmailService._group_messages_by_thread - A (4)
    M 31:4 GmailService.__init__ - A (2)
    F 621:0 main - A (1)
    M 55:4 GmailService._setup_logging - A (1)
    M 202:4 GmailService.get_emails - A (1)
gmail/oauth.py
    M 31:4 GmailAuth.get_credentials - C (12)
    C 15:0 GmailAuth - B (6)
    M 69:4 GmailAuth.is_authenticated - A (2)
    M 18:4 GmailAuth.__init__ - A (1)

1219 blocks (classes, functions, methods) analyzed.
Average complexity: A (4.292042657916324)

### Maintainability Index
knowledge_graph/similarity_integration.py - A
knowledge_graph/__init__.py - A
knowledge_graph/timeline_relationships.py - A
knowledge_graph/topic_clustering.py - A
knowledge_graph/main.py - A
knowledge_graph/similarity_analyzer.py - A
knowledge_graph/graph_queries.py - A
tools/__init__.py - A
tools/linting/check_schema_compliance.py - A
tools/cli/__init__.py - A
tools/cli/vsearch - A
tools/cli/vsearch_modular - A
tools/scripts/extract_timeline.py - A
tools/scripts/export_documents.py - A
tools/scripts/run_full_system - A
tools/scripts/check_qdrant_documents.py - A
tools/scripts/setup_wizard - A
tools/scripts/__init__.py - A
tools/scripts/sync_vector_store.py - A
tools/scripts/search - A
tools/scripts/vsearch - A
tools/scripts/check_documents_in_vector.py - A
tools/scripts/process_embeddings.py - A
tools/scripts/vsearch_modular - A
tools/scripts/test_fast - A
tools/scripts/cli/timeline_handler.py - A
tools/scripts/cli/__init__.py - A
tools/scripts/cli/process_handler.py - A
tools/scripts/cli/cli_main.py - A
tools/scripts/cli/search_handler.py - A
tools/scripts/cli/docs_handler.py - A
tools/scripts/cli/legal_handler.py - A
tools/scripts/cli/info_handler.py - A
tools/scripts/cli/service_locator.py - A
tools/scripts/cli/upload_handler.py - A
tools/scripts/cli/notes_handler.py - A
tools/scripts/cli/intelligence_handler.py - A
tools/codemods/replace_content_id_sql.py - A
tools/codemods/consolidate_search.py - A
tools/codemods/centralize_config.py - A
config/settings.py - A
legal_intelligence/__init__.py - A
legal_intelligence/main.py - A
entity/config.py - A
entity/database.py - A
entity/__init__.py - A
entity/main.py - A
entity/processors/entity_normalizer.py - A
entity/processors/__init__.py - A
entity/extractors/legal_extractor.py - A
entity/extractors/extractor_factory.py - A
entity/extractors/__init__.py - A
entity/extractors/spacy_extractor.py - A
entity/extractors/base_extractor.py - A
entity/extractors/relationship_extractor.py - A
entity/extractors/combined_extractor.py - A
summarization/__init__.py - A
summarization/engine.py - A
pdf/database_error_recovery.py - A
pdf/__init__.py - A
pdf/pdf_processor.py - A
pdf/main.py - A
pdf/pdf_validator.py - A
pdf/pdf_health.py - A
pdf/database_health_monitor.py - A
pdf/pdf_storage_enhanced.py - A
pdf/pdf_processor_enhanced.py - A
pdf/wiring.py - A
pdf/ocr/validator.py - A
pdf/ocr/ocr_engine.py - A
pdf/ocr/postprocessor.py - A
pdf/ocr/page_processor.py - A
pdf/ocr/__init__.py - A
pdf/ocr/ocr_coordinator.py - A
pdf/ocr/loader.py - A
pdf/ocr/rasterizer.py - A
shared/original_file_manager.py - A
shared/html_cleaner.py - A
shared/loguru_config.py - A
shared/date_utils.py - A
shared/service_interfaces.py - A
shared/naming_utils.py - A
shared/__init__.py - A
shared/retry_helper.py - A
shared/simple_db.py - C
shared/snippet_utils.py - A
shared/health_check.py - A
shared/error_handler.py - A
shared/file_operations.py - A
shared/archive/cli/dedup_handler.py - A
search_intelligence/basic_search.py - A
search_intelligence/similarity.py - A
search_intelligence/__init__.py - A
search_intelligence/duplicate_detector.py - A
search_intelligence/main.py - A
utilities/archive_manager.py - A
utilities/__init__.py - A
utilities/enhanced_archive_manager.py - A
utilities/embeddings/__init__.py - A
utilities/embeddings/embedding_service.py - A
utilities/deduplication/near_duplicate_detector.py - A
utilities/deduplication/__init__.py - A
utilities/vector_store/__init__.py - A
utilities/notes/__init__.py - A
utilities/notes/main.py - A
utilities/maintenance/update_simpledb_schema_refs.py - A
utilities/maintenance/verify_vector_sync.py - A
utilities/maintenance/migrate_emails_to_content.py - A
utilities/maintenance/reconcile_qdrant_vectors.py - A
utilities/maintenance/fix_content_schema.py - A
utilities/maintenance/sync_emails_to_qdrant.py - A
utilities/maintenance/sync_missing_vectors.py - A
utilities/timeline/database.py - A
utilities/timeline/__init__.py - A
utilities/timeline/main.py - A
utilities/entities/__init__.py - A
utilities/entities/main.py - A
infrastructure/__init__.py - A
infrastructure/pipelines/data_pipeline.py - A
infrastructure/pipelines/timeline_extractor.py - A
infrastructure/pipelines/document_exporter.py - A
infrastructure/pipelines/__init__.py - A
infrastructure/pipelines/intelligence.py - A
infrastructure/pipelines/orchestrator.py - A
infrastructure/pipelines/formats.py - A
infrastructure/pipelines/processors.py - A
infrastructure/mcp_servers/legal_intelligence_mcp.py - B
infrastructure/mcp_servers/search_intelligence_mcp.py - A
infrastructure/mcp_servers/__init__.py - A
infrastructure/documents/document_converter.py - A
infrastructure/documents/lifecycle_manager.py - A
infrastructure/documents/__init__.py - A
infrastructure/documents/format_detector.py - A
infrastructure/documents/document_pipeline.py - A
infrastructure/documents/naming_convention.py - A
infrastructure/documents/processors/email_thread_processor.py - A
infrastructure/documents/processors/text_processor.py - A
infrastructure/documents/processors/__init__.py - A
infrastructure/documents/processors/base_processor.py - A
infrastructure/documents/processors/markdown_processor.py - A
infrastructure/documents/processors/docx_processor.py - A
gmail/config.py - A
gmail/gmail_api.py - A
gmail/validators.py - A
gmail/__init__.py - A
gmail/storage.py - A
gmail/main.py - A
gmail/oauth.py - A

### Raw Metrics
knowledge_graph/similarity_integration.py
    LOC: 375
    LLOC: 145
    SLOC: 257
    Comments: 19
    Single comments: 19
    Multi: 35
    Blank: 64
    - Comment Stats
        (C % L): 5%
        (C % S): 7%
        (C + M % L): 14%
knowledge_graph/__init__.py
    LOC: 27
    LLOC: 8
    SLOC: 20
    Comments: 0
    Single comments: 0
    Multi: 4
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 15%
knowledge_graph/timeline_relationships.py
    LOC: 524
    LLOC: 275
    SLOC: 324
    Comments: 37
    Single comments: 26
    Multi: 83
    Blank: 91
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 23%
knowledge_graph/topic_clustering.py
    LOC: 469
    LLOC: 223
    SLOC: 285
    Comments: 51
    Single comments: 44
    Multi: 57
    Blank: 83
    - Comment Stats
        (C % L): 11%
        (C % S): 18%
        (C + M % L): 23%
knowledge_graph/main.py
    LOC: 458
    LLOC: 209
    SLOC: 301
    Comments: 13
    Single comments: 12
    Multi: 80
    Blank: 65
    - Comment Stats
        (C % L): 3%
        (C % S): 4%
        (C + M % L): 20%
knowledge_graph/similarity_analyzer.py
    LOC: 320
    LLOC: 141
    SLOC: 194
    Comments: 19
    Single comments: 17
    Multi: 47
    Blank: 62
    - Comment Stats
        (C % L): 6%
        (C % S): 10%
        (C + M % L): 21%
knowledge_graph/graph_queries.py
    LOC: 656
    LLOC: 297
    SLOC: 446
    Comments: 46
    Single comments: 42
    Multi: 62
    Blank: 106
    - Comment Stats
        (C % L): 7%
        (C % S): 10%
        (C + M % L): 16%
tools/__init__.py
    LOC: 1
    LLOC: 1
    SLOC: 0
    Comments: 0
    Single comments: 1
    Multi: 0
    Blank: 0
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 0%
tools/linting/check_schema_compliance.py
    LOC: 215
    LLOC: 135
    SLOC: 138
    Comments: 22
    Single comments: 26
    Multi: 8
    Blank: 43
    - Comment Stats
        (C % L): 10%
        (C % S): 16%
        (C + M % L): 14%
tools/cli/__init__.py
    LOC: 1
    LLOC: 1
    SLOC: 0
    Comments: 0
    Single comments: 1
    Multi: 0
    Blank: 0
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 0%
tools/cli/vsearch
    LOC: 259
    LLOC: 182
    SLOC: 175
    Comments: 22
    Single comments: 28
    Multi: 5
    Blank: 51
    - Comment Stats
        (C % L): 8%
        (C % S): 13%
        (C + M % L): 10%
tools/cli/vsearch_modular
    LOC: 19
    LLOC: 8
    SLOC: 7
    Comments: 3
    Single comments: 3
    Multi: 5
    Blank: 4
    - Comment Stats
        (C % L): 16%
        (C % S): 43%
        (C + M % L): 42%
tools/scripts/extract_timeline.py
    LOC: 221
    LLOC: 112
    SLOC: 145
    Comments: 21
    Single comments: 23
    Multi: 5
    Blank: 48
    - Comment Stats
        (C % L): 10%
        (C % S): 14%
        (C + M % L): 12%
tools/scripts/export_documents.py
    LOC: 145
    LLOC: 86
    SLOC: 96
    Comments: 8
    Single comments: 8
    Multi: 7
    Blank: 34
    - Comment Stats
        (C % L): 6%
        (C % S): 8%
        (C + M % L): 10%
tools/scripts/run_full_system
    LOC: 587
    LLOC: 399
    SLOC: 406
    Comments: 43
    Single comments: 56
    Multi: 4
    Blank: 121
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 8%
tools/scripts/check_qdrant_documents.py
    LOC: 70
    LLOC: 44
    SLOC: 42
    Comments: 8
    Single comments: 7
    Multi: 3
    Blank: 18
    - Comment Stats
        (C % L): 11%
        (C % S): 19%
        (C + M % L): 16%
tools/scripts/setup_wizard
    LOC: 540
    LLOC: 275
    SLOC: 406
    Comments: 22
    Single comments: 36
    Multi: 4
    Blank: 94
    - Comment Stats
        (C % L): 4%
        (C % S): 5%
        (C + M % L): 5%
tools/scripts/__init__.py
    LOC: 5
    LLOC: 1
    SLOC: 0
    Comments: 0
    Single comments: 0
    Multi: 4
    Blank: 1
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 80%
tools/scripts/sync_vector_store.py
    LOC: 211
    LLOC: 125
    SLOC: 138
    Comments: 18
    Single comments: 20
    Multi: 6
    Blank: 47
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 11%
tools/scripts/search
    LOC: 22
    LLOC: 14
    SLOC: 12
    Comments: 1
    Single comments: 1
    Multi: 4
    Blank: 5
    - Comment Stats
        (C % L): 5%
        (C % S): 8%
        (C + M % L): 23%
tools/scripts/vsearch
    LOC: 618
    LLOC: 348
    SLOC: 462
    Comments: 53
    Single comments: 59
    Multi: 5
    Blank: 92
    - Comment Stats
        (C % L): 9%
        (C % S): 11%
        (C + M % L): 9%
tools/scripts/check_documents_in_vector.py
    LOC: 74
    LLOC: 45
    SLOC: 47
    Comments: 8
    Single comments: 6
    Multi: 3
    Blank: 18
    - Comment Stats
        (C % L): 11%
        (C % S): 17%
        (C + M % L): 15%
tools/scripts/process_embeddings.py
    LOC: 159
    LLOC: 85
    SLOC: 102
    Comments: 14
    Single comments: 15
    Multi: 4
    Blank: 38
    - Comment Stats
        (C % L): 9%
        (C % S): 14%
        (C + M % L): 11%
tools/scripts/vsearch_modular
    LOC: 19
    LLOC: 8
    SLOC: 7
    Comments: 3
    Single comments: 3
    Multi: 5
    Blank: 4
    - Comment Stats
        (C % L): 16%
        (C % S): 43%
        (C + M % L): 42%
tools/scripts/test_fast
    LOC: 67
    LLOC: 46
    SLOC: 43
    Comments: 5
    Single comments: 7
    Multi: 4
    Blank: 13
    - Comment Stats
        (C % L): 7%
        (C % S): 12%
        (C + M % L): 13%
tools/scripts/cli/timeline_handler.py
    LOC: 73
    LLOC: 45
    SLOC: 47
    Comments: 5
    Single comments: 6
    Multi: 4
    Blank: 16
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 12%
tools/scripts/cli/__init__.py
    LOC: 5
    LLOC: 1
    SLOC: 0
    Comments: 0
    Single comments: 0
    Multi: 4
    Blank: 1
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 80%
tools/scripts/cli/process_handler.py
    LOC: 85
    LLOC: 61
    SLOC: 57
    Comments: 3
    Single comments: 5
    Multi: 4
    Blank: 19
    - Comment Stats
        (C % L): 4%
        (C % S): 5%
        (C + M % L): 8%
tools/scripts/cli/cli_main.py
    LOC: 239
    LLOC: 118
    SLOC: 178
    Comments: 10
    Single comments: 21
    Multi: 4
    Blank: 36
    - Comment Stats
        (C % L): 4%
        (C % S): 6%
        (C + M % L): 6%
tools/scripts/cli/search_handler.py
    LOC: 252
    LLOC: 164
    SLOC: 173
    Comments: 20
    Single comments: 22
    Multi: 11
    Blank: 46
    - Comment Stats
        (C % L): 8%
        (C % S): 12%
        (C + M % L): 12%
tools/scripts/cli/docs_handler.py
    LOC: 186
    LLOC: 129
    SLOC: 126
    Comments: 13
    Single comments: 18
    Multi: 4
    Blank: 38
    - Comment Stats
        (C % L): 7%
        (C % S): 10%
        (C + M % L): 9%
tools/scripts/cli/legal_handler.py
    LOC: 412
    LLOC: 242
    SLOC: 247
    Comments: 38
    Single comments: 34
    Multi: 42
    Blank: 89
    - Comment Stats
        (C % L): 9%
        (C % S): 15%
        (C + M % L): 19%
tools/scripts/cli/info_handler.py
    LOC: 227
    LLOC: 139
    SLOC: 156
    Comments: 17
    Single comments: 20
    Multi: 4
    Blank: 47
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 9%
tools/scripts/cli/service_locator.py
    LOC: 93
    LLOC: 50
    SLOC: 36
    Comments: 7
    Single comments: 18
    Multi: 11
    Blank: 28
    - Comment Stats
        (C % L): 8%
        (C % S): 19%
        (C + M % L): 19%
tools/scripts/cli/upload_handler.py
    LOC: 132
    LLOC: 94
    SLOC: 87
    Comments: 6
    Single comments: 11
    Multi: 4
    Blank: 30
    - Comment Stats
        (C % L): 5%
        (C % S): 7%
        (C + M % L): 8%
tools/scripts/cli/notes_handler.py
    LOC: 91
    LLOC: 61
    SLOC: 64
    Comments: 2
    Single comments: 4
    Multi: 4
    Blank: 19
    - Comment Stats
        (C % L): 2%
        (C % S): 3%
        (C + M % L): 7%
tools/scripts/cli/intelligence_handler.py
    LOC: 421
    LLOC: 285
    SLOC: 294
    Comments: 17
    Single comments: 27
    Multi: 4
    Blank: 96
    - Comment Stats
        (C % L): 4%
        (C % S): 6%
        (C + M % L): 5%
tools/codemods/replace_content_id_sql.py
    LOC: 309
    LLOC: 144
    SLOC: 203
    Comments: 27
    Single comments: 25
    Multi: 16
    Blank: 65
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 14%
tools/codemods/consolidate_search.py
    LOC: 114
    LLOC: 63
    SLOC: 76
    Comments: 8
    Single comments: 9
    Multi: 3
    Blank: 26
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 10%
tools/codemods/centralize_config.py
    LOC: 244
    LLOC: 129
    SLOC: 154
    Comments: 21
    Single comments: 27
    Multi: 4
    Blank: 59
    - Comment Stats
        (C % L): 9%
        (C % S): 14%
        (C + M % L): 10%
config/settings.py
    LOC: 200
    LLOC: 142
    SLOC: 128
    Comments: 17
    Single comments: 24
    Multi: 4
    Blank: 44
    - Comment Stats
        (C % L): 8%
        (C % S): 13%
        (C + M % L): 10%
legal_intelligence/__init__.py
    LOC: 17
    LLOC: 6
    SLOC: 4
    Comments: 0
    Single comments: 0
    Multi: 7
    Blank: 6
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 41%
legal_intelligence/main.py
    LOC: 818
    LLOC: 356
    SLOC: 493
    Comments: 61
    Single comments: 53
    Multi: 121
    Blank: 151
    - Comment Stats
        (C % L): 7%
        (C % S): 12%
        (C + M % L): 22%
entity/config.py
    LOC: 82
    LLOC: 44
    SLOC: 46
    Comments: 7
    Single comments: 3
    Multi: 18
    Blank: 15
    - Comment Stats
        (C % L): 9%
        (C % S): 15%
        (C + M % L): 30%
entity/database.py
    LOC: 422
    LLOC: 187
    SLOC: 314
    Comments: 14
    Single comments: 14
    Multi: 45
    Blank: 49
    - Comment Stats
        (C % L): 3%
        (C % S): 4%
        (C + M % L): 14%
entity/__init__.py
    LOC: 16
    LLOC: 5
    SLOC: 4
    Comments: 0
    Single comments: 0
    Multi: 8
    Blank: 4
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 50%
entity/main.py
    LOC: 375
    LLOC: 201
    SLOC: 240
    Comments: 18
    Single comments: 18
    Multi: 52
    Blank: 65
    - Comment Stats
        (C % L): 5%
        (C % S): 8%
        (C + M % L): 19%
entity/processors/entity_normalizer.py
    LOC: 384
    LLOC: 200
    SLOC: 236
    Comments: 32
    Single comments: 30
    Multi: 54
    Blank: 64
    - Comment Stats
        (C % L): 8%
        (C % S): 14%
        (C + M % L): 22%
entity/processors/__init__.py
    LOC: 1
    LLOC: 0
    SLOC: 0
    Comments: 1
    Single comments: 1
    Multi: 0
    Blank: 0
    - Comment Stats
        (C % L): 100%
        (C % S): 100%
        (C + M % L): 100%
entity/extractors/legal_extractor.py
    LOC: 324
    LLOC: 122
    SLOC: 216
    Comments: 27
    Single comments: 17
    Multi: 43
    Blank: 48
    - Comment Stats
        (C % L): 8%
        (C % S): 12%
        (C + M % L): 22%
entity/extractors/extractor_factory.py
    LOC: 162
    LLOC: 64
    SLOC: 81
    Comments: 16
    Single comments: 10
    Multi: 34
    Blank: 37
    - Comment Stats
        (C % L): 10%
        (C % S): 20%
        (C + M % L): 31%
entity/extractors/__init__.py
    LOC: 11
    LLOC: 5
    SLOC: 4
    Comments: 0
    Single comments: 0
    Multi: 4
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 36%
entity/extractors/spacy_extractor.py
    LOC: 226
    LLOC: 100
    SLOC: 149
    Comments: 29
    Single comments: 9
    Multi: 34
    Blank: 34
    - Comment Stats
        (C % L): 13%
        (C % S): 19%
        (C + M % L): 28%
entity/extractors/base_extractor.py
    LOC: 98
    LLOC: 43
    SLOC: 39
    Comments: 2
    Single comments: 2
    Multi: 37
    Blank: 20
    - Comment Stats
        (C % L): 2%
        (C % S): 5%
        (C + M % L): 40%
entity/extractors/relationship_extractor.py
    LOC: 306
    LLOC: 129
    SLOC: 190
    Comments: 30
    Single comments: 23
    Multi: 43
    Blank: 50
    - Comment Stats
        (C % L): 10%
        (C % S): 16%
        (C + M % L): 24%
entity/extractors/combined_extractor.py
    LOC: 238
    LLOC: 126
    SLOC: 145
    Comments: 11
    Single comments: 10
    Multi: 33
    Blank: 50
    - Comment Stats
        (C % L): 5%
        (C % S): 8%
        (C + M % L): 18%
summarization/__init__.py
    LOC: 8
    LLOC: 3
    SLOC: 2
    Comments: 0
    Single comments: 0
    Multi: 3
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 38%
summarization/engine.py
    LOC: 447
    LLOC: 220
    SLOC: 226
    Comments: 43
    Single comments: 42
    Multi: 87
    Blank: 92
    - Comment Stats
        (C % L): 10%
        (C % S): 19%
        (C + M % L): 29%
pdf/database_error_recovery.py
    LOC: 548
    LLOC: 282
    SLOC: 352
    Comments: 39
    Single comments: 47
    Multi: 50
    Blank: 99
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 16%
pdf/__init__.py
    LOC: 16
    LLOC: 3
    SLOC: 2
    Comments: 0
    Single comments: 0
    Multi: 10
    Blank: 4
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 62%
pdf/pdf_processor.py
    LOC: 121
    LLOC: 90
    SLOC: 79
    Comments: 2
    Single comments: 11
    Multi: 3
    Blank: 28
    - Comment Stats
        (C % L): 2%
        (C % S): 3%
        (C + M % L): 4%
pdf/main.py
    LOC: 400
    LLOC: 232
    SLOC: 278
    Comments: 37
    Single comments: 40
    Multi: 19
    Blank: 63
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 14%
pdf/pdf_validator.py
    LOC: 80
    LLOC: 52
    SLOC: 53
    Comments: 5
    Single comments: 8
    Multi: 3
    Blank: 16
    - Comment Stats
        (C % L): 6%
        (C % S): 9%
        (C + M % L): 10%
pdf/pdf_health.py
    LOC: 90
    LLOC: 45
    SLOC: 67
    Comments: 2
    Single comments: 7
    Multi: 3
    Blank: 13
    - Comment Stats
        (C % L): 2%
        (C % S): 3%
        (C + M % L): 6%
pdf/database_health_monitor.py
    LOC: 492
    LLOC: 245
    SLOC: 339
    Comments: 36
    Single comments: 37
    Multi: 37
    Blank: 79
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 15%
pdf/pdf_storage_enhanced.py
    LOC: 261
    LLOC: 119
    SLOC: 203
    Comments: 10
    Single comments: 19
    Multi: 4
    Blank: 35
    - Comment Stats
        (C % L): 4%
        (C % S): 5%
        (C + M % L): 5%
pdf/pdf_processor_enhanced.py
    LOC: 132
    LLOC: 82
    SLOC: 88
    Comments: 9
    Single comments: 16
    Multi: 4
    Blank: 24
    - Comment Stats
        (C % L): 7%
        (C % S): 10%
        (C + M % L): 10%
pdf/wiring.py
    LOC: 116
    LLOC: 60
    SLOC: 68
    Comments: 7
    Single comments: 7
    Multi: 15
    Blank: 26
    - Comment Stats
        (C % L): 6%
        (C % S): 10%
        (C + M % L): 19%
pdf/ocr/validator.py
    LOC: 135
    LLOC: 79
    SLOC: 90
    Comments: 11
    Single comments: 11
    Multi: 5
    Blank: 29
    - Comment Stats
        (C % L): 8%
        (C % S): 12%
        (C + M % L): 12%
pdf/ocr/ocr_engine.py
    LOC: 192
    LLOC: 109
    SLOC: 114
    Comments: 19
    Single comments: 21
    Multi: 15
    Blank: 42
    - Comment Stats
        (C % L): 10%
        (C % S): 17%
        (C + M % L): 18%
pdf/ocr/postprocessor.py
    LOC: 179
    LLOC: 78
    SLOC: 92
    Comments: 22
    Single comments: 18
    Multi: 29
    Blank: 40
    - Comment Stats
        (C % L): 12%
        (C % S): 24%
        (C + M % L): 28%
pdf/ocr/page_processor.py
    LOC: 187
    LLOC: 81
    SLOC: 115
    Comments: 13
    Single comments: 14
    Multi: 25
    Blank: 33
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 20%
pdf/ocr/__init__.py
    LOC: 19
    LLOC: 9
    SLOC: 16
    Comments: 0
    Single comments: 1
    Multi: 0
    Blank: 2
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 0%
pdf/ocr/ocr_coordinator.py
    LOC: 120
    LLOC: 60
    SLOC: 74
    Comments: 11
    Single comments: 15
    Multi: 8
    Blank: 23
    - Comment Stats
        (C % L): 9%
        (C % S): 15%
        (C + M % L): 16%
pdf/ocr/loader.py
    LOC: 90
    LLOC: 67
    SLOC: 59
    Comments: 4
    Single comments: 9
    Multi: 0
    Blank: 22
    - Comment Stats
        (C % L): 4%
        (C % S): 7%
        (C + M % L): 4%
pdf/ocr/rasterizer.py
    LOC: 102
    LLOC: 47
    SLOC: 49
    Comments: 5
    Single comments: 7
    Multi: 21
    Blank: 25
    - Comment Stats
        (C % L): 5%
        (C % S): 10%
        (C + M % L): 25%
shared/original_file_manager.py
    LOC: 399
    LLOC: 190
    SLOC: 212
    Comments: 36
    Single comments: 41
    Multi: 71
    Blank: 75
    - Comment Stats
        (C % L): 9%
        (C % S): 17%
        (C + M % L): 27%
shared/html_cleaner.py
    LOC: 168
    LLOC: 77
    SLOC: 85
    Comments: 23
    Single comments: 16
    Multi: 26
    Blank: 41
    - Comment Stats
        (C % L): 14%
        (C % S): 27%
        (C + M % L): 29%
shared/loguru_config.py
    LOC: 144
    LLOC: 42
    SLOC: 92
    Comments: 17
    Single comments: 16
    Multi: 11
    Blank: 25
    - Comment Stats
        (C % L): 12%
        (C % S): 18%
        (C + M % L): 19%
shared/date_utils.py
    LOC: 184
    LLOC: 88
    SLOC: 114
    Comments: 26
    Single comments: 12
    Multi: 26
    Blank: 32
    - Comment Stats
        (C % L): 14%
        (C % S): 23%
        (C + M % L): 28%
shared/service_interfaces.py
    LOC: 104
    LLOC: 65
    SLOC: 36
    Comments: 1
    Single comments: 13
    Multi: 20
    Blank: 35
    - Comment Stats
        (C % L): 1%
        (C % S): 3%
        (C + M % L): 20%
shared/naming_utils.py
    LOC: 848
    LLOC: 372
    SLOC: 399
    Comments: 86
    Single comments: 98
    Multi: 156
    Blank: 195
    - Comment Stats
        (C % L): 10%
        (C % S): 22%
        (C + M % L): 29%
shared/__init__.py
    LOC: 11
    LLOC: 4
    SLOC: 3
    Comments: 0
    Single comments: 0
    Multi: 5
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 45%
shared/retry_helper.py
    LOC: 84
    LLOC: 37
    SLOC: 48
    Comments: 2
    Single comments: 4
    Multi: 15
    Blank: 17
    - Comment Stats
        (C % L): 2%
        (C % S): 4%
        (C + M % L): 20%
shared/simple_db.py
    LOC: 1729
    LLOC: 761
    SLOC: 1205
    Comments: 134
    Single comments: 158
    Multi: 122
    Blank: 244
    - Comment Stats
        (C % L): 8%
        (C % S): 11%
        (C + M % L): 15%
shared/snippet_utils.py
    LOC: 218
    LLOC: 108
    SLOC: 92
    Comments: 25
    Single comments: 25
    Multi: 48
    Blank: 53
    - Comment Stats
        (C % L): 11%
        (C % S): 27%
        (C + M % L): 33%
shared/health_check.py
    LOC: 158
    LLOC: 96
    SLOC: 104
    Comments: 14
    Single comments: 19
    Multi: 4
    Blank: 31
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 11%
shared/error_handler.py
    LOC: 118
    LLOC: 60
    SLOC: 63
    Comments: 5
    Single comments: 6
    Multi: 28
    Blank: 21
    - Comment Stats
        (C % L): 4%
        (C % S): 8%
        (C + M % L): 28%
shared/file_operations.py
    LOC: 134
    LLOC: 69
    SLOC: 58
    Comments: 5
    Single comments: 9
    Multi: 41
    Blank: 26
    - Comment Stats
        (C % L): 4%
        (C % S): 9%
        (C + M % L): 34%
shared/archive/cli/dedup_handler.py
    LOC: 336
    LLOC: 185
    SLOC: 224
    Comments: 24
    Single comments: 23
    Multi: 25
    Blank: 64
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 15%
search_intelligence/basic_search.py
    LOC: 243
    LLOC: 119
    SLOC: 131
    Comments: 23
    Single comments: 23
    Multi: 37
    Blank: 52
    - Comment Stats
        (C % L): 9%
        (C % S): 18%
        (C + M % L): 25%
search_intelligence/similarity.py
    LOC: 354
    LLOC: 163
    SLOC: 193
    Comments: 31
    Single comments: 34
    Multi: 56
    Blank: 71
    - Comment Stats
        (C % L): 9%
        (C % S): 16%
        (C + M % L): 25%
search_intelligence/__init__.py
    LOC: 26
    LLOC: 11
    SLOC: 9
    Comments: 2
    Single comments: 3
    Multi: 5
    Blank: 9
    - Comment Stats
        (C % L): 8%
        (C % S): 22%
        (C + M % L): 27%
search_intelligence/duplicate_detector.py
    LOC: 474
    LLOC: 238
    SLOC: 312
    Comments: 40
    Single comments: 45
    Multi: 31
    Blank: 86
    - Comment Stats
        (C % L): 8%
        (C % S): 13%
        (C + M % L): 15%
search_intelligence/main.py
    LOC: 568
    LLOC: 295
    SLOC: 374
    Comments: 64
    Single comments: 72
    Multi: 18
    Blank: 104
    - Comment Stats
        (C % L): 11%
        (C % S): 17%
        (C + M % L): 14%
utilities/archive_manager.py
    LOC: 326
    LLOC: 157
    SLOC: 183
    Comments: 22
    Single comments: 26
    Multi: 55
    Blank: 62
    - Comment Stats
        (C % L): 7%
        (C % S): 12%
        (C + M % L): 24%
utilities/__init__.py
    LOC: 7
    LLOC: 3
    SLOC: 2
    Comments: 0
    Single comments: 0
    Multi: 3
    Blank: 2
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 43%
utilities/enhanced_archive_manager.py
    LOC: 370
    LLOC: 160
    SLOC: 241
    Comments: 17
    Single comments: 27
    Multi: 40
    Blank: 62
    - Comment Stats
        (C % L): 5%
        (C % S): 7%
        (C + M % L): 15%
utilities/embeddings/__init__.py
    LOC: 8
    LLOC: 3
    SLOC: 2
    Comments: 0
    Single comments: 0
    Multi: 3
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 38%
utilities/embeddings/embedding_service.py
    LOC: 137
    LLOC: 76
    SLOC: 69
    Comments: 6
    Single comments: 5
    Multi: 33
    Blank: 30
    - Comment Stats
        (C % L): 4%
        (C % S): 9%
        (C + M % L): 28%
utilities/deduplication/near_duplicate_detector.py
    LOC: 428
    LLOC: 192
    SLOC: 218
    Comments: 34
    Single comments: 32
    Multi: 91
    Blank: 87
    - Comment Stats
        (C % L): 8%
        (C % S): 16%
        (C + M % L): 29%
utilities/deduplication/__init__.py
    LOC: 17
    LLOC: 3
    SLOC: 12
    Comments: 0
    Single comments: 0
    Multi: 3
    Blank: 2
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 18%
utilities/vector_store/__init__.py
    LOC: 166
    LLOC: 108
    SLOC: 108
    Comments: 6
    Single comments: 17
    Multi: 7
    Blank: 34
    - Comment Stats
        (C % L): 4%
        (C % S): 6%
        (C + M % L): 8%
utilities/notes/__init__.py
    LOC: 5
    LLOC: 3
    SLOC: 2
    Comments: 0
    Single comments: 1
    Multi: 0
    Blank: 2
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 0%
utilities/notes/main.py
    LOC: 189
    LLOC: 100
    SLOC: 145
    Comments: 2
    Single comments: 8
    Multi: 3
    Blank: 33
    - Comment Stats
        (C % L): 1%
        (C % S): 1%
        (C + M % L): 3%
utilities/maintenance/update_simpledb_schema_refs.py
    LOC: 271
    LLOC: 119
    SLOC: 199
    Comments: 22
    Single comments: 15
    Multi: 4
    Blank: 53
    - Comment Stats
        (C % L): 8%
        (C % S): 11%
        (C + M % L): 10%
utilities/maintenance/verify_vector_sync.py
    LOC: 74
    LLOC: 52
    SLOC: 50
    Comments: 7
    Single comments: 8
    Multi: 0
    Blank: 16
    - Comment Stats
        (C % L): 9%
        (C % S): 14%
        (C + M % L): 9%
utilities/maintenance/migrate_emails_to_content.py
    LOC: 225
    LLOC: 110
    SLOC: 161
    Comments: 16
    Single comments: 19
    Multi: 4
    Blank: 41
    - Comment Stats
        (C % L): 7%
        (C % S): 10%
        (C + M % L): 9%
utilities/maintenance/reconcile_qdrant_vectors.py
    LOC: 421
    LLOC: 229
    SLOC: 280
    Comments: 40
    Single comments: 44
    Multi: 7
    Blank: 90
    - Comment Stats
        (C % L): 10%
        (C % S): 14%
        (C + M % L): 11%
utilities/maintenance/fix_content_schema.py
    LOC: 511
    LLOC: 258
    SLOC: 352
    Comments: 47
    Single comments: 54
    Multi: 9
    Blank: 96
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 11%
utilities/maintenance/sync_emails_to_qdrant.py
    LOC: 96
    LLOC: 51
    SLOC: 63
    Comments: 12
    Single comments: 10
    Multi: 3
    Blank: 20
    - Comment Stats
        (C % L): 12%
        (C % S): 19%
        (C + M % L): 16%
utilities/maintenance/sync_missing_vectors.py
    LOC: 171
    LLOC: 75
    SLOC: 104
    Comments: 16
    Single comments: 15
    Multi: 18
    Blank: 34
    - Comment Stats
        (C % L): 9%
        (C % S): 15%
        (C + M % L): 20%
utilities/timeline/database.py
    LOC: 166
    LLOC: 95
    SLOC: 127
    Comments: 1
    Single comments: 6
    Multi: 3
    Blank: 30
    - Comment Stats
        (C % L): 1%
        (C % S): 1%
        (C + M % L): 2%
utilities/timeline/__init__.py
    LOC: 6
    LLOC: 4
    SLOC: 3
    Comments: 0
    Single comments: 1
    Multi: 0
    Blank: 2
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 0%
utilities/timeline/main.py
    LOC: 216
    LLOC: 98
    SLOC: 163
    Comments: 4
    Single comments: 10
    Multi: 9
    Blank: 34
    - Comment Stats
        (C % L): 2%
        (C % S): 2%
        (C + M % L): 6%
utilities/entities/__init__.py
    LOC: 27
    LLOC: 4
    SLOC: 13
    Comments: 0
    Single comments: 0
    Multi: 10
    Blank: 4
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 37%
utilities/entities/main.py
    LOC: 160
    LLOC: 68
    SLOC: 74
    Comments: 10
    Single comments: 10
    Multi: 40
    Blank: 36
    - Comment Stats
        (C % L): 6%
        (C % S): 14%
        (C + M % L): 31%
infrastructure/__init__.py
    LOC: 1
    LLOC: 1
    SLOC: 0
    Comments: 0
    Single comments: 1
    Multi: 0
    Blank: 0
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 0%
infrastructure/pipelines/data_pipeline.py
    LOC: 166
    LLOC: 112
    SLOC: 106
    Comments: 6
    Single comments: 17
    Multi: 9
    Blank: 34
    - Comment Stats
        (C % L): 4%
        (C % S): 6%
        (C + M % L): 9%
infrastructure/pipelines/timeline_extractor.py
    LOC: 571
    LLOC: 264
    SLOC: 342
    Comments: 62
    Single comments: 57
    Multi: 67
    Blank: 105
    - Comment Stats
        (C % L): 11%
        (C % S): 18%
        (C + M % L): 23%
infrastructure/pipelines/document_exporter.py
    LOC: 195
    LLOC: 117
    SLOC: 118
    Comments: 29
    Single comments: 31
    Multi: 8
    Blank: 38
    - Comment Stats
        (C % L): 15%
        (C % S): 25%
        (C + M % L): 19%
infrastructure/pipelines/__init__.py
    LOC: 43
    LLOC: 17
    SLOC: 14
    Comments: 3
    Single comments: 4
    Multi: 10
    Blank: 15
    - Comment Stats
        (C % L): 7%
        (C % S): 21%
        (C + M % L): 30%
infrastructure/pipelines/intelligence.py
    LOC: 269
    LLOC: 132
    SLOC: 168
    Comments: 19
    Single comments: 24
    Multi: 32
    Blank: 45
    - Comment Stats
        (C % L): 7%
        (C % S): 11%
        (C + M % L): 19%
infrastructure/pipelines/orchestrator.py
    LOC: 526
    LLOC: 240
    SLOC: 287
    Comments: 33
    Single comments: 35
    Multi: 100
    Blank: 104
    - Comment Stats
        (C % L): 6%
        (C % S): 11%
        (C + M % L): 25%
infrastructure/pipelines/formats.py
    LOC: 237
    LLOC: 100
    SLOC: 112
    Comments: 13
    Single comments: 17
    Multi: 57
    Blank: 51
    - Comment Stats
        (C % L): 5%
        (C % S): 12%
        (C + M % L): 30%
infrastructure/pipelines/processors.py
    LOC: 324
    LLOC: 118
    SLOC: 120
    Comments: 33
    Single comments: 34
    Multi: 85
    Blank: 85
    - Comment Stats
        (C % L): 10%
        (C % S): 28%
        (C + M % L): 36%
infrastructure/mcp_servers/legal_intelligence_mcp.py
    LOC: 893
    LLOC: 505
    SLOC: 661
    Comments: 68
    Single comments: 68
    Multi: 6
    Blank: 158
    - Comment Stats
        (C % L): 8%
        (C % S): 10%
        (C + M % L): 8%
infrastructure/mcp_servers/search_intelligence_mcp.py
    LOC: 684
    LLOC: 326
    SLOC: 518
    Comments: 41
    Single comments: 47
    Multi: 6
    Blank: 113
    - Comment Stats
        (C % L): 6%
        (C % S): 8%
        (C + M % L): 7%
infrastructure/mcp_servers/__init__.py
    LOC: 21
    LLOC: 2
    SLOC: 7
    Comments: 0
    Single comments: 0
    Multi: 11
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 52%
infrastructure/documents/document_converter.py
    LOC: 364
    LLOC: 189
    SLOC: 230
    Comments: 31
    Single comments: 39
    Multi: 27
    Blank: 68
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 16%
infrastructure/documents/lifecycle_manager.py
    LOC: 164
    LLOC: 92
    SLOC: 102
    Comments: 7
    Single comments: 17
    Multi: 16
    Blank: 29
    - Comment Stats
        (C % L): 4%
        (C % S): 7%
        (C + M % L): 14%
infrastructure/documents/__init__.py
    LOC: 20
    LLOC: 6
    SLOC: 12
    Comments: 0
    Single comments: 0
    Multi: 5
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 25%
infrastructure/documents/format_detector.py
    LOC: 184
    LLOC: 66
    SLOC: 103
    Comments: 17
    Single comments: 14
    Multi: 32
    Blank: 35
    - Comment Stats
        (C % L): 9%
        (C % S): 17%
        (C + M % L): 27%
infrastructure/documents/document_pipeline.py
    LOC: 307
    LLOC: 143
    SLOC: 173
    Comments: 24
    Single comments: 26
    Multi: 45
    Blank: 63
    - Comment Stats
        (C % L): 8%
        (C % S): 14%
        (C + M % L): 22%
infrastructure/documents/naming_convention.py
    LOC: 218
    LLOC: 102
    SLOC: 89
    Comments: 17
    Single comments: 21
    Multi: 61
    Blank: 47
    - Comment Stats
        (C % L): 8%
        (C % S): 19%
        (C + M % L): 36%
infrastructure/documents/processors/email_thread_processor.py
    LOC: 558
    LLOC: 308
    SLOC: 372
    Comments: 49
    Single comments: 60
    Multi: 27
    Blank: 99
    - Comment Stats
        (C % L): 9%
        (C % S): 13%
        (C + M % L): 14%
infrastructure/documents/processors/text_processor.py
    LOC: 191
    LLOC: 99
    SLOC: 93
    Comments: 19
    Single comments: 18
    Multi: 39
    Blank: 41
    - Comment Stats
        (C % L): 10%
        (C % S): 20%
        (C + M % L): 30%
infrastructure/documents/processors/__init__.py
    LOC: 18
    LLOC: 7
    SLOC: 13
    Comments: 0
    Single comments: 0
    Multi: 3
    Blank: 2
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 17%
infrastructure/documents/processors/base_processor.py
    LOC: 131
    LLOC: 47
    SLOC: 53
    Comments: 7
    Single comments: 8
    Multi: 40
    Blank: 30
    - Comment Stats
        (C % L): 5%
        (C % S): 13%
        (C + M % L): 36%
infrastructure/documents/processors/markdown_processor.py
    LOC: 243
    LLOC: 111
    SLOC: 106
    Comments: 27
    Single comments: 25
    Multi: 53
    Blank: 59
    - Comment Stats
        (C % L): 11%
        (C % S): 25%
        (C + M % L): 33%
infrastructure/documents/processors/docx_processor.py
    LOC: 296
    LLOC: 158
    SLOC: 153
    Comments: 21
    Single comments: 20
    Multi: 53
    Blank: 70
    - Comment Stats
        (C % L): 7%
        (C % S): 14%
        (C + M % L): 25%
gmail/config.py
    LOC: 31
    LLOC: 11
    SLOC: 19
    Comments: 3
    Single comments: 4
    Multi: 4
    Blank: 4
    - Comment Stats
        (C % L): 10%
        (C % S): 16%
        (C + M % L): 23%
gmail/gmail_api.py
    LOC: 370
    LLOC: 206
    SLOC: 217
    Comments: 24
    Single comments: 33
    Multi: 50
    Blank: 70
    - Comment Stats
        (C % L): 6%
        (C % S): 11%
        (C + M % L): 20%
gmail/validators.py
    LOC: 267
    LLOC: 194
    SLOC: 157
    Comments: 23
    Single comments: 31
    Multi: 18
    Blank: 61
    - Comment Stats
        (C % L): 9%
        (C % S): 15%
        (C + M % L): 15%
gmail/__init__.py
    LOC: 18
    LLOC: 7
    SLOC: 6
    Comments: 0
    Single comments: 0
    Multi: 9
    Blank: 3
    - Comment Stats
        (C % L): 0%
        (C % S): 0%
        (C + M % L): 50%
gmail/storage.py
    LOC: 458
    LLOC: 208
    SLOC: 343
    Comments: 30
    Single comments: 38
    Multi: 18
    Blank: 59
    - Comment Stats
        (C % L): 7%
        (C % S): 9%
        (C + M % L): 10%
gmail/main.py
    LOC: 628
    LLOC: 293
    SLOC: 409
    Comments: 59
    Single comments: 54
    Multi: 51
    Blank: 114
    - Comment Stats
        (C % L): 9%
        (C % S): 14%
        (C + M % L): 18%
gmail/oauth.py
    LOC: 75
    LLOC: 43
    SLOC: 40
    Comments: 5
    Single comments: 6
    Multi: 13
    Blank: 16
    - Comment Stats
        (C % L): 7%
        (C % S): 12%
        (C + M % L): 24%
** Total **
    LOC: 35128
    LLOC: 17803
    SLOC: 22074
    Comments: 2660
    Single comments: 2925
    Multi: 3490
    Blank: 6639
    - Comment Stats
        (C % L): 8%
        (C % S): 12%
        (C + M % L): 18%
