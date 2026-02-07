"""
dna_core - Event-driven graph engine for data processing pipelines.

This package provides a flexible, extensible framework for building
event-driven data processing workflows using a graph-based architecture.
"""

from dna_core.engine.graph.graph import ObserverGraph
from dna_core.engine.graph.graph_event import GraphEvent, EventType, NodeState
from dna_core.engine.nodes.base_node import BaseNode

from dna_core.engine.nodes.http.http_node import (
    HTTPGetRequestNode,
    HTTPPostRequestNode,
    HTTPPutRequestNode,
    HTTPDeleteRequestNode,
    HTTPPatchRequestNode,
)
from dna_core.engine.nodes.email.sender.emailsend_node import MailSenderNode
from dna_core.engine.nodes.condition.switch_node import SwitchNode
from dna_core.engine.nodes.mapper import (
    MapperNode,
    MapperProcessor,
    MappingError,
    MissingRequiredFieldError,
    MapperLoggingMiddleware,
    MapperValidationMiddleware,
)
from dna_core.engine.nodes.mqtt import MQTTSubscriberNode, MQTTPublisherNode

# Note: GroqNode requires langchain-groq to be installed separately
# Import it directly if needed: from dna_core.engine.nodes.LLM.base_llm_nodes.groq import GroqNode

__version__ = "0.1.0"

__all__ = [
    # Core graph
    "ObserverGraph",
    "GraphEvent",
    "EventType",
    "NodeState",
    "BaseNode",
    # HTTP nodes
    "HTTPGetRequestNode",
    "HTTPPostRequestNode",
    "HTTPPutRequestNode",
    "HTTPDeleteRequestNode",
    "HTTPPatchRequestNode",
    # Email node
    "MailSenderNode",
    # Routing node
    "SwitchNode",
    # Data transformation (Mapper)
    "MapperNode",
    "MapperProcessor",
    "MappingError",
    "MissingRequiredFieldError",
    "MapperLoggingMiddleware",
    "MapperValidationMiddleware",
    # MQTT nodes
    "MQTTSubscriberNode",
    "MQTTPublisherNode",
    # Version
    "__version__",
]
