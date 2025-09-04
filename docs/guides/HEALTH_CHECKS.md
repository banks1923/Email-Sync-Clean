# Health Checks and Diagnostics

This guide explains the unified health system for core services and how to use it from the CLI and code.

## Overview

- Uniform schema across services with consistent keys:
  - `status`: "healthy" | "mock" | "degraded" | "error"
  - `details`: stable, service-specific fields (e.g., model_name, vector_size, db_path)
  - `metrics`: lightweight stats
  - `hints`: actionable guidance

- Light vs Deep checks:
  - Light avoids heavy work and external dependencies.
  - Deep performs a tiny encode for embeddings and may count vectors.

## CLI Usage

```bash
# Human-readable
python tools/scripts/vsearch admin health

# Machine-readable
python tools/scripts/vsearch admin health --json

# Deep checks (heavier, optional)
python tools/scripts/vsearch admin health --deep

# CI/dev fast-path
TEST_MODE=1 python tools/scripts/vsearch admin health --json
```

Exit codes: 0 healthy, 1 degraded/mock (0 in TEST_MODE), 2 error.

## Environment Variables

- `TEST_MODE=1`: enable fast, dependency-free checks and treat mock as success
- `SKIP_MODEL_LOAD=1`: skip loading real embedding models (use mock)
- `QDRANT_DISABLED=1`: force mock vector store
- `QDRANT_HOST`, `QDRANT_PORT`: vector store endpoint (defaults: localhost:6333)
- `QDRANT_TIMEOUT_S`: HTTP timeout in seconds (default: 0.5)

## Programmatic API

```python
from lib.db import SimpleDB
from lib.embeddings import get_embedding_service
from lib.vector_store import get_vector_store

db_health = SimpleDB().health_check(deep=False)
emb_health = get_embedding_service().health_check(deep=False)
vec_health = get_vector_store().health_check(deep=False)

report = {
    "status": "healthy",  # compute from the three statuses
    "services": {"db": db_health, "embeddings": emb_health, "vector": vec_health},
}
```

## Troubleshooting

- Vector service unavailable:
  - Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
  - Configure endpoint: `QDRANT_HOST`, `QDRANT_PORT`
- Embeddings too slow or failing:
  - Use `SKIP_MODEL_LOAD=1` or `TEST_MODE=1` to use mock
  - Install `sentence-transformers` and retry
- Database issues:
  - Check the path under `details.db_path` and file permissions

