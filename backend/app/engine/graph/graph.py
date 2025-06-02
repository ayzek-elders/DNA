import logging
from typing import Any, Dict, List, Optional

from  app.engine.graph.graph_event import GraphEvent
from  app.engine.interfaces.İ_middleware import IMiddleware
from  app.engine.nodes.base_node import BaseNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ObserverGraph:    
    def __init__(self):
        self._nodes: Dict[str, BaseNode] = {}
        self._global_middleware: List[IMiddleware] = []
    
    def add_node(self, node: BaseNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Node {node.id} already exists")
        
        for middleware in self._global_middleware:
            node.add_middleware(middleware)
        
        self._nodes[node.id] = node
        logger.info(f"Added node {node.id} of type {node.node_type}")
    
    def get_node(self, node_id: str) -> Optional[BaseNode]:
        return self._nodes.get(node_id)
    
    def add_edge(self, from_id: str, to_id: str) -> None:
        from_node = self._nodes.get(from_id)
        to_node = self._nodes.get(to_id)
        
        if not from_node or not to_node:
            raise ValueError(f"Node not found: {from_id} or {to_id}")
        
        from_node.add_edge_to(to_node)
        logger.info(f"Added edge {from_id} -> {to_id}")
    
    def add_global_middleware(self, middleware: IMiddleware) -> None:
        self._global_middleware.append(middleware)
        for node in self._nodes.values():
            node.add_middleware(middleware)
    
    async def trigger_event(self, node_id: str, event: GraphEvent) -> None:
        node = self._nodes.get(node_id)
        if node:
            await node.update(event)
    
    def get_graph_summary(self) -> Dict[str, Any]:
        return {
            'total_nodes': len(self._nodes),
            'node_types': {},
            'nodes': {node_id: node.get_info() for node_id, node in self._nodes.items()},
            'edges': self._get_edges()
        }
    
    def _get_edges(self) -> List[Dict[str, str]]:
        edges = []
        for node in self._nodes.values():
            for target in node._outgoing_edges:
                edges.append({'from': node.id, 'to': target.id})
        return edges