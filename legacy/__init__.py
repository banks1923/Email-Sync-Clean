"""
Legacy module trap to prevent usage of deprecated tables.
This module raises an error immediately when imported.
"""

raise RuntimeError(
    "FATAL: Legacy 'emails' table/module is forbidden!\n"
    "Use content_unified + individual_messages instead.\n"
    "See scripts/migrate_legacy_to_v2_final.py for migration."
)