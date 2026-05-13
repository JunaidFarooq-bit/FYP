import json
from openai import OpenAI
from django.conf import settings

_client = None


def get_client():
    """Lazy initialization of AI client (Groq preferred, OpenAI fallback)."""
    global _client
    if _client is None:
        if getattr(settings, "USE_GROQ", True):
            api_key = getattr(settings, "GROQ_API_KEY", None)
            if api_key:
                _client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        else:
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if api_key:
                _client = OpenAI(api_key=api_key)
    return _client


def get_model():
    """Return the active model name based on provider."""
    if getattr(settings, "USE_GROQ", True):
        return getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    return getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")


def refine_keywords(keywords: list[str], page_topic: str = "", context: str = "") -> dict:
    """
    Send keywords to GPT-3.5 for intent grouping and enrichment.
    Returns a dict with grouped keywords and suggested focus keywords.
    
    Args:
        keywords: List of keywords to refine
        page_topic: Optional page topic hint
        context: Optional RAG context from similar content analyses
    """
    if not keywords:
        return {"groups": {}, "focus_keywords": [], "raw": []}

    client = get_client()
    if client is None:
        # Graceful fallback when OpenAI API key is not configured
        return {
            "groups": {"All": keywords},
            "focus_keywords": keywords[:5],
            "raw": keywords,
        }

    keyword_list = "\n".join(f"- {kw}" for kw in keywords[:30])  # cap at 30

    topic_hint = f" The page is about: {page_topic}." if page_topic else ""
    
    # Include RAG context if provided
    context_section = f"\n\n{context}\n\n" if context else ""

    prompt = f"""You are an SEO expert.{topic_hint}{context_section}
Group the following keywords by search intent (Informational, Navigational, Transactional, Commercial).
Also suggest the top 5 focus keywords.

Keywords:
{keyword_list}

Respond ONLY with valid JSON in this exact format:
{{
  "groups": {{
    "Informational": ["keyword1", "keyword2"],
    "Navigational": [],
    "Transactional": ["keyword3"],
    "Commercial": ["keyword4"]
  }},
  "focus_keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )
        raw_text = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result = json.loads(raw_text)
        result["raw"] = keywords
        return result

    except (json.JSONDecodeError, Exception) as e:
        # Graceful fallback — return ungrouped keywords
        return {
            "groups": {"Uncategorized": keywords},
            "focus_keywords": keywords[:5],
            "raw": keywords,
            "error": str(e),
        }