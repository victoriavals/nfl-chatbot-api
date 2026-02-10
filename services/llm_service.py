"""
LLM Service - Unlimited LLM with Fallback System.

This module provides LLM integration with automatic fallback
when one provider fails. Uses native httpx for lightweight Vercel deployment.

Providers: Ai4Chat (primary) -> Cerebras -> Groq -> OpenRouter -> Gemini.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx

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
            temperature (float): Temperature setting for LLM responses.
        """
        self.temperature: float = temperature
        self.providers: list[LLMProvider] = self._initialize_providers()
        self.last_successful_provider: Optional[str] = None
        
        debug_info(f"[LLM] Service initialized with {len(self.providers)} providers")
    
    def _initialize_providers(self) -> list[LLMProvider]:
        """
        Initialize and return list of LLM providers sorted by priority.
        
        Returns:
            list[LLMProvider]: Provider configs sorted by priority.
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
        Query Ai4Chat API (free, no key required).
        
        Args:
            prompt (str): The prompt to send.
            
        Returns:
            LLMResponse: Result from Ai4Chat.
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
                
                response: httpx.Response = await client.get(
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
    
    async def _query_openai_compatible(self, provider: LLMProvider, prompt: str) -> LLMResponse:
        """
        Query an OpenAI-compatible API (Cerebras, Groq, OpenRouter).
        
        Uses raw httpx POST to /chat/completions endpoint.
        
        Args:
            provider (LLMProvider): The provider configuration.
            prompt (str): The prompt to send.
            
        Returns:
            LLMResponse: Result from the provider.
        """
        debug_info(f"[{provider.name}] Attempting query with model: {provider.model}")
        
        try:
            headers: dict[str, str] = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json"
            }
            
            # OpenRouter requires extra headers
            if provider.name == "OpenRouter":
                headers["HTTP-Referer"] = "http://localhost:3000"
                headers["X-Title"] = "NFLChatbotAPI"
            
            payload: dict[str, Any] = {
                "model": provider.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature
            }
            
            async with httpx.AsyncClient(timeout=APIConfig.REQUEST_TIMEOUT) as client:
                response: httpx.Response = await client.post(
                    f"{provider.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
            
            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                content: str = data["choices"][0]["message"]["content"]
                
                if content:
                    debug_success(f"[{provider.name}] Request successful!")
                    return LLMResponse(
                        status=LLMStatus.SUCCESS,
                        content=content,
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
            else:
                error_body: str = response.text[:200]
                return self._classify_http_error(
                    provider, response.status_code, error_body
                )
                
        except Exception as e:
            return self._classify_exception(provider, e)
    
    async def _query_gemini(self, provider: LLMProvider, prompt: str) -> LLMResponse:
        """
        Query Google Gemini API using REST endpoint.
        
        Args:
            provider (LLMProvider): The Gemini provider configuration.
            prompt (str): The prompt to send.
            
        Returns:
            LLMResponse: Result from Gemini.
        """
        debug_info(f"[{provider.name}] Attempting query with model: {provider.model}")
        
        try:
            url: str = (
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/{provider.model}:generateContent"
                f"?key={provider.api_key}"
            )
            
            payload: dict[str, Any] = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature
                }
            }
            
            async with httpx.AsyncClient(timeout=APIConfig.REQUEST_TIMEOUT) as client:
                response: httpx.Response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
            
            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                content: str = (
                    data["candidates"][0]["content"]["parts"][0]["text"]
                )
                
                if content:
                    debug_success(f"[{provider.name}] Request successful!")
                    return LLMResponse(
                        status=LLMStatus.SUCCESS,
                        content=content,
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
            else:
                error_body: str = response.text[:200]
                return self._classify_http_error(
                    provider, response.status_code, error_body
                )
                
        except Exception as e:
            return self._classify_exception(provider, e)
    
    def _classify_http_error(
        self,
        provider: LLMProvider,
        status_code: int,
        error_body: str
    ) -> LLMResponse:
        """
        Classify an HTTP error response into the appropriate LLMStatus.
        
        Args:
            provider (LLMProvider): The provider that returned the error.
            status_code (int): HTTP status code.
            error_body (str): Response body for logging.
            
        Returns:
            LLMResponse: Error response with classified status.
        """
        error_msg: str = f"HTTP {status_code}: {error_body}"
        
        if status_code == 429:
            debug_warning(f"[{provider.name}] Rate limited: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.RATE_LIMITED,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
        elif status_code in (401, 403):
            debug_error(f"[{provider.name}] API key issue: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.API_KEY_MISSING,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
        elif status_code == 404:
            debug_error(f"[{provider.name}] Model not found: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.MODEL_NOT_FOUND,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
        else:
            debug_error(f"[{provider.name}] Error: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.ERROR,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
    
    def _classify_exception(self, provider: LLMProvider, exc: Exception) -> LLMResponse:
        """
        Classify a Python exception into the appropriate LLMStatus.
        
        Args:
            provider (LLMProvider): The provider that raised the exception.
            exc (Exception): The exception.
            
        Returns:
            LLMResponse: Error response with classified status.
        """
        error_msg: str = str(exc)
        
        if "429" in error_msg or "rate" in error_msg.lower():
            debug_warning(f"[{provider.name}] Rate limited: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.RATE_LIMITED,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            debug_error(f"[{provider.name}] API key issue: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.API_KEY_MISSING,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
        else:
            debug_error(f"[{provider.name}] Error: {error_msg[:100]}")
            return LLMResponse(
                status=LLMStatus.ERROR,
                content=None,
                provider=provider.name,
                model=provider.model,
                error_message=error_msg
            )
    
    async def query(self, prompt: str) -> LLMResponse:
        """
        Send a query to the LLM with automatic fallback.
        
        Args:
            prompt (str): The prompt to send.
            
        Returns:
            LLMResponse: The result from the first successful provider.
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
            
            # Use appropriate query method based on provider type
            if provider.provider_type == "ai4chat":
                response: LLMResponse = await self._query_ai4chat(prompt)
            elif provider.provider_type == "google":
                response = await self._query_gemini(provider, prompt)
            else:
                response = await self._query_openai_compatible(provider, prompt)
            
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
            list[str]: List of provider names.
        """
        return [p.name for p in self.providers]


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the LLM service singleton.
    
    Returns:
        LLMService: Singleton instance.
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(temperature=APIConfig.DEFAULT_TEMPERATURE)
    return _llm_service
