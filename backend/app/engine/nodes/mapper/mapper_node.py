import logging
from typing import Dict, Any

from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.mapper.mapper_processor import MapperProcessor
from app.engine.nodes.mapper.mapper_middleware import MapperLoggingMiddleware

logger = logging.getLogger(__name__)


class MapperNode(BaseNode):
    """
    A node that transforms and maps JSON data structures.

    This node can:
    - Filter fields from incoming data (select only specific fields)
    - Rename/remap field names
    - Transform/reformat data structures
    - Access nested fields using JMESPath expressions
    - Process arrays with filtering and mapping

    Example config:
    {
        "mode": "object",
        "mappings": [
            {"source": "user.name", "target": "userName"},
            {"source": "user.email", "target": "email"},
            {"source": "timestamp", "target": "createdAt", "transform": "string"}
        ]
    }

    For array processing:
    {
        "mode": "array",
        "array_settings": {
            "source_path": "data.items",
            "filter": {">": [{"var": "price"}, 10]},
            "item_mappings": [
                {"source": "name", "target": "productName"},
                {"source": "price", "target": "cost"}
            ]
        }
    }
    """

    def __init__(self, node_id: str, config: Dict[str, Any]):
        """
        Initialize the mapper node.

        Args:
            node_id: Unique identifier for the node
            config: Configuration containing mappings and options
        """
        super().__init__(node_id, "mapper_node", None, config)

        # Add the mapper processor
        mapper_processor = MapperProcessor(config)
        self.add_processor(mapper_processor)

        # Add logging middleware
        self.add_middleware(MapperLoggingMiddleware())
