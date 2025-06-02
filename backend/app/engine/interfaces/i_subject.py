from abc import ABC, abstractmethod
from  app.engine.interfaces.i_observer import IObserver
from  app.engine.interfaces.graph_event import GraphEvent

class ISubject(ABC):
    @abstractmethod
    async def notify_observers(self, event: GraphEvent) -> None:
        pass
    @abstractmethod
    def add_observer(self, observer: IObserver) -> None:
        pass

    @abstractmethod
    def remove_observer(self, observer: IObserver) -> None:
        pass