# Design: Beurer Lifestyle-Informed Hero Image Generation

**Date:** 2026-04-13
**Status:** Approved

## Overview

Enhance the existing hero image generation by adding a library of LLM-generated descriptions of real Beurer lifestyle photography. These descriptions are used at generation time to (1) select the most relevant visual reference for a given article and (2) enrich the Imagen prompt with authentic Beurer visual style details — lighting, colors, composition, mood.

No API changes; the existing `generate_images()` path is preserved. The `edit_image` / `StyleReferenceImage` API is not used — descriptions alone drive the style.

## Background

The current system generates hero images via Google Imagen 4.0 (`generate_images()`) using theme-specific scene prompts. The results are generic lifestyle photography that doesn't match Beurer's actual brand photography style. Beurer has ~67 professional product/lifestyle photos, of which ~20 are pure lifestyle (no visible product) covering pain, yoga, wellness, sleep, social, and exercise scenes.

## Approach

1. Feed each lifestyle image to Gemini vision to produce a structured description
2. Store descriptions in a JSON file in the repo
3. At generation time: detect theme → keyword-match the best lifestyle image description → weave its visual details into the Imagen prompt
4. Generate with the existing `generate_images()` API — no new endpoints, no `edit_image`

## Components

### 1. One-time setup: describe lifestyle images

- Extract the ~20 lifestyle-only images from `C:\Users\yousi\Downloads\assets_download.zip`
- Filter out product-in-use photos (those with model prefixes like `bm27-use-`, `bc54-use-`, `em50-use-`, etc.)
- Keep only `lifestyle-*` prefixed images
- Feed each to Gemini vision (`gemini-2.5-pro` or `gemini-2.0-flash`) to produce a structured description
- Save as `blog/stage2/lifestyle_images.json`
- Upload the raw images to Supabase Storage under `blog-images/lifestyle/` for future reference

### 2. Description schema

Each entry in `lifestyle_images.json`:

```json
{
  "filename": "lifestyle-female-yoga-healthy-6918-beurer.jpg",
  "themes": ["tens_ems", "rueckenschmerzen", "default"],
  "scene": "Woman in flowing yoga pose on mat in bright modern living room",
  "mood": "calm, focused, empowered, peaceful",
  "lighting": "Soft natural daylight from large windows, even diffused light, no harsh shadows",
  "colors": "Warm whites, light wood tones, soft sage green from plants, neutral grays",
  "composition": "Medium-wide shot, slightly low angle, subject centered, shallow depth of field on background",
  "setting": "Spacious modern living room, minimal Scandinavian furniture, indoor plants"
}
```

Fields:

| Field | Purpose | Used for |
|-------|---------|----------|
| `filename` | Image file reference in Supabase Storage | Lookup / traceability |
| `themes` | Which article themes this image matches | Selection (primary filter) |
| `scene` | What's happening in the image | Selection (keyword scoring) |
| `mood` | Emotional tone | Selection (keyword scoring) + prompt enrichment |
| `lighting` | Lighting description | Prompt enrichment |
| `colors` | Dominant color palette | Prompt enrichment |
| `composition` | Framing and camera details | Prompt enrichment |
| `setting` | Location/environment | Selection (keyword scoring) + prompt enrichment |

### 3. Selection logic

New function `select_lifestyle_reference(article, theme)` in `image_prompts.py`:

1. Filter `lifestyle_images.json` entries where `theme` is in the entry's `themes` list
2. Score each candidate by keyword overlap:
   - Tokenize article headline + keyword into words (lowercased, stripped of common German stopwords)
   - Count how many tokens appear in the candidate's `scene` + `mood` + `setting` (concatenated, lowercased)
3. Return the top-scoring description dict
4. If tied, use the same headline-hash approach as current scene selection for deterministic variety
5. If no theme matches at all, return `None` (prompt falls back to existing behavior without style enrichment)

### 4. Prompt enrichment

Modify `build_beurer_hero_prompt()` to accept an optional `style_ref` parameter:

```python
def build_beurer_hero_prompt(article: dict, style_ref: dict | None = None) -> str:
```

When `style_ref` is provided, append to the existing prompt:

```
Visual style reference — match this photography aesthetic:
Lighting: {style_ref['lighting']}.
Color palette: {style_ref['colors']}.
Composition: {style_ref['composition']}.
Setting atmosphere: {style_ref['setting']}.
```

The existing scene descriptions, atmosphere, negative prompts (no devices, no text, etc.) all stay unchanged. The style reference adds specificity, it doesn't replace the core prompt.

### 5. Call chain changes

**`image_prompts.py`:**
- Add `load_lifestyle_images()` — reads and caches `lifestyle_images.json`
- Add `select_lifestyle_reference(article, theme)` — selection logic
- Modify `build_beurer_hero_prompt(article, style_ref=None)` — accepts optional style reference

**`article_service.py` (`_generate_article_images`):**
```python
theme = detect_theme(article)
style_ref = select_lifestyle_reference(article, theme)
prompt = build_beurer_hero_prompt(article, style_ref=style_ref)
# ... rest unchanged
```

**`router.py` (`generate_hero_image` endpoint):**
```python
theme = detect_theme(article_json)
style_ref = select_lifestyle_reference(article_json, theme)
prompt = build_beurer_hero_prompt(article_json, style_ref=style_ref)
# ... rest unchanged
```

### 6. Unchanged components

- `ImageCreator` / `generate_image()` — same API, same model, same upload flow
- `detect_theme()` — same keyword matching
- Product image mapping (Track 2) — untouched
- Dashboard endpoints — same interface
- Batch regeneration — same flow, just better prompts

## Data flow

```
detect_theme(article)
    → "rueckenschmerzen"
    ↓
select_lifestyle_reference(article, "rueckenschmerzen")
    → { filename: "lifestyle-female-pain-kitchen-back-770-beurer.jpg",
        lighting: "Warm natural light from kitchen window...",
        colors: "Neutral whites, warm wood, soft earth tones...", ... }
    ↓
build_beurer_hero_prompt(article, style_ref=ref)
    → existing prompt + "Visual style reference — match this photography aesthetic: ..."
    ↓
generate_images()  ← same as today, just a richer prompt
    ↓
WebP conversion → Supabase upload → URL into article_json
```

## File changes summary

| File | Change |
|------|--------|
| `blog/stage2/lifestyle_images.json` | **New** — structured lifestyle image descriptions (~20 entries) |
| `blog/stage2/image_prompts.py` | Add `load_lifestyle_images()`, `select_lifestyle_reference()`. Modify `build_beurer_hero_prompt()` signature to accept `style_ref`. |
| `blog/article_service.py` | Call `select_lifestyle_reference()` before `build_beurer_hero_prompt()`, pass result through |
| `blog/router.py` | Same change in `generate_hero_image` endpoint |
| `scripts/describe_lifestyle_images.py` | **New** (one-time) — extracts lifestyle images from zip, describes via Gemini vision, outputs JSON |

## One-time setup script

`scripts/describe_lifestyle_images.py`:

1. Opens `assets_download.zip`
2. Filters to `lifestyle-*` filenames only
3. For each image:
   - Reads bytes from zip
   - Sends to Gemini vision with a structured prompt requesting: scene, mood, lighting, colors, composition, setting, and suggested theme tags
4. Collects all descriptions into a list
5. Writes `blog/stage2/lifestyle_images.json`
6. Optionally uploads raw images to Supabase Storage `blog-images/lifestyle/`

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Style descriptions don't improve Imagen output noticeably | Test with a few articles before batch regeneration. Descriptions can be tuned. |
| Keyword overlap gives poor matches | With only ~20 images and theme pre-filtering, candidates are 2-5 per theme. Even random selection within the theme would be reasonable. |
| Gemini vision produces inaccurate descriptions | Quick manual review of the generated JSON before committing. One-time cost. |
| `lifestyle_images.json` grows stale if new photos are added | Simple: re-run the description script with new images. JSON is append-only. |
