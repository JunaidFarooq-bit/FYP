"""
Celery tasks for asynchronous keyword analysis.
Phase 4: Batch processing and async task management.
"""

import uuid
from typing import List, Dict
from celery import shared_task
from django.utils import timezone

from .models import AnalysisTask
from .pipeline_v2 import run_keyword_pipeline_v2


@shared_task(bind=True, max_retries=3)
def analyze_single_url_task(self, task_id: str, url: str, parameters: dict):
    """
    Celery task to analyze a single URL.
    
    Args:
        task_id: The AnalysisTask ID
        url: URL to analyze
        parameters: Analysis parameters (page_topic, use_llm, etc.)
    """
    try:
        # Get task record
        task = AnalysisTask.objects.get(task_id=task_id)
        task.status = 'processing'
        task.started_at = timezone.now()
        task.current_step = 'Starting analysis...'
        task.save()
        
        # Run pipeline
        task.update_progress(10, 'Extracting content...')
        
        result = run_keyword_pipeline_v2(
            url=url,
            page_topic=parameters.get('page_topic', ''),
            use_llm=parameters.get('use_llm', True),
            use_advanced_ai=parameters.get('use_advanced_ai', True),
            analyze_competitors=parameters.get('analyze_competitors', False),
            generate_optimization=parameters.get('generate_optimization', False),
            target_audience=parameters.get('target_audience', ''),
            save_to_db=True,
        )
        
        task.update_progress(90, 'Saving results...')
        
        if 'error' in result:
            task.mark_failed(result['error'])
            return {'status': 'failed', 'error': result['error']}
        
        task.mark_completed(result)
        
        return {
            'status': 'completed',
            'task_id': task_id,
            'url': url,
            'keywords_found': len(result.get('relevant_keywords', [])),
        }
        
    except AnalysisTask.DoesNotExist:
        return {'status': 'failed', 'error': 'Task not found'}
    except Exception as exc:
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        
        try:
            task = AnalysisTask.objects.get(task_id=task_id)
            task.mark_failed(str(exc))
        except Exception:
            pass
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, max_retries=2)
def analyze_batch_urls_task(self, task_id: str, urls: List[str], parameters: dict):
    """
    Celery task to analyze multiple URLs in batch.
    
    Args:
        task_id: The AnalysisTask ID
        urls: List of URLs to analyze
        parameters: Analysis parameters
    """
    try:
        task = AnalysisTask.objects.get(task_id=task_id)
        task.status = 'processing'
        task.started_at = timezone.now()
        task.total_urls = len(urls)
        task.save()
        
        results = []
        processed = 0
        failed = 0
        
        for i, url in enumerate(urls):
            progress = int((i / len(urls)) * 80)  # 0-80% for processing
            task.update_progress(progress, f'Analyzing URL {i+1} of {len(urls)}: {url[:50]}...')
            
            try:
                result = run_keyword_pipeline_v2(
                    url=url,
                    page_topic=parameters.get('page_topic', ''),
                    use_llm=parameters.get('use_llm', True),
                    use_advanced_ai=parameters.get('use_advanced_ai', True),
                    analyze_competitors=False,  # Skip for batch to save time
                    save_to_db=True,
                )
                
                if 'error' not in result:
                    results.append({
                        'url': url,
                        'status': 'success',
                        'keywords': result.get('relevant_keywords', []),
                        'focus_keywords': result.get('focus_keywords', []),
                        'quality_score': result.get('content_analysis', {}).get('quality_score', 0),
                    })
                    processed += 1
                else:
                    results.append({
                        'url': url,
                        'status': 'failed',
                        'error': result['error'],
                    })
                    failed += 1
                    
            except Exception as e:
                results.append({
                    'url': url,
                    'status': 'failed',
                    'error': str(e),
                })
                failed += 1
            
            # Update progress
            task.processed_urls = processed
            task.failed_urls = failed
            task.save()
        
        task.update_progress(90, 'Compiling results...')
        
        # Compile aggregate results
        aggregate = {
            'total_urls': len(urls),
            'successful': processed,
            'failed': failed,
            'all_keywords': [],
            'url_results': results,
        }
        
        # Collect all unique keywords
        all_keywords = set()
        for r in results:
            if r['status'] == 'success':
                all_keywords.update(r.get('keywords', []))
        aggregate['all_keywords'] = sorted(list(all_keywords))
        
        task.mark_completed(aggregate)
        
        return {
            'status': 'completed',
            'task_id': task_id,
            'total_processed': processed,
            'total_failed': failed,
        }
        
    except AnalysisTask.DoesNotExist:
        return {'status': 'failed', 'error': 'Task not found'}
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        
        try:
            task = AnalysisTask.objects.get(task_id=task_id)
            task.mark_failed(str(exc))
        except Exception:
            pass
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task
def cleanup_old_tasks():
    """
    Periodic task to clean up old completed/failed tasks.
    Keeps only last 30 days of tasks.
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_tasks = AnalysisTask.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed', 'cancelled']
    )
    
    count = old_tasks.count()
    old_tasks.delete()
    
    return f'Deleted {count} old tasks'


def create_analysis_task(
    task_type: str,
    parameters: dict,
    urls: List[str] = None,
    session_id: str = ""
) -> AnalysisTask:
    """
    Helper function to create an analysis task.
    
    Args:
        task_type: Type of task (single_url, batch_urls, etc.)
        parameters: Analysis parameters
        urls: List of URLs (for batch tasks)
        session_id: User session ID for tracking
        
    Returns:
        Created AnalysisTask instance
    """
    task = AnalysisTask.objects.create(
        task_id=str(uuid.uuid4()),
        task_type=task_type,
        parameters=parameters,
        total_urls=len(urls) if urls else 1,
        session_id=session_id,
    )
    
    return task


def start_single_url_analysis(url: str, parameters: dict, session_id: str = "") -> str:
    """
    Start async analysis of a single URL.
    
    Returns:
        Task ID
    """
    task = create_analysis_task('single_url', parameters, [url], session_id)
    
    # Queue the Celery task
    analyze_single_url_task.delay(task.task_id, url, parameters)
    
    return task.task_id


def start_batch_analysis(urls: List[str], parameters: dict, session_id: str = "") -> str:
    """
    Start async batch analysis of multiple URLs.
    
    Returns:
        Task ID
    """
    task = create_analysis_task('batch_urls', parameters, urls, session_id)
    
    # Queue the Celery task
    analyze_batch_urls_task.delay(task.task_id, urls, parameters)
    
    return task.task_id
