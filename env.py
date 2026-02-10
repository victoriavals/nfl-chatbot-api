"""
Environment configuration module.

This module centralizes all environment variables and API keys loading.
"""

import sys
import os
import logging

# Append project root to path to ensure utils can be imported if constant_var is run directly or from subdirs
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

IS_DEBUG_MODE: bool = True
IS_PROMPT_CHECK: bool = True

load_dotenv(override=True)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
app_logger: logging.Logger = logging.getLogger(__name__)


class ConstantsVar:
    """
    Centralized configuration class for the application.
    
    Loads environment variables and defines default constants.
    All API keys should be loaded from the .env file using os.getenv().
    """
    
    # Result Constants
    PASS_RESULT: int = 0
    FAIL_RESULT: int = 1
    UNDEFINED_RESULT: int = 2

    ## My API Key
    MY_OPENROUTER_API_KEY: str = os.getenv("MY_OPENROUTER_API_KEY", "")
    MY_CEREBRAS_API_KEY: str = os.getenv("MY_CEREBRAS_API_KEY", "")
    MY_GEMINI_API_KEY: str = os.getenv("MY_GEMINI_API_KEY", "")
    MY_GROQ_API_KEY: str = os.getenv("MY_GROQ_API_KEY", "")

    ## Supabase
    SUPABASE_PROJECT_URL: str = os.getenv("SUPABASE_PROJECT_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASEANON_PUBLIC_KEY", "")
    

def debug_error(text: str) -> None:
    """
    Log an error message using the file logger.
    
    Params:
        text (str): The error message to log.
    
    Returns:
        None
    """
    if IS_DEBUG_MODE:
        app_logger.error(text)


def debug_info(text: str) -> None:
    """
    Log an informational message using the file logger.
    
    Params:
        text (str): The info message to log.
    
    Returns:
        None
    """
    if IS_DEBUG_MODE:
        app_logger.info(text)


def debug_warning(text: str) -> None:
    """
    Log a warning message using the file logger.
    
    Params:
        text (str): The warning message to log.
    
    Returns:
        None
    """
    if IS_DEBUG_MODE:
        app_logger.warning(text)


def debug_success(text: str) -> None:
    """
    Log a success message (as info) using the file logger.
    
    Params:
        text (str): The success message to log.
    
    Returns:
        None
    """
    if IS_DEBUG_MODE:
        # Logging doesn't have a 'success' level, map to INFO with a prefix
        app_logger.info(f"[SUCCESS] {text}")


def debug_critical(text: str) -> None:
    """
    Log a critical message using the file logger.
    
    Params:
        text (str): The critical message to log.
    
    Returns:
        None
    """
    if IS_DEBUG_MODE:
        app_logger.critical(text)


def debug_prompt(text: str) -> None:
    """
    Log a prompt message using the dedicated prompt logger.
    
    Params:
        text (str): The prompt message to log.
    
    Returns:
        None
    """
    if IS_PROMPT_CHECK:
        app_logger.info(f"[PROMPT] {text}")


if __name__ == "__main__":
    print("=" * 60)
    print("Environment Configuration Check")
    print("=" * 60)
    
    # API Keys (showing first/last 4 chars for security)
    def mask_key(key: str) -> str:
        """Mask API key for secure display."""
        if not key or len(key) < 10:
            return "NOT SET"
        return f"{key[:4]}...{key[-4:]}"
    
    print("\n--- API Keys ---")
    print(f"OpenRouter API Key: {mask_key(ConstantsVar.MY_OPENROUTER_API_KEY)}")
    print(f"Gemini API Key: {mask_key(ConstantsVar.MY_GEMINI_API_KEY)}")
    print(f"Groq API Key: {mask_key(ConstantsVar.MY_GROQ_API_KEY)}")
    print(f"Cerebras API Key: {mask_key(ConstantsVar.MY_CEREBRAS_API_KEY)}")
    
    print("\n--- Debug Settings ---")
    print(f"Debug Mode: {IS_DEBUG_MODE}")
    print(f"Prompt Check: {IS_PROMPT_CHECK}")
    print("=" * 60)
