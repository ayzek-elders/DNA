import logging
from typing import Any, Optional

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_middleware import IMiddleware

logger = logging.getLogger(__name__)


class MQTTLoggingMiddleware(IMiddleware):
    """
    Middleware for logging MQTT operations.

    Logs incoming messages, publish operations, and connection events
    while sanitizing potentially large payloads.
    """

    def __init__(self, max_payload_log_size: int = 200):
        """
        Args:
            max_payload_log_size: Maximum payload size to log (truncates larger payloads)
        """
        self._max_payload_size = max_payload_log_size

    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Log incoming event details."""
        if event.type == EventType.MQTT_MESSAGE:
            topic = event.data.get("topic", "unknown") if isinstance(event.data, dict) else "unknown"
            payload = self._truncate_payload(
                event.data.get("payload") if isinstance(event.data, dict) else event.data
            )
            qos = event.metadata.get("qos", "?")

            logger.info(
                f"MQTT Message received - Node {node_id}: "
                f"topic={topic}, qos={qos}, payload={payload}"
            )

        elif event.type == EventType.MQTT_PUBLISH:
            topic = event.data.get("topic", "unknown") if isinstance(event.data, dict) else "unknown"
            payload = self._truncate_payload(
                event.data.get("payload") if isinstance(event.data, dict) else event.data
            )

            logger.info(
                f"MQTT Publish requested - Node {node_id}: "
                f"topic={topic}, payload={payload}"
            )

        elif event.type == EventType.MQTT_CONNECTED:
            broker = event.data.get("broker", "unknown") if isinstance(event.data, dict) else "unknown"
            logger.info(f"MQTT Connected - Node {node_id}: broker={broker}")

        elif event.type == EventType.MQTT_DISCONNECTED:
            broker = event.data.get("broker", "unknown") if isinstance(event.data, dict) else "unknown"
            reason = event.data.get("reason", "unknown") if isinstance(event.data, dict) else "unknown"
            logger.warning(f"MQTT Disconnected - Node {node_id}: broker={broker}, reason={reason}")

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
                error = result.data.get("error", "Unknown error") if isinstance(result.data, dict) else "Unknown error"
                logger.error(f"MQTT operation failed - Node {node_id}: {error}")
            else:
                status = result.metadata.get("status", "completed")
                operation = result.metadata.get("operation", "unknown")
                logger.debug(
                    f"MQTT operation completed - Node {node_id}: "
                    f"{operation} - {status}"
                )

        return result

    def _truncate_payload(self, payload: Any) -> str:
        """Truncate payload for logging."""
        if payload is None:
            return "null"

        payload_str = str(payload)
        if len(payload_str) > self._max_payload_size:
            return payload_str[:self._max_payload_size] + f"... ({len(payload_str)} chars)"
        return payload_str


class MQTTTopicValidationMiddleware(IMiddleware):
    """
    Middleware for validating MQTT topics.

    Can enforce topic patterns, restrict publish topics, or validate
    incoming message topics against allowed patterns.
    """

    def __init__(
        self,
        allowed_publish_patterns: Optional[list] = None,
        blocked_publish_patterns: Optional[list] = None,
    ):
        """
        Args:
            allowed_publish_patterns: List of allowed topic patterns (regex strings)
            blocked_publish_patterns: List of blocked topic patterns (regex strings)
        """
        import re

        self._allowed_patterns = [
            re.compile(p) for p in (allowed_publish_patterns or [])
        ]
        self._blocked_patterns = [
            re.compile(p) for p in (blocked_publish_patterns or [])
        ]

    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Validate topics before processing."""
        if event.type == EventType.MQTT_PUBLISH:
            if not isinstance(event.data, dict):
                return event

            topic = event.data.get("topic", "")

            # Check blocked patterns
            for pattern in self._blocked_patterns:
                if pattern.match(topic):
                    logger.warning(f"MQTT topic blocked - Node {node_id}: {topic}")
                    return GraphEvent(
                        type=EventType.ERROR,
                        data={
                            "error": f"Topic '{topic}' is blocked",
                            "original_request": event.data,
                        },
                        source_id=event.source_id,
                        metadata={"status": "blocked", **event.metadata}
                    )

            # Check allowed patterns (if any are defined)
            if self._allowed_patterns:
                allowed = any(p.match(topic) for p in self._allowed_patterns)
                if not allowed:
                    logger.warning(f"MQTT topic not in allowed list - Node {node_id}: {topic}")
                    return GraphEvent(
                        type=EventType.ERROR,
                        data={
                            "error": f"Topic '{topic}' is not in allowed list",
                            "original_request": event.data,
                        },
                        source_id=event.source_id,
                        metadata={"status": "blocked", **event.metadata}
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
