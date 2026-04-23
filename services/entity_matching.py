"""Deterministic entity matching service (no LLM).

Scans social item content for product/brand mentions using the entities table,
extracts context snippets, and determines mention types heuristically.
"""
import re
import logging
from typing import List, Dict, Optional

from db.client import get_beurer_supabase, save_item_entities

logger = logging.getLogger(__name__)

# Words that signal specific mention types (German + English).
# We check if any of these appear within ±100 chars of the entity match.
COMPARISON_WORDS = [
    "vs", "oder", "vergleich", "besser als", "schlechter als",
    "im vergleich", "verglichen", "gegenüber", "alternative",
    "unterschied", "versus",
]
RECOMMENDATION_WORDS = [
    "empfehle", "empfehlung", "kann ich empfehlen", "empfohlen",
    "würde ich empfehlen", "rate ich", "empfehlenswert", "top gerät",
    "sehr zufrieden", "kann man empfehlen",
]
COMPLAINT_WORDS = [
    "schlecht", "problem", "defekt", "mangel", "kaputt", "fehler",
    "funktioniert nicht", "enttäuscht", "schrott", "reklamation",
    "ärgerlich", "unbrauchbar", "mangelhaft", "unzuverlässig",
]


def load_entities(client) -> List[Dict]:
    """Load all entities from the database.

    Returns list of entity dicts with id, canonical_name, entity_type,
    category, brand, aliases.
    """
    result = client.table("entities").select(
        "id, canonical_name, entity_type, category, brand, aliases"
    ).execute()
    return result.data or []


def _extract_snippet(text: str, start: int, end: int, context: int = 50) -> str:
    """Extract a context snippet around a match position."""
    snippet_start = max(0, start - context)
    snippet_end = min(len(text), end + context)
    snippet = text[snippet_start:snippet_end].strip()
    if snippet_start > 0:
        snippet = "..." + snippet
    if snippet_end < len(text):
        snippet = snippet + "..."
    return snippet


def _classify_mention_type(text: str, match_start: int, match_end: int) -> str:
    """Determine mention type based on nearby words.

    Checks ±100 chars around the match for comparison, recommendation,
    or complaint signals.
    """
    window_start = max(0, match_start - 100)
    window_end = min(len(text), match_end + 100)
    window = text[window_start:window_end].lower()

    # Check in priority order: comparison > recommendation > complaint > direct
    for word in COMPARISON_WORDS:
        if word in window:
            return "comparison"

    for word in RECOMMENDATION_WORDS:
        if word in window:
            return "recommendation"

    for word in COMPLAINT_WORDS:
        if word in window:
            return "complaint"

    return "direct"


def match_entities(content: str, title: str, entities: List[Dict]) -> List[Dict]:
    """Match entities in title + content using case-insensitive text scanning.

    Args:
        content: Item content text
        title: Item title text
        entities: List of entity dicts from load_entities()

    Returns:
        List of match dicts: {entity_id, mention_type, confidence, context_snippet}
    """
    if not content and not title:
        return []

    # Combine title and content for scanning
    full_text = f"{title or ''}\n{content or ''}"
    full_text_lower = full_text.lower()

    matches = []
    seen_entity_ids = set()

    for entity in entities:
        entity_id = entity["id"]
        if entity_id in seen_entity_ids:
            continue

        canonical = entity["canonical_name"]
        aliases = entity.get("aliases") or []

        # Try canonical name first (higher confidence)
        canonical_lower = canonical.lower()
        pattern = r'\b' + re.escape(canonical_lower) + r'\b'
        m = re.search(pattern, full_text_lower)
        if m:
            idx = m.start()
            match_end = m.end()
            snippet = _extract_snippet(full_text, idx, match_end)
            mention_type = _classify_mention_type(full_text, idx, match_end)
            matches.append({
                "entity_id": entity_id,
                "mention_type": mention_type,
                "confidence": 1.0,
                "context_snippet": snippet,
            })
            seen_entity_ids.add(entity_id)
            continue

        # Try aliases (slightly lower confidence)
        for alias in aliases:
            alias_lower = alias.lower()
            # Skip short aliases (<=3 chars) to avoid false positives
            if len(alias_lower) <= 3:
                continue
            # For aliases that are common substrings (4-5 chars), require word boundary
            if len(alias_lower) <= 5:
                pattern = r'\b' + re.escape(alias_lower) + r'\b'
                match = re.search(pattern, full_text_lower)
                if match:
                    idx = match.start()
                    match_end = match.end()
                else:
                    continue
            else:
                idx = full_text_lower.find(alias_lower)
                if idx == -1:
                    continue
                match_end = idx + len(alias_lower)
            snippet = _extract_snippet(full_text, idx, match_end)
            mention_type = _classify_mention_type(full_text, idx, match_end)
            matches.append({
                "entity_id": entity_id,
                "mention_type": mention_type,
                "confidence": 0.9,
                "context_snippet": snippet,
            })
            seen_entity_ids.add(entity_id)
            break  # One alias match per entity is enough

    return matches


def backfill_entities(batch_size: int = 100) -> dict:
    """Backfill entity mentions for all social items.

    Loads all entities once, then scans social_items in batches.
    For each item, runs match_entities() and saves results via
    save_item_entities(). Also updates the product_mentions column
    with canonical names for consistency.

    Args:
        batch_size: Number of items to process per batch

    Returns:
        Stats dict: {processed, matched, total_mentions, by_entity_type}
    """
    client = get_beurer_supabase()

    # Load all entities once
    entities = load_entities(client)
    if not entities:
        logger.warning("No entities found in database. Run seed_entities.py first.")
        return {"processed": 0, "matched": 0, "total_mentions": 0, "by_entity_type": {}}

    logger.info(f"Loaded {len(entities)} entities for matching")

    # Build entity lookup by ID for product_mentions update
    entity_lookup = {e["id"]: e for e in entities}

    stats = {
        "processed": 0,
        "matched": 0,
        "total_mentions": 0,
        "by_entity_type": {},
        "errors": 0,
    }

    # Paginate through all social_items by id
    last_id = None
    while True:
        query = client.table("social_items") \
            .select("id, title, content, product_mentions") \
            .order("id") \
            .limit(batch_size)

        if last_id:
            query = query.gt("id", last_id)

        result = query.execute()
        items = result.data or []

        if not items:
            break

        for item in items:
            stats["processed"] += 1
            last_id = item["id"]

            try:
                item_matches = match_entities(
                    content=item.get("content") or "",
                    title=item.get("title") or "",
                    entities=entities,
                )

                if item_matches:
                    stats["matched"] += 1
                    stats["total_mentions"] += len(item_matches)

                    # Save to item_entities
                    save_item_entities(client, item["id"], item_matches)

                    # Track by entity type
                    for m in item_matches:
                        ent = entity_lookup.get(m["entity_id"])
                        if ent:
                            etype = ent["entity_type"]
                            stats["by_entity_type"][etype] = (
                                stats["by_entity_type"].get(etype, 0) + 1
                            )

                    # Update product_mentions column with canonical names (dedup)
                    matched_canonicals = []
                    for m in item_matches:
                        ent = entity_lookup.get(m["entity_id"])
                        if ent and ent["entity_type"] in ("beurer_product", "competitor_product"):
                            matched_canonicals.append(ent["canonical_name"])

                    if matched_canonicals:
                        # Merge with existing product_mentions
                        existing = item.get("product_mentions") or []
                        merged = sorted(set(existing) | set(matched_canonicals))
                        try:
                            client.table("social_items").update(
                                {"product_mentions": merged}
                            ).eq("id", item["id"]).execute()
                        except Exception as e:
                            logger.warning(
                                f"Failed to update product_mentions for {item['id']}: {e}"
                            )

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error processing item {item['id']}: {e}")

        logger.info(
            f"Processed {stats['processed']} items, "
            f"{stats['matched']} matched, "
            f"{stats['total_mentions']} total mentions"
        )

        # If we got fewer items than batch_size, we're done
        if len(items) < batch_size:
            break

    logger.info(
        f"Entity backfill complete: {stats['processed']} processed, "
        f"{stats['matched']} matched, {stats['total_mentions']} mentions"
    )
    return stats
