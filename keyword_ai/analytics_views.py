"""
Analytics Dashboard Views for Monitoring (Phase 5)
Provides API endpoints for analytics and monitoring.
"""

import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta

from .services.feedback_collector import (
    FeedbackCollector,
    PerformanceTracker,
    ContinuousLearningMonitor,
)
from .services.ab_testing import ABTestManager
from .retraining_pipeline import RetrainingPipeline
from .models import (
    AnalysisTask,
    SuggestionFeedback,
    KeywordOpportunity,
    ContentAnalysis,
    ModelPerformance,
    ABTest,
)


@require_http_methods(["GET"])
def get_dashboard_summary(request):
    """
    Get overall dashboard summary metrics.
    
    GET /api/keywords/analytics/dashboard/
    """
    # System health
    health = PerformanceTracker.get_system_health()
    
    # Recent activity
    since_24h = timezone.now() - timedelta(hours=24)
    since_7d = timezone.now() - timedelta(days=7)
    
    recent_analyses = AnalysisTask.objects.filter(
        created_at__gte=since_24h
    ).count()
    
    recent_feedback = SuggestionFeedback.objects.filter(
        timestamp__gte=since_24h
    ).count()
    
    # Active A/B tests
    active_tests = ABTest.objects.filter(status='running').count()
    
    # Pending retraining recommendations
    retraining_needs = ContinuousLearningMonitor.get_retraining_recommendations()
    
    data = {
        "system_health": health,
        "recent_activity": {
            "last_24h": {
                "analyses": recent_analyses,
                "feedback_submitted": recent_feedback,
            }
        },
        "active_ab_tests": active_tests,
        "retraining_recommendations": len(retraining_needs),
        "models_needing_retrain": [r["model"] for r in retraining_needs],
    }
    
    return JsonResponse(data)


@require_http_methods(["GET"])
def get_model_performance(request):
    """
    Get model performance metrics.
    
    GET /api/keywords/analytics/model-performance/?model=relevance_scorer_v2&days=30
    """
    model_name = request.GET.get("model", "")
    days = int(request.GET.get("days", 30))
    
    if not model_name:
        # Return all models summary
        models = ModelPerformance.objects.values('model_name').distinct()
        summary = []
        
        for m in models:
            name = m['model_name']
            perf = PerformanceTracker.get_model_performance_history(name, days=days)
            latest = perf[-1] if perf else None
            
            summary.append({
                "model_name": name,
                "latest_version": latest['version'] if latest else None,
                "acceptance_rate": latest['acceptance_rate'] if latest else 0,
                "total_predictions": latest['total_predictions'] if latest else 0,
                "history": perf,
            })
        
        return JsonResponse({"models": summary})
    
    # Specific model
    history = PerformanceTracker.get_model_performance_history(model_name, days=days)
    
    return JsonResponse({
        "model_name": model_name,
        "days": days,
        "history": history,
        "latest": history[-1] if history else None,
    })


@require_http_methods(["GET"])
def get_feedback_analytics(request):
    """
    Get detailed feedback analytics.
    
    GET /api/keywords/analytics/feedback/?days=30&group_by=keyword_type
    """
    days = int(request.GET.get("days", 30))
    group_by = request.GET.get("group_by", "action")
    
    since = timezone.now() - timedelta(days=days)
    
    # Get all feedback
    feedback = SuggestionFeedback.objects.filter(timestamp__gte=since)
    
    total = feedback.count()
    
    if total == 0:
        return JsonResponse({
            "period_days": days,
            "total_feedback": 0,
            "message": "No feedback in this period",
        })
    
    # Group by action
    action_counts = {}
    for action in ['accepted', 'rejected', 'implemented', 'ignored']:
        action_counts[action] = feedback.filter(user_action=action).count()
    
    # Group by keyword type if requested
    type_breakdown = {}
    if group_by == 'keyword_type':
        types = KeywordOpportunity.objects.filter(
            created_at__gte=since
        ).values('keyword_type').distinct()
        
        for t in types:
            type_name = t['keyword_type']
            type_feedback = FeedbackCollector.get_feedback_by_keyword_type(type_name, days)
            type_breakdown[type_name] = type_feedback
    
    # Rating distribution
    ratings = feedback.filter(rating__isnull=False).values('rating').annotate(count=Count('rating'))
    rating_dist = {r['rating']: r['count'] for r in ratings}
    
    return JsonResponse({
        "period_days": days,
        "total_feedback": total,
        "action_breakdown": action_counts,
        "acceptance_rate": round(
            (action_counts.get('accepted', 0) + action_counts.get('implemented', 0)) / 
            max(total, 1) * 100, 2
        ),
        "by_keyword_type": type_breakdown if type_breakdown else None,
        "rating_distribution": rating_dist,
    })


@require_http_methods(["GET"])
def get_ab_test_results(request):
    """
    Get A/B test results and status.
    
    GET /api/keywords/analytics/ab-tests/?status=running
    """
    status = request.GET.get("status", "all")
    
    if status == "all":
        tests = ABTest.objects.all().order_by('-started_at')
    else:
        tests = ABTest.objects.filter(status=status).order_by('-started_at')
    
    results = []
    for test in tests:
        # Compute detailed results
        detailed = ABTestManager.compute_test_results(test.id)
        
        results.append({
            "id": test.id,
            "name": test.test_name,
            "status": test.status,
            "control_model": test.control_model,
            "treatment_model": test.treatment_model,
            "traffic_split": test.traffic_split_percent,
            "winner": test.winner,
            "confidence": test.confidence_level,
            "started": test.started_at.isoformat(),
            "completed": test.completed_at.isoformat() if test.completed_at else None,
            "metrics": detailed,
        })
    
    return JsonResponse({
        "tests": results,
        "active_count": len([t for t in results if t['status'] == 'running']),
    })


@require_http_methods(["GET"])
def get_retraining_status(request):
    """
    Get retraining recommendations and status.
    
    GET /api/keywords/analytics/retraining/
    """
    # Get recommendations
    recommendations = ContinuousLearningMonitor.get_retraining_recommendations()
    
    # Check status for each model
    status = {}
    for model_name in RetrainingPipeline.MODEL_CONFIGS.keys():
        check = RetrainingPipeline.check_retraining_needed(model_name)
        status[model_name] = check
    
    return JsonResponse({
        "recommendations": recommendations,
        "model_status": status,
        "total_models_needing_retrain": len(recommendations),
    })


@csrf_exempt
@require_http_methods(["POST"])
def trigger_retraining(request):
    """
    Manually trigger model retraining.
    
    POST /api/keywords/analytics/trigger-retrain/
    Body: {"model": "relevance_scorer_v2"} or {} for all
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        body = {}
    
    model_name = body.get("model", "")
    
    if model_name:
        # Retrain specific model
        data = RetrainingPipeline.prepare_training_data(model_name)
        if not data:
            return JsonResponse({
                "success": False,
                "error": "Insufficient training data"
            }, status=400)
        
        if model_name == "relevance_scorer_v2":
            result = RetrainingPipeline.retrain_relevance_scorer(data)
        else:
            result = {
                "success": False,
                "error": f"Retraining not implemented for {model_name}"
            }
        
        return JsonResponse(result)
    
    else:
        # Retrain all models needing it
        results = RetrainingPipeline.run_full_retraining()
        return JsonResponse(results)


@csrf_exempt
@require_http_methods(["POST"])
def create_ab_test(request):
    """
    Create a new A/B test.
    
    POST /api/keywords/analytics/create-ab-test/
    Body: {
        "test_name": "Relevance Scorer v2 vs v3",
        "control_model": "relevance_scorer_v2",
        "treatment_model": "relevance_scorer_v3",
        "traffic_split": 50
    }
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    
    test_name = body.get("test_name", "")
    control = body.get("control_model", "")
    treatment = body.get("treatment_model", "")
    
    if not all([test_name, control, treatment]):
        return JsonResponse({
            "error": "Missing required fields: test_name, control_model, treatment_model"
        }, status=400)
    
    test = ABTestManager.create_test(
        test_name=test_name,
        control_model=control,
        treatment_model=treatment,
        traffic_split_percent=body.get("traffic_split", 50),
        test_description=body.get("description", ""),
    )
    
    return JsonResponse({
        "success": True,
        "test_id": test.id,
        "test_name": test.test_name,
        "status": test.status,
    })


@csrf_exempt
@require_http_methods(["POST"])
def stop_ab_test(request):
    """
    Stop an A/B test.
    
    POST /api/keywords/analytics/stop-ab-test/
    Body: {"test_id": 1, "winner": "treatment"}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    
    test_id = body.get("test_id")
    winner = body.get("winner", None)
    
    if not test_id:
        return JsonResponse({"error": "Missing test_id"}, status=400)
    
    result = ABTestManager.stop_test(test_id, winner)
    
    return JsonResponse(result)


@require_http_methods(["GET"])
def get_usage_metrics(request):
    """
    Get system usage metrics.
    
    GET /api/keywords/analytics/usage/?days=30
    """
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)
    
    # Total analyses
    total_analyses = ContentAnalysis.objects.filter(analyzed_at__gte=since).count()
    
    # By day
    daily_usage = []
    for i in range(days):
        day = timezone.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        count = ContentAnalysis.objects.filter(
            analyzed_at__gte=day_start,
            analyzed_at__lt=day_end
        ).count()
        
        daily_usage.append({
            "date": day_start.strftime('%Y-%m-%d'),
            "analyses": count,
        })
    
    # Keywords generated
    total_keywords = KeywordOpportunity.objects.filter(created_at__gte=since).count()
    
    # Task statistics
    task_stats = {
        "total": AnalysisTask.objects.filter(created_at__gte=since).count(),
        "completed": AnalysisTask.objects.filter(
            created_at__gte=since,
            status='completed'
        ).count(),
        "failed": AnalysisTask.objects.filter(
            created_at__gte=since,
            status='failed'
        ).count(),
    }
    
    return JsonResponse({
        "period_days": days,
        "total_analyses": total_analyses,
        "total_keywords_generated": total_keywords,
        "task_statistics": task_stats,
        "daily_breakdown": list(reversed(daily_usage)),
    })
