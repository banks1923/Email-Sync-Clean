#!/usr/bin/env python3
"""
Service Orchestrator - Coordinates all services in the correct dependency order.
Ensures efficient pipeline execution without redundant operations.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from entity.main import EntityService
from search_intelligence import get_search_intelligence_service
from shared.simple_db import SimpleDB
from summarization import get_document_summarizer
from utilities.embeddings import get_embedding_service

# Import all services
from utilities.timeline import TimelineService
from utilities.vector_store import get_vector_store


class ServiceOrchestrator:
    """Orchestrates service execution in dependency order.

    Dependency chain:
    1. Database (foundation)
    2. Embeddings & Vector Store (for semantic operations)
    3. Entity Extraction (extracts entities from content)
    4. Timeline (creates temporal relationships)
    5. Summarization (generates summaries)
    6. Knowledge Graph (builds relationships) - currently has issues
    7. Search Intelligence (uses all above)
    8. Legal Intelligence (uses all above) - depends on KG
    """

    def __init__(self, mode: str = "efficient"):
        """Initialize orchestrator.

        Args:
            mode: "efficient" (skip redundant ops) or "full" (run everything)
        """
        self.mode = mode
        self.services = {}
        self.results = {}
        self.start_time = None

    def initialize_services(self) -> Dict[str, bool]:
        """
        Initialize all services in dependency order.
        """
        logger.info("Initializing services in dependency order...")

        initialization_order = [
            ("database", lambda: SimpleDB()),
            ("embeddings", lambda: get_embedding_service()),
            ("vector_store", lambda: get_vector_store("emails")),
            ("entity", lambda: EntityService()),
            ("timeline", lambda: TimelineService()),
            ("summarizer", lambda: get_document_summarizer()),
            ("search", lambda: get_search_intelligence_service()),
        ]

        for service_name, initializer in initialization_order:
            try:
                self.services[service_name] = initializer()
                self.results[f"{service_name}_init"] = True
                logger.debug(f"✓ {service_name} initialized")
            except Exception as e:
                self.results[f"{service_name}_init"] = False
                logger.error(f"✗ {service_name} failed: {e}")

                # Critical services must succeed
                if service_name in ["database", "embeddings"]:
                    raise RuntimeError(f"Critical service {service_name} failed to initialize")

        return self.results

    def process_content(
        self, content_type: str = "email", limit: int = 10, operations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process content through the pipeline.

        Args:
            content_type: Type of content to process
            limit: Maximum items to process
            operations: Specific operations to run (None = all)

        Returns:
            Results from each operation
        """
        self.start_time = time.time()

        # Default to all operations
        if operations is None:
            operations = [
                "entity_extraction",
                "timeline_sync",
                "summarization",
                "vector_sync",
                "search_index",
            ]

        logger.info(f"Processing {content_type} content (limit={limit})")
        logger.info(f"Operations: {', '.join(operations)}")

        # Initialize services if not already done
        if not self.services:
            self.initialize_services()

        # Execute operations in order
        if "entity_extraction" in operations:
            self._run_entity_extraction(limit)

        if "timeline_sync" in operations:
            self._run_timeline_sync(limit)

        if "summarization" in operations:
            self._run_summarization(content_type, limit)

        if "vector_sync" in operations:
            self._run_vector_sync(content_type)

        if "search_index" in operations:
            self._run_search_index()

        # Summary
        elapsed = time.time() - self.start_time
        self.results["total_time"] = elapsed
        self.results["operations_run"] = operations

        logger.info(f"Pipeline complete in {elapsed:.2f}s")
        return self.results

    def _run_entity_extraction(self, limit: int):
        """
        Run entity extraction on emails.
        """
        try:
            logger.debug("Running entity extraction...")
            result = self.services["entity"].process_emails(limit=limit)
            self.results["entity_extraction"] = {
                "success": result.get("success", False),
                "processed": result.get("processed", 0),
            }
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            self.results["entity_extraction"] = {"success": False, "error": str(e)}

    def _run_timeline_sync(self, limit: int):
        """
        Sync content to timeline.
        """
        try:
            logger.debug("Running timeline sync...")
            result = self.services["timeline"].sync_emails_to_timeline(limit=limit)
            self.results["timeline_sync"] = {
                "success": result.get("success", False),
                "synced": result.get("synced_events", 0),
            }
        except Exception as e:
            logger.error(f"Timeline sync failed: {e}")
            self.results["timeline_sync"] = {"success": False, "error": str(e)}

    def _run_summarization(self, content_type: str, limit: int):
        """
        Generate summaries for content.
        """
        try:
            logger.debug("Running summarization...")

            # Get content from database
            db = self.services["database"]
            cursor = db.execute(
                "SELECT id, body FROM content_unified WHERE source_type = ? LIMIT ?",
                (content_type, limit),
            )
            items = cursor.fetchall()

            if items:
                texts = [item["body"] for item in items]
                summaries = self.services["summarizer"].summarize_batch(texts, max_sentences=3)

                self.results["summarization"] = {"success": True, "processed": len(summaries)}
            else:
                self.results["summarization"] = {"success": True, "processed": 0}

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            self.results["summarization"] = {"success": False, "error": str(e)}

    def _run_vector_sync(self, content_type: str):
        """
        Sync vectors for content.
        """
        try:
            logger.debug("Running vector sync...")

            # Use vector maintenance for sync
            from utilities.maintenance.vector_maintenance import VectorMaintenance

            vm = VectorMaintenance()

            # Map content type to collection
            collection_map = {
                "email": "emails",
                "pdf": "pdfs",
                "document": "documents",
                "transcript": "transcriptions",
            }
            collection = collection_map.get(content_type, "emails")

            result = vm.sync_missing_vectors(collection)

            self.results["vector_sync"] = {
                "success": True,
                "missing_found": result.get("missing_found", 0),
                "synced": result.get("synced", 0),
            }

        except Exception as e:
            logger.error(f"Vector sync failed: {e}")
            self.results["vector_sync"] = {"success": False, "error": str(e)}

    def _run_search_index(self):
        """
        Update search indices.
        """
        try:
            logger.debug("Updating search indices...")

            # Search intelligence auto-indexes on search
            # Just verify it's working
            health = self.services["search"].health()

            self.results["search_index"] = {
                "success": health.get("status") == "healthy",
                "status": health.get("status"),
            }

        except Exception as e:
            logger.error(f"Search index update failed: {e}")
            self.results["search_index"] = {"success": False, "error": str(e)}

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status.
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
            "services_initialized": len(self.services),
            "last_run": self.results if self.results else None,
        }

        # Check service health
        for name, service in self.services.items():
            try:
                if hasattr(service, "health"):
                    status[f"{name}_health"] = service.health()
                elif hasattr(service, "get_stats"):
                    status[f"{name}_stats"] = service.get_stats()
            except Exception:
                status[f"{name}_health"] = "unknown"

        return status


def main():
    """
    CLI entry point for orchestrator.
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Service Orchestrator")
    parser.add_argument(
        "--content-type",
        default="email",
        choices=["email", "pdf", "document", "transcript"],
        help="Content type to process",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum items to process")
    parser.add_argument("--operations", nargs="+", help="Specific operations to run")
    parser.add_argument(
        "--mode", default="efficient", choices=["efficient", "full"], help="Processing mode"
    )
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    orchestrator = ServiceOrchestrator(mode=args.mode)

    if args.status:
        orchestrator.initialize_services()
        status = orchestrator.get_pipeline_status()

        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            print("\nPipeline Status")
            print("=" * 40)
            for key, value in status.items():
                print(f"{key}: {value}")
    else:
        results = orchestrator.process_content(
            content_type=args.content_type, limit=args.limit, operations=args.operations
        )

        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print("\nPipeline Results")
            print("=" * 40)
            for key, value in results.items():
                if isinstance(value, dict):
                    print(f"\n{key}:")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"{key}: {value}")


if __name__ == "__main__":
    main()
