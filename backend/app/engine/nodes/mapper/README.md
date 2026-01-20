# Mapper Node

JSON transformation node for filtering, selecting, renaming fields, and reformatting data structures from upstream nodes (HTTP responses, MQTT messages, etc.).

## Node

| Node | Type | Description |
|------|------|-------------|
| `MapperNode` | TRANSFORM | Transforms JSON data using JMESPath expressions and JsonLogic filters |

## Installation

Dependencies are already included in the project:

```bash
uv sync
```

## Basic Usage

### Object Mode (Field Selection & Renaming)

```python
from app.engine.graph.graph import ObserverGraph
from app.engine.nodes.mapper import MapperNode

graph = ObserverGraph()

mapper = MapperNode(
    node_id="transform_response",
    config={
        "mappings": [
            {"source": "user.name", "target": "userName"},
            {"source": "user.email", "target": "email"},
            {"source": "timestamp", "target": "createdAt"}
        ]
    }
)

graph.add_node(mapper)
```

### Array Mode (Filter & Map)

```python
mapper = MapperNode(
    node_id="filter_products",
    config={
        "mode": "array",
        "array_settings": {
            "source_path": "data.items",
            "filter": {">": [{"var": "price"}, 10]},  # JsonLogic filter
            "item_mappings": [
                {"source": "name", "target": "productName"},
                {"source": "price", "target": "cost"}
            ]
        }
    }
)
```

---

## Example: HTTP Response Transformation Pipeline

A complete example showing HTTP response data being transformed before further processing.

```python
import asyncio
from app.engine.graph.graph import ObserverGraph
from app.engine.graph.graph_event import GraphEvent, EventType
from app.engine.nodes.http import HTTPGetRequestNode
from app.engine.nodes.mapper import MapperNode
from app.engine.nodes.base_node import BaseNode


class DisplayNode(BaseNode):
    """Displays transformed data."""

    async def update(self, event: GraphEvent) -> None:
        if event.type == EventType.COMPUTATION_RESULT:
            print(f"Transformed Data: {event.data}")


async def main():
    graph = ObserverGraph()

    # 1. HTTP Node - fetches user data from API
    http_node = HTTPGetRequestNode(
        node_id="fetch_users",
        config={"timeout": 30}
    )

    # 2. Mapper Node - extracts and transforms relevant fields
    mapper = MapperNode(
        node_id="transform_users",
        config={
            "mappings": [
                {"source": "content.data.id", "target": "userId"},
                {"source": "content.data.name", "target": "userName"},
                {"source": "content.data.email", "target": "email", "transform": "lowercase"},
                {"source": "content.data.company.name", "target": "company"},
                {"source": "status", "target": "httpStatus", "transform": "integer"}
            ]
        }
    )

    # 3. Display Node - shows the result
    display = DisplayNode(node_id="display")

    # Add nodes
    graph.add_node(http_node)
    graph.add_node(mapper)
    graph.add_node(display)

    # Connect pipeline: HTTP -> Mapper -> Display
    graph.add_edge("fetch_users", "transform_users")
    graph.add_edge("transform_users", "display")

    # Trigger the pipeline
    event = GraphEvent(
        type=EventType.DATA_CHANGE,
        data={"url": "https://jsonplaceholder.typicode.com/users/1"}
    )
    await graph.trigger_event("fetch_users", event)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example: IoT Data Processing with Array Filtering

Filter and transform sensor readings from MQTT messages.

```python
import asyncio
import sys
from app.engine.graph.graph import ObserverGraph
from app.engine.graph.graph_event import GraphEvent, EventType
from app.engine.nodes.mqtt import MQTTSubscriberNode
from app.engine.nodes.mapper import MapperNode
from app.engine.nodes.base_node import BaseNode


class AlertNode(BaseNode):
    """Processes high-value sensor readings."""

    async def update(self, event: GraphEvent) -> None:
        if event.type == EventType.COMPUTATION_RESULT:
            readings = event.data
            for reading in readings:
                print(f"High Reading Alert: {reading}")


async def main():
    graph = ObserverGraph()

    # 1. MQTT Subscriber - receives batch sensor data
    subscriber = MQTTSubscriberNode(
        node_id="sensor_batch",
        config={
            "credential": {"hostname": "localhost", "port": 1883},
            "subscription_settings": {
                "topics": [{"topic": "factory/batch/#", "qos": 1}]
            }
        }
    )

    # 2. Mapper Node - filters high readings and transforms
    mapper = MapperNode(
        node_id="filter_high_readings",
        config={
            "mode": "array",
            "array_settings": {
                "source_path": "payload.readings",
                "filter": {">": [{"var": "value"}, 100]},  # Only values > 100
                "item_mappings": [
                    {"source": "sensor_id", "target": "sensor"},
                    {"source": "value", "target": "reading"},
                    {"source": "timestamp", "target": "time"}
                ]
            }
        }
    )

    # 3. Alert Node
    alert = AlertNode(node_id="alert")

    # Add and connect
    graph.add_node(subscriber)
    graph.add_node(mapper)
    graph.add_node(alert)

    graph.add_edge("sensor_batch", "filter_high_readings")
    graph.add_edge("filter_high_readings", "alert")

    await graph.start()
    print("Listening for batch sensor data on factory/batch/#...")

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        await graph.stop()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
```

Test with:

```bash
mosquitto_pub -t "factory/batch/line1" -m '{"readings": [{"sensor_id": "s1", "value": 50, "timestamp": "2024-01-20T10:00:00Z"}, {"sensor_id": "s2", "value": 150, "timestamp": "2024-01-20T10:00:01Z"}, {"sensor_id": "s3", "value": 200, "timestamp": "2024-01-20T10:00:02Z"}]}'
```

Output: Only s2 and s3 will be processed (value > 100).

---

## Configuration Reference

### Mode

```python
"mode": "object"  # Default: transform single object
"mode": "array"   # Process arrays with filtering
```

### Mappings (Object Mode)

```python
"mappings": [
    {
        "source": "user.profile.name",  # JMESPath expression
        "target": "userName",           # Output field name
        "default": "Unknown",           # Default if source not found
        "required": False,              # If True, error when missing
        "transform": "uppercase"        # Optional transformation
    }
]
```

### Array Settings (Array Mode)

```python
"array_settings": {
    "source_path": "data.items",                    # JMESPath to source array
    "filter": {">": [{"var": "price"}, 10]},        # JsonLogic filter (optional)
    "item_mappings": [                              # Mappings applied to each item
        {"source": "name", "target": "productName"},
        {"source": "price", "target": "cost", "transform": "float"}
    ]
}
```

### Error Handling

```python
"error_handling": {
    "on_missing_required": "error",  # "error" | "skip" | "null"
    "on_transform_error": "skip"     # "error" | "skip" | "original"
}
```

---

## JMESPath Expressions

The mapper uses [JMESPath](https://jmespath.org/) for field access:

| Expression | Description | Example Input | Result |
|------------|-------------|---------------|--------|
| `user.name` | Nested field | `{"user": {"name": "John"}}` | `"John"` |
| `items[0]` | Array index | `{"items": ["a", "b"]}` | `"a"` |
| `items[*].name` | All names in array | `{"items": [{"name": "A"}, {"name": "B"}]}` | `["A", "B"]` |
| `items[?price>\`10\`]` | Filter in expression | `{"items": [...]}` | Filtered array |
| `length(items)` | Array length | `{"items": [1, 2, 3]}` | `3` |

---

## Transformations

| Transform | Description | Example |
|-----------|-------------|---------|
| `string` | Convert to string | `123` → `"123"` |
| `integer` | Convert to integer | `"42"` → `42` |
| `float` | Convert to float | `"99.99"` → `99.99` |
| `number` | Smart number conversion | `"42"` → `42`, `"3.14"` → `3.14` |
| `boolean` | Convert to boolean | `1` → `True` |
| `uppercase` | Uppercase string | `"hello"` → `"HELLO"` |
| `lowercase` | Lowercase string | `"HELLO"` → `"hello"` |
| `trim` | Trim whitespace | `"  hi  "` → `"hi"` |

---

## Nested Output Structure

Create nested output by using dot notation in targets:

```python
config = {
    "mappings": [
        {"source": "firstName", "target": "user.name.first"},
        {"source": "lastName", "target": "user.name.last"},
        {"source": "email", "target": "user.contact.email"}
    ]
}

# Input:  {"firstName": "John", "lastName": "Doe", "email": "john@example.com"}
# Output: {"user": {"name": {"first": "John", "last": "Doe"}, "contact": {"email": "john@example.com"}}}
```

---

## Event Types

| EventType | Direction | Description |
|-----------|-----------|-------------|
| `COMPUTATION_RESULT` | Outbound | Emitted with transformed data |
| `ERROR` | Outbound | Emitted on mapping errors |

### Output Event Structure

```python
GraphEvent(
    type=EventType.COMPUTATION_RESULT,
    data={"userName": "John", "email": "john@example.com"},
    metadata={
        "status": "success",
        "mapper_mode": "object",
        "mappings_applied": 2
    }
)
```

### Error Event Structure

```python
GraphEvent(
    type=EventType.ERROR,
    data={
        "error": "Required field 'user.id' not found",
        "original_data": {...}
    },
    metadata={"status": "error"}
)
```

---

## Middleware

### MapperLoggingMiddleware

Logs mapping operations (included by default):

```python
from app.engine.nodes.mapper import MapperLoggingMiddleware

mapper.add_middleware(MapperLoggingMiddleware())
```

### MapperValidationMiddleware

Validate input data types before processing:

```python
from app.engine.nodes.mapper import MapperValidationMiddleware

mapper.add_middleware(MapperValidationMiddleware(
    allowed_types=["dict", "list"]  # Only allow dict or list inputs
))
```

---

## Common Use Cases

### 1. API Response Cleaning

```python
# Remove internal fields, rename for frontend
config = {
    "mappings": [
        {"source": "data.user.id", "target": "id"},
        {"source": "data.user.displayName", "target": "name"},
        {"source": "data.user.avatarUrl", "target": "avatar"}
        # internal_id, created_at, etc. are excluded
    ]
}
```

### 2. Data Normalization

```python
# Normalize different API response formats
config = {
    "mappings": [
        {"source": "result.items || data.records || rows", "target": "items"},
        {"source": "result.total || data.count || length(rows)", "target": "total"}
    ]
}
```

### 3. Flattening Nested Data

```python
# Flatten for database insertion
config = {
    "mappings": [
        {"source": "order.id", "target": "order_id"},
        {"source": "order.customer.name", "target": "customer_name"},
        {"source": "order.customer.email", "target": "customer_email"},
        {"source": "order.items[0].product", "target": "first_product"}
    ]
}
```

### 4. Array Aggregation

```python
# Extract specific fields from array
config = {
    "mappings": [
        {"source": "users[*].email", "target": "all_emails"},
        {"source": "users[*].name", "target": "all_names"},
        {"source": "length(users)", "target": "user_count"}
    ]
}
```
