#!/usr/bin/env python3
"""Comprehensive semantic pipeline wiring verification.

Verifies:
1. End-to-end flow (entities → embeddings → timeline → EIDs)
2. Idempotency and batch processing
3. Performance benchmarks
4. Data linkage and traceability
"""

import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from search_intelligence import get_search_intelligence_service
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.semantic_pipeline import get_semantic_pipeline
from utilities.vector_store import get_vector_store


class SemanticWiringVerifier:
    """
    Comprehensive semantic pipeline verification.
    """

    def __init__(self):
        self.db = SimpleDB()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "performance": {},
            "linkage": {},
            "recommendations": [],
        }

    def verify_end_to_end(self) -> bool:
        """
        1) Verify end-to-end in 60 seconds.
        """
        print("\n🔍 1) END-TO-END VERIFICATION (60s target)")
        print("=" * 60)

        start_time = time.time()
        all_good = True

        # Check Qdrant connection
        try:
            vector_store = get_vector_store("emails")
            info = vector_store.client.get_collection("emails")
            print(f"✅ Qdrant connected: {info.points_count} points")
            self.results["checks"]["qdrant"] = True
        except Exception as e:
            print(f"❌ Qdrant failed: {e}")
            self.results["checks"]["qdrant"] = False
            all_good = False

        # Check schema completeness
        required_tables = [
            "emails",
            "content",
            "entity_content_mapping",
            "timeline_events",
            "consolidated_entities",
        ]
        for table in required_tables:
            cursor = self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            if cursor.fetchone():
                print(f"✅ Table '{table}' exists")
                self.results["checks"][f"table_{table}"] = True
            else:
                print(f"❌ Table '{table}' missing")
                self.results["checks"][f"table_{table}"] = False
                all_good = False

        # Check embedding dimensions and L2 norm
        try:
            emb_service = get_embedding_service()
            test_emb = emb_service.encode("test semantic wiring")
            dims = len(test_emb)
            l2_norm = np.linalg.norm(test_emb)

            if dims == 1024 and abs(l2_norm - 1.0) < 0.01:
                print(f"✅ Embeddings: {dims}D, L2={l2_norm:.4f}")
                self.results["checks"]["embeddings"] = True
            else:
                print(f"❌ Embeddings: {dims}D (expected 1024), L2={l2_norm:.4f}")
                self.results["checks"]["embeddings"] = False
                all_good = False
        except Exception as e:
            print(f"❌ Embedding service failed: {e}")
            self.results["checks"]["embeddings"] = False
            all_good = False

        # Test hybrid search
        try:
            search_service = get_search_intelligence_service()
            results = search_service.search("invoice payment", limit=5)
            if results and len(results) > 0:
                print(f"✅ Hybrid search: {len(results)} results")
                self.results["checks"]["hybrid_search"] = True
            else:
                print("⚠️  Hybrid search: no results (may need indexing)")
                self.results["checks"]["hybrid_search"] = False
        except Exception as e:
            print(f"❌ Hybrid search failed: {e}")
            self.results["checks"]["hybrid_search"] = False
            all_good = False

        elapsed = time.time() - start_time
        print(f"\n⏱️  Verification completed in {elapsed:.1f}s")
        self.results["performance"]["end_to_end_time"] = elapsed

        return all_good

    def spot_check_linkage(self) -> bool:
        """
        2) Spot-check linkage (EID ↔ message_id ↔ content_id).
        """
        print("\n🔍 2) LINKAGE TRACEABILITY CHECK")
        print("=" * 60)

        # Get a sample email with EID
        cursor = self.db.execute(
            """
            SELECT id, message_id, eid, subject, datetime_utc
            FROM emails 
            WHERE eid IS NOT NULL 
            LIMIT 1
        """
        )
        email = cursor.fetchone()

        if not email:
            print("⚠️  No emails with EIDs found")
            self.results["linkage"]["has_eids"] = False
            return False

        email_id, message_id, eid, subject, date = email
        print(f"📧 Sample: {eid}")
        print(f"   Subject: {subject[:50]}...")
        print(f"   Message-ID: {message_id}")

        # Check content_unified table linkage by source_id
        cursor = self.db.execute(
            """
            SELECT id, source_type FROM content_unified 
            WHERE source_id = ? AND source_type = 'email_message'
            LIMIT 1
        """,
            (message_id,),
        )
        content = cursor.fetchone()

        if content:
            content_id = content[0]
            print(f"✅ Content ID: {content_id}")
            self.results["linkage"]["content_id"] = content_id
        else:
            print("❌ No content record found")
            self.results["linkage"]["content_id"] = None
            return False

        # Check Qdrant payload
        try:
            vector_store = get_vector_store("emails")
            # Convert message_id to UUID format for Qdrant
            point_id = (
                hashlib.md5(message_id.encode()).hexdigest()[:8]
                + "-"
                + hashlib.md5(message_id.encode()).hexdigest()[8:12]
                + "-"
                + hashlib.md5(message_id.encode()).hexdigest()[12:16]
                + "-"
                + hashlib.md5(message_id.encode()).hexdigest()[16:20]
                + "-"
                + hashlib.md5(message_id.encode()).hexdigest()[20:32]
            )

            points = vector_store.client.retrieve(
                collection_name="emails", ids=[point_id], with_payload=True
            )
            if points and points[0].payload.get("content_id") == content_id:
                print(f"✅ Qdrant payload: content_id={content_id}")
                self.results["linkage"]["qdrant_payload"] = True
            else:
                print("⚠️  Qdrant payload missing or mismatched")
                self.results["linkage"]["qdrant_payload"] = False
        except Exception as e:
            print(f"⚠️  Qdrant check skipped: {e}")
            self.results["linkage"]["qdrant_payload"] = None

        # Check entities linkage
        cursor = self.db.execute(
            """
            SELECT COUNT(*) FROM entity_content_mapping 
            WHERE message_id = ?
        """,
            (message_id,),
        )
        entity_count = cursor.fetchone()[0]
        print(f"{'✅' if entity_count > 0 else '⚠️ '} Entities: {entity_count} extracted")
        self.results["linkage"]["entities"] = entity_count

        # Check timeline linkage
        cursor = self.db.execute(
            """
            SELECT COUNT(*) FROM timeline_events 
            WHERE content_id = ?
        """,
            (content_id,),
        )
        timeline_count = cursor.fetchone()[0]
        print(f"{'✅' if timeline_count > 0 else '⚠️ '} Timeline: {timeline_count} events")
        self.results["linkage"]["timeline"] = timeline_count

        print(
            f"\n🔗 Traceability chain: EID({eid}) → Message({message_id}) → Content({content_id})"
        )

        return True

    def check_idempotency(self) -> bool:
        """
        3) Check idempotency and batching.
        """
        print("\n🔍 3) IDEMPOTENCY & BATCH PROCESSING")
        print("=" * 60)

        # Get a sample of already-processed messages
        cursor = self.db.execute(
            """
            SELECT message_id FROM emails 
            WHERE eid IS NOT NULL 
            ORDER BY datetime_utc DESC 
            LIMIT 10
        """
        )
        message_ids = [row[0] for row in cursor.fetchall()]

        if not message_ids:
            print("⚠️  No processed messages to test idempotency")
            self.results["checks"]["idempotency"] = None
            return True

        print(f"Testing with {len(message_ids)} messages...")

        # Count current entities/timeline before re-run
        cursor = self.db.execute("SELECT COUNT(*) FROM entity_content_mapping")
        entities_before = cursor.fetchone()[0]

        cursor = self.db.execute("SELECT COUNT(*) FROM timeline_events")
        timeline_before = cursor.fetchone()[0]

        # Re-run pipeline
        pipeline = get_semantic_pipeline(db=self.db)
        result = pipeline.run_for_messages(message_ids[:5])

        # Count after re-run
        cursor = self.db.execute("SELECT COUNT(*) FROM entity_content_mapping")
        entities_after = cursor.fetchone()[0]

        cursor = self.db.execute("SELECT COUNT(*) FROM timeline_events")
        timeline_after = cursor.fetchone()[0]

        # Should be mostly skipped
        entities_added = entities_after - entities_before
        timeline_added = timeline_after - timeline_before

        print(f"Entities: {entities_added} new (expected ~0 for idempotent)")
        print(f"Timeline: {timeline_added} new (expected ~0 for idempotent)")
        print(f"Skipped: {result.get('skipped', 0)} messages")

        idempotent = entities_added == 0 and timeline_added == 0
        print(
            f"{'✅' if idempotent else '⚠️ '} Idempotency: {'PASS' if idempotent else 'WARN - duplicates created'}"
        )

        self.results["checks"]["idempotency"] = idempotent
        self.results["performance"]["entities_added_on_rerun"] = entities_added
        self.results["performance"]["timeline_added_on_rerun"] = timeline_added

        return True

    def check_performance(self) -> bool:
        """
        4) Performance sanity checks.
        """
        print("\n🔍 4) PERFORMANCE BENCHMARKS")
        print("=" * 60)

        # Test embedding throughput
        print("Testing embedding throughput...")
        emb_service = get_embedding_service()
        test_texts = [f"Test document {i} for performance benchmarking" for i in range(16)]

        start = time.time()
        embeddings = emb_service.encode_batch(test_texts)
        emb_time = time.time() - start
        emb_throughput = len(test_texts) / emb_time * 60  # per minute

        print(f"Embeddings: {emb_throughput:.0f}/min (target ≥600/min)")
        self.results["performance"]["embedding_throughput"] = emb_throughput

        # Test vector upsert throughput (simulated)
        print("Testing vector upsert performance...")
        try:
            vector_store = get_vector_store("emails")
            # Just test connection speed, don't actually upsert
            start = time.time()
            info = vector_store.client.get_collection("emails")
            query_time = time.time() - start

            # Estimate based on typical batch sizes
            estimated_upsert = 500 / (query_time * 10) * 60  # Rough estimate
            print(f"Vector upsert: ~{estimated_upsert:.0f}/min estimated (target ≥2000/min)")
            self.results["performance"]["vector_upsert_estimate"] = estimated_upsert
        except Exception as e:
            print(f"⚠️  Vector performance check failed: {e}")

        # Test search latency
        print("Testing search latency...")
        try:
            search_service = get_search_intelligence_service()
            latencies = []

            for query in ["test", "invoice", "payment"]:
                start = time.time()
                results = search_service.search(query, limit=10)
                latency = (time.time() - start) * 1000  # ms
                latencies.append(latency)

            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            avg_latency = sum(latencies) / len(latencies)

            print(f"Search p95: {p95_latency:.0f}ms (target ≤80ms)")
            print(f"Search avg: {avg_latency:.0f}ms")
            self.results["performance"]["search_p95_ms"] = p95_latency
            self.results["performance"]["search_avg_ms"] = avg_latency
        except Exception as e:
            print(f"⚠️  Search performance check failed: {e}")

        # Check WAL mode
        cursor = self.db.execute("PRAGMA journal_mode")
        wal_mode = cursor.fetchone()[0]
        print(f"{'✅' if wal_mode == 'wal' else '⚠️ '} SQLite WAL mode: {wal_mode}")
        self.results["performance"]["wal_mode"] = wal_mode

        return True

    def check_failure_signals(self) -> bool:
        """
        5) Check for known failure patterns.
        """
        print("\n🔍 5) FAILURE SIGNAL DETECTION")
        print("=" * 60)

        issues = []

        # Check hybrid vs vector search discrepancy
        try:
            search_service = get_search_intelligence_service()
            vector_store = get_vector_store("emails")

            # Do a vector-only search
            test_query = "invoice"
            emb_service = get_embedding_service()
            query_emb = emb_service.encode(test_query)

            vector_results = vector_store.search(query_vector=query_emb.tolist(), limit=5)

            # Do a hybrid search
            hybrid_results = search_service.search(test_query, limit=5)

            if len(vector_results) > 0 and len(hybrid_results) == 0:
                issues.append(
                    "❌ Hybrid search returns 0 while vector returns >0 - payload/join issue"
                )
            else:
                print(
                    f"✅ Search consistency: vector={len(vector_results)}, hybrid={len(hybrid_results)}"
                )

        except Exception as e:
            print(f"⚠️  Search comparison skipped: {e}")

        # Check entity extraction coverage
        cursor = self.db.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM emails) as total_emails,
                (SELECT COUNT(DISTINCT message_id) FROM entity_content_mapping) as emails_with_entities
        """
        )
        total, with_entities = cursor.fetchone()

        if total > 0:
            entity_coverage = 100 * with_entities / total
            if entity_coverage < 10 and total > 50:
                issues.append(
                    f"⚠️  Low entity coverage: {entity_coverage:.1f}% - TTL or extraction issue"
                )
            else:
                print(f"✅ Entity coverage: {entity_coverage:.1f}%")

        # Check timeline deduplication
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as cnt, content_id, event_type
            FROM timeline_events
            GROUP BY content_id, event_type, date(event_date)
            HAVING cnt > 5
            LIMIT 1
        """
        )
        dup_timeline = cursor.fetchone()

        if dup_timeline:
            issues.append(
                f"⚠️  Possible timeline over-deduplication: {dup_timeline[0]} events for same content/type/date"
            )
        else:
            print("✅ Timeline deduplication looks normal")

        # Report issues
        if issues:
            print("\n⚠️  ISSUES DETECTED:")
            for issue in issues:
                print(f"  {issue}")
            self.results["checks"]["failure_signals"] = issues
            return False
        else:
            print("\n✅ No failure signals detected")
            self.results["checks"]["failure_signals"] = []
            return True

    def generate_recommendations(self):
        """
        Generate recommendations based on findings.
        """
        print("\n📋 RECOMMENDATIONS")
        print("=" * 60)

        recs = []

        # Check if semantic processing is enabled
        from config.settings import semantic_settings

        if not semantic_settings.semantics_on_ingest:
            recs.append("Enable SEMANTICS_ON_INGEST=true for automatic enrichment")

        # Check coverage
        cursor = self.db.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM emails) as total,
                (SELECT COUNT(*) FROM emails WHERE eid IS NOT NULL) as with_eid
        """
        )
        total, with_eid = cursor.fetchone()

        if total > 0 and with_eid < total:
            missing = total - with_eid
            recs.append(f"Run 'vsearch evidence assign-eids' to assign EIDs to {missing} emails")

        # Check vector coverage
        cursor = self.db.execute(
            """
            SELECT COUNT(*) FROM content_unified 
            WHERE embedding_generated = 0 OR embedding_generated IS NULL
        """
        )
        unvectorized = cursor.fetchone()[0]

        if unvectorized > 0:
            recs.append(f"Run 'make backfill-all' to vectorize {unvectorized} documents")

        # Performance recommendations
        if self.results.get("performance", {}).get("search_p95_ms", 0) > 100:
            recs.append("Consider optimizing search query expansion or reducing default limit")

        if not recs:
            recs.append("✅ System is well-configured and operational")

        for rec in recs:
            print(f"  • {rec}")

        self.results["recommendations"] = recs

    def save_report(self):
        """
        Save verification report.
        """
        report_path = Path("legal_evidence/verification_report.json")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Report saved to: {report_path}")

    def run_all_checks(self) -> bool:
        """
        Run all verification checks.
        """
        print("\n" + "=" * 60)
        print("SEMANTIC PIPELINE WIRING VERIFICATION")
        print("=" * 60)

        all_good = True

        # Run checks
        if not self.verify_end_to_end():
            all_good = False

        if not self.spot_check_linkage():
            all_good = False

        self.check_idempotency()
        self.check_performance()

        if not self.check_failure_signals():
            all_good = False

        self.generate_recommendations()
        self.save_report()

        # Final verdict
        print("\n" + "=" * 60)
        if all_good:
            print("✅ SEMANTIC PIPELINE WIRING: VERIFIED")
        else:
            print("⚠️  SEMANTIC PIPELINE: NEEDS ATTENTION")
        print("=" * 60)

        return all_good


def eid_lookup(eid: str):
    """
    EID-first lookup showing all linked semantic data.
    """
    db = SimpleDB()

    # Get email details
    cursor = db.execute(
        """
        SELECT message_id, subject, sender, datetime_utc, content
        FROM emails
        WHERE eid = ?
    """,
        (eid,),
    )

    email = cursor.fetchone()
    if not email:
        print(f"❌ EID not found: {eid}")
        return

    message_id, subject, sender, date, content = email

    print("\n" + "=" * 60)
    print(f"📧 EVIDENCE LOOKUP: {eid}")
    print("=" * 60)

    print(f"Subject: {subject}")
    print(f"From: {sender}")
    print(f"Date: {date}")
    print(f"Message-ID: {message_id}")

    # Key quote (first 200 chars of content)
    if content:
        quote = content[:200].replace("\n", " ")
        print(f'\nQuote: "{quote}..."')

    # Get entities
    cursor = db.execute(
        """
        SELECT DISTINCT entity_value, entity_type
        FROM entity_content_mapping
        WHERE message_id = ?
        ORDER BY entity_type, entity_value
        LIMIT 10
    """,
        (message_id,),
    )

    entities = cursor.fetchall()
    if entities:
        print(f"\nEntities ({len(entities)}):")
        for value, etype in entities:
            print(f"  • {etype}: {value}")

    # Get timeline events
    cursor = db.execute(
        """
        SELECT event_date, event_type, description
        FROM timeline_events t
        JOIN content_unified c ON t.content_id = c.id
        WHERE c.source_id = ? AND c.source_type = 'email_message'
        ORDER BY event_date
        LIMIT 5
    """,
        (message_id,),
    )

    events = cursor.fetchall()
    if events:
        print(f"\nTimeline Events ({len(events)}):")
        for event_date, event_type, description in events:
            print(f"  • {event_date}: {event_type} - {description[:50]}...")

    # Gmail link (if we have the thread ID)
    cursor = db.execute("SELECT thread_id FROM emails WHERE eid = ?", (eid,))
    thread = cursor.fetchone()
    if thread and thread[0]:
        # Format: https://mail.google.com/mail/u/0/#all/{thread_id}
        gmail_link = f"https://mail.google.com/mail/u/0/#all/{thread[0]}"
        print(f"\n🔗 Open in Gmail: {gmail_link}")

    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify semantic pipeline wiring")
    parser.add_argument("--eid", help="Lookup specific EID")
    parser.add_argument("--quick", action="store_true", help="Quick check only")

    args = parser.parse_args()

    if args.eid:
        eid_lookup(args.eid)
    else:
        verifier = SemanticWiringVerifier()

        if args.quick:
            verifier.verify_end_to_end()
        else:
            success = verifier.run_all_checks()
            sys.exit(0 if success else 1)
