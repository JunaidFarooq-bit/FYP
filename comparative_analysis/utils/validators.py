"""
URL validation utilities
"""

import re
from urllib.parse import urlparse


def validate_url(url):
    """Validate URL format"""
    
    if not url:
        return False
    
    # Check for basic URL structure
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def normalize_url(url):
    """Normalize URL (add protocol if missing, etc.)"""
    
    if not url:
        return url
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def extract_domain(url):
    """Extract domain from URL"""
    
    parsed = urlparse(url)
    return parsed.netloc