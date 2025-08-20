"""
Adapter for EmailThreadProcessor parameter mismatches.

PROBLEM: gmail/main.py passes save_to_db=True but EmailThreadProcessor doesn't accept it.
SOLUTION: This adapter strips the parameter until services are aligned.
REMOVAL DATE: 2025-09-01
"""

from typing import Any
from loguru import logger


class EmailThreadAdapter:
    """Adapts EmailThreadProcessor calls to handle parameter mismatches."""
    
    def __init__(self, processor):
        """Wrap the actual EmailThreadProcessor."""
        self.processor = processor
        logger.warning("EmailThreadAdapter in use - remove by 2025-09-01")
    
    def process_thread(
        self,
        thread_id: str,
        include_metadata: bool = True,
        save_to_db: bool = True,  # Accept but ignore
        **kwargs  # Catch any other mismatched params
    ) -> dict[str, Any]:
        """
        Forward to real processor, stripping mismatched params.
        
        Args:
            thread_id: Gmail thread ID
            include_metadata: Whether to include YAML frontmatter
            save_to_db: IGNORED - processor doesn't support this
            **kwargs: Any other unexpected params (logged and ignored)
        """
        if save_to_db:
            logger.debug(f"save_to_db=True passed but ignored for thread {thread_id}")
        
        if kwargs:
            logger.warning(f"Unexpected params ignored: {kwargs.keys()}")
        
        # Call real processor with only supported params
        return self.processor.process_thread(
            thread_id=thread_id,
            include_metadata=include_metadata
        )
    
    def __getattr__(self, name):
        """Forward all other methods directly to the processor."""
        return getattr(self.processor, name)