"""Customer journey stage classification."""
import json
import logging
import time
from typing import Any, Dict

from services.gemini import get_classification_model
from report.constants import (
    JOURNEY_STAGES, PAIN_CATEGORY_LABELS_DE, SOLUTION_LABELS_DE,
)

logger = logging.getLogger(__name__)

# Build allowed value lists for validation
_valid_journey_stages = JOURNEY_STAGES
_valid_pain_categories = list(PAIN_CATEGORY_LABELS_DE.keys())
_valid_solutions = list(SOLUTION_LABELS_DE.keys())

JOURNEY_CLASSIFICATION_PROMPT = """Analysiere diesen deutschen Gesundheitsbeitrag und klassifiziere ihn für die Customer Journey Intelligence.

Antworte NUR mit validem JSON mit diesen Feldern:
- journey_stage: Eine der folgenden Stufen:
  * "awareness" — Nutzer erkennt ein Gesundheitsproblem oder Symptom (z.B. "Ich habe seit Wochen Rückenschmerzen")
  * "consideration" — Nutzer sucht nach Lösungsmöglichkeiten (z.B. "Was hilft gegen chronische Schmerzen?")
  * "comparison" — Nutzer vergleicht Methoden oder Produkte (z.B. "TENS oder Wärmetherapie — was ist besser?")
  * "purchase" — Nutzer steht vor Kaufentscheidung (z.B. "Welches TENS-Gerät soll ich kaufen?")
  * "advocacy" — Nutzer teilt Erfahrung oder empfiehlt (z.B. "Mein Beurer EM 59 hat mir sehr geholfen")

- pain_category: Eine der folgenden Kategorien (oder null wenn nicht zutreffend):
  * "ruecken_nacken" — Rücken-/Nackenschmerzen
  * "gelenke_arthrose" — Gelenk-/Arthroseschmerzen
  * "menstruation" — Menstruationsschmerzen
  * "kopfschmerzen" — Kopfschmerzen/Migräne
  * "bluthochdruck" — Bluthochdruck/Kreislauf
  * "neuropathie" — Neuropathie/Nervenschmerzen
  * "sonstige_schmerzen" — Sonstige Schmerzen

- solutions_mentioned: Array der erwähnten Lösungsansätze (leeres Array wenn keine):
  * "tens_ems", "waermetherapie", "blutdruckmessung", "medikamente", "physiotherapie",
  * "hausmittel", "arztbesuch", "sport_bewegung", "massage", "akupunktur", "sonstiges"

- beurer_opportunity: Kurzer Satz (max 25 Wörter, Deutsch): Wie könnte Beurer diesem Nutzer helfen?
  Z.B. "TENS-Gerät EM 59 als Alternative zu Schmerzmitteln positionieren" oder null wenn keine Chance.

Beitrag:
{content}

Antworte mit NUR dem JSON-Objekt, kein Markdown oder Erklärung."""


def classify_journey_stage(content: str, title: str = "") -> Dict[str, Any]:
    """Classify a single item for customer journey intelligence.

    Args:
        content: The main content text
        title: Optional title for context

    Returns:
        Dict with journey_stage, pain_category, solutions_mentioned, beurer_opportunity
    """
    model = get_classification_model()

    full_text = f"{title}\n\n{content}" if title else content
    if len(full_text) > 10000:
        full_text = full_text[:10000]

    prompt = JOURNEY_CLASSIFICATION_PROMPT.format(content=full_text)

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)

        # Validate journey_stage
        if result.get("journey_stage") not in _valid_journey_stages:
            result["journey_stage"] = "awareness"

        # Validate pain_category
        if result.get("pain_category") and result["pain_category"] not in _valid_pain_categories:
            result["pain_category"] = None

        # Validate solutions_mentioned
        if not isinstance(result.get("solutions_mentioned"), list):
            result["solutions_mentioned"] = []
        else:
            result["solutions_mentioned"] = [
                s for s in result["solutions_mentioned"] if s in _valid_solutions
            ]

        # Validate beurer_opportunity
        if not isinstance(result.get("beurer_opportunity"), str):
            result["beurer_opportunity"] = None

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse journey classification JSON: {e}")
        return {
            "journey_stage": "awareness",
            "pain_category": None,
            "solutions_mentioned": [],
            "beurer_opportunity": None,
        }
    except Exception as e:
        logger.error(f"Journey classification failed: {e}")
        raise


def backfill_journey_stages(batch_size: int = 50) -> dict:
    """Backfill journey_stage for items missing it.

    Args:
        batch_size: Number of items to process per run

    Returns:
        Dict with stats: {processed, failed, by_stage: {stage: count}}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "failed": 0, "by_stage": {}}

    # Fetch items without journey_stage
    result = client.table("social_items") \
        .select("id, title, content") \
        .is_("journey_stage", "null") \
        .limit(batch_size) \
        .execute()

    if not result.data:
        logger.info("No items need journey_stage backfill")
        return stats

    items = result.data
    logger.info(f"Processing {len(items)} items for journey stage classification")

    for item in items:
        try:
            classification = classify_journey_stage(
                content=item.get("content", ""),
                title=item.get("title", "")
            )

            update_data = {
                "journey_stage": classification["journey_stage"],
                "pain_category": classification.get("pain_category"),
                "solutions_mentioned": classification.get("solutions_mentioned", []),
                "beurer_opportunity": classification.get("beurer_opportunity"),
            }

            client.table("social_items") \
                .update(update_data) \
                .eq("id", item["id"]) \
                .execute()

            stats["processed"] += 1
            stage = classification["journey_stage"]
            stats["by_stage"][stage] = stats["by_stage"].get(stage, 0) + 1
            logger.debug(f"Journey classified item {item['id']}: {stage}")

            # Rate limiting - Gemini free tier is 60 RPM
            time.sleep(1.1)

        except Exception as e:
            logger.error(f"Failed to classify journey for item {item['id']}: {e}")
            stats["failed"] += 1

    logger.info(f"Journey stage backfill complete: {stats}")
    return stats
