import logging
from typing import Any, Dict, Optional

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)

class ConvertToHTMLProcessor(IProcessor):
    """
    Processor that converts JSON data to HTML format
    """
    def __init__(self, config):
        super().__init__(config)

    def can_handle(self, event):
        return event.data is not None and isinstance(event.data, (dict, list))

    def process(self, event: GraphEvent, context: Dict[str, Any]) -> Optional[GraphEvent]:
        logger.info("Converting data to HTML format.")

        try:
            html_content = self._convert_to_html(event.data)

            return GraphEvent(
                type=EventType.FILE_CONVERTED,
                data={
                    "content": html_content,
                    "format": "html",
                    "original_data": event.data
                },
                source_id=context.get('node_id', 'unknown'),
                metadata={
                    "status": "success",
                    "output_format": "html",
                    **event.metadata
                }
            )

        except Exception as e:
            logger.error(f"Error converting data to HTML: {str(e)}")
            return self._create_error_event(str(e), original_event=event, node_id=context.get('node_id', 'unknown'))

    def _convert_to_html(self, data):
        style = """
        <style>
            body { font-family: 'Consolas', 'Monaco', monospace; background-color: #1e1e1e; color: #d4d4d4; padding: 20px; }
            .container { margin-left: 15px; border-left: 1px solid #444; padding-left: 15px; transition: border-left 0.2s; }
            .container:hover { border-left: 1px solid #007acc; }

            details { margin: 4px 0; }
            summary { cursor: pointer; color: #9cdcfe; font-weight: bold; outline: none; list-style: none; }
            summary::-webkit-details-marker { display: none; }
            summary:before { content: "▶ "; font-size: 10px; color: #666; }
            details[open] > summary:before { content: "▼ "; }
            summary:hover { color: #4fc1ff; }

            p { margin: 2px 0; }
            strong { color: #9cdcfe; font-weight: normal; }

            .val-str { color: #ce9178; }
            .val-num { color: #b5cea8; }
            .val-bool { color: #569cd6; font-style: italic; }
            .val-null { color: #569cd6; opacity: 0.7; }

            ul { list-style: none; padding-left: 15px; border-left: 1px dashed #333; }
            li { margin: 2px 0; }

            .controls { margin-bottom: 20px; position: sticky; top: 0; background: #1e1e1e; padding: 10px 0; z-index: 100; }
            button { background: #333; color: white; border: 1px solid #555; padding: 5px 10px; cursor: pointer; border-radius: 3px; }
            button:hover { background: #444; }
        </style>
        """

        js = """
        <script>
            const toggleAll = (open) => document.querySelectorAll('details').forEach(d => d.open = open);
        </script>
        """

        controls = """
        <div class="controls">
            <button onclick="toggleAll(true)">Expand All</button>
            <button onclick="toggleAll(false)">Collapse All</button>
        </div>
        """

        body = "".join(self._generate_html(data))
        return f"<!DOCTYPE html><html><head>{style}</head><body>{controls}{body}{js}</body></html>"

    def _generate_html(self, data):
        html_fragments = []

        if isinstance(data, dict):
            html_fragments.append('<div class="container">')
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    html_fragments.append('<details>')
                    html_fragments.append(f'<summary>{key}</summary>')
                    html_fragments.extend(self._generate_html(value))
                    html_fragments.append('</details>')
                else:
                    formatted_val = self._get_value_with_type(value)
                    html_fragments.append(f'<p><strong>{key}:</strong> {formatted_val}</p>')
            html_fragments.append("</div>")

        elif isinstance(data, list):
            html_fragments.append('<ul>')
            for item in data:
                html_fragments.append('<li>')
                if isinstance(item, (dict, list)):
                    html_fragments.extend(self._generate_html(item))
                else:
                    html_fragments.append(self._get_value_with_type(item))
                html_fragments.append("</li>")
            html_fragments.append("</ul>")

        return html_fragments

    def _get_value_with_type(self, value):
        if isinstance(value, bool):
            return f'<span class="val-bool">{str(value).lower()}</span>'
        if isinstance(value, (int, float)):
            return f'<span class="val-num">{value}</span>'
        if value is None:
            return f'<span class="val-null">null</span>'
        return f'<span class="val-str">"{value}"</span>'

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
