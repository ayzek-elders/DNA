from typing import Any, Dict, Optional
from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.http.http_processor import HTTPGetRequestProcessor
from app.engine.interfaces.i_middleware import IMiddleware
from app.engine.graph.graph_event import GraphEvent
import logging

logger = logging.getLogger(__name__)

class HTTPRequestLoggingMiddleware(IMiddleware):
    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        if event.data and isinstance(event.data, dict) and "url" in event.data:
            logger.info(f"HTTP Request starting - Node {node_id}: GET {event.data['url']}")
        return event
    
    async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
        if result:
            logger.info(f"HTTP Request completed - Node {node_id}: Status={result.metadata.get('status', 'unknown')}")
        return result

class HTTPGetRequestNode(BaseNode):
    def __init__(
        self,
        node_id: str,
        node_type: str = "HTTP_GET_REQUEST_NODE",
        initial_data: Any = None,
        config: Dict[str, Any] = None
    ):
        default_config = {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1,
            "headers": {
                "User-Agent": "DNA-Engine/1.0",
                "Accept": "application/json, text/plain, */*"
            }
        }
        
        merged_config = {**default_config, **(config or {})}
        
        super().__init__(node_id, node_type, initial_data, merged_config)
        
        self.add_processor(HTTPGetRequestProcessor())
        self.add_middleware(HTTPRequestLoggingMiddleware())