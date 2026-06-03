"""
SEO Analysis Service - Extracted from Website_Audit class
Handles SEO elements like titles, meta descriptions, headings, and Open Graph tags.
"""
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class SEOAnalysisService:
    """Service for analyzing SEO elements on a webpage."""
    
    def __init__(self, html_content: str, base_url: str = '', url: str = ''):
        from bs4 import BeautifulSoup
        if isinstance(html_content, str):
            self.soup = BeautifulSoup(html_content, 'html.parser') if html_content else None
        else:
            self.soup = html_content
        self.base_url = base_url
        self.url = url
        self.data = {}
        
    def analyze_seo_elements(self) -> Dict[str, Any]:
        """Analyze all SEO elements on the page."""
        try:
            result = {
                'title': self.analyze_title(),
                'meta_description': self.analyze_meta_description(),
                'headings': self.analyze_headings(),
                'open_graph': self.analyze_open_graph(),
                'meta_tags': self.analyze_meta_tags(),
                'seo_score': 0
            }
            
            # Calculate overall SEO score
            result['seo_score'] = self._calculate_seo_score(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in SEO analysis: {e}")
            return {
                'title': {'score': 0, 'verdict': 'Error analyzing title'},
                'meta_description': {'score': 0, 'verdict': 'Error analyzing meta description'},
                'headings': {'score': 0, 'verdict': 'Error analyzing headings'},
                'open_graph': {'score': 0, 'verdict': 'Error analyzing Open Graph'},
                'meta_tags': {'score': 0, 'verdict': 'Error analyzing meta tags'},
                'seo_score': 0
            }
    
    def analyze_title(self) -> Dict[str, Any]:
        """Analyze page title element."""
        try:
            if not self.soup:
                return {'score': 0, 'verdict': 'No title found', 'title': ''}
            
            title_tag = self.soup.find('title')
            if not title_tag:
                return {'score': 0, 'verdict': '❌ No title tag found', 'title': ''}
            
            title_text = title_tag.get_text(strip=True)
            title_length = len(title_text)
            
            # Score based on length and content
            score = 0
            verdict = ""
            
            if 30 <= title_length <= 60:
                score = 100
                verdict = "✅ Optimal length (30-60 characters)"
            elif 20 <= title_length <= 70:
                score = 80
                verdict = "⚠️ Good length, could be optimized"
            elif title_length < 20:
                score = 40
                verdict = "❌ Title too short"
            else:
                score = 60
                verdict = "⚠️ Title too long"
            
            # Check for keywords in title (simplified)
            if any(keyword in title_text.lower() for keyword in ['seo', 'optimization', 'marketing']):
                score += 10
            
            return {
                'score': min(100, score),
                'verdict': verdict,
                'title': title_text,
                'length': title_length
            }
            
        except Exception as e:
            logger.error(f"Error analyzing title: {e}")
            return {'score': 0, 'verdict': 'Error analyzing title', 'title': ''}
    
    def analyze_meta_description(self) -> Dict[str, Any]:
        """Analyze meta description."""
        try:
            if not self.soup:
                return {'score': 0, 'verdict': 'No meta description found', 'description': ''}
            
            meta_desc = self.soup.find('meta', attrs={'name': 'description'})
            if not meta_desc:
                return {'score': 0, 'verdict': '❌ No meta description found', 'description': ''}
            
            description = meta_desc.get('content', '').strip()
            desc_length = len(description)
            
            # Score based on length
            score = 0
            verdict = ""
            
            if 120 <= desc_length <= 160:
                score = 100
                verdict = "✅ Optimal length (120-160 characters)"
            elif 100 <= desc_length <= 180:
                score = 80
                verdict = "⚠️ Good length, could be optimized"
            elif desc_length < 50:
                score = 30
                verdict = "❌ Meta description too short"
            else:
                score = 60
                verdict = "⚠️ Meta description too long"
            
            return {
                'score': score,
                'verdict': verdict,
                'description': description,
                'length': desc_length
            }
            
        except Exception as e:
            logger.error(f"Error analyzing meta description: {e}")
            return {'score': 0, 'verdict': 'Error analyzing meta description', 'description': ''}
    
    def analyze_headings(self) -> Dict[str, Any]:
        """Analyze heading structure."""
        try:
            if not self.soup:
                return {'score': 0, 'verdict': 'No headings found', 'structure': {}}
            
            headings = {
                'h1': self.soup.find_all('h1'),
                'h2': self.soup.find_all('h2'),
                'h3': self.soup.find_all('h3'),
                'h4': self.soup.find_all('h4'),
                'h5': self.soup.find_all('h5'),
                'h6': self.soup.find_all('h6'),
            }
            
            structure = {level: len(tags) for level, tags in headings.items()}
            
            # Score based on heading structure
            score = 0
            issues = []
            
            # Check for H1
            h1_count = structure['h1']
            if h1_count == 1:
                score += 40
            elif h1_count == 0:
                issues.append("Missing H1 tag")
            else:
                issues.append(f"Multiple H1 tags ({h1_count})")
                score += 20
            
            # Check for H2 tags
            h2_count = structure['h2']
            if h2_count > 0:
                score += 30
            else:
                issues.append("No H2 tags found")
            
            # Check heading hierarchy
            total_headings = sum(structure.values())
            if total_headings > 1:
                score += 30
            
            verdict = "✅ Good heading structure" if not issues else f"⚠️ {', '.join(issues)}"
            
            return {
                'score': min(100, score),
                'verdict': verdict,
                'structure': structure,
                'total_headings': total_headings
            }
            
        except Exception as e:
            logger.error(f"Error analyzing headings: {e}")
            return {'score': 0, 'verdict': 'Error analyzing headings', 'structure': {}}
    
    def analyze_open_graph(self) -> Dict[str, Any]:
        """Analyze Open Graph tags."""
        try:
            if not self.soup:
                return {'score': 0, 'verdict': 'No Open Graph tags found', 'tags': {}}
            
            # Essential OG tags
            essential_tags = {
                'og:title': self.soup.find('meta', property='og:title'),
                'og:description': self.soup.find('meta', property='og:description'),
                'og:image': self.soup.find('meta', property='og:image'),
                'og:url': self.soup.find('meta', property='og:url'),
                'og:type': self.soup.find('meta', property='og:type'),
            }
            
            # Optional but recommended tags
            optional_tags = {
                'og:site_name': self.soup.find('meta', property='og:site_name'),
                'og:locale': self.soup.find('meta', property='og:locale'),
                'og:image:alt': self.soup.find('meta', property='og:image:alt'),
            }
            
            tags_found = {}
            essential_found = 0
            
            for tag_name, tag in essential_tags.items():
                if tag and tag.get('content'):
                    tags_found[tag_name] = tag.get('content')
                    essential_found += 1
            
            for tag_name, tag in optional_tags.items():
                if tag and tag.get('content'):
                    tags_found[tag_name] = tag.get('content')
            
            # Calculate score
            score = (essential_found / len(essential_tags)) * 100
            
            if score >= 80:
                verdict = "✅ Good Open Graph implementation"
            elif score >= 60:
                verdict = "⚠️ Some Open Graph tags missing"
            else:
                verdict = "❌ Incomplete Open Graph implementation"
            
            return {
                'score': round(score, 1),
                'verdict': verdict,
                'tags': tags_found,
                'essential_found': essential_found,
                'essential_total': len(essential_tags)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Open Graph: {e}")
            return {'score': 0, 'verdict': 'Error analyzing Open Graph', 'tags': {}}
    
    def analyze_meta_tags(self) -> Dict[str, Any]:
        """Analyze other important meta tags."""
        try:
            if not self.soup:
                return {'score': 0, 'verdict': 'No meta tags found', 'tags': {}}
            
            meta_tags = {
                'viewport': self.soup.find('meta', attrs={'name': 'viewport'}),
                'robots': self.soup.find('meta', attrs={'name': 'robots'}),
                'canonical': self.soup.find('link', attrs={'rel': 'canonical'}),
                'charset': self.soup.find('meta', attrs={'charset': True}),
            }
            
            tags_found = {}
            score = 0
            
            for tag_name, tag in meta_tags.items():
                if tag:
                    if tag_name == 'canonical':
                        tags_found[tag_name] = tag.get('href')
                    elif tag_name == 'charset':
                        tags_found[tag_name] = tag.get('charset')
                    else:
                        tags_found[tag_name] = tag.get('content')
                    score += 25
            
            verdict = "✅ Good meta tag implementation" if score >= 75 else "⚠️ Some meta tags missing"
            
            return {
                'score': score,
                'verdict': verdict,
                'tags': tags_found
            }
            
        except Exception as e:
            logger.error(f"Error analyzing meta tags: {e}")
            return {'score': 0, 'verdict': 'Error analyzing meta tags', 'tags': {}}
    
    def _calculate_seo_score(self, elements: Dict[str, Any]) -> float:
        """Calculate overall SEO score."""
        try:
            scores = [
                elements.get('title', {}).get('score', 0) * 0.25,
                elements.get('meta_description', {}).get('score', 0) * 0.20,
                elements.get('headings', {}).get('score', 0) * 0.20,
                elements.get('open_graph', {}).get('score', 0) * 0.20,
                elements.get('meta_tags', {}).get('score', 0) * 0.15,
            ]
            
            total_score = sum(scores)
            return round(min(100, total_score), 1)
            
        except Exception as e:
            logger.error(f"Error calculating SEO score: {e}")
            return 0
