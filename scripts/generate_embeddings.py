#!/usr/bin/env python3
"""DEPRECATED: Legacy embeddings generator.

This script is deprecated in favor of the v2 pipeline:
  tools/scripts/vsearch chunk-ingest --embeddings

Why deprecated:
- Writes to legacy collection (legal_documents) with mismatched schema.
- The active system uses chunk-based embeddings in 'vectors_v2' with quality filtering
  and aggregation. Use the v2 CLI instead.
"""

import sys

DEPRECATION_MESSAGE = (
    "This script is deprecated. Use: tools/scripts/vsearch chunk-ingest --embeddings\n"
    "It writes to the legacy 'legal_documents' collection and is no longer supported."
)

def main() -> int:
    print(f"❌ {DEPRECATION_MESSAGE}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
