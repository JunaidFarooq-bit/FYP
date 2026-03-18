"""
Sentiment Analyzer for SEO Tool
Enhanced with detailed analysis and insights
"""

import os
import json
from openai import OpenAI
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
from collections import Counter

OPENROUTER_API_KEY = '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'

def analyze_sentiment(text, api_key=None, mode='auto', debug=False):
    """
    Analyze sentiment of text content with detailed insights
    
    Args:
        text (str): Content to analyze
        api_key (str): OpenRouter API key (optional, reads from env if not provided)
        mode (str): 'fast', 'deep', or 'auto'
        debug (bool): Print diagnostic information
    
    Returns:
        dict: Comprehensive sentiment analysis results
    """
    
    # Validate input
    if not text or len(text.strip()) < 10:
        return {
            'success': False,
            'error': 'Text too short to analyze',
            'sentiment': 'neutral',
            'sentiment_score': 50,
            'confidence': 0,
            'tone': [],
            'method': 'none'
        }
    
    # Get API key
    if not api_key:
        api_key = os.getenv('OPENROUTER_API_KEY', OPENROUTER_API_KEY)
    
    if debug:
        print(f"[DEBUG] Text length: {len(text)}")
        print(f"[DEBUG] Mode: {mode}")
        print(f"[DEBUG] API key present: {bool(api_key)}")
    
    # Initialize analyzers
    vader = SentimentIntensityAnalyzer()
    
    # ✅ NEW: Get text statistics
    text_stats = _analyze_text_statistics(text)
    
    try:
        # Decide which method to use
        use_ai = False
        if mode == 'deep' and api_key:
            use_ai = True
        elif mode == 'auto' and api_key and len(text) > 1000:
            use_ai = True
        
        if debug:
            print(f"[DEBUG] Will use AI: {use_ai}")
        
        # AI-powered analysis
        if use_ai:
            try:
                if debug:
                    print("[DEBUG] Attempting AI analysis...")
                result = _analyze_with_ai(text, api_key, debug=debug)
                result['success'] = True
                # ✅ Add text statistics to AI result
                result['text_stats'] = text_stats
                if debug:
                    print(f"[DEBUG] AI analysis succeeded")
                return result
            except Exception as e:
                if debug:
                    print(f"[DEBUG] AI analysis failed: {e}")
                print(f"AI analysis failed: {e}, falling back to VADER")
        
        # VADER analysis (fast, local, free)
        if debug:
            print("[DEBUG] Using VADER analysis...")
        result = _analyze_with_vader(text, vader, debug=debug)
        result['success'] = True
        # ✅ Add text statistics to VADER result
        result['text_stats'] = text_stats
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'sentiment': 'neutral',
            'sentiment_score': 50,
            'confidence': 0,
            'tone': [],
            'method': 'error'
        }


def _analyze_text_statistics(text):
    """
    ✅ NEW: Analyze text statistics and characteristics
    """
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Count punctuation
    exclamation_marks = text.count('!')
    question_marks = text.count('?')
    
    # Detect capitalization
    all_caps_words = len([w for w in words if w.isupper() and len(w) > 1])
    
    # Calculate readability (simplified)
    avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
    avg_sentence_length = len(words) / len(sentences) if sentences else 0
    
    # Detect emotional indicators
    emotional_words = _detect_emotional_words(text)
    
    return {
        'word_count': len(words),
        'sentence_count': len(sentences),
        'avg_word_length': round(avg_word_length, 1),
        'avg_sentence_length': round(avg_sentence_length, 1),
        'exclamation_marks': exclamation_marks,
        'question_marks': question_marks,
        'all_caps_words': all_caps_words,
        'emotional_intensity': _calculate_emotional_intensity(
            exclamation_marks, all_caps_words, len(words)
        ),
        'top_emotional_words': emotional_words
    }


def _detect_emotional_words(text):
    """
    ✅ NEW: Detect and count emotional words
    """
    text_lower = text.lower()
    
    emotional_keywords = {
        'positive': ['amazing', 'excellent', 'fantastic', 'great', 'wonderful', 
                    'love', 'best', 'perfect', 'awesome', 'brilliant'],
        'negative': ['terrible', 'awful', 'horrible', 'worst', 'bad', 'hate', 
                    'disappointing', 'poor', 'waste', 'useless'],
        'urgent': ['now', 'today', 'immediately', 'hurry', 'limited', 'urgent', 'quick'],
        'trust': ['guarantee', 'proven', 'certified', 'trusted', 'verified', 'authentic']
    }
    
    found_words = {}
    for category, keywords in emotional_keywords.items():
        matches = [word for word in keywords if word in text_lower]
        if matches:
            found_words[category] = matches
    
    return found_words


def _calculate_emotional_intensity(exclamations, caps_words, total_words):
    """
    ✅ NEW: Calculate emotional intensity score
    """
    if total_words == 0:
        return 0
    
    exclamation_score = min(exclamations * 10, 40)
    caps_score = min(caps_words * 15, 40)
    
    intensity = exclamation_score + caps_score
    return min(intensity, 100)


def _analyze_with_ai(text, api_key, debug=False):
    """Use OpenRouter AI for detailed analysis"""
    
    if not api_key or not api_key.startswith('sk-'):
        raise ValueError("Invalid API key format")
    
    if debug:
        print(f"[DEBUG] Initializing OpenAI client...")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        timeout=30.0,
        max_retries=2
    )
    
    text_sample = text[:3000]
    
    if debug:
        print(f"[DEBUG] Sending request to OpenRouter...")
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert SEO content analyst.
Analyze sentiment, tone, and provide actionable insights. Return ONLY valid JSON (no markdown, no backticks):
{
    "sentiment": "positive/neutral/negative",
    "sentiment_score": 0-100,
    "confidence": 0-100,
    "tone": ["informative", "promotional", "clickbait", "professional", "conversational", "formal"],
    "intent": "informational/transactional/navigational/commercial",
    "primary_topic": "main topic in 2-4 words",
    "seo_quality": "high/medium/low",
    "readability": "easy/moderate/difficult",
    "target_audience": "general/technical/business/casual",
    "emotional_appeal": "high/medium/low",
    "call_to_action": "present/absent",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "recommendations": ["tip1", "tip2", "tip3"]
}"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this content:\n\n{text_sample}"
                }
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        if debug:
            print(f"[DEBUG] Received AI response")
        
        # Clean markdown if present
        if '```' in response_text:
            lines = response_text.split('```')
            for line in lines:
                if line.strip().startswith('{'):
                    response_text = line.strip()
                    break
        
        result = json.loads(response_text)
        result['method'] = 'OpenRouter AI (GPT-4o-mini)'
        
        # ✅ NEW: Add sentiment explanation
        result['analysis_summary'] = _generate_summary(result)
        
        if debug:
            print(f"[DEBUG] AI analysis complete")
        
        return result
        
    except json.JSONDecodeError as e:
        if debug:
            print(f"[DEBUG] JSON parsing failed: {e}")
        raise Exception(f"AI returned invalid JSON: {e}")
    except Exception as e:
        if debug:
            print(f"[DEBUG] API error: {e}")
        raise e


def _analyze_with_vader(text, vader, debug=False):
    """Use VADER for fast local analysis with enhanced details"""
    
    scores = vader.polarity_scores(text)
    
    if debug:
        print(f"[DEBUG] VADER raw scores: {scores}")
    
    # Classify sentiment
    compound = scores['compound']
    if compound >= 0.05:
        sentiment = 'positive'
    elif compound <= -0.05:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    
    # Convert to 0-100 scale
    sentiment_score = int((compound + 1) * 50)
    
    # Calculate dynamic confidence
    confidence = _calculate_confidence(scores, compound)
    
    if debug:
        print(f"[DEBUG] Compound: {compound}, Sentiment: {sentiment}, Score: {sentiment_score}")
    
    # Detect tone
    tone = _detect_basic_tone(text)
    
    # ✅ NEW: Detect intent
    intent = _detect_intent(text)
    
    # ✅ NEW: Detect call to action
    has_cta = _detect_call_to_action(text)
    
    # ✅ NEW: Basic strengths and weaknesses
    strengths, weaknesses = _analyze_content_quality(text, scores)
    
    result = {
        'sentiment': sentiment,
        'sentiment_score': sentiment_score,
        'confidence': confidence,
        'tone': tone,
        'intent': intent,
        'call_to_action': 'present' if has_cta else 'absent',
        'method': 'VADER (Fast & Local)',
        'strengths': strengths,
        'weaknesses': weaknesses,
        'details': {
            'positive': round(scores['pos'] * 100, 1),
            'neutral': round(scores['neu'] * 100, 1),
            'negative': round(scores['neg'] * 100, 1),
            'compound': round(compound, 3)
        }
    }
    
    # ✅ NEW: Add summary
    result['analysis_summary'] = _generate_summary(result)
    
    return result


def _detect_intent(text):
    """
    ✅ NEW: Detect content intent
    """
    text_lower = text.lower()
    
    # Transactional (buy/purchase focused)
    if any(kw in text_lower for kw in ['buy', 'purchase', 'order', 'cart', 'checkout', 'price', '$']):
        return 'transactional'
    
    # Navigational (brand/location seeking)
    if any(kw in text_lower for kw in ['login', 'contact', 'about us', 'location', 'hours']):
        return 'navigational'
    
    # Commercial (comparing/researching)
    if any(kw in text_lower for kw in ['best', 'top', 'review', 'comparison', 'vs', 'alternative']):
        return 'commercial'
    
    # Informational (learning/understanding)
    return 'informational'


def _detect_call_to_action(text):
    """
    ✅ NEW: Detect if content has call-to-action
    """
    text_lower = text.lower()
    
    cta_phrases = [
        'click here', 'learn more', 'sign up', 'subscribe', 'download',
        'get started', 'try now', 'buy now', 'contact us', 'register',
        'join', 'discover', 'shop now', 'order now'
    ]
    
    return any(phrase in text_lower for phrase in cta_phrases)


def _analyze_content_quality(text, vader_scores):
    """
    ✅ NEW: Analyze content strengths and weaknesses
    """
    strengths = []
    weaknesses = []
    
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Check word count
    if len(words) > 300:
        strengths.append("Comprehensive content (300+ words)")
    elif len(words) < 100:
        weaknesses.append("Content may be too brief (under 100 words)")
    
    # Check sentiment clarity
    if abs(vader_scores['compound']) > 0.5:
        strengths.append("Clear sentiment expressed")
    elif abs(vader_scores['compound']) < 0.1:
        weaknesses.append("Sentiment is very neutral/unclear")
    
    # Check for promotional balance
    if vader_scores['pos'] > 0.3 and vader_scores['neg'] < 0.1:
        strengths.append("Positive tone maintained")
    
    # Check exclamation marks
    exclamations = text.count('!')
    if exclamations > 5:
        weaknesses.append(f"Excessive exclamation marks ({exclamations})")
    
    # Check caps
    all_caps = len([w for w in words if w.isupper() and len(w) > 1])
    if all_caps > 3:
        weaknesses.append(f"Too many words in ALL CAPS ({all_caps})")
    
    return strengths, weaknesses


def _generate_summary(result):
    """
    ✅ NEW: Generate human-readable analysis summary
    """
    sentiment = result.get('sentiment', 'neutral')
    score = result.get('sentiment_score', 50)
    tone = result.get('tone', [])
    
    # Sentiment description
    if sentiment == 'positive':
        if score > 80:
            sentiment_desc = "very positive"
        else:
            sentiment_desc = "moderately positive"
    elif sentiment == 'negative':
        if score < 20:
            sentiment_desc = "very negative"
        else:
            sentiment_desc = "moderately negative"
    else:
        sentiment_desc = "neutral"
    
    # Tone description
    tone_desc = ", ".join(tone) if tone else "neutral"
    
    summary = f"This content has a {sentiment_desc} sentiment (score: {score}/100) with a {tone_desc} tone."
    
    # Add intent if available
    if 'intent' in result:
        summary += f" The primary intent appears to be {result['intent']}."
    
    return summary


def _calculate_confidence(scores, compound):
    """Calculate dynamic confidence based on VADER scores"""
    
    compound_confidence = abs(compound) * 50 + 50
    
    pos = scores['pos']
    neg = scores['neg']
    neu = scores['neu']
    
    max_sentiment = max(pos, neg)
    if max_sentiment > 0.5:
        dominance_boost = (max_sentiment - 0.5) * 20
    else:
        dominance_boost = 0
    
    if neu > 0.7:
        neutrality_penalty = (neu - 0.7) * 30
    else:
        neutrality_penalty = 0
    
    confidence = compound_confidence + dominance_boost - neutrality_penalty
    confidence = max(0, min(100, confidence))
    
    return int(confidence)


def _detect_basic_tone(text):
    """Basic rule-based tone detection"""
    text_lower = text.lower()
    tones = []
    
    # Promotional
    if any(kw in text_lower for kw in ['buy', 'discount', 'offer', 'deal', 'sale', 'limited', 'now']):
        tones.append('promotional')
    
    # Clickbait
    if any(kw in text_lower for kw in ['shocking', 'unbelievable', 'secret', 'amazing', "won't believe"]):
        tones.append('clickbait')
    
    # Informative
    if any(kw in text_lower for kw in ['according', 'research', 'study', 'data', 'analysis', 'report']):
        tones.append('informative')
    
    # Professional
    if any(kw in text_lower for kw in ['therefore', 'however', 'furthermore', 'consequently']):
        tones.append('professional')
    
    # Conversational
    if any(kw in text_lower for kw in ["you'll", "we'll", "let's", "your", "our"]):
        tones.append('conversational')
    
    # Default to neutral if nothing detected
    if not tones:
        tones.append('neutral')
    
    return tones


# Enhanced test function
if __name__ == "__main__":
    print("="*60)
    print("ENHANCED SENTIMENT ANALYZER TEST")
    print("="*60)
    
    # Test 1: Promotional content
    print("\n[TEST 1] Promotional content:")
    test_text_1 = """
    This is an AMAZING product! You should definitely buy it now. 
    Limited time offer - get 50% OFF today! Don't miss out on this 
    incredible deal. Click here to order now and transform your life!
    """
    result_1 = analyze_sentiment(test_text_1, mode='deep', debug=False)
    print(json.dumps(result_1, indent=2))
    
    # Test 2: Informative content
    print("\n[TEST 2] Informative content:")
    test_text_2 = """
    According to recent research, the study shows that data analysis 
    can improve business outcomes by 40%. The report indicates that 
    companies using analytics have better decision-making processes.
    Furthermore, the findings suggest a correlation between data 
    literacy and organizational success.
    """
    result_2 = analyze_sentiment(test_text_2, mode='deep', debug=False)
    print(json.dumps(result_2, indent=2))
    
    # Test 3: Negative review
    print("\n[TEST 3] Negative review:")
    test_text_3 = """
    This product is absolutely terrible and completely disappointing. 
    Total waste of money. Very poor quality and doesn't work as advertised. 
    I would not recommend this to anyone. Save your money!
    """
    result_3 = analyze_sentiment(test_text_3, mode='deep', debug=False)
    print(json.dumps(result_3, indent=2))