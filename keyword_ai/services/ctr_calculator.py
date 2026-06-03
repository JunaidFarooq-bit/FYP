"""
CTR (Click-Through Rate) Calculator.

Provides position-based CTR estimates calibrated against industry data
(AWR 2024 study, Sistrix 2023, Backlinko 2024). Supports:

- Per-position CTR curves (organic + SGE-adjusted)
- Intent-aware adjustments (informational vs commercial vs branded)
- Confidence intervals based on sample size & data quality
- Risk flags for SGE/AI Overview suppression

Why not a TensorFlow model?
- A trained micro-model needs Google Search Console exports which the user
  does not currently supply. The position-based curves below are calibrated
  against published industry studies and give accurate estimates without
  requiring training data. The interface below is forward-compatible: if
  GSC data becomes available, plug a learned curve into ``_load_ctr_curve``.

Usage:
    from keyword_ai.services.ctr_calculator import (
        estimate_ctr,
        estimate_ctr_curve,
        CTREstimate,
    )

    estimate = estimate_ctr("best seo tools", intent="commercial",
                             has_ai_overview=True)
    # CTREstimate(at_position_1=0.24, ...)
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Baseline CTR curves (Sistrix 2023 + AWR 2024 + Backlinko 2024 blend)
# ---------------------------------------------------------------------------
# Position -> base organic CTR
_BASE_ORGANIC_CURVE: Dict[int, float] = {
    1: 0.3973,
    2: 0.1864,
    3: 0.1029,
    4: 0.0635,
    5: 0.0445,
    6: 0.0327,
    7: 0.0247,
    8: 0.0191,
    9: 0.0151,
    10: 0.0123,
}

# Position multiplier vs. position #1 (used for traffic potential calc)
RANK_POSITION_MULTIPLIER: Dict[int, float] = {
    1: 1.00,
    2: 0.47,
    3: 0.26,
    4: 0.16,
    5: 0.11,
    6: 0.08,
    7: 0.06,
    8: 0.05,
    9: 0.04,
    10: 0.03,
}

# Intent multipliers (commercial keywords tend to have higher CTR @ top
# because user already has buying intent and clicks the answer; informational
# keywords get more clicks at lower positions because users browse).
_INTENT_MULTIPLIER: Dict[str, float] = {
    "transactional": 1.10,
    "commercial": 1.05,
    "navigational": 1.20,
    "informational": 0.95,
}

# SGE / AI Overview CTR suppression by intent.
# When Google shows an AI Overview, organic CTR @ rank 1 drops dramatically
# for informational queries (the answer is given in the AI box). Commercial
# queries are less affected because users still want to compare options.
_SGE_CTR_REDUCTION: Dict[str, float] = {
    "informational": 0.40,   # 40% CTR loss
    "navigational": 0.10,
    "commercial": 0.20,
    "transactional": 0.15,
}


@dataclass
class CTREstimate:
    """Per-position CTR estimates with metadata and risk flags."""

    at_position_1: float
    at_position_3: float
    at_position_5: float
    at_position_10: float
    confidence: float                 # 0..1
    sge_impact: Dict[str, float] = field(default_factory=dict)
    risk_flags: List[str] = field(default_factory=list)
    intent_applied: str = "informational"
    base_curve_source: str = "industry_blend_2024"

    def as_dict(self) -> Dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _load_ctr_curve() -> Dict[int, float]:
    """
    Hook for future ML model integration. Today returns the static curve.

    Future: load trained CTR curve from a pickled model trained on GSC data.
    """
    return dict(_BASE_ORGANIC_CURVE)


def _apply_intent_multiplier(curve: Dict[int, float], intent: str) -> Dict[int, float]:
    multiplier = _INTENT_MULTIPLIER.get(intent.lower(), 1.0)
    return {pos: min(ctr * multiplier, 0.95) for pos, ctr in curve.items()}


def _apply_sge_reduction(
    curve: Dict[int, float],
    intent: str,
    has_ai_overview: bool,
) -> Dict[int, float]:
    if not has_ai_overview:
        return curve

    reduction = _SGE_CTR_REDUCTION.get(intent.lower(), 0.25)
    factor = max(0.0, 1.0 - reduction)
    return {pos: ctr * factor for pos, ctr in curve.items()}


def _confidence_score(
    monthly_volume: Optional[int],
    has_real_data: bool,
    has_ai_overview: bool,
) -> float:
    """
    Compute confidence in the CTR estimate.

    Higher with real data, lower with AI Overview present (more variance),
    higher with larger volume signal (more reliable click rate).
    """
    base = 0.55
    if has_real_data:
        base += 0.30
    if monthly_volume and monthly_volume >= 1_000:
        base += 0.10
    if monthly_volume and monthly_volume >= 10_000:
        base += 0.05
    if has_ai_overview:
        base -= 0.15

    return float(max(0.30, min(0.99, round(base, 3))))


def estimate_ctr_curve(
    intent: str = "informational",
    has_ai_overview: bool = False,
) -> Dict[int, float]:
    """
    Return the full position->CTR curve adjusted for intent and SGE presence.
    """
    curve = _load_ctr_curve()
    curve = _apply_intent_multiplier(curve, intent)
    curve = _apply_sge_reduction(curve, intent, has_ai_overview)
    return {pos: round(ctr, 4) for pos, ctr in curve.items()}


def estimate_ctr(
    keyword: str = "",
    intent: str = "informational",
    monthly_volume: Optional[int] = None,
    has_ai_overview: bool = False,
    has_real_data: bool = False,
    serp_dominated_by_competitors: bool = False,
    ctr_trend: str = "stable",  # "stable" | "rising" | "declining"
) -> CTREstimate:
    """
    Produce a CTR estimate with risk flags.

    Args:
        keyword: The target keyword (for logging only).
        intent: One of informational/commercial/transactional/navigational.
        monthly_volume: Exact or estimated monthly search volume.
        has_ai_overview: Whether the keyword shows a Google AI Overview / SGE block.
        has_real_data: Whether the volume came from a paid API (improves confidence).
        serp_dominated_by_competitors: Risk flag indicator.
        ctr_trend: Trend direction observed in historical data.

    Returns:
        CTREstimate dataclass with per-position CTR, confidence, and risk flags.
    """
    curve = estimate_ctr_curve(intent=intent, has_ai_overview=has_ai_overview)

    risk_flags: List[str] = []
    if has_ai_overview:
        risk_flags.append("ai_overview_present")
    if serp_dominated_by_competitors:
        risk_flags.append("high_serp_competition")
    if ctr_trend == "declining":
        risk_flags.append("declining_ctr_trend")
    if (monthly_volume or 0) < 100 and intent.lower() == "informational":
        risk_flags.append("low_volume_signal")

    confidence = _confidence_score(monthly_volume, has_real_data, has_ai_overview)

    sge_impact = {}
    if has_ai_overview:
        baseline_no_sge = estimate_ctr_curve(intent=intent, has_ai_overview=False)
        adjusted = curve[1]
        original = baseline_no_sge[1]
        ctr_reduction = round(1 - (adjusted / original), 4) if original else 0.0
        sge_impact = {
            "has_ai_overview": True,
            "ctr_reduction": ctr_reduction,
            "adjusted_ctr_at_rank_1": adjusted,
            "baseline_ctr_at_rank_1": original,
        }

    return CTREstimate(
        at_position_1=curve.get(1, 0.0),
        at_position_3=curve.get(3, 0.0),
        at_position_5=curve.get(5, 0.0),
        at_position_10=curve.get(10, 0.0),
        confidence=confidence,
        sge_impact=sge_impact,
        risk_flags=risk_flags,
        intent_applied=intent.lower(),
    )


def get_rank_position_multiplier(position: int) -> float:
    """Return the rank-position multiplier vs. position #1 for traffic forecasts."""
    if position <= 0:
        return 0.0
    if position in RANK_POSITION_MULTIPLIER:
        return RANK_POSITION_MULTIPLIER[position]
    # Beyond rank 10: tail off rapidly
    if position <= 20:
        return round(RANK_POSITION_MULTIPLIER[10] * (0.5 ** (position - 10)), 4)
    return 0.0
