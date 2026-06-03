# Generated manually for Phase 2: Database Optimization

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add database indexes for query performance optimization.
    Phase 2 of production readiness plan.
    """

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        # UsageTracker indexes - frequently queried by user
        migrations.AddIndex(
            model_name='usagetracker',
            index=models.Index(
                fields=['user', 'last_reset_date'],
                name='subscr_usage_user_reset_idx'
            ),
        ),
        
        # PaymentRecord indexes - payment history queries
        migrations.AddIndex(
            model_name='paymentrecord',
            index=models.Index(
                fields=['user', '-created_at'],
                name='subscr_payment_user_date_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='paymentrecord',
            index=models.Index(
                fields=['status', '-created_at'],
                name='subscr_payment_status_date_idx'
            ),
        ),
        
        # FeatureAccessLog indexes - analytics queries
        migrations.AddIndex(
            model_name='featureaccesslog',
            index=models.Index(
                fields=['user', 'feature_name', '-timestamp'],
                name='subscr_feaure_user_feat_time_idx'
            ),
        ),
        
        # Subscription indexes - status lookups
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['status', '-created_at'],
                name='subscr_sub_status_date_idx'
            ),
        ),
        
        # ManualPaymentSubmission indexes - admin queries
        migrations.AddIndex(
            model_name='manualpaymentsubmission',
            index=models.Index(
                fields=['status', '-created_at'],
                name='subscr_manual_status_date_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='manualpaymentsubmission',
            index=models.Index(
                fields=['user', '-created_at'],
                name='subscr_manual_user_date_idx'
            ),
        ),
    ]
