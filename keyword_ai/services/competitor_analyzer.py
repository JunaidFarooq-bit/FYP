"""
Competitor Analysis Service for Phase 1.
Analyzes top SERP results to identify keyword gaps and opportunities.
"""

import requests
import time
from typing import List, Dict, Set
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed


# Simple search API using Bing or can be extended for Google Custom Search
# For production, use: Google Custom Search API, SerpAPI, or DataForSEO


def get_serp_results(query: str, num_results: int = 10) -> List[Dict]:
    """Return observed organic results from the configured SerpAPI account."""
    from .traffic_data_providers import SerpAPIProvider

    provider = SerpAPIProvider()
    if not provider.enabled:
        return []

    result = provider.get_serp_features(query)
    if not result:
        return []

    return [
        {
            "url": item.get("link", ""),
            "title": item.get("title", ""),
            "position": item.get("position"),
            "domain": item.get("domain", ""),
            "source": "serpapi",
            "provenance": "observed_serp",
        }
        for item in result.get("organic_results", [])[:num_results]
        if item.get("link")
    ]


def extract_competitor_keywords(url: str, timeout: int = 10) -> Dict:
    """
    Extract keywords from a competitor's page.
    
    Args:
        url: Competitor URL
        timeout: Request timeout
        
    Returns:
        Dict with extracted keyword data
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract meta keywords (if present)
        meta_keywords = ""
        meta_keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords_tag:
            meta_keywords = meta_keywords_tag.get("content", "")
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ""
        
        # Extract meta description
        meta_desc = ""
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        if meta_desc_tag:
            meta_desc = meta_desc_tag.get("content", "")
        
        # Extract headings (H1-H6)
        headings = []
        for level in range(1, 7):
            for h in soup.find_all(f'h{level}'):
                text = h.get_text(strip=True)
                if text:
                    headings.append({
                        "level": level,
                        "text": text
                    })
        
        # Clean and extract text for keyword analysis
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        
        # Extract potential keywords from content (simplified)
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter out common stopwords
        stopwords = {'this', 'that', 'with', 'from', 'they', 'have', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'would', 'there', 'what', 'when', 'where', 'than', 'them', 'these', 'could', 'other', 'after', 'first', 'well', 'also', 'make', 'made', 'most', 'over', 'such', 'take', 'only', 'think', 'know', 'just', 'like', 'into', 'year', 'good', 'some', 'come', 'very', 'what', 'said', 'each', 'which', 'she', 'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'too', 'use'}
        filtered_words = [w for w in words if w not in stopwords and len(w) > 3]
        word_freq = Counter(filtered_words)
        
        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "meta_keywords": meta_keywords,
            "headings": headings,
            "top_content_keywords": [word for word, _ in word_freq.most_common(30)],
            "status": "success",
        }
        
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "error": str(e),
        }


def analyze_competitor_gap(user_content: str, competitors: List[Dict]) -> Dict:
    """
    Analyze gaps between user's content and competitors.
    
    Args:
        user_content: User's page content
        competitors: List of competitor analysis results
        
    Returns:
        Dict with gap analysis
    """
    # Extract keywords from user content (simplified)
    import re
    user_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', user_content.lower()))
    
    # Collect all competitor keywords
    competitor_keywords = set()
    for comp in competitors:
        if comp.get("status") == "success":
            comp_words = set(comp.get("top_content_keywords", []))
            competitor_keywords.update(comp_words)
            
            # Also add keywords from headings
            for heading in comp.get("headings", []):
                heading_words = re.findall(r'\b[a-zA-Z]{4,}\b', heading["text"].lower())
                competitor_keywords.update(heading_words)
    
    # Find gaps (keywords competitors use but user doesn't)
    gaps = competitor_keywords - user_words
    
    # Score gaps by frequency across competitors
    gap_scores = {}
    for gap in gaps:
        score = 0
        for comp in competitors:
            if comp.get("status") == "success":
                if gap in comp.get("top_content_keywords", []):
                    score += 1
                for heading in comp.get("headings", []):
                    if gap in heading["text"].lower():
                        score += 2  # Higher weight for headings
        gap_scores[gap] = score
    
    # Sort by score
    sorted_gaps = sorted(gap_scores.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "gap_keywords": [keyword for keyword, _ in sorted_gaps[:50]],
        "high_priority_gaps": [keyword for keyword, score in sorted_gaps[:20] if score >= 2],
        "total_competitors_analyzed": len([c for c in competitors if c.get("status") == "success"]),
        "total_gap_opportunities": len(gaps),
    }


def run_competitor_analysis(user_url: str, target_keywords: List[str], user_content: str, serp_features: Dict[str, Dict] = None) -> Dict:
    """
    Full competitor analysis pipeline.
    
    Args:
        user_url: User's page URL
        target_keywords: Keywords to search for competitors
        user_content: User's page content
        
    Returns:
        Comprehensive competitor analysis
    """
    # Step 1: Reuse observed organic SERPs when supplied by the main pipeline.
    user_domain = urlparse(user_url).netloc.lower().removeprefix("www.")
    observed_results = []
    seen_urls = set()
    serp_features = serp_features or {}

    for keyword in target_keywords[:3]:
        cached_serp = serp_features.get(keyword, {})
        source_results = [
            {
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "position": item.get("position"),
                "domain": item.get("domain", ""),
                "source": "serpapi",
                "provenance": "observed_serp",
            }
            for item in cached_serp.get("organic_results", [])
        ] if cached_serp else get_serp_results(keyword, num_results=10)

        for result in source_results:
            competitor_domain = result.get("domain", "").lower().removeprefix("www.")
            competitor_url = result.get("url", "")
            if not competitor_url or competitor_domain == user_domain or competitor_url in seen_urls:
                continue
            seen_urls.add(competitor_url)
            observed_results.append({**result, "query": keyword})

    # Step 2: Analyze the first five observed competitors concurrently.
    competitor_data = []
    selected = observed_results[:5]
    with ThreadPoolExecutor(max_workers=min(5, len(selected) or 1)) as pool:
        futures = {
            pool.submit(extract_competitor_keywords, result["url"], 8): result
            for result in selected
        }
        for future in as_completed(futures):
            result = futures[future]
            try:
                data = future.result()
            except Exception as exc:
                data = {"url": result["url"], "status": "error", "error": str(exc)}
            data.update({
                "serp_position": result.get("position"),
                "query": result.get("query"),
                "domain": result.get("domain"),
                "provenance": "observed_serp",
            })
            competitor_data.append(data)

    competitor_data.sort(key=lambda item: item.get("serp_position") or 999)

    # Step 3: Analyze gaps
    if competitor_data:
        gap_analysis = analyze_competitor_gap(user_content, competitor_data)
    else:
        gap_analysis = {
            "gap_keywords": [],
            "high_priority_gaps": [],
            "message": "No observed competitor results were available for this analysis."
        }
    
    return {
        "user_url": user_url,
        "target_keywords": target_keywords,
        "competitors": competitor_data,
        "gap_analysis": gap_analysis,
        "recommendations": generate_recommendations(gap_analysis),
    }


def generate_recommendations(gap_analysis: Dict) -> List[str]:
    """Generate actionable recommendations from gap analysis."""
    recommendations = []
    
    high_priority = gap_analysis.get("high_priority_gaps", [])
    if high_priority:
        recommendations.append(
            f"Add content targeting these high-priority keywords: {', '.join(high_priority[:5])}"
        )
    
    total_gaps = gap_analysis.get("total_gap_opportunities", 0)
    if total_gaps > 20:
        recommendations.append(
            f"Found {total_gaps} keyword opportunities from competitor analysis."
        )
    
    if not high_priority and not gap_analysis.get("gap_keywords"):
        recommendations.append(
            "No observed competitor gaps were available for the selected queries."
        )
    
    return recommendations


# API integration notes for production:
SERP_API_PROVIDERS = {
    "serpapi": "https://serpapi.com/ (Google, Bing, Yahoo, etc.)",
    "google_custom_search": "https://developers.google.com/custom-search/v1/overview",
    "dataforseo": "https://dataforseo.com/",
    "brightdata": "https://brightdata.com/",
}
