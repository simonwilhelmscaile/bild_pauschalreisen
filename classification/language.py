"""Language detection (deterministic, no LLM)."""
import logging
import re

logger = logging.getLogger(__name__)

# German indicator words (common, unambiguous)
_GERMAN_INDICATORS = {
    "und", "der", "die", "das", "ist", "nicht", "ein", "eine", "mit", "für",
    "sich", "auf", "den", "dem", "des", "von", "hat", "ich", "auch", "aber",
    "wie", "noch", "bei", "nach", "nur", "über", "oder", "kann", "habe",
    "mir", "sehr", "wenn", "schon", "mein", "meine", "wir", "sind", "war",
    "zum", "zur", "vom", "als", "vor", "dann", "keine", "jetzt", "hier",
    "diese", "dieser", "dieses", "hatte", "immer", "dass", "seit", "weil",
}

# English indicator words (common, unambiguous)
_ENGLISH_INDICATORS = {
    "the", "and", "is", "for", "with", "this", "that", "have", "from", "they",
    "was", "are", "been", "has", "had", "but", "not", "you", "all", "can",
    "her", "would", "their", "what", "there", "been", "one", "our", "out",
    "just", "about", "some", "time", "very", "when", "which", "your", "said",
    "each", "she", "how", "will", "other", "than", "its", "after", "who",
    "get", "would", "could", "should", "into", "because", "does", "where",
}


def detect_language(text: str) -> str:
    """Detect language of text using simple word-frequency heuristics.

    Fast deterministic detection -- no LLM call. Checks for German-specific
    characters (umlauts, eszett) and word frequency.

    Args:
        text: Input text to detect

    Returns:
        "de", "en", or "other"
    """
    if not text or len(text.strip()) < 10:
        return "other"

    text_lower = text.lower()

    # Count German-specific characters
    german_chars = sum(1 for c in text_lower if c in 'äöüß')

    # Tokenize: split on non-alphanumeric (keep umlauts)
    words = re.findall(r'[a-zäöüß]+', text_lower)
    if not words:
        return "other"

    total_words = len(words)
    word_set = set(words)

    # Count indicator word matches
    de_matches = sum(words.count(w) for w in _GERMAN_INDICATORS if w in word_set)
    en_matches = sum(words.count(w) for w in _ENGLISH_INDICATORS if w in word_set)

    # German character bonus (umlauts are strong German signals)
    de_score = de_matches + german_chars * 2
    en_score = en_matches

    # Normalize by total words for comparison
    if total_words > 0:
        de_ratio = de_score / total_words
        en_ratio = en_score / total_words
    else:
        return "other"

    # Decision thresholds
    if de_ratio > en_ratio and de_score >= 3:
        return "de"
    elif en_ratio > de_ratio and en_score >= 3:
        return "en"
    elif german_chars >= 2:
        # If there are umlauts but not enough words matched, still likely German
        return "de"
    elif de_score > 0 and en_score == 0:
        return "de"
    elif en_score > 0 and de_score == 0:
        return "en"
    else:
        return "other"


def backfill_language_detection(batch_size: int = 200) -> dict:
    """Backfill language column for items where language IS NULL.

    Uses deterministic heuristic (no LLM call) so can run at high throughput.

    Args:
        batch_size: Number of items to process per run

    Returns:
        Dict with stats: {processed, by_language}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "by_language": {"de": 0, "en": 0, "other": 0}}

    result = client.table("social_items") \
        .select("id, title, content") \
        .is_("language", "null") \
        .limit(batch_size) \
        .execute()

    if not result.data:
        logger.info("No items need language detection")
        return stats

    items = result.data
    logger.info(f"Processing {len(items)} items for language detection")

    for item in items:
        text = ((item.get("title") or "") + " " + (item.get("content") or "")).strip()
        lang = detect_language(text)

        client.table("social_items") \
            .update({"language": lang}) \
            .eq("id", item["id"]) \
            .execute()

        stats["processed"] += 1
        stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1

    logger.info(f"Language detection backfill complete: {stats}")
    return stats
