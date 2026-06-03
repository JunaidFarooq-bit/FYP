"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from SEOAnalyzer import views_pages as views
from SEOAnalyzer.views import health_check, readiness_check, liveness_check

urlpatterns = [
    # Health checks (must be before other paths for load balancer access)
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('live/', liveness_check, name='liveness_check'),
    
    path('admin/', admin.site.urls),
    path('home/',views.index,name="Home"),
    path('show/', views.show, name="show"),
    path('upload/',views.upload,name='upload'),
    path('report/',views.Report,name='report'),
    path('report/download/', views.download_report, name='download_report'),
    path('seo-metrics/', views.seo_metrics, name="seo_metrics"),
    path('mobiletest/',views.mobiletest,name="mobiletest"),
    path('robot/',views.robot,name="robot"),
    path('keyPosition/',views.keyPosition,name="keyPosition"),
    path('keysuggestion/',views.keysuggestion,name="keysuggestion"),
    path('keyword-ai-suggestions/', views.keyword_ai_suggestions, name="keyword_ai_suggestions"),
    path('', views.loginuser, name="login"),
    path('register/', views.register, name="register"),
    path('logout/', views.logoutuser, name="logout"),
    path('forget-password/', views.ForgetPassword, name="forget_password"),
    path('change-password/<token>/', views.ChangePassword, name="change_password"),
    path('sentimentanalysis/', views.sentiment_analysis_page, name='sentiment_analysis'),
    path('sentimentanalysis/analyze/', views.analyze_sentiment_view, name='analyze_sentiment'),
    path('comparative-analysis/', include('comparative_analysis.urls')),
    path("api/keywords/", include("keyword_ai.urls")),
    path('subscriptions/', include('subscriptions.urls')),  # Subscription management
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)