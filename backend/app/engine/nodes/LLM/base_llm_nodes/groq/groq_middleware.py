import logging 
import os 
from app.engine.interfaces.i_middleware import IMiddleware
from app.engine.graph.graph_event import GraphEvent
from typing import Dict, Any, Optional

class TokenCountLogger(IMiddleware):
    def __init__(self, log_file: os.PathLike):
        self.token_count: int = 0
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,               
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        
    async def after_process(self, event: GraphEvent, node_id) -> None:
        try:
            if event.data["token"] != "[DONE]":
                self.token_count += 1
            else:
                logging.info(f"question = {event.data["question"]}, number of tokens = {self.token_count}")
                self.token_count = 0
            
        except Exception as e:
            logging.error(f"Exception [{e}] occured.")                
