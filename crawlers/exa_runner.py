"""Exa-based crawler for SEO/AEO/GEO industry news.

Uses Exa.ai (semantic search API) to discover and extract recent articles
from authoritative SEO, AEO, and GEO news sources. Returns full article
content in one call (no separate scraping step needed).
"""
import os
import logging
from typing import List, Dict, Any
import httpx

from crawlers.base_crawler import BaseCrawler
from utils.dates import parse_to_yyyy_mm_dd

logger = logging.getLogger(__name__)

# ─── Curated source domains by tier ────────────────────────────────

# Tier 1: Must-have, crawl weekly+
TIER1_DOMAINS = [
    "searchengineland.com",
    "searchenginejournal.com",
    "seroundtable.com",
    "developers.google.com",
    "blog.google",
    "semrush.com",
    "ahrefs.com",
    "moz.com",
    "firstpagesage.com",
    "evergreen.media",
]

# Tier 2: High priority, crawl weekly
TIER2_DOMAINS = [
    "seo-suedwest.de",
    "sistrix.com",
    "backlinko.com",
    "t3n.de",
    "marketingdive.com",
    "fatjoe.com",
]

# Tier 3: Monitor, biweekly (UCP/privacy + Google AI)
TIER3_DOMAINS = [
    "usercentrics.com",
    "didomi.io",
    "seoclarity.net",
    "techpolicy.press",
    "conductor.com",
    "research.google",
    "ai.google",
]

ALL_NEWS_DOMAINS = TIER1_DOMAINS + TIER2_DOMAINS + TIER3_DOMAINS

# Default queries for broad SEO/AEO/GEO discovery (used as fallback)
DEFAULT_NEWS_QUERIES = [
    "SEO latest developments and algorithm updates",
    "AEO answer engine optimization strategies",
    "GEO generative engine optimization research",
    "Google AI Overviews impact on search",
    "AI search optimization for brands",
    "UCP user choice platform privacy SEO impact",
    "Google consent mode v2 SEO implications",
    "zero-click searches AI overviews",
    "structured data schema markup updates",
    "SEO content strategy AI era",
]


def build_tenant_news_queries(tenant_config) -> List[str]:
    """Build news queries tailored to a tenant's company, industry, and products.

    Generates 3 layers of queries:
    1. Company/brand news — what's happening with this company
    2. Industry + competitor news — market trends and competitor moves
    3. Generic SEO/AEO/GEO — always relevant for digital marketing

    Returns ~12-15 queries (deduped).
    """
    queries = []
    company = tenant_config.company_name
    industry = tenant_config.industry or ""
    brands = tenant_config.competitor_brands[:5]
    categories = [c.label_en or c.key for c in tenant_config.categories if c.key != "other"][:4]

    # Layer 1: Company-specific news
    queries.append(f"{company} news latest developments")
    queries.append(f"{company} product launch announcement")
    if industry:
        queries.append(f"{company} {industry} market strategy")

    # Layer 2: Industry + competitor news
    if industry:
        queries.append(f"{industry} market trends news")
        queries.append(f"{industry} industry analysis latest")
    for brand in brands[:3]:
        queries.append(f"{brand} news product updates")

    # Layer 3: Category-specific market news
    for cat in categories[:3]:
        queries.append(f"{cat} market trends consumer news")

    # Layer 4: Generic SEO/AEO/GEO (always relevant, pick a subset)
    queries.extend([
        "SEO latest developments and algorithm updates",
        "Google AI Overviews impact on search",
        "AI search optimization for brands",
        "GEO generative engine optimization research",
    ])

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique


class ExaClient:
    """Async client for Exa.ai search API."""

    BASE_URL = "https://api.exa.ai"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_and_contents(
        self,
        query: str,
        num_results: int = 10,
        include_domains: List[str] = None,
        start_published_date: str = None,
        end_published_date: str = None,
        category: str = None,
        text_max_characters: int = 3000,
        search_type: str = "auto",
        summary: bool = False,
    ) -> Dict[str, Any]:
        """Search and extract content in one call.

        Args:
            query: Semantic search query
            num_results: Max results per query
            include_domains: Restrict to these domains (optional)
            start_published_date: ISO date string (e.g. "2026-02-28")
            end_published_date: ISO date string
            category: Content category filter (e.g. "news", "research paper")
            text_max_characters: Max chars of content to extract per result
            search_type: "auto", "neural", "keyword"

        Returns:
            Exa API response with results including full text content
        """
        contents = {
            "text": {"maxCharacters": text_max_characters},
        }
        if summary:
            contents["summary"] = True

        payload = {
            "query": query,
            "numResults": num_results,
            "type": search_type,
            "contents": contents,
        }

        if include_domains:
            payload["includeDomains"] = include_domains
        if start_published_date:
            payload["startPublishedDate"] = start_published_date
        if end_published_date:
            payload["endPublishedDate"] = end_published_date
        if category:
            payload["category"] = category

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/search",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()


class ExaNewsCrawler(BaseCrawler):
    """Crawls SEO/AEO/GEO news from curated sources via Exa.ai.

    Usage:
        POST /crawl
        {
            "crawler": "exa_news",
            "max_pages": 5,          // queries to run (default: all DEFAULT_NEWS_QUERIES)
            "queries": ["custom query 1", "custom query 2"]  // optional override
        }

    Config options:
        - queries: List of search queries (default: DEFAULT_NEWS_QUERIES)
        - max_queries: Max number of queries to run
        - num_results: Results per query (default: 10)
        - domains: "all" (default), "tier1", "tier2", "tier3", or list of domains
        - days_back: How many days back to search (default: 7)
        - category: Exa category filter (e.g. "news", "research paper")
    """

    name = "exa_news"
    tool = "exa"

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY not set in environment")

        client = ExaClient(api_key)

        # Build queries: explicit > tenant-aware > generic fallback
        if config.get("queries"):
            queries = config["queries"]
        elif getattr(self, 'tenant_config', None):
            queries = build_tenant_news_queries(self.tenant_config)
            logger.info(f"[exa_news] Built {len(queries)} tenant-aware queries for {self.tenant_config.company_name}")
        else:
            queries = DEFAULT_NEWS_QUERIES

        max_queries = config.get("max_queries", len(queries))
        queries = queries[:max_queries]

        # Resolve domain restriction
        # For tenant-specific queries (company/industry), search broadly (no domain filter)
        # For generic SEO queries, restrict to curated news sources
        domains_config = config.get("domains", "auto")
        use_domains_for_generic = ALL_NEWS_DOMAINS
        if domains_config == "tier1":
            use_domains_for_generic = TIER1_DOMAINS
        elif domains_config == "tier2":
            use_domains_for_generic = TIER1_DOMAINS + TIER2_DOMAINS
        elif domains_config == "none":
            use_domains_for_generic = None
        elif isinstance(domains_config, list):
            use_domains_for_generic = domains_config

        # Identify which queries are generic SEO vs tenant-specific
        generic_prefixes = {"seo ", "aeo ", "geo ", "google ai", "ucp ", "zero-click", "structured data", "ai search"}
        def _is_generic(q: str) -> bool:
            q_lower = q.lower()
            return any(q_lower.startswith(p) for p in generic_prefixes)

        # Date range
        days_back = config.get("days_back", 7)
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59.000Z")

        num_results = config.get("num_results", 10)
        category = config.get("category")

        items = []
        seen_urls = set()

        for query in queries:
            try:
                # Generic SEO queries → restrict to curated domains
                # Tenant-specific queries → search broadly for better coverage
                domains = use_domains_for_generic if _is_generic(query) else None

                logger.info(f"[exa_news] Searching: {query} (domains={'curated' if domains else 'all'})")
                response = await client.search_and_contents(
                    query=query,
                    num_results=num_results,
                    include_domains=domains,
                    start_published_date=start_str,
                    end_published_date=end_str,
                    category=category,
                    summary=True,
                )

                for result in response.get("results", []):
                    url = result.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    text = result.get("text", "")
                    if len(text) < 50:
                        continue

                    published = result.get("publishedDate", "")
                    posted_at = parse_to_yyyy_mm_dd(published) if published else None

                    # Resolve source from URL
                    source = _resolve_news_source(url)

                    items.append({
                        "source": source,
                        "source_url": url,
                        "title": result.get("title", ""),
                        "content": text,
                        "posted_at": posted_at,
                        "crawler_tool": "exa",
                        "raw_data": {
                            "exa_score": result.get("score"),
                            "exa_query": query,
                            "exa_summary": result.get("summary") or None,
                            "author": result.get("author"),
                            "published_date": published,
                        },
                    })

            except Exception as e:
                logger.warning(f"[exa_news] Query failed: {query} — {e}")
                continue

        logger.info(f"[exa_news] Found {len(items)} unique articles from {len(queries)} queries")
        return items


def _resolve_news_source(url: str) -> str:
    """Extract a clean source name from URL domain."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lstrip("www.")
        # Map common domains to clean names
        SOURCE_NAMES = {
            "searchengineland.com": "Search Engine Land",
            "searchenginejournal.com": "Search Engine Journal",
            "seroundtable.com": "Search Engine Roundtable",
            "developers.google.com": "Google Search Central",
            "blog.google": "Google Blog",
            "semrush.com": "Semrush",
            "ahrefs.com": "Ahrefs",
            "moz.com": "Moz",
            "firstpagesage.com": "First Page Sage",
            "evergreen.media": "Evergreen Media",
            "seo-suedwest.de": "SEO Sudwest",
            "sistrix.com": "SISTRIX",
            "sistrix.de": "SISTRIX",
            "backlinko.com": "Backlinko",
            "t3n.de": "t3n",
            "marketingdive.com": "Marketing Dive",
            "fatjoe.com": "FatJoe",
            "usercentrics.com": "Usercentrics",
            "didomi.io": "Didomi",
            "seoclarity.net": "SEO Clarity",
            "techpolicy.press": "TechPolicy.Press",
            "conductor.com": "Conductor",
            "research.google": "Google Research",
            "ai.google": "Google AI",
        }
        return SOURCE_NAMES.get(domain, domain)
    except Exception:
        return "unknown"
