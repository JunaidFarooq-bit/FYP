# PostgreSQL Setup Guide for Keyword AI (RAG)

This guide walks you through installing PostgreSQL and configuring it for the Keyword AI system with full RAG (Retrieval-Augmented Generation) support.

---

## Step 1: Install PostgreSQL

### Option A: Windows Installer (Recommended)

1. Download PostgreSQL 15+ from: https://www.postgresql.org/download/windows/
2. Run the installer
3. Remember the **password** you set for the `postgres` user
4. Keep the default port: **5432**
5. Complete installation (includes pgAdmin4 management tool)

### Option B: Using Chocolatey (Windows Package Manager)

```powershell
# Run as Administrator
choco install postgresql
```

### Option C: Docker (Easiest for Development)

```bash
# Pull and run PostgreSQL with pgvector pre-installed
docker run -d \
  --name keyword-ai-db \
  -e POSTGRES_USER=keywordai \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=keywordai_db \
  -p 5432:5432 \
  ankane/pgvector:latest
```

---

## Step 2: Install pgvector Extension

### Windows (Manual)

If you used the standard PostgreSQL installer:

```sql
-- Connect to PostgreSQL using psql or pgAdmin
-- Run as postgres superuser

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Docker (Already Included)

The `ankane/pgvector` image already includes pgvector. Skip this step.

---

## Step 3: Create Database and User

### Using psql Command Line

```bash
# Open psql (add PostgreSQL bin to PATH first or use full path)
psql -U postgres -h localhost -p 5432

# Create database
CREATE DATABASE keywordai_db;

# Create user
CREATE USER keywordai_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE keywordai_db TO keywordai_user;

-- Exit
\q
```

### Using pgAdmin4 (GUI)

1. Open pgAdmin4 (installed with PostgreSQL)
2. Connect to PostgreSQL server
3. Right-click "Databases" → "Create" → "Database"
4. Name: `keywordai_db`
5. Right-click "Login/Group Roles" → "Create" → "Login/Group Role"
6. Name: `keywordai_user`
7. Set password
8. In Privileges tab, grant all on `keywordai_db`

---

## Step 4: Update Django Settings

Edit `e:\Project\Project\settings.py`:

```python
import os
from pathlib import Path

# ... existing imports ...

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# PostgreSQL with pgvector (for full RAG support)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'keywordai_db',           # Your database name
        'USER': 'keywordai_user',         # Your database user
        'PASSWORD': 'your_secure_password',  # Your password
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# SQLite fallback (commented out - use for testing without RAG)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
```

### Using Environment Variables (Recommended for Production)

```python
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'keywordai_db'),
        'USER': os.getenv('DB_USER', 'keywordai_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'default_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

Create `.env` file:
```bash
DB_NAME=keywordai_db
DB_USER=keywordai_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

---

## Step 5: Install Python Dependencies

```bash
# Install PostgreSQL adapter and pgvector
pip install psycopg2-binary pgvector

# Or if using requirements.txt (already added)
pip install -r requirements.txt
```

---

## Step 6: Run Migrations

```bash
# Apply all migrations (this will create pgvector extension)
python manage.py migrate

# Create superuser (optional, for admin access)
python manage.py createsuperuser
```

You should see:
```
Operations to perform:
  Apply all migrations: keyword_ai
Running migrations:
  Applying keyword_ai.0001_phase1_content_analysis_models... OK
  Applying keyword_ai.0002_phase4_async_tasks... OK
  Applying keyword_ai.0003_phase5_feedback_continuous_learning... OK
  Applying keyword_ai.0004_phase6_rag_vector_search... OK
  Creating pgvector extension... OK
  Creating HNSW index... OK
```

---

## Step 7: Verify pgvector Installation

```bash
# Open PostgreSQL shell
psql -U keywordai_user -d keywordai_db -h localhost -p 5432

-- Verify pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test vector operations
SELECT '[1,2,3]'::vector <=> '[4,5,6]'::vector AS distance;

-- Exit
\q
```

---

## Step 8: Backfill Embeddings (If Migrating from SQLite)

If you have existing data:

```bash
# Run the backfill command
python manage.py backfill_embeddings --batch-size 100

# Or process only high-quality content
python manage.py backfill_embeddings --min-quality-score 70 --max-records 1000
```

---

## Step 9: Test RAG is Working

```bash
# Start Django shell
python manage.py shell

# Test RAG retrieval
>>> from keyword_ai.services.rag_retriever import retrieve_similar_analyses
>>> from keyword_ai.services.embeddings import get_single_embedding
>>>
>>> # Create test embedding
>>> embedding = get_single_embedding("artificial intelligence machine learning")
>>>
>>> # Test retrieval
>>> results = retrieve_similar_analyses(embedding, top_k=3)
>>> print(f"Retrieved {len(results)} similar analyses")
>>> for r in results:
...     print(f"  - {r['url']} (score: {r['similarity_score']:.2f})")
```

---

## Troubleshooting

### Error: "FATAL: password authentication failed"

1. Verify password in settings.py matches PostgreSQL user password
2. Check pg_hba.conf allows local connections:
   ```
   # In pg_hba.conf (PostgreSQL data directory)
   # Change:
   host    all             all             127.0.0.1/32            scram-sha-256
   # To (less secure, for testing):
   host    all             all             127.0.0.1/32            trust
   ```
3. Reload PostgreSQL configuration

### Error: "Extension 'vector' does not exist"

```sql
-- Install pgvector manually
CREATE EXTENSION vector;

-- If that fails, you may need to install pgvector binaries
-- Download from: https://github.com/pgvector/pgvector/releases
```

### Error: "HNSW index creation failed"

```sql
-- Check pgvector version
SELECT extversion FROM pg_extension WHERE extname = 'vector';

-- HNSW requires pgvector 0.5.0+
-- If older version, use IVFFlat instead or upgrade
```

### Cannot Connect to PostgreSQL

```bash
# Check if PostgreSQL is running
# Windows: Services app → PostgreSQL → Start
# Or command line:
pg_ctl status -D "C:\Program Files\PostgreSQL\15\data"

# Start if stopped
pg_ctl start -D "C:\Program Files\PostgreSQL\15\data"
```

---

## Performance Tuning (Optional)

### PostgreSQL Configuration

Edit `postgresql.conf` (in PostgreSQL data directory):

```ini
# Memory settings (adjust based on your RAM)
shared_buffers = 256MB
work_mem = 16MB
maintenance_work_mem = 128MB

# Connection settings
max_connections = 100

# Enable for pgvector performance
random_page_cost = 1.1
effective_cache_size = 1GB
```

Restart PostgreSQL after changes.

---

## Migration from SQLite to PostgreSQL

### 1. Export SQLite Data

```bash
# Dump SQLite data
python manage.py dumpdata > backup.json
```

### 2. Switch to PostgreSQL

Update `settings.py` with PostgreSQL credentials (Step 4).

### 3. Create Tables

```bash
python manage.py migrate
```

### 4. Import Data

```bash
# Load data into PostgreSQL
python manage.py loaddata backup.json

# Backfill embeddings for RAG
python manage.py backfill_embeddings
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start PostgreSQL | `pg_ctl start -D <data_dir>` |
| Stop PostgreSQL | `pg_ctl stop -D <data_dir>` |
| Connect to db | `psql -U <user> -d <db>` |
| List databases | `\l` (in psql) |
| List tables | `\dt` (in psql) |
| Check extensions | `SELECT * FROM pg_extension;` |
| Check indexes | `SELECT * FROM pg_indexes WHERE tablename = 'keyword_ai_contentanalysis';` |

---

## Success Checklist

- [ ] PostgreSQL installed and running
- [ ] pgvector extension created
- [ ] Database and user created
- [ ] Django settings updated
- [ ] Migrations applied successfully
- [ ] RAG retrieval test passes
- [ ] Keyword analysis API working with RAG

You're ready to use full RAG with vector similarity search!
