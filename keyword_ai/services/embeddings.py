import numpy as np
from sentence_transformers import SentenceTransformer

_embed_model = None


def get_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    Convert a list of strings to a 2D numpy array of embeddings.
    Shape: (len(texts), 384)  ← all-MiniLM-L6-v2 produces 384-dim vectors
    """
    if not texts:
        return np.array([])

    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings


def get_single_embedding(text: str) -> np.ndarray:
    """Convenience wrapper for a single string."""
    return get_embeddings([text])[0]