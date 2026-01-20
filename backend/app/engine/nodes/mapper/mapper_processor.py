import logging
from typing import Dict, Any, Optional, List
import jmespath
from json_logic import jsonLogic

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)


class MappingError(Exception):
    """Base exception for mapping errors."""
    pass


class MissingRequiredFieldError(MappingError):
    """Raised when a required field is missing."""
    pass


class MapperProcessor(IProcessor):
    """
    Processor that transforms and maps JSON data structures.

    Supports:
    - Field selection and filtering
    - Field renaming/remapping
    - Nested field access via JMESPath expressions
    - Array operations (map, filter) with JsonLogic
    - Optional type transformations

    Config format:
    {
        "mode": "object",  # or "array"
        "mappings": [
            {
                "source": "user.profile.name",  # JMESPath expression
                "target": "name",               # Output field name
                "default": None,                # Default if source not found
                "required": False,              # If True, error when missing
                "transform": "string"           # Optional type coercion
            }
        ],
        "array_settings": {
            "source_path": "data.items",
            "filter": {">": [{"var": "price"}, 10]},  # JsonLogic filter
            "item_mappings": [...]
        },
        "error_handling": {
            "on_missing_required": "error",  # error|skip|null
            "on_transform_error": "skip"     # error|skip|original
        }
    }
    """

    def __init__(self, config: Dict[str, Any]):
        self.mode = config.get("mode", "object")
        self.mappings = config.get("mappings", [])
        self.array_settings = config.get("array_settings", {})
        self.error_handling = config.get("error_handling", {
            "on_missing_required": "error",
            "on_transform_error": "skip"
        })

        self._compiled_mappings = self._compile_mappings(self.mappings)

    def can_handle(self, event: GraphEvent) -> bool:
        """Can handle any event type that contains data."""
        return event.data is not None

    async def process(self, event: GraphEvent, context: Dict[str, Any]) -> Optional[GraphEvent]:
        """Transform the event data according to the configured mappings."""
        try:
            if self.mode == "array":
                result = self._process_array(event.data)
            else:
                result = self._process_object(event.data)
            return self._create_success_event(result, event, context["node_id"])

        except MappingError as e:
            logger.error(f"Mapping error: {str(e)}")
            return self._create_error_event(str(e), event, context["node_id"])
        except Exception as e:
            logger.error(f"Unexpected error in mapper: {str(e)}")
            return self._create_error_event(f"Mapper processing error: {str(e)}", event, context["node_id"])

    def _compile_mappings(self, mappings: List[Dict]) -> List[Dict]:
        """Pre-compile JMESPath expressions for better performance."""
        compiled = []
        for mapping in mappings:
            compiled_mapping = mapping.copy()
            source = mapping.get("source", "")
            try:
                compiled_mapping["_compiled"] = jmespath.compile(source)
            except jmespath.exceptions.JMESPathError as e:
                logger.warning(f"Invalid JMESPath expression '{source}': {e}")
                compiled_mapping["_compiled"] = None
            compiled.append(compiled_mapping)
        return compiled

    def _process_object(self, data: Any) -> Dict[str, Any]:
        """Process data in object mode - apply mappings to create new structure."""
        result = {}

        for mapping in self._compiled_mappings:
            try:
                value = self._extract_value(data, mapping)
                target = mapping.get("target")

                if value is not None or not mapping.get("required", False):
                    if "transform" in mapping and value is not None:
                        value = self._apply_transform(value, mapping["transform"])

                    if value is not None or mapping.get("default") is not None:
                        final_value = value if value is not None else mapping.get("default")
                        self._set_nested_value(result, target, final_value)

            except MissingRequiredFieldError:
                if self.error_handling.get("on_missing_required") == "error":
                    raise
                elif self.error_handling.get("on_missing_required") == "null":
                    self._set_nested_value(result, mapping.get("target"), None)
                # "skip" means we don't add the field at all

        return result

    def _process_array(self, data: Any) -> List[Dict[str, Any]]:
        """Process data in array mode - extract array and apply mappings to each item."""
        array_config = self.array_settings
        source_path = array_config.get("source_path", "")

        if source_path:
            source_array = jmespath.search(source_path, data)
        else:
            source_array = data

        if not isinstance(source_array, list):
            raise MappingError(f"Source path '{source_path}' did not resolve to an array")

        if "filter" in array_config:
            filter_condition = array_config["filter"]
            source_array = [
                item for item in source_array
                if jsonLogic(filter_condition, item)
            ]

        item_mappings = array_config.get("item_mappings", [])
        if item_mappings:
            compiled_item_mappings = self._compile_mappings(item_mappings)

            result = []
            for item in source_array:
                mapped_item = {}
                for mapping in compiled_item_mappings:
                    value = self._extract_value(item, mapping)
                    target = mapping.get("target")
                    if value is not None:
                        if "transform" in mapping:
                            value = self._apply_transform(value, mapping["transform"])
                        self._set_nested_value(mapped_item, target, value)
                    elif mapping.get("default") is not None:
                        self._set_nested_value(mapped_item, target, mapping.get("default"))
                result.append(mapped_item)
            return result

        return source_array

    def _extract_value(self, data: Any, mapping: Dict) -> Any:
        """Extract a value from data using the compiled JMESPath expression."""
        compiled = mapping.get("_compiled")
        source = mapping.get("source", "")

        if compiled is None:
            # Fallback to runtime compilation
            try:
                value = jmespath.search(source, data)
            except jmespath.exceptions.JMESPathError:
                value = None
        else:
            value = compiled.search(data)

        if value is None:
            if mapping.get("required", False):
                raise MissingRequiredFieldError(f"Required field '{source}' not found")
            return mapping.get("default")

        return value

    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply a type transformation to a value."""
        if value is None:
            return None

        transforms = {
            "string": str,
            "number": lambda v: float(v) if '.' in str(v) else int(v),
            "integer": int,
            "float": float,
            "boolean": bool,
            "lowercase": lambda v: str(v).lower(),
            "uppercase": lambda v: str(v).upper(),
            "trim": lambda v: str(v).strip(),
        }

        if transform not in transforms:
            logger.warning(f"Unknown transform '{transform}', returning original value")
            return value

        try:
            return transforms[transform](value)
        except (ValueError, TypeError) as e:
            if self.error_handling.get("on_transform_error") == "error":
                raise MappingError(f"Transform '{transform}' failed: {e}")
            elif self.error_handling.get("on_transform_error") == "original":
                return value
            return None  # "skip"

    def _set_nested_value(self, obj: Dict, path: str, value: Any):
        """Set a value in a nested dict structure using dot notation."""
        keys = path.split(".")
        current = obj

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _create_success_event(self, result: Any, original_event: GraphEvent, node_id: str) -> GraphEvent:
        """Create a success event with the mapped data."""
        return GraphEvent(
            type=EventType.COMPUTATION_RESULT,
            data=result,
            source_id=node_id,
            metadata={
                "status": "success",
                "mapper_mode": self.mode,
                "mappings_applied": len(self.mappings) if self.mode == "object" else len(self.array_settings.get("item_mappings", [])),
                **original_event.metadata
            }
        )

    def _create_error_event(self, error_message: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        """Create an error event."""
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
