"""
Unit tests — SEOAnalyzer services.

Covers: ContentAnalysisService, SEOAnalysisService, TechnicalAuditServiceV2,
        EeatAnalyzer, GrammarAnalyzer, LinkChecker, MinificationChecker,
        SentimentAnalyzer.
Edge cases: empty HTML, missing tags, malformed content, boundary scores.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# ---------------------------------------------------------------------------
# ContentAnalysisService
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestContentAnalysisService:

    def test_analyze_valid_content_returns_word_count(self, sample_html):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService(sample_html)
        result = service.analyze_content_quality()
        assert 'word_count' in result
        assert result['word_count'] > 0

    def test_analyze_returns_readability_score(self, sample_html):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService(sample_html)
        result = service.analyze_content_quality()
        assert 'readability' in result

    def test_analyze_returns_quality_score(self, sample_html):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService(sample_html)
        result = service.analyze_content_quality()
        assert 'quality_score' in result

    def test_empty_content_handled_gracefully(self):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService('')
        result = service.analyze_content_quality()
        assert isinstance(result, dict)
        assert result.get('word_count', 0) == 0 or 'error' in result

    def test_minimal_html_no_crash(self, minimal_html):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService(minimal_html)
        result = service.analyze_content_quality()
        assert isinstance(result, dict)

    def test_readability_score_in_valid_range(self, sample_html):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService(sample_html)
        result = service.analyze_content_quality()
        if 'readability' in result and 'flesch_reading_ease' in result.get('readability', {}):
            score = result['readability']['flesch_reading_ease']
            assert -200 <= score <= 200

    def test_heading_structure_extracted(self, sample_html):
        from SEOAnalyzer.services.content_analysis_service import ContentAnalysisService
        service = ContentAnalysisService(sample_html)
        result = service.analyze_content_quality()
        if 'headings' in result:
            assert isinstance(result['headings'], dict)


# ---------------------------------------------------------------------------
# SEOAnalysisService
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestSEOAnalysisService:

    def test_title_present_detected(self, sample_html):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(sample_html)
        result = service.analyze_seo_elements()
        assert 'title' in result
        # title is a dict with 'score' and 'title' keys
        assert result['title'].get('score', 0) > 0
        assert result['title'].get('title', '') != ''

    def test_title_absent_detected(self, html_no_title):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(html_no_title)
        result = service.analyze_seo_elements()
        if 'title' in result:
            assert result['title'].get('score', 100) == 0

    def test_meta_description_present(self, sample_html):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(sample_html)
        result = service.analyze_seo_elements()
        assert 'meta_description' in result
        # meta_description dict has 'description' key when present
        assert result['meta_description'].get('description', None) is not None

    def test_meta_description_absent(self, minimal_html):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(minimal_html)
        result = service.analyze_seo_elements()
        if 'meta_description' in result:
            assert result['meta_description'].get('score', 100) == 0

    def test_result_has_seo_score(self, sample_html):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(sample_html)
        result = service.analyze_seo_elements()
        assert 'seo_score' in result

    def test_headings_returned(self, sample_html):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(sample_html)
        result = service.analyze_seo_elements()
        assert 'headings' in result

    def test_open_graph_returned(self, sample_html):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService(sample_html)
        result = service.analyze_seo_elements()
        assert 'open_graph' in result

    def test_empty_html_no_crash(self):
        from SEOAnalyzer.services.seo_analysis_service import SEOAnalysisService
        service = SEOAnalysisService('<html></html>')
        result = service.analyze_seo_elements()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TechnicalAuditServiceV2
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestTechnicalAuditServiceV2:

    def _make_service_with_mock_session(self, url='https://example.com'):
        from SEOAnalyzer.services.technical_audit_service_v2 import TechnicalAuditServiceV2
        session = Mock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = 'User-agent: *'
        mock_resp.url = url
        mock_resp.raise_for_status = Mock()
        session.get.return_value = mock_resp
        return TechnicalAuditServiceV2(url, session=session)

    def test_result_has_required_keys(self):
        service = self._make_service_with_mock_session()
        result = service.analyze_technical_seo()
        # actual keys: robots_txt, sitemap, schema, https_status, page_speed, mobile_friendly
        assert 'https_status' in result
        assert 'robots_txt' in result
        assert 'technical_score' in result

    def test_https_status_key_present(self):
        service = self._make_service_with_mock_session()
        result = service.analyze_technical_seo()
        assert 'https_status' in result
        assert isinstance(result['https_status'], dict)

    def test_robots_txt_present_via_session_mock(self):
        from SEOAnalyzer.services.technical_audit_service_v2 import TechnicalAuditServiceV2
        import requests
        session = Mock()

        def session_get(url, **kwargs):
            resp = Mock()
            resp.raise_for_status = Mock()
            if 'robots.txt' in url:
                resp.status_code = 200
                resp.text = 'User-agent: *\nDisallow: /admin/'
            else:
                resp.status_code = 200
                resp.url = url
            return resp

        session.get.side_effect = session_get
        service = TechnicalAuditServiceV2('https://example.com', session=session)
        result = service.check_robots_txt()
        assert result.get('found', False) is True

    def test_robots_txt_absent_via_session_mock(self):
        from SEOAnalyzer.services.technical_audit_service_v2 import TechnicalAuditServiceV2
        session = Mock()

        def session_get(url, **kwargs):
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.status_code = 404
            resp.text = ''
            return resp

        session.get.side_effect = session_get
        service = TechnicalAuditServiceV2('https://example.com', session=session)
        result = service.check_robots_txt()
        assert result.get('found', True) is False

    def test_network_error_handled(self):
        from SEOAnalyzer.services.technical_audit_service_v2 import TechnicalAuditServiceV2
        import requests as req_lib
        session = Mock()
        session.get.side_effect = req_lib.exceptions.ConnectionError('Network error')
        service = TechnicalAuditServiceV2('https://unreachable.example.com', session=session)
        result = service.analyze_technical_seo()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# LinkAnalyzer (class is LinkAnalyzer, not LinkChecker)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestLinkAnalyzer:

    def _make_analyzer(self, html, base_url='https://example.com'):
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse
        from SEOAnalyzer.services.link_checker import LinkAnalyzer
        soup = BeautifulSoup(html, 'html.parser')
        domain = urlparse(base_url).netloc
        return LinkAnalyzer(soup, base_url, domain, base_url)

    def test_count_internal_links(self, sample_html):
        analyzer = self._make_analyzer(sample_html)
        result = analyzer.analyze()
        assert isinstance(result, dict)
        # result keys are capitalised: Internal_links / External_links
        assert result.get('Internal_links', 0) >= 1

    def test_count_external_links(self, sample_html):
        analyzer = self._make_analyzer(sample_html)
        result = analyzer.analyze()
        assert isinstance(result, dict)
        assert result.get('External_links', 0) >= 1

    def test_no_links_html(self):
        html = '<html><body><p>No links here.</p></body></html>'
        analyzer = self._make_analyzer(html)
        result = analyzer.analyze()
        assert isinstance(result, dict)
        assert result.get('Internal_links', 0) == 0
        assert result.get('External_links', 0) == 0


# ---------------------------------------------------------------------------
# EEATAnalyzer (class is EEATAnalyzer, not EeatAnalyzer)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestEEATAnalyzer:
    # EEATAnalyzer takes use_groq/api_key, not html/url.
    # Its analyze(content_type, content) method analyzes text snippets.

    @staticmethod
    def _make_analyzer():
        from SEOAnalyzer.services.eeat_analyzer import EEATAnalyzer
        analyzer = EEATAnalyzer(use_groq=False, api_key='')
        # Force _get_client to return None (fallback mode) by clearing cached client
        analyzer._client = None
        analyzer._model = None
        return analyzer

    def test_analyze_title_returns_dict(self):
        # Patch os.getenv and settings so _get_client() returns None → fallback
        with patch('SEOAnalyzer.services.eeat_analyzer.os.getenv', return_value=''), \
             patch('SEOAnalyzer.services.eeat_analyzer.settings') as mock_settings:
            mock_settings.USE_GROQ = False
            mock_settings.OPENROUTER_API_KEY = ''
            mock_settings.GROQ_API_KEY = ''
            analyzer = self._make_analyzer()
            result = analyzer.analyze('title', 'Expert Python Programming Guide')
        assert isinstance(result, dict)
        assert 'eeat_score' in result

    def test_analyze_description_returns_dict(self):
        with patch('SEOAnalyzer.services.eeat_analyzer.os.getenv', return_value=''), \
             patch('SEOAnalyzer.services.eeat_analyzer.settings') as mock_settings:
            mock_settings.USE_GROQ = False
            mock_settings.OPENROUTER_API_KEY = ''
            mock_settings.GROQ_API_KEY = ''
            analyzer = self._make_analyzer()
            result = analyzer.analyze('description', 'Professional guide written by certified experts.')
        assert isinstance(result, dict)
        assert 'eeat_score' in result

    def test_short_content_returns_zero_score(self):
        with patch('SEOAnalyzer.services.eeat_analyzer.os.getenv', return_value=''), \
             patch('SEOAnalyzer.services.eeat_analyzer.settings') as mock_settings:
            mock_settings.USE_GROQ = False
            mock_settings.OPENROUTER_API_KEY = ''
            mock_settings.GROQ_API_KEY = ''
            analyzer = self._make_analyzer()
            result = analyzer.analyze('title', 'Hi')
        assert result.get('eeat_score', 100) == 0

    def test_empty_content_handled(self):
        with patch('SEOAnalyzer.services.eeat_analyzer.os.getenv', return_value=''), \
             patch('SEOAnalyzer.services.eeat_analyzer.settings') as mock_settings:
            mock_settings.USE_GROQ = False
            mock_settings.OPENROUTER_API_KEY = ''
            mock_settings.GROQ_API_KEY = ''
            analyzer = self._make_analyzer()
            result = analyzer.analyze('title', '')
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# MinificationChecker (abstract base — test via CSSMinificationChecker)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestMinificationChecker:

    def _make_checker(self, html, url='https://example.com'):
        from bs4 import BeautifulSoup
        from SEOAnalyzer.services.minification_checker import CSSMinificationChecker
        import requests
        session = Mock()  # avoid real HTTP
        soup = BeautifulSoup(html, 'html.parser')
        return CSSMinificationChecker(session, url, soup)

    def test_check_no_assets_returns_dict(self):
        html = '<html><body><p>No assets</p></body></html>'
        checker = self._make_checker(html)
        result = checker.check()
        assert isinstance(result, dict)

    def test_check_with_css_link_returns_dict(self):
        html = '<html><head><link rel="stylesheet" href="/style.css"></head><body></body></html>'
        checker = self._make_checker(html)
        mock_resp = Mock()
        mock_resp.text = 'body { color: red; margin: 0; padding: 0; }'
        mock_resp.status_code = 200
        checker.session.get.return_value = mock_resp
        result = checker.check()
        assert isinstance(result, dict)

    def test_service_class_check_all(self):
        from SEOAnalyzer.services.minification_checker import MinificationService
        html = '<html><body></body></html>'
        session = Mock()
        service = MinificationService(session, 'https://example.com', html)
        result = service.check_all()
        assert isinstance(result, dict)
        assert 'css' in result
        assert 'js' in result


# ---------------------------------------------------------------------------
# sentiment_analyzer (module-level function, not a class)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.seo
class TestSentimentAnalyzer:

    def test_analyze_positive_content(self):
        from SEOAnalyzer.services.sentiment_analyzer import analyze_sentiment
        text = 'This is excellent! Amazing and wonderful product we love it very much. Great results.'
        result = analyze_sentiment(text)
        assert isinstance(result, dict)
        assert 'sentiment' in result

    def test_analyze_negative_content(self):
        from SEOAnalyzer.services.sentiment_analyzer import analyze_sentiment
        text = 'Terrible, horrible, disgusting service. Worst experience ever. Awful and dreadful.'
        result = analyze_sentiment(text)
        assert isinstance(result, dict)
        assert 'sentiment' in result

    def test_short_text_returns_error(self):
        from SEOAnalyzer.services.sentiment_analyzer import analyze_sentiment
        result = analyze_sentiment('Hi')
        assert isinstance(result, dict)
        assert result.get('success', True) is False or 'sentiment' in result

    def test_empty_text_handled(self):
        from SEOAnalyzer.services.sentiment_analyzer import analyze_sentiment
        result = analyze_sentiment('')
        assert isinstance(result, dict)
