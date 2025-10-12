"""
Test Client for SAP BRIM Hello World A2A Agent

This client demonstrates how to interact with the SAP BRIM A2A Agent:
1. Fetch the agent card
2. Send a message to the agent
3. Receive streaming responses
"""

import asyncio
import json
import logging
import warnings
from uuid import uuid4
from typing import Any

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


async def main() -> None:
    """Main function to test the SAP BRIM A2A Agent."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Agent server URL
    base_url = 'http://localhost:8000'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize the card resolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        try:
            # Fetch the agent card
            logger.info(f'Fetching agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}')
            agent_card = await resolver.get_agent_card()
            logger.info('✅ Successfully fetched agent card:')
            logger.info(f'   Name: {agent_card.name}')
            logger.info(f'   Description: {agent_card.description}')
            logger.info(f'   Version: {agent_card.version}')
            logger.info(f'   Skills: {[skill.name for skill in agent_card.skills]}')
            
        except Exception as e:
            logger.error(f'❌ Failed to fetch agent card: {e}', exc_info=True)
            raise RuntimeError('Cannot continue without agent card') from e

        # Initialize the A2A client
        # Note: A2AClient is deprecated but we use it for simplicity
        # In production, use the JSON-RPC client directly
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            client = A2AClient(
                httpx_client=httpx_client,
                agent_card=agent_card
            )
        logger.info('✅ A2A Client initialized')

        # Test 1: Send a simple message (non-streaming)
        print("\n" + "="*60)
        print("TEST 1: Sending a simple message (non-streaming)")
        print("="*60)
        
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Get Subscription SR1011023 Details'}
                ],
                'messageId': uuid4().hex,
            },
        }
        
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload)
        )

        logger.info('📤 Sending message: "Hello SAP BRIM!"')
        response = await client.send_message(request)
        logger.info('📥 Received response:')
        print(json.dumps(response.model_dump(mode='json', exclude_none=True), indent=2))

        # Test 2: Send a streaming message
        print("\n" + "="*60)
        print("TEST 2: Sending a streaming message")
        print("="*60)
        
        streaming_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'hi there'}
                ],
                'messageId': uuid4().hex,
            },
        }
        
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**streaming_payload)
        )

        logger.info('📤 Sending streaming message: "hi there"')
        logger.info('📥 Receiving streaming response:')
        
        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            print(json.dumps(chunk.model_dump(mode='json', exclude_none=True), indent=2))

        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
