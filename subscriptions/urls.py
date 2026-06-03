from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Pricing and plans
    path('pricing/', views.pricing, name='pricing'),
    
    # Payment flow (manual bank transfer)
    path('payment/instructions/', views.payment_instructions, name='payment_instructions'),
    path('payment/submit/', views.submit_payment_proof, name='submit_payment_proof'),
    
    # User dashboard
    path('dashboard/', views.subscription_dashboard, name='dashboard'),
    
    # Subscription management
    path('cancel/', views.cancel_subscription, name='cancel'),
    path('change-plan/', views.change_plan, name='change_plan'),
    
    # API
    path('api/usage/', views.usage_api, name='usage_api'),
    path('api/clear-upgrade-flag/', views.clear_upgrade_flag, name='clear_upgrade_flag'),
    
    # Admin payment verification (staff only)
    path('admin/pending-payments/', views.pending_payments_admin, name='pending_payments_admin'),
    path('admin/verify-payment/<int:payment_id>/', views.verify_payment_admin, name='verify_payment_admin'),
    path('admin/reject-payment/<int:payment_id>/', views.reject_payment_admin, name='reject_payment_admin'),
]
