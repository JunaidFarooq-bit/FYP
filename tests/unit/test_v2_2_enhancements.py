"""
Unit tests for the v2.2 keyword pipeline enhancements.

Covers:
1. Year injection utility (placeholder + outdated year refresh)
2. LLM model selector / gpt-4o fallback chain
3. CTR calculator (position curves, SGE impact, intent multiplier)
4. Traffic potential analyzer (volume * CTR * seasonal)
5. GEO/AEO analyzer (local detection, AEO scoring)
6. LLM prompt generator (GEO + year-aware templates)
7. target_keywords scoping fix regression
"""

from __future__ import annotations

import inspect
import pytest
from unittest.mock import patch


pytestmark = [pytest.mark.unit, pytest.mark.keyword]


# ---------------------------------------------------------------------------
# 1. Year Injection
# ---------------------------------------------------------------------------

class TestYearInjector:

    def test_inject_placeholder_replaced(self):
        from keyword_ai.utils.year_injector import inject_current_year, current_year
        result = inject_current_year("Complete SEO Guide {current_year}")
        assert str(current_year()) in result
        assert "{current_year}" not in result

    def test_inject_uppercase_placeholder(self):
        from keyword_ai.utils.year_injector import inject_current_year, current_year
        result = inject_current_year("Year is {CURRENT_YEAR}")
        assert str(current_year()) in result

    def test_inject_with_explicit_year_override(self):
        from keyword_ai.utils.year_injector import inject_current_year
        assert inject_current_year("Best of {current_year}", year=2030) == "Best of 2030"

    def test_noop_on_string_without_placeholder(self):
        from keyword_ai.utils.year_injector import inject_current_year
        text = "No placeholders here."
        assert inject_current_year(text) == text

    def test_noop_on_empty_string(self):
        from keyword_ai.utils.year_injector import inject_current_year
        assert inject_current_year("") == ""

    def test_refresh_outdated_years_replaces_stale(self):
        from keyword_ai.utils.year_injector import refresh_outdated_years
        result = refresh_outdated_years("Complete Guide 2020", year=2025)
        assert "2025" in result
        assert "2020" not in result

    def test_refresh_does_not_touch_future_year(self):
        from keyword_ai.utils.year_injector import refresh_outdated_years
        # 2026 is outside the 2018-2024 outdated range → must be left alone
        text = "Roadmap 2026"
        assert refresh_outdated_years(text, year=2025) == text

    def test_inject_in_dict_walks_nested(self):
        from keyword_ai.utils.year_injector import inject_in_dict, current_year
        data = {
            "title": "SEO Guide {current_year}",
            "items": [
                {"label": "Best of {current_year}"},
                "Top Tools {current_year}",
            ],
        }
        out = inject_in_dict(data)
        year = str(current_year())
        assert year in out["title"]
        assert year in out["items"][0]["label"]
        assert year in out["items"][1]

    def test_inject_in_dict_passthrough_non_strings(self):
        from keyword_ai.utils.year_injector import inject_in_dict
        data = {"count": 42, "flag": True, "ratio": 0.5}
        out = inject_in_dict(data)
        assert out["count"] == 42
        assert out["flag"] is True

    def test_build_year_context_keys(self):
        from keyword_ai.utils.year_injector import build_year_context
        ctx = build_year_context()
        assert "current_year" in ctx
        assert "next_year" in ctx
        assert "previous_year" in ctx
        assert ctx["next_year"] == ctx["current_year"] + 1
        assert ctx["previous_year"] == ctx["current_year"] - 1


# ---------------------------------------------------------------------------
# 2. LLM Model Selector / Fallback chain
# ---------------------------------------------------------------------------

class TestLLMModelSelector:

    def test_openai_priority_starts_with_configured(self, settings):
        settings.OPENAI_MODEL = "gpt-4o"
        from keyword_ai.services.llm_model_selector import get_openai_priority
        chain = get_openai_priority()
        assert chain[0] == "gpt-4o"
        assert "gpt-4-turbo" in chain
        assert "gpt-4" in chain

    def test_openai_priority_includes_all_fallbacks(self, settings):
        settings.OPENAI_MODEL = "gpt-4o"
        from keyword_ai.services.llm_model_selector import get_openai_priority, OPENAI_MODEL_PRIORITY
        chain = get_openai_priority()
        for model in OPENAI_MODEL_PRIORITY:
            assert model in chain

    def test_groq_priority_starts_with_configured(self, settings):
        settings.GROQ_MODEL = "llama-3.3-70b-versatile"
        from keyword_ai.services.llm_model_selector import get_groq_priority
        chain = get_groq_priority()
        assert chain[0] == "llama-3.3-70b-versatile"

    def test_provider_chain_groq_first_when_enabled(self, settings):
        settings.USE_GROQ = True
        settings.GROQ_API_KEY = "test-groq-key"
        settings.OPENAI_API_KEY = "test-openai-key"
        settings.GROQ_MODEL = "llama-3.3-70b-versatile"
        settings.OPENAI_MODEL = "gpt-4o"
        from keyword_ai.services.llm_model_selector import get_provider_chain
        chain = get_provider_chain()
        providers = [p for p, _ in chain]
        assert providers[0] == "groq", "Groq should be first when USE_GROQ=True"
        assert "openai" in providers

    def test_provider_chain_empty_when_no_keys(self, settings):
        settings.USE_GROQ = False
        settings.GROQ_API_KEY = ""
        settings.OPENAI_API_KEY = ""
        from keyword_ai.services.llm_model_selector import get_provider_chain
        assert get_provider_chain() == []

    def test_get_llm_model_raises_when_no_providers(self, settings):
        settings.USE_GROQ = False
        settings.GROQ_API_KEY = ""
        settings.OPENAI_API_KEY = ""
        from keyword_ai.services.llm_model_selector import get_llm_model, NoAvailableModelError
        with pytest.raises(NoAvailableModelError):
            get_llm_model()

    def test_get_model_metadata_openai(self):
        from keyword_ai.services.llm_model_selector import get_model_metadata
        meta = get_model_metadata("gpt-4o")
        assert meta["provider"] == "openai"
        assert meta["context"] == 128_000

    def test_get_model_metadata_unknown_returns_unknown(self):
        from keyword_ai.services.llm_model_selector import get_model_metadata
        meta = get_model_metadata("some-future-model-xyz")
        assert meta["provider"] == "unknown"


# ---------------------------------------------------------------------------
# 3. CTR Calculator
# ---------------------------------------------------------------------------

class TestCTRCalculator:

    def test_position_1_highest_ctr(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr_curve
        curve = estimate_ctr_curve(intent="informational", has_ai_overview=False)
        assert curve[1] > curve[3] > curve[5] > curve[10]

    def test_all_ctr_values_between_0_and_1(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr_curve
        curve = estimate_ctr_curve(intent="commercial", has_ai_overview=True)
        for pos, ctr in curve.items():
            assert 0.0 <= ctr <= 1.0, f"CTR at position {pos} out of range: {ctr}"

    def test_sge_reduces_informational_ctr(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr_curve
        no_sge = estimate_ctr_curve(intent="informational", has_ai_overview=False)
        with_sge = estimate_ctr_curve(intent="informational", has_ai_overview=True)
        assert with_sge[1] < no_sge[1]

    def test_commercial_intent_higher_than_informational_at_rank1(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr_curve
        commercial = estimate_ctr_curve(intent="commercial", has_ai_overview=False)
        informational = estimate_ctr_curve(intent="informational", has_ai_overview=False)
        assert commercial[1] >= informational[1]

    def test_estimate_ctr_sge_risk_flag(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr
        est = estimate_ctr(keyword="what is seo", intent="informational", has_ai_overview=True)
        assert "ai_overview_present" in est.risk_flags

    def test_estimate_ctr_sge_impact_dict(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr
        est = estimate_ctr(keyword="how to do seo", intent="informational", has_ai_overview=True)
        assert est.sge_impact.get("has_ai_overview") is True
        assert est.sge_impact.get("ctr_reduction", 0) > 0

    def test_confidence_higher_with_real_data(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr
        real = estimate_ctr(monthly_volume=10_000, has_real_data=True)
        estimated = estimate_ctr(monthly_volume=10_000, has_real_data=False)
        assert real.confidence > estimated.confidence

    def test_confidence_reduced_with_ai_overview(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr
        no_sge = estimate_ctr(monthly_volume=10_000, has_real_data=True, has_ai_overview=False)
        with_sge = estimate_ctr(monthly_volume=10_000, has_real_data=True, has_ai_overview=True)
        assert with_sge.confidence < no_sge.confidence

    def test_estimate_ctr_as_dict(self):
        from keyword_ai.services.ctr_calculator import estimate_ctr
        est = estimate_ctr()
        d = est.as_dict()
        assert "at_position_1" in d
        assert "at_position_10" in d
        assert "confidence" in d

    def test_rank_position_multiplier_descending(self):
        from keyword_ai.services.ctr_calculator import get_rank_position_multiplier
        assert get_rank_position_multiplier(1) == 1.0
        assert get_rank_position_multiplier(3) < get_rank_position_multiplier(1)
        assert get_rank_position_multiplier(10) < get_rank_position_multiplier(3)
        assert get_rank_position_multiplier(0) == 0.0


# ---------------------------------------------------------------------------
# 4. Traffic Potential Analyzer
# ---------------------------------------------------------------------------

class TestTrafficPotentialAnalyzer:

    def test_rank1_greater_than_rank3_greater_than_rank10(self):
        from keyword_ai.services.traffic_potential_analyzer import calculate_traffic_potential
        r = calculate_traffic_potential(keyword="best seo tools", monthly_volume=10_000, intent="commercial")
        tp = r["traffic_potential"]
        assert tp["rank_1"] > tp["rank_3"] > tp["rank_10"]

    def test_returns_required_schema_keys(self):
        from keyword_ai.services.traffic_potential_analyzer import calculate_traffic_potential
        r = calculate_traffic_potential(keyword="seo tips", monthly_volume=5_000, intent="informational")
        for key in ("keyword", "monthly_volume", "estimated_ctr", "traffic_potential",
                    "sge_impact", "seasonal_adjustment", "risk_flags", "intent_applied"):
            assert key in r, f"Missing key: {key}"

    def test_categorical_volume_resolved(self):
        from keyword_ai.services.traffic_potential_analyzer import calculate_traffic_potential
        r = calculate_traffic_potential(keyword="seo tips", monthly_volume=None, estimated_volume="High")
        assert r["monthly_volume"] > 0
        assert r["data_quality"] == "estimated"

    def test_higher_seasonal_multiplier_gives_more_traffic(self):
        from keyword_ai.services.traffic_potential_analyzer import calculate_traffic_potential
        high = calculate_traffic_potential(keyword="black friday", monthly_volume=10_000,
                                           intent="transactional", seasonal_adjustment=1.20)
        low = calculate_traffic_potential(keyword="black friday", monthly_volume=10_000,
                                          intent="transactional", seasonal_adjustment=0.90)
        assert high["traffic_potential"]["rank_1"] > low["traffic_potential"]["rank_1"]

    def test_sge_reduces_traffic_vs_no_sge(self):
        from keyword_ai.services.traffic_potential_analyzer import calculate_traffic_potential
        no_sge = calculate_traffic_potential(keyword="what is seo", monthly_volume=10_000,
                                             intent="informational", has_ai_overview=False)
        with_sge = calculate_traffic_potential(keyword="what is seo", monthly_volume=10_000,
                                               intent="informational", has_ai_overview=True)
        assert with_sge["traffic_potential"]["rank_1"] < no_sge["traffic_potential"]["rank_1"]

    def test_batch_analysis_returns_list(self):
        from keyword_ai.services.traffic_potential_analyzer import analyze_keywords_batch
        batch = [
            {"keyword": "seo tools", "monthly_volume": 5_000, "intent": "commercial"},
            {"keyword": "seo guide", "monthly_volume": 2_000, "intent": "informational"},
        ]
        results = analyze_keywords_batch(batch)
        assert len(results) == 2
        assert results[0]["keyword"] == "seo tools"

    def test_batch_skips_items_without_keyword(self):
        from keyword_ai.services.traffic_potential_analyzer import analyze_keywords_batch
        batch = [
            {"monthly_volume": 1_000},          # no keyword key
            {"keyword": "", "monthly_volume": 500},  # empty keyword
            {"keyword": "valid kw", "monthly_volume": 100},
        ]
        results = analyze_keywords_batch(batch)
        assert len(results) == 1
        assert results[0]["keyword"] == "valid kw"

    def test_zero_volume_produces_zero_traffic(self):
        from keyword_ai.services.traffic_potential_analyzer import calculate_traffic_potential
        r = calculate_traffic_potential(keyword="niche term", monthly_volume=0)
        assert r["traffic_potential"]["rank_1"] == 0


# ---------------------------------------------------------------------------
# 5. GEO/AEO Analyzer
# ---------------------------------------------------------------------------

class TestGeoAnalyzer:

    def test_near_me_is_local(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        geo = analyze_geo("plumber near me")
        assert geo.has_local_modifier is True
        assert geo.primary_scope == "local"

    def test_city_token_detected(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        geo = analyze_geo("best restaurants in london")
        assert "london" in geo.detected_locations

    def test_eu_region_detected(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        geo = analyze_geo("ecommerce platform germany")
        assert "EU" in geo.detected_regions

    def test_apac_region_detected(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        geo = analyze_geo("logistics company singapore")
        assert "APAC" in geo.detected_regions

    def test_no_location_yields_national(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        geo = analyze_geo("best seo tools")
        assert geo.primary_scope == "national"
        assert geo.detected_locations == []

    def test_geo_score_higher_for_local(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        local = analyze_geo("plumber near me")
        national = analyze_geo("plumbing services")
        assert local.geo_score > national.geo_score

    def test_empty_keyword_returns_defaults(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo
        geo = analyze_geo("")
        assert geo.primary_scope == "national"
        assert geo.geo_score == 0


class TestAeoAnalyzer:

    def test_question_starter_boosts_score(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        q = analyze_aeo("what is search engine optimization")
        plain = analyze_aeo("search engine optimization")
        assert q.score > plain.score

    def test_question_keyword_is_ai_friendly(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        out = analyze_aeo("how to improve seo ranking")
        assert out.ai_friendly is True

    def test_single_word_keyword_lower_score(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        single = analyze_aeo("seo")
        multi = analyze_aeo("how to improve seo for ecommerce websites")
        assert multi.score > single.score

    def test_list_format_hint_detected(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        out = analyze_aeo("best seo tools comparison")
        assert any(f in out.suggested_formats for f in ("list", "comparison"))

    def test_definition_format_hint_detected(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        out = analyze_aeo("what is seo definition")
        assert "definition" in out.suggested_formats or len(out.suggested_formats) > 0

    def test_answer_extraction_likelihood_high_for_question(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        out = analyze_aeo("how does google rank websites")
        assert out.answer_extraction_likelihood in ("medium", "high")

    def test_empty_keyword_returns_zero_score(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_aeo
        out = analyze_aeo("")
        assert out.score == 0


class TestCombinedGeoAeo:

    def test_combined_returns_both_layers(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_geo_aeo
        r = analyze_geo_aeo("best seo tools london")
        assert "geo_data" in r
        assert "aeo_signals" in r

    def test_batch_returns_list_with_keyword(self):
        from keyword_ai.services.geo_aeo_analyzer import analyze_keywords_batch
        results = analyze_keywords_batch(["seo near me", "best seo tools"])
        assert len(results) == 2
        assert all("keyword" in item for item in results)
        assert all("geo_data" in item for item in results)


# ---------------------------------------------------------------------------
# 6. LLM Prompt Generator
# ---------------------------------------------------------------------------

class TestLLMPromptGenerator:

    def test_builds_prompt_with_current_year(self):
        from keyword_ai.services.llm_prompt_generator import build_expansion_prompt
        from keyword_ai.utils.year_injector import current_year
        prompt, meta = build_expansion_prompt(keyword="seo tools", n=5, target_region="NA")
        assert str(current_year()) in prompt
        assert meta["year"] == current_year()

    def test_region_NA_in_metadata(self):
        from keyword_ai.services.llm_prompt_generator import build_expansion_prompt
        _, meta = build_expansion_prompt(keyword="seo", n=3, target_region="NA")
        assert meta["region"] == "NA"

    def test_unknown_region_falls_back_to_global(self):
        from keyword_ai.services.llm_prompt_generator import build_expansion_prompt
        _, meta = build_expansion_prompt(keyword="seo", n=3, target_region="MARS")
        assert meta["region"] == "GLOBAL"

    def test_no_raw_year_placeholders_in_output(self):
        from keyword_ai.services.llm_prompt_generator import build_expansion_prompt
        prompt, _ = build_expansion_prompt(keyword="seo tools", n=5, target_region="EU")
        assert "{current_year}" not in prompt
        assert "{CURRENT_YEAR}" not in prompt

    def test_existing_keywords_appear_in_avoid_section(self):
        from keyword_ai.services.llm_prompt_generator import build_expansion_prompt
        existing = ["seo tools", "keyword research"]
        prompt, _ = build_expansion_prompt(
            keyword="seo", n=5, target_region="GLOBAL", existing_keywords=existing
        )
        assert "seo tools" in prompt
        assert "keyword research" in prompt

    def test_prompt_version_in_metadata(self):
        from keyword_ai.services.llm_prompt_generator import build_expansion_prompt
        _, meta = build_expansion_prompt(keyword="seo", n=3)
        assert "prompt_version" in meta

    def test_apply_intent_modifiers_no_raw_placeholders(self):
        from keyword_ai.services.llm_prompt_generator import apply_intent_modifiers
        results = apply_intent_modifiers("seo tools", intent="commercial")
        for item in results:
            assert "{keyword}" not in item
            assert "{current_year}" not in item


# ---------------------------------------------------------------------------
# 7. target_keywords scoping regression
# ---------------------------------------------------------------------------

class TestTargetKeywordsScopingFix:
    """
    Regression: `target_keywords` was only defined inside
    `if analyze_competitors and url:`, causing NameError on other code paths.
    Fixed by pre-defining it unconditionally before the conditional block.
    """

    def test_pipeline_source_has_unconditional_definition(self):
        import keyword_ai.pipeline_v2 as mod
        source = open(mod.__file__, encoding="utf-8").read()
        assert "Pre-define target_keywords unconditionally" in source
        assert "target_keywords: List[str] = (" in source

    def test_pipeline_accepts_target_region_parameter(self):
        from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2
        sig = inspect.signature(run_keyword_pipeline_v2)
        assert "target_region" in sig.parameters
        assert sig.parameters["target_region"].default == "GLOBAL"

    def test_pipeline_accepts_all_v2_2_parameters(self):
        from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2
        sig = inspect.signature(run_keyword_pipeline_v2)
        expected = {"url", "text", "page_topic", "use_llm", "use_advanced_ai",
                    "analyze_competitors", "generate_optimization",
                    "target_audience", "target_region", "save_to_db"}
        assert expected.issubset(sig.parameters.keys())
