"""
seo_tool/urls.py  (UPDATED for continuous training)
"""

from django.urls import path
from keyword_suggestion.views import (
    KeywordSuggestionsView,
    TrainingStatusView,
    TriggerTrainingView,
)

app_name = "keyword_suggestion"

urlpatterns = [
    # ── Keyword suggestions (unchanged interface) ──────────────
    path("keyword-suggestions/",         KeywordSuggestionsView.as_view(),  name="suggestions"),

    # ── Training pipeline management ──────────────────────────
    path("keyword-suggestions/training-status/", TrainingStatusView.as_view(),   name="training-status"),
    path("keyword-suggestions/trigger-training/", TriggerTrainingView.as_view(), name="trigger-training"),
]