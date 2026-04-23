"""Serper-based crawlers for source discovery.

Uses Serper (Google Search API) to discover new German health forums
and discussions that aren't covered by existing crawlers.
"""
import os
import logging
import asyncio
from typing import List, Dict, Any
import httpx

from crawlers.base_crawler import BaseCrawler
from crawlers.content_utils import deep_crawl_items
from crawlers.firecrawl_runner import FirecrawlClient
from utils.dates import parse_to_yyyy_mm_dd

logger = logging.getLogger(__name__)

# Maps domains from Serper results to canonical source names
# used by other crawlers (gutefrage, reddit, amazon, etc.)
DOMAIN_SOURCE_MAP = {
    "www.gutefrage.net": "gutefrage",
    "gutefrage.net": "gutefrage",
    "www.reddit.com": "reddit",
    "reddit.com": "reddit",
    "www.amazon.de": "amazon",
    "amazon.de": "amazon",
    "www.youtube.com": "youtube",
    "youtube.com": "youtube",
    "www.tiktok.com": "tiktok",
    "tiktok.com": "tiktok",
    "www.instagram.com": "instagram",
    "instagram.com": "instagram",
    "diabetes-forum.de": "diabetes_forum",
    "www.diabetes-forum.de": "diabetes_forum",
    "fragen.onmeda.de": "onmeda",
    "www.onmeda.de": "onmeda",
    "onmeda.de": "onmeda",
    "www.endometriose-vereinigung.de": "endometriose",
    "endometriose-vereinigung.de": "endometriose",
    "www.rheuma-liga.de": "rheuma_liga",
    "rheuma-liga.de": "rheuma_liga",
    # AI-cited competitors (Peec AI)
    "saneostore.de": "saneostore",
    "www.saneostore.de": "saneostore",
    "axion.shop": "axion",
    "www.axion.shop": "axion",
    "orthomechanik.de": "orthomechanik",
    "www.orthomechanik.de": "orthomechanik",
    "menstruflow.de": "menstruflow",
    "www.menstruflow.de": "menstruflow",
    # AI-cited editorial/review sites
    "chip.de": "chip",
    "www.chip.de": "chip",
    "testsieger.de": "testsieger",
    "www.testsieger.de": "testsieger",
    "idealo.de": "idealo",
    "www.idealo.de": "idealo",
    "faz.net": "faz",
    "www.faz.net": "faz",
}


def _resolve_source(url: str) -> str:
    """Resolve a URL to a canonical source name.

    Uses DOMAIN_SOURCE_MAP to match known domains to existing source names.
    Falls back to the raw domain for unmapped sites.
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
    except Exception:
        return "unknown"
    return DOMAIN_SOURCE_MAP.get(domain, domain)


class SerperClient:
    """Async client for Serper Google Search API."""

    BASE_URL = "https://google.serper.dev/search"

    # Google's tbs (time-based search) parameter values
    TIME_FILTERS = {
        "day": "qdr:d",    # Past 24 hours
        "week": "qdr:w",   # Past week
        "month": "qdr:m",  # Past month
        "year": "qdr:y",   # Past year
    }

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(
        self,
        query: str,
        gl: str = "de",
        hl: str = "de",
        num: int = 10,
        time_filter: str = None
    ) -> Dict[str, Any]:
        """Execute a search query via Serper API.

        Args:
            query: Search query string
            gl: Geolocation (default: Germany)
            hl: Language (default: German)
            num: Number of results to return
            time_filter: Time filter - "day", "week", "month", or "year"

        Returns:
            Serper API response with organic results
        """
        payload = {"q": query, "gl": gl, "hl": hl, "num": num}

        # Add time filter if specified
        if time_filter and time_filter in self.TIME_FILTERS:
            payload["tbs"] = self.TIME_FILTERS[time_filter]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.BASE_URL,
                headers={"X-API-KEY": self.api_key},
                json=payload
            )
            response.raise_for_status()
            return response.json()


class SerperDiscoveryCrawler(BaseCrawler):
    """Crawler for discovering new German health sources via Serper.

    Use cases:
    - Find forums/communities not in existing crawler list
    - Discover trending health discussions
    - Identify competitor mentions across the web

    The discovered URLs can be used to:
    1. Add high-value sources to dedicated crawlers
    2. Track brand/product mentions across the web
    3. Find content gaps and opportunities
    """

    name = "serper_discovery"
    tool = "serper"

    # Journey queries: pre-purchase stages 1-3 (awareness, consideration, comparison)
    # No brand terms — captures generic pain/solution discussions
    JOURNEY_QUERIES = [
        # Stage 1: Pain awareness
        "chronische Schmerzen was tun Forum",
        "starke Rückenschmerzen Ursache Hilfe",
        "Nackenschmerzen jeden Tag was hilft",
        "Bluthochdruck Symptome Erfahrung",
        "Regelschmerzen unerträglich Forum",
        # Stage 2: Solution seeking
        "Schmerztherapie ohne Medikamente Erfahrung",
        "Reizstromtherapie Erfahrungen Forum",
        "Wärmetherapie bei Rückenschmerzen",
        "Blutdruck selber messen sinnvoll",
        "TENS Therapie Erfahrung Schmerzen",
        # Stage 3: Method comparison
        "TENS oder Wärme was hilft besser",
        "Schmerztherapie Methoden Vergleich",
        "Blutdruckmessgerät Handgelenk oder Oberarm",
        "Infrarotlampe oder Wärmekissen Vergleich",
        "Reizstrom vs Physiotherapie Erfahrung",
    ]

    # Default discovery queries targeting German health discussions
    # Excludes known sources to find NEW ones
    DEFAULT_QUERIES = [
        # Blood pressure forums (exclude known sources)
        "Blutdruckmessgerät Erfahrungen Forum -site:gutefrage.net -site:amazon.de",
        "Blutdruck messen Tipps Community -site:reddit.com",
        "Hypertonie Selbsthilfe Deutschland Forum",

        # TENS/EMS pain therapy
        "TENS Gerät Erfahrungen Forum -site:gutefrage.net -site:amazon.de",
        "EMS Schmerztherapie Diskussion",
        "Reizstromgerät Empfehlung Community",

        # Menstrual pain (EM 59 target audience)
        "Regelschmerzen Hilfe Forum -site:gutefrage.net",
        "Menstruationsbeschwerden Tipps Community",
        "Endometriose Selbsthilfe Austausch",

        # Chronic pain / back pain
        "chronische Schmerzen Forum Deutschland",
        "Rückenschmerzen Selbsthilfe Community",
        "Schmerzpatienten Austausch Forum",

        # Infrared / heat therapy
        "Infrarotlampe Erfahrungen Forum -site:gutefrage.net -site:amazon.de",
        "Rotlichtlampe Schmerztherapie Diskussion",
        "Wärmelampe Gesundheit Anwendung Community",
        "Infrarot Wärmebehandlung Erfahrung Forum",

        # Brand/product mentions
        "Beurer Blutdruckmessgerät Test Erfahrung",
        "Beurer TENS Gerät Bewertung",
        "Beurer Infrarotlampe Erfahrung",
        "Omron vs Beurer Vergleich",

        # Competitor brand discovery
        "AUVON TENS Gerät Erfahrung",
        "Orthomechanik TENS EMS Erfahrung",
        "Comfytemp TENS Wärmegürtel Erfahrung",
        "Medisana Infrarotlampe Erfahrung",
        # AI-cited editorial sources (Peec AI data)
        "site:chip.de Blutdruckmessgerät Test",
        "site:chip.de TENS Gerät Test",
        "site:chip.de Beurer Test",
        "site:chip.de Infrarotlampe Test",
        "site:testsieger.de Blutdruckmessgerät",
        "site:testsieger.de TENS Gerät",
        "site:testsieger.de Beurer",
        # Price/review site (Peec AI: 11% citation rate)
        "site:idealo.de Beurer Blutdruckmessgerät",
        "site:idealo.de Beurer TENS",
        "site:idealo.de Blutdruckmessgerät Vergleich",
        # Lower priority editorial
        "site:faz.net Blutdruckmessgerät",
        "site:faz.net TENS Schmerztherapie",
    ]

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable must be set")
        self.serper = SerperClient(self.api_key)
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover new sources via Serper search.

        Args:
            config: Configuration dict with optional keys:
                - queries: List of search queries (defaults to DEFAULT_QUERIES)
                - max_queries: Max number of queries to run (default: all)
                - results_per_query: Results per query (default: 10)
                - delay: Seconds between queries (default: 1.0)
                - weekly_mode: If True, filter results to past week via API
                - time_filter: Explicit time filter ("day", "week", "month", "year")
                - deep_crawl: If True (default), scrape each URL for full content
                - max_deep_crawl: Max items to deep crawl (default: 50)

        Returns:
            List of discovered items with source URLs and snippets
        """
        custom_queries = config.get("queries")
        results_per_query = config.get("results_per_query", 10)
        delay = config.get("delay", 1.0)

        # Determine time filter for API-level filtering
        time_filter = config.get("time_filter")
        if config.get("weekly_mode") and not time_filter:
            time_filter = "week"
            logger.info("[serper] Weekly mode enabled - using 'week' time filter")

        # Build tagged query list: (query, collection_type)
        if custom_queries:
            tagged_queries = [(q, "brand") for q in custom_queries]
        else:
            tagged_queries = [(q, "brand") for q in self.DEFAULT_QUERIES] + \
                             [(q, "journey") for q in self.JOURNEY_QUERIES]

        max_queries = config.get("max_queries", len(tagged_queries))
        tagged_queries = tagged_queries[:max_queries]
        all_items = []
        seen_urls = set()

        for i, (query, collection_type) in enumerate(tagged_queries):
            try:
                logger.info(f"[serper] ({i+1}/{len(tagged_queries)}) Searching [{collection_type}]: {query}")

                results = await self.serper.search(query, num=results_per_query, time_filter=time_filter)
                organic = results.get("organic", [])

                for result in organic:
                    url = result.get("link", "")

                    # Skip duplicates within this run
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Extract content from title + snippet
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    content = f"{title}\n\n{snippet}" if snippet else title

                    # Skip if content too short (likely not useful)
                    if len(content) < 30:
                        continue

                    # Extract date from Serper result (German format: "26.12.2025")
                    result_date = result.get("date")
                    posted_at = parse_to_yyyy_mm_dd(result_date)

                    item = {
                        "source": _resolve_source(url),
                        "source_url": url,
                        "title": title[:500] if title else None,
                        "content": content[:2000],
                        "posted_at": posted_at,
                        "crawler_tool": "serper",
                        "collection_type": collection_type,
                        "raw_data": {
                            "query": query,
                            "position": result.get("position"),
                            "snippet": snippet,
                            "domain": self._extract_domain(url),
                            "original_date": result_date,
                        }
                    }
                    all_items.append(item)

                logger.info(f"[serper] Found {len(organic)} results for query")

                # Rate limiting between queries
                if i < len(tagged_queries) - 1:
                    await asyncio.sleep(delay)

            except httpx.HTTPStatusError as e:
                logger.error(f"[serper] HTTP error for '{query}': {e.response.status_code}")
                continue
            except Exception as e:
                logger.error(f"[serper] Error searching '{query}': {e}")
                continue

        logger.info(f"[serper] Total unique items discovered: {len(all_items)}")

        # Deep crawl: scrape each URL for full page content via Firecrawl
        deep_crawl = config.get("deep_crawl", True)
        if deep_crawl and self.firecrawl_api_key:
            max_deep = config.get("max_deep_crawl", 50)
            logger.info(f"[serper] Starting deep crawl for up to {max_deep} items")
            firecrawl = FirecrawlClient(self.firecrawl_api_key)
            all_items = await deep_crawl_items(all_items, firecrawl, max_items=max_deep)
        elif deep_crawl and not self.firecrawl_api_key:
            logger.warning("[serper] Deep crawl requested but FIRECRAWL_API_KEY not set, skipping")

        return all_items

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for categorization."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""


class SerperBrandMentionsCrawler(BaseCrawler):
    """Crawler for finding Beurer brand/product mentions across the web.

    Specialized version of discovery crawler focused on:
    - Beurer product reviews and discussions
    - Competitor comparisons
    - Brand sentiment tracking
    """

    name = "serper_brand"
    tool = "serper"

    # Comprehensive Beurer product queries
    BRAND_QUERIES = [
        # ===========================================
        # BEURER BLOOD PRESSURE MONITORS (BM/BC Series)
        # ===========================================
        # BM 27 - Bestseller (Priority 1)
        "Beurer BM 27 Erfahrung",
        "Beurer BM 27 Test",
        "Beurer BM 27 Bewertung Forum",
        "Beurer BM 27 Genauigkeit",
        "Beurer BM 27 Probleme",

        # BM 25 (Priority 1)
        "Beurer BM 25 Erfahrung",
        "Beurer BM 25 Test",

        # BM 81 - easyLock (Priority 1)
        "Beurer BM 81 Erfahrung",
        "Beurer BM 81 Test",
        "Beurer BM 81 easyLock",

        # BM 53 - Bluetooth (Priority 2)
        "Beurer BM 53 Erfahrung",
        "Beurer BM 53 Test",

        # BM 54 - Bluetooth model (Priority 2)
        "Beurer BM 54 Erfahrung",
        "Beurer BM 54 Test",
        "Beurer BM 54 App Bluetooth",

        # BM 64 (Priority 2)
        "Beurer BM 64 Erfahrung",
        "Beurer BM 64 Test",

        # BC 54 - Wrist (Priority 2)
        "Beurer BC 54 Erfahrung",
        "Beurer BC 54 Test",

        # BC 27 - Wrist (Priority 2)
        "Beurer BC 27 Erfahrung",
        "Beurer BC 27 Test",

        # BM 59 (Priority 3)
        "Beurer BM 59 Erfahrung",
        "Beurer BM 59 Test",

        # BM 96 (Priority 3)
        "Beurer BM 96 Erfahrung",
        "Beurer BM 96 Test",

        # BM 58 - Premium (Priority 4, legacy)
        "Beurer BM 58 Erfahrung",
        "Beurer BM 58 Test Bewertung",

        # BM 77 - Bluetooth premium (Priority 4, legacy)
        "Beurer BM 77 Test",
        "Beurer BM 77 Erfahrung",

        # BM 85 - Top model (Priority 4, legacy)
        "Beurer BM 85 Erfahrung",
        "Beurer BM 85 Test",

        # General blood pressure
        "Beurer Blutdruckmessgerät Erfahrung",
        "Beurer Blutdruckmessgerät Test 2025",
        "Beurer Blutdruckmessgerät Test 2026",
        "Beurer Blutdruckmessgerät Genauigkeit",
        "Beurer Blutdruckmessgerät Manschette Problem",
        "Beurer Oberarm Blutdruckmessgerät Forum",
        "Beurer Handgelenk Blutdruckmessgerät Forum",

        # ===========================================
        # BEURER TENS/EMS DEVICES (EM Series)
        # ===========================================
        # EM 59 - Menstrual pain (Heat + TENS) (Priority 1)
        "Beurer EM 59 Erfahrung",
        "Beurer EM 59 Regelschmerzen",
        "Beurer EM 59 Test Menstruation",
        "Beurer EM 59 Bewertung",

        # EM 89 - Back/neck pain (Priority 1)
        "Beurer EM 89 Erfahrung",
        "Beurer EM 89 Rückenschmerzen",
        "Beurer EM 89 Test Nacken",

        # EM 50 (Priority 2)
        "Beurer EM 50 Erfahrung",
        "Beurer EM 50 Test",

        # EM 55 (Priority 2)
        "Beurer EM 55 Erfahrung",
        "Beurer EM 55 Test",

        # EM 49 - Digital TENS/EMS (Priority 3, legacy)
        "Beurer EM 49 Erfahrung",
        "Beurer EM 49 Test",
        "Beurer EM 49 Anwendung",

        # EM 80 - Digital TENS/EMS (Priority 3, legacy)
        "Beurer EM 80 Erfahrung",
        "Beurer EM 80 Test",

        # General TENS/EMS
        "Beurer TENS Gerät Erfahrung",
        "Beurer TENS Gerät Test 2025",
        "Beurer TENS Gerät Test 2026",
        "Beurer EMS Gerät Bewertung",
        "Beurer Reizstromgerät Forum",

        # ===========================================
        # BEURER INFRARED DEVICES (IL Series)
        # ===========================================
        "Beurer IL 50 Erfahrung",
        "Beurer IL 50 Test",
        "Beurer IL 60 Erfahrung",
        "Beurer IL 60 Test",
        "Beurer Infrarotlampe Erfahrung",
        "Beurer Infrarotlampe Test 2025",
        "Beurer Infrarotlampe Test 2026",
        "Beurer Rotlichtlampe Bewertung",

        # ===========================================
        # COMPETITOR PRODUCTS - Blood Pressure
        # ===========================================
        "Omron M500 Erfahrung",
        "Omron M500 Test",
        "Omron M400 Erfahrung",
        "Omron M400 Test",
        "Withings BPM Erfahrung",
        "Withings BPM Connect Test",

        # ===========================================
        # COMPETITOR PRODUCTS - TENS/EMS
        # ===========================================
        "AUVON TENS Gerät Erfahrung",
        "AUVON TENS Gerät Test",
        "Orthomechanik TENS EMS Erfahrung",
        "Orthomechanik TENS EMS Test",
        "Comfytemp TENS Gerät Erfahrung",
        "Comfytemp TENS Gerät Test",
        "GHTENS Erfahrung",
        "GHTENS Test",

        # ===========================================
        # COMPETITOR PRODUCTS - Infrared / Heat
        # ===========================================
        "Comfytemp Wärmegürtel Erfahrung",
        "Comfytemp Wärmegürtel Test",
        "Slimpal Wärmegürtel Erfahrung",
        "Slimpal Wärmegürtel Test",
        "Medisana IR 850 Erfahrung",
        "Medisana IR 850 Test",
        "Medisana Infrarotlampe Erfahrung",

        # ===========================================
        # COMPETITOR COMPARISONS
        # ===========================================
        "Beurer vs Omron Blutdruckmessgerät",
        "Beurer vs Omron Vergleich",
        "Beurer oder Omron besser",
        "Beurer vs Sanitas Blutdruck",
        "Beurer vs Boso Blutdruckmessgerät",
        "Beurer vs Withings BPM",
        "Omron M500 vs Beurer",
        "Omron M400 vs Beurer BM 27",
        "AUVON vs Beurer TENS",
        "Beurer vs Comfytemp TENS",
        "Beurer vs Medisana Infrarotlampe",
        "bestes Blutdruckmessgerät 2025 Test",
        "bestes Blutdruckmessgerät 2026 Test",
        "bestes TENS Gerät 2025 Test",
        "bestes TENS Gerät 2026 Test",
        "beste Infrarotlampe 2025 Test",
        "beste Infrarotlampe 2026 Test",

        # ===========================================
        # BRAND REPUTATION & SERVICE
        # ===========================================
        "Beurer Qualität Erfahrung",
        "Beurer Kundenservice Erfahrung",
        "Beurer Garantie Erfahrung",
        "Beurer Reparatur Service",
        "Beurer Made in Germany",
        "Beurer Produkte Bewertung",

        # ===========================================
        # SPECIFIC USE CASES
        # ===========================================
        "Beurer Blutdruckmessgerät Vorhofflimmern",
        "Beurer Blutdruckmessgerät Arrhythmie",
        "Beurer TENS Schwangerschaft",
        "Beurer TENS Rückenschmerzen Erfahrung",
        "Beurer Wärmegürtel Regelschmerzen",
        "Beurer Infrarotlampe Rückenschmerzen",
        "Beurer Infrarotlampe Erkältung",

        # ===========================================
        # AI-CITED COMPETITOR WEBSHOPS (Peec AI data)
        # ===========================================
        # SaneoTENS / saneostore.de — 26% AI citation rate (#1 TENS competitor)
        "site:saneostore.de TENS Gerät",
        "site:saneostore.de Schmerztherapie Ratgeber",
        "SaneoTENS Erfahrung",
        "SaneoTENS Test",
        "SaneoTENS vs Beurer",
        # Axion / axion.shop — 16% AI citation rate
        "site:axion.shop TENS EMS Gerät",
        "site:axion.shop Schmerztherapie",
        "Axion TENS Erfahrung",
        "Axion TENS Test",
        # Orthomechanik — 14% AI citation rate (already in competitor discovery above, add site: queries)
        "site:orthomechanik.de TENS EMS",
        "site:orthomechanik.de Schmerztherapie",
        # Menstruflow — 7% AI citation rate (period pain competitor)
        "site:menstruflow.de TENS Regelschmerzen",
        "site:menstruflow.de Endometriose",
        "Menstruflow TENS Erfahrung",
        "Menstruflow vs Beurer EM 59",
    ]

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable must be set")
        self.serper = SerperClient(self.api_key)
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find brand mentions via Serper search.

        Args:
            config: Configuration dict with optional keys:
                - queries: Custom queries (defaults to BRAND_QUERIES)
                - max_queries: Max queries to run
                - results_per_query: Results per query (default: 10)
                - weekly_mode: If True, filter results to past week via API
                - time_filter: Explicit time filter ("day", "week", "month", "year")
                - deep_crawl: If True (default), scrape each URL for full content
                - max_deep_crawl: Max items to deep crawl (default: 50)

        Returns:
            List of items mentioning Beurer or competitors
        """
        queries = config.get("queries", self.BRAND_QUERIES)
        max_queries = config.get("max_queries", len(queries))
        results_per_query = config.get("results_per_query", 10)

        # Determine time filter for API-level filtering
        time_filter = config.get("time_filter")
        if config.get("weekly_mode") and not time_filter:
            time_filter = "week"
            logger.info("[serper_brand] Weekly mode enabled - using 'week' time filter")

        queries = queries[:max_queries]
        all_items = []
        seen_urls = set()

        for i, query in enumerate(queries):
            try:
                logger.info(f"[serper_brand] ({i+1}/{len(queries)}) Searching: {query}")

                results = await self.serper.search(query, num=results_per_query, time_filter=time_filter)
                organic = results.get("organic", [])

                for result in organic:
                    url = result.get("link", "")

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    content = f"{title}\n\n{snippet}" if snippet else title

                    if len(content) < 30:
                        continue

                    # Extract date from Serper result (German format: "26.12.2025")
                    result_date = result.get("date")
                    posted_at = parse_to_yyyy_mm_dd(result_date)

                    item = {
                        "source": _resolve_source(url),
                        "source_url": url,
                        "title": title[:500] if title else None,
                        "content": content[:2000],
                        "posted_at": posted_at,
                        "crawler_tool": "serper",
                        "collection_type": "brand",
                        "raw_data": {
                            "query": query,
                            "position": result.get("position"),
                            "snippet": snippet,
                            "domain": self._extract_domain(url),
                            "original_date": result_date,
                        }
                    }
                    all_items.append(item)

                logger.info(f"[serper_brand] Found {len(organic)} results")

                if i < len(queries) - 1:
                    await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"[serper_brand] Error: {e}")
                continue

        logger.info(f"[serper_brand] Total unique items discovered: {len(all_items)}")

        # Deep crawl: scrape each URL for full page content via Firecrawl
        deep_crawl = config.get("deep_crawl", True)
        if deep_crawl and self.firecrawl_api_key:
            max_deep = config.get("max_deep_crawl", 50)
            logger.info(f"[serper_brand] Starting deep crawl for up to {max_deep} items")
            firecrawl = FirecrawlClient(self.firecrawl_api_key)
            all_items = await deep_crawl_items(all_items, firecrawl, max_items=max_deep)
        elif deep_crawl and not self.firecrawl_api_key:
            logger.warning("[serper_brand] Deep crawl requested but FIRECRAWL_API_KEY not set, skipping")

        return all_items

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for categorization."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""
