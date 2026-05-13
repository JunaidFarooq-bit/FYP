"""
Content extraction service for web pages.
Extracts title, meta description, and body text from URLs.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def extract_content(url: str, timeout: int = 10) -> dict:
    """
    Extract content from a URL.

    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds

    Returns:
        dict with keys: title, meta_description, full_text, error (if any)
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

        # Extract body text
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text from main content areas first
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
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

        return {
            "title": title,
            "meta_description": meta_description,
            "full_text": full_text,
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
