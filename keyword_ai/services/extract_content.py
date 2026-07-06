"""
Content extraction service for web pages.
Extracts title, meta description, OG tags, and clean body text from URLs.
"""

import json
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


def _extract_page_signals(soup: BeautifulSoup, page_url: str) -> dict:
    """Extract verifiable page signals for per-query GEO/AEO audits."""
    parsed_page = urlparse(page_url)
    headings = []
    question_headings = []
    question_answer_pairs = []

    heading_nodes = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    for node in heading_nodes:
        heading_text = " ".join(node.get_text(" ", strip=True).split())
        if not heading_text:
            continue
        headings.append({"level": node.name, "text": heading_text[:300]})
        is_question = bool(
            heading_text.endswith("?")
            or re.match(
                r"^(what|how|why|when|where|who|which|can|is|are|should|do|does)",
                heading_text,
                re.I,
            )
        )
        if not is_question:
            continue
        question_headings.append(heading_text[:300])
        answer_parts = []
        sibling = node.find_next_sibling()
        while sibling and len(answer_parts) < 3:
            if getattr(sibling, "name", "") in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break
            if getattr(sibling, "name", "") in {"p", "ol", "ul", "table"}:
                value = " ".join(sibling.get_text(" ", strip=True).split())
                if value:
                    answer_parts.append(value)
            sibling = sibling.find_next_sibling()
        answer = " ".join(answer_parts)
        if answer:
            question_answer_pairs.append({
                "question": heading_text[:300],
                "answer": answer[:1200],
                "answer_word_count": len(answer.split()),
            })

    concise_answers = []
    for node in soup.find_all("p"):
        value = " ".join(node.get_text(" ", strip=True).split())
        word_count = len(value.split())
        if 20 <= word_count <= 80:
            concise_answers.append(value[:600])
        if len(concise_answers) >= 10:
            break

    schema_types = set()
    schema_addresses = []
    service_areas = []
    valid_json_ld_blocks = 0
    invalid_json_ld_blocks = 0

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
            valid_json_ld_blocks += 1
        except (TypeError, ValueError, json.JSONDecodeError):
            invalid_json_ld_blocks += 1
            continue

        stack = payload if isinstance(payload, list) else [payload]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
                continue
            if not isinstance(item, dict):
                continue

            item_type = item.get("@type")
            if isinstance(item_type, list):
                schema_types.update(str(value) for value in item_type)
            elif item_type:
                schema_types.add(str(item_type))

            address = item.get("address")
            if isinstance(address, str) and address.strip():
                schema_addresses.append(address.strip()[:400])
            elif isinstance(address, dict):
                parts = [
                    address.get("streetAddress"),
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("postalCode"),
                    address.get("addressCountry"),
                ]
                rendered = ", ".join(str(part).strip() for part in parts if part)
                if rendered:
                    schema_addresses.append(rendered[:400])

            area = item.get("areaServed") or item.get("serviceArea")
            if isinstance(area, str) and area.strip():
                service_areas.append(area.strip()[:300])
            elif isinstance(area, dict):
                rendered = area.get("name") or area.get("addressLocality")
                if rendered:
                    service_areas.append(str(rendered)[:300])
            elif isinstance(area, list):
                for value in area:
                    if isinstance(value, str) and value.strip():
                        service_areas.append(value.strip()[:300])
                    elif isinstance(value, dict) and value.get("name"):
                        service_areas.append(str(value["name"])[:300])

            graph = item.get("@graph")
            if graph:
                stack.append(graph)

    def meta_value(*names):
        for name in names:
            node = soup.find("meta", attrs={"name": name}) or soup.find(
                "meta", attrs={"property": name}
            )
            if node and node.get("content"):
                return node.get("content", "").strip()
        return ""

    author = meta_value("author", "article:author")
    publisher = meta_value("publisher", "og:site_name")
    published_at = meta_value("article:published_time", "datePublished", "date")
    modified_at = meta_value("article:modified_time", "dateModified", "last-modified")
    og_locale = meta_value("og:locale")

    external_citations = []
    for anchor_node in soup.find_all("a", href=True):
        href = anchor_node.get("href", "").strip()
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if parsed.netloc.lower() == parsed_page.netloc.lower():
            continue
        external_citations.append({
            "url": href[:500],
            "domain": parsed.netloc.lower().removeprefix("www."),
            "text": " ".join(anchor_node.get_text(" ", strip=True).split())[:160],
        })
        if len(external_citations) >= 20:
            break

    html_tag = soup.find("html")
    language = (html_tag.get("lang") or "").strip() if html_tag else ""
    hreflang = []
    for link in soup.find_all("link", href=True):
        rel = {str(value).lower() for value in (link.get("rel") or [])}
        if "alternate" in rel and link.get("hreflang"):
            hreflang.append({
                "language": str(link.get("hreflang")).strip(),
                "url": link.get("href", "")[:500],
            })

    canonical_node = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_url = canonical_node.get("href", "").strip() if canonical_node else ""

    address_texts = []
    for address in soup.find_all("address"):
        value = " ".join(address.get_text(" ", strip=True).split())
        if value:
            address_texts.append(value[:300])

    local_schema_types = {
        "LocalBusiness", "Place", "PostalAddress", "Store", "Restaurant",
        "ProfessionalService", "MedicalBusiness", "HomeAndConstructionBusiness",
    }
    return {
        "headings": headings[:40],
        "question_headings": question_headings[:20],
        "question_answer_pairs": question_answer_pairs[:20],
        "concise_answers": concise_answers,
        "ordered_lists": len(soup.find_all("ol")),
        "unordered_lists": len(soup.find_all("ul")),
        "tables": len(soup.find_all("table")),
        "schema_types": sorted(schema_types),
        "valid_json_ld_blocks": valid_json_ld_blocks,
        "invalid_json_ld_blocks": invalid_json_ld_blocks,
        "has_faq_schema": "FAQPage" in schema_types,
        "has_howto_schema": "HowTo" in schema_types,
        "has_local_schema": bool(schema_types.intersection(local_schema_types)),
        "author": author,
        "publisher": publisher,
        "published_at": published_at,
        "modified_at": modified_at,
        "external_citations": external_citations,
        "language": language,
        "og_locale": og_locale,
        "hreflang": hreflang[:30],
        "canonical_url": canonical_url[:500],
        "addresses": list(dict.fromkeys(address_texts + schema_addresses))[:10],
        "service_areas": list(dict.fromkeys(service_areas))[:10],
    }

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
        
        # Extract OG tags and evidence before destructive cleaning.
        og_tags = _extract_og_tags(soup)
        page_signals = _extract_page_signals(soup, url)

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
            "page_signals": page_signals,
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
