"""
OpenAI/OpenRouter Client Helper
Supports both OpenAI and OpenRouter APIs with proper error handling
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Custom exception for AI client errors"""
    pass


def get_ai_client() -> OpenAI:
    """
    Get configured AI client (supports Groq, OpenRouter, and OpenAI).
    Groq is preferred when USE_GROQ=True (default).
    """
    use_groq = getattr(settings, 'USE_GROQ', True)
    use_openrouter = getattr(settings, 'USE_OPENROUTER', False)

    if use_groq:
        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            raise AIClientError("GROQ_API_KEY not configured in settings")
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        logger.debug("[AI] Client initialized (provider=groq)")
        return client

    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise AIClientError("OPENAI_API_KEY not configured in settings")

    if use_openrouter:
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        logger.debug("[AI] Client initialized (provider=openrouter)")
    else:
        client = OpenAI(api_key=api_key)
        logger.debug("[AI] Client initialized (provider=openai)")
    return client


def get_ai_model() -> str:
    """Return the configured model name based on active provider."""
    if getattr(settings, 'USE_GROQ', True):
        return getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
    return getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')


def get_ai_completion(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    system_message: Optional[str] = None
) -> Optional[str]:
    """
    Get AI completion with proper error handling
    
    Args:
        prompt: User prompt
        model: Model to use (defaults to settings.OPENAI_MODEL)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        system_message: Optional system message
        
    Returns:
        Completion text or None if failed
    """
    try:
        client = get_ai_client()
        model = model or get_ai_model()
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logger.exception("[AI] Completion failed: %s", e)
        return None


def get_ai_completion_safe(
    prompt: str,
    fallback: str = "Analysis unavailable due to AI service error.",
    **kwargs
) -> str:
    """
    Get AI completion with guaranteed non-None response
    
    Args:
        prompt: User prompt
        fallback: Fallback message if AI fails
        **kwargs: Additional arguments for get_ai_completion
        
    Returns:
        Completion text or fallback message
    """
    return get_ai_completion(prompt, **kwargs) or fallback