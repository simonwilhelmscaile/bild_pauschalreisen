# Hero Image Library — Real-Photo Pipeline

**Date:** 2026-04-20
**Driver:** Beurer briefing 2026-04-17, item #7 — AI heroes don't meet Beurer's bar. Replace with real photos from Academy App + PostAP libraries. AI path stays wired but parked behind a feature flag.
**Scope:** Hero image selection only. Paragraph-scoped body images (briefing #6) are a follow-up.

---

## Problem

Beurer reviewed the 2026-04-14 regenerated articles and flagged AI-generated hero images as not production-ready. The Academy App package delivered 2026-04-19 contains 67 JPEGs:
- 22 `lifestyle-*` shots — already indexed in `blog/stage2/lifestyle_images.json`
- 41 `{sku}-use-*` product-use shots covering 8 SKUs: BM 27, BM 35, BM 49, BM 96, BC 54, EM 50, EM 55, EM 89
- 3 BR-range (baby, out of scope)

PostAP library (larger, product-in-use + image shots for Blutdruck + Schmerztherapie) is still pending download from https://beurer.postap.de/assets-extern-download/391ed283-5ba8-4878-a013-f6a5458e7860 and will be ingested later through the same pipeline.

## Selection algorithm

```
select_hero_image(article) → {filename, url, alt_text} | None

  primary_sku = first_sku_in_headline_or_keyword(article)

  if primary_sku:                                       # Branch A: product-in-use
    matches = library.filter(sku == primary_sku)
    if matches:
      return score_and_pick(matches, article)

  theme = detect_theme(article)                         # Branch B: mood
  matches = library.filter(type == "lifestyle" AND theme in themes)
  if matches:
    return score_and_pick(matches, article)

  return None                                           # no hero rendered
```

**Branch rule** (Q2 answer A): the switch is SKU-in-headline. If the headline or `primary_keyword` contains any alias from `PRODUCT_IMAGE_MAP`, the article is a product article and gets a product-in-use hero. Otherwise it's a mood article.

**First-SKU rule**: for articles mentioning multiple SKUs (e.g. "BM 27 vs BM 35"), find the SKU that appears earliest in reading order within the headline; if no SKU in the headline, repeat on `primary_keyword`. Matching uses `PRODUCT_IMAGE_MAP` aliases (case-insensitive, tolerates missing space: `BM27` ≡ `BM 27`). Deterministic.

**Scoring (`score_and_pick`)**: reuse the existing `select_lifestyle_reference` logic from `blog/stage2/image_prompts.py` — tokenize headline + keyword, score by overlap against each candidate's `scene + mood + setting`, break ties with `md5(headline) mod len(tied)`. Works unchanged once product-use shots are indexed in the same schema.

## Metadata schema

Extend `blog/stage2/lifestyle_images.json` to cover both lifestyle and product-use shots. Three new fields per entry:

```json
{
  "filename": "bm27-use-male-livingroom-157-beurer.jpg",
  "sku": "BM 27",
  "type": "product_use",
  "gender": "male",
  "location": "livingroom",
  "scene": "...",
  "mood": "...",
  "lighting": "...",
  "colors": "...",
  "composition": "...",
  "setting": "...",
  "themes": ["blutdruck"]
}
```

- `sku` — string (e.g. `"BM 27"`) or `null` for lifestyle shots. Space-normalized to match `PRODUCT_IMAGE_MAP` keys.
- `type` — `"lifestyle"` | `"product_use"`.
- `gender` — `"male"` | `"female"` | `null` (unparseable).
- `location` — e.g. `"kitchen"`, `"livingroom"`, `"yoga"`, `null`.
- `scene/mood/lighting/colors/composition/setting` — existing vision-captioned fields, now populated for product-use shots too.
- `themes` — seeded deterministically from SKU for product-use shots; manually tagged for lifestyle (already done).

**SKU → theme seed map:**

| SKU prefix | Theme |
|-----------|-------|
| `BM *`, `BC *` | `blutdruck` |
| `EM 50`, `EM 55` | `regelschmerzen` |
| `EM 39`, `EM 49`, `EM 59`, `EM 80`, `EM 89` | `tens_ems` |
| `IL *` | `infrarot` |

## Ingestion script — `scripts/ingest_hero_library.py`

Idempotent, rerunnable. Inputs: `--source-dir <path>`, `--dry-run`.

For each `*.jpg` in the source directory:
1. Parse filename → `filename`, `sku`, `gender`, `location`, `type`. Filename patterns:
   - `{sku}-use-{gender}[-{location}]-{id}-beurer.jpg` → `type = "product_use"`
   - `lifestyle-{context}-{id}-beurer.jpg` → `type = "lifestyle"`, `sku = null`
   - SKU prefix is matched against `PRODUCT_IMAGE_MAP` keys (case-insensitive, with/without spaces). Unknown prefix → log warning, skip.
   - Filenames with `br-range-*` → skip (out of scope).
2. If entry with same `filename` already exists in JSON → skip upload + captioning, log "already indexed."
3. Upload binary to Supabase Storage `blog-images/library/{filename}`. If exists, skip upload.
4. Capture public URL (not stored in JSON — derived at read time from filename, same as existing `PRODUCT_IMAGE_MAP` handling).
5. Call Gemini 2.0 Flash vision on the image → `{scene, mood, lighting, colors, composition, setting}`. Same prompt template as used for the original 22 lifestyle shots.
6. Seed `themes` from the SKU → theme map (product-use) or keep manual tags (lifestyle).
7. Upsert entry into `lifestyle_images.json`. Preserve JSON ordering stability (sort by filename).

Run once on 2026-04-19 Academy App pack; rerun later for PostAP pack.

## Wiring into the article pipeline

### New function in `blog/stage2/image_prompts.py`

```python
def select_hero_image(article: dict) -> dict | None:
    """
    Select a real photo hero for an article.

    Returns {filename, url, alt_text} or None if no match in either branch.
    Implements Branch A (SKU-in-headline) → Branch B (mood) → None.
    """
```

### Endpoint change — `blog/router.py`

In the `POST /api/v1/blog/articles/{article_id}/generate-hero-image` handler:

1. Call `select_hero_image(article_json)` first.
2. If result → patch `article_json.image_01_url` + `article_json.image_01_alt_text`, re-render HTML, save. Return `{ image_url, article_id, source: "library" }`.
3. If `None` and `os.getenv("HERO_AI_FALLBACK", "false") == "true"` → fall through to existing Imagen path. Return `{ source: "ai" }`.
4. If `None` and AI fallback disabled → clear `image_01_url`, re-render HTML (template handles missing hero gracefully — verify in test plan), save. Return `{ source: "none" }`.

Default env: `HERO_AI_FALLBACK=false`. Flips to `true` only if Beurer explicitly asks us to turn AI back on, or in dev.

### alt text handling

`select_hero_image` returns an `alt_text` field derived from the caption's `scene`. For `language == "de"` articles, translate `scene` to German (plan-level decision: either reuse an existing translator in the pipeline or add a one-shot Gemini call cached by `filename + language`). For `language == "en"`, use `scene` as-is. If translation fails, fall back to English `scene` rather than rendering empty alt. Accessibility requirement: alt text must describe the image, not the article.

## Fallback + edge cases

| Case | Behavior |
|------|----------|
| SKU article, SKU has photo | Product-in-use hero |
| SKU article, SKU has no photo (BM 81, IL 50, EM 59, ...) | Falls through to mood hero for the SKU's theme |
| SKU article, mood branch also empty | No hero rendered |
| Multiple SKUs in headline | First match in headline → `primary_keyword` scan wins |
| No SKU, theme has lifestyle matches | Mood hero |
| No SKU, theme has no lifestyle matches (rare: infrarot) | No hero rendered |
| `HERO_AI_FALLBACK=true` | Falls through to existing Imagen path at the last step |

Template renders without hero when `image_01_url` is empty or missing — verify in test plan that the article layout still looks correct.

## Licensing gate (blocker)

`_Beurer_Marketing Assets_Nutzungsbedingungen.pdf` lives in the same directory as the Academy App assets. Before the ingest script uploads anything to Supabase Storage:

1. Read the PDF.
2. Write a summary to `docs/beurer_asset_licensing.md`: permitted uses, attribution requirements (if any), restrictions on derivative works, retention/deletion obligations.
3. Confirm with Simon / Anika that public CDN serving via Supabase Storage is within the permitted scope.

Implementation cannot merge until this gate clears.

## Storage layout

```
Supabase Storage bucket: blog-images
├── generated/    (existing — AI hero images, kept for fallback path)
├── products/     (existing — product cutouts for inline use)
└── library/      (new — real photo library, hero source-of-truth)
```

`library/` receives both lifestyle and product-use shots. Public URLs; CDN-cacheable. Retention: indefinite (photos are owned assets per licensing gate).

## Out of scope

- Paragraph-scoped inline product images (briefing #6 follow-up — will reuse the captioned index)
- PostAP library ingestion (same script, different `--source-dir`; run when Anika's download link resolves)
- Editor UI for manual hero override
- Removing the AI hero path entirely (stays behind `HERO_AI_FALLBACK`)
- Retiring `PRODUCT_IMAGE_MAP` (still used for inline cutouts)

## Test plan

**Ingestion:**
1. Dry-run `scripts/ingest_hero_library.py --source-dir ../client-beurer/02_CLIENT_INPUT/2026-04-19_academy_app_assets --dry-run` → prints parse results for 67 files. Expect: 41 product-use + 22 lifestyle-skipped + 3 br-range-skipped + 1 PDF-skipped.
2. Real run → 41 new entries in `lifestyle_images.json`, 41 files in `blog-images/library/`. Check no entry has `sku == null && type == "product_use"`.

**Selection:**
3. Regenerate hero for 6 articles covering the matrix:
   - 2 × SKU with photo (e.g. BM 27 guide, EM 50 menstruation)
   - 2 × SKU without photo (e.g. BM 81 test, IL 50 anwendung)
   - 2 × no SKU (e.g. "Regelschmerzen lindern", "Bluthochdruck senken")
4. Eyeball each in the dashboard iframe. Verify: photo is relevant, alt text describes the image, layout unbroken.
5. For the SKU-without-photo cases, verify Branch B fallback fires (mood hero of correct theme).
6. For the rare no-match case (force via a test article in a theme with no lifestyle matches), verify article renders cleanly with no hero.

**Licensing:**
7. `docs/beurer_asset_licensing.md` exists and is signed off before merge.

## Coverage estimate after ingest

Of the 28-SKU catalog, 8 SKUs have product-use photos → ~29% of SKU articles get a product-in-use hero; rest fall back to mood hero. All mood-themed articles (blutdruck, rueckenschmerzen, regelschmerzen, tens_ems, default) have lifestyle matches. Infrarot is thinnest — acceptable until PostAP arrives.
