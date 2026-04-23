# Article Hallucination Prevention — Design Spec

**Date:** 2026-04-09  
**Context:** [Audit document](../../superpowers/plans/2026-04-09-article-hallucination-audit.md) identified 10 recurring hallucination patterns across 25 Beurer blog articles. Prompt-level guardrails exist for most issues but Gemini consistently ignores them. This design prevents hallucinations upstream by controlling what data Gemini receives, with a slim safety net for what leaks through.

**Approach:** Category-scoped context (prevention) + catalog-driven post-generation validation (safety net).

---

## 1. Category Detection

New function `detect_article_category(keyword: str) -> str` in `product_catalog.py`.

Returns one of: `tens_ems`, `blood_pressure`, `menstrual`, `infrarot`, `general`.

**Detection — keyword matching against term sets:**

| Category | Keywords |
|----------|----------|
| `tens_ems` | tens, ems, reizstrom, elektroden, schmerztherapie, muskelstimulation |
| `blood_pressure` | blutdruck, blutdruckmess, oberarm, handgelenk, hypertonie, blood pressure |
| `menstrual` | menstrual, regel, periode, menstruation, periodenschmerz |
| `infrarot` | infrarot, rotlicht, wärmelampe, infrared |
| `general` | fallback — no filtering |

**Ambiguity resolution:** If keyword matches multiple categories, priority order is `menstrual > tens_ems > blood_pressure > infrarot > general`. Menstrual wins because it's a superset (includes menstrual-specific + general TENS devices).

---

## 2. Category-Scoped Product Filtering

New function `get_products_for_category(category: str) -> List[Product]` in `product_catalog.py`.

| Category | Includes | Excludes |
|----------|----------|----------|
| `tens_ems` | `type=tens` or `type=ems`, EXCEPT `usage_restriction=menstrual_only` | EM 50, EM 55, all BM/BC/IL products |
| `blood_pressure` | `type=upper_arm` or `type=wrist` | All EM/IL products |
| `menstrual` | `usage_restriction=menstrual_only` PLUS general TENS (EM 49, EM 59, EM 89) | BM/BC/IL products |
| `infrarot` | `category=infrarot` | EM/BM/BC products |
| `general` | Full catalog | Nothing excluded |

`get_beurer_company_context()` gets a new `keyword` parameter. When provided:
1. Calls `detect_article_category(keyword)`
2. Calls `get_products_for_category(category)`
3. Passes only those product SKUs instead of full `BEURER_PRODUCT_CATALOG.keys()`

`get_beurer_sitemap_urls()` gets a `category` parameter:
- `tens_ems` / `menstrual`: exclude HealthManager Pro URL, exclude blood pressure category URLs
- `blood_pressure`: exclude TENS/EMS category URLs
- `general`: no filtering

---

## 3. Product Specs as Structured Injection

Replace flat product name list in `_format_company_context()` with structured specs from the catalog:

```
=== PRODUCTS FOR THIS ARTICLE (use ONLY these, with EXACTLY these specs) ===
- EM 49: 64 Programme, 2 Kanäle, TENS/EMS, kein Bluetooth, keine App
- EM 59: 64 Programme, 2 Kanäle, 4 Elektroden, Wärmefunktion, kein Bluetooth, keine App
- EM 89: 64 Programme, 4 Kanäle, 8 Elektroden, Wärmefunktion, kein Bluetooth, keine App

DO NOT mention any product not listed above. DO NOT modify these specifications.
```

New function `format_product_specs(products: List[Product], language: str) -> str` in `product_catalog.py` generates this from catalog data. The `kein Bluetooth, keine App` text is generated from `has_bluetooth` and `app_compatible` fields — presented as fact, not as a negative instruction.

For blood pressure articles, HealthManager Pro only appears where `app_compatible=true`:
```
- BM 27: Oberarm, keine App
- BM 54: Oberarm, Bluetooth, HealthManager Pro kompatibel
```

---

## 4. Video URL Removal from Schema

Remove `video_url` and `video_title` from `article_schema.py` (the structured output schema passed to Gemini). If the field doesn't exist, Gemini can't fill it with fabricated URLs.

- Leave fields in HTML renderer so existing articles with manually-added URLs still render
- Remove video URL stripping code from `_post_pipeline_safety()` (dead code)

---

## 5. Source Quality Gate

Changes to `_build_verified_sources()` in `blog_writer.py`:

1. **Hard cap 2-3 sources.** Minimum 2, maximum 3. If fewer than 2 pass quality checks, retry enrichment once.
2. **Drop generic descriptions.** After enrichment, check if description matches fallback template `"Source: .* — relevant to .*"`. If so, drop the source rather than keeping it with a placeholder.
3. **Source type filtering in code.** Reject URLs containing: `reddit.com`, `gutefrage.net`, `forum`, `facebook.com`, `tiktok.com`, `instagram.com`. Deterministic, can't be ignored by Gemini.
4. **Description minimum quality.** Reject descriptions shorter than 30 characters.

Net effect: 2-3 professional sources with real descriptions, or fewer rather than padding. Footnote sync in cleanup handles orphaned markers.

---

## 6. Post-Generation Safety Net

Slimmed-down `_post_pipeline_safety(article, keyword, category)` handles only issues that can't be fully prevented upstream.

### 6a. Unicode cleanup (issue 7)
Strip zero-width characters (U+200B, U+FEFF, U+200C, U+200D) from all text fields. Simple regex pass. Also added to `cleanup.py` HTML cleaning.

### 6b. EM 89 spec correction in prose (issue 3)
Expand current table-only fix to all text fields (section content, FAQs, PAAs, intro, direct answer). Same patterns: "über 70 Programme" → "64 Programme", "2 Kanäle" → "4 Kanäle" near "EM 89".

### 6c. Catalog-aware product mention validation (issue 6)
Scan all text for SKU patterns (`(BM|BC|EM|IL)\s?\d{2,3}`). Any SKU not in the filtered product set for this category:
- Table rows: remove the row
- Prose: flag as warning in pipeline report (too risky to auto-remove from flowing text)

### 6d. HealthManager Pro / app claims leak-through (issue 1)
If category is `tens_ems` and text contains "HealthManager Pro", "App-Anbindung", "Bluetooth" near TENS/EM context:
- Table cells: remove (existing logic)
- `<li>` items: remove
- Prose: flag as warning

### 6e. EM 50/55 leak-through (issue 4)
If category is `tens_ems` (not menstrual), scan for EM 50/EM 55:
- Table rows: remove
- `<li>` items: remove
- Image slots: clear (existing logic)
- Prose: flag as warning

### 6f. Typo fixes (issue 10)
Lookup dict of known typos applied across all text fields. Starting set: `"letzen" → "letzten"`.

### Not included
- **Unattributed statistics (issue 8):** Too hard to detect deterministically. Rely on prompt.
- **Cross-sell content (issue 9):** Fully prevented by category-scoped sitemap URLs.

---

## 7. File Changes

| File | Change |
|------|--------|
| `blog/product_catalog.py` | Add `detect_article_category()`, `get_products_for_category()`, `format_product_specs()` |
| `blog/beurer_context.py` | Add `keyword` param to `get_beurer_company_context()` and `category` param to `get_beurer_sitemap_urls()`, filter products and URLs by category |
| `blog/stage2/blog_writer.py` | Update `_format_company_context()` to use structured product specs. Tighten `_build_verified_sources()` with quality gate and source filtering |
| `blog/stage2/article_schema.py` | Remove `video_url` and `video_title` fields |
| `blog/article_service.py` | Rewrite `_post_pipeline_safety()` with full scope (unicode, EM 89 prose, catalog SKU validation, app claim/EM 50 leak-through, typos). Remove video URL stripping. Pass keyword to context builder. |
| `blog/stage_cleanup/cleanup.py` | Add unicode zero-width character stripping to HTML cleaning |

**Unchanged:** `pipeline.py`, Stage 3, Stage 4, Stage 5, `product_catalog.json`.

**Call chain after:**
```
article_service.py
  → detect_article_category(keyword)
  → get_beurer_company_context(keyword=keyword)     # filtered products + specs
  → get_beurer_sitemap_urls(category=category)       # filtered URLs
  → Stage 2 generates with scoped context
  → _post_pipeline_safety(article, keyword, category) # catches leak-through
```
