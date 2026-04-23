"""Classification package — LLM and deterministic classification modules."""
from .core import classify_item, backfill_classifications, CLASSIFICATION_PROMPT
from .journey import classify_journey_stage, backfill_journey_stages, JOURNEY_CLASSIFICATION_PROMPT
from .deep_insights import (
    classify_deep_insights, backfill_deep_insights,
    _empty_deep_insights, _safe_update_dict, _match_entity_sentiment_to_entities,
)
from .entity_sentiment import classify_entity_sentiments, backfill_entity_sentiments
from .medication import normalize_medications, MEDICATION_NORMALIZATION
from .language import detect_language, backfill_language_detection
from .source_resolution import resolve_source_domain, backfill_resolved_sources
from .engagement import compute_engagement_score, backfill_engagement_scores

__all__ = [
    # Core classification
    "classify_item", "backfill_classifications", "CLASSIFICATION_PROMPT",
    # Journey
    "classify_journey_stage", "backfill_journey_stages", "JOURNEY_CLASSIFICATION_PROMPT",
    # Deep insights
    "classify_deep_insights", "backfill_deep_insights",
    "_empty_deep_insights", "_safe_update_dict", "_match_entity_sentiment_to_entities",
    # Entity sentiment
    "classify_entity_sentiments", "backfill_entity_sentiments",
    # Medication
    "normalize_medications", "MEDICATION_NORMALIZATION",
    # Language
    "detect_language", "backfill_language_detection",
    # Source resolution
    "resolve_source_domain", "backfill_resolved_sources",
    # Engagement
    "compute_engagement_score", "backfill_engagement_scores",
]
