"""
Enhanced Keyword Suggestion Pipeline v2 (Phase 1 + Phase 2 ML + Phase 3 AI).
Integrates content analysis, ML models, and advanced LLM-powered AI features.
"""

import hashlib
import logging
import numpy as np
from typing import Optional, List, Dict

from .pipeline import run_keyword_pipeline  # Fallback to v1
from .services.extract_content import extract_content
from .services.content_analyzer import analyze_content
from .services.competitor_analyzer import run_competitor_analysis
from .services.keybert_extractor import extract_keywords
from .services.similarity_search import expand_keywords
from .services.relevance_scorer import score_keywords as score_keywords_v1
from .services.llm_expander import (
    expand_keywords_with_llm,
    analyze_competitor_gaps_with_llm,
    get_keyword_clusters_with_llm,
)
from .services.content_optimizer import (
    analyze_content_optimization,
    get_complete_optimization_package,
    generate_section_outline,
)
from .services.intent_classifier import (
    classify_intent,
    classify_batch,
    analyze_content_alignment,
    predict_serp_features,
)
from .ml_models.relevance_scorer_v2 import score_keywords_v2, predict_search_intent
from .ml_models.suggestion_generator import generate_keyword_suggestions

from .models import ContentAnalysis, KeywordOpportunity, GapAnalysis
from .services.embeddings import build_page_embedding, EMBEDDING_VERSION
from .services.candidate_ranker import rank_evidence_candidates
from .services.rag_retriever import retrieve_similar_analyses, format_rag_context
from .services.keyword_filter import decontaminate_pipeline_output
from .services.traffic_enrichment import enrich_with_traffic_signals, apply_serp_evidence
from .services.candidate_quality import filter_candidates
from .services.traffic_data_providers import KeywordDataAggregator
from .services.geo_aeo_analyzer import analyze_geo_aeo, analyze_keywords_batch as analyze_geo_aeo_batch
from .services.traffic_potential_analyzer import (
    calculate_traffic_potential,
    analyze_keywords_batch as analyze_traffic_potential_batch,
)
from .utils.year_injector import inject_in_dict, build_year_context

logger = logging.getLogger(__name__)


def get_content_hash(text: str) -> str:
    """Generate MD5 hash of content for change detection."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def save_content_analysis(
    url: str,
    meta: dict,
    analysis: dict,
    content_embedding: np.ndarray = None,
    embedding_metadata: dict = None,
) -> ContentAnalysis:
    """
    Save or update content analysis in database.
    
    Args:
        url: The analyzed URL
        meta: Extracted metadata (title, description, etc.)
        analysis: Content analysis results
        content_embedding: Optional numpy array embedding for pgvector (384-dim)
        
    Returns:
        ContentAnalysis model instance
    """
    content_hash = get_content_hash(meta.get("full_text", ""))
    
    # Prepare structure data
    structure = dict(analysis.get("structure", {}) or {})
    structure["_embedding"] = {
        "version": EMBEDDING_VERSION,
        **(embedding_metadata or {}),
    }
    
    # Prepare entities
    entities = analysis.get("entities", {})
    
    # Prepare TF-IDF keywords
    tfidf_keywords = analysis.get("tfidf_keywords", [])
    
    # Convert embedding to list for pgvector if provided
    embedding_list = None
    if content_embedding is not None:
        if isinstance(content_embedding, np.ndarray):
            embedding_list = content_embedding.tolist()
        else:
            embedding_list = list(content_embedding)
    elif analysis.get("semantic_embedding") is not None:
        # Fallback to analysis dict if not passed directly
        emb = analysis.get("semantic_embedding")
        if isinstance(emb, np.ndarray):
            embedding_list = emb.tolist()
        elif isinstance(emb, (list, tuple)):
            embedding_list = list(emb)
    
    # Create or update
    content_analysis, created = ContentAnalysis.objects.update_or_create(
        url=url,
        defaults={
            "content_hash": content_hash,
            "title": meta.get("title", ""),
            "meta_description": meta.get("meta_description", ""),
            "word_count": analysis.get("readability", {}).get("word_count", 0),
            "quality_score": analysis.get("quality_score", 0),
            "readability_ease": analysis.get("readability", {}).get("flesch_reading_ease", 0),
            "readability_grade": analysis.get("readability", {}).get("flesch_kincaid_grade", 0),
            "structure_data": structure,
            "entities_data": entities,
            "tfidf_keywords": tfidf_keywords,
            "embedding": embedding_list,  # pgvector VectorField
        }
    )
    
    return content_analysis


def save_keyword_opportunities(
    content_analysis: ContentAnalysis,
    keywords: list,
    keyword_type: str,
    scores: dict = None
):
    """
    Save keyword opportunities to database.
    
    Args:
        content_analysis: The parent ContentAnalysis
        keywords: List of keyword strings or dicts
        keyword_type: Type of keyword (tfidf, gap, llm, etc.)
        scores: Optional dict of keyword -> score
    """
    for kw_data in keywords:
        if isinstance(kw_data, dict):
            keyword = kw_data.get("keyword", "")
            raw_score = kw_data.get("relevance_score", kw_data.get("tfidf_score", 0.5))
            # Scores may be 0-1 (from KeyBERT/TF-IDF) or 0-100 (from ML scorer).
            # Normalise: if the value is <= 1.0 treat it as a fraction and scale to 0-100.
            relevance = raw_score * 100 if raw_score <= 1.0 else raw_score
        else:
            keyword = kw_data
            relevance = scores.get(keyword, 50) if scores else 50
        
        if not keyword:
            continue
        
        # Determine priority based on score
        if relevance >= 80:
            priority = "high"
        elif relevance >= 50:
            priority = "medium"
        else:
            priority = "low"
        
        KeywordOpportunity.objects.update_or_create(
            content_analysis=content_analysis,
            keyword=keyword,
            defaults={
                "keyword_type": keyword_type,
                "relevance_score": relevance,
                "priority": priority,
            }
        )


def run_keyword_pipeline_v2(
    url: str = None,
    text: str = None,
    page_topic: str = "",
    use_llm: bool = True,
    use_advanced_ai: bool = True,  # Phase 3 AI features
    analyze_competitors: bool = False,
    generate_optimization: bool = False,  # Generate AI optimization suggestions
    target_audience: str = "",  # Target audience for AI suggestions
    target_region: str = "GLOBAL",  # NEW v2.2: Geographic region for GEO/AEO + LLM prompts
    save_to_db: bool = True,
) -> dict:
    """
    Enhanced keyword pipeline v2.2 (Phase 1 + Phase 2 ML + Phase 2.5 Traffic +
    Phase 2.6 GEO/AEO + Phase 3 AI).

    Args:
        url: URL to analyze
        text: Pre-extracted text (alternative to URL)
        page_topic: Topic hint for LLM
        use_llm: Whether to use LLM refinement
        use_advanced_ai: Whether to use Phase 3 AI features (expansion, optimization)
        analyze_competitors: Whether to run competitor analysis (requires SERP API)
        generate_optimization: Whether to generate AI content optimization suggestions
        target_audience: Target audience description (e.g., "beginners", "experts")
        target_region: Target geographic region (NA, EU, APAC, LATAM, MEA, GLOBAL).
            Drives GEO/AEO scoring AND LLM expansion prompts.
        save_to_db: Whether to save results to database

    Returns:
        Enhanced result dict with ML analysis, traffic forecasts, GEO/AEO scores,
        and AI-powered recommendations.
    """
    
    # Step 1: Content Extraction
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
    
    # Step 2: Get content embedding for ML models (moved before analysis to reuse)
    content_embedding = None
    embedding_metadata = {}
    try:
        content_embedding, embedding_metadata = build_page_embedding(
            full_text=full_text,
            title=meta.get("title", ""),
            meta_description=meta.get("meta_description", ""),
            page_signals=meta.get("page_signals", {}),
        )
    except Exception as e:
        logger.warning(f"Could not generate content embedding: {e}")
    
    # Step 3: Deep Content Analysis (reuses embedding)
    content_analysis_result = analyze_content(full_text, url, content_embedding=content_embedding)
    
    # Save to database (with embedding for pgvector)
    content_analysis_db = None
    if save_to_db and url:
        try:
            content_analysis_db = save_content_analysis(
                url, meta, content_analysis_result, content_embedding, embedding_metadata
            )
        except Exception as e:
            error_msg = str(e)
            if "column \"embedding\" is of type vector" in error_msg and "jsonb" in error_msg:
                logger.warning(f"pgvector embedding type mismatch - saving without embedding field")
                # Retry without embedding by setting it to None
                content_analysis_db = save_content_analysis(
                    url, meta, content_analysis_result, None, embedding_metadata
                )
            else:
                logger.warning(f"Failed to save content analysis: {e}")
    
    # Step 4: KeyBERT Extraction
    keybert_results = extract_keywords(full_text, top_n=20)
    seed_keywords = [item["keyword"] for item in keybert_results]
    
    # Step 5: Expansion is populated later from observed SERP queries.
    # Modifier-template expansion is intentionally excluded from production output.
    expanded = []
    expanded_keywords = []
    
    # Step 6: ML-Powered Keyword Suggestions (NEW - Phase 2)
    generated_suggestions = []
    try:
        generated_suggestions = generate_keyword_suggestions(
            content_text=full_text,
            seed_keywords=seed_keywords,
            num_suggestions=30,
            content_embedding=content_embedding
        )
    except Exception as e:
        logger.warning(f"Keyword generation failed: {e}")

    # Keep only suggestions extracted from the analyzed page. Synthetic
    # question/modifier templates are not treated as keyword evidence.
    generated_suggestions = [
        suggestion
        for suggestion in generated_suggestions
        if suggestion.get("type") in {"lsi", "question_extracted"}
    ]

    # Step 6.5: Build a small page-derived discovery set. Traffic estimation
    # is intentionally delayed until after dynamic reranking.
    traffic_enriched_suggestions = []
    traffic_analysis = {}
    candidate_diagnostics: List[Dict] = []
    raw_candidates = list(dict.fromkeys(
        seed_keywords
        + [
            item.get("keyword")
            for item in content_analysis_result.get("tfidf_keywords", [])
            if item.get("keyword")
        ]
        + [
            item.get("keyword")
            for item in generated_suggestions
            if item.get("keyword")
        ]
    ))
    grounded_traffic_keywords, candidate_diagnostics = filter_candidates(
        raw_candidates,
        page_text=full_text,
        limit=15,
    )
    traffic_enriched_suggestions = [
        {
            "keyword": keyword,
            "type": "page_derived",
            "provenance": "observed_page",
        }
        for keyword in grounded_traffic_keywords
    ]
    # Steps 6.6-6.7 share one location-aware live SERP fetch. This keeps
    # readiness evidence and traffic forecasts based on the same observation.
    geo_aeo_results: List[Dict] = []
    _serp_features: Dict[str, Dict] = {}
    _trend_evidence: Dict[str, Dict] = {}
    _region_locations = {
        "NA": "United States", "EU": "United Kingdom",
        "APAC": "Singapore", "LATAM": "Brazil",
        "MEA": "United Arab Emirates", "GLOBAL": "United States",
    }
    _region_geo = {
        "NA": "US", "EU": "GB", "APAC": "SG",
        "LATAM": "BR", "MEA": "AE", "GLOBAL": "",
    }
    keywords_for_geo_aeo = list(dict.fromkeys(
        s.get("keyword")
        for s in (traffic_enriched_suggestions or generated_suggestions)
        if s.get("keyword")
    ))
    try:
        if keywords_for_geo_aeo:

            _aggregator = KeywordDataAggregator()
            if _aggregator.serp_provider.enabled:
                try:
                    _serp_features = _aggregator.get_serp_features_bulk(
                        keywords_for_geo_aeo[:3],
                        location=_region_locations.get((target_region or "GLOBAL").upper(), "United States"),
                    )
                    logger.info(
                        "SerpAPI: fetched evidence for %s keywords in region=%s",
                        len(_serp_features),
                        target_region,
                    )
                except Exception as _se:
                    logger.warning(f"SerpAPI SERP feature fetch failed: {_se}")

    except Exception as e:
        logger.warning(f"GEO/AEO analysis failed: {e}")

    traffic_potential_results: List[Dict] = []
    _geo_aeo_by_kw: Dict[str, Dict] = {}
    _traffic_potential_by_kw: Dict[str, Dict] = {}

    # Observed query candidates from live related searches and PAA.
    observed_serp_keywords = list(dict.fromkeys(
        candidate
        for serp in _serp_features.values()
        for candidate in (
            (serp.get("related_searches") or [])
            + (serp.get("people_also_ask") or [])
        )
        if candidate
    ))

    expanded = [
        {
            "keyword": keyword,
            "similarity_score": None,
            "source": "serpapi",
            "provenance": "observed_serp",
        }
        for keyword in observed_serp_keywords
    ]
    expanded_keywords = observed_serp_keywords

    # Step 7: Build one domain-specific candidate pool. The old static
    # SEO vocabulary is intentionally excluded from production.
    tfidf_results = content_analysis_result.get("tfidf_keywords", [])
    tfidf_keywords = [item["keyword"] for item in tfidf_results[:15]]

    competitor_data = None
    gap_analysis_result = None
    # Pre-define target_keywords unconditionally for competitor analysis.
    target_keywords: List[str] = (
        [page_topic] if page_topic
        else ([meta.get("title", "")] if meta.get("title") else seed_keywords[:5])
    )

    if url and _serp_features:
        try:
            observed_targets = [
                keyword for keyword in keywords_for_geo_aeo[:3]
                if keyword in _serp_features
            ]
            competitor_data = run_competitor_analysis(
                url,
                observed_targets or target_keywords,
                full_text,
                serp_features=_serp_features,
            )
            gap_analysis_result = competitor_data.get("gap_analysis", {})
            if content_analysis_db:
                gap_keywords_list = gap_analysis_result.get("gap_keywords", [])
                save_keyword_opportunities(
                    content_analysis_db,
                    gap_keywords_list,
                    "gap",
                    {kw: 75 for kw in gap_keywords_list},
                )
        except Exception as e:
            logger.warning("Competitor analysis failed: %s", e)

    evidence_candidates = []

    def _add_candidates(values, source):
        for value in values:
            keyword = value.get("keyword") if isinstance(value, dict) else value
            if keyword:
                evidence_candidates.append({"keyword": keyword, "source": source})

    _add_candidates(seed_keywords, "keybert")
    _add_candidates(tfidf_keywords, "tfidf")
    _add_candidates(observed_serp_keywords, "observed_serp")
    _add_candidates(
        [item.get("keyword") for item in generated_suggestions],
        "observed_page",
    )

    page_signals = meta.get("page_signals", {}) or {}
    _add_candidates([
        heading.get("text", "") if isinstance(heading, dict) else heading
        for heading in (page_signals.get("headings", []) or [])
    ], "observed_page")

    if competitor_data:
        for competitor in competitor_data.get("competitors", []):
            _add_candidates([
                heading.get("text", "")
                for heading in competitor.get("headings", [])
                if isinstance(heading, dict)
            ], "competitor_heading")
            _add_candidates(
                competitor.get("top_content_keywords", []),
                "competitor_content",
            )

    page_summary = "\n".join(filter(None, [
        meta.get("title", ""),
        meta.get("meta_description", ""),
        full_text[:6000],
    ]))
    semantic_keywords = []
    try:
        semantic_keywords = rank_evidence_candidates(
            page_summary=page_summary,
            content_embedding=content_embedding,
            candidates=evidence_candidates,
            top_k=30,
        )
    except Exception as e:
        logger.warning("Dynamic candidate ranking failed: %s", e)

    ranked_candidates = [item["keyword"] for item in semantic_keywords]
    if not ranked_candidates:
        ranked_candidates = [item["keyword"] for item in evidence_candidates]
    all_keywords, final_candidate_diagnostics = filter_candidates(
        ranked_candidates,
        page_text=full_text,
        limit=30,
    )
    candidate_diagnostics.extend(final_candidate_diagnostics)

    # Validate only the final top ten. Discovery queries are cached and reused.
    final_serp_keywords = all_keywords[:10]
    try:
        final_aggregator = KeywordDataAggregator()
        if final_serp_keywords and final_aggregator.serp_provider.enabled:
            final_serp = final_aggregator.get_serp_features_bulk(
                final_serp_keywords,
                location=_region_locations.get(
                    (target_region or "GLOBAL").upper(), "United States"
                ),
            )
            final_trends = final_aggregator.serp_provider.get_trends_scores_bulk(
                final_serp_keywords,
                geo=_region_geo.get((target_region or "GLOBAL").upper(), ""),
            )
            _serp_features.update(final_serp)
            _trend_evidence.update(final_trends)

        traffic_analysis = enrich_with_traffic_signals(
            keywords=all_keywords[:15],
            page_topic=page_topic,
            target_audience=target_audience,
        )
        traffic_analysis = apply_serp_evidence(
            traffic_analysis, _serp_features, _trend_evidence
        )
        traffic_enriched_suggestions = [
            {
                "keyword": item["keyword"],
                "type": "evidence_ranked",
                "provenance": item.get("provenance", "insufficient_evidence"),
                "traffic_signals": item,
            }
            for item in traffic_analysis.get("traffic_prioritized_keywords", [])
        ]
        traffic_by_kw = {
            item["keyword"]: item
            for item in traffic_analysis.get("traffic_prioritized_keywords", [])
        }
        geo_aeo_results = analyze_geo_aeo_batch(
            keywords=all_keywords[:15],
            regional_volume_data={
                kw: traffic_by_kw.get(kw, {}).get("regional_volumes", {})
                for kw in all_keywords[:15]
            },
            page_signals=page_signals,
            page_text=full_text,
            target_region=target_region,
            serp_data_by_keyword=_serp_features,
            page_url=url or "",
        )
        _geo_aeo_by_kw = {item["keyword"]: item for item in geo_aeo_results}
        logger.info(
            "GEO/AEO evidence audit: analyzed %s final-ranked keywords for region=%s",
            len(geo_aeo_results),
            target_region,
        )

        measured_forecasts = []
        for item in traffic_analysis.get("traffic_prioritized_keywords", []):
            if item.get("provenance") != "measured":
                continue
            keyword = item.get("keyword")
            serp = _serp_features.get(keyword, {})
            measured_forecasts.append({
                "keyword": keyword,
                "monthly_volume": item.get("monthly_volume"),
                "intent": item.get("intent", "informational"),
                "has_ai_overview": serp.get("has_ai_overview", False),
                "has_real_data": True,
                "serp_dominated_by_competitors": (item.get("competition_index") or 0) >= 0.7,
                "ctr_trend": item.get("ctr_trend", "stable"),
            })
        traffic_potential_results = analyze_traffic_potential_batch(measured_forecasts)
        _traffic_potential_by_kw = {
            item["keyword"]: item for item in traffic_potential_results
        }
    except Exception as e:
        logger.warning("Final live-evidence enrichment failed: %s", e)
    # Step 11: Multi-Factor ML Relevance Scoring (NEW - Phase 2)
    # Gap keywords from step 10 are now available for scoring.
    try:
        scored = score_keywords_v2(
            keywords=all_keywords,
            content_embedding=content_embedding,
            content_text=full_text,
            gap_keywords=gap_analysis_result.get("gap_keywords", []) if gap_analysis_result else [],
            high_priority_gaps=gap_analysis_result.get("high_priority_gaps", []) if gap_analysis_result else [],
            use_ml_model=True
        )
        relevant_keywords = [
            item["keyword"] for item in scored if item["is_relevant"]
        ]

        # Fallback: If no keywords meet threshold, take top 10 by score
        if not relevant_keywords and scored:
            logger.warning("No keywords met relevance threshold, using top 10 by score")
            relevant_keywords = [item["keyword"] for item in scored[:10]]
    except Exception as e:
        logger.warning(f"V2 scoring failed, falling back to V1: {e}")
        try:
            scored = score_keywords_v1(all_keywords)
            relevant_keywords = [item["keyword"] for item in scored if item["is_relevant"]]
            if not relevant_keywords and scored:
                relevant_keywords = [item["keyword"] for item in scored[:10]]
        except Exception:
            scored = [{"keyword": kw, "relevance_score": 50.0, "is_relevant": True} for kw in all_keywords]
            relevant_keywords = all_keywords
    
    # Step 12: RAG - Retrieve similar content for context augmentation
    # NOW includes traffic signals as additional context for better LLM ranking
    rag_context = ""
    has_rag_history = False
    if content_embedding is not None and save_to_db:
        try:
            history_query = KeywordOpportunity.objects.filter(
                is_accepted=True,
                content_analysis__structure_data___embedding__version=EMBEDDING_VERSION,
            )
            if url:
                history_query = history_query.exclude(content_analysis__url=url)
            has_rag_history = history_query.exists()
        except Exception as e:
            logger.debug("RAG eligibility check failed: %s", e)

    if content_embedding is not None and save_to_db and has_rag_history:
        try:
            similar_analyses = retrieve_similar_analyses(
                content_embedding,
                top_k=3,
                min_quality_score=60.0,
                exclude_url=url,
                embedding_version=EMBEDDING_VERSION,
            )
            rag_context = format_rag_context(similar_analyses, max_context_length=1500)
            logger.info(f"RAG: Retrieved {len(similar_analyses)} similar analyses for context")
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
    
    # Step 13: LLM Refinement with RAG Context + Traffic Signals
    # Pass traffic-enriched context to LLM for real-number-based ranking
    traffic_context = ""
    if traffic_analysis.get("traffic_prioritized_keywords"):
        top_traffic = traffic_analysis["traffic_prioritized_keywords"][:10]
        traffic_context = "\n## Keyword Opportunity Context (source-aware)\n"
        for item in top_traffic:
            traffic_context += f"- {item['keyword']}: Demand band: {item['demand_level']}, Source: {item['provenance']}, Priority: {item['priority_score']}\n"
    
    combined_context = f"{rag_context}\n{traffic_context}" if traffic_context else rag_context
    
    # Intent grouping is deterministic and already available from the local
    # relevance scorer; no extra LLM round trip is needed.
    intent_groups: Dict[str, List[str]] = {}
    score_by_keyword = {item.get("keyword"): item for item in scored}
    for keyword in relevant_keywords:
        intent = score_by_keyword.get(keyword, {}).get("search_intent", "informational")
        intent_groups.setdefault(str(intent).title(), []).append(keyword)
    llm_result = {
        "groups": intent_groups or {"All": relevant_keywords},
        "focus_keywords": relevant_keywords[:5],
        "raw": relevant_keywords,
        "provenance": "local_intent_classifier",
    }
    # Step 14: Phase 3 AI - Advanced LLM Keyword Expansion (NEW)
    llm_expanded_suggestions = []
    question_keywords = []
    ai_gap_analysis = []
    
    if use_advanced_ai and use_llm:
        try:
            # FIX 4: Pass business metadata to LLM for context grounding
            page_metadata = {
                "title": meta.get("title", ""),
                "meta_description": meta.get("meta_description", ""),
                "og_tags": meta.get("og_tags", {}),
            }
            
            # Advanced keyword expansion with reasoning (GEO + year-aware)
            llm_expanded_suggestions = expand_keywords_with_llm(
                content_text=full_text,
                existing_keywords=relevant_keywords,
                page_topic=page_topic,
                target_audience=target_audience,
                num_suggestions=15,
                page_metadata=page_metadata,
                target_region=target_region,
            )

            # Prefer observed PAA and visible page questions over invented
            # question metrics or snippet answers.
            observed_questions = list(dict.fromkeys(
                question
                for serp in _serp_features.values()
                for question in (serp.get("people_also_ask") or [])
                if question
            ))
            page_questions = meta.get("page_signals", {}).get("question_headings", [])
            question_keywords = [
                {
                    "question": question,
                    "type": question.split()[0].title() if question.split() else "Question",
                    "search_volume": None,
                    "answer": None,
                    "format": None,
                    "source": (
                        "observed_serp"
                        if question in observed_questions
                        else "observed_page"
                    ),
                    "keyword_type": "question",
                    "provenance": (
                        "observed_serp"
                        if question in observed_questions
                        else "observed_page"
                    ),
                }
                for question in list(dict.fromkeys(observed_questions + page_questions))[:10]
            ]
            # AI-powered gap analysis if competitor data available
            if gap_analysis_result and gap_analysis_result.get("high_priority_gaps"):
                ai_gap_analysis = analyze_competitor_gaps_with_llm(
                    user_content=full_text,
                    competitor_keywords=gap_analysis_result.get("gap_keywords", []),
                    user_keywords=relevant_keywords,
                    page_topic=page_topic
                )
        except Exception as e:
            logger.warning(f"Advanced AI features failed: {e}")

    # Step 15: Phase 3 AI - Enhanced Intent Classification (NEW)
    intent_analysis = {}
    intent_classifications = []

    try:
        intent_classifications = classify_batch(llm_result.get("focus_keywords", [])[:10])
        intent_analysis = analyze_content_alignment(
            content_text=full_text,
            target_keywords=llm_result.get("focus_keywords", [])[:10]
        )
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")

    # Step 16: Phase 3 AI - Content Optimization (NEW - optional)
    optimization_package = {}

    if generate_optimization and use_advanced_ai:
        try:
            optimization_package = get_complete_optimization_package(
                content_text=full_text,
                target_keywords=llm_result.get("focus_keywords", [])[:10],
                current_title=meta.get("title", ""),
                current_meta_desc=meta.get("meta_description", ""),
                page_topic=page_topic,
                content_type="blog_post" if len(full_text) > 1000 else "landing_page"
            )
        except Exception as e:
            logger.warning(f"Content optimization failed: {e}")

    # Step 17: Phase 3 AI - SERP Feature Prediction (NEW)
    serp_predictions = {}

    try:
        for kw in llm_result.get("focus_keywords", [])[:5]:
            serp_predictions[kw] = predict_serp_features(kw)
    except Exception as e:
        logger.warning(f"SERP prediction failed: {e}")
    
    # Step 18: Save all keyword opportunities to database
    if content_analysis_db and save_to_db:
        try:
            # Save KeyBERT keywords
            save_keyword_opportunities(content_analysis_db, keybert_results, "keybert")
            
            # Save expanded keywords
            save_keyword_opportunities(
                content_analysis_db,
                [{"keyword": k, "relevance_score": 0.6} for k in expanded_keywords],
                "expanded"
            )
            
            # Save TF-IDF keywords
            save_keyword_opportunities(content_analysis_db, tfidf_results[:10], "tfidf")
            
            # Save LLM focus keywords
            save_keyword_opportunities(
                content_analysis_db,
                [{"keyword": k, "relevance_score": 0.9} for k in llm_result.get("focus_keywords", [])],
                "focus"
            )
            
            # Save ML-generated suggestions
            if generated_suggestions:
                save_keyword_opportunities(
                    content_analysis_db,
                    [
                        {
                            "keyword": s["keyword"],
                            "relevance_score": s.get("suggestion_score", 50),
                            "ai_reasoning": f"AI-generated: {s.get('type', 'suggestion')}"
                        }
                        for s in generated_suggestions[:20]
                    ],
                    "ml_generated"
                )
            
            # Save semantic keywords
            if semantic_keywords:
                save_keyword_opportunities(
                    content_analysis_db,
                    [
                        {
                            "keyword": s["keyword"],
                            "relevance_score": s.get("similarity_score", 0.5),
                            "ai_reasoning": "Semantically matched to content"
                        }
                        for s in semantic_keywords[:15]
                    ],
                    "semantic"
                )
        except Exception as e:
            logger.warning(f"Failed to save keyword opportunities: {e}")
    
    # Merge GEO/AEO + traffic potential into each scored keyword for downstream UI
    try:
        for item in scored:
            kw = item.get("keyword")
            if not kw:
                continue
            geo_aeo = _geo_aeo_by_kw.get(kw)
            if geo_aeo:
                item["geo_data"] = geo_aeo.get("geo_data", {})
                item["aeo_signals"] = geo_aeo.get("aeo_signals", {})
            tp = _traffic_potential_by_kw.get(kw)
            if tp:
                item["estimated_ctr"] = tp.get("estimated_ctr", {})
                item["traffic_potential"] = tp.get("traffic_potential", {})
                item["sge_impact"] = tp.get("sge_impact", {})
                item["seasonal_adjustment"] = tp.get("seasonal_adjustment")
                item["risk_flags"] = tp.get("risk_flags", [])
    except Exception as e:
        logger.warning(f"Failed to merge GEO/AEO + traffic potential into scored keywords: {e}")

    # Build enhanced response
    result = {
        # Original data
        "url": url,
        "page_title": meta.get("title", ""),
        "keybert_keywords": keybert_results,
        "expanded_keywords": expanded,
        "scored_keywords": scored,
        "relevant_keywords": relevant_keywords,
        "intent_groups": llm_result.get("groups", {}),
        "focus_keywords": llm_result.get("focus_keywords", []),
        
        # NEW: Content Analysis
        "content_analysis": {
            "quality_score": content_analysis_result.get("quality_score", 0),
            "readability": content_analysis_result.get("readability", {}),
            "structure": content_analysis_result.get("structure", {}),
            "entities": content_analysis_result.get("entities", {}),
            "word_count": content_analysis_result.get("readability", {}).get("word_count", 0),
        },
        
        # NEW: ML-Generated Keywords (Traffic-Enriched)
        "ml_generated_suggestions": traffic_enriched_suggestions[:15] if traffic_enriched_suggestions else generated_suggestions[:15],
        "traffic_analysis": traffic_analysis,
        "candidate_quality": {
            "accepted": len([item for item in candidate_diagnostics if item.get("accepted")]),
            "rejected": len([item for item in candidate_diagnostics if not item.get("accepted")]),
            "diagnostics": candidate_diagnostics,
        },
        "traffic_methodology": {
            "measured_values_require_provider": True,
            "modeled_values_are_ranges": True,
            "offline_dataset_version": "2026-07",
            "provenance_types": [
                "measured", "observed_serp", "dataset_modeled",
                "llm_estimated", "heuristic_fallback",
            ],
        },
        "semantic_keywords": semantic_keywords[:15],

        # NEW v2.2: GEO + AEO Signals (Phase 2.6)
        "geo_aeo_analysis": {
            "target_region": target_region,
            "keywords": geo_aeo_results[:20],
        },

        # NEW v2.2: Traffic Potential Forecasts (Phase 2.7)
        "traffic_potential_forecast": traffic_potential_results[:20],
        
        # NEW: TF-IDF Keywords
        "tfidf_keywords": tfidf_results[:10],
        
        # NEW: Competitor Analysis (if enabled)
        "competitor_analysis": competitor_data,
        "gap_keywords": gap_analysis_result.get("gap_keywords", []) if gap_analysis_result else [],
        "high_priority_gaps": gap_analysis_result.get("high_priority_gaps", []) if gap_analysis_result else [],
        
        # NEW: Enhanced Suggestions with reasoning
        "suggestions": generate_suggestions(
            content_analysis_result,
            llm_result.get("focus_keywords", []),
            gap_analysis_result.get("high_priority_gaps", []) if gap_analysis_result else []
        ),
        
        # Phase 3 AI: Advanced LLM Features
        "ai_expanded_keywords": llm_expanded_suggestions[:10] if llm_expanded_suggestions else [],
        "question_keywords": question_keywords[:8] if question_keywords else [],
        "ai_gap_analysis": ai_gap_analysis[:5] if ai_gap_analysis else [],
        
        # Phase 3 AI: Enhanced Intent Analysis
        "intent_classifications": intent_classifications,
        "intent_analysis": intent_analysis,
        "intent_alignment_score": intent_analysis.get("alignment_score", 0) if intent_analysis else 0,
        
        # Phase 3 AI: SERP Predictions
        "serp_predictions": serp_predictions,
        
        # Phase 3 AI: Content Optimization (if requested)
        "content_optimization": optimization_package if generate_optimization else None,
        
        # RAG: Retrieval-Augmented Generation metadata
        "rag_enabled": bool(rag_context),
        "rag_context_preview": rag_context[:500] + "..." if len(rag_context) > 500 else rag_context,
        
        # Metadata
        "pipeline_version": "2.2",
        "phases_enabled": [
            "phase1_content_analysis",
            "phase2_ml_models",
            "phase2.5_traffic_enrichment",
            "phase2.6_geo_aeo",
            "phase2.7_ctr_traffic_potential",
            "phase3_ai_enhancement",
            "rag_retrieval",
        ],
        "context": {
            "target_region": target_region,
            **build_year_context(),
        },
    }

    # FIX 5: Decontaminate output - remove gambling/adult/pharma keywords
    result = decontaminate_pipeline_output(result)
    if result.get("blocked_keywords_count", 0) > 0:
        logger.info(f"Decontamination removed {result['blocked_keywords_count']} blocked keywords")

    # Final year injection pass — ensures no stale year references reach the UI
    try:
        result = inject_in_dict(result)
    except Exception as e:
        logger.warning(f"Final year injection failed: {e}")

    return result


def generate_suggestions(content_analysis: dict, focus_keywords: list, gap_keywords: list) -> list:
    """
    Generate actionable suggestions based on analysis.
    
    Returns list of suggestion dicts with reasoning.
    """
    suggestions = []
    
    # Quality-based suggestions
    quality_score = content_analysis.get("quality_score", 0)
    if quality_score < 50:
        suggestions.append({
            "type": "improvement",
            "priority": "high",
            "title": "Improve Content Quality",
            "description": f"Current quality score is {quality_score}/100. Consider expanding content, improving readability, and adding more structured formatting.",
            "action": "Expand content to at least 300 words with clear headings and bullet points."
        })
    
    # Readability suggestions
    readability = content_analysis.get("readability", {})
    if readability.get("flesch_reading_ease", 50) < 30:
        suggestions.append({
            "type": "readability",
            "priority": "medium",
            "title": "Improve Readability",
            "description": "Content is difficult to read. Consider simplifying language and shortening sentences.",
            "action": "Break long sentences and use simpler vocabulary."
        })
    
    # Keyword suggestions
    for kw in focus_keywords[:5]:
        suggestions.append({
            "type": "keyword",
            "priority": "high",
            "keyword": kw,
            "title": f"Target Focus Keyword: '{kw}'",
            "description": f"This keyword is highly relevant to your content and has good semantic alignment.",
            "action": f"Add '{kw}' to your H1, first paragraph, and at least one H2 heading."
        })
    
    # Gap-based suggestions
    for gap in gap_keywords[:5]:
        suggestions.append({
            "type": "gap",
            "priority": "medium",
            "keyword": gap,
            "title": f"Close Competitor Gap: '{gap}'",
            "description": f"Competitors are ranking for this keyword but your content doesn't target it.",
            "action": f"Add a section about '{gap}' to capture this traffic opportunity."
        })
    
    return suggestions


def get_historical_analysis(url: str) -> Optional[ContentAnalysis]:
    """
    Retrieve historical analysis for a URL.
    
    Args:
        url: The URL to look up
        
    Returns:
        ContentAnalysis instance or None
    """
    try:
        return ContentAnalysis.objects.get(url=url)
    except ContentAnalysis.DoesNotExist:
        return None


def compare_with_previous(url: str, new_analysis: dict) -> dict:
    """
    Compare new analysis with previous version.
    
    Returns:
        Dict with changes and improvements
    """
    previous = get_historical_analysis(url)
    
    if not previous:
        return {"is_new": True, "changes": {}}
    
    changes = {
        "quality_score_change": new_analysis.get("quality_score", 0) - previous.quality_score,
        "word_count_change": new_analysis.get("readability", {}).get("word_count", 0) - previous.word_count,
        "content_changed": previous.content_hash != get_content_hash(new_analysis.get("full_text", "")),
    }
    
    return {
        "is_new": False,
        "previous_analysis_date": previous.analyzed_at,
        "changes": changes,
    }
