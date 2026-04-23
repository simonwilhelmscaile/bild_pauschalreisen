"""Full re-classification pipeline using direct function calls.

Runs classifications → journey-stages → deep-insights on all items.
Handles rate limiting with exponential backoff.

Usage: python run_reclassify.py [--phase 1|2|3] [--batch 10] [--after-id UUID]
"""
import os
import sys
import time
import logging
import argparse

# Setup — ensure project root is on sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
os.chdir(_project_root)
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("reclassify.log"),
    ],
)
logger = logging.getLogger(__name__)

from db.client import get_beurer_supabase
from classification import classify_item

# Import the Gemini client to check model
from services.gemini import CLASSIFICATION_MODEL
logger.info(f"Using model: {CLASSIFICATION_MODEL}")

DELAY = 1.5  # seconds between API calls (Flash handles 60 RPM)
MAX_RETRIES = 3


def run_classifications(batch_size: int, after_id: str = None):
    """Phase 1: Re-classify all items with emotion/intent/intensity."""
    client = get_beurer_supabase()
    total = 0
    failed = 0
    current_after = after_id

    while True:
        query = client.table("social_items") \
            .select("id, title, content, question_content") \
            .order("id") \
            .limit(batch_size)

        if current_after:
            query = query.gt("id", current_after)

        result = query.execute()
        if not result.data:
            break

        items = result.data
        logger.info(f"Classification batch: {len(items)} items (after {current_after or 'start'})")

        for item in items:
            title = item.get("title", "")
            qc = item.get("question_content")
            content = item.get("content", "")
            text = f"Frage: {title}\n\n{qc}" if qc else f"{title}\n\n{content}"

            for attempt in range(MAX_RETRIES):
                try:
                    classification = classify_item(content=text, title="")
                    client.table("social_items").update({
                        "category": classification["category"],
                        "sentiment": classification["sentiment"],
                        "keywords": classification["keywords"],
                        "product_mentions": classification["product_mentions"],
                        "relevance_score": classification["relevance_score"],
                        "device_relevance_score": classification["device_relevance_score"],
                        "emotion": classification["emotion"],
                        "intent": classification["intent"],
                        "sentiment_intensity": classification["sentiment_intensity"],
                    }).eq("id", item["id"]).execute()
                    total += 1
                    break
                except Exception as e:
                    wait = DELAY * (2 ** attempt)
                    logger.warning(f"Attempt {attempt+1} failed for {item['id']}: {e}. Waiting {wait}s")
                    time.sleep(wait)
                    if attempt == MAX_RETRIES - 1:
                        logger.error(f"FAILED: {item['id']}")
                        failed += 1

            time.sleep(DELAY)

        current_after = items[-1]["id"]
        logger.info(f"Progress: {total} classified, {failed} failed, last_id={current_after[:12]}")
        sys.stdout.flush()

    logger.info(f"=== Classifications done: {total} processed, {failed} failed ===")
    return total, failed


def run_journey_stages(batch_size: int, after_id: str = None):
    """Phase 2: Re-classify journey stages."""
    from classification import classify_journey_stage
    client = get_beurer_supabase()
    total = 0
    failed = 0
    current_after = after_id

    while True:
        query = client.table("social_items") \
            .select("id, title, content, question_content, category") \
            .order("id") \
            .limit(batch_size)

        if current_after:
            query = query.gt("id", current_after)

        result = query.execute()
        if not result.data:
            break

        items = result.data
        logger.info(f"Journey batch: {len(items)} items (after {current_after or 'start'})")

        for item in items:
            title = item.get("title", "")
            qc = item.get("question_content")
            content = item.get("content", "")
            text = f"Frage: {title}\n\n{qc}" if qc else f"{title}\n\n{content}"

            for attempt in range(MAX_RETRIES):
                try:
                    result_data = classify_journey_stage(content=text)
                    update = {}
                    if result_data.get("journey_stage"):
                        update["journey_stage"] = result_data["journey_stage"]
                    if result_data.get("pain_category"):
                        update["pain_category"] = result_data["pain_category"]
                    if result_data.get("solutions_mentioned"):
                        update["solutions_mentioned"] = result_data["solutions_mentioned"]
                    if result_data.get("beurer_opportunity"):
                        update["beurer_opportunity"] = result_data["beurer_opportunity"]
                    if update:
                        client.table("social_items").update(update).eq("id", item["id"]).execute()
                    total += 1
                    break
                except Exception as e:
                    wait = DELAY * (2 ** attempt)
                    logger.warning(f"Attempt {attempt+1} failed for {item['id']}: {e}. Waiting {wait}s")
                    time.sleep(wait)
                    if attempt == MAX_RETRIES - 1:
                        logger.error(f"FAILED: {item['id']}")
                        failed += 1

            time.sleep(DELAY)

        current_after = items[-1]["id"]
        logger.info(f"Progress: {total} journey-classified, {failed} failed, last_id={current_after[:12]}")
        sys.stdout.flush()

    logger.info(f"=== Journey stages done: {total} processed, {failed} failed ===")
    return total, failed


def run_deep_insights(batch_size: int, after_id: str = None):
    """Phase 3: Re-classify deep insights + extract aspects."""
    from classification import classify_deep_insights
    client = get_beurer_supabase()
    total = 0
    failed = 0
    aspects_saved = 0
    current_after = after_id

    while True:
        query = client.table("social_items") \
            .select("id, title, content, question_content, category, sentiment") \
            .order("id") \
            .limit(batch_size)

        if current_after:
            query = query.gt("id", current_after)

        result = query.execute()
        if not result.data:
            break

        items = result.data
        logger.info(f"Deep insights batch: {len(items)} items (after {current_after or 'start'})")

        for item in items:
            title = item.get("title", "")
            qc = item.get("question_content")
            content = item.get("content", "")
            text = f"Frage: {title}\n\n{qc}" if qc else f"{title}\n\n{content}"

            for attempt in range(MAX_RETRIES):
                try:
                    result_data = classify_deep_insights(
                        content=text,
                        category=item.get("category", "other"),
                    )

                    # Update deep insight columns
                    update = {}
                    for field in ["pain_location", "pain_severity", "pain_duration",
                                  "bp_concern_type", "bp_severity", "coping_strategies",
                                  "medications_mentioned", "life_situation",
                                  "solution_frustrations", "negative_root_cause",
                                  "key_insight", "content_opportunity", "bridge_moment"]:
                        if result_data.get(field) is not None:
                            update[field] = result_data[field]

                    if update:
                        client.table("social_items").update(update).eq("id", item["id"]).execute()

                    # Save aspects
                    aspects = result_data.get("aspects", [])
                    if aspects:
                        from db.client import save_item_aspects
                        count = save_item_aspects(client, item["id"], aspects)
                        aspects_saved += count

                    total += 1
                    break
                except Exception as e:
                    wait = DELAY * (2 ** attempt)
                    logger.warning(f"Attempt {attempt+1} failed for {item['id']}: {e}. Waiting {wait}s")
                    time.sleep(wait)
                    if attempt == MAX_RETRIES - 1:
                        logger.error(f"FAILED: {item['id']}")
                        failed += 1

            time.sleep(DELAY)

        current_after = items[-1]["id"]
        logger.info(f"Progress: {total} deep-insights, {failed} failed, {aspects_saved} aspects, last_id={current_after[:12]}")
        sys.stdout.flush()

    logger.info(f"=== Deep insights done: {total} processed, {failed} failed, {aspects_saved} aspects ===")
    return total, failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, default=0, help="Run specific phase (1/2/3) or 0 for all")
    parser.add_argument("--batch", type=int, default=10, help="Batch size")
    parser.add_argument("--after-id", type=str, default=None, help="Resume after this UUID")
    args = parser.parse_args()

    t0 = time.time()
    logger.info(f"Starting re-classification (phase={args.phase or 'all'}, batch={args.batch})")

    if args.phase in (0, 1):
        run_classifications(args.batch, args.after_id if args.phase == 1 else None)
    if args.phase in (0, 2):
        run_journey_stages(args.batch, args.after_id if args.phase == 2 else None)
    if args.phase in (0, 3):
        run_deep_insights(args.batch, args.after_id if args.phase == 3 else None)

    elapsed = time.time() - t0
    logger.info(f"Total time: {elapsed/60:.1f} minutes")
