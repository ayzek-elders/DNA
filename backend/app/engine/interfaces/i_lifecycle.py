from abc import ABC, abstractmethod


class ILifecycle(ABC):
    """Interface for nodes that require lifecycle management (start/stop)."""

    @abstractmethod
    async def start(self) -> None:
        """Start the node (e.g., connect to external service)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the node (e.g., disconnect from external service)."""
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the node is currently running."""
        ...