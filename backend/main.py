import asyncio
from typing import Dict, Any, Optional
from app.engine.interfaces.İ_middleware import IMiddleware
from app.engine.nodes.base_node import BaseNode
from app.engine.interfaces.i_processor import IProcessor
from app.engine.graph.graph_event import GraphEvent, EventType
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
    
class FilterProcessor(IProcessor):
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        if event.data % 8 != 0:
            return None
        return event

    def can_handle(self, event: GraphEvent) -> bool:
        return event.type == EventType.COMPUTATION_RESULT

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
class FilterNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "filter_node", None)
        self.add_processor(FilterProcessor())
        
    async def update(self, event: GraphEvent):
        return await super().update(event)

class ResultNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "result_node", None)
        self.results = []

    async def update(self, event: GraphEvent):
        self.results.append(event.data)
        return await super().update(event)

async def main():
    # Create the graph
    graph = ObserverGraph()

    double_node = DoubleNode("double")
    add_ten_node = AddTenNode("add_ten")
    add_ten_node2 = AddTenNode("add_ten2")
    filter_node = FilterNode("filter")
    result_node = ResultNode("result")
    
    # Add nodes to graph
    graph.add_node(double_node)
    graph.add_node(add_ten_node)
    graph.add_node(add_ten_node2)
    graph.add_node(filter_node)
    graph.add_node(result_node)

    # Set up processing chain:
    # double → add_ten → result
    graph.add_edge("double", "add_ten")
    graph.add_edge("double", "add_ten2")
    graph.add_edge("add_ten", "filter")
    graph.add_edge("add_ten2", "filter")
    graph.add_edge("filter", "result")

    # Add logging
    graph.add_global_middleware(SimpleLoggingMiddleware())

    # Process some numbers
    print("\nProcessing numbers through the graph...")
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
        await asyncio.sleep(0.5)  # Small delay for better readability

    # Print final results
    print("\nAll processing completed!")
    print(f"Input numbers: {test_numbers}")
    print(f"Results: {result_node.results}")

if __name__ == "__main__":
    asyncio.run(main())