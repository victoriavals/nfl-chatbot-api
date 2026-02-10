"""
Test script for General AI endpoint (no RAG).

Tests conversational AI with Supabase memory persistence.
"""

import httpx
import asyncio
from typing import Any
from config import APIConfig

BASE_URL = "http://localhost:8000"
API_KEY = APIConfig.API_KEY


async def test_general_ai():
    """Test general AI endpoint with memory persistence."""
    
    print("=== Testing General AI Endpoint (No RAG) ===\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: First conversation
        print("1. First conversation (simple greeting)...")
        request1 = {
            "user_id": "test_general_ai_user_001",
            "message": "Hi! My name is Alice and I love pizza."
        }
        
        response1 = await client.post(
            f"{BASE_URL}/api/general-ai",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY
            },
            json=request1
        )
        
        print(f"   Status: {response1.status_code}")
        data1: dict = response1.json()
        print(f"   Provider: {data1.get('provider')}")
        print(f"   Memory Length: {data1.get('memory_length')}")
        print(f"   Response: {data1.get('response', '')[:100]}...\n")
        
        # Test 2: Memory recall
        print("2. Testing memory recall...")
        request2 = {
            "user_id": "test_general_ai_user_001",
            "message": "What's my name and what do I like?"
        }
        
        response2 = await client.post(
            f"{BASE_URL}/api/general-ai",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY
            },
            json=request2
        )
        
        print(f"   Status: {response2.status_code}")
        data2: dict = response2.json()
        print(f"   Memory Length: {data2.get('memory_length')}")
        print(f"   Response: {data2.get('response', '')[:150]}...\n")
        
        # Test 3: Custom system prompt
        print("3. Testing custom system prompt (comedian personality)...")
        request3 = {
            "user_id": "test_general_ai_user_002",
            "message": "Tell me something funny about cats",
            "system_prompt": "You are a hilarious comedian who loves puns and dad jokes."
        }
        
        response3 = await client.post(
            f"{BASE_URL}/api/general-ai",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY
            },
            json=request3
        )
        
        print(f"   Status: {response3.status_code}")
        data3: dict = response3.json()
        print(f"   Response: {data3.get('response', '')[:200]}...\n")
        
        # Test 4: Temperature control
        print("4. Testing temperature override (creative mode)...")
        request4 = {
            "user_id": "test_general_ai_user_003",
            "message": "Write a short poem about the moon",
            "temperature": 0.9
        }
        
        response4 = await client.post(
            f"{BASE_URL}/api/general-ai",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY
            },
            json=request4
        )
        
        print(f"   Status: {response4.status_code}")
        data4: dict = response4.json()
        print(f"   Response: {data4.get('response', '')[:200]}...\n")
        
        # Test 5: Memory length check
        print("5. Getting memory length...")
        mem_response = await client.get(
            f"{BASE_URL}/api/general-ai/memory/test_general_ai_user_001/length",
            headers={"X-API-Key": API_KEY}
        )
        
        print(f"   Status: {mem_response.status_code}")
        mem_data: dict = mem_response.json()
        print(f"   Memory Length: {mem_data.get('memory_length')}\n")
        
        # Test 6: Clear memory
        print("6. Clearing memory for user 001...")
        clear_response = await client.delete(
            f"{BASE_URL}/api/general-ai/memory/test_general_ai_user_001",
            headers={"X-API-Key": API_KEY}
        )
        
        print(f"   Status: {clear_response.status_code}")
        clear_data: dict = clear_response.json()
        print(f"   Messages Cleared: {clear_data.get('messages_cleared')}\n")
        
        print("=== All tests completed! ===")
        print("\n📌 Check Supabase Table Editor:")
        print("   - Table: chat_memory")
        print("   - Users: test_general_ai_user_001, 002, 003")
        print("   - Verify user_001 memory is cleared")


if __name__ == "__main__":
    asyncio.run(test_general_ai())
