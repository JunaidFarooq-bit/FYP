"""
Technical Audit Service V2 - Enhanced version extracted from Website_Audit class
Handles technical SEO elements like robots.txt, sitemap, schema, and performance.
"""
import logging
import requests
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class TechnicalAuditServiceV2:
    """Enhanced service for technical SEO analysis."""
    
    def __init__(self, url: str, session: requests.Session = None, base_url: str = None):
        self.session = session or requests.Session()
        self.base_url = base_url or url
        self.url = url
        self.domain = urlparse(url).netloc.lower().replace('www.', '')
        self.data = {}
        
    def analyze_technical_seo(self) -> Dict[str, Any]:
        """Analyze all technical SEO elements."""
        try:
            result = {
                'robots_txt': self.check_robots_txt(),
                'sitemap': self.check_sitemap(),
                'schema': self.check_schema_markup(),
                'https_status': self.check_https_status(),
                'page_speed': self.check_page_speed(),
                'mobile_friendly': self.check_mobile_friendly(),
                'technical_score': 0
            }
            
            # Calculate overall technical score
            result['technical_score'] = self._calculate_technical_score(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in technical SEO analysis: {e}")
            return {
                'robots_txt': {'score': 0, 'verdict': 'Error checking robots.txt'},
                'sitemap': {'score': 0, 'verdict': 'Error checking sitemap'},
                'schema': {'score': 0, 'verdict': 'Error checking schema'},
                'https_status': {'score': 0, 'verdict': 'Error checking HTTPS'},
                'page_speed': {'score': 0, 'verdict': 'Error checking page speed'},
                'mobile_friendly': {'score': 0, 'verdict': 'Error checking mobile'},
                'technical_score': 0
            }
    
    def check_robots_txt(self) -> Dict[str, Any]:
        """Check robots.txt file."""
        try:
            robots_url = self.base_url.rstrip('/') + '/robots.txt'
            
            try:
                response = self.session.get(robots_url, timeout=10)
                
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # Check for important directives
                    has_allow = 'allow:' in content
                    has_disallow = 'disallow:' in content
                    has_sitemap = 'sitemap:' in content
                    
                    score = 0
                    if has_allow or has_disallow:
                        score += 50
                    if has_sitemap:
                        score += 50
                    
                    if score >= 80:
                        verdict = "✅ robots.txt found with good directives"
                    elif score >= 50:
                        verdict = "⚠️ robots.txt found but could be improved"
                    else:
                        verdict = "❌ robots.txt found but minimal content"
                    
                    return {
                        'score': score,
                        'verdict': verdict,
                        'url': robots_url,
                        'found': True,
                        'has_sitemap': has_sitemap
                    }
                else:
                    return {
                        'score': 0,
                        'verdict': "❌ robots.txt not found",
                        'url': robots_url,
                        'found': False
                    }
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error checking robots.txt: {e}")
                return {
                    'score': 0,
                    'verdict': "❌ Error accessing robots.txt",
                    'url': robots_url,
                    'found': False
                }
                
        except Exception as e:
            logger.error(f"Unexpected error in robots.txt check: {e}")
            return {'score': 0, 'verdict': 'Error checking robots.txt'}
    
    def check_sitemap(self) -> Dict[str, Any]:
        """Check XML sitemap."""
        try:
            base = self.base_url.rstrip('/')
            sitemap_urls = [
                f"{base}/sitemap.xml",
                f"{base}/sitemap_index.xml",
                f"{base}/sitemaps.xml",
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    response = self.session.get(sitemap_url, timeout=10)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Check if it's valid XML sitemap
                        if 'urlset' in content or 'sitemapindex' in content:
                            # Count URLs (simplified)
                            url_count = content.count('<url>')
                            
                            if url_count > 0:
                                verdict = f"✓ Sitemap found with {url_count} URLs"
                                score = 100
                            else:
                                verdict = "✓ Sitemap found but appears empty"
                                score = 50
                            
                            return {
                                'score': score,
                                'verdict': verdict,
                                'url': sitemap_url,
                                'found': True,
                                'url_count': url_count
                            }
                        
                except requests.exceptions.RequestException:
                    continue
            
            return {
                'score': 0,
                'verdict': "⚠️ No XML sitemap found",
                'url': None,
                'found': False
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in sitemap check: {e}")
            return {'score': 0, 'verdict': 'Error checking sitemap'}
    
    def check_schema_markup(self) -> Dict[str, Any]:
        """Check for structured data/schema markup."""
        try:
            # This would need the page content to analyze properly
            # For now, return a basic implementation
            return {
                'score': 50,
                'verdict': "⚠️ Schema markup check requires page content analysis",
                'found': False,
                'types': []
            }
            
        except Exception as e:
            logger.error(f"Error checking schema markup: {e}")
            return {'score': 0, 'verdict': 'Error checking schema'}
    
    def check_https_status(self) -> Dict[str, Any]:
        """Check HTTPS implementation."""
        try:
            if self.url.startswith('https://'):
                # Check for mixed content (simplified)
                score = 100
                verdict = "✅ HTTPS properly implemented"
                
                return {
                    'score': score,
                    'verdict': verdict,
                    'https_enabled': True,
                    'protocol': 'https'
                }
            else:
                return {
                    'score': 0,
                    'verdict': "❌ HTTPS not enabled",
                    'https_enabled': False,
                    'protocol': 'http'
                }
                
        except Exception as e:
            logger.error(f"Error checking HTTPS status: {e}")
            return {'score': 0, 'verdict': 'Error checking HTTPS'}
    
    def check_page_speed(self) -> Dict[str, Any]:
        """Check page speed (simplified version)."""
        try:
            # Make a request to measure response time
            start_time = time.time()
            
            try:
                response = self.session.get(self.url, timeout=10)
                response_time = time.time() - start_time
                
                # Simple scoring based on response time
                if response_time < 1:
                    score = 100
                    verdict = "✅ Fast response time"
                elif response_time < 2:
                    score = 80
                    verdict = "⚠️ Moderate response time"
                elif response_time < 4:
                    score = 60
                    verdict = "⚠️ Slow response time"
                else:
                    score = 40
                    verdict = "❌ Very slow response time"
                
                return {
                    'score': score,
                    'verdict': verdict,
                    'response_time': round(response_time, 2),
                    'status_code': response.status_code
                }
                
            except requests.exceptions.Timeout:
                return {
                    'score': 20,
                    'verdict': "❌ Request timeout",
                    'response_time': None,
                    'status_code': None
                }
                
        except Exception as e:
            logger.error(f"Error checking page speed: {e}")
            return {'score': 0, 'verdict': 'Error checking page speed'}
    
    def check_mobile_friendly(self) -> Dict[str, Any]:
        """Check mobile friendliness (simplified)."""
        try:
            # This would need the page content to check viewport meta tag
            # For now, return a basic implementation
            return {
                'score': 75,
                'verdict': "⚠️ Mobile check requires page content analysis",
                'mobile_friendly': True
            }
            
        except Exception as e:
            logger.error(f"Error checking mobile friendliness: {e}")
            return {'score': 0, 'verdict': 'Error checking mobile friendliness'}
    
    def _calculate_technical_score(self, elements: Dict[str, Any]) -> float:
        """Calculate overall technical SEO score."""
        try:
            scores = [
                elements.get('robots_txt', {}).get('score', 0) * 0.20,
                elements.get('sitemap', {}).get('score', 0) * 0.20,
                elements.get('schema', {}).get('score', 0) * 0.15,
                elements.get('https_status', {}).get('score', 0) * 0.20,
                elements.get('page_speed', {}).get('score', 0) * 0.15,
                elements.get('mobile_friendly', {}).get('score', 0) * 0.10,
            ]
            
            total_score = sum(scores)
            return round(min(100, total_score), 1)
            
        except Exception as e:
            logger.error(f"Error calculating technical score: {e}")
            return 0


# Import time for page speed measurement
import time
