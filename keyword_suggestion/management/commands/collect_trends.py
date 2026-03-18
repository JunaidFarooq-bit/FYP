"""
seo_tool/management/commands/collect_trends.py
================================================
Django management command to manually trigger trend collection.

Usage:
    python manage.py collect_trends
    python manage.py collect_trends --source autocomplete
    python manage.py collect_trends --source trends
    python manage.py collect_trends --source rss
    python manage.py collect_trends --dry-run
    python manage.py collect_trends --seeds "ai seo" "sge optimization" "search generative experience"
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Collect trending keywords from Google Autocomplete, Trends, and RSS feeds."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["all", "autocomplete", "trends", "rss"],
            default="all",
            help="Which collection source to use (default: all).",
        )
        parser.add_argument(
            "--seeds",
            nargs="+",
            type=str,
            default=None,
            help="Specific seed keywords for autocomplete collection.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Collect and log keywords but do NOT save to the database.",
        )

    def handle(self, *args, **options):
        from pipeline.trend_collector import TrendCollector

        source  = options["source"]
        dry_run = options["dry_run"]
        seeds   = options["seeds"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE — nothing will be saved."))

        collector = TrendCollector(dry_run=dry_run)
        start = timezone.now()

        self.stdout.write(f"Starting {source} collection at {start.strftime('%H:%M:%S')}...")

        try:
            if source == "all":
                stats = collector.collect_all()
            elif source == "autocomplete":
                new = collector.collect_autocomplete(seeds=seeds)
                stats = {"autocomplete_new": new}
            elif source == "trends":
                new = collector.collect_google_trends()
                stats = {"trends_new": new}
            elif source == "rss":
                new = collector.collect_from_rss()
                stats = {"rss_new": new}

            duration = (timezone.now() - start).total_seconds()
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Collection complete in {duration:.1f}s"
            ))
            for key, val in stats.items():
                self.stdout.write(f"   {key}: {val}")

        except Exception as e:
            raise CommandError(f"Collection failed: {e}")