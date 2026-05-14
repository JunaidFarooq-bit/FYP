"""
Minification Checker Service.
Provides a base class and implementations for checking CSS and JS minification.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import logging

from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class MinificationChecker(ABC):
    """
    Base class for checking resource minification.
    Implements common logic for fetching, analyzing, and scoring minification.
    """
    
    def __init__(self, session: requests.Session, url: str, soup: BeautifulSoup):
        self.session = session
        self.url = url
        self.soup = soup
        self.result_key = 'minified'
        self.count_key = 'count'
        self.inline_count_key = 'inline_count'
        self.external_count_key = 'external_count'
    
    @property
    @abstractmethod
    def resource_type(self) -> str:
        """Return the resource type (e.g., 'css', 'js')."""
        pass
    
    @property
    @abstractmethod
    def tag_name(self) -> str:
        """Return the HTML tag name to search for (e.g., 'link', 'script')."""
        pass
    
    @property
    @abstractmethod
    def tag_attrs(self) -> Dict[str, Any]:
        """Return the tag attributes to match (e.g., {'rel': 'stylesheet'})."""
        pass
    
    @property
    @abstractmethod
    def src_attr(self) -> str:
        """Return the attribute containing the URL (e.g., 'href', 'src')."""
        pass
    
    @abstractmethod
    def should_skip_url(self, url: str) -> bool:
        """Return True if URL should be skipped (e.g., already minified)."""
        pass
    
    @abstractmethod
    def compress(self, code: str) -> str:
        """Compress the code and return minified version."""
        pass
    
    @abstractmethod
    def is_minified(self, original: str, compressed: str) -> bool:
        """Return True if the code is considered minified."""
        pass
    
    def find_inline_resources(self) -> List[Any]:
        """Find inline resources (e.g., <style> or <script> without src)."""
        return []
    
    def check(self, max_files: int = 10, timeout: int = 10, 
              min_size: int = 50, threshold_percent: float = 5.0) -> Dict[str, Any]:
        """
        Check minification status of resources.
        
        Args:
            max_files: Maximum number of external files to check
            timeout: Request timeout in seconds
            min_size: Minimum file size to analyze (bytes)
            threshold_percent: Compression threshold to consider minified (%)
            
        Returns:
            Dict with minification status and statistics
        """
        result = {
            self.result_key: None,
            'is_minified': False,
            self.count_key: 0,
            self.inline_count_key: 0,
            self.external_count_key: 0,
            'files_checked': 0,
            'files_minified': 0,
            'unminified_files': [],
            'ratio_percent': 0
        }
        
        try:
            # Find external resources
            external_urls = []
            for tag in self.soup.find_all(self.tag_name, **self.tag_attrs):
                src = tag.get(self.src_attr)
                if src and not self.should_skip_url(src):
                    full_url = urljoin(self.url, src)
                    external_urls.append(full_url)
            
            result[self.external_count_key] = len(external_urls)
            
            # Find inline resources
            inline_resources = self.find_inline_resources()
            result[self.inline_count_key] = len(inline_resources)
            
            # Handle no resources case
            if not external_urls and not inline_resources:
                result[self.result_key] = f"No {self.resource_type.upper()} found to check."
                return result
            
            if not external_urls:
                result[self.result_key] = f"Only inline {self.resource_type.upper()} found (not optimal for caching)."
                return result
            
            # Check external files
            total_checked = 0
            minified_count = 0
            unminified_files = []
            
            for resource_url in external_urls[:max_files]:
                try:
                    response = self.session.get(resource_url, timeout=timeout)
                    response.raise_for_status()
                    code = response.text
                    
                    if len(code.strip()) < min_size:
                        continue
                    
                    total_checked += 1
                    compressed = self.compress(code)
                    
                    if self.is_minified(code, compressed):
                        minified_count += 1
                    else:
                        unminified_files.append(resource_url)
                        
                except requests.RequestException:
                    continue
            
            result['files_checked'] = total_checked
            result['files_minified'] = minified_count
            result['unminified_files'] = unminified_files
            
            if total_checked == 0:
                result[self.result_key] = f"Unable to verify {self.resource_type.upper()} minification."
                return result
            
            # Calculate ratio and generate verdict
            ratio = (minified_count / total_checked) * 100 if total_checked > 0 else 0
            result['ratio_percent'] = round(ratio, 1)
            
            if ratio >= 80:
                result[self.result_key] = (
                    f"Good! {minified_count}/{total_checked} {self.resource_type.upper()} files "
                    f"are minified ({int(ratio)}%)."
                )
                result['is_minified'] = True
            elif ratio >= 50:
                result[self.result_key] = (
                    f"Partial. {minified_count}/{total_checked} {self.resource_type.upper()} files "
                    f"are minified ({int(ratio)}%)."
                )
            else:
                result[self.result_key] = (
                    f"Poor. Only {minified_count}/{total_checked} {self.resource_type.upper()} files "
                    f"are minified ({int(ratio)}%)."
                )
            
            return result
            
        except Exception as e:
            result[self.result_key] = f"Error analyzing {self.resource_type.upper()}: {str(e)}"
            logger.error(f"Minification check error for {self.resource_type}: {e}")
            return result


class CSSMinificationChecker(MinificationChecker):
    """Checker for CSS minification status."""
    
    @property
    def resource_type(self) -> str:
        return 'css'
    
    @property
    def tag_name(self) -> str:
        return 'link'
    
    @property
    def tag_attrs(self) -> Dict[str, Any]:
        return {'rel': 'stylesheet'}
    
    @property
    def src_attr(self) -> str:
        return 'href'
    
    def should_skip_url(self, url: str) -> bool:
        """Skip data URLs and already minified files."""
        return url.startswith('data:') or 'min.css' in url.lower()
    
    def compress(self, code: str) -> str:
        """Compress CSS using csscompressor."""
        import csscompressor
        return csscompressor.compress(code)
    
    def is_minified(self, original: str, compressed: str) -> bool:
        """Consider minified if compression saves less than 5%."""
        if len(original) == 0:
            return True
        reduction = ((len(original) - len(compressed)) / len(original)) * 100
        return reduction <= 5
    
    def find_inline_resources(self) -> List[Any]:
        """Find inline <style> tags."""
        return self.soup.find_all('style')


class JSMinificationChecker(MinificationChecker):
    """Checker for JavaScript minification status."""
    
    @property
    def resource_type(self) -> str:
        return 'js'
    
    @property
    def tag_name(self) -> str:
        return 'script'
    
    @property
    def tag_attrs(self) -> Dict[str, Any]:
        return {'src': True}
    
    @property
    def src_attr(self) -> str:
        return 'src'
    
    def should_skip_url(self, url: str) -> bool:
        """Skip data URLs and already minified files."""
        return url.startswith('data:') or 'min.js' in url.lower()
    
    def compress(self, code: str) -> str:
        """Compress JavaScript using jsmin."""
        from jsmin import jsmin
        return jsmin(code)
    
    def is_minified(self, original: str, compressed: str) -> bool:
        """Consider minified if compression saves less than 5%."""
        if len(original) == 0:
            return True
        reduction = ((len(original) - len(compressed)) / len(original)) * 100
        return reduction <= 5
    
    def find_inline_resources(self) -> List[Any]:
        """Find inline <script> tags without src."""
        return self.soup.find_all('script', src=False)


class MinificationService:
    """
    Service for checking both CSS and JS minification.
    Provides a unified interface for minification analysis.
    """
    
    def __init__(self, session: requests.Session, url: str, response_text: str):
        self.session = session
        self.url = url
        self.soup = BeautifulSoup(response_text, 'html.parser')
        self._css_checker = CSSMinificationChecker(session, url, self.soup)
        self._js_checker = JSMinificationChecker(session, url, self.soup)
    
    def check_css(self, **kwargs) -> Dict[str, Any]:
        """Check CSS minification status."""
        return self._css_checker.check(**kwargs)
    
    def check_js(self, **kwargs) -> Dict[str, Any]:
        """Check JavaScript minification status."""
        return self._js_checker.check(**kwargs)
    
    def check_all(self, **kwargs) -> Dict[str, Any]:
        """Check both CSS and JS minification."""
        return {
            'css': self.check_css(**kwargs),
            'js': self.check_js(**kwargs)
        }
