"""
E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) Analyzer Service.
Provides AI-powered and fallback analysis for SEO content optimization.
"""
import os
import re
import json
import time
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
import openai  # OpenAI-compatible SDK used for Groq/OpenRouter exceptions
from django.conf import settings

logger = logging.getLogger(__name__)


class EEATAnalyzer:
    """
    Analyzes content for Google's E-E-A-T signals.
    Supports both AI-powered (Groq/OpenRouter) and fallback rule-based analysis.
    """
    
    # 2026 E-E-A-T signal constants
    AUTHOR_SIGNALS = ['by ', 'written by', 'author:', 'dr.', 'md,', 'phd,', 'reviewed by']
    EXPERTISE_WORDS = ['expert', 'guide', 'professional', 'certified', 'proven', 'research-based']
    CLICKBAIT_WORDS = ['shocking', 'secret', 'unbelievable', 'you won\'t believe', 'mind-blowing']
    GENERIC_PHRASES = ['in this article', 'in conclusion', 'in today\'s digital age', 'it\'s important to note']
    CTA_WORDS = ['learn', 'discover', 'find', 'get', 'explore']
    
    def __init__(self, use_groq: Optional[bool] = None, api_key: Optional[str] = None):
        """
        Initialize the E-E-A-T analyzer.
        
        Args:
            use_groq: Whether to use Groq API (default: from settings)
            api_key: Optional API key override
        """
        self.use_groq = use_groq if use_groq is not None else getattr(settings, 'USE_GROQ', True)
        self.api_key = api_key
        self._client = None
        self._model = None
    
    def _get_client(self) -> Optional[OpenAI]:
        """Get or create AI client (Groq preferred, OpenRouter fallback)."""
        if self._client is not None:
            return self._client
            
        if self.use_groq:
            api_key = self.api_key or getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
            if not api_key:
                logger.warning("No GROQ_API_KEY found. Using fallback E-E-A-T analysis.")
                return None
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=45.0,
                max_retries=3
            )
            self._model = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
            logger.info("EEATAnalyzer using Groq API with model %s", self._model)
        else:
            api_key = self.api_key or os.getenv('OPENROUTER_API_KEY') or getattr(settings, 'OPENROUTER_API_KEY', '')
            if not api_key:
                logger.warning("No API key found. Using fallback E-E-A-T analysis.")
                return None
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=45.0,
                max_retries=3
            )
            self._model = getattr(settings, 'OPENAI_MODEL', 'openai/gpt-4o-mini')
            logger.info("EEATAnalyzer using OpenRouter API with model %s", self._model)

        return self._client
    
    def analyze(self, content_type: str, content: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze content for E-E-A-T signals.
        
        Args:
            content_type: 'title', 'description', or 'heading'
            content: The actual text to analyze
            context: Additional context (e.g., full page title for description)
            
        Returns:
            Dict with eeat_score, signals, issues, recommendations, and details
        """
        if not content or len(content.strip()) < 3:
            return {
                'eeat_score': 0,
                'signals': [],
                'issues': ['Content too short for meaningful analysis'],
                'recommendations': ['Add substantive content (minimum 20 characters)'],
                'details': {}
            }
        
        client = self._get_client()
        if client is None:
            return self._fallback_analysis(content_type, content)
        
        return self._analyze_with_ai(client, content_type, content, context)
    
    def _fallback_analysis(self, content_type: str, content: str) -> Dict[str, Any]:
        """
        Enhanced fallback E-E-A-T analysis with 2026 signals.
        Used when AI is unavailable.
        """
        content_lower = content.lower()
        signals = []
        issues = []
        score = 50
        
        # Author/Brand Signals (Crucial for YMYL)
        if any(signal in content_lower for signal in self.AUTHOR_SIGNALS):
            signals.append("✓ Author attribution detected")
            score += 15
        
        # Expertise indicators
        if any(word in content_lower for word in self.EXPERTISE_WORDS):
            signals.append("✓ Expertise markers found")
            score += 12
        
        # Freshness signals (critical for 2026)
        current_year = 2026
        if str(current_year) in content or str(current_year - 1) in content:
            signals.append(f"✓ Current year ({current_year}) mentioned")
            score += 15
        elif re.search(r'\b202[3-5]\b', content):
            signals.append("✓ Recent date found")
            score += 8
        
        # Data/Stat signals (builds authority)
        if re.search(r'\d+%|\d+\s*(percent|users|people)', content_lower):
            signals.append("✓ Data points/statistics included")
            score += 8
        
        # Red flags for thin/AI content
        if any(word in content_lower for word in self.CLICKBAIT_WORDS):
            issues.append("⚠ Clickbait language detected")
            score -= 25
        
        # Generic AI content patterns
        if sum(1 for phrase in self.GENERIC_PHRASES if phrase in content_lower) >= 2:
            issues.append("⚠ Generic phrasing detected (may signal AI/thin content)")
            score -= 15
        
        # Missing key elements
        if content_type == 'description' and len(content) > 50:
            if not any(word in content_lower for word in self.CTA_WORDS):
                issues.append("⚠ No clear call-to-action")
                score -= 10
        
        return {
            'eeat_score': max(0, min(100, score)),
            'signals': signals,
            'issues': issues,
            'recommendations': ['Enable AI analysis for comprehensive insights'],
            'details': {
                'content_type': content_type,
                'analysis_method': 'fallback'
            }
        }
    
    def _get_analysis_prompt(self, content_type: str, content: str, context: Optional[str] = None) -> str:
        """Generate the appropriate analysis prompt based on content type."""
        
        if content_type == 'title':
            return f"""Analyze this page TITLE for Google's 2026 ranking factors (E-E-A-T, Helpful Content, Mobile SERP):

TITLE: "{content}"

Evaluate against 2026 SEO priorities:
1. **Experience**: First-hand language ("I tested", "our guide", specific examples vs generic claims)
2. **Expertise**: Credentials, year/date (2025-2026), numbers/data, "guide"/"complete"
3. **Authority**: Brand name, clear topic focus, no keyword stuffing
4. **Trust**: No clickbait, clear value, mobile-friendly length (50-60 chars optimal)
5. **Helpful Content**: Specific promise, not generic ("how to X" vs "the ultimate guide to everything")

CRITICAL 2026 PENALTIES:
- AI-generated generic titles ("comprehensive guide", "everything you need to know")
- Clickbait ("shocking", "you won't believe")
- Missing freshness (no year for time-sensitive topics)
- Keyword stuffing or duplicate words

Return ONLY valid JSON (no markdown):
{{
    "eeat_score": 0-100,
    "signals_found": ["specific signal 1", "specific signal 2"],
    "issues": ["specific issue 1"],
    "recommendations": ["actionable rec 1", "actionable rec 2"],
    "has_year": true/false,
    "has_brand": true/false,
    "has_expertise_marker": true/false,
    "has_clickbait": true/false,
    "has_specific_value": true/false,
    "mobile_serp_quality": "excellent/good/poor",
    "trust_level": "high/medium/low"
}}"""

        elif content_type == 'description':
            ctx = f'PAGE TITLE: "{context}"' if context else ''
            return f"""Analyze this META DESCRIPTION for Google's 2026 Mobile-First SERP standards:

DESCRIPTION: "{content}"
{ctx}

Evaluate for 2026 Mobile SERP (Google prioritizes descriptions that enhance user choice):
1. **Experience**: Author name ("by Jane Doe"), personal insights, tested claims
2. **Expertise**: Credentials (MD, CPA, "expert"), data/stats, "research-backed"
3. **Authority**: Dates (updated 2026), original source mentions, specific outcomes
4. **Trust**: Clear CTA, complements title (not duplicate), mobile-optimized (150-160 chars)
5. **Helpful Content**: Specific benefits, NOT generic ("learn everything", "comprehensive info")

MOBILE SERP OPTIMIZATION:
- First 120 chars most critical (mobile cutoff)
- Action verbs ("discover", "get", "learn how")
- Unique from title (duplicates are ignored by Google)

CRITICAL PENALTIES:
- Duplicates title text (Google shows "..." or rewrites)
- Generic AI patterns ("in this article, we'll explore")
- No clear benefit stated
- Missing freshness for time-sensitive content

Return ONLY valid JSON (no markdown):
{{
    "eeat_score": 0-100,
    "signals_found": ["signal 1", "signal 2"],
    "issues": ["issue 1"],
    "recommendations": ["rec 1", "rec 2"],
    "has_author_attribution": true/false,
    "has_date": true/false,
    "has_specific_benefit": true/false,
    "has_cta": true/false,
    "duplicates_title": true/false,
    "first_120_chars_quality": "strong/weak",
    "mobile_serp_quality": "excellent/good/poor",
    "trust_level": "high/medium/low"
}}"""

        else:  # heading (H1)
            ctx = f'PAGE TITLE: "{context}"' if context else ''
            return f"""Analyze this H1 HEADING for Google's 2026 Helpful Content & Accessibility standards:

H1: "{content}"
{ctx}

Evaluate for 2026 standards (H1 is critical for topic clarity & accessibility):
1. **Experience**: Specific, actionable ("7 tested strategies" vs "best strategies")
2. **Expertise**: Year for freshness, how-to format, demonstrates depth
3. **Authority**: Clear topic (not vague), aligned with search intent, supports title
4. **Trust**: No clickbait, accessible (screen readers), complements but differs from title
5. **Helpful Content**: User-focused ("how you can X" vs "guide to X"), specific outcome

H1 BEST PRACTICES 2026:
- Should be THE MOST important text on page (accessibility & SEO)
- 60-70 chars ideal (mobile H1 display)
- Must differ from title (shows depth)
- Question format OK if genuinely helpful ("How do I X?" for tutorials)

CRITICAL ISSUES:
- Duplicate of title (wasted opportunity)
- Multiple H1s (confuses topic modeling)
- Vague/generic ("Everything about X")
- Missing for time-sensitive content: year

Return ONLY valid JSON (no markdown):
{{
    "eeat_score": 0-100,
    "signals_found": ["signal 1", "signal 2"],
    "issues": ["issue 1"],
    "recommendations": ["rec 1", "rec 2"],
    "has_year": true/false,
    "is_question_format": true/false,
    "has_specific_outcome": true/false,
    "title_alignment": "complementary/duplicate/conflicting",
    "accessibility_score": "excellent/good/poor",
    "trust_level": "high/medium/low"
}}"""

    def _analyze_with_ai(self, client: OpenAI, content_type: str, content: str, 
                         context: Optional[str] = None) -> Dict[str, Any]:
        """Perform AI-powered E-E-A-T analysis with retry logic."""
        
        analysis_prompt = self._get_analysis_prompt(content_type, content, context)
        
        # Retry on RateLimitError with exponential backoff
        _MAX_RATE_RETRIES = 3
        completion = None
        
        for attempt in range(_MAX_RATE_RETRIES):
            try:
                completion = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert SEO analyst specializing in Google's 2026 ranking systems: 
- E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)
- Helpful Content System (rewards genuine human expertise)
- Mobile-First Indexing (mobile SERP optimization)

Focus on detecting: AI-generated content patterns, thin content, clickbait, missing expertise signals.
Return ONLY valid JSON, no markdown, no preamble."""
                        },
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ],
                    temperature=0.2,
                    max_tokens=700
                )
                break  # success
                
            except openai.RateLimitError:
                if attempt < _MAX_RATE_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        f"RateLimitError — retrying in {wait}s "
                        f"(attempt {attempt + 1}/{_MAX_RATE_RETRIES})"
                    )
                    time.sleep(wait)
                else:
                    logger.error("RateLimitError — all retries exhausted, falling back")
                    return self._fallback_analysis(content_type, content)
        
        if completion is None:
            return self._fallback_analysis(content_type, content)
        
        try:
            response_text = completion.choices[0].message.content.strip()
            
            # Robust JSON extraction
            if '```' in response_text:
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
            
            result = json.loads(response_text)
            
            # Ensure all required fields exist with defaults
            result.setdefault('eeat_score', 50)
            result.setdefault('signals_found', [])
            result.setdefault('issues', [])
            result.setdefault('recommendations', [])
            
            return {
                'eeat_score': result['eeat_score'],
                'signals': result['signals_found'],
                'issues': result['issues'],
                'recommendations': result['recommendations'],
                'details': result
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for {content_type}: {e}")
            return self._fallback_analysis(content_type, content)
        except Exception as e:
            logger.error(f"AI E-E-A-T analysis failed for {content_type}: {e}")
            return self._fallback_analysis(content_type, content)
