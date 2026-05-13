# Keyword AI App - Architecture & Flow Diagram

## Overview

The `keyword_ai` app is a Django-based keyword analysis system that uses ML and AI to extract, analyze, and suggest keywords from web content. It has evolved through **6 phases** of development:

1. **Phase 1**: Content Analysis & TF-IDF
2. **Phase 2**: ML Models (KeyBERT, Relevance Scoring)
3. **Phase 3**: AI Enhancement (LLM, Intent Classification)
4. **Phase 4**: Async Processing (Celery)
5. **Phase 5**: Feedback Loop & Continuous Learning
6. **Phase 6**: **RAG (Retrieval-Augmented Generation)** ⭐ NEW

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    USER INTERFACE                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │  SEOAnalyzer    │  │   Templates     │  │   API Clients   │  │   Admin Dashboard   │ │
│  │   (views.py)    │  │  (keysuggestion │  │   (external)    │  │  (analytics_views)  │ │
│  │                 │  │   .html, etc)   │  │                 │  │                     │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └─────────┬───────────┘ │
└───────────┼────────────────────┼────────────────────┼────────────────────┼─────────────┘
            │                    │                    │                    │
            ▼                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    API LAYER (views.py)                                  │
│                                                                                          │
│   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────────┐    │
│   │ /api/keywords/     │  │ /api/keywords/v2/  │  │ /api/keywords/analyze-async/   │    │
│   │ (keyword_          │  │ (keyword_          │  │ (analyze_url_async)            │    │
│   │  suggestions)     │  │  suggestions_v2)   │  │                                │    │
│   │ • Basic analysis   │  │ • Enhanced AI      │  │ • Background processing        │    │
│   │ • V1 pipeline      │  │ • V2 + RAG         │  │ • Celery tasks                 │    │
│   └────────────────────┘  └────────────────────┘  └────────────────────────────────┘    │
│                                                                                          │
│   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────────┐    │
│   │ /api/keywords/     │  │ /api/keywords/     │  │ /api/keywords/streaming/       │    │
│   │  feedback/         │  │  opportunities/    │  │ (NEW: Real-time SSE)         │    │
│   │ (submit_           │  │ (get_opportunities)│  │ • Live LLM responses         │    │
│   │  feedback)        │  │ • Historical data  │  │ • NDJSON streaming           │    │
│   │ • User feedback    │  │ • Saved results    │  │                                │    │
│   └────────────────────┘  └────────────────────┘  └────────────────────────────────┘    │
└─────────────────────────────────────────┬────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PIPELINE LAYER                                         │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PIPELINE V1 (pipeline.py)                              │   │
│  │  ┌─────────────┐ → ┌─────────────┐ → ┌─────────────┐ → ┌─────────────┐           │   │
│  │  │ 1. Content  │ → │ 2. KeyBERT  │ → │ 3. Similarity│ → │ 4. ML Score │           │   │
│  │  │ Extraction  │    Extraction │    Expansion  │    Keywords   │           │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘           │   │
│  │                                              ↓                                    │   │
│  │                                       ┌─────────────┐                            │   │
│  │                                       │ 5. LLM      │                            │   │
│  │                                       │ Refinement    │                            │   │
│  │                                       └─────────────┘                            │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                          PIPELINE V2 (pipeline_v2.py)                            │   │
│  │                                                                                  │   │
│  │  PHASE 1: Content Analysis          PHASE 2: ML Models     PHASE 3: AI Enhance  │   │
│  │  ┌─────────────────────────┐        ┌─────────────────┐    ┌────────────────┐  │   │
│  │  │ • Content extraction    │        │ • ML suggestion   │    │ • LLM expansion│  │   │
│  │  │ • TF-IDF analysis       │───────→│ • Semantic mapper │───→│ • Question KWs │  │   │
│  │  │ • Quality scoring       │        │ • Relevance v2    │    │ • Intent class │  │   │
│  │  │ • Readability metrics   │        │ • Gap analysis    │    │ • SERP predict │  │   │
│  │  │ • Entity extraction     │        │                   │    │ • Content opt  │  │   │
│  │  └─────────────────────────┘        └─────────────────┘    └────────────────┘  │   │
│  │           │                                  │                      │            │   │
│  │           ▼                                  ▼                      ▼            │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    DATABASE SAVE (save_to_db=True)                       │   │   │
│  │  │  • ContentAnalysis → KeywordOpportunity → SuggestionFeedback          │   │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────┬────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   SERVICE LAYER                                          │
│                                                                                          │
│  Content Services          ML/AI Services           Utility Services                   │
│  ┌────────────────┐        ┌────────────────┐       ┌────────────────┐                  │
│  │ extract_content│        │ keybert_       │       │ embeddings     │                  │
│  │ content_       │        │ extractor      │       │ similarity_    │                  │
│  │ analyzer       │        │ relevance_     │       │ search         │                  │
│  │ competitor_    │        │ scorer(_v2)     │       │                │                  │
│  │ analyzer       │        │ suggestion_    │       │                │                  │
│  │ intent_        │        │ generator      │       │                │                  │
│  │ classifier     │        │ semantic_      │       │                │                  │
│  │ content_       │        │ mapper         │       │                │                  │
│  │ optimizer      │        │                │       │                │                  │
│  └────────────────┘        └────────────────┘       └────────────────┘                  │
│                                                                                          │
│  RAG Services (NEW)        LLM Services                                                  │
│  ┌────────────────┐       ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ rag_retriever  │       │ llm_refiner    │  │ llm_expander   │  │ feedback_collector│ │
│  │ • pgvector     │       │ • Intent groups│  │ • AI expansion │  │ • A/B testing    │ │
│  │ • Similarity   │       │ • Focus KWs    │  │ • Questions    │  │ • Retraining     │ │
│  │ • Context aug  │       │ • +RAG context │  │               │  │                 │ │
│  └────────────────┘       └────────────────┘  └────────────────┘  └────────────────┘  │
└─────────────────────────────────────────┬────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ML MODELS LAYER                                        │
│                                                                                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │ relevance_scorer_v2.py  │  │ suggestion_generator.py │  │ semantic_mapper.py      │  │
│  │                         │  │                         │  │                         │  │
│  │ • Neural relevance      │  │ • LSTM/Transformer      │  │ • FAISS indexing        │  │
│  │   scoring               │  │   keyword generation    │  │ • Vector similarity     │  │
│  │ • Multi-factor scoring  │  │ • Gap-based suggestions │  │ • Semantic clustering   │  │
│  │ • Intent prediction     │  │ • Content-aware         │  │ • Nearest neighbors     │  │
│  │                         │  │                         │  │                         │  │
│  └─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────┬────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DATA LAYER                                             │
│                                                                                          │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐                   │
│  │      DJANGO MODELS           │  │      CELERY TASKS              │                   │
│  │      (models.py)             │  │      (tasks.py)                │                   │
│  │  ┌────────────────────────┐  │  │  ┌────────────────────────┐    │                   │
│  │  │ ContentAnalysis        │  │  │  │ analyze_single_url_task│    │                   │
│  │  │ • url, content_hash    │  │  │  │ • Async processing     │    │                   │
│  │  │ • quality_score        │  │  │  │ • Progress tracking    │    │                   │
│  │  │ • readability metrics  │  │  │  │ • Retry logic          │    │                   │
│  │  │ • embedding (pgvector) │  │  │  └────────────────────────┘    │                   │
│  │  └────────────────────────┘  │  │  ┌────────────────────────┐    │                   │
│  │  ┌────────────────────────┐  │  │  │ analyze_batch_urls_task│    │                   │
│  │  │ KeywordOpportunity     │  │  │  • Batch processing      │    │                   │
│  │  │ • keyword, type        │  │  │  • Aggregate results     │    │                   │
│  │  │ • relevance_score      │  │  │  • Multiple URLs         │    │                   │
│  │  │ • search_intent        │  │  │  └────────────────────────┘    │                   │
│  │  │ • ai_reasoning         │  │  │                               │                   │
│  │  └────────────────────────┘  │  │                               │                   │
│  │  ┌────────────────────────┐  │  └───────────────────────────────┘                   │
│  │  │ SuggestionFeedback     │  │                                                      │
│  │  │ • user_action          │  │                                                      │
│  │  │ • rating, comment    │  │                                                      │
│  │  └────────────────────────┘  │                                                      │
│  │  ┌────────────────────────┐  │                                                      │
│  │  │ AnalysisTask           │  │                                                      │
│  │  │ • task_id, status      │  │                                                      │
│  │  │ • progress tracking    │  │                                                      │
│  │  └────────────────────────┘  │                                                      │
│  └──────────────────────────────┘                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Data Flow

### 1. Synchronous Analysis Flow (V1 Pipeline)

```
User Request (URL/Text)
         │
         ▼
┌─────────────────┐
│  API Endpoint   │  ← views.keyword_suggestions()
│  /api/keywords/ │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Step 1: Extract │────→│ Content Crawler │←── extract_content()
│    Content      │     │ (title, meta,   │
│                 │     │  body text)     │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Step 2: KeyBERT │────→│ KeyBERT Model   │←── keybert_extractor.py
│   Extraction    │     │ Extracts top 20 │
│                 │     │ keywords        │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Step 3: Expand  │────→│ Cosine Similarity│←── similarity_search.py
│   Keywords      │     │ Search (top 20)  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Step 4: ML Score│────→│ Relevance Model │←── relevance_scorer.py
│   Keywords      │     │ (is_relevant?)  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Step 5: LLM     │────→│ OpenAI GPT      │←── llm_refiner.py
│  Refinement     │     │ Intent Groups   │
│                 │     │ Focus Keywords  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  JSON Response  │
│  {keywords,     │
│   groups,       │
│   focus_kws}    │
└─────────────────┘
```

### 2. Enhanced Analysis Flow (V2 Pipeline)

```
User Request (URL/Text + Options)
         │
         ▼
┌─────────────────┐
│ /api/keywords/  │  ← views.keyword_suggestions_v2()
│      v2/        │     • use_advanced_ai=True
└────────┬────────┘     • analyze_competitors=True
         │              • generate_optimization=True
         ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Content Analysis                               │
├─────────────────────────────────────────────────────────┤
│ • Extract content                                      │
│ • TF-IDF analysis → Top keywords                        │
│ • Quality scoring (0-100)                              │
│ • Readability (Flesch-Kincaid)                        │
│ • Entity extraction                                   │
│ • Semantic embedding                                  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: ML Models                                      │
├─────────────────────────────────────────────────────────┤
│ • KeyBERT extraction                                   │
│ • Similarity expansion                               │
│ • ML suggestion generator → New keywords               │
│ • Semantic mapper → Related keywords                    │
│ • relevance_scorer_v2 → Ranking                      │
│ • Competitor analysis (optional) → Gap keywords        │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: RAG - Retrieval-Augmented Generation ⭐ NEW   │
├─────────────────────────────────────────────────────────┤
│ • Generate embedding for current content               │
│ • Query pgvector for similar analyses (cosine sim)     │
│ • Retrieve top-k high-quality similar content          │
│ • Extract successful keywords from similar content     │
│ • Format retrieved context for LLM augmentation        │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: AI Enhancement (RAG-Augmented)               │
├─────────────────────────────────────────────────────────┤
│ • LLM keyword expansion (with reasoning)               │
│ • Question keyword generation                        │
│ • Intent classification (informational/transactional)│
│ • SERP feature prediction                              │
│ • Content optimization (optional)                      │
│   - Title suggestions                                 │
│   - Meta description                                  │
│   - Content outline                                   │
│   - Improvement tips                                  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Save to Database                                        │
├─────────────────────────────────────────────────────────┤
│ ContentAnalysis → KeywordOpportunities (all KWs)      │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Enhanced JSON Response                                  │
├─────────────────────────────────────────────────────────┤
│ • content_analysis (quality, readability)              │
│ • scored_keywords (with relevance scores)              │
│ • ml_generated_suggestions                            │
│ • semantic_keywords                                   │
│ • intent_classifications                              │
│ • serp_predictions                                    │
│ • content_optimization (if requested)                  │
└─────────────────────────────────────────────────────────┘
```

### 3. Async Processing Flow

```
User Request
    │
    ▼
┌─────────────────┐
│ /api/keywords/  │  ← views.analyze_url_async()
│  analyze-async/ │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Create Task     │────→│ Celery Task     │←── tasks.analyze_single_url_task()
│ Record (DB)     │     │ Queue           │
│ task_id=uuid    │     │                 │
└────────┬────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │ Background      │
         │              │ Processing      │
         │              │ • Progress 10%  │
         │              │ • Progress 50%  │
         │              │ • Progress 90%  │
         │              └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Immediate       │     │ Task Complete   │
│ Response        │     │ Save Result     │
│ {task_id,       │     │ to DB           │
│  status:        │     │                 │
│  pending}       │     │                 │
└─────────────────┘     └─────────────────┘
                                 │
         ┌───────────────────────┘
         │
         ▼
┌─────────────────┐
│ Poll Status:    │  ← views.get_task_status()
│ /api/keywords/  │
│  task-status/   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response:       │
│ {status:        │
│  completed/     │
│  failed,       │
│  result: {...}} │
└─────────────────┘
```

### 4. Feedback Loop Flow (Phase 5)

```
User Action
    │
    ▼
┌─────────────────┐
│ Submit Feedback │  ← views.submit_feedback()
│ /api/keywords/  │
│    feedback/    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update Keyword  │
│ Opportunity     │
│ • is_accepted   │
│ • is_rejected   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Feedback  │
│ Record          │
│ • user_action   │
│ • rating        │
│ • comment       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌─────────────────┐
│Analytics│ │ Retraining      │
│Dashboard│ │ Pipeline        │
│         │ │ (periodic)      │
└────────┘ └─────────────────┘
```

---

## File Structure

```
keyword_ai/
├── __init__.py
├── views.py                 # API endpoints (all views)
├── urls.py                  # URL routing
├── models.py                # Database models
├── pipeline.py              # V1 pipeline (basic)
├── pipeline_v2.py           # V2 pipeline (enhanced with ML/AI)
├── tasks.py                 # Celery async tasks
├── train_model.py           # Model training utilities
├── retraining_pipeline.py   # Continuous retraining
├── analytics_views.py       # Analytics dashboard APIs
│
├── services/                # Core business logic
│   ├── extract_content.py       # Web scraping
│   ├── content_analyzer.py      # Content quality analysis
│   ├── keybert_extractor.py     # KeyBERT keyword extraction
│   ├── similarity_search.py     # Semantic similarity
│   ├── relevance_scorer.py      # V1 relevance scoring
│   ├── relevance_scorer_v2.py   # V2 ML relevance scoring
│   ├── llm_refiner.py           # LLM keyword grouping
│   ├── llm_expander.py          # LLM keyword expansion
│   ├── intent_classifier.py     # Search intent classification
│   ├── content_optimizer.py     # Content optimization
│   ├── competitor_analyzer.py   # Competitor analysis
│   ├── embeddings.py            # Vector embeddings
│   ├── feedback_collector.py    # Feedback processing
│   ├── ab_testing.py            # A/B testing framework
│   └── flow.txt                 # Service flow notes
│
├── ml_models/               # Machine Learning Models
│   ├── relevance_scorer_v2.py   # Neural relevance model
│   ├── suggestion_generator.py  # LSTM keyword generator
│   └── semantic_mapper.py       # FAISS semantic search
│
├── models/                  # Django ORM models (split)
│   ├── __init__.py
│   ├── content_analysis.py
│   └── feedback.py
│
├── migrations/              # Database migrations
│   ├── 0001_phase1_content_analysis_models.py
│   ├── 0002_phase4_async_tasks.py
│   └── 0003_phase5_feedback_continuous_learning.py
│
├── management/              # Django management commands
│   └── commands/
│       └── retrain_models.py
│
└── dataset/                 # Training data
    └── training_data.json
```

---

## Key Technologies Used

| Component | Technology |
|-----------|------------|
| Web Framework | Django |
| ML Keyword Extraction | KeyBERT |
| Embeddings | sentence-transformers |
| Vector Search | FAISS |
| Neural Models | PyTorch/TensorFlow (LSTM/Transformer) |
| LLM | OpenAI GPT |
| Async Processing | Celery + Redis/RabbitMQ |
| Data Analysis | scikit-learn, numpy |
| NER | spaCy |

---

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/keywords/` | GET/POST | Basic keyword analysis (V1) |
| `/api/keywords/v2/` | GET/POST | Enhanced AI analysis (V2) |
| `/api/keywords/analyze-async/` | POST | Start async analysis |
| `/api/keywords/analyze-batch/` | POST | Batch URL analysis |
| `/api/keywords/task-status/` | GET | Check async progress |
| `/api/keywords/tasks/` | GET | List recent tasks |
| `/api/keywords/opportunities/` | GET | Get saved opportunities |
| `/api/keywords/feedback/` | POST | Submit feedback |
| `/api/keywords/export/` | POST | Export results (CSV/JSON) |
| `/api/keywords/analytics/*` | GET | Analytics dashboard |
