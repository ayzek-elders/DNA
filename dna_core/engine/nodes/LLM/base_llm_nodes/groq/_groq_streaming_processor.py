from dna_core.engine.nodes.LLM.base_llm_nodes.groq.i_qroq import IGroqProcessor
from dna_core.engine.graph.graph_event import EventType, GraphEvent
from langchain.callbacks.base import AsyncCallbackHandler
from langchain_groq import ChatGroq
from typing import Dict, Any

import asyncio
import os


class StreamingCallbackHandler(AsyncCallbackHandler):
    """Callback handler to capture streaming tokens from LLM"""

    def __init__(self):
        self.tokens = asyncio.Queue()

    async def on_llm_new_token(self, token: str, **kwargs):
        """Called when LLM generates a new token"""
        await self.tokens.put(token)

    async def on_llm_end(self, *args, **kwargs) -> None:
        """Called when LLM finishes generation"""
        await self.tokens.put("[DONE]")

    async def on_llm_error(self, error, **kwargs) -> None:
        """Called when LLM encounters an error"""
        await self.tokens.put(f"[ERROR]: {str(error)}")


class GroqStreamProcessor(IGroqProcessor):
    def __init__(self, config: Dict[str, any]):
        super().__init__()
        self.callback_handler = StreamingCallbackHandler()
        self.config = config
        self.config["callbacks"] = [self.callback_handler]

        if self.config["api_key"]:
            os.environ["GROQ_API_KEY"] = self.config["api_key"]

        self.llm = ChatGroq(**config)

    async def invoke(self, question: str, system_prompt: str = None):
        """
        Stream response tokens for a given question

        Args:
            question: User's question
            system_prompt: Optional system prompt to guide the response

        Yields:
            str: Individual tokens as they're generated
        """
        # Prepare messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": question})

        # Start LLM task
        task = asyncio.create_task(self.llm.ainvoke(messages))

        try:
            while True:
                try:
                    # Wait for next token with timeout
                    token = await asyncio.wait_for(
                        self.callback_handler.tokens.get(), timeout=2.0
                    )

                    if token == "[DONE]":
                        yield token
                    elif token.startswith("[ERROR]"):
                        raise Exception(token[8:])  # Remove "[ERROR]: " prefix
                    else:
                        yield token

                except asyncio.TimeoutError:
                    # Check if task is done
                    if task.done():
                        print("Timeout occurred while waiting for tokens")
                        break
                    # Continue waiting if task is still running
                    continue

        except Exception as e:
            task.cancel()
            raise e
        finally:
            # Ensure task is completed
            if not task.done():
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # async def process(self, event: GraphEvent, context: Dict[str, Any]):
    #     prompt = event.data
    #     payload = {
    #         "question" : prompt
    #     }
    #     print("LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOL")
    #     async for token in self.invoke(question= prompt):
    #         payload["token"] = token
    #         print(token) #DELETE
    #         yield GraphEvent(
    #             type= EventType.LLM_TOKEN,
    #             data= payload,
    #             source_id=context["node_id"]
    #         )

    def process(self, event: GraphEvent, context: Dict[str, Any]):
        prompt = event.data
        payload = {"question": prompt}
        print("LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOL")
        for token in self.invoke(question=prompt):
            payload["token"] = token
            print(token)  # DELETE
            yield GraphEvent(
                type=EventType.LLM_TOKEN, data=payload, source_id=context["node_id"]
            )

    def can_handle(self, event):
        return isinstance(event.data, str)
