"""
Test script to verify chat history persistence fix
This script tests that:
1. Old chat can be loaded
2. New questions can be added to the conversation
3. Reloading the chat shows both old and new messages
"""

import asyncio
import httpx
import json

API_BASE_URL = "http://127.0.0.1:8000"

async def test_chat_history_persistence():
    print("=" * 60)
    print("Testing Chat History Persistence Fix")
    print("=" * 60)
    
    # Step 1: Create a new chat session
    session_id = "test_persistence_session"
    print(f"\n1. Creating new session: {session_id}")
    
    # Step 2: Send first message
    print("\n2. Sending first message...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/query",
            json={
                "query": "What is the capital of France?",
                "session_id": session_id
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {result['final_answer'][:100]}...")
        else:
            print(f"   Error: {response.status_code}")
            return
    
    # Step 3: Load the session to verify first message
    print("\n3. Loading session to verify first message...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/sessions/{session_id}")
        if response.status_code == 200:
            data = response.json()
            history = data.get("history", [])
            print(f"   History length: {len(history)} messages")
            for i, msg in enumerate(history):
                print(f"   [{i}] {msg['role']}: {msg['content'][:50]}...")
        else:
            print(f"   Error: {response.status_code}")
            return
    
    # Step 4: Send second message (continue conversation)
    print("\n4. Sending second message to continue conversation...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/query",
            json={
                "query": "What is the population of that city?",
                "session_id": session_id
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {result['final_answer'][:100]}...")
        else:
            print(f"   Error: {response.status_code}")
            return
    
    # Step 5: Reload session to verify BOTH messages are present
    print("\n5. Reloading session to verify BOTH old and new messages...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/sessions/{session_id}")
        if response.status_code == 200:
            data = response.json()
            history = data.get("history", [])
            print(f"   History length: {len(history)} messages")
            print("\n   Complete conversation history:")
            for i, msg in enumerate(history):
                print(f"   [{i}] {msg['role']}: {msg['content'][:80]}...")
            
            # Verify we have at least 4 messages (2 Q&A pairs)
            if len(history) >= 4:
                print("\n✅ SUCCESS: Chat history is properly preserved!")
                print(f"   Expected: At least 4 messages (2 Q&A pairs)")
                print(f"   Got: {len(history)} messages")
            else:
                print("\n❌ FAILURE: Chat history was not preserved!")
                print(f"   Expected: At least 4 messages (2 Q&A pairs)")
                print(f"   Got: {len(history)} messages")
        else:
            print(f"   Error: {response.status_code}")
            return
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_chat_history_persistence())
