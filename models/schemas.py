"""
Pydantic models for NFL Chatbot API.

This module defines request/response schemas for API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChatStatus(str, Enum):
    """Status enum for chat responses."""
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.
    
    Attributes:
        user_id: Unique identifier for the user (e.g., phone number)
        message: The user's message/question
        include_memory: Whether to include conversation history
    """
    user_id: str = Field(..., description="Unique user identifier", min_length=1)
    message: str = Field(..., description="User message", min_length=1, max_length=2000)
    include_memory: bool = Field(default=True, description="Include conversation history")


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.
    
    Attributes:
        status: Response status (success/error)
        response: The chatbot's response
        provider: Which LLM provider was used
        model: Which model was used
        memory_length: Current conversation memory length
        error_message: Error details if status is error
    """
    status: ChatStatus
    response: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    memory_length: int = 0
    error_message: Optional[str] = None


class MemoryItem(BaseModel):
    """
    Single conversation memory item.
    
    Attributes:
        role: Either 'user' or 'assistant'
        content: The message content
        timestamp: When the message was created
    """
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Attributes:
        status: Health status
        version: API version
        providers_available: Number of LLM providers configured
    """
    status: str = "healthy"
    version: str = "1.0.0"
    providers_available: int = 0


class ClearMemoryResponse(BaseModel):
    """
    Response model for clear memory endpoint.
    
    Attributes:
        status: Operation status
        user_id: User whose memory was cleared
        messages_cleared: Number of messages cleared
    """
    status: str
    user_id: str
    messages_cleared: int
