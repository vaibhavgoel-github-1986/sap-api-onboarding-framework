#!/usr/bin/env python3
"""
Simple quick test of the SAP BRIM A2A Agent
"""

import asyncio
import httpx
import json

async def test_agent():
    base_url = 'http://localhost:8000'
    
    async with httpx.AsyncClient() as client:
        # Test 1: Get Agent Card
        print("🔍 Test 1: Fetching Agent Card...")
        response = await client.get(f'{base_url}/.well-known/agent-card.json')
        card = response.json()
        print(f"✅ Agent Name: {card['name']}")
        print(f"✅ Skills: {[s['name'] for s in card['skills']]}")
        print()
        
        # Test 2: Send a message using JSON-RPC
        print("🔍 Test 2: Sending a message...")
        message_payload = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": "msg-001",
                    "parts": [
                        {"kind": "text", "text": "Hello SAP BRIM!"}
                    ]
                }
            }
        }
        
        response = await client.post(base_url, json=message_payload)
        result = response.json()
        print(f"✅ Response: {json.dumps(result, indent=2)}")
        print()
        
        print("🎉 All tests passed!")

if __name__ == '__main__':
    try:
        asyncio.run(test_agent())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to server at http://localhost:8000")
        print("   Please start the server first with: ./start_server.sh")
    except Exception as e:
        print(f"❌ Error: {e}")
