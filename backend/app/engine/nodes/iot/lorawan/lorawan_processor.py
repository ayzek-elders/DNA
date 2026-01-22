import logging
import aiohttp
import asyncio
import base64
import re
from typing import Any, Dict

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)


class LoRaWANProcessor(IProcessor):
    """
    Processor for sending LoRaWAN downlink messages.

    Sends HTTP POST requests to LoRaWAN network server APIs with proper
    authentication and payload encoding.
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1
    DEFAULT_F_PORT = 1

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LoRaWAN processor.

        Args:
            config: Configuration dictionary containing:
                - network_provider: TTN, ChirpStack, or Helium
                - api_url: Network server API endpoint
                - api_key: Authentication key
                - device_id: Target device ID (DevEUI)
                - payload: Data to send (Hex string or plain text)
                - f_port: LoRaWAN port (default: 1)
        """
        self.network_provider = config.get("network_provider", "TTN")
        self.api_url = config.get("api_url", "")
        self.api_key = config.get("api_key", "")
        self.device_id = config.get("device_id", "")
        self.default_payload = config.get("payload", "")
        self.f_port = config.get("f_port", self.DEFAULT_F_PORT)

        self.timeout = config.get("timeout", self.DEFAULT_TIMEOUT)
        self.retries = config.get("retries", self.DEFAULT_RETRIES)
        self.retry_delay = config.get("retry_delay", self.DEFAULT_RETRY_DELAY)

        self.client_timeout = aiohttp.ClientTimeout(total=self.timeout)

    def can_handle(self, event: GraphEvent) -> bool:
        """Check if this processor can handle the event."""
        return event.type in (EventType.DATA_CHANGE, EventType.CUSTOM)

    async def process(self, event: GraphEvent, context: Dict[str, Any]) -> GraphEvent:
        """
        Process the event and send a downlink message.

        If event.data contains a 'payload' key, it overrides the config payload.
        """
        payload = self.default_payload
        if isinstance(event.data, dict) and "payload" in event.data:
            payload = event.data["payload"]

        base64_payload = self._encode_payload(payload)

        request_body = self._build_request_body(base64_payload)
        headers = self._build_headers()

        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.client_timeout) as session:
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=request_body
                    ) as response:
                        response.raise_for_status()
                        status = response.status

                        content_type = response.headers.get('Content-Type', '')
                        if 'application/json' in content_type:
                            response_data = await response.json()
                        else:
                            response_data = await response.text()

                        logger.info(
                            f"LoRaWAN downlink sent successfully to {self.device_id} "
                            f"(attempt {attempt + 1})"
                        )

                        return GraphEvent(
                            type=EventType.COMPUTATION_RESULT,
                            data={
                                "content": response_data,
                                "status": status,
                                "device_id": self.device_id,
                                "payload_sent": base64_payload,
                            },
                            metadata={
                                "status": status,
                                "attempt": attempt + 1,
                                "provider": self.network_provider,
                                **event.metadata
                            },
                            source_id=event.source_id
                        )

            except aiohttp.ClientResponseError as e:
                logger.error(
                    f"HTTP request error on attempt {attempt + 1}/{self.retries}: "
                    f"Status {e.status} - {e.message}"
                )
                if attempt == self.retries - 1:
                    return self._create_error_event(
                        f"HTTP request error: {e.status} {e.message}",
                        event,
                        context["node_id"]
                    )

            except asyncio.TimeoutError:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{self.retries}")
                if attempt == self.retries - 1:
                    return self._create_error_event(
                        "Request timeout",
                        event,
                        context["node_id"]
                    )

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{self.retries}: {e}")
                if attempt == self.retries - 1:
                    return self._create_error_event(
                        f"Unexpected error: {str(e)}",
                        event,
                        context["node_id"]
                    )

            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)

        return self._create_error_event(
            "Max retries exceeded",
            event,
            context["node_id"]
        )

    def _encode_payload(self, payload: str) -> str:
        """
        Encode payload to Base64.

        Supports:
        - Hex strings (0x... or plain hex)
        - Plain text strings

        Args:
            payload: The payload to encode

        Returns:
            Base64 encoded string
        """
        if not payload:
            return ""

        hex_pattern = r'^(0x)?[0-9a-fA-F]+$'
        if re.match(hex_pattern, payload):
            # Remove 0x prefix if present
            hex_str = payload[2:] if payload.startswith("0x") else payload
            try:
                byte_data = bytes.fromhex(hex_str)
                return base64.b64encode(byte_data).decode('utf-8')
            except ValueError:
                pass

        return base64.b64encode(payload.encode('utf-8')).decode('utf-8')

    def _build_request_body(self, base64_payload: str) -> Dict[str, Any]:
        """
        Build the request body based on the network provider.

        Args:
            base64_payload: Base64 encoded payload

        Returns:
            Request body dictionary
        """
        if self.network_provider == "TTN":
            return {
                "downlinks": [{
                    "f_port": self.f_port,
                    "frm_payload": base64_payload,
                    "priority": "NORMAL"
                }]
            }
        elif self.network_provider == "ChirpStack":
            return {
                "deviceQueueItem": {
                    "data": base64_payload,
                    "fPort": self.f_port,
                    "confirmed": False
                }
            }
        elif self.network_provider == "Helium":
            return {
                "payload_raw": base64_payload,
                "port": self.f_port,
                "confirmed": False
            }
        else:
            return {
                "payload": base64_payload,
                "f_port": self.f_port
            }

    def _build_headers(self) -> Dict[str, str]:
        """
        Build HTTP headers with authentication.

        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DNA-Engine/1.0"
        }

        if self.network_provider == "TTN":
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.network_provider == "ChirpStack":
            headers["Grpc-Metadata-Authorization"] = f"Bearer {self.api_key}"
        elif self.network_provider == "Helium":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _create_error_event(
        self,
        error_message: str,
        original_event: GraphEvent,
        node_id: str
    ) -> GraphEvent:
        """Create an error event."""
        return GraphEvent(
            type=EventType.ERROR,
            data={
                "error": error_message,
                "original_request": original_event.data,
                "device_id": self.device_id
            },
            source_id=node_id,
            metadata={
                "status": "error",
                "provider": self.network_provider,
                **original_event.metadata
            }
        )
