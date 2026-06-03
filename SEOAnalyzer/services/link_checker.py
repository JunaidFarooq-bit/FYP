"""
Link Checking Service.
Analyzes internal/external links and checks for broken links.
"""
import time
import logging
from typing import Dict, Any, List, Set, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import concurrent.futures

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LinkAnalyzer:
    """Analyzes page links (internal vs external, nofollow, etc.)."""
    
    def __init__(self, soup: BeautifulSoup, base_url: str, domain: str, final_url: str):
        self.soup = soup
        self.base_url = base_url
        self.domain = domain.lower().replace('www.', '')
        self.final_url = final_url
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze all links on the page."""
        links = self.soup.findAll('a')
        
        result = {
            'Internal_links': 0,
            'External_links': 0,
            'i_url': "",
            'e_url': "",
            'links_verdict': "",
            'total_links': 0,
            'nofollow_links': 0
        }
        
        if len(links) == 0:
            result.update({
                'Internal_links': 0,
                'External_links': 0,
                'i_url': "No links found on page",
                'e_url': "No links found on page",
                'links_verdict': "⚠️ No links found - Consider adding internal linking"
            })
            return result
        
        internal_links_list = []
        external_links_list = []
        nofollow_count = 0
        internal_count = 0
        external_count = 0
        
        for link in links:
            try:
                href = link.get("href", "").strip()
                
                if not href:
                    continue
                
                # Skip non-HTTP protocols
                if href.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                
                # Check for nofollow
                rel = link.get('rel', [])
                if 'nofollow' in rel or 'nofollow' in str(rel).lower():
                    nofollow_count += 1
                
                # Handle anchor links
                if href.startswith('#'):
                    internal_count += 1
                    internal_links_list.append(f"{internal_count}) {href} (anchor link)")
                    continue
                
                # Handle root-relative URLs
                if href.startswith('/'):
                    internal_count += 1
                    full_url = urljoin(self.base_url, href)
                    internal_links_list.append(f"{internal_count}) {full_url}")
                    continue
                
                # Handle protocol-relative URLs
                if href.startswith('//'):
                    href = 'https:' + href
                
                # Parse and categorize
                try:
                    parsed = urlparse(href)
                    
                    if not parsed.netloc:
                        internal_count += 1
                        full_url = urljoin(self.final_url, href)
                        internal_links_list.append(f"{internal_count}) {full_url}")
                        continue
                    
                    link_domain = parsed.netloc.lower().replace('www.', '')
                    
                    if link_domain == self.domain:
                        internal_count += 1
                        internal_links_list.append(f"{internal_count}) {href}")
                    else:
                        external_count += 1
                        external_links_list.append(f"{external_count}) {href}")
                        
                except Exception as e:
                    logger.debug(f"Error parsing URL {href}: {e}")
                    internal_count += 1
                    internal_links_list.append(f"{internal_count}) {href} (parse error)")
                    
            except Exception as e:
                logger.debug(f"Error processing link: {e}")
                continue
        
        result.update({
            'Internal_links': internal_count,
            'External_links': external_count,
            'i_url': '\n'.join(internal_links_list) if internal_links_list else "No internal links found",
            'e_url': '\n'.join(external_links_list) if external_links_list else "No external links found",
            'total_links': internal_count + external_count,
            'nofollow_links': nofollow_count
        })
        
        # Generate verdict
        result['links_verdict'] = self._generate_verdict(internal_count, external_count)
        
        return result
    
    def _generate_verdict(self, internal: int, external: int) -> str:
        """Generate a verdict based on link counts."""
        total = internal + external
        
        if total == 0:
            return "⚠️ No links found - Add internal linking for better SEO"
        elif internal == 0:
            return "⚠️ No internal links - Add internal linking structure"
        elif internal < 3:
            return "⚠️ Low internal linking - Increase to improve site structure"
        
        if external == 0:
            return f"✓ Good - {internal} internal links found"
        
        ratio = internal / external
        if ratio >= 2:
            return f"✓ Excellent - Good internal/external ratio ({internal}:{external})"
        elif ratio >= 1:
            return f"✓ Good - Balanced linking ({internal}:{external})"
        else:
            return f"⚠️ More external than internal links ({internal}:{external}) - Consider more internal linking"


class BrokenLinkChecker:
    """Checks for broken links using concurrent requests."""
    
    STATUS_REASONS = {
        404: "Not Found",
        410: "Gone (Permanently Deleted)",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout"
    }
    
    def __init__(self, session: requests.Session, base_url: str, domain: str):
        self.session = session
        self.base_url = base_url
        self.domain = domain.lower().replace('www.', '')
    
    def check(self, soup: BeautifulSoup, max_workers: int = 10, timeout: int = 8) -> Dict[str, Any]:
        """Check all links for broken status."""
        links = soup.find_all("a", href=True)
        total_links = len(links)
        
        if total_links == 0:
            return {
                'b_links': 0,
                'b_url': "No links found on this page.",
                'b_verdict': "✓ No links to check",
                'total_links_checked': 0
            }
        
        # Collect unique URLs
        unique_urls: Set[str] = set()
        link_map: Dict[str, str] = {}
        
        for link in links:
            href = link.get("href", "").strip()
            if not href:
                continue
            
            # Skip non-HTTP protocols
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # Resolve URL
            if href.startswith('/'):
                href = urljoin(self.base_url, href)
            elif not href.startswith(('http://', 'https://')):
                href = urljoin(self.base_url, href)
            
            if href.startswith(('http://', 'https://')):
                anchor = link.get_text(strip=True) or "[No Text]"
                unique_urls.add(href)
                if href not in link_map:
                    link_map[href] = anchor
        
        if not unique_urls:
            return {
                'b_links': 0,
                'b_url': "No external links found to check.",
                'b_verdict': "✓ No external links",
                'total_links_checked': 0
            }
        
        logger.info(f"Checking {len(unique_urls)} unique links out of {total_links} total links...")
        
        # Check links concurrently
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(
                    lambda url: self._check_single_link(url, link_map.get(url, "[No Text]")),
                    unique_urls
                ))
        except Exception as e:
            logger.error(f"Error in concurrent link checking: {e}")
            results = [self._check_single_link(url, link_map.get(url, "[No Text]")) for url in unique_urls]
        
        # Process results
        broken_links = []
        restricted_links = []
        working_links = []
        
        for result in results:
            if result is None:
                continue
            if result.get("restricted"):
                restricted_links.append(result)
            elif result.get("is_broken"):
                broken_links.append(result)
            else:
                working_links.append(result)
        
        return self._format_results(
            broken_links, restricted_links, working_links, 
            unique_urls, total_links
        )
    
    def _check_single_link(self, url: str, anchor_text: str) -> Optional[Dict[str, Any]]:
        """Check a single link status."""
        # Determine link type
        try:
            url_domain = urlparse(url).netloc.lower().replace('www.', '')
            link_type = "internal" if url_domain == self.domain else "external"
        except (ValueError, TypeError):
            link_type = "external"
        
        try:
            start_time = time.time()
            
            # Try HEAD first, fall back to GET
            try:
                response = self.session.head(url, timeout=timeout, allow_redirects=True)
                if response.status_code in (405, 501):
                    response = self.session.get(url, timeout=timeout, allow_redirects=True, stream=True)
                    response.close()
            except requests.exceptions.RequestException:
                response = self.session.get(url, timeout=timeout, allow_redirects=True, stream=True)
                response.close()
            
            response_time = round((time.time() - start_time) * 1000, 2)
            redirects = len(response.history)
            status = response.status_code
            
            # Handle restricted
            if status == 403:
                return {
                    "url": url, "status": 403, 
                    "reason": "Forbidden / Access Restricted",
                    "anchor_text": anchor_text, "type": link_type,
                    "response_time": f"{response_time} ms", "restricted": True,
                    "is_broken": False, "redirects": redirects
                }
            
            # Handle success
            if 200 <= status < 300:
                if redirects > 3:
                    return {
                        "url": url, "status": status,
                        "reason": f"⚠️ Excessive Redirects ({redirects}x)",
                        "anchor_text": anchor_text, "type": link_type,
                        "response_time": f"{response_time} ms", "restricted": False,
                        "is_broken": True, "redirects": redirects
                    }
                return {
                    "url": url, "status": status,
                    "reason": "OK" + (f" (Redirected {redirects}x)" if redirects > 0 else ""),
                    "anchor_text": anchor_text, "type": link_type,
                    "response_time": f"{response_time} ms", "restricted": False,
                    "is_broken": False, "redirects": redirects
                }
            
            # Handle errors
            reason = self.STATUS_REASONS.get(status, response.reason)
            return {
                "url": url, "status": status,
                "reason": reason + (f" (Redirected {redirects}x)" if redirects > 0 else ""),
                "anchor_text": anchor_text, "type": link_type,
                "response_time": f"{response_time} ms", "restricted": False,
                "is_broken": True, "redirects": redirects
            }
            
        except requests.exceptions.SSLError:
            return {"url": url, "status": "SSL Error", "reason": "SSL Certificate Error",
                    "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                    "restricted": False, "is_broken": True, "redirects": 0}
        except requests.exceptions.Timeout:
            return {"url": url, "status": "Timeout", 
                    "reason": "Connection timed out",
                    "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                    "restricted": False, "is_broken": True, "redirects": 0}
        except requests.exceptions.ConnectionError:
            return {"url": url, "status": "Connection Error", 
                    "reason": "Unable to establish connection",
                    "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                    "restricted": False, "is_broken": True, "redirects": 0}
        except Exception as e:
            return {"url": url, "status": "Error", "reason": str(e)[:100],
                    "anchor_text": anchor_text, "type": link_type, "response_time": "-",
                    "restricted": False, "is_broken": True, "redirects": 0}
    
    def _format_results(self, broken: List[Dict], restricted: List[Dict], 
                       working: List[Dict], unique_urls: Set[str], 
                       total_links: int) -> Dict[str, Any]:
        """Format the check results into the expected structure."""
        total_broken = len(broken)
        total_working = len(working)
        internal_broken = sum(1 for link in broken if link["type"] == "internal")
        external_broken = sum(1 for link in broken if link["type"] == "external")
        
        # Group errors by type
        error_groups = defaultdict(list)
        for link in broken:
            status = str(link["status"])
            if "404" in status or "410" in status:
                error_groups["404"].append(link)
            elif "500" in status or "502" in status or "503" in status or "504" in status:
                error_groups["500"].append(link)
            elif "SSL" in status:
                error_groups["SSL"].append(link)
            elif "Timeout" in status:
                error_groups["Timeout"].append(link)
            elif "Connection" in status:
                error_groups["Connection"].append(link)
            elif "Redirects" in link.get("reason", ""):
                error_groups["Redirects"].append(link)
            else:
                error_groups["Other"].append(link)
        
        # Generate verdict
        if total_broken == 0 and len(restricted) == 0:
            verdict = "✓ Perfect - No broken links detected"
        elif internal_broken > 0:
            verdict = f"❌ Critical - {internal_broken} internal broken link(s) detected (High SEO Impact)"
        elif total_broken <= 3:
            verdict = f"⚠️ Minor - {total_broken} external broken link(s) found"
        else:
            verdict = f"❌ High Priority - {total_broken} broken links detected (Fix for better UX)"
        
        # Format link lists
        formatted_broken = self._format_link_list(broken[:50])
        formatted_restricted = self._format_link_list(restricted[:20])
        
        # Calculate health score
        health_score = round((total_working / len(unique_urls) * 100), 1) if unique_urls else 0
        
        return {
            'b_links': total_broken,
            'b_url': formatted_broken,
            'b_verdict': verdict,
            'total_links_checked': len(unique_urls),
            'working_links': total_working,
            'internal_broken': internal_broken,
            'external_broken': external_broken,
            'restricted_links_count': len(restricted),
            'restricted_links': formatted_restricted,
            'link_health_score': health_score,
            'broken_summary': {
                "404 Not Found": len(error_groups["404"]),
                "500 Server Error": len(error_groups["500"]),
                "SSL Error": len(error_groups["SSL"]),
                "Timeout": len(error_groups["Timeout"]),
                "Connection Error": len(error_groups["Connection"]),
                "Excessive Redirects": len(error_groups["Redirects"]),
                "Other": len(error_groups["Other"])
            },
            'checked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'broken_links_detail': broken[:20],
            'priority_fixes': [link for link in broken if link["type"] == "internal"]
        }
    
    def _format_link_list(self, links: List[Dict]) -> str:
        """Format a list of links for display."""
        if not links:
            return "No links found."
        
        lines = []
        for i, link in enumerate(links, 1):
            lines.append(
                f"{i}) [{link['type'].upper()}] {link['url']}\n"
                f"   Status: {link['status']} - {link['reason']}\n"
                f"   Anchor: {link['anchor_text']}\n"
                f"   Response Time: {link['response_time']}"
            )
        return "\n".join(lines)


class LinkService:
    """
    Unified service for link analysis and broken link checking.
    """
    
    def __init__(self, session: requests.Session, base_url: str, domain: str, final_url: str):
        self.session = session
        self.base_url = base_url
        self.domain = domain
        self.final_url = final_url
        self._analyzer = None
        self._checker = None
    
    def analyze_links(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze internal/external links."""
        if self._analyzer is None:
            self._analyzer = LinkAnalyzer(soup, self.base_url, self.domain, self.final_url)
        return self._analyzer.analyze()
    
    def check_broken_links(self, soup: BeautifulSoup, max_workers: int = 10, 
                         timeout: int = 8) -> Dict[str, Any]:
        """Check for broken links."""
        if self._checker is None:
            self._checker = BrokenLinkChecker(self.session, self.base_url, self.domain)
        return self._checker.check(soup, max_workers, timeout)
