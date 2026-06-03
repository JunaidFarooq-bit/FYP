"""
Technical SEO Audit Service.
Analyzes schema markup, Open Graph tags, favicon, robots.txt, and sitemap.
"""
import json
import logging
from typing import Dict, Any, List, Set, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """Analyzes Schema.org structured data on a page."""
    
    # Important schema types that should be present
    IMPORTANT_TYPES = [
        'Organization', 'WebSite', 'WebPage', 'Article', 'Product',
        'LocalBusiness', 'BreadcrumbList', 'FAQPage'
    ]
    
    def analyze(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze schema markup on the page."""
        schema_types = []
        schema_formats = []
        schema_found = False
        
        # Check for JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        if json_ld_scripts:
            schema_formats.append("JSON-LD")
            schema_found = True
            
            for script in json_ld_scripts:
                try:
                    schema_data = json.loads(script.string)
                    if isinstance(schema_data, dict):
                        schema_type = schema_data.get('@type', '')
                        if schema_type:
                            schema_types.append(schema_type)
                        # Check for @graph array
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
        
        # Check for inline schema.org scripts
        all_scripts = soup.find_all('script')
        for script in all_scripts:
            script_text = script.string if script.string else ""
            if 'schema.org' in script_text:
                schema_found = True
                if "JSON-LD" not in schema_formats:
                    schema_formats.append("Embedded")
                if 'yoast-schema-graph' in str(script.get('class', [])):
                    schema_formats.append("Yoast SEO")
        
        # Check for Microdata
        microdata_items = soup.find_all(attrs={"itemtype": True})
        if microdata_items:
            schema_formats.append("Microdata")
            schema_found = True
            for item in microdata_items:
                itemtype = item.get('itemtype', '')
                if 'schema.org' in itemtype:
                    type_name = itemtype.split('/')[-1]
                    schema_types.append(type_name)
        
        # Check for RDFa
        rdfa_items = soup.find_all(attrs={"vocab": True})
        if rdfa_items:
            for item in rdfa_items:
                if 'schema.org' in item.get('vocab', ''):
                    schema_formats.append("RDFa")
                    schema_found = True
        
        return self._format_results(schema_found, schema_types, schema_formats)
    
    def _format_results(self, found: bool, types: List[str], formats: List[str]) -> Dict[str, Any]:
        """Format the analysis results."""
        result = {
            'schema': "",
            'schema_format': None,
            'schema_types': [],
            'schema_recommendations': [],
            'schema_found': found
        }
        
        if found:
            unique_types = list(set(types))
            unique_formats = list(set(formats))
            
            schema_verdict = "✓ Found - Schema.org structured data detected"
            
            if unique_formats:
                schema_verdict += f" ({', '.join(unique_formats)})"
            
            if unique_types:
                top_types = unique_types[:5]
                result['schema_types'] = top_types
                schema_verdict += f"\nTypes: {', '.join(top_types)}"
            
            recommendations = []
            
            if "JSON-LD" not in unique_formats and unique_formats:
                recommendations.append("Consider migrating to JSON-LD (Google's preferred format)")
            
            # Check for missing important types
            types_lower = [t.lower() for t in unique_types]
            missing_important = [t for t in self.IMPORTANT_TYPES if t.lower() not in types_lower]
            
            if missing_important and len(missing_important) <= 3:
                recommendations.append(f"Consider adding: {', '.join(missing_important[:3])}")
            
            result['schema'] = schema_verdict
            result['schema_format'] = unique_formats if unique_formats else None
            result['schema_recommendations'] = recommendations if recommendations else ["Schema implementation looks good"]
        else:
            result['schema'] = "⚠️ Not Found - No Schema.org structured data detected"
            result['schema_recommendations'] = [
                "Add JSON-LD structured data for better search visibility",
                "Recommended types: Organization, WebSite, WebPage, BreadcrumbList",
                "Use Google's Rich Results Test to validate: https://search.google.com/test/rich-results"
            ]
        
        return result


class OpenGraphAnalyzer:
    """Analyzes Open Graph Protocol tags."""
    
    # Required OG tags for social sharing
    REQUIRED_TAGS = ['og:title', 'og:type', 'og:url', 'og:image']
    # Tags that are critical for social SEO
    SOCIAL_SEO_REQUIRED = {'og:title', 'og:description', 'og:image'}
    
    def analyze(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze Open Graph tags on the page."""
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
        
        # Find all OG tags
        for tag_name in og_tags.keys():
            try:
                tag = soup.find("meta", property=tag_name)
                if tag and tag.get("content"):
                    content = tag.get("content", "").strip()
                    if content:
                        og_tags[tag_name]['found'] = True
                        og_tags[tag_name]['content'] = content
            except Exception as e:
                logger.debug(f"Error checking {tag_name}: {e}")
                continue
        
        return self._format_results(og_tags)
    
    def _format_results(self, og_tags: Dict) -> Dict[str, Any]:
        """Format the OG analysis results."""
        found_tags = [tag for tag, data in og_tags.items() if data['found']]
        required_tags = [tag for tag, data in og_tags.items() if data['required']]
        found_required = [tag for tag in required_tags if og_tags[tag]['found']]
        
        total_tags = len(og_tags)
        found_count = len(found_tags)
        
        # Social SEO flag is true when critical sharing tags are present
        ogp_flag = all(og_tags[tag]['found'] for tag in self.SOCIAL_SEO_REQUIRED)
        
        # Generate verdict
        if len(found_required) == 4:
            verdict = f"✓ Excellent - All required Open Graph tags found ({found_count}/{total_tags} total)"
            
            if not og_tags['og:image:width']['found'] or not og_tags['og:image:height']['found']:
                verdict += "\n⚠️ Tip: Add og:image:width and og:image:height for better image rendering"
            
            if not og_tags['og:description']['found']:
                verdict += "\n⚠️ Tip: Add og:description for better social shares"
        elif len(found_required) >= 2:
            missing_required = [tag for tag in required_tags if not og_tags[tag]['found']]
            verdict = f"⚠️ Partial - {len(found_required)}/4 required OG tags found"
            verdict += f"\nMissing required: {', '.join(missing_required)}"
        elif found_count > 0:
            verdict = f"⚠️ Incomplete - Found {found_count} OG tags but missing required tags"
            verdict += f"\nRequired tags: og:title, og:type, og:url, og:image"
        else:
            verdict = "❌ Not Found - No Open Graph Protocol tags detected"
        
        # Collect OG values
        og_values = {}
        for tag, data in og_tags.items():
            if data['found'] and data['content']:
                og_values[tag] = data['content'][:100]
        
        # Generate recommendations
        recommendations = []
        if not ogp_flag:
            recommendations.append("Add all 4 required OG tags: og:title, og:type, og:url, og:image")
            recommendations.append("Recommended image size: 1200x630px for best social media display")
        else:
            if not og_tags['og:description']['found']:
                recommendations.append("Add og:description (recommended)")
            if not og_tags['og:image:alt']['found']:
                recommendations.append("Add og:image:alt for accessibility")
        
        return {
            'open_gp': verdict,
            'ogp_flag': ogp_flag,
            'og_tags_found': found_tags,
            'og_tags_missing': [tag for tag, data in og_tags.items() if not data['found']],
            'og_required_complete': len(found_required) == 4,
            'og_values': og_values if og_values else None,
            'og_recommendations': recommendations if recommendations else ["✓ Open Graph implementation is complete"]
        }


class FaviconAnalyzer:
    """Analyzes favicon presence and details."""
    
    # Common favicon locations to check
    FAVICON_LOCATIONS = [
        '/favicon.ico',
        '/favicon.png',
        '/apple-touch-icon.png',
        '/apple-touch-icon-precomposed.png'
    ]
    
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url
    
    def analyze(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze favicon presence on the page."""
        try:
            # Try using favicon library first
            try:
                import favicon
                icons = favicon.get(self.base_url, timeout=10)
                
                if icons and len(icons) > 0:
                    return self._analyze_favicon_icons(icons)
            except Exception:
                pass
            
            # Fallback: check common locations
            return self._check_fallback_locations(soup)
            
        except Exception as e:
            logger.error(f"Error in favicon analysis: {e}")
            return self._not_found_result()
    
    def _analyze_favicon_icons(self, icons: List) -> Dict[str, Any]:
        """Analyze icons returned by the favicon library."""
        # Sort by size (largest first)
        icons_sorted = sorted(icons, key=lambda x: (x.width or 0) * (x.height or 0), reverse=True)
        icon = icons_sorted[0]
        
        icon_url = icon.url
        if not icon_url.startswith(('http://', 'https://')):
            icon_url = urljoin(self.base_url, icon_url)
        
        # Determine format
        ext = 'ico'
        if '.' in icon_url:
            ext = icon_url.split('.')[-1].split('?')[0].lower()
            if ext not in ['ico', 'png', 'jpg', 'jpeg', 'gif', 'svg']:
                ext = 'ico'
        
        size_info = ""
        if icon.width and icon.height:
            size_info = f" ({icon.width}x{icon.height}px)"
        
        return {
            'Favicon': f"✓ Found - Website has favicon{size_info}",
            'icon_flag': True,
            'favicon_url': icon_url,
            'favicon_size': f"{icon.width}x{icon.height}" if icon.width and icon.height else "Unknown",
            'favicon_format': ext.upper()
        }
    
    def _check_fallback_locations(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Check common favicon locations as fallback."""
        # Check standard locations
        for location in self.FAVICON_LOCATIONS:
            try:
                favicon_url = self.base_url.rstrip('/') + location
                response = self.session.head(favicon_url, timeout=5)
                
                if response.status_code == 200:
                    return {
                        'Favicon': f"✓ Found - Favicon available at {location}",
                        'icon_flag': True,
                        'favicon_url': favicon_url
                    }
            except requests.exceptions.RequestException:
                continue
        
        # Check HTML for favicon links
        favicon_links = soup.find_all('link', rel=lambda x: x and 'icon' in x.lower())
        if favicon_links:
            favicon_href = favicon_links[0].get('href', '')
            if favicon_href:
                return {
                    'Favicon': "✓ Found - Favicon referenced in HTML",
                    'icon_flag': True,
                    'favicon_url': urljoin(self.base_url, favicon_href)
                }
        
        return self._not_found_result()
    
    def _not_found_result(self) -> Dict[str, Any]:
        """Return result when no favicon is found."""
        return {
            'Favicon': "⚠️ Not Found - No favicon detected",
            'icon_flag': False,
            'favicon_recommendations': [
                "Add a favicon.ico file to your website root",
                "Recommended sizes: 16x16, 32x32, 48x48px",
                "Also add apple-touch-icon.png (180x180px) for iOS devices",
                "Use PNG or ICO format for best compatibility"
            ]
        }


class RobotsAnalyzer:
    """Analyzes robots.txt file."""
    
    # Valid patterns that indicate a proper robots.txt
    VALID_PATTERNS = [
        "User-agent:",
        "user-agent:",
        "USER-AGENT:",
        "Disallow:",
        "Allow:",
        "Sitemap:"
    ]
    
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.robots_url = base_url.rstrip('/') + '/robots.txt'
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze the robots.txt file."""
        try:
            response = self.session.get(self.robots_url, timeout=10)
            text = response.text
            
            is_valid = any(pattern in text for pattern in self.VALID_PATTERNS)
            
            if response.status_code == 200 and is_valid:
                verdict = "✓ Found - Website has robots.txt file"
                robot_flag = True
                
                # Check for blocking directives
                if "Disallow: /" in text and "User-agent: *" in text:
                    verdict += " (Warning: Site is blocking all crawlers)"
                
                # Check for sitemap reference
                has_sitemap = "Sitemap:" in text or "sitemap:" in text
                
            else:
                verdict = "⚠️ Not Found - Consider adding robots.txt file"
                robot_flag = False
                has_sitemap = False
            
            return {
                'robot': verdict,
                'robot_flag': robot_flag,
                'robots_url': self.robots_url,
                'robots_has_sitemap': has_sitemap if robot_flag else None
            }
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error checking robots.txt: {e}")
            return {
                'robot': "⚠️ Not Found - Consider adding robots.txt file",
                'robot_flag': False,
                'robots_url': self.robots_url
            }
        except Exception as e:
            logger.error(f"Unexpected error in robots.txt check: {e}")
            return {
                'robot': "⚠️ Error checking robots.txt",
                'robot_flag': False,
                'robots_url': self.robots_url
            }


class SitemapAnalyzer:
    """Analyzes XML sitemap presence."""
    
    # Common sitemap paths to check
    SITEMAP_PATHS = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap1.xml',
        '/sitemaps/sitemap.xml',
        '/sitemap/sitemap.xml'
    ]
    
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip('/')
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze sitemap presence and content."""
        sitemap_found = False
        sitemap_location = None
        
        for path in self.SITEMAP_PATHS:
            try:
                sitemap_url = self.base_url + path
                response = self.session.get(sitemap_url, timeout=10)
                text = response.text
                
                valid_sitemap = (
                    response.status_code == 200 and
                    ('<urlset' in text or '<sitemapindex' in text or 'sitemap.xml' in text.lower()) and
                    ('<?xml' in text or '<urlset' in text or '<sitemapindex' in text)
                )
                
                if valid_sitemap:
                    sitemap_found = True
                    sitemap_location = sitemap_url
                    
                    url_count = text.count('<loc>')
                    sitemap_index_count = text.count('<sitemap>')
                    
                    if sitemap_index_count > 0:
                        verdict = f"✓ Found - Sitemap index with {sitemap_index_count} sitemaps at {path}"
                    elif url_count > 0:
                        verdict = f"✓ Found - Sitemap with {url_count} URLs at {path}"
                    else:
                        verdict = f"✓ Found - Sitemap at {path}"
                    
                    return {
                        'sitemap': verdict,
                        'sitemap_location': sitemap_location,
                        'sitemap_flag': True,
                        'sitemap_url_count': url_count if sitemap_index_count == 0 else None,
                        'sitemap_index_count': sitemap_index_count if sitemap_index_count > 0 else None
                    }
                    
            except requests.exceptions.RequestException:
                continue
            except Exception as e:
                logger.debug(f"Error checking sitemap at {path}: {e}")
                continue
        
        # No sitemap found
        return {
            'sitemap': "⚠️ Not Found - Consider adding XML sitemap for better crawlability (Recommended: /sitemap.xml)",
            'sitemap_location': None,
            'sitemap_flag': False
        }


class TechnicalAuditService:
    """
    Unified service for technical SEO audits.
    Combines schema, Open Graph, favicon, robots.txt, and sitemap analysis.
    """
    
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url
        self._schema = SchemaAnalyzer()
        self._og = OpenGraphAnalyzer()
        self._favicon = FaviconAnalyzer(session, base_url)
        self._robots = RobotsAnalyzer(session, base_url)
        self._sitemap = SitemapAnalyzer(session, base_url)
    
    def analyze(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Run all technical audits and combine results."""
        results = {}
        
        # Schema analysis
        results.update(self._schema.analyze(soup))
        
        # Open Graph analysis
        results.update(self._og.analyze(soup))
        
        # Favicon analysis
        results.update(self._favicon.analyze(soup))
        
        # Robots.txt analysis
        results.update(self._robots.analyze())
        
        # Sitemap analysis
        results.update(self._sitemap.analyze())
        
        return results
