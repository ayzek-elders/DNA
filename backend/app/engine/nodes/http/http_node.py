from typing import Any, Dict, Optional
from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.http.http_processor import HTTPGetRequestProcessor, HTTPPostRequestProcessor

class HTTPGetRequestNode(BaseNode):
    """
    Node for handling HTTP GET requests.

    A specialized node that performs HTTP GET requests with configurable timeout,
    retries, and headers. Includes built-in logging middleware.

    Args:
        node_id (str): Unique identifier for the node.
        node_type (str, optional): Type identifier for the node. Defaults to "HTTP_GET_REQUEST_NODE".
        initial_data (Any, optional): Initial data for the node. Defaults to None.
        config (Dict[str, Any], optional): Configuration dictionary for the node. Defaults to None.
            Supported config options:
            - timeout (int): Request timeout in seconds
            - max_retries (int): Maximum number of retry attempts
            - retry_delay (int): Delay between retries in seconds
            - headers (dict): Custom HTTP headers
    """
    def __init__(
        self,
        node_id: str,
        node_type: str = "HTTP_GET_REQUEST_NODE",
        initial_data: Any = None,
        config: Dict[str, Any] = None
    ):
        default_config = {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1,
            "headers": {
                "User-Agent": "DNA-Engine/1.0",
                "Accept": "application/json, text/plain, */*"
            }
        }
        
        merged_config = {**default_config, **(config or {})}
        
        super().__init__(node_id, node_type, initial_data, merged_config)
        
        self.add_processor(HTTPGetRequestProcessor(merged_config))

class HTTPPostRequestNode(BaseNode):
    """
    Node for handling HTTP POST requests.

    A specialized node that performs HTTP POST requests with configurable timeout,
    retries, and headers. Includes built-in logging middleware.

    Args:
        node_id (str): Unique identifier for the node.
        node_type (str, optional): Type identifier for the node. Defaults to "HTTP_POST_REQUEST_NODE".
        initial_data (Any, optional): Initial data for the node. Defaults to None.
        config (Dict[str, Any], optional): Configuration dictionary for the node. Defaults to None.
            Supported config options:
            - timeout (int): Request timeout in seconds
            - max_retries (int): Maximum number of retry attempts
            - retry_delay (int): Delay between retries in seconds
            - headers (dict): Custom HTTP headers with Content-Type defaulting to application/json
    """
    def __init__(
        self,
        node_id: str,
        node_type: str = "HTTP_POST_REQUEST_NODE",
        initial_data: Any = None,
        config: Dict[str, Any] = None
    ):
        default_config = {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1,
            "headers": {
                "User-Agent": "DNA-Engine/1.0",
                "Content-Type": "application/json"
            }
        }
        
        merged_config = {**default_config, **(config or {})}
        
        super().__init__(node_id, node_type, initial_data, merged_config)
        
        self.add_processor(HTTPPostRequestProcessor(merged_config))