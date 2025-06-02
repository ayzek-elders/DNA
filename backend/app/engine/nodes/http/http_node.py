from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.http.http_processor import HTTPGetRequestProcessor


class HTTPGetRequestNode(BaseNode):
    def __init__(self, node_id, node_type = "HTTP_GET_REQUEST_NODE", initial_data = None):
        super().__init__(node_id, node_type, initial_data)
        self.add_processor(HTTPGetRequestProcessor())