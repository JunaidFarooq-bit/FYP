"""
OpenAI/OpenRouter Client Helper
Supports both OpenAI and OpenRouter APIs with proper error handling
Uses print statements for debugging
"""

from typing import Optional, Dict, Any
from django.conf import settings
from openai import OpenAI


class AIClientError(Exception):
    """Custom exception for AI client errors"""
    pass


def get_ai_client() -> OpenAI:
    """
    Get configured OpenAI client (supports both OpenAI and OpenRouter)
    
    Returns:
        OpenAI client instance
        
    Raises:
        AIClientError: If configuration is invalid
    """
    print("\n[AI] Initializing AI client...")
    
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    
    if not api_key:
        print("[AI] ERROR: OPENAI_API_KEY not configured in settings")
        raise AIClientError("OPENAI_API_KEY not configured in settings")
    
    print(f"[AI] API key present: {bool(api_key)}")
    print(f"[AI] API key starts with: {api_key[:10]}...")
    
    # Check if we should use OpenRouter
    use_openrouter = getattr(settings, 'USE_OPENROUTER', False)
    print(f"[AI] USE_OPENROUTER setting: {use_openrouter}")
    
    if use_openrouter:
        print("[AI] Using OpenRouter API")
        print("[AI] Base URL: https://openrouter.ai/api/v1")
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        print("[AI] Using OpenAI API")
        print("[AI] Base URL: https://api.openai.com/v1")
        client = OpenAI(api_key=api_key)
    
    print("[AI] Client initialized successfully")
    return client


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
    print("\n" + "="*80)
    print("[AI] Getting completion...")
    print("="*80)
    
    try:
        client = get_ai_client()
        model = model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        
        print(f"[AI] Model: {model}")
        print(f"[AI] Max tokens: {max_tokens}")
        print(f"[AI] Temperature: {temperature}")
        print(f"[AI] Prompt length: {len(prompt)} chars")
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
            print(f"[AI] System message included ({len(system_message)} chars)")
        
        messages.append({"role": "user", "content": prompt})
        
        print(f"[AI] Total messages: {len(messages)}")
        print(f"[AI] Sending request to API...")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        completion = response.choices[0].message.content
        
        print(f"[AI] SUCCESS: Received completion")
        print(f"[AI] Completion length: {len(completion)} chars")
        print(f"[AI] Preview: {completion[:100]}...")
        print("="*80 + "\n")
        
        return completion
        
    except Exception as e:
        print(f"\n[AI] ERROR: {e}")
        print(f"[AI] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
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
    result = get_ai_completion(prompt, **kwargs)
    
    if result:
        print(f"[AI] Returning AI-generated response")
        return result
    else:
        print(f"[AI] Returning fallback message")
        return fallback


# Example usage in your code:
def get_content_explanation(content: str, max_length: int = 500) -> str:
    """
    Get AI explanation of content
    
    Args:
        content: Content to explain
        max_length: Maximum length of content to analyze
        
    Returns:
        Explanation text
    """
    print(f"\n[EXPLAIN] Getting content explanation...")
    print(f"[EXPLAIN] Content length: {len(content)} chars")
    
    # Truncate content if too long
    truncated = content[:max_length] if len(content) > max_length else content
    
    if len(content) > max_length:
        print(f"[EXPLAIN] Truncated to {max_length} chars")
    
    prompt = f"""Analyze this content and provide a brief explanation of what makes it effective or ineffective for SEO:

Content:
{truncated}

Provide a 2-3 sentence analysis focusing on:
1. Content quality and relevance
2. SEO optimization signals
3. User engagement factors
"""
    
    system_message = "You are an SEO expert analyzing web content for optimization opportunities."
    
    print(f"[EXPLAIN] Requesting analysis from AI...")
    
    result = get_ai_completion_safe(
        prompt=prompt,
        system_message=system_message,
        max_tokens=300,
        temperature=0.5,
        fallback="Content analysis unavailable."
    )
    
    print(f"[EXPLAIN] Analysis complete")
    return result