"""
================================================================================
Keyword AI API Views
================================================================================

This file handles all API endpoints for the keyword analysis system:
- Keyword suggestions (basic and AI-enhanced)
- User feedback collection
- Async batch processing
- Results export (CSV/JSON)

Each view function follows this pattern:
1. Extract data from request (GET params or JSON body)
2. Validate required inputs
3. Call the appropriate service/pipeline
4. Return JSON response (or CSV for exports)

================================================================================
"""

# Standard library imports
import json      # For parsing request bodies
import csv       # For CSV exports
import io        # For in-memory file handling
import logging   # For error logging
from typing import Dict, Any, Optional  # Type hints for clarity

# Third-party imports
import validators  # For URL validation

# Django imports
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
# from django.views.decorators.csrf import csrf_exempt  # Removed for security
from django.utils import timezone

# Local imports - our keyword AI modules
from keyword_ai.pipeline import run_keyword_pipeline
from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2, get_historical_analysis
from keyword_ai.models import KeywordOpportunity, SuggestionFeedback, AnalysisTask
from keyword_ai.tasks import start_single_url_analysis, start_batch_analysis
from keyword_ai.services.traffic_enrichment import enrich_with_traffic_signals
from subscriptions.decorators import api_subscription_check
from subscriptions.ratelimit import rate_limit_api, rate_limit_ai


# =============================================================================
# CONSTANTS - Configuration values used across the file
# =============================================================================

# Valid actions for user feedback
VALID_FEEDBACK_ACTIONS = {"accepted", "rejected", "implemented", "ignored"}

# Maximum URLs allowed in a single batch analysis (prevents overloading)
MAX_BATCH_SIZE = 50

# Default and max limits for listing tasks
DEFAULT_TASK_LIMIT = 10
MAX_TASK_LIMIT = 50

# CSV export column headers
CSV_EXPORT_HEADERS = [
    "Keyword",           # The suggested keyword
    "Type",              # Keyword type/category
    "Relevance Score",   # How relevant (0-100)
    "Priority",          # high/medium/low
    "Search Intent",     # informational/transactional/etc
    "AI Reasoning",      # Why this keyword was suggested
    "Suggested Action",  # What to do with it
]


# =============================================================================
# HELPER FUNCTIONS - Reusable utilities used by multiple views
# =============================================================================

def parse_json_body(request) -> tuple[bool, Optional[Dict]]:
    """
    Safely parse JSON from request body.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        Tuple of (success: bool, data: dict or None)
        - success=True: data contains the parsed JSON
        - success=False: data is None, JSON was invalid
    """
    try:
        return True, json.loads(request.body)
    except json.JSONDecodeError:
        return False, None


def parse_boolean_param(value: Any, default: bool = True) -> bool:
    """
    Convert various input types to boolean.
    
    Handles:
        - True/False (bool) -> returns as-is
        - "true", "1", "yes" (str) -> True
        - "false", "0", "no" (str) -> False
        - None or missing -> returns default
    
    Args:
        value: The value to convert
        default: Fallback if value is None/empty
        
    Returns:
        Boolean representation of the value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return default


def get_request_data(request) -> Dict:
    """
    Get request data regardless of HTTP method.
    
    For POST: parses JSON body
    For GET: returns query parameters as dict
    
    Args:
        request: Django HTTP request
        
    Returns:
        Dictionary with request data, or {"_error": message} if JSON invalid
    """
    if request.method == "POST":
        success, data = parse_json_body(request)
        if not success:
            return {"_error": "Invalid JSON body"}
        return data
    # For GET requests, convert QueryDict to regular dict
    return dict(request.GET)


def error_response(message: str, status: int = 400) -> JsonResponse:
    """
    Create a standardized error JSON response.
    
    Args:
        message: Error message to display to user
        status: HTTP status code (default 400 = Bad Request)
        
    Returns:
        Django JsonResponse with error format
    """
    return JsonResponse({"error": message}, status=status)


def parse_analysis_params(data: Dict) -> Dict:
    """
    Extract common analysis parameters from request data.
    
    This ensures all boolean flags are properly converted and
    default values are applied consistently.
    
    Args:
        data: Dictionary from request (GET params or JSON body)
        
    Returns:
        Dictionary with normalized parameters for pipeline functions
    """
    return {
        "page_topic": data.get("page_topic", ""),
        "use_llm": parse_boolean_param(data.get("use_llm"), True),
        "use_advanced_ai": parse_boolean_param(data.get("use_advanced_ai"), True),
        "analyze_competitors": parse_boolean_param(data.get("analyze_competitors"), False),
        "generate_optimization": parse_boolean_param(data.get("generate_optimization"), False),
        "target_audience": data.get("target_audience", ""),
        # NEW v2.2: Geographic region for GEO/AEO scoring + LLM prompts
        "target_region": (data.get("target_region") or "GLOBAL").upper(),
    }


# =============================================================================
# SERIALIZATION HELPERS - Convert model objects to API-friendly dictionaries
# =============================================================================

def serialize_opportunity(opp: KeywordOpportunity) -> Dict:
    """
    Convert a KeywordOpportunity model instance to a dictionary.
    
    This is used when returning opportunities in API responses.
    
    Args:
        opp: KeywordOpportunity database object
        
    Returns:
        Dictionary with opportunity details
    """
    return {
        "id": opp.id,
        "keyword": opp.keyword,
        "type": opp.keyword_type,
        "relevance_score": opp.relevance_score,
        "search_intent": opp.search_intent,
        "priority": opp.priority,
        "ai_reasoning": opp.ai_reasoning,
        "suggested_action": opp.suggested_action,
    }


def serialize_task(task: AnalysisTask, include_result: bool = False) -> Dict:
    """
    Convert an AnalysisTask model instance to a dictionary.
    
    Args:
        task: AnalysisTask database object
        include_result: Whether to include the full result data (for completed tasks)
        
    Returns:
        Dictionary with task status and details
    """
    data = {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status,
        "progress_percent": task.progress_percent,
        "current_step": task.current_step,
        "total_urls": task.total_urls,
        "processed_urls": task.processed_urls,
        "failed_urls": task.failed_urls,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "duration_seconds": task.duration_seconds,
    }
    
    # Only include result data for completed tasks when explicitly requested
    # (result data can be large, so we don't include it in list views)
    if include_result and task.status == 'completed' and task.result_data:
        data["result"] = task.result_data
    
    # Include error message if task failed
    if task.status == 'failed':
        data["error"] = task.error_message
    
    return data


# =============================================================================
# API ENDPOINTS - Main view functions that handle HTTP requests
# =============================================================================


# -----------------------------------------------------------------------------
# KEYWORD SUGGESTIONS
# -----------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
@api_subscription_check
def keyword_suggestions(request):
    """
    Basic keyword suggestions endpoint (v1).
    
    This is the simplest endpoint - give it a URL or text, get back keywords.
    Uses the basic pipeline without advanced AI features.
    
    URL: /api/keywords/
    Methods: GET, POST
    
    GET Params:
        url: Website URL to analyze
        text: Raw text content (alternative to URL)
        page_topic: Optional hint about page content
        use_llm: Whether to use LLM enhancement (default: true)
    
    POST Body (JSON):
        Same as GET params, but in JSON format
    
    Returns:
        {
            "keywords": ["word1", "word2", ...],
            "suggestions": [...],
            ...
        }
    """
    # Step 1: Get data from request (handles both GET and POST)
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])

    # Step 2: Extract and validate inputs
    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    
    # Input validation
    if url and not validators.url(url):
        return error_response("Invalid URL format provided.")
    
    if text and len(text) > 50000:  # 50KB limit
        return error_response("Text content too large. Maximum 50,000 characters allowed.")
    
    # Must provide either URL or text
    if not url and not text:
        return error_response("Provide 'url' or 'text' in the request body.")

    # Step 3: Run the keyword pipeline
    result = run_keyword_pipeline(
        url=url or None,  # Convert empty string to None
        text=text or None,
        page_topic=data.get("page_topic", ""),
        use_llm=parse_boolean_param(data.get("use_llm"), True),
    )

    # Step 4: Return response
    if "error" in result:
        return JsonResponse(result, status=500)
    return JsonResponse(result)


@require_http_methods(["GET", "POST"])
@api_subscription_check
@rate_limit_ai(requests_per_minute=10)  # AI endpoints are expensive
def keyword_suggestions_v2(request):
    """
    Enhanced keyword suggestions endpoint (v2) with AI features.
    
    This endpoint uses the advanced pipeline with:
    - Content quality analysis
    - ML-generated keyword suggestions
    - Search intent classification
    - SERP feature predictions
    - Competitor analysis (optional)
    - Content optimization suggestions (optional)
    
    URL: /api/keywords/v2/
    Methods: GET, POST
    
    GET/POST Params:
        url: Website URL to analyze
        text: Raw text content (alternative to URL)
        page_topic: Optional hint about page content
        use_llm: Use LLM enhancement (default: true)
        use_advanced_ai: Use ML/AI features (default: true)
        analyze_competitors: Include competitor analysis (default: false)
        generate_optimization: Get content optimization tips (default: false)
        target_audience: Who is the content for (e.g., "beginners")
        target_region: Target geographic region (NA, EU, APAC, LATAM, MEA, GLOBAL)
            - Drives GEO/AEO scoring + LLM expansion prompt regionalization

    Returns:
        Enhanced results with AI analysis, intent data, and:
        - geo_aeo_analysis: Per-keyword GEO scope + AEO friendliness scores
        - traffic_potential_forecast: CTR + traffic forecasts at ranks 1/3/5/10
        - scored_keywords: Each keyword now carries geo_data, aeo_signals,
          estimated_ctr, traffic_potential, sge_impact, and risk_flags.
    """
    # Step 1: Get data from request
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])

    # Step 2: Validate inputs
    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    
    # Input validation
    if url and not validators.url(url):
        return error_response("Invalid URL format provided.")
    
    if text and len(text) > 50000:  # 50KB limit
        return error_response("Text content too large. Maximum 50,000 characters allowed.")
    
    if not url and not text:
        return error_response("Provide 'url' or 'text' in the request body.")

    # Step 3: Parse all analysis parameters
    params = parse_analysis_params(data)
    
    # Step 4: Run the enhanced v2 pipeline
    result = run_keyword_pipeline_v2(
        url=url or None,
        text=text or None,
        save_to_db=True,  # Save results for later retrieval
        **params
    )

    # Step 5: Return response
    if "error" in result:
        return JsonResponse(result, status=500)
    return JsonResponse(result)


# -----------------------------------------------------------------------------
# FEEDBACK & OPPORTUNITIES
# -----------------------------------------------------------------------------

@require_http_methods(["POST"])
@api_subscription_check
def submit_feedback(request):
    """
    Submit user feedback on a keyword suggestion.
    
    This allows users to accept, reject, or mark suggestions as implemented.
    Feedback is stored and used to improve future suggestions.
    
    URL: /api/keywords/feedback/
    Method: POST
    
    POST Body:
        opportunity_id: ID of the keyword opportunity (number)
        action: One of: "accepted", "rejected", "implemented", "ignored"
        comment: Optional user comment (string)
        rating: Optional rating 1-5 (number)
    
    Returns:
        { "success": true, "feedback_id": 123, "message": "..." }
    """
    # Step 1: Parse request body
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])
    
    # Step 2: Validate required fields
    opportunity_id = data.get("opportunity_id")
    action = data.get("action")
    
    if not opportunity_id or not action:
        return error_response("Missing opportunity_id or action")
    
    # Step 3: Validate action is allowed
    if action not in VALID_FEEDBACK_ACTIONS:
        return error_response(f"Invalid action. Must be one of: {', '.join(VALID_FEEDBACK_ACTIONS)}")
    
    # Step 4: Update database
    try:
        # Find the opportunity
        opportunity = KeywordOpportunity.objects.get(id=opportunity_id)
        
        # Update status based on action
        opportunity.is_accepted = action in ("accepted", "implemented")
        opportunity.is_rejected = (action == "rejected")
        opportunity.save()
        
        # Create a feedback record for analytics
        feedback = SuggestionFeedback.objects.create(
            opportunity=opportunity,
            user_action=action,
            user_comment=data.get("comment", ""),
            rating=data.get("rating"),
        )

        retraining = {"triggered": False}
        if action in ("accepted", "implemented", "rejected"):
            try:
                from .retraining_pipeline import RetrainingPipeline
                retraining = RetrainingPipeline.maybe_retrain_relevance_scorer()
            except Exception as retrain_error:
                logger.warning("Feedback retraining check failed: %s", retrain_error)
                retraining = {"triggered": False, "error": str(retrain_error)}
        
        return JsonResponse({
            "success": True,
            "feedback_id": feedback.id,
            "message": f"Feedback recorded: {action}",
            "retraining": retraining
        })
        
    except KeywordOpportunity.DoesNotExist:
        return error_response("Opportunity not found", 404)
    except Exception as e:
        return error_response(str(e), 500)


@require_http_methods(["GET"])
def get_opportunities(request):
    """
    Get keyword opportunities for a previously analyzed URL.
    
    Retrieves saved keyword suggestions from a past analysis.
    Excludes rejected opportunities.
    
    URL: /api/keywords/opportunities/
    Method: GET
    
    Query Params:
        url: The URL that was previously analyzed (required)
    
    Returns:
        {
            "url": "https://...",
            "analyzed_at": "2024-01-15T10:30:00",
            "quality_score": 85,
            "opportunities_count": 25,
            "opportunities": [ {...}, {...} ]
        }
    """
    # Step 1: Get URL from query params
    url = request.GET.get("url", "").strip()
    
    if not url:
        return error_response("Provide 'url' parameter")
    
    # Step 2: Look up the historical analysis
    analysis = get_historical_analysis(url)
    if not analysis:
        return JsonResponse({
            "error": "No analysis found for this URL. Run analysis first.",
            "url": url
        }, status=404)
    
    # Step 3: Get opportunities for this analysis
    # - Exclude rejected ones
    # - Order by relevance (highest first)
    # - Limit to 50 results
    opportunities = KeywordOpportunity.objects.filter(
        content_analysis=analysis,
    ).exclude(
        is_rejected=True
    ).order_by("-relevance_score")[:50]
    
    # Step 4: Build response
    return JsonResponse({
        "url": url,
        "analyzed_at": analysis.analyzed_at.isoformat(),
        "quality_score": analysis.quality_score,
        "opportunities_count": opportunities.count(),
        "opportunities": [serialize_opportunity(opp) for opp in opportunities]
    })


# -----------------------------------------------------------------------------
# ASYNC ANALYSIS (For long-running operations)
# -----------------------------------------------------------------------------

@require_http_methods(["POST"])
@api_subscription_check
@rate_limit_api(requests_per_minute=20)  # Async analysis rate limit
def analyze_url_async(request):
    """
    Start async analysis of a single URL.
    
    Use this when analysis might take a long time (large pages, many keywords).
    Returns immediately with a task_id that you can poll for status.
    
    URL: /api/keywords/analyze-async/
    Method: POST
    
    POST Body:
        url: Website URL to analyze (required)
        All other params same as keyword_suggestions_v2
    
    Returns immediately:
        { "task_id": "uuid", "status": "pending", "message": "..." }
    
    Check progress with: GET /api/keywords/task-status/?task_id=uuid
    """
    # Step 1: Parse request
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])
    
    # Step 2: Validate URL
    url = data.get("url", "").strip()
    if not url:
        return error_response("Provide 'url' in request body.")
    
    # Step 3: Start background task
    params = parse_analysis_params(data)
    session_id = request.session.session_key or ""  # For grouping user's tasks
    task_id = start_single_url_analysis(url, params, session_id)
    
    # Step 4: Return task info immediately (don't wait for completion)
    return JsonResponse({
        "task_id": task_id,
        "status": "pending",
        "message": "Analysis started. Check progress via /api/keywords/task-status/?task_id=..."
    })


@require_http_methods(["POST"])
@api_subscription_check
@rate_limit_api(requests_per_minute=5)  # Batch is expensive, strict limit
def analyze_batch_async(request):
    """
    Start async batch analysis of multiple URLs.
    
    Analyze many URLs at once in the background.
    
    URL: /api/keywords/analyze-batch/
    Method: POST
    
    POST Body:
        urls: Array of URLs to analyze (required, max 50)
        page_topic: Optional hint for all URLs
        use_llm: Whether to use LLM (default: true)
    
    Returns:
        { "task_id": "uuid", "status": "pending", "total_urls": 5 }
    """
    # Step 1: Parse request
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])
    
    # Step 2: Validate URLs array
    urls = data.get("urls", [])
    if not urls or not isinstance(urls, list):
        return error_response("Provide 'urls' array in request body.")
    
    # Step 3: Check batch size limit
    if len(urls) > MAX_BATCH_SIZE:
        return error_response(f"Maximum {MAX_BATCH_SIZE} URLs per batch.")
    
    # Step 4: Start batch task
    params = {
        "page_topic": data.get("page_topic", ""),
        "use_llm": parse_boolean_param(data.get("use_llm"), True),
        "use_advanced_ai": parse_boolean_param(data.get("use_advanced_ai"), True),
    }
    session_id = request.session.session_key or ""
    task_id = start_batch_analysis(urls, params, session_id)
    
    return JsonResponse({
        "task_id": task_id,
        "status": "pending",
        "total_urls": len(urls),
        "message": "Batch analysis started. Check progress via /api/keywords/task-status/?task_id=..."
    })


@require_http_methods(["GET"])
def get_task_status(request):
    """
    Check the status of an async analysis task.
    
    Poll this endpoint to track progress of async analyses.
    
    URL: /api/keywords/task-status/
    Method: GET
    
    Query Params:
        task_id: The task ID returned from analyze_url_async (required)
    
    Returns:
        {
            "task_id": "uuid",
            "status": "processing",  // pending/processing/completed/failed
            "progress_percent": 45,
            "current_step": "Analyzing URL 2 of 5...",
            "result": {...}  // Only included when completed
        }
    """
    # Step 1: Get task ID
    task_id = request.GET.get("task_id", "").strip()
    if not task_id:
        return error_response("Provide 'task_id' parameter.")
    
    # Step 2: Look up task in database
    try:
        task = AnalysisTask.objects.get(task_id=task_id)
        # Return full task info including result if completed
        return JsonResponse(serialize_task(task, include_result=True))
    except AnalysisTask.DoesNotExist:
        return error_response("Task not found.", 404)


@require_http_methods(["GET"])
def list_tasks(request):
    """
    List recent analysis tasks for the current user session.
    
    URL: /api/keywords/tasks/
    Method: GET
    
    Query Params:
        limit: Number of tasks to return (default: 10, max: 50)
    
    Returns:
        { "tasks": [ {...}, {...} ] }
    """
    # Step 1: Parse limit parameter
    limit = min(int(request.GET.get("limit", DEFAULT_TASK_LIMIT)), MAX_TASK_LIMIT)
    
    # Step 2: Get session ID to filter tasks
    session_id = request.session.session_key or ""
    
    # Step 3: Fetch tasks from database
    tasks = AnalysisTask.objects.filter(
        session_id=session_id
    ).order_by('-created_at')[:limit]  # Most recent first
    
    # Step 4: Return serialized tasks
    return JsonResponse({
        "tasks": [serialize_task(t) for t in tasks]
    })


# -----------------------------------------------------------------------------
# EXPORT
# -----------------------------------------------------------------------------

def generate_csv_response(opportunities, analysis_id: int) -> HttpResponse:
    """
    Create a CSV file download response from keyword opportunities.
    
    Args:
        opportunities: QuerySet of KeywordOpportunity objects
        analysis_id: ID of the analysis (used for filename)
        
    Returns:
        Django HttpResponse with CSV content
    """
    # Create CSV in memory (don't save to disk)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow(CSV_EXPORT_HEADERS)
    
    # Write data rows
    for opp in opportunities:
        writer.writerow([
            opp.keyword,
            opp.keyword_type,
            opp.relevance_score,
            opp.priority,
            opp.search_intent or "",  # Handle null values
            opp.ai_reasoning or "",
            opp.suggested_action or "",
        ])
    
    # Create HTTP response with CSV content
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="keywords_{analysis_id}.csv"'
    return response


@require_http_methods(["POST"])
@api_subscription_check
def export_results(request):
    """
    Export keyword analysis results as CSV or JSON.
    
    URL: /api/keywords/export/
    Method: POST
    
    POST Body:
        url: The analyzed URL (required)
        format: "csv" or "json" (default: "json")
    
    Returns:
        - CSV file download if format=csv
        - JSON response if format=json
    """
    # Step 1: Parse request
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])
    
    # Step 2: Validate URL
    url = data.get("url", "").strip()
    if not url:
        return error_response("Provide 'url' in request body.")
    
    # Step 3: Find the analysis
    analysis = get_historical_analysis(url)
    if not analysis:
        return error_response("No analysis found for this URL.", 404)
    
    # Step 4: Get opportunities
    opportunities = KeywordOpportunity.objects.filter(
        content_analysis=analysis,
    ).exclude(
        is_rejected=True
    ).order_by("-relevance_score")
    
    # Step 5: Return in requested format
    export_format = data.get("format", "json").lower()
    
    if export_format == "csv":
        # Return CSV file download
        return generate_csv_response(opportunities, analysis.id)
    
    # Default: Return JSON
    return JsonResponse({
        "url": url,
        "exported_at": timezone.now().isoformat(),
        "keywords_count": opportunities.count(),
        "keywords": [serialize_opportunity(opp) for opp in opportunities]
    })


# -----------------------------------------------------------------------------
# TRAFFIC ENRICHMENT ANALYSIS
# -----------------------------------------------------------------------------

@require_http_methods(["POST"])
@api_subscription_check
def analyze_traffic_signals(request):
    """
    Analyze real-time traffic signals for a list of keywords.

    Enriches keywords with trending data, volume estimates, difficulty scores,
    and strategic recommendations based on the traffic signal framework.

    URL: /api/keywords/traffic-analysis/
    Method: POST

    POST Body:
        keywords: List of keywords to analyze (required, max 50)
        page_topic: Optional page topic for context
        target_audience: Optional target audience description
        use_google_trends: Whether to fetch real Google Trends data (default: true)

    Returns:
        {
            "trending_alerts": [...],
            "traffic_prioritized_keywords": [...],
            "quick_win_keywords": [...],
            "avoid_keywords": [...],
            "topic_cluster": {...},
            "enrichment_metadata": {...}
        }
    """
    # Step 1: Parse request
    data = get_request_data(request)
    if "_error" in data:
        return error_response(data["_error"])

    # Step 2: Validate keywords
    keywords = data.get("keywords", [])
    if not keywords or not isinstance(keywords, list):
        return error_response("Provide 'keywords' array in request body")

    if len(keywords) > 50:
        return error_response("Maximum 50 keywords per request")

    # Step 3: Get optional parameters
    page_topic = data.get("page_topic", "")
    target_audience = data.get("target_audience", "")
    use_google_trends = parse_boolean_param(data.get("use_google_trends"), True)

    # Step 4: Run traffic enrichment
    try:
        result = enrich_with_traffic_signals(
            keywords=keywords,
            page_topic=page_topic,
            target_audience=target_audience,
            use_google_trends=use_google_trends
        )
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Traffic analysis failed: {e}")
        return error_response(f"Traffic analysis failed: {str(e)}", 500)


# =============================================================================
# STREAMING RESPONSES - Real-time keyword suggestions (NEW)
# =============================================================================

from django.http import StreamingHttpResponse
from keyword_ai.services.llm_refiner import get_client, get_model


def stream_llm_response(prompt: str):
    """
    Generator function for streaming LLM responses.
    
    Yields chunks of the LLM response as they arrive.
    """
    client = get_client()
    if client is None:
        yield json.dumps({"error": "LLM client not configured"})
        return
    
    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
            stream=True,  # Enable streaming
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield json.dumps({"chunk": content}) + "\n"
        
        yield json.dumps({"done": True})
        
    except Exception as e:
        yield json.dumps({"error": str(e)})


@require_http_methods(["POST"])
@api_subscription_check
def keyword_suggestions_streaming(request):
    """
    Real-time streaming keyword suggestions.
    
    Returns a Server-Sent Events (SSE) stream of keyword suggestions
    as they are generated by the LLM. Useful for real-time UI updates.
    
    URL: /api/keywords/streaming/
    Method: POST
    
    POST Body:
        keywords: List of keywords to refine (required)
        page_topic: Optional topic context
        context: Optional RAG context from similar content
    
    Returns: 
        Streaming response with JSON chunks:
        {"chunk": "keyword group..."}
        {"chunk": " intent..."}
        {"done": true}
    """
    # Parse request
    success, data = parse_json_body(request)
    if not success:
        return error_response("Invalid JSON body")
    
    keywords = data.get("keywords", [])
    if not keywords:
        return error_response("Provide 'keywords' array in request body")
    
    page_topic = data.get("page_topic", "")
    rag_context = data.get("context", "")
    
    # Build prompt (similar to llm_refiner but for streaming)
    keyword_list = "\n".join(f"- {kw}" for kw in keywords[:30])
    topic_hint = f" The page is about: {page_topic}." if page_topic else ""
    context_section = f"\n\n{rag_context}\n\n" if rag_context else ""
    
    prompt = f"""You are an SEO expert.{topic_hint}{context_section}
Analyze these keywords and provide suggestions:

Keywords:
{keyword_list}

Provide a concise analysis of:
1. Top 5 focus keywords to target
2. Search intent distribution
3. Content optimization tips

Keep your response brief and actionable."""
    
    # Return streaming response
    response = StreamingHttpResponse(
        stream_llm_response(prompt),
        content_type='application/x-ndjson'  # Newline-delimited JSON
    )
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response
