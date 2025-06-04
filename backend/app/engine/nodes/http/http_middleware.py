from app.engine.interfaces.i_middleware import IMiddleware
from app.engine.graph.graph_event import GraphEvent
from typing import Optional
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