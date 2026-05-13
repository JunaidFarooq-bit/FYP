"""
Phase 6: RAG (Retrieval-Augmented Generation) with pgvector

Enables vector similarity search for content analysis.
- Installs pgvector PostgreSQL extension (PostgreSQL only)
- Adds vector index on embedding field
- Enables cosine similarity queries for RAG
"""

from django.db import migrations, models, connection
import pgvector.django


def create_vector_extension(apps, schema_editor):
    """Create pgvector extension only on PostgreSQL."""
    if connection.vendor == 'postgresql':
        try:
            schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception:
            # pgvector not installed on server, skip
            pass


def drop_vector_extension(apps, schema_editor):
    """Drop pgvector extension only on PostgreSQL."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("DROP EXTENSION IF EXISTS vector;")


def create_hnsw_index(apps, schema_editor):
    """Create HNSW index only on PostgreSQL."""
    if connection.vendor == 'postgresql':
        try:
            schema_editor.execute("""
                CREATE INDEX IF NOT EXISTS contentanalysis_embedding_idx 
                ON keyword_ai_contentanalysis 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
        except Exception:
            # pgvector extension not available, skip index creation
            pass


def drop_hnsw_index(apps, schema_editor):
    """Drop HNSW index only on PostgreSQL."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("DROP INDEX IF EXISTS contentanalysis_embedding_idx;")


class Migration(migrations.Migration):
    """
    Phase 6: Add pgvector support for RAG retrieval.
    Works with PostgreSQL (full RAG) and SQLite (fallback to JSON storage).
    """
    
    dependencies = [
        ('keyword_ai', '0003_phase5_feedback_continuous_learning'),
    ]
    
    operations = [
        # Install pgvector extension (PostgreSQL only)
        migrations.RunPython(create_vector_extension, drop_vector_extension),
        
        # Remove old embedding_vector TextField
        migrations.RemoveField(
            model_name='contentanalysis',
            name='embedding_vector',
        ),
        
        # Add new embedding VectorField (384 dimensions for all-MiniLM-L6-v2)
        # On SQLite, this stores as JSON; on PostgreSQL, uses pgvector
        migrations.AddField(
            model_name='contentanalysis',
            name='embedding',
            field=pgvector.django.VectorField(
                dimensions=384, 
                blank=True, 
                null=True,
                help_text='Vector embedding for RAG similarity search (384-dim from all-MiniLM-L6-2)'
            ),
        ),
        
        # Add HNSW index for fast approximate nearest neighbor search (PostgreSQL only)
        migrations.RunPython(create_hnsw_index, drop_hnsw_index),
        
        # Add index on quality_score + analyzed_at for filtered similarity queries
        migrations.AddIndex(
            model_name='contentanalysis',
            index=models.Index(
                fields=['quality_score', '-analyzed_at'],
                name='contentanalysis_quality_analyzed_idx'
            ),
        ),
        
        # Add index on URL for faster lookups
        migrations.AddIndex(
            model_name='contentanalysis',
            index=models.Index(
                fields=['url'],
                name='contentanalysis_url_idx'
            ),
        ),
    ]
