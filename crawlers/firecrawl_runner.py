"""Firecrawl crawlers for gutefrage.net and health forums.

This module consolidates all Firecrawl-based crawlers:
- GutefrageCrawler: German Q&A platform (Priority 1A)
- HealthForumsCrawler: German health forums (Priority 2)
"""
import asyncio
import logging
import os
import re
from typing import Any, Dict, List

import httpx

from crawlers.base_crawler import BaseCrawler
from crawlers.content_utils import extract_page_content, extract_structured_content, extract_date_from_text
from utils.dates import parse_to_yyyy_mm_dd

logger = logging.getLogger(__name__)


# =============================================================================
# FIRECRAWL API CLIENT
# =============================================================================

class FirecrawlClient:
    """Shared Firecrawl API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def scrape_url(self, url: str, timeout: int = 60, include_html: bool = False) -> Dict[str, Any]:
        """Scrape a single URL via Firecrawl.

        Args:
            url: URL to scrape
            timeout: Request timeout in seconds
            include_html: If True, also request HTML format for date extraction
        """
        formats = ["markdown"]
        if include_html:
            formats.append("html")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"url": url, "formats": formats, "waitFor": 3000}
            )
            response.raise_for_status()
            return response.json()


# =============================================================================
# GUTEFRAGE CRAWLER (Priority 1A)
# =============================================================================

# gutefrage.net URLs to crawl — brand-focused (existing)
GUTEFRAGE_URLS = [
    # Blood pressure
    "https://www.gutefrage.net/tag/blutdruck/1",
    "https://www.gutefrage.net/tag/blutdruck/2",
    "https://www.gutefrage.net/tag/blutdruck/3",
    "https://www.gutefrage.net/tag/blutdruckmessgeraet/1",
    "https://www.gutefrage.net/tag/bluthochdruck/1",
    "https://www.gutefrage.net/tag/bluthochdruck/2",
    # TENS/EMS
    "https://www.gutefrage.net/tag/tens/1",
    "https://www.gutefrage.net/tag/ems/1",
    # Menstrual pain
    "https://www.gutefrage.net/tag/regelschmerzen/1",
    "https://www.gutefrage.net/tag/regelschmerzen/2",
    "https://www.gutefrage.net/tag/periodenschmerzen/1",
    # Back/neck pain
    "https://www.gutefrage.net/tag/rueckenschmerzen/1",
    "https://www.gutefrage.net/tag/rueckenschmerzen/2",
    "https://www.gutefrage.net/tag/nackenschmerzen/1",
]

# Journey-focused gutefrage URLs — broader pain awareness (stages 1-3)
GUTEFRAGE_JOURNEY_URLS = [
    "https://www.gutefrage.net/tag/schmerzen/1",
    "https://www.gutefrage.net/tag/schmerztherapie/1",
    "https://www.gutefrage.net/tag/gelenkschmerzen/1",
    "https://www.gutefrage.net/tag/kopfschmerzen/1",
]


class GutefrageCrawler(BaseCrawler):
    """Crawler for gutefrage.net using Firecrawl."""

    name = "gutefrage"
    tool = "firecrawl"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY must be set")
        self.firecrawl = FirecrawlClient(self.api_key)

    def _extract_dates_from_html(self, html: str) -> Dict[str, str]:
        """Extract question URL → datetime mapping from HTML.

        Gutefrage HTML structure: datetime appears BEFORE the question link in the card.
        Structure is:
          <time datetime="2026-01-30T13:47:41.000Z">...</time>
          ...
          <a href="https://www.gutefrage.net/frage/..." class="ListingElement-questionLink">

        Returns:
            Dict mapping question URLs to their datetime strings
        """
        url_to_date = {}

        if not html:
            return url_to_date

        # Strategy 1: datetime BEFORE link (most common in gutefrage)
        # Look for datetime followed by a question link within ~2000 chars
        dt_then_link_pattern = r'datetime="(\d{4}-\d{2}-\d{2}T[^"]+)"(?:(?!datetime=").){0,2000}?href="(https://www\.gutefrage\.net/frage/[^"]+)"'
        matches = re.findall(dt_then_link_pattern, html, re.DOTALL)

        for dt, url in matches:
            if url not in url_to_date:
                url_to_date[url] = dt

        # Strategy 2: If strategy 1 didn't find much, try link BEFORE datetime
        if len(url_to_date) < 10:
            link_then_dt_pattern = r'href="(https://www\.gutefrage\.net/frage/[^"]+)"(?:(?!href="https://www\.gutefrage\.net/frage/).){0,2000}?datetime="(\d{4}-\d{2}-\d{2}T[^"]+)"'
            matches2 = re.findall(link_then_dt_pattern, html, re.DOTALL)

            for url, dt in matches2:
                if url not in url_to_date:
                    url_to_date[url] = dt

        logger.debug(f"[gutefrage] Extracted {len(url_to_date)} dates from HTML")
        return url_to_date

    def _parse_questions(self, markdown: str, html: str, page_url: str) -> List[Dict[str, Any]]:
        """Parse questions from gutefrage markdown with dates from HTML.

        Args:
            markdown: Firecrawl markdown output for content extraction
            html: Firecrawl HTML output for date extraction
            page_url: The listing page URL being parsed
        """
        items = []

        # Build URL → datetime mapping from HTML
        url_to_date = self._extract_dates_from_html(html)

        # gutefrage format: [**Title**\\content\\tags](url)
        # Match questions with their URLs - the URL contains /frage/
        pattern = r'\[\*\*(.+?)\*\*\\\\(.*?)\]\((https://www\.gutefrage\.net/frage/[^\)]+)\)'

        matches = re.findall(pattern, markdown, re.DOTALL)

        for match in matches:
            title = match[0].strip()
            content_raw = match[1]
            url = match[2]

            # Clean up content: remove \\ and extra whitespace
            content = content_raw.replace('\\\\', '\n').replace('\\', '')
            content = re.sub(r'\n{3,}', '\n\n', content)  # Reduce multiple newlines
            content = content.strip()

            # Skip if content is too short
            if len(content) < 30:
                continue

            # Skip duplicates within same page
            if any(item["source_url"] == url for item in items):
                continue

            # Get actual post date from HTML, or None (will default to crawl date)
            posted_at_raw = url_to_date.get(url)

            items.append({
                "source": "gutefrage",
                "source_url": url,
                "title": title[:500],  # Truncate long titles
                "content": content[:2000],  # Truncate content
                "posted_at": parse_to_yyyy_mm_dd(posted_at_raw),
                "crawler_tool": "firecrawl",
                "raw_data": {"page_url": page_url, "original_datetime": posted_at_raw}
            })

        return items

    async def _deep_crawl_question(self, url: str) -> Dict[str, Any]:
        """Deep-crawl a single /frage/ URL to get full question text and answers.

        Args:
            url: The gutefrage.net /frage/ URL

        Returns:
            Dict with question_text and answers list
        """
        try:
            result = await self.firecrawl.scrape_url(url)
            if result.get("success") and result.get("data", {}).get("markdown"):
                return self._parse_question_page(result["data"]["markdown"])
        except Exception as e:
            logger.warning(f"[gutefrage] Deep crawl failed for {url}: {e}")

        return {"question_text": None, "answers": []}

    def _parse_question_page(self, markdown: str) -> Dict[str, Any]:
        """Parse a gutefrage question page to extract OP question and answers.

        Firecrawl markdown structure for gutefrage:
          # Title
          <question body>
          ...kompletten Beitrag anzeigen
          Antworten
          ## N Antworten
          Sortiert nach: ...
          ![](avatar)                          ← answer boundary
          [Username](gutefrage.net/nutzer/...)
          vor X Jahren
          <answer content>
          Hilfreich
          <N>
          <N>
          Nicht hilfreich

        Args:
            markdown: Firecrawl markdown of the question page

        Returns:
            Dict with question_text and answers list
        """
        answers = []
        question_text = ""

        try:
            # User profile link marks each answer boundary
            user_link_re = re.compile(
                r'\[([^\]]+)\]\(https?://(?:www\.)?gutefrage\.net/nutzer/[^)]+\)'
            )
            # "## N Antwort(en)" header marks end of question section
            antworten_header_re = re.compile(
                r'^##\s+\d+\s+Antwort', re.MULTILINE
            )
            # Timestamp line right after username
            timestamp_re = re.compile(r'^vor\s+.+$', re.MULTILINE)
            # Accepted / best answer markers
            accepted_re = re.compile(
                r'(?:Beste\s+Antwort|hilfreichste\s+Antwort|ausgezeichnete\s+Antwort)',
                re.IGNORECASE
            )

            # --- Extract question text ---
            header_match = antworten_header_re.search(markdown)
            if header_match:
                question_text = markdown[:header_match.start()]
            else:
                # Fallback: everything before first user profile link
                first_user = user_link_re.search(markdown)
                question_text = markdown[:first_user.start()] if first_user else markdown

            # Clean question: remove boilerplate, images, heading markers
            q_lines = []
            for line in question_text.split('\n'):
                stripped = line.strip()
                if stripped.startswith('!['):
                    continue
                if stripped.lower() in ('antworten', ''):
                    continue
                if any(skip in stripped.lower() for skip in [
                    'navigation', 'menü', 'cookie', 'datenschutz',
                    'impressum', 'anmelden', 'registrieren',
                    'zum inhalt', 'breadcrumb', 'frage stellen',
                    '...kompletten beitrag',
                ]):
                    continue
                q_lines.append(line)
            question_text = '\n'.join(q_lines).strip()
            question_text = re.sub(r'#{1,6}\s*', '', question_text)
            question_text = re.sub(r'\n{3,}', '\n\n', question_text).strip()

            # --- Split into answer blocks by user profile links ---
            matches = list(user_link_re.finditer(markdown))
            if not matches:
                return {
                    "question_text": question_text[:5000] if question_text else None,
                    "answers": [],
                }

            for i, match in enumerate(matches):
                author = match.group(1)
                block_start = match.end()

                # Block ends at the next avatar image block before next user link,
                # or at end of markdown
                if i + 1 < len(matches):
                    block_end = matches[i + 1].start()
                    # Trim back to before avatar images preceding next answer
                    preceding = markdown[block_start:block_end]
                    # Find last "Nicht hilfreich" which closes current answer
                    nh_pos = preceding.rfind('Nicht hilfreich')
                    if nh_pos != -1:
                        block_end = block_start + nh_pos + len('Nicht hilfreich')
                else:
                    block_end = len(markdown)

                block = markdown[block_start:block_end]

                # Extract timestamp
                ts_match = timestamp_re.search(block[:200])
                content_start = ts_match.end() if ts_match else 0

                # Content ends at "Hilfreich" footer
                hilfreich_pos = block.find('\nHilfreich\n')
                if hilfreich_pos == -1:
                    hilfreich_pos = block.find('\nHilfreich')
                content_end = hilfreich_pos if hilfreich_pos != -1 else len(block)

                content = block[content_start:content_end]

                # Clean content: remove images, trailing boilerplate
                content_lines = []
                for line in content.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('!['):
                        continue
                    if stripped.lower().startswith('woher ich das weiß'):
                        continue
                    if stripped in ('Antwort schreiben…', 'Absenden',
                                    'Weitere Antworten zeigen'):
                        continue
                    content_lines.append(line)
                content = '\n'.join(content_lines).strip()
                content = re.sub(r'\n{3,}', '\n\n', content)

                # Extract votes from "Hilfreich\n\nN" pattern
                votes = 0
                vote_match = re.search(r'Hilfreich\s+(\d+)', block)
                if vote_match:
                    try:
                        votes = int(vote_match.group(1))
                    except (ValueError, TypeError):
                        pass

                # Check for accepted answer marker
                is_accepted = bool(accepted_re.search(block[:300]))

                if len(content) >= 20:
                    answers.append({
                        "content": content[:5000],
                        "author": author,
                        "votes": votes,
                        "is_accepted": is_accepted,
                        "position": i,
                    })

        except Exception as e:
            logger.warning(f"[gutefrage] Question page parsing error: {e}")
            if not question_text:
                question_text = markdown[:5000]

        return {
            "question_text": question_text[:5000] if question_text else None,
            "answers": answers,
        }

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch items from gutefrage.net."""
        max_pages = config.get("max_pages", len(GUTEFRAGE_URLS) + len(GUTEFRAGE_JOURNEY_URLS))
        max_deep_crawl = config.get("max_deep_crawl", 50)

        # Build tagged URL list: (url, collection_type)
        tagged_urls = [(u, "brand") for u in GUTEFRAGE_URLS] + \
                      [(u, "journey") for u in GUTEFRAGE_JOURNEY_URLS]
        tagged_urls = tagged_urls[:max_pages]

        all_items = []
        for url, collection_type in tagged_urls:
            try:
                logger.info(f"[gutefrage] Scraping [{collection_type}] {url}")
                # Request HTML in addition to markdown for date extraction
                result = await self.firecrawl.scrape_url(url, include_html=True)

                if result.get("success") and result.get("data", {}).get("markdown"):
                    markdown = result["data"]["markdown"]
                    html_content = result["data"].get("html", "")
                    items = self._parse_questions(markdown, html_content, url)
                    # Tag each item with collection_type
                    for item in items:
                        item["collection_type"] = collection_type
                    all_items.extend(items)

                    # Log how many items got actual dates vs fallback
                    items_with_dates = sum(1 for item in items if item.get("raw_data", {}).get("original_datetime"))
                    logger.info(f"[gutefrage] Found {len(items)} items from {url} ({items_with_dates} with actual dates)")

                # Rate limit: 2 second delay between requests
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[gutefrage] Error scraping {url}: {e}")
                continue

        # Deep-crawl pass: visit each /frage/ URL to get full question text + answers
        deep_crawl_count = min(len(all_items), max_deep_crawl)
        if deep_crawl_count > 0:
            logger.info(f"[gutefrage] Deep-crawling {deep_crawl_count} question pages...")

        for i, item in enumerate(all_items[:deep_crawl_count]):
            try:
                question_url = item["source_url"]
                logger.info(f"[gutefrage] Deep crawl ({i+1}/{deep_crawl_count}): {question_url}")

                result = await self._deep_crawl_question(question_url)

                if result.get("question_text"):
                    # Store original listing snippet
                    item["raw_data"]["original_snippet"] = item["content"]
                    # Replace with full question text
                    item["content"] = result["question_text"][:5000]
                    item["_question_content"] = result["question_text"][:10000]

                if result.get("answers"):
                    item["_answers"] = result["answers"]

                # Rate limit: 2 second delay between Firecrawl requests
                await asyncio.sleep(2)

            except Exception as e:
                logger.warning(f"[gutefrage] Deep crawl error for {item.get('source_url')}: {e}")
                continue

        return all_items


# =============================================================================
# HEALTH FORUMS CRAWLER (Priority 2)
# =============================================================================

# Configuration for German health forums
# deep_crawl: If True, crawl each linked page to extract actual content
HEALTH_FORUM_CONFIGS = {
    "diabetes_forum": {
        "urls": [
            "https://www.diabetes-forum.de/forum/",
            "https://www.diabetes-forum.de/forum/blutdruck/",
        ],
        "source": "diabetes-forum.de",
        "deep_crawl": True,  # Forum index pages don't contain full post content
        "thread_style": True,  # Thread-based forum: OP + replies
    },
    "endometriose": {
        "urls": [
            # Main info pages about endometriosis
            "https://www.endometriose-vereinigung.de/was-ist-endometriose/",
            "https://www.endometriose-vereinigung.de/behandlung/",
            "https://www.endometriose-vereinigung.de/diagnose/",
            # User experiences and stories
            "https://www.endometriose-vereinigung.de/erfahrungen/",
            "https://www.endometriose-vereinigung.de/endo-geschichten/",
            # Blog and current topics
            "https://www.endometriose-vereinigung.de/blog/",
            # Related conditions and symptoms
            "https://www.endometriose-vereinigung.de/begleiterkrankungen/",
            "https://www.endometriose-vereinigung.de/endometriose-und-psyche/",
        ],
        "source": "endometriose-vereinigung.de",
        "deep_crawl": True,  # Info site, needs full page content
        "thread_style": False,  # Info pages, not thread-based
        "category": "menstrual",  # Pre-classify as menstrual pain content
    },
    "rheuma_liga": {
        "urls": [
            # Pain-related content pages (highest priority for TENS relevance)
            "https://www.rheuma-liga.de/rheuma/alltag-mit-rheuma/schmerz",
            "https://www.rheuma-liga.de/rheuma/therapie/nichtmedikamentoese-therapie",
            "https://www.rheuma-liga.de/rheuma/alltag-mit-rheuma/naturheilkunde",
            # Chronic pain conditions (fibromyalgie, back pain, arthritis)
            "https://www.rheuma-liga.de/rheuma/krankheitsbilder/fibromyalgie",
            "https://www.rheuma-liga.de/rheuma/krankheitsbilder/rueckenschmerzen",
            "https://www.rheuma-liga.de/rheuma/krankheitsbilder/arthrose",
            "https://www.rheuma-liga.de/rheuma/krankheitsbilder/rheumatoide-arthritis",
            # Therapy overview pages
            "https://www.rheuma-liga.de/rheuma/therapie",
            "https://www.rheuma-liga.de/rheuma/therapie/medikamententherapie/schmerzmedikamente",
            # Daily life with pain
            "https://www.rheuma-liga.de/rheuma/alltag-mit-rheuma",
            # Disease overview (for more chronic pain conditions)
            "https://www.rheuma-liga.de/rheuma/krankheitsbilder",
        ],
        "source": "rheuma-liga.de",
        "deep_crawl": True,  # Info site, needs full page content
        "thread_style": False,  # Info pages, not thread-based
        "category": "pain_tens",  # Pre-classify as pain/TENS content
    },
    "onmeda": {
        "urls": [
            # Blood pressure - primary category for BP monitors
            "https://fragen.onmeda.de/forum/bluthochdruck",
            # Chronic pain - primary category for TENS devices
            "https://fragen.onmeda.de/forum/chronische-schmerzen",
            # Back pain / orthopedics - TENS device relevant
            "https://fragen.onmeda.de/forum/orthopädie_rückenschmerzen",
            # Migraine / headaches - pain therapy relevant
            "https://fragen.onmeda.de/forum/migräne-kopfschmerzen",
        ],
        "source": "fragen.onmeda.de",
        "deep_crawl": True,  # Forum index pages contain thread listings to deep crawl
        "thread_style": True,  # Thread-based forum: OP + replies
    },
}


class HealthForumsCrawler(BaseCrawler):
    """Crawler for German health forums using Firecrawl."""

    name = "health_forums"
    tool = "firecrawl"

    def __init__(self, forum_key: str = None):
        super().__init__()
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY must be set")
        self.firecrawl = FirecrawlClient(self.api_key)
        self.forum_key = forum_key  # Optional: limit to specific forum

    def _extract_article_links(self, markdown: str, page_url: str, source: str) -> List[Dict[str, str]]:
        """Extract article links from an index page for deep crawling."""
        links = []
        seen_urls = set()

        # Pattern for markdown links: [Title](url) - exclude image links starting with !
        link_pattern = r'(?<!\!)\[([^\]]+)\]\((https?://[^\)]+)\)'
        matches = re.findall(link_pattern, markdown)

        # Get base domain for filtering
        source_base = source.replace('.de', '').replace('-', '').replace('.', '')

        for title, url in matches:
            # Clean URL (remove trailing quotes/text)
            url = url.split('"')[0].split(' ')[0].rstrip('"\'')

            # Skip image/asset URLs
            if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif', '.svg', '.css', '.js', '.pdf', '.php', '/wp-content/uploads/', '/core/image']):
                continue

            # Skip navigation URLs by pattern
            skip_url_patterns = [
                '#',  # Anchor links
                '/register', '/login', '/anmelden', '/abmelden',
                '/member/', '/user/', '/profile/',
                '/page', '/seite',  # Pagination
                '/search', '/suche',
                '/impressum', '/datenschutz', '/kontakt',
                '/cookie', '/privacy',
            ]
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in skip_url_patterns):
                continue

            # Skip navigation/utility links by title
            skip_titles = [
                'startseite', 'home', 'navigation', 'menü', 'menu',
                'login', 'register', 'anmelden', 'abmelden',
                'impressum', 'datenschutz', 'kontakt', 'cookie',
                'facebook', 'twitter', 'instagram', 'youtube',
                'vorlesen', 'suche', 'search', 'close menu', 'scroll up',
                'scroll down', 'zum eintrag wechseln', 'weiterlesen',
                'mehr lesen', 'read more', 'zurück', 'back', 'weiter', 'next',
                'newsletter', 'spenden', 'mitglied werden', 'kontakt',
                'hier registrieren', 'template', 'vorherige', 'nächste',
                'kanäle als gelesen markieren', 'themen', 'neuste beiträge',
                'meine abonnements', 'bilder', 'beiträge',
            ]
            # Strip markdown formatting from title before checking
            title_clean = re.sub(r'\*+', '', title).lower().strip()
            if title_clean in skip_titles or len(title_clean) < 5:
                continue

            # Skip URLs we've already seen
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Only include links from the same domain
            if source_base not in url.lower().replace('-', '').replace('.', ''):
                continue

            # Skip if URL is the same as index page
            if url.rstrip('/') == page_url.rstrip('/'):
                continue

            # Skip URLs that are just the forum root
            if url.rstrip('/').endswith('/forum'):
                continue

            links.append({"title": title, "url": url})

        return links

    def _extract_page_content(self, markdown: str) -> str:
        """Extract main content from a page's markdown, removing navigation/boilerplate."""
        return extract_page_content(markdown)

    def _parse_forum_posts(self, markdown: str, page_url: str, source: str) -> List[Dict[str, Any]]:
        """Parse forum posts from markdown - for forum-style sites."""
        items = []
        seen_urls = set()

        # Pattern for markdown links: [Title](url) - exclude image links starting with !
        link_pattern = re.compile(r'(?<!\!)\[([^\]]+)\]\((https?://[^\)]+)\)')

        # Get base domain for filtering
        source_base = source.replace('.de', '').replace('-', '').replace('.', '')

        for match in link_pattern.finditer(markdown):
            title = match.group(1)
            url = match.group(2)

            # Skip image/asset URLs
            if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif', '.svg', '.css', '.js', '.pdf', '.php', '/wp-content/uploads/', '/core/image']):
                continue

            # Skip navigation/utility links by title
            skip_titles = [
                'startseite', 'home', 'navigation', 'menü', 'menu',
                'login', 'register', 'anmelden', 'abmelden',
                'impressum', 'datenschutz', 'kontakt', 'cookie',
                'facebook', 'twitter', 'instagram', 'youtube',
                'vorlesen', 'suche', 'search', 'close menu', 'scroll up',
                'scroll down', 'zum eintrag wechseln', 'weiterlesen',
                'mehr lesen', 'read more', 'zurück', 'back', 'weiter', 'next'
            ]
            title_lower = title.lower().strip()
            if title_lower in skip_titles or len(title) < 5:
                continue

            # Skip URLs we've already seen
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Only include links from the same domain
            if source_base not in url.lower().replace('-', '').replace('.', ''):
                continue

            # Skip items where content would just be the title (too short to be useful)
            if len(title) < 50:
                continue

            # Try to extract a date from surrounding context (~500 chars before the link)
            context_start = max(0, match.start() - 500)
            context = markdown[context_start:match.end()]
            extracted_date = extract_date_from_text(context)

            items.append({
                "source": source,
                "source_url": url,
                "title": title[:500],
                "content": title[:2000],  # Use title as content initially (fallback for shallow crawl)
                "posted_at": extracted_date or parse_to_yyyy_mm_dd(None),
                "crawler_tool": "firecrawl",
                "raw_data": {"page_url": page_url}
            })

        # Also try to extract content blocks - common forum patterns
        # Look for headings followed by content
        heading_pattern = r'#{1,3}\s+(.+?)(?:\n|\r\n?)(.*?)(?=#{1,3}\s+|\Z)'
        heading_matches = re.findall(heading_pattern, markdown, re.DOTALL)

        for heading, content in heading_matches:
            heading = heading.strip()
            content = content.strip()

            # Skip short headings or navigation-like content
            if len(heading) < 15 or len(content) < 50:
                continue

            # Skip if heading looks like navigation
            if any(skip in heading.lower() for skip in ['menü', 'navigation', 'footer', 'header']):
                continue

            # Try to find a URL in the content for this heading
            content_urls = re.findall(r'(https?://[^\s\)]+)', content)
            item_url = content_urls[0] if content_urls else page_url

            if item_url in seen_urls:
                continue
            seen_urls.add(item_url)

            # Try to extract date from heading + content
            extracted_date = extract_date_from_text(heading + " " + content[:500])

            items.append({
                "source": source,
                "source_url": item_url,
                "title": heading[:500],
                "content": content[:2000],
                "posted_at": extracted_date or parse_to_yyyy_mm_dd(None),
                "crawler_tool": "firecrawl",
                "raw_data": {"page_url": page_url}
            })

        return items

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch items from health forums."""
        max_pages = config.get("max_pages", 5)
        max_articles = config.get("max_articles", 20)  # Limit articles for deep crawl
        forum_key = config.get("forum") or self.forum_key

        # Determine which forums to crawl
        if forum_key and forum_key in HEALTH_FORUM_CONFIGS:
            forums_to_crawl = {forum_key: HEALTH_FORUM_CONFIGS[forum_key]}
            # Update crawler name to specific forum
            self.name = forum_key
        else:
            forums_to_crawl = HEALTH_FORUM_CONFIGS

        all_items = []
        for forum_name, forum_config in forums_to_crawl.items():
            urls = forum_config["urls"][:max_pages]
            source = forum_config["source"]
            deep_crawl = forum_config.get("deep_crawl", False)
            preset_category = forum_config.get("category")  # Pre-set category if defined

            thread_style = forum_config.get("thread_style", False)

            for url in urls:
                try:
                    logger.info(f"[health_forums] Scraping index: {url}")
                    result = await self.firecrawl.scrape_url(url)

                    if not result.get("success") or not result.get("data", {}).get("markdown"):
                        continue

                    markdown = result["data"]["markdown"]

                    if deep_crawl:
                        # Deep crawl: extract links, then crawl each article
                        links = self._extract_article_links(markdown, url, source)
                        logger.info(f"[health_forums] Found {len(links)} article links from {url}")

                        # Limit number of articles to crawl
                        for link in links[:max_articles]:
                            try:
                                logger.info(f"[health_forums] Deep crawling: {link['url']}")
                                article_result = await self.firecrawl.scrape_url(link["url"])

                                if article_result.get("success") and article_result.get("data", {}).get("markdown"):
                                    article_markdown = article_result["data"]["markdown"]

                                    if thread_style:
                                        # Thread-based forum: separate OP from replies
                                        structured = extract_structured_content(article_markdown)
                                        content = structured["op_content"]
                                        extracted_date = structured.get("posted_at")

                                        if len(content) >= 100:
                                            item = {
                                                "source": source,
                                                "source_url": link["url"],
                                                "title": link["title"][:500],
                                                "content": content[:2000],
                                                "posted_at": extracted_date or parse_to_yyyy_mm_dd(None),
                                                "crawler_tool": "firecrawl",
                                                "raw_data": {"index_url": url},
                                                "_question_content": content[:10000],
                                            }
                                            if structured["replies"]:
                                                item["_answers"] = structured["replies"]
                                            if preset_category:
                                                item["category"] = preset_category
                                            all_items.append(item)
                                        else:
                                            logger.warning(f"[health_forums] Skipped {link['url']} - OP content too short ({len(content)} chars)")
                                    else:
                                        # Info-page style: use plain content extraction
                                        content = self._extract_page_content(article_markdown)
                                        extracted_date = extract_date_from_text(article_markdown)

                                        # Only save if we got meaningful content
                                        if len(content) >= 100:
                                            item = {
                                                "source": source,
                                                "source_url": link["url"],
                                                "title": link["title"][:500],
                                                "content": content[:2000],
                                                "posted_at": extracted_date or parse_to_yyyy_mm_dd(None),
                                                "crawler_tool": "firecrawl",
                                                "raw_data": {"index_url": url}
                                            }
                                            if preset_category:
                                                item["category"] = preset_category
                                            all_items.append(item)
                                        else:
                                            logger.warning(f"[health_forums] Skipped {link['url']} - content too short ({len(content)} chars)")

                                # Rate limit between article fetches
                                await asyncio.sleep(2)

                            except Exception as e:
                                logger.error(f"[health_forums] Error deep crawling {link['url']}: {e}")
                                continue
                    else:
                        # Shallow crawl: extract posts from index page
                        items = self._parse_forum_posts(markdown, url, source)
                        all_items.extend(items)
                        logger.info(f"[health_forums] Found {len(items)} items from {url}")

                    # Rate limit between index pages
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"[health_forums] Error scraping {url}: {e}")
                    continue

        return all_items
