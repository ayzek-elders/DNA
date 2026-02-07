from abc import ABC, abstractmethod
from typing import Optional

from  dna_core.engine.graph.graph_event import GraphEvent


class IMiddleware(ABC):
    @abstractmethod
    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        pass
    
    @abstractmethod
    async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
        pass