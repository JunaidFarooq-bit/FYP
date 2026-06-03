"""
Multi-Factor Keyword Relevance Scorer v2 (Phase 2)
Advanced relevance scoring using multiple features:
- Content relevance (cosine similarity)
- Search intent match
- Keyword difficulty estimation
- Competition gap score
- Content structure alignment
"""

import logging
import os
import joblib
import numpy as np
from typing import List, Dict, Tuple
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import re

from keyword_ai.services.embeddings import get_model as get_shared_embedding_model
from keyword_ai.utils.intent_detection import get_intent_features

logger = logging.getLogger(__name__)

# Model paths — stored alongside this file inside keyword_ai/ml_models/
MODEL_DIR = os.path.dirname(__file__)
RELEVANCE_MODEL_PATH = os.path.join(MODEL_DIR, "relevance_scorer_v2.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "relevance_scaler_v2.pkl")

# Lazy-loaded models
_relevance_model = None
_scaler = None


def get_embedding_model():
    """Return the shared sentence transformer singleton."""
    return get_shared_embedding_model()


def get_relevance_model():
    """Lazy load relevance scoring model."""
    global _relevance_model
    if _relevance_model is None:
        if os.path.exists(RELEVANCE_MODEL_PATH):
            _relevance_model = joblib.load(RELEVANCE_MODEL_PATH)
        else:
            _relevance_model = None
    return _relevance_model


def get_scaler():
    """Lazy load feature scaler."""
    global _scaler
    if _scaler is None:
        if os.path.exists(SCALER_PATH):
            _scaler = joblib.load(SCALER_PATH)
        else:
            _scaler = StandardScaler()
    return _scaler


class KeywordFeatureExtractor:
    """
    Extracts multiple features from keywords for relevance scoring.
    """
    
    def __init__(self, content_embedding: np.ndarray = None, content_text: str = None):
        self.content_embedding = content_embedding
        self.content_text = content_text or ""
        self.embedding_model = get_embedding_model()
    
    def extract_features(self, keyword: str) -> np.ndarray:
        """
        Extract feature vector for a keyword.
        
        Features (11 total):
        1. Content cosine similarity
        2. Keyword length (normalized)
        3. Word count in keyword
        4. Has numbers (binary)
        5. Has special chars (binary)
        6. Is question format (binary)
        7. Contains power words (binary)
        8. Title case ratio
        9. Search intent: Informational (binary)
        10. Search intent: Transactional (binary)
        11. Search intent: Navigational (binary)
        """
        features = []
        
        # 1. Content cosine similarity
        if self.content_embedding is not None:
            keyword_embedding = self.embedding_model.encode(keyword, convert_to_numpy=True)
            similarity = self._cosine_similarity(keyword_embedding, self.content_embedding)
            features.append(similarity)
        else:
            features.append(0.5)  # Default neutral
        
        # 2. Keyword length (normalized to 0-1, assuming max 100 chars)
        features.append(min(len(keyword) / 100, 1.0))
        
        # 3. Word count
        word_count = len(keyword.split())
        features.append(min(word_count / 10, 1.0))  # Normalize, max 10 words
        
        # 4. Has numbers
        has_numbers = bool(re.search(r'\d', keyword))
        features.append(float(has_numbers))
        
        # 5. Has special chars (excluding spaces and hyphens)
        has_special = bool(re.search(r'[^\w\s\-]', keyword))
        features.append(float(has_special))
        
        # 6. Is question format
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'does', 'is', 'are']
        is_question = any(keyword.lower().startswith(qw) for qw in question_words) or keyword.endswith('?')
        features.append(float(is_question))
        
        # 7. Contains power words
        power_words = ['best', 'top', 'ultimate', 'complete', 'guide', 'tutorial', 'review', 'free', 'pro', 'expert']
        has_power_word = any(pw in keyword.lower() for pw in power_words)
        features.append(float(has_power_word))
        
        # 8. Title case ratio (count of capitalized words / total words)
        words = keyword.split()
        if words:
            title_case_count = sum(1 for w in words if w and w[0].isupper())
            features.append(title_case_count / len(words))
        else:
            features.append(0.0)
        
        # 9-11. Search intent classification
        intent_features = self._classify_intent(keyword)
        features.extend(intent_features)
        
        return np.array(features)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def _classify_intent(self, keyword: str) -> List[float]:
        """
        Classify search intent: Informational, Transactional/Commercial, Navigational.
        Returns 3 binary features via the shared intent detection utility.
        """
        return get_intent_features(keyword)
    
    def extract_batch(self, keywords: List[str]) -> np.ndarray:
        """Extract features for multiple keywords using batched encoding."""
        if not keywords:
            return np.array([])

        # Batch-encode all keywords in one forward pass (instead of per-keyword)
        keyword_embeddings = self.embedding_model.encode(
            keywords, convert_to_numpy=True, show_progress_bar=False
        )

        features_list = []
        for i, keyword in enumerate(keywords):
            features = []

            # 1. Content cosine similarity
            if self.content_embedding is not None:
                features.append(self._cosine_similarity(
                    keyword_embeddings[i], self.content_embedding
                ))
            else:
                features.append(0.5)

            # 2-8: cheap textual features
            features.append(min(len(keyword) / 100, 1.0))
            word_count = len(keyword.split())
            features.append(min(word_count / 10, 1.0))
            features.append(float(bool(re.search(r'\d', keyword))))
            features.append(float(bool(re.search(r'[^\w\s\-]', keyword))))
            question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'does', 'is', 'are']
            features.append(float(any(keyword.lower().startswith(qw) for qw in question_words) or keyword.endswith('?')))
            power_words = ['best', 'top', 'ultimate', 'complete', 'guide', 'tutorial', 'review', 'free', 'pro', 'expert']
            features.append(float(any(pw in keyword.lower() for pw in power_words)))
            words = keyword.split()
            if words:
                features.append(sum(1 for w in words if w and w[0].isupper()) / len(words))
            else:
                features.append(0.0)

            # 9-11: intent
            features.extend(self._classify_intent(keyword))

            features_list.append(features)

        return np.array(features_list)


def estimate_keyword_difficulty(keyword: str) -> float:
    """
    Estimate SEO difficulty score (0-100) based on keyword characteristics.
    
    Factors:
    - Length (longer = generally easier)
    - Competition indicators (brand names, high-value terms)
    - Search volume proxy (generic vs. specific)
    """
    difficulty = 50.0  # Base difficulty
    
    # Length factor - longer keywords are usually less competitive
    length = len(keyword)
    if length > 30:
        difficulty -= 15
    elif length > 20:
        difficulty -= 10
    elif length < 10:
        difficulty += 10
    
    # Generic terms are harder
    generic_terms = ['seo', 'marketing', 'business', 'money', 'health', 'fitness', 'insurance', 'loans', 'credit']
    if any(term in keyword.lower() for term in generic_terms):
        difficulty += 20
    
    # Question keywords are usually easier
    if '?' in keyword or keyword.lower().startswith(('how', 'what', 'why')):
        difficulty -= 10
    
    # Long-tail indicators (easier)
    word_count = len(keyword.split())
    if word_count >= 4:
        difficulty -= 15
    elif word_count == 3:
        difficulty -= 5
    
    return max(0, min(100, difficulty))


def calculate_competition_gap_score(
    keyword: str, 
    gap_keywords: List[str], 
    high_priority_gaps: List[str]
) -> float:
    """
    Calculate how much of a gap opportunity this keyword represents.
    
    Returns score 0-100 where higher = better opportunity
    """
    if keyword in high_priority_gaps:
        return 90.0  # High priority gap
    elif keyword in gap_keywords:
        return 70.0  # Regular gap
    else:
        return 50.0  # Neutral score for non-gap keywords (don't penalize)


def _heuristic_score(features: np.ndarray) -> np.ndarray:
    """
    Heuristic scoring when ML model unavailable.
    
    Features (11 total):
    [0] Content cosine similarity (most important)
    [1] Keyword length (normalized)
    [2] Word count
    [3] Has numbers
    [4] Has special chars
    [5] Is question format
    [6] Has power words
    [7] Title case ratio
    [8] Is informational
    [9] Is transactional
    [10] Is navigational
    
    Returns scores in 0-100 range.
    """
    # Base score from cosine similarity (typically 0.2-0.7 for relevant content)
    # Scale: similarity * 120 gives 24-84 base score
    base_scores = features[:, 0] * 120  # Boosted similarity weight
    
    # Bonuses for keyword quality indicators
    # Multi-word keywords (long-tail) are more valuable
    word_count_bonus = features[:, 2] * 30  # 0-30 bonus based on word count
    
    # Question format adds value (good for SEO)
    question_bonus = features[:, 5] * 10
    
    # Power words add value
    power_bonus = features[:, 6] * 8
    
    # Intent signals add value
    intent_bonus = (features[:, 8] + features[:, 9] + features[:, 10]) * 5
    
    # Penalties
    # Special chars reduce quality
    special_penalty = features[:, 4] * -10
    
    # Combine all
    scores = base_scores + word_count_bonus + question_bonus + power_bonus + intent_bonus + special_penalty
    
    # Clip to 0-100
    return np.clip(scores, 0, 100)


def score_keywords_v2(
    keywords: List[str],
    content_embedding: np.ndarray = None,
    content_text: str = None,
    gap_keywords: List[str] = None,
    high_priority_gaps: List[str] = None,
    use_ml_model: bool = True
) -> List[Dict]:
    """
    Score keywords using multi-factor model.
    
    Args:
        keywords: List of keywords to score
        content_embedding: Semantic embedding of page content
        content_text: Raw page content text
        gap_keywords: List of gap keywords from competitor analysis
        high_priority_gaps: High-priority gap keywords
        use_ml_model: Whether to use trained ML model or heuristic scoring
        
    Returns:
        List of keyword dicts with scores
    """
    if not keywords:
        return []
    
    # Initialize feature extractor
    extractor = KeywordFeatureExtractor(content_embedding, content_text)
    
    # Extract features for all keywords
    features = extractor.extract_batch(keywords)
    
    # Get ML model score if available
    # Note: Only use ML model if it was properly trained (not the dummy model)
    model = get_relevance_model() if use_ml_model else None
    
    if model is not None and hasattr(model, 'n_estimators_'):
        scaler = get_scaler()
        try:
            features_scaled = scaler.transform(features)
            ml_scores = model.predict(features_scaled)
            # Ensure scores are in 0-100 range
            ml_scores = np.clip(ml_scores * 100 if ml_scores.max() <= 1 else ml_scores, 0, 100)
        except Exception as e:
            # Fall back to heuristic if model fails
            logger.warning(f"ML model scoring failed, falling back to heuristic: {e}")
            ml_scores = _heuristic_score(features)
    else:
        # Heuristic scoring with improved weights
        ml_scores = _heuristic_score(features)
    
    # Calculate additional scores
    results = []
    
    # Ensure ml_scores is iterable (handles scalar case when only 1 keyword)
    if np.isscalar(ml_scores):
        ml_scores = np.array([ml_scores])
    
    for i, keyword in enumerate(keywords):
        # ML-based relevance score (0-100)
        ml_score = float(ml_scores[i]) if i < len(ml_scores) else 50.0
        
        # Difficulty score (0-100, lower is easier)
        difficulty = estimate_keyword_difficulty(keyword)
        
        # Competition gap score (0-100)
        gap_score = calculate_competition_gap_score(
            keyword, 
            gap_keywords or [], 
            high_priority_gaps or []
        )
        
        # Composite score with weights
        # 50% relevance + 25% (100 - difficulty) + 25% gap score
        composite_score = (
            0.50 * ml_score +
            0.25 * (100 - difficulty) +  # Easier keywords get higher score
            0.25 * gap_score
        )
        
        # Determine if relevant (threshold: 35 - balanced for coverage)
        is_relevant = composite_score >= 35
        
        results.append({
            "keyword": keyword,
            "relevance_score": round(composite_score, 2),
            "ml_relevance_score": round(ml_score, 2),
            "difficulty_score": round(difficulty, 2),
            "competition_gap_score": round(gap_score, 2),
            "is_relevant": is_relevant,
            "search_intent": predict_search_intent(keyword),
        })
    
    # Sort by composite relevance score
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return results


def predict_search_intent(keyword: str) -> str:
    """Predict primary search intent for a keyword."""
    keyword_lower = keyword.lower()
    
    # Check for navigational
    nav_words = ['login', 'signin', 'signup', 'official', 'website', 'app', 'download']
    if any(w in keyword_lower for w in nav_words):
        return "navigational"
    
    # Check for transactional/commercial
    trans_words = ['buy', 'price', 'discount', 'deal', 'purchase', 'order', 'shop', 'cheap']
    commercial_words = ['best', 'top', 'compare', 'review', 'vs', 'alternative']
    
    if any(w in keyword_lower for w in trans_words):
        return "transactional"
    
    if any(w in keyword_lower for w in commercial_words):
        return "commercial"
    
    # Default to informational
    return "informational"


# Training function for model training pipeline
def train_relevance_model(training_data: List[Tuple[str, np.ndarray, float]]):
    """
    Train the relevance scoring model.
    
    Args:
        training_data: List of (keyword, feature_vector, relevance_score) tuples
    """
    # Extract features and labels
    X = np.array([item[1] for item in training_data])
    y = np.array([item[2] for item in training_data])
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train gradient boosting regressor
    model = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )
    model.fit(X_scaled, y)
    
    # Save model and scaler
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, RELEVANCE_MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    
    logger.info(f"Model saved to {RELEVANCE_MODEL_PATH}")
    logger.info(f"Scaler saved to {SCALER_PATH}")
    
    return model, scaler
