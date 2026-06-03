"""
LLM-Powered Traffic & CTR Estimator (Replaces heuristic estimation)

Uses LLM to provide intelligent search volume, CPC, and keyword difficulty estimates
based on keyword semantics, intent, and market knowledge.

Much more accurate than word-count heuristics.
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from .llm_refiner import get_client, get_model
from SEOAnalyzer.services.circuit_breaker import groq_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)


@dataclass
class LLMTrafficEstimate:
    """Traffic estimate from LLM."""
    keyword: str
    monthly_volume: int
    volume_confidence: str  # high | medium | low
    cpc_usd: float
    keyword_difficulty: int  # 0-100
    competition_level: str  # Low | Medium | High
    search_intent: str  # informational | commercial | transactional | navigational
    reasoning: str


def _parse_llm_response(raw_text: str, keyword: str) -> LLMTrafficEstimate:
    """Parse LLM JSON response into estimate object."""
    try:
        # Clean markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        data = json.loads(raw_text.strip())
        
        return LLMTrafficEstimate(
            keyword=keyword,
            monthly_volume=int(data.get("monthly_volume", 1000)),
            volume_confidence=data.get("volume_confidence", "medium"),
            cpc_usd=float(data.get("cpc_usd", 1.0)),
            keyword_difficulty=int(data.get("keyword_difficulty", 50)),
            competition_level=data.get("competition_level", "Medium"),
            search_intent=data.get("search_intent", "informational"),
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Failed to parse LLM traffic response for '{keyword}': {e}")
        # Return sensible fallback
        return LLMTrafficEstimate(
            keyword=keyword,
            monthly_volume=1000,
            volume_confidence="low",
            cpc_usd=1.0,
            keyword_difficulty=50,
            competition_level="Medium",
            search_intent="informational",
            reasoning="Fallback estimate due to parsing error",
        )


def estimate_keyword_traffic_llm(
    keyword: str,
    page_topic: str = "",
    target_region: str = "GLOBAL",
) -> LLMTrafficEstimate:
    """
    Use LLM to estimate traffic metrics for a single keyword.
    
    Args:
        keyword: The keyword to estimate
        page_topic: Context about the page content
        target_region: Geographic region (NA, EU, APAC, LATAM, MEA, GLOBAL)
    
    Returns:
        LLMTrafficEstimate with volume, CPC, difficulty, and reasoning
    """
    logger.info(f"[LLM-ESTIMATE] Requesting LLM traffic estimate for: '{keyword}'")
    
    client = get_client()
    if client is None:
        logger.warning("[LLM-ESTIMATE] LLM client not available (check GROQ_API_KEY or OPENAI_API_KEY), using fallback")
        return _fallback_estimate(keyword)
    
    topic_context = f"The page is about: {page_topic}." if page_topic else ""
    region_context = f"Target region: {target_region}." if target_region != "GLOBAL" else ""
    
    prompt = f"""You are a senior SEO data analyst at a top-tier digital marketing agency. You specialize in search volume forecasting, CPC estimation, and keyword difficulty assessment. Your estimates are used for million-dollar budget allocations, so accuracy is critical.

## INDUSTRY BENCHMARK DATA (2024 Google Ads / Ahrefs / SEMrush averages)

**Search Volume Tiers:**
- Head terms (1-2 words): 10K-500K/month (highly competitive)
- Mid-tail (3-4 words): 1K-20K/month (moderate competition)
- Long-tail (5+ words): 100-2K/month (low competition, high conversion)
- Question keywords: 20% lower volume than equivalent statements
- "Best" + category: 3x volume of generic category terms
- "Near me" / location: 40% lower volume but 2x conversion intent

**CPC Benchmarks by Industry (USD):**
- Finance/Insurance/Legal: $5-$50 (extremely high value)
- Healthcare/Medical: $2-$15 (high trust barrier)
- SaaS/B2B Software: $3-$25 (high LTV)
- E-commerce/Retail: $0.50-$3 (competitive)
- Education/Career: $2-$8 (medium-high)
- General/Lifestyle: $0.30-$2 (lower intent)
- Local Services: $1-$8 (geographic competition)

**Keyword Difficulty Scale (0-100):**
- 0-30: Easy (new sites can rank in 3-6 months)
- 31-50: Medium (requires domain authority + content investment)
- 51-70: Hard (needs strong backlink profile + 6+ months)
- 71-100: Very Hard (competes with Wikipedia, Forbes, major brands)

**Search Intent Classification:**
- Informational: "how to", "what is", "guide", "tutorial", "vs" → Low CPC, high volume, educational content wins
- Commercial Investigation: "best", "top", "review", "comparison" → Medium-high CPC, medium volume, product roundup content
- Transactional: "buy", "discount", "free shipping", "deal" → High CPC, lower volume, product pages win
- Navigational: Brand names, "login", "official" → Low CPC, varies volume, brand protection critical

## ANALYSIS TASK

Analyze this keyword: "{keyword}"
{topic_context}
{region_context}

**Step 1: Intent Classification**
- Identify the primary search intent (informational/commercial/transactional/navigational)
- Look for intent modifiers ("best", "how to", "buy", "vs", etc.)

**Step 2: Volume Estimation**
- Consider keyword length and specificity
- Factor in question vs statement format
- Account for commercial intent volume multipliers
- Use benchmark ranges above as starting point

**Step 3: CPC Estimation**
- Identify the industry/niche from keyword semantics
- Apply appropriate industry CPC range
- Adjust for commercial vs informational intent
- Factor in geographic market (US/UK/AU higher than global average)

**Step 4: Difficulty Assessment**
- Estimate based on competitor landscape (brands vs blogs vs aggregators)
- Consider content type required to rank
- Factor in SERP features (shopping ads, local pack, featured snippets)

## RESPONSE FORMAT

Respond with ONLY this JSON (no markdown, no explanation outside JSON):

{{
  "monthly_volume": 2500,
  "volume_confidence": "medium",
  "cpc_usd": 2.50,
  "keyword_difficulty": 45,
  "competition_level": "Medium",
  "search_intent": "commercial",
  "reasoning": "3-4 word commercial investigation keyword. Based on benchmarks: commercial keywords in this niche average 2K-5K volume with $2-4 CPC. Moderate difficulty due to affiliate sites competing but not major brands dominating."
}}

**Field Guidelines:**
- monthly_volume: Integer between 100 and 500,000. Be realistic - most keywords are under 10K.
- volume_confidence: "high" (well-known term), "medium" (educated guess), "low" (rare/obscure term)
- cpc_usd: Use industry benchmarks. Finance = $10+, SaaS = $5+, E-commerce = $1-3, General = $0.50-2
- keyword_difficulty: 0-100 scale. Most keywords 30-70. New sites avoid >60.
- competition_level: Low (<30 difficulty), Medium (30-60), High (>60)
- search_intent: informational | commercial | transactional | navigational
- reasoning: 1-2 sentences explaining your logic using the benchmarks above"""

    try:
        response = groq_circuit_breaker.call(
            client.chat.completions.create,
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        raw_text = response.choices[0].message.content.strip()
        estimate = _parse_llm_response(raw_text, keyword)
        logger.info(f"[LLM-ESTIMATE] '{keyword}': vol={estimate.monthly_volume}, cpc=${estimate.cpc_usd}, diff={estimate.keyword_difficulty}, intent={estimate.search_intent}, conf={estimate.volume_confidence}")
        return estimate
        
    except CircuitBreakerOpen:
        logger.warning("[LLM-ESTIMATE] Circuit breaker open - using fallback traffic estimate")
        return _fallback_estimate(keyword)
    except Exception as e:
        logger.warning(f"[LLM-ESTIMATE] Failed for '{keyword}': {e}")
        return _fallback_estimate(keyword)


def estimate_keywords_batch_llm(
    keywords: List[str],
    page_topic: str = "",
    target_region: str = "GLOBAL",
) -> Dict[str, LLMTrafficEstimate]:
    """
    Estimate traffic for multiple keywords in a single LLM call (cheaper/faster).
    
    Args:
        keywords: List of keywords to estimate (max 10 for best results)
        page_topic: Context about the page
        target_region: Target geographic region
    
    Returns:
        Dict mapping keyword to LLMTrafficEstimate
    """
    if not keywords:
        return {}
    
    # Limit batch size for quality
    keywords = keywords[:10]
    
    client = get_client()
    if client is None:
        return {kw: _fallback_estimate(kw) for kw in keywords}
    
    topic_context = f"The page is about: {page_topic}." if page_topic else ""
    region_context = f"Target region: {target_region}." if target_region != "GLOBAL" else ""
    keyword_list = "\n".join(f"{i+1}. {kw}" for i, kw in enumerate(keywords))
    
    prompt = f"""You are a senior SEO data analyst at a top-tier digital marketing agency. You specialize in search volume forecasting, CPC estimation, and keyword difficulty assessment. Your estimates are used for million-dollar budget allocations, so accuracy is critical.

## INDUSTRY BENCHMARK DATA (2024 Google Ads / Ahrefs / SEMrush averages)

**Search Volume Tiers:**
- Head terms (1-2 words): 10K-500K/month (highly competitive)
- Mid-tail (3-4 words): 1K-20K/month (moderate competition)
- Long-tail (5+ words): 100-2K/month (low competition, high conversion)
- Question keywords: 20% lower volume than equivalent statements
- "Best" + category: 3x volume of generic category terms
- "Near me" / location: 40% lower volume but 2x conversion intent

**CPC Benchmarks by Industry (USD):**
- Finance/Insurance/Legal: $5-$50 (extremely high value)
- Healthcare/Medical: $2-$15 (high trust barrier)
- SaaS/B2B Software: $3-$25 (high LTV)
- E-commerce/Retail: $0.50-$3 (competitive)
- Education/Career: $2-$8 (medium-high)
- General/Lifestyle: $0.30-$2 (lower intent)
- Local Services: $1-$8 (geographic competition)

**Keyword Difficulty Scale (0-100):**
- 0-30: Easy (new sites can rank in 3-6 months)
- 31-50: Medium (requires domain authority + content investment)
- 51-70: Hard (needs strong backlink profile + 6+ months)
- 71-100: Very Hard (competes with Wikipedia, Forbes, major brands)

**Search Intent Classification:**
- Informational: "how to", "what is", "guide", "tutorial", "vs" → Low CPC, high volume
- Commercial Investigation: "best", "top", "review", "comparison" → Medium-high CPC, medium volume
- Transactional: "buy", "discount", "deal" → High CPC, lower volume
- Navigational: Brand names, "login", "official" → Low CPC, varies volume

## ANALYSIS TASK

{topic_context}
{region_context}

Keywords to analyze:
{keyword_list}

For each keyword, analyze:
1. **Intent**: Identify informational/commercial/transactional/navigational intent
2. **Volume**: Use keyword length + intent + industry benchmarks
3. **CPC**: Identify industry from keyword semantics, apply benchmark range
4. **Difficulty**: Estimate competition (brands vs blogs vs aggregators)

## RESPONSE FORMAT

Respond with ONLY a JSON array where each element matches this format:
{{
  "keyword": "exact keyword text",
  "monthly_volume": 2500,
  "volume_confidence": "medium",
  "cpc_usd": 2.50,
  "keyword_difficulty": 45,
  "competition_level": "Medium",
  "search_intent": "commercial",
  "reasoning": "Based on benchmarks: commercial keywords average 2K-5K volume with $2-4 CPC. Moderate difficulty."
}}

**Field Guidelines:**
- monthly_volume: 100 to 500,000 (most keywords under 10K)
- volume_confidence: "high" (well-known), "medium" (educated guess), "low" (rare/obscure)
- cpc_usd: Finance = $10+, SaaS = $5+, E-commerce = $1-3, General = $0.50-2
- keyword_difficulty: 0-100 scale. Most keywords 30-70.
- competition_level: Low (<30), Medium (30-60), High (>60)
- search_intent: informational | commercial | transactional | navigational
- Provide estimates for ALL {len(keywords)} keywords in the list"""

    try:
        response = groq_circuit_breaker.call(
            client.chat.completions.create,
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1200,
        )
        raw_text = response.choices[0].message.content.strip()
        
        # Clean markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        data = json.loads(raw_text.strip())
        
        results = {}
        for item in data:
            kw = item.get("keyword", "")
            if kw:
                results[kw] = LLMTrafficEstimate(
                    keyword=kw,
                    monthly_volume=int(item.get("monthly_volume", 1000)),
                    volume_confidence=item.get("volume_confidence", "medium"),
                    cpc_usd=float(item.get("cpc_usd", 1.0)),
                    keyword_difficulty=int(item.get("keyword_difficulty", 50)),
                    competition_level=item.get("competition_level", "Medium"),
                    search_intent=item.get("search_intent", "informational"),
                    reasoning=item.get("reasoning", ""),
                )
        
        # Ensure all keywords have results
        for kw in keywords:
            if kw not in results:
                results[kw] = _fallback_estimate(kw)
        
        return results
        
    except Exception as e:
        logger.warning(f"Batch LLM traffic estimation failed: {e}")
        return {kw: _fallback_estimate(kw) for kw in keywords}


def _fallback_estimate(keyword: str) -> LLMTrafficEstimate:
    """Provide fallback estimate when LLM fails."""
    word_count = len(keyword.split())
    
    # Sensible defaults based on keyword length
    if word_count >= 5:
        volume = 500
        difficulty = 35
    elif word_count == 4:
        volume = 2000
        difficulty = 45
    elif word_count == 3:
        volume = 8000
        difficulty = 55
    else:
        volume = 25000
        difficulty = 70
    
    return LLMTrafficEstimate(
        keyword=keyword,
        monthly_volume=volume,
        volume_confidence="low",
        cpc_usd=1.50,
        keyword_difficulty=difficulty,
        competition_level="Medium",
        search_intent="informational",
        reasoning="Fallback estimate (LLM unavailable)",
    )
