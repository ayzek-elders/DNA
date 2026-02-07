from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from  dna_core.engine.graph.graph_event import GraphEvent

class IProcessor(ABC):
    @abstractmethod
    async def process(self, event: GraphEvent, context:Dict[str,Any]):
        pass
    @abstractmethod
    def can_handle(self, event: GraphEvent) -> bool:
        pass