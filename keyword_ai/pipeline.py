"""
Main pipeline: call run_keyword_pipeline(url) to get ranked keywords.
"""

from keyword_ai.services.extract_content import extract_content
from keyword_ai.services.keybert_extractor import extract_keywords
from keyword_ai.services.similarity_search import expand_keywords
from keyword_ai.services.relevance_scorer import score_keywords
from keyword_ai.services.llm_refiner import refine_keywords


def run_keyword_pipeline(
    url: str = None,
    text: str = None,       # pass pre-extracted text if you have it already
    page_topic: str = "",
    use_llm: bool = True,
) -> dict:
    """
    Run the full hybrid keyword pipeline.

    Args:
        url:         URL to crawl (or pass text directly)
        text:        Pre-extracted page text (bypasses content extraction)
        page_topic:  Short description of the page topic (improves LLM grouping)
        use_llm:     Set False to skip the OpenAI step (saves API cost in testing)

    Returns a dict with all pipeline outputs.
    """

    # ── Step 1: Content extraction ──────────────────────────────────────────
    if text:
        full_text = text
        meta = {"title": "", "meta_description": "", "full_text": text}
    elif url:
        meta = extract_content(url)
        full_text = meta.get("full_text", "")
        if "error" in meta:
            return {"error": meta["error"]}
    else:
        return {"error": "Provide either a url or text parameter."}

    if len(full_text.strip()) < 50:
        return {"error": "Not enough text content found on the page."}

    # ── Step 2: KeyBERT extraction ───────────────────────────────────────────
    keybert_results = extract_keywords(full_text, top_n=20)
    seed_keywords = [item["keyword"] for item in keybert_results]

    # ── Step 3: Cosine similarity expansion ──────────────────────────────────
    expanded = expand_keywords(seed_keywords, top_k=20)
    expanded_keywords = [item["keyword"] for item in expanded]

    # ── Step 4: Combine & deduplicate ────────────────────────────────────────
    all_keywords = list(dict.fromkeys(seed_keywords + expanded_keywords))

    # ── Step 5: ML relevance scoring ─────────────────────────────────────────
    try:
        scored = score_keywords(all_keywords)
        relevant_keywords = [
            item["keyword"] for item in scored if item["is_relevant"]
        ]
    except FileNotFoundError:
        # Model not trained yet — skip scoring gracefully
        scored = [{"keyword": kw, "relevance_score": 0.5, "is_relevant": True} for kw in all_keywords]
        relevant_keywords = all_keywords

    # ── Step 6: LLM intent grouping ──────────────────────────────────────────
    if use_llm and relevant_keywords:
        llm_result = refine_keywords(relevant_keywords, page_topic=page_topic)
    else:
        llm_result = {
            "groups": {"All": relevant_keywords},
            "focus_keywords": relevant_keywords[:5],
        }

    return {
        "url": url,
        "page_title": meta.get("title", ""),
        "keybert_keywords": keybert_results,
        "expanded_keywords": expanded,
        "scored_keywords": scored,
        "relevant_keywords": relevant_keywords,
        "intent_groups": llm_result.get("groups", {}),
        "focus_keywords": llm_result.get("focus_keywords", []),
    }