"""Beurer-specific Supabase client."""
import os
import hashlib
import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

logger = logging.getLogger(__name__)


def get_beurer_supabase() -> Client:
    """Get Beurer Supabase client."""
    url = os.getenv("BEURER_SUPABASE_URL")
    key = os.getenv("BEURER_SUPABASE_KEY")
    if not url or not key:
        raise ValueError("BEURER_SUPABASE_URL and BEURER_SUPABASE_KEY must be set")
    return create_client(url, key)


def content_hash(content: str) -> str:
    """Generate MD5 hash for deduplication."""
    return hashlib.md5(content.encode()).hexdigest()


def item_exists(client: Client, source_url: str) -> bool:
    """Check if item already exists by URL."""
    result = client.table("social_items").select("id").eq("source_url", source_url).limit(1).execute()
    return len(result.data) > 0


def save_social_item(client: Client, item: Dict[str, Any], run_id: str = None) -> Optional[Dict]:
    """Save item if not duplicate. Returns saved item or None.

    Args:
        client: Supabase client
        item: Item data to save
        run_id: Optional crawler run ID to link this item to
    """
    if item_exists(client, item["source_url"]):
        return None
    item["content_hash"] = content_hash(item["content"])
    if run_id:
        item["crawler_run_id"] = run_id
    result = client.table("social_items").insert(item).execute()
    return result.data[0] if result.data else None


def create_crawler_run(client: Client, crawler_name: str, tool: str, config: Dict = None) -> Dict:
    """Create a new crawler run record."""
    result = client.table("crawler_runs").insert({
        "crawler_name": crawler_name,
        "tool": tool,
        "config": config or {}
    }).execute()
    return result.data[0]


def update_crawler_run(client: Client, run_id: str, **kwargs) -> Dict:
    """Update crawler run record."""
    result = client.table("crawler_runs").update(kwargs).eq("id", run_id).execute()
    return result.data[0] if result.data else None


def get_items_without_embeddings(client: Client, limit: int = 100) -> List[Dict]:
    """Get items that need embeddings."""
    result = client.table("social_items") \
        .select("id, title, content") \
        .is_("embedding", "null") \
        .limit(limit) \
        .execute()
    return result.data


def update_item_embedding(client: Client, item_id: str, embedding: List[float]) -> bool:
    """Update an item's embedding."""
    try:
        client.table("social_items") \
            .update({"embedding": embedding}) \
            .eq("id", item_id) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update embedding for {item_id}: {e}")
        return False


def search_by_embedding(
    client: Client,
    query_embedding: List[float],
    match_count: int = 10,
    filter_category: str = None
) -> List[Dict]:
    """Search items by embedding similarity using the RPC function.

    Args:
        client: Supabase client
        query_embedding: Query embedding vector (768 dimensions - Gemini)
        match_count: Number of results to return
        filter_category: Optional category filter

    Returns:
        List of matching items with similarity scores
    """
    result = client.rpc(
        "search_social_items",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_category": filter_category
        }
    ).execute()
    return result.data


def get_item_count(client: Client) -> int:
    """Get total count of social items."""
    result = client.table("social_items").select("id", count="exact").execute()
    return result.count or 0


def get_items_needing_date_fix(client: Client, limit: int = 100) -> List[Dict]:
    """Get items with NULL or non-YYYY-MM-DD posted_at values.

    Returns items where posted_at needs normalization.
    """
    # Get items with NULL posted_at
    null_result = client.table("social_items") \
        .select("id, posted_at, source") \
        .is_("posted_at", "null") \
        .limit(limit) \
        .execute()

    # Get items with non-null posted_at (we'll filter in Python for non-YYYY-MM-DD)
    remaining = limit - len(null_result.data)
    if remaining > 0:
        non_null_result = client.table("social_items") \
            .select("id, posted_at, source") \
            .not_.is_("posted_at", "null") \
            .limit(remaining * 2) \
            .execute()

        # Filter to items NOT in YYYY-MM-DD format
        import re
        pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        non_standard = [
            item for item in non_null_result.data
            if item.get("posted_at") and not pattern.match(str(item["posted_at"]))
        ][:remaining]

        return null_result.data + non_standard

    return null_result.data


def update_item_posted_at(client: Client, item_id: str, posted_at: str) -> bool:
    """Update an item's posted_at field."""
    try:
        client.table("social_items") \
            .update({"posted_at": posted_at}) \
            .eq("id", item_id) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update posted_at for {item_id}: {e}")
        return False


def get_embedding_count(client: Client) -> int:
    """Get count of items with embeddings."""
    result = client.table("social_items") \
        .select("id", count="exact") \
        .not_.is_("embedding", "null") \
        .execute()
    return result.count or 0


# =============================================================================
# ANSWERS (social_item_answers)
# =============================================================================

def save_answers(client: Client, social_item_id: str, answers: List[Dict]) -> int:
    """Save answers for a social item. Returns count saved."""
    if not answers:
        return 0
    saved = 0
    for i, answer in enumerate(answers):
        row = {
            "social_item_id": social_item_id,
            "content": answer.get("content", "")[:5000],
            "author": answer.get("author"),
            "position": answer.get("position", i),
            "votes": answer.get("votes", 0),
            "is_accepted": answer.get("is_accepted", False),
            "posted_at": answer.get("posted_at"),
            "source_id": answer.get("source_id"),
            "raw_data": answer.get("raw_data"),
        }
        try:
            client.table("social_item_answers").insert(row).execute()
            saved += 1
        except Exception as e:
            logger.warning(f"Failed to save answer for {social_item_id}: {e}")
    return saved


def get_answers_for_item(client: Client, social_item_id: str) -> List[Dict]:
    """Get answers for a social item, ordered by position."""
    result = client.table("social_item_answers") \
        .select("*") \
        .eq("social_item_id", social_item_id) \
        .order("position") \
        .execute()
    return result.data or []


def update_item_qa_metadata(client: Client, item_id: str, question_content: str = None, answer_count: int = 0) -> bool:
    """Update Q&A metadata on a social item."""
    try:
        update = {
            "has_answers": answer_count > 0,
            "answer_count": answer_count,
        }
        if question_content:
            update["question_content"] = question_content[:10000]
        client.table("social_items") \
            .update(update) \
            .eq("id", item_id) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update QA metadata for {item_id}: {e}")
        return False


def get_items_without_answers(client: Client, source: str = None, limit: int = 100) -> List[Dict]:
    """Get items that have no answers yet (for backfill)."""
    query = client.table("social_items") \
        .select("id, source, source_url, title, content") \
        .eq("has_answers", False) \
        .limit(limit)
    if source:
        query = query.eq("source", source)
    result = query.execute()
    return result.data or []


# =============================================================================
# ENTITIES (item_entities, entities)
# =============================================================================

def save_item_entities(client: Client, social_item_id: str, entities: List[Dict]) -> int:
    """Save entity mentions for a social item. Returns count saved.

    Each entity dict: {entity_id, mention_type, sentiment, confidence, context_snippet}
    Uses upsert to handle re-runs gracefully.
    """
    if not entities:
        return 0
    saved = 0
    for entity in entities:
        row = {
            "social_item_id": social_item_id,
            "entity_id": entity["entity_id"],
            "mention_type": entity.get("mention_type", "direct"),
            "sentiment": entity.get("sentiment"),
            "confidence": entity.get("confidence", 1.0),
            "context_snippet": entity.get("context_snippet", "")[:500],
        }
        try:
            client.table("item_entities").upsert(
                row, on_conflict="social_item_id,entity_id"
            ).execute()
            saved += 1
        except Exception as e:
            logger.warning(f"Failed to save entity for {social_item_id}: {e}")
    return saved


# =============================================================================
# ASPECTS (item_aspects)
# =============================================================================

def cleanup_false_product_mentions(
    batch_size: int = 200,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Remove false product_mentions that don't actually appear in the item text.

    Iterates all items with non-empty product_mentions, checks each mention
    against the item's title + content, and strips any that aren't found.

    Args:
        batch_size: Items to fetch per batch
        dry_run: If True, report stats without updating

    Returns:
        Stats dict with processed, cleaned, unchanged counts
    """
    client = get_beurer_supabase()

    stats = {
        "processed": 0,
        "cleaned": 0,
        "unchanged": 0,
        "mentions_removed": 0,
        "dry_run": dry_run,
        "batches": 0,
        "samples": [],
    }

    last_id = None

    while True:
        stats["batches"] += 1

        # Fetch items with product_mentions, paginate by id
        query = client.table("social_items") \
            .select("id, title, content, product_mentions") \
            .not_.is_("product_mentions", "null") \
            .order("id") \
            .limit(batch_size)

        if last_id:
            query = query.gt("id", last_id)

        result = query.execute()
        items = result.data or []

        if not items:
            break

        for item in items:
            last_id = item["id"]
            pm = item.get("product_mentions") or []
            if not pm:
                continue

            stats["processed"] += 1
            text_lower = ((item.get("title") or "") + " " + (item.get("content") or "")).lower()

            valid = [p for p in pm if p.lower() in text_lower]

            if len(valid) == len(pm):
                stats["unchanged"] += 1
                continue

            removed = [p for p in pm if p not in valid]
            stats["mentions_removed"] += len(removed)
            stats["cleaned"] += 1

            if len(stats["samples"]) < 10:
                stats["samples"].append({
                    "id": item["id"],
                    "before": pm,
                    "after": valid,
                    "removed": removed,
                })

            if not dry_run:
                client.table("social_items") \
                    .update({"product_mentions": valid if valid else []}) \
                    .eq("id", item["id"]) \
                    .execute()

        logger.info(f"Cleanup batch {stats['batches']}: processed {len(items)}, cleaned {stats['cleaned']} so far")

    return stats


def purge_low_relevance_items(
    threshold: float = 0.3,
    batch_size: int = 200,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Delete low-relevance items from the DB after classification.

    Loops through the entire table in batches until no more candidates remain.

    Purge criteria (ALL must be true):
    - device_relevance_score IS NOT NULL (classification has run)
    - device_relevance_score < threshold
    - product_mentions is empty/null
    - No associated rows in item_entities

    Args:
        threshold: Items below this device_relevance_score are candidates (default 0.3)
        batch_size: Items to fetch per batch (default 200)
        dry_run: If True, report stats without actually deleting

    Returns:
        Stats dict with candidates_found, purged, skipped_has_products, skipped_has_entities, dry_run
    """
    client = get_beurer_supabase()

    stats = {
        "candidates_found": 0,
        "purged": 0,
        "skipped_has_products": 0,
        "skipped_has_entities": 0,
        "dry_run": dry_run,
        "threshold": threshold,
        "batches": 0,
    }

    while True:
        stats["batches"] += 1

        # Step 1: Query next batch of low device_relevance_score items
        result = client.table("social_items") \
            .select("id, product_mentions, device_relevance_score") \
            .not_.is_("device_relevance_score", "null") \
            .lt("device_relevance_score", threshold) \
            .limit(batch_size) \
            .execute()

        candidates = result.data or []
        if not candidates:
            break

        stats["candidates_found"] += len(candidates)

        # Step 2: Filter out items with non-empty product_mentions
        no_products = []
        for item in candidates:
            pm = item.get("product_mentions") or []
            if pm and len(pm) > 0:
                stats["skipped_has_products"] += 1
            else:
                no_products.append(item)

        if not no_products:
            # All candidates in this batch have products — no more purgeable items
            break

        # Step 3: Batch-check item_entities to exclude items with entity associations
        candidate_ids = [item["id"] for item in no_products]

        entity_result = client.table("item_entities") \
            .select("social_item_id") \
            .in_("social_item_id", candidate_ids) \
            .execute()

        ids_with_entities = set(row["social_item_id"] for row in (entity_result.data or []))

        to_purge = []
        for item in no_products:
            if item["id"] in ids_with_entities:
                stats["skipped_has_entities"] += 1
            else:
                to_purge.append(item["id"])

        if not to_purge:
            # All remaining candidates have entities — no more purgeable items
            break

        if dry_run:
            stats["purged"] += len(to_purge)
            # In dry_run, keep fetching to report total count across all batches
            # But we need to skip past these items — use id ordering
            # Since we can't delete them, we'd loop forever. Just do one pass for dry_run.
            # Count remaining candidates approximately
            count_result = client.table("social_items") \
                .select("id", count="exact") \
                .not_.is_("device_relevance_score", "null") \
                .lt("device_relevance_score", threshold) \
                .execute()
            stats["candidates_found"] = count_result.count or stats["candidates_found"]
            break

        # Step 4: Bulk-delete dependent rows first, then social_items
        try:
            client.table("item_aspects").delete().in_("social_item_id", to_purge).execute()
            client.table("item_entities").delete().in_("social_item_id", to_purge).execute()
            client.table("social_item_answers").delete().in_("social_item_id", to_purge).execute()
            client.table("social_items").delete().in_("id", to_purge).execute()
            stats["purged"] += len(to_purge)
        except Exception as e:
            logger.warning(f"Batch purge failed: {e}")

        logger.info(f"Purge batch {stats['batches']}: deleted {len(to_purge)} items (total: {stats['purged']})")

    return stats


def save_item_aspects(client: Client, social_item_id: str, aspects: List[Dict]) -> int:
    """Save aspect-based sentiment for a social item. Returns count saved.

    Each aspect dict: {aspect, sentiment, intensity, evidence_snippet}
    Uses upsert to handle re-runs gracefully.
    """
    if not aspects:
        return 0
    saved = 0
    for aspect in aspects:
        row = {
            "social_item_id": social_item_id,
            "aspect": aspect["aspect"],
            "sentiment": aspect["sentiment"],
            "intensity": aspect.get("intensity", 3),
            "evidence_snippet": aspect.get("evidence_snippet", "")[:500],
        }
        try:
            client.table("item_aspects").upsert(
                row, on_conflict="social_item_id,aspect"
            ).execute()
            saved += 1
        except Exception as e:
            logger.warning(f"Failed to save aspect for {social_item_id}: {e}")
    return saved


# =============================================================================
# SERVICE CASES (service_cases)
# =============================================================================


def get_existing_case_ids(client: Client, client_id: str, case_ids: List[str]) -> set:
    """Return set of case_ids that already exist for this client."""
    if not case_ids:
        return set()
    existing = set()
    # Query in chunks of 500 to avoid URL length limits
    for i in range(0, len(case_ids), 500):
        chunk = case_ids[i:i+500]
        result = client.table("service_cases").select("case_id").eq("client_id", client_id).in_("case_id", chunk).execute()
        existing.update(row["case_id"] for row in result.data)
    return existing


def save_service_cases(client: Client, cases: List[Dict[str, Any]]) -> int:
    """Bulk insert service cases in batches of 1000. Returns count inserted."""
    total = 0
    for i in range(0, len(cases), 1000):
        batch = cases[i:i+1000]
        result = client.table("service_cases").insert(batch).execute()
        total += len(result.data)
    return total


def get_service_cases(client: Client, client_id: str, start_date: str, end_date: str) -> List[Dict]:
    """Fetch service cases for a client within a date range."""
    result = (
        client.table("service_cases")
        .select("*")
        .eq("client_id", client_id)
        .gte("case_date", start_date)
        .lte("case_date", end_date)
        .execute()
    )
    return result.data


def get_service_case_summary(client: Client, client_id: str, product_model: str, days: int = 90) -> Optional[Dict]:
    """Get top 5 reasons + counts for a product over the last N days.

    Returns: { product, total_cases, top_reasons: [{ reason, count, percent }] }
    or None if no data.
    """
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = (
        client.table("service_cases")
        .select("reason")
        .eq("client_id", client_id)
        .eq("product_model", product_model)
        .gte("case_date", cutoff)
        .execute()
    )
    if not result.data:
        return None
    # Count by reason
    counts: Dict[str, int] = {}
    for row in result.data:
        counts[row["reason"]] = counts.get(row["reason"], 0) + 1
    total = sum(counts.values())
    top_reasons = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "product": product_model,
        "total_cases": total,
        "top_reasons": [
            {"reason": r, "count": c, "percent": round(c / total * 100)}
            for r, c in top_reasons
        ],
    }
