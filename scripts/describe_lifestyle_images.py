"""
One-time script: describe Beurer lifestyle images using Gemini vision.

Reads lifestyle-* images from assets_download.zip, sends each to Gemini 2.0 Flash
for a structured description, and writes blog/stage2/lifestyle_images.json.
Optionally uploads raw images to Supabase Storage (blog-images/lifestyle/).

Usage:
    python scripts/describe_lifestyle_images.py
    python scripts/describe_lifestyle_images.py --upload   # also upload to Supabase
    python scripts/describe_lifestyle_images.py --dry-run  # print filenames only
"""

import argparse
import json
import logging
import os
import sys
import time
import zipfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ZIP_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "assets_download.zip")
OUTPUT_PATH = os.path.join(Path(__file__).resolve().parent.parent, "blog", "stage2", "lifestyle_images.json")
SUPABASE_BUCKET = "blog-images"
SUPABASE_FOLDER = "lifestyle"

# Available themes (from image_prompts.py IMAGE_THEMES keys)
THEMES = [
    "blutdruck", "blutdruck_messen", "tens_ems", "rueckenschmerzen",
    "regelschmerzen", "infrarot", "vergleich", "tutorial", "default",
]

VISION_PROMPT = f"""Analyze this Beurer lifestyle photograph and provide a structured description in JSON format.

This image is part of Beurer's professional lifestyle photography library used for health magazine articles.
It does NOT show any Beurer products — it's a pure mood/lifestyle/atmosphere image.

Return ONLY valid JSON with these exact fields:

{{
  "scene": "One sentence describing what is happening in the image (e.g. 'Woman doing gentle yoga stretches on a mat in a bright modern living room')",
  "mood": "Comma-separated emotional tones (e.g. 'calm, focused, peaceful, empowered')",
  "lighting": "Describe the lighting in detail (e.g. 'Soft natural daylight from large windows, warm golden tones, no harsh shadows')",
  "colors": "Dominant color palette (e.g. 'Warm whites, light wood tones, soft sage green from plants, neutral grays')",
  "composition": "Camera/framing details (e.g. 'Medium-wide shot, eye-level, subject centered, shallow depth of field')",
  "setting": "Location/environment (e.g. 'Modern minimalist living room with Scandinavian furniture, indoor plants')",
  "themes": ["list", "of", "matching", "themes"]
}}

For the "themes" field, pick ALL that apply from this list: {json.dumps(THEMES)}

Theme guidance:
- "blutdruck" / "blutdruck_messen": calm wellness, morning routines, health awareness, relaxation at home
- "tens_ems": exercise, yoga, stretching, active recovery, fitness, sport
- "rueckenschmerzen": back/neck pain, stretching, relief, posture, discomfort scenes
- "regelschmerzen": feminine comfort, cozy warmth, self-care, gentle relief
- "infrarot": warmth, spa-like, therapeutic calm, warm lighting
- "vergleich": thoughtful evaluation, reading, comparing, research
- "tutorial": learning, step-by-step, organized workspace
- "default": general health/wellness (assign this if the image fits broadly)

Return ONLY the JSON object, no markdown fencing, no explanation."""


def get_lifestyle_filenames(zip_path: str) -> list[str]:
    """Extract lifestyle-* filenames from the zip."""
    with zipfile.ZipFile(zip_path) as z:
        return sorted(n for n in z.namelist() if n.startswith("lifestyle-") and n.endswith(".jpg"))


def describe_image(image_bytes: bytes, filename: str) -> dict | None:
    """Send image to Gemini vision and parse the structured description."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    try:
        response = model.generate_content(
            [
                {"mime_type": "image/jpeg", "data": image_bytes},
                VISION_PROMPT,
            ]
        )

        text = response.text.strip()
        # Strip markdown fencing if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[: text.rfind("```")]
            text = text.strip()

        desc = json.loads(text)

        # Validate required fields
        required = ["scene", "mood", "lighting", "colors", "composition", "setting", "themes"]
        for field in required:
            if field not in desc:
                logger.warning(f"{filename}: missing field '{field}' in response")
                return None

        # Validate themes are from allowed list
        desc["themes"] = [t for t in desc["themes"] if t in THEMES]
        if not desc["themes"]:
            desc["themes"] = ["default"]

        return desc

    except json.JSONDecodeError as e:
        logger.error(f"{filename}: failed to parse JSON: {e}\nRaw: {text[:200]}")
        return None
    except Exception as e:
        logger.error(f"{filename}: Gemini vision error: {e}")
        return None


def upload_to_supabase(image_bytes: bytes, filename: str) -> str | None:
    """Upload a lifestyle image to Supabase Storage."""
    try:
        from db.client import get_beurer_supabase

        sb = get_beurer_supabase()
        filepath = f"{SUPABASE_FOLDER}/{filename}"
        sb.storage.from_(SUPABASE_BUCKET).upload(
            path=filepath,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        url = sb.storage.from_(SUPABASE_BUCKET).get_public_url(filepath)
        return url
    except Exception as e:
        logger.error(f"Supabase upload failed for {filename}: {e}")
        return None


def main():
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="Describe Beurer lifestyle images via Gemini vision")
    parser.add_argument("--upload", action="store_true", help="Also upload images to Supabase Storage")
    parser.add_argument("--dry-run", action="store_true", help="Print filenames only, no API calls")
    parser.add_argument("--zip", default=ZIP_PATH, help=f"Path to assets zip (default: {ZIP_PATH})")
    args = parser.parse_args()

    if not os.path.exists(args.zip):
        logger.error(f"Zip file not found: {args.zip}")
        sys.exit(1)

    filenames = get_lifestyle_filenames(args.zip)
    logger.info(f"Found {len(filenames)} lifestyle images")

    if args.dry_run:
        for f in filenames:
            print(f)
        return

    results = []

    with zipfile.ZipFile(args.zip) as z:
        for i, filename in enumerate(filenames):
            logger.info(f"[{i + 1}/{len(filenames)}] Describing: {filename}")

            image_bytes = z.read(filename)

            # Describe via Gemini vision
            desc = describe_image(image_bytes, filename)
            if not desc:
                logger.warning(f"Skipping {filename} — description failed")
                continue

            entry = {"filename": filename, **desc}
            results.append(entry)

            # Upload to Supabase if requested
            if args.upload:
                url = upload_to_supabase(image_bytes, filename)
                if url:
                    logger.info(f"  Uploaded: {url[:80]}...")

            # Rate limit: Gemini free tier is 60 RPM
            if i < len(filenames) - 1:
                time.sleep(1.5)

    # Write JSON
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(results)} descriptions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
