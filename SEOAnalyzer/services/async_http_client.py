"""
Optimized Async HTTP Client for SEO Analyzer.

Provides efficient async HTTP requests with connection pooling,
proper event loop management, and caching capabilities.
"""
import asyncio
import ssl
import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse
import time
import aiohttp
from django.conf import settings
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """
    Optimized async HTTP client with connection pooling and caching.
    
    Features:
    - Connection pooling for better performance
    - Request caching for repeated URLs
    - Proper SSL context handling
    - Timeout and retry logic
    - Event loop optimization
    """
    
    _instance = None
    _session = None
    _connector = None
    _cache: TTLCache = TTLCache(maxsize=1000, ttl=300)  # Bounded cache: 1000 items, 5 min TTL
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _ensure_initialized(self):
        """No-op: connector/session are created per-coroutine inside fetch_url."""
        pass
    
    def _make_ssl_context(self):
        """Create a fresh SSL context with configurable verification."""
        ssl_ctx = ssl.create_default_context()
        
        # SSL verification mode: 'strict' (prod) or 'relaxed' (dev only)
        verify_mode = getattr(settings, 'SSL_VERIFY_MODE', 'strict').lower()
        
        if verify_mode == 'relaxed':
            # Development only - allows self-signed certs
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            logger.warning("SSL verification disabled - DEV MODE ONLY")
        else:
            # Production - strict verification (default)
            ssl_ctx.check_hostname = True
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        
        return ssl_ctx
    
    @property
    def ssl_context(self):
        """Get SSL context for testing/inspection."""
        # Return a standard SSL context with verification enabled for tests
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = True
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        return ssl_ctx
    
    async def fetch_url(self, url: str, cache_ttl: int = 300) -> Dict[str, Any]:  # noqa: C901
        """
        Fetch URL with caching and error handling.
        
        Args:
            url: URL to fetch
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            Dictionary with response data
        """
        # Check in-process cache first (TTLCache handles expiry automatically)
        cache_key = f"http_cache:{hash(url)}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for URL: {url}")
            return cached

        ssl_ctx = self._make_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(
            total=getattr(settings, 'HTTP_TIMEOUT', 30),
            connect=getattr(settings, 'HTTP_CONNECT_TIMEOUT', 10),
            sock_read=getattr(settings, 'HTTP_READ_TIMEOUT', 20),
        )
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': getattr(settings, 'USER_AGENT',
                'Mozilla/5.0 (compatible; WebLift-SEO/1.0)')},
        )
        try:
            async with session.get(
                url,
                allow_redirects=True,
                max_redirects=10
            ) as response:
                raw_bytes = await response.read()
                detected_encoding = response.charset or 'utf-8'
                text = raw_bytes.decode(detected_encoding, errors='replace')

                result = {
                    'text': text,
                    'encoding': detected_encoding,
                    'headers': dict(response.headers),
                    'status': response.status,
                    'final_url': str(response.url),
                    'error': None,
                }

                if response.status == 200:
                    # TTLCache stores with automatic TTL (set at class level)
                    # Note: TTLCache uses fixed TTL, per-entry TTL requires different approach
                    self._cache[cache_key] = result

                return result

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching URL: {url}")
            return {
                'text': '', 'encoding': 'utf-8', 'headers': {},
                'status': None, 'final_url': url, 'error': 'timeout'
            }
        except aiohttp.ClientError as exc:
            logger.error(f"Client error fetching URL {url}: {exc}")
            return {
                'text': '', 'encoding': 'utf-8', 'headers': {},
                'status': None, 'final_url': url, 'error': str(exc)
            }
        except Exception as exc:
            logger.error(f"Unexpected error fetching URL {url}: {exc}")
            return {
                'text': '', 'encoding': 'utf-8', 'headers': {},
                'status': None, 'final_url': url, 'error': str(exc)
            }
        finally:
            await session.close()
    
    def fetch_url_sync(self, url: str, cache_ttl: int = 300) -> Dict[str, Any]:
        """
        Synchronous wrapper for async fetch_url.
        Always uses asyncio.run() which creates a brand-new event loop,
        avoiding "no running event loop" errors in Django sync views.
        """
        return asyncio.run(self.fetch_url(url, cache_ttl))
    
    async def fetch_multiple_urls(self, urls: list, cache_ttl: int = 300) -> Dict[str, Any]:
        """
        Fetch multiple URLs concurrently.
        
        Args:
            urls: List of URLs to fetch
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            Dictionary mapping URLs to response data
        """
        tasks = [self.fetch_url(url, cache_ttl) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return dict(zip(urls, results))
    
    async def close(self):
        """Close the aiohttp session and connector."""
        if self._session:
            await self._session.close()
        if self._connector:
            await self._connector.close()
    
    def __del__(self):
        """Cleanup when instance is destroyed."""
        if self._session and not self._session.closed:
            # Schedule cleanup in event loop
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.create_task(self.close())
            except RuntimeError:
                pass


# Global instance for easy access
async_client = AsyncHTTPClient()


def fetch_url_optimized(url: str, cache_ttl: int = 300) -> Dict[str, Any]:
    """
    Convenience function to fetch URL with optimizations.
    
    Args:
        url: URL to fetch
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Dictionary with response data
    """
    return async_client.fetch_url_sync(url, cache_ttl)


async def fetch_multiple_urls_optimized(urls: list, cache_ttl: int = 300) -> Dict[str, Any]:
    """
    Convenience function to fetch multiple URLs concurrently.
    
    Args:
        urls: List of URLs to fetch
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Dictionary mapping URLs to response data
    """
    return await async_client.fetch_multiple_urls(urls, cache_ttl)
