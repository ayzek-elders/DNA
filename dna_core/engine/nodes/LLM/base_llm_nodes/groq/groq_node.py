import logging

from dna_core.engine.nodes.base_node import BaseNode
from dna_core.engine.nodes.LLM.base_llm_nodes.groq.groq_processor import GroqProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroqNode(BaseNode):
    def __init__(self, node_id, node_type="base", initial_data=None, config=None):
        super().__init__(node_id, node_type, initial_data, config)

        try:
            self.add_processor(GroqProcessor(config))

        except Exception as e:
            logger.error(f"Error occurs: {e}")
