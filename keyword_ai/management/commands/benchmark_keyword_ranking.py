"""Run the versioned offline keyword-ranking benchmark."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from keyword_ai.services.ranking_benchmark import evaluate_cases


class Command(BaseCommand):
    help = "Report Precision@10, acceptance rate, and malformed keyword rate."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            default=str(
                Path(__file__).resolve().parents[2]
                / "dataset"
                / "keyword_ranking_benchmark.json"
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["dataset"])
        cases = json.loads(path.read_text(encoding="utf-8"))
        metrics = evaluate_cases(cases)
        self.stdout.write(json.dumps({"dataset": str(path), **metrics}, indent=2))