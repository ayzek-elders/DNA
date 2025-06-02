**Core Concepts:**

*   **`Graph`**: The main orchestrator. It manages nodes, edges, and global middleware.
*   **`BaseNode`**: The fundamental building block of the graph. Each node can:
    *   Hold data and configuration.
    *   Process incoming events using `IProcessor` implementations.
    *   Have `IMiddleware` applied before and after processing.
    *   Notify `IObserver` (other nodes or custom observers) about events.
    *   Connect to other nodes via edges (directed).
*   **`GraphEvent`**: Represents an event flowing through the graph. It includes:
    *   `id`: Unique event identifier.
    *   `type`: `EventType` enum (e.g., `DATA_CHANGE`, `COMPUTATION_RESULT`).
    *   `source_id`: ID of the node that originated the event.
    *   `target_id`: Optional ID of the intended recipient node.
    *   `timestamp`: Event creation time.
    *   `data`: The actual payload of the event.
    *   `metadata`: Additional information about the event.
    *   `priority`: Event priority.
*   **Interfaces:**
    *   **`IProcessor`**: Defines how a node processes an event.
        *   `process(event, context)`: Contains the core logic for handling an event.
        *   `can_handle(event)`: Determines if the processor is suitable for a given event.
    *   **`IMiddleware`**: Allows for pre-processing and post-processing of events at the node level or globally.
        *   `before_process(event, node_id)`: Modifies the event or performs actions before the main processor.
        *   `after_process(event, result, node_id)`: Modifies the result or performs actions after the main processor.
    *   **`IObserver`**: Defines how an entity (like another node) reacts to an event.
        *   `update(event)`: Called when a subject node notifies its observers.
    *   **`ISubject`**: Defines an entity that can be observed (e.g., `BaseNode`).
        *   `add_observer(observer)`
        *   `remove_observer(observer)`
        *   `notify_observers(event)`

**How to Use:**

1.  **Define Custom Nodes:**
    *   Create classes that inherit from `BaseNode`.
    *   In the constructor, you can set `node_id`, `node_type`, `initial_data`, and `config`.
    *   Add custom `IProcessor` implementations to handle specific event types or logic.

    ```python
    from backend.app.engine.nodes.base_node import BaseNode
    from backend.app.engine.interfaces.i_processor import IProcessor
    from backend.app.engine.interfaces.graph_event import GraphEvent, EventType
    from typing import Dict, Any

    class MyCustomProcessor(IProcessor):
        async def process(self, event: GraphEvent, context: Dict[str, Any]):
            # Your processing logic here
            print(f"Node {context['node_id']} processing event: {event.data}")
            return GraphEvent(
                type=EventType.COMPUTATION_RESULT,
                data={"result": event.data * 2},
                source_id=context['node_id']
            )

        def can_handle(self, event: GraphEvent) -> bool:
            return event.type == EventType.DATA_CHANGE and isinstance(event.data, int)

    class MyNode(BaseNode):
        def __init__(self, node_id: str, initial_data: Any = None):
            super().__init__(node_id, "my_custom_node", initial_data)
            self.add_processor(MyCustomProcessor())
    ```

2.  **Define Custom Middleware (Optional):**
    *   Create classes that implement `IMiddleware`.
    *   Implement `before_process` and/or `after_process`.

    ```python
    from backend.app.engine.interfaces.İ_middleware import IMiddleware # Note: Ensure correct import for İ_middleware.py
    from backend.app.engine.interfaces.graph_event import GraphEvent
    from typing import Optional

    class LoggingMiddleware(IMiddleware):
        async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
            print(f"MIDDLEWARE (Before) - Node {node_id}: Received event {event.id} of type {event.type.value}")
            return event

        async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
            print(f"MIDDLEWARE (After) - Node {node_id}: Processed event {event.id}, result: {result.data if result else 'None'}")
            return result
    ```

3.  **Build the Graph:**
    *   Instantiate `ObserverGraph`.
    *   Create instances of your custom nodes (or `BaseNode` directly).
    *   Add nodes to the graph using `graph.add_node()`.
    *   Connect nodes by adding edges using `graph.add_edge(from_node_id, to_node_id)`.
    *   Optionally, add global middleware using `graph.add_global_middleware()`.

    ```python
    from backend.app.engine.graph.graph import ObserverGraph
    # Assuming MyNode and LoggingMiddleware are defined as above

    # 1. Initialize Graph
    graph = ObserverGraph()

    # 2. Create Nodes
    node_a = MyNode("node_A", initial_data=10)
    node_b = BaseNode("node_B") # Can also act as a simple observer/router

    # 3. Add Nodes to Graph
    graph.add_node(node_a)
    graph.add_node(node_b)

    # 4. Add Edges (Node A will notify Node B)
    graph.add_edge("node_A", "node_B")

    # 5. Add Global Middleware (Optional)
    logging_mw = LoggingMiddleware()
    graph.add_global_middleware(logging_mw)
    ```

4.  **Trigger Events:**
    *   Create a `GraphEvent` instance.
    *   Use `graph.trigger_event(node_id, event)` to send an event to a specific node in the graph.
    *   The node will process the event, and if it has outgoing edges, it will notify the connected nodes.

    ```python
    import asyncio
    from backend.app.engine.interfaces.graph_event import GraphEvent, EventType
    # Assuming graph is set up as above

    async def main():
        # Trigger an event on Node A
        initial_event = GraphEvent(
            type=EventType.DATA_CHANGE,
            data=5, # This will be processed by MyCustomProcessor in node_A
            # source_id will be set by the node, target_id can be set if event is for a specific node initially
        )
        # Triggering event on node_A, so it becomes the first recipient
        await graph.trigger_event("node_A", initial_event)

        # Node A processes, its MyCustomProcessor runs,
        # then it notifies Node B (its observer) with the COMPUTATION_RESULT event.
        # Node B, being a BaseNode without specific processors, will receive the update.
        # Its update method will be called, which by default might not do much with the data
        # unless a processor is added or its update method is overridden.

        summary = graph.get_graph_summary()
        print("\nGraph Summary:")
        import json
        print(json.dumps(summary, indent=2))

    if __name__ == "__main__":
        asyncio.run(main())
    ```

**Key Features & Functionality:**

*   **Event-Driven Architecture:** Processing is triggered by events flowing through the graph.
*   **Decoupled Components:** Nodes, processors, and middleware are largely independent, promoting modularity.
*   **Observer Pattern:** Nodes act as subjects and observers, enabling easy communication and data propagation.
*   **Middleware Support:** Inject custom logic before and after event processing in nodes.
*   **Configurable Nodes:** Each node can have its own specific configuration.
*   **Event Filtering:** `BaseNode` includes `_event_filters` (though `add_event_filter` needs to initialize `self._event_filters = []` in `__init__` if not already done) to decide whether to process an incoming event.
*   **State Management:** Nodes maintain their own state (`NodeState`: IDLE, PROCESSING, ERROR, DISABLED).
*   **Metrics & History:** `BaseNode` keeps basic metrics (events processed/sent, errors) and a history of recent events.
*   **Graph Summary:** `graph.get_graph_summary()` provides an overview of the graph structure, node types, and edges.

**To Extend and Customize:**

*   Implement various `IProcessor` classes for different data transformations, computations, or I/O operations.
*   Create specialized `BaseNode` subclasses for common node types (e.g., input nodes, output nodes, transformation nodes).
*   Develop more sophisticated `IMiddleware` for concerns like authentication, validation, rate limiting, or advanced logging/tracing.
*   Enhance `GraphEvent` with more specific event types or data structures as needed.
*   Implement custom `IObserver` classes for tasks beyond simple node-to-node communication (e.g., writing to a database, sending notifications to external systems).

This framework provides a solid foundation for building complex, real-time data processing pipelines.
