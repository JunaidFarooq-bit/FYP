"""
NLP and text analysis utilities
"""

import re
from collections import Counter
from textblob import TextBlob  # Install: pip install textblob --break-system-packages
import math


def extract_keywords(text, top_n=10):
    """Extract top keywords from text using TF-IDF approach"""
    
    if not text:
        return []
    
    # Tokenize and clean
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    
    # Remove common stop words
    stop_words = set([
        'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
        'in', 'with', 'to', 'for', 'of', 'as', 'by', 'that', 'this',
        'it', 'from', 'are', 'was', 'were', 'been', 'be', 'have', 'has',
        'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'can', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off',
        'over', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'both', 'each',
        'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'
    ])
    
    # Filter stop words
    filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
    
    # Count frequencies
    word_freq = Counter(filtered_words)
    
    # Get top N
    top_words = word_freq.most_common(top_n)
    
    return [{'keyword': word, 'frequency': freq} for word, freq in top_words]


def calculate_keyword_density(text, keyword):
    """Calculate keyword density percentage"""
    
    if not text or not keyword:
        return 0.0
    
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # Count total words
    total_words = len(re.findall(r'\b\w+\b', text))
    
    if total_words == 0:
        return 0.0
    
    # Count keyword occurrences (exact match)
    keyword_count = text_lower.count(keyword_lower)
    
    # Calculate density
    density = (keyword_count / total_words) * 100
    
    return round(density, 2)


def detect_search_intent(title, h1, body_text, keyword=''):
    """Detect search intent type"""
    
    combined_text = f"{title} {h1} {body_text}".lower()
    
    # Informational intent signals
    informational_signals = [
        'what is', 'how to', 'guide', 'tutorial', 'learn', 'understand',
        'explain', 'definition', 'meaning', 'tips', 'ways to', 'benefits of'
    ]
    
    # Commercial investigation intent signals
    commercial_signals = [
        'best', 'top', 'review', 'comparison', 'vs', 'versus', 'compare',
        'alternative', 'option', 'recommend', 'choose', 'find'
    ]
    
    # Transactional intent signals
    transactional_signals = [
        'buy', 'purchase', 'order', 'price', 'cost', 'cheap', 'deal',
        'discount', 'sale', 'shop', 'store', 'online', 'shipping'
    ]
    
    # Navigational intent signals (brand/company names)
    # This is harder to detect without a brand list
    
    # Count signals
    informational_count = sum(1 for signal in informational_signals if signal in combined_text)
    commercial_count = sum(1 for signal in commercial_signals if signal in combined_text)
    transactional_count = sum(1 for signal in transactional_signals if signal in combined_text)
    
    # Determine intent
    if transactional_count >= 2:
        return 'transactional'
    elif commercial_count >= 2:
        return 'commercial_investigation'
    elif informational_count >= 1:
        return 'informational'
    else:
        # Default based on keyword presence
        if keyword and keyword.lower() in title.lower():
            return 'navigational'
        return 'informational'


def extract_entities(text, limit=20):
    """Extract named entities using simple pattern matching"""
    
    # This is a simplified version - use spaCy for production
    
    entities = {
        'PERSON': [],
        'ORG': [],
        'LOCATION': [],
        'PRODUCT': [],
    }
    
    # Capitalized words (simple entity detection)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    
    # Count frequencies
    entity_freq = Counter(capitalized)
    
    # Classify top entities (simplified)
    for entity, freq in entity_freq.most_common(limit):
        # This is very basic - in production use NER model
        if len(entity.split()) > 1:
            entities['ORG'].append({'text': entity, 'count': freq})
        else:
            entities['PERSON'].append({'text': entity, 'count': freq})
    
    return entities


def calculate_readability_score(text):
    """Calculate readability score (Flesch Reading Ease)"""
    
    if not text or len(text) < 100:
        return 50  # Default for short text
    
    try:
        blob = TextBlob(text)
        
        # Count sentences
        sentences = blob.sentences
        sentence_count = len(sentences)
        
        if sentence_count == 0:
            return 50
        
        # Count words
        words = text.split()
        word_count = len(words)
        
        # Count syllables (simplified)
        syllable_count = sum(count_syllables(word) for word in words)
        
        # Flesch Reading Ease formula
        if word_count > 0 and sentence_count > 0:
            avg_sentence_length = word_count / sentence_count
            avg_syllables_per_word = syllable_count / word_count
            
            score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            
            # Normalize to 0-100
            score = max(0, min(100, score))
            
            return int(score)

    except (ZeroDivisionError, ValueError, TypeError):
        pass

    return 50  # Default


def count_syllables(word):
    """Count syllables in a word (simplified)"""
    
    word = word.lower()
    syllables = 0
    vowels = 'aeiouy'
    
    if word[0] in vowels:
        syllables += 1
    
    for i in range(1, len(word)):
        if word[i] in vowels and word[i - 1] not in vowels:
            syllables += 1
    
    if word.endswith('e'):
        syllables -= 1
    
    if word.endswith('le') and len(word) > 2 and word[-3] not in vowels:
        syllables += 1
    
    if syllables == 0:
        syllables = 1
    
    return syllables


def analyze_topic_depth(headings, body_text):
    """Analyze topic depth based on heading structure"""
    
    if not headings:
        return {'score': 0, 'depth_level': 0}
    
    # Count heading levels
    h1_count = sum(1 for h in headings if h['level'] == 'h1')
    h2_count = sum(1 for h in headings if h['level'] == 'h2')
    h3_count = sum(1 for h in headings if h['level'] == 'h3')
    h4_plus = sum(1 for h in headings if h['level'] in ['h4', 'h5', 'h6'])
    
    # Calculate depth score
    score = 0
    
    # Proper H1 usage
    if h1_count == 1:
        score += 25
    
    # H2 subtopics
    if h2_count >= 3:
        score += 30
    elif h2_count >= 1:
        score += 15
    
    # H3 depth
    if h3_count >= 5:
        score += 25
    elif h3_count >= 2:
        score += 15
    
    # Deep hierarchy
    if h4_plus >= 3:
        score += 20
    
    # Determine depth level
    if h4_plus > 0:
        depth_level = 4
    elif h3_count > 0:
        depth_level = 3
    elif h2_count > 0:
        depth_level = 2
    elif h1_count > 0:
        depth_level = 1
    else:
        depth_level = 0
    
    return {
        'score': min(score, 100),
        'depth_level': depth_level,
        'h1_count': h1_count,
        'h2_count': h2_count,
        'h3_count': h3_count,
        'h4_plus_count': h4_plus
    }