from typing import Any, Dict

from dna_core.engine.nodes.base_node import BaseNode
from dna_core.engine.nodes.email.sender.emailsend_processor import MailSenderProcessor


class MailSenderNode(BaseNode):
    """
    Node for sending emails via SMTP.

    A specialized node that sends emails with configurable SMTP settings,
    retry logic, and support for both manual configuration and dynamic data.
    Includes built-in email logging middleware.

    Args:
        node_id (str): Unique identifier for the node.
        node_type (str, optional): Type identifier for the node. Defaults to "MAIL_SENDER_NODE".
        initial_data (Any, optional): Initial data for the node. Defaults to None.
        config (Dict[str, Any], optional): Configuration dictionary for the node. Defaults to None.
            Supported config options:
            - credential (dict): SMTP server credentials
                - username (str): SMTP username
                - password (str): SMTP password
                - server_name (str): SMTP server hostname
                - server_port (int): SMTP server port (default: 25)
                - use_ssl (bool): Whether to use SSL (default: False)
            - email_settings (dict, optional): Default email settings
                - from (str): Default sender email
                - cc (list/str): Default CC recipients
                - bcc (list/str): Default BCC recipients
                - subject (str): Default subject line
                - signature (str): Default email signature
                - html (bool): Whether to send HTML emails (default: False)
                - priority (str): Email priority - low/normal/high (default: normal)
            - retry_settings (dict, optional): Retry configuration
                - max_retries (int): Maximum retry attempts (default: 3)
                - retry_delay (int): Delay between retries in seconds (default: 2)
                - retry_on_connection_error (bool): Retry on connection errors (default: True)
    """
    
    def __init__(
        self,
        node_id: str,
        node_type: str = "MAIL_SENDER_NODE",
        initial_data: Any = None,
        config: Dict[str, Any] = None
    ):
        default_config = {
            "credential": {
                "server_port": 25,
                "use_ssl": False
            },
            "email_settings": {
                "html": False,
                "priority": "normal"
            },
            "retry_settings": {
                "max_retries": 3,
                "retry_delay": 2,
                "retry_on_connection_error": True
            }
        }
        
        merged_config = self._deep_merge_config(default_config, config or {})
    
        super().__init__(node_id, node_type, initial_data, merged_config)
        
        # Add the mail sender processor
        self.add_processor(MailSenderProcessor(merged_config))

    def _deep_merge_config(self, default: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge configuration dictionaries.
        User config takes priority over defaults.
        """
        result = default.copy()
        
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_config(result[key], value)
            else:
                result[key] = value
        
        return result