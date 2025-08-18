"""
Deduplication utilities for exact and near-duplicate detection
"""

from .near_duplicate_detector import (
    NearDuplicateDetector,
    get_duplicate_detector,
    MinHasher,
    LSHIndex
)

__all__ = [
    'NearDuplicateDetector',
    'get_duplicate_detector',
    'MinHasher',
    'LSHIndex'
]