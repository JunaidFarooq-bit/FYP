"""
Management command to sync embeddings from PostgreSQL to Pinecone.

Usage:
    python manage.py sync_pinecone [--create-index] [--sync-all] [--analysis-id 123]

This command syncs vector embeddings from PostgreSQL (pgvector) to Pinecone
for faster, scalable similarity search in production.

Prerequisites:
    - Set PINECONE_API_KEY in your .env file
    - Set USE_PINECONE=True in your .env file (optional, for switching to Pinecone)

Examples:
    # Check Pinecone connection and stats
    python manage.py sync_pinecone --stats
    
    # Create Pinecone index (if it doesn't exist)
    python manage.py sync_pinecone --create-index
    
    # Sync all embeddings to Pinecone
    python manage.py sync_pinecone --sync-all
    
    # Sync specific analysis
    python manage.py sync_pinecone --analysis-id 123
    
    # Test vector search with both backends
    python manage.py sync_pinecone --test-search "https://example.com"
"""

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from tqdm import tqdm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync embeddings from PostgreSQL to Pinecone vector database"

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-index',
            action='store_true',
            help='Create Pinecone index if it does not exist'
        )
        parser.add_argument(
            '--force-recreate',
            action='store_true',
            help='Delete and recreate the index (WARNING: destroys all data)'
        )
        parser.add_argument(
            '--sync-all',
            action='store_true',
            help='Sync all ContentAnalysis records with embeddings to Pinecone'
        )
        parser.add_argument(
            '--analysis-id',
            type=int,
            default=None,
            help='Sync a specific ContentAnalysis record by ID'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records per batch (default: 100)'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show vector database statistics'
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connectivity to Pinecone and pgvector'
        )
        parser.add_argument(
            '--test-search',
            type=str,
            default=None,
            help='Test search with a URL (must exist in database)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )

    def handle(self, *args, **options):
        # Import here to avoid slow startup if Pinecone not configured
        from keyword_ai.services.pinecone_service import get_pinecone_service, sync_content_analysis_to_pinecone
        from keyword_ai.services.vector_db_adapter import (
            test_vector_db_connection,
            get_vector_db_stats,
            batch_sync_to_pinecone
        )
        from keyword_ai.models import ContentAnalysis
        from keyword_ai.services.embeddings import get_single_embedding

        # Check if Pinecone is configured
        if not settings.PINECONE_API_KEY:
            self.stdout.write(
                self.style.ERROR(
                    "PINECONE_API_KEY not set in environment.\n"
                    "Add PINECONE_API_KEY=your_key to your .env file"
                )
            )
            return

        pc = get_pinecone_service()

        # Test connection
        if options['test_connection']:
            self._test_connection()
            return

        # Show stats
        if options['stats']:
            self._show_stats()
            return

        # Create index
        if options['create_index']:
            self._create_index(pc, force=options['force_recreate'])
            return

        # Sync specific analysis
        if options['analysis_id']:
            self._sync_single(options['analysis_id'], dry_run=options['dry_run'])
            return

        # Sync all
        if options['sync_all']:
            self._sync_all(batch_size=options['batch_size'], dry_run=options['dry_run'])
            return

        # Test search
        if options['test_search']:
            self._test_search(options['test_search'])
            return

        # No action specified - show help
        self.stdout.write(self.style.WARNING("No action specified. Use --help for options."))
        self._show_stats()

    def _test_connection(self):
        """Test connectivity to both backends."""
        from keyword_ai.services.vector_db_adapter import test_vector_db_connection
        
        self.stdout.write("Testing vector database connections...")
        results = test_vector_db_connection()
        
        # PostgreSQL/pgvector
        pg = results.get('pgvector', {})
        if pg.get('status') == 'connected':
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ PostgreSQL (pgvector): Connected"
                    f" ({pg.get('embeddings_count', 0)} embeddings)"
                )
            )
        elif pg.get('status') == 'limited':
            self.stdout.write(
                self.style.WARNING(f"⚠ PostgreSQL: {pg.get('message')}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ PostgreSQL: {pg.get('error', 'Unknown error')}")
            )
        
        # Pinecone
        pc = results.get('pinecone', {})
        if pc.get('status') == 'connected':
            stats = pc.get('stats', {})
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Pinecone: Connected"
                    f" (index: {pc.get('index_name')},"
                    f" vectors: {stats.get('total_vector_count', 0)})"
                )
            )
        elif pc.get('status') == 'disabled':
            self.stdout.write(
                self.style.WARNING("⚠ Pinecone: Disabled (set USE_PINECONE=True to enable)")
            )
        elif pc.get('status') == 'not_configured':
            self.stdout.write(
                self.style.ERROR(f"✗ Pinecone: {pc.get('message')}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ Pinecone: {pc.get('error', 'Unknown error')}")
            )

    def _show_stats(self):
        """Show vector database statistics."""
        from keyword_ai.services.vector_db_adapter import get_vector_db_stats
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.NOTICE("Vector Database Statistics"))
        self.stdout.write("=" * 50)
        
        stats = get_vector_db_stats()
        
        # PostgreSQL stats
        pg = stats.get('pgvector', {})
        self.stdout.write("\nPostgreSQL (pgvector):")
        if 'error' in pg:
            self.stdout.write(self.style.ERROR(f"  Error: {pg['error']}"))
        else:
            self.stdout.write(f"  Total analyses: {pg.get('total_analyses', 0)}")
            self.stdout.write(f"  With embeddings: {pg.get('with_embeddings', 0)}")
            self.stdout.write(f"  Coverage: {pg.get('coverage_percent', 0)}%")
            self.stdout.write(f"  Database: {pg.get('database', 'unknown')}")
        
        # Pinecone stats
        self.stdout.write("\nPinecone:")
        pc = stats.get('pinecone')
        if pc is None:
            self.stdout.write("  Status: Not configured")
        elif 'error' in pc:
            self.stdout.write(self.style.ERROR(f"  Error: {pc['error']}"))
        else:
            self.stdout.write(f"  Dimension: {pc.get('dimension', 'N/A')}")
            self.stdout.write(f"  Total vectors: {pc.get('total_vector_count', 0)}")
            self.stdout.write(f"  Index fullness: {pc.get('index_fullness', 0):.2%}")
        
        self.stdout.write("\n" + "=" * 50)
        active = stats.get('active_backend', 'pgvector')
        self.stdout.write(f"Active backend: {self.style.NOTICE(active)}")

    def _create_index(self, pc, force=False):
        """Create Pinecone index."""
        if not pc.is_ready():
            self.stdout.write(
                self.style.ERROR("Pinecone client not initialized. Check PINECONE_API_KEY.")
            )
            return
        
        if force:
            self.stdout.write(
                self.style.WARNING("WARNING: This will delete all existing vectors in Pinecone!")
            )
            confirm = input("Type 'yes' to confirm: ")
            if confirm != 'yes':
                self.stdout.write("Cancelled.")
                return
        
        self.stdout.write(f"Creating index '{settings.PINECONE_INDEX_NAME}'...")
        
        if pc.create_index(force=force):
            self.stdout.write(
                self.style.SUCCESS(f"✓ Index '{settings.PINECONE_INDEX_NAME}' ready")
            )
        else:
            self.stdout.write(
                self.style.ERROR("Failed to create index. Check logs for details.")
            )

    def _sync_single(self, analysis_id, dry_run=False):
        """Sync a single analysis record."""
        from keyword_ai.models import ContentAnalysis
        from keyword_ai.services.pinecone_service import sync_content_analysis_to_pinecone
        
        try:
            analysis = ContentAnalysis.objects.get(id=analysis_id)
        except ContentAnalysis.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"ContentAnalysis with ID {analysis_id} not found")
            )
            return
        
        if not analysis.embedding:
            self.stdout.write(
                self.style.WARNING(f"Analysis {analysis_id} has no embedding. Run backfill_embeddings first.")
            )
            return
        
        self.stdout.write(f"Syncing analysis {analysis_id}: {analysis.url}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No changes made")
            )
            self.stdout.write(f"Would sync: analysis_{analysis_id}")
            return
        
        if sync_content_analysis_to_pinecone(analysis_id):
            self.stdout.write(
                self.style.SUCCESS(f"✓ Synced analysis {analysis_id} to Pinecone")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to sync analysis {analysis_id}")
            )

    def _sync_all(self, batch_size=100, dry_run=False):
        """Sync all analyses with embeddings."""
        from keyword_ai.services.vector_db_adapter import batch_sync_to_pinecone
        
        self.stdout.write("Starting batch sync to Pinecone...")
        
        if dry_run:
            from keyword_ai.models import ContentAnalysis
            count = ContentAnalysis.objects.filter(embedding__isnull=False).count()
            self.stdout.write(
                self.style.WARNING(f"DRY RUN - Would sync {count} vectors")
            )
            return
        
        result = batch_sync_to_pinecone(batch_size=batch_size)
        
        if result.get('success'):
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Synced {result.get('synced', 0)} vectors "
                    f"({result.get('failed', 0)} failed)"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Sync failed: {result.get('error')}")
            )

    def _test_search(self, url):
        """Test vector search with a URL."""
        from keyword_ai.models import ContentAnalysis
        from keyword_ai.services.vector_db_adapter import search_similar_analyses
        from keyword_ai.services.pinecone_service import search_similar_with_pinecone
        import numpy as np
        
        try:
            analysis = ContentAnalysis.objects.get(url=url)
        except ContentAnalysis.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"URL not found in database: {url}")
            )
            return
        
        if not analysis.embedding:
            self.stdout.write(
                self.style.ERROR(f"No embedding for this URL. Run backfill_embeddings first.")
            )
            return
        
        embedding = analysis.get_embedding_list()
        if not embedding:
            self.stdout.write(self.style.ERROR("Failed to load embedding"))
            return
        
        self.stdout.write(f"\nTesting vector search for: {url}")
        self.stdout.write("=" * 50)
        
        # Test pgvector (always available if PostgreSQL)
        self.stdout.write("\npgvector results:")
        from django.db import connection
        if connection.vendor == 'postgresql':
            from keyword_ai.services.vector_db_adapter import _search_with_pgvector
            pg_results = _search_with_pgvector(np.array(embedding), top_k=3)
            for i, r in enumerate(pg_results, 1):
                self.stdout.write(f"  {i}. {r['title'][:50]}... (sim: {r['similarity_score']:.3f})")
        else:
            self.stdout.write("  (PostgreSQL not available)")
        
        # Test Pinecone if configured
        if settings.USE_PINECONE and settings.PINECONE_API_KEY:
            self.stdout.write("\nPinecone results:")
            pc_results = search_similar_with_pinecone(np.array(embedding), top_k=3)
            if pc_results:
                for i, r in enumerate(pc_results, 1):
                    title = r.get('title', 'N/A')[:50]
                    score = r.get('similarity_score', 0)
                    self.stdout.write(f"  {i}. {title}... (sim: {score:.3f})")
            else:
                self.stdout.write("  (No results - index may be empty)")
        else:
            self.stdout.write("\nPinecone: Not configured")
