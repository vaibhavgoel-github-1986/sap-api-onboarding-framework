"""
SAP BRIM Hello World Agent Executor

This is a simple A2A agent that demonstrates the basic structure
of an A2A agent for SAP BRIM integration.
"""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message


class SAPBRIMHelloWorldAgent:
    """
    Simple Hello World Agent for SAP BRIM.
    
    This agent responds with a friendly greeting message.
    In a real implementation, this would connect to SAP BRIM APIs.
    """

    async def invoke(self, user_input: str = "") -> str:
        """
        Process the user input and return a greeting.
        
        Args:
            user_input: The user's message (optional)
            
        Returns:
            A greeting message
        """
        if user_input:
            return f"Hello! You said: '{user_input}'. Welcome to SAP BRIM A2A Agent!"
        return "Hello World from SAP BRIM A2A Agent! 🚀"


class SAPBRIMAgentExecutor(AgentExecutor):
    """
    Agent Executor for SAP BRIM Hello World Agent.
    
    This class implements the AgentExecutor interface required by the A2A SDK.
    It handles:
    - Executing agent tasks
    - Managing the event queue for streaming responses
    - Canceling tasks (if needed)
    """

    def __init__(self):
        """Initialize the agent executor with the SAP BRIM agent."""
        self.agent = SAPBRIMHelloWorldAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute the agent task.
        
        This method:
        1. Extracts user input from the request context
        2. Invokes the agent
        3. Sends the response back via the event queue
        
        Args:
            context: Request context containing user input and metadata
            event_queue: Queue for sending events back to the client
        """
        # Extract user input from the request using the context helper method
        user_input = context.get_user_input()
        
        # Invoke the agent
        result = await self.agent.invoke(user_input)
        
        # Send the response back to the client
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """
        Cancel the agent task.
        
        For this simple agent, we don't support cancellation.
        In a real implementation, this would stop any ongoing SAP BRIM operations.
        
        Args:
            context: Request context
            event_queue: Event queue for sending cancellation messages
        """
        raise Exception('Task cancellation is not supported for this agent')
