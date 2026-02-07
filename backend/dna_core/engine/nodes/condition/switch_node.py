import logging
from datetime import datetime
from typing import Dict, Any

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.nodes.base_node import BaseNode
from dna_core.engine.nodes.condition.switch_processor import SwitchProcessor

logger = logging.getLogger(__name__)


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

    async def notify_observers(self, event: GraphEvent) -> None:
        """
        Override to route events only to the target node specified in routing decisions.
        """
        event.source_id = self.id
        self._event_history.append(event)
        self._metrics['events_sent'] += 1
        self._metrics['last_activity'] = datetime.now().isoformat()

        # For routing decisions, only notify the target node
        if event.type == EventType.ROUTING_DECISION:
            target_node_id = event.data.get("target_node")
            if target_node_id:
                # Find the target observer
                target_observer = None
                for observer in self._observers:
                    if hasattr(observer, 'id') and observer.id == target_node_id:
                        target_observer = observer
                        break

                if target_observer:
                    logger.info(f"Node {self.id} routing event to {target_node_id}")
                    try:
                        await target_observer.update(event)
                    except Exception as e:
                        logger.error(f"Error notifying observer {target_node_id}: {e}")
                else:
                    logger.warning(f"Target node {target_node_id} not found in observers")
                return

        # For non-routing events, broadcast to all observers (default behavior)
        logger.info(f"Node {self.id} sending event {event.type.value} to {len(self._observers)} observers")
        for observer in self._observers:
            try:
                await observer.update(event)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")
