"""
SAP BRIM Hello World A2A Agent Server

This is the main entry point for the SAP BRIM A2A Agent.
It sets up the A2A server with:
- Agent Card (describes the agent)
- Agent Executor (implements the agent logic)
- HTTP server (exposes the agent via A2A protocol)
"""

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from src.agent.agent_executor import SAPBRIMAgentExecutor


if __name__ == '__main__':
    # Define the agent's skills
    # A skill describes what the agent can do
    # You can have multiple skills in ONE agent
    
    greeting_skill = AgentSkill(
        id='sap_brim_hello',
        name='SAP BRIM Hello World',
        description='A simple greeting agent for SAP BRIM integration',
        tags=['sap', 'brim', 'hello', 'greeting'],
        examples=[
            'hi',
            'hello',
            'greet me',
            'hello SAP BRIM',
        ],
    )
    
    subscription_skill = AgentSkill(
        id='get_subscription',
        name='Get Subscription Details',
        description='Retrieve subscription order information from SAP BRIM',
        tags=['sap', 'brim', 'subscription', 'order'],
        examples=[
            'show subscription 12345',
            'get order details for ABC123',
            'what is the status of subscription 67890',
        ],
    )
    
    product_skill = AgentSkill(
        id='list_products',
        name='List Products',
        description='List available products from SAP BRIM catalog',
        tags=['sap', 'brim', 'product', 'catalog'],
        examples=[
            'show all products',
            'list available products',
            'what products do we have',
        ],
    )

    # Create the Agent Card
    # This is the public-facing description of the agent
    # Notice: ONE agent can have MULTIPLE skills
    agent_card = AgentCard(
        name='SAP BRIM Multi-Skill Agent',
        description=(
            'An A2A agent with multiple skills for SAP BRIM integration. '
            'Can handle greetings, subscription queries, and product listings.'
        ),
        url='http://localhost:8000/',
        version='0.2.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[greeting_skill, subscription_skill, product_skill],  # Multiple skills!
    )

    # Create the request handler
    # This handles incoming A2A requests and manages task state
    request_handler = DefaultRequestHandler(
        agent_executor=SAPBRIMAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # Create the A2A server application
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    # Run the server
    print("🚀 Starting SAP BRIM Hello World A2A Agent...")
    print("📍 Server running at: http://localhost:8000")
    print("📋 Agent Card available at: http://localhost:8000/.well-known/agent.json")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(server.build(), host='0.0.0.0', port=8000)
