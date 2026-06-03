"""
Celery tasks for SEOAnalyzer app.

Heavy operations like website audits, link checking, and technical analysis
are moved to background tasks for better user experience.
"""
import logging
from celery import shared_task
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def perform_website_audit(self, user_id, url, audit_type='full'):
    """
    Perform comprehensive website audit in background.
    
    Args:
        user_id: ID of user requesting audit
        url: Website URL to audit
        audit_type: 'full', 'technical', 'content', or 'links'
    
    Returns:
        dict with audit results and status
    """
    try:
        from .models import AuditResult, WebsiteAnalysis
        from .services.link_checker import LinkChecker
        from .services.technical_audit import TechnicalAudit
        
        logger.info(f"Starting {audit_type} audit for {url} by user {user_id}")
        
        # Update status to processing
        audit = WebsiteAnalysis.objects.filter(
            user_id=user_id, 
            url=url
        ).latest('created_at')
        audit.status = 'processing'
        audit.save()
        
        results = {
            'url': url,
            'audit_type': audit_type,
            'status': 'completed',
            'findings': {}
        }
        
        # Run link check
        if audit_type in ['full', 'links']:
            link_checker = LinkChecker()
            results['findings']['links'] = link_checker.check_website_links(url)
        
        # Run technical audit
        if audit_type in ['full', 'technical']:
            tech_audit = TechnicalAudit()
            results['findings']['technical'] = tech_audit.analyze(url)
        
        # Save results
        audit.status = 'completed'
        audit.results = results
        audit.save()
        
        logger.info(f"Completed audit for {url}")
        return results
        
    except Exception as exc:
        logger.error(f"Audit failed for {url}: {exc}")
        # Mark as failed
        try:
            audit = WebsiteAnalysis.objects.filter(
                user_id=user_id, 
                url=url
            ).latest('created_at')
            audit.status = 'failed'
            audit.error_message = str(exc)
            audit.save()
        except Exception:
            pass
        
        # Retry on failure
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def check_broken_links_batch(self, user_id, urls):
    """
    Check multiple URLs for broken links in batch.
    
    Args:
        user_id: User requesting the check
        urls: List of URLs to check
    
    Returns:
        List of broken link results
    """
    from .services.link_checker import LinkChecker
    
    checker = LinkChecker()
    broken_links = []
    
    for url in urls:
        try:
            result = checker.check_url(url)
            if not result.get('is_valid'):
                broken_links.append({
                    'url': url,
                    'status': result.get('status_code'),
                    'error': result.get('error')
                })
        except Exception as e:
            logger.warning(f"Failed to check {url}: {e}")
            broken_links.append({
                'url': url,
                'error': str(e)
            })
    
    logger.info(f"Checked {len(urls)} URLs, found {len(broken_links)} broken")
    return broken_links


@shared_task
def cleanup_old_audit_results(days=30):
    """
    Clean up old audit results to save database space.
    
    Args:
        days: Delete audits older than this many days
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import AuditResult
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_audits = AuditResult.objects.filter(
        created_at__lt=cutoff_date,
        is_saved=False  # Only delete unsaved audits
    )
    
    count = old_audits.count()
    old_audits.delete()
    
    logger.info(f"Cleaned up {count} old audit results")
    return count


@shared_task
def generate_monthly_report(user_id, month=None, year=None):
    """
    Generate monthly SEO report for user.
    
    Args:
        user_id: User to generate report for
        month: Month number (1-12), defaults to previous month
        year: Year, defaults to current year
    
    Returns:
        Report data dict
    """
    from django.utils import timezone
    from datetime import datetime
    from .models import AuditResult
    from subscriptions.models import UsageTracker
    
    now = timezone.now()
    if month is None:
        month = now.month - 1 if now.month > 1 else 12
        year = now.year if now.month > 1 else now.year - 1
    if year is None:
        year = now.year
    
    # Get user's audits for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    audits = AuditResult.objects.filter(
        user_id=user_id,
        created_at__gte=start_date,
        created_at__lt=end_date
    )
    
    # Get usage stats
    usage, _ = UsageTracker.objects.get_or_create(user_id=user_id)
    
    report = {
        'user_id': user_id,
        'month': month,
        'year': year,
        'total_audits': audits.count(),
        'average_score': audits.filter(score__isnull=False).aggregate(
            avg_score=models.Avg('score')
        )['avg_score'],
        'usage_summary': {
            'audits_used': usage.audits_used_this_month,
            'keywords_analyzed': usage.keywords_analyzed_this_month,
        }
    }
    
    logger.info(f"Generated report for user {user_id}: {month}/{year}")
    return report
