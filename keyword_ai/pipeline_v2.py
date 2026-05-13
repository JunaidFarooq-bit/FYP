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
from .services.llm_refiner import refine_keywords
from .services.llm_expander import (
    expand_keywords_with_llm,
    analyze_competitor_gaps_with_llm,
    generate_question_keywords,
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
from .ml_models.semantic_mapper import find_semantic_keywords, SemanticKeywordMapper
from .models import ContentAnalysis, KeywordOpportunity, GapAnalysis
from .services.embeddings import get_single_embedding
from .services.rag_retriever import retrieve_similar_analyses, format_rag_context

logger = logging.getLogger(__name__)


def get_content_hash(text: str) -> str:
    """Generate MD5 hash of content for change detection."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def save_content_analysis(url: str, meta: dict, analysis: dict, content_embedding: np.ndarray = None) -> ContentAnalysis:
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
    structure = analysis.get("structure", {})
    
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
    use_advanced_ai: bool = True,  # NEW: Phase 3 AI features
    analyze_competitors: bool = False,
    generate_optimization: bool = False,  # NEW: Generate AI optimization suggestions
    target_audience: str = "",  # NEW: Target audience for AI suggestions
    save_to_db: bool = True,
) -> dict:
    """
    Enhanced keyword pipeline v2 (Phase 1 + Phase 2 ML + Phase 3 AI).
    
    Args:
        url: URL to analyze
        text: Pre-extracted text (alternative to URL)
        page_topic: Topic hint for LLM
        use_llm: Whether to use LLM refinement
        use_advanced_ai: Whether to use Phase 3 AI features (expansion, optimization)
        analyze_competitors: Whether to run competitor analysis (requires SERP API)
        generate_optimization: Whether to generate AI content optimization suggestions
        target_audience: Target audience description (e.g., "beginners", "experts")
        save_to_db: Whether to save results to database
        
    Returns:
        Enhanced result dict with ML analysis and AI-powered recommendations
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
    
    # Step 2: Deep Content Analysis (NEW)
    content_analysis_result = analyze_content(full_text, url)
    
    # Step 3: Get content embedding for ML models (moved before save)
    content_embedding = None
    try:
        content_embedding = get_single_embedding(full_text[:1500])  # First 1500 chars
    except Exception as e:
        logger.warning(f"Could not generate content embedding: {e}")
    
    # Save to database (with embedding for pgvector)
    content_analysis_db = None
    if save_to_db and url:
        try:
            content_analysis_db = save_content_analysis(url, meta, content_analysis_result, content_embedding)
        except Exception as e:
            logger.warning(f"Failed to save content analysis: {e}")
    
    # Step 4: KeyBERT Extraction
    keybert_results = extract_keywords(full_text, top_n=20)
    seed_keywords = [item["keyword"] for item in keybert_results]
    
    # Step 5: Similarity Expansion
    expanded = expand_keywords(seed_keywords, top_k=20)
    expanded_keywords = [item["keyword"] for item in expanded]
    
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
    
    # Step 7: Semantic Keyword Mapping (NEW - Phase 2)
    semantic_keywords = []
    try:
        semantic_keywords = find_semantic_keywords(
            content_text=full_text,
            top_k=20,
            use_cached_index=True
        )
    except Exception as e:
        logger.warning(f"Semantic mapping failed: {e}")
    
    # Step 8: TF-IDF Analysis
    tfidf_results = content_analysis_result.get("tfidf_keywords", [])
    tfidf_keywords = [item["keyword"] for item in tfidf_results[:15]]
    
    # Step 9: Combine all keywords from different sources
    all_keywords = list(dict.fromkeys(
        seed_keywords + 
        expanded_keywords + 
        tfidf_keywords +
        [s["keyword"] for s in generated_suggestions] +
        [s["keyword"] for s in semantic_keywords]
    ))
    
    # Competitor analysis variables (populated in step 10, used in step 11)
    competitor_data = None
    gap_analysis_result = None

    # Step 10: Competitor Analysis (OPTIONAL - runs BEFORE scoring so gap keywords
    # are available as input to the ML relevance scorer in step 11)
    if analyze_competitors and url:
        try:
            target_keywords = [page_topic] if page_topic else [meta.get("title", "")]
            competitor_data = run_competitor_analysis(url, target_keywords, full_text)
            gap_analysis_result = competitor_data.get("gap_analysis", {})

            # Save gap keywords as opportunities
            if content_analysis_db:
                gap_keywords_list = gap_analysis_result.get("gap_keywords", [])
                save_keyword_opportunities(
                    content_analysis_db,
                    gap_keywords_list,
                    "gap",
                    {kw: 75 for kw in gap_keywords_list}
                )
        except Exception as e:
            logger.warning(f"Competitor analysis failed: {e}")

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
    rag_context = ""
    if content_embedding is not None and save_to_db:
        try:
            similar_analyses = retrieve_similar_analyses(
                content_embedding,
                top_k=3,
                min_quality_score=60.0
            )
            rag_context = format_rag_context(similar_analyses, max_context_length=1500)
            logger.info(f"RAG: Retrieved {len(similar_analyses)} similar analyses for context")
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
    
    # Step 13: LLM Refinement with RAG Context
    if use_llm and relevant_keywords:
        llm_result = refine_keywords(relevant_keywords, page_topic=page_topic, context=rag_context)
    else:
        llm_result = {
            "groups": {"All": relevant_keywords},
            "focus_keywords": relevant_keywords[:5],
        }
    
    # Step 14: Phase 3 AI - Advanced LLM Keyword Expansion (NEW)
    llm_expanded_suggestions = []
    question_keywords = []
    ai_gap_analysis = []
    
    if use_advanced_ai and use_llm:
        try:
            # Advanced keyword expansion with reasoning
            llm_expanded_suggestions = expand_keywords_with_llm(
                content_text=full_text,
                existing_keywords=relevant_keywords,
                page_topic=page_topic,
                target_audience=target_audience,
                num_suggestions=15
            )

            # Question-based keyword generation
            question_keywords = generate_question_keywords(
                content_text=full_text,
                page_topic=page_topic,
                num_questions=10
            )

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
                            "relevance_score": s.get("suggestion_score", 50) / 100,
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
        
        # NEW: ML-Generated Keywords
        "ml_generated_suggestions": generated_suggestions[:15],
        "semantic_keywords": semantic_keywords[:15],
        
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
        "pipeline_version": "2.1",
        "phases_enabled": ["phase1_content_analysis", "phase2_ml_models", "phase3_ai_enhancement", "rag_retrieval"],
    }
    
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
