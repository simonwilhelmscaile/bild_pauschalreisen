"""Core classification — category, sentiment, keywords, relevance."""
import json
import logging
import time
from typing import Any, Dict

from services.gemini import get_classification_model
from report.constants import (
    format_products_for_llm_prompt, COMPETITOR_PRODUCTS,
    EMOTION_VALUES, INTENT_VALUES,
)

logger = logging.getLogger(__name__)

# Build product list strings once at import time
_beurer_products_str = format_products_for_llm_prompt()
_competitor_products_str = ", ".join(p for p in COMPETITOR_PRODUCTS if p != "Omron")

CLASSIFICATION_PROMPT = """Analyze this German health forum post. Return ONLY valid JSON with these fields:
- category: One of "blood_pressure", "pain_tens", "infrarot", "menstrual", "other"
- sentiment: One of "positive", "neutral", "negative"
- keywords: Array of 3-5 German keywords relevant to the content
- relevance_score: Float 0.0-1.0 indicating how actionable and insightful this post is for Beurer's product strategy:
  * 0.9-1.0: Specific Beurer product experience, comparison, or detailed recommendation
  * 0.7-0.8: Device purchase decision, detailed product comparison, or concrete device-related problem
  * 0.5-0.6: General discussion of device category with some actionable insight (technique, use case)
  * 0.3-0.4: Tangentially related health topic, no device focus, limited actionable value
  * 0.0-0.2: Pure health/lifestyle question with no device or product context

  IMPORTANT: General health discussions, symptom questions, or lifestyle posts WITHOUT device/product context must score 0.0-0.3 even if they mention a health category like "Blutdruck" or "Schmerzen".

  Examples of LOW relevance (0.0-0.3):
  - "Ist mein Blutdruck mit 140/90 zu hoch?" -> 0.2 (health question, no device)
  - "Tipps gegen Rückenschmerzen?" -> 0.2 (general health, no product)
  - "Mein Arzt hat Bluthochdruck diagnostiziert" -> 0.1 (medical, no device context)
  - "Welche Hausmittel helfen bei Erkältung?" -> 0.1 (unrelated health topic)

  Examples of HIGH relevance (0.7+):
  - "Beurer BM 27 zeigt unterschiedliche Werte an linkem/rechtem Arm" -> 0.9 (specific product issue)
  - "TENS oder Wärmekissen gegen Menstruationsschmerzen?" -> 0.7 (device comparison for specific pain)
  - "Welches Blutdruckmessgerät für Oberarm empfehlt ihr?" -> 0.8 (purchase intent, device category)

- product_mentions: Array of product names/models whose exact name or model number literally appears in the post text (e.g., "BM 27", "EM 59", "Omron M500"). ONLY include a product if its name is explicitly written in the text. Do NOT guess or infer products — if no product name appears in the text, return an empty array [].
- device_relevance_score: Float 0.0-1.0 indicating how device/product focused the content is:
  * 0.9-1.0: Directly asks about or mentions a specific device/brand ("Ist Beurer BM 27 gut?")
  * 0.7-0.8: Asks for device recommendations, comparisons, purchase advice ("Welches Blutdruckmessgerät?")
  * 0.5-0.6: Mentions device category but focuses on usage/technique ("Wie messe ich richtig?")
  * 0.3-0.4: Could be answered with a device but doesn't mention one
  * 0.0-0.2: Pure health question with no device context ("Ist 140/90 normal für mein Alter?")

  IMPORTANT: Questions about age, body effects, symptoms, or doctor visits WITHOUT device/measurement context must score 0.0-0.2.

  Examples of LOW device_relevance (0.0-0.2):
  - "Ab wie vielen Jahren ist EMS Training geeignet?" -> 0.1 (age question, no device)
  - "Macht EMS den Bauch flach?" -> 0.1 (body effect question)
  - "Habe ich Bluthochdruck?" -> 0.1 (health question, no device)
  - "Sollte ich zum Arzt gehen?" -> 0.0 (medical advice question)

  Examples of HIGH device_relevance (0.7+):
  - "Welches EMS-Gerät für Rückenschmerzen?" -> 0.8 (device recommendation)
  - "BM 27 vs Omron M500?" -> 0.9 (device comparison)
  - "Beurer EM 59 Erfahrungen?" -> 0.9 (specific product inquiry)

- emotion: The dominant emotion expressed by the author. One of:
  "frustration" (user is annoyed/stuck with a problem), "relief" (user found a solution or feels better),
  "anxiety" (user is worried about health or a purchase), "satisfaction" (user is happy with product/outcome),
  "confusion" (user doesn't understand something), "anger" (user is upset about service/product/situation),
  "hope" (user is optimistic about a solution), "resignation" (user has given up or feels helpless).
  Examples: "Mein Gerät zeigt ständig falsche Werte" -> "frustration"
  "Endlich normaler Blutdruck!" -> "relief". "Ist 160/100 gefährlich?" -> "anxiety"

- intent: The user's primary intent for posting. One of:
  "purchase_question" (wants to buy, asks which product), "troubleshooting" (has a problem with a device),
  "experience_sharing" (shares personal experience with product/health), "recommendation_request" (asks for advice/recommendations),
  "comparison" (compares products or methods), "general_question" (asks a general health question),
  "complaint" (files a complaint about product/service), "advocacy" (recommends/praises a product).
  Examples: "Welches TENS-Gerät ist gut?" -> "purchase_question"
  "BM 27 zeigt Error" -> "troubleshooting". "Ich liebe mein Beurer" -> "advocacy"

- sentiment_intensity: Integer 1-5 rating how strongly the sentiment is expressed:
  1 = very mild ("ganz ok"), 2 = mild ("nicht schlecht"), 3 = moderate ("bin zufrieden"),
  4 = strong ("wirklich super"/"ziemlich enttäuscht"), 5 = very strong ("absolut begeistert"/"völlig unbrauchbar")

Categories — classify by health topic, even WITHOUT a device mention:
- blood_pressure: Blood pressure monitoring, hypertension, BP values, BP medication, Blutdruckmessgeräte. Also: discussions about blood pressure readings (e.g. "Blutdruck 140/90"), hypertension diagnosis ("Hypertonie"), BP medication side effects, or home BP monitoring — even without mentioning a specific device.
- pain_tens: TENS/EMS devices, pain therapy, muscle stimulation, chronic pain management, nerve pain. Also: discussions about chronic pain, Rückenschmerzen, Nackenschmerzen, Nervenschmerzen, Ischias, pain treatment options — even without mentioning a device.
- infrarot: Infrared lamps, heat therapy, Wärmelampen, Rotlichtlampen. Also: discussions about heat therapy, warming treatments, Rotlicht gegen Verspannungen, Tiefenwärme — even generic heat therapy without a device.
- menstrual: Menstrual pain, period cramps, endometriosis, menstrual relief devices. Also: discussions about Regelschmerzen, Periodenschmerzen, Endometriose, Unterleibsschmerzen — even without mentioning a device.
- other: ONLY for content that does NOT relate to any of the above health categories. Use "other" only for general wellness, nutrition, mental health, or topics completely unrelated to blood pressure, pain/TENS, infrared/heat therapy, or menstrual health.

IMPORTANT: Health-topic discussions WITHOUT a device mention should STILL be categorized by their health topic (blood_pressure, pain_tens, infrarot, menstrual), NOT as "other". For example:
- "Mein Blutdruck ist 140/90, ist das normal?" → blood_pressure (NOT other)
- "Rückenschmerzen seit Monaten, was hilft?" → pain_tens (NOT other)
- "Rotlicht gegen Verspannungen" → infrarot (NOT other)
- "Starke Regelschmerzen jeden Monat" → menstrual (NOT other)
- "Tipps zum Abnehmen" → other (unrelated to Beurer health categories)

Known Beurer products to look for:
""" + _beurer_products_str + """
- Competitor products: """ + _competitor_products_str + """

Post content:
{content}

Respond with ONLY the JSON object, no markdown or explanation."""


def classify_item(content: str, title: str = "") -> Dict[str, Any]:
    """Classify a single item.

    Args:
        content: The main content text
        title: Optional title to include for context

    Returns:
        Dict with category, sentiment, keywords, relevance_score, product_mentions,
        device_relevance_score, emotion, intent, sentiment_intensity
    """
    model = get_classification_model()

    # Combine title and content, truncate if needed
    full_text = f"{title}\n\n{content}" if title else content
    if len(full_text) > 10000:
        full_text = full_text[:10000]

    prompt = CLASSIFICATION_PROMPT.format(content=full_text)

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)

        # Validate and normalize
        valid_categories = ["blood_pressure", "pain_tens", "infrarot", "menstrual", "other"]
        if result.get("category") not in valid_categories:
            result["category"] = "other"

        valid_sentiments = ["positive", "neutral", "negative"]
        if result.get("sentiment") not in valid_sentiments:
            result["sentiment"] = "neutral"

        if not isinstance(result.get("keywords"), list):
            result["keywords"] = []

        if not isinstance(result.get("product_mentions"), list):
            result["product_mentions"] = []

        # Post-validate: strip product_mentions that don't actually appear in the text
        if result["product_mentions"]:
            text_lower = full_text.lower()
            result["product_mentions"] = [
                p for p in result["product_mentions"]
                if p.lower() in text_lower
            ]

        relevance = result.get("relevance_score", 0.5)
        if not isinstance(relevance, (int, float)) or relevance < 0 or relevance > 1:
            result["relevance_score"] = 0.5
        else:
            result["relevance_score"] = float(relevance)

        device_relevance = result.get("device_relevance_score", 0.3)
        if not isinstance(device_relevance, (int, float)) or device_relevance < 0 or device_relevance > 1:
            result["device_relevance_score"] = 0.3
        else:
            result["device_relevance_score"] = float(device_relevance)

        # Consistency clamp: relevance can't wildly exceed device relevance
        device_rel = result["device_relevance_score"]
        if device_rel < 0.3 and result["relevance_score"] > 0.5:
            result["relevance_score"] = min(result["relevance_score"], device_rel + 0.2)

        # Validate emotion
        if result.get("emotion") not in EMOTION_VALUES:
            result["emotion"] = "confusion"

        # Validate intent
        if result.get("intent") not in INTENT_VALUES:
            result["intent"] = "general_question"

        # Validate sentiment_intensity
        intensity = result.get("sentiment_intensity", 3)
        if not isinstance(intensity, int) or intensity < 1 or intensity > 5:
            result["sentiment_intensity"] = 3
        else:
            result["sentiment_intensity"] = intensity

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return {
            "category": "other",
            "sentiment": "neutral",
            "keywords": [],
            "product_mentions": [],
            "relevance_score": 0.5,
            "device_relevance_score": 0.3,
            "emotion": "confusion",
            "intent": "general_question",
            "sentiment_intensity": 3,
        }
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise


def backfill_classifications(batch_size: int = 50, force: bool = False, after_id: str = None) -> dict:
    """Backfill classifications for items.

    By default, only classifies items with NULL category. When force=True,
    re-classifies ALL items (uses after_id for pagination).

    Args:
        batch_size: Number of items to process per run
        force: If True, re-classify ALL items (not just NULL category)
        after_id: Process items with id > this value (for pagination in force mode)

    Returns:
        Dict with stats: {processed: int, failed: int, last_id: str}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "failed": 0, "last_id": None}

    # Build query
    query = client.table("social_items") \
        .select("id, title, content, question_content") \
        .order("id") \
        .limit(batch_size)

    if not force:
        query = query.is_("category", "null")

    if after_id:
        query = query.gt("id", after_id)

    result = query.execute()

    if not result.data:
        logger.info("No items to classify")
        return stats

    items = result.data
    logger.info(f"Processing {len(items)} items for classification")

    for item in items:
        try:
            title = item.get("title", "")
            question_content = item.get("question_content")
            content = item.get("content", "")

            # Prefer question_content over content when available
            if question_content:
                text = f"Frage: {title}\n\n{question_content}\n\n"
            else:
                text = f"{title}\n\n{content}"

            classification = classify_item(
                content=text,
                title=""
            )

            client.table("social_items") \
                .update({
                    "category": classification["category"],
                    "sentiment": classification["sentiment"],
                    "keywords": classification["keywords"],
                    "product_mentions": classification["product_mentions"],
                    "relevance_score": classification["relevance_score"],
                    "device_relevance_score": classification["device_relevance_score"],
                    "emotion": classification["emotion"],
                    "intent": classification["intent"],
                    "sentiment_intensity": classification["sentiment_intensity"],
                }) \
                .eq("id", item["id"]) \
                .execute()

            stats["processed"] += 1
            logger.debug(f"Classified item {item['id']}: {classification['category']}")

            # Rate limiting - Gemini free tier is 60 RPM
            time.sleep(1.1)

        except Exception as e:
            logger.error(f"Failed to classify item {item['id']}: {e}")
            stats["failed"] += 1

    if items:
        stats["last_id"] = items[-1]["id"]

    logger.info(f"Classification complete: {stats}")
    return stats
