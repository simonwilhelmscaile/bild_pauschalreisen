"""Answer backfill service — re-crawls source pages to populate social_item_answers.

Supports gutefrage.net, health forums (diabetes-forum.de, fragen.onmeda.de), and Reddit.
Each source uses its native extraction method from the existing crawler code.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional

from db.client import (
    get_beurer_supabase,
    save_answers,
    update_item_qa_metadata,
)

logger = logging.getLogger(__name__)

# Sources that support Q&A extraction
QA_CAPABLE_SOURCES = {
    "gutefrage",
    "reddit",
    "diabetes_forum",
    "endometriose",
    "rheuma_liga",
    "onmeda",
    # Serper items linking to these domains
    "serper_discovery",
    "serper_brand",
}

# Domain patterns for health forums (used to identify serper items)
HEALTH_FORUM_DOMAINS = [
    "diabetes-forum.de",
    "fragen.onmeda.de",
    "rheuma-liga-bw.de",
    "endometriose-vereinigung.de",
]


def _is_qa_capable(item: Dict) -> bool:
    """Check if an item's source supports Q&A extraction."""
    source = item.get("source", "")
    source_url = item.get("source_url", "")

    if source in ("gutefrage", "reddit"):
        return True

    # Health forum sources
    if source in ("diabetes_forum", "endometriose", "rheuma_liga", "onmeda"):
        return True

    # Serper items that point to Q&A-capable domains
    if source in ("serper_discovery", "serper_brand"):
        for domain in HEALTH_FORUM_DOMAINS + ["gutefrage.net"]:
            if domain in source_url:
                return True

    return False


def _get_source_type(item: Dict) -> Optional[str]:
    """Determine which extraction method to use for an item."""
    source = item.get("source", "")
    source_url = item.get("source_url", "")

    if source == "gutefrage" or "gutefrage.net" in source_url:
        return "gutefrage"
    if source == "reddit" or "reddit.com" in source_url:
        return "reddit"
    # Health forums
    for domain in HEALTH_FORUM_DOMAINS:
        if source in ("diabetes_forum", "endometriose", "rheuma_liga", "onmeda"):
            return "health_forum"
        if domain in source_url:
            return "health_forum"

    return None


async def _extract_gutefrage_answers(url: str) -> Dict:
    """Re-crawl a gutefrage.net URL to extract Q&A content."""
    from crawlers.firecrawl_runner import FirecrawlClient, GutefrageCrawler

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY required for gutefrage backfill")

    firecrawl = FirecrawlClient(api_key)

    try:
        result = await firecrawl.scrape_url(url)
        if result.get("success") and result.get("data", {}).get("markdown"):
            # Use GutefrageCrawler's parser (it's a static-ish method)
            crawler = object.__new__(GutefrageCrawler)
            parsed = crawler._parse_question_page(result["data"]["markdown"])
            return parsed
    except Exception as e:
        logger.warning(f"[answer_backfill] Gutefrage crawl failed for {url}: {e}")

    return {"question_text": None, "answers": []}


async def _extract_health_forum_answers(url: str) -> Dict:
    """Re-crawl a health forum URL to extract structured content."""
    from crawlers.firecrawl_runner import FirecrawlClient
    from crawlers.content_utils import extract_structured_content

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY required for health forum backfill")

    firecrawl = FirecrawlClient(api_key)

    try:
        result = await firecrawl.scrape_url(url)
        if result.get("success") and result.get("data", {}).get("markdown"):
            structured = extract_structured_content(result["data"]["markdown"])
            # Convert replies to answer format
            answers = []
            for reply in structured.get("replies", []):
                answers.append({
                    "content": reply.get("content", "")[:5000],
                    "author": reply.get("author"),
                    "votes": 0,
                    "is_accepted": False,
                    "position": reply.get("position", len(answers)),
                })
            return {
                "question_text": structured.get("op_content"),
                "answers": answers,
            }
    except Exception as e:
        logger.warning(f"[answer_backfill] Health forum crawl failed for {url}: {e}")

    return {"question_text": None, "answers": []}


async def _extract_reddit_answers(source_url: str) -> Dict:
    """Fetch Reddit comments for a post via JSON API."""
    import httpx
    from utils.dates import parse_to_yyyy_mm_dd

    # Derive permalink from source_url
    permalink = source_url.replace("https://www.reddit.com", "")
    if not permalink:
        return {"question_text": None, "answers": []}

    url = f"https://www.reddit.com{permalink}.json?limit=10&sort=top"
    comments = []
    question_text = None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (social-listening-bot)"},
            )

            if resp.status_code == 429:
                logger.warning("[answer_backfill] Reddit rate limited, waiting 5s...")
                await asyncio.sleep(5)
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (social-listening-bot)"},
                )

            if resp.status_code != 200:
                logger.debug(f"[answer_backfill] Reddit fetch failed: {resp.status_code}")
                return {"question_text": None, "answers": []}

            data = resp.json()

            if not isinstance(data, list) or len(data) < 2:
                return {"question_text": None, "answers": []}

            # Extract question text from post
            post_data = data[0].get("data", {}).get("children", [])
            if post_data:
                post = post_data[0].get("data", {})
                title = (post.get("title") or "").strip()
                selftext = (post.get("selftext") or "").strip()
                question_text = f"{title}\n\n{selftext}" if selftext else title

            # Extract comments
            comment_listing = data[1].get("data", {}).get("children", [])
            for child in comment_listing:
                if child.get("kind") != "t1":
                    continue
                comment_data = child.get("data", {})
                body = (comment_data.get("body") or "").strip()
                if not body or body in ("[deleted]", "[removed]"):
                    continue

                comments.append({
                    "content": body[:5000],
                    "author": comment_data.get("author"),
                    "votes": comment_data.get("score", 0),
                    "is_accepted": False,
                    "position": len(comments),
                    "posted_at": parse_to_yyyy_mm_dd(comment_data.get("created_utc")),
                    "source_id": comment_data.get("id"),
                })

    except Exception as e:
        logger.debug(f"[answer_backfill] Reddit comment fetch exception: {e}")

    return {"question_text": question_text, "answers": comments}


# Rate limits per source type (seconds between requests)
RATE_LIMITS = {
    "gutefrage": 2.0,
    "health_forum": 2.0,
    "reddit": 1.0,
}


async def backfill_answers(
    batch_size: int = 20,
    source: str = None,
    force: bool = False,
) -> Dict:
    """Backfill answers by re-crawling source pages.

    Args:
        batch_size: Number of items to process
        source: Filter by source name (e.g. 'gutefrage', 'reddit')
        force: If True, re-process items that already have answers

    Returns:
        Stats dict with processed/updated/failed/skipped counts
    """
    client = get_beurer_supabase()

    stats = {"processed": 0, "updated": 0, "failed": 0, "skipped": 0}

    # Fetch candidates
    if force and source:
        # Force mode: get items from source regardless of has_answers status
        query = client.table("social_items") \
            .select("id, source, source_url, title, content") \
            .eq("source", source) \
            .limit(batch_size)
        result = query.execute()
        candidates = result.data or []
    else:
        from db.client import get_items_without_answers
        candidates = get_items_without_answers(client, source=source, limit=batch_size)

    if not candidates:
        logger.info("[answer_backfill] No candidates found")
        return stats

    logger.info(f"[answer_backfill] Processing {len(candidates)} candidates")

    for item in candidates:
        item_id = item["id"]
        source_url = item.get("source_url", "")
        item_source = item.get("source", "")

        if not _is_qa_capable(item):
            stats["skipped"] += 1
            continue

        source_type = _get_source_type(item)
        if not source_type:
            stats["skipped"] += 1
            continue

        stats["processed"] += 1

        try:
            # If force mode, delete existing answers first
            if force:
                try:
                    client.table("social_item_answers") \
                        .delete() \
                        .eq("social_item_id", item_id) \
                        .execute()
                except Exception:
                    pass

            # Extract answers based on source type
            if source_type == "gutefrage":
                result = await _extract_gutefrage_answers(source_url)
            elif source_type == "health_forum":
                result = await _extract_health_forum_answers(source_url)
            elif source_type == "reddit":
                result = await _extract_reddit_answers(source_url)
            else:
                stats["skipped"] += 1
                continue

            answers = result.get("answers", [])
            question_text = result.get("question_text")

            if answers:
                saved_count = save_answers(client, item_id, answers)
                update_item_qa_metadata(
                    client, item_id,
                    question_content=question_text,
                    answer_count=saved_count,
                )
                stats["updated"] += 1
                logger.info(
                    f"[answer_backfill] {item_source} item {item_id}: "
                    f"saved {saved_count} answers"
                )
            else:
                # No answers found — still update metadata to mark as processed
                update_item_qa_metadata(
                    client, item_id,
                    question_content=question_text,
                    answer_count=0,
                )
                logger.debug(f"[answer_backfill] {item_source} item {item_id}: no answers found")

            # Rate limit between requests
            delay = RATE_LIMITS.get(source_type, 2.0)
            await asyncio.sleep(delay)

        except Exception as e:
            stats["failed"] += 1
            logger.error(f"[answer_backfill] Failed for {item_id} ({source_url}): {e}")

    logger.info(f"[answer_backfill] Complete: {stats}")
    return stats
