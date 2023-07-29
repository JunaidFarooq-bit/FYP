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
from django.urls import path
from SEOAnalyzer import views

app_name='SEOAnalyzer'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home',views.index,name="Home"),
    path('show', views.show, name="show"),
    path('upload/',views.upload,name='upload'),
    path('report/',views.Report,name='report'),
    path('backlink',views.backlink,name="backlink"),
    path('DomainAuthority',views.DomainAuthority,name="DomainAuthority"),
    path('pageAuthority',views.pageAuthority,name="pageAuthority"),
    path('mobiletest',views.mobiletest,name="mobiletest"),
    path('robot',views.robot,name="robot"),
    path('keyPosition',views.keyPosition,name="keyPosition"),
    path('keysuggestion',views.keysuggestion,name="keysuggestion"),
    path('', views.loginuser, name="login"),
    path('register/', views.register, name="register"),
    path('logout/', views.logoutuser, name="logout"),
    path('forget-password/', views.ForgetPassword, name="forget_password"),
    path('change-password/<token>/', views.ChangePassword, name="change_password"),
]