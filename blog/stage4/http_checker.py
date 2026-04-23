"""
HTTP Checker - Verify URL accessibility via HTTP requests.

Performs HEAD/GET requests to check if URLs are alive.
Cherry-picked and improved from existing stage-4 code.
"""

import asyncio
import logging
import os
import re
import time
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Default timeout can be overridden via environment variable
# Reduced for faster blog generation
DEFAULT_HTTP_TIMEOUT = float(os.getenv("HTTP_CHECK_TIMEOUT", "3.0"))
DEFAULT_MAX_CONCURRENT = int(os.getenv("HTTP_CHECK_MAX_CONCURRENT", "20"))


@dataclass
class HTTPCheckResult:
    """Result of an HTTP check for a single URL."""
    url: str
    is_alive: bool
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None
    is_homepage_redirect: bool = False


def _is_homepage_path(path: str) -> bool:
    """Check if a URL path looks like a homepage (root or shallow locale path)."""
    clean = path.rstrip("/")
    if not clean:
        return True  # Root path
    segments = [s for s in clean.split("/") if s]
    if len(segments) <= 1 and re.match(r'^[a-z]{2}(-[a-z]{2})?$', segments[0] if segments else ''):
        return True
    return False


class HTTPChecker:
    """
    Checks URL accessibility via HTTP requests.

    Features:
    - Parallel async requests
    - HEAD first, fallback to GET
    - Follows redirects
    - Configurable timeout
    - Rate limiting
    """

    def __init__(
        self,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        user_agent: str = "OpenBlog-URLVerifier/1.0"
    ):
        """
        Initialize HTTP checker.

        Args:
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests
            user_agent: User-Agent header for requests
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.user_agent = user_agent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def check_urls(self, urls: Set[str]) -> List[HTTPCheckResult]:
        """
        Check multiple URLs in parallel.

        Args:
            urls: Set of URLs to check

        Returns:
            List of HTTPCheckResult objects
        """
        logger.info(f"Checking {len(urls)} URLs (max {self.max_concurrent} concurrent)")

        tasks = [self._check_single(url) for url in urls]
        results = await asyncio.gather(*tasks)

        alive = sum(1 for r in results if r.is_alive)
        dead = len(results) - alive
        logger.info(f"HTTP check complete: {alive} alive, {dead} dead")

        return results

    async def check_url(self, url: str) -> HTTPCheckResult:
        """
        Check a single URL.

        Args:
            url: URL to check

        Returns:
            HTTPCheckResult
        """
        return await self._check_single(url)

    async def _check_single(self, url: str) -> HTTPCheckResult:
        """Check a single URL with semaphore for rate limiting."""
        async with self._semaphore:
            return await self._do_check(url)

    async def _do_check(self, url: str) -> HTTPCheckResult:
        """
        Perform the actual HTTP check.

        Strategy:
        1. Try HEAD request (faster)
        2. If HEAD fails with 405, try GET
        3. Follow redirects and capture final URL
        """
        start = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent}
            ) as client:
                # Try HEAD first (faster, less bandwidth)
                response = await client.head(url)

                # Some servers reject HEAD with 405, try GET
                if response.status_code == 405:
                    response = await client.get(url)

                elapsed = (time.monotonic() - start) * 1000

                # Determine final URL after redirects
                final_url = str(response.url) if response.url != url else None

                # Consider 2xx and 3xx as alive
                is_alive = response.status_code < 400

                # Detect homepage redirects
                is_homepage_redirect = False
                if final_url and is_alive:
                    from urllib.parse import urlparse
                    is_homepage_redirect = _is_homepage_path(urlparse(final_url).path)

                return HTTPCheckResult(
                    url=url,
                    is_alive=is_alive,
                    status_code=response.status_code,
                    final_url=final_url,
                    response_time_ms=elapsed,
                    is_homepage_redirect=is_homepage_redirect
                )

        except httpx.TimeoutException:
            elapsed = (time.monotonic() - start) * 1000
            return HTTPCheckResult(
                url=url,
                is_alive=False,
                error="Timeout",
                response_time_ms=elapsed
            )

        except httpx.ConnectError as e:
            elapsed = (time.monotonic() - start) * 1000
            return HTTPCheckResult(
                url=url,
                is_alive=False,
                error=f"Connection error: {str(e)[:100]}",
                response_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return HTTPCheckResult(
                url=url,
                is_alive=False,
                error=f"Error: {str(e)[:100]}",
                response_time_ms=elapsed
            )

    def categorize_results(
        self,
        results: List[HTTPCheckResult]
    ) -> Tuple[List[str], List[str]]:
        """
        Categorize results into alive and dead URLs.

        Args:
            results: List of HTTPCheckResult

        Returns:
            Tuple of (alive_urls, dead_urls)
        """
        alive = [r.url for r in results if r.is_alive]
        dead = [r.url for r in results if not r.is_alive]
        return alive, dead


async def check_urls(
    urls: Set[str],
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
) -> List[HTTPCheckResult]:
    """
    Convenience function to check URLs.

    Args:
        urls: Set of URLs to check
        timeout: Request timeout in seconds
        max_concurrent: Maximum concurrent requests

    Returns:
        List of HTTPCheckResult
    """
    checker = HTTPChecker(timeout=timeout, max_concurrent=max_concurrent)
    return await checker.check_urls(urls)


async def check_source_urls(
    urls: List[str],
    timeout: float = 3.0,
    max_concurrent: int = 10,
) -> Tuple[List[str], List[str]]:
    """Quick check which source URLs are alive. Returns (alive_urls, dead_urls).

    Treats homepage redirects as dead (URL resolved to site root, not the
    original resource).
    """
    if not urls:
        return [], []
    checker = HTTPChecker(timeout=timeout, max_concurrent=max_concurrent)
    results = await checker.check_urls(set(urls))
    alive, dead = checker.categorize_results(results)
    # Also treat homepage redirects as dead
    homepage_redirects = {r.url for r in results if r.is_homepage_redirect}
    alive = [u for u in alive if u not in homepage_redirects]
    dead = dead + list(homepage_redirects)
    return alive, dead
