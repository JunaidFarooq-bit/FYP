"""
AI-Powered Content Optimization Service (Phase 3)
Provides specific recommendations for content improvements.

Features:
- Heading structure optimization
- Keyword placement recommendations
- Content gap filling suggestions
- Readability improvements
- Meta tag optimization
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from django.conf import settings


def _get_smart_content_slice(content_text: str, num_paragraphs: int = 10, max_chars: int = 2000) -> str:
    """
    Intelligently slice content for LLM prompts.
    (Duplicate of llm_expander.get_smart_content_slice for local use)
    """
    if not content_text:
        return ""
    
    # Split into paragraphs
    raw_paragraphs = re.split(r'\n\n+|\n', content_text)
    
    # Clean and score paragraphs
    scored_paragraphs = []
    for para in raw_paragraphs:
        para = para.strip()
        if len(para) < 30:
            continue
        
        char_count = len(para)
        word_count = len(para.split())
        
        # Character density
        alnum_chars = sum(1 for c in para if c.isalnum() or c.isspace())
        density = alnum_chars / max(char_count, 1)
        
        # Punctuation penalty
        punct_count = sum(1 for c in para if c in '!@#$%^&*()_+-=[]{}|;:,.<>?')
        punct_ratio = punct_count / max(char_count, 1)
        
        # Composite score
        score = (word_count * 0.6) + (density * 100) - (punct_ratio * 50)
        scored_paragraphs.append((para, score, char_count))
    
    if not scored_paragraphs:
        return content_text[:max_chars].strip()
    
    # Sort by score descending
    scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
    
    # Take top N paragraphs
    selected = []
    total_chars = 0
    
    for para, score, char_count in scored_paragraphs[:num_paragraphs]:
        if total_chars + char_count > max_chars:
            remaining = max_chars - total_chars
            if remaining > 100:
                selected.append(para[:remaining])
            break
        selected.append(para)
        total_chars += char_count
    
    return "\n\n".join(selected).strip()

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
    """Return active model name based on provider."""
    if getattr(settings, "USE_GROQ", True):
        return getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    return getattr(settings, "OPENAI_MODEL", "gpt-4")


def analyze_content_optimization(
    content_text: str,
    target_keywords: List[str],
    current_title: str = "",
    current_meta_desc: str = "",
    page_topic: str = "",
    content_type: str = "blog_post"  # blog_post, product_page, landing_page, etc.
) -> Dict:
    """
    Comprehensive content optimization analysis using AI.
    
    Args:
        content_text: Full page content
        target_keywords: Keywords to optimize for
        current_title: Current page title
        current_meta_desc: Current meta description
        page_topic: Page topic/context
        content_type: Type of content
        
    Returns:
        Dict with optimization recommendations
    """
    client = get_client()
    if client is None:
        return {"error": "OpenAI API not configured", "optimizations": []}
    
    # Extract headings for analysis
    headings = extract_headings(content_text)
    content_summary = content_text[:2500] if len(content_text) > 2500 else content_text
    
    from ..utils.year_injector import build_year_context
    _year_ctx = build_year_context()

    prompt = f"""You are a senior SEO content strategist. Analyze this content and provide specific optimization recommendations.

CONTENT TYPE: {content_type}
PAGE TOPIC: {page_topic or "Not specified"}
CURRENT YEAR: {_year_ctx['current_year']}

CURRENT TITLE: {current_title or "Not provided"}
CURRENT META DESCRIPTION: {current_meta_desc or "Not provided"}

TARGET KEYWORDS: {', '.join(target_keywords[:10])}

IMPORTANT: When suggesting title/meta examples that reference a year, ALWAYS use {_year_ctx['current_year']} (never older years).

EXISTING HEADINGS:
{chr(10).join(f"H{h['level']}: {h['text']}" for h in headings[:15])}

CONTENT SAMPLE:
{content_summary}

Provide optimization recommendations in these categories:

1. Title Tag Optimization
2. Meta Description Optimization
3. Heading Structure (H1-H6)
4. Keyword Placement
5. Content Gaps (missing topics)
6. Readability Improvements
7. Internal Linking Opportunities
8. Call-to-Action (CTA) Recommendations

For each recommendation:
- Current state (what exists now)
- Issue/problem identified
- Specific recommendation (actionable)
- Priority (High/Medium/Low)
- Expected impact

Respond ONLY with valid JSON:
{{
  "optimization_score": 75,
  "title_recommendations": [
    {{
      "current": "Current title",
      "recommended": "Better optimized title",
      "reason": "Why this is better",
      "priority": "High"
    }}
  ],
  "meta_recommendations": [
    {{
      "current": "Current meta",
      "recommended": "Better meta description",
      "reason": "Why this improves CTR",
      "priority": "High"
    }}
  ],
  "heading_recommendations": [
    {{
      "action": "add" | "modify" | "reorder",
      "current_heading": "Existing heading or null",
      "recommended_heading": "Suggested heading",
      "level": 2,
      "reason": "Why this helps SEO",
      "priority": "Medium"
    }}
  ],
  "keyword_placement": [
    {{
      "keyword": "target keyword",
      "current_mentions": 2,
      "recommended_mentions": 4,
      "placement_locations": ["H1", "first paragraph", "H2 section"],
      "priority": "High"
    }}
  ],
  "content_gaps": [
    {{
      "topic": "Missing topic",
      "reason": "Why this should be covered",
      "suggested_section": "Where to add this",
      "priority": "Medium"
    }}
  ],
  "readability_improvements": [
    {{
      "issue": "Long paragraphs",
      "location": "Paragraph 3",
      "recommendation": "Break into 2-3 shorter paragraphs",
      "priority": "Low"
    }}
  ],
  "quick_wins": [
    "Easy optimization 1",
    "Easy optimization 2"
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2500,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        # Clean markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        result["analysis_type"] = "ai_content_optimization"
        result["content_type"] = content_type

        # Inject current year into all title/meta/heading recommendations so
        # output examples never carry stale references like "Guide 2024".
        try:
            from ..utils.year_injector import inject_in_dict
            result = inject_in_dict(result, refresh_outdated=True)
        except Exception:
            pass

        return result
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Content optimization error: {e}")
        return {
            "error": str(e),
            "optimization_score": 50,
            "optimizations": [],
        }


def generate_section_outline(
    target_keyword: str,
    page_topic: str = "",
    content_goal: str = "inform",  # inform, convert, educate
    word_count_target: int = 1500
) -> Dict:
    """
    Generate AI-powered content outline for a target keyword.
    
    Args:
        target_keyword: Primary keyword to target
        page_topic: Broad topic context
        content_goal: Purpose of content
        word_count_target: Target word count
        
    Returns:
        Dict with complete content outline
    """
    client = get_client()
    if client is None:
        return {"error": "OpenAI API not configured"}
    
    prompt = f"""Create a detailed SEO-optimized content outline for:

PRIMARY KEYWORD: {target_keyword}
PAGE TOPIC: {page_topic or "Related to " + target_keyword}
CONTENT GOAL: {content_goal}
TARGET LENGTH: {word_count_target} words

Provide:
1. Optimized title (H1)
2. SEO-friendly URL slug
3. Meta description (155 chars max)
4. Detailed H2-H4 structure with word count allocation
5. Key points to cover in each section
6. Internal linking opportunities
7. LSI/secondary keywords to include
8. Call-to-action placement
9. Content format recommendations

Respond ONLY with valid JSON:
{{
  "title": "Optimized H1 Title",
  "url_slug": "optimized-url-slug",
  "meta_description": "Compelling meta description...",
  "estimated_word_count": {word_count_target},
  "sections": [
    {{
      "heading": "H2 Heading Text",
      "level": 2,
      "word_count": 300,
      "key_points": ["Point 1", "Point 2"],
      "secondary_keywords": ["related term 1", "related term 2"],
      "format": "paragraphs" | "bullet_list" | "numbered_list" | "table"
    }}
  ],
  "internal_links": [
    {{
      "anchor_text": "related article",
      "target_keyword": "target keyword",
      "placement_section": "Section 3"
    }}
  ],
  "cta_placement": {{
    "primary_cta": {{
      "text": "Sign up now",
      "location": "After section 4"
    }},
    "secondary_ctas": [
      {{
        "text": "Learn more",
        "location": "Mid-content"
      }}
    ]
  }}
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        result["target_keyword"] = target_keyword
        result["source"] = "ai_outline_generator"
        
        return result
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Outline generation error: {e}")
        return {"error": str(e), "target_keyword": target_keyword}


def analyze_readability_improvements(
    content_text: str,
    target_audience: str = "general"
) -> Dict:
    """
    Analyze content readability and provide specific improvements.
    
    Args:
        content_text: Content to analyze
        target_audience: Target audience level (beginner/intermediate/expert)
        
    Returns:
        Readability analysis with improvements
    """
    client = get_client()
    if client is None:
        return {"error": "OpenAI API not configured"}
    
    # Calculate basic stats
    sentences = re.split(r'[.!?]+', content_text)
    avg_sentence_length = len(content_text.split()) / max(len(sentences), 1)
    
    # Smart content slicing: get richest paragraphs
    content_sample = _get_smart_content_slice(content_text, num_paragraphs=10, max_chars=2000)
    
    prompt = f"""Analyze this content for readability and provide specific improvements.

TARGET AUDIENCE: {target_audience}
CURRENT AVG SENTENCE LENGTH: {avg_sentence_length:.1f} words

CONTENT SAMPLE:
{content_sample}

Analyze and provide:
1. Readability score estimate (0-100)
2. Flesch-Kincaid grade level estimate
3. Specific sentences that are too complex
4. Simplified rewrites for complex sentences
5. Paragraph structure issues
6. Vocabulary recommendations
7. Transition/flow improvements

Respond ONLY with valid JSON:
{{
  "readability_score": 65,
  "grade_level": 10,
  "sentence_analysis": [
    {{
      "original": "Original complex sentence",
      "simplified": "Simpler version",
      "issue": "Too many clauses"
    }}
  ],
  "paragraph_improvements": [
    {{
      "paragraph_index": 3,
      "issue": "Too long",
      "recommendation": "Split into 2 paragraphs after '...'"
    }}
  ],
  "vocabulary_suggestions": [
    {{
      "complex_word": "utilize",
      "simpler_alternative": "use",
      "context": "sentence context"
    }}
  ],
  "general_recommendations": [
    "Add transition words between paragraphs",
    "Use bullet points for lists"
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1800,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        result["analysis_type"] = "readability"
        result["target_audience"] = target_audience
        
        return result
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Readability analysis error: {e}")
        return {"error": str(e), "target_audience": target_audience}


def extract_headings(content_text: str) -> List[Dict]:
    """Extract headings from content (simulated from plain text)."""
    headings = []
    lines = content_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detect potential headings by patterns
        if line.isupper() and len(line) < 100:
            headings.append({"level": 2, "text": line.title()})
        elif line.endswith(':') and len(line) < 100:
            headings.append({"level": 3, "text": line.rstrip(':')})
        elif line.startswith(('## ', '### ', '#### ')):
            level = line.count('#')
            text = line.lstrip('#').strip()
            headings.append({"level": min(level, 6), "text": text})
    
    return headings


def generate_meta_tags(
    target_keyword: str,
    content_summary: str,
    page_type: str = "article"
) -> Dict:
    """
    Generate optimized meta title and description.
    
    Args:
        target_keyword: Primary keyword
        content_summary: Brief content summary
        page_type: Type of page
        
    Returns:
        Dict with optimized meta tags
    """
    client = get_client()
    if client is None:
        return {"error": "OpenAI API not configured"}
    
    prompt = f"""Create optimized meta tags for SEO.

TARGET KEYWORD: {target_keyword}
PAGE TYPE: {page_type}
CONTENT SUMMARY: {content_summary[:500]}

Requirements:
- Title: 50-60 characters, compelling, include keyword
- Meta Description: 150-160 characters, include keyword, clear CTA

Respond ONLY with valid JSON:
{{
  "title": "Optimized Title | Brand",
  "title_length": 55,
  "meta_description": "Compelling description with keyword...",
  "meta_length": 158,
  "og_title": "Social media title",
  "og_description": "Social media description"
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        return json.loads(raw_text)
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Meta generation error: {e}")
        return {"error": str(e)}


# Convenience function for complete optimization analysis
def get_complete_optimization_package(
    content_text: str,
    target_keywords: List[str],
    current_title: str = "",
    current_meta_desc: str = "",
    page_topic: str = "",
    content_type: str = "blog_post"
) -> Dict:
    """
    Get comprehensive content optimization analysis.
    
    Combines multiple analyses into one package.
    """
    # Main optimization analysis
    main_analysis = analyze_content_optimization(
        content_text=content_text,
        target_keywords=target_keywords,
        current_title=current_title,
        current_meta_desc=current_meta_desc,
        page_topic=page_topic,
        content_type=content_type
    )
    
    # Readability analysis
    readability = analyze_readability_improvements(
        content_text=content_text,
        target_audience="general"
    )
    
    # Meta tag generation
    meta_tags = generate_meta_tags(
        target_keyword=target_keywords[0] if target_keywords else "",
        content_summary=content_text,
        page_type=content_type
    )
    
    return {
        "optimization_analysis": main_analysis,
        "readability_analysis": readability,
        "meta_recommendations": meta_tags,
        "summary": {
            "total_optimizations": (
                len(main_analysis.get("title_recommendations", [])) +
                len(main_analysis.get("heading_recommendations", [])) +
                len(main_analysis.get("keyword_placement", []))
            ),
            "priority_actions": main_analysis.get("quick_wins", []),
            "estimated_impact": "High" if main_analysis.get("optimization_score", 0) < 70 else "Medium"
        }
    }
