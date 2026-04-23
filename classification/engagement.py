"""Engagement score computation (deterministic, no LLM)."""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def compute_engagement_score(item: Dict) -> float | None:
    """Compute an engagement score from raw_data metrics.

    Formula varies by source:
    - Reddit: score + num_comments * 2
    - Amazon: (rating or 3) + helpful_votes * 5
    - YouTube: likes + reply_count * 2
    - TikTok/Instagram: (likes + comments * 3 + shares * 5) / 100
    - Gutefrage/Health forums/Serper: None (no engagement data)

    Args:
        item: Dict with 'source' and 'raw_data' keys

    Returns:
        Float engagement score, or None if not applicable
    """
    source = (item.get("source") or "").lower()
    raw = item.get("raw_data") or {}

    if source == "reddit":
        score = raw.get("score") or 0
        num_comments = raw.get("num_comments") or 0
        return float(score + num_comments * 2)

    elif source == "amazon.de":
        rating = raw.get("rating") or 3
        helpful_votes = raw.get("helpful_votes") or 0
        return float(rating + helpful_votes * 5)

    elif source == "youtube":
        likes = raw.get("likes") or raw.get("voteCount") or 0
        reply_count = raw.get("reply_count") or raw.get("replyCount") or 0
        return float(likes + reply_count * 2)

    elif source == "youtube_transcript":
        views = raw.get("views") or 0
        likes = raw.get("likes") or 0
        return float(likes + (views / 1000))

    elif source in ("tiktok", "instagram"):
        likes = raw.get("likes") or raw.get("diggCount") or raw.get("likesCount") or 0
        comments = raw.get("comments") or raw.get("commentCount") or raw.get("commentsCount") or 0
        shares = raw.get("shares") or raw.get("shareCount") or 0
        return float(likes + comments * 3 + shares * 5) / 100.0

    elif source == "twitter":
        likes = raw.get("likes") or raw.get("favorite_count") or raw.get("likeCount") or 0
        retweets = raw.get("retweets") or raw.get("retweet_count") or raw.get("retweetCount") or 0
        replies = raw.get("replies") or raw.get("reply_count") or raw.get("replyCount") or 0
        return float(likes + retweets * 3 + replies * 2) / 100.0

    else:
        return None


def backfill_engagement_scores(batch_size: int = 200) -> dict:
    """Backfill engagement_score for items where it IS NULL and source has engagement data.

    Args:
        batch_size: Number of items to process per run

    Returns:
        Dict with stats: {processed, computed, skipped}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "computed": 0, "skipped": 0}

    # Only fetch items from sources that have engagement data
    engagement_sources = ["reddit", "amazon.de", "youtube", "youtube_transcript", "tiktok", "instagram", "twitter"]

    result = client.table("social_items") \
        .select("id, source, raw_data") \
        .is_("engagement_score", "null") \
        .in_("source", engagement_sources) \
        .limit(batch_size) \
        .execute()

    if not result.data:
        logger.info("No items need engagement_score backfill")
        return stats

    items = result.data
    logger.info(f"Processing {len(items)} items for engagement scores")

    for item in items:
        score = compute_engagement_score(item)
        stats["processed"] += 1

        if score is not None:
            client.table("social_items") \
                .update({"engagement_score": score}) \
                .eq("id", item["id"]) \
                .execute()
            stats["computed"] += 1
        else:
            stats["skipped"] += 1

    logger.info(f"Engagement score backfill complete: {stats}")
    return stats
