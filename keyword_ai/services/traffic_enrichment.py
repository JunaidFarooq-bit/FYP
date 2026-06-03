"""
Traffic Enrichment Layer (Phase 2.5) — Real-Time Traffic Signals

Fetches real-time traffic signals for ML-generated keywords using:
- Google Trends (Free via pytrends)
- Estimated metrics calculation based on keyword characteristics

Integrates between Phase 2 (ML) and Phase 3 (RAG) in pipeline_v2.py
to provide traffic-first keyword prioritization.
"""

import logging
import random
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
import re

from .traffic_data_providers import KeywordDataAggregator, KeywordMetrics
from keyword_ai.utils.intent_detection import (
    TRANSACTIONAL_INDICATORS,
    COMMERCIAL_INDICATORS,
    has_question_intent,
    has_commercial_intent,
)

logger = logging.getLogger(__name__)

# Fallback SOCS value used when live fetch fails.
# This encodes: consent accepted, language=en.
# Update periodically if live fetch is consistently unavailable.
_SOCS_FALLBACK = "CAESEwgDEgk0OTM5NTk1NDICD2VuIAEaBgiA5OymBg"


def _fetch_socs_cookie() -> str:
    """
    Fetch a fresh SOCS consent cookie from google.com.

    Google's GDPR consent gate redirects pytrends requests to /sorry/index
    with a 429 when no valid SOCS cookie is present. This fetches a real
    cookie from the consent endpoint at startup.

    Returns the SOCS cookie value, or the hardcoded fallback on failure.
    """
    try:
        import requests as _req
        resp = _req.get(
            "https://consent.google.com/save",
            params={
                "continue": "https://trends.google.com/",
                "gl": "US",
                "m": "0",
                "pc": "trender",
                "x": "6",
                "src": "2",
                "hl": "en",
                "set_eom": "false",
                "set_sc": "true",
                "set_aps": "true",
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            timeout=8,
            allow_redirects=True,
        )
        socs = resp.cookies.get("SOCS")
        if socs:
            logger.info("Fetched fresh SOCS cookie from Google consent endpoint")
            return socs
    except Exception as exc:
        logger.debug("Could not fetch fresh SOCS cookie (%s), using fallback", exc)
    return _SOCS_FALLBACK


@dataclass
class TrafficSignals:
    """Traffic signal data structure for a keyword."""
    keyword: str

    # Tier 1: Trend Status
    trend_status: str = "➡️ STABLE"  # 🔥 TRENDING NOW | 📈 RISING | ➡️ STABLE | 📉 DECLINING
    trend_score: float = 50.0  # 0-100 scale

    # Tier 2: Traffic Opportunity
    # NEW: Actual numbers from data providers
    monthly_volume: Optional[int] = None  # Exact monthly searches
    volume_display: str = ""  # Formatted for display (e.g., "12,500/mo")
    volume_range: str = ""  # Range if exact not available (e.g., "10K-100K")
    
    # Legacy categories (for backward compatibility)
    estimated_volume: str = "Medium"  # Very High | High | Medium | Low | Very Low
    
    traffic_velocity: str = "Moderate"  # Viral | Fast | Moderate | Slow
    keyword_difficulty: str = "Medium"  # Very Hard | Hard | Medium | Easy
    difficulty_score: Optional[int] = None  # 0-100 exact score
    
    cpc_signal: str = "Medium"  # Very High | High | Medium | Low
    cpc_value: Optional[float] = None  # Actual CPC in USD
    
    competition_level: str = "Medium"  # Low | Medium | High
    competition_index: Optional[float] = None  # 0-1 exact

    # Tier 3: Strategic Fit
    intent: str = "Informational"  # Informational | Commercial | Transactional | Navigational
    serp_opportunities: List[str] = field(default_factory=list)
    content_type: str = "Blog"  # Blog | Landing Page | Product Page | FAQ | Comparison
    funnel_stage: str = "Awareness"  # Awareness | Consideration | Decision

    # Meta
    priority_score: float = 0.0
    traffic_score: float = 0.0  # Combined score 0-100
    data_source: str = "estimated"
    last_updated: str = None
    provider_used: str = ""  # Which API provided the data

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        # Add computed display fields
        if self.monthly_volume:
            data['volume_display'] = f"{self.monthly_volume:,}/mo"
            data['traffic_potential'] = self._calculate_traffic_potential()
        return data
    
    def _calculate_traffic_potential(self) -> str:
        """Calculate potential monthly traffic if ranked #1."""
        if not self.monthly_volume:
            return "Unknown"
        # #1 ranking typically gets ~30% CTR
        potential = int(self.monthly_volume * 0.30)
        return f"~{potential:,}/mo"


class TrafficEnricher:
    """
    Enriches keywords with real-time traffic signals.
    
    Uses Google Trends when available, falls back to intelligent estimation
    based on keyword characteristics and market patterns.
    """
    
    def __init__(self, use_google_trends: bool = True, cache_ttl_minutes: int = 60, use_real_data: bool = True, use_llm_estimation: bool = True):
        self.use_google_trends = use_google_trends
        self.use_real_data = use_real_data
        self.use_llm_estimation = use_llm_estimation
        self.cache_ttl = cache_ttl_minutes
        self._cache: Dict[str, Tuple[TrafficSignals, datetime]] = {}
        self._pytrends = None
        self._pytrends_initialized = False
        
        # Initialize real data provider
        self.data_aggregator = KeywordDataAggregator() if use_real_data else None
    
    def _ensure_pytrends(self):
        """Lazy-initialize the pytrends client on first actual use."""
        if self._pytrends_initialized:
            return
        self._pytrends_initialized = True
        
        if not self.use_google_trends:
            return
        
        try:
            from pytrends.request import TrendReq

            _ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
            self._pytrends = TrendReq(
                hl='en-US',
                tz=360,
                retries=0,
                backoff_factor=0,
                timeout=(15, 40),
                requests_args={
                    "headers": {"User-Agent": _ua, "Accept-Language": "en-US,en;q=0.9"},
                    "verify": True,
                },
            )
            self._pytrends.cookies["SOCS"] = _fetch_socs_cookie()
            logger.info("Google Trends client initialized (lazy)")
        except ImportError:
            logger.warning("pytrends not installed, using estimation only")
            self._pytrends = None
        except Exception as e:
            logger.warning(f"Failed to initialize Google Trends: {e}")
            self._pytrends = None
    
    def _get_cached(self, keyword: str) -> Optional[TrafficSignals]:
        """Get cached traffic signals if still valid."""
        if keyword in self._cache:
            signals, cached_time = self._cache[keyword]
            if datetime.now() - cached_time < timedelta(minutes=self.cache_ttl):
                return signals
        return None
    
    def _cache_signals(self, keyword: str, signals: TrafficSignals):
        """Cache traffic signals with timestamp."""
        self._cache[keyword] = (signals, datetime.now())
    
    def _fetch_google_trends(self, keywords: List[str]) -> Dict[str, float]:
        """
        Fetch trend scores from Google Trends.
        
        Returns:
            Dict mapping keyword to trend score (0-100)
        """
        self._ensure_pytrends()
        if not self._pytrends or not keywords:
            return {}
        
        try:
            # Google Trends accepts max 5 keywords per request
            results = {}
            consecutive_failures = 0
            
            for i in range(0, len(keywords), 5):
                # Circuit-breaker: abort on 2 consecutive failures to avoid
                # hammering the API after a 429 rate-limit response
                if consecutive_failures >= 2:
                    logger.warning(
                        "Google Trends circuit-breaker triggered after %d consecutive "
                        "failures — skipping remaining %d keywords",
                        consecutive_failures,
                        len(keywords) - i,
                    )
                    self._pytrends = None  # Disable for this enricher instance
                    break

                batch = keywords[i:i+5]
                
                try:
                    self._pytrends.build_payload(
                        batch,
                        cat=0,
                        timeframe='now 7-d',  # Last 7 days
                        geo='',
                        gprop=''
                    )
                    
                    # Get interest over time
                    trend_data = self._pytrends.interest_over_time()
                    
                    if not trend_data.empty:
                        # Calculate trend score: recent average + trend direction
                        for keyword in batch:
                            if keyword in trend_data.columns:
                                values = trend_data[keyword].values
                                if len(values) > 0:
                                    # Score based on recent interest
                                    recent_avg = values[-3:].mean() if len(values) >= 3 else values.mean()
                                    trend_direction = (values[-1] - values[0]) / max(values[0], 1) * 20
                                    score = min(100, max(0, recent_avg + trend_direction))
                                    results[keyword] = score
                    
                    consecutive_failures = 0  # Reset on success
                    # Randomized delay 2-4s — avoids bot-pattern detection
                    time.sleep(random.uniform(2.0, 4.0))
                    
                except Exception as e:
                    consecutive_failures += 1
                    logger.warning(f"Google Trends batch error: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Google Trends fetch failed: {e}")
            return {}
    
    def _get_real_metrics(self, keyword: str) -> Optional[KeywordMetrics]:
        """Fetch real metrics from data providers."""
        if not self.data_aggregator:
            return None
        return self.data_aggregator.get_keyword_metrics(keyword)

    def _estimate_from_keyword(self, keyword: str, real_metrics: Optional[KeywordMetrics] = None) -> TrafficSignals:
        """
        Build traffic signals from real data or estimation.
        
        Priority:
        1. Use real metrics from API if available
        2. Fall back to intelligent estimation
        """
        keyword_lower = keyword.lower()
        words = keyword.split()
        word_count = len(words)
        
        # Base signals
        signals = TrafficSignals(keyword=keyword)
        
        # ===== USE REAL DATA IF AVAILABLE =====
        if real_metrics and real_metrics.monthly_volume:
            signals.monthly_volume = real_metrics.monthly_volume
            signals.volume_range = real_metrics.volume_range if hasattr(real_metrics, 'volume_range') else ""
            signals.difficulty_score = real_metrics.keyword_difficulty
            signals.cpc_value = real_metrics.cpc
            signals.competition_index = real_metrics.competition_index
            signals.competition_level = real_metrics.competition_level or "Medium"
            signals.data_source = real_metrics.data_source
            signals.provider_used = real_metrics.data_source
            
            # Map real volume to category for compatibility
            vol = real_metrics.monthly_volume
            if vol >= 100000:
                signals.estimated_volume = "Very High"
            elif vol >= 10000:
                signals.estimated_volume = "High"
            elif vol >= 1000:
                signals.estimated_volume = "Medium"
            elif vol >= 100:
                signals.estimated_volume = "Low"
            else:
                signals.estimated_volume = "Very Low"
            
            # Use real difficulty if available
            if real_metrics.keyword_difficulty is not None:
                diff = real_metrics.keyword_difficulty
                signals.keyword_difficulty = "Easy" if diff < 30 else "Medium" if diff < 60 else "Hard" if diff < 80 else "Very Hard"
            
            # Use real CPC for signal
            if real_metrics.cpc:
                cpc = real_metrics.cpc
                signals.cpc_signal = "Low" if cpc < 1 else "Medium" if cpc < 3 else "High" if cpc < 5 else "Very High"
        
        elif self.use_llm_estimation:
            # ===== FALLBACK: Use LLM for intelligent estimation =====
            signals.data_source = "llm_estimated"
            logger.info(f"[TRAFFIC-LlM] No real data for '{keyword}' - using LLM estimation")
            try:
                from .llm_traffic_estimator import estimate_keyword_traffic_llm
                llm_estimate = estimate_keyword_traffic_llm(keyword, page_topic="", target_region="GLOBAL")
                
                signals.monthly_volume = llm_estimate.monthly_volume
                signals.difficulty_score = llm_estimate.keyword_difficulty
                signals.cpc_value = llm_estimate.cpc_usd
                signals.competition_level = llm_estimate.competition_level
                signals.intent = llm_estimate.search_intent.capitalize()
                
                logger.info(f"[TRAFFIC-LlM] '{keyword}': vol={llm_estimate.monthly_volume}, cpc=${llm_estimate.cpc_usd}, diff={llm_estimate.keyword_difficulty}, conf={llm_estimate.volume_confidence}")
                
                # Map volume to category
                vol = llm_estimate.monthly_volume
                if vol >= 100000:
                    signals.estimated_volume = "Very High"
                    signals.volume_range = "50K-500K"
                elif vol >= 10000:
                    signals.estimated_volume = "High"
                    signals.volume_range = "5K-50K"
                elif vol >= 1000:
                    signals.estimated_volume = "Medium"
                    signals.volume_range = "500-5K"
                elif vol >= 100:
                    signals.estimated_volume = "Low"
                    signals.volume_range = "10-500"
                else:
                    signals.estimated_volume = "Very Low"
                    signals.volume_range = "<10"
                    
                # Map CPC to signal
                cpc = llm_estimate.cpc_usd
                signals.cpc_signal = "Low" if cpc < 1 else "Medium" if cpc < 3 else "High" if cpc < 5 else "Very High"
                
            except Exception as e:
                logger.warning(f"LLM traffic estimation failed for '{keyword}', using heuristic fallback: {e}")
                # ===== LAST RESORT: Heuristic based on keyword length =====
                signals.data_source = "estimated_heuristic"
                if word_count >= 5:
                    signals.estimated_volume = "Low"
                    signals.volume_range = "10-500"
                    signals.monthly_volume = 100
                elif word_count == 4:
                    signals.estimated_volume = "Medium"
                    signals.volume_range = "500-5K"
                    signals.monthly_volume = 1000
                elif word_count == 3:
                    signals.estimated_volume = "High"
                    signals.volume_range = "5K-50K"
                    signals.monthly_volume = 10000
                else:
                    signals.estimated_volume = "Very High"
                    signals.volume_range = "50K-500K"
                    signals.monthly_volume = 100000
        else:
            # ===== FALLBACK: Heuristic based on keyword length =====
            signals.data_source = "estimated_heuristic"
            logger.info(f"[TRAFFIC-HEURISTIC] '{keyword}' - using word-count heuristic (LLM disabled or failed)")
            if word_count >= 5:
                signals.estimated_volume = "Low"
                signals.volume_range = "10-500"
                signals.monthly_volume = 100
            elif word_count == 4:
                signals.estimated_volume = "Medium"
                signals.volume_range = "500-5K"
                signals.monthly_volume = 1000
            elif word_count == 3:
                signals.estimated_volume = "High"
                signals.volume_range = "5K-50K"
                signals.monthly_volume = 10000
            else:
                signals.estimated_volume = "Very High"
                signals.volume_range = "50K-500K"
                signals.monthly_volume = 100000
        
        # Adjust for question keywords (typically lower volume but high intent)
        if has_question_intent(keyword):
            signals.estimated_volume = "Medium" if signals.estimated_volume == "Very High" else "Low"
            signals.intent = "Informational"
            signals.serp_opportunities.append("people_also_ask")
            signals.serp_opportunities.append("featured_snippet")
            signals.content_type = "FAQ"
        
        # ===== DETECT COMMERCIAL INTENT (using shared indicators) =====
        if any(ind in keyword_lower for ind in TRANSACTIONAL_INDICATORS):
            signals.intent = "Transactional"
            signals.cpc_signal = "High"
            signals.content_type = "Product Page"
            signals.funnel_stage = "Decision"
            signals.serp_opportunities.append("shopping_ads")
        elif any(ind in keyword_lower for ind in COMMERCIAL_INDICATORS):
            signals.intent = "Commercial"
            signals.cpc_signal = "High"
            signals.content_type = "Landing Page"
            signals.funnel_stage = "Consideration"
            signals.serp_opportunities.append("featured_snippet")
        
        # ===== ESTIMATE KEYWORD DIFFICULTY =====
        # Based on length, commercial terms, and competition indicators
        difficulty_score = 0
        
        if word_count <= 2:
            difficulty_score += 40  # Head terms are hard
        elif word_count == 3:
            difficulty_score += 25
        elif word_count >= 5:
            difficulty_score += 10  # Long-tail is easier
        
        if signals.intent in ["Transactional", "Commercial"]:
            difficulty_score += 20  # Money keywords are competitive
        
        if any(ind in keyword_lower for ind in ['best', 'top', 'review']):
            difficulty_score += 15
        
        if difficulty_score >= 70:
            signals.keyword_difficulty = "Very Hard"
        elif difficulty_score >= 50:
            signals.keyword_difficulty = "Hard"
        elif difficulty_score >= 30:
            signals.keyword_difficulty = "Medium"
        else:
            signals.keyword_difficulty = "Easy"
        
        # ===== DETECT SEASONAL/TRENDING PATTERNS =====
        seasonal_keywords = {
            'christmas': 12, 'holiday': 12, 'black friday': 11, 'cyber monday': 11,
            'new year': 1, 'valentine': 2, 'easter': 4, 'summer': 6,
            'back to school': 8, 'halloween': 10, 'thanksgiving': 11,
            'winter': 12, 'spring': 3, 'autumn': 9, 'fall': 9
        }
        
        current_month = datetime.now().month
        for season, month in seasonal_keywords.items():
            if season in keyword_lower:
                month_diff = abs(current_month - month)
                if month_diff <= 1:
                    signals.trend_status = "🔥 TRENDING NOW"
                    signals.trend_score = 90.0
                    signals.traffic_velocity = "Fast"
                elif month_diff <= 2:
                    signals.trend_status = "📈 RISING"
                    signals.trend_score = 70.0
                    signals.traffic_velocity = "Moderate"
                else:
                    signals.trend_status = "📉 DECLINING"
                    signals.trend_score = 30.0
                break
        
        # ===== DETECT TECH TRENDS (2024-2025) =====
        trending_tech = [
            'ai', 'artificial intelligence', 'chatgpt', 'llm', 'machine learning',
            'automation', 'n8n', 'make.com', 'zapier', 'workflow automation',
            'seo ai', 'ai content', 'ai tools', 'ai marketing'
        ]
        if any(trend in keyword_lower for trend in trending_tech):
            signals.trend_status = "🔥 TRENDING NOW"
            signals.trend_score = 95.0
            signals.traffic_velocity = "Fast"
            signals.estimated_volume = "Very High" if signals.estimated_volume == "High" else signals.estimated_volume
        
        # ===== CALCULATE PRIORITY SCORE =====
        # Weighted combination: Traffic potential (40%), Trend momentum (35%), Strategic fit (25%)
        volume_scores = {"Very Low": 10, "Low": 25, "Medium": 50, "High": 75, "Very High": 100}
        difficulty_scores = {"Easy": 100, "Medium": 70, "Hard": 40, "Very Hard": 20}
        cpc_scores = {"Low": 25, "Medium": 50, "High": 80, "Very High": 100}
        
        traffic_score = (
            volume_scores.get(signals.estimated_volume, 50) * 0.4 +
            difficulty_scores.get(signals.keyword_difficulty, 50) * 0.3 +
            cpc_scores.get(signals.cpc_signal, 50) * 0.3
        )
        
        priority_score = (
            signals.trend_score * 0.35 +
            traffic_score * 0.40 +
            (100 if signals.intent in ["Transactional", "Commercial"] else 60) * 0.25
        )
        
        signals.traffic_score = round(traffic_score, 1)
        signals.priority_score = round(priority_score, 1)
        
        return signals
    
    def enrich_keywords(
        self,
        keywords: List[str],
        page_topic: str = "",
        target_audience: str = ""
    ) -> List[TrafficSignals]:
        """
        Enrich keywords with real traffic signals and volume data.
        
        Uses real API data when available, falls back to estimation.
        """
        if not keywords:
            return []
        
        results = []
        keywords_to_fetch = []
        
        # Check cache first
        for keyword in keywords:
            cached = self._get_cached(keyword)
            if cached:
                results.append(cached)
            else:
                keywords_to_fetch.append(keyword)
        
        if not keywords_to_fetch:
            return results
        
        # ===== STEP 1: FETCH REAL KEYWORD DATA =====
        real_metrics = {}
        if self.use_real_data and self.data_aggregator and self.data_aggregator.enabled_providers:
            logger.info(f"Fetching real keyword data for {len(keywords_to_fetch)} keywords...")
            real_metrics = self.data_aggregator.get_bulk_metrics(keywords_to_fetch)
            # Only count metrics that came from a real provider, not estimation fallback
            real_count = sum(1 for m in real_metrics.values() if m.data_source != "estimated")
            estimated_count = len(keywords_to_fetch) - real_count
            if real_count > 0:
                logger.info(f"Got real data for {real_count}/{len(keywords_to_fetch)} keywords (estimated: {estimated_count})")
            else:
                logger.warning(
                    f"All {len(keywords_to_fetch)} keyword data requests failed — "
                    "falling back to estimation. Check API credentials."
                )
                self.data_aggregator = None  # Disable for this session to stop 401 spam
        
        # ===== STEP 2: FETCH GOOGLE TRENDS =====
        trend_scores = {}
        if self.use_google_trends and self._pytrends:
            trend_scores = self._fetch_google_trends(keywords_to_fetch[:20])
            logger.info(f"Fetched Google Trends for {len(trend_scores)} keywords")
        
        # ===== STEP 3: ENRICH EACH KEYWORD =====
        for keyword in keywords_to_fetch:
            # Get real metrics if available
            metrics = real_metrics.get(keyword)
            
            # Build signals with real data or estimation
            signals = self._estimate_from_keyword(keyword, metrics)
            
            # Overlay Google Trends
            if keyword in trend_scores:
                trend_score = trend_scores[keyword]
                signals.trend_score = trend_score
                if signals.data_source == "estimated":
                    signals.data_source = "google_trends"
                
                if trend_score >= 75:
                    signals.trend_status = "🔥 TRENDING NOW"
                    signals.traffic_velocity = "Fast"
                elif trend_score >= 50:
                    signals.trend_status = "📈 RISING"
                    signals.traffic_velocity = "Moderate"
                elif trend_score >= 25:
                    signals.trend_status = "➡️ STABLE"
                else:
                    signals.trend_status = "📉 DECLINING"
                    signals.traffic_velocity = "Slow"
            
            # Recalculate priority with real numbers
            volume_score = min(100, (signals.monthly_volume or 0) / 1000) if signals.monthly_volume else 50
            difficulty_score = 100 - (signals.difficulty_score or 50)  # Lower difficulty = higher score
            
            # Cap CPC contribution to avoid excessive scores (max $10 CPC = 100 points)
            cpc_score = min((signals.cpc_value or 1) * 10, 100)
            
            signals.traffic_score = min(100, round(
                volume_score * 0.5 +
                difficulty_score * 0.3 +
                cpc_score * 0.2
            , 1))
            
            signals.priority_score = min(100, round(
                signals.trend_score * 0.25 +
                signals.traffic_score * 0.45 +
                (100 if signals.intent in ["Transactional", "Commercial"] else 60) * 0.30
            , 1))
            
            # Adjust for audience
            if target_audience:
                signals = self._adjust_for_audience(signals, target_audience)
            
            self._cache_signals(keyword, signals)
            results.append(signals)
        
        # Sort by priority score
        results.sort(key=lambda x: x.priority_score, reverse=True)
        return results
    
    def _adjust_for_audience(self, signals: TrafficSignals, audience: str) -> TrafficSignals:
        """Adjust signals based on target audience."""
        audience_lower = audience.lower()
        
        # Adjust for B2B audiences
        if any(term in audience_lower for term in ['b2b', 'business', 'enterprise', 'saas']):
            if signals.intent == "Informational":
                signals.cpc_signal = "High" if signals.cpc_signal == "Medium" else signals.cpc_signal
                signals.funnel_stage = "Consideration"
        
        # Adjust for beginner audiences
        if any(term in audience_lower for term in ['beginner', 'novice', 'starter', 'new']):
            if signals.intent in ["Transactional"]:
                signals.intent = "Commercial"  # Beginners research before buying
                signals.content_type = "Comparison" if signals.content_type == "Product Page" else signals.content_type
        
        # Adjust for expert audiences
        if any(term in audience_lower for term in ['expert', 'advanced', 'professional']):
            if signals.intent == "Informational":
                signals.content_type = "Blog"  # Experts want deep content
        
        return signals
    
    def get_trending_alerts(self, signals_list: List[TrafficSignals]) -> List[Dict]:
        """
        Extract trending alerts that need immediate action.
        
        Returns:
            List of trending alert dicts with urgency levels
        """
        alerts = []
        
        for signals in signals_list:
            if signals.trend_status == "🔥 TRENDING NOW" and signals.priority_score >= 70:
                urgency = "Act within 24 hours" if signals.traffic_velocity == "Viral" else "Act within 24–72 hours"
                
                alerts.append({
                    "keyword": signals.keyword,
                    "reason": f"{signals.trend_status} — {signals.intent} keyword with {signals.estimated_volume.lower().replace('_', ' ')} search volume",
                    "urgency": urgency,
                    "priority_score": signals.priority_score,
                    "trend_score": signals.trend_score
                })
        
        # Sort by priority score
        alerts.sort(key=lambda x: x["priority_score"], reverse=True)
        return alerts[:10]  # Top 10 alerts
    
    def get_quick_wins(self, signals_list: List[TrafficSignals], min_priority: float = 60.0) -> List[str]:
        """
        Extract quick-win keywords (easy difficulty, decent priority).
        
        Args:
            signals_list: List of enriched keyword signals
            min_priority: Minimum priority score threshold
            
        Returns:
            List of quick-win keyword strings
        """
        quick_wins = []
        
        for signals in signals_list:
            if signals.keyword_difficulty in ["Easy", "Medium"] and signals.priority_score >= min_priority:
                if signals.trend_status in ["🔥 TRENDING NOW", "📈 RISING", "➡️ STABLE"]:
                    quick_wins.append(signals.keyword)
        
        return quick_wins[:15]
    
    def get_avoid_keywords(self, signals_list: List[TrafficSignals]) -> List[Dict]:
        """
        Identify keywords to avoid (declining, too hard, poor fit).
        
        Returns:
            List of keywords to avoid with reasons
        """
        avoid = []
        
        for signals in signals_list:
            reasons = []
            
            if signals.trend_status == "📉 DECLINING":
                reasons.append("Declining search interest")
            
            if signals.keyword_difficulty == "Very Hard" and signals.priority_score < 50:
                reasons.append("Too competitive for current authority level")
            
            if signals.estimated_volume == "Very Low" and signals.cpc_signal == "Low":
                reasons.append("Low volume + low commercial value")
            
            if signals.trend_score < 20 and signals.priority_score < 40:
                reasons.append("Poor traffic opportunity profile")
            
            if reasons:
                avoid.append({
                    "keyword": signals.keyword,
                    "reason": "; ".join(reasons)
                })
        
        return avoid
    
    def build_topic_cluster(self, signals_list: List[TrafficSignals], page_topic: str = "") -> Dict:
        """
        Build a topic cluster from enriched keywords.
        
        Returns:
            Dict with pillar keyword, cluster keywords, and LSI terms
        """
        if not signals_list:
            return {
                "pillar_keyword": page_topic or "",
                "cluster_keywords": [],
                "lsi_terms": []
            }
        
        # Pillar keyword: highest priority short-tail term
        pillar_candidates = [s for s in signals_list if len(s.keyword.split()) <= 3]
        if pillar_candidates:
            pillar = max(pillar_candidates, key=lambda x: x.priority_score)
            pillar_keyword = pillar.keyword
        else:
            pillar_keyword = signals_list[0].keyword
        
        # Cluster keywords: long-tail variations
        cluster = [s.keyword for s in signals_list if len(s.keyword.split()) >= 4][:15]
        
        # LSI terms: informational/commercial terms
        lsi_candidates = [s for s in signals_list if s.intent in ["Informational", "Commercial"]]
        lsi_terms = [s.keyword for s in lsi_candidates[:10]]
        
        return {
            "pillar_keyword": pillar_keyword,
            "cluster_keywords": cluster,
            "lsi_terms": lsi_terms
        }


def enrich_with_traffic_signals(
    keywords: List[str],
    page_topic: str = "",
    target_audience: str = "",
    use_google_trends: bool = True,
    use_llm_estimation: bool = True
) -> Dict:
    """
    Main entry point: Enrich keywords with traffic signals and return formatted output.
    
    This is the function to call from pipeline_v2.py between Phase 2 and Phase 3.
    
    Args:
        keywords: List of ML-generated keywords
        page_topic: Page topic for context
        target_audience: Target audience description
        use_google_trends: Whether to fetch real Google Trends data
        use_llm_estimation: Whether to use LLM for traffic estimation when real data unavailable
        
    Returns:
        Dict matching the expected JSON output format
    """
    enricher = TrafficEnricher(use_google_trends=use_google_trends, use_llm_estimation=use_llm_estimation)
    
    # Enrich all keywords
    signals_list = enricher.enrich_keywords(keywords, page_topic, target_audience)
    
    # Build output structure with ACTUAL NUMBERS
    output = {
        "trending_alerts": enricher.get_trending_alerts(signals_list),
        "traffic_prioritized_keywords": [
            {
                "keyword": s.keyword,
                "trend_status": s.trend_status,
                "traffic_velocity": s.traffic_velocity,
                
                # ACTUAL NUMBERS (new)
                "monthly_volume": s.monthly_volume,
                "volume_display": f"{s.monthly_volume:,}/mo" if s.monthly_volume else s.volume_range,
                "volume_range": s.volume_range,
                "traffic_potential": f"~{int((s.monthly_volume or 0) * 0.3):,}/mo" if s.monthly_volume else "Unknown",
                "difficulty_score": s.difficulty_score,
                "cpc_value": f"${s.cpc_value:.2f}" if s.cpc_value else None,
                "competition_index": s.competition_index,
                
                # Legacy categories (backward compatibility)
                "estimated_volume": s.estimated_volume,
                "keyword_difficulty": s.keyword_difficulty,
                "cpc_signal": s.cpc_signal,
                "competition_level": s.competition_level,
                
                "intent": s.intent,
                "serp_opportunity": s.serp_opportunities or ["none"],
                "content_type": s.content_type,
                "funnel_stage": s.funnel_stage,
                "priority_score": s.priority_score,
                "traffic_score": s.traffic_score,
                "trend_score": s.trend_score,
                "data_source": s.data_source,
                "provider_used": s.provider_used,
                "reasoning": f"{s.trend_status} {s.intent.lower()} keyword with {s.monthly_volume or s.estimated_volume} monthly searches — difficulty: {s.difficulty_score or s.keyword_difficulty}"
            }
            for s in signals_list
        ],
        "quick_win_keywords": enricher.get_quick_wins(signals_list),
        "avoid_keywords": enricher.get_avoid_keywords(signals_list),
        "topic_cluster": enricher.build_topic_cluster(signals_list, page_topic),
        "enrichment_metadata": {
            "total_keywords_processed": len(keywords),
            "keywords_with_real_data": len([s for s in signals_list if s.data_source != "estimated"]),
            "keywords_with_trends_data": len([s for s in signals_list if s.data_source == "google_trends"]),
            "data_providers_used": list(set([s.provider_used for s in signals_list if s.provider_used])),
            "avg_priority_score": round(sum(s.priority_score for s in signals_list) / len(signals_list), 1) if signals_list else 0,
            "avg_monthly_volume": round(sum(s.monthly_volume or 0 for s in signals_list) / len([s for s in signals_list if s.monthly_volume]), 0) if any(s.monthly_volume for s in signals_list) else 0,
            "processed_at": datetime.now().isoformat()
        }
    }
    
    return output


# Convenience function for pipeline integration
def enrich_pipeline_keywords(
    ml_keywords: List[Dict],
    page_topic: str = "",
    target_audience: str = ""
) -> List[Dict]:
    """
    Enrich ML-generated keywords from pipeline with traffic signals.
    
    Args:
        ml_keywords: List of dicts with 'keyword' key from ML models
        page_topic: Page topic context
        target_audience: Target audience description
        
    Returns:
        List of enriched keyword dicts with traffic signals added
    """
    # Extract keyword strings
    keyword_strings = [
        k["keyword"] if isinstance(k, dict) else k
        for k in ml_keywords
    ]
    
    # Get traffic enrichment
    enrichment = enrich_with_traffic_signals(
        keywords=keyword_strings,
        page_topic=page_topic,
        target_audience=target_audience
    )
    
    # Merge traffic signals back into original ML keyword dicts
    traffic_by_keyword = {
        item["keyword"]: item
        for item in enrichment["traffic_prioritized_keywords"]
    }
    
    enriched = []
    for kw_data in ml_keywords:
        keyword = kw_data["keyword"] if isinstance(kw_data, dict) else kw_data
        
        if keyword in traffic_by_keyword:
            merged = {
                **(kw_data if isinstance(kw_data, dict) else {"keyword": kw_data}),
                "traffic_signals": traffic_by_keyword[keyword]
            }
            enriched.append(merged)
        else:
            enriched.append(kw_data if isinstance(kw_data, dict) else {"keyword": kw_data})
    
    return enriched
