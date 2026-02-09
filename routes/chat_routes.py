"""
Chat Routes - API endpoints for chatbot.

This module provides FastAPI routes for chat, health check, and memory management.
"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from config import APIConfig, debug_info, debug_error, debug_warning
from models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStatus,
    HealthResponse,
    ClearMemoryResponse
)
from services.rag_service import get_rag_service
from services.llm_service import get_llm_service, LLMStatus
from services.memory_service import get_memory_service


router = APIRouter(tags=["Chat"])


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
    if not x_api_key:
        debug_warning("[Auth] Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header."
        )
    
    if x_api_key != APIConfig.API_KEY:
        debug_warning(f"[Auth] Invalid API key: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return x_api_key


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with API status
    """
    llm_service = get_llm_service()
    providers: list[str] = llm_service.get_available_providers()
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        providers_available=len(providers)
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: str = Header(..., description="API Key for authentication")
) -> ChatResponse:
    """
    Chat endpoint with RAG-based response.
    
    Args:
        request: Chat request with user_id and message
        x_api_key: API key header
        
    Returns:
        ChatResponse with bot response
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    debug_info(f"[API] Chat request from user: {request.user_id[:8]}...")
    debug_info(f"[API] Message: {request.message[:50]}...")
    
    try:
        # Get RAG service and process query
        rag_service = get_rag_service()
        memory_service = get_memory_service()
        
        response = await rag_service.process_query(
            user_id=request.user_id,
            message=request.message,
            include_memory=request.include_memory
        )
        
        # Get current memory length
        memory_length: int = memory_service.get_memory_length(request.user_id)
        
        if response.status == LLMStatus.SUCCESS:
            return ChatResponse(
                status=ChatStatus.SUCCESS,
                response=response.content,
                provider=response.provider,
                model=response.model,
                memory_length=memory_length
            )
        else:
            debug_error(f"[API] LLM error: {response.error_message}")
            return ChatResponse(
                status=ChatStatus.ERROR,
                response="Wah maaf, ada error nih. Coba lagi nanti ya!",
                provider=response.provider,
                model=response.model,
                memory_length=memory_length,
                error_message=response.error_message
            )
            
    except Exception as e:
        debug_error(f"[API] Unexpected error: {e}")
        return ChatResponse(
            status=ChatStatus.ERROR,
            error_message=str(e)
        )


@router.delete("/memory/{user_id}", response_model=ClearMemoryResponse)
async def clear_memory(
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
    
    debug_info(f"[API] Clearing memory for user: {user_id[:8]}...")
    
    memory_service = get_memory_service()
    messages_cleared: int = memory_service.clear_memory(user_id)
    
    return ClearMemoryResponse(
        status="success",
        user_id=user_id,
        messages_cleared=messages_cleared
    )


@router.get("/memory/{user_id}/length")
async def get_memory_length(
    user_id: str,
    x_api_key: str = Header(..., description="API Key for authentication")
) -> dict[str, any]:
    """
    Get memory length for a user.
    
    Args:
        user_id: User identifier
        x_api_key: API key header
        
    Returns:
        dict with user_id and memory length
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    memory_service = get_memory_service()
    length: int = memory_service.get_memory_length(user_id)
    
    return {
        "user_id": user_id,
        "memory_length": length
    }
