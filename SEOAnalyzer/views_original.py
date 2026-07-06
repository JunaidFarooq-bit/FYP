from keyword_ai.pipeline_v2 import run_keyword_pipeline_v2
import logging

logger = logging.getLogger(__name__)
# ================================
# DJANGO CORE IMPORTS
# ================================
from .services.sentiment_analyzer import analyze_sentiment

from django.contrib.auth.models import User                 # Django built-in User model
from django.contrib.auth import authenticate, login, logout # Authentication utilities
from django.contrib.auth.decorators import login_required   # Protect views with login
from django.db import IntegrityError, DatabaseError          # Database exceptions
from django.shortcuts import render, redirect, reverse      # Rendering and redirects
from django.http import JsonResponse                        # HTTP responses
from django.views.decorators.cache import never_cache       # Disable caching for views
from django.views.decorators.http import require_POST       # Restrict HTTP methods
from django.contrib import messages                         # Flash messages

# ================================
# PROJECT / APP SPECIFIC IMPORTS
# ================================

from .models import Profile                                 # User profile model
from .helpers import send_forget_password_mail               # Password reset email
from .modern_report import generate_seo_report               # SEO report generator

# ================================
# ASYNC & NETWORKING
# ================================

import asyncio                                              # Async operations
import aiohttp                                              # Async HTTP requests
import ssl                                                  # SSL/TLS handling
import socket                                               # Network socket info

# ================================
# WEB SCRAPING & URL HANDLING
# ================================

import requests                                             # HTTP requests
from urllib.parse import urlparse, urljoin, urlunparse, quote  # URL parsing utilities
from bs4 import BeautifulSoup                                # HTML parsing
import validators                                           # URL validation


# ================================
# SEO / WEBSITE ANALYSIS TOOLS
# ================================

import favicon                                              # Website favicon detection
from py_w3c.validators.html.validator import HTMLValidator   # W3C HTML validation

# ================================
# DATA ANALYSIS & VISUALIZATION
# ================================

import pandas as pd                                         # Data analysis
import plotly.express as px                                 # Interactive charts


# ================================
# GEO / LOCATION / COUNTRY INFO
# ================================

import geocoder                                             # IP-based geolocation

# ================================
# CODE OPTIMIZATION
# ================================

import csscompressor                                        # Minify CSS
from jsmin import jsmin                                     # Minify JavaScript


# ================================
# SECURITY / TOKENS / HASHING
# ================================

import uuid                                                 # Unique tokens
import hashlib                                              # Hashing
import hmac                                                 # Secure hashing
import base64                                               # Encoding/decoding

# ================================
# UTILITIES & HELPERS
# ================================

import os                                                   # File system access
import re                                                   # Regex processing
import json                                                 # JSON handling
import time                                                 # Time utilities
import logging                                              # Logging
import concurrent.futures                                   # Parallel execution
from datetime import datetime                                # Date & time
from collections import Counter                              # Frequency counting
from typing import Optional, Dict
from openai import OpenAI
import openai          # OpenAI-compatible SDK used for Groq/OpenRouter exceptions
from django.conf import settings
logger = logging.getLogger(__name__)

# Create your views here.

# API key now loaded from environment variables in settings
OPENROUTER_API_KEY = getattr(settings, 'OPENROUTER_API_KEY', '')

class Website_Audit(object):
    def __init__(self, url, request=None):

        # ✅ FIX (Global State): store request and derive user_email as an
        #    instance attribute so no module-level global is needed anywhere.
        self.request = request
        self.user_email = (
            request.user.email
            if request is not None
            and hasattr(request, 'user')
            and request.user.is_authenticated
            else None
        )

        # ✅ FIX: Normalize and validate URL to accept all page types
        self.url = self._normalize_url(url)
        self.base_url = self._get_base_url(self.url)
        self.domain = self._get_domain(self.url)

        # ✅ Modern session configuration with security headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

        # ✅ FIX (Async Networking): use aiohttp with a 15-second timeout so the
        #    Django worker thread is never blocked for the old 120-second window.
        #    We spin up a dedicated event loop so __init__ remains synchronous
        #    from the caller's perspective.
        async def _async_fetch(target_url: str):
            timeout = aiohttp.ClientTimeout(total=15)          # ✅ 15 s hard limit
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
                        # ✅ FIX (Encoding): honour server-declared charset so
                        #    BeautifulSoup never sees mis-decoded bytes.
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
            # ✅ FIX (Encoding): pass detected encoding explicitly to BeautifulSoup
            #    so multi-byte characters (CJK, Arabic, accented Latin …) are not
            #    corrupted during HTML parsing.
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

            # ✅ FIX (Core Web Vitals — TTFB): use a fast HEAD request so we can
            #    read response.elapsed.total_seconds() without re-downloading the
            #    full page body.
            try:
                _head = self.session.head(self.url, timeout=5, allow_redirects=True)
                self.ttfb = round(_head.elapsed.total_seconds(), 3)
            except Exception:
                self.ttfb = None
        
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
        self.data = {}
        self.expiry_date = None
        self.lst = []

    def _get_ai_client(self):
        """Get AI client (Groq preferred, OpenRouter fallback)."""
        use_groq = getattr(settings, 'USE_GROQ', True)

        if use_groq:
            api_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
            if not api_key:
                logger.warning("No GROQ_API_KEY found. Using fallback E-E-A-T analysis.")
                return None
            logger.info("Using Groq API for E-E-A-T analysis with model %s", self._get_ai_model())
            return OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=45.0,
                max_retries=3
            )

        api_key = os.getenv('OPENROUTER_API_KEY') or OPENROUTER_API_KEY
        if not api_key:
            logger.warning("No API key found. Using fallback E-E-A-T analysis.")
            return None

        logger.info("Using OpenRouter API for E-E-A-T analysis with model %s", self._get_ai_model())
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=45.0,
            max_retries=3
        )

    def _get_ai_provider(self):
        """Return the active AI provider name for logging/debugging."""
        return 'groq' if getattr(settings, 'USE_GROQ', True) else 'openrouter'

    def _get_ai_model(self):
        """Get model name based on active provider"""
        if getattr(settings, 'USE_GROQ', True):
            return getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        return getattr(settings, 'OPENAI_MODEL', 'openai/gpt-4o-mini')

    def _normalize_url(self, url):
        """
        ✅ FIX (URL Validation): replaced the hand-maintained TLD regex list with
        the `validators` library.  It handles every real-world TLD including
        ccTLDs, new gTLDs (.app, .dev, .cloud …) and IDNs.
        """
        if not url:
            return url

        url = url.strip()

        # Add scheme if missing so urlparse works correctly
        if not url.startswith(('http://', 'https://', '//')):
            url = 'https://' + url

        parsed = urlparse(url)

        # If netloc is empty but path has domain-like structure, reconstruct
        if not parsed.netloc and parsed.path:
            parts = parsed.path.split('/', 1)
            if len(parts) == 2:
                domain_part, path_part = parts
                url = f"{parsed.scheme or 'https'}://{domain_part}/{path_part}"
            else:
                url = f"{parsed.scheme or 'https'}://{parsed.path}"
            parsed = urlparse(url)

        # Ensure path starts with '/'
        path = parsed.path
        if path and not path.startswith('/'):
            path = '/' + path

        clean_url = urlunparse((
            parsed.scheme or 'https',
            parsed.netloc,
            path or '/',
            parsed.params,
            parsed.query,
            ''  # Strip fragment
        ))

        # ✅ Validate with the validators library — covers all real TLDs
        if not validators.url(clean_url):
            logger.warning(f"_normalize_url: '{clean_url}' did not pass validators.url() — proceeding anyway")

        return clean_url

    def _get_base_url(self, url):
        """Extract base URL (scheme + netloc only)"""
        try:
            parsed = urlparse(url)
            
            if not parsed.netloc:
                return None
            
            # Ensure we have a scheme
            scheme = parsed.scheme or 'https'
            
            return f"{scheme}://{parsed.netloc}"
        except Exception:
            return None

    def _get_domain(self, url):
        """
        Extract domain name only
        Example: https://example.com/page → example.com
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc if parsed.netloc else url
        except Exception:
            return url

    def Score(self, max_val, length):
        """
        ✅ MODERNIZED: Dynamic scoring with optimal range penalties
        """
        if max_val <= 0:
            return 0
        
        if length < 0:
            length = 0
        
        if length == 0:
            return 0
        elif length > max_val:
            excess = length - max_val
            penalty = min(excess * 2, 50)
            base_score = ((max_val / max_val) * 100) - penalty
            score = max(0, base_score)
        else:
            score = (length / max_val) * 100
        
        score = round(score)
        score = max(0, min(100, score))
        
        return score

    def remove_unicode_characters(self, input_string):
        """
        ✅ MODERNIZED: UTF-8 preservation for international SEO
        """
        if input_string is None:
            return ""
        
        if not isinstance(input_string, str):
            input_string = str(input_string)
        
        try:
            cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', input_string)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned.strip()
        except Exception as e:
            logger.error(f"Error cleaning text: {str(e)}")
            return input_string.strip() if input_string else ""

    def _fallback_eeat_analysis(self, content_type, content):
        """
        Enhanced fallback E-E-A-T analysis with 2026 signals
        Includes: AI content detection, freshness, expertise markers
        """
        content_lower = content.lower()
        signals = []
        issues = []
        score = 50
        
        # ✅ 2026 PRIORITY: Author/Brand Signals (Crucial for YMYL)
        author_signals = ['by ', 'written by', 'author:', 'dr.', 'md,', 'phd,', 'reviewed by']
        if any(signal in content_lower for signal in author_signals):
            signals.append("✓ Author attribution detected")
            score += 15
        
        # ✅ Expertise indicators
        expertise_words = ['expert', 'guide', 'professional', 'certified', 'proven', 'research-based']
        if any(word in content_lower for word in expertise_words):
            signals.append("✓ Expertise markers found")
            score += 12
        
        # ✅ Freshness signals (critical for 2026)
        current_year = 2026
        if str(current_year) in content or str(current_year - 1) in content:
            signals.append(f"✓ Current year ({current_year}) mentioned")
            score += 15
        elif re.search(r'\b202[3-5]\b', content):
            signals.append("✓ Recent date found")
            score += 8
        
        # ✅ Data/Stat signals (builds authority)
        if re.search(r'\d+%|\d+\s*(percent|users|people)', content_lower):
            signals.append("✓ Data points/statistics included")
            score += 8
        
        # ⚠️ Red flags for thin/AI content
        clickbait_words = ['shocking', 'secret', 'unbelievable', 'you won\'t believe', 'mind-blowing']
        if any(word in content_lower for word in clickbait_words):
            issues.append("⚠ Clickbait language detected")
            score -= 25
        
        # ⚠️ Generic AI content patterns
        generic_phrases = ['in this article', 'in conclusion', 'in today\'s digital age', 'it\'s important to note']
        if sum(1 for phrase in generic_phrases if phrase in content_lower) >= 2:
            issues.append("⚠ Generic phrasing detected (may signal AI/thin content)")
            score -= 15
        
        # ⚠️ Missing key elements
        if content_type == 'description' and len(content) > 50:
            if not any(word in content_lower for word in ['learn', 'discover', 'find', 'get', 'explore']):
                issues.append("⚠ No clear call-to-action")
                score -= 10
        
        return {
            'eeat_score': max(0, min(100, score)),
            'signals': signals,
            'issues': issues,
            'recommendations': ['Enable AI analysis for comprehensive insights'],
            'details': {
                'content_type': content_type,
                'analysis_method': 'fallback'
            }
        }
    
    def _analyze_eeat_with_ai(self, content_type, content, context=None):
        """
        ✅ AI-POWERED E-E-A-T Analysis - 2026 Updated
        Focus: Helpful Content, Experience signals, Brand authority, Mobile SERP
        
        Args:
            content_type: 'title', 'description', or 'heading'
            content: The actual text to analyze
            context: Additional context (e.g., full page title for description)
        
        Returns:
            dict: E-E-A-T analysis with score, signals, and actionable recommendations
        """
        
        if not content or len(content.strip()) < 3:
            return {
                'eeat_score': 0,
                'signals': [],
                'issues': ['Content too short for meaningful analysis'],
                'recommendations': ['Add substantive content (minimum 20 characters)'],
                'details': {}
            }
        
        try:
            client = self._get_ai_client()
            
            # ✅ FIX: If no API key, fall back immediately without crashing
            if client is None:
                return self._fallback_eeat_analysis(content_type, content)
            
            # ✅ 2026 UPDATED PROMPTS - Focus on Helpful Content & Mobile SERP
            if content_type == 'title':
                analysis_prompt = f"""Analyze this page TITLE for Google's 2026 ranking factors (E-E-A-T, Helpful Content, Mobile SERP):

TITLE: "{content}"

Evaluate against 2026 SEO priorities:
1. **Experience**: First-hand language ("I tested", "our guide", specific examples vs generic claims)
2. **Expertise**: Credentials, year/date (2025-2026), numbers/data, "guide"/"complete"
3. **Authority**: Brand name, clear topic focus, no keyword stuffing
4. **Trust**: No clickbait, clear value, mobile-friendly length (50-60 chars optimal)
5. **Helpful Content**: Specific promise, not generic ("how to X" vs "the ultimate guide to everything")

CRITICAL 2026 PENALTIES:
- AI-generated generic titles ("comprehensive guide", "everything you need to know")
- Clickbait ("shocking", "you won't believe")
- Missing freshness (no year for time-sensitive topics)
- Keyword stuffing or duplicate words

Return ONLY valid JSON (no markdown):
{{
    "eeat_score": 0-100,
    "signals_found": ["specific signal 1", "specific signal 2"],
    "issues": ["specific issue 1"],
    "recommendations": ["actionable rec 1", "actionable rec 2"],
    "has_year": true/false,
    "has_brand": true/false,
    "has_expertise_marker": true/false,
    "has_clickbait": true/false,
    "has_specific_value": true/false,
    "mobile_serp_quality": "excellent/good/poor",
    "trust_level": "high/medium/low"
}}"""

            elif content_type == 'description':
                analysis_prompt = f"""Analyze this META DESCRIPTION for Google's 2026 Mobile-First SERP standards:

DESCRIPTION: "{content}"
{f'PAGE TITLE: "{context}"' if context else ''}

Evaluate for 2026 Mobile SERP (Google prioritizes descriptions that enhance user choice):
1. **Experience**: Author name ("by Jane Doe"), personal insights, tested claims
2. **Expertise**: Credentials (MD, CPA, "expert"), data/stats, "research-backed"
3. **Authority**: Dates (updated 2026), original source mentions, specific outcomes
4. **Trust**: Clear CTA, complements title (not duplicate), mobile-optimized (150-160 chars)
5. **Helpful Content**: Specific benefits, NOT generic ("learn everything", "comprehensive info")

MOBILE SERP OPTIMIZATION:
- First 120 chars most critical (mobile cutoff)
- Action verbs ("discover", "get", "learn how")
- Unique from title (duplicates are ignored by Google)

CRITICAL PENALTIES:
- Duplicates title text (Google shows "..." or rewrites)
- Generic AI patterns ("in this article, we'll explore")
- No clear benefit stated
- Missing freshness for time-sensitive content

Return ONLY valid JSON (no markdown):
{{
    "eeat_score": 0-100,
    "signals_found": ["signal 1", "signal 2"],
    "issues": ["issue 1"],
    "recommendations": ["rec 1", "rec 2"],
    "has_author_attribution": true/false,
    "has_date": true/false,
    "has_specific_benefit": true/false,
    "has_cta": true/false,
    "duplicates_title": true/false,
    "first_120_chars_quality": "strong/weak",
    "mobile_serp_quality": "excellent/good/poor",
    "trust_level": "high/medium/low"
}}"""

            else:  # heading (H1)
                analysis_prompt = f"""Analyze this H1 HEADING for Google's 2026 Helpful Content & Accessibility standards:

H1: "{content}"
{f'PAGE TITLE: "{context}"' if context else ''}

Evaluate for 2026 standards (H1 is critical for topic clarity & accessibility):
1. **Experience**: Specific, actionable ("7 tested strategies" vs "best strategies")
2. **Expertise**: Year for freshness, how-to format, demonstrates depth
3. **Authority**: Clear topic (not vague), aligned with search intent, supports title
4. **Trust**: No clickbait, accessible (screen readers), complements but differs from title
5. **Helpful Content**: User-focused ("how you can X" vs "guide to X"), specific outcome

H1 BEST PRACTICES 2026:
- Should be THE MOST important text on page (accessibility & SEO)
- 60-70 chars ideal (mobile H1 display)
- Must differ from title (shows depth)
- Question format OK if genuinely helpful ("How do I X?" for tutorials)

CRITICAL ISSUES:
- Duplicate of title (wasted opportunity)
- Multiple H1s (confuses topic modeling)
- Vague/generic ("Everything about X")
- Missing for time-sensitive content: year

Return ONLY valid JSON (no markdown):
{{
    "eeat_score": 0-100,
    "signals_found": ["signal 1", "signal 2"],
    "issues": ["issue 1"],
    "recommendations": ["rec 1", "rec 2"],
    "has_year": true/false,
    "is_question_format": true/false,
    "has_specific_outcome": true/false,
    "title_alignment": "complementary/duplicate/conflicting",
    "accessibility_score": "excellent/good/poor",
    "trust_level": "high/medium/low"
}}"""

            # ✅ FIX (Error Handling): retry on RateLimitError with exponential
            #    back-off before falling back to the basic analysis.
            _MAX_RATE_RETRIES = 3
            completion = None
            for _attempt in range(_MAX_RATE_RETRIES):
                try:
                    completion = client.chat.completions.create(
                        model=self._get_ai_model(),
                        messages=[
                            {
                                "role": "system",
                                "content": """You are an expert SEO analyst specializing in Google's 2026 ranking systems: 
- E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)
- Helpful Content System (rewards genuine human expertise)
- Mobile-First Indexing (mobile SERP optimization)

Focus on detecting: AI-generated content patterns, thin content, clickbait, missing expertise signals.
Return ONLY valid JSON, no markdown, no preamble."""
                            },
                            {
                                "role": "user",
                                "content": analysis_prompt
                            }
                        ],
                        temperature=0.2,  # Lower for more consistent analysis
                        max_tokens=700
                    )
                    logger.info(
                        "E-E-A-T AI analysis completed via %s using model %s for %s",
                        self._get_ai_provider(),
                        self._get_ai_model(),
                        content_type
                    )
                    break  # success — exit retry loop
                except openai.RateLimitError:
                    if _attempt < _MAX_RATE_RETRIES - 1:
                        _wait = 2 ** _attempt  # 1 s, 2 s, then give up
                        logger.warning(
                            f"OpenAI RateLimitError — retrying in {_wait}s "
                            f"(attempt {_attempt + 1}/{_MAX_RATE_RETRIES})"
                        )
                        time.sleep(_wait)
                    else:
                        logger.error(
                            "OpenAI RateLimitError — all retries exhausted, "
                            "falling back to basic analysis"
                        )
                        return self._fallback_eeat_analysis(content_type, content)
            if completion is None:
                return self._fallback_eeat_analysis(content_type, content)
            
            response_text = completion.choices[0].message.content.strip()
            
            # Robust JSON extraction
            if '```' in response_text:
                # Extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                else:
                    # Fallback: find first JSON object
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
            
            result = json.loads(response_text)
            
            # Ensure all required fields exist with defaults
            result.setdefault('eeat_score', 50)
            result.setdefault('signals_found', [])
            result.setdefault('issues', [])
            result.setdefault('recommendations', [])
            
            return {
                'eeat_score': result['eeat_score'],
                'signals': result['signals_found'],
                'issues': result['issues'],
                'recommendations': result['recommendations'],
                'details': result  # Store full AI response for debugging
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for {content_type}: {e}")
            logger.error(f"Response was: {response_text[:200]}")
            return self._fallback_eeat_analysis(content_type, content)
        except Exception as e:
            logger.error(f"AI E-E-A-T analysis failed for {content_type}: {e}")
            return self._fallback_eeat_analysis(content_type, content)

    def get_title(self, min_length=30, max_length=60, use_ai=True):
        """
        ✅ 2026 TITLE OPTIMIZATION
        - Mobile-first (50-60 chars ideal for full mobile display)
        - E-E-A-T signals (expertise, freshness, brand)
        - Helpful Content compliance (specific value, not generic)
        """
        title_tag = self.soup.find('title')

        if not title_tag:
            self.title = "Title is not Found!"
            self.data['title_verdict'] = ' | ' + self.title
            self.data['title'] = ''
            self.data['title_length'] = 0
            self.data['title_issues'] = ['❌ CRITICAL: Missing <title> tag - Major SEO/accessibility issue']
            self.data['title_eeat_score'] = 0
            self.data['title_eeat_signals'] = []
            self.data['title_eeat_recommendations'] = ['Add a descriptive, unique <title> tag immediately']
            self.title_score = 0
            return None
        
        try:
            title_text = title_tag.get_text(strip=True)
            title = self.remove_unicode_characters(title_text)
        except Exception as e:
            logger.error(f"Error extracting title: {str(e)}")
            title = ''
        
        title = title.strip()
        title_length = len(title)
        
        # ✅ AI-POWERED E-E-A-T ANALYSIS
        if use_ai and title:
            eeat_analysis = self._analyze_eeat_with_ai('title', title)
        else:
            eeat_analysis = self._fallback_eeat_analysis('title', title)
        
        issues = []
        
        # ✅ 2026 CRITICAL LENGTH CHECKS (Mobile-first)
        if title_length == 0:
            self.title = "Title is Empty!"
            issues.append("❌ Empty title tag - Critical SEO issue")
            eeat_analysis['eeat_score'] = 0
        elif title_length < min_length:
            self.title = "Title is too Short!"
            issues.append(f"⚠ Title too short ({title_length} chars) - Optimal: 50-60 chars")
            issues.append("💡 Short titles may appear incomplete in SERPs")
        elif min_length <= title_length <= max_length:
            self.title = "Title is Optimal!"
        elif max_length < title_length <= 70:
            self.title = "Title is Acceptable (may truncate on mobile)"
            issues.append(f"⚠ Title ({title_length} chars) may truncate on mobile (60+ chars)")
        else:
            self.title = "Title is too Long!"
            issues.append(f"❌ Title too long ({title_length} chars) - Will truncate in SERPs")
            issues.append(f"💡 Recommended: Keep under 60 chars for full mobile display")
        
        # ✅ 2026 KEYWORD STUFFING DETECTION (Helpful Content penalty)
        if title:
            words = [w.lower() for w in re.findall(r'\b\w+\b', title) if len(w) > 3]
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            repeated_words = [word for word, count in word_freq.items() if count > 2]
            if repeated_words:
                issues.append(f"❌ Keyword stuffing detected: '{', '.join(repeated_words)}' repeated {word_freq[repeated_words[0]]}+ times")
                eeat_analysis['eeat_score'] = max(0, eeat_analysis['eeat_score'] - 20)
        
        # Combine issues from AI and basic checks
        all_issues = issues + eeat_analysis['issues']
        
        # Store results
        self.data['title_verdict'] = ' | ' + self.title
        self.title = title
        self.data['title'] = self.title
        self.data['title_length'] = title_length
        self.data['title_issues'] = all_issues if all_issues else ['✅ No issues detected']
        self.data['title_eeat_score'] = eeat_analysis['eeat_score']
        self.data['title_eeat_signals'] = eeat_analysis['signals']
        self.data['title_eeat_recommendations'] = eeat_analysis['recommendations']
        self.data['title_eeat_details'] = eeat_analysis.get('details', {})
        
        # ✅ CALCULATE TECHNICAL SCORE (mobile-optimized formula)
        if title_length == 0:
            title_score = 0
        elif min_length <= title_length <= max_length:
            # Optimal range: 50-60 chars gets 95-100
            ideal = 55
            deviation = abs(title_length - ideal)
            title_score = 100 - (deviation * 1.5)
            title_score = max(95, min(100, title_score))
        else:
            title_score = self.Score(max_length, title_length)
        
        # ✅ COMBINE: Technical (55%) + E-E-A-T (45%) - 2026 weights
        self.title_score = int((title_score * 0.55) + (eeat_analysis['eeat_score'] * 0.45))
        
        return title

    def get_description(self, min_length=120, max_length=160, use_ai=True):
        """
        ✅ 2026 META DESCRIPTION OPTIMIZATION
        - Mobile-first (120-160 chars, first 120 critical)
        - Unique from title (duplicates ignored by Google)
        - Clear benefit/CTA for click-through
        """
        meta_tags = self.soup.findAll("meta")
        description = ""
        
        # Find description meta tag
        for tag in meta_tags:
            try:
                if 'name' in tag.attrs and tag.attrs['name'].strip().lower() == 'description':
                    if 'content' in tag.attrs and tag.attrs['content']:
                        description = tag.attrs['content']
                        break
            except (AttributeError, KeyError):
                continue
        
        # Clean description
        self.comp_desc = self.remove_unicode_characters(description)
        self.data['description'] = self.comp_desc if self.comp_desc else ''
        desc_length = len(self.comp_desc)
        
        # ✅ AI-POWERED E-E-A-T ANALYSIS (with title context)
        if use_ai and self.comp_desc:
            eeat_analysis = self._analyze_eeat_with_ai('description', self.comp_desc, context=self.title)
        else:
            eeat_analysis = self._fallback_eeat_analysis('description', self.comp_desc)
        
        issues = []
        
        # ✅ 2026 CRITICAL CHECKS
        if desc_length == 0:
            self.desc = "Description Missing!"
            issues.append("❌ CRITICAL: Missing meta description")
            issues.append("💡 Google will auto-generate from content (often poor quality)")
            eeat_analysis['eeat_score'] = 0
        elif desc_length < min_length:
            self.desc = "Description is too Short"
            issues.append(f"⚠ Description too short ({desc_length} chars)")
            issues.append("💡 Optimal: 150-160 chars for full mobile display")
        elif min_length <= desc_length <= max_length:
            self.desc = "Description is Optimal!"
        elif max_length < desc_length <= 170:
            self.desc = "Description is Acceptable (may truncate)"
            issues.append(f"⚠ Description ({desc_length} chars) may truncate on mobile")
        else:
            self.desc = "Description is too Long!"
            issues.append(f"❌ Description too long ({desc_length} chars) - Will truncate in SERPs")
            issues.append("💡 Keep under 160 chars for full display")
        
        # ✅ CHECK FOR TITLE DUPLICATION (major 2026 issue)
        if self.comp_desc and self.title:
            desc_lower = self.comp_desc.lower()
            title_lower = self.title.lower()
            
            if desc_lower == title_lower:
                issues.append("❌ CRITICAL: Description duplicates title exactly")
                issues.append("💡 Google ignores duplicate descriptions - make it unique")
                eeat_analysis['eeat_score'] = max(0, eeat_analysis['eeat_score'] - 30)
            elif title_lower in desc_lower and len(self.comp_desc) < 100:
                issues.append("⚠ Description mostly duplicates title")
                issues.append("💡 Add unique value/benefit not in title")
        
        # Combine issues
        all_issues = issues + eeat_analysis['issues']
        
        # Store results
        self.data['desc_verdict'] = ' | ' + self.desc
        self.data['desc_length'] = desc_length
        self.data['desc_issues'] = all_issues if all_issues else ['✅ No issues detected']
        self.data['desc_eeat_score'] = eeat_analysis['eeat_score']
        self.data['desc_eeat_signals'] = eeat_analysis['signals']
        self.data['desc_eeat_recommendations'] = eeat_analysis['recommendations']
        self.data['desc_eeat_details'] = eeat_analysis.get('details', {})
        
        # ✅ CALCULATE TECHNICAL SCORE (mobile-optimized)
        if desc_length == 0:
            desc_score = 0
        elif min_length <= desc_length <= max_length:
            ideal = 155
            deviation = abs(desc_length - ideal)
            desc_score = 100 - (deviation * 1.0)
            desc_score = max(95, min(100, desc_score))
        else:
            desc_score = self.Score(max_length, desc_length)
        
        # ✅ COMBINE: Technical (50%) + E-E-A-T (50%) - 2026 equal weight
        self.desc_score = int((desc_score * 0.50) + (eeat_analysis['eeat_score'] * 0.50))
        
        return

    def get_Heading(self, min_length=20, max_length=70, use_ai=True):
        """
        ✅ 2026 HEADING OPTIMIZATION
        - Semantic HTML5 structure (WCAG 2.2 compliant)
        - One H1 only (topic clarity)
        - Logical hierarchy (H1 > H2 > H3)
        - Mobile-friendly length
        """
        h1_tags = self.soup.findAll('h1')
        
        # Count all heading levels
        h1_count = len(h1_tags) if h1_tags else 0
        h2_count = len(self.soup.findAll('h2')) if self.soup else 0
        h3_count = len(self.soup.findAll('h3')) if self.soup else 0
        h4_count = len(self.soup.findAll('h4')) if self.soup else 0
        
        issues = []
        
        # ✅ 2026 CRITICAL: H1 COUNT (must be exactly 1)
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
            # Fallback to H2 if no H1
            h2_tags = self.soup.findAll('h2')
            if h2_tags:
                heading_tags = h2_tags
                self.H = "H2"
                issues.append("⚠ Using H2 as fallback - H1 is required")

        # ✅ FIX (UnboundLocalError): initialise all three variables unconditionally
        #    so the rest of the method never references an unbound name when the
        #    page has no heading tags at all.
        com_heading = ""
        heading_length = 0
        eeat_analysis = self._fallback_eeat_analysis('heading', '')
        self.heading = "No Heading Found"

        # Extract heading text (only when heading_tags was populated above)
        if heading_tags:
            heading_text = ""
            try:
                heading_text = heading_tags[0].get_text(strip=True)
                self.comp_head = heading_text
            except Exception as e:
                logger.error(f"Error extracting heading: {str(e)}")

            com_heading = self.remove_unicode_characters(heading_text).strip()
            heading_length = len(com_heading)

            # ✅ AI-POWERED E-E-A-T ANALYSIS (with title context)
            if use_ai and com_heading:
                eeat_analysis = self._analyze_eeat_with_ai('heading', com_heading, context=self.title)
            else:
                eeat_analysis = self._fallback_eeat_analysis('heading', com_heading)
        
        # ✅ TECHNICAL VALIDATION
        if heading_length == 0:
            self.heading = "Heading Tag is Empty"
            heading_length = 0
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
        
        # ✅ 2026 CRITICAL: HEADING HIERARCHY VALIDATION (WCAG 2.2)
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
        
        # ✅ H1-TITLE RELATIONSHIP CHECK
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
        
        # Combine issues
        all_issues = issues + eeat_analysis['issues']
        
        # ✅ CONTENT STRUCTURE SIGNALS (positive indicators)
        structure_signals = []
        if h2_count >= 3:
            structure_signals.append(f"✓ Well-structured content ({h2_count} H2 sections)")
        if h3_count >= 2:
            structure_signals.append(f"✓ Detailed hierarchy ({h3_count} H3 subsections)")
        if h1_count == 1 and h2_count >= 3 and h3_count >= 1:
            structure_signals.append("✓ Excellent semantic structure (aids accessibility)")
        
        # Store results
        self.data['head_verdict'] = ' | ' + self.heading
        self.data['heading'] = com_heading if heading_length > 0 else ''
        self.data['heading_length'] = heading_length
        self.data['heading_type'] = self.H
        self.data['h1_count'] = h1_count
        self.data['h2_count'] = h2_count
        self.data['h3_count'] = h3_count
        self.data['h4_count'] = h4_count
        self.data['heading_issues'] = all_issues if all_issues else ['✅ No issues detected']
        self.data['heading_eeat_score'] = eeat_analysis['eeat_score']
        self.data['heading_eeat_signals'] = eeat_analysis['signals'] + structure_signals
        self.data['heading_eeat_recommendations'] = eeat_analysis['recommendations']
        self.data['heading_eeat_details'] = eeat_analysis.get('details', {})
        
        # ✅ CALCULATE TECHNICAL SCORE
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
        
        # ✅ BONUS FOR EXCELLENT STRUCTURE
        if h1_count == 1 and h2_count >= 3 and h3_count >= 2 and not hierarchy_issues:
            heading_score = min(100, heading_score + 5)
        
        # ✅ COMBINE: Technical (50%) + E-E-A-T (50%) - 2026 equal weight
        self.heading_score = int((heading_score * 0.50) + (eeat_analysis['eeat_score'] * 0.50))
        
        return

    def get_Google_preview(self):
        """
        ✅ 2026 COMPREHENSIVE SERP OPTIMIZATION SCORE
        Combines: Technical SEO + E-E-A-T + Structure + Mobile-First
        """
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

            # ✅ FIX (Core Web Vitals — TTFB): factor TTFB into the avg_score.
            #    Good TTFB (≤0.8 s) earns a bonus; poor TTFB (>1.8 s) is penalised.
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
            
            self.data['eeat_breakdown'] = {
                'title_eeat': self.data.get('title_eeat_score', 0),
                'description_eeat': self.data.get('desc_eeat_score', 0),
                'heading_eeat': self.data.get('heading_eeat_score', 0),
                'average_eeat': round(avg_eeat, 1),
                'trust_level': 'high' if avg_eeat >= 75 else 'medium' if avg_eeat >= 50 else 'low',
                'helpful_content_ready': avg_eeat >= 70
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimization score: {str(e)}")
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
            google1 = "🏆 Excellent - SERP Optimized (2026 Standards)"
            self.data['google_verdict'] = google1
            self.data['verdict'] = True
            self.data['optimization_level'] = 'Excellent'
            
            if avg_eeat < 90:
                recommendations.append("💡 Consider: Further E-E-A-T enhancement for YMYL topics")
            
            return_val = 1
            
        elif self.avg_score >= good:
            google1 = "✅ Good - Well Optimized"
            self.data['google_verdict'] = google1
            self.data['verdict'] = True
            self.data['optimization_level'] = 'Good'
            
            if avg_eeat < 70:
                recommendations.append("🎯 PRIORITY: Improve E-E-A-T signals (currently below 2026 threshold)")
            
            if self.title_score < 80:
                recommendations.append("⚡ Optimize title: Add year/brand/expertise marker")
            
            if self.desc_score < 80:
                recommendations.append("⚡ Improve description: Add specific benefit/CTA")
            
            recommendations.extend(ai_recs[:3])
            
            return_val = 1
            
        else:
            google1 = "⚠️ Needs Optimization"
            self.data['google_verdict'] = google1
            self.data['verdict'] = False
            self.data['optimization_level'] = 'Needs Improvement'
            
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
        
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)
        
        self.data['recommendations'] = unique_recs[:10] if unique_recs else ['✅ No major issues - maintain optimization']
        
        self.data['mobile_optimized'] = (
            20 <= self.data.get('title_length', 0) <= 60 and
            120 <= self.data.get('desc_length', 0) <= 160
        )
        
        self.data['accessibility_ready'] = (
            self.data.get('h1_count') == 1 and
            self.data.get('heading_length', 0) > 0
        )
        
        return return_val

    def get_grammar_analysis(self):
        """
        ✅ Spelling & Grammar Analysis with File-Based Custom Dictionaries
        Loads custom words from external files for easy management
        """
        import re
        import os
        from collections import Counter
        
        try:
            from spellchecker import SpellChecker
        except ImportError:
            logger.warning("pyspellchecker not installed. Run: pip install pyspellchecker")
            self._set_empty_grammar_data()
            return None
        
        # Extract visible text from soup
        if not self.soup:
            self._set_empty_grammar_data()
            return None
        
        # Remove script and style elements
        for script in self.soup(["script", "style", "noscript"]):
            script.decompose()
        
        # Get text content
        try:
            text = self.soup.get_text(separator=' ', strip=True)
            text = self.remove_unicode_characters(text)
        except Exception as e:
            logger.error(f"Error extracting text for grammar analysis: {str(e)}")
            self._set_empty_grammar_data()
            return None
        
        if not text or len(text.strip()) < 50:
            self.data['grammar_verdict'] = 'Insufficient content for analysis'
            self.data['grammar_score'] = 0
            self.data['spelling_errors'] = []
            self.data['grammar_issues'] = ['Content too short for meaningful analysis']
            self.data['readability_score'] = 0
            self.data['grammar_recommendations'] = ['Add more content (minimum 50 characters)']
            return None
        
        # Initialize tracking
        spelling_errors = []
        grammar_issues = []
        recommendations = []
        total_deductions = 0
        
        # Clean text for analysis
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        words_lower = [w.lower() for w in words]
        
        # --- LOAD CUSTOM DICTIONARIES FROM FILES ---
        spell = SpellChecker()
        
        # ✅ Load custom words from external files
        custom_words = self._load_custom_dictionaries()
        
        # Add custom words to spell checker
        if custom_words:
            spell.word_frequency.load_words(custom_words)
        
        # Filter words to check
        words_to_check = []
        for word in words:
            word_lower = word.lower()
            
            if word_lower in custom_words:
                continue
            
            if (len(word) < 3 or 
                word.isupper() or 
                any(c.isdigit() for c in word) or
                any(c.isupper() for c in word[1:]) or
                word.endswith("'s") or
                "'" in word or
                word.isdigit()):
                continue
                
            if word_lower in ['www', 'http', 'https', 'com', 'net', 'org', 'io', 'co', 'pk', 'edu', 'gov']:
                continue
                
            words_to_check.append(word_lower)
        
        # Find misspelled words
        misspelled = spell.unknown(words_to_check)
        
        # ✅ Filter out proper nouns (capitalized words)
        original_words_set = set(words)
        filtered_misspelled = []
        
        for word in misspelled:
            capitalized_version = word.capitalize()
            if capitalized_version in original_words_set or word.upper() in original_words_set:
                continue
            filtered_misspelled.append(word)
        
        # Get corrections for misspelled words (limit to top 10)
        spelling_errors_with_buttons = []
        for word in list(filtered_misspelled)[:10]:
            correction = spell.correction(word)
            if correction and correction != word:
                count = words_lower.count(word)
                
                if len(word) > 4 and len(correction) > 4:
                    common_chars = set(word) & set(correction)
                    if len(common_chars) < len(word) * 0.5:
                        continue
                
                if count > 1:
                    display_text = f"'{word}' → '{correction}' ({count} occurrences)"
                else:
                    display_text = f"'{word}' → '{correction}'"
                
                spelling_errors_with_buttons.append({
                    'word': word,
                    'suggestion': correction,
                    'count': count,
                    'display': display_text
                })
                total_deductions += 2 * count

        if len(filtered_misspelled) > 10:
            spelling_errors_with_buttons.append({
                'display': f"... and {len(filtered_misspelled) - 10} more potential spelling issues",
                'word': None,
                'suggestion': None,
                'count': 0
            })

        if not spelling_errors_with_buttons:
            spelling_errors_with_buttons = [{
                'display': '✓ No spelling errors detected',
                'word': None,
                'suggestion': None,
                'count': 0
            }]

        self.data['spelling_errors'] = spelling_errors_with_buttons
        # --- GRAMMAR CHECKS ---
        
        # 1. Repeated words
        word_pairs = [' '.join(words_lower[i:i+2]) for i in range(len(words_lower)-1)]
        repeated = [pair.split()[0] for pair in word_pairs if len(pair.split()) == 2 and pair.split()[0] == pair.split()[1]]
        if repeated:
            unique_repeated = list(set(repeated))[:5]
            grammar_issues.append(f"Repeated words detected: {', '.join(unique_repeated)}")
            total_deductions += len(set(repeated)) * 3
        
        # 2. Sentence length analysis
        long_sentences = [s for s in sentences if len(s.split()) > 30]
        if long_sentences:
            count = len(long_sentences)
            grammar_issues.append(f"{count} overly long sentence(s) detected (>30 words)")
            recommendations.append("Break long sentences for better readability")
            total_deductions += count * 2
        
        short_sentences = [s for s in sentences if 0 < len(s.split()) < 5]
        if len(short_sentences) > len(sentences) * 0.3 and len(sentences) > 5:
            grammar_issues.append("Too many short sentences - affects flow")
            recommendations.append("Combine short sentences for better rhythm")
            total_deductions += 3
        
        # 3. Passive voice detection
        passive_indicators = ['is being', 'was being', 'has been', 'have been', 
                            'had been', 'will be', 'is done', 'was done', 'were being']
        text_lower = text.lower()
        passive_count = sum(text_lower.count(indicator) for indicator in passive_indicators)
        if passive_count > 3:
            grammar_issues.append(f"Excessive passive voice detected ({passive_count} instances)")
            recommendations.append("Use active voice for stronger, clearer writing")
            total_deductions += passive_count
        
        # 4. Capitalization issues
        sentences_text = '. '.join(sentences)
        lowercase_starts = len(re.findall(r'\.\s+[a-z]', sentences_text))
        if lowercase_starts > 0:
            grammar_issues.append(f"{lowercase_starts} sentence(s) start with lowercase")
            total_deductions += lowercase_starts * 2
        
        # 5. Multiple punctuation
        multi_punct = len(re.findall(r'[!?]{2,}', text))
        if multi_punct > 0:
            grammar_issues.append("Multiple exclamation/question marks detected")
            recommendations.append("Use single punctuation marks for professionalism")
            total_deductions += multi_punct * 2
        
        # 6. Common grammar mistakes
        grammar_patterns = {
            r'\b(your)\s+(welcome)\b': "Use \"you're welcome\" (contraction of 'you are')",
            r'\b(should|could|would)\s+(of)\b': "Use 'have' instead of 'of' (should have, could have, would have)",
            r'\b(alot)\b': "Use 'a lot' (two words)",
            r'\bthere\s+(own|coming|going)\b': "Consider if 'their' or 'they're' is correct here",
        }
        
        for pattern, suggestion in grammar_patterns.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                grammar_issues.append(f"{suggestion} - {len(matches)} instance(s)")
                total_deductions += len(matches) * 2
        
        # 7. Missing spaces after punctuation
        no_space_after_punct = len(re.findall(r'[.,;:][a-zA-Z]', text))
        if no_space_after_punct > 2:
            grammar_issues.append(f"Missing space after punctuation ({no_space_after_punct} instances)")
            total_deductions += no_space_after_punct
        
        # 8. Double spaces
        double_spaces = len(re.findall(r'\s{2,}', text))
        if double_spaces > 2:
            grammar_issues.append(f"Multiple spaces detected ({double_spaces} instances)")
            total_deductions += 1
        
        # --- READABILITY ANALYSIS ---
        if words and sentences:
            avg_word_length = sum(len(w) for w in words) / len(words)
            avg_sentence_length = len(words) / len(sentences)
            
            syllable_estimate = sum(max(1, len(re.findall(r'[aeiou]+', w.lower()))) for w in words)
            syllables_per_word = syllable_estimate / len(words)
            
            readability_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * syllables_per_word
            readability_score = max(0, min(100, readability_score))
            
            if readability_score < 50:
                recommendations.append("Simplify language for better readability")
                total_deductions += 2
            elif readability_score > 80:
                recommendations.append("✓ Excellent readability - text is easy to understand")
        else:
            readability_score = 50
        
        # --- SEO RECOMMENDATIONS ---
        if len(words) < 300:
            recommendations.append("Consider adding more content (aim for 300+ words for SEO)")
        
        if not spelling_errors and not grammar_issues:
            recommendations.append("✓ Excellent writing quality - no issues detected")
        
        if len(spelling_errors) == 0:
            recommendations.append("✓ No spelling errors found")
        
        if passive_count == 0:
            recommendations.append("✓ Good use of active voice")
        
        # --- CALCULATE FINAL SCORE ---
        grammar_score = max(0, min(100, 100 - total_deductions))
        
        if grammar_score >= 90:
            verdict = "✓ Excellent - Professional writing quality"
        elif grammar_score >= 75:
            verdict = "✓ Good - Minor improvements possible"
        elif grammar_score >= 60:
            verdict = "⚠️ Fair - Several issues to address"
        else:
            verdict = "❌ Poor - Significant writing issues detected"
        
        # Store results
        self.data['grammar_verdict'] = verdict
        self.data['grammar_score'] = round(grammar_score, 1)
        self.data['spelling_errors'] = self.data.get('spelling_errors', [])
        self.data['grammar_issues'] = grammar_issues if grammar_issues else ['✓ No grammar issues detected']
        self.data['readability_score'] = round(readability_score, 1)
        self.data['grammar_recommendations'] = recommendations if recommendations else ['✓ Content quality is excellent']
        
        return True


    def _load_custom_dictionaries(self):
        """
        ✅ Load custom words from external dictionary files
        Returns a set of all custom words
        """
        import os
        
        custom_words = set()
        
        # Define dictionary directory
        dict_dir = os.path.join(os.path.dirname(__file__), 'dictionaries')
        
        # Create directory if it doesn't exist
        if not os.path.exists(dict_dir):
            os.makedirs(dict_dir)
            logger.info(f"Created dictionaries directory: {dict_dir}")
        
        # List of dictionary files to load
        dict_files = [
            'custom_dictionary.txt',
            'tech_terms.txt',
            'brand_names.txt',
            'pakistani_locations.txt',
            'user_ignored_words.txt'
        ]
        
        # Load each dictionary file
        for filename in dict_files:
            filepath = os.path.join(dict_dir, filename)
            
            if not os.path.exists(filepath):
                self._create_sample_dictionary(filepath, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip().lower()
                        if line and not line.startswith('#'):
                            custom_words.add(line)
            except Exception as e:
                logger.warning(f"Could not load dictionary file {filename}: {str(e)}")
        
        return custom_words


    def _create_sample_dictionary(self, filepath, filename):
        """
        ✅ Create sample dictionary files with common words
        """
        sample_content = {
            'custom_dictionary.txt': '''# Common abbreviations and contractions
doesn
isn
wasn
hasn
haven
didn
wouldn
shouldn
couldn
aren
weren
won
don
ll
ve
re
''',
            'tech_terms.txt': '''# Technology and programming terms
app
apps
api
apis
css
html
javascript
js
python
reactjs
nodejs
github
docker
kubernetes
mongodb
postgresql
frontend
backend
fullstack
devops
seo
ui
ux
admin
analytics
shopify
wordpress
blockchain
saas
''',
            'brand_names.txt': '''# Company and product names
google
facebook
twitter
instagram
linkedin
amazon
microsoft
apple
shopify
stripe
paypal
zoom
slack
tabnine
copilot
''',
            'pakistani_locations.txt': '''# Pakistani cities and locations
karachi
lahore
islamabad
rawalpindi
faisalabad
multan
peshawar
quetta
hyderabad
sindh
punjab
balochistan
kpk
pakistan
pakistani
shahrah
clifton
defence
gulshan
saddar
''',
            'user_ignored_words.txt': '''# Words marked as correct by users
# This file is auto-updated when users click "Not a mistake"
# Add your custom words below:
codup
'''
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                content = sample_content.get(filename, '# Custom dictionary words\n# Add one word per line\n')
                f.write(content)
            logger.info(f"Created sample dictionary: {filepath}")
        except Exception as e:
            logger.warning(f"Could not create dictionary file {filename}: {str(e)}")


    @require_POST
    def add_to_dictionary(request):
        try:
            data = json.loads(request.body)
            word = data.get('word', '').strip().lower()
            
            if not word:
                return JsonResponse({'success': False, 'error': 'No word provided'})
            
            dict_dir = os.path.join(os.path.dirname(__file__), 'dictionaries')
            filepath = os.path.join(dict_dir, 'user_ignored_words.txt')
            
            os.makedirs(dict_dir, exist_ok=True)
            
            existing_words = set()
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_words = {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}
            
            if word not in existing_words:
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(f'\n{word}')
                
                return JsonResponse({
                    'success': True, 
                    'word': word,
                    'message': f"'{word}' added to dictionary"
                })
            else:
                return JsonResponse({
                    'success': True, 
                    'word': word,
                    'message': f"'{word}' already in dictionary"
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })


    def _set_empty_grammar_data(self):
        """Helper to set empty grammar data"""
        self.data['grammar_verdict'] = 'Analysis unavailable'
        self.data['grammar_score'] = 0
        self.data['spelling_errors'] = []
        self.data['grammar_issues'] = []
        self.data['readability_score'] = 0
        self.data['grammar_recommendations'] = []

    def Keyword_Density(self):
        """
        ✅ MODERNIZED: Semantic keyword analysis for 2024 SEO
        """
        
        for script in self.soup(["script", "style", "noscript", "iframe"]):
            script.decompose()
        
        visible_text = self.soup.get_text(separator=' ', strip=True)
        
        content1 = re.sub(r'[0-9|!&()@#$%^*/{}+=:;"\[\]<>?~`]', ' ', visible_text)
        content1 = re.sub(r'[-]{2,}', ' ', content1)
        content1 = re.sub(r'[_]{2,}', ' ', content1)
        
        content = self.remove_unicode_characters(content1)
        content = re.sub(r'\s+', ' ', content).strip()
        
        all_words = content.lower().split()
        
        meta = self.soup.findAll("meta")
        keyword = ""
        meta_keywords_found = False
        
        for tag in meta:
            try:
                if 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() in ['keyword', 'keywords']:
                    if 'content' in tag.attrs:
                        keyword = keyword + tag.attrs['content']
                        meta_keywords_found = True
            except (AttributeError, KeyError):
                continue
        
        if meta_keywords_found:
            self.data['meta_keywords_warning'] = "Meta keywords tag detected but ignored by Google since 2009"
        
        result = all_words
        
        if len(result) < 50:
            self.data['density'] = "Insufficient content for keyword analysis (minimum 50 words required)"
            self.data['word_count'] = len(result)
            self.data['content_quality'] = 'Too Short'
            return
        
        extra_words = {
            'a', 'an', 'the', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
            'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'themselves',
            'in', 'on', 'at', 'to', 'for', 'of', 'from', 'with', 'without', 'by', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'over',
            'and', 'or', 'but', 'nor', 'so', 'yet', 'if', 'when', 'where', 'while', 'because',
            'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'may', 'might', 'must',
            'can', 'could',
            'not', 'no', 'yes', 'very', 'too', 'so', 'just', 'only', 'even', 'also', 'both',
            'more', 'most', 'less', 'least', 'much', 'many', 'few', 'some', 'any', 'all',
            'each', 'every', 'either', 'neither', 'other', 'another',
            'what', 'when', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how',
            'here', 'there', 'now', 'then', 'than', 'as', 'such', 'like', 'well',
            'up', 'down', 'out', 'off', 'back', 'home', 'page', 'new', 'old',
            'one', 'two', 'first', 'second', 'third', 'next', 'last', 'ago', 'today',
            'minute', 'minutes', 'hour', 'hours', 'day', 'days', 'week', 'month', 'year',
            'get', 'got', 'make', 'made', 'go', 'going', 'gone', 'come', 'came',
            'know', 'see', 'saw', 'take', 'took', 'give', 'find', 'tell', 'ask',
            'use', 'used', 'way', 'said', 'say',
            'click', 'please', 'read', 'learn', 'view', 'copyright', 'rights', 'reserved',
            'privacy', 'policy', 'terms', 'conditions', 'cookies', 'accept',
            '...', '--', '–', '—', '»', '«', '›', '‹'
        }
        
        filtered_words = [
            word for word in result 
            if len(word) >= 3 
            and word not in extra_words
            and word.isalpha()
            and not word.startswith(('http', 'www'))
        ]
        
        if len(filtered_words) < 10:
            self.data['density'] = "Insufficient meaningful content for analysis"
            self.data['word_count'] = len(all_words)
            self.data['filtered_word_count'] = len(filtered_words)
            self.data['content_quality'] = 'Low Quality'
            return
        
        dict_c = Counter(filtered_words)
        high = dict_c.most_common(10)
        
        if len(high) < 5:
            self.data['density'] = "Insufficient keyword diversity for analysis"
            self.data['content_quality'] = 'Low Diversity'
            return
        
        if high[0][1] < 3:
            self.data['density'] = "Content lacks topical focus - no clear keyword themes detected"
            self.data['content_quality'] = 'Unfocused'
            self.data['top_keyword_count'] = high[0][1]
            return
        
        density_dict = {}
        semantic_analysis = {}
        
        total_meaningful_words = len(filtered_words)
        total_all_words = len(all_words)
        
        if len(high) >= 2:
            self.keyword_lst.append(high[0][0])
            self.keyword_lst.append(high[1][0])
        
        top_5_total = sum([count for word, count in high[:5]])
        topic_concentration = (top_5_total / total_meaningful_words) * 100
        
        for i, (word, count) in enumerate(high[:10]):
            density_percent = (count / total_meaningful_words) * 100
            
            if density_percent > 4.0:
                usage_verdict = "⚠️ Overused - Risk of keyword stuffing"
            elif density_percent > 2.5:
                usage_verdict = "⚠️ High usage - Monitor for naturalness"
            elif density_percent >= 1.0:
                usage_verdict = "✓ Optimal - Natural usage"
            elif density_percent >= 0.5:
                usage_verdict = "✓ Good - Supporting keyword"
            else:
                usage_verdict = "Low - Minor relevance"
            
            density_dict[word] = {
                "count": count,
                "density": f"{density_percent:.2f}%",
                "usage": usage_verdict,
                "rank": i + 1
            }
        
        self.data['density_dict'] = density_dict
        self.data['total_words'] = total_all_words
        self.data['meaningful_words'] = total_meaningful_words
        self.data['unique_keywords'] = len(dict_c)
        self.data['keyword_diversity'] = round((len(dict_c) / total_meaningful_words) * 100, 2)
        
        if topic_concentration > 30:
            concentration_verdict = "⚠️ High - Content may lack depth or be overly repetitive"
        elif topic_concentration > 20:
            concentration_verdict = "⚠️ Moderate-High - Consider broadening topical coverage"
        elif topic_concentration >= 10:
            concentration_verdict = "✓ Good - Focused content with clear topics"
        else:
            concentration_verdict = "⚠️ Low - Content may lack focus or be too broad"
        
        self.data['topic_concentration'] = f"{topic_concentration:.2f}%"
        self.data['topic_concentration_verdict'] = concentration_verdict
        
        if total_all_words < 300:
            content_quality = "Thin Content - Increase word count to 500+ for better rankings"
        elif total_all_words < 500:
            content_quality = "Short Content - Consider expanding to 800+ words"
        elif total_all_words < 800:
            content_quality = "Moderate Content - Good for basic pages"
        elif total_all_words < 1500:
            content_quality = "Good Content Depth - Suitable for most topics"
        elif total_all_words < 2500:
            content_quality = "Excellent Content Depth - Strong for competitive topics"
        else:
            content_quality = "Comprehensive Content - Excellent for authority building"
        
        self.data['content_quality'] = content_quality
        
        stuffing_indicators = []
        
        for word, count in high[:10]:
            density = (count / total_meaningful_words) * 100
            if density > 4.0:
                stuffing_indicators.append(f"'{word}' appears {count} times ({density:.1f}% density)")
        
        if high[0][1] / total_meaningful_words > 0.05:
            stuffing_indicators.append(f"Top keyword '{high[0][0]}' dominates content")
        
        if stuffing_indicators:
            self.data['keyword_stuffing_risk'] = "⚠️ HIGH - " + "; ".join(stuffing_indicators)
        else:
            self.data['keyword_stuffing_risk'] = "✓ Low - Natural keyword usage detected"
        
        recommendations = []
        
        if total_all_words < 500:
            recommendations.append("Increase content to minimum 500 words for better topical coverage")
        
        if len(dict_c) < 50:
            recommendations.append("Expand vocabulary diversity for better semantic relevance")
        
        if topic_concentration > 25:
            recommendations.append("Reduce keyword repetition and add supporting LSI keywords")
        
        if any(density > 4.0 for word, density in [(w, (c/total_meaningful_words)*100) for w, c in high[:5]]):
            recommendations.append("Reduce primary keyword usage to under 4% density")
        
        if len(high) >= 2:
            top_two_ratio = high[0][1] / high[1][1] if high[1][1] > 0 else 0
            if top_two_ratio > 3:
                recommendations.append("Balance keyword distribution - top keyword used 3x more than second")
        
        self.data['seo_recommendations'] = recommendations if recommendations else ["✓ Keyword usage appears natural and well-balanced"]
        
        self.conversion = dict(high[:5])
        self.lst = list(self.conversion)
        
        issues = len(stuffing_indicators) + len(recommendations)
        
        if issues == 0 and total_all_words >= 500:
            self.data['density'] = "✓ Excellent - Natural keyword usage with good content depth"
        elif issues <= 2 and total_all_words >= 300:
            self.data['density'] = "✓ Good - Minor improvements recommended"
        else:
            self.data['density'] = "⚠️ Needs Optimization - See recommendations for improvements"
        
        return

    def get_missing_alt(self):
        alt = ""
        images_found = self.soup.find_all('img')
        
        if not images_found:
            self.data['alt_check'] = 0
            self.data['alt_links'] = "No images found on page"
            self.data['alt_verdict'] = "✓ No images to optimize"
            self.alt_count = 0
            return
        
        total_images = len(images_found)
        missing_alt_images = []
        
        for image in images_found:
            try:
                if 'alt' not in image.attrs:
                    missing_alt_images.append(image)
                    alt += f"{self.alt_count + 1}) {str(image)}\n"
                    self.alt_count += 1
                elif image.get('alt', '').strip() == "":
                    if image.get('src'):
                        missing_alt_images.append(image)
                        alt += f"{self.alt_count + 1}) {str(image)}\n"
                        self.alt_count += 1
            except Exception as e:
                logger.error(f"Error processing image tag: {str(e)}")
                missing_alt_images.append(image)
                alt += f"{self.alt_count + 1}) {str(image)}\n"
                self.alt_count += 1
        
        if total_images > 0:
            optimized_images = total_images - self.alt_count
            optimization_percentage = (optimized_images / total_images) * 100
            self.data['image_optimization'] = round(optimization_percentage, 2)
        else:
            self.data['image_optimization'] = 100
        
        self.data['alt_check'] = self.alt_count
        self.data['total_images'] = total_images
        self.data['alt_links'] = alt if alt else "✓ All images have alt attributes"
        
        if self.alt_count == 0:
            self.data['alt_verdict'] = f"✓ Excellent - All {total_images} images have alt attributes"
        elif self.alt_count <= total_images * 0.2:
            self.data['alt_verdict'] = f"⚠️ Good - {self.alt_count} of {total_images} images missing alt text"
        elif self.alt_count <= total_images * 0.5:
            self.data['alt_verdict'] = f"⚠️ Needs Improvement - {self.alt_count} of {total_images} images missing alt text"
        else:
            self.data['alt_verdict'] = f"❌ Critical - {self.alt_count} of {total_images} images missing alt text (Accessibility & SEO issue)"
        
        return


    def get_links(self):
        external_links = ""
        internal_links = ""
        
        base_url = self.base_url
        domain = self.domain
        
        links = self.soup.findAll('a')
        
        self.internal_links = 0
        self.external_links = 0
        
        if len(links) == 0:
            self.data['Internal_links'] = 0
            self.data['External_links'] = 0
            self.data['i_url'] = "No links found on page"
            self.data['e_url'] = "No links found on page"
            self.data['links_verdict'] = "⚠️ No links found - Consider adding internal linking"
            return
        
        broken_links = 0
        nofollow_count = 0
        
        for link in links:
            try:
                href_link = link.get("href", "").strip()
                
                if not href_link or href_link == "":
                    continue
                
                if href_link.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                
                rel = link.get('rel', [])
                if 'nofollow' in rel or 'nofollow' in str(rel).lower():
                    nofollow_count += 1
                
                if href_link.startswith('#'):
                    self.internal_links += 1
                    internal_links += f"{self.internal_links}) {href_link} (anchor link)\n"
                    continue
                
                if href_link.startswith('/'):
                    self.internal_links += 1
                    full_url = urljoin(base_url, href_link)
                    internal_links += f"{self.internal_links}) {full_url}\n"
                    continue
                
                if href_link.startswith('//'):
                    href_link = 'https:' + href_link
                
                try:
                    parsed_href = urlparse(href_link)
                    
                    if not parsed_href.netloc:
                        self.internal_links += 1
                        full_url = urljoin(self.final_url, href_link)
                        internal_links += f"{self.internal_links}) {full_url}\n"
                        continue
                    
                    link_domain = parsed_href.netloc.lower()
                    site_domain = domain.lower()
                    
                    link_domain_clean = link_domain.replace('www.', '')
                    site_domain_clean = site_domain.replace('www.', '')
                    
                    if link_domain_clean == site_domain_clean:
                        self.internal_links += 1
                        internal_links += f"{self.internal_links}) {href_link}\n"
                    else:
                        self.external_links += 1
                        external_links += f"{self.external_links}) {href_link}\n"
                        
                except Exception as e:
                    logger.error(f"Error parsing URL {href_link}: {str(e)}")
                    self.internal_links += 1
                    internal_links += f"{self.internal_links}) {href_link} (parse error)\n"
                    
            except Exception as e:
                logger.error(f"Error processing link: {str(e)}")
                continue
        
        self.data['Internal_links'] = self.internal_links
        self.data['External_links'] = self.external_links
        self.data['i_url'] = internal_links if internal_links else "No internal links found"
        self.data['e_url'] = external_links if external_links else "No external links found"
        self.data['total_links'] = self.internal_links + self.external_links
        self.data['nofollow_links'] = nofollow_count
        
        total_links = self.internal_links + self.external_links
        
        if total_links == 0:
            links_verdict = "⚠️ No links found - Add internal linking for better SEO"
        elif self.internal_links == 0:
            links_verdict = "⚠️ No internal links - Add internal linking structure"
        elif self.internal_links < 3:
            links_verdict = "⚠️ Low internal linking - Increase to improve site structure"
        else:
            if self.external_links == 0:
                links_verdict = f"✓ Good - {self.internal_links} internal links found"
            else:
                ratio = self.internal_links / self.external_links
                if ratio >= 2:
                    links_verdict = f"✓ Excellent - Good internal/external ratio ({self.internal_links}:{self.external_links})"
                elif ratio >= 1:
                    links_verdict = f"✓ Good - Balanced linking ({self.internal_links}:{self.external_links})"
                else:
                    links_verdict = f"⚠️ More external than internal links ({self.internal_links}:{self.external_links}) - Consider more internal linking"
        
        self.data['links_verdict'] = links_verdict
        
        return


    def get_Status(self):
        statuses = {
            200: "Website Available",
            201: "Created",
            204: "No Content",
            301: "Permanent Redirect",
            302: "Temporary Redirect",
            303: "See Other",
            304: "Not Modified",
            307: "Temporary Redirect",
            308: "Permanent Redirect",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            408: "Request Timeout",
            410: "Gone",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        
        try:
            web_response = self.session.get(self.url, timeout=30, allow_redirects=True)
            status_code = web_response.status_code
            status_text = statuses.get(status_code, "Unknown Status")
            
            status = f"{status_code} - {status_text}"
            self.data['status'] = status
            self.data['status_code'] = status_code
            
            if status_code == 200:
                self.data['status_verdict'] = "✓ Excellent - Page loads successfully"
            elif status_code in [301, 302, 307, 308]:
                self.data['status_verdict'] = f"⚠️ Redirect detected - Consider fixing redirect chain"
                if hasattr(self, 'redirect_url') and self.redirect_url:
                    self.data['redirected_to'] = self.redirect_url
            elif status_code == 404:
                self.data['status_verdict'] = "❌ Critical - Page not found (404 error)"
            elif status_code >= 500:
                self.data['status_verdict'] = "❌ Critical - Server error detected"
            elif status_code >= 400:
                self.data['status_verdict'] = "⚠️ Client error - Page may not be accessible"
            else:
                self.data['status_verdict'] = "✓ Page accessible"
                
        except requests.exceptions.Timeout:
            status = "Timeout - Server took too long to respond"
            self.data['status'] = status
            self.data['status_code'] = 0
            self.data['status_verdict'] = "⚠️ Timeout error - Check server performance"
        except requests.exceptions.ConnectionError:
            status = "Connection Error - Cannot reach server"
            self.data['status'] = status
            self.data['status_code'] = 0
            self.data['status_verdict'] = "❌ Cannot connect to server"
        except Exception as e:
            status = f"Error: {str(e)}"
            self.data['status'] = status
            self.data['status_code'] = 0
            self.data['status_verdict'] = "⚠️ Status check failed"
            logger.error(f"Status check error: {str(e)}")
        
        return


    def Score_Graph(self, name, tag, score):
        try:
            score = max(0, min(100, score))
            
            if name == 'Alt_Image':
                if score <= 50:
                    shape1 = 'rgba(0,0,0,0)'
                    shape2 = 'red'
                else:
                    shape1 = 'red'
                    shape2 = 'rgba(0,0,0,0)'
            else:
                if score <= 50:
                    shape1 = 'rgba(0,0,0,0)'
                    shape2 = 'red'
                else:
                    shape1 = 'green'
                    shape2 = 'rgba(0,0,0,0)'
            
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
            
            fig.data[0].textfont.color = 'white'
            
            try:
                fig.write_image(tag)
            except Exception as e:
                logger.error(f"Error saving chart image {tag}: {str(e)}")
                try:
                    html_tag = tag.replace('.png', '.html').replace('.jpg', '.html')
                    fig.write_html(html_tag)
                    logger.info(f"Saved as HTML instead: {html_tag}")
                except Exception as e2:
                    logger.error(f"Could not save chart in any format: {str(e2)}")
            
        except Exception as e:
            logger.error(f"Error creating score graph for {name}: {str(e)}")
        
        return


    def check_robot_txt(self):
        try:
            robots_url = self.base_url.rstrip('/') + '/robots.txt'
            
            try:
                req = self.session.get(robots_url, timeout=10)
                req_text = req.text
                
                valid_patterns = [
                    "User-agent:",
                    "user-agent:",
                    "USER-AGENT:",
                    "Disallow:",
                    "Allow:",
                    "Sitemap:"
                ]
                
                is_valid = any(pattern in req_text for pattern in valid_patterns)
                
                if req.status_code == 200 and is_valid:
                    robot_verdict = "✓ Found - Website has robots.txt file"
                    self.robot_flag = True
                    
                    if "Disallow: /" in req_text and "User-agent: *" in req_text:
                        robot_verdict += " (Warning: Site is blocking all crawlers)"
                        
                    if "Sitemap:" in req_text or "sitemap:" in req_text:
                        self.data['robots_has_sitemap'] = True
                        
                else:
                    robot_verdict = "⚠️ Not Found - Consider adding robots.txt file"
                    self.robot_flag = False
                    
            except requests.exceptions.RequestException as e:
                robot_verdict = "⚠️ Not Found - Consider adding robots.txt file"
                self.robot_flag = False
                logger.error(f"Error checking robots.txt: {str(e)}")
                
        except Exception as e:
            robot_verdict = "⚠️ Error checking robots.txt"
            self.robot_flag = False
            logger.error(f"Unexpected error in robots.txt check: {str(e)}")
        
        self.data['robot'] = robot_verdict
        self.data['robots_url'] = robots_url if 'robots_url' in locals() else None
        
        return


    def get_sitemap(self):
        try:
            base = self.base_url.rstrip('/')
            
            sitemap_paths = [
                '/sitemap.xml',
                '/sitemap_index.xml',
                '/sitemap1.xml',
                '/sitemaps/sitemap.xml',
                '/sitemap/sitemap.xml'
            ]
            
            sitemap_found = False
            sitemap_location = None
            
            for path in sitemap_paths:
                try:
                    sitemap_url = base + path
                    req = self.session.get(sitemap_url, timeout=10)
                    req_text = req.text
                    
                    valid_sitemap = (
                        req.status_code == 200 and
                        (
                            '<urlset' in req_text or
                            '<sitemapindex' in req_text or
                            'sitemap.xml' in req_text.lower()
                        ) and
                        ('<?xml' in req_text or '<urlset' in req_text or '<sitemapindex' in req_text)
                    )
                    
                    if valid_sitemap:
                        sitemap_found = True
                        sitemap_location = sitemap_url
                        self.sitemap_flag = True
                        
                        url_count = req_text.count('<loc>')
                        sitemap_index_count = req_text.count('<sitemap>')
                        
                        if sitemap_index_count > 0:
                            sitemap_verdict = f"✓ Found - Sitemap index with {sitemap_index_count} sitemaps at {path}"
                        elif url_count > 0:
                            sitemap_verdict = f"✓ Found - Sitemap with {url_count} URLs at {path}"
                        else:
                            sitemap_verdict = f"✓ Found - Sitemap at {path}"
                        
                        break
                        
                except requests.exceptions.RequestException:
                    continue
                except Exception as e:
                    logger.error(f"Error checking sitemap at {path}: {str(e)}")
                    continue
            
            if not sitemap_found:
                sitemap_verdict = "⚠️ Not Found - Consider adding XML sitemap for better crawlability"
                self.sitemap_flag = False
                sitemap_verdict += " (Recommended: /sitemap.xml)"
                
        except Exception as e:
            sitemap_verdict = "⚠️ Error checking sitemap"
            self.sitemap_flag = False
            logger.error(f"Unexpected error in sitemap check: {str(e)}")
        
        self.data['sitemap'] = sitemap_verdict
        self.data['sitemap_location'] = sitemap_location if sitemap_found else None
        
        return

    def get_broken_links(self, max_workers: int = 10, timeout: int = 8) -> Dict[str, any]:
        broken_links = []
        restricted_links = []
        working_links = []
        
        try:
            if hasattr(self, 'soup') and self.soup:
                soup = self.soup
            else:
                response = self.session.get(self.url, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            self.data.update({
                'b_links': 0,
                'b_url': f"Error fetching main page: {str(e)}",
                'b_verdict': "Unable to check links"
            })
            return self.data
        
        links = soup.find_all("a", href=True)
        total_links = len(links)
        
        if total_links == 0:
            self.data.update({
                'b_links': 0,
                'b_url': "No links found on this page.",
                'b_verdict': "✓ No links to check"
            })
            return self.data
        
        unique_urls = set()
        link_map = {}
        
        for link in links:
            href = link.get("href", "").strip()
            if not href:
                continue
            
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            if href.startswith('/'):
                href = urljoin(self.base_url, href)
            elif not href.startswith(('http://', 'https://')):
                href = urljoin(self.final_url, href)
            
            if href.startswith(('http://', 'https://')):
                anchor = link.get_text(strip=True) or "[No Text]"
                unique_urls.add(href)
                if href not in link_map:
                    link_map[href] = anchor
        
        if len(unique_urls) == 0:
            self.data.update({
                'b_links': 0,
                'b_url': "No external links found to check.",
                'b_verdict': "✓ No external links"
            })
            return self.data
        
        logger.info(f"Checking {len(unique_urls)} unique links out of {total_links} total links...")
        
        def check_link(url: str) -> Optional[Dict]:
            anchor_text = link_map.get(url, "[No Text]")
            
            try:
                url_domain = urlparse(url).netloc.lower().replace('www.', '')
                site_domain = self.domain.lower().replace('www.', '')
                link_type = "internal" if url_domain == site_domain else "external"
            except (ValueError, AttributeError):
                link_type = "external"
            
            try:
                start_time = time.time()
                try:
                    r = self.session.head(url, timeout=timeout, allow_redirects=True)
                    if r.status_code == 405 or r.status_code == 501:
                        r = self.session.get(url, timeout=timeout, allow_redirects=True, stream=True)
                        r.close()
                except Exception:
                    r = self.session.get(url, timeout=timeout, allow_redirects=True, stream=True)
                    r.close()
                
                response_time = round((time.time() - start_time) * 1000, 2)
                redirects = len(r.history)
                
                if r.status_code == 403:
                    return {
                        "url": url, "status": 403, "reason": "Forbidden / Access Restricted",
                        "anchor_text": anchor_text, "type": link_type,
                        "response_time": f"{response_time} ms", "restricted": True,
                        "is_broken": False, "redirects": redirects
                    }
                
                if 200 <= r.status_code < 300:
                    if redirects > 3:
                        return {
                            "url": url, "status": r.status_code,
                            "reason": f"⚠️ Excessive Redirects ({redirects}x)",
                            "anchor_text": anchor_text, "type": link_type,
                            "response_time": f"{response_time} ms", "restricted": False,
                            "is_broken": True, "redirects": redirects
                        }
                    return {
                        "url": url, "status": r.status_code,
                        "reason": "OK" + (f" (Redirected {redirects}x)" if redirects > 0 else ""),
                        "anchor_text": anchor_text, "type": link_type,
                        "response_time": f"{response_time} ms", "restricted": False,
                        "is_broken": False, "redirects": redirects
                    }
                
                status_reasons = {
                    404: "Not Found", 410: "Gone (Permanently Deleted)",
                    500: "Internal Server Error", 502: "Bad Gateway",
                    503: "Service Unavailable", 504: "Gateway Timeout"
                }
                reason = status_reasons.get(r.status_code, r.reason)
                
                return {
                    "url": url, "status": r.status_code,
                    "reason": reason + (f" (Redirected {redirects}x)" if redirects > 0 else ""),
                    "anchor_text": anchor_text, "type": link_type,
                    "response_time": f"{response_time} ms", "restricted": False,
                    "is_broken": True, "redirects": redirects
                }
                
            except requests.exceptions.SSLError:
                return {"url": url, "status": "SSL Error", "reason": "SSL Certificate Error",
                        "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                        "restricted": False, "is_broken": True, "redirects": 0}
            except requests.exceptions.Timeout:
                return {"url": url, "status": "Timeout", "reason": f"Connection timed out ({timeout}s)",
                        "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                        "restricted": False, "is_broken": True, "redirects": 0}
            except requests.exceptions.ConnectionError:
                return {"url": url, "status": "Connection Error", "reason": "Unable to establish connection",
                        "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                        "restricted": False, "is_broken": True, "redirects": 0}
            except Exception as e:
                return {"url": url, "status": "Error", "reason": str(e)[:100],
                        "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                        "restricted": False, "is_broken": True, "redirects": 0}
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(check_link, unique_urls))
        except Exception as e:
            logger.error(f"Error in concurrent link checking: {str(e)}")
            results = [check_link(url) for url in unique_urls]
        
        for result in results:
            if result is None:
                continue
            if result.get("restricted"):
                restricted_links.append(result)
            elif result.get("is_broken"):
                broken_links.append(result)
            else:
                working_links.append(result)
        
        total_broken = len(broken_links)
        total_working = len(working_links)
        internal_broken = sum(1 for link in broken_links if link["type"] == "internal")
        external_broken = sum(1 for link in broken_links if link["type"] == "external")
        
        error_groups = {
            "404": [], "500": [], "SSL": [], "Timeout": [],
            "Connection": [], "Redirects": [], "Other": []
        }
        
        for link in broken_links:
            status = str(link["status"])
            if "404" in status or "410" in status:
                error_groups["404"].append(link)
            elif "500" in status or "502" in status or "503" in status or "504" in status:
                error_groups["500"].append(link)
            elif "SSL" in status:
                error_groups["SSL"].append(link)
            elif "Timeout" in status:
                error_groups["Timeout"].append(link)
            elif "Connection" in status:
                error_groups["Connection"].append(link)
            elif "Redirects" in link.get("reason", ""):
                error_groups["Redirects"].append(link)
            else:
                error_groups["Other"].append(link)
        
        if total_broken == 0 and len(restricted_links) == 0:
            verdict = "✓ Perfect - No broken links detected"
        elif internal_broken > 0:
            verdict = f"❌ Critical - {internal_broken} internal broken link(s) detected (High SEO Impact)"
        elif total_broken <= 3:
            verdict = f"⚠️ Minor - {total_broken} external broken link(s) found"
        else:
            verdict = f"❌ High Priority - {total_broken} broken links detected (Fix for better UX)"
        
        formatted_broken = "\n".join([
            f"{i+1}) [{link['type'].upper()}] {link['url']}\n"
            f"   Status: {link['status']} - {link['reason']}\n"
            f"   Anchor: {link['anchor_text']}\n"
            f"   Response Time: {link['response_time']}"
            for i, link in enumerate(broken_links[:50])
        ]) if broken_links else "No broken links found."
        
        formatted_restricted = "\n".join([
            f"{i+1}) [{link['type'].upper()}] {link['url']}\n"
            f"   Status: {link['status']} - {link['reason']}\n"
            f"   Anchor: {link['anchor_text']}"
            for i, link in enumerate(restricted_links[:20])
        ]) if restricted_links else "No restricted links found."
        
        health_score = round((total_working / len(unique_urls) * 100), 1) if unique_urls else 0
        
        self.b_links = total_broken
        
        self.data.update({
            'b_links': total_broken,
            'b_url': formatted_broken,
            'b_verdict': verdict,
            'total_links_checked': len(unique_urls),
            'working_links': total_working,
            'internal_broken': internal_broken,
            'external_broken': external_broken,
            'restricted_links_count': len(restricted_links),
            'restricted_links': formatted_restricted,
            'link_health_score': health_score,
            'broken_summary': {
                "404 Not Found": len(error_groups["404"]),
                "500 Server Error": len(error_groups["500"]),
                "SSL Error": len(error_groups["SSL"]),
                "Timeout": len(error_groups["Timeout"]),
                "Connection Error": len(error_groups["Connection"]),
                "Excessive Redirects": len(error_groups["Redirects"]),
                "Other": len(error_groups["Other"])
            },
            'checked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'broken_links_detail': broken_links[:20],
            'priority_fixes': [link for link in broken_links if link["type"] == "internal"]
        })
        
        return self.data


    def get_schema(self):
        try:
            if not hasattr(self, 'soup') or not self.soup:
                try:
                    response = self.session.get(self.url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                except Exception as e:
                    self.data['schema'] = f"Error checking schema: {str(e)}"
                    self.schema_flag = False
                    return
            else:
                soup = self.soup
            
            schema_types = []
            schema_formats = []
            
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            if json_ld_scripts:
                schema_formats.append("JSON-LD")
                for script in json_ld_scripts:
                    try:
                        schema_data = json.loads(script.string)
                        if isinstance(schema_data, dict):
                            schema_type = schema_data.get('@type', '')
                            if schema_type:
                                schema_types.append(schema_type)
                            if '@graph' in schema_data:
                                for item in schema_data['@graph']:
                                    if isinstance(item, dict) and '@type' in item:
                                        schema_types.append(item['@type'])
                        elif isinstance(schema_data, list):
                            for item in schema_data:
                                if isinstance(item, dict) and '@type' in item:
                                    schema_types.append(item['@type'])
                    except json.JSONDecodeError:
                        pass
            
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                script_text = script.string if script.string else ""
                if 'schema.org' in script_text:
                    self.schema_flag = True
                    if "JSON-LD" not in schema_formats:
                        schema_formats.append("Embedded")
                if 'yoast-schema-graph' in str(script.get('class', [])):
                    self.schema_flag = True
                    schema_formats.append("Yoast SEO")
            
            microdata_items = soup.find_all(attrs={"itemtype": True})
            if microdata_items:
                schema_formats.append("Microdata")
                self.schema_flag = True
                for item in microdata_items:
                    itemtype = item.get('itemtype', '')
                    if 'schema.org' in itemtype:
                        type_name = itemtype.split('/')[-1]
                        schema_types.append(type_name)
            
            rdfa_items = soup.find_all(attrs={"vocab": True})
            if rdfa_items:
                for item in rdfa_items:
                    if 'schema.org' in item.get('vocab', ''):
                        schema_formats.append("RDFa")
                        self.schema_flag = True
            
            if self.schema_flag:
                schema_types = list(set(schema_types))
                schema_formats = list(set(schema_formats))
                
                schema_verdict = f"✓ Found - Schema.org structured data detected"
                
                if schema_formats:
                    schema_verdict += f" ({', '.join(schema_formats)})"
                
                if schema_types:
                    top_types = schema_types[:5]
                    self.data['schema_types'] = top_types
                    schema_verdict += f"\nTypes: {', '.join(top_types)}"
                
                recommendations = []
                
                if "JSON-LD" not in schema_formats and schema_formats:
                    recommendations.append("Consider migrating to JSON-LD (Google's preferred format)")
                
                important_types = ['Organization', 'WebSite', 'WebPage', 'Article', 'Product', 
                                'LocalBusiness', 'BreadcrumbList', 'FAQPage']
                
                schema_types_lower = [t.lower() for t in schema_types]
                missing_important = [t for t in important_types if t.lower() not in schema_types_lower]
                
                if missing_important and len(missing_important) <= 3:
                    recommendations.append(f"Consider adding: {', '.join(missing_important[:3])}")
                
                self.data['schema_recommendations'] = recommendations if recommendations else ["Schema implementation looks good"]
                
            else:
                schema_verdict = "⚠️ Not Found - No Schema.org structured data detected"
                self.data['schema_recommendations'] = [
                    "Add JSON-LD structured data for better search visibility",
                    "Recommended types: Organization, WebSite, WebPage, BreadcrumbList",
                    "Use Google's Rich Results Test to validate: https://search.google.com/test/rich-results"
                ]
            
            self.data['schema'] = schema_verdict
            self.data['schema_format'] = schema_formats if schema_formats else None
            
        except Exception as e:
            logger.error(f"Error in schema detection: {str(e)}")
            self.schema_flag = False
            self.data['schema'] = f"⚠️ Error checking schema: {str(e)}"
        
        return


    def get_Open_GP(self):
        try:
            if not hasattr(self, 'soup') or not self.soup:
                try:
                    response = self.session.get(self.url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                except Exception as e:
                    self.data['open_gp'] = f"Error checking Open Graph tags: {str(e)}"
                    self.ogp_flag = False
                    return
            else:
                soup = self.soup
            
            og_tags = {
                'og:title': {'found': False, 'content': None, 'required': True},
                'og:type': {'found': False, 'content': None, 'required': True},
                'og:url': {'found': False, 'content': None, 'required': True},
                'og:image': {'found': False, 'content': None, 'required': True},
                'og:description': {'found': False, 'content': None, 'required': False},
                'og:site_name': {'found': False, 'content': None, 'required': False},
                'og:locale': {'found': False, 'content': None, 'required': False},
                'og:image:width': {'found': False, 'content': None, 'required': False},
                'og:image:height': {'found': False, 'content': None, 'required': False},
                'og:image:alt': {'found': False, 'content': None, 'required': False}
            }
            
            for tag_name in og_tags.keys():
                try:
                    tag = soup.find("meta", property=tag_name)
                    if tag and tag.get("content"):
                        content = tag.get("content", "").strip()
                        if content:
                            og_tags[tag_name]['found'] = True
                            og_tags[tag_name]['content'] = content
                except Exception as e:
                    logger.error(f"Error checking {tag_name}: {str(e)}")
                    continue
            
            found_tags = [tag for tag, data in og_tags.items() if data['found']]
            required_tags = [tag for tag, data in og_tags.items() if data['required']]
            found_required = [tag for tag in required_tags if og_tags[tag]['found']]
            
            total_tags = len(og_tags)
            found_count = len(found_tags)
            
            # ✅ FIX (Social SEO 2026): ogp_flag is True only when the three
            #    content-critical sharing tags are ALL present.  og:type / og:url
            #    are structural but og:title, og:description and og:image are what
            #    social platforms actually render in link previews.
            _SOCIAL_SEO_REQUIRED = {'og:title', 'og:description', 'og:image'}
            self.ogp_flag = all(og_tags[tag]['found'] for tag in _SOCIAL_SEO_REQUIRED)
            
            if len(found_required) == 4:
                open_gp = f"✓ Excellent - All required Open Graph tags found ({found_count}/{total_tags} total)"
                
                if not og_tags['og:image:width']['found'] or not og_tags['og:image:height']['found']:
                    open_gp += "\n⚠️ Tip: Add og:image:width and og:image:height for better image rendering"
                
                if not og_tags['og:description']['found']:
                    open_gp += "\n⚠️ Tip: Add og:description for better social shares"
                    
            elif len(found_required) >= 2:
                missing_required = [tag for tag in required_tags if not og_tags[tag]['found']]
                open_gp = f"⚠️ Partial - {len(found_required)}/4 required OG tags found"
                open_gp += f"\nMissing required: {', '.join(missing_required)}"
                
            elif found_count > 0:
                open_gp = f"⚠️ Incomplete - Found {found_count} OG tags but missing required tags"
                open_gp += f"\nRequired tags: og:title, og:type, og:url, og:image"
                
            else:
                open_gp = "❌ Not Found - No Open Graph Protocol tags detected"
            
            self.data['open_gp'] = open_gp
            self.data['og_tags_found'] = found_tags
            self.data['og_tags_missing'] = [tag for tag, data in og_tags.items() if not data['found']]
            self.data['og_required_complete'] = len(found_required) == 4
            
            og_values = {}
            for tag, data in og_tags.items():
                if data['found'] and data['content']:
                    og_values[tag] = data['content'][:100]
            
            if og_values:
                self.data['og_values'] = og_values
            
            recommendations = []
            
            if not self.ogp_flag:
                recommendations.append("Add all 4 required OG tags: og:title, og:type, og:url, og:image")
                recommendations.append("Recommended image size: 1200x630px for best social media display")
            else:
                if not og_tags['og:description']['found']:
                    recommendations.append("Add og:description (recommended)")
                if not og_tags['og:image:alt']['found']:
                    recommendations.append("Add og:image:alt for accessibility")
            
            self.data['og_recommendations'] = recommendations if recommendations else ["✓ Open Graph implementation is complete"]
            
        except Exception as e:
            logger.error(f"Error in Open Graph detection: {str(e)}")
            self.ogp_flag = False
            self.data['open_gp'] = f"⚠️ Error checking Open Graph tags: {str(e)}"
        
        return


    def get_favicon(self):
        try:
            try:
                icons = favicon.get(self.url, timeout=10)
                
                if icons and len(icons) > 0:
                    icons_sorted = sorted(icons, key=lambda x: (x.width or 0) * (x.height or 0), reverse=True)
                    icon = icons_sorted[0]
                    
                    icon_url = icon.url
                    if not icon_url.startswith(('http://', 'https://')):
                        icon_url = urljoin(self.base_url, icon_url)
                    
                    ext = 'ico'
                    if '.' in icon_url:
                        ext = icon_url.split('.')[-1].split('?')[0].lower()
                        if ext not in ['ico', 'png', 'jpg', 'jpeg', 'gif', 'svg']:
                            ext = 'ico'
                    
                    try:
                        response = self.session.get(icon_url, timeout=5, stream=True)
                        
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > 1024 * 1024:
                            raise ValueError("Favicon too large (>1MB)")
                        
                        filename = f"favicon.{ext}"
                        with open(filename, "wb") as f:
                            downloaded = 0
                            for chunk in response.iter_content(chunk_size=8192):
                                downloaded += len(chunk)
                                if downloaded > 1024 * 1024:
                                    raise ValueError("Favicon too large")
                                f.write(chunk)
                        
                        size_info = ""
                        if icon.width and icon.height:
                            size_info = f" ({icon.width}x{icon.height}px)"
                        
                        Favicon = f"✓ Found - Website has favicon{size_info}"
                        self.icon_flag = True
                        self.data['favicon_url'] = icon_url
                        self.data['favicon_size'] = f"{icon.width}x{icon.height}" if icon.width and icon.height else "Unknown"
                        self.data['favicon_format'] = ext.upper()
                        
                    except Exception as download_error:
                        Favicon = f"✓ Found - Favicon detected at {icon_url} (download failed: {str(download_error)})"
                        self.icon_flag = True
                        self.data['favicon_url'] = icon_url
                        
                else:
                    raise ValueError("No favicon found")
                    
            except Exception as e:
                favicon_locations = [
                    '/favicon.ico',
                    '/favicon.png',
                    '/apple-touch-icon.png',
                    '/apple-touch-icon-precomposed.png'
                ]
                
                favicon_found = False
                for location in favicon_locations:
                    try:
                        favicon_url = self.base_url.rstrip('/') + location
                        response = self.session.head(favicon_url, timeout=5)
                        
                        if response.status_code == 200:
                            Favicon = f"✓ Found - Favicon available at {location}"
                            self.icon_flag = True
                            self.data['favicon_url'] = favicon_url
                            favicon_found = True
                            break
                    except Exception:
                        continue
                
                if not favicon_found:
                    if hasattr(self, 'soup') and self.soup:
                        favicon_links = self.soup.find_all('link', rel=lambda x: x and 'icon' in x.lower())
                        if favicon_links:
                            favicon_href = favicon_links[0].get('href', '')
                            if favicon_href:
                                Favicon = f"✓ Found - Favicon referenced in HTML"
                                self.icon_flag = True
                                self.data['favicon_url'] = urljoin(self.base_url, favicon_href)
                            else:
                                raise ValueError("Favicon link found but no href")
                        else:
                            raise ValueError("No favicon found")
                    else:
                        raise ValueError("No favicon found")
        
        except Exception as e:
            Favicon = f"⚠️ Not Found - No favicon detected"
            self.icon_flag = False
            self.data['favicon_recommendations'] = [
                "Add a favicon.ico file to your website root",
                "Recommended sizes: 16x16, 32x32, 48x48px",
                "Also add apple-touch-icon.png (180x180px) for iOS devices",
                "Use PNG or ICO format for best compatibility"
            ]
        
        self.data['Favicon'] = Favicon
        
        return

    def Social(self):
        social_platforms = {
            "facebook": ["facebook.com/", "fb.com/"],
            "instagram": ["instagram.com/"],
            "twitter": ["twitter.com/", "x.com/"],
            "linkedin": ["linkedin.com/in/", "linkedin.com/company/"],
        }

        self.s_count = 0
        found_links = {key: set() for key in social_platforms}
        verdicts = {}

        try:
            response = self.session.get(self.url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception:
            for platform in social_platforms:
                verdicts[platform] = "Not allowed to scrape!"
            self.data.update(verdicts)
            self.data["social_verdict"] = "Score: 0%"
            self.data["social_links"] = {}
            return

        for tag in soup.find_all("a", href=True):
            raw_link = tag["href"].strip()
            link = raw_link.lower()
            full_link = urljoin(self.url, raw_link)

            for platform, patterns in social_platforms.items():
                matched = False

                if any(p in link for p in patterns):
                    matched = True

                path = urlparse(full_link).path.lower()
                if any(p in path for p in patterns):
                    matched = True

                text = tag.get_text().lower()
                if any(p in text for p in patterns):
                    matched = True

                aria = (tag.get("aria-label") or "").lower()
                title = (tag.get("title") or "").lower()

                if any(p in aria or p in title for p in patterns):
                    matched = True

                if matched:
                    if self._is_valid_social_link(full_link, platform):
                        found_links[platform].add(full_link)

        for platform, links in found_links.items():
            if links:
                verdicts[platform] = f"{platform.capitalize()} found!"
                self.s_count += 25
                setattr(self, f"{platform}_flag", True)
            else:
                verdicts[platform] = f"{platform.capitalize()} not found!"
                setattr(self, f"{platform}_flag", False)

        self.data.update(verdicts)
        self.data["social_links"] = {k: list(v) for k, v in found_links.items()}
        self.data["social_accounts_found"] = sum(1 for v in found_links.values() if v)
        self.data["social_verdict"] = f"Score: {self.s_count}%"

    def _is_valid_social_link(self, link, platform):
        excluded = [
            "sharer.php", "share?", "intent/tweet", 
            "shareArticle", "sharing", "share-button",
            ".js", ".css", "cdn.", "static.",
            "sitemap", ".xml", ".json"
        ]

        if any(exc in link for exc in excluded):
            return False

        parsed = urlparse(link)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        if platform == "twitter":
            return (
                domain in ["twitter.com", "www.twitter.com", "x.com", "www.x.com"]
                and len(path.split("/")) >= 2
                and not path.startswith("/share")
                and not path.startswith("/intent")
            )

        if platform == "facebook":
            return (
                "facebook.com" in domain or "fb.com" in domain
            ) and len(path) > 2

        if platform == "instagram":
            return (
                "instagram.com" in domain
            ) and len(path) > 2

        if platform == "linkedin":
            return (
                "linkedin.com" in domain
            ) and any(x in path for x in ["/in/", "/company/"])

        return False

    def get_technology(self):
        dict={}
        try:
            technology = requests.get(self.url, timeout=15)
            technology.raise_for_status()
            self.webserver = technology.headers.get('Server', 'Not Found!')
            dict['Server']=self.webserver
            self.data['technology']=dict
            self.tech_flag = True if self.webserver != 'Not Found!' else False
        except Exception:
            self.webserver = "Not Found!"
            dict['Server'] = self.webserver
            self.data['technology'] = dict
            self.tech_flag = False
        return


    def Google_Analytics(self):
        a = self.soup.findAll("script", src=True)
        if a ==[]:
            self.data['analytics'] = "Not Found!"
            self.analytics_flag = False
            return
        analytics=""
        found = False
        for i in a:
            src = i.get("src", "")
            if "UA-" in src and "google" in src:
                self.analytics_flag = True
                analytics="Google Analytics found!"
                self.data['analytics'] = analytics
                found = True
                break
        
        if not found:
            analytics = "Google Analytics not found!"
            self.data['analytics'] = analytics
            self.analytics_flag = False



    def w3c_validation(self):
        try:
            vld = HTMLValidator(charset='utf-8')
            vld.validate(self.url)
            error = vld.errors
            warnings = vld.warnings
            self.error_len = len(error)
            self.warn_len = len(warnings)
            self.data['w3c']=("Errors: "+str(self.error_len),"Warnings: "+str(self.warn_len))
        except Exception:
            self.data['w3c']="None"
            self.error_len = 0
            self.warn_len = 0


    def get_content(self):
        try:
            response = requests.get(self.url, timeout=15)
            response.raise_for_status()
            a=response.headers.get('Content-Type', '')
            a=a.split(';')
            try:
                self.Doctype=a[0].strip()
                self.doc_flag = True if self.Doctype else False
            except (IndexError, AttributeError):
                self.Doctype="Not Found!"
                self.doc_flag = False
            try:
                encoding_part = a[1].strip() if len(a) > 1 else ""
                if 'charset=' in encoding_part:
                    self.Encoding = encoding_part.split('=')[1].strip()
                    self.encod_flag = True
                else:
                    self.Encoding = "Not Found!"
                    self.encod_flag = False
            except (IndexError, AttributeError):
                self.Encoding="Not Found!"
                self.encod_flag = False

            self.data['doctype']=self.Doctype
            self.data['encoding']=self.Encoding
        except Exception:
            self.Doctype="Not Found!"
            self.Encoding="Not Found!"
            self.doc_flag = False
            self.encod_flag = False
            self.data['doctype']=self.Doctype
            self.data['encoding']=self.Encoding



    def get_server(self):
        if "https://" in self.url:
            url=self.url.replace("https://","")
        elif "http://" in self.url:
            url=self.url.replace("http://","")
        else:
            url=self.url
        
        url = url.split('/')[0].split('?')[0].strip()
        
        try:
            ip_address = socket.gethostbyname(url)
            g = geocoder.ip(ip_address)
            server_location = g.country if g.country else "Not Found!"
            try:
                hostname = socket.getfqdn(url)
            except Exception:
                hostname = "Not Found!"
            
            if len(ip_address) != 0 and ip_address:
                self.ip=ip_address
                self.ip_flag=True
            else:
                self.ip="Not Found!"
                self.ip_flag=False
            
            if server_location and server_location != "Not Found!":
                self.loc_name=server_location
                self.server_loc_flag=True
            else:
                self.loc_name="Not Found!"
                self.server_loc_flag=False
        except Exception:
            self.ip = "Not Found!"
            self.loc_name = "Not Found!"
            hostname="Not Found!"
            self.ip_flag=False
            self.server_loc_flag=False
        
        self.data['s_ip'] = self.ip
        self.data['s_loc'] = self.loc_name
        self.data['hostname'] = hostname

    def SSL(self):
        import ssl, socket, datetime, requests

        url = self.url.replace("https://", "").replace("http://", "")
        host = url.split("/")[0].split("?")[0].strip()

        self.data['ssl_name'] = "Not Found!"
        self.data['ssl_verdict'] = "Website doesn't have a valid SSL!"
        self.data['ssl_organ'] = "Not Found!"
        self.data['ssl_expiry'] = "Not Found!"
        self.data['http_redir'] = "Not checked"
        self.ssl = False

        try:
            test_urls = [f"http://{host}", f"http://www.{host}"]

            for url in test_urls:
                try:
                    r = requests.get(url, timeout=5, allow_redirects=True)
                    if r.url.startswith("https://"):
                        self.data['http_redir'] = f"Yes, HTTP → HTTPS redirection is enabled ✔ (Final URL: {r.url})"
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

        try:
            context = ssl.create_default_context()
            conn = socket.create_connection((host, 443), timeout=5)
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
        except ssl.CertificateError:
            self.data['ssl_verdict'] = "Hostname mismatch (Invalid SSL)"
            self.ssl = False
        except ssl.SSLError:
            self.data['ssl_verdict'] = "SSL Handshake error (Invalid or broken SSL)"
            self.ssl = False
        except socket.timeout:
            self.data['ssl_verdict'] = "Connection timed out"
            self.ssl = False
        except ConnectionRefusedError:
            self.data['ssl_verdict'] = "SSL not supported on this domain"
            self.ssl = False
        except Exception:
            self.data['ssl_verdict'] = "Could not verify SSL"
            self.ssl = False


    def DMCA(self):
        try:
            response = requests.get(self.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            response.raise_for_status()
            content = response.text

            dmca_pattern = re.compile(r"DMCA|Digital Millennium Copyright Act", re.IGNORECASE)

            if dmca_pattern.search(content):
                self.data['dmca'] = "The website is protected by DMCA."
                self.dmca = True
            else:
                self.data['dmca'] = "The website is not protected by DMCA."
                self.dmca = False

        except requests.exceptions.RequestException as e:
            self.data['dmca'] = f"Error fetching page: {str(e)}"
            self.dmca = False


    async def measure_website_speed(self):
        try:
            start_time = asyncio.get_event_loop().time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url, 
                    headers={"User-Agent": "Mozilla/5.0"}, 
                    timeout=aiohttp.ClientTimeout(total=120)
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
                
        except asyncio.TimeoutError:
            self.speed = 0
            self.data['website_speed'] = 0
            self.data['speed_verdict'] = "The request timed out!"
        except aiohttp.ClientError as e:
            self.speed = 0
            self.data['website_speed'] = 0
            self.data['speed_verdict'] = f"An error occurred: {e}"
        except Exception as e:
            self.speed = 0
            self.data['website_speed'] = 0
            self.data['speed_verdict'] = f"Unexpected error: {e}"

        try:
            API_KEY = getattr(settings, 'PAGESPEED_API_KEY', '')
            
            psi_url_mobile = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={self.url}&strategy=mobile&key={API_KEY}"
            psi_url_desktop = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={self.url}&strategy=desktop&key={API_KEY}"

            def fetch_psi(url): 
                response = requests.get(url, timeout=180)
                response.raise_for_status()
                return response.json()
            
            psi_data = await asyncio.to_thread(fetch_psi, psi_url_mobile)
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

        except requests.exceptions.Timeout:
            logger.error("PageSpeed API request timed out")
            self.data['lcp'] = self.data['cls'] = self.data['inp'] = self.data['full_page_load'] = "Timeout"
            self.data['fcp'] = self.data['tti'] = self.data['tbt'] = "Timeout"
            self.data['performance_score'] = self.data['seo_score'] = 0
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Core Web Vitals: {e}")
            self.data['lcp'] = self.data['cls'] = self.data['inp'] = self.data['full_page_load'] = "Error"
            self.data['fcp'] = self.data['tti'] = self.data['tbt'] = "Error"
            self.data['performance_score'] = self.data['seo_score'] = 0
        except Exception as e:
            logger.error(f"Unexpected error in Core Web Vitals: {e}")
            self.data['lcp'] = self.data['cls'] = self.data['inp'] = self.data['full_page_load'] = "Error"
            self.data['fcp'] = self.data['tti'] = self.data['tbt'] = "Error"
            self.data['performance_score'] = self.data['seo_score'] = 0

    def CSS_minification(self):
        try:
            css_links = []
            soup = BeautifulSoup(self.response, "html.parser")
            
            for link in soup.find_all("link", rel="stylesheet"):
                href = link.get("href")
                if href:
                    if href.startswith('data:') or 'min.css' in href.lower():
                        continue
                    full_url = urljoin(self.url, href)
                    css_links.append(full_url)
            
            inline_styles = soup.find_all("style")
            has_inline_css = len(inline_styles) > 0
            
            if not css_links and not has_inline_css:
                self.data['css_minified'] = "No CSS found to check."
                self.css = True
                return
            
            if not css_links:
                self.data['css_minified'] = "Only inline CSS found (not optimal for caching)."
                self.css = False
                return
            
            total_css = 0
            minified_css = 0
            unminified_files = []
            
            for css_url in css_links[:10]:
                try:
                    r = self.session.get(css_url, timeout=10)
                    r.raise_for_status()
                    css_code = r.text
                    
                    if len(css_code.strip()) < 50:
                        continue
                    
                    total_css += 1
                    compressed_css = csscompressor.compress(css_code)
                    
                    reduction = ((len(css_code) - len(compressed_css)) / len(css_code)) * 100
                    
                    if reduction > 5:
                        unminified_files.append(css_url)
                    else:
                        minified_css += 1
                        
                except requests.RequestException:
                    continue
            
            if total_css == 0:
                self.data['css_minified'] = "Unable to verify CSS minification."
                self.css = False
                return
            
            minification_ratio = (minified_css / total_css) * 100 if total_css > 0 else 0
            
            if minification_ratio >= 80:
                self.data['css_minified'] = f"Good! {minified_css}/{total_css} CSS files are minified ({int(minification_ratio)}%)."
                self.css = True
            elif minification_ratio >= 50:
                self.data['css_minified'] = f"Partial. {minified_css}/{total_css} CSS files are minified ({int(minification_ratio)}%)."
                self.css = False
            else:
                self.data['css_minified'] = f"Poor. Only {minified_css}/{total_css} CSS files are minified ({int(minification_ratio)}%)."
                self.css = False
            
            self.data['inline_css_count'] = len(inline_styles)
            self.data['external_css_count'] = len(css_links)
            
        except Exception as e:
            self.data['css_minified'] = f"Error analyzing CSS: {str(e)}"
            self.css = False

    def JSS_minification(self):
        try:
            js_links = []
            soup = BeautifulSoup(self.response, "html.parser")
            
            for script in soup.find_all("script", src=True):
                src = script.get("src")
                if src:
                    if src.startswith('data:') or 'min.js' in src.lower():
                        continue
                    full_url = urljoin(self.url, src)
                    js_links.append(full_url)
            
            inline_scripts = soup.find_all("script", src=False)
            has_inline_js = len([s for s in inline_scripts if s.string and len(s.string.strip()) > 50]) > 0
            
            if not js_links and not has_inline_js:
                self.data['jss_minified'] = "No JS found to check."
                self.jss = True
                return
            
            if not js_links:
                self.data['jss_minified'] = "Only inline JS found (not optimal for caching)."
                self.jss = False
                return
            
            total_js = 0
            minified_js = 0
            unminified_files = []
            
            for js_url in js_links[:10]:
                try:
                    r = self.session.get(js_url, timeout=10)
                    r.raise_for_status()
                    js_code = r.text
                    
                    if len(js_code.strip()) < 50:
                        continue
                    
                    total_js += 1
                    compressed_js = jsmin(js_code)
                    
                    reduction = ((len(js_code) - len(compressed_js)) / len(js_code)) * 100
                    
                    if reduction > 5:
                        unminified_files.append(js_url)
                    else:
                        minified_js += 1
                        
                except requests.RequestException:
                    continue
            
            if total_js == 0:
                self.data['jss_minified'] = "Unable to verify JS minification."
                self.jss = False
                return
            
            minification_ratio = (minified_js / total_js) * 100 if total_js > 0 else 0
            
            if minification_ratio >= 80:
                self.data['jss_minified'] = f"Good! {minified_js}/{total_js} JS files are minified ({int(minification_ratio)}%)."
                self.jss = True
            elif minification_ratio >= 50:
                self.data['jss_minified'] = f"Partial. {minified_js}/{total_js} JS files are minified ({int(minification_ratio)}%)."
                self.jss = False
            else:
                self.data['jss_minified'] = f"Poor. Only {minified_js}/{total_js} JS files are minified ({int(minification_ratio)}%)."
                self.jss = False
            
            self.data['inline_js_count'] = len([s for s in inline_scripts if s.string and len(s.string.strip()) > 50])
            self.data['external_js_count'] = len(js_links)
            
            render_blocking = []
            for script in soup.find_all("script", src=True):
                if not script.get("async") and not script.get("defer"):
                    render_blocking.append(script.get("src"))
            
            self.data['render_blocking_js'] = len(render_blocking)
            
        except Exception as e:
            self.data['jss_minified'] = f"Error analyzing JS: {str(e)}"
            self.jss = False


    async def Optmized_Plugins(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url, 
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        html_content = await response.read()

                        soup = BeautifulSoup(html_content, 'html.parser')

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
                            self.data['opt_plugins'] = f"Excellent! Website uses {optimization_count} performance optimizations: {', '.join(optimizations_found)}"
                            self.plugins = True
                        elif optimization_count >= 2:
                            self.data['opt_plugins'] = f"Good. Website uses {optimization_count} optimizations: {', '.join(optimizations_found)}"
                            self.plugins = True
                        elif optimization_count > 0:
                            self.data['opt_plugins'] = f"Basic optimizations found: {', '.join(optimizations_found)}"
                            self.plugins = False
                        else:
                            self.data['opt_plugins'] = "No resource optimization techniques detected."
                            self.plugins = False
                    else:
                        self.data['opt_plugins'] = f"Unable to fetch page (HTTP {response.status})"
                        self.plugins = False

        except asyncio.TimeoutError:
            self.data['opt_plugins'] = "The request timed out!"
            self.plugins = False
        except aiohttp.ClientError as e:
            self.data['opt_plugins'] = f"An error occurred: {str(e)}"
            self.plugins = False
        except Exception as e:
            self.data['opt_plugins'] = f"Unexpected error: {str(e)}"
            self.plugins = False

    

    

    def Report(self, dict, output_dir=None):
        """Generate and optionally send SEO report via email"""
        try:
            current_user_email = self._get_user_email(dict)
            
            sender_email = os.getenv('SENDER_EMAIL', '')
            sender_password = os.getenv('SENDER_PASSWORD', '')
            
            if output_dir is None:
                try:
                    from django.conf import settings
                    output_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
                except (ImportError, AttributeError):
                    output_dir = os.path.join(os.getcwd(), 'reports')
            
            send_email = bool(current_user_email)
            
            logger.info(f"Generating report for URL: {dict.get('url', 'Unknown')}")
            result = generate_seo_report(
                data_dict=dict,
                user_email=current_user_email,
                sender_email=sender_email,
                sender_password=sender_password,
                output_dir=output_dir,
                send_email=send_email
            )
            
            if result['success']:
                logger.info(f"Report generated successfully: {result['pdf_path']}")
                if result['email_sent']:
                    logger.info(f"Email sent to: {current_user_email}")
            else:
                logger.error(f"Report generation failed: {result['message']}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in Report method: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'pdf_path': None,
                'email_sent': False,
                'message': error_msg
            }


    def _get_user_email(self, data_dict):
        """Get user email from request or data dict"""
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
        
        logger.warning("No user email found - report will be generated without sending email")
        return None

    def get_data(self):
        # ✅ FIX (Global State): all audit variables live in self.data.
        #    The old Report_variables global dict is replaced by self.data so
        #    concurrent requests for different users never overwrite each other.
        self.data['url'] = self.url
        self.get_title()
        self.get_description()
        self.get_Heading()
        self.get_Google_preview()
        self.get_grammar_analysis()
        self.Keyword_Density()
        self.get_missing_alt()
        self.get_Status()
        self.get_links()
        self.check_robot_txt()
        self.get_sitemap()
        self.get_broken_links()
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
        self.CSS_minification()
        self.JSS_minification()

        async def analyze_and_get_results():
            coroutines = [
                self.measure_website_speed(),
                self.Optmized_Plugins(),
            ]
            await asyncio.gather(*coroutines)

        asyncio.run(analyze_and_get_results())

        # ✅ FIX (Global State): mirror all instance attributes into self.data so
        #    callers (templates, Report method) have a single serialisable dict.
        #    The Report view now reads from self.data instead of Report_variables.
        self.data.setdefault('title',       self.title)
        self.data.setdefault('title_score',  self.title_score)
        self.data.setdefault('desc_score',   self.desc_score)
        self.data.setdefault('H',            self.H)
        self.data.setdefault('heading_score',self.heading_score)
        self.data.setdefault('alt_count',    self.alt_count)
        self.data.setdefault('external_links',self.external_links)
        self.data.setdefault('internal_links',self.internal_links)
        self.data.setdefault('robot_flag',   self.robot_flag)
        self.data.setdefault('sitemap_flag', self.sitemap_flag)
        self.data.setdefault('b_links',      self.b_links)
        self.data.setdefault('icon_flag',    self.icon_flag)
        self.data.setdefault('ogp_flag',     self.ogp_flag)
        self.data.setdefault('tech_flag',    self.tech_flag)
        self.data.setdefault('analytics_flag',self.analytics_flag)
        self.data.setdefault('doc_flag',     self.doc_flag)
        self.data.setdefault('Doctype',      self.Doctype)
        self.data.setdefault('Encoding',     self.Encoding)
        self.data.setdefault('dmca',         self.dmca)
        self.data.setdefault('https',        self.https)
        self.data.setdefault('facebook_flag',self.facebook_flag)
        self.data.setdefault('instagram_flag',self.instagram_flag)
        self.data.setdefault('twitter_flag', self.twitter_flag)
        self.data.setdefault('linkedin_flag',self.linkedin_flag)
        self.data.setdefault('speed',        self.speed)
        self.data.setdefault('css',          self.css)
        self.data.setdefault('jss',          self.jss)
        self.data.setdefault('mob_score',    self.mob_score)
        self.data.setdefault('amp',          self.amp)
        self.data.setdefault('render',       self.render)
        self.data.setdefault('desc',         self.desc)
        self.data.setdefault('heading',      self.heading)
        self.data.setdefault('comp_desc',    self.comp_desc)
        self.data.setdefault('lst',          self.lst)
        self.data.setdefault('comp_head',    self.comp_head)
        self.data.setdefault('conversion',   self.conversion)
        self.data.setdefault('schema_flag',  self.schema_flag)
        self.data.setdefault('s_count',      self.s_count)
        self.data.setdefault('ip_flag',      self.ip_flag)
        self.data.setdefault('ip',           self.ip)
        self.data.setdefault('server_loc_flag',self.server_loc_flag)
        self.data.setdefault('loc_name',     self.loc_name)
        self.data.setdefault('webserver',    self.webserver)
        self.data.setdefault('error_len',    self.error_len)
        self.data.setdefault('warn_len',     self.warn_len)
        self.data.setdefault('encod_flag',   self.encod_flag)
        self.data.setdefault('plugins',      self.plugins)
        self.data.setdefault('mobpreview',   self.mobpreview)
        self.data.setdefault('ssl',          self.ssl)
        self.data.setdefault('ssl_name',     self.data.get('ssl_name', 'Not Found!'))
        self.data.setdefault('ssl_organ',    self.data.get('ssl_organ', 'Not Found!'))
        self.data.setdefault('ssl_expiry',   self.data.get('ssl_expiry', 'Not Found!'))
        # Expose user_email so the Report method can reach it from self.data
        self.data['user_email'] = self.user_email

        return self.data



def sentiment_analysis_page(request):
    return render(request, 'sentiment_analysis.html')


def analyze_sentiment_view(request):
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
                api_key=None,  # let analyze_sentiment pick the right key based on USE_GROQ
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
    if not url:
        return
    obj = Website_Audit(str(url), request=request)
    return obj


def Report(request):
    """Generate and send SEO report.

    ✅ FIX (Global State): Report_variables global dict is gone.  The audit data
    is retrieved by re-running get_data() on a fresh Website_Audit instance whose
    URL comes from the POST/GET parameter, matching how the show() view works.
    The user email flows via self.user_email on the instance.
    """
    try:
        url = request.POST.get('url') or request.GET.get('url', '')
        if not url:
            messages.error(request, 'No URL provided for report generation.')
            return render(request, 'home.html')

        obj = Website_Audit(url, request=request)
        audit_data = obj.get_data()
        result = obj.Report(audit_data)
        
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
            logger.info(f"Report generated: {result['pdf_path']}")
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
def index(request):
    return render(request, 'index.html')

@login_required(login_url='login')
def show(request):
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
        data = upload(request, url)
        data = data.get_data()
        return render(request, 'home.html', data)
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
        # 🔐 Moz API v1 (Linkscape) Authentication with query string
        from urllib.parse import quote
        expires = str(int(time.time()) + 300)
        string_to_sign = f"{access_id}\n{expires}"
        binary_signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        safe_signature = quote(base64.b64encode(binary_signature))

        # Cols bitmask: pda(68719476736) + upa(34359738368) + umrp(16384) + ueid(32) + uid(2048) = 103079233568
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

        result = response.json()

        # 🎯 Extract metrics from v1 API response
        data.update({
            "url": url,
            "da": round(result.get("pda", 0), 2),  # Domain Authority
            "pa": round(result.get("upa", 0), 2),  # Page Authority
            "total_backlinks": result.get("ueid", 0),  # External links
            "linking_root_domains": result.get("uid", 0),  # Root domains linking
            "moz_rank": round(result.get("umrp", 0), 2),  # MozRank
        })

    except requests.exceptions.Timeout:
        messages.error(request, 'Connection timed out. Please try again.')
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Network error: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')

    return render(request, 'seo_metrics.html', data)

@login_required(login_url='login')
def mobiletest(request):
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

        api_data = {}
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

            # PageSpeed Insights runs full Lighthouse on Google's servers and can
            # take 60-90s for slow/mobile pages. Use a generous timeout + one retry
            # so transient slowness doesn't break the Mobile-Friendly Test.
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
                logger.warning(f"PageSpeed API error {response.status_code}: {error_detail}")
                data["lighthouse_error"] = f"PageSpeed API error ({response.status_code}): {error_detail}"
                raise Exception(data["lighthouse_error"])

            api_data = response.json()
            lh = api_data.get("lighthouseResult", {}).get("categories", {})

            if not lh:
                logger.warning(f"PageSpeed API returned no lighthouseResult: {api_data}")
                raise Exception("PageSpeed API returned no Lighthouse data.")

            data.update({
                "performance_score": round((lh.get("performance", {}).get("score") or 0) * 100),
                "accessibility_score": round((lh.get("accessibility", {}).get("score") or 0) * 100),
                "best_practices_score": round((lh.get("best-practices", {}).get("score") or 0) * 100),
                "seo_score": round((lh.get("seo", {}).get("score") or 0) * 100),
                "pwa_score": lh.get("pwa", {}).get("score", None)
            })
        except Exception as e:
            logger.warning(f"Lighthouse fetch error: {e}")
            if "lighthouse_error" not in data:
                data["lighthouse_error"] = str(e)
            data.update({
                "performance_score": None,
                "accessibility_score": None,
                "best_practices_score": None,
                "seo_score": None,
                "pwa_score": None
            })


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
                    except (ValueError, AttributeError):
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

        data["url"] = url
        return render(request, "mobiletest.html", data)
    except requests.exceptions.Timeout:
        messages.error(request, "Request timed out")
        return render(request, "mobiletest.html")

    except Exception as e:
        messages.error(request, str(e))
        return render(request, "mobiletest.html")

@login_required(login_url='login')
def robot(request):
    try:
        if request.method=="GET":
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

        data={}
        data['content']=content
        data["url"]=url
        return render(request, 'robot.html', data)
    except requests.exceptions.Timeout as e:
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'robot.html')
    except requests.exceptions.RequestException as e:
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'robot.html')

@login_required(login_url='login')
def keyPosition(request):
    from googlesearch import search
    try:
        if request.method == 'GET':
            return render(request, 'keyPosition.html')

        data = {}
        url = request.POST.get("url")
        keyword = request.POST.get("keyword")

        data['url'] = url
        data['keyword'] = keyword

        if not url or not keyword or not validators.url(url):
            data.clear()
            return render(request, 'keyPosition.html', data)


        def check_url(url):
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            if not re.search(r'www\.', url):
                url = url.replace("://", "://www.")
            if not url.endswith('/'):
                url += '/'
            return url

        url1=check_url(url)

        data["url"] = url1
        data["keyword"]= keyword


        def find_link_position(keyword, link):
            search_results = list(search(keyword, num_results=10))
            for position, url in enumerate(search_results, 1):
                if url == link:
                    return position
            return -1

        position = find_link_position(keyword, url1)
        if position != -1:
            data['rank']=f"The link '{url1}' is found at position {position} in the results."
        else:
            data['rank']=f"The link '{url1}' is not found in the top 10 search results."

        return render(request, 'keyPosition.html',data)
    except requests.exceptions.Timeout as e:
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'keyPosition.html')
    except requests.exceptions.RequestException as e:
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'keyPosition.html')

@login_required(login_url='login')
def keysuggestion(request):
    try:
        if request.method=="GET":
            return render(request, 'keysuggestion.html')
        data={}
        keyword = request.POST.get("fname", "").strip()
        word_regex = re.compile(r'^[A-Za-z]+$')

        if keyword == '' or not word_regex.match(keyword):
            data.clear()
            return render(request, 'keysuggestion.html', data)
        url = f"http://suggestqueries.google.com/complete/search?output=firefox&q={keyword}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers)
        suggestions = response.json()[1]
        keywords = ""
        for i in suggestions:
            keywords += i + "\n"
        data["keywords"]=keywords
        data["keyword"]=keyword
        return render(request, 'keysuggestion.html',data)
    except requests.exceptions.Timeout as e:
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'keysuggestion.html')
    except requests.exceptions.RequestException as e:
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'keysuggestion.html')

@login_required(login_url='login')
def keyword_ai_suggestions(request):
    """
    AI-Powered Keyword Suggestion using keyword_ai pipeline.
    Analyzes URL or text to extract, expand, and rank keywords using ML.
    """
    try:
        if request.method == "GET":
            return render(request, 'keyword_ai_suggestions.html')
        
        data = {}
        url = request.POST.get("url", "").strip()
        text = request.POST.get("text", "").strip()
        page_topic = request.POST.get("page_topic", "").strip()
        use_llm = request.POST.get("use_llm", "true").lower() != "false"
        
        # Validate input
        if not url and not text:
            messages.error(request, 'Please provide either a URL or text content.')
            return render(request, 'keyword_ai_suggestions.html', data)
        
        # Run the AI pipeline v2 with all advanced features
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
        
        # Prepare data for template
        data["url"] = url
        data["text"] = text[:200] + "..." if len(text) > 200 else text
        data["page_topic"] = page_topic
        data["page_title"] = result.get("page_title", "")
        data["relevant_keywords"] = result.get("relevant_keywords", [])
        data["scored_keywords"] = result.get("scored_keywords", [])[:20]  # Top 20
        data["intent_groups"] = result.get("intent_groups", {})
        data["focus_keywords"] = result.get("focus_keywords", [])
        data["keybert_keywords"] = result.get("keybert_keywords", [])[:10]
        data["expanded_keywords"] = result.get("expanded_keywords", [])[:10]
        
        # Phase 2 ML features
        data["ml_generated_suggestions"] = result.get("ml_generated_suggestions", [])[:15]
        data["semantic_keywords"] = result.get("semantic_keywords", [])[:15]
        data["tfidf_keywords"] = result.get("tfidf_keywords", [])[:10]
        
        # Phase 3 AI features
        data["ai_expanded_keywords"] = result.get("ai_expanded_keywords", [])[:10]
        data["question_keywords"] = result.get("question_keywords", [])[:8]
        data["intent_classifications"] = result.get("intent_classifications", [])
        data["content_analysis"] = result.get("content_analysis", {})
        
        data["keyword_count"] = len(result.get("relevant_keywords", []))
        
        # Fetch or create opportunity IDs for feedback buttons
        try:
            from keyword_ai.models import ContentAnalysis, KeywordOpportunity
            content_analysis = ContentAnalysis.objects.filter(url=url).order_by('-analyzed_at').first()
            if content_analysis:
                # Get existing opportunities
                opportunities = {
                    opp.keyword: opp.id
                    for opp in KeywordOpportunity.objects.filter(content_analysis=content_analysis)
                }
                # Create opportunities for keywords that don't have them
                for item in data["scored_keywords"]:
                    keyword = item["keyword"]
                    if keyword in opportunities:
                        item["opportunity_id"] = opportunities[keyword]
                    else:
                        # Create new opportunity for this keyword
                        opp = KeywordOpportunity.objects.create(
                            content_analysis=content_analysis,
                            keyword=keyword,
                            keyword_type=item.get("type", "tfidf"),
                            relevance_score=item.get("relevance_score", item.get("score", 50)),
                            search_volume_estimate=item.get("search_volume", "Unknown"),
                            difficulty_score=item.get("difficulty", 50),
                            intent=item.get("intent", "informational"),
                            priority="medium",
                        )
                        item["opportunity_id"] = opp.id
                        opportunities[keyword] = opp.id
        except Exception as e:
            logger.warning(f"Could not create opportunity IDs: {e}")
        
        messages.success(request, f'Successfully analyzed and found {data["keyword_count"]} relevant keywords!')
        return render(request, 'keyword_ai_suggestions.html', data)
        
    except Exception as e:
        logger.error(f"Keyword AI analysis failed: {str(e)}")
        messages.error(request, f'Analysis failed: {str(e)}')
        return render(request, 'keyword_ai_suggestions.html')

def loginuser(request):
    # ✅ FIX (Global State): removed `global current_user_email`.
    #    The email is available anywhere via request.user.email after login()
    #    and is stored on Website_Audit instances via self.user_email.
    if request.method == 'POST':
        username = request.POST.get('username')
        pass1 = request.POST.get('pass')
        if username == '' or pass1 == '':
            messages.error(request, 'Please fill to Proceed!')
            return redirect('login')
        user = authenticate(request, username=username, password=pass1)
        if user is not None:
            login(request, user)
            return redirect('Home')
        else:
            messages.error(request, 'Invalid Credentials!')
            return redirect('login')
    return render(request, 'fyplogin.html')

def register(request):

    def is_valid_email(email):
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(regex, email))

    dict={}
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('FirstName')
        last_name = request.POST.get('LastName')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        dict['username'] = username
        dict['firstname'] = first_name
        dict['lastname'] = last_name
        dict['email'] = email

        if not all([username, email, first_name, last_name, password1, password2]):
            messages.error(request, 'Please fill in all the fields!')
            return render(request, 'register.html',dict)

        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'register.html',dict)

        if not is_valid_email(email):
            messages.error(request, 'Please enter a valid email address!')
            return render(request, 'register.html',dict)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered!')
            del dict['email']
            return render(request, 'register.html',dict)

        try:
            user = User.objects.create_user(username, email, password1, first_name=first_name, last_name=last_name)
            profile = Profile.objects.create(user=user)
            return redirect('login')
        except (IntegrityError, DatabaseError):
            messages.error(request, 'This User already exist!')
            return render(request, 'register.html')

    return render(request, 'register.html')

@never_cache
def logoutuser(request):
    logout(request)
    response = redirect('login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def ChangePassword(request, token):
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
        logger.error(f'ChangePassword error: {str(e)}')
    return render(request, 'change-password.html', context)


def ForgetPassword(request):
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
        logger.error(f'ForgetPassword error: {str(e)}')
        messages.error(request, 'An error occurred. Please try again.')

    return render(request, 'forget-password.html')
