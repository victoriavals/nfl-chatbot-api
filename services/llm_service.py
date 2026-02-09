"""
LLM Service - Unlimited LLM with Fallback System.

This module provides LLM integration with automatic fallback
when one provider fails. Includes Ai4Chat as primary and
Cerebras/Groq/OpenRouter/Gemini as fallbacks.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config import (
    ConstantsVar,
    APIConfig,
    debug_info,
    debug_error,
    debug_warning,
    debug_success
)


class LLMStatus(Enum):
    """Enum for LLM response status."""
    SUCCESS = 200
    ERROR = 500
    RATE_LIMITED = 429
    API_KEY_MISSING = 401
    MODEL_NOT_FOUND = 404


@dataclass
class LLMResponse:
    """Response object from LLM query."""
    status: LLMStatus
    content: Optional[str]
    provider: str
    model: str
    error_message: Optional[str] = None


@dataclass
class LLMProvider:
    """Configuration for an LLM provider."""
    name: str
    api_key: str
    base_url: Optional[str]
    model: str
    priority: int
    provider_type: str  # "openai_compatible", "google", or "ai4chat"


class LLMService:
    """
    LLM Service with fallback system.
    
    Priority order:
    0. Ai4Chat (Free, no key required)
    1. Cerebras (Most stable)
    2. Groq (Fast)
    3. OpenRouter (Flexible)
    4. Gemini (Often rate limited)
    """
    
    def __init__(self, temperature: float = 0.7) -> None:
        """
        Initialize the LLM Service.
        
        Args:
            temperature: Temperature setting for LLM responses
        """
        self.temperature: float = temperature
        self.providers: list[LLMProvider] = self._initialize_providers()
        self.last_successful_provider: Optional[str] = None
        
        debug_info(f"[LLM] Service initialized with {len(self.providers)} providers")
    
    def _initialize_providers(self) -> list[LLMProvider]:
        """
        Initialize and return list of LLM providers sorted by priority.
        
        Returns:
            List of LLMProvider configs sorted by priority
        """
        providers: list[LLMProvider] = []
        
        # 0. Ai4Chat (Priority 0 - Primary, Free)
        providers.append(LLMProvider(
            name="Ai4Chat",
            api_key="",  # No key needed
            base_url="https://yw85opafq6.execute-api.us-east-1.amazonaws.com/default/boss_mode_15aug",
            model="ai4chat",
            priority=0,
            provider_type="ai4chat"
        ))
        
        # 1. Cerebras (Priority 1 - Best fallback)
        if ConstantsVar.MY_CEREBRAS_API_KEY:
            providers.append(LLMProvider(
                name="Cerebras",
                api_key=ConstantsVar.MY_CEREBRAS_API_KEY,
                base_url="https://api.cerebras.ai/v1",
                model="llama-3.3-70b",
                priority=1,
                provider_type="openai_compatible"
            ))
        
        # 2. Groq (Priority 2)
        if ConstantsVar.MY_GROQ_API_KEY:
            providers.append(LLMProvider(
                name="Groq",
                api_key=ConstantsVar.MY_GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile",
                priority=2,
                provider_type="openai_compatible"
            ))
        
        # 3. OpenRouter (Priority 3)
        if ConstantsVar.MY_OPENROUTER_API_KEY:
            providers.append(LLMProvider(
                name="OpenRouter",
                api_key=ConstantsVar.MY_OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                model="google/gemma-3-12b-it:free",
                priority=3,
                provider_type="openai_compatible"
            ))
        
        # 4. Gemini (Priority 4 - Often rate limited)
        if ConstantsVar.MY_GEMINI_API_KEY:
            providers.append(LLMProvider(
                name="Gemini",
                api_key=ConstantsVar.MY_GEMINI_API_KEY,
                base_url=None,
                model="gemini-1.5-flash",
                priority=4,
                provider_type="google"
            ))
        
        # Sort by priority
        providers.sort(key=lambda x: x.priority)
        
        return providers
    
    async def _query_ai4chat(self, prompt: str) -> LLMResponse:
        """
        Query Ai4Chat API.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            LLMResponse with result
        """
        debug_info("[Ai4Chat] Attempting query...")
        
        try:
            async with httpx.AsyncClient(timeout=APIConfig.REQUEST_TIMEOUT) as client:
                params: dict[str, str] = {
                    "text": prompt,
                    "country": "Indonesia",
                    "user_id": "FalBot_Naufal"
                }
                headers: dict[str, str] = {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 11) Chrome/90.0.0.0",
                    "Referer": "https://www.ai4chat.co/pages/riddle-generator"
                }
                
                response = await client.get(
                    "https://yw85opafq6.execute-api.us-east-1.amazonaws.com/default/boss_mode_15aug",
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 200:
                    content: str = response.text
                    if content:
                        debug_success("[Ai4Chat] Request successful!")
                        return LLMResponse(
                            status=LLMStatus.SUCCESS,
                            content=content,
                            provider="Ai4Chat",
                            model="ai4chat"
                        )
                
                debug_warning(f"[Ai4Chat] Non-200 response: {response.status_code}")
                return LLMResponse(
                    status=LLMStatus.ERROR,
                    content=None,
                    provider="Ai4Chat",
                    model="ai4chat",
                    error_message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            debug_error(f"[Ai4Chat] Error: {str(e)[:100]}")
            return LLMResponse(
                status=LLMStatus.ERROR,
                content=None,
                provider="Ai4Chat",
                model="ai4chat",
                error_message=str(e)
            )
    
    def _create_llm_client(self, provider: LLMProvider):
        """
        Create LangChain LLM client for the given provider.
        
        Args:
            provider: LLMProvider configuration
            
        Returns:
            LangChain chat model instance
        """
        if provider.provider_type == "openai_compatible":
            extra_kwargs: dict = {}
            if provider.name == "OpenRouter":
                extra_kwargs["default_headers"] = {
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "NFLChatbotAPI"
                }
            
            return ChatOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                model=provider.model,
                temperature=self.temperature,
                **extra_kwargs
            )
        elif provider.provider_type == "google":
            return ChatGoogleGenerativeAI(
                model=provider.model,
                temperature=self.temperature,
                google_api_key=provider.api_key
            )
        else:
            raise ValueError(f"Unknown provider type: {provider.provider_type}")
    
    async def _query_langchain_provider(self, provider: LLMProvider, prompt: str) -> LLMResponse:
        """
        Query a LangChain-based provider.
        
        Args:
            provider: The LLM provider to use
            prompt: The prompt to send
            
        Returns:
            LLMResponse with result
        """
        debug_info(f"[{provider.name}] Attempting query with model: {provider.model}")
        
        try:
            llm = self._create_llm_client(provider)
            messages = [HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            
            if response.content:
                debug_success(f"[{provider.name}] Request successful!")
                return LLMResponse(
                    status=LLMStatus.SUCCESS,
                    content=str(response.content),
                    provider=provider.name,
                    model=provider.model
                )
            else:
                debug_warning(f"[{provider.name}] Empty response received.")
                return LLMResponse(
                    status=LLMStatus.ERROR,
                    content=None,
                    provider=provider.name,
                    model=provider.model,
                    error_message="Empty response"
                )
                
        except Exception as e:
            error_msg: str = str(e)
            
            # Classify error type
            if "429" in error_msg or "rate" in error_msg.lower():
                status = LLMStatus.RATE_LIMITED
                debug_warning(f"[{provider.name}] Rate limited: {error_msg[:100]}")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                status = LLMStatus.API_KEY_MISSING
                debug_error(f"[{provider.name}] API key issue: {error_msg[:100]}")
            else:
                status = LLMStatus.ERROR
                debug_error(f"[{provider.name}] Error: {error_msg[:100]}")
            
            return LLMResponse(
                status=status,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
    
    async def query(self, prompt: str) -> LLMResponse:
        """
        Send a query to the LLM with automatic fallback.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            LLMResponse with the result
        """
        if not self.providers:
            return LLMResponse(
                status=LLMStatus.API_KEY_MISSING,
                content=None,
                provider="None",
                model="None",
                error_message="No providers configured"
            )
        
        debug_info("=== LLM Query Started ===")
        debug_info(f"Prompt: '{prompt[:50]}...'")
        
        errors: list[str] = []
        
        for i, provider in enumerate(self.providers, 1):
            debug_info(f"Trying provider {i}/{len(self.providers)}: {provider.name}")
            
            # Use appropriate query method
            if provider.provider_type == "ai4chat":
                response = await self._query_ai4chat(prompt)
            else:
                response = await self._query_langchain_provider(provider, prompt)
            
            if response.status == LLMStatus.SUCCESS:
                self.last_successful_provider = provider.name
                debug_success(f"=== Query completed via {provider.name} ===")
                return response
            else:
                errors.append(f"{provider.name}: {response.error_message}")
                debug_warning(f"Provider {provider.name} failed, trying next...")
        
        # All providers failed
        debug_error("=== All providers failed! ===")
        return LLMResponse(
            status=LLMStatus.ERROR,
            content=None,
            provider="All",
            model="All",
            error_message=f"All providers failed: {'; '.join(errors)}"
        )
    
    def get_available_providers(self) -> list[str]:
        """
        Get list of configured provider names.
        
        Returns:
            List of provider names
        """
        return [p.name for p in self.providers]


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the LLM service singleton.
    
    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(temperature=APIConfig.DEFAULT_TEMPERATURE)
    return _llm_service
