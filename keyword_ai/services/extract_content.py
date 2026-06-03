"""
Content extraction service for web pages.
Extracts title, meta description, OG tags, and clean body text from URLs.
"""

import re
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse


# Junk patterns to exclude (class/id names containing these as whole words)
# Using word boundaries to avoid matching 'ad' inside 'header', 'lead', etc.
JUNK_PATTERNS = [
    r"\bad\b", r"\bads\b", r"advertisement", r"advertising",
    r"cookie", r"cookies", r"consent", r"gdpr",
    r"banner", r"banners",
    r"affiliate", r"affiliates",
    r"newsletter", r"subscribe", r"signup",
    r"popup", r"modal", r"overlay",
    r"social-share", r"sharing",  # Keep 'social' but be specific about sharing
    r"sidebar", r"widget", r"widgets",
    r"comment", r"comments",
    r"related", r"recommended", r"sponsored",
    r"promo", r"promotion",
]


def _is_junk_element(element) -> bool:
    """Check if an element should be removed based on class/id attributes."""
    from bs4.element import Tag
    
    # Defensive: skip if not a Tag or is None
    if element is None or not isinstance(element, Tag):
        return False
    
    # Get class and id attributes (handle None return)
    try:
        classes = element.get("class", []) or []
        element_id = element.get("id", "") or ""
    except (AttributeError, TypeError):
        return False
    
    # Convert to string for pattern matching
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
    identifier = f"{class_str} {element_id}".lower()
    
    # Check against junk patterns using regex for word boundaries
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, identifier):
            return True
    
    return False


def _clean_soup(soup: BeautifulSoup) -> None:
    """Remove junk elements from soup in-place."""
    from bs4.element import Tag
    
    # Remove by tag name
    for tag in ["script", "style", "nav", "footer", "header", "aside", "noscript", 
                "iframe", "canvas", "svg", "form", "button", "input"]:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # Remove elements with junk class/id patterns (only check Tag elements, not NavigableString)
    for element in soup.find_all():
        if isinstance(element, Tag) and _is_junk_element(element):
            element.decompose()


def _extract_og_tags(soup: BeautifulSoup) -> dict:
    """Extract Open Graph tags from HTML."""
    og_tags = {}
    
    # Common OG tags to extract
    og_properties = [
        "og:title", "og:description", "og:type", "og:url",
        "og:site_name", "og:locale", "og:image",
        "article:published_time", "article:modified_time",
        "article:section", "article:tag"
    ]
    
    for prop in og_properties:
        tag = soup.find("meta", property=prop)
        if tag:
            og_tags[prop] = tag.get("content", "").strip()
    
    return og_tags


def extract_content(url: str, timeout: int = 10) -> dict:
    """
    Extract content from a URL with aggressive HTML cleaning.

    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds

    Returns:
        dict with keys: title, meta_description, full_text, og_tags, error (if any)
    """
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"error": "Invalid URL format. Must include http:// or https://"}

        # Fetch the page
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ""

        # Extract meta description
        meta_description = ""
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        if meta_desc_tag:
            meta_description = meta_desc_tag.get("content", "").strip()
        
        # Extract OG tags
        og_tags = _extract_og_tags(soup)

        # AGGRESSIVE CLEANING: Remove junk before extracting text
        _clean_soup(soup)

        # Get text from main content areas first
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|article", re.I))
        if main_content:
            full_text = main_content.get_text(separator=" ", strip=True)
        else:
            # Fall back to body text
            body = soup.find("body")
            if body:
                full_text = body.get_text(separator=" ", strip=True)
            else:
                full_text = soup.get_text(separator=" ", strip=True)

        # Clean up whitespace
        full_text = " ".join(full_text.split())
        
        # Fallback: if cleaning removed too much content, try extracting from original HTML
        if len(full_text) < 100:
            # Re-parse the original HTML
            soup_original = BeautifulSoup(response.content, "html.parser")
            # Basic cleaning only (no aggressive class/id filtering)
            for tag in ["script", "style", "nav", "footer", "header"]:
                for element in soup_original.find_all(tag):
                    element.decompose()
            # Try to get content from main areas
            main_original = soup_original.find("main") or soup_original.find("article") or soup_original.find("body")
            if main_original:
                fallback_text = main_original.get_text(separator=" ", strip=True)
                fallback_text = " ".join(fallback_text.split())
                if len(fallback_text) > len(full_text):
                    full_text = fallback_text

        return {
            "title": title,
            "meta_description": meta_description,
            "full_text": full_text,
            "og_tags": og_tags,
            "url": url,
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {timeout} seconds"}
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to the server"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to extract content: {str(e)}"}
