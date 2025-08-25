# Archived Document AI Scripts

These scripts were retired on 2025-08-25 after implementing the enhanced Document AI processor.

## Reason for Archival
These scripts were replaced by `process_legal_docs_enhanced.py` which includes:
- Automatic PDF splitting for large documents
- Coverage metrics for quality assessment  
- Stage→Merge BigQuery pattern
- Resume support with state tracking
- Exponential backoff and retry logic

## Archived Scripts
- `process_legal_docs_v2.py` - Initial v2 attempt
- `process_legal_docs_fixed.py` - Intermediate fixes
- `document_ai_enhanced.py` - Early enhancement attempt
- `document_ai_manager.py` - Management utility
- `batch_process_documents.py` - Batch processing utility
- `process_single_document.py` - Single doc processor
- `simple_legal_cleaner.py` - Text cleaning utility
- `test_document_ai_connection.py` - Connection test
- `segregate_privileged_docs.py` - Manual privilege segregation
- `segregate_privileged_docs_auto.py` - Auto privilege segregation

## Active Scripts
The following remain active:
- `process_legal_docs_enhanced.py` - Main production processor
- `bigquery_schema_prod.sql` - Production BigQuery schema
- `test_bigquery.py` - BigQuery connection test (kept for diagnostics)

To restore any archived script:
```bash
cp scripts/archived_document_ai/[script_name] scripts/
```
