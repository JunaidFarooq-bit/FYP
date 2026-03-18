"""
keyword_suggestion/management/commands/run_training.py
=============================================
Django management command to trigger model training manually.

Usage:
    python manage.py run_training                    # smart (auto-decides)
    python manage.py run_training --mode incremental # add new keywords only
    python manage.py run_training --mode full        # rebuild everything
    python manage.py run_training --rollback         # revert to previous model
    python manage.py run_training --status           # show current model info
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Trigger keyword suggestion model training or rollback."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["auto", "incremental", "full"],
            default="auto",
            help=(
                "Training mode:\n"
                "  auto        = let the system decide (default)\n"
                "  incremental = only encode new keywords (fast)\n"
                "  full        = rebuild entire index from scratch\n"
            ),
        )
        parser.add_argument(
            "--rollback",
            action="store_true",
            default=False,
            help="Rollback to the previous successful training run.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            default=False,
            help="Show current model status without training.",
        )

    def handle(self, *args, **options):
        from pipeline.incremental_trainer import IncrementalTrainer
        from keyword_suggestion.models import ModelTrainingRun

        # ── Show status ───────────────────────────────────────
        if options["status"]:
            self._show_status()
            return

        # ── Rollback ──────────────────────────────────────────
        if options["rollback"]:
            trainer = IncrementalTrainer()
            success = trainer.rollback_to_previous()
            if success:
                self.stdout.write(self.style.SUCCESS("✅ Rollback successful."))
            else:
                self.stdout.write(self.style.ERROR("❌ Rollback failed. Check logs."))
            return

        # ── Training ──────────────────────────────────────────
        mode = options["mode"]
        trainer = IncrementalTrainer()
        start = timezone.now()

        self.stdout.write(f"Starting {mode} training at {start.strftime('%H:%M:%S')}...")

        try:
            if mode == "full":
                run = trainer.run_full_retrain(
                    trigger=ModelTrainingRun.TriggerType.MANUAL
                )
            elif mode == "incremental":
                run = trainer.run_incremental(
                    trigger=ModelTrainingRun.TriggerType.MANUAL
                )
            else:  # auto
                run = trainer.run_if_needed()
                if run is None:
                    self.stdout.write(self.style.WARNING(
                        "⏭  Training skipped — not enough new keywords. "
                        "Use --mode full to force a retrain."
                    ))
                    return

            duration = run.duration_seconds or 0
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Training complete!"
            ))
            self.stdout.write(f"   Run ID          : #{run.pk}")
            self.stdout.write(f"   Status          : {run.status}")
            self.stdout.write(f"   Keywords in index: {run.keywords_count:,}")
            self.stdout.write(f"   New keywords     : {run.new_keywords_added:,}")
            self.stdout.write(f"   Duration         : {duration:.1f}s")
            self.stdout.write(f"   Index path       : {run.faiss_index_path}")

        except Exception as e:
            raise CommandError(f"Training failed: {e}")

    def _show_status(self):
        """Displays current model and recent training history."""
        from keyword_suggestion.models import ModelTrainingRun, KeywordEntry

        # Active run
        active = ModelTrainingRun.objects.filter(is_active=True).first()
        if active:
            self.stdout.write(self.style.SUCCESS("\n📊 Active Model:"))
            self.stdout.write(f"   Run ID       : #{active.pk}")
            self.stdout.write(f"   Model        : {active.model_name}")
            self.stdout.write(f"   Keywords     : {active.keywords_count:,}")
            self.stdout.write(f"   Trained at   : {active.completed_at}")
            self.stdout.write(f"   Trigger      : {active.trigger}")
        else:
            self.stdout.write(self.style.WARNING("No active model found."))

        # DB stats
        total_kw = KeywordEntry.objects.filter(is_active=True).count()
        self.stdout.write(f"\n📂 Database Keywords: {total_kw:,} active")

        # Recent runs
        recent = ModelTrainingRun.objects.order_by("-created_at")[:5]
        self.stdout.write("\n🕐 Recent Training Runs:")
        for run in recent:
            flag = " ← ACTIVE" if run.is_active else ""
            duration = f"{run.duration_seconds:.0f}s" if run.duration_seconds else "N/A"
            self.stdout.write(
                f"   #{run.pk:3} | {run.status:10} | "
                f"{run.keywords_count:6,} kw | "
                f"{duration:8} | "
                f"{str(run.completed_at or run.created_at)[:19]}{flag}"
            )