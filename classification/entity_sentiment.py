"""Standalone entity sentiment classification."""
import json
import logging
import time
from typing import Dict, List

from services.gemini import get_classification_model
from .deep_insights import _match_entity_sentiment_to_entities

logger = logging.getLogger(__name__)

_ENTITY_SENTIMENT_PROMPT = """Analysiere diesen deutschen Beitrag und bewerte das Sentiment gegenüber JEDEM genannten Produkt/Marke.

Produkte/Marken im Beitrag: {entity_names}

WICHTIG: Verschiedene Produkte können UNTERSCHIEDLICHE Sentiments haben.
Antworte NUR mit validem JSON-Array:
[{{"entity": "Produktname", "sentiment": "positive/neutral/negative"}}]

Beitrag:
{content}

Antworte mit NUR dem JSON-Array, kein Markdown oder Erklärung."""


def classify_entity_sentiments(content: str, title: str, entity_names: List[str]) -> List[Dict]:
    """Classify sentiment toward specific entities in a text.

    Lightweight prompt — only asks for per-entity sentiment, no other fields.

    Args:
        content: Item content text
        title: Item title
        entity_names: List of entity canonical names to evaluate

    Returns:
        List of dicts: {entity, sentiment}
    """
    model = get_classification_model()

    full_text = f"{title}\n\n{content}" if title else content
    if len(full_text) > 5000:
        full_text = full_text[:5000]

    prompt = _ENTITY_SENTIMENT_PROMPT.format(
        entity_names=", ".join(entity_names),
        content=full_text,
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)

        if not isinstance(result, list):
            return []

        valid = []
        for entry in result:
            if not isinstance(entry, dict):
                continue
            entity = entry.get("entity")
            sentiment = entry.get("sentiment")
            if not entity or sentiment not in ["positive", "neutral", "negative"]:
                continue
            valid.append({"entity": str(entity).strip()[:100], "sentiment": sentiment})

        return valid

    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Entity sentiment classification failed: {e}")
        return []


def backfill_entity_sentiments(batch_size: int = 100, after_id: str = None) -> dict:
    """Backfill sentiment for item_entities rows where sentiment IS NULL.

    Groups by social_item_id, fetches item content, runs lightweight LLM prompt
    to get per-entity sentiment, and updates item_entities.sentiment.

    For items with only one entity, copies item-level sentiment (no LLM needed).

    Args:
        batch_size: Number of items to process
        after_id: Process items with social_item_id > this value (pagination)

    Returns:
        Stats dict: {processed, updated, skipped_single, failed, last_id}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "updated": 0, "skipped_single": 0, "failed": 0, "last_id": None}

    # Find items with NULL entity sentiment
    query = client.table("item_entities") \
        .select("social_item_id, entity_id, entities(canonical_name, entity_type)") \
        .is_("sentiment", "null") \
        .order("social_item_id") \
        .limit(batch_size * 5)  # Over-fetch since multiple entities per item

    if after_id:
        query = query.gt("social_item_id", after_id)

    result = query.execute()
    if not result.data:
        logger.info("No entity sentiments need backfill")
        return stats

    # Group by social_item_id
    entities_by_item: Dict[str, List[Dict]] = {}
    for row in result.data:
        sid = row["social_item_id"]
        if sid not in entities_by_item:
            entities_by_item[sid] = []
        entities_by_item[sid].append(row)

    # Limit to batch_size unique items
    item_ids = list(entities_by_item.keys())[:batch_size]

    # Fetch item content + item-level sentiment
    items_data: Dict[str, Dict] = {}
    for batch_start in range(0, len(item_ids), 100):
        batch_ids = item_ids[batch_start:batch_start + 100]
        item_result = client.table("social_items") \
            .select("id, title, content, sentiment") \
            .in_("id", batch_ids) \
            .execute()
        for item in (item_result.data or []):
            items_data[item["id"]] = item

    for item_id in item_ids:
        item = items_data.get(item_id)
        if not item:
            continue

        item_ents = entities_by_item.get(item_id, [])
        stats["processed"] += 1
        stats["last_id"] = item_id

        try:
            # Single entity: copy item-level sentiment (no LLM needed)
            if len(item_ents) == 1:
                item_sentiment = item.get("sentiment") or "neutral"
                ent = item_ents[0]
                client.table("item_entities").update({
                    "sentiment": item_sentiment,
                }).eq("social_item_id", item_id).eq("entity_id", ent["entity_id"]).execute()
                stats["updated"] += 1
                stats["skipped_single"] += 1
                continue

            # Multiple entities: use LLM for per-entity sentiment
            entity_names = []
            for ent in item_ents:
                info = ent.get("entities") or {}
                name = info.get("canonical_name", "")
                if name:
                    entity_names.append(name)

            if not entity_names:
                continue

            entity_sents = classify_entity_sentiments(
                content=item.get("content", ""),
                title=item.get("title", ""),
                entity_names=entity_names,
            )

            # Match results back to item_entities
            if entity_sents:
                matched = _match_entity_sentiment_to_entities(entity_sents, item_ents)
                for m in matched:
                    client.table("item_entities").update({
                        "sentiment": m["sentiment"],
                    }).eq("social_item_id", item_id).eq("entity_id", m["entity_id"]).execute()
                    stats["updated"] += 1

            # Rate limiting for multi-entity items (LLM call)
            time.sleep(1.1)

        except Exception as e:
            logger.error(f"Failed entity sentiment for item {item_id}: {e}")
            stats["failed"] += 1

    logger.info(f"Entity sentiment backfill complete: {stats}")
    return stats
