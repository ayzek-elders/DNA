import asyncio
import json
import logging
from typing import Any, Dict, Optional

from dna_core.engine.nodes.base_node import BaseNode
from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_lifecycle import ILifecycle
from dna_core.engine.nodes.mqtt.mqtt_connection_manager import MQTTConnectionManager

logger = logging.getLogger(__name__)


class MQTTSubscriberNode(BaseNode, ILifecycle):
    """
    MQTT Subscriber node - SOURCE node that listens for messages and triggers GraphEvents.

    This node connects to an MQTT broker, subscribes to topics, and emits
    MQTT_MESSAGE events to downstream nodes when messages arrive.

    Implements ILifecycle for graph-managed start/stop.

    Args:
        node_id: Unique identifier for the node
        node_type: Type identifier (defaults to "MQTT_SUBSCRIBER_NODE")
        initial_data: Initial data for the node
        config: Configuration dictionary:
            - credential: Broker connection settings
                - hostname: MQTT broker hostname (required)
                - port: Broker port (default: 1883)
                - username: Authentication username (optional)
                - password: Authentication password (optional)
                - use_tls: Enable TLS/SSL (default: False)
                - ca_certs: CA certificate path (optional)
            - client_settings: MQTT client configuration
                - client_id: Client identifier (auto-generated if None)
                - clean_session: Clean session flag (default: True)
                - keepalive: Keepalive interval in seconds (default: 60)
            - subscription_settings: Topics to subscribe to
                - topics: List of {"topic": str, "qos": int}
                - default_qos: Default QoS level (default: 1)
            - retry_settings: Reconnection configuration
                - max_retries: Max reconnection attempts (default: 5)
                - retry_delay: Initial retry delay in seconds (default: 5)
                - retry_backoff: Exponential backoff multiplier (default: 2.0)
                - max_retry_delay: Maximum retry delay (default: 60)
                - reconnect_on_failure: Auto-reconnect on disconnect (default: True)

    Example:
        config = {
            "credential": {
                "hostname": "mqtt.example.com",
                "port": 1883
            },
            "subscription_settings": {
                "topics": [
                    {"topic": "sensors/#", "qos": 1},
                    {"topic": "commands/+/status", "qos": 2}
                ]
            }
        }

        subscriber = MQTTSubscriberNode(node_id="iot_listener", config=config)
        graph.add_node(subscriber)
        graph.add_edge("iot_listener", "data_processor")
        await graph.start()
    """

    def __init__(
        self,
        node_id: str,
        node_type: str = "MQTT_SUBSCRIBER_NODE",
        initial_data: Any = None,
        config: Dict[str, Any] = None
    ):
        default_config = {
            "credential": {
                "port": 1883,
                "use_tls": False,
            },
            "client_settings": {
                "clean_session": True,
                "keepalive": 60,
            },
            "subscription_settings": {
                "topics": [],
                "default_qos": 1,
            },
            "retry_settings": {
                "max_retries": 5,
                "retry_delay": 5,
                "retry_backoff": 2.0,
                "max_retry_delay": 60,
                "reconnect_on_failure": True,
            }
        }

        merged_config = self._deep_merge_config(default_config, config or {})
        super().__init__(node_id, node_type, initial_data, merged_config)

        self._connection_manager: Optional[MQTTConnectionManager] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        """
        Start the subscriber - connect to broker and begin listening.

        Called automatically by ObserverGraph.start().
        """
        if self._is_running:
            logger.warning(f"MQTT Subscriber {self.id} is already running")
            return

        self._connection_manager = MQTTConnectionManager(
            config=self.config,
            on_message_callback=self._handle_incoming_message,
            on_connect_callback=self._handle_connect,
            on_disconnect_callback=self._handle_disconnect,
        )

        await self._connection_manager.connect()
        self._is_running = True

        self._listener_task = asyncio.create_task(
            self._connection_manager.listen(),
            name=f"mqtt_subscriber_{self.id}"
        )

        logger.info(f"MQTT Subscriber {self.id} started")

    async def stop(self) -> None:
        """
        Stop the subscriber - disconnect from broker.

        Called automatically by ObserverGraph.stop().
        """
        if not self._is_running:
            return

        self._is_running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._connection_manager:
            await self._connection_manager.disconnect()
            self._connection_manager = None

        logger.info(f"MQTT Subscriber {self.id} stopped")

    @property
    def is_running(self) -> bool:
        """Check if the subscriber is currently running."""
        return self._is_running

    async def _handle_incoming_message(
        self,
        topic: str,
        payload: bytes,
        qos: int,
        retain: bool
    ) -> None:
        """Convert MQTT message to GraphEvent and notify observers."""
        try:
            # Decode payload
            try:
                decoded_payload = payload.decode("utf-8")
                try:
                    message_data = json.loads(decoded_payload)
                except json.JSONDecodeError:
                    message_data = decoded_payload
            except UnicodeDecodeError:
                message_data = payload

            event = GraphEvent(
                type=EventType.MQTT_MESSAGE,
                data={
                    "topic": topic,
                    "payload": message_data,
                    "raw_payload": payload,
                },
                source_id=self.id,
                metadata={
                    "qos": qos,
                    "retain": retain,
                    "broker": self.config.get("credential", {}).get("hostname"),
                }
            )

            await self.notify_observers(event)

        except Exception as e:
            logger.error(f"Error handling MQTT message in {self.id}: {e}")
            error_event = self.create_error_event(
                f"Failed to process MQTT message: {str(e)}",
                GraphEvent(type=EventType.MQTT_MESSAGE, data={"topic": topic}),
                self.id
            )
            await self.notify_observers(error_event)

    async def _handle_connect(self) -> None:
        """Handle successful broker connection."""
        event = GraphEvent(
            type=EventType.MQTT_CONNECTED,
            data={"broker": self.config.get("credential", {}).get("hostname")},
            source_id=self.id,
            metadata={"status": "connected"}
        )
        await self.notify_observers(event)

    async def _handle_disconnect(self, reason: Optional[str] = None) -> None:
        """Handle broker disconnection."""
        event = GraphEvent(
            type=EventType.MQTT_DISCONNECTED,
            data={
                "broker": self.config.get("credential", {}).get("hostname"),
                "reason": reason or "Unknown"
            },
            source_id=self.id,
            metadata={"status": "disconnected"}
        )
        await self.notify_observers(event)

    async def subscribe(self, topic: str, qos: int = None) -> None:
        """Subscribe to an additional topic at runtime."""
        if not self._connection_manager or not self._is_running:
            raise ConnectionError(f"Subscriber {self.id} is not connected")

        await self._connection_manager.subscribe(topic, qos)

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic at runtime."""
        if not self._connection_manager or not self._is_running:
            raise ConnectionError(f"Subscriber {self.id} is not connected")

        await self._connection_manager.unsubscribe(topic)

    def _deep_merge_config(
        self,
        default: Dict[str, Any],
        user_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge configuration dictionaries."""
        result = default.copy()
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def get_info(self) -> Dict[str, Any]:
        """Get node information including connection status."""
        info = super().get_info()
        info.update({
            "is_running": self._is_running,
            "broker": self.config.get("credential", {}).get("hostname"),
            "subscribed_topics": [
                t.get("topic")
                for t in self.config.get("subscription_settings", {}).get("topics", [])
            ],
        })
        return info
