# Image Pipeline Integration & Dashboard Controls — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate hero image generation and product image mapping into the article generation pipeline, add dashboard image management controls, and batch-regenerate all client-facing articles.

**Architecture:** Image generation (Imagen 4.0) and product image mapping become inline steps in `article_service.py`, executed after quality checks and before HTML rendering. The dashboard sidebar gains an "Images" section with generate/remove/download controls. A batch endpoint regenerates all approved/published articles with version snapshots for safety.

**Tech Stack:** Python/FastAPI (backend), Google Imagen 4.0 API, Supabase Storage, Next.js API routes (dashboard proxy), vanilla JS (dashboard template)

---

## File Map

| File | Responsibility | Action |
|------|---------------|--------|
| `scripts/upload_product_images.py` | One-time upload of 21 product JPGs to Supabase Storage | Create |
| `blog/stage2/image_prompts.py` | Product image URL resolution via Supabase Storage | Modify |
| `blog/article_service.py` | Inline image generation + product mapping in pipeline | Modify |
| `blog/router.py` | Batch regeneration endpoint, update attach-product-images | Modify |
| `dashboard/app/api/blog-article/route.ts` | `remove_image` PATCH action | Modify |
| `styles/dashboard_template.html` | Sidebar image section, nav bar relocation, batch button | Modify |

---

### Task 1: Upload Product Images to Supabase Storage

**Files:**
- Create: `scripts/upload_product_images.py`

- [ ] **Step 1: Create the upload script**

```python
"""One-time upload of Beurer product cutout images to Supabase Storage."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.client import get_beurer_supabase

PRODUCT_IMAGES_DIR = Path(os.environ.get(
    "BEURER_PRODUCT_IMAGES_DIR",
    "C:/Users/yousi/scaile/workshop-beurer/02_CLIENT_INPUT/2026-02-18_produktbilder_datenblaetter/produktbilder",
))

BUCKET = "blog-images"
FOLDER = "products"


def upload_all():
    sb = get_beurer_supabase()
    if not PRODUCT_IMAGES_DIR.exists():
        print(f"ERROR: Directory not found: {PRODUCT_IMAGES_DIR}")
        sys.exit(1)

    jpg_files = list(PRODUCT_IMAGES_DIR.glob("*.jpg")) + list(PRODUCT_IMAGES_DIR.glob("*.JPG"))
    print(f"Found {len(jpg_files)} product images in {PRODUCT_IMAGES_DIR}")

    uploaded = 0
    for img_path in sorted(jpg_files):
        storage_path = f"{FOLDER}/{img_path.name}"
        try:
            with open(img_path, "rb") as f:
                sb.storage.from_(BUCKET).upload(
                    path=storage_path,
                    file=f.read(),
                    file_options={"content-type": "image/jpeg", "upsert": "true"},
                )
            url = sb.storage.from_(BUCKET).get_public_url(storage_path)
            print(f"  OK: {img_path.name} -> {url[:80]}...")
            uploaded += 1
        except Exception as e:
            print(f"  FAIL: {img_path.name} -> {e}")

    print(f"\nUploaded {uploaded}/{len(jpg_files)} images to {BUCKET}/{FOLDER}/")


if __name__ == "__main__":
    upload_all()
```

- [ ] **Step 2: Run the upload script**

Run: `python scripts/upload_product_images.py`
Expected: All 21 JPGs uploaded to `blog-images/products/` in Supabase Storage. Output shows `OK` for each file.

- [ ] **Step 3: Commit**

```bash
git add scripts/upload_product_images.py
git commit -m "feat: add script to upload product images to Supabase Storage"
```

---

### Task 2: Update Product Image Map to Use Supabase URLs

**Files:**
- Modify: `blog/stage2/image_prompts.py`

- [ ] **Step 1: Add Supabase URL builder and update find_product_images**

In `blog/stage2/image_prompts.py`, replace the `_PRODUCT_IMAGES_DIR` local path logic with Supabase Storage URL resolution.

Replace this block (lines 97-102):
```python
# ── Product image mapping (Track 2: inline product cutouts) ──

# Path to real Beurer product images
_PRODUCT_IMAGES_DIR = Path(os.environ.get(
    "BEURER_PRODUCT_IMAGES_DIR",
    "C:/Users/yousi/scaile/workshop-beurer/02_CLIENT_INPUT/2026-02-18_produktbilder_datenblaetter/produktbilder",
))
```

With:
```python
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
```

- [ ] **Step 2: Update find_product_images to return URLs instead of paths**

Replace the `find_product_images` function (lines 184-249) — change the matching logic to return Supabase URLs instead of local `Path` objects:

```python
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
```

- [ ] **Step 3: Remove unused imports**

Remove `os` and `Path` from imports at the top of the file (lines 3-4) since `_PRODUCT_IMAGES_DIR` is gone. Keep `logging` and `typing`.

Updated imports:
```python
import logging
from typing import List

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Verify the module imports without errors**

Run: `python -c "from blog.stage2.image_prompts import find_product_images, build_beurer_hero_prompt, detect_theme; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py
git commit -m "feat: switch product image mapping from local paths to Supabase Storage URLs"
```

---

### Task 3: Integrate Image Generation into Article Pipeline

**Files:**
- Modify: `blog/article_service.py:468-499` (between stages 4/5 cleanup and HTML render)

- [ ] **Step 1: Add image generation helper function**

Add this function before `generate_article()` (around line 100, after the module-level imports and helpers):

```python
async def _generate_article_images(article: dict, article_id: str) -> dict:
    """Generate hero image and map product images inline in the pipeline.

    Modifies article dict in-place with image URLs.
    Hero image: Imagen 4.0 with one retry on failure.
    Product images: Supabase Storage URL lookup.
    """
    import asyncio as _aio
    from .stage_tracker import _set_stage

    _set_stage(article_id, "images")

    # Hero image generation with one retry
    try:
        from .stage2.image_prompts import build_beurer_hero_prompt, detect_theme
        from .stage2.image_creator import ImageCreator

        theme = detect_theme(article)
        prompt = build_beurer_hero_prompt(article)
        logger.info(f"Generating hero image for '{article_id}' — theme: {theme}")

        creator = ImageCreator()
        image_url = await creator.generate_async(prompt, aspect_ratio="16:9")

        if not image_url:
            logger.warning(f"Hero image attempt 1 failed for '{article_id}', retrying in 2s...")
            await _aio.sleep(2)
            image_url = await creator.generate_async(prompt, aspect_ratio="16:9")

        if image_url:
            headline = article.get("Headline", "") or article.get("headline", "")
            alt_text = f"Beurer Magazin: {headline}"
            if len(alt_text) > 125:
                alt_text = alt_text[:122] + "..."
            article["image_01_url"] = image_url
            article["image_01_alt_text"] = alt_text
            logger.info(f"Hero image set for '{article_id}': {image_url[:80]}...")
        else:
            logger.warning(f"Hero image generation failed after retry for '{article_id}'")
    except Exception as e:
        logger.error(f"Hero image generation error for '{article_id}': {e}")

    # Product image mapping
    try:
        from .stage2.image_prompts import find_product_images
        matches = find_product_images(article)
        for i, match in enumerate(matches[:2]):
            slot = f"image_0{i + 2}"
            article[f"{slot}_url"] = match["url"]
            article[f"{slot}_alt_text"] = f"Beurer {match['model']}"
            logger.info(f"Product image {slot} set: {match['model']}")
    except Exception as e:
        logger.error(f"Product image mapping error for '{article_id}': {e}")

    return article
```

- [ ] **Step 2: Call image generation in `generate_article()` before HTML render**

In `generate_article()`, insert the image generation call between the stages 4/5 cleanup (line 472) and the author fetch (line 474). Add after `pipeline_reports.update(extra_reports)` (line 472):

```python
        # Generate images (hero + product) inline
        fixed_article = await _generate_article_images(fixed_article, article_id)
```

- [ ] **Step 3: Call image generation in `regenerate_article()` before HTML render**

In `regenerate_article()`, insert the same call between the stages 4/5 cleanup (line 748) and the author fetch (line 753). Add after `pipeline_reports["stage3"] = {...}` (line 751):

```python
        # Generate images (hero + product) inline
        fixed_article = await _generate_article_images(fixed_article, article_id)
```

- [ ] **Step 4: Add "images" stage label to stage tracker**

In `blog/stage_tracker.py`, the `_set_stage` function just stores a string — no changes needed since it accepts any string. But verify the dashboard template handles the "images" stage for the generation progress display.

Check by searching in `styles/dashboard_template.html` for stage display logic. If there's a stage label map, add `"images"` to it.

- [ ] **Step 5: Verify the module imports without errors**

Run: `python -c "from blog.article_service import generate_article, regenerate_article; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add blog/article_service.py
git commit -m "feat: integrate hero image generation and product mapping into article pipeline"
```

---

### Task 4: Update attach-product-images Endpoint

**Files:**
- Modify: `blog/router.py:513-600`

- [ ] **Step 1: Simplify attach-product-images to use Supabase URLs**

The `find_product_images` function now returns `url` instead of `path`. Update the endpoint to use the URL directly instead of building Supabase Storage URLs manually.

Replace lines 549-562 (the URL building and attachment loop) in the `attach_product_images` function:

```python
    # 3. Attach matched product images (URLs come from Supabase Storage)
    attached = []
    for i, match in enumerate(matches[:2]):  # Max 2 product images (image_02, image_03)
        slot = f"image_0{i + 2}"
        article_json[f"{slot}_url"] = match["url"]
        article_json[f"{slot}_alt_text"] = f"Beurer {match['model']}"
        attached.append({"model": match["model"], "slot": slot, "url": match["url"]})
```

This replaces the old logic that tried to build URLs from `base_url` and `match['filename']`.

- [ ] **Step 2: Commit**

```bash
git add blog/router.py
git commit -m "fix: use Supabase Storage URLs from find_product_images in attach endpoint"
```

---

### Task 5: Add Batch Regeneration Endpoint

**Files:**
- Modify: `blog/router.py` (add new endpoint after `attach_product_images`)

- [ ] **Step 1: Add the batch regeneration endpoint**

Add after the `attach_product_images` endpoint (after line ~600):

```python
@router.post("/articles/regenerate-batch")
async def regenerate_batch(background_tasks: BackgroundTasks):
    """
    Regenerate all client-facing articles (approved/published).

    Snapshots current state before regenerating each article.
    Runs sequentially in background — returns immediately with article count.
    """
    from db.client import get_beurer_supabase

    supabase = get_beurer_supabase()

    # Fetch all client-facing articles
    result = (
        supabase.table("blog_articles")
        .select("id, keyword, review_status, status")
        .in_("review_status", ["approved", "published"])
        .execute()
    )

    articles = result.data or []
    if not articles:
        return {"total": 0, "message": "No client-facing articles found"}

    article_ids = [a["id"] for a in articles]
    logger.info(f"Batch regeneration: {len(article_ids)} articles queued")

    background_tasks.add_task(_run_batch_regeneration, article_ids)

    return {
        "total": len(article_ids),
        "article_ids": article_ids,
        "status": "started",
        "message": f"Regenerating {len(article_ids)} articles in background",
    }


async def _run_batch_regeneration(article_ids: list):
    """Process batch regeneration sequentially, snapshotting each article first."""
    from db.client import get_beurer_supabase
    from .article_service import regenerate_article as _regenerate

    supabase = get_beurer_supabase()
    succeeded = 0
    failed = 0
    errors = []

    for article_id in article_ids:
        try:
            # Snapshot current state into feedback_history
            row = (
                supabase.table("blog_articles")
                .select("article_json, article_html, headline, feedback_history")
                .eq("id", article_id)
                .limit(1)
                .execute()
            )
            if not row.data:
                errors.append({"article_id": article_id, "error": "Not found"})
                failed += 1
                continue

            article = row.data[0]
            history = article.get("feedback_history") or []
            history.append({
                "type": "snapshot",
                "headline": article.get("headline", ""),
                "article_html": article.get("article_html", ""),
                "article_json": article.get("article_json", {}),
                "created_at": datetime.utcnow().isoformat(),
                "version": len(history) + 1,
                "reason": "batch_regeneration",
            })
            supabase.table("blog_articles").update({
                "feedback_history": history,
            }).eq("id", article_id).execute()

            # Regenerate (from scratch, no feedback)
            result = await _regenerate(article_id=article_id, feedback=None, from_scratch=True)
            if result.get("status") == "completed":
                succeeded += 1
                logger.info(f"Batch regen: {article_id} completed ({succeeded}/{len(article_ids)})")
            else:
                failed += 1
                errors.append({"article_id": article_id, "error": result.get("error_message", "Unknown")})
        except Exception as e:
            failed += 1
            errors.append({"article_id": article_id, "error": str(e)[:200]})
            logger.error(f"Batch regen failed for {article_id}: {e}")

    logger.info(f"Batch regeneration complete: {succeeded} succeeded, {failed} failed out of {len(article_ids)}")
```

- [ ] **Step 2: Add missing import**

At the top of `blog/router.py`, ensure `datetime` is imported. Check existing imports — if `datetime` is already imported, skip this step. If not, add:

```python
from datetime import datetime
```

- [ ] **Step 3: Commit**

```bash
git add blog/router.py
git commit -m "feat: add batch regeneration endpoint for client-facing articles"
```

---

### Task 6: Add remove_image Action to Dashboard API

**Files:**
- Modify: `dashboard/app/api/blog-article/route.ts` (PATCH handler, after `save_html` action around line 400)

- [ ] **Step 1: Add the remove_image action**

Insert after the `save_html` action block (after line ~400):

```typescript
    // Remove image — detach from article_json, re-render HTML
    if (action === "remove_image") {
      const { slot } = body;
      const validSlots = ["image_01", "image_02", "image_03"];
      if (!validSlots.includes(slot)) {
        return NextResponse.json(
          { error: `Invalid slot. Must be one of: ${validSlots.join(", ")}` },
          { status: 400 }
        );
      }

      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("article_json, language, social_context, author_id")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }
      if (!article.article_json) {
        return NextResponse.json({ error: "No article data" }, { status: 400 });
      }

      // Clear the image fields
      const updatedJson = { ...article.article_json };
      updatedJson[`${slot}_url`] = "";
      updatedJson[`${slot}_alt_text`] = "";

      // Fetch author if assigned
      let author = null;
      if (article.author_id) {
        const { data: authorData } = await supabase
          .from("blog_authors")
          .select("name, title, bio, image_url, credentials, linkedin_url")
          .eq("id", article.author_id)
          .single();
        author = authorData;
      }

      // Re-render HTML
      const articleHtml = renderArticleHtml({
        article: updatedJson,
        companyName: "Beurer",
        companyUrl: "https://www.beurer.com",
        language: article.language || "de",
        category: article.social_context?.category || "",
        author,
      });

      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          article_json: updatedJson,
          article_html: articleHtml,
          html_custom: false,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }
```

- [ ] **Step 2: Commit**

```bash
cd dashboard && git add app/api/blog-article/route.ts && cd ..
git commit -m "feat: add remove_image PATCH action to blog-article API"
```

---

### Task 7: Dashboard — Relocate Nav Bar Above Content Pane

**Files:**
- Modify: `styles/dashboard_template.html`

This task moves the article modal action buttons (Markdown, Copy HTML, Download, Edit, Save, Reset) from the full-width `.article-modal-header` into a new bar directly above the article content pane. The modal header retains only the title, meta badges, and close button.

- [ ] **Step 1: Move action buttons out of the header**

In `openArticleModal()` (around line 7187-7194), the action buttons are in `.article-modal-actions` inside `.article-modal-header`. Move them to a new `<div class="article-content-toolbar">` placed inside `.article-modal-content`, before the iframe.

Replace the article modal header's actions div (lines 7187-7195) — remove all buttons except the panel toggle and close button:

Old (lines 7187-7195):
```javascript
                    <div class="article-modal-actions">
                        <button class="viewer-only" onclick="saveArticleAsMarkdown('${articleId}', '${esc(article.headline || article.keyword || 'article')}')">&#128196; ${t('article_save_markdown')}</button>
                        <button class="viewer-only" id="btn-copy-html" onclick="copyArticleHtml('${articleId}')">&#128203; ${t('article_copy_html')}</button>
                        <button class="viewer-only" id="btn-download-modal" onclick="downloadArticleFromModal('${articleId}', '${esc(article.headline || article.keyword || 'article')}')">&#8615; ${t('article_download_modal')}</button>
                        <button class="editor-only" id="btn-toggle-edit" onclick="toggleArticleEditMode('${articleId}')">&#9998; ${t('article_edit_html')}</button>
                        <div class="editor-only article-dirty-indicator" id="article-dirty-dot"></div>
                        <button class="editor-only save-btn" id="btn-save-html" style="display:none" onclick="handleSaveArticleHtml('${articleId}')">${t('article_save_html')}</button>
                        <button class="editor-only" id="btn-reset-edits" onclick="handleResetEdits('${articleId}')" style="${article.html_custom ? '' : 'display:none'}" title="${t('article_reset_edits')}">&#8634; ${t('article_reset_edits')}</button>
                        <button id="btn-toggle-panel" onclick="toggleArticlePanel()">&#9998; ${t('article_edit_panel')}</button>
                        <button class="article-modal-close">&times;</button>
                    </div>
```

New header actions (keep only panel toggle and close):
```javascript
                    <div class="article-modal-actions">
                        <button id="btn-toggle-panel" onclick="toggleArticlePanel()">&#9998; ${t('article_edit_panel')}</button>
                        <button class="article-modal-close">&times;</button>
                    </div>
```

- [ ] **Step 2: Add content toolbar above the iframe**

Inside `.article-modal-content` (around line 7212), before the SERP preview and iframe, insert the toolbar:

Insert before the SERP preview block (the `${['completed',...].includes(...) ? (() => {` block around line 7213):

```javascript
                        <div class="article-content-toolbar">
                            <button class="viewer-only" onclick="saveArticleAsMarkdown('${articleId}', '${esc(article.headline || article.keyword || 'article')}')">&#128196; ${t('article_save_markdown')}</button>
                            <button class="viewer-only" id="btn-copy-html" onclick="copyArticleHtml('${articleId}')">&#128203; ${t('article_copy_html')}</button>
                            <button class="viewer-only" id="btn-download-modal" onclick="downloadArticleFromModal('${articleId}', '${esc(article.headline || article.keyword || 'article')}')">&#8615; ${t('article_download_modal')}</button>
                            <button class="editor-only" id="btn-toggle-edit" onclick="toggleArticleEditMode('${articleId}')">&#9998; ${t('article_edit_html')}</button>
                            <div class="editor-only article-dirty-indicator" id="article-dirty-dot"></div>
                            <button class="editor-only save-btn" id="btn-save-html" style="display:none" onclick="handleSaveArticleHtml('${articleId}')">${t('article_save_html')}</button>
                            <button class="editor-only" id="btn-reset-edits" onclick="handleResetEdits('${articleId}')" style="${article.html_custom ? '' : 'display:none'}" title="${t('article_reset_edits')}">&#8634; ${t('article_reset_edits')}</button>
                        </div>
```

- [ ] **Step 3: Add CSS for the content toolbar**

Add in the `<style>` section (near the other `.article-modal-*` styles, around line 1350):

```css
        .article-content-toolbar {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 12px;
            background: #f9fafb;
            border-bottom: 1px solid #e5e7eb;
            border-radius: 8px 8px 0 0;
            flex-shrink: 0;
        }
        .article-content-toolbar button {
            font-size: 11px;
            padding: 4px 10px;
            border: 1px solid #d1d5db;
            border-radius: 5px;
            background: #fff;
            cursor: pointer;
            white-space: nowrap;
        }
        .article-content-toolbar button:hover { background: #f3f4f6; }
```

- [ ] **Step 4: Verify the modal renders correctly**

Open the dashboard, click any article, confirm:
- Header shows only title + meta + panel toggle + close
- Toolbar with all action buttons appears above the article content
- Sidebar starts at the same vertical level as the content area

- [ ] **Step 5: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "refactor: relocate article modal nav bar above content pane for more sidebar headroom"
```

---

### Task 8: Dashboard — Add Sidebar Image Section

**Files:**
- Modify: `styles/dashboard_template.html`

- [ ] **Step 1: Add image section HTML in the sidebar**

In `openArticleModal()`, inside `.sidebar-scroll-area` (line 7249), insert the image section between the review status row (line 7258) and the publish status row (line 7259).

Insert after the closing `</div>` of `.review-status-row` (line 7258):

```javascript
                        <div class="image-section" id="image-section" data-article-id="${articleId}">
                            <div class="sidebar-section-title" style="padding:12px 16px 8px;">Images</div>
                            <div style="padding:0 16px 12px;">
                                ${(() => {
                                    const aj = article.article_json || {};
                                    const hasHero = !!aj.image_01_url;
                                    const slots = [
                                        { key: 'image_01', label: 'Hero', url: aj.image_01_url, alt: aj.image_01_alt_text },
                                        { key: 'image_02', label: 'Product 1', url: aj.image_02_url, alt: aj.image_02_alt_text },
                                        { key: 'image_03', label: 'Product 2', url: aj.image_03_url, alt: aj.image_03_alt_text },
                                    ].filter(s => s.url);

                                    let html = '<div class="image-actions-row">';
                                    html += '<button class="img-action-btn" id="btn-gen-hero" onclick="handleGenerateHeroImage(\'' + articleId + '\')">' + (hasHero ? '&#8635; Regenerate Hero' : '&#9998; Generate Hero') + '</button>';
                                    html += '<button class="img-action-btn" id="btn-attach-products" onclick="handleAttachProductImages(\'' + articleId + '\')">&#128247; Attach Products</button>';
                                    html += '</div>';

                                    if (slots.length > 0) {
                                        html += '<div class="image-thumbs">';
                                        slots.forEach(s => {
                                            html += '<div class="image-thumb-row">';
                                            html += '<img src="' + esc(s.url) + '" alt="' + esc(s.alt || '') + '" class="image-thumb">';
                                            html += '<span class="image-thumb-label">' + s.label + '</span>';
                                            html += '<a href="' + esc(s.url) + '" download class="image-thumb-action" title="Download">&#8615;</a>';
                                            html += '<button class="image-thumb-action" onclick="handleRemoveImage(\'' + articleId + '\', \'' + s.key + '\')" title="Remove">&times;</button>';
                                            html += '</div>';
                                        });
                                        html += '</div>';
                                    } else {
                                        html += '<div style="font-size:11px;color:#9ca3af;font-style:italic;margin-top:4px;">No images attached</div>';
                                    }
                                    return html;
                                })()}
                            </div>
                        </div>
```

- [ ] **Step 2: Add CSS for the image section**

Add in the `<style>` section (near other sidebar styles):

```css
        .image-section {
            border-bottom: 1px solid #e5e7eb;
        }
        .image-actions-row {
            display: flex;
            gap: 6px;
            margin-bottom: 8px;
        }
        .img-action-btn {
            flex: 1;
            padding: 6px 8px;
            font-size: 11px;
            font-weight: 500;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background: #fff;
            cursor: pointer;
            white-space: nowrap;
        }
        .img-action-btn:hover { background: #f3f4f6; }
        .img-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .image-thumbs {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .image-thumb-row {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: #fafafa;
        }
        .image-thumb {
            width: 60px;
            height: 34px;
            object-fit: cover;
            border-radius: 4px;
            background: #e5e7eb;
        }
        .image-thumb-label {
            font-size: 11px;
            font-weight: 500;
            color: #374151;
            flex: 1;
        }
        .image-thumb-action {
            background: none;
            border: none;
            font-size: 14px;
            cursor: pointer;
            color: #6b7280;
            padding: 2px 4px;
            text-decoration: none;
        }
        .image-thumb-action:hover { color: #111827; }
```

- [ ] **Step 3: Add JavaScript handlers for image actions**

Add these functions in the `<script>` section (near other article action handlers):

```javascript
async function handleGenerateHeroImage(articleId) {
    const btn = document.getElementById('btn-gen-hero');
    if (!btn) return;
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '&#8987; Generating...';

    try {
        const res = await fetch('/api/blog-article', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'generate_hero_image', article_id: articleId }),
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            showToast(data.error || 'Image generation failed', 'error');
            btn.innerHTML = origText;
            btn.disabled = false;
            return;
        }
        showToast('Hero image generated!');
        // Refresh the article modal to show the new image
        openArticleModal(articleId);
    } catch (e) {
        console.error('Hero image generation failed:', e);
        showToast('Image generation failed', 'error');
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

async function handleAttachProductImages(articleId) {
    const btn = document.getElementById('btn-attach-products');
    if (!btn) return;
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '&#8987; Searching...';

    try {
        const res = await fetch('/api/blog-article', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'attach_product_images', article_id: articleId }),
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            showToast(data.error || data.message || 'No products matched', 'error');
            btn.innerHTML = origText;
            btn.disabled = false;
            return;
        }
        const count = (data.product_images || data.attached || []).length;
        showToast(count > 0 ? count + ' product image(s) attached!' : 'No matching products found');
        openArticleModal(articleId);
    } catch (e) {
        console.error('Product image attach failed:', e);
        showToast('Product image attach failed', 'error');
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

async function handleRemoveImage(articleId, slot) {
    if (!confirm('Remove this image from the article?')) return;

    try {
        const res = await fetch('/api/blog-article', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'remove_image', article_id: articleId, slot: slot }),
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            showToast(data.error || 'Image removal failed', 'error');
            return;
        }
        showToast('Image removed');
        openArticleModal(articleId);
    } catch (e) {
        console.error('Image removal failed:', e);
        showToast('Image removal failed', 'error');
    }
}
```

- [ ] **Step 4: Add proxy routes in Next.js API for generate/attach**

In `dashboard/app/api/blog-article/route.ts`, the POST handler needs to proxy `generate_hero_image` and `attach_product_images` actions to the Python backend. Add to the POST handler:

```typescript
    // In the POST handler, after checking for existing article creation logic:
    const { action } = body;

    if (action === "generate_hero_image") {
      if (!BACKEND_URL) {
        return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
      }
      const res = await fetch(
        `${BACKEND_URL}/api/v1/blog/articles/${body.article_id}/generate-hero-image`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    }

    if (action === "attach_product_images") {
      if (!BACKEND_URL) {
        return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
      }
      const res = await fetch(
        `${BACKEND_URL}/api/v1/blog/articles/${body.article_id}/attach-product-images`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    }
```

- [ ] **Step 5: Verify the sidebar renders correctly**

Open the dashboard, click an article modal. Confirm:
- Image section visible between review status and publish status
- Generate Hero / Attach Products buttons render
- For articles with images: thumbnail rows with download/remove icons appear

- [ ] **Step 6: Commit**

```bash
git add styles/dashboard_template.html dashboard/app/api/blog-article/route.ts
git commit -m "feat: add sidebar image section with generate, attach, download, and remove controls"
```

---

### Task 9: Dashboard — Add Batch Regeneration Button

**Files:**
- Modify: `styles/dashboard_template.html`

- [ ] **Step 1: Add the batch regeneration button**

In `renderUnifiedContentView()` (line 9526-9528), add a batch regeneration button next to the "Add Topic" button in the content header:

Replace the header (lines 9526-9528):
```javascript
        <div class="unified-content-header">
          <h3 style="margin:0;font-size:15px;">Content Pipeline</h3>
          <button class="gen-article-btn" onclick="openAddTopicModal()" style="font-size:11px;">+ Add Topic</button>
        </div>
```

With:
```javascript
        <div class="unified-content-header">
          <h3 style="margin:0;font-size:15px;">Content Pipeline</h3>
          <div style="display:flex;gap:6px;">
            <button class="gen-article-btn" id="btn-batch-regen" onclick="handleBatchRegenerate()" style="font-size:11px;background:#f3f4f6;color:#374151;border:1px solid #d1d5db;">&#8635; Regenerate All Published</button>
            <button class="gen-article-btn" onclick="openAddTopicModal()" style="font-size:11px;">+ Add Topic</button>
          </div>
        </div>
```

- [ ] **Step 2: Add the batch regeneration handler**

Add this function in the `<script>` section:

```javascript
async function handleBatchRegenerate() {
    if (!confirm('This will regenerate ALL approved/published articles with fresh content and images. Current versions will be saved as snapshots. Continue?')) return;

    const btn = document.getElementById('btn-batch-regen');
    if (!btn) return;
    btn.disabled = true;
    btn.innerHTML = '&#8987; Starting batch...';

    try {
        const res = await fetch('/api/blog-article', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'regenerate_batch' }),
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            showToast(data.error || 'Batch regeneration failed', 'error');
            btn.disabled = false;
            btn.innerHTML = '&#8635; Regenerate All Published';
            return;
        }
        showToast('Batch regeneration started: ' + data.total + ' articles');
        btn.innerHTML = '&#8987; Regenerating ' + data.total + ' articles...';

        // Poll until articles are done (check every 10s for up to 30min)
        let polls = 0;
        const poll = setInterval(async () => {
            polls++;
            if (polls > 180) {
                clearInterval(poll);
                btn.disabled = false;
                btn.innerHTML = '&#8635; Regenerate All Published';
                return;
            }
            try {
                // Check if any articles are still regenerating
                const checkRes = await fetch('/api/blog-article');
                const articles = await checkRes.json();
                const stillGenerating = (articles || []).some(a => a.status === 'regenerating');
                if (!stillGenerating) {
                    clearInterval(poll);
                    btn.disabled = false;
                    btn.innerHTML = '&#8635; Regenerate All Published';
                    showToast('Batch regeneration complete!');
                    articleListLoaded = false;
                    renderArticleListView();
                }
            } catch (e) { /* continue polling */ }
        }, 10000);
    } catch (e) {
        console.error('Batch regeneration failed:', e);
        showToast('Batch regeneration failed', 'error');
        btn.disabled = false;
        btn.innerHTML = '&#8635; Regenerate All Published';
    }
}
```

- [ ] **Step 3: Add proxy route for batch regeneration in Next.js API**

In `dashboard/app/api/blog-article/route.ts`, add to the POST handler (alongside the other action proxies from Task 8):

```typescript
    if (action === "regenerate_batch") {
      if (!BACKEND_URL) {
        return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
      }
      const res = await fetch(
        `${BACKEND_URL}/api/v1/blog/articles/regenerate-batch`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    }
```

- [ ] **Step 4: Commit**

```bash
git add styles/dashboard_template.html dashboard/app/api/blog-article/route.ts
git commit -m "feat: add batch regeneration button for all published articles"
```

---

### Task 10: End-to-End Verification

- [ ] **Step 1: Start the backend server**

Run: `python dev.py`
Expected: FastAPI server starts on port 8000

- [ ] **Step 2: Start the dashboard**

Run: `cd dashboard && npm run dev`
Expected: Next.js dev server starts on port 3000

- [ ] **Step 3: Test hero image generation via sidebar**

Open dashboard → Content tab → click an article → in the sidebar Image section, click "Generate Hero". Verify:
- Spinner shows while generating
- Image appears in thumbnail row after completion
- Article preview iframe refreshes with hero image at top

- [ ] **Step 4: Test product image attachment**

Click "Attach Products" for an article that mentions a Beurer product (e.g., BM 27). Verify:
- Product thumbnail(s) appear in the image section
- Product images render inline in the article preview

- [ ] **Step 5: Test image download**

Click the download icon on any image thumbnail. Verify browser downloads the image file.

- [ ] **Step 6: Test image removal**

Click the remove (x) icon on an image. Confirm the dialog. Verify:
- Thumbnail disappears from sidebar
- Article preview updates (image gone, placeholder shows for hero)

- [ ] **Step 7: Test article generation pipeline**

Generate a new article via "Add Topic". Verify the article completes with:
- Hero image auto-generated
- Product images auto-attached (if product mentions exist)

- [ ] **Step 8: Test batch regeneration**

Click "Regenerate All Published" in the content pipeline header. Verify:
- Confirmation dialog appears
- Button shows progress
- Articles regenerate with images
- Previous versions are accessible via version pills

- [ ] **Step 9: Commit final state**

```bash
git add -A
git commit -m "feat: complete image pipeline integration with dashboard controls and batch regeneration"
```
