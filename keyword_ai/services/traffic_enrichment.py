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
    provenance: str = "heuristic_fallback"
    confidence: str = "low"
    dataset_version: str = ""
    demand_level: str = "Medium"
    modeled_range: str = "500-5K"
    commercial_value: str = "Low"
    competition_band: str = "Moderate"

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

    def _estimate_from_keyword(self, keyword: str, real_metrics: Optional[KeywordMetrics] = None, llm_estimate=None) -> TrafficSignals:
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
        
        # ===== MEASURED PROVIDER DATA OR TRANSPARENT OFFLINE BAND =====
        if real_metrics and real_metrics.monthly_volume and real_metrics.data_source != "estimated":
            signals.monthly_volume = real_metrics.monthly_volume
            if real_metrics.volume_range_low and real_metrics.volume_range_high:
                signals.volume_range = f"{real_metrics.volume_range_low:,}-{real_metrics.volume_range_high:,}"
            signals.difficulty_score = real_metrics.keyword_difficulty
            signals.cpc_value = real_metrics.cpc
            signals.competition_index = real_metrics.competition_index
            signals.competition_level = real_metrics.competition_level or "Medium"
            signals.competition_band = signals.competition_level
            signals.data_source = real_metrics.data_source
            signals.provider_used = real_metrics.data_source
            signals.provenance = "measured"
            signals.confidence = "high"
            vol = real_metrics.monthly_volume
            signals.demand_level = (
                "Very High" if vol >= 100000 else "High" if vol >= 10000
                else "Medium" if vol >= 1000 else "Low" if vol >= 100 else "Very Low"
            )
            signals.estimated_volume = signals.demand_level
            signals.modeled_range = signals.volume_range
            if real_metrics.keyword_difficulty is not None:
                diff = real_metrics.keyword_difficulty
                signals.keyword_difficulty = (
                    "Easy" if diff < 30 else "Moderate" if diff < 60
                    else "Hard" if diff < 80 else "Very Hard"
                )
            if real_metrics.cpc is not None:
                signals.commercial_value = (
                    "Low" if real_metrics.cpc < 1 else
                    "Medium" if real_metrics.cpc < 3 else "High"
                )
                signals.cpc_signal = signals.commercial_value
        else:
            from .offline_benchmark import classify_keyword_opportunity
            modeled = classify_keyword_opportunity(keyword)
            signals.monthly_volume = None
            signals.cpc_value = None
            signals.difficulty_score = None
            signals.competition_index = None
            signals.data_source = modeled["provenance"]
            signals.provenance = modeled["provenance"]
            signals.confidence = modeled["confidence"]
            signals.dataset_version = modeled["dataset_version"]
            signals.demand_level = modeled["demand_level"]
            signals.estimated_volume = modeled["demand_level"]
            signals.modeled_range = modeled["modeled_range"]
            signals.volume_range = modeled["modeled_range"]
            signals.commercial_value = modeled["commercial_value"]
            signals.cpc_signal = modeled["commercial_value"]
            signals.competition_band = modeled["competition_band"]
            signals.competition_level = modeled["competition_band"]
            signals.keyword_difficulty = modeled["competition_band"]
            signals.trend_status = "Not measured"
            signals.trend_score = 50.0
            signals.traffic_velocity = "Unknown"

        # Adjust for question keywords (typically lower volume but high intent)
        if has_question_intent(keyword):
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
        
        # Competition is measured by a provider or classified by the offline model.
        signals.keyword_difficulty = signals.competition_band

        # No trend claim is made without observed trend data.
        demand_scores = {"Very Low": 15, "Low": 35, "Medium": 60, "High": 80, "Very High": 95}
        competition_opportunity = {"Low": 90, "Moderate": 65, "Medium": 65, "High": 35, "Very Hard": 20}
        commercial_scores = {"Low": 35, "Medium": 65, "High": 90}
        signals.traffic_score = round(
            demand_scores.get(signals.demand_level, 50) * 0.45
            + competition_opportunity.get(signals.competition_band, 50) * 0.35
            + commercial_scores.get(signals.commercial_value, 50) * 0.20,
            1,
        )
        signals.priority_score = round(
            signals.traffic_score * 0.75
            + (85 if signals.intent in ["Transactional", "Commercial"] else 60) * 0.25,
            1,
        )

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
        
        # ===== STEP 3: OFFLINE MODEL IS APPLIED LOCALLY =====
        # No LLM is used to invent volume, CPC, or difficulty.

        # ===== STEP 4: ENRICH EACH KEYWORD LOCALLY =====
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
            
            # Preserve modeled band scoring. Recalculate only measured rows.
            if signals.provenance == "measured":
                volume_score = min(100, (signals.monthly_volume or 0) / 1000)
                difficulty_score = 100 - (signals.difficulty_score or 50)
                commercial_score = {"Low": 35, "Medium": 65, "High": 90}.get(
                    signals.commercial_value, 50
                )
                signals.traffic_score = min(100, round(
                    volume_score * 0.5 + difficulty_score * 0.3 + commercial_score * 0.2, 1
                ))
                signals.priority_score = min(100, round(
                    signals.traffic_score * 0.7
                    + (100 if signals.intent in ["Transactional", "Commercial"] else 60) * 0.3,
                    1,
                ))

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
    
    # Build source-aware output structure
    output = {
        "trending_alerts": enricher.get_trending_alerts(signals_list),
        "traffic_prioritized_keywords": [
            {
                "keyword": s.keyword,
                "trend_status": s.trend_status,
                "traffic_velocity": s.traffic_velocity,
                
                # Exact fields are populated only for measured providers
                "monthly_volume": s.monthly_volume,
                "volume_display": f"{s.monthly_volume:,}/mo" if s.provenance == "measured" and s.monthly_volume else s.modeled_range,
                "volume_range": s.volume_range,
                "traffic_potential": f"~{int(s.monthly_volume * 0.3):,}/mo" if s.provenance == "measured" and s.monthly_volume else None,
                "difficulty_score": s.difficulty_score,
                "cpc_value": f"${s.cpc_value:.2f}" if s.provenance == "measured" and s.cpc_value is not None else None,
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
                "provenance": s.provenance,
                "confidence": s.confidence,
                "dataset_version": s.dataset_version,
                "demand_level": s.demand_level,
                "modeled_range": s.modeled_range,
                "commercial_value": s.commercial_value,
                "competition_band": s.competition_band,
                "reasoning": f"{s.demand_level} modeled demand, {s.competition_band.lower()} competition, {s.commercial_value.lower()} commercial value"
            }
            for s in signals_list
        ],
        "quick_win_keywords": enricher.get_quick_wins(signals_list),
        "avoid_keywords": enricher.get_avoid_keywords(signals_list),
        "topic_cluster": enricher.build_topic_cluster(signals_list, page_topic),
        "enrichment_metadata": {
            "total_keywords_processed": len(keywords),
            "keywords_with_real_data": len([s for s in signals_list if s.provenance == "measured"]),
            "keywords_with_trends_data": len([s for s in signals_list if s.data_source == "google_trends"]),
            "data_providers_used": list(set([s.provider_used for s in signals_list if s.provider_used])),
            "avg_priority_score": round(sum(s.priority_score for s in signals_list) / len(signals_list), 1) if signals_list else 0,
            "avg_monthly_volume": round(sum(s.monthly_volume for s in signals_list if s.provenance == "measured" and s.monthly_volume) / len([s for s in signals_list if s.provenance == "measured" and s.monthly_volume]), 0) if any(s.provenance == "measured" and s.monthly_volume for s in signals_list) else None,
            "processed_at": datetime.now().isoformat()
        }
    }
    
    return output


def _infer_serp_intent(organic_results: List[Dict]) -> Dict:
    counts = {"informational": 0, "commercial": 0, "transactional": 0, "navigational": 0}
    for result in organic_results[:10]:
        text = f"{result.get('title', '')} {result.get('link', '')}".lower()
        if any(term in text for term in ("buy", "shop", "product", "pricing", "book", "quote")):
            counts["transactional"] += 1
        elif any(term in text for term in ("best", "review", "compare", "comparison", "alternative", " vs ")):
            counts["commercial"] += 1
        elif any(term in text for term in ("login", "sign in", "official", "dashboard")):
            counts["navigational"] += 1
        else:
            counts["informational"] += 1

    total = sum(counts.values())
    primary = max(counts, key=counts.get) if total else None
    confidence = round(counts[primary] / total, 2) if primary and total else 0.0
    return {
        "primary_intent": primary,
        "confidence": confidence,
        "distribution": counts,
        "sample_size": total,
        "provenance": "observed_serp" if total else None,
    }


def apply_serp_evidence(
    traffic_analysis: Dict,
    serp_features: Dict[str, Dict],
    trend_evidence: Optional[Dict[str, Dict]] = None,
) -> Dict:
    """Merge observed SERP composition and relative demand into opportunity rows."""
    rows = traffic_analysis.get("traffic_prioritized_keywords", [])
    trend_evidence = trend_evidence or {}
    observed_count = 0
    trend_count = 0
    weights = {
        "paid_ads": 3, "shopping": 3, "local_pack": 2,
        "knowledge_graph": 2, "ai_overview": 2,
        "featured_snippet": 1, "people_also_ask": 1, "news": 1,
    }

    for item in rows:
        keyword = item.get("keyword")
        serp = serp_features.get(keyword, {})
        trend = trend_evidence.get(keyword, {})
        has_serp = bool(serp and serp.get("data_source") == "serpapi")

        if has_serp:
            observed_count += 1
            features = list(dict.fromkeys(serp.get("serp_features") or []))
            pressure_score = sum(weights.get(feature, 0) for feature in features)
            if pressure_score >= 4:
                pressure = "High"
                item["competition_band"] = "High"
                item["priority_score"] = max(0, round(item.get("priority_score", 0) - 10, 1))
            elif pressure_score >= 2:
                pressure = "Moderate"
                if item.get("competition_band") == "Low":
                    item["competition_band"] = "Moderate"
                item["priority_score"] = max(0, round(item.get("priority_score", 0) - 5, 1))
            else:
                pressure = "Standard"

            domains = [
                result.get("domain")
                for result in (serp.get("organic_results") or [])[:5]
                if result.get("domain")
            ]
            intent_evidence = _infer_serp_intent(serp.get("organic_results") or [])
            if intent_evidence["sample_size"] >= 3 and intent_evidence["confidence"] >= 0.5:
                item["intent"] = intent_evidence["primary_intent"].title()
                item["intent_source"] = "observed_serp"

            item.update({
                "serp_observed": True,
                "evidence_provenance": "observed_serp",
                "evidence_source": "serpapi",
                "evidence_confidence": "high",
                "source_label": "SERP observed + modeled demand",
                "serp_pressure": pressure,
                "serp_pressure_score": pressure_score,
                "observed_features": features,
                "competitor_domains": domains,
                "serp_intent": intent_evidence,
                "serp_opportunity": features or ["standard_organic_results"],
                "related_query_count": len(serp.get("related_searches") or []),
                "paa_question_count": len(serp.get("people_also_ask") or []),
            })
        else:
            item["serp_observed"] = False

        if trend:
            trend_count += 1
            item.update({
                "relative_demand_index": trend.get("relative_interest"),
                "trend_direction": trend.get("trend_direction"),
                "trend_change_index": trend.get("change_index"),
                "trend_period": trend.get("period"),
                "demand_provenance": "observed_serp",
                "trend_status": trend.get("trend_direction", "Stable"),
            })
            if trend.get("trend_direction") == "Rising":
                item["priority_score"] = min(100, round(item.get("priority_score", 0) + 5, 1))
            elif trend.get("trend_direction") == "Declining":
                item["priority_score"] = max(0, round(item.get("priority_score", 0) - 5, 1))

        item["evidence_status"] = (
            "observed" if has_serp and trend
            else "partial_evidence" if has_serp or trend
            else "insufficient_evidence"
        )
        if item["evidence_status"] == "insufficient_evidence":
            item["source_label"] = "Insufficient live evidence"

    metadata = traffic_analysis.setdefault("enrichment_metadata", {})
    metadata["keywords_with_serp_evidence"] = observed_count
    metadata["keywords_with_trend_evidence"] = trend_count
    metadata["serp_evidence_source"] = "serpapi" if observed_count else None
    metadata["trend_evidence_source"] = "serpapi_google_trends" if trend_count else None
    return traffic_analysis


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
