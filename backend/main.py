import asyncio
from typing import Dict, Any, Optional
from app.engine.interfaces.İ_middleware import IMiddleware
from app.engine.nodes.base_node import BaseNode
from app.engine.interfaces.i_processor import IProcessor
from app.engine.interfaces.graph_event import GraphEvent, EventType
from app.engine.graph.graph import ObserverGraph

# Processor that doubles a number
class DoubleProcessor(IProcessor):
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        number = event.data
        result = number * 2
        print(f"Doubling {number} = {result}")
        return GraphEvent(
            type=EventType.COMPUTATION_RESULT,
            data=result,
            source_id=context['node_id']
        )

    def can_handle(self, event: GraphEvent) -> bool:
        return event.type == EventType.DATA_CHANGE and isinstance(event.data, (int, float))

# Processor that adds 10 to a number
class AddTenProcessor(IProcessor):
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        number = event.data
        result = number + 10
        print(f"Adding 10 to {number} = {result}")
        return GraphEvent(
            type=EventType.COMPUTATION_RESULT,
            data=result,
            source_id=context['node_id']
        )

    def can_handle(self, event: GraphEvent) -> bool:
        return isinstance(event.data, (int, float))

# Simple logging middleware
class SimpleLoggingMiddleware(IMiddleware):
    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        print(f"\n→ Node {node_id} received: {event.data}")
        return event

    async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
        if result:
            print(f"← Node {node_id} output: {result.data}")
        return result

# Nodes for our math operations
class DoubleNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "double_node", None)
        self.add_processor(DoubleProcessor())

class AddTenNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "add_ten_node", None)
        self.add_processor(AddTenProcessor())

# Result collector node
class ResultNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "result_node", None)
        self.results = []

    async def update(self, event: GraphEvent):
        self.results.append(event.data)
        print(f"✓ Final result: {event.data}")
        return await super().update(event)

async def main():
    # Create the graph
    graph = ObserverGraph()

    # Create nodes:
    # double_node: multiplies input by 2
    # add_ten_node: adds 10 to input
    # result_node: collects final results
    double_node = DoubleNode("double")
    add_ten_node = AddTenNode("add_ten")
    add_ten_node2 = AddTenNode("add_ten2")
    result_node = ResultNode("result")

    # Add nodes to graph
    graph.add_node(double_node)
    graph.add_node(add_ten_node)
    graph.add_node(add_ten_node2)
    graph.add_node(result_node)

    # Set up processing chain:
    # double → add_ten → result
    graph.add_edge("double", "add_ten")
    graph.add_edge("double", "add_ten2")
    graph.add_edge("add_ten", "result")
    graph.add_edge("add_ten2", "result")

    # Add logging
    graph.add_global_middleware(SimpleLoggingMiddleware())

    # Process some numbers
    print("\nProcessing numbers through the graph...")
    print("Flow: Input → Double → Add 10 → Result")
    print("-" * 40)

    # Test with different numbers
    test_numbers = [5, 10, 15]
    for number in test_numbers:
        print(f"\nProcessing number: {number}")
        event = GraphEvent(
            type=EventType.DATA_CHANGE,
            data=number
        )
        await graph.trigger_event("double", event)
        await asyncio.sleep(5)  # Small delay for better readability

    # Print final results
    print("\nAll processing completed!")
    print(f"Input numbers: {test_numbers}")
    print(f"Final results: {result_node.results}")

if __name__ == "__main__":
    asyncio.run(main())