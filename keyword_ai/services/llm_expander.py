"""
Advanced LLM-Powered Keyword Expansion Service (Phase 3)
Uses GPT-4 for intelligent keyword discovery with reasoning.

Features:
- Semantic keyword expansion with explanations
- Long-tail keyword generation with search volume estimates
- Competitor gap keyword suggestions
- Question-based keyword discovery
- Trending keyword identification
"""

import json
from typing import List, Dict, Optional
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
    return getattr(settings, "OPENAI_MODEL", "gpt-4")


def expand_keywords_with_llm(
    content_text: str,
    existing_keywords: List[str],
    page_topic: str = "",
    target_audience: str = "",
    num_suggestions: int = 15
) -> List[Dict]:
    """
    Use LLM to intelligently expand keywords with reasoning.
    
    Args:
        content_text: The page content
        existing_keywords: Keywords already identified
        page_topic: Topic description
        target_audience: Target audience description
        num_suggestions: Number of new keywords to suggest
        
    Returns:
        List of suggestion dicts with reasoning
    """
    client = get_client()
    if client is None:
        return []
    
    # Truncate content for token limit
    content_summary = content_text[:2000] if len(content_text) > 2000 else content_text
    existing_kw_list = ", ".join(existing_keywords[:20])
    
    prompt = f"""You are an expert SEO strategist with 10+ years of experience.

Analyze the following content and suggest {num_suggestions} NEW keyword opportunities that are NOT in the existing list.

CONTENT:
{content_summary}

EXISTING KEYWORDS (DO NOT SUGGEST THESE):
{existing_kw_list}

PAGE TOPIC: {page_topic or "Not specified"}
TARGET AUDIENCE: {target_audience or "General"}

For each suggested keyword, provide:
1. The keyword phrase
2. Search intent (Informational/Transactional/Commercial/Navigational)
3. Estimated search volume (Very High/High/Medium/Low/Very Low)
4. Competition level (High/Medium/Low)
5. Strategic reasoning - why this keyword is valuable
6. Content recommendation - specific advice on how to target this keyword

Respond ONLY with valid JSON in this format:
{{
  "suggestions": [
    {{
      "keyword": "example keyword phrase",
      "intent": "Informational",
      "search_volume": "High",
      "competition": "Medium",
      "reasoning": "This keyword captures users looking for...",
      "recommendation": "Add an H2 section titled 'Example Keyword Guide'..."
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        # Clean markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        suggestions = result.get("suggestions", [])
        
        # Add metadata
        for sug in suggestions:
            sug["source"] = "llm_expansion"
            sug["confidence"] = _calculate_confidence(sug)
        
        return suggestions
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"LLM expansion error: {e}")
        return []


def analyze_competitor_gaps_with_llm(
    user_content: str,
    competitor_keywords: List[str],
    user_keywords: List[str],
    page_topic: str = ""
) -> List[Dict]:
    """
    Use LLM to analyze competitor keyword gaps with strategic insights.
    
    Args:
        user_content: User's page content
        competitor_keywords: Keywords competitors rank for
        user_keywords: User's current keywords
        page_topic: Page topic description
        
    Returns:
        List of gap opportunities with strategic analysis
    """
    client = get_client()
    if client is None:
        return []
    
    # Find gaps
    competitor_set = set(kw.lower() for kw in competitor_keywords)
    user_set = set(kw.lower() for kw in user_keywords)
    gaps = list(competitor_set - user_set)
    
    if not gaps:
        return []
    
    # Limit to top 20 gaps for analysis
    gaps_to_analyze = gaps[:20]
    
    prompt = f"""You are a competitive SEO analyst.

Analyze these competitor keyword gaps and prioritize them by strategic value.

USER'S PAGE TOPIC: {page_topic or "Not specified"}

COMPETITOR KEYWORDS (User is NOT targeting these):
{chr(10).join(f"- {kw}" for kw in gaps_to_analyze)}

USER'S CURRENT KEYWORDS:
{chr(10).join(f"- {kw}" for kw in user_keywords[:15])}

For the top 10 most valuable gaps, provide:
1. The keyword
2. Priority (High/Medium/Low)
3. Why this gap matters - strategic importance
4. Difficulty to rank (1-10 scale)
5. Traffic potential (High/Medium/Low)
6. Actionable recommendation

Respond ONLY with valid JSON:
{{
  "gaps": [
    {{
      "keyword": "example keyword",
      "priority": "High",
      "strategic_importance": "This keyword drives qualified traffic...",
      "difficulty": 7,
      "traffic_potential": "High",
      "recommendation": "Create comprehensive guide targeting this keyword..."
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        gaps = result.get("gaps", [])
        
        for gap in gaps:
            gap["source"] = "llm_gap_analysis"
            gap["is_gap"] = True
        
        return gaps
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Gap analysis error: {e}")
        return []


def generate_question_keywords(
    content_text: str,
    page_topic: str = "",
    num_questions: int = 10
) -> List[Dict]:
    """
    Generate question-based keywords (People Also Ask style).
    
    Args:
        content_text: Page content
        page_topic: Topic description
        num_questions: Number of questions to generate
        
    Returns:
        List of question keywords with answers
    """
    client = get_client()
    if client is None:
        return []
    
    content_summary = content_text[:1500] if len(content_text) > 1500 else content_text
    
    prompt = f"""You are an SEO expert specializing in featured snippets and People Also Ask optimization.

Based on this content, generate {num_questions} question-based search queries that users might ask.

CONTENT:
{content_summary}

PAGE TOPIC: {page_topic or "General"}

For each question:
1. The question as a search query
2. Question type (What/How/Why/When/Where/Who/Which/Can/Does/Is)
3. Search volume estimate (High/Medium/Low)
4. Brief answer that could appear in a featured snippet
5. Recommended content format (Paragraph/List/Table/Video)

Respond ONLY with valid JSON:
{{
  "questions": [
    {{
      "question": "What is SEO optimization?",
      "type": "What",
      "search_volume": "High",
      "answer": "SEO optimization is the process of improving...",
      "format": "Paragraph"
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        questions = result.get("questions", [])
        
        for q in questions:
            q["source"] = "llm_questions"
            q["keyword_type"] = "question"
        
        return questions
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Question generation error: {e}")
        return []


def get_keyword_clusters_with_llm(
    keywords: List[str],
    page_topic: str = ""
) -> Dict:
    """
    Use LLM to intelligently cluster keywords by topic and intent.
    
    Args:
        keywords: List of keywords to cluster
        page_topic: Page topic context
        
    Returns:
        Dict with clusters and analysis
    """
    client = get_client()
    if client is None:
        return {"clusters": {"All": keywords}, "themes": []}
    
    keyword_list = "\n".join(f"- {kw}" for kw in keywords[:40])
    
    prompt = f"""You are a semantic SEO expert.

Cluster these keywords into logical topic groups. Identify overarching themes.

KEYWORDS:
{keyword_list}

PAGE CONTEXT: {page_topic or "Not specified"}

Provide:
1. 3-5 topic clusters with names
2. Keywords assigned to each cluster
3. Primary theme for each cluster
4. Content angle recommendation for each cluster

Respond ONLY with valid JSON:
{{
  "clusters": {{
    "Cluster Name": ["keyword1", "keyword2"]
  }},
  "themes": [
    {{
      "theme": "Theme name",
      "description": "What this theme covers",
      "content_angle": "How to approach content for this theme"
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        return result
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Clustering error: {e}")
        return {"clusters": {"All": keywords}, "themes": [], "error": str(e)}


def _calculate_confidence(suggestion: Dict) -> float:
    """Calculate confidence score based on LLM suggestion quality."""
    confidence = 0.7  # Base confidence
    
    # Boost for detailed reasoning
    if len(suggestion.get("reasoning", "")) > 50:
        confidence += 0.1
    
    # Boost for actionable recommendation
    if len(suggestion.get("recommendation", "")) > 30:
        confidence += 0.1
    
    # Boost for high search volume
    if suggestion.get("search_volume") in ["Very High", "High"]:
        confidence += 0.05
    
    # Lower confidence for high competition
    if suggestion.get("competition") == "High":
        confidence -= 0.05
    
    return round(min(0.95, max(0.5, confidence)), 2)


# Batch processing for efficiency
def batch_expand_keywords(
    content_items: List[Dict],
    batch_size: int = 5
) -> List[List[Dict]]:
    """
    Process multiple content items in batches.
    
    Args:
        content_items: List of dicts with 'content', 'existing_keywords', 'page_topic'
        batch_size: Number of items to process per batch
        
    Returns:
        List of suggestion lists for each content item
    """
    results = []
    
    for i in range(0, len(content_items), batch_size):
        batch = content_items[i:i + batch_size]
        
        for item in batch:
            suggestions = expand_keywords_with_llm(
                content_text=item.get("content", ""),
                existing_keywords=item.get("existing_keywords", []),
                page_topic=item.get("page_topic", ""),
                num_suggestions=10
            )
            results.append(suggestions)
    
    return results
