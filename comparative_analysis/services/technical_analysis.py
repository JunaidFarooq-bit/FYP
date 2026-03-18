"""
Layer 3: Technical SEO Analysis
Analyzes technical SEO factors like speed, mobile-friendliness, structure
"""

import re
from urllib.parse import urlparse
from ..utils.performance_estimators import estimate_page_speed, estimate_core_web_vitals


class TechnicalAnalyzer:
    """Analyze technical SEO factors"""
    
    def analyze(self, url, extracted_data):
        """Perform full technical SEO analysis"""
        
        # Page speed estimation
        load_time = extracted_data.get('load_time', 0)
        speed_score = self._calculate_speed_score(load_time)
        
        # Core Web Vitals estimation
        cwv = estimate_core_web_vitals(extracted_data)
        
        # Mobile responsiveness
        is_mobile_responsive = extracted_data.get('is_mobile_responsive', False)
        
        # HTTPS
        is_https = extracted_data.get('is_https', False)
        
        # Canonical tag
        canonical = extracted_data.get('canonical', '')
        has_canonical = bool(canonical)
        
        # Robots directives
        robots_meta = extracted_data.get('robots', '')
        is_indexable = self._check_indexability(robots_meta)
        is_crawlable = self._check_crawlability(robots_meta)
        
        # Structured data
        structured_data = extracted_data.get('structured_data', [])
        schema_types = extracted_data.get('schema_types', [])
        has_structured_data = len(structured_data) > 0
        
        # URL structure quality
        url_quality = self._analyze_url_structure(url)
        
        # Image optimization
        image_optimization = self._analyze_image_optimization(extracted_data)
        
        # Internal linking
        internal_links = extracted_data.get('internal_links', [])
        internal_link_count = len(internal_links)
        
        # Calculate overall technical score
        technical_score = self._calculate_technical_score({
            'speed_score': speed_score,
            'is_https': is_https,
            'has_canonical': has_canonical,
            'is_indexable': is_indexable,
            'is_mobile_responsive': is_mobile_responsive,
            'has_structured_data': has_structured_data,
            'url_quality_score': url_quality['score'],
            'image_optimization_score': image_optimization['score']
        })
        
        return {
            'technical_score': technical_score,
            'page_speed': {
                'load_time': load_time,
                'speed_score': speed_score,
            },
            'core_web_vitals': cwv,
            'mobile_responsive': is_mobile_responsive,
            'https_enabled': is_https,
            'canonical': {
                'present': has_canonical,
                'url': canonical
            },
            'indexability': {
                'is_indexable': is_indexable,
                'is_crawlable': is_crawlable,
                'robots_directive': robots_meta
            },
            'structured_data': {
                'present': has_structured_data,
                'count': len(structured_data),
                'schema_types': schema_types
            },
            'url_structure': url_quality,
            'image_optimization': image_optimization,
            'internal_links': internal_link_count
        }
    
    def _calculate_speed_score(self, load_time):
        """Calculate speed score based on load time"""
        if load_time < 1.0:
            return 100
        elif load_time < 2.5:
            return 80
        elif load_time < 4.0:
            return 60
        elif load_time < 6.0:
            return 40
        else:
            return 20
    
    def _check_indexability(self, robots_meta):
        """Check if page is indexable"""
        if not robots_meta:
            return True  # Default is indexable
        
        robots_lower = robots_meta.lower()
        return 'noindex' not in robots_lower
    
    def _check_crawlability(self, robots_meta):
        """Check if page is crawlable"""
        if not robots_meta:
            return True  # Default is crawlable
        
        robots_lower = robots_meta.lower()
        return 'nofollow' not in robots_lower
    
    def _analyze_url_structure(self, url):
        """Analyze URL structure quality"""
        
        parsed = urlparse(url)
        path = parsed.path
        
        score = 50  # Base score
        issues = []
        
        # Clean URL (no query parameters for main content)
        if not parsed.query:
            score += 15
        else:
            issues.append("URL contains query parameters")
        
        # Not too long
        if len(url) < 75:
            score += 15
        elif len(url) > 150:
            score -= 10
            issues.append("URL is too long")
        
        # Uses hyphens, not underscores
        if '_' in path:
            score -= 10
            issues.append("URL uses underscores instead of hyphens")
        
        # Descriptive
        if len(path.strip('/').split('/')) > 0:
            score += 10
        
        # No excessive subdirectories
        depth = len(path.strip('/').split('/'))
        if depth > 4:
            score -= 10
            issues.append("URL has too many subdirectories")
        
        return {
            'score': max(min(score, 100), 0),
            'length': len(url),
            'depth': depth,
            'issues': issues
        }
    
    def _analyze_image_optimization(self, extracted_data):
        """Analyze image optimization"""
        
        images = extracted_data.get('images', [])
        
        if not images:
            return {'score': 100, 'total_images': 0, 'images_with_alt': 0}
        
        images_with_alt = sum(1 for img in images if img.get('has_alt', False))
        alt_percentage = (images_with_alt / len(images)) * 100 if images else 0
        
        return {
            'score': int(alt_percentage),
            'total_images': len(images),
            'images_with_alt': images_with_alt,
            'alt_percentage': alt_percentage
        }
    
    def _calculate_technical_score(self, factors):
        """Calculate overall technical SEO score"""
        
        score = 0
        
        # Speed (25 points)
        score += (factors['speed_score'] / 100) * 25
        
        # HTTPS (15 points)
        score += 15 if factors['is_https'] else 0
        
        # Mobile responsive (20 points)
        score += 20 if factors['is_mobile_responsive'] else 0
        
        # Indexable (10 points)
        score += 10 if factors['is_indexable'] else 0
        
        # Canonical (10 points)
        score += 10 if factors['has_canonical'] else 0
        
        # Structured data (10 points)
        score += 10 if factors['has_structured_data'] else 0
        
        # URL quality (10 points)
        score += (factors['url_quality_score'] / 100) * 10
        
        return int(min(score, 100))