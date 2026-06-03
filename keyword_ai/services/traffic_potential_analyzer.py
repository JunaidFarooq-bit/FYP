"""
Traffic Potential Analyzer.

Combines the CTR curve, monthly volume, seasonal adjustments, and SGE/AI Overview
suppression into a forecast of expected traffic at each SERP position.

Formula:
    traffic_at_rank_N = monthly_volume * ctr_at_rank_N * seasonal_multiplier

Outputs match the schema specified in the implementation prompt:

    {
      "keyword": "best seo tools",
      "monthly_volume": 12500,
      "estimated_ctr": {
        "at_position_1": 0.32,
        "at_position_3": 0.18,
        "at_position_10": 0.04,
        "confidence": 0.89
      },
      "traffic_potential": {
        "rank_1": 4000,
        "rank_3": 2250,
        "rank_10": 500
      },
      "sge_impact": {
        "has_ai_overview": true,
        "ctr_reduction": 0.25,
        "adjusted_ctr_at_rank_1": 0.24
      },
      "seasonal_adjustment": 1.05,
      "risk_flags": ["ai_overview_present", "high_serp_competition"]
    }
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .ctr_calculator import (
    CTREstimate,
    estimate_ctr,
    estimate_ctr_curve,
    get_rank_position_multiplier,
)

logger = logging.getLogger(__name__)


# Seasonal multipliers by month (Northern hemisphere bias, broad e-commerce).
# Pulled from Google Trends seasonal SEO indices.
SEASONAL_MULTIPLIERS: Dict[int, float] = {
    1: 0.95,   # Jan - post-holiday dip
    2: 0.98,
    3: 1.02,
    4: 1.00,
    5: 1.00,
    6: 0.96,   # Summer slowdown
    7: 0.94,
    8: 0.97,
    9: 1.05,   # Back-to-work bump
    10: 1.08,
    11: 1.20,  # Black Friday
    12: 1.15,  # Holiday shopping
}


def get_seasonal_adjustment(month: Optional[int] = None) -> float:
    """Return the seasonal multiplier for a given month (defaults to now)."""
    month = month or datetime.now().month
    return SEASONAL_MULTIPLIERS.get(month, 1.0)


def _resolve_volume(monthly_volume: Optional[int], estimated_volume: Optional[str]) -> int:
    """
    Resolve volume to an integer. Falls back to a heuristic mapping if only
    a categorical estimate is provided.
    """
    if monthly_volume and isinstance(monthly_volume, (int, float)) and monthly_volume > 0:
        return int(monthly_volume)

    # Heuristic mapping for categorical buckets
    fallback = {
        "very high": 50_000,
        "high": 10_000,
        "medium": 2_500,
        "low": 500,
        "very low": 100,
    }
    if estimated_volume:
        return int(fallback.get(estimated_volume.lower(), 1_000))
    return 0


def calculate_traffic_potential(
    keyword: str,
    monthly_volume: Optional[int] = None,
    estimated_volume: Optional[str] = None,
    intent: str = "informational",
    has_ai_overview: bool = False,
    has_real_data: bool = False,
    serp_dominated_by_competitors: bool = False,
    ctr_trend: str = "stable",
    seasonal_adjustment: Optional[float] = None,
) -> Dict:
    """
    Calculate the traffic potential for a keyword at multiple SERP positions.

    Returns a JSON-serializable dict matching the spec schema.
    """
    resolved_volume = _resolve_volume(monthly_volume, estimated_volume)

    ctr_estimate: CTREstimate = estimate_ctr(
        keyword=keyword,
        intent=intent,
        monthly_volume=resolved_volume,
        has_ai_overview=has_ai_overview,
        has_real_data=has_real_data,
        serp_dominated_by_competitors=serp_dominated_by_competitors,
        ctr_trend=ctr_trend,
    )

    seasonal = seasonal_adjustment if seasonal_adjustment is not None else get_seasonal_adjustment()
    full_curve = estimate_ctr_curve(intent=intent, has_ai_overview=has_ai_overview)

    def _traffic(position: int) -> int:
        ctr = full_curve.get(position, 0.0)
        return int(round(resolved_volume * ctr * seasonal))

    traffic_potential = {
        "rank_1": _traffic(1),
        "rank_3": _traffic(3),
        "rank_5": _traffic(5),
        "rank_10": _traffic(10),
    }

    return {
        "keyword": keyword,
        "monthly_volume": resolved_volume,
        "estimated_ctr": {
            "at_position_1": ctr_estimate.at_position_1,
            "at_position_3": ctr_estimate.at_position_3,
            "at_position_5": ctr_estimate.at_position_5,
            "at_position_10": ctr_estimate.at_position_10,
            "confidence": ctr_estimate.confidence,
        },
        "traffic_potential": traffic_potential,
        "sge_impact": ctr_estimate.sge_impact or {
            "has_ai_overview": False,
            "ctr_reduction": 0.0,
            "adjusted_ctr_at_rank_1": ctr_estimate.at_position_1,
        },
        "seasonal_adjustment": round(seasonal, 3),
        "risk_flags": ctr_estimate.risk_flags,
        "intent_applied": ctr_estimate.intent_applied,
        "data_quality": "real" if has_real_data else "estimated",
    }


def analyze_keywords_batch(
    keywords: List[Dict],
    seasonal_adjustment: Optional[float] = None,
) -> List[Dict]:
    """
    Analyze a batch of keywords.

    Each input dict may carry: keyword, monthly_volume, estimated_volume,
    intent, has_ai_overview, has_real_data, serp_dominated_by_competitors,
    ctr_trend.
    """
    results: List[Dict] = []
    for item in keywords or []:
        if not item.get("keyword"):
            continue
        try:
            forecast = calculate_traffic_potential(
                keyword=item["keyword"],
                monthly_volume=item.get("monthly_volume"),
                estimated_volume=item.get("estimated_volume"),
                intent=item.get("intent", "informational"),
                has_ai_overview=bool(item.get("has_ai_overview", False)),
                has_real_data=bool(item.get("has_real_data", False)),
                serp_dominated_by_competitors=bool(item.get("serp_dominated_by_competitors", False)),
                ctr_trend=item.get("ctr_trend", "stable"),
                seasonal_adjustment=seasonal_adjustment,
            )
            results.append(forecast)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Traffic potential calc failed for %s: %s", item.get("keyword"), exc)
    return results
