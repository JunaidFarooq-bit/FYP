import os
import joblib
import numpy as np
from .embeddings import get_embeddings

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "relevance_scorer.pkl"
)

_clf = None


def get_classifier():
    global _clf
    if _clf is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run `python keyword_ai/train_model.py` first."
            )
        _clf = joblib.load(MODEL_PATH)
    return _clf


def score_keywords(keywords: list[str]) -> list[dict]:
    """
    Score a list of keywords using the trained Logistic Regression.
    Returns each keyword enriched with 'relevance_score' (0.0–1.0)
    and 'is_relevant' (bool).
    """
    if not keywords:
        return []

    clf = get_classifier()
    embeddings = get_embeddings(keywords)         # (n, 384)
    proba = clf.predict_proba(embeddings)[:, 1]   # probability of class=1 (relevant)

    results = []
    for kw, score in zip(keywords, proba):
        results.append({
            "keyword": kw,
            "relevance_score": round(float(score), 4),
            "is_relevant": bool(score >= 0.5),
        })

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results