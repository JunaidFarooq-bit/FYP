"""
==============================================================
STEP 1: DATA COLLECTION
==============================================================
This script collects keyword suggestions from Google Autocomplete.
It uses HTTP requests to hit Google's suggest API (no API key needed).

Google Autocomplete API endpoint:
  https://suggestqueries.google.com/complete/search?client=firefox&q=<query>

The response is a JSON array like:
  ["seo tools", ["best seo tools", "free seo tools", ...]]

We iterate over seed keywords and multiple alphabet permutations
(e.g., "seo tools a", "seo tools b", ...) to maximize coverage.
"""

import requests
import json
import time
import csv
import random
import string
from pathlib import Path

# ── Configuration ────────────────────────────────────────────
OUTPUT_FILE = Path(__file__).parent / "raw_keywords.csv"
REQUEST_DELAY = 0.8          # seconds between requests (be polite)
MAX_RETRIES   = 3            # retry failed requests
TIMEOUT       = 8            # seconds before request timeout

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Seed keywords relevant to your SEO tool
SEED_KEYWORDS = [
    "seo tools",
    "keyword research",
    "backlink analysis",
    "on page seo",
    "technical seo",
    "seo audit",
    "rank tracking",
    "competitor analysis",
    "content optimization",
    "link building",
    "local seo",
    "seo for beginners",
    "google search console",
    "site speed optimization",
    "crawl errors",
]


def fetch_autocomplete(query: str) -> list[str]:
    """
    Calls the Google Suggest API for a given query.

    Google returns: [query, [suggestion1, suggestion2, ...], ...]
    We extract only the suggestions list.

    Args:
        query: The search query string.

    Returns:
        A list of autocomplete suggestion strings.
    """
    url = "https://suggestqueries.google.com/complete/search"
    params = {
        "client": "firefox",   # returns clean JSON
        "q": query,
        "hl": "en",            # language
        "gl": "us",            # country
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = json.loads(resp.text)
            # data[1] is the list of suggestions
            return data[1] if len(data) > 1 else []
        except (requests.RequestException, json.JSONDecodeError, IndexError) as e:
            print(f"  [Attempt {attempt+1}] Error for '{query}': {e}")
            time.sleep(REQUEST_DELAY * 2)

    return []


def expand_with_alphabet(seed: str) -> list[str]:
    """
    Generates alphabet-expanded queries to capture more long-tail keywords.

    Example: "seo tools" → ["seo tools a", "seo tools b", ..., "seo tools z"]

    This is a proven technique to extract more autocomplete variants.
    """
    queries = [seed]  # always include the base seed
    for char in string.ascii_lowercase:
        queries.append(f"{seed} {char}")
    return queries


def collect_all_keywords(seeds: list[str]) -> list[dict]:
    """
    Iterates over all seeds, expands them, fetches autocomplete,
    and returns a flat list of {seed_keyword, suggested_keyword} dicts.
    """
    results = []
    total_queries = sum(27 for _ in seeds)  # 26 letters + base
    processed = 0

    print(f"Starting collection for {len(seeds)} seeds ({total_queries} total queries)...\n")

    for seed in seeds:
        queries = expand_with_alphabet(seed)

        for query in queries:
            processed += 1
            suggestions = fetch_autocomplete(query)

            for suggestion in suggestions:
                suggestion = suggestion.strip().lower()
                if suggestion and suggestion != seed:
                    results.append({
                        "seed_keyword": seed,
                        "suggested_keyword": suggestion
                    })

            print(f"[{processed}/{total_queries}] '{query}' → {len(suggestions)} suggestions")

            # Random delay to avoid rate limiting
            time.sleep(REQUEST_DELAY + random.uniform(0, 0.4))

    return results


def save_to_csv(records: list[dict], filepath: Path) -> None:
    """Saves collected keyword pairs to a CSV file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["seed_keyword", "suggested_keyword"])
        writer.writeheader()
        writer.writerows(records)

    print(f"\n✅ Saved {len(records)} keyword pairs to: {filepath}")


if __name__ == "__main__":
    records = collect_all_keywords(SEED_KEYWORDS)
    save_to_csv(records, OUTPUT_FILE)

    print(f"\n📊 Collection Summary:")
    print(f"   Total pairs collected : {len(records)}")
    print(f"   Unique seeds covered  : {len(set(r['seed_keyword'] for r in records))}")
    print(f"   Output file           : {OUTPUT_FILE}")


# ==============================================================
# ALTERNATIVE DATA SOURCES
# ==============================================================
#
# 1. GOOGLE KEYWORD PLANNER EXPORT
#    - Sign in to Google Ads → Tools → Keyword Planner
#    - "Discover new keywords" → enter seeds → Download CSV
#    - The CSV columns you need: "Keyword" (becomes suggested_keyword)
#    - Assign seed_keyword manually or group by ad group
#
# 2. KAGGLE DATASETS
#    - Search: https://www.kaggle.com/datasets?search=seo+keywords
#    - Recommended datasets:
#      * "SEO Keyword Research Dataset" by various authors
#      * "Google Search Terms" datasets
#    - Download, load with pandas, reshape to (seed_keyword, suggested_keyword)
#
# 3. COMBINING SOURCES (recommended for production)
#    Load all CSVs into pandas and concat:
#
#    import pandas as pd
#    df1 = pd.read_csv("autocomplete.csv")
#    df2 = pd.read_csv("keyword_planner_export.csv")
#    df2 = df2.rename(columns={"Keyword": "suggested_keyword"})
#    df2["seed_keyword"] = "your_seed"   # assign manually
#    combined = pd.concat([df1, df2], ignore_index=True)
#    combined.to_csv("raw_keywords.csv", index=False)