"""
keyword_suggestion/views.py  (UPDATED for continuous training)
=====================================================
The key addition here is that every user search is automatically
logged into the keyword database. This creates a feedback loop:

  User searches "ai seo tools"
        ↓
  Logged to KeywordEntry (source=USER_SEARCH, times_searched++)
        ↓
  Next training run includes "ai seo tools" as a keyword
        ↓
  Future users get better suggestions for trending queries

This is how the model improves over time with zero manual effort.
"""

import json
import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from keyword_suggestion.services.keyword_service import keyword_service

logger = logging.getLogger(__name__)


def _parse_json_body(request):
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON in request body."}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class KeywordSuggestionsView(View):
    """
    POST /api/keyword-suggestions/

    Now also logs the searched keyword into the training pipeline.
    """

    def post(self, request, *args, **kwargs):
        data, error = _parse_json_body(request)
        if error:
            return error

        keyword = data.get("keyword", "").strip()
        if not keyword:
            return JsonResponse({"error": "Keyword is required."}, status=400)

        try:
            top_k = max(1, min(int(data.get("top_k", 10)), 50))
        except (TypeError, ValueError):
            top_k = 10

        # ── Log this search to the training pipeline ──────────
        # This is non-blocking — if it fails, the suggestion still works
        self._log_user_search(keyword)

        # ── Get suggestions ───────────────────────────────────
        try:
            from keyword_suggestion.services.keyword_service import KeywordSuggestionService
            svc = KeywordSuggestionService(top_k=top_k, use_cache=True)
            result = svc.suggest(keyword)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except RuntimeError as e:
            return JsonResponse({"error": str(e)}, status=503)

        return JsonResponse(result, status=200)

    def _log_user_search(self, keyword: str) -> None:
        """
        Logs the search to the keyword DB for future training.

        Runs synchronously but is very fast (single DB upsert).
        For high traffic, offload to a Celery task:
            log_user_search_task.delay(keyword)
        """
        try:
            from pipeline.trend_collector import TrendCollector
            collector = TrendCollector()
            collector.log_user_search(keyword)
        except Exception as e:
            # Never let logging crash the main request
            logger.warning(f"Failed to log user search for '{keyword}': {e}")

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {"message": "Use POST with JSON: { \"keyword\": \"your keyword\" }"},
            status=200
        )


@method_decorator(csrf_exempt, name="dispatch")
class TrainingStatusView(View):
    """
    GET /api/keyword-suggestions/training-status/

    Returns live stats on the model and training pipeline.
    Useful for a dashboard in your SEO tool admin panel.
    """

    def get(self, request, *args, **kwargs):
        from keyword_suggestion.models import ModelTrainingRun, KeywordEntry, KeywordPair

        active_run = ModelTrainingRun.objects.filter(is_active=True).first()
        last_5_runs = ModelTrainingRun.objects.order_by("-created_at")[:5]

        # DB stats
        total_keywords = KeywordEntry.objects.filter(is_active=True).count()
        total_pairs    = KeywordPair.objects.filter(is_active=True).count()
        user_sourced   = KeywordEntry.objects.filter(
            source="user_search", is_active=True
        ).count()

        response = {
            "active_model": {
                "run_id"       : active_run.pk if active_run else None,
                "model_name"   : active_run.model_name if active_run else None,
                "keywords_count": active_run.keywords_count if active_run else 0,
                "trained_at"   : str(active_run.completed_at) if active_run else None,
                "trigger"      : active_run.trigger if active_run else None,
            },
            "database": {
                "total_keywords"   : total_keywords,
                "total_pairs"      : total_pairs,
                "user_sourced_keywords": user_sourced,
            },
            "recent_runs": [
                {
                    "id"          : r.pk,
                    "status"      : r.status,
                    "trigger"     : r.trigger,
                    "keywords"    : r.keywords_count,
                    "new_keywords": r.new_keywords_added,
                    "duration_s"  : r.duration_seconds,
                    "completed_at": str(r.completed_at) if r.completed_at else None,
                    "is_active"   : r.is_active,
                }
                for r in last_5_runs
            ]
        }
        return JsonResponse(response)


@method_decorator(csrf_exempt, name="dispatch")
class TriggerTrainingView(View):
    """
    POST /api/keyword-suggestions/trigger-training/

    Manually triggers a training run from an API call.
    Useful for:
      - Triggering after a bulk keyword import
      - External webhooks (e.g., after deploying new seed keywords)
      - Admin dashboards

    Request body (optional):
        { "mode": "incremental" }   or   { "mode": "full" }
    """

    def post(self, request, *args, **kwargs):
        # In production, add authentication here!
        # e.g.: if not request.user.is_staff: return JsonResponse({...}, status=403)

        data, error = _parse_json_body(request)
        if error:
            data = {}

        mode = data.get("mode", "auto")
        if mode not in ("auto", "incremental", "full"):
            return JsonResponse({"error": "mode must be 'auto', 'incremental', or 'full'"}, status=400)

        try:
            # Queue as a Celery task (non-blocking)
            if mode == "full":
                from pipeline.tasks import run_full_retrain_task
                task = run_full_retrain_task.delay()
            elif mode == "incremental":
                from pipeline.tasks import run_incremental_training_task
                task = run_incremental_training_task.delay()
            else:
                from pipeline.tasks import check_and_train_task
                task = check_and_train_task.delay()

            return JsonResponse({
                "status"  : "queued",
                "mode"    : mode,
                "task_id" : task.id,
                "message" : f"Training task queued. Check /api/keyword-suggestions/training-status/ for updates.",
            })

        except Exception as e:
            # Fallback: run synchronously if Celery isn't set up
            logger.warning(f"Celery not available, running training synchronously: {e}")
            try:
                from pipeline.incremental_trainer import IncrementalTrainer
                trainer = IncrementalTrainer()
                if mode == "full":
                    run = trainer.run_full_retrain()
                elif mode == "incremental":
                    run = trainer.run_incremental()
                else:
                    run = trainer.run_if_needed()

                return JsonResponse({
                    "status"   : "completed",
                    "run_id"   : run.pk if run else None,
                    "keywords" : run.keywords_count if run else 0,
                })
            except Exception as train_err:
                return JsonResponse({"error": str(train_err)}, status=500)