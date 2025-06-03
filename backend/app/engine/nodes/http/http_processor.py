import logging
import aiohttp
import asyncio
from typing import Any, Dict

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)

class HTTPProcessor(IProcessor):
    """
    Base class for HTTP request processors.

    Handles common HTTP request logic such as timeout, retries, and headers.
    """
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1
    
    def __init__(self, config: Dict[str, Any]):
        self.timeout = config.get("timeout", self.DEFAULT_TIMEOUT)
        self.retries = config.get("retries", self.DEFAULT_RETRIES)
        self.retry_delay = config.get("retry_delay", self.DEFAULT_RETRY_DELAY)
        self.headers = config.get("headers", {})
        self.client_timeout = aiohttp.ClientTimeout(total=self.timeout)
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
    
    async def _convert_response(self, response: aiohttp.ClientResponse) -> Any:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return await response.json()
        elif 'text/' in content_type:
            return await response.text()
        return await response.read()

    async def _handle_request_exceptions(self, attempt: int, event: GraphEvent, context: Dict[str, Any], error: Exception) -> GraphEvent | None:
        if isinstance(error, asyncio.TimeoutError):
            logger.warning(f"Request timeout on attempt {attempt + 1}/{self.retries}")
            if attempt == self.retries - 1:
                return self.create_error_event("Request timeout", event, context["node_id"])
        
        elif isinstance(error, aiohttp.ClientError):
            logger.error(f"HTTP request error on attempt {attempt + 1}/{self.retries}: {str(error)}")
            if attempt == self.retries - 1:
                return self.create_error_event(f"HTTP request failed: {str(error)}", event, context["node_id"])
        
        else:
            logger.error(f"Unexpected error on attempt {attempt + 1}/{self.retries}: {str(error)}")
            return self.create_error_event(f"Unexpected error: {str(error)}", event, context["node_id"])
        
        return None
    
    def _create_response_event(self, response_data: Any, status: int, event: GraphEvent, node_id: str, attempt: int) -> GraphEvent:
        return GraphEvent(
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

class HTTPGetRequestProcessor(HTTPProcessor):
    """
    Processor for handling HTTP GET requests.

    Inherits from HTTPProcessor and implements the process method for GET requests.
    """
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if not self._validate_request_data(event.data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event

        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.client_timeout) as session:
                    response_data, status = await self._get_request(session, event.data["url"], self.headers)
                    response_event = self._create_response_event(response_data, status, event, context["node_id"], attempt)
                    return response_event
            except Exception as e:
                error_event = await self._handle_request_exceptions(attempt, event, context, e)
                if error_event:
                    return error_event
            
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE 
    
    async def _get_request(self, session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> tuple[Any, int]:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            status = response.status
            return await self._convert_response(response), status

class HTTPPostRequestProcessor(HTTPProcessor):
    """
    Processor for handling HTTP POST requests.

    Inherits from HTTPProcessor and implements the process method for POST requests.
    """
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if not self._validate_request_data(event.data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event

        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.client_timeout) as session:
                    response_data, status = await self._post_request(session, event.data["url"], self.headers, event.data["data"])
                    response_event = self._create_response_event(response_data, status, event, context["node_id"], attempt)
                    return response_event
            except Exception as e:
                error_event = await self._handle_request_exceptions(attempt, event, context, e)
                if error_event:
                    return error_event
            
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE 
    
    async def _post_request(self, session: aiohttp.ClientSession, url: str, headers: Dict[str, str], data: Any) -> tuple[Any, int]:
        async with session.post(url, headers=headers, json=data) as response:
            response.raise_for_status()
            status = response.status
            return await self._convert_response(response), status

class HTTPPutRequestProcessor(HTTPProcessor):
    """
    Processor for handling HTTP PUT requests.

    Inherits from HTTPProcessor and implements the process method for PUT requests.
    """
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if not self._validate_request_data(event.data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event
        
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.client_timeout) as session:
                    response_data, status = await self._put_request(session, event.data["url"], self.headers, event.data["data"])
                    response_event = self._create_response_event(response_data, status, event, context["node_id"], attempt)
                    return response_event
            except Exception as e:
                error_event = await self._handle_request_exceptions(attempt, event, context, e)
                if error_event:
                    return error_event
            
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE
    
    async def _put_request(self, session: aiohttp.ClientSession, url: str, headers: Dict[str, str], data: Any) -> tuple[Any, int]:
        async with session.put(url, headers=headers, json=data) as response:
            response.raise_for_status()
            status = response.status
            return await self._convert_response(response), status

class HTTPDeleteRequestProcessor(HTTPProcessor):
    """
    Processor for handling HTTP DELETE requests.

    Inherits from HTTPProcessor and implements the process method for DELETE requests.
    """
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if not self._validate_request_data(event.data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event
        
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.client_timeout) as session:
                    response_data, status = await self._delete_request(session, event.data["url"], self.headers)
                    response_event = self._create_response_event(response_data, status, event, context["node_id"], attempt)
                    return response_event
            except Exception as e:
                error_event = await self._handle_request_exceptions(attempt, event, context, e)
                if error_event:
                    return error_event
            
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE
    
    async def _delete_request(self, session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> tuple[Any, int]:
        async with session.delete(url, headers=headers) as response:
            response.raise_for_status()
            status = response.status
            return await self._convert_response(response), status


class HTTPPatchRequestProcessor(HTTPProcessor):
    """
    Processor for handling HTTP PATCH requests.

    Inherits from HTTPProcessor and implements the process method for PATCH requests.
    """
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if not self._validate_request_data(event.data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event
        
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.client_timeout) as session:
                    response_data, status = await self._patch_request(session, event.data["url"], self.headers, event.data["data"])
                    response_event = self._create_response_event(response_data, status, event, context["node_id"], attempt)
                    return response_event
            except Exception as e:
                error_event = await self._handle_request_exceptions(attempt, event, context, e)
                if error_event:
                    return error_event  
            
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)
    
    def can_handle(self, event):
        return event.type == EventType.DATA_CHANGE
    
    async def _patch_request(self, session: aiohttp.ClientSession, url: str, headers: Dict[str, str], data: Any) -> tuple[Any, int]:
        async with session.patch(url, headers=headers, json=data) as response:
            response.raise_for_status()
            status = response.status
            return await self._convert_response(response), status