"""
General AI Routes - Simple conversational AI without RAG.

This module provides endpoints for general conversation using LLM + memory only.
No knowledge base injection, just pure conversational AI.
"""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status

from config import APIConfig, debug_info, debug_error, debug_warning
from models.schemas import (
    GeneralAIRequest,
    GeneralAIResponse,
    ClearMemoryResponse
)
from services.llm_service import get_llm_service, LLMStatus
from services.memory_service import get_memory_service


router = APIRouter(tags=["General AI"])


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Check if header is completely missing (None), not just empty string
    if x_api_key is None:
        debug_warning("[Auth] Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header."
        )
    
    # Allow empty string if configured in APIConfig
    if x_api_key != APIConfig.API_KEY:
        debug_warning(f"[Auth] Invalid API key: {x_api_key[:8] if x_api_key else '(empty)'}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return x_api_key


async def build_conversation_prompt(
    user_message: str,
    user_id: str,
    system_prompt: str | None = None,
    max_history: int = 10
) -> str:
    """
    Build a simple conversational prompt with memory.
    
    Args:
        user_message: Current user message
        user_id: User identifier for memory lookup
        system_prompt: Optional custom system prompt
        max_history: Maximum number of history messages to include
        
    Returns:
        str: Complete prompt with system + history + current message
    """
    memory_service = get_memory_service()
    
    # Default system prompt
    default_system: str = "You are a helpful, friendly AI assistant. Answer questions clearly and concisely."
    system: str = system_prompt or default_system
    
    # Get conversation history
    memory_items = await memory_service.get_memory(user_id)
    
    # Build prompt
    prompt_parts: list[str] = [f"System: {system}\n"]
    
    if memory_items:
        prompt_parts.append("\n=== Conversation History ===")
        # Get last N messages
        recent_history = memory_items[-max_history:] if len(memory_items) > max_history else memory_items
        
        for item in recent_history:
            role: str = "User" if item["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {item['content']}")
        
        prompt_parts.append("\n=== Current Conversation ===")
    
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    return "\n".join(prompt_parts)


@router.post("/general-ai", response_model=GeneralAIResponse)
async def general_ai_chat(
    request: GeneralAIRequest,
    x_api_key: str = Header(..., description="API Key for authentication")
) -> GeneralAIResponse:
    """
    General AI chat endpoint without RAG.
    
    Simple conversational AI using LLM + memory only.
    No knowledge base, no time context, just pure conversation.
    
    Args:
        request: Chat request with user_id and message
        x_api_key: API key header
        
    Returns:
        GeneralAIResponse with AI response and metadata
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    debug_info(f"[General AI] Request from user: {request.user_id}")
    debug_info(f"[General AI] Message: {request.message[:50]}...")
    
    memory_service = get_memory_service()
    llm_service = get_llm_service()
    
    try:
        # Save user message to memory
        await memory_service.add_message(request.user_id, "user", request.message)
        
        # Build conversation prompt
        prompt: str = await build_conversation_prompt(
            user_message=request.message,
            user_id=request.user_id,
            system_prompt=request.system_prompt,
            max_history=10
        )
        
        # Query LLM with optional temperature override
        temperature: float = request.temperature if request.temperature is not None else APIConfig.DEFAULT_TEMPERATURE
        response = await llm_service.query(prompt, temperature=temperature)
        
        # Get current memory length
        memory_length: int = await memory_service.get_memory_length(request.user_id)
        
        if response.status == LLMStatus.SUCCESS:
            # Save assistant response to memory
            await memory_service.add_message(request.user_id, "assistant", response.content)
            
            return GeneralAIResponse(
                status="success",
                response=response.content,
                provider=response.provider,
                model=response.model,
                memory_length=memory_length
            )
        else:
            debug_error(f"[General AI] LLM error: {response.error_message}")
            return GeneralAIResponse(
                status="error",
                response="Sorry, I encountered an error. Please try again.",
                provider=response.provider,
                model=response.model,
                memory_length=memory_length,
                error_message=response.error_message
            )
            
    except Exception as e:
        debug_error(f"[General AI] Unexpected error: {e}")
        return GeneralAIResponse(
            status="error",
            response="An unexpected error occurred.",
            error_message=str(e)
        )


@router.delete("/general-ai/memory/{user_id}", response_model=ClearMemoryResponse)
async def clear_general_ai_memory(
    user_id: str,
    x_api_key: str = Header(..., description="API Key for authentication")
) -> ClearMemoryResponse:
    """
    Clear conversation memory for a user.
    
    Args:
        user_id: User identifier
        x_api_key: API key header
        
    Returns:
        ClearMemoryResponse with result
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    debug_info(f"[General AI] Clearing memory for user: {user_id[:8]}...")
    
    memory_service = get_memory_service()
    messages_cleared: int = await memory_service.clear_memory(user_id)
    
    return ClearMemoryResponse(
        status="success",
        user_id=user_id,
        messages_cleared=messages_cleared
    )


@router.get("/general-ai/memory/{user_id}/length")
async def get_general_ai_memory_length(
    user_id: str,
    x_api_key: str = Header(..., description="API Key for authentication")
) -> dict:
    """
    Get the number of messages in conversation history.
    
    Args:
        user_id: User identifier
        x_api_key: API key header
        
    Returns:
        Dictionary with memory length
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    memory_service = get_memory_service()
    length: int = await memory_service.get_memory_length(user_id)
    
    return {
        "user_id": user_id,
        "memory_length": length
    }
