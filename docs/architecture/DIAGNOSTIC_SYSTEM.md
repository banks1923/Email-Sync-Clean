# System Diagnostic Documentation

Comprehensive diagnostic system for validating Email Sync wiring, performance, and efficiency from a user perspective.

## Quick Start

```bash
# Full system diagnostic (recommended)
make diagnose

# Quick system health check
make status

# Direct script execution
python3 tools/diag_wiring.py
```

## What It Validates

### WORKING: Alignment Check
- **Qdrant Connection**: Validates connection to localhost:6333
- **Collection Existence**: Ensures 'emails' collection exists with correct dimensions
- **Dimension Matching**: Verifies embedding dimensions (1024) match collection dimensions
- **Vector Store Health**: Confirms Qdrant service is responsive

### WORKING: Embeddings Performance
- **Device Detection**: Reports device (mps/cuda/cpu) being used
- **Batch Processing**: Tests batch_encode with 256 strings (batch size 16)
- **Throughput**: Measures items/sec processing rate (budget: ≥600/min)
- **Latency**: P95 latency per item (budget: ≤25ms)
- **Normalization**: Validates L2-normalized embeddings

### WORKING: Vector Store Operations
- **Method Availability**: Confirms batch_upsert and iter_ids methods exist
- **Batch Performance**: Tests 1000 vector upsert throughput (budget: ≥2000/min)
- **API Compatibility**: Validates expected method signatures
- **Cleanup**: Automatically removes test data after validation

### WORKING: Search User Experience
- **Query Testing**: Runs searches for "invoice", "schedule", "legal"
- **Latency Measurement**: P95 search latency (budget: ≤80ms)
- **Relevance Scoring**: Validates semantic similarity scores
- **Result Quality**: Ensures at least 1 hit per query

### WORKING: Maintenance Operations
- **Database Health**: Tests WAL checkpoint functionality
- **Batch Configuration**: Validates batch_size=500, progress_every=100
- **Performance**: Measures checkpoint timing
- **Policy Compliance**: Confirms maintenance policies are implemented

### WORKING: Reconciliation Scanning (Optional)
- **ID Pagination**: Tests iter_ids pagination performance
- **Scan Rate**: Measures IDs/min processing (budget: ≥10k/min)
- **Memory Efficiency**: Validates paginated approach over list_all_ids

## Report Format

The diagnostic outputs a standardized one-screen report:

```
REPO: Email-Sync-Clean-Backup
QDRANT: localhost:6333 | collection=emails
ALIGNMENT: dim_embed=1024 dim_collection=1024 dim_match=True l2_norm=True  WORKING:
EMBEDDINGS: device=mps:0 batch=16 throughput=247/s p95=4.0 ms  WORKING:
VECTORS: batch_upsert=YES iter_ids=YES upsert=1021/s  WORKING:
SEARCH: k=10 q=['invoice','schedule','legal'] p95=5.1 ms top1=0.525  WORKING:
MAINTENANCE: batch=500 progress=100 wal_checkpoint=0.4 ms  WORKING:
RECONCILE (opt): scan_rate=5850k ids/min  WORKING:
VERDICT: WORKING: OK
```

### Status Indicators
- **WORKING:**: Check passed
- ****: Check failed
- **N/A**: Feature not available (non-critical)

## Performance Budgets

| Component | Metric | Budget | Typical Performance |
|-----------|--------|--------|-------------------|
| Embeddings | Throughput | ≥600/min | 14,000+/min |
| Embeddings | P95 Latency | ≤25ms/item | 4-5ms |
| Vector Upsert | Throughput | ≥2000/min | 60,000+/min |
| Search | P95 Latency | ≤80ms | 5-20ms |
| Reconcile | Scan Rate | ≥10k IDs/min | 4-6M IDs/min |

## Exit Codes

- **0**: All checks passed (WORKING: OK)
- **1**: One or more checks failed ( MISWIRED)

## Usage Patterns

### Daily Health Check
```bash
make diagnose
# Quick validation before development work
```

### CI/CD Integration
```bash
# In build scripts
python3 tools/diag_wiring.py
if [ $? -ne 0 ]; then
  echo "System diagnostic failed"
  exit 1
fi
```

### Performance Monitoring
```bash
# Benchmark after changes
make diagnose > diagnostic_$(date +%Y%m%d).log
```

### Troubleshooting
```bash
# When search seems slow
make status  # Quick validation
make diagnose   # Full analysis
```

## Architecture

### Dependencies
- **utilities.embeddings**: Legal BERT embedding service
- **utilities.vector_store**: Qdrant vector operations
- **shared.simple_db**: Database operations with WAL
- **torch**: Tensor operations for normalization checks

### Test Data Management
- **Temporary IDs**: Uses UUID4 for test vectors
- **Automatic Cleanup**: Removes all test data after validation
- **Isolation**: Test data marked with metadata for identification
- **Safety**: Read-only checks except for temporary test data

### Performance Optimizations
- **Batch Operations**: Uses batch_encode and batch_upsert where available
- **Pagination**: Tests iter_ids over list_all_ids for memory efficiency
- **Limited Scope**: Reconcile check limits to 5 pages to avoid long tests
- **Parallel Safe**: Can run alongside normal operations

## Implementation Details

### Configuration
```python
# Key settings (tools/diag_wiring.py)
DEFAULT_COLLECTION = "emails"
EMBEDDING_DIM = 1024
BATCH_SIZE = 500
EMBED_BATCH_SIZE = 16
ID_PAGE_SIZE = 1000
```

### Validation Logic
1. **Fail Fast**: Stops at first critical failure (Qdrant unreachable)
2. **Graceful Degradation**: Non-critical features marked N/A
3. **Detailed Reporting**: Shows specific failure reasons
4. **Clean Recovery**: Always cleans up test data, even on failures

### Error Handling
- **Connection Failures**: Clear "Qdrant unreachable" messages
- **Dimension Mismatches**: Shows expected vs actual dimensions
- **Performance Issues**: Identifies which budget was missed
- **Missing Features**: Reports unavailable methods (batch_upsert, iter_ids)

## Integration

### Make Targets
```makefile
diag-wiring: ## Full system diagnostic - validate wiring & efficiency
vector-smoke: ## Quick vector smoke test - upsert 50 points & run 2 searches
```

### Related Commands
```bash
# System health
make check          # Code quality + fast tests
make diagnose    # System wiring validation
make vector-status  # Vector store sync status

# Maintenance
make vector-sync    # Sync missing vectors
make maintenance-all # Run all maintenance checks
```

## Security & Safety

### Safe Operations
- **Read-Only**: Only reads system state (except temp test data)
- **Isolated Testing**: Test data clearly marked and auto-removed
- **No Side Effects**: Doesn't modify existing data or configuration
- **Timeout Protection**: All operations have reasonable timeouts

### Privacy
- **No Data Access**: Doesn't read user documents or emails
- **Test Data Only**: Uses synthetic "test document N" strings
- **Metadata Safe**: Only creates temporary diagnostic metadata
- **Log Safety**: No sensitive information in diagnostic output

---

## Troubleshooting Guide

###  Qdrant Connection Failures

**Symptom**: `ALIGNMENT: FAILED - Qdrant unreachable`

**Solutions**:
```bash
# Start Qdrant service
cd /path/to/Email\ Sync
QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant &

# Check if process is running
ps aux | grep qdrant

# Verify port is open
nc -z localhost 6333
```

**Common Causes**:
- Qdrant service not started
- Port 6333 already in use
- Firewall blocking local connections
- Wrong path to qdrant binary

###  Dimension Mismatch

**Symptom**: `dim_match=False` with different embed_dim vs collection_dim

**Solutions**:
```bash
# Delete and recreate collection
make vector-sync  # Will recreate with correct dimensions
```

**Root Cause**: Collection was created with different embedding model

###  Embeddings Performance Issues

**Symptom**: `EMBEDDINGS: FAILED - throughput_ok=False` or `latency_ok=False`

**Performance Debugging**:
```bash
# Check device being used
python3 -c "
import torch
print(f'MPS available: {torch.backends.mps.is_available()}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')
"
```

**Solutions**:
- **Slow MPS**: Normal for first run (model loading), retry diagnostic
- **CPU Fallback**: Install proper PyTorch for your platform
- **Memory Issues**: Reduce EMBED_BATCH_SIZE in tools/diag_wiring.py

###  Vector Store API Issues  

**Symptom**: `VECTORS: FAILED - batch_upsert not implemented`

**Investigation**:
```bash
# Check vector store implementation
python3 -c "
from utilities.vector_store import get_vector_store
vs = get_vector_store()
print(f'batch_upsert: {hasattr(vs, \"batch_upsert\")}')
print(f'iter_ids: {hasattr(vs, \"iter_ids\")}')
"
```

**Solutions**:
- Update vector store implementation to include missing methods
- Check import paths in diagnostic script

###  Search Performance Issues

**Symptom**: `SEARCH: FAILED` with high p95 latency or no hits

**Debugging**:
```bash
# Check collection status
python3 -c "
from utilities.vector_store import get_vector_store
vs = get_vector_store()
stats = vs.get_collection_stats()
print(f'Points in collection: {stats[\"points_count\"]}')
print(f'Collection health: {vs.health()}')
"
```

**Common Issues**:
- **No Data**: Empty collection (points_count=0)
- **Cold Start**: First search after restart is slower
- **Network Issues**: High latency to Qdrant

###  Database Maintenance Issues

**Symptom**: `MAINTENANCE: FAILED - db_maintenance not implemented`

**Check Implementation**:
```bash
# Verify db_maintenance method exists
python3 -c "
from shared.db.simple_db import SimpleDB
db = SimpleDB()
print(f'db_maintenance available: {hasattr(db, \"db_maintenance\")}')
"
```

###  Import/Module Issues

**Symptom**: `ImportError` or `ModuleNotFoundError`

**Environment Check**:
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Verify key modules
python3 -c "
try:
    from utilities.embeddings import get_embedding_service
    from utilities.vector_store import get_vector_store
    from shared.db.simple_db import SimpleDB
    print(' All modules importable')
except ImportError as e:
    print(f' Import error: {e}')
"
```

## Performance Tuning

### Embedding Optimization
```python
# In tools/diag_wiring.py, adjust batch size
EMBED_BATCH_SIZE = 8   # Reduce if memory issues
EMBED_BATCH_SIZE = 32  # Increase if underutilized GPU
```

### Vector Store Optimization  
```python
# Reduce test size for faster diagnostics
test_count = 500  # Instead of 1000
```

### Search Optimization
```bash
# Warm up search cache
make status  # Run before diag-wiring for faster results
```

## Monitoring & Alerts

### Automated Health Checks
```bash
# Add to cron for daily health monitoring
0 9 * * * cd /path/to/project && make diagnose > /tmp/health_$(date +\%Y\%m\%d).log 2>&1
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: System Diagnostics
  run: |
    make diagnose
    if [ $? -ne 0 ]; then
      echo "::error::System diagnostic failed"
      exit 1
    fi
```

### Performance Regression Detection
```bash
# Baseline performance tracking
make diagnose 2>&1 | grep "throughput\|p95" > perf_baseline.txt
```

## Advanced Debugging

### Verbose Diagnostic Mode
```python
# Edit tools/diag_wiring.py to add debug output
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Manual Step-by-Step Testing
```python
# Test individual components
python3 -c "
import sys; sys.path.insert(0, '.')
from tools.diag_wiring import check_alignment, check_embeddings

# Test each check individually
align_ok, align_data = check_alignment()
print(f'Alignment: {align_ok}, {align_data}')

embed_ok, embed_data = check_embeddings() 
print(f'Embeddings: {embed_ok}, {embed_data}')
"
```

### Log Analysis
```bash
# Filter diagnostic logs for specific issues
make diagnose 2>&1 | grep -E "(ERROR|FAILED|)"

# Check system logs during diagnostic
tail -f ~/.local/share/qdrant/logs/qdrant.log &
make diagnose
```