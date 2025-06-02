from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

class EventType(Enum):
    DATA_CHANGE = "data_change"
    COMPUTATION_RESULT = "computation_result"
    ERROR = "error"
    ALERT = "alert"
    NOTIFICATION = "notification"
    CUSTOM = "custom"

class NodeState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class GraphEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.CUSTOM
    source_id: str = ""
    target_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'timestamp': self.timestamp,
            'data': self.data,
            'metadata': self.metadata,
            'priority': self.priority
        }