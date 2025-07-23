import asyncio
from typing import Dict, Any, Optional
from app.engine.interfaces.i_middleware import IMiddleware
from app.engine.nodes.base_node import BaseNode
from app.engine.graph.graph_event import GraphEvent, EventType
from app.engine.graph.graph import ObserverGraph
from app.engine.nodes.http.http_node import HTTPGetRequestNode, HTTPPostRequestNode, HTTPPutRequestNode
from app.engine.nodes.http.http_middleware import HTTPRequestLoggingMiddleware
from app.engine.nodes.email.sender.emailsend_node import MailSenderNode


class SimpleLoggingMiddleware(IMiddleware):
    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        print(f"\n→ Node {node_id} received: {event.data}")
        return event

    async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
        if result:
            print(f"← Node {node_id} output: {result.data}")
        return result


class ResultNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "result_node", None)
        self.results = []

    async def update(self, event: GraphEvent):
        self.results.append(event.data)
        return await super().update(event)

# Alternative: Workflow-style email sending
async def workflow_example():
    """
    Example showing how email node can be part of a workflow
    where data flows between nodes
    """
    graph = ObserverGraph()
    
    # Data source node (could be database, API, etc.)
    data_node = HTTPGetRequestNode(node_id="get_user_data")
    
    # Email notification node
    mail_config = {
        "credential": {
            "username": "info@dna.com",
            "password": "password123",
            "server_name": "100.104.57.105",
            "server_port": 587,
            "use_tls": False,
            "use_ssl": False
        },
        "email_settings": {
            "from": "admin@dna.com",
            "to": "info@dna.com",
            "subject": "User Data Retrieved",
        }
    }
    
    notification_node = MailSenderNode(
        node_id="send_notification",
        config=mail_config
    )
    
    result_node = ResultNode("final_result")
    
    # Connect nodes: data retrieval → email notification → result
    graph.add_node(data_node)
    graph.add_node(notification_node)
    graph.add_node(result_node)
    
    graph.add_edge("get_user_data", "send_notification")
    graph.add_edge("send_notification", "final_result")
    
    # Trigger workflow
    user_data_event = GraphEvent(
        type=EventType.DATA_CHANGE,
        data={
            "url": "https://jsonplaceholder.typicode.com/users/1"
        }
    )

    
    print("\n🔄 Workflow Example:")
    print("Step 1: Retrieving user data...")
    await graph.trigger_event("get_user_data", user_data_event)

    
    print("✅ Workflow completed!")


if __name__ == "__main__":    
    print("\n" + "="*60)
    asyncio.run(workflow_example())


