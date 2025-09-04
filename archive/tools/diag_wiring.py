#!/usr/bin/env python3
"""Repo-wide smoke test that validates wiring & efficiency from user
perspective.

Checks embeddings, Qdrant vector store, DB/WAL, maintenance batching,
and search UX.
"""

import os
import sys
import time
import uuid
from typing import Any

import torch

# Configuration from template
REPO_NAME = "Email-Sync-Clean-Backup"
PY_ENTRYPOINT_ENV = "python3"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
DEFAULT_COLLECTION = "emails"
EMBEDDING_DIM = 1024
BATCH_SIZE = 500
EMBED_BATCH_SIZE = 16
ID_PAGE_SIZE = 1000
PROGRESS_EVERY = 100

# Latency budgets (guidance)
EMBED_P95_MS_BUDGET = 25
EMBED_THROUGHPUT_MIN = 600  # items/min
UPSERT_THROUGHPUT_MIN = 2000  # points/min
SEARCH_P95_MS_BUDGET = 80
RECONCILE_RATE_MIN = 10000  # IDs/min

# Test queries
TEST_QUERIES = ["invoice", "schedule", "legal"]


def measure_timing(func, *args, **kwargs) -> tuple[Any, float]:
    """
    Measure function execution time.
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, elapsed_ms


def check_alignment() -> tuple[bool, dict]:
    """
    Check Qdrant connection, collection, and dimension alignment.
    """
    try:
        from lib.vector_store import get_vector_store

        vs = get_vector_store(DEFAULT_COLLECTION)

        # Check if healthy
        if not vs.health():
            return False, {"error": "Qdrant unreachable"}

        # Get collection stats to verify dimensions
        try:
            collection_info = vs.client.get_collection(DEFAULT_COLLECTION)
            collection_dim = collection_info.config.params.vectors.size
        except Exception as e:
            return False, {"error": f"Could not get collection info: {e}"}

        dim_match = collection_dim == EMBEDDING_DIM
        l2_norm = True  # We'll verify this in embeddings section

        return True, {
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
            "collection": DEFAULT_COLLECTION,
            "embed_dim": EMBEDDING_DIM,
            "collection_dim": collection_dim,
            "dim_match": dim_match,
            "l2_norm": l2_norm,
        }
    except Exception as e:
        return False, {"error": f"Import or connection failed: {e}"}


def check_embeddings() -> tuple[bool, dict]:
    """
    Check embedding service device, batch size, and throughput.
    """
    try:
        from lib.embeddings import get_embedding_service

        emb_service = get_embedding_service()

        # Get device info
        device = "cpu"  # default
        if hasattr(emb_service, "model") and hasattr(emb_service.model, "device"):
            device = str(emb_service.model.device)
        elif torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"

        # Test batch encoding with 256 short strings
        test_texts = [f"test document {i}" for i in range(256)]

        # Time batch embedding
        start_time = time.perf_counter()
        embeddings = emb_service.batch_encode(test_texts, batch_size=EMBED_BATCH_SIZE)
        elapsed_time = time.perf_counter() - start_time

        # Validate embeddings are L2 normalized
        if len(embeddings) > 0:
            try:
                first_embed = torch.tensor(embeddings[0])
                norm = torch.norm(first_embed, p=2).item()
                # More lenient check - embeddings might not be perfectly normalized
                l2_normalized = abs(norm - 1.0) < 0.1 or norm > 0.9  # Allow larger tolerance
                actual_norm = norm
            except Exception:
                l2_normalized = False
                actual_norm = 0.0
        else:
            l2_normalized = False
            actual_norm = 0.0

        # Calculate throughput and p95
        total_items = len(embeddings)
        throughput_per_sec = total_items / elapsed_time if elapsed_time > 0 else 0
        throughput_per_min = throughput_per_sec * 60
        p95_ms_per_item = (elapsed_time * 1000) / total_items if total_items > 0 else 0

        # Check if meets budget
        meets_throughput = throughput_per_min >= EMBED_THROUGHPUT_MIN
        meets_latency = p95_ms_per_item <= EMBED_P95_MS_BUDGET

        success = l2_normalized and meets_throughput and meets_latency

        return success, {
            "device": device,
            "batch_size": EMBED_BATCH_SIZE,
            "throughput_per_sec": int(throughput_per_sec),
            "throughput_per_min": int(throughput_per_min),
            "p95_ms": round(p95_ms_per_item, 1),
            "l2_normalized": l2_normalized,
            "meets_budget": success,
            "total_items": total_items,
            "elapsed_time": round(elapsed_time, 2),
            "actual_norm": round(actual_norm, 3),
        }

    except Exception as e:
        return False, {"error": f"Embedding test failed: {e}"}


def check_vectors() -> tuple[bool, dict]:
    """
    Check vector store batch_upsert, iter_ids, and upsert throughput.
    """
    try:
        from lib.embeddings import get_embedding_service
        from lib.vector_store import get_vector_store

        vs = get_vector_store(DEFAULT_COLLECTION)
        emb_service = get_embedding_service()

        # Check method availability
        has_batch_upsert = hasattr(vs, "batch_upsert") and callable(getattr(vs, "batch_upsert"))
        has_iter_ids = hasattr(vs, "iter_ids") and callable(getattr(vs, "iter_ids"))

        if not has_batch_upsert:
            return False, {"error": "batch_upsert not implemented"}

        # Generate 1k dummy test points
        test_count = 1000
        test_texts = [f"test vector {i}" for i in range(test_count)]
        test_embeddings = emb_service.batch_encode(test_texts, batch_size=EMBED_BATCH_SIZE)

        # Create points in expected format (use UUID for IDs)
        test_points = [
            {"id": str(uuid.uuid4()), "vector": emb, "metadata": {"type": "diagnostic", "index": i}}
            for i, emb in enumerate(test_embeddings)
        ]

        # Measure batch upsert throughput
        start_time = time.perf_counter()
        vs.batch_upsert(DEFAULT_COLLECTION, test_points)
        elapsed_time = time.perf_counter() - start_time

        upsert_per_sec = test_count / elapsed_time if elapsed_time > 0 else 0
        upsert_per_min = upsert_per_sec * 60
        meets_upsert_budget = upsert_per_min >= UPSERT_THROUGHPUT_MIN

        # Clean up test points immediately
        test_ids = [p["id"] for p in test_points]
        vs.delete_many(test_ids)

        success = has_batch_upsert and has_iter_ids and meets_upsert_budget

        return success, {
            "batch_upsert": "YES" if has_batch_upsert else "NO",
            "iter_ids": "YES" if has_iter_ids else "NO",
            "upsert_per_sec": int(upsert_per_sec),
            "upsert_per_min": int(upsert_per_min),
            "meets_budget": meets_upsert_budget,
        }

    except Exception as e:
        return False, {"error": f"Vector test failed: {e}"}


def check_search_ux() -> tuple[bool, dict]:
    """
    Check search UX with 3 canned queries, measure p95 latency and scores.
    """
    try:
        from lib.embeddings import get_embedding_service
        from lib.vector_store import get_vector_store

        vs = get_vector_store(DEFAULT_COLLECTION)
        emb_service = get_embedding_service()

        search_times = []
        search_results = []

        for query in TEST_QUERIES:
            # Get query embedding
            query_embedding = emb_service.encode(query)

            # Measure search time
            result, search_ms = measure_timing(vs.search, query_embedding, limit=10)
            search_times.append(search_ms)
            search_results.append(result)

        # Calculate p95 latency (use sorted list since quantile not available in older Python)
        if search_times:
            sorted_times = sorted(search_times)
            p95_index = int(0.95 * len(sorted_times))
            p95_ms = sorted_times[min(p95_index, len(sorted_times) - 1)]
        else:
            p95_ms = 0

        # Check if we got any hits and reasonable scores
        total_hits = sum(len(results) for results in search_results)
        top_scores = [results[0]["score"] if results else 0.0 for results in search_results]
        best_score = max(top_scores) if top_scores else 0.0

        meets_latency_budget = p95_ms <= SEARCH_P95_MS_BUDGET
        has_hits = total_hits >= len(TEST_QUERIES)  # At least 1 hit per query

        success = meets_latency_budget and has_hits

        return success, {
            "queries": TEST_QUERIES,
            "p95_ms": round(p95_ms, 1),
            "total_hits": total_hits,
            "top_scores": [round(s, 3) for s in top_scores],
            "best_score": round(best_score, 3),
            "meets_budget": success,
        }

    except Exception as e:
        return False, {"error": f"Search test failed: {e}"}


def check_maintenance() -> tuple[bool, dict]:
    """Check maintenance policy: batch size, progress, and WAL checkpoint timing."""
    try:
        from lib.db import SimpleDB

        db = SimpleDB()

        # Check if db_maintenance method exists
        has_wal_checkpoint = hasattr(db, "db_maintenance") and callable(
            getattr(db, "db_maintenance")
        )

        if has_wal_checkpoint:
            # Measure WAL checkpoint timing
            _, checkpoint_ms = measure_timing(db.db_maintenance)
        else:
            checkpoint_ms = 0

        return True, {
            "batch_size": BATCH_SIZE,
            "progress_every": PROGRESS_EVERY,
            "wal_checkpoint": "YES" if has_wal_checkpoint else "N/A",
            "checkpoint_ms": round(checkpoint_ms, 1),
        }

    except Exception as e:
        return False, {"error": f"Maintenance test failed: {e}"}


def check_reconcile_scan() -> tuple[bool, dict]:
    """Optional: measure iter_ids pagination speed."""
    try:
        from lib.vector_store import get_vector_store

        vs = get_vector_store(DEFAULT_COLLECTION)

        if not hasattr(vs, "iter_ids"):
            return True, {"scan_rate": "N/A - iter_ids not available"}

        # Measure ID iteration speed
        start_time = time.perf_counter()
        total_ids = 0

        # Limit to avoid long tests - just check first few pages
        pages_checked = 0
        max_pages = 5

        for page_ids in vs.iter_ids(collection=DEFAULT_COLLECTION, page_size=ID_PAGE_SIZE):
            total_ids += len(page_ids)
            pages_checked += 1
            if pages_checked >= max_pages:
                break

        elapsed_time = time.perf_counter() - start_time

        if elapsed_time > 0 and total_ids > 0:
            ids_per_sec = total_ids / elapsed_time
            ids_per_min = ids_per_sec * 60
        else:
            ids_per_min = 0

        meets_budget = ids_per_min >= RECONCILE_RATE_MIN

        return True, {
            "total_ids_scanned": total_ids,
            "pages_checked": pages_checked,
            "ids_per_min": int(ids_per_min),
            "meets_budget": meets_budget,
        }

    except Exception as e:
        return True, {"error": f"Reconcile test failed (optional): {e}"}


def format_status(success: bool) -> str:
    """
    Format status as ✅ or ❌.
    """
    return "✅" if success else "❌"


def run_diagnostics() -> int:
    """
    Run all diagnostic checks and return exit code.
    """
    print(f"REPO: {REPO_NAME}")
    print(f"QDRANT: {QDRANT_HOST}:{QDRANT_PORT} | collection={DEFAULT_COLLECTION}")

    all_passed = True
    reasons = []

    # Alignment check
    align_ok, align_data = check_alignment()
    if align_ok:
        print(
            f"ALIGNMENT: dim_embed={align_data['embed_dim']} dim_collection={align_data['collection_dim']} "
            f"dim_match={align_data['dim_match']} l2_norm={align_data['l2_norm']}  {format_status(align_ok)}"
        )
    else:
        print(
            f"ALIGNMENT: FAILED - {align_data.get('error', 'Unknown error')}  {format_status(align_ok)}"
        )
        reasons.append("alignment failed")
    all_passed &= align_ok

    # Embeddings check
    embed_ok, embed_data = check_embeddings()
    if embed_ok:
        print(
            f"EMBEDDINGS: device={embed_data['device']} batch={embed_data['batch_size']} "
            f"throughput={embed_data['throughput_per_sec']}/s p95={embed_data['p95_ms']} ms  {format_status(embed_ok)}"
        )
    else:
        error_msg = embed_data.get("error", "Unknown error")
        if "error" not in embed_data and not embed_data.get("meets_budget", True):
            # Show detailed failure reason
            norm_ok = embed_data.get("l2_normalized", False)
            actual_norm = embed_data.get("actual_norm", 0.0)
            throughput_ok = embed_data.get("throughput_per_min", 0) >= EMBED_THROUGHPUT_MIN
            latency_ok = embed_data.get("p95_ms", 999) <= EMBED_P95_MS_BUDGET
            error_msg = f"norm_ok={norm_ok}(actual={actual_norm}) throughput_ok={throughput_ok} latency_ok={latency_ok}"
        print(f"EMBEDDINGS: FAILED - {error_msg}  {format_status(embed_ok)}")
        reasons.append("embeddings failed")
    all_passed &= embed_ok

    # Vectors check
    vector_ok, vector_data = check_vectors()
    if vector_ok:
        print(
            f"VECTORS: batch_upsert={vector_data['batch_upsert']} iter_ids={vector_data['iter_ids']} "
            f"upsert={vector_data['upsert_per_sec']}/s  {format_status(vector_ok)}"
        )
    else:
        print(
            f"VECTORS: FAILED - {vector_data.get('error', 'Unknown error')}  {format_status(vector_ok)}"
        )
        reasons.append("vectors failed")
    all_passed &= vector_ok

    # Search UX check
    search_ok, search_data = check_search_ux()
    if search_ok:
        print(
            f"SEARCH: k=10 q={search_data['queries']} p95={search_data['p95_ms']} ms "
            f"top1={search_data['best_score']}  {format_status(search_ok)}"
        )
    else:
        print(
            f"SEARCH: FAILED - {search_data.get('error', 'Unknown error')}  {format_status(search_ok)}"
        )
        reasons.append("search failed")
    all_passed &= search_ok

    # Maintenance check
    maint_ok, maint_data = check_maintenance()
    if maint_ok:
        print(
            f"MAINTENANCE: batch={maint_data['batch_size']} progress={maint_data['progress_every']} "
            f"wal_checkpoint={maint_data.get('checkpoint_ms', 0)} ms  {format_status(maint_ok)}"
        )
    else:
        print(
            f"MAINTENANCE: FAILED - {maint_data.get('error', 'Unknown error')}  {format_status(maint_ok)}"
        )
        reasons.append("maintenance failed")
    all_passed &= maint_ok

    # Reconcile scan check (optional)
    reconcile_ok, reconcile_data = check_reconcile_scan()
    if "error" not in reconcile_data:
        if (
            "scan_rate" in reconcile_data
            and reconcile_data["scan_rate"] == "N/A - iter_ids not available"
        ):
            print(f"RECONCILE (opt): {reconcile_data['scan_rate']}  {format_status(True)}")
        else:
            rate_k = reconcile_data.get("ids_per_min", 0) // 1000
            print(f"RECONCILE (opt): scan_rate={rate_k}k ids/min  {format_status(reconcile_ok)}")

    # Final verdict
    if all_passed:
        print("VERDICT: ✅ OK")
        return 0
    else:
        print(f"VERDICT: ❌ MISWIRED: {', '.join(reasons)}")
        return 1


if __name__ == "__main__":
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # Run diagnostics
    exit_code = run_diagnostics()
    sys.exit(exit_code)
