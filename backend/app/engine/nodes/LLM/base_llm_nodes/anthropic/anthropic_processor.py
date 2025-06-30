from app.engine.interfaces.i_processor import IProcessor
from app.engine.graph.graph_event import EventType, GraphEvent
from langchain_groq import ChatGroq
from typing import Dict, Any

import os 

class anthropic_node(IProcessor):
    