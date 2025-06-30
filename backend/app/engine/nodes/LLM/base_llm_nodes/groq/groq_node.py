import logging 

from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.LLM.base_llm_nodes.groq.groq_processor import GroqProcessor
from app.engine.nodes.LLM.base_llm_nodes.groq.groq_streaming_processor import GroqStreamProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroqNode(BaseNode):
    def __init__(self, node_id, node_type = "base", initial_data = None, config = None, api_key = None):
        super().__init__(node_id, node_type, initial_data, config)
        
        try:
            if config["streaming"]:
                self.add_processor(GroqStreamProcessor(config, api_key))
            else:
                self.add_processor(GroqProcessor(config, api_key))
        
        except Exception as e:
            logger.error(f"Error occurs: {e}")