"""
Keyword Suggestion Generator (Phase 2)
Generates new keyword suggestions based on content analysis.
Uses semantic similarity and generative patterns.
"""

import os
import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import re
from collections import Counter

# Model paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

# Lazy-loaded model
_embedding_model = None


def get_embedding_model():
    """Lazy load sentence transformer model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


class KeywordSuggestionGenerator:
    """
    Generates keyword suggestions based on content analysis.
    
    Strategies:
    1. Long-tail variations of seed keywords
    2. Question-based keyword generation
    3. LSI (Latent Semantic Indexing) keyword discovery
    4. Competitor gap keyword expansion
    5. Trending modifier combinations
    """
    
    def __init__(self, content_text: str = "", existing_keywords: List[str] = None):
        self.content_text = content_text.lower()
        self.existing_keywords = set(kw.lower() for kw in (existing_keywords or []))
        self.embedding_model = get_embedding_model()
        
        # Common modifier templates for long-tail generation
        self.question_templates = [
            "what is {keyword}",
            "how to {keyword}",
            "why {keyword} matters",
            "when to use {keyword}",
            "where to find {keyword}",
            "who needs {keyword}",
            "which {keyword} is best",
            "can {keyword} help",
            "does {keyword} work",
            "is {keyword} worth it",
        ]
        
        self.commercial_templates = [
            "best {keyword}",
            "top {keyword}",
            "cheap {keyword}",
            "affordable {keyword}",
            "professional {keyword}",
            "{keyword} review",
            "{keyword} comparison",
            "{keyword} vs {keyword} alternative",
            "{keyword} guide",
            "{keyword} tutorial",
        ]
        
        self.informational_templates = [
            "{keyword} explained",
            "{keyword} meaning",
            "{keyword} definition",
            "understanding {keyword}",
            "{keyword} for beginners",
            "{keyword} for dummies",
            "{keyword} examples",
            "{keyword} case study",
            "{keyword} tips",
            "{keyword} tricks",
        ]
    
    def generate_suggestions(
        self, 
        seed_keywords: List[str], 
        num_suggestions: int = 30,
        content_embedding: np.ndarray = None
    ) -> List[Dict]:
        """
        Generate keyword suggestions based on seed keywords.
        
        Args:
            seed_keywords: Base keywords to expand
            num_suggestions: Number of suggestions to generate
            content_embedding: Semantic embedding of content
            
        Returns:
            List of suggestion dicts with scores
        """
        suggestions = []
        
        # Strategy 1: Long-tail variations
        long_tail = self._generate_long_tail(seed_keywords)
        suggestions.extend(long_tail)
        
        # Strategy 2: Question-based keywords
        questions = self._generate_questions(seed_keywords)
        suggestions.extend(questions)
        
        # Strategy 3: LSI keywords from content
        lsi_keywords = self._extract_lsi_keywords(content_embedding)
        suggestions.extend([{"keyword": kw, "type": "lsi", "confidence": 0.7} for kw in lsi_keywords])
        
        # Strategy 4: Modifier combinations
        modifiers = self._generate_modifiers(seed_keywords)
        suggestions.extend(modifiers)
        
        # Deduplicate
        seen = set()
        unique_suggestions = []
        for sug in suggestions:
            kw_lower = sug["keyword"].lower()
            if kw_lower not in seen and kw_lower not in self.existing_keywords:
                seen.add(kw_lower)
                unique_suggestions.append(sug)
        
        # Score and rank suggestions
        scored_suggestions = self._score_suggestions(unique_suggestions, content_embedding)
        
        # Sort by score and return top N
        scored_suggestions.sort(key=lambda x: x["suggestion_score"], reverse=True)
        return scored_suggestions[:num_suggestions]
    
    def _generate_long_tail(self, seed_keywords: List[str]) -> List[Dict]:
        """Generate long-tail keyword variations."""
        suggestions = []
        
        for seed in seed_keywords:
            seed_lower = seed.lower()
            
            # Question templates
            for template in self.question_templates[:5]:  # Limit to top 5
                keyword = template.format(keyword=seed_lower)
                if len(keyword.split()) >= 3:  # At least 3 words for long-tail
                    suggestions.append({
                        "keyword": keyword,
                        "type": "long_tail_question",
                        "parent_keyword": seed,
                        "confidence": 0.75,
                    })
            
            # Commercial templates
            for template in self.commercial_templates[:5]:
                keyword = template.format(keyword=seed_lower)
                suggestions.append({
                    "keyword": keyword,
                    "type": "long_tail_commercial",
                    "parent_keyword": seed,
                    "confidence": 0.7,
                })
            
            # Informational templates
            for template in self.informational_templates[:5]:
                keyword = template.format(keyword=seed_lower)
                suggestions.append({
                    "keyword": keyword,
                    "type": "long_tail_informational",
                    "parent_keyword": seed,
                    "confidence": 0.72,
                })
        
        return suggestions
    
    def _generate_questions(self, seed_keywords: List[str]) -> List[Dict]:
        """Generate question-based keywords from content."""
        suggestions = []
        
        # Extract potential questions from content
        if self.content_text:
            sentences = re.split(r'[.!?]+', self.content_text)
            for sent in sentences:
                sent = sent.strip()
                if sent.startswith(('what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'does', 'is')):
                    # Clean and shorten
                    cleaned = re.sub(r'\s+', ' ', sent)[:60]
                    if len(cleaned) > 15 and cleaned not in self.existing_keywords:
                        suggestions.append({
                            "keyword": cleaned,
                            "type": "question_extracted",
                            "confidence": 0.65,
                        })
        
        # Generate synthetic questions from seeds
        for seed in seed_keywords[:5]:
            questions = [
                f"what is {seed}",
                f"how does {seed} work",
                f"why use {seed}",
                f"when should you use {seed}",
                f"where to learn {seed}",
                f"who uses {seed}",
            ]
            for q in questions:
                suggestions.append({
                    "keyword": q,
                    "type": "question_synthetic",
                    "parent_keyword": seed,
                    "confidence": 0.6,
                })
        
        return suggestions
    
    def _extract_lsi_keywords(self, content_embedding: np.ndarray = None) -> List[str]:
        """
        Extract Latent Semantic Indexing (LSI) keywords.
        These are semantically related but not exact match keywords.
        """
        if not self.content_text or content_embedding is None:
            return []
        
        # Get content embedding
        if content_embedding is None:
            content_embedding = self.embedding_model.encode(self.content_text, convert_to_numpy=True)
        
        # Extract bigrams and trigrams
        words = re.findall(r'\b[a-z]{4,}\b', self.content_text)
        
        # Generate candidate phrases
        candidates = []
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if len(bigram) > 10:
                candidates.append(bigram)
        
        # Score by semantic similarity to content
        if candidates:
            candidate_embeddings = self.embedding_model.encode(candidates, convert_to_numpy=True, show_progress_bar=False)
            
            similarities = np.dot(candidate_embeddings, content_embedding) / (
                np.linalg.norm(candidate_embeddings, axis=1) * np.linalg.norm(content_embedding)
            )
            
            # Return top candidates by similarity
            top_indices = np.argsort(similarities)[-20:][::-1]
            return [candidates[i] for i in top_indices if similarities[i] > 0.3]
        
        return []
    
    def _generate_modifiers(self, seed_keywords: List[str]) -> List[Dict]:
        """Generate keyword variations with location/audience modifiers."""
        suggestions = []
        
        # Geographic modifiers (examples - can be expanded)
        geo_modifiers = ["in pakistan", "in karachi", "in lahore", "near me", "online"]
        
        # Audience modifiers
        audience_modifiers = ["for beginners", "for experts", "for small business", "for startups"]
        
        # Time modifiers
        time_modifiers = ["2024", "2025", "latest", "updated", "new"]
        
        for seed in seed_keywords[:8]:
            # Geographic
            for mod in geo_modifiers[:3]:
                suggestions.append({
                    "keyword": f"{seed} {mod}",
                    "type": "geo_modified",
                    "parent_keyword": seed,
                    "confidence": 0.55,
                })
            
            # Audience
            for mod in audience_modifiers[:2]:
                suggestions.append({
                    "keyword": f"{seed} {mod}",
                    "type": "audience_modified",
                    "parent_keyword": seed,
                    "confidence": 0.6,
                })
            
            # Time
            for mod in time_modifiers[:2]:
                suggestions.append({
                    "keyword": f"{mod} {seed}",
                    "type": "time_modified",
                    "parent_keyword": seed,
                    "confidence": 0.65,
                })
        
        return suggestions
    
    def _score_suggestions(
        self, 
        suggestions: List[Dict], 
        content_embedding: np.ndarray = None
    ) -> List[Dict]:
        """
        Score generated suggestions for quality.
        
        Scoring factors:
        - Semantic relevance to content
        - Length (long-tail preference)
        - Uniqueness
        - Search intent clarity
        """
        if content_embedding is None and self.content_text:
            content_embedding = self.embedding_model.encode(self.content_text, convert_to_numpy=True)
        
        keywords = [s["keyword"] for s in suggestions]
        
        # Get embeddings for all suggestions
        if keywords:
            keyword_embeddings = self.embedding_model.encode(
                keywords, 
                convert_to_numpy=True, 
                show_progress_bar=False
            )
        else:
            keyword_embeddings = np.array([])
        
        scored = []
        for i, sug in enumerate(suggestions):
            score = sug.get("confidence", 0.5) * 50  # Base score from confidence
            
            # Semantic relevance (if we have embeddings)
            if content_embedding is not None and len(keyword_embeddings) > i:
                similarity = float(
                    np.dot(keyword_embeddings[i], content_embedding) / 
                    (np.linalg.norm(keyword_embeddings[i]) * np.linalg.norm(content_embedding))
                )
                score += similarity * 30  # Up to 30 points for relevance
            
            # Length bonus (slight preference for 3-6 words)
            word_count = len(sug["keyword"].split())
            if 3 <= word_count <= 6:
                score += 10
            elif word_count > 6:
                score += 5
            
            # Intent clarity bonus
            if sug["type"].startswith("question"):
                score += 5  # Questions have clear intent
            
            # Cap at 100
            sug["suggestion_score"] = round(min(100, score), 2)
            
            # Add predicted search intent
            sug["predicted_intent"] = self._predict_intent(sug["keyword"])
            
            scored.append(sug)
        
        return scored
    
    def _predict_intent(self, keyword: str) -> str:
        """Predict search intent for a keyword."""
        keyword_lower = keyword.lower()
        
        # Informational patterns
        if any(w in keyword_lower for w in ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'guide', 'tutorial', 'explained', 'meaning', 'definition']):
            return "informational"
        
        # Transactional patterns
        if any(w in keyword_lower for w in ['buy', 'price', 'discount', 'deal', 'purchase', 'order', 'shop', 'cheap', 'affordable', 'review', 'compare']):
            return "transactional"
        
        # Navigational patterns
        if any(w in keyword_lower for w in ['login', 'signin', 'official', 'website', 'app', 'download']):
            return "navigational"
        
        return "informational"  # Default


def generate_keyword_suggestions(
    content_text: str,
    seed_keywords: List[str],
    num_suggestions: int = 30,
    content_embedding: np.ndarray = None
) -> List[Dict]:
    """
    Convenience function to generate keyword suggestions.
    
    Args:
        content_text: The page content
        seed_keywords: Base keywords to expand from
        num_suggestions: Number of suggestions to generate
        content_embedding: Pre-computed content embedding
        
    Returns:
        List of suggestion dicts
    """
    generator = KeywordSuggestionGenerator(content_text, seed_keywords)
    return generator.generate_suggestions(seed_keywords, num_suggestions, content_embedding)


# Training data generator for future model training
def generate_training_pairs(content_samples: List[str], keyword_samples: List[List[str]]) -> List[Tuple]:
    """
    Generate training pairs for supervised learning.
    
    Returns:
        List of (content_embedding, keyword, relevance_score) tuples
    """
    model = get_embedding_model()
    training_pairs = []
    
    for content, keywords in zip(content_samples, keyword_samples):
        content_emb = model.encode(content, convert_to_numpy=True)
        
        for kw in keywords:
            kw_emb = model.encode(kw, convert_to_numpy=True)
            
            # Calculate relevance as cosine similarity
            relevance = float(
                np.dot(content_emb, kw_emb) / 
                (np.linalg.norm(content_emb) * np.linalg.norm(kw_emb))
            )
            
            training_pairs.append((content_emb, kw, relevance))
    
    return training_pairs
