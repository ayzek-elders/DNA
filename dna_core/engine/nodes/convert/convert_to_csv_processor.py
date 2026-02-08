import json
import logging
from typing import Dict, Any, Optional, Set, List
import csv
from io import StringIO

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)


class ConvertToCSVProcessor(IProcessor):
    """
    Processor that converts nested JSON/dict data to CSV format.

    ### Supports:
    - Nested field flattening with customizable separator
    - Array handling (joins values with semicolon)
    - Multiple output formats (string or array of rows)
    - Configurable CSV delimiter and quote character

    ### Config Format:
    - "separator": ".",           Separator for nested fields (default: ".")
    - "delimiter": ",",           CSV delimiter (default: ",")
    - "quote_char": '"',          CSV quote character (default: '"')
    - "include_headers": true,    Include header row (default: true)
    - "output_format": "string",  "string" or "array" (default: "string")
    - "sort_headers": true        Sort headers alphabetically (default: true)
    
    """

    def __init__(self, config: Dict[str, Any]):
        self.separator = config.get("separator", ".")
        self.delimiter = config.get("delimiter", ",")
        self.quote_char = config.get("quote_char", '"')
        self.include_headers = config.get("include_headers", True)
        self.output_format = config.get("output_format", "string")
        self.sort_headers = config.get("sort_headers", True)

    def can_handle(self, event: GraphEvent) -> bool:
        return event.data is not None

    async def process(self, event: GraphEvent, context: Dict[str, Any]) -> Optional[GraphEvent]:
        try:
            result = self._convert_to_csv(event.data)
            return self._create_success_event(result, event, context["node_id"])
        except Exception as e:
            logger.error(f"Error converting to CSV: {str(e)}")
            return self._create_error_event(str(e), event, context["node_id"])

    def _convert_to_csv(self, data: Any) -> str | List[List[str]]:
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass
            
        if not isinstance(data, list):
            data = [data]

        headers_set = self._get_csv_headers(data, sep=self.separator)
        headers = sorted(list(headers_set)) if self.sort_headers else list(headers_set)

        rows = []
        for item in data:
            row = []
            for header in headers:
                keys = header.split(self.separator)
                val = self._get_deep_value(item, keys)
                row.append(val if val is not None else "")
            rows.append(row)

        if self.output_format == "array":
            result = [headers] + rows if self.include_headers else rows
            return result
        else:
            output = StringIO()
            writer = csv.writer(output, delimiter=self.delimiter, quotechar=self.quote_char)

            if self.include_headers:
                writer.writerow(headers)

            writer.writerows(rows)
            return output.getvalue()

    def _get_csv_headers(self, data: Any, parent_key: str = '', sep: str = '.') -> Set[str]:
        """
        Recursively extract all unique field paths from nested data structures.

        Args:
            data: The data to extract headers from (dict, list, or primitive)
            parent_key: The current path prefix
            sep: Separator for nested keys

        Returns:
            Set of all unique field paths
        """
        columns = set()

        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key

                if isinstance(value, (dict, list)):
                    columns.update(self._get_csv_headers(value, new_key, sep=sep))
                else:
                    columns.add(new_key)

        elif isinstance(data, list):
            for item in data:
                columns.update(self._get_csv_headers(item, parent_key, sep=sep))

        return columns

    def _get_deep_value(self, data: Any, keys: List[str]) -> Any:
        """
        Extract a value from nested data structure using a list of keys.

        Args:
            data: The data structure to extract from
            keys: List of keys representing the path to the value

        Returns:
            The value at the specified path, or None if not found
        """
        if not keys:
            return data

        if isinstance(data, list):
            gathered = []
            for item in data:
                val = self._get_deep_value(item, keys)
                if val is not None:
                    gathered.append(str(val))
            return "; ".join(gathered) if gathered else None

        if isinstance(data, dict):
            current_key = keys[0]
            remaining_keys = keys[1:]

            val = data.get(current_key)

            if val is None:
                return None

            return self._get_deep_value(val, remaining_keys)

        return None

    def _create_success_event(self, result: Any, original_event: GraphEvent, node_id: str) -> GraphEvent:
        return GraphEvent(
            type=EventType.FILE_CONVERTED,
            data=result,
            source_id=node_id,
            metadata={
                "status": "success",
                "format": "csv",
                "output_type": self.output_format,
                "delimiter": self.delimiter,
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
                **original_event.metadata
            }
        )