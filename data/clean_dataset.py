"""
==============================================================
STEP 2: DATA CLEANING
==============================================================
Cleans the raw keyword dataset using Pandas.

Operations performed:
  1. Load raw CSV
  2. Drop rows with null/empty values
  3. Normalize text (lowercase, strip whitespace, collapse spaces)
  4. Remove duplicates
  5. Filter out very short or very long keywords
  6. Remove non-alphanumeric junk
  7. Export clean dataset + standalone keyword list
"""

import re
import pandas as pd
from pathlib import Path

# ── Configuration ────────────────────────────────────────────
RAW_FILE        = Path(__file__).parent / "raw_keywords.csv"
CLEAN_FILE      = Path(__file__).parent / "clean_keywords.csv"
ALL_KEYWORDS_FILE = Path(__file__).parent / "all_keywords.txt"

MIN_KEYWORD_LENGTH = 3    # characters
MAX_KEYWORD_LENGTH = 80   # characters
MIN_WORD_COUNT     = 1    # words
MAX_WORD_COUNT     = 10   # words


def normalize_keyword(text: str) -> str:
    """
    Normalizes a keyword string:
      - Lowercase
      - Strip leading/trailing whitespace
      - Collapse multiple spaces into one
      - Remove non-alphanumeric characters (except spaces and hyphens)
      - Remove leading/trailing hyphens

    Args:
        text: Raw keyword string.

    Returns:
        Normalized keyword string.
    """
    text = str(text).lower().strip()
    # Remove characters that aren't letters, digits, spaces, or hyphens
    text = re.sub(r"[^a-z0-9\s\-]", "", text)
    # Collapse multiple whitespace into single space
    text = re.sub(r"\s+", " ", text).strip()
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text


def is_valid_keyword(keyword: str) -> bool:
    """
    Validates keyword quality using multiple heuristic checks.

    Filters out:
      - Too short or too long (character count)
      - Too few or too many words
      - Purely numeric strings (e.g., "12345")
      - Keywords with no alphabetic characters at all

    Args:
        keyword: Normalized keyword string.

    Returns:
        True if the keyword passes all quality checks.
    """
    if not keyword:
        return False

    # Character length check
    if not (MIN_KEYWORD_LENGTH <= len(keyword) <= MAX_KEYWORD_LENGTH):
        return False

    words = keyword.split()

    # Word count check
    if not (MIN_WORD_COUNT <= len(words) <= MAX_WORD_COUNT):
        return False

    # Must contain at least one alphabetic character
    if not any(c.isalpha() for c in keyword):
        return False

    # Skip purely numeric tokens
    if keyword.replace(" ", "").isdigit():
        return False

    return True


def clean_dataset(raw_path: Path, clean_path: Path, keywords_path: Path) -> pd.DataFrame:
    """
    Full cleaning pipeline for the raw keyword CSV.

    Pipeline:
      load → drop nulls → normalize → filter → deduplicate → save

    Args:
        raw_path     : Path to raw input CSV.
        clean_path   : Path for cleaned keyword pairs CSV output.
        keywords_path: Path for flat list of all unique keywords (txt).

    Returns:
        Cleaned DataFrame.
    """
    print(f"📂 Loading raw data from: {raw_path}")
    df = pd.read_csv(raw_path, dtype=str)
    print(f"   Raw rows loaded: {len(df):,}")

    # ── Step 1: Drop rows missing required columns ────────────
    required_cols = ["seed_keyword", "suggested_keyword"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: '{col}'")

    before = len(df)
    df.dropna(subset=required_cols, inplace=True)
    print(f"   After dropping nulls: {len(df):,} (removed {before - len(df):,})")

    # ── Step 2: Normalize both columns ───────────────────────
    df["seed_keyword"]      = df["seed_keyword"].apply(normalize_keyword)
    df["suggested_keyword"] = df["suggested_keyword"].apply(normalize_keyword)
    print("   Normalization complete.")

    # ── Step 3: Filter out invalid keywords ──────────────────
    before = len(df)
    valid_seeds      = df["seed_keyword"].apply(is_valid_keyword)
    valid_suggested  = df["suggested_keyword"].apply(is_valid_keyword)
    df = df[valid_seeds & valid_suggested].copy()
    print(f"   After quality filter: {len(df):,} (removed {before - len(df):,})")

    # ── Step 4: Remove duplicate (seed, suggested) pairs ─────
    before = len(df)
    df.drop_duplicates(subset=required_cols, inplace=True)
    print(f"   After deduplication: {len(df):,} (removed {before - len(df):,})")

    # ── Step 5: Remove rows where seed == suggested ───────────
    before = len(df)
    df = df[df["seed_keyword"] != df["suggested_keyword"]].copy()
    print(f"   After removing seed==suggestion rows: {len(df):,} (removed {before - len(df):,})")

    # ── Step 6: Reset index ───────────────────────────────────
    df.reset_index(drop=True, inplace=True)

    # ── Save cleaned pairs CSV ────────────────────────────────
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(clean_path, index=False, encoding="utf-8")
    print(f"\n✅ Clean pairs saved to  : {clean_path}")

    # ── Save flat keyword list (all unique keywords) ──────────
    # This is what we feed to the embedding model.
    # We include both seed and suggested keywords as individual strings.
    all_keywords = pd.concat([
        df["seed_keyword"],
        df["suggested_keyword"]
    ]).drop_duplicates().sort_values().reset_index(drop=True)

    with open(keywords_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_keywords.tolist()))

    print(f"✅ All keywords list saved: {keywords_path}")
    print(f"   Unique keywords total  : {len(all_keywords):,}")

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Prints a brief statistical summary of the cleaned dataset."""
    print("\n📊 Dataset Summary")
    print(f"   Total keyword pairs  : {len(df):,}")
    print(f"   Unique seeds         : {df['seed_keyword'].nunique():,}")
    print(f"   Unique suggestions   : {df['suggested_keyword'].nunique():,}")
    print(f"\n   Top 5 seeds by volume:")
    top = df.groupby("seed_keyword").size().sort_values(ascending=False).head(5)
    for seed, count in top.items():
        print(f"     '{seed}': {count} suggestions")
    print(f"\n   Sample rows:")
    print(df.sample(min(5, len(df))).to_string(index=False))


if __name__ == "__main__":
    df_clean = clean_dataset(RAW_FILE, CLEAN_FILE, ALL_KEYWORDS_FILE)
    print_summary(df_clean)