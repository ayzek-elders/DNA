import asyncio
import json
import logging
import ssl
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aiomqtt

from dna_core.engine.interfaces.i_conntection_manager import IConnectionManager

logger = logging.getLogger(__name__)


class MQTTConnectionManager(IConnectionManager):
    """
    Manages MQTT broker connection lifecycle including:
    - Initial connection with authentication
    - TLS/SSL support
    - Subscription management
    - Automatic reconnection with exponential backoff
    - Health monitoring
    """

    def __init__(
        self,
        config: Dict[str, Any],
        on_message_callback: Callable[[str, bytes, int, bool], Awaitable[None]],
        on_connect_callback: Optional[Callable[[], Awaitable[None]]] = None,
        on_disconnect_callback: Optional[Callable[[Optional[str]], Awaitable[None]]] = None,
    ):
        self.config = config
        self._on_message = on_message_callback
        self._on_connect = on_connect_callback
        self._on_disconnect = on_disconnect_callback

        self._client: Optional[aiomqtt.Client] = None
        self._is_connected = False
        self._reconnect_attempts = 0
        self._should_reconnect = True

        # Extract credential configuration
        cred = config.get("credential", {})
        self._hostname = cred.get("hostname")
        self._port = cred.get("port", 1883)
        self._username = cred.get("username")
        self._password = cred.get("password")
        self._use_tls = cred.get("use_tls", False)
        self._ca_certs = cred.get("ca_certs")
        self._client_cert = cred.get("client_cert")
        self._client_key = cred.get("client_key")

        # Extract client settings
        client_settings = config.get("client_settings", {})
        self._client_id = client_settings.get("client_id")
        self._clean_session = client_settings.get("clean_session", True)
        self._keepalive = client_settings.get("keepalive", 60)

        # Extract retry settings
        retry_settings = config.get("retry_settings", {})
        self._max_retries = retry_settings.get("max_retries", 5)
        self._retry_delay = retry_settings.get("retry_delay", 5)
        self._retry_backoff = retry_settings.get("retry_backoff", 2.0)
        self._max_retry_delay = retry_settings.get("max_retry_delay", 60)
        self._reconnect_on_failure = retry_settings.get("reconnect_on_failure", True)

        # Extract subscription settings
        sub_settings = config.get("subscription_settings", {})
        self._topics: List[Dict[str, Any]] = sub_settings.get("topics", [])
        self._default_qos = sub_settings.get("default_qos", 1)

    def _create_tls_context(self) -> Optional[ssl.SSLContext]:
        """Create TLS context if TLS is enabled."""
        if not self._use_tls:
            return None

        context = ssl.create_default_context()

        if self._ca_certs:
            context.load_verify_locations(self._ca_certs)

        if self._client_cert and self._client_key:
            context.load_cert_chain(self._client_cert, self._client_key)

        return context

    async def connect(self) -> None:
        """Connect to the MQTT broker with retry logic."""
        if not self._hostname:
            raise ValueError("MQTT hostname is required in credential.hostname")

        self._should_reconnect = True
        self._reconnect_attempts = 0

        while self._reconnect_attempts < self._max_retries:
            try:
                tls_context = self._create_tls_context()

                self._client = aiomqtt.Client(
                    hostname=self._hostname,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    tls_context=tls_context,
                    identifier=self._client_id,
                    clean_session=self._clean_session,
                    keepalive=self._keepalive,
                )

                await self._client.__aenter__()
                self._is_connected = True
                self._reconnect_attempts = 0

                logger.info(f"Connected to MQTT broker: {self._hostname}:{self._port}")

                # Subscribe to configured topics
                await self._subscribe_to_topics()

                if self._on_connect:
                    await self._on_connect()

                return

            except aiomqtt.MqttError as e:
                self._reconnect_attempts += 1
                delay = min(
                    self._retry_delay * (self._retry_backoff ** (self._reconnect_attempts - 1)),
                    self._max_retry_delay
                )

                # Clean up the failed client before retrying
                if self._client:
                    try:
                        await self._client.__aexit__(None, None, None)
                    except Exception:
                        pass
                    self._client = None

                logger.warning(
                    f"MQTT connection failed (attempt {self._reconnect_attempts}/{self._max_retries}): {e}. "
                    f"Retrying in {delay:.1f}s"
                )

                if self._reconnect_attempts >= self._max_retries:
                    raise ConnectionError(
                        f"Failed to connect to MQTT broker after {self._max_retries} attempts: {e}"
                    )

                await asyncio.sleep(delay)

    async def _subscribe_to_topics(self) -> None:
        """Subscribe to all configured topics."""
        if not self._client or not self._topics:
            return

        for topic_config in self._topics:
            topic = topic_config.get("topic")
            qos = topic_config.get("qos", self._default_qos)

            if topic:
                await self._client.subscribe(topic, qos=qos)
                logger.info(f"Subscribed to topic: {topic} (QoS {qos})")

    async def listen(self) -> None:
        """
        Listen for incoming messages. Runs indefinitely until stopped.
        Handles reconnection on disconnection.
        """
        while self._should_reconnect:
            try:
                if not self._is_connected:
                    await self.connect()

                async for message in self._client.messages:
                    await self._on_message(
                        topic=str(message.topic),
                        payload=message.payload,
                        qos=message.qos,
                        retain=message.retain,
                    )

            except aiomqtt.MqttError as e:
                self._is_connected = False
                logger.error(f"MQTT connection lost: {e}")

                if self._on_disconnect:
                    await self._on_disconnect(str(e))

                if self._reconnect_on_failure and self._should_reconnect:
                    logger.info("Attempting to reconnect...")
                    self._reconnect_attempts = 0
                    await asyncio.sleep(self._retry_delay)
                else:
                    break

            except asyncio.CancelledError:
                logger.info("MQTT listener cancelled")
                break

    async def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = 1,
        retain: bool = False
    ) -> bool:
        """
        Publish a message to a topic.

        Args:
            topic: MQTT topic to publish to
            payload: Message payload (str, bytes, or JSON-serializable object)
            qos: Quality of Service (0, 1, or 2)
            retain: Whether to retain the message on the broker

        Returns:
            bool: True if successful
        """
        if not self._client or not self._is_connected:
            logger.error("Cannot publish - not connected to broker")
            return False

        try:
            # Convert payload to bytes
            if isinstance(payload, str):
                payload_bytes = payload.encode("utf-8")
            elif isinstance(payload, bytes):
                payload_bytes = payload
            else:
                payload_bytes = json.dumps(payload).encode("utf-8")

            await self._client.publish(
                topic=topic,
                payload=payload_bytes,
                qos=qos,
                retain=retain,
            )

            logger.debug(f"Published message to {topic} (QoS {qos}, retain={retain})")
            return True

        except aiomqtt.MqttError as e:
            logger.error(f"Failed to publish message: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the broker."""
        self._should_reconnect = False

        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._client = None
                self._is_connected = False

        logger.info("Disconnected from MQTT broker")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to broker."""
        return self._is_connected

    async def subscribe(self, topic: str, qos: int = None) -> None:
        """
        Subscribe to an additional topic at runtime.

        Args:
            topic: MQTT topic (supports wildcards + and #)
            qos: Quality of Service level
        """
        if not self._client or not self._is_connected:
            raise ConnectionError("Not connected to broker")

        qos = qos if qos is not None else self._default_qos
        await self._client.subscribe(topic, qos=qos)

        # Track for reconnection
        self._topics.append({"topic": topic, "qos": qos})
        logger.info(f"Subscribed to topic: {topic} (QoS {qos})")

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        if not self._client or not self._is_connected:
            raise ConnectionError("Not connected to broker")

        await self._client.unsubscribe(topic)

        # Remove from tracking
        self._topics = [t for t in self._topics if t.get("topic") != topic]
        logger.info(f"Unsubscribed from topic: {topic}")
