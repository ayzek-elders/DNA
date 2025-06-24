import asyncio

from app.engine.nodes.LLM.base_llm_nodes.groq.groq_node import GroqNode
from app.engine.graph.graph_event import GraphEvent, EventType
from app.engine.graph.graph import ObserverGraph
from app.engine.nodes.base_node import BaseNode


GROQ_NODE_ID = "llm_node"
GROQ_NODE_TYPE = "groq_llm_node"
GROQ_CONFIG = {
    "model": "llama3-70b-8192",
    "temperature": 0.7,
    "streaming": True,
}
GROQ_API_KEY = "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"

class ResultNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "result_node", None)
        self.results = []

    async def update(self, event: GraphEvent):
        self.results.append(event.data)
        return await super().update(event)

async def main():
    graph = ObserverGraph()
    groq_node = GroqNode(GROQ_NODE_ID, GROQ_NODE_TYPE, config= GROQ_CONFIG, api_key= GROQ_API_KEY)
    result_node = ResultNode("result_node")
    
    graph.add_node(groq_node)
    graph.add_node(result_node)
    
    graph.add_edge(GROQ_NODE_ID, "result_node")
    
    event = GraphEvent(
        type= EventType.LLM_REQUEST,
        data = "what is the capital of syria?"
    )
    
    await graph.trigger_event("llm_node", event)
    await asyncio.sleep(0.5)

    print(f"result = {result_node.results}")
    
if __name__ == "__main__":
    asyncio.run(main())