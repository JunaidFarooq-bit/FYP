"""
==============================================================
STEP 3 & 4: MODEL TRAINING + FAISS INDEX CREATION
==============================================================

HOW EMBEDDINGS WORK:
--------------------
A Sentence Transformer converts a text string into a dense
numerical vector (e.g., 384 dimensions for "all-MiniLM-L6-v2").

Words with similar meaning end up CLOSE together in this
high-dimensional space. For example:
  "best seo tools"     → [0.12, -0.45, 0.87, ...]
  "top seo software"   → [0.13, -0.43, 0.85, ...]   ← very close!
  "chocolate cake"     → [-0.92, 0.11, -0.34, ...]  ← far away

WHY THIS IS GREAT FOR KEYWORD SUGGESTION:
-----------------------------------------
- Traditional string matching only finds exact/prefix matches.
- Embeddings capture SEMANTIC meaning, so:
    "keyword research" ≈ "finding search terms" ≈ "keyword analysis"
  even though they share no words.
- FAISS (Facebook AI Similarity Search) finds the nearest embedding
  vectors in milliseconds even with millions of entries.

PIPELINE:
  clean_keywords.csv → load keywords → encode with SentenceTransformer
  → save embeddings (.npy) → build FAISS index → save index (.bin)
"""

import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ── Configuration ────────────────────────────────────────────
DATA_DIR          = Path(__file__).parent.parent / "data"
MODELS_DIR        = Path(__file__).parent

KEYWORDS_FILE     = DATA_DIR / "all_keywords.txt"
EMBEDDINGS_FILE   = MODELS_DIR / "keyword_embeddings.npy"
KEYWORDS_JSON     = MODELS_DIR / "keywords.json"
FAISS_INDEX_FILE  = MODELS_DIR / "faiss_index.bin"

# "all-MiniLM-L6-v2" is an excellent balance of:
#   - Speed       : fast inference, small model (~80MB)
#   - Quality     : 384-dim embeddings, strong semantic understanding
#   - License     : Apache 2.0 (free for commercial use)
MODEL_NAME        = "all-MiniLM-L6-v2"
BATCH_SIZE        = 256      # keywords encoded per batch (tune for your RAM)
EMBEDDING_DIM     = 384      # output dimension of all-MiniLM-L6-v2


def load_keywords(filepath: Path) -> list[str]:
    """
    Loads the flat keyword list from a text file (one keyword per line).

    Args:
        filepath: Path to keywords .txt file.

    Returns:
        List of keyword strings.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    print(f"📂 Loaded {len(keywords):,} keywords from {filepath.name}")
    return keywords


def generate_embeddings(
    keywords: list[str],
    model_name: str,
    batch_size: int
) -> np.ndarray:
    """
    Uses SentenceTransformer to encode all keywords into dense vectors.

    The model is downloaded automatically on first run and cached at:
      ~/.cache/torch/sentence_transformers/

    Args:
        keywords  : List of keyword strings.
        model_name: HuggingFace model identifier.
        batch_size: Number of keywords to encode per batch.

    Returns:
        NumPy array of shape (N, EMBEDDING_DIM) as float32.
    """
    print(f"\n🤖 Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"   Encoding {len(keywords):,} keywords (batch_size={batch_size})...")
    print("   This may take a few minutes on CPU...\n")

    embeddings = model.encode(
        keywords,
        batch_size=batch_size,
        show_progress_bar=True,   # prints a tqdm progress bar
        convert_to_numpy=True,    # returns np.ndarray directly
        normalize_embeddings=True # L2-normalize → cosine sim = dot product
    )

    # Cast to float32 — required by FAISS
    embeddings = embeddings.astype(np.float32)

    print(f"\n✅ Embeddings shape: {embeddings.shape}")
    return embeddings


def save_embeddings(
    embeddings: np.ndarray,
    keywords: list[str],
    embeddings_path: Path,
    keywords_path: Path
) -> None:
    """
    Persists embeddings and the corresponding keyword list to disk.

    We save BOTH because we need the keyword strings to map
    FAISS search results (indices) back to human-readable text.

    Args:
        embeddings      : NumPy array (N, D).
        keywords        : List of N keyword strings.
        embeddings_path : Output .npy file path.
        keywords_path   : Output .json file path.
    """
    np.save(embeddings_path, embeddings)
    print(f"✅ Embeddings saved to  : {embeddings_path}")

    with open(keywords_path, "w", encoding="utf-8") as f:
        json.dump(keywords, f, ensure_ascii=False, indent=2)
    print(f"✅ Keywords list saved to: {keywords_path}")


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Creates and populates a FAISS index for fast similarity search.

    INDEX TYPE EXPLANATION:
    -----------------------
    IndexFlatIP  = Inner Product (dot product) index
    Since embeddings are L2-normalized, dot product == cosine similarity.
    This is the simplest, most accurate index (exact search, no approximation).

    For 100K+ keywords, consider IndexIVFFlat (approximate, faster):
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist=100)
        index.train(embeddings)
        index.add(embeddings)
        index.nprobe = 10  # tune for speed/recall tradeoff

    Args:
        embeddings: L2-normalized float32 numpy array (N, D).

    Returns:
        Populated FAISS index.
    """
    dim = embeddings.shape[1]
    print(f"\n🔍 Building FAISS IndexFlatIP (dim={dim}, vectors={len(embeddings):,})...")

    index = faiss.IndexFlatIP(dim)  # Inner Product = cosine sim (normalized vecs)
    index.add(embeddings)

    print(f"✅ FAISS index built. Total vectors: {index.ntotal:,}")
    return index


def save_faiss_index(index: faiss.Index, filepath: Path) -> None:
    """
    Serializes the FAISS index to disk using an atomic write pattern.

    Writes to a .tmp file first, then renames to the final path.
    This prevents a corrupt/empty .bin if the write is interrupted,
    which would cause a 'read error: 0 != 1' on next load.

    Args:
        index   : Populated FAISS index object.
        filepath: Output .bin file path.
    """
    tmp_path = filepath.with_suffix(".tmp")

    try:
        faiss.write_index(index, str(tmp_path))

        # Validate the temp file is non-empty before promoting it
        tmp_size = tmp_path.stat().st_size
        if tmp_size == 0:
            raise RuntimeError(
                "FAISS write_index produced an empty file. "
                "Check available disk space and permissions."
            )

        # Atomic replace — safe on both Windows and Linux
        tmp_path.replace(filepath)

        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"✅ FAISS index saved to : {filepath}  ({size_mb:.1f} MB)")

    except Exception as e:
        # Clean up the temp file if anything went wrong
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(f"Failed to save FAISS index: {e}") from e


def load_faiss_index(filepath: Path) -> faiss.Index:
    """
    Reloads a FAISS index from disk.

    Call this at application startup (once) to avoid re-building every request.

    Args:
        filepath: Path to the saved .bin index file.

    Returns:
        Loaded FAISS index ready for search.
    """
    # Guard against empty/corrupt file before FAISS tries to read it
    if not filepath.exists():
        raise FileNotFoundError(f"FAISS index not found at {filepath}.")

    file_size = filepath.stat().st_size
    if file_size == 0:
        raise RuntimeError(
            f"FAISS index file is empty (0 bytes): {filepath}\n"
            "Delete the file and re-run train_model.py."
        )

    index = faiss.read_index(str(filepath))
    print(f"✅ FAISS index loaded from: {filepath}  ({index.ntotal:,} vectors)")
    return index


def train_pipeline() -> None:
    """Runs the complete training pipeline end-to-end."""

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load keywords
    keywords = load_keywords(KEYWORDS_FILE)

    # 2. Generate embeddings
    embeddings = generate_embeddings(keywords, MODEL_NAME, BATCH_SIZE)

    # 3. Save embeddings + keyword list
    save_embeddings(embeddings, keywords, EMBEDDINGS_FILE, KEYWORDS_JSON)

    # 4. Build FAISS index
    index = build_faiss_index(embeddings)

    # 5. Save FAISS index (atomic write — no more empty .bin files)
    save_faiss_index(index, FAISS_INDEX_FILE)

    print("\n🎉 Training pipeline complete!")
    print(f"   Model          : {MODEL_NAME}")
    print(f"   Keywords       : {len(keywords):,}")
    print(f"   Embedding dim  : {embeddings.shape[1]}")
    print(f"   FAISS vectors  : {index.ntotal:,}")
    print(f"\nFiles created:")
    print(f"   {EMBEDDINGS_FILE}")
    print(f"   {KEYWORDS_JSON}")
    print(f"   {FAISS_INDEX_FILE}")


if __name__ == "__main__":
    train_pipeline()