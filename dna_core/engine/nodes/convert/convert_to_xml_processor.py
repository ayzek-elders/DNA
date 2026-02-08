import logging
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, Optional

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)


class ConvertToXMLProcessor(IProcessor):
    """
    Processor that converts JSON data to XML format.

    Supports:
    - Dictionary to XML element conversion
    - Array handling (creates <Item> elements)
    - Nested structures
    - Pretty-printed output

    Config format:
    {
        "root_element": "Root",  # Name of the root XML element (default: "Root")
        "item_element": "Item",  # Name for array item elements (default: "Item")
        "indent": "  ",          # Indentation for pretty printing (default: two spaces)
        "encoding": "utf-8"      # XML encoding (default: "utf-8")
    }
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        self.root_element = config.get("root_element", "Root")
        self.item_element = config.get("item_element", "Item")
        self.indent = config.get("indent", "  ")
        self.encoding = config.get("encoding", "utf-8")

    def can_handle(self, event: GraphEvent) -> bool:
        return event.data is not None

    async def process(self, event: GraphEvent, context: Dict[str, Any]) -> Optional[GraphEvent]:
        try:
            xml_string = self._convert_to_xml(event.data)
            return self._create_success_event(xml_string, event, context["node_id"])

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON input: {str(e)}"
            logger.error(error_msg)
            return self._create_error_event(error_msg, event, context["node_id"])
        except Exception as e:
            error_msg = f"XML conversion error: {str(e)}"
            logger.error(error_msg)
            return self._create_error_event(error_msg, event, context["node_id"])

    def _convert_to_xml(self, data: Any) -> str:
        """
        Convert Python data structure (from JSON) to XML string.

        Args:
            data: Python dict, list, or primitive to convert

        Returns:
            Pretty-printed XML string
        """
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass

        root = ET.Element(self.root_element)

        if isinstance(data, list):
            for item in data:
                item_element = ET.SubElement(root, self.item_element)
                self._build_xml(item, item_element)
        else:
            self._build_xml(data, root)

        raw_xml = ET.tostring(root, encoding=self.encoding)
        parsed_xml = minidom.parseString(raw_xml)
        return parsed_xml.toprettyxml(indent=self.indent)

    def _build_xml(self, data: Any, parent: ET.Element):
        """
        Recursively processes data (dicts, lists, primitives)
        and attaches them to the XML parent element.

        Args:
            data: The data to process (dict, list, or primitive)
            parent: The parent XML element to attach to
        """
        
        if isinstance(data, dict):
            for key, value in data.items():
                child = ET.SubElement(parent, key)
                self._build_xml(value, child)

        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, self.item_element)
                self._build_xml(item, child)

        else:
            if data is None:
                parent.text = ""
            else:
                parent.text = str(data)

    def _create_success_event(self, xml_result: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        return GraphEvent(
            type=EventType.FILE_CONVERTED,
            data=xml_result,
            source_id=node_id,
            metadata={
                "status": "success",
                "conversion_type": "json_to_xml",
                "root_element": self.root_element,
                **original_event.metadata
            }
        )

    def _create_error_event(self, error_message: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        return GraphEvent(
            type=EventType.ERROR,
            data={
                "error": error_message,
                "original_data": original_event.data
            },
            source_id=node_id,
            metadata={
                "status": "error",
                "conversion_type": "json_to_xml",
                **original_event.metadata
            }
        )
