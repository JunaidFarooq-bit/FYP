from bs4 import BeautifulSoup

from keyword_ai.services.extract_content import _extract_page_signals
from keyword_ai.services.geo_aeo_analyzer import analyze_aeo, analyze_geo
from keyword_ai.services.traffic_data_providers import SerpAPIProvider


def test_page_evidence_increases_aeo_readiness():
    weak = analyze_aeo("how to improve technical seo", page_text="A short unrelated page.")
    strong = analyze_aeo(
        "how to improve technical seo",
        page_signals={
            "question_headings": ["How do you improve technical SEO?"],
            "concise_answers": ["Technical SEO improves crawling, indexing, speed, and structured data."],
            "schema_types": ["HowTo"],
            "ordered_lists": 1,
            "unordered_lists": 1,
            "tables": 1,
            "author": "SEO Team",
            "external_citations": [{"url": "https://developers.google.com/search"}],
            "modified_at": "2026-07-05",
        },
        page_text="How to improve technical SEO with crawling indexing speed and structured data.",
    )
    assert strong.score > weak.score
    assert strong.readiness_label == "Strong evidence coverage"
    assert any(item["signal"] == "supported_structured_data" for item in strong.evidence)


def test_live_ai_overview_citation_is_observed():
    result = analyze_aeo(
        "what is technical seo",
        page_url="https://example.com/guide",
        serp_data={
            "data_source": "serpapi",
            "has_ai_overview": True,
            "ai_overview_sources": [
                {"link": "https://example.com/guide", "domain": "example.com"}
            ],
        },
    )
    assert result.score_type == "evidence_coverage_with_live_serp"
    assert result.data_status == "observed"
    assert result.observed_visibility["target_domain_cited"] is True


def test_regional_volume_and_local_pack_are_measured_geo_evidence():
    result = analyze_geo(
        "plumber near me",
        regional_volume_data={"NA": 1200},
        target_region="NA",
        page_signals={"has_local_schema": True, "addresses": ["10 Main Street"]},
        serp_data={"data_source": "serpapi", "serp_features": ["local_pack"]},
    )
    assert result.target_region == "NA"
    assert result.data_status == "observed"
    assert result.confidence in {"medium", "high"}
    assert "serpapi" in result.provider_sources


def test_serp_provider_extracts_nested_ai_sources_once():
    payload = {
        "text_blocks": [
            {"references": [{"title": "Example", "link": "https://www.example.com/a"}]},
            {"source": {"url": "https://example.org/b"}},
            {"duplicate": {"link": "https://www.example.com/a"}},
        ]
    }
    sources = SerpAPIProvider._result_sources(payload)
    assert {item["domain"] for item in sources} == {"example.com", "example.org"}
    assert len(sources) == 2


def test_extractor_collects_real_page_signals():
    soup = BeautifulSoup(
        """
        <html lang="en"><head>
          <meta name="author" content="Inshal">
          <script type="application/ld+json">
            {"@context":"https://schema.org","@type":"FAQPage"}
          </script>
        </head><body>
          <h2>What is AEO?</h2>
          <p>Answer engine optimization structures clear, useful and attributable information
             so search and generative systems can retrieve a precise response for a user.</p>
          <ol><li>Research</li><li>Answer</li></ol>
          <a href="https://developers.google.com/search">Google documentation</a>
        </body></html>
        """,
        "html.parser",
    )
    signals = _extract_page_signals(soup, "https://example.com/article")
    assert "FAQPage" in signals["schema_types"]
    assert signals["question_headings"] == ["What is AEO?"]
    assert signals["author"] == "Inshal"
    assert signals["ordered_lists"] == 1
    assert signals["external_citations"][0]["domain"] == "developers.google.com"


def test_generic_organization_schema_is_not_local():
    soup = BeautifulSoup(
        '<script type="application/ld+json">{"@type":"Organization"}</script>',
        "html.parser",
    )
    signals = _extract_page_signals(soup, "https://example.com")
    assert signals["has_local_schema"] is False


def test_traffic_enrichment_uses_offline_bands_without_fake_point_metrics(monkeypatch):
    from keyword_ai.services.traffic_enrichment import TrafficEnricher

    def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM traffic estimation must not be called")

    monkeypatch.setattr(
        "keyword_ai.services.llm_traffic_estimator.estimate_keywords_batch_llm",
        fail_if_called,
    )
    enricher = TrafficEnricher(
        use_google_trends=False,
        use_real_data=False,
        use_llm_estimation=True,
    )
    results = enricher.enrich_keywords([f"keyword {i}" for i in range(12)])
    assert len(results) == 12
    assert all(item.provenance == "dataset_modeled" for item in results)
    assert all(item.monthly_volume is None for item in results)
    assert all(item.cpc_value is None for item in results)
    assert all(item.modeled_range for item in results)


def test_offline_benchmark_is_versioned_and_exposes_evidence():
    from keyword_ai.services.offline_benchmark import classify_keyword_opportunity

    result = classify_keyword_opportunity("best enterprise seo platform")
    assert result["provenance"] == "dataset_modeled"
    assert result["dataset_version"] == "2026-07"
    assert result["commercial_value"] == "Medium"
    assert result["modeled_range"]
    assert result["evidence"]["commercial_modifiers"]


def test_serp_bulk_is_bounded_to_ten_keywords(monkeypatch):
    provider = SerpAPIProvider(api_key="test")
    seen = []

    def fake_fetch(keyword, location="United States", hl="en"):
        seen.append(keyword)
        return {"data_source": "serpapi"}

    monkeypatch.setattr(provider, "get_serp_features", fake_fetch)
    results = provider.get_bulk_serp_features([f"keyword {i}" for i in range(15)])
    assert len(seen) == 10
    assert len(results) == 10


def test_competitor_discovery_uses_observed_serp_results(monkeypatch, settings):
    from keyword_ai.services.competitor_analyzer import get_serp_results

    settings.SERPAPI_KEY = "test"

    def fake_features(self, keyword, location="United States", hl="en"):
        return {
            "organic_results": [
                {
                    "position": 1,
                    "title": "Observed result",
                    "link": "https://competitor.example/guide",
                    "domain": "competitor.example",
                }
            ]
        }

    monkeypatch.setattr(SerpAPIProvider, "get_serp_features", fake_features)
    results = get_serp_results("technical seo")
    assert results[0]["domain"] == "competitor.example"
    assert results[0]["provenance"] == "observed_serp"


def test_serialized_modeled_traffic_never_claims_exact_metrics():
    from keyword_ai.services.traffic_enrichment import enrich_with_traffic_signals

    output = enrich_with_traffic_signals(
        ["technical seo guide"],
        use_google_trends=False,
        use_llm_estimation=False,
    )
    item = output["traffic_prioritized_keywords"][0]
    assert item["provenance"] == "dataset_modeled"
    assert item["monthly_volume"] is None
    assert item["cpc_value"] is None
    assert item["traffic_potential"] is None
    assert output["enrichment_metadata"]["keywords_with_real_data"] == 0


def test_live_serp_evidence_upgrades_competition_not_demand():
    from keyword_ai.services.traffic_enrichment import (
        apply_serp_evidence,
        enrich_with_traffic_signals,
    )

    output = enrich_with_traffic_signals(
        ["best technical seo platform"],
        use_google_trends=False,
        use_llm_estimation=False,
    )
    apply_serp_evidence(output, {
        "best technical seo platform": {
            "data_source": "serpapi",
            "serp_features": ["paid_ads", "ai_overview", "people_also_ask"],
            "organic_results": [
                {"domain": "example-one.com"},
                {"domain": "example-two.com"},
            ],
            "related_searches": ["technical seo software"],
            "people_also_ask": ["What is technical SEO?"],
        }
    })
    item = output["traffic_prioritized_keywords"][0]
    assert item["serp_observed"] is True
    assert item["evidence_provenance"] == "observed_serp"
    assert item["serp_pressure"] == "High"
    assert item["competition_band"] == "High"
    assert item["provenance"] == "dataset_modeled"
    assert item["monthly_volume"] is None
    assert item["cpc_value"] is None


def test_unrelated_concise_answer_does_not_pass_query_answer_check():
    result = analyze_aeo(
        "how to configure canonical tags",
        page_signals={
            "concise_answers": [
                "Email marketing campaigns help teams communicate with customers through newsletters and promotional sequences."
            ],
        },
        page_text="This page discusses email marketing campaigns and newsletters.",
    )
    direct_answer = next(item for item in result.checks if item["id"] == "direct_answer")
    assert direct_answer["status"] == "fail"
    assert result.ai_friendly is False


def test_non_local_query_is_explicitly_not_applicable_for_geo():
    result = analyze_geo("technical seo audit")
    assert result.applicability == "not_applicable"
    assert result.geo_score == 0
    assert result.data_status == "insufficient_evidence"


def test_answer_box_and_organic_visibility_are_observed_separately():
    result = analyze_aeo(
        "what is technical seo",
        page_url="https://example.com/guide",
        page_text="Technical SEO helps search engines crawl and index a website.",
        serp_data={
            "data_source": "serpapi",
            "has_featured_snippet": True,
            "answer_sources": [{"domain": "example.com"}],
            "organic_results": [
                {"position": 3, "domain": "example.com"},
            ],
        },
    )
    assert result.observed_visibility["target_domain_in_answer_box"] is True
    assert result.observed_visibility["target_domain_organic_position"] == 3


def test_extractor_collects_locale_hreflang_and_schema_address():
    soup = BeautifulSoup(
        """
        <html lang="en-GB"><head>
          <link rel="canonical" href="https://example.com/uk/service">
          <link rel="alternate" hreflang="en-US" href="https://example.com/us/service">
          <meta property="og:locale" content="en_GB">
          <script type="application/ld+json">
            {
              "@context":"https://schema.org",
              "@type":"LocalBusiness",
              "address":{
                "@type":"PostalAddress",
                "streetAddress":"10 Main Street",
                "addressLocality":"London",
                "addressCountry":"GB"
              },
              "areaServed":"Greater London"
            }
          </script>
        </head><body><p>Local service page content for customers in London.</p></body></html>
        """,
        "html.parser",
    )
    signals = _extract_page_signals(soup, "https://example.com/uk/service")
    assert signals["language"] == "en-GB"
    assert signals["og_locale"] == "en_GB"
    assert signals["hreflang"][0]["language"] == "en-US"
    assert "London" in signals["addresses"][0]
    assert signals["service_areas"] == ["Greater London"]
    assert signals["valid_json_ld_blocks"] == 1