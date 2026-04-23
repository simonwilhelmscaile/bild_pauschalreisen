"""
Beurer Hero Image Prompts — theme detection and Imagen prompt building.

Generates atmospheric/mood hero images per article topic.
Product cutout images are handled separately (Track 2).
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Beurer brand guidelines
BEURER_BRAND = {
    "primary_color": "#C60050",   # Beurer Magenta
    "accent_color": "#003366",    # Deep blue
    "secondary": "#666666",       # Neutral gray
}

# Theme-specific style guidelines for atmospheric hero images.
# IMPORTANT: No devices, products, or medical equipment in hero images.
# Hero images are pure mood/lifestyle/atmosphere — products are shown
# separately as real cutouts inline (Track 2).
_NO_PRODUCTS = "text, logos, watermarks, medical devices, health devices, electronics, screens, buttons, cables, cuffs, electrodes, pads, lamps, infrared lamps, heat lamps, light therapy devices, any device or product"
IMAGE_THEMES = {
    "blutdruck": {
        "scenes": [
            "Person relaxing at a bright kitchen table with morning tea and an open journal, smiling, calm morning light from a window",
            "Middle-aged couple walking hand in hand through a sunny park with autumn leaves, healthy active lifestyle",
            "Woman sitting on a balcony at sunrise, eyes closed, breathing deeply, green plants around her, serene morning",
            "Man preparing a colorful Mediterranean salad in a modern bright kitchen, fresh vegetables, natural window light",
            "Senior woman doing gentle tai chi in a garden at golden hour, flowing movements, peaceful expression",
        ],
        "atmosphere": "Calm, health awareness, peaceful morning routine, self-care",
        "composition": "Lifestyle stock photo style, warm and inviting",
        "avoid": _NO_PRODUCTS,
    },
    "blutdruck_messen": {
        "scenes": [
            "Smiling person sitting comfortably at home with a cup of herbal tea, notebook on the table, bright natural daylight",
            "Person at a tidy desk writing in a health diary, morning sunlight streaming through blinds, calm focused expression",
            "Couple having breakfast together at a wooden table, fruit and juice, warm domestic morning scene",
            "Person sitting in a cozy reading nook with a book about wellness, soft lamp light, relaxed posture",
            "Woman in comfortable home clothes stretching by a window, morning routine, bright airy room",
        ],
        "atmosphere": "Daily health routine, self-care, mindful wellbeing",
        "composition": "Lifestyle stock photo, eye-level or slightly above",
        "avoid": _NO_PRODUCTS,
    },
    "tens_ems": {
        "scenes": [
            "Person smiling after a yoga or stretching session, sitting on a yoga mat with a towel and water bottle nearby, soft blue-white lighting",
            "Athletic woman resting on a gym bench looking relieved and content, water bottle in hand, modern fitness studio",
            "Man doing gentle stretches on a foam roller in a bright living room, relaxed expression, clean minimal interior",
            "Person walking confidently through a park, athletic wear, morning dew on grass, feeling energized",
            "Woman sitting cross-legged on a meditation cushion, hands on knees, soft smile, clean bright studio",
        ],
        "atmosphere": "Pain relief, active recovery, feeling good after therapy",
        "composition": "Lifestyle stock photo, clean wellness aesthetic",
        "avoid": _NO_PRODUCTS,
    },
    "rueckenschmerzen": {
        "scenes": [
            "Person stretching their back gently, looking relieved and happy, yoga mat and foam roller nearby, calming blue-purple ambient lighting",
            "Man standing tall with good posture by a large window, hands on hips, confident smile, bright natural light",
            "Woman doing a gentle cat-cow yoga pose on a mat in a bright modern living room, peaceful expression",
            "Person enjoying a walk through a forest path, sunlight filtering through trees, moving freely and happily",
            "Couple doing partner stretches together in a bright studio, laughing, supportive body language",
        ],
        "atmosphere": "Relief, hope, pathway to wellness, active recovery",
        "composition": "Lifestyle stock photo, clean wellness aesthetic",
        "avoid": _NO_PRODUCTS + ", X-rays, graphic medical imagery, pain expressions",
    },
    "regelschmerzen": {
        "scenes": [
            "Woman relaxing comfortably on a sofa with a soft blanket and hot water bottle, warm smile, chamomile tea nearby, warm-toned lighting",
            "Woman in cozy sweater reading a book by a rain-streaked window, candles lit, warm golden tones",
            "Two women laughing together on a couch, cozy blankets, hot chocolate, warm intimate living room scene",
            "Woman doing gentle yoga in soft morning light, comfortable clothes, peaceful bedroom setting",
            "Woman wrapped in a soft robe enjoying a warm bath setting, candles and plants, spa-like bathroom",
        ],
        "atmosphere": "Comfort, care, gentle relief, feminine wellness, cozy warmth",
        "composition": "Warm lifestyle photography, soft focus, cozy setting",
        "avoid": _NO_PRODUCTS,
    },
    "infrarot": {
        "scenes": [
            "Woman wrapped in a cozy knit blanket on a sofa, holding a warm mug of herbal tea, content smile, soft cushions around her",
            "Person sitting comfortably on a bed propped up with pillows, warm knit sweater, holding a tissue and a warm drink, gentle smile, cozy bedroom",
            "Woman sitting cross-legged on a yoga mat beside a window with golden hour sunlight streaming in, peaceful expression",
            "Person wrapped in a bathrobe relaxing on a daybed, a book resting on their lap, serene indoor setting with plants",
            "Couple sharing a blanket on a couch, mugs of tea, smiling at each other, cozy living room with warm afternoon light from a window",
        ],
        "atmosphere": "Cozy comfort, gentle wellness, peaceful relaxation at home",
        "composition": "Warm color grading, soft focus background",
        "avoid": _NO_PRODUCTS + ", any visible lamp or light fixture or light source, ceiling lights",
    },
    "vergleich": {
        "scenes": [
            "Person thoughtfully reading or comparing options at a clean desk, notebook and coffee cup, bright natural light, focused but relaxed expression",
            "Person browsing a tablet while sitting in a modern cafe, bright window light, contemplative expression",
            "Two people having a friendly discussion over coffee, pointing at a magazine together, bright airy setting",
            "Person with glasses studying a consumer guide at a library table, organized notes, natural daylight",
            "Woman making a checklist at a standing desk in a modern home office, plants and natural light",
        ],
        "atmosphere": "Thoughtful evaluation, informed choice, clarity",
        "composition": "Lifestyle stock photo, clean bright setting",
        "avoid": _NO_PRODUCTS,
    },
    "tutorial": {
        "scenes": [
            "Person following along with instructions at a clean desk, notebook open, markers and sticky notes, smiling, good lighting",
            "Hands arranging colorful step-by-step cards on a white table, organized workspace, bright overhead light",
            "Person watching a tutorial on a laptop at a kitchen counter, taking notes, engaged expression, bright room",
            "Teacher-like figure explaining something with hand gestures, whiteboard behind them, friendly approachable look",
            "Person unpacking a new purchase at a clean desk, instruction booklet open, excited curious expression",
        ],
        "atmosphere": "Learning, clarity, step-by-step guidance, organized",
        "composition": "Lifestyle stock photo, bright and clear",
        "avoid": _NO_PRODUCTS,
    },
    "default": {
        "scenes": [
            "Happy person enjoying a healthy morning routine, herbal tea, journal, fresh greenery, soft natural lighting",
            "Person jogging on a scenic trail at sunrise, misty background, energetic and healthy",
            "Family preparing a healthy meal together in a bright modern kitchen, laughter, natural light",
            "Person meditating on a hilltop at dawn, panoramic view, peaceful solitude",
            "Woman tending to plants on a sunny balcony garden, watering can, fresh herbs, happy expression",
        ],
        "atmosphere": "Health awareness, modern self-care, calm, positive",
        "composition": "Clean lifestyle stock photography, warm and inviting",
        "avoid": _NO_PRODUCTS,
    },
}

# Theme keyword matching — order matters (first match wins)
_THEME_KEYWORDS = [
    ("regelschmerzen", ["regelschmerz", "menstruation", "em 50", "em 55", "endometriose"]),
    ("rueckenschmerzen", ["ruecken", "nacken", "bandscheibe", "schmerz"]),
    ("tens_ems", ["tens", "ems", "em 59", "em 89", "elektroden", "elektrische"]),
    ("infrarot", ["infrarot", "il 50", "il 60", "waerme"]),
    ("blutdruck_messen", ["messen", "anleitung", "richtig", "fehler", "tagebuch"]),
    ("blutdruck", ["blutdruck", "bm ", "bc ", "hypertonie", "bluthochdruck", "dhl"]),
    ("vergleich", ["vergleich", "vs", "test", "unterschied"]),
    ("tutorial", ["tutorial", "anleitung", "einrichten", "funktion", "laedt nicht"]),
]

# ── Product image mapping (Track 2: inline product cutouts) ──

# Supabase Storage bucket and folder for product images
_PRODUCT_BUCKET = "blog-images"
_PRODUCT_FOLDER = "products"


def _get_product_image_url(filename: str) -> str:
    """Build Supabase Storage public URL for a product image."""
    try:
        from db.client import get_beurer_supabase
        sb = get_beurer_supabase()
        return sb.storage.from_(_PRODUCT_BUCKET).get_public_url(f"{_PRODUCT_FOLDER}/{filename}")
    except Exception as e:
        logger.warning(f"Could not build product image URL for {filename}: {e}")
        return ""

# Product model → image filename mapping
PRODUCT_IMAGE_MAP = {
    # Blood pressure monitors (Oberarm)
    "bm 25": "bm25-main-product-v01a-beurer.jpg",
    "bm 27": "bm27-main-product-side-left-v00-beurer.jpg",
    "bm27": "bm27-main-product-side-left-v00-beurer.jpg",
    "bm 27 usb": "bm27-usb-c-main-product-side-left-v00b-beurer.jpg",
    "bm 53": "bm53-main-product-side-beurer.jpg",
    "bm 54": "bm54-bluetooth-main-product-side-left-v00-beurer.jpg",
    "bm54": "bm54-bluetooth-main-product-side-left-v00-beurer.jpg",
    "bm 59": "bm59-main-product-side-left-cuff-beurer_bw.jpg",
    "bm 64": "bm64-main-product-beurer.jpg",
    "bm 81": "BM81-Side.jpg",
    "bm 96": "BM96-main-product_Set-Stick-Cuff-ECG.jpg",
    # Blood pressure monitors (Handgelenk)
    "bc 27": "bc27-main-product-side-cuff-v01-beurer.jpg",
    "bc 54": "bc54-bluetooth-main-product-side-left-v00-beurer.jpg",
    # TENS/EMS devices
    "em 50": "EM50-Front_WomansLife.jpg",
    "em 55": "em55-main-product-front-v01b-beurer.jpg",
    "em 59": "EM59-Front-Set_NEU_Nov_2021_OH.jpg",
    "em59": "EM59-Front-Set_NEU_Nov_2021_OH.jpg",
    "em 89": "EM89-HEAT-product-set-front-v00-beurer.jpg",
    # Infrared lamps
    "il 50": "il50-main-product-side-left-v00-beurer.jpg",
    "il 60": "il60-main-product-v01d-beurer_01.jpg",
}


def detect_theme(article: dict) -> str:
    """
    Detect the best matching Beurer health theme for an article.

    Checks headline and primary_keyword against theme keyword lists.
    Returns theme name string (e.g. 'blutdruck', 'tens_ems', 'default').
    """
    headline = (article.get("Headline", "") or article.get("headline", "") or "").lower()
    keyword = (article.get("primary_keyword", "") or article.get("keyword", "") or "").lower()
    combined = f"{headline} {keyword}"

    for theme_name, keywords in _THEME_KEYWORDS:
        if any(kw in combined for kw in keywords):
            return theme_name

    return "default"


# ── Lifestyle image reference selection ──

_lifestyle_images_cache: list[dict] | None = None

# Common German stopwords to skip in keyword matching
_STOPWORDS = frozenset(
    "der die das ein eine einer einem einen und oder aber nicht mit von zu für"
    " auf an in ist sind war hat wie was auch nach bei aus über zum zur im".split()
)


def load_lifestyle_images() -> list[dict]:
    """Load and cache lifestyle image descriptions from JSON."""
    global _lifestyle_images_cache
    if _lifestyle_images_cache is not None:
        return _lifestyle_images_cache

    json_path = Path(__file__).parent / "lifestyle_images.json"
    if not json_path.exists():
        logger.warning(f"Lifestyle images JSON not found: {json_path}")
        _lifestyle_images_cache = []
        return _lifestyle_images_cache

    with open(json_path, "r", encoding="utf-8") as f:
        _lifestyle_images_cache = json.load(f)

    logger.info(f"Loaded {len(_lifestyle_images_cache)} lifestyle image descriptions")
    return _lifestyle_images_cache


def select_lifestyle_reference(article: dict, theme: str) -> Optional[dict]:
    """Select the best-matching lifestyle image description for an article.

    1. Filter by theme match
    2. Score by keyword overlap (article headline+keyword vs image scene+mood+setting)
    3. Break ties with headline hash for deterministic variety

    Returns the best-matching description dict, or None if no images available.
    """
    images = load_lifestyle_images()
    if not images:
        return None

    # Filter by theme
    candidates = [img for img in images if theme in img.get("themes", [])]
    if not candidates:
        # Fall back to "default" theme images
        candidates = [img for img in images if "default" in img.get("themes", [])]
    if not candidates:
        return None

    # If only one candidate, return it
    if len(candidates) == 1:
        return candidates[0]

    # Tokenize article text
    headline = (article.get("Headline", "") or article.get("headline", "") or "").lower()
    keyword = (article.get("primary_keyword", "") or article.get("keyword", "") or "").lower()
    article_tokens = set(
        w for w in f"{headline} {keyword}".split()
        if len(w) > 2 and w not in _STOPWORDS
    )

    if not article_tokens:
        # No meaningful tokens — use headline hash for deterministic pick
        topic = headline or keyword or "default"
        idx = int(hashlib.md5(topic.encode()).hexdigest(), 16) % len(candidates)
        return candidates[idx]

    # Score each candidate by keyword overlap
    scored = []
    for img in candidates:
        img_text = f"{img.get('scene', '')} {img.get('mood', '')} {img.get('setting', '')}".lower()
        score = sum(1 for token in article_tokens if token in img_text)
        scored.append((score, img))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]

    # Collect all tied at top score
    tied = [img for score, img in scored if score == top_score]

    # Break ties with headline hash for deterministic variety
    topic = headline or keyword or "default"
    idx = int(hashlib.md5(topic.encode()).hexdigest(), 16) % len(tied)
    selected = tied[idx]

    logger.info(
        f"Selected lifestyle reference: {selected['filename']} "
        f"(score: {top_score}, candidates: {len(candidates)})"
    )
    return selected


def build_beurer_hero_prompt(article: dict, style_ref: dict | None = None) -> str:
    """
    Build an atmospheric, article-specific hero image prompt for Imagen 4.0.

    Creates mood/lifestyle scenes relevant to the article topic.
    When style_ref is provided, appends Beurer photography visual details
    (lighting, colors, composition) extracted from real lifestyle photos.
    Does NOT try to render specific products — that's Track 2 (inline images).
    """
    theme_name = detect_theme(article)
    theme = IMAGE_THEMES.get(theme_name, IMAGE_THEMES["default"])

    # Extract article-specific content for a unique image
    headline = (
        article.get("Headline", "") or article.get("headline", "") or ""
    )
    keyword = (
        article.get("primary_keyword", "") or article.get("keyword", "") or ""
    )
    article_topic = headline or keyword or "Health and wellness"

    # Pick a scene variation based on article headline hash for diversity
    scenes = theme.get("scenes", [theme.get("scene", "")])
    scene_idx = int(hashlib.md5(article_topic.encode()).hexdigest(), 16) % len(scenes)
    scene = scenes[scene_idx]

    logger.info(f"Building Beurer hero prompt — theme: {theme_name}, scene: {scene_idx + 1}/{len(scenes)}, topic: {article_topic[:60]}")

    prompt = f"""Photorealistic lifestyle photograph. {scene}. {theme['atmosphere']}.
{theme['composition']}.
Professional photography, soft natural lighting, 16:9 aspect ratio, shallow depth of field.
Clean white background tones with warm accents.
This is a raw photograph only. The image contains absolutely no text, no words, no letters, no numbers, no logos, no watermarks, no captions, no overlays, no borders, no frames, no graphic design elements, no colored bars, no gradients, no magazine layouts.
No medical devices, no health devices, no electronics, no screens, no gadgets, no products, no lamps, no infrared lamps, no heat lamps, no light therapy devices, no devices of any kind visible in the scene."""

    # Merge style reference into the prompt using an LLM for coherence
    if style_ref:
        prompt = _merge_style_into_prompt(prompt, style_ref)

    return prompt


def _merge_style_into_prompt(base_prompt: str, style_ref: dict) -> str:
    """Use Gemini to merge a base image prompt with a style reference into one coherent prompt.

    The LLM combines the scene description with the photography style (lighting, colors,
    composition) so Imagen receives a single unified direction instead of conflicting blocks.
    Falls back to the base prompt if the merge call fails.
    """
    # Only use lighting and colors from the style reference — not composition or scene
    # (composition/scene descriptions reference the original photo's subjects which
    # would contaminate the scene prompt with irrelevant people/objects)
    style_parts = []
    if style_ref.get("lighting"):
        style_parts.append(f"Lighting: {style_ref['lighting']}")
    if style_ref.get("colors"):
        style_parts.append(f"Color palette: {style_ref['colors']}")
    if not style_parts:
        return base_prompt

    style_description = ". ".join(style_parts)

    merge_instruction = f"""Rewrite this image generation prompt by integrating the photography style into it. Return ONLY the final prompt.

RULES:
- The scene, subject, people, and setting MUST stay exactly as described in the original
- ONLY change the visual aesthetics: lighting quality, color grading, color temperature
- NEVER add or remove people, animals, objects, or scene elements
- NEVER drop restrictions (lines starting with "No..." or "The image contains...")
- Do not output anything except the rewritten prompt — no intro, no explanation

ORIGINAL PROMPT:
{base_prompt}

PHOTOGRAPHY STYLE TO INTEGRATE:
{style_description}"""

    try:
        from google import genai
        import os
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=merge_instruction,
            config={"temperature": 0.3, "max_output_tokens": 1024},
        )
        merged = response.text.strip()
        if len(merged) > 100 and "no text" in merged.lower():
            logger.info(f"Style merge: successfully combined prompt ({len(base_prompt)} -> {len(merged)} chars)")
            return merged
        else:
            logger.warning(f"Style merge: LLM output too short or missing restrictions, using base prompt")
            return base_prompt
    except Exception as e:
        logger.warning(f"Style merge failed ({e}), using base prompt")
        return base_prompt


def find_product_images(article: dict) -> List[dict]:
    """
    Find matching Beurer product cutout images for an article.

    Scans article headline, keyword, product_mentions, and body sections
    for model numbers (BM 27, EM 59, IL 50, etc.).
    Returns list of dicts: [{"model": "BM 27", "filename": "bm27-...", "url": "https://..."}]
    """
    headline = (article.get("Headline", "") or article.get("headline", "") or "").lower()
    keyword = (article.get("primary_keyword", "") or article.get("keyword", "") or "").lower()
    mentions = article.get("product_mentions", []) or []
    if isinstance(mentions, str):
        mentions = [mentions]
    mentions_text = " ".join(m.lower() if isinstance(m, str) else "" for m in mentions)

    body_parts = []
    for key, val in article.items():
        if isinstance(val, str) and any(k in key.lower() for k in ["section", "intro", "content", "faq", "answer"]):
            body_parts.append(val)
    body_text = " ".join(body_parts).lower()

    primary_text = f"{headline} {keyword} {mentions_text}"
    full_text = f"{primary_text} {body_text}"

    theme = detect_theme(article)
    _THEME_MODEL_PREFIXES = {
        "blutdruck": ["bm", "bc"],
        "blutdruck_messen": ["bm", "bc"],
        "tens_ems": ["em"],
        "rueckenschmerzen": ["em"],
        "regelschmerzen": ["em"],
        "infrarot": ["il"],
    }
    preferred_prefixes = _THEME_MODEL_PREFIXES.get(theme, [])

    primary_matches = []
    theme_body_matches = []
    other_body_matches = []
    seen_files = set()

    for model_key, filename in PRODUCT_IMAGE_MAP.items():
        if filename in seen_files:
            continue
        if model_key in primary_text:
            url = _get_product_image_url(filename)
            if url:
                primary_matches.append({"model": model_key.upper(), "filename": filename, "url": url})
                seen_files.add(filename)
        elif model_key in full_text:
            url = _get_product_image_url(filename)
            if url:
                entry = {"model": model_key.upper(), "filename": filename, "url": url}
                if any(model_key.startswith(p) for p in preferred_prefixes):
                    theme_body_matches.append(entry)
                else:
                    other_body_matches.append(entry)
                seen_files.add(filename)

    matched = primary_matches + theme_body_matches + other_body_matches
    logger.info(f"Found {len(matched)} product images for article: {[m['model'] for m in matched]}")
    return matched
