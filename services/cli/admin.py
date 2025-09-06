import argparse
import json
import os


def _aggregate_status(*statuses: str) -> str:
    order = {"healthy": 0, "mock": 1, "degraded": 1, "error": 2}
    worst = max(statuses, key=lambda s: order.get(s, 2)) if statuses else "healthy"
    return worst


def _exit_code_for(status: str) -> int:
    if status == "error":
        return 2
    if status in ("degraded", "mock"):
        # Treat mock as ok in TEST_MODE
        return 0 if os.getenv("TEST_MODE") == "1" else 1
    return 0


def health(argv=None) -> int:
    ap = argparse.ArgumentParser(description="System health")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    ap.add_argument("--deep", action="store_true", help="Run deep checks (slower)")
    args = ap.parse_args(argv)

    # DB health
    from lib.db import SimpleDB

    db = SimpleDB()
    db_health = db.health_check(deep=args.deep)

    # Embeddings health (avoid heavy load in light mode)
    from lib.embeddings import get_embedding_service

    # Fixed: use real embeddings unless explicitly in test mode
    emb = get_embedding_service(use_mock=False)
    emb_health = emb.health_check(deep=args.deep)

    # Vector health (mock in TEST_MODE or if disabled)
    from lib.vector_store import get_vector_store

    store = get_vector_store()
    vec_health = store.health_check(deep=args.deep)

    overall = _aggregate_status(db_health.get("status"), emb_health.get("status"), vec_health.get("status"))

    result = {
        "status": overall,
        "services": {
            "db": db_health,
            "embeddings": emb_health,
            "vector": vec_health,
        },
    }

    if args.__dict__["json"]:
        print(json.dumps(result, indent=2))
    else:
        print("System Health:\n==========")
        print(f"Overall: {overall}")
        for name, report in result["services"].items():
            print(f"\n{name.upper()} -> {report.get('status')}")
            details = report.get("details", {})
            if name == "vector":
                host = details.get("host")
                port = details.get("port")
                print(f"  Endpoint: {host}:{port}")
                print(f"  Collection: {details.get('collection_name')} (exists={details.get('collection_exists')})")
            if name == "embeddings":
                print(f"  Model: {details.get('model_name')} (loaded={details.get('model_loaded')})")
                print(f"  Dimension: {details.get('vector_dimension')}")
            if name == "db":
                print(f"  Path: {details.get('db_path')}")
                print(f"  Content count: {details.get('content_count')}")
            hints = report.get("hints") or []
            for h in hints:
                print(f"  Hint: {h}")

    return _exit_code_for(overall)


def main(argv=None):
    p = argparse.ArgumentParser(description="Diagnostics and info")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("health", help="Show health for core services")
    sub.add_parser("doctor", help="Alias for health")
    sub.add_parser("info", help="Alias for health")
    ns, rest = p.parse_known_args(argv)
    if ns.action in ("health", "doctor", "info"):
        return health(rest)
    return 2
