from keybert import KeyBERT
from .embeddings import get_model as get_embedding_model

# Model loads once and is reused — avoids reloading on every request
_kw_model = None


def get_model() -> KeyBERT:
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT(model=get_embedding_model())
    return _kw_model


def extract_keywords(
    text: str,
    top_n: int = 20,
    keyphrase_ngram_range: tuple = (1, 3),
    stop_words: str = "english",
    diversity: float = 0.5,
) -> list[dict]:
    """
    Extract keywords from text using KeyBERT with MMR (Maximal Marginal Relevance)
    for diversity. Returns a list of dicts: [{"keyword": ..., "score": ...}]
    """
    if not text or len(text.strip()) < 50:
        return []

    model = get_model()

    keywords = model.extract_keywords(
        text,
        keyphrase_ngram_range=keyphrase_ngram_range,
        stop_words=stop_words,
        use_mmr=True,           # reduces redundant keywords
        diversity=diversity,
        top_n=top_n,
    )

    return [{"keyword": kw, "score": round(score, 4)} for kw, score in keywords]