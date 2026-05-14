# Pinecone Vector Database Setup Guide

This guide helps you set up Pinecone as an alternative (or replacement) for PostgreSQL with pgvector for storing and searching vector embeddings in the Keyword AI system.

## Why Pinecone?

- **Managed Service**: No database administration required
- **Scalability**: Handles millions of vectors without performance degradation
- **Speed**: Sub-10ms query latency at scale
- **Hybrid Search**: Combine vector + metadata filtering
- **Production-Ready**: Built for high-availability applications

## Quick Start

### 1. Get Your Pinecone API Key

1. Sign up at [pinecone.io](https://www.pinecone.io/)
2. Create an index (or let the app create it)
3. Copy your API key from the dashboard

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# Enable Pinecone
USE_PINECONE=true

# Your Pinecone API key (required)
PINECONE_API_KEY=pc_your_key_here

# Index configuration (optional - uses defaults if not set)
PINECONE_INDEX_NAME=keyword-ai-vectors
PINECONE_CLOUD=aws                    # aws, gcp, or azure
PINECONE_REGION=us-east-1             # us-east-1, eu-west-1, etc.
```

**Option: Use SQLite instead of PostgreSQL**

If you want simpler setup without PostgreSQL:

```env
# Use SQLite for relational data (users, analyses, etc.)
USE_SQLITE=true
USE_PINECONE=true
PINECONE_API_KEY=pc_your_key_here
```

**Important**: When using SQLite, you **must** use Pinecone for vectors (pgvector only works with PostgreSQL).

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or just the Pinecone client:

```bash
pip install pinecone>=6.0.0
```

### 4. Test Connection

```bash
python manage.py sync_pinecone --test-connection
```

Expected output:
```
Testing vector database connections...
✓ PostgreSQL (pgvector): Connected (152 embeddings)
✓ Pinecone: Connected (index: keyword-ai-vectors, vectors: 0)
```

### 5. Create Pinecone Index (if needed)

```bash
python manage.py sync_pinecone --create-index
```

Or force recreate (⚠️ destroys existing data):

```bash
python manage.py sync_pinecone --create-index --force-recreate
```

### 6. Sync Your Data

If you have existing embeddings in PostgreSQL:

```bash
# Sync all embeddings to Pinecone
python manage.py sync_pinecone --sync-all

# Sync specific record
python manage.py sync_pinecone --analysis-id 123
```

### 7. Verify Setup

```bash
# Show stats
python manage.py sync_pinecone --stats

# Test search with a URL
python manage.py sync_pinecone --test-search "https://your-domain.com/page"
```

## Switching Between Backends

The system supports seamless switching between **pgvector** (PostgreSQL) and **Pinecone**:

### Use Pinecone (Production)
```env
USE_PINECONE=true
PINECONE_API_KEY=your_key
```

### Use pgvector (Development/Local)
```env
USE_PINECONE=false
```

When `USE_PINECONE=true`, the RAG system automatically queries Pinecone first. If Pinecone fails or returns no results, it falls back to pgvector.

## Architecture

```
┌─────────────────┐
│ Content Text    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Embeddings      │────▶│ 384-dim Vector  │
│ (all-MiniLM-L6) │     │ (384 floats)    │
└─────────────────┘     └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   PostgreSQL    │ │    Pinecone     │ │   FAISS Index   │
    │   (pgvector)      │ │  (Managed Cloud)  │ │  (Local File)   │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
                                 ▼
                    ┌─────────────────┐
                    │  Similarity     │
                    │    Search       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  RAG Context    │
                    │  for LLM        │
                    └─────────────────┘
```

## Database Configuration Options

You have flexibility in choosing your database setup:

### Option 1: SQLite + Pinecone (Recommended for Development)
```env
USE_SQLITE=true
USE_PINECONE=true
PINECONE_API_KEY=your_key
```
- ✅ Simple setup, no PostgreSQL installation
- ✅ Fast local development
- ✅ Pinecone handles all vector operations
- ⚠️ SQLite is file-based (not suitable for production with high traffic)

### Option 2: PostgreSQL + Pinecone (Recommended for Production)
```env
USE_SQLITE=false  # or omit
USE_PINECONE=true
PINECONE_API_KEY=your_key
DB_HOST=your-db-host
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASSWORD=your-password
```
- ✅ Full PostgreSQL reliability for relational data
- ✅ Pinecone for fast vector search
- ✅ Best performance and scalability
- ⚠️ Requires PostgreSQL server (Supabase, AWS RDS, or local)

### Option 3: PostgreSQL + pgvector (Legacy/Default)
```env
USE_PINECONE=false
# DB_* variables for PostgreSQL
```
- ✅ Single database for everything
- ✅ No external vector service needed
- ⚠️ Vector search is slower than Pinecone at scale
- ⚠️ Requires pgvector extension installed

| Setup | Relational DB | Vector DB | Best For |
|-------|--------------|-----------|----------|
| SQLite + Pinecone | SQLite (file) | Pinecone | Development, testing |
| PostgreSQL + Pinecone | PostgreSQL | Pinecone | Production (recommended) |
| PostgreSQL + pgvector | PostgreSQL | PostgreSQL | Simple production, existing pgvector setups |

## Usage in Code

### Basic Vector Search

```python
from keyword_ai.services.vector_db_adapter import search_similar_analyses
from keyword_ai.services.embeddings import get_single_embedding
import numpy as np

# Get embedding for content
text = "machine learning tutorial for beginners"
embedding = get_single_embedding(text)

# Search automatically uses Pinecone if USE_PINECONE=true
results = search_similar_analyses(
    content_embedding=embedding,
    top_k=5,
    min_quality_score=60.0
)

for r in results:
    print(f"{r['title']} (score: {r['similarity_score']:.3f})")
```

### Direct Pinecone Access

```python
from keyword_ai.services.pinecone_service import get_pinecone_service

pc = get_pinecone_service()

# Check if ready
if pc.is_ready():
    # Upsert vectors
    pc.upsert_vectors([
        {
            "id": "analysis_1",
            "values": [0.1, 0.2, ...],  # 384 dimensions
            "metadata": {"url": "...", "title": "..."}
        }
    ])
    
    # Search
    results = pc.search(
        query_vector=[0.1, 0.2, ...],
        top_k=5,
        min_quality_score=50.0
    )
```

### Database Adapter (Recommended)

```python
from keyword_ai.services.vector_db_adapter import (
    search_similar_analyses,
    upsert_analysis_embedding,
    get_vector_db_stats,
    batch_sync_to_pinecone
)

# Unified interface works with both backends
results = search_similar_analyses(embedding, top_k=5)
stats = get_vector_db_stats()
```

## Cost Considerations

| Plan | Vectors | Monthly Cost | Best For |
|------|---------|--------------|----------|
| Free | 100K | $0 | Development, small projects |
| Starter | 2M | ~$70 | Production apps with moderate traffic |
| Standard | 10M+ | ~$200+ | High-traffic applications |

**Tips to reduce costs:**
1. Use pgvector in development (free)
2. Only sync high-quality content to Pinecone
3. Batch operations to minimize API calls
4. Monitor vector count in dashboard

## Troubleshooting

### "Pinecone client not initialized"
- Check `PINECONE_API_KEY` is set correctly
- Verify `USE_PINECONE=true`
- Run `python manage.py sync_pinecone --test-connection`

### "Index not found"
- Create index: `python manage.py sync_pinecone --create-index`
- Or check `PINECONE_INDEX_NAME` matches existing index

### "No results from search"
- Ensure data is synced: `python manage.py sync_pinecone --sync-all`
- Check stats: `python manage.py sync_pinecone --stats`
- Verify embeddings exist in PostgreSQL

### Slow sync
- Use smaller batch sizes: `--batch-size 50`
- Sync only specific records with `--analysis-id`
- Run during off-peak hours for large datasets

## Files Added

| File | Purpose |
|------|---------|
| `keyword_ai/services/pinecone_service.py` | Core Pinecone client |
| `keyword_ai/services/vector_db_adapter.py` | Unified interface |
| `keyword_ai/management/commands/sync_pinecone.py` | CLI for management |
| `PINECONE_SETUP.md` | This guide |

## Migration from pgvector to Pinecone

If you want to completely switch:

1. **Enable dual-write** (recommended for transition):
   ```python
   # In pipeline_v2.py or where embeddings are saved
   from keyword_ai.services.vector_db_adapter import upsert_analysis_embedding
   
   upsert_analysis_embedding(
       analysis_id=analysis.id,
       embedding=embedding,
       sync_to_pinecone=True  # Writes to both
   )
   ```

2. **Sync existing data**:
   ```bash
   python manage.py sync_pinecone --sync-all
   ```

3. **Switch to Pinecone**:
   ```env
   USE_PINECONE=true
   ```

4. **(Optional) Disable pgvector writes**:
   Once Pinecone is stable, you can remove the `embedding` field from PostgreSQL
   to save space, or keep it as a backup.

## Security Notes

- Never commit `PINECONE_API_KEY` to git
- Use environment variables or secrets manager
- Pinecone API key has full access to your index - protect it like a database password
- Consider using separate indexes for dev/staging/production

## Support

- Pinecone docs: https://docs.pinecone.io/
- Pinecone dashboard: https://app.pinecone.io/
- Project issues: Create an issue in the repository
