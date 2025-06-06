from abc import abstractmethod, ABC

from  app.engine.graph.graph_event import GraphEvent

class IObserver(ABC):
    @abstractmethod
    async def update(self, event: GraphEvent) -> None:
        pass