"""
Memory Service - Conversation History Management with Supabase.

This module provides persistent conversation storage using Supabase PostgreSQL.
Uses httpx for lightweight REST API calls (no SDK dependency).
"""

from typing import Optional
import httpx

from config import APIConfig, debug_info, debug_warning, debug_error


class MemoryService:
    """
    Persistent conversation storage service using Supabase.
    
    Stores conversation history per user in PostgreSQL table.
    Memory persists across server restarts.
    """
    
    def __init__(self, max_memory_per_user: int = 10) -> None:
        """
        Initialize the memory service.
        
        Args:
            max_memory_per_user: Maximum messages to keep per user
        """
        self.max_memory: int = max_memory_per_user
        self.supabase_url: str = APIConfig.SUPABASE_URL
        self.supabase_key: str = APIConfig.SUPABASE_KEY
        
        if not self.supabase_url or not self.supabase_key:
            debug_warning("[Memory] Supabase credentials not configured - memory will not persist!")
        else:
            debug_info(f"[Memory] Service initialized with Supabase (max {max_memory_per_user} messages per user)")
    
    def _get_headers(self) -> dict[str, str]:
        """
        Get HTTP headers for Supabase REST API.
        
        Returns:
            dict: Headers with API key and authorization
        """
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
    
    async def add_message(self, user_id: str, role: str, content: str) -> None:
        """
        Add a message to user's conversation history in Supabase.
        
        Args:
            user_id: Unique user identifier
            role: Either 'user' or 'assistant'
            content: The message content
        """
        if not self.supabase_url or not self.supabase_key:
            debug_warning(f"[Memory] Skipping save - Supabase not configured")
            return
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Insert new message
                response: httpx.Response = await client.post(
                    f"{self.supabase_url}/rest/v1/chat_memory",
                    headers=self._get_headers(),
                    json={
                        "user_id": user_id,
                        "role": role,
                        "content": content
                    }
                )
                
                if response.status_code == 201:
                    debug_info(f"[Memory] Added {role} message for user {user_id[:8]}...")
                    
                    # Cleanup old messages if exceeds max
                    await self._cleanup_old_messages(user_id)
                else:
                    debug_error(f"[Memory] Failed to add message: HTTP {response.status_code}")
                    
        except Exception as e:
            debug_error(f"[Memory] Error adding message: {str(e)[:100]}")
    
    async def _cleanup_old_messages(self, user_id: str) -> None:
        """
        Remove old messages if user has more than max_memory.
        
        Args:
            user_id: User identifier
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Count messages for this user
                count_response: httpx.Response = await client.get(
                    f"{self.supabase_url}/rest/v1/chat_memory",
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "id"
                    },
                    headers=self._get_headers()
                )
                
                if count_response.status_code == 200:
                    messages: list = count_response.json()
                    count: int = len(messages)
                    
                    if count > self.max_memory:
                        # Delete oldest messages
                        to_delete: int = count - self.max_memory
                        
                        # Get IDs of oldest messages
                        oldest_response: httpx.Response = await client.get(
                            f"{self.supabase_url}/rest/v1/chat_memory",
                            params={
                                "user_id": f"eq.{user_id}",
                                "select": "id",
                                "order": "created_at.asc",
                                "limit": str(to_delete)
                            },
                            headers=self._get_headers()
                        )
                        
                        if oldest_response.status_code == 200:
                            oldest_ids: list = oldest_response.json()
                            ids_to_delete: list[int] = [msg["id"] for msg in oldest_ids]
                            
                            # Delete by IDs
                            for msg_id in ids_to_delete:
                                await client.delete(
                                    f"{self.supabase_url}/rest/v1/chat_memory",
                                    params={"id": f"eq.{msg_id}"},
                                    headers=self._get_headers()
                                )
                            
                            debug_info(f"[Memory] Cleaned up {to_delete} old messages for user {user_id[:8]}...")
                            
        except Exception as e:
            debug_error(f"[Memory] Error during cleanup: {str(e)[:100]}")
    
    async def get_memory(self, user_id: str) -> list[dict]:
        """
        Get conversation history for a user from Supabase.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            List of message dictionaries
        """
        if not self.supabase_url or not self.supabase_key:
            debug_warning(f"[Memory] Skipping get - Supabase not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response: httpx.Response = await client.get(
                    f"{self.supabase_url}/rest/v1/chat_memory",
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "role,content,created_at",
                        "order": "created_at.asc",
                        "limit": str(self.max_memory)
                    },
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    messages: list[dict] = response.json()
                    
                    # Convert Supabase format to memory format
                    formatted_messages: list[dict] = []
                    for msg in messages:
                        formatted_messages.append({
                            "role": msg["role"],
                            "content": msg["content"],
                            "timestamp": msg["created_at"]
                        })
                    
                    return formatted_messages
                else:
                    debug_error(f"[Memory] Failed to get memory: HTTP {response.status_code}")
                    return []
                    
        except Exception as e:
            debug_error(f"[Memory] Error getting memory: {str(e)[:100]}")
            return []
    
    async def get_memory_length(self, user_id: str) -> int:
        """
        Get the number of messages in user's history.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Number of messages
        """
        if not self.supabase_url or not self.supabase_key:
            return 0
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response: httpx.Response = await client.get(
                    f"{self.supabase_url}/rest/v1/chat_memory",
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "id"
                    },
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return len(response.json())
                else:
                    return 0
                    
        except Exception as e:
            debug_error(f"[Memory] Error getting memory length: {str(e)[:100]}")
            return 0
    
    async def clear_memory(self, user_id: str) -> int:
        """
        Clear conversation history for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Number of messages cleared
        """
        if not self.supabase_url or not self.supabase_key:
            debug_warning(f"[Memory] Skipping clear - Supabase not configured")
            return 0
        
        try:
            # Get count first
            count: int = await self.get_memory_length(user_id)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response: httpx.Response = await client.delete(
                    f"{self.supabase_url}/rest/v1/chat_memory",
                    params={"user_id": f"eq.{user_id}"},
                    headers=self._get_headers()
                )
                
                if response.status_code in (200, 204):
                    debug_info(f"[Memory] Cleared {count} messages for user {user_id[:8]}...")
                    return count
                else:
                    debug_error(f"[Memory] Failed to clear memory: HTTP {response.status_code}")
                    return 0
                    
        except Exception as e:
            debug_error(f"[Memory] Error clearing memory: {str(e)[:100]}")
            return 0


# Singleton instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """
    Get or create the memory service singleton.
    
    Returns:
        MemoryService instance
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService(max_memory_per_user=APIConfig.MAX_MEMORY_LENGTH)
    return _memory_service
