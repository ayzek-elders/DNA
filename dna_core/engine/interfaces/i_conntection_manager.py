from abc import ABC, abstractmethod

class IConnectionManager(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Establish the connection."""
        ...
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is currently established."""
        ...