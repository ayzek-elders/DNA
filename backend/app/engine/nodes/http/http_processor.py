import logging
import aiohttp
import asyncio
from typing import Any, Dict

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)

class HTTPGetRequestProcessor(IProcessor):
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1
    
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if not self._validate_request_data(event.data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event

        config = context.get("config", {})
        timeout = config.get("timeout", self.DEFAULT_TIMEOUT)
        max_retries = config.get("max_retries", self.DEFAULT_RETRIES)
        retry_delay = config.get("retry_delay", self.DEFAULT_RETRY_DELAY)
        headers = config.get("headers", {})

        client_timeout = aiohttp.ClientTimeout(total=timeout)
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=client_timeout) as session:
                    response_data, status = await self._get_request(session, event.data["url"], headers)
                    response_event = GraphEvent(
                        type=EventType.COMPUTATION_RESULT,
                        data={
                            "content": response_data,
                            "status": status
                        },
                        metadata={
                            "status": status,
                            "attempt": attempt + 1,
                            **event.metadata
                        },
                        source_id=event.source_id
                    )
                    return response_event
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    return self.create_error_event("Request timeout", event, context["node_id"])
            
            except aiohttp.ClientError as e:
                logger.error(f"HTTP request error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    return self.create_error_event(f"HTTP request failed: {str(e)}", event, context["node_id"])
            
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                return self.create_error_event(f"Unexpected error: {str(e)}", event, context["node_id"])
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE
    
    def _validate_request_data(self, data: Any) -> bool:
        return (
            isinstance(data, dict) and
            "url" in data and
            isinstance(data["url"], str) and
            data["url"].startswith(("http://", "https://"))
        )  
    def create_error_event(self, error_message: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        return GraphEvent(
            type=EventType.ERROR,
            data={
                "error": error_message,
                "original_request": original_event.data
            },
            source_id=node_id,
            metadata={
                "status": "error",
                **original_event.metadata
            }
        )
    async def _get_request(self, session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> tuple[Any, int]:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            status = response.status
            
            if 'application/json' in content_type:
                content = await response.json()
            elif 'text/' in content_type:
                content = await response.text()
            else:
                content = await response.read()
                
            return content, status