"""
Keyword Output Filter (Fix 5)
Filters out undesirable keywords from the pipeline output.

Includes blocklists for:
- Gambling/Casino keywords
- Adult/NSFW content
- Pharmaceuticals (controlled substances)
- Known spam/affiliate terms
- Offensive language
"""

import re
from typing import List, Dict, Set


# Blocked keyword patterns (lowercase, partial matches)
GAMBLING_BLOCKLIST: Set[str] = {
    "casino", "casinos", "slot", "slots", "poker", "blackjack", "roulette",
    "betting", "gambling", "wager", "odds", "jackpot", "lottery", "lotto",
    "bingo", "sportsbook", "bookmaker", "bet", "bets", "betting",
    "online casino", "live casino", "mobile casino", "crypto casino",
    "free spins", "no deposit", "bonus code", "promo code", "wagering",
    "high roller", "vip casino", "real money", "cash bonus",
    "blackjack strategy", "poker hands", "roulette strategy", "slot machine",
}

ADULT_BLOCKLIST: Set[str] = {
    "xxx", "porn", "porno", "sex", "sexy", "nude", "naked", "escort",
    "adult", "mature", "nsfw", "onlyfans", "camgirl", "webcam",
    "dating", "hookup", "singles", "swingers", "affair", "mistress",
    "bride", "mail order", "russian bride", "asian bride",
}

PHARMA_BLOCKLIST: Set[str] = {
    "viagra", "cialis", "levitra", "kamagra", "sildenafil", "tadalafil",
    "phentermine", "adderall", "xanax", "valium", "ativan", "klonopin",
    "oxycodone", "oxycontin", "percocet", "vicodin", "hydrocodone",
    "tramadol", "fentanyl", "morphine", "codeine",
    "prednisone", "amoxicillin", "azithromycin", "ciprofloxacin",
    "propecia", "finasteride", "minoxidil", "rogaine",
    "weight loss pill", "diet pill", "fat burner", "appetite suppressant",
    "steroid", "anabolic", "testosterone", "hgh", "human growth hormone",
    "cbd oil", "cbd gummies", "delta 8", "delta 9", "thc", "cannabis",
    "no prescription", "without prescription", "buy cheap", "generic pills",
}

SPAM_AFFILIATE_BLOCKLIST: Set[str] = {
    "earn money", "make money", "get rich", "work from home",
    "passive income", "side hustle", "quick cash", "easy money",
    "mlm", "multi level marketing", "pyramid scheme",
    "investment opportunity", "financial freedom", "be your own boss",
    "limited time", "act now", "urgent", "hurry", "exclusive deal",
    "click here", "buy now", "order now", "call now", "limited supply",
    "risk free", "money back", "guaranteed", "no risk",
    "free trial", "just pay shipping", "as seen on tv",
    "crypto scam", "bitcoin scam", "forex scam", "binary options",
    "loan shark", "payday loan", "cash advance", "title loan",
    "debt consolidation", "credit repair", "fix credit",
}

# Garbage/foreign nonsense keywords that appear from cross-contamination
GARBAGE_FOREIGN_BLOCKLIST: Set[str] = {
    # Nonsense terms from screenshots (codup.co contamination)
    "pozhikara", "baghir", "pozhikara baghir", "politikalarina",
    # Turkish gambling terms found on codup.co
    "paribahis", "bahis", "pinco casino", "pinco", "oyuncularinin",
    "oyuncularinin", "oyun", "kumar", "online bahis", "bahsegel",
    "bettilt", "pin up", "pinup", "giriş", "giris", "güvenilir",
    "milyar", "dolar", "reklam", "yatırım", "yatirim",
    # Common foreign gambling/spam terms
    "matka", "satta", "satta matka", "fix jodi", "fix game",
    "kalyan", "milan", "rajdhani", "disawar", "gali", "desawar",
    # Other common garbage terms
    "chart", "panel", "result", " guessing",
}

# Combine all blocklists
FULL_BLOCKLIST: Set[str] = (
    GAMBLING_BLOCKLIST | 
    ADULT_BLOCKLIST | 
    PHARMA_BLOCKLIST | 
    SPAM_AFFILIATE_BLOCKLIST |
    GARBAGE_FOREIGN_BLOCKLIST
)


def is_valid_english_keyword(keyword: str, min_english_word_ratio: float = 0.5) -> bool:
    """
    Check if a keyword contains valid English words.
    
    This catches foreign language keywords and gibberish that 
    slip through other filters.
    
    Args:
        keyword: The keyword to check
        min_english_word_ratio: Minimum ratio of words that should be valid English
        
    Returns:
        True if keyword appears to be valid English
    """
    if not isinstance(keyword, str):
        return False
    
    # Common English words for validation (subset of most common words)
    common_english = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their",
        "what", "so", "up", "out", "if", "about", "who", "get", "which", "go",
        "me", "when", "make", "can", "like", "time", "no", "just", "him", "know",
        "take", "people", "into", "year", "your", "good", "some", "could", "them",
        "see", "other", "than", "then", "now", "look", "only", "come", "its", "over",
        "think", "also", "back", "after", "use", "two", "how", "our", "work",
        "first", "well", "way", "even", "new", "want", "because", "any", "these",
        "give", "day", "most", "us", "is", "was", "are", "been", "has", "had",
        "did", "does", "doing", "software", "development", "web", "app", "application",
        "digital", "marketing", "seo", "services", "company", "business", "online",
        "global", "professional", "solution", "solutions", "technology", "tech",
        "design", "website", "websites", "mobile", "custom", "best", "top",
        "expert", "team", "agency", "consulting", "strategy", "strategies",
        "content", "management", "system", "platform", "tools", "tool",
        "analytics", "data", "cloud", "server", "hosting", "domain", "email",
        "ecommerce", "commerce", "shop", "store", "product", "products",
        "buy", "purchase", "order", "cheap", "affordable", "price", "pricing",
        "service", "support", "help", "guide", "tutorial", "training",
        "learn", "learning", "course", "courses", "certification", "certified",
        "review", "reviews", "rating", "compare", "comparison", "vs", "versus",
        "free", "trial", "demo", "download", "install", "setup", "configure",
        "integrate", "integration", "api", "automation", "automated", "ai",
        "artificial", "intelligence", "machine", "learning", "ml", "bot",
        "chatbot", "virtual", "assistant", "voice", "search", "engine",
        "optimization", "ranking", "rankings", "traffic", "conversion",
        "lead", "leads", "generation", "generating", "sales", "funnel",
        "landing", "page", "pages", "blog", "article", "articles", "news",
        "update", "updates", "latest", "new", "trends", "trending", "2024", "2025",
        "beginner", "beginners", "advanced", "expert", "experts", "professional",
        "enterprise", "small", "medium", "large", "startup", "startups",
        "local", "national", "international", "worldwide", "near", "me",
        "how", "what", "why", "where", "when", "who", "which", "can",
        "do", "does", "is", "are", "was", "were", "will", "would",
        "should", "could", "may", "might", "must", "shall",
        "to", "for", "in", "on", "at", "by", "with", "from", "about",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "up", "down", "out", "off", "over", "under", "again", "further",
    }
    
    # Words that indicate gambling/gaming even if they look like English
    gambling_indicators = {
        "bet", "betting", "wager", "odds", "jackpot", "casino", "poker",
        "slot", "slots", "lottery", "lotto", "bingo", "race", "racing",
        "fix", "jodi", "matka", "satta", "chart", "panel", "result",
        "open", "close", "final", "ank", "patti", "panna",
        # Turkish gambling terms
        "bahis", "paribahis", "pinco", "oyuncularinin", "oyun", "kumar",
        "bahsegel", "bettilt", "pinup", "pin", "giriş", "giris",
    }
    
    # Foreign/non-English words that indicate spam
    foreign_spam_words = {
        # Turkish words from codup.co spam content
        "dijital", "eglence", "dunyasinda", "tercih", "edilen", "kategorileri",
        "istikrari", "kaliteyi", "guveni", "guven", "musteri", "memnuniyet",
        "verilerine", "yilinda", "yili", "milyar", "olarak", "kaydedilmistir",
        "politikalara", "politika", "baglidir", "bagli", "olcekle", "olcek",
        "insan", "oynamakta", "oyna", "kullanicilar", "kullanici", "hizli",
        "yapmak", "linkini", "kullaniyor", "yeni", "uyeliklerde", "uyelik",
        "ekstra", "bonus", "firsatlari", "firsat", "sunan", "sunar",
        "kazandirmaya", "devam", "ediyor", "yilin", "dikkat", "ceken",
        "surumu", "surum", "olacak", "simdiden", "gundeme", "oturdu",
        "adresini", "adres", "seciyor", "turkiye", "bahiscilerin", "guvenini",
        "kazanan", "guvenilir", "yapisiyla", "one", "cikiyor", "kitlenin",
        "platformlarindan", "biridir", "sisteme", "hizli", "giris", "yapmak",
        "kazanmaya", "devam", "ediyor", "sürümü", "olacak", "şimdiden",
        "gündeme", "oturdu", "kullanıcılar", "hızlı", "işlem", "için",
        "seçiyor", "türkiye", "bahisçilerin", "yapısıyla", "ön", "çıkıyor",
        # Domain TLDs commonly used in spam
        "co", "uk", "pk", "ae",
    }
    
    words = keyword.lower().split()
    if not words:
        return False
    
    english_word_count = 0
    gambling_indicator_count = 0
    foreign_spam_count = 0
    
    for word in words:
        # Remove punctuation
        clean_word = re.sub(r'[^\w]', '', word)
        if not clean_word:
            continue
            
        if clean_word in common_english:
            english_word_count += 1
        if clean_word in gambling_indicators:
            gambling_indicator_count += 1
        if clean_word in foreign_spam_words:
            foreign_spam_count += 1
    
    # If it has gambling indicators, it's likely garbage
    if gambling_indicator_count > 0:
        return False
    
    # If it has foreign spam words, reject it
    if foreign_spam_count > 0:
        return False
    
    # Require at least 60% English words (stricter than 50%)
    min_english_word_ratio = max(min_english_word_ratio, 0.6)
    ratio = english_word_count / len(words) if words else 0
    return ratio >= min_english_word_ratio


def _contains_blocked_term(keyword, blocklist: Set[str] = None) -> bool:
    """
    Check if a keyword contains any blocked terms.
    
    Args:
        keyword: The keyword to check (string or dict with 'keyword' field)
        blocklist: Set of blocked terms (defaults to FULL_BLOCKLIST)
        
    Returns:
        True if keyword contains a blocked term
    """
    if blocklist is None:
        blocklist = FULL_BLOCKLIST
    
    # Handle dict objects by extracting the keyword string
    if isinstance(keyword, dict):
        keyword = keyword.get("keyword", "")
    
    # Skip non-string inputs
    if not isinstance(keyword, str):
        return False
    
    keyword_lower = keyword.lower()
    keyword_words = set(keyword_lower.split())
    
    # Check for exact word matches
    for blocked in blocklist:
        blocked_lower = blocked.lower()
        
        # Check if blocked term is a substring
        if blocked_lower in keyword_lower:
            return True
        
        # Check for word boundary matches (for multi-word terms)
        if " " in blocked_lower and blocked_lower in keyword_lower:
            return True
    
    return False


def filter_keywords(
    keywords: List,
    blocklist: Set[str] = None,
    return_blocked: bool = False
) -> List | tuple[List, List]:
    """
    Filter out blocked keywords from a list.
    
    Args:
        keywords: List of keywords to filter
        blocklist: Set of blocked terms (defaults to FULL_BLOCKLIST)
        return_blocked: If True, return tuple of (allowed, blocked)
        
    Returns:
        List of allowed keywords, or tuple of (allowed, blocked) if return_blocked=True
    """
    if blocklist is None:
        blocklist = FULL_BLOCKLIST
    
    allowed = []
    blocked = []
    
    for keyword in keywords:
        # Handle dict objects by extracting the keyword string
        keyword_str = keyword
        if isinstance(keyword, dict):
            keyword_str = keyword.get("keyword", "")
        
        # Skip non-string inputs
        if not isinstance(keyword_str, str):
            allowed.append(keyword)
            continue
            
        if _contains_blocked_term(keyword_str, blocklist):
            blocked.append(keyword)
        else:
            allowed.append(keyword)
    
    if return_blocked:
        return allowed, blocked
    return allowed


def filter_keyword_objects(
    keyword_objects: List[Dict],
    keyword_field: str = "keyword",
    blocklist: Set[str] = None,
    add_flag: bool = True
) -> List[Dict]:
    """
    Filter keyword objects (dicts) by checking a specific field.
    
    Args:
        keyword_objects: List of dicts containing keywords
        keyword_field: The field name containing the keyword string
        blocklist: Set of blocked terms (defaults to FULL_BLOCKLIST)
        add_flag: If True, add 'is_blocked' field to each object
        
    Returns:
        List of filtered keyword objects with allowed keywords only
    """
    if blocklist is None:
        blocklist = FULL_BLOCKLIST
    
    filtered = []
    
    for obj in keyword_objects:
        keyword = obj.get(keyword_field, "")
        is_blocked = _contains_blocked_term(keyword, blocklist)
        
        if add_flag:
            obj["is_blocked"] = is_blocked
        
        if not is_blocked:
            filtered.append(obj)
    
    return filtered


def decontaminate_pipeline_output(
    result: Dict,
    blocklist: Set[str] = None,
    validate_english: bool = True
) -> Dict:
    """
    Apply decontamination filter to pipeline output.
    
    Filters all keyword lists in the result dict.
    
    Args:
        result: Pipeline output dict containing keyword lists
        blocklist: Set of blocked terms (defaults to FULL_BLOCKLIST)
        validate_english: Also validate keywords are valid English words
        
    Returns:
        Decontaminated result dict with blocked keywords removed
    """
    if blocklist is None:
        blocklist = FULL_BLOCKLIST
    
    # Track what was blocked for logging/debugging
    blocked_keywords = []
    invalid_english_keywords = []
    
    # Filter simple keyword lists
    list_fields = [
        "relevant_keywords",
        "focus_keywords",
        "gap_keywords",
        "high_priority_gaps",
        "question_keywords",
    ]
    
    for field in list_fields:
        if field in result and isinstance(result[field], list):
            # First apply blocklist filter
            allowed, blocked = filter_keywords(result[field], blocklist, return_blocked=True)
            blocked_keywords.extend(blocked)
            
            # Then validate English if enabled
            if validate_english:
                english_valid = []
                for kw in allowed:
                    kw_str = kw.get("keyword", "") if isinstance(kw, dict) else kw
                    if isinstance(kw_str, str) and is_valid_english_keyword(kw_str):
                        english_valid.append(kw)
                    else:
                        invalid_english_keywords.append(kw_str)
                allowed = english_valid
            
            result[field] = allowed
    
    # Filter keyword object lists
    object_list_fields = [
        "scored_keywords",
        "ml_generated_suggestions",
        "semantic_keywords",
        "tfidf_keywords",
        "keybert_keywords",
        "ai_expanded_keywords",
        "expanded_keywords",
    ]
    
    for field in object_list_fields:
        if field in result and isinstance(result[field], list):
            # Apply blocklist filter
            filtered = filter_keyword_objects(result[field], keyword_field="keyword", blocklist=blocklist)
            
            # Track what was removed by blocklist
            original_count = len(result[field])
            after_blocklist = len(filtered)
            if original_count > after_blocklist:
                for obj in result[field]:
                    kw = obj.get("keyword", "") if isinstance(obj, dict) else obj
                    if isinstance(kw, str) and _contains_blocked_term(kw, blocklist):
                        blocked_keywords.append(kw)
            
            # Also validate English if enabled
            if validate_english:
                english_filtered = []
                for obj in filtered:
                    kw = obj.get("keyword", "") if isinstance(obj, dict) else obj
                    if isinstance(kw, str):
                        if is_valid_english_keyword(kw):
                            english_filtered.append(obj)
                        else:
                            invalid_english_keywords.append(kw)
                filtered = english_filtered
            
            result[field] = filtered
    
    # Add decontamination metadata
    result["decontamination_applied"] = True
    result["blocked_keywords_count"] = len(blocked_keywords)
    result["blocked_keywords_sample"] = blocked_keywords[:10]  # First 10 for debugging
    result["invalid_english_count"] = len(invalid_english_keywords)
    result["invalid_english_sample"] = invalid_english_keywords[:10]  # First 10 for debugging
    
    return result


def get_blocklist_stats() -> Dict[str, int]:
    """
    Get statistics about the current blocklist.
    
    Returns:
        Dict with counts for each category
    """
    return {
        "gambling": len(GAMBLING_BLOCKLIST),
        "adult": len(ADULT_BLOCKLIST),
        "pharma": len(PHARMA_BLOCKLIST),
        "spam_affiliate": len(SPAM_AFFILIATE_BLOCKLIST),
        "garbage_foreign": len(GARBAGE_FOREIGN_BLOCKLIST),
        "total": len(FULL_BLOCKLIST),
    }


def is_keyword_safe(keyword) -> bool:
    """
    Quick check if a single keyword is safe (not blocked).
    
    Args:
        keyword: The keyword to check (string or dict with 'keyword' field)
        
    Returns:
        True if keyword is safe, False if blocked
    """
    # Handle dict objects
    if isinstance(keyword, dict):
        keyword = keyword.get("keyword", "")
    
    # Non-strings are considered safe
    if not isinstance(keyword, str):
        return True
        
    return not _contains_blocked_term(keyword, FULL_BLOCKLIST)
