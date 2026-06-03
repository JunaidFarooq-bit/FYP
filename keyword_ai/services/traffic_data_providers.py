"""
Traffic Data Providers — Real Keyword Volume & Competition Data

Integrates with multiple keyword research APIs to fetch actual:
- Monthly search volume (exact numbers)
- Keyword difficulty scores (0-100)
- CPC (cost-per-click) data
- Competition level
- Trend data

Supported providers (in priority order):
1. SEMrush API (most comprehensive)
2. Ahrefs API (best for SEO metrics)
3. DataForSEO (pay-as-you-go, good for startups)
4. Serpstat API (affordable option)
5. Google Keyword Planner (free but complex setup)

Fallback: Intelligent estimation when no APIs configured
"""

import os
import logging
import requests
import time
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class KeywordMetrics:
    """Real keyword metrics from data providers."""
    keyword: str
    
    # Volume data
    monthly_volume: Optional[int] = None
    volume_range_low: Optional[int] = None
    volume_range_high: Optional[int] = None
    
    # Competition & CPC
    keyword_difficulty: Optional[int] = None  # 0-100
    cpc: Optional[float] = None  # Cost per click in USD
    competition_level: Optional[str] = None  # Low/Medium/High
    competition_index: Optional[float] = None  # 0-1 scale
    
    # Trend data
    trend_direction: Optional[str] = None  # Rising/Falling/Stable
    trend_percentage: Optional[float] = None  # % change
    
    # SERP features
    serp_features: List[str] = None
    
    # Metadata
    data_source: str = "estimated"
    last_updated: str = None
    
    def __post_init__(self):
        if self.serp_features is None:
            self.serp_features = []
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'keyword': self.keyword,
            'monthly_volume': self.monthly_volume,
            'volume_range': f"{self.volume_range_low:,}-{self.volume_range_high:,}" if self.volume_range_low and self.volume_range_high else None,
            'keyword_difficulty': self.keyword_difficulty,
            'cpc': f"${self.cpc:.2f}" if self.cpc else None,
            'competition_level': self.competition_level,
            'trend_direction': self.trend_direction,
            'trend_percentage': f"{self.trend_percentage:+.1f}%" if self.trend_percentage else None,
            'serp_features': self.serp_features,
            'data_source': self.data_source,
        }


class SEMrushProvider:
    """SEMrush API integration for keyword data."""
    
    BASE_URL = "https://api.semrush.com/"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'SEMRUSH_API_KEY', os.getenv('SEMRUSH_API_KEY', ''))
        self.enabled = bool(self.api_key)
    
    def get_keyword_metrics(self, keyword: str, database: str = 'us') -> Optional[KeywordMetrics]:
        """Fetch keyword metrics from SEMrush."""
        if not self.enabled:
            return None
        
        try:
            params = {
                'type': 'phrase_this',
                'key': self.api_key,
                'phrase': keyword,
                'database': database,
                'export_columns': 'Ph,Nq,Cp,Co,Nr,Td',
            }
            
            response = requests.get(
                f"{self.BASE_URL}/",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse CSV response
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return None
            
            # Header: Keyword;Search Volume;CPC;Competition;Number of Results;Trends
            # Data: keyword;1234;1.23;0.45;1234567;0.12,0.15,0.18
            data_line = lines[1]
            parts = data_line.split(';')
            
            if len(parts) >= 5:
                return KeywordMetrics(
                    keyword=keyword,
                    monthly_volume=int(parts[1]) if parts[1].isdigit() else None,
                    cpc=float(parts[2]) if parts[2] else None,
                    competition_index=float(parts[3]) if parts[3] else None,
                    competition_level=self._index_to_level(parts[3]),
                    trend_direction=self._parse_trend(parts[5]) if len(parts) > 5 else None,
                    data_source='semrush'
                )
            
        except Exception as e:
            logger.warning(f"SEMrush API error for '{keyword}': {e}")
        
        return None
    
    def _index_to_level(self, index: str) -> str:
        """Convert competition index to level."""
        try:
            val = float(index)
            if val < 0.3:
                return 'Low'
            elif val < 0.6:
                return 'Medium'
            else:
                return 'High'
        except:
            return 'Unknown'
    
    def _parse_trend(self, trend_str: str) -> str:
        """Parse trend data from SEMrush."""
        try:
            trends = [float(x) for x in trend_str.split(',')]
            if len(trends) >= 2 and trends[0] != 0:
                change = ((trends[-1] - trends[0]) / trends[0]) * 100
                if change > 10:
                    return 'Rising'
                elif change < -10:
                    return 'Falling'
        except:
            pass
        return 'Stable'
    
    def get_bulk_metrics(self, keywords: List[str], database: str = 'us') -> Dict[str, KeywordMetrics]:
        """Fetch metrics for multiple keywords (SEMrush supports bulk)."""
        if not self.enabled or not keywords:
            return {}
        
        results = {}
        
        # SEMrush supports up to 100 keywords per request
        for i in range(0, len(keywords), 100):
            batch = keywords[i:i+100]
            
            try:
                params = {
                    'type': 'phrase_this',
                    'key': self.api_key,
                    'phrase': ','.join(batch),
                    'database': database,
                    'export_columns': 'Ph,Nq,Cp,Co,Nr,Td',
                }
                
                response = requests.get(
                    f"{self.BASE_URL}/",
                    params=params,
                    timeout=60
                )
                response.raise_for_status()
                
                # Parse CSV
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split(';')
                        if len(parts) >= 5:
                            kw = parts[0]
                            results[kw] = KeywordMetrics(
                                keyword=kw,
                                monthly_volume=int(parts[1]) if parts[1].isdigit() else None,
                                cpc=float(parts[2]) if parts[2] else None,
                                competition_index=float(parts[3]) if parts[3] else None,
                                competition_level=self._index_to_level(parts[3]),
                                data_source='semrush'
                            )
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"SEMrush bulk API error: {e}")
        
        return results


class DataForSEOProvider:
    """DataForSEO API integration — pay-as-you-go keyword data."""
    
    BASE_URL = "https://api.dataforseo.com/v3"
    
    def __init__(self, login: str = None, password: str = None):
        self.login = login or getattr(settings, 'DATAFORSEO_LOGIN', os.getenv('DATAFORSEO_LOGIN', ''))
        self.password = password or getattr(settings, 'DATAFORSEO_PASSWORD', os.getenv('DATAFORSEO_PASSWORD', ''))
        self.enabled = bool(self.login and self.password)
    
    def get_keyword_metrics(self, keyword: str, location_code: int = 2840, language_code: str = 'en') -> Optional[KeywordMetrics]:
        """Fetch keyword metrics from DataForSEO."""
        if not self.enabled:
            return None
        
        try:
            payload = [{
                'keywords': [keyword],
                'location_code': location_code,
                'language_code': language_code,
            }]
            
            response = requests.post(
                f"{self.BASE_URL}/keywords_data/google/search_volume/task_post",
                auth=(self.login, self.password),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('tasks') and data['tasks'][0].get('result'):
                result = data['tasks'][0]['result'][0]
                
                return KeywordMetrics(
                    keyword=keyword,
                    monthly_volume=result.get('search_volume'),
                    cpc=result.get('cpc'),
                    competition_index=result.get('competition'),
                    competition_level=self._index_to_level(result.get('competition')),
                    data_source='dataforseo'
                )
            
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                raise  # Let aggregator circuit-breaker handle auth failures
            logger.warning(f"DataForSEO API error for '{keyword}': {e}")

        return None

    def _index_to_level(self, index: float) -> str:
        """Convert competition index to level."""
        if index is None:
            return 'Unknown'
        if index < 0.3:
            return 'Low'
        elif index < 0.6:
            return 'Medium'
        else:
            return 'High'


class SerpstatProvider:
    """Serpstat API integration — affordable keyword data."""
    
    BASE_URL = "https://api.serpstat.com/v4"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'SERPSTAT_API_KEY', os.getenv('SERPSTAT_API_KEY', ''))
        self.enabled = bool(self.api_key)
    
    def get_keyword_metrics(self, keyword: str, se: str = 'g_us') -> Optional[KeywordMetrics]:
        """Fetch keyword metrics from Serpstat."""
        if not self.enabled:
            return None
        
        try:
            headers = {
                'Authorization': f'Token {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'method': 'SerpstatKeywordProcedure.getKeywordData',
                'params': {
                    'keyword': keyword,
                    'se': se,
                }
            }
            
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            result = data.get('result', {}).get('data', {})
            
            if result:
                return KeywordMetrics(
                    keyword=keyword,
                    monthly_volume=result.get('volume'),
                    keyword_difficulty=result.get('difficulty'),
                    cpc=result.get('cpc'),
                    competition_level=result.get('competition'),
                    data_source='serpstat'
                )
            
        except Exception as e:
            logger.warning(f"Serpstat API error for '{keyword}': {e}")
        
        return None


class SerpAPIProvider:
    """
    SerpAPI integration for live SERP data.

    Provides real:
    - AI Overview / SGE presence per keyword
    - SERP features (featured snippet, PAA, shopping, etc.)
    - Organic result count
    - Related searches

    Cost: ~$0.005 per search (50,000 free/mo on free plan).
    Sign up: https://serpapi.com
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'SERPAPI_KEY', os.getenv('SERPAPI_KEY', ''))
        self.enabled = bool(self.api_key)

    def get_serp_features(self, keyword: str, location: str = "United States", hl: str = "en") -> Optional[Dict]:
        """
        Fetch live SERP data for a keyword.

        Returns dict with:
            has_ai_overview  bool
            has_featured_snippet  bool
            has_people_also_ask   bool
            serp_features         List[str]
            organic_results_count int
            related_searches      List[str]
        """
        if not self.enabled:
            return None

        try:
            params = {
                "engine": "google",
                "q": keyword,
                "location": location,
                "hl": hl,
                "gl": "us",
                "api_key": self.api_key,
                "num": 10,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            features: List[str] = []
            has_ai_overview = bool(data.get("ai_overview"))
            has_featured_snippet = bool(data.get("answer_box") or data.get("featured_snippet"))
            has_paa = bool(data.get("related_questions"))

            if has_ai_overview:
                features.append("ai_overview")
            if has_featured_snippet:
                features.append("featured_snippet")
            if has_paa:
                features.append("people_also_ask")
            if data.get("shopping_results"):
                features.append("shopping")
            if data.get("knowledge_graph"):
                features.append("knowledge_graph")
            if data.get("local_results"):
                features.append("local_pack")
            if data.get("news_results"):
                features.append("news")

            related = [r.get("query", "") for r in (data.get("related_searches") or [])[:5]]

            return {
                "has_ai_overview": has_ai_overview,
                "has_featured_snippet": has_featured_snippet,
                "has_people_also_ask": has_paa,
                "serp_features": features,
                "organic_results_count": len(data.get("organic_results") or []),
                "related_searches": related,
                "data_source": "serpapi",
            }

        except Exception as exc:
            logger.warning("SerpAPI error for '%s': %s", keyword, exc)
            return None

    def get_bulk_serp_features(self, keywords: List[str], location: str = "United States") -> Dict[str, Dict]:
        """Fetch SERP features for a list of keywords."""
        results = {}
        for kw in keywords:
            data = self.get_serp_features(kw, location=location)
            if data:
                results[kw] = data
            time.sleep(0.3)  # SerpAPI rate limit
        return results


class KeywordDataAggregator:
    """
    Aggregates keyword data from multiple providers.
    
    Falls back through providers in priority order:
    1. SEMrush (most data)
    2. DataForSEO (affordable)
    3. Serpstat (backup)
    4. Estimation (always available)
    """
    
    def __init__(self):
        self.providers = [
            SEMrushProvider(),
            DataForSEOProvider(),
            SerpstatProvider(),
        ]
        self.enabled_providers = [p for p in self.providers if p.enabled]
        self.serp_provider = SerpAPIProvider()

        if self.enabled_providers:
            logger.info(f"Keyword data providers active: {[p.__class__.__name__ for p in self.enabled_providers]}")
        else:
            logger.warning("No keyword data API keys configured. Using estimation only.")
        if self.serp_provider.enabled:
            logger.info("SerpAPI provider active — real SGE/SERP feature detection enabled")
    
    def get_keyword_metrics(self, keyword: str) -> KeywordMetrics:
        """
        Get best available metrics for a keyword.
        
        Tries each provider in order until one succeeds.
        Falls back to estimation if all APIs fail.
        """
        # Try real data providers first
        for provider in list(self.enabled_providers):
            try:
                metrics = provider.get_keyword_metrics(keyword)
                if metrics and metrics.monthly_volume:
                    logger.debug(f"Got real data for '{keyword}' from {provider.__class__.__name__}")
                    return metrics
            except Exception as e:
                err_str = str(e)
                if "401" in err_str or "Unauthorized" in err_str:
                    logger.warning(
                        f"{provider.__class__.__name__} returned 401 Unauthorized — "
                        "removing from active providers. Check credentials in .env"
                    )
                    self.enabled_providers = [p for p in self.enabled_providers if p is not provider]
                else:
                    logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                continue

        # Fallback to estimation
        return self._estimate_metrics(keyword)
    
    def get_bulk_metrics(self, keywords: List[str]) -> Dict[str, KeywordMetrics]:
        """
        Get metrics for multiple keywords efficiently.
        
        Uses bulk APIs when available, falls back to individual requests.
        """
        results = {}
        remaining = keywords.copy()
        
        # Try bulk methods first
        for provider in self.enabled_providers:
            if hasattr(provider, 'get_bulk_metrics') and remaining:
                try:
                    bulk_results = provider.get_bulk_metrics(remaining)
                    for kw, metrics in bulk_results.items():
                        if metrics and metrics.monthly_volume:
                            results[kw] = metrics
                            remaining.remove(kw)
                except Exception as e:
                    logger.warning(f"Bulk fetch from {provider.__class__.__name__} failed: {e}")
        
        # Individual fallback for remaining keywords.
        # Probe with the first keyword — if it returns an auth error (401),
        # skip all remaining calls and fall straight to estimation to avoid
        # hammering the API with 30 sequential failing requests.
        auth_failed = False
        for keyword in remaining:
            if auth_failed:
                results[keyword] = self._estimate_metrics(keyword)
                continue
            try:
                metrics = self.get_keyword_metrics(keyword)
                results[keyword] = metrics
            except Exception as exc:
                if "401" in str(exc) or "Unauthorized" in str(exc):
                    auth_failed = True
                    logger.warning(
                        "DataForSEO 401 Unauthorized — disabling provider for this session. "
                        "Check DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in .env"
                    )
                    # Disable all providers so future calls skip straight to estimation
                    self.enabled_providers = []
                results[keyword] = self._estimate_metrics(keyword)

        return results
    
    def _estimate_metrics(self, keyword: str) -> KeywordMetrics:
        """Estimate metrics when no real data available."""
        # Use the same estimation logic from traffic_enrichment.py
        words = keyword.split()
        word_count = len(words)
        
        # Estimate volume based on keyword length
        if word_count >= 5:
            volume_low, volume_high = 10, 500
        elif word_count == 4:
            volume_low, volume_high = 100, 1000
        elif word_count == 3:
            volume_low, volume_high = 500, 5000
        else:
            volume_low, volume_high = 2000, 20000
        
        # Detect commercial intent for CPC estimation
        keyword_lower = keyword.lower()
        commercial_terms = ['buy', 'price', 'cost', 'software', 'tool', 'service', 'best', 'top']
        has_commercial = any(term in keyword_lower for term in commercial_terms)
        
        estimated_cpc = 2.5 if has_commercial else 0.8
        
        # Estimate difficulty
        difficulty = min(100, word_count * 15 + (30 if has_commercial else 0))
        
        return KeywordMetrics(
            keyword=keyword,
            monthly_volume=(volume_low + volume_high) // 2,
            volume_range_low=volume_low,
            volume_range_high=volume_high,
            cpc=estimated_cpc,
            keyword_difficulty=difficulty,
            competition_level='Medium' if has_commercial else 'Low',
            data_source='estimated'
        )
    
    def get_serp_features_bulk(self, keywords: List[str], location: str = "United States") -> Dict[str, Dict]:
        """
        Fetch real SERP features (AI Overview, featured snippet, PAA) for
        a list of keywords via SerpAPI.

        Returns empty dict if SerpAPI key not configured.
        """
        if not self.serp_provider.enabled:
            return {}
        return self.serp_provider.get_bulk_serp_features(keywords, location=location)

    def get_provider_status(self) -> Dict[str, bool]:
        """Get status of all providers."""
        return {
            'semrush': SEMrushProvider().enabled,
            'dataforseo': DataForSEOProvider().enabled,
            'serpstat': SerpstatProvider().enabled,
            'serpapi': self.serp_provider.enabled,
            'any_enabled': len(self.enabled_providers) > 0
        }


# Convenience functions for external use
def get_keyword_volume(keyword: str) -> Optional[int]:
    """Get monthly search volume for a single keyword."""
    aggregator = KeywordDataAggregator()
    metrics = aggregator.get_keyword_metrics(keyword)
    return metrics.monthly_volume


def get_bulk_volumes(keywords: List[str]) -> Dict[str, Optional[int]]:
    """Get monthly search volumes for multiple keywords."""
    aggregator = KeywordDataAggregator()
    metrics = aggregator.get_bulk_metrics(keywords)
    return {kw: m.monthly_volume for kw, m in metrics.items()}


def check_provider_status() -> Dict:
    """Check which keyword data providers are configured."""
    aggregator = KeywordDataAggregator()
    return aggregator.get_provider_status()
