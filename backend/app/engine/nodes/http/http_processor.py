import aiohttp
import asyncio
from typing import Any, Dict

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_processor import IProcessor


class HTTPGetRequestProcessor(IProcessor):
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if event.data["url"] is None:
            return None
        
        async with aiohttp.ClientSession() as session:
            task = self._get_request(session, event.data["url"])
            result = await asyncio.gather(task)

            response_event = GraphEvent(
                type=EventType.COMPUTATION_RESULT,
                data=result,
                source_id=context["node_id"],
                metadata=event.metadata
            )

            return response_event
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE
    
    async def _get_request(self,session: aiohttp.ClientSession, url: str) -> Any:
        async with session.get(url) as response:
            result = await response.json()
            return result