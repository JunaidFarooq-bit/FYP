# Keyword Suggestion Feature - Technical Documentation

## What's New (v2.2)

### 🚦 Traffic Signal Framework (Phase 2.5)
**Real keyword data integration** — Get actual traffic numbers instead of estimates:
- **Monthly volume**: Exact searches (e.g., "12,500/mo")
- **Difficulty score**: 0-100 ranking difficulty
- **CPC value**: Cost-per-click in USD
- **Trend status**: 🔥 TRENDING NOW / 📈 RISING / ➡️ STABLE / 📉 DECLINING
- **Data providers**: SEMrush, DataForSEO, Serpstat + Google Trends

### 🌍 GEO + AEO Signals (Phase 2.6) — NEW
**Per-keyword geographic and answer-engine signals:**
- **GEO scope detection**: Classifies each keyword as local / regional / national / international
- **Location modifier detection**: "near me", city names, country codes
- **Regional volume breakdown**: Per-region volume data when available from providers
- **AEO (Answer Engine Optimization) score**: 0–100 readiness for ChatGPT/Gemini/Copilot answers
- **Content format suggestions**: FAQ, definition, list, tutorial, comparison
- **`target_region` API parameter**: `NA | EU | APAC | LATAM | MEA | GLOBAL`

### � CTR + Traffic Potential Forecast (Phase 2.7) — NEW
**Position-based CTR curves with SGE and seasonal adjustment:**
- **Industry-calibrated curves**: Blended from AWR 2024, Sistrix 2023, Backlinko 2024
- **Google AI Overview impact**: Automatic CTR reduction by intent when AI Overview present
- **Seasonal multipliers**: November (+20%) to July (-6%) adjustments
- **Per-position traffic forecast**: Rank 1 / 3 / 5 / 10 traffic estimates
- **Confidence scores**: Based on data quality (real vs. estimated) and SGE variance
- **Risk flags**: `ai_overview_present`, `high_serp_competition`, `declining_ctr_trend`

### 🤖 LLM Prompt Upgrades (Phase 2.3) — NEW
- **GEO-aware templates**: YAML-driven regional prompts (NA, EU, APAC, LATAM, MEA, GLOBAL)
- **Dynamic year injection**: All LLM outputs use `{current_year}` — never stale years
- **AEO prompt add-ons**: Guides LLM to generate AI-answer-friendly keywords
- **Model fallback chain**: `gpt-4o → gpt-4-turbo → gpt-4 → gpt-3.5-turbo`

### 🐛 Bug Fixes
- **`target_keywords` NameError**: Pre-defined unconditionally outside `if analyze_competitors` block
- **OpenAI default model**: Upgraded from `gpt-4o-mini` → `gpt-4o`

### �📊 Enhanced Output
- **Traffic potential**: Estimated traffic if ranked #1, #3, #5, #10
- **Quick wins**: Easy-to-rank keywords highlighted
- **Topic clusters**: Pillar + cluster visualization
- **Priority scores**: Calculated with real traffic data + CTR curve

### 🔌 New API Endpoint
```
POST /api/keywords/traffic-analysis/
```
Standalone traffic signal analysis for any keyword list.

---

## Overview

The Keyword Suggestion Feature is an AI-powered SEO tool that analyzes web content and generates relevant keyword recommendations. It uses a multi-phase pipeline combining ML models, semantic analysis, LLM augmentation, RAG (Retrieval-Augmented Generation), and **real traffic data**. The system now supports **actual keyword volume** from SEMrush, DataForSEO, and Serpstat APIs.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ /api/keywords/     │  │ /api/keywords/v2/│  │ /api/keywords/   │      │
│  │ (Basic V1)         │  │ (Enhanced V2)      │  │ feedback/          │      │
│  │                    │  │ • use_advanced_ai  │  │                    │      │
│  │ • URL/Text input   │  │ • analyze_competitors│ • User feedback    │      │
│  │ • Basic keywords   │  │ • optimization     │  • Accept/Reject     │      │
│  └─────────┬────────┘  └─────────┬────────┘  └─────────┬────────┘      │
└────────────┼─────────────────────┼─────────────────────┼───────────────┘
             │                     │                     │
             ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE V2                                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: Content Extraction & Analysis                            │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │ │ 1. Extract  │→ │ 2. Content  │→ │ 3. Generate │              │   │
│  │ │    Content  │    Analyzer   │    Embedding  │              │   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: ML-Powered Keyword Generation                            │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│   │
│  │ │ 4. KeyBERT  │→ │ 5. Similarity│→ │ 6. ML Sugg. │→ │ 7. Sem.  ││   │
│  │ │ Extraction  │    Expansion    │    Generator    │    Mapper  ││   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2.5: Traffic Enrichment (Real Data Providers)              │   │
│  │ ┌─────────────────────────────────────────────────────────────┐│   │
│  │ │ • Fetch real volume from SEMrush/DataForSEO/Serpstat        ││   │
│  │ │ • Google Trends for trending signals                        ││   │
│  │ │ • Calculate priority scores with real numbers               ││   │
│  │ └─────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2.6: GEO + AEO Analysis (NEW)                              │   │
│  │ ┌─────────────────────────────────────────────────────────────┐│   │
│  │ │ • Detect geographic scope (local/regional/national/intl)    ││   │
│  │ │ • Identify city/country tokens and "near me" modifiers      ││   │
│  │ │ • Score AI answer engine friendliness (0–100)               ││   │
│  │ │ • Suggest content formats (FAQ/list/tutorial/comparison)    ││   │
│  │ └─────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2.7: CTR + Traffic Potential Forecast (NEW)                │   │
│  │ ┌─────────────────────────────────────────────────────────────┐│   │
│  │ │ • Position-based CTR curves (industry-calibrated 2024)      ││   │
│  │ │ • Google AI Overview (SGE) CTR suppression by intent        ││   │
│  │ │ • Seasonal multipliers (Nov +20% → Jul -6%)                 ││   │
│  │ │ • Traffic forecast at rank 1 / 3 / 5 / 10                  ││   │
│  │ │ • Confidence scores + risk flags                            ││   │
│  │ └─────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: RAG (Retrieval-Augmented Generation)                     │   │
│  │ ┌─────────────────────────────────────────────────────────────┐│   │
│  │ │ 8. Retrieve similar analyses (pgvector cosine similarity)   ││   │
│  │ │ 9. Format context from high-quality similar content         ││   │
│  │ └─────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 4: AI Enhancement (LLM + RAG Context)                       │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│   │
│  │ │ 10. LLM     │→ │ 11. Intent  │→ │ 12. SERP    │→ │ 13. Opt. ││   │
│  │ │ Refinement  │    Classification   │    Predict    │    Package││   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 5: Persistence                                              │   │
│  │ ┌─────────────┐  ┌─────────────────────────────────────────────┐│   │
│  │ │ 14. Save    │→ │ ContentAnalysis → KeywordOpportunity     ││   │
│  │ │ to Database │    (with embeddings for pgvector)              ││   │
│  │ └─────────────┘  └─────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### 1. Basic Keyword Suggestions (V1)

**Endpoint:** `GET|POST /api/keywords/`

```python
@require_http_methods(["GET", "POST"])
@api_subscription_check
def keyword_suggestions(request):
    """
    Basic keyword suggestions endpoint.
    
    GET/POST Params:
        url: Website URL to analyze
        text: Raw text content (alternative to URL)
        page_topic: Optional hint about page content
        use_llm: Whether to use LLM enhancement (default: true)
    
    Returns:
        {
            "keywords": ["word1", "word2", ...],
            "suggestions": [...],
            "groups": {...},
            "focus_keywords": [...]
        }
    """
    data = get_request_data(request)
    
    result = run_keyword_pipeline(
        url=data.get("url"),
        text=data.get("text"),
        page_topic=data.get("page_topic", ""),
        use_llm=parse_boolean_param(data.get("use_llm"), True),
    )
    
    return JsonResponse(result)
```

### 2. Enhanced Keyword Suggestions (V2)

**Endpoint:** `GET|POST /api/keywords/v2/`

```python
@require_http_methods(["GET", "POST"])
@rate_limit_ai(requests_per_minute=10)
@api_subscription_check
def keyword_suggestions_v2(request):
    """
    Enhanced keyword suggestions with AI features.
    
    GET/POST Params:
        url: Website URL to analyze
        text: Raw text content
        page_topic: Topic hint for LLM
        use_llm: Use LLM enhancement (default: true)
        use_advanced_ai: Use ML/AI features (default: true)
        analyze_competitors: Include competitor analysis (default: false)
        generate_optimization: Get content optimization tips (default: false)
        target_audience: Target audience (e.g., "beginners", "experts")
    
    Returns:
        Enhanced results with ML analysis, intent data, SERP predictions, etc.
    """
    data = get_request_data(request)
    params = parse_analysis_params(data)
    
    result = run_keyword_pipeline_v2(
        url=data.get("url"),
        text=data.get("text"),
        save_to_db=True,
        **params
    )
    
    return JsonResponse(result)
```

### 3. Submit Feedback

**Endpoint:** `POST /api/keywords/feedback/`

```python
@require_http_methods(["POST"])
@api_subscription_check
def submit_feedback(request):
    """
    Submit user feedback on a keyword suggestion.
    
    POST Body:
        opportunity_id: ID of the keyword opportunity (number)
        action: One of: "accepted", "rejected", "implemented", "ignored"
        comment: Optional user comment (string)
        rating: Optional rating 1-5 (number)
    
    Returns:
        { "success": true, "feedback_id": 123, "message": "..." }
    """
    data = get_request_data(request)
    opportunity_id = data.get("opportunity_id")
    action = data.get("action")
    
    # Validate action
    if action not in VALID_FEEDBACK_ACTIONS:
        return error_response(f"Invalid action. Must be one of: {', '.join(VALID_FEEDBACK_ACTIONS)}")
    
    # Update opportunity status
    opportunity = KeywordOpportunity.objects.get(id=opportunity_id)
    opportunity.is_accepted = action in ("accepted", "implemented")
    opportunity.is_rejected = (action == "rejected")
    opportunity.save()
    
    # Create feedback record
    feedback = SuggestionFeedback.objects.create(
        opportunity=opportunity,
        user_action=action,
        user_comment=data.get("comment", ""),
        rating=data.get("rating"),
    )
    
    return JsonResponse({
        "success": True,
        "feedback_id": feedback.id,
        "message": f"Feedback recorded: {action}"
    })
```

### 4. Traffic Signal Analysis (NEW)

**Endpoint:** `POST /api/keywords/traffic-analysis/`

```python
@require_http_methods(["POST"])
@api_subscription_check
def analyze_traffic_signals(request):
    """
    Analyze real-time traffic signals for a list of keywords.
    
    POST Body:
        keywords: List of keywords to analyze (required, max 50)
        page_topic: Optional page topic for context
        target_audience: Optional target audience description
        use_google_trends: Whether to fetch real Google Trends data (default: true)
    
    Returns:
        {
            "trending_alerts": [
                {
                    "keyword": "AI SEO tools",
                    "reason": "🔥 TRENDING NOW",
                    "urgency": "Act within 24–72 hours",
                    "priority_score": 85.0
                }
            ],
            "traffic_prioritized_keywords": [
                {
                    "keyword": "SEO automation",
                    "monthly_volume": 12500,           // REAL DATA
                    "volume_display": "12,500/mo",
                    "traffic_potential": "~3,750/mo",
                    "difficulty_score": 45,            // 0-100
                    "cpc_value": "$2.50",
                    "trend_status": "📈 RISING",
                    "priority_score": 78.5,
                    "data_source": "semrush"           // or "estimated"
                }
            ],
            "quick_win_keywords": ["easy to rank keywords"],
            "avoid_keywords": [{"keyword": "SEO", "reason": "Too broad"}],
            "topic_cluster": {
                "pillar_keyword": "SEO automation",
                "cluster_keywords": ["..."],
                "lsi_terms": ["..."]
            },
            "enrichment_metadata": {
                "total_keywords_processed": 15,
                "keywords_with_real_data": 12,
                "data_providers_used": ["semrush"],
                "avg_priority_score": 74.2,
                "processed_at": "2026-05-21T22:30:00"
            }
        }
    """
    data = get_request_data(request)
    
    keywords = data.get("keywords", [])
    page_topic = data.get("page_topic", "")
    target_audience = data.get("target_audience", "")
    use_google_trends = parse_boolean_param(data.get("use_google_trends"), True)
    
    from keyword_ai.services.traffic_enrichment import enrich_with_traffic_signals
    
    result = enrich_with_traffic_signals(
        keywords=keywords,
        page_topic=page_topic,
        target_audience=target_audience,
        use_google_trends=use_google_trends
    )
    
    return JsonResponse(result)
```

---

## Pipeline V2 Implementation

### Main Pipeline Function

```python
def run_keyword_pipeline_v2(
    url: str = None,
    text: str = None,
    page_topic: str = "",
    use_llm: bool = True,
    use_advanced_ai: bool = True,
    analyze_competitors: bool = False,
    generate_optimization: bool = False,
    target_audience: str = "",
    save_to_db: bool = True,
) -> dict:
    """
    Enhanced keyword pipeline v2 (Phase 1 + Phase 2 ML + Phase 3 AI + RAG).
    """
    
    # ─────────────────────────────────────────────────────────────────
    # PHASE 1: Content Extraction & Analysis
    # ─────────────────────────────────────────────────────────────────
    
    # Step 1: Extract content
    if text:
        full_text = text
        meta = {"title": "", "meta_description": "", "full_text": text}
    elif url:
        meta = extract_content(url)
        full_text = meta.get("full_text", "")
        if "error" in meta:
            return {"error": meta["error"]}
    
    if len(full_text.strip()) < 50:
        return {"error": "Not enough text content found on the page."}
    
    # Step 2: Deep Content Analysis
    content_analysis_result = analyze_content(full_text, url)
    
    # Step 3: Generate content embedding for ML/RAG
    content_embedding = get_single_embedding(full_text[:1500])
    
    # Save to database with embedding
    if save_to_db and url:
        content_analysis_db = save_content_analysis(
            url, meta, content_analysis_result, content_embedding
        )
    
    # ─────────────────────────────────────────────────────────────────
    # PHASE 2: ML-Powered Keyword Generation
    # ─────────────────────────────────────────────────────────────────
    
    # Step 4: KeyBERT Extraction
    keybert_results = extract_keywords(full_text, top_n=20)
    seed_keywords = [item["keyword"] for item in keybert_results]
    
    # Step 5: Similarity Expansion
    expanded = expand_keywords(seed_keywords, top_k=20)
    expanded_keywords = [item["keyword"] for item in expanded]
    
    # Step 6: ML-Generated Suggestions
    generated_suggestions = generate_keyword_suggestions(
        content_text=full_text,
        seed_keywords=seed_keywords,
        num_suggestions=30,
        content_embedding=content_embedding
    )
    
    # Step 7: Semantic Keyword Mapping
    semantic_keywords = find_semantic_keywords(
        content_text=full_text,
        top_k=20,
        use_cached_index=True
    )
    
    # Step 8: TF-IDF Analysis
    tfidf_results = content_analysis_result.get("tfidf_keywords", [])
    tfidf_keywords = [item["keyword"] for item in tfidf_results[:15]]
    
    # Combine all keywords
    all_keywords = list(dict.fromkeys(
        seed_keywords + expanded_keywords + tfidf_keywords +
        [s["keyword"] for s in generated_suggestions] +
        [s["keyword"] for s in semantic_keywords]
    ))
    
    # Step 9: Competitor Analysis (optional)
    if analyze_competitors and url:
        competitor_data = run_competitor_analysis(url, target_keywords, full_text)
        gap_analysis_result = competitor_data.get("gap_analysis", {})
    
    # Step 10: Multi-Factor ML Relevance Scoring
    scored = score_keywords_v2(
        keywords=all_keywords,
        content_embedding=content_embedding,
        content_text=full_text,
        gap_keywords=gap_analysis_result.get("gap_keywords", []),
        use_ml_model=True
    )
    relevant_keywords = [item["keyword"] for item in scored if item["is_relevant"]]
    
    # ─────────────────────────────────────────────────────────────────
    # PHASE 2.5: Traffic Enrichment (NEW - Real Data Providers)
    # ─────────────────────────────────────────────────────────────────
    
    # Step 10.5: Enrich ML keywords with real traffic signals
    traffic_analysis = {}
    if generated_suggestions:
        from keyword_ai.services.traffic_enrichment import enrich_with_traffic_signals
        
        ml_keywords = [s["keyword"] for s in generated_suggestions]
        traffic_analysis = enrich_with_traffic_signals(
            keywords=ml_keywords,
            page_topic=page_topic,
            target_audience=target_audience,
            use_google_trends=True
        )
        
        # Merge traffic signals back into suggestions
        traffic_by_keyword = {
            item["keyword"]: item 
            for item in traffic_analysis.get("traffic_prioritized_keywords", [])
        }
        
        for suggestion in generated_suggestions:
            kw = suggestion["keyword"]
            if kw in traffic_by_keyword:
                suggestion["traffic_signals"] = traffic_by_keyword[kw]
                # Add real numbers if available
                signals = traffic_by_keyword[kw]
                suggestion["monthly_volume"] = signals.get("monthly_volume")
                suggestion["difficulty_score"] = signals.get("difficulty_score")
    
    # ─────────────────────────────────────────────────────────────────
    # PHASE 3: RAG (Retrieval-Augmented Generation)
    # ─────────────────────────────────────────────────────────────────
    
    # Step 11: Retrieve similar content for context augmentation
    rag_context = ""
    if content_embedding is not None and save_to_db:
        similar_analyses = retrieve_similar_analyses(
            content_embedding,
            top_k=3,
            min_quality_score=60.0
        )
        rag_context = format_rag_context(similar_analyses, max_context_length=1500)
    
    # ─────────────────────────────────────────────────────────────────
    # PHASE 4: AI Enhancement (LLM + RAG + Traffic Context)
    # ─────────────────────────────────────────────────────────────────
    
    # Step 12: LLM Refinement with RAG + Traffic Context (NEW)
    # Combine RAG context with real traffic signals for better ranking
    if use_llm and relevant_keywords:
        traffic_context = ""
        if traffic_analysis.get("traffic_prioritized_keywords"):
            top_traffic = traffic_analysis["traffic_prioritized_keywords"][:10]
            traffic_context = "\n## Traffic Signal Context (Real-Time Data)\n"
            for item in top_traffic:
                traffic_context += (
                    f"- {item['keyword']}: {item['trend_status']}, "
                    f"Volume: {item.get('monthly_volume') or item['estimated_volume']}, "
                    f"Priority: {item['priority_score']}\n"
                )
        
        combined_context = f"{rag_context}\n{traffic_context}" if traffic_context else rag_context
        
        llm_result = refine_keywords(
            relevant_keywords, 
            page_topic=page_topic, 
            context=combined_context  # Now includes real traffic numbers!
        )
    
    # Step 13: Advanced LLM Keyword Expansion
    if use_advanced_ai and use_llm:
        llm_expanded_suggestions = expand_keywords_with_llm(
            content_text=full_text,
            existing_keywords=relevant_keywords,
            page_topic=page_topic,
            target_audience=target_audience,
            num_suggestions=15
        )
        
        question_keywords = generate_question_keywords(
            content_text=full_text,
            page_topic=page_topic,
            num_questions=10
        )
    
    # Step 14: Intent Classification
    intent_classifications = classify_batch(llm_result.get("focus_keywords", [])[:10])
    
    # Step 15: SERP Feature Prediction
    serp_predictions = {}
    for kw in llm_result.get("focus_keywords", [])[:5]:
        serp_predictions[kw] = predict_serp_features(kw)
    
    # Step 16: Content Optimization (optional)
    if generate_optimization and use_advanced_ai:
        optimization_package = get_complete_optimization_package(
            content_text=full_text,
            target_keywords=llm_result.get("focus_keywords", [])[:10],
            current_title=meta.get("title", ""),
            current_meta_desc=meta.get("meta_description", ""),
            page_topic=page_topic,
        )
    
    # ─────────────────────────────────────────────────────────────────
    # PHASE 5: Persistence
    # ─────────────────────────────────────────────────────────────────
    
    # Step 17: Save all keyword opportunities
    if content_analysis_db and save_to_db:
        save_keyword_opportunities(content_analysis_db, keybert_results, "keybert")
        save_keyword_opportunities(content_analysis_db, generated_suggestions[:20], "ml_generated")
        save_keyword_opportunities(content_analysis_db, semantic_keywords[:15], "semantic")
        save_keyword_opportunities(
            content_analysis_db,
            [{"keyword": k, "relevance_score": 0.9} for k in llm_result.get("focus_keywords", [])],
            "focus"
        )
    
    # Build enhanced response
    return {
        "url": url,
        "page_title": meta.get("title", ""),
        "scored_keywords": scored,
        "relevant_keywords": relevant_keywords,
        "focus_keywords": llm_result.get("focus_keywords", []),
        
        "content_analysis": {
            "quality_score": content_analysis_result.get("quality_score", 0),
            "readability": content_analysis_result.get("readability", {}),
            "word_count": content_analysis_result.get("readability", {}).get("word_count", 0),
        },
        
        "ml_generated_suggestions": generated_suggestions[:15],
        "semantic_keywords": semantic_keywords[:15],
        "tfidf_keywords": tfidf_results[:10],
        
        "intent_classifications": intent_classifications,
        "serp_predictions": serp_predictions,
        "ai_expanded_keywords": llm_expanded_suggestions[:10] if llm_expanded_suggestions else [],
        "question_keywords": question_keywords[:8] if question_keywords else [],
        "content_optimization": optimization_package if generate_optimization else None,
        
        "rag_enabled": bool(rag_context),
        "traffic_analysis": traffic_analysis,  # NEW: Real traffic signals
        "pipeline_version": "2.2",
        "phases_enabled": ["phase1_content_analysis", "phase2_ml_models", "phase2.5_traffic_enrichment", "phase3_ai_enhancement", "rag_retrieval"],
    }
```

---

## Phase 2.5: Traffic Enrichment Layer (NEW)

### Overview
The Traffic Enrichment Layer sits between ML keyword generation and RAG retrieval. It fetches **real traffic data** from keyword research APIs to replace estimations with actual numbers.

### Traffic Signal Framework

Each keyword is scored through a 3-tier framework:

#### Tier 1 — Real-Time Demand Signals (Weight: 40%)
- Trend status: 🔥 TRENDING NOW / 📈 RISING / ➡️ STABLE / 📉 DECLINING
- Traffic velocity: Viral / Fast / Moderate / Slow
- Google Trends integration for live momentum

#### Tier 2 — Traffic Opportunity Score (Weight: 45%)
With real data providers:
```json
{
  "monthly_volume": 12500,        // Exact monthly searches
  "volume_display": "12,500/mo",
  "traffic_potential": "~3,750/mo", // If ranked #1 (30% CTR)
  "difficulty_score": 45,          // 0-100 exact
  "cpc_value": "$2.50",            // Cost per click
  "competition_index": 0.67        // 0-1 scale
}
```

Without real data (estimation fallback):
```json
{
  "estimated_volume": "High",      // Category
  "volume_range": "10K-100K",      // Estimated range
  "keyword_difficulty": "Medium",
  "cpc_signal": "High"
}
```

#### Tier 3 — Strategic Fit (Weight: 25%)
- Intent: Informational / Commercial / Transactional / Navigational
- SERP Feature Opportunity: Featured Snippet / People Also Ask / Video / Local Pack
- Content Type: Blog / Landing Page / Product Page / FAQ / Comparison
- Funnel Stage: Awareness / Consideration / Decision

### Data Providers

```python
from keyword_ai.services.traffic_data_providers import (
    SEMrushProvider,      # ~$200/mo, most comprehensive
    DataForSEOProvider,   # ~$0.001/keyword, pay-as-you-go
    SerpstatProvider,     # ~$69/mo, budget option
)

# Configuration (add to .env)
SEMRUSH_API_KEY=your_key
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
SERPSTAT_API_KEY=your_key
```

### Traffic Enrichment Service

```python
from keyword_ai.services.traffic_enrichment import enrich_with_traffic_signals

# Enrich keywords with real traffic data
result = enrich_with_traffic_signals(
    keywords=["SEO automation", "AI tools", "keyword research"],
    page_topic="Digital Marketing",
    target_audience="SaaS marketers",
    use_google_trends=True
)

# Returns:
{
    "trending_alerts": [
        {
            "keyword": "AI SEO tools 2025",
            "reason": "🔥 TRENDING NOW — Commercial keyword with very high search volume",
            "urgency": "Act within 24–72 hours",
            "priority_score": 85.0
        }
    ],
    "traffic_prioritized_keywords": [
        {
            "keyword": "n8n workflow automation",
            "monthly_volume": 15400,
            "difficulty_score": 42,
            "cpc_value": "$3.20",
            "trend_status": "🔥 TRENDING NOW",
            "priority_score": 88.5,
            "data_source": "semrush"
        }
    ],
    "quick_win_keywords": ["easy to rank keywords"],
    "avoid_keywords": [{"keyword": "SEO", "reason": "Too competitive"}],
    "topic_cluster": {
        "pillar_keyword": "SEO automation",
        "cluster_keywords": ["..."],
        "lsi_terms": ["..."]
    }
}
```

### Provider Priority
1. **SEMrush** - Most comprehensive (volume, difficulty, CPC, competition)
2. **DataForSEO** - Pay-as-you-go, good for startups
3. **Serpstat** - Budget-friendly alternative
4. **Google Trends** - Free trend data (relative scores 0-100)
5. **Estimation** - Intelligent heuristics (always available fallback)

### API Endpoint

```python
@require_http_methods(["POST"])
def analyze_traffic_signals(request):
    """
    POST /api/keywords/traffic-analysis/
    
    Body:
        keywords: ["keyword1", "keyword2"]
        page_topic: "optional context"
        target_audience: "optional audience"
        use_google_trends: true
    
    Returns: Full traffic signal analysis with real numbers
    """
```

---

## ML Keyword Suggestion Generator

### Generation Strategies

```python
class KeywordSuggestionGenerator:
    """
    Generates keyword suggestions using multiple strategies:
    1. Long-tail variations of seed keywords
    2. Question-based keyword generation
    3. LSI (Latent Semantic Indexing) keyword discovery
    4. Competitor gap keyword expansion
    5. Trending modifier combinations
    """
    
    def __init__(self, content_text: str = "", existing_keywords: List[str] = None):
        self.content_text = content_text.lower()
        self.existing_keywords = set(kw.lower() for kw in (existing_keywords or []))
        self.embedding_model = get_embedding_model()
        
        # Question templates
        self.question_templates = [
            "what is {keyword}",
            "how to {keyword}",
            "why {keyword} matters",
            "when to use {keyword}",
            "where to find {keyword}",
            "who needs {keyword}",
            "which {keyword} is best",
            "can {keyword} help",
            "does {keyword} work",
            "is {keyword} worth it",
        ]
        
        # Commercial intent templates
        self.commercial_templates = [
            "best {keyword}",
            "top {keyword}",
            "cheap {keyword}",
            "affordable {keyword}",
            "professional {keyword}",
            "{keyword} review",
            "{keyword} comparison",
            "{keyword} guide",
            "{keyword} tutorial",
        ]
        
        # Informational templates
        self.informational_templates = [
            "{keyword} explained",
            "{keyword} meaning",
            "{keyword} definition",
            "understanding {keyword}",
            "{keyword} for beginners",
            "{keyword} examples",
            "{keyword} case study",
            "{keyword} tips",
            "{keyword} tricks",
        ]
    
    def generate_suggestions(
        self, 
        seed_keywords: List[str], 
        num_suggestions: int = 30,
        content_embedding: np.ndarray = None
    ) -> List[Dict]:
        """
        Generate keyword suggestions based on seed keywords.
        """
        suggestions = []
        
        # Strategy 1: Long-tail variations
        long_tail = self._generate_long_tail(seed_keywords)
        suggestions.extend(long_tail)
        
        # Strategy 2: Question-based keywords
        questions = self._generate_questions(seed_keywords)
        suggestions.extend(questions)
        
        # Strategy 3: LSI keywords from content
        lsi_keywords = self._extract_lsi_keywords(content_embedding)
        suggestions.extend([{"keyword": kw, "type": "lsi", "confidence": 0.7} for kw in lsi_keywords])
        
        # Strategy 4: Modifier combinations
        modifiers = self._generate_modifiers(seed_keywords)
        suggestions.extend(modifiers)
        
        # Deduplicate
        seen = set()
        unique_suggestions = []
        for sug in suggestions:
            kw_lower = sug["keyword"].lower()
            if kw_lower not in seen and kw_lower not in self.existing_keywords:
                seen.add(kw_lower)
                unique_suggestions.append(sug)
        
        # Score and rank
        scored_suggestions = self._score_suggestions(unique_suggestions, content_embedding)
        scored_suggestions.sort(key=lambda x: x["suggestion_score"], reverse=True)
        return scored_suggestions[:num_suggestions]
```

---

## LLM Expansion Service

### AI-Powered Keyword Expansion

```python
def expand_keywords_with_llm(
    content_text: str,
    existing_keywords: List[str],
    page_topic: str = "",
    target_audience: str = "",
    num_suggestions: int = 15
) -> List[Dict]:
    """
    Use LLM to intelligently expand keywords with reasoning.
    Uses Groq (preferred) or OpenAI as fallback.
    """
    client = get_client()  # Lazy initialization
    if client is None:
        return []
    
    # Truncate content for token limit
    content_summary = content_text[:2000] if len(content_text) > 2000 else content_text
    existing_kw_list = ", ".join(existing_keywords[:20])
    
    prompt = f"""You are an expert SEO strategist with 10+ years of experience.

Analyze the following content and suggest {num_suggestions} NEW keyword opportunities 
that are NOT in the existing list.

CONTENT:
{content_summary}

EXISTING KEYWORDS (DO NOT SUGGEST THESE):
{existing_kw_list}

PAGE TOPIC: {page_topic or "Not specified"}
TARGET AUDIENCE: {target_audience or "General"}

For each suggested keyword, provide:
1. The keyword phrase
2. Search intent (Informational/Transactional/Commercial/Navigational)
3. Estimated search volume (Very High/High/Medium/Low/Very Low)
4. Competition level (High/Medium/Low)
5. Strategic reasoning - why this keyword is valuable
6. Content recommendation - specific advice on how to target this keyword

Respond ONLY with valid JSON in this format:
{{
  "suggestions": [
    {{
      "keyword": "example keyword phrase",
      "intent": "Informational",
      "search_volume": "High",
      "competition": "Medium",
      "reasoning": "This keyword captures users looking for...",
      "recommendation": "Add an H2 section titled 'Example Keyword Guide'..."
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=get_model(),  # llama-3.3-70b-versatile or gpt-4
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        # Clean markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        suggestions = result.get("suggestions", [])
        
        # Add metadata
        for sug in suggestions:
            sug["source"] = "llm_expansion"
            sug["confidence"] = _calculate_confidence(sug)
        
        return suggestions
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"LLM expansion error: {e}")
        return []
```

---

## Data Models

### KeywordOpportunity Model

```python
class KeywordOpportunity(models.Model):
    """
    Identified keyword opportunities for a specific URL.
    Tracks potential keywords with their metrics and user feedback.
    """
    
    INTENT_CHOICES = [
        ('informational', 'Informational'),
        ('navigational', 'Navigational'),
        ('transactional', 'Transactional'),
        ('commercial', 'Commercial'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    # Relations
    content_analysis = models.ForeignKey(
        ContentAnalysis, 
        on_delete=models.CASCADE,
        related_name='opportunities'
    )
    
    # Keyword data
    keyword = models.CharField(max_length=200, db_index=True)
    keyword_type = models.CharField(
        max_length=20,
        choices=[
            ('tfidf', 'TF-IDF Extracted'),
            ('gap', 'Competitor Gap'),
            ('llm', 'AI Suggested'),
            ('longtail', 'Long-tail'),
            ('keybert', 'KeyBERT'),
            ('expanded', 'Similarity Expanded'),
            ('ml_generated', 'ML Generated'),
            ('semantic', 'Semantic'),
            ('focus', 'LLM Focus'),
        ],
        default='tfidf'
    )
    
    # Metrics
    relevance_score = models.FloatField(default=0.0, help_text="Relevance to content 0-100")
    search_volume_estimate = models.CharField(max_length=50, blank=True, help_text="e.g., '1K-10K'")
    difficulty_score = models.FloatField(default=0.0, help_text="SEO difficulty 0-100")
    competition_gap_score = models.FloatField(default=0.0, help_text="Gap vs competitors 0-100")
    
    # Classification
    search_intent = models.CharField(max_length=20, choices=INTENT_CHOICES, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # AI reasoning
    ai_reasoning = models.TextField(blank=True, help_text="Explanation for why this keyword is suggested")
    suggested_action = models.TextField(blank=True, help_text="Action to take (e.g., 'Add H2 section')")
    
    # Status (for feedback loop)
    is_accepted = models.BooleanField(null=True, blank=True, help_text="User accepted this suggestion")
    is_rejected = models.BooleanField(null=True, blank=True, help_text="User rejected this suggestion")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-relevance_score']
        unique_together = ['content_analysis', 'keyword']
        indexes = [
            models.Index(fields=['content_analysis', '-relevance_score']),
            models.Index(fields=['keyword', 'keyword_type']),
            models.Index(fields=['search_intent', '-relevance_score']),
            models.Index(fields=['priority', '-relevance_score']),
        ]
```

### SuggestionFeedback Model

```python
class SuggestionFeedback(models.Model):
    """
    Tracks user feedback on keyword suggestions.
    Used for continuous model improvement.
    """
    
    ACTION_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('ignored', 'Ignored'),
        ('implemented', 'Implemented'),
    ]
    
    opportunity = models.ForeignKey(
        KeywordOpportunity,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    
    user_action = models.CharField(max_length=15, choices=ACTION_CHOICES)
    
    # Optional feedback
    user_comment = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True, help_text="1-5 star rating")
    
    # Tracking
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True, help_text="For tracking user sessions")
    
    # Performance tracking (updated later via cron job)
    ranking_before = models.IntegerField(null=True, blank=True)
    ranking_after_30_days = models.IntegerField(null=True, blank=True)
    traffic_increase_estimate = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['opportunity', '-timestamp']),
            models.Index(fields=['user_action', '-timestamp']),
        ]
```

---

## Feedback System

### Feedback Collection

```python
class FeedbackCollector:
    """
    Collects and manages user feedback on keyword suggestions.
    Enables continuous learning and model improvement.
    """
    
    @staticmethod
    def record_feedback(
        opportunity_id: int,
        user_action: str,
        user_comment: str = "",
        rating: Optional[int] = None,
        session_id: str = "",
        time_spent_seconds: Optional[int] = None,
    ) -> Dict:
        """
        Record user feedback on a keyword suggestion.
        
        Args:
            opportunity_id: The KeywordOpportunity ID
            user_action: 'accepted', 'rejected', 'implemented', 'ignored'
            user_comment: Optional user comment
            rating: Optional 1-5 star rating
            session_id: User session identifier
            time_spent_seconds: Time user spent considering this suggestion
        """
        try:
            opportunity = KeywordOpportunity.objects.get(id=opportunity_id)
            
            # Update opportunity status
            if user_action in ['accepted', 'implemented']:
                opportunity.is_accepted = True
                opportunity.is_rejected = False
            elif user_action == 'rejected':
                opportunity.is_accepted = False
                opportunity.is_rejected = True
            
            opportunity.save()
            
            # Create feedback record
            feedback = SuggestionFeedback.objects.create(
                opportunity=opportunity,
                user_action=user_action,
                user_comment=user_comment,
                rating=rating,
                session_id=session_id,
            )
            
            # Update session metrics
            FeedbackCollector._update_session_metrics(
                session_id, 
                feedback_submitted=True,
                time_spent=time_spent_seconds
            )
            
            return {
                "success": True,
                "feedback_id": feedback.id,
                "opportunity_id": opportunity_id,
                "action": user_action,
                "message": f"Feedback recorded: {user_action}"
            }
            
        except KeywordOpportunity.DoesNotExist:
            return {"success": False, "error": "Opportunity not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

---

## Response Examples

### V2 API Response Structure

```json
{
  "url": "https://example.com/blog/seo-guide",
  "page_title": "Complete SEO Guide 2025",
  
  "content_analysis": {
    "quality_score": 85,
    "readability": {
      "flesch_reading_ease": 65.2,
      "flesch_kincaid_grade": 8.5,
      "word_count": 2450
    },
    "structure": {
      "has_h1": true,
      "h2_count": 8,
      "h3_count": 12,
      "paragraph_count": 24
    }
  },
  
  "scored_keywords": [
    {
      "keyword": "digital marketing",
      "relevance_score": 92.5,
      "is_relevant": true,
      "predicted_intent": "informational"
    },
    {
      "keyword": "seo strategy",
      "relevance_score": 88.3,
      "is_relevant": true,
      "predicted_intent": "informational"
    }
  ],
  
  "focus_keywords": [
    "digital marketing",
    "seo strategy",
    "content optimization",
    "keyword research",
    "search rankings"
  ],
  
  "ml_generated_suggestions": [
    {
      "keyword": "how to improve seo rankings",
      "type": "long_tail_question",
      "suggestion_score": 78.5,
      "predicted_intent": "informational",
      "parent_keyword": "seo strategy"
    },
    {
      "keyword": "best digital marketing tools 2025",
      "type": "long_tail_commercial",
      "suggestion_score": 72.3,
      "predicted_intent": "commercial"
    }
  ],
  
  "semantic_keywords": [
    {
      "keyword": "search engine optimization",
      "similarity_score": 0.85,
      "source": "semantic_mapping"
    },
    {
      "keyword": "content marketing strategy",
      "similarity_score": 0.82
    }
  ],
  
  "intent_classifications": [
    {
      "keyword": "how to improve seo",
      "intent": "informational",
      "confidence": 0.95,
      "indicators": ["how", "improve"]
    },
    {
      "keyword": "buy seo tools",
      "intent": "transactional",
      "confidence": 0.92,
      "indicators": ["buy"]
    }
  ],
  
  "serp_predictions": {
    "digital marketing": ["featured_snippet", "people_also_ask", "video_carousel"],
    "seo strategy": ["featured_snippet", "people_also_ask"],
    "content optimization": ["featured_snippet"]
  },
  
  "ai_expanded_keywords": [
    {
      "keyword": "best digital marketing strategies for small business",
      "intent": "Commercial",
      "search_volume": "High",
      "competition": "Medium",
      "reasoning": "Long-tail keyword with commercial intent, targets SMBs with lower competition",
      "recommendation": "Create a dedicated H2 section for small business strategies"
    }
  ],
  
  "question_keywords": [
    "what is digital marketing",
    "how does seo work",
    "why is content optimization important"
  ],
  
  "competitor_analysis": {
    "competitors_analyzed": 3,
    "gap_keywords": ["local seo guide", "technical seo checklist"],
    "high_priority_gaps": ["voice search optimization"]
  },
  
  "content_optimization": {
    "title_suggestions": [
      "The Ultimate SEO Guide 2025: Proven Strategies + Checklists",
      "Complete SEO Strategy Guide: From Beginner to Expert"
    ],
    "meta_description_suggestions": [
      "Master SEO with our comprehensive 2025 guide. Learn proven strategies, get actionable checklists, and boost your rankings today."
    ],
    "content_outline": {
      "recommended_h2s": [
        "Understanding SEO Fundamentals",
        "Keyword Research Strategies",
        "On-Page Optimization Checklist",
        "Technical SEO Essentials"
      ]
    }
  },
  
  "rag_enabled": true,
  "rag_context_preview": "Similar high-performing content suggests focusing on...",
  
  "pipeline_version": "2.1",
  "phases_enabled": [
    "phase1_content_analysis",
    "phase2_ml_models",
    "phase3_ai_enhancement",
    "rag_retrieval"
  ]
}
```

---

## File Structure

```
keyword_ai/
├── views.py                    # API endpoints
├── urls.py                     # URL routing
├── pipeline_v2.py              # Main pipeline implementation
├── models.py                   # Django ORM models
├── 
├── services/                   # Core business logic
│   ├── extract_content.py      # Web scraping
│   ├── content_analyzer.py     # Content quality analysis
│   ├── keybert_extractor.py    # KeyBERT keyword extraction
│   ├── similarity_search.py    # Semantic similarity expansion
│   ├── relevance_scorer.py     # V1 relevance scoring
│   ├── relevance_scorer_v2.py  # V2 ML relevance scoring
│   ├── llm_refiner.py          # LLM keyword grouping
│   ├── llm_expander.py         # LLM keyword expansion
│   ├── intent_classifier.py    # Search intent classification
│   ├── content_optimizer.py    # Content optimization
│   ├── competitor_analyzer.py  # Competitor analysis
│   ├── embeddings.py           # Vector embeddings
│   ├── rag_retriever.py        # RAG context retrieval
│   ├── feedback_collector.py   # Feedback processing
│   └── ab_testing.py           # A/B testing framework
│
├── ml_models/                  # ML Models
│   ├── relevance_scorer_v2.py  # Neural relevance model
│   ├── suggestion_generator.py # LSTM keyword generator
│   └── semantic_mapper.py      # FAISS semantic search
│
└── migrations/                 # Database migrations
```

---

## Key Features Summary

| Feature | Description | Files |
|---------|-------------|-------|
| **Content Extraction** | Scrapes web pages, extracts text/metadata | `services/extract_content.py` |
| **KeyBERT Extraction** | ML-based keyword extraction | `services/keybert_extractor.py` |
| **Similarity Expansion** | Semantic keyword expansion | `services/similarity_search.py` |
| **ML Suggestions** | Generates new keywords using templates + LSI | `ml_models/suggestion_generator.py` |
| **Semantic Mapping** | FAISS-based semantic keyword discovery | `ml_models/semantic_mapper.py` |
| **Relevance Scoring** | Neural relevance scoring (v2) | `ml_models/relevance_scorer_v2.py` |
| **RAG** | Retrieves similar content for LLM context | `services/rag_retriever.py` |
| **LLM Expansion** | AI-powered keyword generation | `services/llm_expander.py` |
| **Intent Classification** | Classifies search intent | `services/intent_classifier.py` |
| **SERP Prediction** | Predicts SERP features | `services/intent_classifier.py` |
| **Content Optimization** | Title/meta/content suggestions | `services/content_optimizer.py` |
| **Feedback Loop** | Tracks accept/reject for learning | `services/feedback_collector.py` |

---

## Environment Variables

```bash
# LLM Provider (Groq preferred, OpenAI fallback)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
USE_GROQ=True

# OpenAI (fallback)
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4

# pgvector (for RAG)
DATABASE_URL=postgresql://user:pass@localhost/dbname
```
