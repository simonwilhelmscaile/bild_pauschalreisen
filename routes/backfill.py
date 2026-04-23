"""Backfill endpoints — 12 endpoints with DRY helper."""
import logging
from typing import Any, Callable, Dict
from fastapi import APIRouter, HTTPException

from db.client import (
    get_beurer_supabase,
    get_items_needing_date_fix,
    update_item_posted_at,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_backfill(name: str, fn: Callable, **kwargs) -> Dict[str, Any]:
    """DRY helper for backfill endpoints."""
    try:
        stats = fn(**kwargs) if not callable(getattr(fn, '__wrapped__', None)) else fn(**kwargs)
        return {"status": "success", "stats": stats}
    except ValueError as e:
        raise HTTPException(500, f"{name} error: {str(e)}")
    except Exception as e:
        logger.error(f"{name} failed: {e}")
        raise HTTPException(500, f"{name} failed: {str(e)}")


async def _run_backfill_async(name: str, coro, **kwargs) -> Dict[str, Any]:
    """DRY helper for async backfill endpoints."""
    try:
        stats = await coro(**kwargs)
        return {"status": "success", "stats": stats}
    except ValueError as e:
        raise HTTPException(500, f"{name} error: {str(e)}")
    except Exception as e:
        logger.error(f"{name} failed: {e}")
        raise HTTPException(500, f"{name} failed: {str(e)}")


@router.post("/backfill/embeddings")
async def backfill_embeddings_endpoint(batch_size: int = 100):
    """Backfill embeddings for items missing them."""
    from services.embedding import backfill_embeddings
    return await _run_backfill("Embedding backfill", backfill_embeddings, batch_size=batch_size)


@router.post("/backfill/classifications")
async def backfill_classifications_endpoint(batch_size: int = 50, force: bool = False, after_id: str = None):
    """Backfill classifications for items missing them.

    Args:
        batch_size: Number of items to process per request (default 50)
        force: If True, re-classify ALL items (not just those with NULL category).
               Use with after_id for pagination.
        after_id: Process items with id > this value (use last_id from previous batch to paginate)
    """
    from classification import backfill_classifications
    return await _run_backfill("Classification backfill", backfill_classifications,
                               batch_size=batch_size, force=force, after_id=after_id)


@router.post("/backfill/journey-stages")
async def backfill_journey_stages_endpoint(batch_size: int = 50):
    """Backfill journey_stage, pain_category, solutions_mentioned for items missing them."""
    from classification import backfill_journey_stages
    return await _run_backfill("Journey stage backfill", backfill_journey_stages, batch_size=batch_size)


@router.post("/backfill/deep-insights")
async def backfill_deep_insights_endpoint(batch_size: int = 50, category: str = None, force: bool = False, after_id: str = None):
    """Backfill deep insights (pain location, coping strategies, life situations, etc.).

    Args:
        batch_size: Number of items to process per request (default 50)
        category: Optional category filter for priority processing (e.g. "blood_pressure")
        force: If True, re-classify ALL items (not just those missing deep insights).
        after_id: Process items with id > this value (use last_id from previous batch to paginate)
    """
    from classification import backfill_deep_insights
    return await _run_backfill("Deep insights backfill", backfill_deep_insights,
                               batch_size=batch_size, category_filter=category, force=force, after_id=after_id)


@router.post("/backfill/entity-sentiment")
async def backfill_entity_sentiment_endpoint(batch_size: int = 100, after_id: str = None):
    """Backfill per-entity sentiment for items with entity matches but NULL entity sentiment.

    For single-entity items, copies item-level sentiment (no LLM call).
    For multi-entity items, uses a lightweight LLM prompt to determine
    per-entity sentiment (different products can have different sentiments).
    """
    from classification import backfill_entity_sentiments
    return await _run_backfill("Entity sentiment backfill", backfill_entity_sentiments,
                               batch_size=batch_size, after_id=after_id)


@router.post("/backfill/normalize-medications")
async def normalize_medications_endpoint():
    """Normalize medication names across all items (casing, German conventions)."""
    from classification import normalize_medications
    return await _run_backfill("Medication normalization", normalize_medications)


@router.post("/backfill/dates")
async def backfill_dates_endpoint(batch_size: int = 100):
    """Backfill and normalize posted_at dates to YYYY-MM-DD format."""
    from utils.dates import parse_to_yyyy_mm_dd

    try:
        client = get_beurer_supabase()
        items = get_items_needing_date_fix(client, limit=batch_size)

        stats = {
            "processed": 0,
            "updated": 0,
            "failed": 0,
            "already_correct": 0,
            "samples": []
        }

        for item in items:
            stats["processed"] += 1
            old_value = item.get("posted_at")
            new_value = parse_to_yyyy_mm_dd(old_value)

            if len(stats["samples"]) < 5:
                stats["samples"].append({
                    "id": item["id"],
                    "source": item.get("source"),
                    "old": old_value,
                    "new": new_value
                })

            if update_item_posted_at(client, item["id"], new_value):
                stats["updated"] += 1
            else:
                stats["failed"] += 1

        remaining = get_items_needing_date_fix(client, limit=1)
        stats["remaining"] = len(remaining) > 0

        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"Date backfill failed: {e}")
        raise HTTPException(500, f"Date backfill failed: {str(e)}")


@router.post("/backfill/date-extraction")
async def backfill_date_extraction_endpoint(batch_size: int = 20):
    """Re-crawl health forum items to extract actual post dates from page content.

    Targets items from health forum sources whose posted_at likely defaulted to
    the crawl date. Re-scrapes source_url via Firecrawl, runs date extraction
    on the page markdown, and updates posted_at if a real date is found.
    """
    import asyncio
    import os
    from datetime import datetime, timedelta

    from crawlers.content_utils import extract_date_from_text, extract_structured_content
    from crawlers.firecrawl_runner import FirecrawlClient

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise HTTPException(500, "FIRECRAWL_API_KEY required for date re-extraction")

    firecrawl = FirecrawlClient(api_key)
    client = get_beurer_supabase()

    # Health forum source values (from HEALTH_FORUM_CONFIGS)
    forum_sources = [
        "diabetes-forum.de",
        "endometriose-vereinigung.de",
        "rheuma-liga.de",
        "fragen.onmeda.de",
    ]

    stats = {"processed": 0, "updated": 0, "skipped": 0, "failed": 0, "samples": []}

    try:
        # Fetch health forum items — those whose posted_at equals crawled_at date
        # (i.e., date was likely set to crawl date as a fallback)
        all_candidates = []
        for source in forum_sources:
            result = client.table("social_items") \
                .select("id, source, source_url, posted_at, crawled_at") \
                .eq("source", source) \
                .limit(batch_size) \
                .execute()
            all_candidates.extend(result.data or [])

        if not all_candidates:
            return {"status": "success", "stats": stats}

        # Filter to items where posted_at matches crawled_at date (crawl-date fallback)
        candidates = []
        for item in all_candidates:
            posted = (item.get("posted_at") or "")[:10]
            created = (item.get("crawled_at") or "")[:10]
            if posted and created and posted == created:
                candidates.append(item)

        candidates = candidates[:batch_size]
        logger.info(f"[date-extraction] {len(candidates)} candidates from {len(all_candidates)} forum items")

        for item in candidates:
            item_id = item["id"]
            source_url = item.get("source_url", "")
            stats["processed"] += 1

            try:
                result = await firecrawl.scrape_url(source_url)

                if result.get("success") and result.get("data", {}).get("markdown"):
                    markdown = result["data"]["markdown"]
                    extracted_date = extract_date_from_text(markdown)

                    if extracted_date and extracted_date != item.get("posted_at", "")[:10]:
                        if update_item_posted_at(client, item_id, extracted_date):
                            stats["updated"] += 1
                            if len(stats["samples"]) < 5:
                                stats["samples"].append({
                                    "id": item_id,
                                    "source": item.get("source"),
                                    "old": item.get("posted_at"),
                                    "new": extracted_date,
                                    "url": source_url,
                                })
                        else:
                            stats["failed"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    stats["failed"] += 1

            except Exception as e:
                logger.warning(f"[date-extraction] Failed for {source_url}: {e}")
                stats["failed"] += 1

            # Rate limit between Firecrawl requests
            await asyncio.sleep(2)

        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"Date extraction backfill failed: {e}")
        raise HTTPException(500, f"Date extraction backfill failed: {str(e)}")


@router.post("/backfill/entities")
async def backfill_entities_endpoint(batch_size: int = 100):
    """Backfill entity mentions (products, brands) for all social items.

    Deterministic matching (no LLM) — scans title + content for known
    product names, model numbers, and brand names from the entities table.
    """
    from services.entity_matching import backfill_entities
    return await _run_backfill("Entity backfill", backfill_entities, batch_size=batch_size)


@router.post("/backfill/sources")
async def backfill_sources_endpoint():
    """Backfill source names for old Serper-crawled items + resolved_source for ALL items."""
    from crawlers.serper_runner import _resolve_source
    from classification import backfill_resolved_sources

    try:
        client = get_beurer_supabase()

        # Part 1: Fix serper source names
        result = client.table("social_items").select("id, source, source_url").in_(
            "source", ["serper_brand", "serper_discovery"]
        ).execute()
        items = result.data or []

        stats = {"processed": 0, "updated": 0, "skipped": 0, "samples": []}

        for item in items:
            stats["processed"] += 1
            old_source = item["source"]
            resolved = _resolve_source(item.get("source_url", ""))

            if resolved == old_source:
                stats["skipped"] += 1
                continue

            client.table("social_items").update(
                {"source": resolved}
            ).eq("id", item["id"]).execute()
            stats["updated"] += 1

            if len(stats["samples"]) < 10:
                stats["samples"].append({
                    "id": item["id"],
                    "old": old_source,
                    "new": resolved,
                    "url": item.get("source_url", "")[:80],
                })

        # Part 2: Backfill resolved_source for all items
        resolved_stats = backfill_resolved_sources(batch_size=200)
        stats["resolved_source"] = resolved_stats

        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"Source backfill failed: {e}")
        raise HTTPException(500, f"Source backfill failed: {str(e)}")


@router.post("/backfill/language-detection")
async def backfill_language_detection_endpoint(batch_size: int = 200):
    """Backfill language detection for items missing it."""
    from classification import backfill_language_detection
    return await _run_backfill("Language detection backfill", backfill_language_detection, batch_size=batch_size)


@router.post("/backfill/engagement-scores")
async def backfill_engagement_scores_endpoint(batch_size: int = 200):
    """Backfill engagement scores for items from sources that have engagement metrics."""
    from classification import backfill_engagement_scores
    return await _run_backfill("Engagement score backfill", backfill_engagement_scores, batch_size=batch_size)


@router.post("/backfill/cleanup-product-mentions")
async def cleanup_product_mentions_endpoint(
    batch_size: int = 200,
    dry_run: bool = True,
):
    """Remove false product_mentions that don't appear in the item text.

    Safety: defaults to dry_run=True. Pass dry_run=false to actually update.
    """
    from db.client import cleanup_false_product_mentions
    return await _run_backfill("Product mentions cleanup", cleanup_false_product_mentions,
                               batch_size=batch_size, dry_run=dry_run)


@router.post("/backfill/purge-low-relevance")
async def purge_low_relevance_endpoint(
    threshold: float = 0.3,
    batch_size: int = 200,
    dry_run: bool = True,
):
    """Purge low-relevance items from the database after classification.

    Safety: defaults to dry_run=True. Pass dry_run=false to actually delete.
    """
    from db.client import purge_low_relevance_items
    return await _run_backfill("Low-relevance purge", purge_low_relevance_items,
                               threshold=threshold, batch_size=batch_size, dry_run=dry_run)


@router.post("/backfill/answers")
async def backfill_answers_endpoint(
    batch_size: int = 20,
    source: str = None,
    force: bool = False,
):
    """Backfill answers by re-crawling source pages to populate social_item_answers."""
    from services.answer_backfill import backfill_answers
    return await _run_backfill_async("Answer backfill", backfill_answers,
                                     batch_size=batch_size, source=source, force=force)
