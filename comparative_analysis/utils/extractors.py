"""
HTML parsing and extraction utilities
"""

from bs4 import BeautifulSoup
import re


def clean_text(text):
    """Clean extracted text"""
    
    if not text:
        return ''
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_text_between_tags(soup, start_tag, end_tag=None):
    """Extract text between specific tags"""
    
    start = soup.find(start_tag)
    if not start:
        return ''
    
    if end_tag:
        end = soup.find(end_tag)
        if end:
            # Get all text between start and end
            text = ''
            for sibling in start.next_siblings:
                if sibling == end:
                    break
                if hasattr(sibling, 'get_text'):
                    text += sibling.get_text()
            return clean_text(text)
    
    return clean_text(start.get_text())


def count_tag_occurrences(soup, tag_name):
    """Count occurrences of a specific tag"""
    
    return len(soup.find_all(tag_name))


def extract_links_by_position(soup, position='content'):
    """Extract links from specific page positions"""
    
    if position == 'nav':
        nav = soup.find('nav')
        if nav:
            return nav.find_all('a', href=True)
    
    elif position == 'footer':
        footer = soup.find('footer')
        if footer:
            return footer.find_all('a', href=True)
    
    elif position == 'content':
        # Remove nav and footer, then get links
        for tag in soup(['nav', 'footer', 'header']):
            tag.decompose()
        return soup.find_all('a', href=True)
    
    return []