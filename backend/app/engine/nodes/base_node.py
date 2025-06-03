from collections import deque
from datetime import datetime
import logging
from typing import Any, Callable, Dict, List, Set
from  app.engine.graph.graph_event import EventType, GraphEvent, NodeState
from  app.engine.interfaces.i_observer import IObserver
from  app.engine.interfaces.i_processor import IProcessor
from  app.engine.interfaces.i_subject import ISubject
from  app.engine.interfaces.i_middleware import IMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseNode(IObserver, ISubject):
    def __init__(self,
                 node_id: str,
                 node_type: str = "base",
                 initial_data: Any = None,
                 config: Dict[str, Any] = None):
        self.id = node_id
        self.node_type = node_type
        self.data = initial_data
        self.config = config or {}
        self.state = NodeState.IDLE
        self.created_at = datetime.now().isoformat()

        self._observers: Set[IObserver] = set()
        self._outgoing_edges: Set['BaseNode'] = set()
        self._incoming_edges: Set['BaseNode'] = set()

        self._processors: List[IProcessor] = []
        self._middleware: List[IMiddleware] = []
        self._event_filters:List[Callable[[GraphEvent], bool]] = []
        self._event_history: deque = deque(maxlen=100)
        self._metrics = {
            'events_processed': 0,
            'events_sent': 0,
            'errors': 0,
            'last_activity': None
        }
    
    def add_observer(self, observer: IObserver) -> None:
        self._observers.add(observer)

    def remove_observer(self, observer: IObserver) -> None:
        self._observers.discard(observer)

    async def notify_observers(self, event: GraphEvent):
        event.source_id = self.id
        self._event_history.append(event)
        self._metrics['events_sent'] += 1
        self._metrics['last_activity'] = datetime.now().isoformat()

        logger.info(f"Node {self.id} sending event {event.type.value} to {len(self._observers)} observers")

        for observer in self._observers:
            try:
                await observer.update(event)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")

    async def update(self, event: GraphEvent) -> None:
        if not self._should_process_event(event):
            return
        
        self.state = NodeState.PROCESSING
        self._metrics['events_processed'] += 1

        try:
            processed_event = event
            for middleware in self._middleware:
                processed_event = await middleware.before_process(processed_event, self.id)
            
            result_event = None
            for processor in self._processors:
                if processor.can_handle(processed_event):
                    context = self._build_context()
                    result_event = await processor.process(processed_event, context)
                    break
                
            for middleware in self._middleware:
                result_event = await middleware.after_process(processed_event, result_event, self.id)

            if result_event:
                await self.notify_observers(result_event)
            
            self.state = NodeState.IDLE

        except Exception as e:
            self.state = NodeState.ERROR
            self._metrics['errors'] += 1
            logger.error(f"Error in node {self.id}: {e}")
            
            error_event = self.create_error_event(str(e), event, self.id)
            await self.notify_observers(error_event)

    def add_processor(self, processor: IProcessor) -> None:
        self._processors.append(processor)
    
    def add_middleware(self, middleware: IMiddleware) -> None:
        self._middleware.append(middleware)
    
    def add_event_filter(self, filter_func: Callable[[GraphEvent], bool]) -> None:
        self._event_filters.append(filter_func)
    
    def add_edge_to(self, target: 'BaseNode') -> None:
        if target not in self._outgoing_edges:
            self._outgoing_edges.add(target)
            target._incoming_edges.add(self)
            self.add_observer(target)

    def remove_edge_to(self, target: 'BaseNode') -> None:
        self._outgoing_edges.discard(target)
        target._incoming_edges.discard(self)
        self.remove_observer(target)

    def _should_process_event(self, event: GraphEvent) -> bool:
        if self.state == NodeState.DISABLED:
            return False
        if self._event_filters:
            for filter_func in self._event_filters:
                if not filter_func(event):
                    return False
        
        return True
    
    
    
    def _build_context(self) -> Dict[str, Any]:
        return {
            'node_id': self.id,
            'node_type': self.node_type,
            'config': self.config,
            'current_data': self.data,
            'incoming_nodes': [node.id for node in self._incoming_edges],
            'outgoing_nodes': [node.id for node in self._outgoing_edges],
            'metrics': self._metrics.copy(),
            'recent_events': list(self._event_history)[-10:]
        }

    def get_info(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.node_type,
            'state': self.state.value,
            'data': self.data,
            'config': self.config,
            'metrics': self._metrics,
            'processors': len(self._processors),
            'middleware': len(self._middleware)
        }
    def create_error_event(self, error_message: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        return GraphEvent(
            type=EventType.ERROR,
            data={
                "error": error_message,
                "original_request": original_event.data
            },
            source_id=node_id,
            metadata={
                "status": "error",
                **original_event.metadata
            }
        )