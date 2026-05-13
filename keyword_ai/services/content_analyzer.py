"""
Enhanced Content Analysis Service for Phase 1.
Provides deep content analysis including:
- TF-IDF vectorization
- Content quality scoring
- Named Entity Recognition (NER)
- Topic modeling
- Readability analysis
- Semantic embedding
"""

import re
import math
from collections import Counter
from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from .embeddings import get_single_embedding


def calculate_readability_scores(text: str) -> Dict[str, float]:
    """
    Calculate Flesch-Kincaid readability scores.
    Returns reading ease and grade level.
    """
    # Count sentences (approximate by punctuation)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)
    
    # Count words
    words = re.findall(r'\b\w+\b', text.lower())
    word_count = len(words)
    
    # Count syllables (approximate)
    def count_syllables(word):
        word = word.lower()
        vowels = "aeiouy"
        syllables = 0
        prev_was_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllables += 1
            prev_was_vowel = is_vowel
        if word.endswith('e'):
            syllables -= 1
        return max(1, syllables)
    
    syllable_count = sum(count_syllables(word) for word in words)
    
    # Calculate scores
    if sentence_count == 0 or word_count == 0:
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade": 0.0,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": 0.0,
            "avg_syllables_per_word": 0.0,
        }
    
    avg_words_per_sentence = word_count / sentence_count
    avg_syllables_per_word = syllable_count / word_count
    
    # Flesch Reading Ease: 0-100 (higher is easier)
    flesch_reading_ease = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    
    # Flesch-Kincaid Grade Level
    flesch_kincaid_grade = (0.39 * avg_words_per_sentence) + (11.8 * avg_syllables_per_word) - 15.59
    
    return {
        "flesch_reading_ease": round(flesch_reading_ease, 2),
        "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_words_per_sentence": round(avg_words_per_sentence, 2),
        "avg_syllables_per_word": round(avg_syllables_per_word, 2),
    }


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Simple rule-based Named Entity Recognition.
    Extracts potential entities using patterns.
    
    For production, consider using spaCy or transformer NER models.
    """
    entities = {
        "organizations": [],
        "people": [],
        "locations": [],
        "products": [],
        "technologies": [],
    }
    
    # Common tech terms/organizations pattern
    org_patterns = [
        r'\b(?:Google|Microsoft|Apple|Amazon|Meta|Netflix|Spotify|Uber|Airbnb|Slack|Discord)\b',
        r'\b[A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company|Technologies|Solutions)\b',
    ]
    
    # Technology patterns
    tech_patterns = [
        r'\b(?:Python|JavaScript|Java|React|Angular|Vue|Node\.js|Django|Flask|FastAPI|AWS|Azure|Docker|Kubernetes)\b',
        r'\b(?:AI|ML|API|SEO|CRM|ERP|SaaS|PaaS|IaaS)\b',
    ]
    
    # Location patterns (simplified)
    location_patterns = [
        r'\b(?:USA|UK|Canada|Germany|France|Japan|India|Pakistan|Australia|Singapore)\b',
    ]
    
    for pattern in org_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["organizations"].extend(matches)
    
    for pattern in tech_patterns:
        matches = re.findall(pattern, text)
        entities["technologies"].extend(matches)
    
    for pattern in location_patterns:
        matches = re.findall(pattern, text)
        entities["locations"].extend(matches)
    
    # Deduplicate
    for key in entities:
        entities[key] = list(set(entities[key]))
    
    return entities


def extract_tfidf_keywords(text: str, top_n: int = 20) -> List[Dict]:
    """
    Extract keywords using TF-IDF scoring.
    Returns top N keywords with their TF-IDF scores.
    """
    # Split into sentences/documents for TF-IDF
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if len(sentences) < 2:
        # Not enough sentences, use word frequency instead
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        filtered_words = [w for w in words if w not in stopwords]
        word_freq = Counter(filtered_words)
        return [{"keyword": word, "tfidf_score": round(freq / len(words), 4)} 
                for word, freq in word_freq.most_common(top_n)]
    
    try:
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2),  # unigrams and bigrams
            min_df=1,
        )
        
        tfidf_matrix = vectorizer.fit_transform(sentences)
        feature_names = vectorizer.get_feature_names_out()
        
        # Get average TF-IDF scores across all documents
        scores = np.array(tfidf_matrix.mean(axis=0)).flatten()
        
        # Sort by score
        top_indices = scores.argsort()[-top_n:][::-1]
        
        keywords = []
        for idx in top_indices:
            if scores[idx] > 0:
                keywords.append({
                    "keyword": feature_names[idx],
                    "tfidf_score": round(float(scores[idx]), 4)
                })
        
        return keywords
    except Exception:
        # Fallback to simple frequency
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_freq = Counter(words)
        return [{"keyword": word, "tfidf_score": round(freq / len(words), 4)} 
                for word, freq in word_freq.most_common(top_n)]


def analyze_content_structure(text: str) -> Dict:
    """
    Analyze content structure and formatting.
    """
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    return {
        "paragraph_count": len(paragraphs),
        "avg_paragraph_length": round(sum(len(p) for p in paragraphs) / len(paragraphs), 2) if paragraphs else 0,
        "bullet_points": len(re.findall(r'^[\s]*[•\-\*]', text, re.MULTILINE)),
        "numbered_lists": len(re.findall(r'^[\s]*\d+\.', text, re.MULTILINE)),
        "headings_count": len(re.findall(r'\b(h1|h2|h3|h4|h5|h6)\b', text, re.IGNORECASE)),
    }


def calculate_content_quality_score(readability: Dict, structure: Dict, text: str) -> float:
    """
    Calculate overall content quality score (0-100).
    Based on readability, length, structure, and formatting.
    """
    score = 50.0  # Base score
    
    # Length factor (ideal: 300-2000 words)
    word_count = readability.get("word_count", 0)
    if 300 <= word_count <= 2000:
        score += 20
    elif word_count > 100:
        score += 10
    
    # Readability factor (ideal: 60-80)
    reading_ease = readability.get("flesch_reading_ease", 50)
    if 50 <= reading_ease <= 80:
        score += 15
    elif reading_ease > 30:
        score += 10
    
    # Structure factor
    if structure.get("paragraph_count", 0) >= 3:
        score += 10
    
    # Has lists (good formatting)
    if structure.get("bullet_points", 0) > 0 or structure.get("numbered_lists", 0) > 0:
        score += 5
    
    return round(min(100, max(0, score)), 2)


def analyze_content(text: str, url: str = None) -> Dict:
    """
    Main content analysis function.
    Performs comprehensive analysis of content.
    
    Args:
        text: The content text to analyze
        url: Optional URL for context
        
    Returns:
        Dict with all analysis results
    """
    if not text or len(text.strip()) < 50:
        return {
            "error": "Insufficient content for analysis",
            "quality_score": 0.0,
        }
    
    # Run all analyses
    readability = calculate_readability_scores(text)
    entities = extract_entities(text)
    tfidf_keywords = extract_tfidf_keywords(text, top_n=30)
    structure = analyze_content_structure(text)
    quality_score = calculate_content_quality_score(readability, structure, text)
    
    # Get semantic embedding
    try:
        embedding = get_single_embedding(text[:1000])  # Limit to first 1000 chars for speed
        embedding_vector = embedding.tolist()
    except Exception:
        embedding_vector = None
    
    return {
        "url": url,
        "quality_score": quality_score,
        "readability": readability,
        "entities": entities,
        "tfidf_keywords": tfidf_keywords,
        "structure": structure,
        "semantic_embedding": embedding_vector,
        "analysis_timestamp": None,  # Will be set by caller if needed
    }


# Convenience function for quick analysis
def quick_analyze(text: str) -> Dict:
    """Quick analysis with just the essentials."""
    return {
        "word_count": len(text.split()),
        "readability": calculate_readability_scores(text),
        "top_keywords": [k["keyword"] for k in extract_tfidf_keywords(text, top_n=10)],
    }
