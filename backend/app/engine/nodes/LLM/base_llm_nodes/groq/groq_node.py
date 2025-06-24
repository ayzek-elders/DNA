import logging 

from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.LLM.base_llm_nodes.groq.groq_processor import GroqProcessor
# from app.engine.nodes.LLM.base_llm_nodes.groq.groq_middleware import TokenCountLogger

class GroqNode(BaseNode):
    def __init__(self, node_id, node_type = "base", initial_data = None, config = None, api_key = None):
        super().__init__(node_id, node_type, initial_data, config)
        self.add_processor(GroqProcessor(config, api_key))
        