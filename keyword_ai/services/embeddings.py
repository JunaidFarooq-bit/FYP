"""Shared and versioned embedding utilities for keyword retrieval."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

import numpy as np

from .model_manager import get_embedding_model


EMBEDDING_MODEL_NAME = os.getenv("KEYWORD_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_VERSION = os.getenv("KEYWORD_EMBEDDING_VERSION", "bge-small-en-v1.5-weighted-v1")


def get_model():
    return get_embedding_model(EMBEDDING_MODEL_NAME)


def get_embeddings(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.array([])
    return get_model().encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )


def get_single_embedding(text: str) -> np.ndarray:
    embeddings = get_embeddings([text])
    return embeddings[0] if len(embeddings) else np.array([])


def _body_chunks(text: str, max_words: int = 180, max_chunks: int = 12) -> List[str]:
    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n{2,}|(?<=[.!?])\s+", text or "")
        if paragraph.strip()
    ]
    chunks: List[str] = []
    current: List[str] = []
    current_words = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if current and current_words + len(words) > max_words:
            chunks.append(" ".join(current))
            current, current_words = [], 0
            if len(chunks) >= max_chunks:
                break
        current.append(paragraph)
        current_words += len(words)
    if current and len(chunks) < max_chunks:
        chunks.append(" ".join(current))
    return chunks


def build_page_embedding(
    full_text: str,
    title: str = "",
    meta_description: str = "",
    page_signals: Dict = None,
) -> Tuple[np.ndarray, Dict]:
    """Create a normalized weighted page vector from structural chunks."""
    page_signals = page_signals or {}
    sections: List[str] = []
    weights: List[float] = []
    labels: List[str] = []

    def add(value: str, weight: float, label: str):
        value = " ".join((value or "").split())
        if value:
            sections.append(value)
            weights.append(weight)
            labels.append(label)

    add(title, 3.0, "title")
    add(meta_description, 2.0, "meta_description")
    for heading in (page_signals.get("headings") or [])[:20]:
        add(heading.get("text", "") if isinstance(heading, dict) else str(heading), 2.0, "heading")
    for chunk in _body_chunks(full_text):
        add(chunk, 1.0, "body")

    if not sections:
        return np.array([]), {
            "model": EMBEDDING_MODEL_NAME,
            "version": EMBEDDING_VERSION,
            "chunks": 0,
        }

    vectors = get_embeddings(sections)
    weight_array = np.asarray(weights, dtype=np.float32)
    vector = np.average(vectors, axis=0, weights=weight_array)
    norm = np.linalg.norm(vector)
    if norm:
        vector = vector / norm

    return vector.astype(np.float32), {
        "model": EMBEDDING_MODEL_NAME,
        "version": EMBEDDING_VERSION,
        "chunks": len(sections),
        "chunk_types": {label: labels.count(label) for label in set(labels)},
    }
