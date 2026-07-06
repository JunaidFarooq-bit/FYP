from django.core.cache import cache

from keyword_ai.services.candidate_quality import assess_candidate, filter_candidates
from keyword_ai.services.traffic_data_providers import SerpAPIProvider
from keyword_ai.services.traffic_enrichment import apply_serp_evidence, enrich_with_traffic_signals


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_candidate_gate_rejects_fragments_and_keeps_queries():
    assert assess_candidate("commerce infrastructure operational")["accepted"] is False
    assert assess_candidate("sales leaders enable")["accepted"] is False
    assert assess_candidate("best ecommerce integration platform")["accepted"] is True
    accepted, diagnostics = filter_candidates(
        [
            "commerce infrastructure operational",
            "best ecommerce integration platform",
            "how to streamline sales processes",
        ],
        limit=15,
    )
    assert accepted == [
        "best ecommerce integration platform",
        "how to streamline sales processes",
    ]
    assert len(diagnostics) == 3


def test_serp_results_are_cached_for_repeated_queries(monkeypatch):
    cache.clear()
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(kwargs.get("params", {}))
        return FakeResponse({
            "organic_results": [
                {"position": 1, "title": "Guide", "link": "https://example.com/guide"}
            ],
            "related_questions": [{"question": "What is SEO?"}],
        })

    monkeypatch.setattr("keyword_ai.services.traffic_data_providers.requests.get", fake_get)
    provider = SerpAPIProvider(api_key="test")
    first = provider.get_serp_features("technical seo")
    second = provider.get_serp_features("technical seo")
    assert len(calls) == 1
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True


def test_serpapi_trends_returns_relative_observed_demand(monkeypatch):
    cache.clear()

    def fake_get(*args, **kwargs):
        return FakeResponse({
            "interest_over_time": {
                "timeline_data": [
                    {
                        "values": [
                            {"query": "seo tools", "extracted_value": 20},
                            {"query": "seo audit", "extracted_value": 40},
                        ]
                    },
                    {
                        "values": [
                            {"query": "seo tools", "extracted_value": 60},
                            {"query": "seo audit", "extracted_value": 50},
                        ]
                    },
                ]
            }
        })

    monkeypatch.setattr("keyword_ai.services.traffic_data_providers.requests.get", fake_get)
    provider = SerpAPIProvider(api_key="test")
    results = provider.get_trends_scores(["seo tools", "seo audit"])
    assert results["seo tools"]["relative_interest"] == 40.0
    assert results["seo tools"]["provenance"] == "observed_serp"
    assert results["seo audit"]["source"] == "serpapi_google_trends"


def test_serp_composition_validates_intent_and_missing_evidence_is_explicit():
    output = enrich_with_traffic_signals(
        ["best seo platform", "technical seo checklist"],
        use_google_trends=False,
        use_llm_estimation=False,
    )
    apply_serp_evidence(
        output,
        {
            "best seo platform": {
                "data_source": "serpapi",
                "serp_features": ["paid_ads", "people_also_ask"],
                "organic_results": [
                    {"title": "Best SEO Platforms", "link": "https://one.test/best"},
                    {"title": "SEO Platform Reviews", "link": "https://two.test/review"},
                    {"title": "Compare SEO Software", "link": "https://three.test/compare"},
                ],
            }
        },
        {
            "best seo platform": {
                "relative_interest": 72,
                "trend_direction": "Rising",
                "change_index": 12,
                "period": "today 12-m",
            }
        },
    )
    by_keyword = {item["keyword"]: item for item in output["traffic_prioritized_keywords"]}
    observed = by_keyword["best seo platform"]
    missing = by_keyword["technical seo checklist"]
    assert observed["intent"] == "Commercial"
    assert observed["intent_source"] == "observed_serp"
    assert observed["relative_demand_index"] == 72
    assert observed["evidence_status"] == "observed"
    assert missing["evidence_status"] == "insufficient_evidence"


def test_feedback_training_uses_decisive_actions_as_labels(db, sample_content_analysis):
    from keyword_ai.models import KeywordOpportunity, SuggestionFeedback
    from keyword_ai.retraining_pipeline import RetrainingPipeline

    for index in range(20):
        opportunity = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword=f"feedback keyword {index}",
            keyword_type="tfidf",
            relevance_score=50,
        )
        SuggestionFeedback.objects.create(
            opportunity=opportunity,
            user_action="accepted" if index < 12 else "rejected",
        )

    data = RetrainingPipeline.prepare_training_data("relevance_scorer_v2")
    assert data["training_samples"] == 20
    assert data["positive_samples"] == 12
    assert data["negative_samples"] == 8
    assert {item["label"] for item in data["data"]} == {0, 1}
