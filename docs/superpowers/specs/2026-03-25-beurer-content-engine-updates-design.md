# Beurer Content Engine Updates — Design Spec

**Date:** 2026-03-25
**Status:** Approved
**Deadline:** Content engine fixes before March 28 article regeneration
**Context:** Anika sent detailed article feedback + German webshop product catalog. Feedback freeze is March 27; after that all 15 articles are regenerated.

---

## 1. Product Catalog & Validation Layer

### Problem

The existing `report/constants.py` catalog has 28 Beurer products with no webshop URLs and no priority tiers. A US-only product appeared in a German article because there is no validation gate. Anika provided a 33-product German webshop catalog with URLs, priorities, and 5 category pages.

### Design

**Separate catalog for blog pipeline** — `report/constants.py` stays for social listening (tracks competitor products, different concerns). A new `blog/product_catalog.json` + `blog/product_catalog.py` serves article generation.

**`blog/product_catalog.json`:**

```json
{
  "products": {
    "BM 27": {
      "url": null,
      "priority": 1,
      "category": "blood_pressure",
      "type": "oberarm"
    },
    "BC 27": {
      "url": null,
      "priority": 2,
      "category": "blood_pressure",
      "type": "handgelenk"
    }
  },
  "categories": {
    "blutdruckmessgeraete": null,
    "oberarm": null,
    "handgelenk": null,
    "tens": null,
    "infrarotlampen": null
  },
  "meta": {
    "source": "excel",
    "updated": "2026-03-25",
    "note": "URLs pending confirmation from Beurer — populate once confirmed"
  }
}
```

> **Note:** URLs are `null` until Beurer confirms working links (expected March 26). `null` distinguishes "not yet populated" from "product has no webshop page." The validation gate checks product mentions regardless of URL availability.

**`blog/product_catalog.py`** — PIM-ready loader:

```python
class ProductCatalog:
    products: Dict[str, Product]      # SKU -> {url, priority, category, type}
    categories: Dict[str, str]        # key -> URL
    priority_products: List[str]      # SKUs with priority <= given level

def load_catalog() -> ProductCatalog:
    """Load from JSON. Later: swap for API fetch without interface change."""

def validate_product_mentions(html: str, catalog: ProductCatalog) -> ValidationResult:
    """Regex scan for Beurer product patterns ([A-Z]{2} ?\\d{2,3}), flag any not in catalog."""

def get_product_url(sku: str) -> Optional[str]:
    """Return webshop URL for a product SKU, or None if not yet populated."""

def get_priority_products(max_priority: int = 1) -> List[Product]:
    """Return products at or above the given priority level."""
```

**New Stage 5.5 — Product Validation:**

Runs after Stage 5 (internal linking), before cleanup. Deterministic gate (no LLM).

**Must be wired into both orchestration paths:**
- `blog/pipeline.py` — batch pipeline (`process_single_article`)
- `blog/article_service.py` — single article API (`_run_stages_4_5_cleanup()`, between Stage 5 block ending at line 196 and cleanup block starting at line 199)

**Steps:**

1. Regex scan for Beurer product patterns — restricted to known prefixes: `(?:BM|BC|EM|IL)\s?\d{2,3}`
2. Each match checked against catalog
3. Products NOT in catalog — replacement heuristic:
   - Find the highest-priority product in the same category AND type (oberarm/handgelenk/etc.)
   - If no type match, replace with a category-level mention without specific SKU (e.g., "Beurer Oberarm-Blutdruckmessgeraet" instead of "Beurer BM 99")
   - If the invalid product is in a sentence that only makes sense with a specific SKU, remove the entire sentence
4. Product links rewritten to use webshop URLs from catalog (when URLs are non-null)
5. Category page links injected where relevant (addresses "too few category links" feedback)

**Priority products** (Prio 1: BM 25, BM 27, BM 81, EM 50, EM 55, EM 59, EM 89, IL 50, IL 60) get preferential treatment in Stage 2 prompt — listed first, flagged as "focus products."

### Full product list from Anika's catalog

| SKU | Category | Priority |
|-----|----------|----------|
| BC 21 | blood_pressure (handgelenk) | — |
| BC 27 | blood_pressure (handgelenk) | Prio 2 |
| BC 28 | blood_pressure (handgelenk) | — |
| BC 44 | blood_pressure (handgelenk) | — |
| BC 51 | blood_pressure (handgelenk) | — |
| BC 54 | blood_pressure (handgelenk) | — |
| BC 87 | blood_pressure (handgelenk) | — |
| BM 25 | blood_pressure (oberarm) | Prio 1 |
| BM 27 | blood_pressure (oberarm) | Prio 1 |
| BM 28 | blood_pressure (oberarm) | — |
| BM 38 | blood_pressure (oberarm) | — |
| BM 40 | blood_pressure (oberarm) | — |
| BM 45 | blood_pressure (oberarm) | — |
| BM 48 | blood_pressure (oberarm) | — |
| BM 49 | blood_pressure (oberarm) | — |
| BM 51 | blood_pressure (oberarm) | — |
| BM 53 | blood_pressure (oberarm) | Prio 2 |
| BM 54 | blood_pressure (oberarm) | Prio 3 |
| BM 58 | blood_pressure (oberarm) | — |
| BM 59 | blood_pressure (oberarm) | Prio 3 |
| BM 64 | blood_pressure (oberarm) | Prio 2 |
| BM 81 | blood_pressure (oberarm) | Prio 1 |
| BM 96 | blood_pressure (oberarm) | Prio 3 |
| EM 49 | pain_tens | — |
| EM 50 | pain_tens | Prio 1 |
| EM 55 | pain_tens | Prio 1 |
| EM 59 | pain_tens | Prio 1 |
| EM 89 | pain_tens | Prio 1 |
| IL 11 | infrarot | — |
| IL 21 | infrarot | — |
| IL 35 | infrarot | — |
| IL 50 | infrarot | Prio 1 |
| IL 60 | infrarot | Prio 1 |

**Category pages:** Blutdruckmessgeraete, Oberarm-Blutdruckmessgeraete, Handgelenk-Blutdruckmessgeraete, TENS-Geraete, Infrarotlampen (URLs pending).

### PIM Integration (Future)

Anika offered PIM API access or regular exports. The `load_catalog()` function is designed so the data source can be swapped from JSON file to API fetch without changing the interface or any consuming code. No action needed now.

---

## 2. Content Engine Fixes

All changes must land before the March 28+ article regeneration.

### 2a. Lettered Footnotes

**Problem:** Beurer uses numbers for campaigns; numbered footnotes (1, 2, 3) cause confusion.

**Changes:**
- `blog/shared/html_renderer.py` line 918: change `<ol class="sources-list">` to `<ol class="sources-list" type="A">`
- `dashboard/lib/html-renderer.ts`: same change in the TypeScript renderer
- Stage 2 Gemini prompt: instruct to emit `<sup>A</sup>`, `<sup>B</sup>` instead of `<sup>1</sup>` for in-text source references
- Cleanup stage: if superscript letter count does not match source count, add a warning to `CleanupResult.warnings` (non-blocking — does not fail the pipeline). Iterate `<sup>` tags across all section content fields and compare count against `len(Sources)`.
- Existing articles with numbered footnotes are NOT retroactively fixed — this only applies to newly generated/regenerated articles.

**Format:** In-article: `...laut einer Studie<sup>A</sup>...` — At bottom: `[A] Source name, URL`

### 2b. "Kurze Antwort" to "Das Wichtigste in Kuerze"

**Problem:** "Kurze Antwort" implies the headline is a question, but many headlines are not questions.

**Changes:**
- `blog/shared/html_renderer.py` line 35: change `"direct_answer": "Kurze Antwort:"` to `"direct_answer": "Das Wichtigste in K\u00fcrze:"`
- `dashboard/lib/html-renderer.ts`: same label change
- No field rename needed — `Direct_Answer` stays as the JSON key, only the display label changes

### 2c. Grammar at Insertions

**Problem:** The correction agent (inline edits via Gemini) sometimes produces broken spacing around parentheses, periods, and formatted text. Example: `TENS (Transkutane Elektrische Nervenstimulation)ist eine...`

**Changes:**
Add a whitespace normalization function in `blog/stage_cleanup/cleanup.py` (not in `replacement_validator.py` — keep the validator's contract as "validate", not "validate and transform"). Run as part of the cleanup stage on every article.

**Normalization rules:**
- Ensure space before `(` unless preceded by newline, tag-open (`>`), or start of string
- Ensure space after `)` unless followed by punctuation (`,`, `.`, `:`, `;`)
- Ensure space after `.`, `:`, `;` unless followed by `</` (closing tag)
- Ensure space at **tag-text boundaries**: space between closing tag and adjacent text (`</strong>text` -> `</strong> text`) and between text and opening tag (`text<strong>` -> `text <strong>`). Do NOT add spaces inside tags (e.g., `<strong> text </strong>` would be wrong).

This runs deterministically on every article — catches LLM spacing errors without relying on the LLM to get it right. Also benefits inline edits since cleanup runs after edit application.

### 2d. Internal Linking Rules

**Problem:** Stage 5 uses sitemap URLs indiscriminately. Links to "App Welt" and "Produktberater" appear in articles (not relevant). Category overview page links are underrepresented.

**Changes to Stage 5:**
- At the call site (`article_service.py` line 182, `pipeline.py`): replace `sitemap_product_urls` with catalog-derived product URLs (no `Stage5Input` model change needed — same field, better data)
- Add a new `sitemap_category_urls` field to `Stage5Input` for category page URLs from catalog. These are listed separately in the prompt with explicit instruction: "Include at least 1-2 links to category overview pages, especially in introductions and section conclusions."
- Blocklist: implement in `InternalLinker._build_link_pool()` — filter out any URLs matching `/app-welt/` or `/produktberater/` patterns. This ensures all callers are protected.
- Category links get "higher weight" meaning: listed first in the prompt's AVAILABLE LINKS section, with an annotation like "(Kategorie-Uebersicht — bevorzugt verlinken)"

**Linking rules:**
- DO link to product pages using catalog URLs (Sheet "Produkte")
- DO link to category overview pages using catalog URLs (Sheet "Kategorien")
- DO NOT link to App Welt or Produktberater pages
- Increase category page link density (currently underrepresented per Anika's feedback)

### 2e. External Source Validation Enhancement

**Problem:** Some source URLs return 200 but redirect to the homepage of the source site. Stage 4 currently only checks HTTP status, not redirect destination.

**Enhancement to Stage 4:**
- After getting a 200 response, check if the final URL (after redirects) is a homepage
- **Path-based detection (primary):** compare `urlparse(final_url).path` against `/`, `/en/`, `/de/`, or paths with only 1-2 segments
- **Title heuristic (stretch goal — skip for March 28 if tight on time):** requires a full GET request + HTML title parsing, which the current HEAD-only `HTTPChecker` doesn't do. Only add if path-based detection produces too many false positives.
- New status: `URLStatus.REDIRECTED_TO_HOMEPAGE` added to enum in `stage4_models.py`
- Same treatment as dead URLs: Gemini finds replacement or link is removed
- If no good replacement found: remove the source entirely rather than linking to a homepage

### 2f. Repetition Reduction

**Problem:** Some articles repeat the same information across multiple sections.

**Approach (two-layer):**

1. **Prompt-level (Stage 2):** Add explicit instruction: "Never repeat the same fact, claim, or statistic in multiple sections. Each piece of information should appear exactly once, in the most relevant section."

2. **Check-level (Stage 3):** During quality check, add a deduplication instruction to the Gemini review: "Identify any facts, claims, or statistics that appear in more than one section. For each duplicate, keep it in the most relevant section and rewrite the other occurrence as a cross-reference (e.g., 'Wie in Abschnitt X erlaeutert...')."

Start with prompt-level enforcement. If repetition persists after regeneration, add the explicit Stage 3 dedup check.

---

## 3. Dashboard/Platform Fixes

No hard deadline — can run in parallel with content engine work.

### 3a. Inline Comment URL Edits

**Root cause:** `find_html_passage()` resolves the user's plain-text selection to HTML correctly. But the Gemini prompt (`article_service.py` line 781) sends only the plain text + comment. When the comment says "change URL to X", Gemini can only modify anchor text — it never sees the `href` attribute.

**Fix:**
- Add URL-edit detection heuristic:
  ```python
  is_url_edit = bool(re.search(r'https?://|link|url|verlinkung', edit["comment"], re.IGNORECASE))
  ```
- If `is_url_edit` is true: send the `original_html` (from `resolved[i]["original_html"]`, line 749) to Gemini instead of `r['plain_text']`
- Add prompt rule: "When asked to change a URL/link, modify the href attribute value in the anchor tag."
- Validate that the replacement contains a valid `href` attribute
- **Validation handling:** When `is_url_edit` is true, pass both original and replacement to `replacement_validator.py` with `is_html=True` so tag-balance and length checks operate on HTML, not plain text vs HTML mismatch

### 3b. Change Visibility After Edit

**Problem:** After inline edits are processed, reviewers must manually search for what changed.

**Fix:**
- `apply_inline_edits` return payload: add a `changes` array:
  ```json
  [{"section": "section_03_content", "original_snippet": "...", "revised_snippet": "..."}]
  ```
- Dashboard frontend: render changes as a diff-style highlight panel (toast or sidebar). Frontend component to be identified during implementation (likely the article editor/preview component that handles inline edits).
- Optional: scroll to the first change in the article preview iframe via `postMessage`

### 3c. Text Selection for Normal Comments

**Problem:** Normal (non-inline) comments cannot reference a specific text passage.

**Fix:**
- Frontend: when user has text selected in the iframe at "add comment" time, capture selection as `selected_text`
- Backend: add optional `selected_text` field to `article_comments` table/payload
- Display: comments with `selected_text` show a quoted block above the comment text
- Interaction: hovering over a comment with `selected_text` highlights the matching passage in the iframe. Note: `find_html_passage()` is a Python backend function — for client-side highlighting, reimplement the plain-text-to-HTML matching logic in JavaScript (simpler subset: just find the plain text in the iframe's `textContent` and highlight the corresponding DOM range)

---

## 4. Deferred Items (Documented, Not Implemented)

### 4a. Amazon Review Summaries (Item 2g)

**Status:** Awaiting legal clearance from Beurer.

**Feasibility:** Confirmed. Amazon reviews already crawled via `AmazonCrawler`, stored in `social_items` with entity matching via `item_entities`. Aspect-based sentiment in `item_aspects` enables grouping by theme.

**Planned approach:**
- Query `social_items` where `source = 'amazon'` + join `item_entities` for target SKU
- Filter to `sentiment = 'positive'`, group by aspect themes
- Gemini synthesizes 3-5 bullet summary (not quoting reviews — synthesized themes)
- Output: `"Was Nutzer am Beurer {SKU} besonders schaetzen:"` + bullet list
- Feature flag: `include_review_summary: bool = False` — flipped on after legal clearance
- Minimum threshold: 5+ reviews with entity match; below that, section omitted

**Template:**
```json
{
  "review_summary": {
    "product_sku": "BM 27",
    "positive_themes": [
      {"theme": "Intuitive Bedienung", "detail": "grosses, gut lesbares Display"},
      {"theme": "Manschettensitzkontrolle", "detail": "integrierte Sitzkontrolle gibt Sicherheit"}
    ],
    "review_count": 47,
    "avg_sentiment_score": 0.82
  }
}
```

### 4b. BM 53 Validation Study

**File:** `Beuer BM53_Manuscript 20260310_clean.docx` — ISO 81060-2:2018 clinical validation in diabetic patients.

**Status:** Can be used as product context/source for BM 53-related articles, but only once the study is published online. Not actionable until then.

### 4c. PIM Integration

**Status:** Anika offered PIM API connection or regular product data exports. The `blog/product_catalog.py` loader is designed with a stable interface so the data source can be swapped from JSON to API without restructuring consuming code. No action needed until Beurer provides API access.

---

## 5. Execution Plan

### Workstreams

| Workstream | Items | Deadline | Blockers |
|---|---|---|---|
| **A: Product Catalog** | 1, 2d | Before regeneration (Mar 28+) | URLs pending Beurer (Mar 26) |
| **B: Content Engine** | 2a, 2b, 2c, 2e, 2f | Before regeneration (Mar 28+) | None |
| **C: Dashboard Fixes** | 3a, 3b, 3c | No hard deadline | None |
| **D: Deferred** | 2g, BM 53 study, PIM | TBD | Legal, publication, API access |

### Execution Order

1. `blog/product_catalog.py` + JSON structure (A) — foundation
2. 2b label rename (B) — trivial, independent
3. 2a lettered footnotes (B) — independent
4. 2c grammar normalization (B) — independent
5. 2e homepage-redirect detection (B) — independent
6. 2f repetition reduction prompt (B) — independent
7. 2d internal linking rules in Stage 5 (A) — depends on step 1
8. New Stage 5.5 product validation gate (A) — depends on step 1

Steps 2-6 can all run in parallel. Steps 7-8 run after step 1.

Workstream C (dashboard fixes 3a-3c) is fully independent and can run in parallel with A+B.

### Timeline

- **Now - March 26:** Implement workstreams A (catalog structure, no URLs yet) + B (all content engine fixes)
- **March 26:** Receive confirmed URLs from Beurer, populate catalog
- **March 27:** Feedback freeze
- **March 28+:** Regenerate all 15 articles with full pipeline (product validation, lettered footnotes, renamed label, dedup, enhanced URL verification, catalog-driven linking)
- **Parallel:** Workstream C (dashboard fixes) — no deadline pressure

### Files Modified

| File | Changes |
|---|---|
| `blog/product_catalog.json` | **NEW** — Product catalog data |
| `blog/product_catalog.py` | **NEW** — Catalog loader + validation functions |
| `blog/shared/html_renderer.py` | 2a (lettered sources), 2b (label rename) |
| `dashboard/lib/html-renderer.ts` | 2a (lettered sources), 2b (label rename) |
| `blog/stage_cleanup/cleanup.py` | 2a (footnote count warning), 2c (whitespace normalization) |
| `blog/stage2/stage_2.py` | 2a (footnote format in prompt), 2f (dedup instruction) |
| `blog/stage4/stage_4.py` | 2e (homepage redirect detection) |
| `blog/stage4/stage4_models.py` | 2e (new `REDIRECTED_TO_HOMEPAGE` status) |
| `blog/stage5/stage_5.py` | 2d (blocklist in `_build_link_pool()`, category emphasis in prompt) |
| `blog/stage5/stage5_models.py` | 2d (new `sitemap_category_urls` field on `Stage5Input`) |
| `blog/pipeline.py` | Wire Stage 5.5, pass catalog URLs to Stage 5 |
| `blog/article_service.py` | Wire Stage 5.5 in `_run_stages_4_5_cleanup()`, pass catalog URLs to Stage 5, 3a (URL-edit detection + HTML-aware prompt) |
| `dashboard/app/api/blog-article/route.ts` | 3b (change visibility), 3c (selected_text field) |
| Frontend component (TBD) | 3b (diff highlight panel), 3c (text selection capture + hover highlight) |
