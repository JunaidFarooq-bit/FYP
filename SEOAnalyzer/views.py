"""
Refactored SEO Analyzer Views - Simplified Website_Audit Class
Uses service modules for better separation of concerns.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urlparse

from django.conf import settings
from django.shortcuts import render

from bs4 import BeautifulSoup
import requests
import validators

from .services.async_http_client import fetch_url_optimized
from .models import Profile
from .helpers import send_forget_password_mail
from .modern_report import generate_seo_report
from .services.report_orchestrator import generate_comprehensive_report_data
from .services.eeat_analyzer import EEATAnalyzer
from .services.grammar_analyzer import GrammarAnalyzer
from .services.link_checker import LinkService
from .services.minification_checker import MinificationService
from .services.technical_audit import TechnicalAuditService
from .services.content_analysis_service import ContentAnalysisService
from .services.seo_analysis_service import SEOAnalysisService
from .services.technical_audit_service_v2 import TechnicalAuditServiceV2

logger = logging.getLogger(__name__)


class WebsiteAuditOrchestrator:
    """
    Simplified Website Audit orchestrator that coordinates various analysis services.
    Much smaller and focused compared to the original monolithic class.
    """
    
    def __init__(self, url, request=None):
        # Store request and derive user_email
        self.request = request
        self.user_email = (
            request.user.email
            if request is not None
            and hasattr(request, 'user')
            and request.user.is_authenticated
            else None
        )
        
        # Normalize and validate URL
        self.url = self._normalize_url(url)
        self.base_url = self._get_base_url(self.url)
        self.domain = self._get_domain(self.url)
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # Fetch page content
        self._fetch_page()
        
        # Initialize service instances
        self._init_services()
        
        # Store results
        self.results = {}
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL format."""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def _get_base_url(self, url: str) -> str:
        """Extract base URL from full URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc.lower().replace('www.', '')
    
    def _fetch_page(self):
        """Fetch page content using optimized async HTTP client."""
        try:
            result = fetch_url_optimized(self.url, cache_ttl=300)
            if result['error']:
                logger.error(f"Error fetching {self.url}: {result['error']}")
                self.response = ""
                self.soup = BeautifulSoup("", 'html.parser')
                self.response_headers = {}
                self.status_code = None
                self.final_url = self.url
                self.was_redirected = False
                self.redirect_url = None
                self.ttfb = None
            else:
                self.response = result['text']
                _enc = result['encoding'] or 'utf-8'
                self.soup = BeautifulSoup(
                    self.response.encode(_enc, errors='replace'),
                    'html.parser',
                    from_encoding=_enc,
                )
                self.response_headers = result['headers']
                self.status_code = result['status']
                self.final_url = result['final_url']
                self.was_redirected = (self.final_url != self.url)
                self.redirect_url = self.final_url if self.was_redirected else None
                self.ttfb = None
        except Exception as e:
            logger.error(f"Unexpected error fetching {self.url}: {e}")
            self.response = ""
            self.soup = BeautifulSoup("", 'html.parser')
            self.response_headers = {}
            self.status_code = None
            self.final_url = self.url
            self.was_redirected = False
            self.redirect_url = None
            self.ttfb = None
    
    def _init_services(self):
        """Initialize all analysis services."""
        # Existing services
        self._eeat_analyzer = EEATAnalyzer()
        self._grammar_analyzer = GrammarAnalyzer()
        self._link_service = LinkService(self.session, self.base_url, self.domain, self.final_url)
        self._tech_audit = TechnicalAuditService(self.session, self.base_url)
        self._minification_service = MinificationService(self.session, self.url, self.response)
        
        # New refactored services
        self._content_service = ContentAnalysisService(self.soup, self.response)
        self._seo_service = SEOAnalysisService(self.soup, self.base_url, self.url)
        self._technical_service_v2 = TechnicalAuditServiceV2(self.session, self.base_url, self.url)
    
    def run_comprehensive_audit(self) -> Dict[str, Any]:
        """Run comprehensive audit using all services."""
        try:
            # Content Analysis
            content_results = self._content_service.analyze_content_quality()
            
            # SEO Analysis
            seo_results = self._seo_service.analyze_seo_elements()
            
            # Technical Analysis
            technical_results = self._technical_service_v2.analyze_technical_seo()
            
            # E-E-A-T Analysis
            eeat_results = self._analyze_eeat()
            
            # Grammar Analysis
            grammar_results = self._analyze_grammar()
            
            # Link Analysis
            link_results = self._analyze_links()
            
            # Minification Analysis
            minification_results = self._analyze_minification()
            
            # Calculate overall scores
            overall_score = self._calculate_overall_score({
                'content': content_results,
                'seo': seo_results,
                'technical': technical_results,
                'eeat': eeat_results,
                'grammar': grammar_results,
                'links': link_results,
                'minification': minification_results
            })
            
            # Compile results
            self.results = {
                'url': self.url,
                'final_url': self.final_url,
                'status_code': self.status_code,
                'overall_score': overall_score,
                'content_analysis': content_results,
                'seo_analysis': seo_results,
                'technical_analysis': technical_results,
                'eeat_analysis': eeat_results,
                'grammar_analysis': grammar_results,
                'link_analysis': link_results,
                'minification_analysis': minification_results,
                'audit_timestamp': datetime.now().isoformat(),
                'user_email': self.user_email
            }
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error in comprehensive audit: {e}")
            return {
                'url': self.url,
                'error': str(e),
                'overall_score': 0,
                'audit_timestamp': datetime.now().isoformat()
            }
    
    def _analyze_eeat(self) -> Dict[str, Any]:
        """Analyze E-E-A-T factors."""
        try:
            # Use existing E-E-A-T analyzer
            title = self.soup.find('title')
            title_text = title.get_text(strip=True) if title else ""
            
            eeat_result = self._eeat_analyzer.analyze(content_type='title', content=title_text)
            return eeat_result or {'score': 0, 'signals': [], 'recommendations': []}
            
        except Exception as e:
            logger.error(f"Error in E-E-A-T analysis: {e}")
            return {'score': 0, 'signals': [], 'recommendations': []}
    
    def _analyze_grammar(self) -> Dict[str, Any]:
        """Analyze grammar and spelling."""
        try:
            grammar_result = self._grammar_analyzer.analyze(self.soup)
            return grammar_result or {'score': 0, 'errors': [], 'recommendations': []}
            
        except Exception as e:
            logger.error(f"Error in grammar analysis: {e}")
            return {'score': 0, 'errors': [], 'recommendations': []}
    
    def _analyze_links(self) -> Dict[str, Any]:
        """Analyze internal and external links."""
        try:
            link_result = self._link_service.analyze_links(self.soup)
            return link_result or {'score': 0, 'internal': 0, 'external': 0, 'broken': 0}
            
        except Exception as e:
            logger.error(f"Error in link analysis: {e}")
            return {'score': 0, 'internal': 0, 'external': 0, 'broken': 0}
    
    def _analyze_minification(self) -> Dict[str, Any]:
        """Analyze CSS/JS minification."""
        try:
            minification_result = self._minification_service.check_all()
            return minification_result or {'score': 0, 'css_minified': False, 'js_minified': False}
            
        except Exception as e:
            logger.error(f"Error in minification analysis: {e}")
            return {'score': 0, 'css_minified': False, 'js_minified': False}
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall audit score."""
        try:
            scores = []
            weights = {
                'content': 0.20,
                'seo': 0.25,
                'technical': 0.20,
                'eeat': 0.15,
                'grammar': 0.10,
                'links': 0.05,
                'minification': 0.05
            }
            
            for category, weight in weights.items():
                if category in results:
                    if 'score' in results[category]:
                        scores.append(results[category]['score'] * weight)
                    elif 'content_quality_score' in results[category]:
                        scores.append(results[category]['content_quality_score'] * weight)
                    elif 'seo_score' in results[category]:
                        scores.append(results[category]['seo_score'] * weight)
                    elif 'technical_score' in results[category]:
                        scores.append(results[category]['technical_score'] * weight)
            
            overall_score = sum(scores) if scores else 0
            return round(min(100, overall_score), 1)
            
        except Exception as e:
            logger.error(f"Error calculating overall score: {e}")
            return 0


    def get_data(self):
        """Backward-compatible alias for run_comprehensive_audit()."""
        return self.run_comprehensive_audit()

    def Report(self, audit_data=None, use_comprehensive=False):
        """Backward-compatible stub for report generation. Returns a basic result dict."""
        from .services.report_orchestrator import generate_comprehensive_report_data
        try:
            report_data = generate_comprehensive_report_data(
                url=self.url,
                request=self.request,
                use_cache=True,
                force_refresh=False,
            )
            return {'success': True, 'email_sent': False, 'pdf_path': '', 'data': report_data}
        except Exception as e:
            return {'success': False, 'email_sent': False, 'message': str(e)}


# Use the original battle-tested implementation which returns the flat dict
# that all templates and views expect. The refactored orchestrator above returns
# a nested structure incompatible with the existing templates.
from .views_original import Website_Audit  # noqa: F401, E402
