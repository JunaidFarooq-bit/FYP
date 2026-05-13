"""
Management command to retrain ML models based on feedback.
Usage: python manage.py retrain_models [--model relevance_scorer_v2] [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from keyword_ai.retraining_pipeline import RetrainingPipeline
from keyword_ai.services.feedback_collector import PerformanceTracker


class Command(BaseCommand):
    help = 'Retrain ML models based on collected user feedback'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Specific model to retrain (relevance_scorer_v2, suggestion_generator, etc.)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Check if retraining is needed without actually retraining',
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate current model performance',
        )

    def handle(self, *args, **options):
        model_name = options.get('model')
        dry_run = options.get('dry_run', False)
        validate_only = options.get('validate_only', False)
        
        self.stdout.write(self.style.NOTICE('Starting model retraining pipeline...'))
        self.stdout.write(f"Time: {timezone.now().isoformat()}")
        
        if validate_only:
            self._validate_models()
            return
        
        if model_name:
            # Retrain specific model
            self._retrain_single_model(model_name, dry_run)
        else:
            # Check and retrain all models
            self._retrain_all_models(dry_run)
        
        self.stdout.write(self.style.SUCCESS('Retraining pipeline completed!'))
    
    def _retrain_single_model(self, model_name: str, dry_run: bool):
        """Retrain a specific model."""
        self.stdout.write(f"\nChecking {model_name}...")
        
        # Check if retraining needed
        check = RetrainingPipeline.check_retraining_needed(model_name)
        
        if not check.get("needs_retraining", False):
            self.stdout.write(self.style.WARNING(
                f"  No retraining needed: {check.get('reason', 'Unknown')}"
            ))
            return
        
        self.stdout.write(self.style.NOTICE(
            f"  Retraining recommended: {check.get('reason')}"
        ))
        self.stdout.write(f"  Acceptance rate: {check.get('acceptance_rate', 0):.1f}%")
        self.stdout.write(f"  Feedback samples: {check.get('feedback_count', 0)}")
        
        if dry_run:
            self.stdout.write(self.style.NOTICE("  (Dry run - skipping actual retraining)"))
            return
        
        # Prepare training data
        self.stdout.write("  Preparing training data...")
        data = RetrainingPipeline.prepare_training_data(model_name)
        
        if not data:
            self.stdout.write(self.style.ERROR("  Failed: Insufficient training data"))
            return
        
        self.stdout.write(f"  Samples: {data['training_samples']} " +
                         f"(Pos: {data['positive_samples']}, Neg: {data['negative_samples']})")
        
        # Retrain
        self.stdout.write("  Starting retraining...")
        
        if model_name == "relevance_scorer_v2":
            result = RetrainingPipeline.retrain_relevance_scorer(data)
        else:
            result = {
                "success": False,
                "error": f"Retraining not implemented for {model_name}"
            }
        
        if result.get("success"):
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ Retraining successful: {result.get('message', '')}"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"  ✗ Retraining failed: {result.get('error', 'Unknown error')}"
            ))
    
    def _retrain_all_models(self, dry_run: bool):
        """Check and retrain all models."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Checking all models for retraining needs...")
        self.stdout.write("=" * 50)
        
        results = RetrainingPipeline.run_full_retraining()
        
        for model_name, result in results.get("results", {}).items():
            if result.get("retrained"):
                self.stdout.write(self.style.SUCCESS(
                    f"✓ {model_name}: Retrained successfully"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"○ {model_name}: {result.get('reason', 'No action taken')}"
                ))
    
    def _validate_models(self):
        """Validate current model performance."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Current Model Performance")
        self.stdout.write("=" * 50)
        
        models = ["relevance_scorer_v2", "suggestion_generator", "semantic_mapper"]
        
        for model_name in models:
            self.stdout.write(f"\n{model_name}:")
            history = PerformanceTracker.get_model_performance_history(model_name, days=7)
            
            if history:
                latest = history[-1]
                self.stdout.write(f"  Version: {latest['version']}")
                self.stdout.write(f"  Acceptance rate: {latest['acceptance_rate']:.1f}%")
                self.stdout.write(f"  Total predictions: {latest['total_predictions']:,}")
                if latest['avg_rating']:
                    self.stdout.write(f"  Avg rating: {latest['avg_rating']:.2f}/5")
            else:
                self.stdout.write(self.style.WARNING("  No performance data available"))
