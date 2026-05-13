"""
Management command to backfill embeddings for existing ContentAnalysis records.

Usage:
    python manage.py backfill_embeddings [--batch-size 100] [--max-records 1000]

This command generates vector embeddings for ContentAnalysis records that don't have them yet,
enabling RAG (Retrieval-Augmented Generation) for historical content.
"""

import logging
from django.core.management.base import BaseCommand
from tqdm import tqdm

from keyword_ai.models import ContentAnalysis
from keyword_ai.services.embeddings import get_single_embedding

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate embeddings for ContentAnalysis records without embeddings"

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=None,
            help='Maximum number of records to process (default: all)'
        )
        parser.add_argument(
            '--min-quality-score',
            type=float,
            default=40.0,
            help='Only process records with quality_score >= this value (default: 40)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually generating embeddings'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        max_records = options['max_records']
        min_quality_score = options['min_quality_score']
        dry_run = options['dry_run']

        # Find records without embeddings
        queryset = ContentAnalysis.objects.filter(
            embedding__isnull=True,
            quality_score__gte=min_quality_score
        ).order_by('-quality_score', '-analyzed_at')

        if max_records:
            queryset = queryset[:max_records]

        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS("No records need embeddings. All up to date!")
            )
            return

        self.stdout.write(
            f"Found {total_count} records needing embeddings "
            f"(quality_score >= {min_quality_score})"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No changes will be made")
            )
            for record in queryset[:10]:
                self.stdout.write(f"  - {record.url[:60]}... (score: {record.quality_score})")
            if total_count > 10:
                self.stdout.write(f"  ... and {total_count - 10} more")
            return

        # Process records
        processed = 0
        failed = 0
        errors = []

        self.stdout.write("Generating embeddings...")

        with tqdm(total=total_count, desc="Processing") as pbar:
            for record in queryset:
                try:
                    # Build text from available fields
                    text_parts = []
                    if record.title:
                        text_parts.append(record.title)
                    if record.meta_description:
                        text_parts.append(record.meta_description)
                    if record.tfidf_keywords:
                        # Use top TF-IDF keywords as content proxy
                        keywords_text = " ".join([
                            kw.get('keyword', '') 
                            for kw in record.tfidf_keywords[:10]
                        ])
                        text_parts.append(keywords_text)

                    if not text_parts:
                        logger.warning(f"No text content for {record.url}, skipping")
                        failed += 1
                        pbar.update(1)
                        continue

                    text = " ".join(text_parts)

                    # Truncate if too long (embedding model has token limit)
                    if len(text) > 1500:
                        text = text[:1500]

                    # Generate embedding
                    embedding = get_single_embedding(text)
                    record.embedding = embedding.tolist()
                    record.save(update_fields=['embedding'])

                    processed += 1

                except Exception as e:
                    failed += 1
                    error_msg = f"Failed for {record.url}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

                pbar.update(1)

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"Total records: {total_count}")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed: {processed}")
        )
        if failed > 0:
            self.stdout.write(
                self.style.ERROR(f"Failed: {failed}")
            )

        if errors and failed <= 10:
            self.stdout.write("\nErrors:")
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        self.stdout.write("\n" + self.style.SUCCESS(
            "Embedding backfill complete! RAG is now available for these records."
        ))
