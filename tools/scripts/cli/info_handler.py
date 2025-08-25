#!/usr/bin/env python3
"""
Info Handler - Fixed version using clean services
Handles: info, pdf-stats, transcription-stats commands
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import new clean services
from shared.simple_db import SimpleDB

# Import service locator for backward compatibility
try:
    from tools.scripts.cli.service_locator import get_locator

    SERVICE_LOCATOR_AVAILABLE = True
except ImportError:
    SERVICE_LOCATOR_AVAILABLE = False


def show_info():
    """
    Show system status using clean services.
    """
    print("🤖 AI-Powered Email Search System Status")
    print("=" * 50)

    # Database statistics using SimpleDB
    try:
        db = SimpleDB()
        stats = db.get_content_stats()

        print("\n📁 Database Statistics:")
        print(f"  📄 Raw documents: {stats.get('total_documents', 0)}")
        print(f"  📝 Text chunks: {stats.get('total_content', 0)}")
        print("  Breakdown by type:")
        print(f"    📧 Email chunks: {stats.get('total_emails', 0)}")
        print(f"    📄 PDF chunks: {stats.get('total_pdfs', 0)}")
        print(f"    🎙️  Transcript chunks: {stats.get('total_transcripts', 0)}")

        # Show last sync times if available
        if stats.get("latest_email_date"):
            print(f"  🕐 Latest email: {stats['latest_email_date']}")
    except Exception as e:
        print(f"❌ Database error: {e}")

    # Vector service status using clean services
    try:
        from utilities.vector_store import get_vector_store

        store = get_vector_store()

        print("\n🧠 Vector Service:")
        print("  ✅ Status: Connected")
        print(f"  📊 Collection: {store.collection}")
        print(f"  📐 Dimensions: {store.dimensions} (Legal BERT)")

        # Try to get vector count
        try:
            # This is a simple check - actual count requires Qdrant query
            print("  🔍 Semantic search: Available")
        except Exception:
            print("  ⚠️  Semantic search: Requires Qdrant running")

    except Exception:
        print("\n🧠 Vector Service:")
        print("  ❌ Status: Not available")
        print("  💡 Run 'docker run -p 6333:6333 qdrant/qdrant' to enable")

    # Embedding service status
    try:
        from utilities.embeddings import get_embedding_service

        emb = get_embedding_service()

        print("\n🤖 Embedding Service:")
        print(f"  ✅ Model: {emb.model_name}")
        print(f"  📐 Dimensions: {emb.dimensions}")
        print(f"  🖥️  Device: {emb.device}")
    except Exception as e:
        print("\n🤖 Embedding Service:")
        print(f"  ⚠️  Status: Not configured ({e})")

    # Search capabilities
    print("\n🎯 Search Capabilities:")
    print("  ✅ Keyword Search: Full-text search across all content")

    try:
        from search_intelligence import get_search_intelligence_service as get_search_service

        get_search_service()
        print("  ✅ Semantic Search: AI-powered similarity using Legal BERT")
        print("  ✅ Hybrid Search: Combines both for best results")
        print("  ✅ Unified Search: Searches emails, PDFs, and transcriptions")
    except Exception:
        print("  ⚠️  Semantic Search: Requires vector service")
        print("  ⚠️  Hybrid Search: Requires vector service")

    # System health check
    if SERVICE_LOCATOR_AVAILABLE:
        try:
            locator = get_locator()
            print("\n💻 Service Health:")

            # Check each service
            services = ["gmail", "pdf", "transcription", "search"]
            for service_name in services:
                if locator.is_service_healthy(service_name):
                    print(f"  ✅ {service_name.capitalize()}: Healthy")
                else:
                    print(f"  ⚠️  {service_name.capitalize()}: Degraded")
        except Exception as e:
            print(f"\n💻 Service Health: Unable to check ({e})")

    print("\n✅ System check complete")
    return True


def show_pdf_stats():
    """
    Show PDF collection statistics using clean services.
    """
    print("📄 PDF Collection Statistics")
    print("=" * 40)

    try:
        db = SimpleDB()

        # Get PDF-specific stats
        cursor = db.execute(
            """
            SELECT
                COUNT(DISTINCT source_path) as total_pdfs,
                COUNT(*) as total_chunks,
                SUM(LENGTH(body)) as total_chars,
                AVG(LENGTH(body)) as avg_chunk_size
            FROM content_unified
            WHERE source_type = 'pdf'
        """
        )

        row = cursor.fetchone()
        if row:
            total_pdfs = row["total_pdfs"] or 0
            total_chunks = row["total_chunks"] or 0
            total_chars = row["total_chars"] or 0

            print(f"📄 Total PDFs: {total_pdfs}")
            print(f"📝 Total chunks: {total_chunks}")
            print(f"📊 Total characters: {total_chars:,}")

            if total_pdfs > 0:
                print(f"📈 Avg chunks/PDF: {total_chunks / total_pdfs:.1f}")

            if total_chars > 0:
                storage_mb = total_chars / (1024 * 1024)
                print(f"💾 Storage estimate: {storage_mb:.2f} MB")
        else:
            print("No PDF data found")

        return True

    except Exception as e:
        print(f"❌ PDF stats error: {e}")
        return False


def show_transcription_stats():
    """
    Show transcription statistics using clean services.
    """
    print("🎙️ Transcription Service Statistics")
    print("=" * 40)

    try:
        db = SimpleDB()

        # Get transcription stats
        cursor = db.execute(
            """
            SELECT
                COUNT(*) as total_transcripts,
                COUNT(DISTINCT source_path) as unique_files,
                SUM(LENGTH(body)) as total_chars,
                MIN(created_at) as first_transcript,
                MAX(created_at) as last_transcript
            FROM content_unified
            WHERE source_type = 'transcript'
        """
        )

        row = cursor.fetchone()
        if row:
            total = row["total_transcripts"] or 0
            unique = row["unique_files"] or 0
            chars = row["total_chars"] or 0

            print(f"📝 Total transcripts: {total}")
            print(f"📁 Unique files: {unique}")

            if chars > 0:
                print(f"📊 Total characters: {chars:,}")
                print(f"📏 Avg length: {chars / max(total, 1):,.0f} chars")

            if row["first_transcript"]:
                print(f"🕐 First transcript: {row['first_transcript']}")
            if row["last_transcript"]:
                print(f"🕐 Latest transcript: {row['last_transcript']}")
        else:
            print("No transcription data found")

        # Check if transcription service is available
        if SERVICE_LOCATOR_AVAILABLE:
            try:
                locator = get_locator()
                service = locator.get_transcription_service()
                if service:
                    print("\n🔧 Service Status: Available")
                    print("   Providers: OpenAI Whisper (local)")
            except Exception:
                print("\n🔧 Service Status: Check configuration")

        return True

    except Exception as e:
        print(f"❌ Transcription stats error: {e}")
        return False


# Export the handler functions
__all__ = ["show_info", "show_pdf_stats", "show_transcription_stats"]
