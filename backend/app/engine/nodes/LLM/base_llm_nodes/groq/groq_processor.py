from app.engine.nodes.LLM.base_llm_nodes.groq.i_qroq import IGroqProcessor
from app.engine.graph.graph_event import EventType, GraphEvent
from langchain_groq import ChatGroq
from typing import Dict, Any

import os


class GroqProcessor(IGroqProcessor):
    def __init__(self, config: Dict[str, any]):
        super().__init__()
        self.config = config.copy()  # Copy to avoid modifying original config
        api_key = config["api"]

        self.llm = ChatGroq(**self.config)

    async def invoke(self, question: str, system_prompt: str = None):
        """
        Get complete response for a given question

        Args:
            question: User's question
            system_prompt: Optional system prompt to guide the response

        Returns:
            str: Complete response from the LLM
        """
        # Prepare messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": question})

        try:
            # Get complete response
            response = await self.llm.ainvoke(messages)
            return response

        except Exception as e:
            raise Exception(f"Error invoking LLM: {str(e)}")

    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        """
        Process event and return complete response

        Args:
            event: GraphEvent containing the prompt
            context: Context dictionary containing node_id

        Returns:
            str: Complete response from the LLM
        """
        prompt = event.data

        try:
            # Get complete response
            response = await self.invoke(question=prompt)
            return GraphEvent(
                type=EventType.LMM_RESPONSE,
                data=response.content,
                source_id=context["node_id"],
            )

        except Exception as e:
            # Re-raise the exception with more context
            raise Exception(f"Error processing event: {str(e)}")

    def can_handle(self, event):
        return isinstance(event.data, str)
