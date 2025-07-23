from typing import Dict, Any

from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.condition.switch_processor import SwitchProcessor


class SwitchNode(BaseNode):
    """
    A node that routes events based on conditional rules.
    
    This node evaluates incoming events against configured rules and
    routes them to different target nodes based on the conditions.
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        """
        Initialize the switch node.
        
        Args:
            node_id: Unique identifier for the node
            config: Configuration containing rules and optional default target
        """
        super().__init__(node_id, "switch_node", None, config)
        
        # Add the switch processor
        switch_processor = SwitchProcessor(config)
        self.add_processor(switch_processor)
