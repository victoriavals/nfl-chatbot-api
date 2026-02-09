"""
Memory Service - Conversation History Management.

This module provides in-memory conversation storage per user.
For production, consider using Redis or a database.
"""

from datetime import datetime
from typing import Optional
from collections import OrderedDict

from config import APIConfig, debug_info, debug_warning


class MemoryService:
    """
    In-memory conversation storage service.
    
    Stores conversation history per user with configurable limits.
    Memory is cleared when the server restarts.
    """
    
    def __init__(self, max_memory_per_user: int = 10) -> None:
        """
        Initialize the memory service.
        
        Args:
            max_memory_per_user: Maximum messages to keep per user
        """
        self.max_memory: int = max_memory_per_user
        self.storage: OrderedDict[str, list[dict]] = OrderedDict()
        
        debug_info(f"[Memory] Service initialized with max {max_memory_per_user} messages per user")
    
    def add_message(self, user_id: str, role: str, content: str) -> None:
        """
        Add a message to user's conversation history.
        
        Args:
            user_id: Unique user identifier
            role: Either 'user' or 'assistant'
            content: The message content
        """
        if user_id not in self.storage:
            self.storage[user_id] = []
        
        message: dict = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.storage[user_id].append(message)
        
        # Trim if exceeds max
        if len(self.storage[user_id]) > self.max_memory:
            self.storage[user_id] = self.storage[user_id][-self.max_memory:]
        
        # Move user to end (most recent)
        self.storage.move_to_end(user_id)
        
        debug_info(f"[Memory] Added {role} message for user {user_id[:8]}...")
        
        # Cleanup if too many users
        self._cleanup_if_needed()
    
    def get_memory(self, user_id: str) -> list[dict]:
        """
        Get conversation history for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            List of message dictionaries
        """
        return self.storage.get(user_id, [])
    
    def get_memory_length(self, user_id: str) -> int:
        """
        Get the number of messages in user's history.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Number of messages
        """
        return len(self.storage.get(user_id, []))
    
    def clear_memory(self, user_id: str) -> int:
        """
        Clear conversation history for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Number of messages cleared
        """
        if user_id in self.storage:
            count: int = len(self.storage[user_id])
            del self.storage[user_id]
            debug_info(f"[Memory] Cleared {count} messages for user {user_id[:8]}...")
            return count
        return 0
    
    def get_total_users(self) -> int:
        """
        Get total number of users with stored memory.
        
        Returns:
            Number of users
        """
        return len(self.storage)
    
    def _cleanup_if_needed(self) -> None:
        """
        Remove oldest users if threshold exceeded.
        
        Removes the oldest 20% of users when threshold is reached.
        """
        threshold: int = APIConfig.MEMORY_CLEANUP_THRESHOLD
        
        if len(self.storage) > threshold:
            # Remove oldest 20%
            remove_count: int = threshold // 5
            users_to_remove: list[str] = list(self.storage.keys())[:remove_count]
            
            for user_id in users_to_remove:
                del self.storage[user_id]
            
            debug_warning(f"[Memory] Cleaned up {remove_count} oldest users")


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
