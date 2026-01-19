# MQTT Nodes

MQTT integration nodes for connecting to MQTT brokers (Mosquitto, EMQX, HiveMQ) and processing IoT data streams.

## Nodes

| Node | Type | Description |
|------|------|-------------|
| `MQTTSubscriberNode` | SOURCE | Subscribes to topics, emits `MQTT_MESSAGE` events |
| `MQTTPublisherNode` | SINK | Receives events, publishes to MQTT broker |

## Installation

Ensure `aiomqtt` is installed:

```bash
uv sync
```

## Basic Usage

### Subscriber Node (Receive Messages)

```python
from app.engine.graph.graph import ObserverGraph
from app.engine.nodes.mqtt import MQTTSubscriberNode

graph = ObserverGraph()

subscriber = MQTTSubscriberNode(
    node_id="sensor_listener",
    config={
        "credential": {
            "hostname": "mqtt.example.com",
            "port": 1883,
            "username": "user",        # optional
            "password": "password",    # optional
        },
        "subscription_settings": {
            "topics": [
                {"topic": "sensors/#", "qos": 1},      # wildcard: all sensors
                {"topic": "alerts/+/critical", "qos": 2}  # single-level wildcard
            ]
        }
    }
)

graph.add_node(subscriber)
await graph.start()   # Auto-connects and starts listening
```

### Publisher Node (Send Messages)

```python
from app.engine.nodes.mqtt import MQTTPublisherNode

publisher = MQTTPublisherNode(
    node_id="command_sender",
    config={
        "credential": {
            "hostname": "mqtt.example.com",
            "port": 1883
        },
        "publish_settings": {
            "default_topic": "devices/commands",
            "default_qos": 1,
            "retain": False
        }
    }
)

graph.add_node(publisher)
await graph.start()

# Direct publish
await publisher.publish("devices/sensor1/command", {"action": "restart"})
```

---

## Example: IoT Pipeline with SwitchNode

A complete example showing sensor data flowing through a processing pipeline with conditional routing.

```python
import asyncio
import sys
from app.engine.graph.graph import ObserverGraph
from app.engine.graph.graph_event import GraphEvent, EventType
from app.engine.nodes.mqtt import MQTTSubscriberNode, MQTTPublisherNode
from app.engine.nodes.condition.switch_node import SwitchNode
from app.engine.nodes.base_node import BaseNode


class AlertHandlerNode(BaseNode):
    """Handles critical alerts."""

    async def update(self, event: GraphEvent) -> None:
        if event.type == EventType.ROUTING_DECISION:
            data = event.data.get("original_data", {})
            print(f"🚨 ALERT: {data}")
            # Create publish event for alert topic
            # Exclude raw_payload (bytes) as it's not JSON serializable
            payload_data = {
                "topic": data.get("topic"),
                "payload": data.get("payload"),
            }
            alert_event = GraphEvent(
                type=EventType.MQTT_PUBLISH,
                data={
                    "topic": f"alerts/{data.get('payload', {}).get('sensor_id', 'unknown')}",
                    "payload": {"alert": "threshold_exceeded", "data": payload_data}
                }
            )
            await self.notify_observers(alert_event)


class NormalHandlerNode(BaseNode):
    """Handles normal sensor readings."""

    async def update(self, event: GraphEvent) -> None:
        if event.type == EventType.ROUTING_DECISION:
            data = event.data.get("original_data", {})
            print(f"✅ Normal reading: {data}")


class AlertReceiverNode(BaseNode):
    """Receives and displays published alerts."""

    async def update(self, event: GraphEvent) -> None:
        if event.type == EventType.MQTT_MESSAGE:
            topic = event.data.get("topic", "")
            payload = event.data.get("payload", {})
            print(f"📩 ALERT RECEIVED on {topic}: {payload}")


async def main():
    graph = ObserverGraph()

    # 1. MQTT Subscriber - receives sensor data
    subscriber = MQTTSubscriberNode(
        node_id="sensor_subscriber",
        config={
            "credential": {
                "hostname": "localhost",
                "port": 1883
            },
            "subscription_settings": {
                "topics": [
                    {"topic": "factory/sensors/#", "qos": 1}
                ]
            }
        }
    )

    # 2. Switch Node - routes based on sensor values
    switch = SwitchNode(
        node_id="sensor_router",
        config={
            "rules": [
                {
                    "high-temperature": {
                        "condition": {">": [{"var": "payload.temperature"}, 80]},
                        "then": "alert_handler"
                    }
                },
                {
                    "low-battery": {
                        "condition": {"<": [{"var": "payload.battery"}, 20]},
                        "then": "alert_handler"
                    }
                },
                {
                    "critical-pressure": {
                        "condition": {">": [{"var": "payload.pressure"}, 150]},
                        "then": "alert_handler"
                    }
                }
            ],
            "default_target": "normal_handler"
        }
    )

    # 3. Handler Nodes
    alert_handler = AlertHandlerNode(node_id="alert_handler")
    normal_handler = NormalHandlerNode(node_id="normal_handler")

    # 4. MQTT Publisher - sends alerts back to broker
    publisher = MQTTPublisherNode(
        node_id="alert_publisher",
        config={
            "credential": {
                "hostname": "localhost",
                "port": 1883
            },
            "publish_settings": {
                "default_qos": 2  # QoS 2 for critical alerts
            }
        }
    )

    # 5. MQTT Subscriber for alerts - receives published alerts
    alert_subscriber = MQTTSubscriberNode(
        node_id="alert_subscriber",
        config={
            "credential": {
                "hostname": "localhost",
                "port": 1883
            },
            "subscription_settings": {
                "topics": [
                    {"topic": "alerts/#", "qos": 2}
                ]
            }
        }
    )

    # 6. Alert Receiver - displays received alerts
    alert_receiver = AlertReceiverNode(node_id="alert_receiver")

    # Add nodes to graph
    graph.add_node(subscriber)
    graph.add_node(switch)
    graph.add_node(alert_handler)
    graph.add_node(normal_handler)
    graph.add_node(publisher)
    graph.add_node(alert_subscriber)
    graph.add_node(alert_receiver)

    # Connect the pipeline
    #
    #  subscriber --> switch --[alert]--> alert_handler --> publisher
    #                       \--[normal]--> normal_handler
    #
    #  alert_subscriber --> alert_receiver (separate pipeline for receiving alerts)
    #
    graph.add_edge("sensor_subscriber", "sensor_router")
    graph.add_edge("sensor_router", "alert_handler")
    graph.add_edge("sensor_router", "normal_handler")
    graph.add_edge("alert_handler", "alert_publisher")
    graph.add_edge("alert_subscriber", "alert_receiver")

    # Start the graph (auto-connects MQTT nodes)
    await graph.start()

    print("Pipeline running. Waiting for sensor data...")
    print("Subscribe to: factory/sensors/#")
    print("Press Ctrl+C to stop")

    try:
        # Keep running
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await graph.stop()


if __name__ == "__main__":
    # On Windows, aiomqtt requires SelectorEventLoop (not the default ProactorEventLoop)
    # because paho-mqtt uses add_reader/add_writer which ProactorEventLoop doesn't support
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
```

### Testing the Pipeline

Start a local MQTT broker (e.g., Mosquitto):

```bash
docker run -it -p 1883:1883 eclipse-mosquitto
```

Publish test messages:

```bash
# Normal reading - routed to normal_handler
mosquitto_pub -t "factory/sensors/temp1" -m '{"sensor_id": "temp1", "temperature": 45, "battery": 80}'

# High temperature - routed to alert_handler
mosquitto_pub -t "factory/sensors/temp2" -m '{"sensor_id": "temp2", "temperature": 95, "battery": 90}'

# Low battery - routed to alert_handler
mosquitto_pub -t "factory/sensors/temp3" -m '{"sensor_id": "temp3", "temperature": 50, "battery": 15}'
```

---

## Configuration Reference

### Credential Settings

```python
"credential": {
    "hostname": "mqtt.example.com",  # Required
    "port": 1883,                    # Default: 1883 (8883 for TLS)
    "username": None,                # Optional
    "password": None,                # Optional
    "use_tls": False,                # Enable TLS/SSL
    "ca_certs": None,                # CA certificate path
    "client_cert": None,             # Client certificate path
    "client_key": None,              # Client key path
}
```

### Client Settings

```python
"client_settings": {
    "client_id": None,       # Auto-generated if None
    "clean_session": True,   # Clean session on connect
    "keepalive": 60,         # Keepalive interval (seconds)
}
```

### Subscription Settings (Subscriber only)

```python
"subscription_settings": {
    "topics": [
        {"topic": "sensors/#", "qos": 1},      # Multi-level wildcard
        {"topic": "device/+/status", "qos": 0} # Single-level wildcard
    ],
    "default_qos": 1,
}
```

### Publish Settings (Publisher only)

```python
"publish_settings": {
    "default_topic": "devices/commands",  # Fallback topic
    "default_qos": 1,                     # 0, 1, or 2
    "retain": False,                      # Retain messages
}
```

### Retry Settings

```python
"retry_settings": {
    "max_retries": 5,           # Max reconnection attempts
    "retry_delay": 5,           # Initial delay (seconds)
    "retry_backoff": 2.0,       # Exponential backoff multiplier
    "max_retry_delay": 60,      # Max delay between retries
    "reconnect_on_failure": True,
}
```

---

## Event Types

| EventType | Direction | Description |
|-----------|-----------|-------------|
| `MQTT_MESSAGE` | Outbound (Subscriber) | Emitted when a message is received |
| `MQTT_PUBLISH` | Inbound (Publisher) | Triggers a publish to the broker |
| `MQTT_CONNECTED` | Outbound | Emitted on successful connection |
| `MQTT_DISCONNECTED` | Outbound | Emitted on disconnection |

### MQTT_MESSAGE Event Structure

```python
GraphEvent(
    type=EventType.MQTT_MESSAGE,
    data={
        "topic": "sensors/temp1",
        "payload": {"temperature": 25.5},  # Auto-parsed JSON
        "raw_payload": b'{"temperature": 25.5}',
    },
    metadata={
        "qos": 1,
        "retain": False,
        "broker": "mqtt.example.com",
    }
)
```

### MQTT_PUBLISH Event Structure

```python
GraphEvent(
    type=EventType.MQTT_PUBLISH,
    data={
        "topic": "devices/sensor1/command",
        "payload": {"action": "restart"},
        "qos": 1,       # Optional
        "retain": False # Optional
    }
)
```

---

## Middleware

### MQTTLoggingMiddleware

Logs all MQTT operations with payload truncation:

```python
from app.engine.nodes.mqtt import MQTTLoggingMiddleware

subscriber.add_middleware(MQTTLoggingMiddleware(max_payload_log_size=200))
```

### MQTTTopicValidationMiddleware

Restrict which topics can be published to:

```python
from app.engine.nodes.mqtt import MQTTTopicValidationMiddleware

publisher.add_middleware(MQTTTopicValidationMiddleware(
    allowed_publish_patterns=[r"^devices/.*"],
    blocked_publish_patterns=[r"^admin/.*", r"^system/.*"]
))
```

---

## QoS Levels

| QoS | Delivery | Use Case |
|-----|----------|----------|
| 0 | At most once | Telemetry, non-critical data |
| 1 | At least once | Important messages, may duplicate |
| 2 | Exactly once | Critical commands, transactions |
