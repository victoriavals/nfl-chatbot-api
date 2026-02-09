"""
Configuration module for NFL Chatbot API.

This module provides centralized configuration for the FastAPI backend,
importing settings from the parent env.py file.
"""

import sys
import os
from typing import ClassVar

# Add parent directory to path to import env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from env import (
        ConstantsVar,
        debug_info,
        debug_error,
        debug_warning,
        debug_success,
        debug_critical,
        debug_prompt,
        IS_DEBUG_MODE,
        IS_PROMPT_CHECK
    )
except ImportError as e:
    print(f"Error: Could not import env.py from parent directory: {e}")
    sys.exit(1)


class APIConfig:
    """
    API-specific configuration settings.
    
    Contains settings for authentication, CORS, and API behavior.
    """
    
    # API Authentication
    API_KEY: ClassVar[str] = os.getenv("NFL_CHATBOT_API_KEY", "nfl-dev-key-2026")
    
    # CORS Settings
    ALLOWED_ORIGINS: ClassVar[list[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://*.vercel.app",
        "*"  # Allow all for development
    ]
    
    # Memory Settings
    MAX_MEMORY_LENGTH: ClassVar[int] = 10  # Max messages per user
    MEMORY_CLEANUP_THRESHOLD: ClassVar[int] = 100  # Cleanup when total users exceed
    
    # LLM Settings
    DEFAULT_TEMPERATURE: ClassVar[float] = 0.7
    REQUEST_TIMEOUT: ClassVar[int] = 30  # seconds
    
    # Knowledge Base Path
    KNOWLEDGE_BASE_PATH: ClassVar[str] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "myData.md"
    )


# Re-export from env for convenience
__all__ = [
    "ConstantsVar",
    "APIConfig",
    "debug_info",
    "debug_error", 
    "debug_warning",
    "debug_success",
    "debug_critical",
    "debug_prompt",
    "IS_DEBUG_MODE",
    "IS_PROMPT_CHECK"
]
