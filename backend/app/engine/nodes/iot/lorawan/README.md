# LoRaWAN Node

LoRaWAN integration nodes for sending downlink messages to IoT devices via network servers (The Things Network, ChirpStack, Helium).

## Nodes

| Node | Type | Description |
|------|------|-------------|
| `LoRaWANDownlinkNode` | SINK | Sends downlink commands to LoRaWAN devices |

## Installation

Ensure `aiohttp` is installed:

```bash
uv sync
```

## Basic Usage

### Downlink Node (Send Commands to Device)

```python
from app.engine.graph.graph import ObserverGraph
from app.engine.nodes.iot.lorawan import LoRaWANDownlinkNode

graph = ObserverGraph()

# The Things Network (TTN) example
downlink_node = LoRaWANDownlinkNode(
    node_id="valve_controller",
    config={
        "network_provider": "TTN",
        "api_url": "https://eu1.cloud.thethings.network/api/v3/as/applications/my-app/devices/my-device/down/push",
        "api_key": "NNSXS.xxxxxxxxxxxx",
        "device_id": "my-device",
        "payload": "0x00",  # Close valve (hex)
        "f_port": 1
    }
)

graph.add_node(downlink_node)
```

---

## Example: Weather-Triggered Irrigation Control

A complete example showing weather data triggering a valve control command via LoRaWAN.

```python
import asyncio
from aiohttp import web
from app.engine.graph.graph import ObserverGraph
from app.engine.graph.graph_event import GraphEvent, EventType
from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.iot.lorawan import LoRaWANDownlinkNode
from app.engine.nodes.condition.switch_node import SwitchNode


# ==================== Mock TTN Server ====================

received_commands = []

async def mock_ttn_handler(request):
    """Simulates TTN Network Server API."""
    data = await request.json()
    received_commands.append(data)
    
    payload = data.get("downlinks", [{}])[0].get("frm_payload", "")
    f_port = data.get("downlinks", [{}])[0].get("f_port", 1)
    
    print(f"  📡 TTN API received: payload={payload}, f_port={f_port}")
    return web.json_response({"success": True, "message": "Downlink scheduled"})


async def start_mock_server():
    app = web.Application()
    app.router.add_post('/api/v3/as/applications/farm/devices/valve-01/down/push', mock_ttn_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8888)
    await site.start()
    return runner


# ==================== Custom Nodes ====================

class WeatherSensorNode(BaseNode):
    """
    Simulates a weather sensor that sends periodic readings.
    """
    
    def __init__(self, node_id: str, location: str = "Field A"):
        super().__init__(node_id, node_type="WEATHER_SENSOR_NODE")
        self.location = location
    
    async def send_reading(self, temperature: float, humidity: float, is_raining: bool):
        """Send a weather reading to observers."""
        print(f"\n🌡️  [{self.location}] Weather Reading:")
        print(f"    Temperature: {temperature}°C")
        print(f"    Humidity: {humidity}%")
        print(f"    Raining: {'Yes 🌧️' if is_raining else 'No ☀️'}")
        
        event = GraphEvent(
            type=EventType.DATA_CHANGE,
            data={
                "temperature": temperature,
                "humidity": humidity,
                "is_raining": is_raining,
                "sensor_id": self.id,
                "location": self.location
            },
            source_id=self.id
        )
        await self.notify_observers(event)


class CloseValveNode(BaseNode):
    """
    Handles CLOSE valve commands.
    Converts routing decision to LoRaWAN payload 0x00 (close).
    """
    
    async def update(self, event: GraphEvent) -> None:
        if event.type != EventType.ROUTING_DECISION:
            return
        
        original_data = event.data.get("original_data", {})
        reason = "Rain detected" if original_data.get("is_raining") else "Condition triggered"
        
        print(f"\n� CLOSE VALVE Command")
        print(f"    Reason: {reason}")
        print(f"    Payload: 0x00")
        
        command_event = GraphEvent(
            type=EventType.DATA_CHANGE,
            data={
                "payload": "0x00",
                "command": "close_valve",
                "triggered_by": original_data
            },
            source_id=self.id
        )
        await self.notify_observers(command_event)


class OpenValveNode(BaseNode):
    """
    Handles OPEN valve commands.
    Converts routing decision to LoRaWAN payload 0x01 (open).
    """
    
    async def update(self, event: GraphEvent) -> None:
        if event.type != EventType.ROUTING_DECISION:
            return
        
        original_data = event.data.get("original_data", {})
        temp = original_data.get("temperature", 0)
        humidity = original_data.get("humidity", 0)
        
        if temp > 35:
            reason = f"High temperature ({temp}°C)"
        elif humidity < 30:
            reason = f"Low humidity ({humidity}%)"
        else:
            reason = "Condition triggered"
        
        print(f"\n🟢 OPEN VALVE Command")
        print(f"    Reason: {reason}")
        print(f"    Payload: 0x01")
        
        command_event = GraphEvent(
            type=EventType.DATA_CHANGE,
            data={
                "payload": "0x01",
                "command": "open_valve",
                "triggered_by": original_data
            },
            source_id=self.id
        )
        await self.notify_observers(command_event)


class ResultLoggerNode(BaseNode):
    """Logs the final result of the LoRaWAN operation."""
    
    async def update(self, event: GraphEvent) -> None:
        if event.type == EventType.COMPUTATION_RESULT:
            print(f"\n✅ LoRaWAN Success:")
            print(f"    Device: {event.data.get('device_id')}")
            print(f"    Status: {event.data.get('status')}")
            print(f"    Payload Sent: {event.data.get('payload_sent')}")
        
        elif event.type == EventType.ERROR:
            print(f"\n❌ LoRaWAN Error:")
            print(f"    Error: {event.data.get('error')}")


# ==================== Main Demo ====================

async def main():
    print("=" * 60)
    print("🌾 Smart Irrigation System - LoRaWAN Demo")
    print("=" * 60)
    
    # Start mock TTN server
    runner = await start_mock_server()
    print("🚀 Mock TTN server running on localhost:8888\n")
    
    # Create the graph
    graph = ObserverGraph()
    
    # 1. Weather Sensor Node
    weather_sensor = WeatherSensorNode(
        node_id="weather_sensor",
        location="Field A - North"
    )
    
    # 2. Switch Node - Routes to different handler nodes
    router = SwitchNode(
        node_id="irrigation_router",
        config={
            "rules": [
                {
                    "rain-detected": {
                        "condition": {"==": [{"var": "is_raining"}, True]},
                        "then": "close_valve_handler"  # Route to close valve node
                    }
                },
                {
                    "high-temperature": {
                        "condition": {">": [{"var": "temperature"}, 35]},
                        "then": "open_valve_handler"  # Route to open valve node
                    }
                },
                {
                    "low-humidity": {
                        "condition": {"<": [{"var": "humidity"}, 30]},
                        "then": "open_valve_handler"  # Route to open valve node
                    }
                }
            ],
            "default_target": None  # No action if no condition matches
        }
    )
    
    # 3. Valve Command Handlers (separate nodes for different actions)
    close_valve_handler = CloseValveNode(node_id="close_valve_handler")
    open_valve_handler = OpenValveNode(node_id="open_valve_handler")
    
    # 4. LoRaWAN Downlink Node
    lorawan_valve = LoRaWANDownlinkNode(
        node_id="lorawan_valve",
        config={
            "network_provider": "TTN",
            "api_url": "http://localhost:8888/api/v3/as/applications/farm/devices/valve-01/down/push",
            "api_key": "NNSXS.demo-api-key-for-testing",
            "device_id": "valve-01",
            "f_port": 10
        }
    )
    
    # 5. Result Logger
    result_logger = ResultLoggerNode(node_id="result_logger")
    
    # Add all nodes to graph
    for node in [weather_sensor, router, close_valve_handler, open_valve_handler, lorawan_valve, result_logger]:
        graph.add_node(node)
    
    # Connect the pipeline
    #
    #  weather_sensor --> router --[rain]-------> close_valve_handler --> lorawan_valve --> logger
    #                           \--[hot/dry]----> open_valve_handler  --/
    #
    graph.add_edge("weather_sensor", "irrigation_router")
    graph.add_edge("irrigation_router", "close_valve_handler")
    graph.add_edge("irrigation_router", "open_valve_handler")
    graph.add_edge("close_valve_handler", "lorawan_valve")
    graph.add_edge("open_valve_handler", "lorawan_valve")
    graph.add_edge("lorawan_valve", "result_logger")
    
    print("📊 Pipeline Created:")
    print("    WeatherSensor -> Router -> [CloseValve/OpenValve] -> LoRaWAN -> Logger\n")
    
    # ==================== Test Scenarios ====================
    
    print("\n" + "=" * 60)
    print("📋 SCENARIO 1: Rain Detected -> Close Valve")
    print("=" * 60)
    await weather_sensor.send_reading(
        temperature=25.0,
        humidity=80.0,
        is_raining=True
    )
    await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("📋 SCENARIO 2: High Temperature -> Open Valve")
    print("=" * 60)
    await weather_sensor.send_reading(
        temperature=38.5,
        humidity=45.0,
        is_raining=False
    )
    await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("📋 SCENARIO 3: Low Humidity -> Open Valve")
    print("=" * 60)
    await weather_sensor.send_reading(
        temperature=28.0,
        humidity=25.0,
        is_raining=False
    )
    await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("📋 SCENARIO 4: Normal Conditions (No Action)")
    print("=" * 60)
    await weather_sensor.send_reading(
        temperature=22.0,
        humidity=55.0,
        is_raining=False
    )
    await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total commands sent to TTN: {len(received_commands)}")
    for i, cmd in enumerate(received_commands, 1):
        payload = cmd.get("downlinks", [{}])[0].get("frm_payload", "")
        # Decode base64 to show hex
        import base64
        try:
            hex_val = base64.b64decode(payload).hex()
            print(f"  {i}. Payload: {payload} (0x{hex_val})")
        except:
            print(f"  {i}. Payload: {payload}")
    
    print("\n✨ Demo completed!")
    
    # Cleanup
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Configuration Reference

### Required Settings

```python
{
    "network_provider": "TTN",       # "TTN", "ChirpStack", or "Helium"
    "api_url": "https://...",        # Network server API endpoint
    "api_key": "secret",             # Authentication key (sensitive)
    "device_id": "my-device",        # Target device DevEUI or ID
}
```

### Optional Settings

```python
{
    "payload": "0x00",     # Default payload (hex or plain text)
    "f_port": 1,           # LoRaWAN port (1-223)
    "timeout": 30,         # Request timeout (seconds)
    "retries": 3,          # Max retry attempts
    "retry_delay": 1,      # Delay between retries (seconds)
}
```

---

## Supported Network Providers

### The Things Network (TTN)

```python
config = {
    "network_provider": "TTN",
    "api_url": "https://eu1.cloud.thethings.network/api/v3/as/applications/{app-id}/devices/{device-id}/down/push",
    "api_key": "NNSXS.xxxxxxxx",  # TTN API Key
    "device_id": "my-device"
}
```

API Regions:
- EU: `eu1.cloud.thethings.network`
- US: `nam1.cloud.thethings.network`
- AU: `au1.cloud.thethings.network`

### ChirpStack

```python
config = {
    "network_provider": "ChirpStack",
    "api_url": "http://localhost:8080/api/devices/{dev-eui}/queue",
    "api_key": "your-chirpstack-api-key",
    "device_id": "0011223344556677"
}
```

### Helium

```python
config = {
    "network_provider": "Helium",
    "api_url": "https://console.helium.com/api/v1/down/{device-id}/{downlink-key}",
    "api_key": "your-helium-api-key",
    "device_id": "my-helium-device"
}
```

---

## Payload Encoding

The processor automatically converts payloads to Base64:

| Input Format | Example | Base64 Output |
|--------------|---------|---------------|
| Hex (0x prefix) | `0x01020304` | `AQIDBA==` |
| Hex (plain) | `01020304` | `AQIDBA==` |
| Plain text | `hello` | `aGVsbG8=` |

### Dynamic Payload via Event

Override the default payload by including `payload` in the event data:

```python
event = GraphEvent(
    type=EventType.DATA_CHANGE,
    data={"payload": "0xFF"}  # Override config payload
)
```

---

## Middleware

### LoRaWANValidationMiddleware

Validates configuration before sending (automatically added):

- Checks `api_url`, `api_key`, `device_id` are not empty
- Validates payload size (max 242 bytes)
- Logs warnings for large payloads (>51 bytes)

### LoRaWANLoggingMiddleware

Logs all operations with payload truncation (automatically added).

---

## Error Handling

The node returns `EventType.ERROR` events for:

| Error | Description |
|-------|-------------|
| `401 Unauthorized` | Invalid API key |
| `404 Not Found` | Device not found |
| `Timeout` | Request timeout after retries |
| `Validation Error` | Missing required config fields |

Example error event:

```python
GraphEvent(
    type=EventType.ERROR,
    data={
        "error": "HTTP request error: 401 Unauthorized",
        "device_id": "my-device",
        "original_request": {...}
    }
)
```

---

## LoRaWAN Payload Size Limits

| Data Rate | Max Payload (bytes) |
|-----------|---------------------|
| DR0 (SF12) | 51 |
| DR1 (SF11) | 51 |
| DR2 (SF10) | 51 |
| DR3 (SF9) | 115 |
| DR4 (SF8) | 222 |
| DR5 (SF7) | 242 |

> **Tip**: Keep payloads under 51 bytes for maximum compatibility across all data rates.
