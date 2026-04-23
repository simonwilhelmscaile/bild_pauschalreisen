"""Source URL resolution (deterministic, no LLM)."""
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def resolve_source_domain(source_url: str) -> str:
    """Extract and clean the domain from a source URL.

    Strips 'www.' prefix and returns the bare domain.

    Args:
        source_url: Full URL string

    Returns:
        Domain string (e.g., "otto.de", "chip.de"), or "unknown"
    """
    if not source_url:
        return "unknown"
    try:
        domain = urlparse(source_url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or "unknown"
    except Exception:
        return "unknown"


def backfill_resolved_sources(batch_size: int = 200) -> dict:
    """Backfill resolved_source for ALL items where resolved_source IS NULL.

    Extracts the domain from source_url for every item.

    Args:
        batch_size: Number of items to process per run

    Returns:
        Dict with stats: {processed, samples}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "samples": []}

    result = client.table("social_items") \
        .select("id, source_url") \
        .is_("resolved_source", "null") \
        .limit(batch_size) \
        .execute()

    if not result.data:
        logger.info("No items need resolved_source backfill")
        return stats

    items = result.data
    logger.info(f"Processing {len(items)} items for resolved_source")

    for item in items:
        domain = resolve_source_domain(item.get("source_url", ""))

        client.table("social_items") \
            .update({"resolved_source": domain}) \
            .eq("id", item["id"]) \
            .execute()

        stats["processed"] += 1

        if len(stats["samples"]) < 5:
            stats["samples"].append({
                "id": item["id"],
                "url": (item.get("source_url") or "")[:80],
                "resolved": domain,
            })

    logger.info(f"Resolved source backfill complete: {stats}")
    return stats
