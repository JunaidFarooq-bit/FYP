"""
SEO Analyzer Views - Refactored.
Main audit logic using service modules.
"""
# Standard imports
import os
import re
import json
import time
import logging
import concurrent.futures
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin, urlunparse

# Django imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, reverse
from django.views.decorators.http import require_POST

# Third-party imports
import requests
import validators
import aiohttp
import asyncio
import ssl
import socket
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import geocoder

# Internal imports
from .models import Profile
from .helpers import send_forget_password_mail
from .modern_report import generate_seo_report
from .services.report_orchestrator import generate_comprehensive_report_data

# Service imports
from .services.eeat_analyzer import EEATAnalyzer
from .services.grammar_analyzer import GrammarAnalyzer, DictionaryManager, add_to_dictionary_view
from .services.link_checker import LinkService
from .services.minification_checker import MinificationService
from .services.technical_audit import TechnicalAuditService

logger = logging.getLogger(__name__)

# API Keys
OPENROUTER_API_KEY = getattr(settings, 'OPENROUTER_API_KEY', '')


class Website_Audit(object):
    """
    Main SEO Audit class - now using service modules.
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
        
        # Fetch page content asynchronously
        self._fetch_page()
        
        # Initialize score variables
        self._init_scores()
        
        # Initialize service instances
        self._eeat_analyzer = EEATAnalyzer()
        self._grammar_analyzer = GrammarAnalyzer()
        self._link_service = LinkService(self.session, self.base_url, self.domain, self.final_url)
        self._tech_audit = TechnicalAuditService(self.session, self.base_url)
        self._minification_service = MinificationService(self.session, self.url, self.response)
    
    def _fetch_page(self):
        """Fetch page content using aiohttp with timeout."""
        async def _async_fetch(target_url: str):
            timeout = aiohttp.ClientTimeout(total=15)
            ssl_ctx = ssl.create_default_context()
            try:
                async with aiohttp.ClientSession(
                    headers=dict(self.session.headers),
                    connector=aiohttp.TCPConnector(ssl=ssl_ctx)
                ) as client:
                    async with client.get(
                        target_url,
                        timeout=timeout,
                        allow_redirects=True,
                        max_redirects=10
                    ) as resp:
                        raw_bytes = await resp.read()
                        detected_encoding = resp.charset or 'utf-8'
                        text = raw_bytes.decode(detected_encoding, errors='replace')
                        return {
                            'text': text,
                            'encoding': detected_encoding,
                            'headers': dict(resp.headers),
                            'status': resp.status,
                            'final_url': str(resp.url),
                            'error': None,
                        }
            except asyncio.TimeoutError:
                return {'text': '', 'encoding': 'utf-8', 'headers': {}, 'status': None,
                        'final_url': target_url, 'error': 'timeout'}
            except aiohttp.ClientError as exc:
                return {'text': '', 'encoding': 'utf-8', 'headers': {}, 'status': None,
                        'final_url': target_url, 'error': str(exc)}
        
        try:
            _loop = asyncio.new_event_loop()
            _fetch = _loop.run_until_complete(_async_fetch(self.url))
            _loop.close()
        except Exception as exc:
            _fetch = {'text': '', 'encoding': 'utf-8', 'headers': {}, 'status': None,
                      'final_url': self.url, 'error': str(exc)}
        
        if _fetch['error']:
            self.response = ""
            self.soup = BeautifulSoup("", 'html.parser')
            self.response_headers = {}
            self.status_code = None
            self.final_url = self.url
            self.was_redirected = False
            self.redirect_url = None
            self.ttfb = None
            logger.warning(f"Fetch error for {self.url}: {_fetch['error']}")
        else:
            self.response = _fetch['text']
            _enc = _fetch['encoding'] or 'utf-8'
            self.soup = BeautifulSoup(
                self.response.encode(_enc, errors='replace'),
                'html.parser',
                from_encoding=_enc,
            )
            self.response_headers = _fetch['headers']
            self.status_code = _fetch['status']
            self.final_url = _fetch['final_url']
            self.was_redirected = (self.final_url != self.url)
            self.redirect_url = self.final_url if self.was_redirected else None
            
            try:
                _head = self.session.head(self.url, timeout=5, allow_redirects=True)
                self.ttfb = round(_head.elapsed.total_seconds(), 3)
            except Exception:
                self.ttfb = None
        
        self.data = {}
    
    def _init_scores(self):
        """Initialize all score and flag variables."""
        self.title_score = 0
        self.desc_score = 0
        self.heading_score = 0
        self.internal_links = 0
        self.external_links = 0
        self.avg_score = 0
        self.alt_count = 0
        self.title = ""
        self.desc = ""
        self.heading = None
        self.H = None
        self.comp_desc = ""
        self.comp_head = ""
        self.conversion = None
        self.dict_1 = None
        self.total_count = 0
        self.Img_score = 0
        self.robot_flag = False
        self.sitemap_flag = False
        self.b_links = 0
        self.icon_flag = None
        self.schema_flag = None
        self.ogp_flag = None
        self.facebook_flag = False
        self.instagram_flag = False
        self.twitter_flag = False
        self.linkedin_flag = False
        self.ip_flag = None
        self.ip = None
        self.s_count = 0
        self.server_loc_flag = None
        self.loc_name = None
        self.error_len = 0
        self.warn_len = 0
        self.analytics_flag = None
        self.tech_flag = False
        self.webserver = None
        self.doc_flag = False
        self.encod_flag = False
        self.Doctype = None
        self.Encoding = None
        self.keyword_lst = []
        self.speed = 0
        self.plugins = None
        self.css = None
        self.jss = None
        self.mob_score = 0
        self.amp = None
        self.render = None
        self.mobpreview = None
        self.name = None
        self.organization = None
        self.ssl = False
        self.dmca = None
        self.https = None
        self.lst = []
        self.expiry_date = None
    
    def _normalize_url(self, url):
        """Normalize and validate URL."""
        if not url:
            return url
        
        url = url.strip()
        
        if not url.startswith(('http://', 'https://', '//')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        
        if not parsed.netloc and parsed.path:
            parts = parsed.path.split('/', 1)
            if len(parts) == 2:
                domain_part, path_part = parts
                url = f"{parsed.scheme or 'https'}://{domain_part}/{path_part}"
            else:
                url = f"{parsed.scheme or 'https'}://{parsed.path}"
            parsed = urlparse(url)
        
        path = parsed.path
        if path and not path.startswith('/'):
            path = '/' + path
        
        clean_url = urlunparse((
            parsed.scheme or 'https',
            parsed.netloc,
            path or '/',
            parsed.params,
            parsed.query,
            ''
        ))
        
        if not validators.url(clean_url):
            logger.warning(f"_normalize_url: '{clean_url}' did not pass validators.url()")
        
        return clean_url
    
    def _get_base_url(self, url):
        """Extract base URL (scheme + netloc only)."""
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
            scheme = parsed.scheme or 'https'
            return f"{scheme}://{parsed.netloc}"
        except Exception:
            return None
    
    def _get_domain(self, url):
        """Extract domain name only."""
        try:
            parsed = urlparse(url)
            return parsed.netloc if parsed.netloc else url
        except Exception:
            return url
    
    def Score(self, max_val, length):
        """Dynamic scoring with optimal range penalties."""
        if max_val <= 0:
            return 0
        
        if length < 0:
            length = 0
        
        if length == 0:
            return 0
        elif length > max_val:
            excess = length - max_val
            penalty = min(excess * 2, 50)
            base_score = 100 - penalty
            score = max(0, base_score)
        else:
            score = (length / max_val) * 100
        
        return max(0, min(100, round(score)))
    
    def remove_unicode_characters(self, input_string):
        """Clean string while preserving UTF-8 for international SEO."""
        if input_string is None:
            return ""
        
        if not isinstance(input_string, str):
            input_string = str(input_string)
        
        try:
            cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', input_string)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned.strip()
        except Exception as e:
            logger.error(f"Error cleaning text: {e}")
            return input_string.strip() if input_string else ""
    
    def _analyze_eeat_with_ai(self, content_type, content, context=None):
        """Delegate to EEATAnalyzer service."""
        return self._eeat_analyzer.analyze(content_type, content, context)
    
    def _fallback_eeat_analysis(self, content_type, content):
        """Use EEATAnalyzer fallback."""
        return self._eeat_analyzer._fallback_analysis(content_type, content)
    
    def get_title(self, min_length=30, max_length=60, use_ai=True):
        """Analyze title with E-E-A-T scoring."""
        title_tag = self.soup.find('title')
        
        if not title_tag:
            self.title = "Title is not Found!"
            self.data.update({
                'title_verdict': ' | ' + self.title,
                'title': '',
                'title_length': 0,
                'title_issues': ['Missing <title> tag'],
                'title_eeat_score': 0,
                'title_eeat_signals': [],
                'title_eeat_recommendations': ['Add a descriptive <title> tag']
            })
            self.title_score = 0
            return None
        
        try:
            title_text = title_tag.get_text(strip=True)
            title = self.remove_unicode_characters(title_text)
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
            title = ''
        
        title = title.strip()
        title_length = len(title)
        
        # E-E-A-T Analysis
        if use_ai and title:
            eeat_analysis = self._analyze_eeat_with_ai('title', title)
        else:
            eeat_analysis = self._fallback_eeat_analysis('title', title)
        
        issues = []
        
        # Length checks
        if title_length == 0:
            self.title = "Title is Empty!"
            issues.append("Empty title tag")
            eeat_analysis['eeat_score'] = 0
        elif title_length < min_length:
            self.title = "Title is too Short!"
            issues.append(f"Title too short ({title_length} chars)")
        elif min_length <= title_length <= max_length:
            self.title = "Title is Optimal!"
        elif max_length < title_length <= 70:
            self.title = "Title is Acceptable (may truncate on mobile)"
            issues.append(f"Title ({title_length} chars) may truncate")
        else:
            self.title = "Title is too Long!"
            issues.append(f"Title too long ({title_length} chars)")
        
        # Keyword stuffing detection
        if title:
            words = [w.lower() for w in re.findall(r'\b\w+\b', title) if len(w) > 3]
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            repeated_words = [word for word, count in word_freq.items() if count > 2]
            if repeated_words:
                issues.append(f"Keyword stuffing: '{repeated_words[0]}' repeated")
                eeat_analysis['eeat_score'] = max(0, eeat_analysis['eeat_score'] - 20)
        
        all_issues = issues + eeat_analysis['issues']
        
        # Calculate score
        if title_length == 0:
            title_score = 0
        elif min_length <= title_length <= max_length:
            ideal = 55
            deviation = abs(title_length - ideal)
            title_score = max(95, 100 - (deviation * 1.5))
        else:
            title_score = self.Score(max_length, title_length)
        
        # Combine: Technical (55%) + E-E-A-T (45%)
        self.title_score = int((title_score * 0.55) + (eeat_analysis['eeat_score'] * 0.45))
        
        self.data.update({
            'title_verdict': ' | ' + self.title,
            'title': title,
            'title_length': title_length,
            'title_issues': all_issues if all_issues else ['No issues detected'],
            'title_eeat_score': eeat_analysis['eeat_score'],
            'title_eeat_signals': eeat_analysis['signals'],
            'title_eeat_recommendations': eeat_analysis['recommendations'],
            'title_eeat_details': eeat_analysis.get('details', {})
        })
        
        return title
    
    def get_description(self, min_length=120, max_length=160, use_ai=True):
        """Analyze meta description with E-E-A-T scoring."""
        meta_tags = self.soup.findAll("meta")
        description = ""
        
        for tag in meta_tags:
            try:
                if 'name' in tag.attrs and tag.attrs['name'].strip().lower() == 'description':
                    if 'content' in tag.attrs and tag.attrs['content']:
                        description = tag.attrs['content']
                        break
            except (AttributeError, KeyError):
                continue
        
        self.comp_desc = self.remove_unicode_characters(description)
        self.data['description'] = self.comp_desc if self.comp_desc else ''
        desc_length = len(self.comp_desc)
        
        # E-E-A-T Analysis
        if use_ai and self.comp_desc:
            eeat_analysis = self._analyze_eeat_with_ai('description', self.comp_desc, context=self.title)
        else:
            eeat_analysis = self._fallback_eeat_analysis('description', self.comp_desc)
        
        issues = []
        
        # Length checks
        if desc_length == 0:
            self.desc = "Description Missing!"
            issues.append("Missing meta description")
            eeat_analysis['eeat_score'] = 0
        elif desc_length < min_length:
            self.desc = "Description is too Short"
            issues.append(f"Description too short ({desc_length} chars)")
        elif min_length <= desc_length <= max_length:
            self.desc = "Description is Optimal!"
        elif max_length < desc_length <= 170:
            self.desc = "Description is Acceptable (may truncate)"
            issues.append(f"Description ({desc_length} chars) may truncate")
        else:
            self.desc = "Description is too Long!"
            issues.append(f"Description too long ({desc_length} chars)")
        
        # Check for title duplication
        if self.comp_desc and self.title:
            desc_lower = self.comp_desc.lower()
            title_lower = self.title.lower()
            
            if desc_lower == title_lower:
                issues.append("Description duplicates title exactly")
                eeat_analysis['eeat_score'] = max(0, eeat_analysis['eeat_score'] - 30)
        
        all_issues = issues + eeat_analysis['issues']
        
        # Calculate score
        if desc_length == 0:
            desc_score = 0
        elif min_length <= desc_length <= max_length:
            ideal = 155
            deviation = abs(desc_length - ideal)
            desc_score = max(95, 100 - (deviation * 1.0))
        else:
            desc_score = self.Score(max_length, desc_length)
        
        # Combine: Technical (50%) + E-E-A-T (50%)
        self.desc_score = int((desc_score * 0.50) + (eeat_analysis['eeat_score'] * 0.50))
        
        self.data.update({
            'desc_verdict': ' | ' + self.desc,
            'desc_length': desc_length,
            'desc_issues': all_issues if all_issues else ['No issues detected'],
            'desc_eeat_score': eeat_analysis['eeat_score'],
            'desc_eeat_signals': eeat_analysis['signals'],
            'desc_eeat_recommendations': eeat_analysis['recommendations'],
            'desc_eeat_details': eeat_analysis.get('details', {})
        })
    
    def get_Heading(self, min_length=20, max_length=70, use_ai=True):
        """Analyze H1 heading with E-E-A-T scoring."""
        # Count all heading levels
        h1_tags = self.soup.findAll('h1')
        h1_count = len(h1_tags) if h1_tags else 0
        h2_count = len(self.soup.findAll('h2')) if self.soup else 0
        h3_count = len(self.soup.findAll('h3')) if self.soup else 0
        h4_count = len(self.soup.findAll('h4')) if self.soup else 0
        
        issues = []
        
        # H1 Count validation
        if h1_count > 1:
            issues.append(f"❌ CRITICAL: {h1_count} H1 tags found - Use ONLY ONE H1 per page")
            issues.append("💡 Multiple H1s confuse topic modeling & accessibility")
        elif h1_count == 0:
            issues.append("❌ CRITICAL: No H1 tag found - Essential for SEO & accessibility")
            issues.append("💡 H1 defines primary topic for Google & screen readers")
        
        # Determine which heading to analyze
        heading_tags = []
        if h1_count > 0:
            heading_tags = h1_tags
            self.H = "H1"
        else:
            h2_tags = self.soup.findAll('h2')
            if h2_tags:
                heading_tags = h2_tags
                self.H = "H2"
                issues.append("⚠ Using H2 as fallback - H1 is required")
        
        # Initialize variables
        com_heading = ""
        heading_length = 0
        eeat_analysis = self._fallback_eeat_analysis('heading', '')
        self.heading = "No Heading Found"
        
        # Extract heading text
        if heading_tags:
            try:
                heading_text = heading_tags[0].get_text(strip=True)
                self.comp_head = heading_text
            except Exception as e:
                logger.error(f"Error extracting heading: {e}")
                heading_text = ""
            
            com_heading = self.remove_unicode_characters(heading_text).strip()
            heading_length = len(com_heading)
            
            # E-E-A-T Analysis
            if use_ai and com_heading:
                eeat_analysis = self._analyze_eeat_with_ai('heading', com_heading, context=self.title)
            else:
                eeat_analysis = self._fallback_eeat_analysis('heading', com_heading)
        
        # Technical validation
        if heading_length == 0:
            self.heading = "Heading Tag is Empty"
            issues.append("❌ Empty heading tag - Bad for SEO & accessibility")
            eeat_analysis['eeat_score'] = 0
        elif heading_length < min_length:
            self.heading = "Heading is too Short"
            issues.append(f"⚠ Heading too short ({heading_length} chars)")
            issues.append("💡 Optimal: 60-70 chars for clear topic description")
        elif min_length <= heading_length <= max_length:
            self.heading = "Heading is Optimal!"
        else:
            self.heading = "Heading is too Long"
            issues.append(f"⚠ Heading too long ({heading_length} chars)")
            issues.append(f"💡 Keep under 70 chars for mobile readability")
        
        # Hierarchy validation
        hierarchy_issues = []
        if h2_count > 0 and h1_count == 0:
            hierarchy_issues.append("❌ H2 tags without H1 - Violates semantic structure")
        if h3_count > 0 and h2_count == 0:
            hierarchy_issues.append("❌ H3 tags without H2 - Breaks heading hierarchy")
        if h4_count > 0 and h3_count == 0:
            hierarchy_issues.append("❌ H4 tags without H3 - Invalid heading flow")
        
        if hierarchy_issues:
            issues.extend(hierarchy_issues)
            issues.append("💡 Fix: Ensure headings follow H1 > H2 > H3 > H4 order")
        
        # H1-Title relationship check
        if com_heading and self.title and self.H == "H1":
            h1_lower = com_heading.lower()
            title_lower = self.title.lower()
            
            if h1_lower == title_lower:
                issues.append("⚠ H1 duplicates title exactly")
                issues.append("💡 H1 should complement title with different wording")
            
            common_words = set(h1_lower.split()) & set(title_lower.split())
            if len(common_words) < 2 and len(title_lower.split()) > 3:
                issues.append("⚠ H1 and title have minimal overlap")
                issues.append("💡 Ensure H1 supports same topic as title")
        
        all_issues = issues + eeat_analysis['issues']
        
        # Structure signals
        structure_signals = []
        if h2_count >= 3:
            structure_signals.append(f"✓ Well-structured content ({h2_count} H2 sections)")
        if h3_count >= 2:
            structure_signals.append(f"✓ Detailed hierarchy ({h3_count} H3 subsections)")
        if h1_count == 1 and h2_count >= 3 and h3_count >= 1:
            structure_signals.append("✓ Excellent semantic structure (aids accessibility)")
        
        # Calculate technical score
        if h1_count == 0:
            heading_score = max(0, self.Score(max_length, heading_length) - 40)
        elif h1_count > 1:
            heading_score = max(0, self.Score(max_length, heading_length) - 25)
        elif heading_length == 0:
            heading_score = 0
        elif min_length <= heading_length <= max_length:
            ideal = 62
            deviation = abs(heading_length - ideal)
            heading_score = 100 - (deviation * 0.8)
            heading_score = max(95, min(100, heading_score))
        else:
            heading_score = self.Score(max_length, heading_length)
        
        # Bonus for excellent structure
        if h1_count == 1 and h2_count >= 3 and h3_count >= 2 and not hierarchy_issues:
            heading_score = min(100, heading_score + 5)
        
        self.heading_score = int((heading_score * 0.50) + (eeat_analysis['eeat_score'] * 0.50))
        
        # Store all results
        self.data.update({
            'head_verdict': ' | ' + self.heading,
            'heading': com_heading if heading_length > 0 else '',
            'heading_length': heading_length,
            'heading_type': self.H,
            'h1_count': h1_count,
            'h2_count': h2_count,
            'h3_count': h3_count,
            'h4_count': h4_count,
            'heading_issues': all_issues if all_issues else ['✅ No issues detected'],
            'heading_eeat_score': eeat_analysis['eeat_score'],
            'heading_eeat_signals': eeat_analysis['signals'] + structure_signals,
            'heading_eeat_recommendations': eeat_analysis['recommendations'],
            'heading_eeat_details': eeat_analysis.get('details', {})
        })
    
    def get_Google_preview(self):
        """Calculate Google SERP optimization score with E-E-A-T breakdown."""
        try:
            title_weight = 0.25
            desc_weight = 0.20
            heading_weight = 0.15
            title_eeat_weight = 0.15
            desc_eeat_weight = 0.15
            heading_eeat_weight = 0.10
            
            weighted_score = (
                (self.title_score * title_weight) +
                (self.desc_score * desc_weight) +
                (self.heading_score * heading_weight) +
                (self.data.get('title_eeat_score', 50) * title_eeat_weight) +
                (self.data.get('desc_eeat_score', 50) * desc_eeat_weight) +
                (self.data.get('heading_eeat_score', 50) * heading_eeat_weight)
            )
            
            bonus = 0
            
            if self.title_score >= 90 and self.desc_score >= 90:
                bonus += 3
            
            avg_eeat = (
                self.data.get('title_eeat_score', 0) + 
                self.data.get('desc_eeat_score', 0) + 
                self.data.get('heading_eeat_score', 0)
            ) / 3
            
            if avg_eeat >= 85:
                bonus += 7
            elif avg_eeat >= 70:
                bonus += 4
            
            if self.data.get('h1_count') == 1:
                bonus += 3
            
            if (self.data.get('h2_count', 0) >= 3 and 
                self.data.get('h3_count', 0) >= 2 and
                self.data.get('h1_count') == 1):
                bonus += 4
            
            mobile_ready = (
                20 <= self.data.get('title_length', 0) <= 60 and
                120 <= self.data.get('desc_length', 0) <= 160 and
                20 <= self.data.get('heading_length', 0) <= 70
            )
            if mobile_ready:
                bonus += 3

            # TTFB bonus/penalty
            if self.ttfb is not None:
                if self.ttfb <= 0.8:
                    bonus += 5
                    self.data['ttfb_verdict'] = f"Excellent ✓ ({self.ttfb}s)"
                elif self.ttfb <= 1.8:
                    bonus += 2
                    self.data['ttfb_verdict'] = f"Acceptable ⚠ ({self.ttfb}s)"
                else:
                    bonus = max(0, bonus - 3)
                    self.data['ttfb_verdict'] = f"Poor — optimize server response ✗ ({self.ttfb}s)"
                self.data['ttfb'] = self.ttfb

            self.avg_score = round(weighted_score + bonus)
            self.avg_score = max(0, min(100, self.avg_score))
            
            # E-E-A-T Breakdown for template
            self.data['eeat_breakdown'] = {
                'title_eeat': self.data.get('title_eeat_score', 0),
                'description_eeat': self.data.get('desc_eeat_score', 0),
                'heading_eeat': self.data.get('heading_eeat_score', 0),
                'average_eeat': round(avg_eeat, 1),
                'trust_level': 'high' if avg_eeat >= 75 else 'medium' if avg_eeat >= 50 else 'low',
                'helpful_content_ready': avg_eeat >= 70
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimization score: {e}")
            self.avg_score = 0
            avg_eeat = 0
        
        excellent = 88
        good = 70
        
        recommendations = []
        
        ai_recs = (
            self.data.get('title_eeat_recommendations', []) +
            self.data.get('desc_eeat_recommendations', []) +
            self.data.get('heading_eeat_recommendations', [])
        )
        ai_recs = list(dict.fromkeys(ai_recs))
        
        if self.avg_score >= excellent:
            google_verdict = "🏆 Excellent - SERP Optimized (2026 Standards)"
            optimization_level = 'Excellent'
            verdict = True
            
            if avg_eeat < 90:
                recommendations.append("💡 Consider: Further E-E-A-T enhancement for YMYL topics")
            
            return_val = 1
            
        elif self.avg_score >= good:
            google_verdict = "✅ Good - Well Optimized"
            optimization_level = 'Good'
            verdict = True
            
            if avg_eeat < 70:
                recommendations.append("🎯 PRIORITY: Improve E-E-A-T signals (currently below 2026 threshold)")
            
            if self.title_score < 80:
                recommendations.append("⚡ Optimize title: Add year/brand/expertise marker")
            
            if self.desc_score < 80:
                recommendations.append("⚡ Improve description: Add specific benefit/CTA")
            
            recommendations.extend(ai_recs[:3])
            return_val = 1
            
        else:
            google_verdict = "⚠️ Needs Optimization"
            optimization_level = 'Needs Improvement'
            verdict = False
            
            critical_issues = []
            
            if self.data.get('h1_count', 0) == 0:
                critical_issues.append("🚨 CRITICAL: Add H1 tag (essential for SEO)")
            elif self.data.get('h1_count', 0) > 1:
                critical_issues.append("🚨 CRITICAL: Remove extra H1 tags (use only ONE)")
            
            if self.data.get('title_length', 0) == 0:
                critical_issues.append("🚨 CRITICAL: Add page title")
            
            if self.data.get('desc_length', 0) == 0:
                critical_issues.append("🚨 CRITICAL: Add meta description")
            
            recommendations.extend(critical_issues)
            
            if not critical_issues:
                if self.title_score < 70:
                    recommendations.append("⚡ Fix title: Optimize length (50-60 chars) + add freshness")
                
                if self.desc_score < 70:
                    recommendations.append("⚡ Fix description: 150-160 chars + unique from title")
                
                if self.heading_score < 70:
                    recommendations.append("⚡ Fix heading: Ensure ONE H1 + proper hierarchy")
            
            if avg_eeat < 60:
                recommendations.append("🛡️ E-E-A-T CRITICAL: See AI analysis below for expertise signals")
                recommendations.append("💡 Add: Author attribution, dates, credentials, data/stats")
            
            recommendations.extend(ai_recs[:6])
            return_val = 0
        
        # Deduplicate recommendations
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)
        
        self.data.update({
            'avg_score': self.avg_score,
            'google_verdict': google_verdict,
            'optimization_level': optimization_level,
            'verdict': verdict,
            'recommendations': unique_recs[:10] if unique_recs else ['✅ No major issues - maintain optimization'],
            'mobile_optimized': (
                20 <= self.data.get('title_length', 0) <= 60 and
                120 <= self.data.get('desc_length', 0) <= 160
            ),
            'accessibility_ready': (
                self.data.get('h1_count') == 1 and
                self.data.get('heading_length', 0) > 0
            ),
            'title_score': self.title_score,
            'description_score': self.desc_score,
            'heading_score': self.heading_score,
            'Score_Calculation': f"Title: {self.title_score}/100, Description: {self.desc_score}/100, Heading: {self.heading_score}/100"
        })
        
        return return_val
    
    def get_grammar_analysis(self):
        """Delegate to GrammarAnalyzer service."""
        try:
            result = self._grammar_analyzer.analyze(self.soup)
            self.data.update(result)
            return result.get('grammar_score', 0)
        except Exception as e:
            logger.error(f"Grammar analysis failed: {e}")
            self.data.update({
                'grammar_verdict': 'Analysis failed',
                'grammar_score': 0,
                'spelling_errors': [],
                'grammar_issues': [f'Analysis error: {str(e)[:50]}'],
                'readability_score': 0,
                'grammar_recommendations': ['Retry analysis or check content']
            })
            return 0
    
    def Keyword_Density(self):
        """Analyze keyword density and frequency."""
        for script in self.soup(["script", "style", "noscript", "iframe"]):
            script.decompose()
        
        visible_text = self.soup.get_text(separator=' ', strip=True)
        
        if not visible_text or len(visible_text.strip()) < 50:
            self.data.update({
                'density_dict': {},
                'keyword_verdict': "Insufficient content for keyword analysis",
                'total_words': 0,
                'meaningful_words': 0,
                'unique_keywords': 0
            })
            return
        
        # Clean and tokenize
        text = re.sub(r'[^\w\s]', ' ', visible_text.lower())
        all_words = text.split()
        total_all_words = len(all_words)
        
        # Common stop words (expanded)
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one',
            'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old',
            'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'many', 'oil', 'sit', 'set',
            'that', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been',
            'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long',
            'make', 'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what', 'each', 'said'
        }
        
        # Filter words
        filtered_words = [w for w in all_words if w not in stop_words and not w.isdigit() and len(w) > 2]
        total_meaningful_words = len(filtered_words)
        
        # Count frequencies
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top 15 keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Build density_dict in the format template expects
        density_dict = {}
        for i, (word, count) in enumerate(sorted_words):
            density_percent = (count / total_all_words) * 100 if total_all_words > 0 else 0
            
            # Determine usage verdict
            if density_percent > 5.0:
                usage_verdict = "⚠️ Overused - Risk of keyword stuffing"
            elif density_percent >= 2.0:
                usage_verdict = "✓ Optimal - Good keyword prominence"
            elif density_percent >= 1.0:
                usage_verdict = "✓ Good - Natural usage"
            elif density_percent >= 0.5:
                usage_verdict = "⚠️ Low - Consider more prominence"
            else:
                usage_verdict = "Low - Minor relevance"
            
            density_dict[word] = {
                "count": count,
                "density": f"{density_percent:.2f}%",
                "usage": usage_verdict,
                "rank": i + 1
            }
        
        # Generate overall verdict
        if sorted_words:
            top_density = (sorted_words[0][1] / total_all_words) * 100
            if top_density > 5:
                verdict = f"⚠️ Possible keyword stuffing detected ({sorted_words[0][0]}: {top_density:.2f}%)"
            elif top_density > 2:
                verdict = f"✓ Good keyword density for '{sorted_words[0][0]}' ({top_density:.2f}%)"
            else:
                verdict = "✓ Keyword density looks natural"
        else:
            verdict = "⚠️ No meaningful keywords found"
        
        self.data.update({
            'density_dict': density_dict,
            'keyword_verdict': verdict,
            'total_words': total_all_words,
            'meaningful_words': total_meaningful_words,
            'unique_keywords': len(word_freq)
        })
    
    def get_missing_alt(self):
        """Check for images missing alt text."""
        images = self.soup.find_all('img')
        
        total_images = len(images)
        missing_alt = []
        images_with_alt = 0
        
        for img in images:
            src = img.get('src', img.get('data-src', 'no-src'))
            alt = img.get('alt')
            
            if alt is None or alt.strip() == '':
                missing_alt.append(src[:50])
            else:
                images_with_alt += 1
        
        self.alt_count = images_with_alt
        missing_count = len(missing_alt)
        
        if total_images == 0:
            alt_verdict = "No images found on page"
            self.Img_score = 100
        elif missing_count == 0:
            alt_verdict = f"✓ All {total_images} images have alt text"
            self.Img_score = 100
        elif missing_count <= 3:
            alt_verdict = f"⚠️ {missing_count} of {total_images} images missing alt text"
            self.Img_score = max(0, 100 - (missing_count * 10))
        else:
            alt_verdict = f"❌ {missing_count} of {total_images} images missing alt text"
            self.Img_score = max(0, 100 - (missing_count * 5))
        
        # Calculate optimization percentage
        image_optimization = round((images_with_alt / total_images) * 100) if total_images > 0 else 0
        
        self.data.update({
            'alt_verdict': alt_verdict,  # Template expects 'alt_verdict'
            'alt_check': missing_count,  # Template expects 'alt_check'
            'total_images': total_images,
            'images_with_alt': images_with_alt,
            'missing_alt_count': missing_count,
            'missing_alt_images': missing_alt[:10],
            'img_score': self.Img_score,
            'image_optimization': image_optimization  # Template expects this
        })
    
    def get_links(self):
        """Delegate to LinkService for link analysis."""
        try:
            result = self._link_service.analyze_links(self.soup)
            self.internal_links = result.get('Internal_links', 0)
            self.external_links = result.get('External_links', 0)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Link analysis failed: {e}")
            self.internal_links = 0
            self.external_links = 0
            self.data.update({
                'Internal_links': 0,
                'External_links': 0,
                'link_analysis_error': str(e)[:50]
            })
    
    def get_broken_links(self, max_workers: int = 10, timeout: int = 8):
        """Delegate to LinkService for broken link checking."""
        try:
            result = self._link_service.check_broken_links(self.soup, max_workers, timeout)
            self.b_links = result.get('b_links', 0)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Broken link check failed: {e}")
            self.b_links = 0
            self.data.update({
                'b_links': 0,
                'b_verdict': f'Link check failed: {str(e)[:50]}',
                'b_url': [],
                'broken_summary': {},
                'internal_broken': 0,
                'external_broken': 0,
                'working_links': 0,
                'link_health_score': 0
            })
    
    def check_robot_txt(self):
        """Delegate to TechnicalAuditService for robots.txt check."""
        try:
            result = self._tech_audit._robots.analyze()
            self.robot_flag = result.get('robot_flag', False)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Robots.txt check failed: {e}")
            self.robot_flag = False
            self.data.update({
                'robot_flag': False,
                'robot': '⚠️ Check failed - Unable to analyze robots.txt'
            })
    
    def get_sitemap(self):
        """Delegate to TechnicalAuditService for sitemap check."""
        try:
            result = self._tech_audit._sitemap.analyze()
            self.sitemap_flag = result.get('sitemap_flag', False)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Sitemap check failed: {e}")
            self.sitemap_flag = False
            self.data.update({
                'sitemap_flag': False,
                'sitemap': '⚠️ Check failed - Unable to analyze sitemap'
            })
    
    def get_schema(self):
        """Delegate to TechnicalAuditService for schema analysis."""
        try:
            result = self._tech_audit._schema.analyze(self.soup)
            self.schema_flag = result.get('schema_found', False)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Schema analysis failed: {e}")
            self.schema_flag = False
            self.data.update({
                'schema_flag': False,
                'schema': '⚠️ Analysis failed - Unable to check schema markup'
            })
    
    def get_Open_GP(self):
        """Delegate to TechnicalAuditService for Open Graph analysis."""
        try:
            result = self._tech_audit._og.analyze(self.soup)
            self.ogp_flag = result.get('ogp_flag', False)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Open Graph analysis failed: {e}")
            self.ogp_flag = False
            self.data.update({
                'ogp_flag': False,
                'open_gp': '⚠️ Analysis failed - Unable to check Open Graph tags'
            })
    
    def get_favicon(self):
        """Delegate to TechnicalAuditService for favicon analysis."""
        try:
            result = self._tech_audit._favicon.analyze(self.soup)
            self.icon_flag = result.get('icon_flag', False)
            self.data.update(result)
        except Exception as e:
            logger.error(f"Favicon check failed: {e}")
            self.icon_flag = False
            self.data.update({
                'icon_flag': False,
                'Favicon': '⚠️ Check failed - Unable to detect favicon'
            })
    
    def CSS_minification(self):
        """Delegate to MinificationService for CSS check."""
        try:
            result = self._minification_service.check_css()
            self.css = result.get('is_minified', False)
            self.data.update({
                'css_minified': result.get('minified', 'Unknown'),  # Service returns 'minified' not 'css_minified'
                'css': self.css,
                'inline_css_count': result.get('inline_count', 0),  # Service returns 'inline_count' not 'css_inline_count'
                'external_css_count': result.get('external_count', 0)  # Service returns 'external_count'
            })
        except Exception as e:
            logger.error(f"CSS minification check failed: {e}")
            self.css = False
            self.data.update({
                'css_minified': 'Check failed',
                'css': False,
                'inline_css_count': 0,
                'external_css_count': 0
            })
    
    def JSS_minification(self):
        """Delegate to MinificationService for JS check."""
        try:
            result = self._minification_service.check_js()
            self.jss = result.get('is_minified', False)
            self.data.update({
                'jss_minified': result.get('minified', 'Unknown'),  # Service returns 'minified' not 'js_minified'
                'js_minified': result.get('minified', 'Unknown'),
                'jss': self.jss,
                'inline_js_count': result.get('inline_count', 0),  # Service returns 'inline_count'
                'external_js_count': result.get('external_count', 0)  # Service returns 'external_count'
            })
        except Exception as e:
            logger.error(f"JS minification check failed: {e}")
            self.jss = False
            self.data.update({
                'jss_minified': 'Check failed',
                'js_minified': 'Check failed',
                'jss': False,
                'inline_js_count': 0,
                'external_js_count': 0
            })
    
    async def measure_website_speed(self):
        """Measure website speed and fetch Core Web Vitals via PageSpeed API."""
        try:
            start_time = asyncio.get_event_loop().time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url, 
                    headers={"User-Agent": "Mozilla/5.0"}, 
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    await response.text()
                    end_time = asyncio.get_event_loop().time()
                    self.speed = round(end_time - start_time, 2)

            self.data['website_speed'] = self.speed
            
            if self.speed < 1.0:
                self.data['speed_verdict'] = "Excellent! Server response time is very fast."
            elif self.speed < 2.5:
                self.data['speed_verdict'] = "Good! Server response time is acceptable."
            elif self.speed < 4.0:
                self.data['speed_verdict'] = "Fair. Server response could be improved."
            else:
                self.data['speed_verdict'] = "Poor. Server response time needs optimization."
                
        except Exception as e:
            self.speed = 0
            self.data['website_speed'] = 0
            self.data['speed_verdict'] = f"Error: {e}"

        # PageSpeed Insights API with retry logic
        API_KEY = getattr(settings, 'PAGESPEED_API_KEY', '')
        
        if not API_KEY:
            logger.warning("PAGESPEED_API_KEY not configured - Core Web Vitals unavailable")
            self.data['lcp'] = self.data['cls'] = self.data['inp'] = self.data['full_page_load'] = "No API Key"
            self.data['fcp'] = self.data['tti'] = self.data['tbt'] = "No API Key"
            self.data['performance_score'] = self.data['seo_score'] = 0
            self.data['vitals_assessment'] = "Configure PAGESPEED_API_KEY in settings"
            return
        
        psi_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={self.url}&strategy=mobile&key={API_KEY}"
        
        last_error = None
        psi_data = None
        
        for attempt in range(3):  # 3 retries with exponential backoff
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2, 4 seconds
                    logger.info(f"PageSpeed API retry {attempt}/3, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                
                def fetch_psi(url, attempt_num): 
                    # Increase timeout with each retry
                    timeout = 60 + (attempt_num * 30)  # 60s, 90s, 120s
                    response = requests.get(url, timeout=timeout)
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        raise requests.exceptions.HTTPError("Rate limited (429) - Too many requests")
                    
                    # Handle server errors (5xx) - these are transient
                    if response.status_code >= 500:
                        raise requests.exceptions.HTTPError(f"Server error ({response.status_code})")
                    
                    response.raise_for_status()
                    return response.json()
                
                psi_data = await asyncio.to_thread(fetch_psi, psi_url, attempt)
                break  # Success, exit retry loop
                
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout (attempt {attempt + 1})"
                logger.warning(f"PageSpeed API timeout on attempt {attempt + 1}")
                continue
            except requests.exceptions.HTTPError as e:
                last_error = str(e)
                error_msg = str(e).lower()
                if "rate limited" in error_msg and attempt < 2:
                    logger.warning(f"PageSpeed API rate limited, will retry...")
                    continue
                # Don't retry on client errors (4xx except 429)
                if any(code in error_msg for code in ['400', '401', '403', '404', 'client error']):
                    break
                continue
            except Exception as e:
                last_error = str(e)
                logger.warning(f"PageSpeed API error on attempt {attempt + 1}: {e}")
                continue
        
        # If all retries failed
        if psi_data is None:
            logger.error(f"PageSpeed API failed after 3 attempts: {last_error}")
            self.data['lcp'] = self.data['cls'] = self.data['inp'] = self.data['full_page_load'] = "API Failed"
            self.data['fcp'] = self.data['tti'] = self.data['tbt'] = "API Failed"
            self.data['performance_score'] = self.data['seo_score'] = 0
            self.data['vitals_assessment'] = f"PageSpeed API unavailable: {str(last_error)[:50]}"
            return
        
        # Process successful response
        try:
            audits = psi_data.get("lighthouseResult", {}).get("audits", {})
            
            performance_score = psi_data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0)
            self.data['performance_score'] = round(performance_score * 100) if performance_score else 0

            lcp_value = audits.get("largest-contentful-paint", {}).get("numericValue", 0)
            self.data['lcp'] = round(lcp_value / 1000, 2) if lcp_value else 0
            
            cls_value = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
            self.data['cls'] = round(cls_value, 3) if cls_value is not None else 0
            
            inp_val = audits.get("interaction-to-next-paint", {}).get("numericValue")
            self.data['inp'] = round(inp_val / 1000, 2) if inp_val else "N/A"
            
            speed_index = audits.get("speed-index", {}).get("numericValue", 0)
            self.data['full_page_load'] = round(speed_index / 1000, 2) if speed_index else 0
            
            fcp_value = audits.get("first-contentful-paint", {}).get("numericValue", 0)
            self.data['fcp'] = round(fcp_value / 1000, 2) if fcp_value else 0
            
            tti_value = audits.get("interactive", {}).get("numericValue", 0)
            self.data['tti'] = round(tti_value / 1000, 2) if tti_value else 0
            
            tbt_value = audits.get("total-blocking-time", {}).get("numericValue", 0)
            self.data['tbt'] = round(tbt_value, 2) if tbt_value else 0
            
            vitals_assessment = []
            
            if self.data['lcp'] > 0:
                if self.data['lcp'] <= 2.5:
                    vitals_assessment.append("LCP: Good ✓")
                elif self.data['lcp'] <= 4.0:
                    vitals_assessment.append("LCP: Needs Improvement ⚠")
                else:
                    vitals_assessment.append("LCP: Poor ✗")
            
            if self.data['cls'] >= 0:
                if self.data['cls'] <= 0.1:
                    vitals_assessment.append("CLS: Good ✓")
                elif self.data['cls'] <= 0.25:
                    vitals_assessment.append("CLS: Needs Improvement ⚠")
                else:
                    vitals_assessment.append("CLS: Poor ✗")
            
            if self.data['fcp'] > 0:
                if self.data['fcp'] <= 1.8:
                    vitals_assessment.append("FCP: Good ✓")
                elif self.data['fcp'] <= 3.0:
                    vitals_assessment.append("FCP: Needs Improvement ⚠")
                else:
                    vitals_assessment.append("FCP: Poor ✗")
            
            self.data['vitals_assessment'] = ", ".join(vitals_assessment) if vitals_assessment else "Unable to assess"
            
            seo_score = psi_data.get("lighthouseResult", {}).get("categories", {}).get("seo", {}).get("score", 0)
            self.data['seo_score'] = round(seo_score * 100) if seo_score else 0
            
            accessibility_score = psi_data.get("lighthouseResult", {}).get("categories", {}).get("accessibility", {}).get("score", 0)
            self.data['accessibility_score'] = round(accessibility_score * 100) if accessibility_score else 0
            
            best_practices_score = psi_data.get("lighthouseResult", {}).get("categories", {}).get("best-practices", {}).get("score", 0)
            self.data['best_practices_score'] = round(best_practices_score * 100) if best_practices_score else 0

        except Exception as e:
            logger.warning(f"PageSpeed API error: {e}")
            self.data['lcp'] = self.data['cls'] = self.data['inp'] = self.data['full_page_load'] = "Error"
            self.data['fcp'] = self.data['tti'] = self.data['tbt'] = "Error"
            self.data['performance_score'] = self.data['seo_score'] = 0

    async def Optmized_Plugins(self):
        """Detect performance optimization techniques on the page."""
        try:
            if not self.soup:
                self.data['opt_plugins'] = "Unable to analyze - no content"
                self.plugins = False
                return
                
            soup = self.soup
            
            preload_links = soup.find_all('link', {'rel': 'preload'})
            prefetch_links = soup.find_all('link', {'rel': 'prefetch'})
            preconnect_links = soup.find_all('link', {'rel': 'preconnect'})
            dns_prefetch_links = soup.find_all('link', {'rel': 'dns-prefetch'})
            
            optimization_count = 0
            optimizations_found = []
            
            if preload_links:
                optimization_count += len(preload_links)
                optimizations_found.append(f"Preload ({len(preload_links)})")
            
            if prefetch_links:
                optimization_count += len(prefetch_links)
                optimizations_found.append(f"Prefetch ({len(prefetch_links)})")
            
            if preconnect_links:
                optimization_count += len(preconnect_links)
                optimizations_found.append(f"Preconnect ({len(preconnect_links)})")
            
            if dns_prefetch_links:
                optimization_count += len(dns_prefetch_links)
                optimizations_found.append(f"DNS-Prefetch ({len(dns_prefetch_links)})")
            
            lazy_images = soup.find_all('img', {'loading': 'lazy'})
            if lazy_images:
                optimization_count += len(lazy_images)
                optimizations_found.append(f"Lazy Loading ({len(lazy_images)} images)")
            
            async_scripts = soup.find_all('script', {'async': True})
            defer_scripts = soup.find_all('script', {'defer': True})
            if async_scripts or defer_scripts:
                script_count = len(async_scripts) + len(defer_scripts)
                optimization_count += script_count
                optimizations_found.append(f"Async/Defer Scripts ({script_count})")
            
            self.data['optimization_techniques'] = ", ".join(optimizations_found) if optimizations_found else "None"
            self.data['optimization_count'] = optimization_count
            
            if optimization_count >= 5:
                self.data['opt_plugins'] = f"Excellent! Website uses {optimization_count} performance optimizations"
                self.plugins = True
            elif optimization_count >= 2:
                self.data['opt_plugins'] = f"Good. Website uses {optimization_count} optimizations"
                self.plugins = True
            elif optimization_count > 0:
                self.data['opt_plugins'] = f"Basic optimizations found: {', '.join(optimizations_found)}"
                self.plugins = False
            else:
                self.data['opt_plugins'] = "No resource optimization techniques detected."
                self.plugins = False
                
        except Exception as e:
            logger.warning(f"Error in Optmized_Plugins: {e}")
            self.data['opt_plugins'] = f"Error analyzing optimizations: {e}"
            self.plugins = False
    
    def get_Status(self):
        """Check HTTP status and availability."""
        statuses = {
            200: "Website Available",
            201: "Created",
            204: "No Content",
            301: "Permanent Redirect",
            302: "Temporary Redirect",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        
        try:
            status = self.status_code
            
            if status in statuses:
                status_text = statuses[status]
            elif status is None:
                status_text = "Unable to determine status"
            else:
                status_text = f"HTTP {status}"
            
            self.data.update({
                'status': status_text,
                'status_code': status or 0,
                'status_verdict': "✓ Page accessible" if status == 200 else f"⚠️ Status: {status_text}"
            })
            
        except Exception as e:
            self.data.update({
                'status': f"Error: {e}",
                'status_code': 0,
                'status_verdict': "⚠️ Status check failed"
            })
    
    def Score_Graph(self, name, tag, score):
        """Generate a Plotly pie chart for scores."""
        try:
            score = max(0, min(100, score))
            
            if name == 'Alt_Image':
                if score <= 50:
                    shape1, shape2 = 'rgba(0,0,0,0)', 'red'
                else:
                    shape1, shape2 = 'red', 'rgba(0,0,0,0)'
            else:
                if score <= 50:
                    shape1, shape2 = 'rgba(0,0,0,0)', 'red'
                else:
                    shape1, shape2 = 'green', 'rgba(0,0,0,0)'
            
            df = pd.DataFrame({'values': [100 - score, score]})
            
            fig = px.pie(
                df,
                values='values',
                hole=0.7,
                color_discrete_sequence=[shape1, shape2],
                title=name + ' Score',
                width=350,
                height=350
            )
            
            fig.update_traces(textinfo='none')
            fig.update_layout(
                showlegend=False,
                annotations=[dict(text=f'{score}%', x=0.5, y=0.5, font_size=20, showarrow=False)],
                margin=dict(t=50, b=30, l=30, r=30)
            )
            
            self.data[tag] = fig.to_html(full_html=False)
            
        except Exception as e:
            logger.error(f"Error generating score graph: {e}")
            self.data[tag] = f"<div>Error generating graph: {score}%</div>"
    
    def Social(self):
        """
        Comprehensive social media presence detection.
        Checks links, meta tags, scripts, and page text for social media indicators.
        """
        try:
            if not self.soup:
                raise ValueError("No HTML content to analyze")
            
            # Expanded social platform definitions with multiple indicators
            social_platforms = {
                "facebook": {
                    "urls": ["facebook.com/", "fb.com/", "m.facebook.com/", "www.facebook.com/"],
                    "meta_tags": ["og:facebook", "facebook-domain-verification", "fb:app_id", "fb:pages"],
                    "scripts": ["connect.facebook.net", "facebook.com/sdk", "fbq("],
                    "text_patterns": ["facebook.com/", "fb.me/", "@facebook"],
                    "icons": ["facebook", "fb-icon", "fb-logo"]
                },
                "instagram": {
                    "urls": ["instagram.com/", "www.instagram.com/", "instagr.am/"],
                    "meta_tags": ["og:instagram", "instagram:site"],
                    "scripts": ["instagram.com", "instafeed"],
                    "text_patterns": ["instagram.com/", "@instagram", "#instagram"],
                    "icons": ["instagram", "ig-icon", "ig-logo"]
                },
                "twitter": {
                    "urls": ["twitter.com/", "x.com/", "mobile.twitter.com/", "t.co/"],
                    "meta_tags": ["twitter:site", "twitter:creator", "twitter:card"],
                    "scripts": ["platform.twitter.com", "widgets.twimg.com", "twitter-wjs"],
                    "text_patterns": ["twitter.com/", "@", "#"],
                    "icons": ["twitter", "x-icon", "twitter-logo", "x-logo"]
                },
                "linkedin": {
                    "urls": ["linkedin.com/", "www.linkedin.com/", "mobile.linkedin.com/"],
                    "meta_tags": ["linkedin:owner", "og:linkedin"],
                    "scripts": ["platform.linkedin.com", "linkedin.com/in"],
                    "text_patterns": ["linkedin.com/in/", "linkedin.com/company/"],
                    "icons": ["linkedin", "li-icon", "linkedin-logo"]
                },
                "youtube": {
                    "urls": ["youtube.com/", "youtu.be/", "www.youtube.com/", "m.youtube.com/"],
                    "meta_tags": ["og:youtube", "youtube:channel"],
                    "scripts": ["youtube.com/embed", "youtube.com/iframe_api"],
                    "text_patterns": ["youtube.com/channel/", "youtube.com/c/", "youtube.com/user/", "youtu.be/"],
                    "icons": ["youtube", "yt-icon", "youtube-logo"]
                },
                "pinterest": {
                    "urls": ["pinterest.com/", "www.pinterest.com/", "pin.it/"],
                    "meta_tags": ["pinterest", "og:pinterest"],
                    "scripts": ["assets.pinterest.com", "pinit.js"],
                    "text_patterns": ["pinterest.com/", "pin.it/"],
                    "icons": ["pinterest", "pin-icon", "pinterest-logo"]
                },
                "tiktok": {
                    "urls": ["tiktok.com/", "www.tiktok.com/", "vm.tiktok.com/"],
                    "meta_tags": ["tiktok", "og:tiktok"],
                    "scripts": ["tiktok.com", "tiktok-embed"],
                    "text_patterns": ["tiktok.com/@"],
                    "icons": ["tiktok", "tiktok-logo"]
                },
                "snapchat": {
                    "urls": ["snapchat.com/", "www.snapchat.com/"],
                    "meta_tags": ["snapchat"],
                    "scripts": ["snapchat.com", "sc-pixel"],
                    "text_patterns": ["snapchat.com/add/"],
                    "icons": ["snapchat", "snap-logo"]
                },
                "reddit": {
                    "urls": ["reddit.com/", "www.reddit.com/", "redd.it/"],
                    "meta_tags": ["reddit"],
                    "scripts": ["reddit.com", "reddit-embed"],
                    "text_patterns": ["reddit.com/r/", "reddit.com/u/", "redd.it/"],
                    "icons": ["reddit", "reddit-logo"]
                }
            }
            
            found_links = {platform: None for platform in social_platforms}
            evidence_types = {platform: [] for platform in social_platforms}  # Track how we found it
            self.s_count = 0
            
            # Get all page text for pattern matching
            page_text = str(self.soup).lower()
            visible_text = self.soup.get_text(separator=' ', strip=True).lower() if self.soup else ""
            
            # 1. CHECK EXTERNAL LINKS (original method)
            for link in self.soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                for platform, indicators in social_platforms.items():
                    if any(url in href for url in indicators["urls"]):
                        if not found_links[platform]:
                            found_links[platform] = href
                            evidence_types[platform].append("link")
                            self.s_count += 15
            
            # 2. CHECK META TAGS
            for meta in self.soup.find_all('meta'):
                content = (meta.get('content', '') + ' ' + meta.get('name', '') + ' ' + meta.get('property', '')).lower()
                for platform, indicators in social_platforms.items():
                    if any(tag.lower() in content for tag in indicators["meta_tags"]):
                        if platform not in evidence_types[platform] or not found_links[platform]:
                            if not found_links[platform]:
                                found_links[platform] = f"Meta tag: {meta.get('content', 'Found')}"
                            evidence_types[platform].append("meta_tag")
                            self.s_count += 10
            
            # 3. CHECK SCRIPT SOURCES
            for script in self.soup.find_all('script', src=True):
                src = script.get('src', '').lower()
                for platform, indicators in social_platforms.items():
                    if any(script_ind in src for script_ind in indicators["scripts"]):
                        if not found_links[platform]:
                            found_links[platform] = f"Script: {src[:50]}"
                        evidence_types[platform].append("script")
                        self.s_count += 10
            
            # 4. CHECK IFRAME SOURCES (embedded social feeds)
            for iframe in self.soup.find_all('iframe', src=True):
                src = iframe.get('src', '').lower()
                for platform, indicators in social_platforms.items():
                    if any(url in src for url in indicators["urls"]):
                        if not found_links[platform]:
                            found_links[platform] = f"Embed: {src[:50]}"
                        evidence_types[platform].append("embed")
                        self.s_count += 15
            
            # 5. CHECK IMAGE ALT TEXT AND TITLES (social icons)
            for img in self.soup.find_all(['img', 'svg', 'i']):
                alt_text = (img.get('alt', '') + ' ' + img.get('title', '') + ' ' + str(img.get('class', ''))).lower()
                for platform, indicators in social_platforms.items():
                    if any(icon in alt_text for icon in indicators["icons"]):
                        # Check if parent is a link to the platform
                        parent = img.find_parent('a', href=True)
                        if parent:
                            href = parent.get('href', '').lower()
                            if any(url in href for url in indicators["urls"]):
                                if not found_links[platform]:
                                    found_links[platform] = href
                                evidence_types[platform].append("icon")
                                self.s_count += 5
            
            # 6. CHECK PAGE TEXT FOR SOCIAL MENTIONS
            for platform, indicators in social_platforms.items():
                if found_links[platform]:  # Skip if already found via link
                    continue
                    
                # Look for text patterns in visible text
                for pattern in indicators["text_patterns"]:
                    if pattern.lower() in visible_text:
                        found_links[platform] = f"Mentioned in text (pattern: {pattern})"
                        evidence_types[platform].append("text_mention")
                        self.s_count += 5
                        break
            
            # 7. CHECK FOOTER AND CONTACT SECTIONS (common location for social links)
            footer = self.soup.find(['footer', 'div'], class_=lambda x: x and ('footer' in x.lower() if x else False))
            if footer:
                for link in footer.find_all('a', href=True):
                    href = link.get('href', '').lower()
                    for platform, indicators in social_platforms.items():
                        if any(url in href for url in indicators["urls"]):
                            if not found_links[platform]:
                                found_links[platform] = href
                                evidence_types[platform].append("footer_link")
                                self.s_count += 15
            
            self.s_count = min(100, self.s_count)
            
            # Set individual platform flags for template compatibility
            self.facebook_flag = bool(found_links.get('facebook'))
            self.instagram_flag = bool(found_links.get('instagram'))
            self.twitter_flag = bool(found_links.get('twitter'))
            self.linkedin_flag = bool(found_links.get('linkedin'))
            
            # Generate detailed verdict
            found_count = sum(1 for v in found_links.values() if v)
            if found_count == 0:
                verdict = "No social media presence detected"
            elif found_count == 1:
                verdict = f"1 social platform found (Score: {self.s_count}%)"
            else:
                verdict = f"{found_count} social platforms found (Score: {self.s_count}%)"
            
            self.data.update({
                "social_links": found_links,
                "social_accounts_found": found_count,
                "social_verdict": verdict,
                "social_score": self.s_count,
                "facebook_flag": self.facebook_flag,
                "instagram_flag": self.instagram_flag,
                "twitter_flag": self.twitter_flag,
                "linkedin_flag": self.linkedin_flag,
                "social_evidence": evidence_types  # New: how we found each platform
            })
            
        except Exception as e:
            logger.error(f"Social media detection failed: {e}")
            self.facebook_flag = False
            self.instagram_flag = False
            self.twitter_flag = False
            self.linkedin_flag = False
            self.s_count = 0
            self.data.update({
                "social_links": {},
                "social_accounts_found": 0,
                "social_verdict": "Social media check failed",
                "social_score": 0,
                "facebook_flag": False,
                "instagram_flag": False,
                "twitter_flag": False,
                "linkedin_flag": False
            })
    
    def get_technology(self):
        """Detect technologies used on the site."""
        try:
            technologies = []
            
            # Check server header
            server = self.response_headers.get('Server', '')
            if server:
                technologies.append(f"Server: {server}")
            
            # Check X-Powered-By
            powered_by = self.response_headers.get('X-Powered-By', '')
            if powered_by:
                technologies.append(f"Powered by: {powered_by}")
            
            # Check for common technologies in HTML
            html_text = str(self.soup).lower() if self.soup else ''
            
            tech_indicators = {
                'WordPress': 'wp-content' in html_text or 'wordpress' in html_text,
                'Shopify': 'shopify' in html_text or 'myshopify' in html_text,
                'Wix': 'wix' in html_text,
                'Squarespace': 'squarespace' in html_text,
                'Drupal': 'drupal' in html_text,
                'Joomla': 'joomla' in html_text,
                'React': 'react' in html_text or 'data-reactroot' in html_text,
                'Vue.js': 'vue' in html_text,
                'Angular': 'ng-' in html_text,
                'jQuery': 'jquery' in html_text,
                'Bootstrap': 'bootstrap' in html_text,
                'Google Analytics': 'google-analytics' in html_text or 'gtag' in html_text,
                'Google Tag Manager': 'gtm-' in html_text or 'googletagmanager' in html_text,
                'Facebook Pixel': 'facebook-pixel' in html_text or 'fbevents' in html_text,
                'Hotjar': 'hotjar' in html_text
            }
            
            detected = [tech for tech, found in tech_indicators.items() if found]
            
            self.tech_flag = len(detected) > 0
            
            self.data.update({
                'detected_technologies': detected,
                'server_software': server or 'Unknown',
                'tech_count': len(detected),
                'tech_flag': self.tech_flag
            })
        except Exception as e:
            logger.error(f"Technology detection failed: {e}")
            self.tech_flag = False
            self.data.update({
                'detected_technologies': [],
                'server_software': 'Unknown',
                'tech_count': 0,
                'tech_flag': False
            })
    
    def Google_Analytics(self):
        """Check for Google Analytics or Tag Manager."""
        html_text = str(self.soup).lower()
        
        has_ga = 'google-analytics' in html_text or 'gtag' in html_text or 'ga(' in html_text
        has_gtm = 'googletagmanager' in html_text or 'gtm-' in html_text
        
        if has_ga and has_gtm:
            verdict = "✓ Found - Google Analytics + Tag Manager detected"
        elif has_ga:
            verdict = "✓ Found - Google Analytics detected"
        elif has_gtm:
            verdict = "✓ Found - Google Tag Manager detected"
        else:
            verdict = "⚠️ Not Found - Consider adding analytics tracking"
        
        self.data.update({
            'analytics': verdict,
            'has_google_analytics': has_ga,
            'has_google_tag_manager': has_gtm
        })
        self.analytics_flag = has_ga or has_gtm
    
    def w3c_validation(self):
        """Basic HTML validation checks."""
        try:
            issues = []
            
            if not self.soup:
                raise ValueError("No HTML content to validate")
            
            # Check for doctype
            doctype = self.soup.contents[0] if self.soup.contents else None
            has_doctype = isinstance(doctype, str) and 'doctype' in doctype.lower()
            
            if not has_doctype:
                issues.append("Missing DOCTYPE declaration")
            
            # Check for charset
            charset_meta = self.soup.find('meta', charset=True)
            content_type_meta = self.soup.find('meta', {'http-equiv': 'Content-Type'})
            has_charset = bool(charset_meta or content_type_meta)
            
            if not has_charset:
                issues.append("Missing charset declaration")
            
            # Check for viewport
            viewport = self.soup.find('meta', attrs={'name': 'viewport'})
            if not viewport:
                issues.append("Missing viewport meta tag (needed for mobile)")
            
            # Check for lang attribute
            html_tag = self.soup.find('html')
            has_lang = html_tag and html_tag.get('lang')
            if not has_lang:
                issues.append("Missing lang attribute on <html> tag")
            
            if not issues:
                verdict = "✓ Basic HTML structure looks good"
            else:
                verdict = f"⚠️ {len(issues)} HTML structure issue(s) found"
            
            # Get actual doctype and encoding values for display
            doctype_value = "HTML5" if has_doctype else "Not Found!"
            
            encoding_value = "UTF-8"  # default assumption
            if charset_meta:
                encoding_value = charset_meta.get('charset', 'UTF-8')
            elif content_type_meta:
                content = content_type_meta.get('content', '')
                if 'charset=' in content:
                    encoding_value = content.split('charset=')[-1].split(';')[0].strip()
            
            self.data.update({
                'w3c': verdict,
                'doctype': doctype_value,
                'encoding': encoding_value,
                'html_validation': verdict,
                'html_issues': issues,
                'has_doctype': has_doctype,
                'has_charset': has_charset,
                'has_viewport': bool(viewport),
                'has_lang': bool(has_lang)
            })
            
            # Set instance variables for get_data defaults
            self.Doctype = doctype_value
            self.Encoding = encoding_value
            self.doc_flag = has_doctype
            self.encod_flag = has_charset
            self.error_len = len(issues)
            
        except Exception as e:
            logger.error(f"W3C validation failed: {e}")
            self.Doctype = "HTML5"
            self.Encoding = "UTF-8"
            self.doc_flag = True  # Assume HTML5
            self.encod_flag = True  # Assume UTF-8
            self.error_len = 0
            self.data.update({
                'w3c': "✓ Basic HTML structure (assumed)",
                'doctype': "HTML5",
                'encoding': "UTF-8",
                'html_validation': "✓ Basic HTML structure (assumed)",
                'html_issues': [],
                'has_doctype': True,
                'has_charset': True,
                'has_viewport': True,
                'has_lang': True
            })
    
    def get_content(self):
        """Analyze page content."""
        try:
            if not self.soup:
                raise ValueError("No HTML content to analyze")
                
            for script in self.soup(["script", "style", "noscript"]):
                script.decompose()
            
            text = self.soup.get_text(separator=' ', strip=True)
            words = text.split()
            word_count = len(words)
            
            # Estimate reading time (average 200 wpm)
            reading_time = max(1, round(word_count / 200))
            
            self.data.update({
                'word_count': word_count,
                'reading_time': reading_time,
                'content_length': 'Short' if word_count < 300 else ('Medium' if word_count < 1000 else 'Long')
            })
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            self.data.update({
                'word_count': 0,
                'reading_time': 0,
                'content_length': 'Unknown'
            })
    
    def get_server(self):
        """Get server information."""
        try:
            server = self.response_headers.get('Server', 'Unknown')
            self.data['server'] = server
            self.webserver = server
            
            # Try to get IP and location
            try:
                ip = socket.gethostbyname(self.domain)
                self.ip = ip
                self.data['ip'] = ip
                self.ip_flag = True
                
                # Get hostname
                try:
                    hostname = socket.getfqdn(self.domain)
                except Exception:
                    hostname = "Not Found!"
                
                # Geolocation
                g = geocoder.ip(ip)
                if g.ok:
                    location = g.city or g.country or 'Unknown'
                    self.loc_name = location
                    self.server_loc_flag = True
                else:
                    self.loc_name = 'Unknown'
                    self.server_loc_flag = False
                
                # Set template-compatible keys
                self.data['s_ip'] = ip
                self.data['s_loc'] = self.loc_name
                self.data['hostname'] = hostname
                    
            except Exception:
                self.ip = 'Unknown'
                self.ip_flag = False
                self.loc_name = 'Unknown'
                self.server_loc_flag = False
                self.data['ip'] = 'Unknown'
                self.data['s_ip'] = 'Unknown'
                self.data['s_loc'] = 'Unknown'
                self.data['hostname'] = 'Unknown'
                
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            self.data['server'] = 'Unknown'
            self.webserver = 'Unknown'
    
    def SSL(self):
        """Check SSL/HTTPS status and fetch certificate details with retry logic."""
        import ssl as ssl_module
        import datetime
        import time as time_module
        
        url = self.url.replace("https://", "").replace("http://", "")
        host = url.split("/")[0].split("?")[0].strip()

        # Initialize defaults
        self.data['ssl_name'] = "Not Found!"
        self.data['ssl_verdict'] = "Website doesn't have a valid SSL!"
        self.data['ssl_organ'] = "Not Found!"
        self.data['ssl_expiry'] = "Not Found!"
        self.data['http_redir'] = "Not checked"
        self.ssl = False

        # Check HTTP → HTTPS redirection
        try:
            test_urls = [f"http://{host}", f"http://www.{host}"]

            for test_url in test_urls:
                try:
                    r = requests.get(test_url, timeout=5, allow_redirects=True)
                    if r.url.startswith("https://"):
                        self.data['http_redir'] = f"Yes, HTTP → HTTPS redirection is enabled ✔"
                        break
                except requests.exceptions.SSLError:
                    self.data['http_redir'] = f"Yes, HTTPS enforced (SSL error on HTTP access) ✔"
                    break
                except requests.RequestException:
                    continue
            else:
                self.data['http_redir'] = "No, website does NOT redirect to HTTPS ❌"

        except Exception:
            self.data['http_redir'] = "Could not check redirection"

        # Fetch SSL certificate details with retry
        last_error = None
        for attempt in range(3):  # 3 retries
            try:
                if attempt > 0:
                    time_module.sleep(1)  # Wait 1 second between retries
                
                context = ssl_module.create_default_context()
                # Increased timeout for slow servers
                conn = socket.create_connection((host, 443), timeout=8)
                sock = context.wrap_socket(conn, server_hostname=host)
                cert = sock.getpeercert()

                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))

                cn = subject.get("commonName")
                issuer_cn = issuer.get("commonName")
                issuer_org = issuer.get("organizationName", issuer_cn)
                expiry = cert.get("notAfter")
                
                try:
                    expires = datetime.datetime.strptime(expiry, "%b %d %H:%M:%S %Y %Z")
                except ValueError:
                    try:
                        expires = datetime.datetime.strptime(expiry, "%b %d %H:%M:%S %Y")
                    except ValueError:
                        expires = datetime.datetime.utcnow() + datetime.timedelta(days=365)
                
                days_left = (expires - datetime.datetime.utcnow()).days

                self.data['ssl_name'] = cn or "Not Found!"
                self.data['ssl_organ'] = issuer_org or "Not Found!"
                self.data['ssl_expiry'] = expiry

                if days_left < 0:
                    self.data['ssl_verdict'] = "SSL certificate is EXPIRED!"
                    self.ssl = False
                elif days_left < 15:
                    self.data['ssl_verdict'] = f"SSL expiring soon! ({days_left} days left)"
                    self.ssl = True
                else:
                    if self.data.get('ssl_name') != "Not Found!" and self.data.get('ssl_organ') != "Not Found!":
                        self.data['ssl_verdict'] = "SSL certificate is valid!"
                        self.ssl = True
                    else:
                        self.data['ssl_verdict'] = "SSL not found or invalid."
                        self.ssl = False

                sock.close()
                break  # Success, exit retry loop
                
            except ssl_module.CertificateError as e:
                last_error = e
                if attempt == 2:  # Last attempt
                    self.data['ssl_verdict'] = "Hostname mismatch (Invalid SSL)"
                    self.ssl = False
                continue
            except ssl_module.SSLError as e:
                last_error = e
                if attempt == 2:  # Last attempt
                    self.data['ssl_verdict'] = "SSL Handshake error (Invalid or broken SSL)"
                    self.ssl = False
                continue
            except Exception as e:
                last_error = e
                if attempt == 2:  # Last attempt
                    logger.warning(f"SSL check failed after 3 attempts: {e}")
                    self.data['ssl_verdict'] = "SSL Error - Could not retrieve certificate"
                    self.ssl = False
                continue

        # Set overall SSL status
        is_https = self.url.startswith('https://')
        self.data.update({
            'ssl': self.data['ssl_verdict'],
            'is_https': is_https,
            'ssl_enabled': self.ssl
        })
        self.https = is_https
    
    def DMCA(self):
        """Check for DMCA protection badge."""
        page_text = str(self.soup).lower()
        
        dmca_indicators = ['dmca', 'dmca.com', 'copyright', 'all rights reserved']
        has_dmca = any(indicator in page_text for indicator in dmca_indicators)
        
        self.data.update({
            'dmca': 'Found' if has_dmca else 'Not detected',
            'has_dmca_badge': has_dmca
        })
        
        self.dmca = has_dmca
    
    def Report(self, dict_data, output_dir=None, use_comprehensive=True):
        """
        Generate and optionally send comprehensive SEO report.
        
        Args:
            dict_data: Audit data dictionary (from cached show() view)
            output_dir: Directory to save PDF
            use_comprehensive: Whether to use new comprehensive analysis (default: True)
        
        Returns:
            dict: Report generation result
        """
        try:
            current_user_email = self._get_user_email(dict_data)
            url = dict_data.get('url', '')
            
            sender_email = os.getenv('SENDER_EMAIL', '')
            sender_password = os.getenv('SENDER_PASSWORD', '')
            
            if output_dir is None:
                try:
                    output_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
                except:
                    output_dir = os.path.join(os.getcwd(), 'reports')
            
            send_email = bool(current_user_email)
            
            # Use comprehensive report data if enabled
            if use_comprehensive and url:
                logger.info(f"Generating comprehensive report for: {url}")
                
                # Get comprehensive data (SEO metrics + keyword_ai)
                comprehensive_data = generate_comprehensive_report_data(
                    url=url,
                    request=self.request,
                    use_cache=True,
                    force_refresh=False
                )
                
                # Check if we got valid data from orchestrator
                if 'error' not in comprehensive_data or comprehensive_data.get('analysis_sources'):
                    # Merge: Use the SAME audit data (dict_data) + comprehensive metrics
                    # This ensures consistency between page display and PDF
                    report_data = comprehensive_data.copy()
                    report_data['seo'] = dict_data  # Use EXACT data from page
                    
                    # Also copy legacy fields that PDF expects at root level
                    report_data['url'] = dict_data.get('url', url)
                    report_data['title'] = dict_data.get('title', '')
                    report_data['desc'] = dict_data.get('desc', '')
                    report_data['title_score'] = dict_data.get('title_score', 0)
                    report_data['desc_score'] = dict_data.get('desc_score', 0)
                    report_data['H'] = dict_data.get('H', 'None')
                    report_data['heading_score'] = dict_data.get('heading_score', 0)
                    report_data['speed'] = dict_data.get('speed', 0)
                    report_data['internal_links'] = dict_data.get('internal_links', 0)
                    report_data['external_links'] = dict_data.get('external_links', 0)
                    report_data['b_links'] = dict_data.get('b_links', 0)
                    report_data['alt_count'] = dict_data.get('alt_count', 0)
                    report_data['lst'] = dict_data.get('lst', [])
                    report_data['dens'] = dict_data.get('dens', [])
                    report_data['robot_flag'] = dict_data.get('robot_flag', False)
                    report_data['sitemap_flag'] = dict_data.get('sitemap_flag', False)
                    report_data['schema_flag'] = dict_data.get('schema_flag', False)
                    report_data['ogp_flag'] = dict_data.get('ogp_flag', False)
                    report_data['icon_flag'] = dict_data.get('icon_flag', False)
                    report_data['analytics_flag'] = dict_data.get('analytics_flag', False)
                    report_data['https'] = dict_data.get('https', False)
                    report_data['dmca'] = dict_data.get('dmca', False)
                    report_data['ssl_name'] = dict_data.get('ssl_name', '')
                    report_data['ssl_expiry'] = dict_data.get('ssl_expiry', '')
                    report_data['ip'] = dict_data.get('ip', '')
                    report_data['loc_name'] = dict_data.get('loc_name', '')
                    report_data['webserver'] = dict_data.get('webserver', '')
                    report_data['error_len'] = dict_data.get('error_len', 0)
                    report_data['warn_len'] = dict_data.get('warn_len', 0)
                    report_data['mob_score'] = dict_data.get('mob_score', 0)
                    report_data['amp'] = dict_data.get('amp', False)
                    report_data['render'] = dict_data.get('render', False)
                    report_data['s_count'] = dict_data.get('s_count', 0)
                    report_data['facebook_flag'] = dict_data.get('facebook_flag', False)
                    report_data['instagram_flag'] = dict_data.get('instagram_flag', False)
                    report_data['twitter_flag'] = dict_data.get('twitter_flag', False)
                    report_data['linkedin_flag'] = dict_data.get('linkedin_flag', False)
                    
                    report_data['from_cache'] = comprehensive_data.get('from_cache', False)
                    logger.info(f"Using merged report data (comprehensive metrics + cached audit)")
                else:
                    # Fallback to legacy data
                    logger.warning(f"Comprehensive analysis failed, using legacy data: {comprehensive_data.get('error')}")
                    report_data = dict_data
            else:
                report_data = dict_data
            
            result = generate_seo_report(
                data_dict=report_data,
                user_email=current_user_email,
                sender_email=sender_email,
                sender_password=sender_password,
                output_dir=output_dir,
                send_email=send_email
            )
            
            # Add metadata about comprehensive analysis
            if use_comprehensive:
                result['comprehensive_analysis'] = True
                result['from_cache'] = report_data.get('from_cache', False)
            
            return result
            
        except Exception as e:
            error_msg = f"Error in Report method: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'pdf_path': None,
                'email_sent': False,
                'message': error_msg
            }
    
    def _get_user_email(self, data_dict):
        """Get user email from request or data dict."""
        try:
            if self.request and hasattr(self.request, 'user') and self.request.user.is_authenticated:
                email = self.request.user.email
                if email:
                    return email
        except Exception as e:
            logger.debug(f"Could not get email from request.user: {e}")
        
        email = data_dict.get('user_email')
        if email:
            return email
        
        return None
    
    def get_data(self):
        """Run all audit methods and collect data."""
        # Core SEO checks
        self.get_title()
        self.get_description()
        self.get_Heading()
        self.get_Google_preview()
        self.get_grammar_analysis()
        self.Keyword_Density()
        self.get_missing_alt()
        self.get_Status()
        
        # Link analysis
        self.get_links()
        self.check_robot_txt()
        self.get_sitemap()
        self.get_broken_links()
        
        # Technical SEO
        self.get_schema()
        self.get_Open_GP()
        self.get_favicon()
        self.Social()
        self.get_technology()
        self.Google_Analytics()
        self.w3c_validation()
        self.get_content()
        self.get_server()
        self.SSL()
        self.DMCA()
        
        # Performance
        self.CSS_minification()
        self.JSS_minification()
        
        # Async performance checks
        async def analyze_and_get_results():
            coroutines = [
                self.measure_website_speed(),
                self.Optmized_Plugins(),
            ]
            await asyncio.gather(*coroutines)
        
        try:
            asyncio.run(analyze_and_get_results())
        except Exception as e:
            logger.warning(f"Async performance checks failed: {e}")
        
        # Store URL info
        self.data.update({
            'url': self.url,
            'base_url': self.base_url,
            'domain': self.domain,
            'final_url': self.final_url,
            'user_email': self.user_email
        })
        
        # Mirror all instance attributes into self.data for template compatibility
        self.data.setdefault('title', self.title)
        self.data.setdefault('title_score', self.title_score)
        self.data.setdefault('desc_score', self.desc_score)
        self.data.setdefault('H', self.H)
        self.data.setdefault('heading_score', self.heading_score)
        self.data.setdefault('alt_count', self.alt_count)
        self.data.setdefault('external_links', self.external_links)
        self.data.setdefault('internal_links', self.internal_links)
        self.data.setdefault('robot_flag', self.robot_flag)
        self.data.setdefault('sitemap_flag', self.sitemap_flag)
        self.data.setdefault('b_links', self.b_links)
        self.data.setdefault('icon_flag', self.icon_flag)
        self.data.setdefault('ogp_flag', self.ogp_flag)
        self.data.setdefault('tech_flag', self.tech_flag)
        # Technology stack - format for template or provide defaults
        tech_list = self.data.get('detected_technologies', [])
        if tech_list:
            tech_str = ', '.join(tech_list[:5])
            if len(tech_list) > 5:
                tech_str += f' (+{len(tech_list) - 5} more)'
            self.data.setdefault('technology', tech_str)
        else:
            self.data.setdefault('technology', self.data.get('server_software', 'Unknown'))
        self.data.setdefault('detected_technologies', [])
        self.data.setdefault('server_software', 'Unknown')
        self.data.setdefault('tech_count', 0)
        self.data.setdefault('analytics_flag', self.analytics_flag)
        self.data.setdefault('analytics', self.data.get('analytics', 'Not Found'))
        self.data.setdefault('doc_flag', self.doc_flag)
        self.data.setdefault('doctype', self.Doctype or 'HTML5')  # Template expects lowercase 'doctype'
        self.data.setdefault('Doctype', self.Doctype or 'HTML5')
        self.data.setdefault('encoding', self.Encoding or 'UTF-8')  # Template expects lowercase 'encoding'
        self.data.setdefault('Encoding', self.Encoding or 'UTF-8')
        self.data.setdefault('dmca', self.dmca)
        self.data.setdefault('https', self.https)
        self.data.setdefault('facebook_flag', self.facebook_flag)
        self.data.setdefault('instagram_flag', self.instagram_flag)
        self.data.setdefault('twitter_flag', self.twitter_flag)
        self.data.setdefault('linkedin_flag', self.linkedin_flag)
        self.data.setdefault('speed', self.speed)
        self.data.setdefault('css', self.css)
        self.data.setdefault('jss', self.jss)
        self.data.setdefault('mob_score', self.mob_score)
        self.data.setdefault('amp', self.amp)
        self.data.setdefault('render', self.render)
        self.data.setdefault('desc', self.desc)
        self.data.setdefault('heading', self.heading)
        self.data.setdefault('comp_desc', self.comp_desc)
        self.data.setdefault('lst', self.lst)
        self.data.setdefault('comp_head', self.comp_head)
        self.data.setdefault('conversion', self.conversion)
        self.data.setdefault('schema_flag', self.schema_flag)
        self.data.setdefault('s_count', self.s_count)
        self.data.setdefault('ip_flag', self.ip_flag)
        self.data.setdefault('ip', self.ip)
        self.data.setdefault('server_loc_flag', self.server_loc_flag)
        self.data.setdefault('loc_name', self.loc_name)
        self.data.setdefault('webserver', self.webserver)
        self.data.setdefault('error_len', self.error_len)
        self.data.setdefault('warn_len', self.warn_len)
        self.data.setdefault('encod_flag', self.encod_flag)
        self.data.setdefault('plugins', self.plugins)
        self.data.setdefault('mobpreview', self.mobpreview)
        self.data.setdefault('ssl', self.ssl)
        self.data.setdefault('ssl_name', self.data.get('ssl_name', 'Not Found!'))
        self.data.setdefault('ssl_organ', self.data.get('ssl_organ', 'Not Found!'))
        self.data.setdefault('ssl_expiry', self.data.get('ssl_expiry', 'Not Found!'))
        # Server IP - use self.ip (set by get_server) not self.data.get('ip')
        self.data.setdefault('ip', self.ip or 'Unknown')
        self.data.setdefault('s_ip', self.ip or 'Unknown')  # Template uses s_ip
        self.data.setdefault('s_loc', self.loc_name or 'Unknown')  # Template uses s_loc
        self.data.setdefault('hostname', self.data.get('hostname', 'Unknown'))
        
        return self.data


# Import view functions from views_pages module
from .views_pages import (
    sentiment_analysis_page,
    analyze_sentiment_view,
    upload,
    Report,
    download_report,
    index,
    show,
    seo_metrics,
    mobiletest,
    robot,
    keyPosition,
    keysuggestion,
    keyword_ai_suggestions,
    loginuser,
    register,
    logoutuser,
    ChangePassword,
    ForgetPassword,
)

# Also export the add_to_dictionary view from grammar_analyzer
add_to_dictionary = add_to_dictionary_view
