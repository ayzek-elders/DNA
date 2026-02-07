import logging
from typing import Optional

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_middleware import IMiddleware

logger = logging.getLogger(__name__)


class MapperLoggingMiddleware(IMiddleware):
    """Middleware for logging mapper operations."""

    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Log incoming data before mapping."""
        data_type = type(event.data).__name__
        data_preview = str(event.data)[:100] + "..." if len(str(event.data)) > 100 else str(event.data)

        logger.info(f"Mapper Node {node_id}: Processing {data_type} - {data_preview}")
        return event

    async def after_process(
        self,
        event: GraphEvent,
        result: Optional[GraphEvent],
        node_id: str
    ) -> Optional[GraphEvent]:
        """Log mapping result."""
        if result:
            if result.type == EventType.ERROR:
                error = result.data.get("error", "Unknown error")
                logger.error(f"Mapper Node {node_id}: Mapping failed - {error}")
            else:
                status = result.metadata.get("status", "completed")
                mappings = result.metadata.get("mappings_applied", 0)
                logger.info(f"Mapper Node {node_id}: Mapping {status} - {mappings} mappings applied")

        return result


class MapperValidationMiddleware(IMiddleware):
    """Middleware for validating mapper input data."""

    def __init__(self, allowed_types: list = None):
        """
        Args:
            allowed_types: List of allowed data types (e.g., ["dict", "list"])
        """
        self._allowed_types = allowed_types or ["dict", "list"]

    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Validate input data type."""
        data_type = type(event.data).__name__

        if data_type not in self._allowed_types:
            logger.warning(f"Mapper Node {node_id}: Unexpected data type '{data_type}'")
            return GraphEvent(
                type=EventType.ERROR,
                data={
                    "error": f"Invalid input type: expected one of {self._allowed_types}, got {data_type}",
                    "original_data": event.data
                },
                source_id=event.source_id,
                metadata={"status": "validation_error", **event.metadata}
            )

        return event

    async def after_process(
        self,
        event: GraphEvent,
        result: Optional[GraphEvent],
        node_id: str
    ) -> Optional[GraphEvent]:
        """No post-processing needed."""
        return result
