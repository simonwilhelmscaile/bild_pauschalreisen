"""Shared content utilities for crawlers.

Provides reusable functions for extracting and enriching page content,
used by both HealthForumsCrawler and Serper crawlers for deep crawling.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from utils.dates import parse_to_yyyy_mm_dd

logger = logging.getLogger(__name__)

# German month names for date extraction
_GERMAN_MONTHS = {
    'januar': 1, 'jan': 1, 'jan.': 1,
    'februar': 2, 'feb': 2, 'feb.': 2,
    'märz': 3, 'mär': 3, 'mär.': 3, 'maerz': 3,
    'april': 4, 'apr': 4, 'apr.': 4,
    'mai': 5,
    'juni': 6, 'jun': 6, 'jun.': 6,
    'juli': 7, 'jul': 7, 'jul.': 7,
    'august': 8, 'aug': 8, 'aug.': 8,
    'september': 9, 'sep': 9, 'sep.': 9, 'sept': 9, 'sept.': 9,
    'oktober': 10, 'okt': 10, 'okt.': 10,
    'november': 11, 'nov': 11, 'nov.': 11,
    'dezember': 12, 'dez': 12, 'dez.': 12,
}

# Compiled regex for German relative dates (vor X Tagen/Stunden/etc.)
_RELATIVE_DATE_RE = re.compile(
    r'vor\s+\d+\s+(?:Stunde|Minute|Tag|Woche|Monat)(?:en|n)?',
    re.IGNORECASE,
)

# Compiled regex for German date formats: DD.MM.YYYY with optional time
_GERMAN_DATE_RE = re.compile(
    r'\d{1,2}\.\d{1,2}\.\d{2,4}(?:\s*[,]?\s*\d{1,2}:\d{2})?'
)

# ISO date format: YYYY-MM-DD with optional time
_ISO_DATE_RE = re.compile(
    r'\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?'
)

# German month name: "Januar 2024", "Feb. 2025", "12. März 2024"
_MONTH_YEAR_RE = re.compile(
    r'(?:(\d{1,2})\.\s*)?(' + '|'.join(re.escape(m) for m in _GERMAN_MONTHS) + r')\s+(\d{4})',
    re.IGNORECASE,
)


def extract_date_from_text(text: str) -> Optional[str]:
    """Extract the earliest/first date from text content.

    Scans for German date formats, ISO dates, relative dates ("vor 2 Tagen"),
    and German month names ("Januar 2024"). Returns YYYY-MM-DD or None.

    Args:
        text: Text content (markdown or plain) to scan for dates

    Returns:
        Date string in YYYY-MM-DD format, or None if no date found
    """
    if not text:
        return None

    candidates = []  # list of (position_in_text, date_string)

    # 1. German date: 01.03.2024 or 1.3.2024 (with optional time)
    for m in _GERMAN_DATE_RE.finditer(text):
        raw = m.group(0).split()[0]  # take just the date part
        parsed = parse_to_yyyy_mm_dd(raw)
        if parsed:
            candidates.append((m.start(), parsed))

    # 2. ISO date: 2024-03-01
    for m in _ISO_DATE_RE.finditer(text):
        raw = m.group(0).split()[0]
        parsed = parse_to_yyyy_mm_dd(raw)
        if parsed:
            candidates.append((m.start(), parsed))

    # 3. Relative date: "vor 2 Tagen"
    for m in _RELATIVE_DATE_RE.finditer(text):
        parsed = parse_to_yyyy_mm_dd(m.group(0))
        if parsed:
            candidates.append((m.start(), parsed))

    # 4. German month name: "Januar 2024", "12. März 2024"
    for m in _MONTH_YEAR_RE.finditer(text):
        day_str, month_str, year_str = m.group(1), m.group(2), m.group(3)
        month_num = _GERMAN_MONTHS.get(month_str.lower().rstrip('.'))
        if month_num:
            day = int(day_str) if day_str else 1
            try:
                from datetime import date
                d = date(int(year_str), month_num, min(day, 28))
                candidates.append((m.start(), d.strftime('%Y-%m-%d')))
            except (ValueError, TypeError):
                pass

    if not candidates:
        return None

    # Return the first date found in text (by position)
    candidates.sort(key=lambda c: c[0])

    # Validate: don't return parse_to_yyyy_mm_dd's fallback (today's date)
    # Since we pass actual matched strings, this should be fine,
    # but guard against it anyway
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    for _, date_str in candidates:
        # Accept relative dates that resolve to today (e.g. "vor 1 Stunde")
        # but the match itself guarantees it came from actual text
        return date_str

    return None


# File extensions that cannot be meaningfully scraped
SKIP_EXTENSIONS = (
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
    '.mp4', '.mp3', '.zip', '.rar', '.exe', '.dmg',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
)


def extract_page_content(markdown: str) -> str:
    """Extract main content from a page's markdown, removing navigation/boilerplate.

    Strips navigation elements, short link-only lines, and markdown formatting
    to produce clean text content suitable for storage and analysis.

    Args:
        markdown: Raw markdown output from Firecrawl

    Returns:
        Cleaned text content
    """
    lines = markdown.split('\n')
    content_lines = []
    in_content = False

    for line in lines:
        line_lower = line.lower().strip()
        if any(skip in line_lower for skip in [
            'navigation', 'menü', 'footer', 'cookie', 'datenschutz',
            'impressum', 'newsletter', 'social media', 'teilen',
            'facebook', 'twitter', 'instagram', 'youtube',
            'zum inhalt springen', 'skip to', 'breadcrumb'
        ]):
            continue

        # Skip lines that are just links
        if line.strip().startswith('[') and line.strip().endswith(')'):
            link_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
            if len(link_text.strip()) < 20:
                continue

        # Skip short lines that look like navigation
        if len(line.strip()) < 10 and not line.strip().startswith('#'):
            continue

        # Start capturing after first heading
        if line.strip().startswith('#'):
            in_content = True

        if in_content:
            content_lines.append(line)

    content = '\n'.join(content_lines)

    # Clean up: remove excessive whitespace, markdown artifacts
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # Convert links to text
    content = re.sub(r'#{1,6}\s*', '', content)  # Remove heading markers
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Remove bold
    content = re.sub(r'\*([^*]+)\*', r'\1', content)  # Remove italic

    return content.strip()


def extract_structured_content(markdown: str) -> Dict[str, Any]:
    """Extract structured content from a forum thread page, separating OP from replies.

    Uses heuristic separation: first content block = OP, subsequent blocks with
    user attribution = replies. Looks for patterns like user names, timestamps,
    'Antwort'/'Beitrag' markers, and horizontal rules.

    Args:
        markdown: Raw markdown output from Firecrawl

    Returns:
        Dict with op_content, replies list, and full_content fallback
    """
    full_content = extract_page_content(markdown)
    op_content = ""
    replies = []
    posted_at = extract_date_from_text(markdown)

    try:
        lines = markdown.split('\n')

        # Patterns for detecting reply/post boundaries
        # Forum user attribution patterns
        author_pattern = re.compile(
            r'(?:'
            r'\*\*([^*]{2,30})\*\*\s*(?:schrieb|wrote|am\s+\d|·|\|)|'  # **Username** schrieb/am/·
            r'(?:Beitrag|Antwort|Antworten|Re:|RE:)\s+(?:von|by)\s+(\w+)|'  # Beitrag von User
            r'(?:^|\n)\s*von\s+(\w+)\s*(?:am|,\s*\d)|'  # von User am
            r'Verfasst\s+von\s+(\w+)|'  # Verfasst von User
            r'Autor:\s*(\w+)'  # Autor: User
            r')',
            re.IGNORECASE | re.MULTILINE
        )

        # Horizontal rule pattern
        hr_pattern = re.compile(r'^[-*_]{3,}\s*$')

        # Timestamp patterns that often mark post boundaries
        timestamp_pattern = re.compile(
            r'\d{1,2}\.\d{1,2}\.\d{2,4}\s*[,]?\s*\d{1,2}:\d{2}|'  # 01.01.2024 12:30
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|'  # 2024-01-01 12:30
            r'vor\s+\d+\s+(?:Stunde|Minute|Tag|Woche|Monat)',  # vor 2 Tagen
            re.IGNORECASE
        )

        # Split into sections by horizontal rules first
        sections = []
        current_section_lines = []

        for line in lines:
            if hr_pattern.match(line.strip()):
                if current_section_lines:
                    sections.append('\n'.join(current_section_lines))
                    current_section_lines = []
            else:
                current_section_lines.append(line)

        if current_section_lines:
            sections.append('\n'.join(current_section_lines))

        if len(sections) <= 1:
            # No horizontal rules; try splitting by author patterns
            text_block = '\n'.join(lines)
            split_points = []
            for match in author_pattern.finditer(text_block):
                # Find the start of the line containing the match
                line_start = text_block.rfind('\n', 0, match.start())
                if line_start == -1:
                    line_start = 0
                else:
                    line_start += 1
                split_points.append(line_start)

            if split_points:
                # First section = OP (before first author match)
                sections = [text_block[:split_points[0]]]
                for i, sp in enumerate(split_points):
                    end = split_points[i + 1] if i + 1 < len(split_points) else len(text_block)
                    sections.append(text_block[sp:end])
            else:
                sections = [text_block]

        # Process sections
        # First section = OP content
        if sections:
            raw_op = sections[0].strip()
            # Clean navigation boilerplate from OP
            op_lines = []
            in_content = False
            for line in raw_op.split('\n'):
                line_lower = line.lower().strip()
                if any(skip in line_lower for skip in [
                    'navigation', 'menü', 'cookie', 'datenschutz',
                    'impressum', 'newsletter', 'breadcrumb', 'zum inhalt',
                    'anmelden', 'registrieren'
                ]):
                    continue
                if line.strip().startswith('#') or len(line.strip()) > 20:
                    in_content = True
                if in_content:
                    op_lines.append(line)

            op_content = '\n'.join(op_lines).strip()
            # Strip markdown formatting
            op_content = re.sub(r'#{1,6}\s*', '', op_content)
            op_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', op_content)
            op_content = re.sub(r'\*([^*]+)\*', r'\1', op_content)
            op_content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', op_content)
            op_content = re.sub(r'\n{3,}', '\n\n', op_content)
            op_content = op_content.strip()

        # Remaining sections = replies
        for idx, section in enumerate(sections[1:], 1):
            section_stripped = section.strip()
            if len(section_stripped) < 20:
                continue

            # Try to extract author from the section
            author_match = author_pattern.search(section_stripped[:300])
            author = None
            if author_match:
                author = next((g for g in author_match.groups() if g), None)

            # Clean reply content
            reply_content = section_stripped
            reply_content = re.sub(r'#{1,6}\s*', '', reply_content)
            reply_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', reply_content)
            reply_content = re.sub(r'\*([^*]+)\*', r'\1', reply_content)
            reply_content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', reply_content)
            reply_content = re.sub(r'\n{3,}', '\n\n', reply_content)
            reply_content = reply_content.strip()

            if len(reply_content) >= 20:
                replies.append({
                    "content": reply_content[:5000],
                    "author": author,
                    "position": idx - 1,
                })

    except Exception as e:
        logger.warning(f"[structured_content] Parsing error: {e}")

    # Fallback: if no OP content extracted, use full_content
    if not op_content or len(op_content) < 30:
        op_content = full_content

    return {
        "op_content": op_content[:5000],
        "replies": replies,
        "full_content": full_content[:5000],
        "posted_at": posted_at,
    }


def _should_skip_url(url: str) -> bool:
    """Check if a URL points to a non-scrapable resource."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    return any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS)


async def deep_crawl_items(
    items: List[Dict[str, Any]],
    firecrawl_client,
    max_items: int = 50,
    delay: float = 2.0,
) -> List[Dict[str, Any]]:
    """Enrich crawler items by scraping their source URLs for full page content.

    Takes a list of crawler items (e.g. from Serper with only Google snippets),
    scrapes each source_url via Firecrawl, and replaces the snippet content
    with the full extracted page content.

    Args:
        items: List of crawler item dicts with 'source_url' and 'content' keys
        firecrawl_client: FirecrawlClient instance for scraping
        max_items: Maximum number of items to deep crawl (cost control)
        delay: Seconds to wait between Firecrawl requests (rate limiting)

    Returns:
        The same list of items, with content enriched where possible.
        Items that fail to scrape retain their original content.
    """
    if not items:
        return items

    items_to_crawl = items[:max_items]
    items_skipped = items[max_items:]
    enriched_count = 0
    skipped_count = 0
    failed_count = 0

    for i, item in enumerate(items_to_crawl):
        url = item.get("source_url", "")

        # Skip non-scrapable URLs
        if _should_skip_url(url):
            skipped_count += 1
            logger.debug(f"[deep_crawl] Skipping non-scrapable URL: {url}")
            continue

        try:
            logger.info(f"[deep_crawl] ({i+1}/{len(items_to_crawl)}) Scraping: {url}")
            result = await firecrawl_client.scrape_url(url)

            if result.get("success") and result.get("data", {}).get("markdown"):
                page_markdown = result["data"]["markdown"]
                full_content = extract_page_content(page_markdown)

                # Only replace if we got meaningful content (longer than the snippet)
                if len(full_content) >= 100:
                    # Store original snippet in raw_data for reference
                    if "raw_data" not in item:
                        item["raw_data"] = {}
                    item["raw_data"]["original_snippet"] = item.get("content", "")
                    item["raw_data"]["deep_crawled"] = True

                    item["content"] = full_content[:5000]  # Allow more content than snippet
                    enriched_count += 1
                else:
                    logger.debug(f"[deep_crawl] Content too short ({len(full_content)} chars), keeping snippet: {url}")
                    failed_count += 1
            else:
                logger.debug(f"[deep_crawl] Scrape returned no content: {url}")
                failed_count += 1

        except Exception as e:
            logger.warning(f"[deep_crawl] Failed to scrape {url}: {e}")
            failed_count += 1

        # Rate limiting between requests
        if i < len(items_to_crawl) - 1:
            await asyncio.sleep(delay)

    logger.info(
        f"[deep_crawl] Complete: {enriched_count} enriched, "
        f"{failed_count} failed (kept snippet), "
        f"{skipped_count} skipped (non-scrapable), "
        f"{len(items_skipped)} not attempted (over max_items={max_items})"
    )

    return items_to_crawl + items_skipped
