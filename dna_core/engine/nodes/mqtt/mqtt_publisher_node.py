import asyncio
import json
import logging
from typing import Any, Dict, Optional

from dna_core.engine.nodes.base_node import BaseNode
from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_lifecycle import ILifecycle
from dna_core.engine.nodes.mqtt.mqtt_connection_manager import MQTTConnectionManager

logger = logging.getLogger(__name__)


class MQTTPublisherNode(BaseNode, ILifecycle):
    """
    MQTT Publisher node - SINK node that publishes messages to an MQTT broker.

    This node receives events and publishes them to MQTT topics. It can handle
    MQTT_PUBLISH events or any event type (publishing the event data as payload).

    Implements ILifecycle for graph-managed start/stop.

    Args:
        node_id: Unique identifier for the node
        node_type: Type identifier (defaults to "MQTT_PUBLISHER_NODE")
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
            - publish_settings: Default publish settings
                - default_topic: Default topic for publishing (optional)
                - default_qos: Default QoS for publishing (default: 1)
                - retain: Default retain flag (default: False)
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
            "publish_settings": {
                "default_topic": "devices/commands",
                "default_qos": 1
            }
        }

        publisher = MQTTPublisherNode(node_id="command_sender", config=config)
        graph.add_node(publisher)
        graph.add_edge("command_generator", "command_sender")
        await graph.start()

    Event Data Format:
        For MQTT_PUBLISH events:
        {
            "topic": "devices/sensor1/command",  # Required (or use default_topic)
            "payload": {"action": "restart"},    # Required
            "qos": 1,                            # Optional
            "retain": False                      # Optional
        }

        For other event types, the entire event.data is published as JSON payload.
    """

    def __init__(
        self,
        node_id: str,
        node_type: str = "MQTT_PUBLISHER_NODE",
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
            "publish_settings": {
                "default_topic": None,
                "default_qos": 1,
                "retain": False,
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
        self._is_running = False

        # Publish settings
        pub_settings = merged_config.get("publish_settings", {})
        self._default_topic = pub_settings.get("default_topic")
        self._default_qos = pub_settings.get("default_qos", 1)
        self._default_retain = pub_settings.get("retain", False)

    async def start(self) -> None:
        """
        Start the publisher - connect to broker.

        Called automatically by ObserverGraph.start().
        """
        if self._is_running:
            logger.warning(f"MQTT Publisher {self.id} is already running")
            return

        # Publisher doesn't need message callback since it only publishes
        self._connection_manager = MQTTConnectionManager(
            config=self.config,
            on_message_callback=self._noop_message_handler,
            on_connect_callback=self._handle_connect,
            on_disconnect_callback=self._handle_disconnect,
        )

        await self._connection_manager.connect()
        self._is_running = True

        logger.info(f"MQTT Publisher {self.id} started")

    async def stop(self) -> None:
        """
        Stop the publisher - disconnect from broker.

        Called automatically by ObserverGraph.stop().
        """
        if not self._is_running:
            return

        self._is_running = False

        if self._connection_manager:
            await self._connection_manager.disconnect()
            self._connection_manager = None

        logger.info(f"MQTT Publisher {self.id} stopped")

    @property
    def is_running(self) -> bool:
        """Check if the publisher is currently running."""
        return self._is_running

    async def _noop_message_handler(
        self,
        topic: str,
        payload: bytes,
        qos: int,
        retain: bool
    ) -> None:
        """No-op message handler - publisher doesn't process incoming messages."""
        pass

    async def update(self, event: GraphEvent) -> None:
        """
        Process incoming event and publish to MQTT broker.

        Overrides BaseNode.update() to handle publishing logic directly.
        """
        if not self._is_running or not self._connection_manager:
            logger.warning(f"MQTT Publisher {self.id} is not connected, dropping event")
            return

        try:
            # Extract publish parameters from event
            if event.type == EventType.MQTT_PUBLISH:
                # Explicit publish event
                topic, payload, qos, retain = self._extract_publish_params(event.data)
            else:
                # Any other event - publish event.data to default topic
                topic = self._default_topic
                payload = event.data
                qos = self._default_qos
                retain = self._default_retain

            if not topic:
                logger.error(f"No topic specified and no default_topic configured in {self.id}")
                error_event = self.create_error_event(
                    "No topic specified for publish",
                    event,
                    self.id
                )
                await self.notify_observers(error_event)
                return

            # Publish the message
            success = await self._connection_manager.publish(
                topic=topic,
                payload=payload,
                qos=qos,
                retain=retain,
            )

            if success:
                result_event = GraphEvent(
                    type=EventType.COMPUTATION_RESULT,
                    data={
                        "status": "published",
                        "topic": topic,
                        "qos": qos,
                        "retain": retain,
                    },
                    source_id=self.id,
                    metadata={
                        "status": "success",
                        "operation": "mqtt_publish",
                        **event.metadata
                    }
                )
                await self.notify_observers(result_event)
            else:
                error_event = self.create_error_event(
                    "Failed to publish message - not connected",
                    event,
                    self.id
                )
                await self.notify_observers(error_event)

        except Exception as e:
            logger.error(f"Error publishing in {self.id}: {e}")
            error_event = self.create_error_event(str(e), event, self.id)
            await self.notify_observers(error_event)

    def _extract_publish_params(self, data: Any) -> tuple:
        """Extract publish parameters from event data."""
        if not isinstance(data, dict):
            return self._default_topic, data, self._default_qos, self._default_retain

        topic = data.get("topic", self._default_topic)
        payload = data.get("payload", data)
        qos = data.get("qos", self._default_qos)
        retain = data.get("retain", self._default_retain)

        return topic, payload, qos, retain

    async def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = None,
        retain: bool = None
    ) -> bool:
        """
        Publish a message directly (convenience method).

        Args:
            topic: MQTT topic to publish to
            payload: Message payload (str, bytes, or JSON-serializable object)
            qos: Quality of Service level (0, 1, or 2)
            retain: Whether to retain the message on the broker

        Returns:
            bool: True if publish was successful
        """
        if not self._connection_manager or not self._is_running:
            logger.error(f"Cannot publish - MQTT Publisher {self.id} is not connected")
            return False

        return await self._connection_manager.publish(
            topic=topic,
            payload=payload,
            qos=qos if qos is not None else self._default_qos,
            retain=retain if retain is not None else self._default_retain
        )

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
            "default_topic": self._default_topic,
        })
        return info
