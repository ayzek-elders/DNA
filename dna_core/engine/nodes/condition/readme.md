## Configuration

### Basic Configuration Format

```python
config = {
    "rules": [
        {
            "rule-name": {
                "condition": {JsonLogic condition},
                "then": "target-node-id"
            }
        }
    ],
    "default_target": "default-node-id"  # Optional
}
```

### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `rules` | List[Dict] | Yes | List of rule objects containing conditions and targets |
| `default_target` | String | No | Target node when no rules match |

## JsonLogic Syntax Guide

JsonLogic uses a consistent `{"operator": ["values"...]}` format. Here are the most common operators:

### Comparison Operators

```python
# Equality
{"==": [{"var": "status"}, "active"]}

# Greater than
{">": [{"var": "score"}, 50]}

# Less than
{"<": [{"var": "age"}, 18]}

# Greater than or equal
{">=": [{"var": "rating"}, 4.5]}

# Less than or equal
{"<=": [{"var": "price"}, 100]}

# Not equal
{"!=": [{"var": "status"}, "inactive"]}
```

### Logical Operators

```python
# AND - All conditions must be true
{
    "and": [
        {"==": [{"var": "status"}, "active"]},
        {"==": [{"var": "plan"}, "premium"]}
    ]
}

# OR - At least one condition must be true
{
    "or": [
        {"==": [{"var": "priority"}, "urgent"]},
        {"==": [{"var": "important"}, True]}
    ]
}

# NOT - Negate a condition
{"!": {"==": [{"var": "status"}, "blocked"]}}
```

### Array and String Operations

```python
# Check if array contains value
{"in": ["apple", {"var": "fruits"}]}

# Check if string contains substring
{"in": ["error", {"var": "message"}]}

# Access array element by index
{"var": "items.0"}  # First element
{"var": "items.1"}  # Second element
```

### Accessing Nested Data

```python
# Nested object properties
{"var": "user.profile.name"}
{"var": "order.billing.address.city"}

# Array elements in nested objects
{"var": "user.orders.0.total"}
```

## Usage Examples

### Example 1: Simple Number Routing

Route numbers to different handlers based on value:

```python
from app.engine.nodes.condition.switch_node import SwitchNode

# Configuration
config = {
    "rules": [
        {
            "high-number": {
                "condition": {">": [{"var": "value"}, 10]},
                "then": "high_handler"
            }
        },
        {
            "low-number": {
                "condition": {"<": [{"var": "value"}, 5]},
                "then": "low_handler"
            }
        }
    ],
    "default_target": "medium_handler"
}

# Create the switch node
number_switch = SwitchNode("number_router", config)

# Test data
test_data = [
    {"value": 15},  # → high_handler
    {"value": 3},   # → low_handler
    {"value": 7}    # → medium_handler (default)
]
```

### Example 2: User Role-Based Routing

Route based on user roles and message content:

```python
config = {
    "rules": [
        {
            "admin-user": {
                "condition": {"==": [{"var": "role"}, "admin"]},
                "then": "admin_area"
            }
        },
        {
            "urgent-message": {
                "condition": {"in": ["urgent", {"var": "message"}]},
                "then": "urgent_queue"
            }
        }
    ],
    "default_target": "normal_queue"
}

# Test data
test_cases = [
    {"role": "admin", "message": "Hello"},           # → admin_area
    {"role": "user", "message": "This is urgent!"}, # → urgent_queue
    {"role": "user", "message": "Normal message"}   # → normal_queue
]
```

### Example 3: Complex Nested Data Routing

Handle complex nested objects:

```python
config = {
    "rules": [
        {
            "vip-customer": {
                "condition": {"==": [{"var": "user.type"}, "vip"]},
                "then": "vip_service"
            }
        },
        {
            "big-order": {
                "condition": {">": [{"var": "order.amount"}, 100]},
                "then": "special_handling"
            }
        }
    ],
    "default_target": "standard_service"
}

# Test data
test_data = {
    "user": {
        "name": "Alice",
        "type": "vip"
    },
    "order": {
        "id": 1,
        "amount": 50
    }
}
# This would route to "vip_service" due to user.type == "vip"
```

### Example 4: Multiple Conditions

Combine multiple conditions with AND/OR logic:

```python
config = {
    "rules": [
        {
            "premium-and-active": {
                "condition": {
                    "and": [
                        {"==": [{"var": "status"}, "active"]},
                        {"==": [{"var": "plan"}, "premium"]}
                    ]
                },
                "then": "premium_features"
            }
        },
        {
            "urgent-or-important": {
                "condition": {
                    "or": [
                        {"==": [{"var": "priority"}, "urgent"]},
                        {"==": [{"var": "important"}, True]}
                    ]
                },
                "then": "priority_queue"
            }
        }
    ],
    "default_target": "normal_processing"
}

# Test cases
test_cases = [
    {
        "status": "active", 
        "plan": "premium", 
        "priority": "normal", 
        "important": False
    },  # → premium_features (both conditions in AND are true)
    
    {
        "status": "inactive", 
        "plan": "basic", 
        "priority": "urgent", 
        "important": False
    },  # → priority_queue (priority is urgent)
    
    {
        "status": "inactive", 
        "plan": "basic", 
        "priority": "normal", 
        "important": False
    }   # → normal_processing (no rules match)
]
```

## Integration with Graph Workflow

### Adding to Graph

```python
from app.engine.graph.graph import ObserverGraph
from app.engine.nodes.condition.switch_node import SwitchNode

# Create graph
graph = ObserverGraph()

# Create switch node
switch_node = SwitchNode("my_switch", config)
graph.add_node(switch_node)

# Create target nodes
target1 = SomeTargetNode("target1")
target2 = SomeTargetNode("target2")
graph.add_node(target1)
graph.add_node(target2)

# Connect edges
graph.add_edge("my_switch", "target1")
graph.add_edge("my_switch", "target2")

# Trigger events
event = GraphEvent(type=EventType.DATA_CHANGE, data=your_data)
await graph.trigger_event("my_switch", event)
```

### Event Flow

1. **Input**: SwitchProcessor receives a `GraphEvent` with data
2. **Evaluation**: Each rule is evaluated against `event.data` using JsonLogic
3. **Routing**: First matching rule determines the target node
4. **Output**: Returns a `ROUTING_DECISION` event with target information
5. **Fallback**: Uses `default_target` if no rules match

## Event Types

### Input Events
The SwitchProcessor can handle any event type and evaluates rules against `event.data`.

### Output Events

#### ROUTING_DECISION (Success)
```python
{
    "type": EventType.ROUTING_DECISION,
    "data": {
        "original_data": {...},        # Original event data
        "target_node": "target_id",    # Where to route
        "rule_name": "rule-name",      # Which rule matched
        "condition": {...},            # The JsonLogic condition
        "routing_type": "jsonlogic_switch"
    },
    "metadata": {
        "status": "routed",
        "target": "target_id"
    }
}
```

#### ERROR Event
```python
{
    "type": EventType.ERROR,
    "data": {
        "error": "Error message",
        "original_data": {...},
        "routing_type": "jsonlogic_switch"
    },
    "metadata": {
        "status": "error"
    }
}
```
