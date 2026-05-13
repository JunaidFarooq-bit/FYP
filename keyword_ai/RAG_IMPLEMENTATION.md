# RAG (Retrieval-Augmented Generation) Implementation

This document describes the RAG implementation added to the Keyword AI system.

## Overview

RAG enhances LLM keyword suggestions by retrieving semantically similar historical content analyses and augmenting prompts with this contextual knowledge.

## Architecture

```
User Content
    │
    ▼
┌─────────────────┐
│ Generate        │  ← sentence-transformers (all-MiniLM-L6-v2)
│ Embedding       │     384-dimensional vector
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ pgvector         │  ← Cosine similarity search
│ Similarity Query │     Top-3 similar analyses
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Format Context  │  ← Build RAG prompt section
│ (rag_retriever) │     with similar content + keywords
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Augmented LLM   │  ← GPT-3.5/Groq with context
│ Prompt          │     "Similar successful content used: X, Y, Z"
└─────────────────┘
```

## New Components

### 1. Database Layer (pgvector)

**File:** `@e:

# RAG (Retrieval-Augmented Generation) Implementation

This document describes the RAG implementation added to the Keyword AI system.

## Overview

RAG enhances LLM keyword suggestions by retrieving semantically similar historical content analyses and augmenting prompts with this contextual knowledge.

## Architecture

```
User Content
    │
    ▼
┌─────────────────┐
│ Generate        │  ← sentence-transformers (all-MiniLM-L6-v2)
│ Embedding       │     384-dimensional vector
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ pgvector         │  ← Cosine similarity search
│ Similarity Query │     Top-3 similar analyses
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Format Context  │  ← Build RAG prompt section
│ (rag_retriever) │     with similar content + keywords
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Augmented LLM   │  ← GPT-3.5/Groq with context
│ Prompt          │     "Similar successful content used: X, Y, Z"
└─────────────────┘
```

## New Components

### 1. Database Layer (pgvector)

**File:** `e:\Project\keyword_ai\models.py`

```python
# Vector field for semantic search
embedding = VectorField(dimensions=384, blank=True, null=True)
```

**Migration:** `e:\Project\keyword_ai\migrations\0004_phase6_rag_vector_search.py`
- Installs `pgvector` PostgreSQL extension
- Creates HNSW index for fast cosine similarity queries
- Adds indexes on `quality_score` and `url`

### 2. RAG Retriever Service

**File:** `e:\Project\keyword_ai\services\rag_retriever.py`

Key functions:

```python
# Retrieve similar content by vector similarity
def retrieve_similar_analyses(
    content_embedding: np.ndarray,
    top_k: int = 5,
    min_quality_score: float = 50.0
) -> List[Dict]

# Format for LLM prompt
def format_rag_context(
    retrieved_analyses: List[Dict],
    max_context_length: int = 2000
) -> str

# Full RAG pipeline
def build_augmented_prompt(
    base_prompt: str,
    content_embedding: np.ndarray
) -> str
```

### 3. Updated Pipeline

**File:** `e:\Project\keyword_ai\pipeline_v2.py`

New steps added:

```python
# Step 12: RAG - Retrieve similar content
rag_context = ""
if content_embedding is not None:
    similar_analyses = retrieve_similar_analyses(
        content_embedding,
        top_k=3,
        min_quality_score=60.0
    )
    rag_context = format_rag_context(similar_analyses)

# Step 13: LLM Refinement with RAG Context
llm_result = refine_keywords(
    relevant_keywords,
    page_topic=page_topic,
    context=rag_context  # NEW: Augmented with RAG
)
```

### 4. Streaming LLM Endpoint

**File:** `e:\Project\keyword_ai\views.py`

```python
# Real-time streaming endpoint
POST /api/keywords/streaming/

Request:
{
    "keywords": ["ai", "machine learning", "python"],
    "page_topic": "Technology Blog",
    "context": "Optional RAG context"
}

Response: Streaming NDJSON
{"chunk": "Focus keywords: "}
{"chunk": "1. machine learning tutorials"}
{"done": true}
```

## API Changes

### Response now includes RAG metadata:

```json
{
    "keywords": [...],
    "intent_groups": {...},
    
    // NEW: RAG metadata
    "rag_enabled": true,
    "rag_context_preview": "## Similar Content References...",
    
    // Updated version
    "pipeline_version": "2.1",
    "phases_enabled": [
        "phase1_content_analysis",
        "phase2_ml_models",
        "phase3_ai_enhancement",
        "rag_retrieval"  // NEW
    ]
}
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install pgvector psycopg2-binary
```

### 2. Configure PostgreSQL

Ensure you're using PostgreSQL (not SQLite). Update `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db',
        'USER': 'your_user',
        'PASSWORD': 'your_pass',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 3. Run Migrations

```bash
python manage.py migrate keyword_ai
```

This will:
- Install the `vector` PostgreSQL extension
- Add the `embedding` VectorField
- Create HNSW index for fast similarity search

### 4. Re-analyze Content (Optional)

Existing content needs embeddings generated:

```python
from keyword_ai.models import ContentAnalysis
from keyword_ai.services.embeddings import get_single_embedding

for analysis in ContentAnalysis.objects.filter(embedding__isnull=True):
    # Fetch content and regenerate embedding
    embedding = get_single_embedding(analysis.title + " " + analysis.meta_description)
    analysis.embedding = embedding.tolist()
    analysis.save()
```

## Query Examples

### Find Similar Content (Raw SQL)

```sql
-- Find top 5 similar analyses by cosine similarity
SELECT 
    url,
    title,
    quality_score,
    embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM keyword_ai_contentanalysis
WHERE quality_score > 60
ORDER BY distance
LIMIT 5;
```

### Django ORM Query

```python
from keyword_ai.models import ContentAnalysis
import numpy as np

# Current content embedding
query_embedding = [0.1, 0.2, ...]  # 384-dim vector

# Find similar
similar = ContentAnalysis.objects.filter(
    quality_score__gte=60,
    embedding__isnull=False
).annotate(
    distance=models.Func(
        models.F('embedding'),
        query_embedding,
        function='embedding <=>',
        output_field=models.FloatField()
    )
).order_by('distance')[:5]

for s in similar:
    print(f"{s.url} (similarity: {1 - s.distance:.2%})")
```

## Performance Considerations

| Aspect | Details |
|--------|---------|
| **Index Type** | HNSW (Hierarchical Navigable Small World) |
| **Parameters** | m=16, ef_construction=64 |
| **Query Time** | ~1-5ms for top-k queries on 10K vectors |
| **Memory** | ~1.5KB per 384-dim vector |
| **Update Strategy** | Async embedding generation on save |

## Benefits of RAG

1. **Contextual Awareness**: LLM knows what worked for similar content
2. **Consistency**: Suggestions align with historically successful patterns
3. **Explainability**: Can show which similar content influenced suggestions
4. **Continuous Learning**: Better suggestions as more content is analyzed

## Future Enhancements

- [ ] Hybrid search (BM25 + vector similarity)
- [ ] Multi-modal embeddings (content + images)
- [ ] Feedback-weighted retrieval (prioritize accepted suggestions)
- [ ] Real-time embedding updates via Celery
- [ ] Cross-domain transfer (learn from related domains)

## Migration from Old System

The old `embedding_vector` TextField is automatically migrated to the new `embedding` VectorField by migration `0004_phase6_rag_vector_search.py`.

**Note:** Existing data will have `NULL` embeddings until re-analyzed. The system gracefully handles this by skipping RAG when no embedding exists.

## Testing RAG

```python
# Test the RAG pipeline
from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2

result = run_keyword_pipeline_v2(
    url="https://example.com/blog/ai-tutorial",
    use_advanced_ai=True,
    save_to_db=True
)

print(f"RAG enabled: {result['rag_enabled']}")
print(f"Context preview: {result['rag_context_preview'][:200]}")
```
