"""
Deduplication utilities for exact and near-duplicate detection.
"""

from .near_duplicate_detector import (
    LSHIndex,
    MinHasher,
    NearDuplicateDetector,
    get_duplicate_detector,
)

__all__ = [
    'NearDuplicateDetector',
    'get_duplicate_detector',
    'MinHasher',
    'LSHIndex'
]