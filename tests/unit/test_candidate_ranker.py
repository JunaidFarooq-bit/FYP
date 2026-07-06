import numpy as np

from keyword_ai.services import candidate_ranker


def test_dynamic_ranker_merges_sources_and_ranks_page_evidence(monkeypatch):
    vectors = {
        "patient scheduling": np.array([1.0, 0.0], dtype=np.float32),
        "appointment booking": np.array([0.8, 0.2], dtype=np.float32),
        "affiliate marketing": np.array([0.0, 1.0], dtype=np.float32),
    }
    monkeypatch.setattr(
        candidate_ranker,
        "get_embeddings",
        lambda values: np.asarray([vectors[value] for value in values]),
    )

    ranked = candidate_ranker.rank_evidence_candidates(
        page_summary="Healthcare appointment software",
        content_embedding=np.array([1.0, 0.0], dtype=np.float32),
        candidates=[
            {"keyword": "patient scheduling", "source": "observed_page"},
            {"keyword": "patient scheduling", "source": "observed_serp"},
            {"keyword": "appointment booking", "source": "competitor_heading"},
            {"keyword": "affiliate marketing", "source": "competitor_content"},
        ],
        use_cross_encoder=False,
    )

    assert ranked[0]["keyword"] == "patient scheduling"
    assert ranked[0]["sources"] == ["observed_page", "observed_serp"]
    assert ranked[-1]["keyword"] == "affiliate marketing"
    assert all(item["provenance"] == "dynamic_evidence_ranking" for item in ranked)


def test_dynamic_ranker_returns_empty_without_embedding():
    assert candidate_ranker.rank_evidence_candidates(
        page_summary="page",
        content_embedding=None,
        candidates=[{"keyword": "useful keyword", "source": "observed_page"}],
    ) == []