import os
import sys
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.llm_model.get_azure_llm import get_azure_llm
from src.tools.call_sap_api import call_sap_api_generic

checkpointer = InMemorySaver()

agent = create_react_agent(
    model=get_azure_llm(),
    tools=[call_sap_api_generic],
    prompt="You are a helpful assistant",
    checkpointer=checkpointer
)
# Run the agent
config: RunnableConfig = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf?"}]},
    config
)

print(response)