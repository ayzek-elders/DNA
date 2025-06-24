from app.engine.graph.graph_event import GraphEvent
from app.engine.interfaces.i_processor import IProcessor
from typing import Dict, Any
from abc import ABC, abstractmethod

class IGroqProcessor(IProcessor):
    @abstractmethod
    async def invoke(self, question: str, system_prompt: str = None):
        pass
    
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        pass