from django.urls import path
from . import views, analytics_views

urlpatterns = [
    # Original endpoints
    path("", views.keyword_suggestions, name="keyword_suggestions"),
    path("v2/", views.keyword_suggestions_v2, name="keyword_suggestions_v2"),
    path("streaming/", views.keyword_suggestions_streaming, name="keyword_suggestions_streaming"),
    path("feedback/", views.submit_feedback, name="submit_feedback"),
    path("opportunities/", views.get_opportunities, name="get_opportunities"),
    
    # Phase 4: Async Processing
    path("analyze-async/", views.analyze_url_async, name="analyze_url_async"),
    path("analyze-batch/", views.analyze_batch_async, name="analyze_batch_async"),
    path("task-status/", views.get_task_status, name="get_task_status"),
    path("tasks/", views.list_tasks, name="list_tasks"),
    
    # Phase 4: Export
    path("export/", views.export_results, name="export_results"),
    
    # Phase 5: Analytics Dashboard
    path("analytics/dashboard/", analytics_views.get_dashboard_summary, name="analytics_dashboard"),
    path("analytics/model-performance/", analytics_views.get_model_performance, name="model_performance"),
    path("analytics/feedback/", analytics_views.get_feedback_analytics, name="feedback_analytics"),
    path("analytics/ab-tests/", analytics_views.get_ab_test_results, name="ab_test_results"),
    path("analytics/retraining/", analytics_views.get_retraining_status, name="retraining_status"),
    path("analytics/usage/", analytics_views.get_usage_metrics, name="usage_metrics"),
    
    # Phase 5: Management Actions
    path("analytics/trigger-retrain/", analytics_views.trigger_retraining, name="trigger_retraining"),
    path("analytics/create-ab-test/", analytics_views.create_ab_test, name="create_ab_test"),
    path("analytics/stop-ab-test/", analytics_views.stop_ab_test, name="stop_ab_test"),
]