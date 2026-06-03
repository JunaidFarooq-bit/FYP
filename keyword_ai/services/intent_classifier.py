"""
Enhanced Search Intent Classification Service (Phase 3)
Provides detailed intent analysis with confidence scores.

Features:
- Multi-label intent classification
- Intent confidence scoring
- Content alignment checking
- Search result intent prediction
"""

import json
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter
from openai import OpenAI
from django.conf import settings
import numpy as np

from keyword_ai.utils.intent_detection import (
    INFORMATIONAL_INDICATORS,
    NAVIGATIONAL_INDICATORS,
    TRANSACTIONAL_INDICATORS,
    COMMERCIAL_INDICATORS,
    classify_keyword_intent,
)

logger = logging.getLogger(__name__)

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


def _get_active_model():
    """Return active model name based on provider."""
    if getattr(settings, "USE_GROQ", True):
        return getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    return getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")


class IntentClassifier:
    """
    Advanced search intent classifier using hybrid approach:
    - Rule-based for common patterns
    - ML-based for complex cases
    - LLM-based for nuanced understanding
    """
    
    # Intent definitions using shared canonical indicator lists
    INTENTS = {
        "informational": {
            "indicators": INFORMATIONAL_INDICATORS,
            "weight": 1.0,
            "description": "Seeking information or answers"
        },
        "navigational": {
            "indicators": NAVIGATIONAL_INDICATORS,
            "weight": 1.0,
            "description": "Looking for a specific website or page"
        },
        "transactional": {
            "indicators": TRANSACTIONAL_INDICATORS,
            "weight": 1.0,
            "description": "Ready to make a purchase"
        },
        "commercial": {
            "indicators": COMMERCIAL_INDICATORS,
            "weight": 0.9,
            "description": "Researching before purchase"
        },
    }
    
    def classify(self, keyword: str, use_llm: bool = True) -> Dict:
        """
        Classify search intent for a keyword.
        
        Args:
            keyword: The keyword to classify
            use_llm: Whether to use LLM for enhanced classification
            
        Returns:
            Dict with intent classification and confidence
        """
        keyword_lower = keyword.lower()
        
        # Rule-based scoring
        scores = {}
        for intent_name, intent_data in self.INTENTS.items():
            score = 0
            for indicator in intent_data["indicators"]:
                if indicator in keyword_lower:
                    score += intent_data["weight"]
            scores[intent_name] = score
        
        # Normalize scores
        max_score = max(scores.values()) if scores else 0
        if max_score > 0:
            for intent in scores:
                scores[intent] = scores[intent] / max_score
        
        # Determine primary and secondary intents
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent = sorted_intents[0][0] if sorted_intents else "informational"
        primary_confidence = sorted_intents[0][1] if sorted_intents else 0.5
        
        # Check for mixed intent
        secondary_intents = [
            {"intent": name, "confidence": round(score, 2)}
            for name, score in sorted_intents[1:]
            if score > 0.3
        ]
        
        result = {
            "keyword": keyword,
            "primary_intent": primary_intent,
            "primary_confidence": round(primary_confidence, 2),
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
            "mixed_intent": len(secondary_intents) > 0,
            "secondary_intents": secondary_intents[:2],
            "classification_method": "rule_based"
        }
        
        # Enhance with LLM if available and confidence is low
        if use_llm and get_client() and primary_confidence < 0.7:
            llm_result = self._llm_classify(keyword)
            if llm_result:
                result = llm_result
                result["classification_method"] = "llm_enhanced"
        
        return result
    
    def _llm_classify(self, keyword: str) -> Optional[Dict]:
        """Use LLM for nuanced intent classification."""
        client = get_client()
        if client is None:
            return None
        
        prompt = f"""Analyze the search intent for this keyword: "{keyword}"

Provide detailed analysis:
1. Primary intent (Informational/Navigational/Transactional/Commercial)
2. Confidence level (0-1)
3. Any secondary intents with weights
4. User journey stage (Awareness/Consideration/Decision/Retention)
5. Content format that would best satisfy this intent
6. Search result features likely to appear (featured snippet, shopping, local pack, etc.)

Respond ONLY with valid JSON:
{{
  "keyword": "{keyword}",
  "primary_intent": "informational",
  "primary_confidence": 0.85,
  "all_scores": {{
    "informational": 0.85,
    "navigational": 0.1,
    "transactional": 0.05,
    "commerc
  "mixed_intent": true,get_active_()
  "secondary_intents": [
    {{"intent": "commercial", "confidence": 0.20}}
  ],
  "user_journey_stage": "Consideration",
  "recommended_content_format": "Comprehensive guide",
  "serp_features": ["featured_snippet", "people_also_ask"]
}}"""
        
        try:
            _model = getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
            response = client.chat.completions.create(
                model=_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
            )
            
            raw_text = response.choices[0].message.content.strip()
            
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            
            return json.loads(raw_text)
            
        except Exception as e:
            logger.warning(f"LLM intent classification error: {e}")
            return None
    
    def classify_batch(self, keywords: List[str]) -> List[Dict]:
        """Classify multiple keywords."""
        return [self.classify(kw, use_llm=False) for kw in keywords]
    
    def analyze_content_intent_alignment(
        self,
        content_text: str,
        target_keywords: List[str]
    ) -> Dict:
        """
        Analyze if content aligns with search intent of target keywords.
        
        Args:
            content_text: Page content
            target_keywords: Keywords targeting
            
        Returns:
            Intent alignment analysis
        """
        # Classify all keywords
        keyword_intents = self.classify_batch(target_keywords)
        
        # Count intent distribution
        intent_counts = Counter([k["primary_intent"] for k in keyword_intents])
        total = len(keyword_intents)
        
        intent_distribution = {
            intent: {
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0.0
            }
            for intent, count in intent_counts.items()
        }
        
        # Detect dominant intent
        dominant_intent = intent_counts.most_common(1)[0][0] if intent_counts else "informational"
        
        # Check content alignment (simple heuristic)
        content_lower = content_text.lower()
        content_indicators = {
            "informational": ["guide", "how to", "what is", "learn", "understand"],
            "transactional": ["buy", "price", "order", "shop", "purchase"],
            "commercial": ["best", "top", "review", "compare"],
            "navigational": ["login", "sign in", "download", "app"]
        }
        
        content_scores = {}
        for intent, indicators in content_indicators.items():
            score = sum(1 for ind in indicators if ind in content_lower)
            content_scores[intent] = score
        
        # Calculate alignment
        dominant_content_intent = max(content_scores, key=content_scores.get)
        alignment_score = 0.7 if dominant_content_intent == dominant_intent else 0.4
        
        # Generate recommendations
        recommendations = []
        if dominant_content_intent != dominant_intent:
            recommendations.append(
                f"Content appears {dominant_content_intent} but keywords are {dominant_intent}. "
                f"Consider adjusting content to better match intent."
            )
        
        if intent_distribution.get("commercial", {}).get("percentage", 0) > 30:
            recommendations.append(
                "High commercial intent detected. Add comparison tables and product recommendations."
            )
        
        return {
            "intent_distribution": intent_distribution,
            "dominant_keyword_intent": dominant_intent,
            "dominant_content_intent": dominant_content_intent,
            "alignment_score": round(alignment_score, 2),
            "is_aligned": dominant_content_intent == dominant_intent,
            "keyword_intents": keyword_intents,
            "recommendations": recommendations,
        }
    
    def predict_serp_features(self, keyword: str) -> List[str]:
        """Predict which SERP features will appear for a keyword."""
        keyword_lower = keyword.lower()
        features = []
        
        # Featured snippet indicators
        if any(w in keyword_lower for w in ['what is', 'how to', 'why does', 'meaning']):
            features.append("featured_snippet")
        
        # People Also Ask indicators
        if any(w in keyword_lower for w in ['how', 'what', 'why', 'when', 'which']):
            features.append("people_also_ask")
        
        # Shopping results indicators
        if any(w in keyword_lower for w in ['buy', 'price', 'cheap', 'deal', 'best']):
            features.append("shopping_results")
        
        # Local pack indicators
        if any(w in keyword_lower for w in ['near me', 'in karachi', 'in lahore', 'in pakistan']):
            features.append("local_pack")
        
        # Video results indicators
        if any(w in keyword_lower for w in ['tutorial', 'how to', 'demo', 'review']):
            features.append("video_results")
        
        # Image results indicators
        if any(w in keyword_lower for w in ['ideas', 'design', 'pictures', 'images', 'photos']):
            features.append("image_results")
        
        # Knowledge panel indicators
        if any(w in keyword_lower for w in ['definition', 'meaning', 'what is']):
            features.append("knowledge_panel")
        
        return features


# Convenience functions
_classifier = None


def get_classifier():
    """Get or create intent classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(keyword: str) -> Dict:
    """Classify intent for a single keyword."""
    return get_classifier().classify(keyword)


def classify_batch(keywords: List[str]) -> List[Dict]:
    """Classify intents for multiple keywords."""
    return get_classifier().classify_batch(keywords)


def analyze_content_alignment(content_text: str, target_keywords: List[str]) -> Dict:
    """Analyze content alignment with keyword intents."""
    return get_classifier().analyze_content_intent_alignment(content_text, target_keywords)


def predict_serp_features(keyword: str) -> List[str]:
    """Predict SERP features for a keyword."""
    return get_classifier().predict_serp_features(keyword)
