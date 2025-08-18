"""Document Processing Pipeline Module

Provides orchestration for document lifecycle management through
structured stages: raw → staged → processed → quarantine/export
"""

from loguru import logger

# Logger is now imported globally from loguru

# Singleton instance
_pipeline_orchestrator = None


def get_pipeline_orchestrator(data_dir: str = "data"):
    """Get or create singleton PipelineOrchestrator instance.

    Args:
        data_dir: Root directory for pipeline data (default: "data")

    Returns:
        PipelineOrchestrator: Singleton orchestrator instance
    """
    global _pipeline_orchestrator

    if _pipeline_orchestrator is None:
        from infrastructure.pipelines.orchestrator import PipelineOrchestrator

        _pipeline_orchestrator = PipelineOrchestrator(data_dir)
        logger.info(f"Initialized PipelineOrchestrator with data_dir: {data_dir}")

    return _pipeline_orchestrator


def reset_pipeline_orchestrator() -> None:
    """Reset the singleton instance (mainly for testing)."""
    global _pipeline_orchestrator
    _pipeline_orchestrator = None
    logger.debug("Pipeline orchestrator singleton reset")


# Export main components
__all__ = ["get_pipeline_orchestrator", "reset_pipeline_orchestrator"]
