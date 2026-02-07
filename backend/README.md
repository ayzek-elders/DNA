# DNA Core

**Event-driven graph engine for building data processing pipelines**

DNA Core is a flexible, extensible Python framework for building event-driven data processing workflows using a graph-based architecture. It provides a powerful foundation for creating complex data pipelines with support for HTTP requests, MQTT messaging, email notifications, LLM integrations, and more.

## Features

- **Event-Driven Architecture**: Build reactive pipelines that respond to events flowing through the graph
- **Graph-Based Orchestration**: Connect nodes to create complex data processing workflows
- **Extensible Node System**: Easily create custom nodes by extending base classes
- **Observer Pattern**: Nodes can observe and react to events from other nodes
- **Middleware Support**: Add pre/post-processing hooks for cross-cutting concerns
- **Built-in Node Types**:
  - **HTTP Nodes**: GET, POST, PUT, DELETE, PATCH requests with retry logic
  - **MQTT Nodes**: Subscribe and publish to MQTT brokers
  - **Mapper Node**: Transform JSON data using JMESPath expressions
  - **Switch Node**: Conditional routing based on JSON Logic rules
  - **Email Node**: Send emails via SMTP
  - **LLM Nodes**: Integration with Groq and other LLM providers

## Installation

### From Private PyPI

```bash
pip install dna-core --index-url https://your-private-pypi.com/simple
```

### From GitHub

```bash
pip install git+https://github.com/your-org/dna-core.git
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/dna-core.git
cd dna-core

# Install in editable mode
pip install -e .
```

## Quick Start

Here's a simple example that fetches data from an API and processes it:

```python
from dna_core import ObserverGraph, HTTPGetRequestNode, MapperNode, EventType

# Create a graph
graph = ObserverGraph()

# Create nodes
http_node = HTTPGetRequestNode(
    node_id="fetch_data",
    config={
        "url": "https://api.example.com/data",
        "timeout": 10
    }
)

mapper_node = MapperNode(
    node_id="transform_data",
    config={
        "mappings": {
            "id": "data.id",
            "name": "data.attributes.name",
            "value": "data.attributes.value"
        }
    }
)

# Add nodes to graph
graph.add_node(http_node)
graph.add_node(mapper_node)

# Connect nodes
graph.add_edge("fetch_data", "transform_data")

# Start the graph
graph.start()

# Trigger an event
from dna_core import GraphEvent
event = GraphEvent(
    event_type=EventType.DATA_CHANGE,
    source_node_id="fetch_data",
    payload={}
)
graph.trigger_event(event)

# Stop the graph
graph.stop()
```

## Core Concepts

### Graph

The `ObserverGraph` is the central orchestrator that manages nodes and their connections. It handles event routing and lifecycle management.

```python
from dna_core import ObserverGraph

graph = ObserverGraph()
graph.add_node(node)
graph.add_edge(source_id, target_id)
graph.start()
```

### Nodes

Nodes are the building blocks of your pipeline. Each node processes events and can emit new events to downstream nodes.

```python
from dna_core import BaseNode

class CustomNode(BaseNode):
    def __init__(self, node_id, config):
        super().__init__(node_id, config)
        # Custom initialization
```

### Events

Events carry data through the graph. Each event has a type, payload, and metadata.

```python
from dna_core import GraphEvent, EventType

event = GraphEvent(
    event_type=EventType.DATA_CHANGE,
    source_node_id="node1",
    target_node_id="node2",
    payload={"key": "value"}
)
```

### Middleware

Middleware provides hooks for pre and post-processing of events.

```python
from dna_core.engine import IMiddleware

class LoggingMiddleware(IMiddleware):
    def before_process(self, event, node):
        print(f"Processing event in {node.node_id}")

    def after_process(self, event, node, result):
        print(f"Completed processing in {node.node_id}")
```

## Available Nodes

### HTTP Nodes

Make HTTP requests with automatic retry and error handling:

```python
from dna_core import HTTPGetRequestNode, HTTPPostRequestNode

get_node = HTTPGetRequestNode(
    node_id="fetch",
    config={
        "url": "https://api.example.com/resource",
        "headers": {"Authorization": "Bearer token"},
        "timeout": 30,
        "retry_count": 3
    }
)

post_node = HTTPPostRequestNode(
    node_id="create",
    config={
        "url": "https://api.example.com/resource",
        "headers": {"Content-Type": "application/json"},
        "body": {"name": "example"}
    }
)
```

### MQTT Nodes

Connect to MQTT brokers for pub/sub messaging:

```python
from dna_core import MQTTSubscriberNode, MQTTPublisherNode

subscriber = MQTTSubscriberNode(
    node_id="mqtt_sub",
    config={
        "broker": "mqtt.example.com",
        "port": 1883,
        "topic": "sensors/temperature",
        "qos": 1
    }
)

publisher = MQTTPublisherNode(
    node_id="mqtt_pub",
    config={
        "broker": "mqtt.example.com",
        "port": 1883,
        "topic": "commands/actuator",
        "qos": 2
    }
)
```

### Mapper Node

Transform JSON data using JMESPath expressions:

```python
from dna_core import MapperNode

mapper = MapperNode(
    node_id="transform",
    config={
        "mappings": {
            "user_id": "data.id",
            "full_name": "join(' ', [data.first_name, data.last_name])",
            "email": "data.contact.email"
        }
    }
)
```

### Switch Node

Route events based on conditions:

```python
from dna_core import SwitchNode

switch = SwitchNode(
    node_id="router",
    config={
        "routes": {
            "high_priority": {">=": [{"var": "priority"}, 8]},
            "medium_priority": {"and": [
                {">=": [{"var": "priority"}, 4]},
                {"<": [{"var": "priority"}, 8]}
            ]},
            "low_priority": {"<": [{"var": "priority"}, 4]}
        }
    }
)
```

### Email Node

Send emails via SMTP:

```python
from dna_core import MailSenderNode

email_node = MailSenderNode(
    node_id="notify",
    config={
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "your-password",
        "from_address": "notifications@example.com",
        "to_addresses": ["recipient@example.com"]
    }
)
```

### LLM Nodes

Integrate with Large Language Models:

```python
from dna_core import GroqNode

llm_node = GroqNode(
    node_id="ai_processor",
    config={
        "api_key": "your-groq-api-key",
        "model": "llama-3.1-70b-versatile",
        "temperature": 0.7
    }
)
```

## Architecture

DNA Core uses an Observer pattern where:
1. **Graph** orchestrates nodes and manages event flow
2. **Events** carry data and metadata through the graph
3. **Nodes** process events and notify observers (downstream nodes)
4. **Processors** contain the business logic for each node type
5. **Middleware** provides cross-cutting concerns (logging, validation, etc.)
6. **Interfaces** define contracts for extensibility

```
┌─────────────────────────────────────────┐
│         ObserverGraph                   │
│  - Manages nodes and edges              │
│  - Routes events                        │
│  - Handles lifecycle                    │
└──────────────┬──────────────────────────┘
               │
               │ contains
               │
┌──────────────▼──────────────────────────┐
│           Nodes                         │
│  - BaseNode (abstract)                  │
│  - HTTPNode, MQTTNode, etc.             │
│  - Process events via Processors        │
│  - Apply Middleware chains              │
└──────────────┬──────────────────────────┘
               │
               │ uses
               │
┌──────────────▼──────────────────────────┐
│       Interfaces                        │
│  - IProcessor: Event processing logic   │
│  - IMiddleware: Pre/post hooks          │
│  - IObserver: Event notification        │
│  - ISubject: Observer management        │
│  - ILifecycle: Start/stop behavior      │
└─────────────────────────────────────────┘
```

## Documentation

For detailed documentation on specific node types, see:
- [Engine Documentation](dna_core/engine/README.md)
- [MQTT Nodes](dna_core/engine/nodes/mqtt/README.md)
- [Mapper Node](dna_core/engine/nodes/mapper/README.md)
- [Switch Node](dna_core/engine/nodes/condition/readme.md)

## Requirements

- Python >= 3.13
- Dependencies listed in `pyproject.toml`

## License

Proprietary. All rights reserved.

Copyright (c) 2025 Fatih Akkuş, Rabia Akkuş, Muhammed Esad Doğan

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without prior written permission.

## Authors

- Fatih Akkuş <whitebirdsdk@gmail.com>
- Rabia Akkuş <rabia.akkus@gmail.com>
- Muhammed Esad Doğan <esad@gmail.com>

## Contributing

This project uses automated GitHub Actions for CI/CD. See [RELEASE.md](RELEASE.md) for details on the release process.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/dna-core.git
cd dna-core

# Install dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest tests/

# Run linter
uv run ruff check dna_core

# Build package
uv build
```

### Release Process

We use automated releases via GitHub Actions. To release a new version:

```bash
# Bump version (updates pyproject.toml and __init__.py)
python scripts/bump_version.py patch  # or minor, major

# Commit and tag
git add -u
git commit -m "Bump version to X.Y.Z"
git tag -a vX.Y.Z -m "Release X.Y.Z"

# Push (triggers automated build and publish)
git push origin main --tags
```

See [RELEASE.md](RELEASE.md) for complete documentation.

## Support

For support and questions, please contact the development team.
