from typing import Any, Dict

from app.engine.nodes.base_node import BaseNode
from app.engine.nodes.iot.lorawan.lorawan_processor import LoRaWANProcessor
from app.engine.nodes.iot.lorawan.lorawan_middleware import (
    LoRaWANValidationMiddleware,
    LoRaWANLoggingMiddleware
)


class LoRaWANDownlinkNode(BaseNode):
    """
    Node for sending LoRaWAN downlink messages to IoT devices.

    A specialized SINK node that sends commands to LoRaWAN devices via
    network server APIs (The Things Network, ChirpStack, Helium).

    Args:
        node_id (str): Unique identifier for the node.
        node_type (str, optional): Type identifier. Defaults to "LORAWAN_DOWNLINK_NODE".
        initial_data (Any, optional): Initial data for the node.
        config (Dict[str, Any], optional): Configuration dictionary.
            Required config options:
            - network_provider (str): "TTN", "ChirpStack", or "Helium"
            - api_url (str): Network server API endpoint
            - api_key (str): Authentication key (sensitive)
            - device_id (str): Target device DevEUI or ID

            Optional config options:
            - payload (str): Default payload (Hex string or plain text)
            - f_port (int): LoRaWAN port number (default: 1)
            - timeout (int): Request timeout in seconds (default: 30)
            - retries (int): Max retry attempts (default: 3)
            - retry_delay (int): Delay between retries in seconds (default: 1)
    """

    def __init__(
        self,
        node_id: str,
        node_type: str = "LORAWAN_DOWNLINK_NODE",
        initial_data: Any = None,
        config: Dict[str, Any] = None
    ):
        default_config = {
            "network_provider": "TTN",
            "api_url": "",
            "api_key": "",
            "device_id": "",
            "payload": "",
            "f_port": 1,
            "timeout": 30,
            "retries": 3,
            "retry_delay": 1
        }

        merged_config = {**default_config, **(config or {})}

        super().__init__(node_id, node_type, initial_data, merged_config)

        self.add_middleware(LoRaWANValidationMiddleware(merged_config))

        self.add_middleware(LoRaWANLoggingMiddleware())

        self.add_processor(LoRaWANProcessor(merged_config))

    def get_info(self) -> Dict[str, Any]:
        """Get node information including LoRaWAN-specific details."""
        info = super().get_info()
        info.update({
            "network_provider": self.config.get("network_provider"),
            "device_id": self.config.get("device_id"),
            "f_port": self.config.get("f_port"),
            "api_url": self.config.get("api_url"),
        })
        return info
