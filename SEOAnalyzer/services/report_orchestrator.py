"""
================================================================================
Comprehensive SEO Report Orchestrator
================================================================================

Orchestrates data collection from 3 analysis systems:
1. SEOAnalyzer - Traditional website audit (titles, meta, speed, links, etc.)
2. SEO Metrics - Moz API for Domain Authority, Page Authority, Backlinks
3. keyword_ai - AI-powered keyword suggestions, semantic analysis

Features:
- Cache management (24-hour TTL)
- Data merging from multiple sources
- Fallback handling for missing data

================================================================================
"""

import hashlib
import hmac
import base64
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import quote

import requests
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache TTL in seconds (24 hours)
CACHE_TTL = 86400


def get_cache_key(url: str) -> str:
    """Generate cache key for comprehensive report."""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return f"comprehensive_report_{url_hash}"


def check_cached_report(url: str) -> Tuple[bool, Optional[Dict]]:
    """
    Check if comprehensive report data exists in cache.
    
    Returns:
        Tuple of (exists: bool, data: dict or None)
    """
    cache_key = get_cache_key(url)
    cached_data = cache.get(cache_key)
    
    if cached_data:
        cached_time = cached_data.get('cached_at', '')
        logger.info(f"[CACHE HIT] Report for {url} (cached: {cached_time})")
        return True, cached_data
    
    logger.info(f"[CACHE MISS] Report for {url}")
    return False, None


def cache_report_data(url: str, data: Dict) -> None:
    """Cache comprehensive report data."""
    cache_key = get_cache_key(url)
    data['cached_at'] = datetime.now().isoformat()
    cache.set(cache_key, data, CACHE_TTL)
    logger.info(f"[CACHE SET] Report for {url} (TTL: {CACHE_TTL}s)")


def run_seoanalyzer_audit(url: str, request=None) -> Dict[str, Any]:
    """
    Run traditional SEOAnalyzer audit.
    
    Args:
        url: URL to analyze
        request: Optional Django request for user context
        
    Returns:
        Dictionary with all SEO audit data
    """
    try:
        from ..views import Website_Audit
        
        logger.info(f"[SEOAnalyzer] Starting audit for: {url}")
        audit = Website_Audit(url, request=request)
        data = audit.get_data()
        logger.info(f"[SEOAnalyzer] Audit complete: {len(data)} metrics collected")
        return data
    except Exception as e:
        logger.error(f"[SEOAnalyzer] Audit failed: {e}")
        return {'url': url, 'error': str(e)}


def run_keyword_ai_analysis(url: str) -> Dict[str, Any]:
    """
    Run keyword_ai pipeline v2 for AI-powered keyword suggestions.
    
    Args:
        url: URL to analyze
        
    Returns:
        Dictionary with keyword opportunities, clusters, and semantic analysis
    """
    try:
        from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2
        
        logger.info(f"[keyword_ai] Starting pipeline for: {url}")
        
        result = run_keyword_pipeline_v2(
            url=url,
            page_topic="",
            use_llm=True,
            use_advanced_ai=True,
            analyze_competitors=False,  # Single URL focus
            generate_optimization=True,
            save_to_db=True
        )
        
        if 'error' in result:
            logger.warning(f"[keyword_ai] Pipeline error: {result['error']}")
            return {'url': url, 'error': result['error']}
        
        logger.info(f"[keyword_ai] Pipeline complete: {len(result.get('keywords', []))} keywords")
        return result
        
    except Exception as e:
        logger.error(f"[keyword_ai] Pipeline failed: {e}")
        return {'url': url, 'error': str(e)}


def run_seo_metrics(url: str) -> Dict[str, Any]:
    """
    Fetch SEO Metrics from Moz API (Domain Authority, Page Authority, Backlinks).
    
    Args:
        url: URL to analyze
        
    Returns:
        Dictionary with DA, PA, backlink metrics
    """
    try:
        access_id = getattr(settings, 'MOZ_ACCESS_ID', '')
        secret_key = getattr(settings, 'MOZ_SECRET_KEY', '')
        
        if not access_id or not secret_key:
            logger.warning("[SEO Metrics] Moz API credentials not configured")
            return {
                'url': url,
                'error': 'Moz API credentials not configured',
                'domain_authority': None,
                'page_authority': None,
                'backlinks': {}
            }
        
        logger.info(f"[SEO Metrics] Fetching Moz metrics for: {url}")
        
        # Generate signature
        expires = str(int(time.time()) + 300)
        string_to_sign = f"{access_id}\n{expires}"
        binary_signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        safe_signature = quote(base64.b64encode(binary_signature))
        
        # Moz API columns (DA, PA, linking domains, external links, mozrank)
        cols = "103079233568"
        encoded_url = quote(url, safe='')
        api_url = (
            f"https://lsapi.seomoz.com/linkscape/url-metrics/{encoded_url}"
            f"?Cols={cols}&AccessID={access_id}&Expires={expires}&Signature={safe_signature}"
        )
        
        response = requests.get(api_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"[SEO Metrics] Moz API error: {response.status_code}")
            return {
                'url': url,
                'error': f'Moz API error: {response.status_code}',
                'domain_authority': None,
                'page_authority': None,
                'backlinks': {}
            }
        
        json_data = response.json()
        
        result = {
            'url': url,
            'domain_authority': round(json_data.get('pda', 0), 2),
            'page_authority': round(json_data.get('upa', 0), 2),
            'linking_root_domains': json_data.get('uid', 0),
            'total_backlinks': json_data.get('ueid', 0),
            'moz_rank': round(json_data.get('umrp', 0), 2),
            'backlinks': {
                'referring_domains': json_data.get('uid', 'N/A'),
                'total_backlinks': json_data.get('ueid', 'N/A'),
            }
        }
        
        logger.info(f"[SEO Metrics] DA={result['domain_authority']}, PA={result['page_authority']}")
        return result
        
    except Exception as e:
        logger.error(f"[SEO Metrics] Failed to fetch metrics: {e}")
        return {
            'url': url,
            'error': str(e),
            'domain_authority': None,
            'page_authority': None,
            'backlinks': {}
        }


def merge_analysis_data(
    seo_data: Dict,
    keyword_data: Dict,
    seo_metrics_data: Dict
) -> Dict[str, Any]:
    """
    Merge data from all 3 analysis sources into unified report structure.
    
    Args:
        seo_data: SEOAnalyzer audit results
        keyword_data: keyword_ai pipeline results
        seo_metrics_data: SEO metrics (DA, PA, backlinks) from Moz API
        
    Returns:
        Unified dictionary with all data for PDF generation
    """
    url = seo_data.get('url', keyword_data.get('url', seo_metrics_data.get('url', '')))
    
    merged = {
        # Basic info
        'url': url,
        'generated_at': datetime.now().isoformat(),
        
        # SEOAnalyzer Data (Traditional SEO)
        'seo': {
            'title': seo_data.get('title', ''),
            'title_score': seo_data.get('title_score', 0),
            'description': seo_data.get('desc', ''),
            'description_score': seo_data.get('desc_score', 0),
            'heading_structure': seo_data.get('H', 'None'),
            'heading_score': seo_data.get('heading_score', 0),
            'speed': seo_data.get('speed', 0),
            'internal_links': seo_data.get('internal_links', 0),
            'external_links': seo_data.get('external_links', 0),
            'broken_links': seo_data.get('b_links', 0),
            'images_without_alt': seo_data.get('alt_count', 0),
            'keywords': seo_data.get('lst', []),
            'keyword_density': seo_data.get('dens', []),
            
            # Technical flags
            'has_robots_txt': seo_data.get('robot_flag', False),
            'has_sitemap': seo_data.get('sitemap_flag', False),
            'has_schema': seo_data.get('schema_flag', False),
            'has_ogp': seo_data.get('ogp_flag', False),
            'has_favicon': seo_data.get('icon_flag', False),
            'has_analytics': seo_data.get('analytics_flag', False),
            'has_https': seo_data.get('https', False),
            'has_dmca': seo_data.get('dmca', False),
            
            # SSL info
            'ssl_name': seo_data.get('ssl_name', ''),
            'ssl_expiry': seo_data.get('ssl_expiry', ''),
            
            # Server info
            'server_ip': seo_data.get('ip', ''),
            'server_location': seo_data.get('loc_name', ''),
            'web_server': seo_data.get('webserver', ''),
            'w3c_errors': seo_data.get('error_len', 0),
            'w3c_warnings': seo_data.get('warn_len', 0),
            
            # Mobile
            'mobile_score': seo_data.get('mob_score', 0),
            'has_amp': seo_data.get('amp', False),
            'mobile_render': seo_data.get('render', False),
            
            # Social
            'social_score': seo_data.get('s_count', 0),
            'social_links': {
                'facebook': seo_data.get('facebook_flag', False),
                'instagram': seo_data.get('instagram_flag', False),
                'twitter': seo_data.get('twitter_flag', False),
                'linkedin': seo_data.get('linkedin_flag', False),
            }
        },
        
        # keyword_ai Data (AI-Powered)
        'keyword_ai': {
            'top_keywords': keyword_data.get('keywords', [])[:20] if 'keywords' in keyword_data else [],
            'keyword_clusters': keyword_data.get('keyword_clusters', {}),
            'intent_analysis': keyword_data.get('intent_analysis', {}),
            'search_intent': keyword_data.get('search_intent', ''),
            'content_quality': keyword_data.get('content_quality', {}),
            'semantic_keywords': keyword_data.get('semantic_keywords', []),
            'tfidf_keywords': keyword_data.get('tfidf_keywords', []),
            'optimization_suggestions': keyword_data.get('optimization_suggestions', []),
            'content_stats': {
                'word_count': keyword_data.get('word_count', 0),
                'readability_score': keyword_data.get('readability_score', 0),
                'quality_score': keyword_data.get('quality_score', 0),
            }
        },
        
        # SEO Metrics Data (Moz API - Domain Authority, Page Authority, Backlinks)
        'metrics': {
            # Authority from Moz API
            'domain_authority': seo_metrics_data.get('domain_authority'),
            'page_authority': seo_metrics_data.get('page_authority'),
            'moz_rank': seo_metrics_data.get('moz_rank'),
            'linking_root_domains': seo_metrics_data.get('linking_root_domains'),
            'total_backlinks': seo_metrics_data.get('total_backlinks'),
            'backlinks': seo_metrics_data.get('backlinks', {})
        }
    }
    
    logger.info(f"[MERGE] Data merged: {len(merged['seo'])} SEO metrics, "
                f"{len(merged['keyword_ai']['top_keywords'])} keywords, "
                f"DA={merged['metrics']['domain_authority']}")
    
    return merged


def generate_comprehensive_report_data(
    url: str,
    request=None,
    use_cache: bool = True,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Main orchestrator function - generates comprehensive report data.
    
    This is the primary entry point for the enhanced PDF report.
    
    Args:
        url: URL to analyze
        request: Optional Django request for user context
        use_cache: Whether to check/use cache (default: True)
        force_refresh: Whether to force fresh analysis (default: False)
        
    Returns:
        Dictionary with all merged analysis data
    """
    logger.info(f"=" * 60)
    logger.info(f"[ORCHESTRATOR] Generating comprehensive report for: {url}")
    logger.info(f"=" * 60)
    
    # Check cache first (if enabled and not forcing refresh)
    if use_cache and not force_refresh:
        cache_hit, cached_data = check_cached_report(url)
        if cache_hit:
            logger.info(f"[ORCHESTRATOR] Returning cached report")
            cached_data['from_cache'] = True
            return cached_data
    
    # Run all 3 analyzers
    logger.info(f"[ORCHESTRATOR] Running all 3 analyzers...")
    
    seo_data = run_seoanalyzer_audit(url, request)
    keyword_data = run_keyword_ai_analysis(url)
    seo_metrics_data = run_seo_metrics(url)
    
    # Merge data
    merged_data = merge_analysis_data(seo_data, keyword_data, seo_metrics_data)
    
    # Add metadata
    merged_data['from_cache'] = False
    merged_data['analysis_sources'] = {
        'seoanalyzer': 'success' if 'error' not in seo_data else 'failed',
        'keyword_ai': 'success' if 'error' not in keyword_data else 'failed',
        'seo_metrics': 'success' if 'error' not in seo_metrics_data else 'failed',
    }
    
    # Cache the result
    if use_cache:
        cache_report_data(url, merged_data)
    
    logger.info(f"[ORCHESTRATOR] Report generation complete")
    logger.info(f"=" * 60)
    
    return merged_data


def clear_report_cache(url: str) -> bool:
    """Clear cached report for a specific URL."""
    cache_key = get_cache_key(url)
    cache.delete(cache_key)
    logger.info(f"[CACHE CLEAR] Report for {url}")
    return True
