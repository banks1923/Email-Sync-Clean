"""Entity Extractors Module.

Provides abstraction layer for different entity extraction providers.
Follows the same provider pattern as vector_service/providers/.
"""

from .base_extractor import BaseExtractor
from .extractor_factory import ExtractorFactory
from .spacy_extractor import SpacyExtractor

__all__ = ["BaseExtractor", "ExtractorFactory", "SpacyExtractor"]
