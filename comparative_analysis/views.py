from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
import time
import logging
import json as json_lib

from .models import ComparisonReport
from .services.comparison_orchestrator import ComparisonOrchestrator
from .utils.validators import validate_url

logger = logging.getLogger(__name__)


# ============================================================
# FALLBACK DATA STRUCTURES
# ============================================================

def _empty_technical():
    return {
        'technical_score': 0,
        'page_speed': {'load_time': 0, 'speed_score': 0},
        'core_web_vitals': {},
        'mobile_responsive': False,
        'https_enabled': False,
        'canonical': {'present': False, 'url': ''},
        'indexability': {'is_indexable': True, 'is_crawlable': True, 'robots_directive': ''},
        'structured_data': {'present': False, 'count': 0, 'schema_types': []},
        'url_structure': {'score': 0, 'length': 0, 'depth': 0, 'issues': []},
        'image_optimization': {'score': 0, 'total_images': 0, 'images_with_alt': 0},
        'internal_links': 0,
    }


def _empty_authority():
    return {
        'authority_score': 0,
        'domain_authority': None,
        'page_authority': None,
        'spam_score': None,
        'backlink_profile': {
            'referring_domains': 'N/A',
            'total_backlinks': 'N/A',
            'data_source': 'Data unavailable',
        },
    }


def _empty_eeat():
    return {
        'has_author': False,
        'has_date': False,
        'has_citations': False,
        'https_enabled': False,
        'score': 0,
        'experience_score': 0,
        'expertise_score': 0,
        'authoritativeness_score': 0,
        'trustworthiness_score': 0,
        'ai_signals': [],
        'ai_recommendations': [],
    }


# ============================================================
# DATA EXTRACTORS — try multiple key names from orchestrator
# ============================================================

def _get_technical(data_dict):
    return (
        data_dict.get('technical') or
        data_dict.get('technical_analysis') or
        data_dict.get('tech') or
        data_dict.get('technical_seo') or
        _empty_technical()
    )


def _get_authority(data_dict):
    return (
        data_dict.get('authority') or
        data_dict.get('authority_analysis') or
        data_dict.get('backlinks') or
        data_dict.get('link_analysis') or
        _empty_authority()
    )


# ============================================================
# EXPLANATION PARSER
# ============================================================

def _parse_ranking_explanation(raw):
    """
    Parse ranking_explanation:
    - Valid JSON string        -> (dict, True)
    - JSON in ```json fences   -> strip then parse -> (dict, True)
    - Plain text / markdown    -> (str, False)
    """
    if not raw:
        return ('No explanation available.', False)

    stripped = raw.strip()
    if stripped.startswith('```'):
        stripped = stripped.split('\n', 1)[-1]
        if stripped.endswith('```'):
            stripped = stripped.rsplit('```', 1)[0]
        stripped = stripped.strip()

    try:
        data = json_lib.loads(stripped)
        if isinstance(data, dict) and ('opening' in data or 'reasons' in data or 'recommendations' in data):
            logger.info("[EXPLANATION] Parsed as JSON successfully")
            return (data, True)
        else:
            logger.warning("[EXPLANATION] JSON parsed but unexpected structure")
            return (raw, False)
    except (json_lib.JSONDecodeError, ValueError):
        logger.info("[EXPLANATION] Not JSON, treating as plain text")
        return (raw, False)


# ============================================================
# VIEWS
# ============================================================

@require_http_methods(["GET"])
def input_form(request):
    return render(request, 'comparative_analysis/input_form.html')


@require_http_methods(["POST"])
def analyze_comparison(request):
    url_primary = request.POST.get('url_primary', '').strip()
    url_competitor = request.POST.get('url_competitor', '').strip()
    target_keyword = request.POST.get('target_keyword', '').strip()

    if not url_primary or not url_competitor:
        messages.error(request, "Both URLs are required.")
        return redirect('comparative_analysis:input_form')

    if not validate_url(url_primary):
        messages.error(request, f"Invalid primary URL: {url_primary}")
        return redirect('comparative_analysis:input_form')

    if not validate_url(url_competitor):
        messages.error(request, f"Invalid competitor URL: {url_competitor}")
        return redirect('comparative_analysis:input_form')

    try:
        start_time = time.time()

        orchestrator = ComparisonOrchestrator(
            url_primary=url_primary,
            url_competitor=url_competitor,
            target_keyword=target_keyword
        )

        results = orchestrator.run_full_analysis()
        duration = time.time() - start_time

        primary_onpage_score = calculate_onpage_score(results['primary'].get('semantic', {}))
        competitor_onpage_score = calculate_onpage_score(results['competitor'].get('semantic', {}))

        if 'scores' not in results['primary']:
            results['primary']['scores'] = {}
        if 'scores' not in results['competitor']:
            results['competitor']['scores'] = {}

        results['primary']['scores']['on_page_score'] = primary_onpage_score
        results['competitor']['scores']['on_page_score'] = competitor_onpage_score

        # Debug: log all keys from orchestrator
        logger.info("=" * 80)
        logger.info("ORCHESTRATOR RESULTS KEYS:")
        logger.info(f"Primary keys:    {list(results.get('primary', {}).keys())}")
        logger.info(f"Competitor keys: {list(results.get('competitor', {}).keys())}")
        for key in ['technical', 'authority', 'semantic']:
            val = results.get('primary', {}).get(key)
            if val:
                logger.info(f"Primary '{key}' keys: {list(val.keys())}")
            else:
                logger.warning(f"Primary '{key}' NOT FOUND in orchestrator results")
        logger.info("=" * 80)

        report = ComparisonReport.objects.create(
            url_primary=url_primary,
            url_competitor=url_competitor,
            target_keyword=target_keyword,
            detected_keyword_primary=results['primary'].get('detected_keyword', 'Unknown'),
            detected_keyword_competitor=results['competitor'].get('detected_keyword', 'Unknown'),
            intent_type_primary=results['primary'].get('intent_type', 'informational'),
            intent_type_competitor=results['competitor'].get('intent_type', 'informational'),
            scores_primary=results['primary'].get('scores', {}),
            scores_competitor=results['competitor'].get('scores', {}),
            gap_summary=results.get('gap_analysis', {}).get('summary', 'No summary available'),
            ranking_explanation=results.get('gap_analysis', {}).get('explanation', 'No explanation available'),
            analysis_duration=duration
        )

        # Strip non-serializable objects (BeautifulSoup) before storing in session
        def _strip_soup(d):
            if isinstance(d, dict):
                return {k: _strip_soup(v) for k, v in d.items() if k != 'soup'}
            if isinstance(d, list):
                return [_strip_soup(i) for i in d]
            return d

        request.session[f'analysis_results_{report.id}'] = _strip_soup(results)
        return redirect('comparative_analysis:results', report_id=report.id)

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        messages.error(request, f"Analysis failed: {str(e)}")
        return redirect('comparative_analysis:input_form')


@require_http_methods(["GET"])
def view_results(request, report_id):
    report = get_object_or_404(ComparisonReport, id=report_id)

    session_key = f'analysis_results_{report.id}'
    full_results = request.session.get(session_key, None)

    if full_results:
        logger.info(f"Loading full results from session for report {report_id}")

        primary_data = full_results.get('primary', {})
        competitor_data = full_results.get('competitor', {})

        primary_semantic = primary_data.get('semantic', {})
        competitor_semantic = competitor_data.get('semantic', {})
        primary_technical = _get_technical(primary_data)
        competitor_technical = _get_technical(competitor_data)
        primary_authority = _get_authority(primary_data)
        competitor_authority = _get_authority(competitor_data)

        context = {
            'report': report,
            'url_primary': report.url_primary,
            'url_competitor': report.url_competitor,
            'target_keyword': report.target_keyword,

            'primary': {
                'url': report.url_primary,
                'detected_keyword': primary_semantic.get('detected_keyword', report.detected_keyword_primary),
                'intent_type': primary_semantic.get('intent_type', report.intent_type_primary),
                'scores': report.scores_primary,
                'semantic': primary_semantic,
                'technical': primary_technical,
                'authority': primary_authority,
                'keyword_placement': primary_semantic.get('keyword_placement', {
                    'in_title': False, 'in_h1': False, 'density': 0.0
                }),
                'topic_depth': primary_semantic.get('topic_depth', {
                    'score': 0, 'depth_level': 0, 'coverage_areas': [],
                    'missing_topics': [], 'hierarchy_quality': 0
                }),
                'eeat_signals': primary_semantic.get('eeat_signals', _empty_eeat()),
                'content_quality_score': primary_semantic.get('content_quality_score', 0),
                'readability_score': primary_semantic.get('readability_score', 0),
                'intent_alignment_score': primary_semantic.get('intent_alignment_score', 0),
                'word_count': primary_semantic.get('word_count', 0),
            },

            'competitor': {
                'url': report.url_competitor,
                'detected_keyword': competitor_semantic.get('detected_keyword', report.detected_keyword_competitor),
                'intent_type': competitor_semantic.get('intent_type', report.intent_type_competitor),
                'scores': report.scores_competitor,
                'semantic': competitor_semantic,
                'technical': competitor_technical,
                'authority': competitor_authority,
                'keyword_placement': competitor_semantic.get('keyword_placement', {
                    'in_title': False, 'in_h1': False, 'density': 0.0
                }),
                'topic_depth': competitor_semantic.get('topic_depth', {
                    'score': 0, 'depth_level': 0, 'coverage_areas': [],
                    'missing_topics': [], 'hierarchy_quality': 0
                }),
                'eeat_signals': competitor_semantic.get('eeat_signals', _empty_eeat()),
                'content_quality_score': competitor_semantic.get('content_quality_score', 0),
                'readability_score': competitor_semantic.get('readability_score', 0),
                'intent_alignment_score': competitor_semantic.get('intent_alignment_score', 0),
                'word_count': competitor_semantic.get('word_count', 0),
            },

            'gap_summary': report.gap_summary,
            'ranking_explanation': report.ranking_explanation,
            'analysis_duration': round(report.analysis_duration, 2) if report.analysis_duration else None,
            'gap_analysis': full_results.get('gap_analysis', {}),
        }

        logger.info("=" * 80)
        logger.info("CONTEXT SUMMARY:")
        logger.info(f"primary.technical.technical_score : {primary_technical.get('technical_score', 'N/A')}")
        logger.info(f"primary.technical.mobile_responsive: {primary_technical.get('mobile_responsive', 'N/A')}")
        logger.info(f"primary.authority keys            : {list(primary_authority.keys())}")
        logger.info(f"primary.authority.domain_authority: {primary_authority.get('domain_authority', 'N/A')}")
        logger.info("=" * 80)

    else:
        logger.warning(f"No session data for report {report_id} - using database data only")

        context = {
            'report': report,
            'url_primary': report.url_primary,
            'url_competitor': report.url_competitor,
            'target_keyword': report.target_keyword,
            'primary': {
                'url': report.url_primary,
                'detected_keyword': report.detected_keyword_primary,
                'intent_type': report.intent_type_primary,
                'scores': report.scores_primary,
                'semantic': {},
                'technical': _empty_technical(),
                'authority': _empty_authority(),
                'keyword_placement': {'in_title': False, 'in_h1': False, 'density': 0.0},
                'topic_depth': {'score': 0, 'depth_level': 0},
                'eeat_signals': _empty_eeat(),
                'content_quality_score': 0,
                'readability_score': 0,
                'intent_alignment_score': 0,
            },
            'competitor': {
                'url': report.url_competitor,
                'detected_keyword': report.detected_keyword_competitor,
                'intent_type': report.intent_type_competitor,
                'scores': report.scores_competitor,
                'semantic': {},
                'technical': _empty_technical(),
                'authority': _empty_authority(),
                'keyword_placement': {'in_title': False, 'in_h1': False, 'density': 0.0},
                'topic_depth': {'score': 0, 'depth_level': 0},
                'eeat_signals': _empty_eeat(),
                'content_quality_score': 0,
                'readability_score': 0,
                'intent_alignment_score': 0,
            },
            'gap_summary': report.gap_summary,
            'ranking_explanation': report.ranking_explanation,
            'analysis_duration': round(report.analysis_duration, 2) if report.analysis_duration else None,
        }

        messages.warning(request, "Detailed analysis data not available. Re-run analysis for full details.")

    # Parse ranking_explanation — runs for BOTH paths
    raw_explanation = context.get('ranking_explanation') or ''
    logger.info(f"[EXPLANATION] preview={repr(raw_explanation[:200])}")

    parsed_explanation, is_json = _parse_ranking_explanation(raw_explanation)
    context['ranking_explanation'] = parsed_explanation
    context['explanation_is_json'] = is_json

    if is_json:
        logger.info(
            f"[EXPLANATION] is_json=True, "
            f"reasons={len(parsed_explanation.get('reasons', []))}, "
            f"recs={len(parsed_explanation.get('recommendations', []))}"
        )

    return render(request, 'comparative_analysis/results.html', context)


# ============================================================
# HELPER: Calculate On-Page Score
# ============================================================
def calculate_onpage_score(semantic_data):
    """
    On-page SEO score (0-100):
    - Keyword placement : 30 pts
    - Content quality   : 25 pts
    - Intent alignment  : 20 pts
    - Topic depth       : 15 pts
    - E-E-A-T signals   : 10 pts
    """
    if not semantic_data:
        return 0

    score = 0
    kw = semantic_data.get('keyword_placement', {})

    if kw.get('in_title', False):
        score += 10
    if kw.get('in_h1', False):
        score += 10
    density = kw.get('density', 0)
    if 0.5 <= density <= 2.5:
        score += 10
    elif density > 0:
        score += 5

    score += int(semantic_data.get('content_quality_score', 0) * 0.25)
    score += int(semantic_data.get('intent_alignment_score', 0) * 0.20)
    score += int(semantic_data.get('topic_depth', {}).get('score', 0) * 0.15)
    score += int(semantic_data.get('eeat_signals', {}).get('score', 0) * 0.10)

    final = min(max(score, 0), 100)
    logger.info(f"On-page score: {final}/100")
    return final