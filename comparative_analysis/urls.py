from django.urls import path
from . import views

app_name = 'comparative_analysis'

urlpatterns = [
    path('', views.input_form, name='input_form'),
    path('analyze/', views.analyze_comparison, name='analyze'),
    path('results/<int:report_id>/', views.view_results, name='results'),
]