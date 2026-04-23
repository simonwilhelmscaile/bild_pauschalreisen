# Image Pipeline Integration & Dashboard Controls

**Date:** 2026-04-07
**Scope:** Integrate image generation into article pipeline, add dashboard image management, batch-regenerate client-facing articles

---

## Overview

Three workstreams:

1. **Pipeline integration** — hero image generation (Imagen 4.0) and product image mapping become part of the standard article generation flow in `stage_2.py`
2. **Dashboard image controls** — sidebar section for generating, removing, and downloading images per article, plus nav bar relocation for more sidebar headroom
3. **Batch regeneration** — re-run full pipeline (content + images) for all client-facing articles

---

## 1. Pipeline Integration

### Where

`blog/stage2/stage_2.py` — after `article_json` is fully built, before `HTMLRenderer.render()`.

### Flow

1. Article JSON complete (headline, sections, meta, etc.)
2. **Hero image:** `build_beurer_hero_prompt(article_json)` → `ImageCreator.generate_async(prompt, aspect_ratio="16:9")` → set `article_json.image_01_url` + `article_json.image_01_alt_text`
3. **Retry on failure:** If Imagen fails, wait 2s, retry once. If second attempt fails, log warning and continue — article saves with placeholder image.
4. **Product images:** `find_product_images(article_json)` → look up Supabase Storage URLs → set `image_02_url`/`image_02_alt_text` (mid-article) and `image_03_url`/`image_03_alt_text` (bottom) for up to 2 matched products
5. Render HTML with all images
6. Save to DB

### Product Image Storage

The 21 Beurer product cutout JPGs must be uploaded to Supabase Storage once:

- **Bucket:** `blog-images`
- **Folder:** `products/`
- **Files:** All JPGs from `workshop-beurer/02_CLIENT_INPUT/.../produktbilder/`

A one-time upload script (`scripts/upload_product_images.py`) handles this. After upload, `PRODUCT_IMAGE_MAP` in `image_prompts.py` returns Supabase Storage public URLs instead of local filesystem paths.

### Files Modified

| File | Change |
|------|--------|
| `blog/stage2/stage_2.py` | Add hero image generation + product image mapping after article JSON build, before HTML render |
| `blog/stage2/image_prompts.py` | Update `PRODUCT_IMAGE_MAP` to return Supabase Storage URLs; add helper `get_product_image_url(model)` |
| `blog/stage2/image_creator.py` | No changes needed (already supports async + aspect_ratio) |
| `blog/router.py` | Update `attach-product-images` endpoint to use Supabase URLs |

### New Files

| File | Purpose |
|------|---------|
| `scripts/upload_product_images.py` | One-time script to upload 21 product JPGs to Supabase Storage |

---

## 2. Dashboard Image Controls

### Sidebar Image Section

New section in the article modal sidebar, visually distinct, positioned below review status and above author assignment. Header: "Images" / "Bilder".

**Controls:**

- **"Generate Hero Image" button** — calls `POST /api/v1/blog/articles/{id}/generate-hero-image`. Shows spinner while generating. On success, refreshes article preview iframe. Label changes to "Regenerate Hero Image" when a hero image already exists.
- **"Attach Product Images" button** — calls `POST /api/v1/blog/articles/{id}/attach-product-images`. Shows match count on success (e.g. "2 product images attached"). Only visible if article has product mentions in `article_json`.

**Per-image rows:** Each attached image (hero, product 1, product 2) renders as a thumbnail row:
- ~60px thumbnail preview
- Label: "Hero" / "Product 1" / "Product 2"
- Download icon — triggers browser download of the image file from its URL
- Remove icon (x) — clears `image_0X_url` and `image_0X_alt_text` from `article_json`, re-renders HTML, saves to DB. The file remains in Supabase Storage (detach only, no deletion).

### Nav Bar Relocation

The article modal action buttons row (Markdown, Copy HTML, Download HTML, Edit, Save, Reset) moves from the full-width modal header to sit directly above the article content pane only (inside `.article-modal-content`). The sidebar starts at the same vertical level as the content, gaining the headroom previously occupied by the nav bar.

The modal header retains only the title, meta badges, and close button.

### API Changes

| Endpoint | Change |
|----------|--------|
| `PATCH /api/blog-article` (Next.js) | New action: `remove_image` — accepts `{ action: "remove_image", article_id, slot: "image_01" \| "image_02" \| "image_03" }`. Clears the URL and alt text fields, re-renders HTML, saves. |

### Files Modified

| File | Change |
|------|--------|
| `styles/dashboard_template.html` | Add sidebar image section with generate/attach buttons, thumbnail rows, download/remove icons. Relocate nav bar above content pane only. |
| `dashboard/app/api/blog-article/route.ts` | Add `remove_image` PATCH action |

---

## 3. Batch Regeneration

### Endpoint

`POST /api/v1/blog/articles/regenerate-batch`

**Flow:**
1. Query all client-facing articles: `review_status` in `['approved', 'published']`
2. For each article, sequentially:
   a. Snapshot current `article_json` and `article_html` into `feedback_history` as a version entry (preserves rollback via existing version bar)
   b. Re-run full article generation pipeline (LLM content generation using existing `social_context` and `keyword`)
   c. Generate hero image (inline, per pipeline integration above)
   d. Map product images (inline, per pipeline integration above)
   e. Render HTML, save to DB
3. Return summary: `{ total, succeeded, failed, errors: [{article_id, error}] }`

**Long-running operation:** Articles process sequentially (LLM + Imagen per article). The endpoint streams progress or the dashboard polls for completion.

### Dashboard Integration

A button in the content tab article list view: "Regenerate All Published Articles". Positioned in the article list header area, not in individual article modals. Shows a progress indicator during execution.

### Safety

- Each article's current state is snapshotted before regeneration
- Previous versions are recoverable via the existing version pill bar in the article modal
- Failures on individual articles don't halt the batch — the endpoint continues and reports errors at the end

### Files Modified

| File | Change |
|------|--------|
| `blog/router.py` | Add `POST /articles/regenerate-batch` endpoint |
| `styles/dashboard_template.html` | Add "Regenerate All Published" button in article list view, with progress indicator |

---

## Data Model

No new tables or columns. Uses existing `article_json` fields:

| Field | Slot | Usage |
|-------|------|-------|
| `image_01_url` | Hero image | AI-generated via Imagen 4.0 |
| `image_01_alt_text` | Hero alt | Auto-generated: "Beurer Magazin: {headline}" |
| `image_02_url` | Mid-article | Product cutout from Supabase Storage |
| `image_02_alt_text` | Product 1 alt | "Beurer {MODEL}" |
| `image_03_url` | Bottom | Product cutout from Supabase Storage |
| `image_03_alt_text` | Product 2 alt | "Beurer {MODEL}" |

---

## Out of Scope

- Image deletion from Supabase Storage (remove = detach only for now)
- Manual image upload / drag-and-drop
- Beurer Academy App integration (pending API access confirmation)
- Infographics / data visualization images
- Image editing / cropping in dashboard
