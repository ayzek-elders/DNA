import logging
import re
from typing import Optional

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_middleware import IMiddleware

logger = logging.getLogger(__name__)

# LoRaWAN payload size limits (bytes) - varies by data rate
LORAWAN_MIN_PAYLOAD = 1
LORAWAN_MAX_PAYLOAD = 242  # Maximum for DR5/SF7 (EU868)
LORAWAN_TYPICAL_MAX = 51   # Safe limit for DR0/SF12


class LoRaWANValidationMiddleware(IMiddleware):
    """
    Middleware for validating LoRaWAN downlink configurations.

    Validates:
    - Required fields (api_url, api_key, device_id)
    - Payload format (Hex or plain text)
    - Payload size limits (optional warning)
    """

    def __init__(self, config: dict = None):
        """
        Initialize the validation middleware.

        Args:
            config: Configuration dictionary containing node settings
        """
        self.config = config or {}
        self.api_url = self.config.get("api_url", "")
        self.api_key = self.config.get("api_key", "")
        self.device_id = self.config.get("device_id", "")
        self.payload = self.config.get("payload", "")
        self.warn_on_large_payload = self.config.get("warn_on_large_payload", True)

    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """
        Validate configuration before processing.

        Returns an error event if validation fails.
        """
        errors = []

        if not self.api_url:
            errors.append("Missing required field: api_url")

        if not self.api_key:
            errors.append("Missing required field: api_key")

        if not self.device_id:
            errors.append("Missing required field: device_id")

        payload = self.payload
        if isinstance(event.data, dict) and "payload" in event.data:
            payload = event.data["payload"]

        if payload:
            payload_bytes = self._get_payload_bytes(payload)

            if payload_bytes is not None:
                if len(payload_bytes) > LORAWAN_MAX_PAYLOAD:
                    errors.append(
                        f"Payload size ({len(payload_bytes)} bytes) exceeds "
                        f"LoRaWAN maximum ({LORAWAN_MAX_PAYLOAD} bytes)"
                    )
                elif len(payload_bytes) > LORAWAN_TYPICAL_MAX and self.warn_on_large_payload:
                    logger.warning(
                        f"LoRaWAN payload size ({len(payload_bytes)} bytes) may be "
                        f"too large for low data rates. Consider keeping under "
                        f"{LORAWAN_TYPICAL_MAX} bytes for maximum compatibility."
                    )

        if errors:
            error_message = "; ".join(errors)
            logger.error(f"LoRaWAN validation failed for node {node_id}: {error_message}")

            return GraphEvent(
                type=EventType.ERROR,
                data={
                    "error": error_message,
                    "validation_errors": errors,
                    "original_request": event.data
                },
                source_id=node_id,
                metadata={
                    "status": "validation_error",
                    **event.metadata
                }
            )

        logger.debug(f"LoRaWAN validation passed for node {node_id}")
        return event

    async def after_process(
        self,
        event: GraphEvent,
        result: Optional[GraphEvent],
        node_id: str
    ) -> Optional[GraphEvent]:
        """
        Post-processing hook (logging only).
        """
        if result:
            if result.type == EventType.ERROR:
                logger.error(
                    f"LoRaWAN downlink failed for node {node_id}: "
                    f"{result.data.get('error', 'Unknown error')}"
                )
            elif result.type == EventType.COMPUTATION_RESULT:
                logger.info(
                    f"LoRaWAN downlink completed for node {node_id}: "
                    f"device={result.data.get('device_id')}, "
                    f"status={result.data.get('status')}"
                )

        return result

    def _get_payload_bytes(self, payload: str) -> Optional[bytes]:
        """
        Convert payload to bytes for size calculation.

        Args:
            payload: Hex string (0x...) or plain text

        Returns:
            Bytes representation or None if conversion fails
        """
        if not payload:
            return b""

        hex_pattern = r'^(0x)?[0-9a-fA-F]+$'
        if re.match(hex_pattern, payload):
            hex_str = payload[2:] if payload.startswith("0x") else payload
            try:
                return bytes.fromhex(hex_str)
            except ValueError:
                pass

        return payload.encode('utf-8')


class LoRaWANLoggingMiddleware(IMiddleware):
    """
    Middleware for logging LoRaWAN operations.

    Logs downlink requests and responses with optional payload truncation.
    """

    def __init__(self, max_payload_log_size: int = 50):
        """
        Args:
            max_payload_log_size: Maximum payload size to log (truncates larger)
        """
        self._max_payload_size = max_payload_log_size

    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Log incoming downlink request."""
        payload = ""
        if isinstance(event.data, dict):
            payload = event.data.get("payload", "")

        truncated_payload = self._truncate_payload(payload)

        logger.info(
            f"LoRaWAN Downlink request - Node {node_id}: "
            f"payload={truncated_payload}"
        )

        return event

    async def after_process(
        self,
        event: GraphEvent,
        result: Optional[GraphEvent],
        node_id: str
    ) -> Optional[GraphEvent]:
        """Log processing result."""
        if result:
            if result.type == EventType.ERROR:
                error = result.data.get("error", "Unknown error")
                logger.error(f"LoRaWAN downlink failed - Node {node_id}: {error}")
            else:
                device_id = result.data.get("device_id", "unknown")
                status = result.data.get("status", "unknown")
                logger.info(
                    f"LoRaWAN downlink completed - Node {node_id}: "
                    f"device={device_id}, status={status}"
                )

        return result

    def _truncate_payload(self, payload: str) -> str:
        """Truncate payload for logging."""
        if not payload:
            return "(empty)"

        if len(payload) > self._max_payload_size:
            return payload[:self._max_payload_size] + f"... ({len(payload)} chars)"

        return payload
