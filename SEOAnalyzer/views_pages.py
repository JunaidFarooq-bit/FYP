"""
View Functions for SEOAnalyzer.
Page views, authentication, and utility views separated from the main audit logic.
"""
import re
import uuid
import hashlib
import hmac
import base64
import time
import logging
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from googlesearch import search

from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse, FileResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings

from .models import Profile
from .helpers import send_forget_password_mail
from .services.sentiment_analyzer import analyze_sentiment
from .views import Website_Audit
from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2

logger = logging.getLogger(__name__)


def sentiment_analysis_page(request):
    """Render the sentiment analysis page."""
    return render(request, 'sentiment_analysis.html')


def analyze_sentiment_view(request):
    """Analyze sentiment of content from a URL."""
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        mode = request.POST.get('mode', 'auto')
        
        if not url:
            return render(request, 'sentiment_analysis.html', {
                'error': 'Please enter a valid URL'
            })
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            title = soup.find('title')
            page_title = title.get_text().strip() if title else 'No title'
            
            page_text = soup.get_text(separator=' ', strip=True)
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc['content'] if meta_desc else ''
            
            word_count = len(page_text.split())
            
            sentiment_result = analyze_sentiment(
                text=page_text,
                api_key=None,
                mode=mode
            )
            
            context = {
                'success': True,
                'url': url,
                'title': page_title,
                'meta_description': meta_description,
                'word_count': word_count,
                'sentiment': sentiment_result,
                'mode_used': mode
            }
            
            return render(request, 'sentiment_results.html', context)
            
        except requests.RequestException as e:
            return render(request, 'sentiment_analysis.html', {
                'error': f'Failed to fetch URL: {str(e)}'
            })
        except Exception as e:
            return render(request, 'sentiment_analysis.html', {
                'error': f'Error analyzing content: {str(e)}'
            })
    
    return render(request, 'sentiment_analysis.html')


def upload(request, url):
    """Create a Website_Audit instance for a URL."""
    if not url:
        return None
    obj = Website_Audit(str(url), request=request)
    return obj


def Report(request):
    """Generate and send SEO report via email using cached audit data."""
    import hashlib
    from django.core.cache import cache
    
    try:
        url = request.POST.get('url') or request.GET.get('url', '')
        if not url:
            messages.error(request, 'No URL provided for report generation.')
            return render(request, 'home.html')
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Try to get cached audit results first (from show() view)
        cache_key = f"audit_results_{hashlib.md5(url.encode()).hexdigest()}"
        cached_audit_data = cache.get(cache_key)
        
        if cached_audit_data:
            # Use the exact same data that was displayed on the page
            logger.info(f"Using cached audit data for email report")
            audit_data = cached_audit_data
            used_cached = True
        else:
            # Fallback: run fresh audit
            logger.warning(f"No cached audit data found, running fresh audit for email")
            obj = Website_Audit(url, request=request)
            audit_data = obj.get_data()
            used_cached = False
        
        # Log key data points for verification
        logger.info(f"Email Report Data - Title: '{audit_data.get('title', '')[:50]}...', Score: {audit_data.get('title_score')}")
        logger.info(f"Email Report Data - Speed: {audit_data.get('speed')}s, Links: {audit_data.get('internal_links')}/{audit_data.get('external_links')}")
        logger.info(f"Email Report Data - Flags: robots={audit_data.get('robot_flag')}, sitemap={audit_data.get('sitemap_flag')}, schema={audit_data.get('schema_flag')}")
        
        # Generate report using cached/fresh data
        obj = Website_Audit(url, request=request)
        result = obj.Report(audit_data, use_comprehensive=True)
        
        if result['success']:
            if result['email_sent']:
                messages.success(
                    request, 
                    'Report generated successfully! Check your registered email.'
                )
            else:
                messages.success(
                    request, 
                    'Report generated successfully!'
                )
            logger.info(f"Report generated: {result['pdf_path']} (cached_audit={used_cached})")
        else:
            messages.error(
                request, 
                f'Report generation failed: {result["message"]}'
            )
            logger.error(f"Report failed: {result['message']}")
        
        home_url = reverse('Home')
        return redirect(home_url)
        
    except Exception as e:
        error_msg = f'An error occurred: {str(e)}'
        messages.error(request, error_msg)
        logger.error(error_msg)
        return render(request, 'home.html')


@login_required(login_url='login')
def download_report(request):
    """
    Generate and download SEO report PDF directly to device.
    
    This view uses the CACHED audit results (from show() view) to ensure
    the PDF matches exactly what was displayed on the page.
    """
    try:
        url = request.POST.get('url') or request.GET.get('url', '')
        if not url:
            messages.error(request, 'No URL provided for report generation.')
            return render(request, 'home.html')
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        logger.info(f"Generating downloadable PDF report for: {url}")
        
        # Try to get cached audit results first (from show() view)
        import hashlib
        from django.core.cache import cache
        from .services.report_orchestrator import generate_comprehensive_report_data
        
        cache_key = f"audit_results_{hashlib.md5(url.encode()).hexdigest()}"
        cached_audit_data = cache.get(cache_key)
        
        if cached_audit_data:
            # Use the exact same data that was displayed on the page
            logger.info(f"Using cached audit data for PDF generation")
            audit_data = cached_audit_data
            used_cached = True
        else:
            # Fallback: run fresh audit (shouldn't happen in normal flow)
            logger.warning(f"No cached audit data found, running fresh audit")
            obj = Website_Audit(url, request=request)
            audit_data = obj.get_data()
            used_cached = False
        
        # Get SEO metrics and keyword data (these can be from cache or fresh)
        # but merge them with the SAME audit data that was displayed
        comprehensive_data = generate_comprehensive_report_data(
            url=url,
            request=request,
            use_cache=True,
            force_refresh=False
        )
        
        # Merge: Use the SAME audit data that was displayed + fresh/comprehensive metrics
        # This ensures consistency between page display and PDF
        if 'error' not in comprehensive_data or comprehensive_data.get('analysis_sources'):
            # Use comprehensive structure but override SEO section with cached data
            report_data = comprehensive_data.copy()
            report_data['seo'] = audit_data  # Use the EXACT same data from page
            report_data['from_cached_audit'] = used_cached
            
            # Also copy legacy fields that PDF expects at root level
            report_data['url'] = audit_data.get('url', url)
            report_data['title'] = audit_data.get('title', '')
            report_data['desc'] = audit_data.get('desc', '')
            report_data['title_score'] = audit_data.get('title_score', 0)
            report_data['desc_score'] = audit_data.get('desc_score', 0)
            report_data['H'] = audit_data.get('H', 'None')
            report_data['heading_score'] = audit_data.get('heading_score', 0)
            report_data['speed'] = audit_data.get('speed', 0)
            report_data['internal_links'] = audit_data.get('internal_links', 0)
            report_data['external_links'] = audit_data.get('external_links', 0)
            report_data['b_links'] = audit_data.get('b_links', 0)
            report_data['alt_count'] = audit_data.get('alt_count', 0)
            report_data['lst'] = audit_data.get('lst', [])
            report_data['dens'] = audit_data.get('dens', [])
            report_data['robot_flag'] = audit_data.get('robot_flag', False)
            report_data['sitemap_flag'] = audit_data.get('sitemap_flag', False)
            report_data['schema_flag'] = audit_data.get('schema_flag', False)
            report_data['ogp_flag'] = audit_data.get('ogp_flag', False)
            report_data['icon_flag'] = audit_data.get('icon_flag', False)
            report_data['analytics_flag'] = audit_data.get('analytics_flag', False)
            report_data['https'] = audit_data.get('https', False)
            report_data['dmca'] = audit_data.get('dmca', False)
            report_data['ssl_name'] = audit_data.get('ssl_name', '')
            report_data['ssl_expiry'] = audit_data.get('ssl_expiry', '')
            report_data['ip'] = audit_data.get('ip', '')
            report_data['loc_name'] = audit_data.get('loc_name', '')
            report_data['webserver'] = audit_data.get('webserver', '')
            report_data['error_len'] = audit_data.get('error_len', 0)
            report_data['warn_len'] = audit_data.get('warn_len', 0)
            report_data['mob_score'] = audit_data.get('mob_score', 0)
            report_data['amp'] = audit_data.get('amp', False)
            report_data['render'] = audit_data.get('render', False)
            report_data['s_count'] = audit_data.get('s_count', 0)
            report_data['facebook_flag'] = audit_data.get('facebook_flag', False)
            report_data['instagram_flag'] = audit_data.get('instagram_flag', False)
            report_data['twitter_flag'] = audit_data.get('twitter_flag', False)
            report_data['linkedin_flag'] = audit_data.get('linkedin_flag', False)
            
            # Log key data points for verification
            logger.info(f"PDF Data Verification - Title: '{report_data.get('title')[:50]}...', Score: {report_data.get('title_score')}")
            logger.info(f"PDF Data Verification - Speed: {report_data.get('speed')}s, Links: {report_data.get('internal_links')}/{report_data.get('external_links')}")
            logger.info(f"PDF Data Verification - Flags: robots={report_data.get('robot_flag')}, sitemap={report_data.get('sitemap_flag')}, schema={report_data.get('schema_flag')}")
        else:
            # Fallback to just audit data if comprehensive failed
            report_data = audit_data
        
        # Generate PDF without sending email
        from .modern_report import generate_seo_report
        import os
        
        output_dir = os.path.join(settings.MEDIA_ROOT, 'reports') if hasattr(settings, 'MEDIA_ROOT') else os.path.join(os.getcwd(), 'reports')
        os.makedirs(output_dir, exist_ok=True)
        
        result = generate_seo_report(
            data_dict=report_data,
            user_email='',  # No email
            sender_email='',
            sender_password='',
            output_dir=output_dir,
            send_email=False  # Don't send email, just generate
        )
        
        if not result['success']:
            messages.error(request, f'PDF generation failed: {result["message"]}')
            return redirect('Home')
        
        pdf_path = result['pdf_path']
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            messages.error(request, 'PDF file not found after generation.')
            return redirect('Home')
        
        # Create filename for download
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
        download_filename = f"WEB_LIFT_Report_{domain}_{time.strftime('%Y%m%d')}.pdf"
        
        # Return file as downloadable response
        response = FileResponse(
            open(pdf_path, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{download_filename}"'
        response['Content-Length'] = os.path.getsize(pdf_path)
        
        logger.info(f"PDF downloaded: {download_filename} (cached_audit={used_cached})")
        return response
        
    except Exception as e:
        error_msg = f'Error generating PDF download: {str(e)}'
        messages.error(request, error_msg)
        logger.error(error_msg)
        return redirect('Home')


@login_required(login_url='login')
def index(request):
    """Render the main index page."""
    return render(request, 'index.html')


@login_required(login_url='login')
def show(request):
    """Main SEO audit view - runs full analysis and displays results."""
    import validators
    import hashlib
    import json
    from django.core.cache import cache
    
    url = request.POST.get("fname")
    
    if not url:
        return render(request, 'index.html')
    
    url = url.strip()
    
    if not validators.url(url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if not validators.url(url):
            messages.error(request, 'Invalid URL format.')
            return render(request, 'index.html')
    
    try:
        # Run the audit
        data = upload(request, url)
        audit_data = data.get_data()
        
        # Store audit results in cache for PDF generation consistency
        # Use URL-based cache key so PDF generation retrieves the same data
        cache_key = f"audit_results_{hashlib.md5(url.encode()).hexdigest()}"
        cache.set(cache_key, audit_data, timeout=3600)  # 1 hour cache
        
        # Also store URL in session for reference
        request.session['last_audited_url'] = url
        request.session['last_audit_cache_key'] = cache_key
        
        # Log key data points for verification
        logger.info(f"=" * 60)
        logger.info(f"AUDIT CACHED - URL: {url}")
        logger.info(f"AUDIT CACHED - Key: {cache_key}")
        logger.info(f"AUDIT DATA - Title: '{audit_data.get('title', '')[:50]}...', Score: {audit_data.get('title_score')}")
        logger.info(f"AUDIT DATA - Speed: {audit_data.get('speed')}s, Links: {audit_data.get('internal_links')}/{audit_data.get('external_links')}")
        logger.info(f"AUDIT DATA - Flags: robots={audit_data.get('robot_flag')}, sitemap={audit_data.get('sitemap_flag')}, schema={audit_data.get('schema_flag')}")
        logger.info(f"=" * 60)
        
        return render(request, 'home.html', audit_data)
    except requests.exceptions.Timeout as e:
        messages.error(request, 'Connection timed out! Website is taking too much time.')
        return render(request, 'index.html')
    except requests.exceptions.RequestException as e:
        messages.error(request, 'Check your internet connection! Or maybe network error.')
        return render(request, 'index.html')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return render(request, 'index.html')


@login_required(login_url='login')
def seo_metrics(request):
    """Display SEO metrics using Moz API."""
    import validators
    
    data = {}

    if request.method == "GET":
        return render(request, 'seo_metrics.html')

    url = request.POST.get("fname")

    if not url or not validators.url(url):
        messages.error(request, 'Please enter a valid URL.')
        return render(request, 'seo_metrics.html')

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    access_id = getattr(settings, 'MOZ_ACCESS_ID', '')
    secret_key = getattr(settings, 'MOZ_SECRET_KEY', '')

    try:
        expires = str(int(time.time()) + 300)
        string_to_sign = f"{access_id}\n{expires}"
        binary_signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        safe_signature = quote(base64.b64encode(binary_signature))

        cols = "103079233568"
        encoded_url = quote(url, safe='')
        api_url = (
            f"https://lsapi.seomoz.com/linkscape/url-metrics/{encoded_url}"
            f"?Cols={cols}&AccessID={access_id}&Expires={expires}&Signature={safe_signature}"
        )

        response = requests.get(api_url, timeout=30)

        if response.status_code != 200:
            messages.error(request, f"Moz API error (Status {response.status_code}): {response.text[:200]}")
            return render(request, 'seo_metrics.html', data)

        json_data = response.json()

        data = {
            'pda': json_data.get('pda', 'N/A'),
            'upa': json_data.get('upa', 'N/A'),
            'links': json_data.get('uid', 'N/A'),
            'equity_links': json_data.get('ueid', 'N/A'),
            'moz_rank': json_data.get('umrp', 'N/A'),
        }

        return render(request, 'seo_metrics.html', data)

    except Exception as e:
        messages.error(request, f"Error fetching Moz metrics: {str(e)}")
        return render(request, 'seo_metrics.html', data)


@login_required(login_url='login')
def mobiletest(request):
    """Test mobile-friendliness using PageSpeed Insights API."""
    import validators
    import json
    
    try:
        if request.method == "GET":
            return render(request, 'mobiletest.html')

        url = request.POST.get("fname")
        if not url or not validators.url(url):
            messages.error(request, "Invalid URL")
            return render(request, 'mobiletest.html')
        
        data = {
            "url": url,
            "performance_score": None,
            "issues": [],
            "ux_checks": {},
            "final_verdict": ""
        }

        try:
            api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            params = [
                ("url", url),
                ("strategy", "mobile"),
                ("key", getattr(settings, 'PAGESPEED_API_KEY', '')),
                ("category", "performance"),
                ("category", "accessibility"),
                ("category", "best-practices"),
                ("category", "seo"),
            ]

            response = None
            last_err = None
            for attempt in range(2):
                try:
                    response = requests.get(api_url, params=params, timeout=120)
                    break
                except requests.exceptions.Timeout as te:
                    last_err = te
                    logger.warning(f"PageSpeed API timeout (attempt {attempt + 1}/2): {te}")
            
            if response is None:
                raise last_err if last_err else Exception("PageSpeed API: no response")

            if response.status_code != 200:
                error_detail = response.json().get("error", {}).get("message", response.text[:200])
                raise Exception(f"PageSpeed API error ({response.status_code}): {error_detail}")

            api_data = response.json()
            lh = api_data.get("lighthouseResult", {}).get("categories", {})

            data.update({
                "performance_score": round((lh.get("performance", {}).get("score") or 0) * 100),
                "accessibility_score": round((lh.get("accessibility", {}).get("score") or 0) * 100),
                "best_practices_score": round((lh.get("best-practices", {}).get("score") or 0) * 100),
                "seo_score": round((lh.get("seo", {}).get("score") or 0) * 100),
            })
        except Exception as e:
            logger.warning(f"Lighthouse fetch error: {e}")
            data["lighthouse_error"] = str(e)

        try:
            html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).text
            soup = BeautifulSoup(html, "html.parser")

            viewport = soup.find("meta", attrs={"name": "viewport"})
            data["ux_checks"]["viewport"] = bool(viewport)
            viewport_content = viewport.get("content", "") if viewport else ""
            data["ux_checks"]["content_fit"] = "width=device-width" in viewport_content
            data["ux_checks"]["scalable"] = "user-scalable=no" not in viewport_content

            images = soup.find_all("img")
            responsive_images = sum(1 for img in images if "max-width" in img.get("style", "") or img.get("width") is None)
            data["ux_checks"]["responsive_images"] = responsive_images > 0
            data["ux_checks"]["alt_text"] = all(img.get("alt") for img in images) if images else True

            small_fonts = 0
            for tag in soup.find_all(style=True):
                if "font-size" in tag["style"]:
                    size = tag["style"].split("font-size:")[-1].split("px")[0]
                    try:
                        if int(size.strip()) < 12:
                            small_fonts += 1
                    except: 
                        pass
            data["ux_checks"]["font_size_ok"] = small_fonts == 0

            buttons = soup.find_all(["button", "a"])
            data["ux_checks"]["tap_targets"] = len(buttons) > 0

        except Exception:
            data["ux_checks"] = {}

        checks_passed = sum(1 for check in data["ux_checks"].values() if check)
        if (data.get("performance_score") or 0) >= 90 and checks_passed >= 5:
            data["final_verdict"] = "Fully Mobile Optimized"
        elif checks_passed >= 3:
            data["final_verdict"] = "Partially Mobile Friendly"
        else:
            data["final_verdict"] = "Poor Mobile Experience"

        return render(request, "mobiletest.html", data)
    
    except requests.exceptions.Timeout:
        messages.error(request, "Request timed out")
        return render(request, "mobiletest.html")
    except Exception as e:
        messages.error(request, str(e))
        return render(request, "mobiletest.html")


@login_required(login_url='login')
def robot(request):
    """Generate robots.txt content for a URL."""
    import validators
    
    try:
        if request.method == "GET":
            return render(request, 'robot.html')
        
        url = request.POST["fname"]
        if not url or not validators.url(url):
            return render(request, 'robot.html')

        content = "#robots.txt generated by Smart Web Analyzer\n"
        content += f"User-agent: *\n"
        content += "Disallow: \n"
        content += "Disallow: /cgi-bin/\n"
        content += "#Restricted Directory\n"
        content += "Sitemap: {}/sitemap.xml".format(url)

        data = {
            'content': content,
            'url': url
        }
        return render(request, 'robot.html', data)
    
    except requests.exceptions.Timeout:
        messages.error(request, 'Connection timed out!')
        return render(request, 'robot.html')
    except requests.exceptions.RequestException:
        messages.error(request, 'Check your internet connection!')
        return render(request, 'robot.html')


@login_required(login_url='login')
def keyPosition(request):
    """Check keyword ranking position in Google search results."""
    import validators
    
    try:
        if request.method == 'GET':
            return render(request, 'keyPosition.html')

        data = {}
        url = request.POST.get("url")
        keyword = request.POST.get("keyword")

        data['url'] = url
        data['keyword'] = keyword

        if not url or not keyword or not validators.url(url):
            return render(request, 'keyPosition.html', data)

        def normalize_url(url):
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
            if not re.search(r'www\.', url):
                url = url.replace("://", "://www.")
            if not url.endswith('/'):
                url += '/'
            return url

        url1 = normalize_url(url)
        data["url"] = url1
        data["keyword"] = keyword

        def find_link_position(keyword, link):
            search_results = list(search(keyword, num_results=10))
            for position, url in enumerate(search_results, 1):
                if url == link:
                    return position
            return -1

        position = find_link_position(keyword, url1)
        if position != -1:
            data['rank'] = f"The link '{url1}' is found at position {position} in the results."
        else:
            data['rank'] = f"The link '{url1}' is not found in the top 10 search results."

        return render(request, 'keyPosition.html', data)
    
    except requests.exceptions.Timeout:
        messages.error(request, 'Connection timed out!')
        return render(request, 'keyPosition.html')
    except requests.exceptions.RequestException:
        messages.error(request, 'Check your internet connection!')
        return render(request, 'keyPosition.html')


@login_required(login_url='login')
def keysuggestion(request):
    """Get keyword suggestions from Google Autocomplete."""
    try:
        if request.method == "GET":
            return render(request, 'keysuggestion.html')
        
        data = {}
        keyword = request.POST.get("fname", "").strip()
        word_regex = re.compile(r'^[A-Za-z]+$')

        if keyword == '' or not word_regex.match(keyword):
            return render(request, 'keysuggestion.html', data)
        
        url = f"http://suggestqueries.google.com/complete/search?output=firefox&q={keyword}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        suggestions = response.json()[1]
        
        keywords = ""
        for i in suggestions:
            keywords += i + "\n"
        
        data["keywords"] = keywords
        data["keyword"] = keyword
        return render(request, 'keysuggestion.html', data)
    
    except requests.exceptions.Timeout:
        messages.error(request, 'Connection timed out!')
        return render(request, 'keysuggestion.html')
    except requests.exceptions.RequestException:
        messages.error(request, 'Check your internet connection!')
        return render(request, 'keysuggestion.html')


@login_required(login_url='login')
def keyword_ai_suggestions(request):
    """AI-Powered Keyword Suggestion using keyword_ai pipeline."""
    try:
        if request.method == "GET":
            return render(request, 'keyword_ai_suggestions.html')
        
        data = {}
        url = request.POST.get("url", "").strip()
        text = request.POST.get("text", "").strip()
        page_topic = request.POST.get("page_topic", "").strip()
        use_llm = request.POST.get("use_llm", "true").lower() != "false"
        
        if not url and not text:
            messages.error(request, 'Please provide either a URL or text content.')
            return render(request, 'keyword_ai_suggestions.html', data)
        
        result = run_keyword_pipeline_v2(
            url=url if url else None,
            text=text if text else None,
            page_topic=page_topic,
            use_llm=use_llm,
            use_advanced_ai=True,
            analyze_competitors=False,
            generate_optimization=False,
            save_to_db=True,
        )
        
        if "error" in result:
            messages.error(request, f"Analysis failed: {result['error']}")
            return render(request, 'keyword_ai_suggestions.html', data)
        
        data.update({
            "url": url,
            "text": text[:200] + "..." if len(text) > 200 else text,
            "page_topic": page_topic,
            "page_title": result.get("page_title", ""),
            "relevant_keywords": result.get("relevant_keywords", []),
            "scored_keywords": result.get("scored_keywords", [])[:20],
            "intent_groups": result.get("intent_groups", {}),
            "focus_keywords": result.get("focus_keywords", []),
            "keybert_keywords": result.get("keybert_keywords", [])[:10],
            "expanded_keywords": result.get("expanded_keywords", [])[:10],
            "ml_generated_suggestions": result.get("ml_generated_suggestions", [])[:15],
            "semantic_keywords": result.get("semantic_keywords", [])[:15],
            "tfidf_keywords": result.get("tfidf_keywords", [])[:10],
            "ai_expanded_keywords": result.get("ai_expanded_keywords", [])[:10],
            "question_keywords": result.get("question_keywords", [])[:8],
            "intent_classifications": result.get("intent_classifications", []),
            "content_analysis": result.get("content_analysis", {}),
            "keyword_count": len(result.get("relevant_keywords", []))
        })
        
        messages.success(request, f'Successfully analyzed and found {data["keyword_count"]} relevant keywords!')
        return render(request, 'keyword_ai_suggestions.html', data)
        
    except Exception as e:
        logger.error(f"Keyword AI analysis failed: {e}")
        messages.error(request, f'Analysis failed: {str(e)}')
        return render(request, 'keyword_ai_suggestions.html')


def loginuser(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('pass')
        
        if not username or not password:
            messages.error(request, 'Please fill in all fields!')
            return redirect('login')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('Home')
        else:
            messages.error(request, 'Invalid Credentials!')
            return redirect('login')
    
    return render(request, 'fyplogin.html')


def register(request):
    """Handle user registration."""
    def is_valid_email(email):
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(regex, email))

    context = {}
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('FirstName')
        last_name = request.POST.get('LastName')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        context.update({
            'username': username,
            'firstname': first_name,
            'lastname': last_name,
            'email': email
        })

        if not all([username, email, first_name, last_name, password1, password2]):
            messages.error(request, 'Please fill in all the fields!')
            return render(request, 'register.html', context)

        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'register.html', context)

        if not is_valid_email(email):
            messages.error(request, 'Please enter a valid email address!')
            return render(request, 'register.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered!')
            del context['email']
            return render(request, 'register.html', context)

        try:
            user = User.objects.create_user(
                username, email, password1, 
                first_name=first_name, last_name=last_name
            )
            Profile.objects.create(user=user)
            return redirect('login')
        except:
            messages.error(request, 'This username already exists!')
            return render(request, 'register.html')

    return render(request, 'register.html')


@never_cache
def logoutuser(request):
    """Handle user logout."""
    logout(request)
    response = redirect('login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def ChangePassword(request, token):
    """Handle password change via token."""
    context = {}

    try:
        profile_obj = Profile.objects.filter(forget_password_token=token).first()
        context = {'user_id': profile_obj.user.id}

        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('reconfirm_password')
            user_id = request.POST.get('user_id')

            if user_id is None:
                messages.error(request, 'No user id found.')
                return redirect(f'/change-password/{token}/')

            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect(f'/change-password/{token}/')

            user_obj = User.objects.get(id=user_id)
            user_obj.set_password(new_password)
            user_obj.save()
            return redirect('login')

    except Exception as e:
        logger.error(f'ChangePassword error: {e}')
    
    return render(request, 'change-password.html', context)


def ForgetPassword(request):
    """Handle forgot password request."""
    try:
        if request.method == 'POST':
            email = request.POST.get('email')

            if not email:
                messages.error(request, 'Please enter your email address.')
                return redirect('forget_password')

            user = User.objects.filter(email=email).first()

            if not user:
                messages.error(request, 'No account found with this email address.')
                return redirect('forget_password')

            token = str(uuid.uuid4())

            profile = Profile.objects.get(user=user)
            profile.forget_password_token = token
            profile.save()

            send_forget_password_mail(user.email, token)

            messages.success(request, 'Password reset email sent! Please check your inbox.')
            return redirect('forget_password')

    except Exception as e:
        logger.error(f'ForgetPassword error: {e}')
        messages.error(request, 'An error occurred. Please try again.')

    return render(request, 'forget-password.html')
