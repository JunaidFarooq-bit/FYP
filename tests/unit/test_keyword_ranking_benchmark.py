from keyword_ai.services.ranking_benchmark import (
    evaluate_cases,
    is_malformed_keyword,
    precision_at_k,
)


def test_precision_at_k_uses_explicit_acceptance_labels():
    assert precision_at_k(["alpha keyword", "beta keyword"], ["beta keyword"]) == 0.5


def test_malformed_keyword_detection_rejects_fragment_noise():
    assert is_malformed_keyword("operational")
    assert not is_malformed_keyword("workflow automation software")


def test_benchmark_reports_release_metrics():
    metrics = evaluate_cases([
        {
            "predicted": ["workflow automation software", "operational"],
            "accepted": ["workflow automation software"],
        }
    ])
    assert metrics == {
        "cases": 1,
        "precision_at_10": 0.5,
        "acceptance_rate": 0.5,
        "malformed_keyword_rate": 0.5,
    }