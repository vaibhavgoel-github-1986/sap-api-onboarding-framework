import os
import sys
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph_supervisor import create_supervisor
from typing import Literal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.llm_model.get_azure_llm import get_azure_llm
from src.tools.call_sap_api import call_sap_api_generic
from src.tools.get_sap_api_metadata import get_service_metadata
from src.prompts.som_agent_prompt import SOM_AGENT_PROMPT
from src.prompts.tech_agent_prompt import TECH_AGENT_PROMPT 
from src.prompts.supervisor_agent_prompt import SUPERVISOR_AGENT_PROMPT
from src.utils.logger import logger

model = get_azure_llm()
checkpointer = InMemorySaver()

class SupervisorStreamer:
    
    def __init__(self, graph):
        self.graph = graph
    
    def stream(self, user_message: str, thread_id: str = "1", stream_mode: Literal["values", "updates"] = "values"):
        """Stream responses from the supervisor agent."""
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"Starting stream for user message: {user_message}")
        logger.debug(f"Thread ID: {thread_id}, Stream mode: {stream_mode}")
        
        for chunk in self.graph.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            config,
            stream_mode=stream_mode
        ):
            if "messages" in chunk and chunk["messages"]:
                message = chunk["messages"][-1]

                if message:
                    # Human Messages
                    if isinstance(message, HumanMessage):
                        message.pretty_print()

                    # AI Messages  
                    elif isinstance(message, AIMessage):
                        message.pretty_print()
                        
                    # Tool Messages
                    elif isinstance(message, ToolMessage):
                        message.pretty_print()
        
            yield message
    
    def invoke(self, user_message: str, thread_id: str = "1"):
        """Get the final response without streaming."""
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        
        return self.graph.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config
        )

# Create SAP Technical Agent
tech_agent = create_react_agent(
    model=model,
    tools=[call_sap_api_generic, get_service_metadata],
    prompt=TECH_AGENT_PROMPT,
    name="SAPTechnicalAgent"
)
        
# Create Subscription Management Agent
som_agent = create_react_agent(
    model=model,
    tools=[call_sap_api_generic, get_service_metadata],
    prompt=SOM_AGENT_PROMPT,
    name="SubscriptionAgent"
)

# Create Supervisor Agent
supervisor_agent = create_supervisor(
    [som_agent, tech_agent],
    model=model,
    prompt=SUPERVISOR_AGENT_PROMPT,
    supervisor_name="SupervisorAgent", 
    output_mode="last_message",
    add_handoff_messages=True,
    add_handoff_back_messages=False,
    include_agent_name="inline"
)

supervisor_graph = supervisor_agent.compile(
    # checkpointer=checkpointer
)

# Create the production streamer instance
response_generator = SupervisorStreamer(supervisor_graph)

# Example usage
if __name__ == "__main__":
    # Test with values mode (recommended)
    logger.info("Starting supervisor agent test")
    logger.info("Testing supervisor agent streaming...")
    
    input = "Get table schema for MAKT table in D2A system"
    # input = "get details for INTSRD2AVGAR0004, D2A System"
    
    try:
        for chunk in response_generator.stream(input):
            pass  # The pretty_print() happens inside the stream method
        logger.info("Stream completed successfully")
    except Exception as e:
        logger.error(f"Error during streaming: {str(e)}")
        raise
