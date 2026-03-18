"""
Layer 1: Data Extraction
Extracts raw HTML, metadata, and structural elements
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import time


class DataExtractor:
    """Extract raw page data and metadata"""
    
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; WebLiftBot/1.0; +http://weblift.io/bot)'
        }
    
    def extract(self, url):
        """Extract all raw data from a URL"""
        
        try:
            # Fetch page with timing
            start_time = time.time()
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            load_time = time.time() - start_time
            
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all components
            return {
                'url': url,
                'html': response.text,
                'soup': soup,
                'status_code': response.status_code,
                'load_time': load_time,
                'headers': dict(response.headers),
                
                # Meta elements
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'meta_keywords': self._extract_meta_keywords(soup),
                'canonical': self._extract_canonical(soup, url),
                'robots': self._extract_robots_meta(soup),
                
                # Content structure
                'h1': self._extract_h1(soup),
                'h2_list': self._extract_headings(soup, 'h2'),
                'h3_list': self._extract_headings(soup, 'h3'),
                'headings_all': self._extract_all_headings(soup),
                
                # Content
                'body_text': self._extract_body_text(soup),
                'word_count': self._count_words(soup),
                'paragraphs': self._extract_paragraphs(soup),
                
                # Links
                'internal_links': self._extract_internal_links(soup, url),
                'external_links': self._extract_external_links(soup, url),
                'total_links': None,  # Will calculate
                
                # Media
                'images': self._extract_images(soup),
                'videos': self._extract_videos(soup),
                
                # Technical elements
                'structured_data': self._extract_structured_data(soup),
                'schema_types': self._extract_schema_types(soup),
                'is_https': url.startswith('https://'),
                'is_mobile_responsive': self._check_viewport(soup),
                
                # Additional signals
                'has_author': self._check_author_presence(soup),
                'has_date': self._check_date_presence(soup),
                'has_faq': self._check_faq_schema(soup),
            }
            
        except Exception as e:
            raise Exception(f"Failed to extract data from {url}: {str(e)}")
    
    def _extract_title(self, soup):
        """Extract page title"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ''
    
    def _extract_meta_description(self, soup):
        """Extract meta description"""
        meta = soup.find('meta', attrs={'name': 'description'})
        if not meta:
            meta = soup.find('meta', attrs={'property': 'og:description'})
        return meta.get('content', '').strip() if meta else ''
    
    def _extract_meta_keywords(self, soup):
        """Extract meta keywords"""
        meta = soup.find('meta', attrs={'name': 'keywords'})
        return meta.get('content', '').strip() if meta else ''
    
    def _extract_canonical(self, soup, base_url):
        """Extract canonical URL"""
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        return canonical.get('href', '') if canonical else base_url
    
    def _extract_robots_meta(self, soup):
        """Extract robots meta tag"""
        robots = soup.find('meta', attrs={'name': 'robots'})
        return robots.get('content', '').strip() if robots else ''
    
    def _extract_h1(self, soup):
        """Extract H1 text"""
        h1 = soup.find('h1')
        return h1.get_text().strip() if h1 else ''
    
    def _extract_headings(self, soup, tag):
        """Extract all headings of a specific tag"""
        headings = soup.find_all(tag)
        return [h.get_text().strip() for h in headings]
    
    def _extract_all_headings(self, soup):
        """Extract all heading hierarchy"""
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(tag):
                headings.append({
                    'level': tag,
                    'text': heading.get_text().strip()
                })
        return headings
    
    def _extract_body_text(self, soup):
        """Extract main body text"""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        return text
    
    def _count_words(self, soup):
        """Count words in body text"""
        text = self._extract_body_text(soup)
        words = re.findall(r'\b\w+\b', text)
        return len(words)
    
    def _extract_paragraphs(self, soup):
        """Extract paragraph texts"""
        paragraphs = soup.find_all('p')
        return [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
    
    def _extract_internal_links(self, soup, base_url):
        """Extract internal links"""
        domain = urlparse(base_url).netloc
        internal = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            if urlparse(absolute_url).netloc == domain:
                internal.append({
                    'url': absolute_url,
                    'anchor': link.get_text().strip(),
                })
        
        return internal
    
    def _extract_external_links(self, soup, base_url):
        """Extract external links"""
        domain = urlparse(base_url).netloc
        external = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            if urlparse(absolute_url).netloc != domain and not href.startswith('#'):
                external.append({
                    'url': absolute_url,
                    'anchor': link.get_text().strip(),
                })
        
        return external
    
    def _extract_images(self, soup):
        """Extract image information"""
        images = []
        for img in soup.find_all('img'):
            images.append({
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'has_alt': bool(img.get('alt', '').strip())
            })
        return images
    
    def _extract_videos(self, soup):
        """Detect video presence"""
        videos = soup.find_all(['video', 'iframe'])
        video_count = len(videos)
        return {
            'count': video_count,
            'has_video': video_count > 0
        }
    
    def _extract_structured_data(self, soup):
        """Extract JSON-LD structured data"""
        scripts = soup.find_all('script', type='application/ld+json')
        return [script.string for script in scripts if script.string]
    
    def _extract_schema_types(self, soup):
        """Extract schema.org types"""
        import json
        types = set()
        
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and '@type' in data:
                        types.add(data['@type'])
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and '@type' in item:
                                types.add(item['@type'])
                except:
                    pass
        
        return list(types)
    
    def _check_viewport(self, soup):
        """Check for mobile viewport meta tag"""
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        return viewport is not None
    
    def _check_author_presence(self, soup):
        """Check for author signals"""
        # Check for author meta, schema, or byline
        author_meta = soup.find('meta', attrs={'name': 'author'})
        author_class = soup.find(class_=re.compile(r'author|byline', re.I))
        return author_meta is not None or author_class is not None
    
    def _check_date_presence(self, soup):
        """Check for publish date signals"""
        date_meta = soup.find('meta', attrs={'property': 'article:published_time'})
        time_tag = soup.find('time')
        return date_meta is not None or time_tag is not None
    
    def _check_faq_schema(self, soup):
        """Check for FAQ schema"""
        import json
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string and 'FAQPage' in script.string:
                return True
        return False