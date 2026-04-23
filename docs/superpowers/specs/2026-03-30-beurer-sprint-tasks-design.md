# Sprint Tasks Design Spec — KW 14/15

**Date:** 2026-03-30
**Status:** Draft
**Branch:** master
**Scope:** 6 tasks from Formmed client meeting — meta SEO, AI visibility, Salesforce import, known issues, multi-language, hreflang

---

## Task 1: Meta Title + Description — SERP Preview in Article Modal

### Context

Articles already generate `Meta_Title` and `Meta_Description` via the Gemini writer. Both fields exist in `ArticleOutput` (`blog/shared/models.py:106-107`), are stored in `article_json` JSONB, and `meta_description` has its own DB column. The dashboard article modal (`styles/dashboard_template.html:6437-6484`) shows the article in an iframe with a header bar, but doesn't surface the meta fields as copyable text.

Anika wants to copy meta title/description from the dashboard into Beurer's CMS (Makaria) without opening the HTML source.

### Changes

#### 1.1 Update character limits

**File:** `blog/shared/models.py`
- `Meta_Title` field description: change `≤55` → `≤60`
- `meta_title_length` validator (line 294): truncate threshold from 55 → 60, smart break at 57

**File:** `blog/stage_cleanup/cleanup.py`
- `_validate_article_structure` (line 265): change `max 55` → `max 60`

**File:** `blog/shared/models.py`
- `Meta_Description` field description: change `≤160` → `≤155`
- `meta_description_length` validator (line 306): truncate threshold from 160 → 155, ellipsis at 152

**File:** `blog/stage_cleanup/cleanup.py`
- Update matching validation for meta description max chars

**File:** `dashboard/lib/article-generator.ts`
- Update any matching character limit references if present

#### 1.2 Add `meta_title` DB column

**File:** `migrations/010_blog_article_meta_title.sql` (new — next after existing 009)

```sql
ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS meta_title TEXT;

-- Backfill from article_json for existing articles
UPDATE blog_articles
SET meta_title = article_json->>'Meta_Title'
WHERE meta_title IS NULL
  AND article_json->>'Meta_Title' IS NOT NULL;
```

**File:** `blog/article_service.py`
- In `generate_article()` (around line 398): extract and save `meta_title` alongside `meta_description`
- In `regenerate_article()` (around line 640): same extraction for regeneration
- In `pipeline.py` (around line 718): already extracts `meta_title` — verify it's saved to DB

#### 1.3 SERP preview card in article modal

**File:** `styles/dashboard_template.html`

Add a Google-style SERP preview between the article modal header and the iframe. Positioned inside `.article-modal-panels` above the iframe content area.

**Design:**

```
+----------------------------------------------------------+
| Google Search Preview                          [Copy All] |
+----------------------------------------------------------+
| beurer.com > Ratgeber > Blutdruck                        |
| Meta Title Here — Max 60 Characters              [Copy]  |
| Meta description text here, max 155 characters.   [Copy] |
| This is what users see in Google search results.         |
+----------------------------------------------------------+
```

**Styling:**
- Card with subtle border, white background, `border-radius: 8px`
- Title: `color: #1a0dab` (Google blue), `font-size: 20px`, `font-family: arial`
- URL breadcrumb: `color: #006621` (Google green), `font-size: 14px`
- Description: `color: #545454`, `font-size: 14px`, `line-height: 1.58`
- Copy buttons: small clipboard icon buttons, inline right-aligned
- Character count indicators below each field (e.g., "52/60 chars") with color warning when near limit

**Copy behavior:**
- Individual copy buttons per field (meta title, meta description)
- "Copy All" button copies both as formatted text: `Meta Title: ...\nMeta Description: ...`
- Visual feedback: button text briefly changes to checkmark

**Data source:** Read from the article's `article_json` field (already fetched when opening the modal). Fields: `article_json.Meta_Title` and `article_json.Meta_Description`.

**Visibility:** Only shown when the article has status `completed`, `review`, `approved`, or `published`. Hidden during `generating`/`regenerating`/`failed`.

---

## Task 2: AI Visibility Dashboard — Peekaboo API Visualization

### Context

The Peekaboo API integration already exists on master (`dashboard/app/api/media-visibility/route.ts`). It fetches 3 endpoints in parallel:
- `/brands/{id}/snapshot` — visibility score, competitors, prompts, sources, traffic
- `/brands/{id}/prompts` — detailed prompt data with trend/bestScore/worstScore
- `/brands/{id}/competitors` — detailed competitor data with monthlyVisits/change

The `transform()` function (line 59) already structures this into: `overview`, `competitors`, `competitorSummary`, `prompts`, `sources`, `suggestions`, `traffic`, `snapshotDate`.

The dashboard has a `tab-media` ("Medien-Sichtbarkeit") tab, but the current rendering is either empty or minimal. We need to build the full visualization.

### Data already available from Peekaboo API

| Section | API Fields | Chart Type |
|---------|-----------|------------|
| Overview | `score`, `rank`, `totalCitations`, `totalChats`, `trend` | KPI cards |
| Competitors | `[{name, score, change, monthlyVisits}]` | Bar chart + table |
| Prompts | `[{text, category, mentions, score, aiModels, trend}]` | Table with AI model badges |
| Sources | `[{domain, mentions, aiModels}]` | Horizontal bar chart |
| Traffic | `monthlyVisits`, `bounceRate`, `pagesPerVisit`, `avgTimeOnSite` | KPI cards (secondary) |

### Dashboard layout

The `tab-media` tab will be reorganized into 4 sections:

#### Section 1: Overview KPI Cards

```
+---------------------------------------------------------------+
| AI Visibility Score    | Total Citations | Rank  | Trend      |
| 72/100                 | 1,847           | #3    | +5.2% ↑    |
+---------------------------------------------------------------+
```

4-column KPI grid. Score card gets accent styling. Trend shows WoW change with colored arrow.

#### Section 2: Beurer vs Competitors

```
+---------------------------------------------------------------+
| AI Sichtbarkeit — Wettbewerbsvergleich                        |
| +---+                                                          |
| | Beurer    ████████████████ 72  (+5.2%)                      |
| | Omron     ██████████████ 65    (-2.1%)                      |
| | Withings  ████████████ 58      (+1.4%)                      |
| | Medisana  █████████ 41         (—)                          |
| +---+                                                          |
+---------------------------------------------------------------+
```

Horizontal bar chart (Chart.js) with score labels. Each bar has brand color. Change percentage shown inline. Data from `competitors` array.

Below the chart: detail table with columns: Brand, Score, Monthly Visits, Change.

#### Section 3: AI Model Breakdown (Prompt Analysis)

```
+---------------------------------------------------------------+
| Prompt-Analyse — Welche KI-Modelle zitieren Beurer?           |
| Filter: [Alle] [ChatGPT] [Perplexity] [Gemini] [AI Mode]    |
+---------------------------------------------------------------+
| Prompt                        | Score | Mentions | AI Models  |
| "Bestes Blutdruckmessgerät"   | 85    | 23       | 🟢🔵🟣    |
| "TENS Gerät Empfehlung"       | 72    | 18       | 🟢🔵      |
| ...                           |       |          |            |
+---------------------------------------------------------------+
```

Table with prompt text, score, mention count. AI model column shows colored dots per model (ChatGPT=green, Perplexity=blue, Gemini=purple, AI Mode=orange). Each dot from the `aiModels` array on each prompt.

Filter bar to show only prompts where a specific AI model cites Beurer.

Aggregate summary above table: pie chart or donut showing citation share per AI model across all prompts.

#### Section 4: Source Breakdown

```
+---------------------------------------------------------------+
| Quellen-Analyse — Welche Domains treiben Zitierungen?         |
+---------------------------------------------------------------+
| chip.de          ████████████████████  34 mentions            |
| testsieger.de    ███████████████  27 mentions                 |
| stiftungwarest.. ██████████  18 mentions                      |
| ...                                                           |
+---------------------------------------------------------------+
```

Horizontal bar chart sorted by mention count. Each bar shows domain name + count. Data from `sources` array. Top 15 sources shown, remainder collapsed under "Weitere anzeigen".

### Localization

Add German and English labels to the existing localization objects in `dashboard_template.html`:

```javascript
// German
media_ai_score: 'AI Sichtbarkeit',
media_total_citations: 'Zitierungen gesamt',
media_rank: 'Rang',
media_trend: 'Trend',
media_competitor_title: 'Wettbewerbsvergleich',
media_prompt_title: 'Prompt-Analyse',
media_source_title: 'Quellen-Analyse',
media_filter_all: 'Alle',
// English equivalents...
```

### Data fetching

**File:** `styles/dashboard_template.html`

The template's `renderMediaTab()` function calls the `/api/media-visibility` endpoint client-side (fetch from browser). The existing endpoint returns cached data (60-min TTL). No server-side aggregation needed — data comes pre-structured from Peekaboo API.

### File manifest

| File | Action |
|------|--------|
| `styles/dashboard_template.html` | Modify — rewrite `renderMediaTab()` with 4-section layout |
| `dashboard/app/api/media-visibility/route.ts` | No changes — existing transform is sufficient |

---

## Task 3: Salesforce Weekly Import + Customer Success Tab

### Existing spec

A complete design spec already exists at `docs/superpowers/specs/2026-03-26-salesforce-service-cases-design.md`. It covers:
- `service_cases` DB table schema with dedup by `case_id`
- Import pipeline (`services/service_case_importer.py`) with HTML-XLS and CSV parsing
- Upload route (`routes/imports.py`)
- TypeScript aggregator (`dashboard/lib/aggregator/service-cases/`)
- Kundendienst tab layout (heatmap, trends, alerts)
- Content engine integration (service case summary injected into article context)

### Additions to existing spec

#### 3.1 Dashboard upload UI

**File:** `styles/dashboard_template.html`

Add an upload button in the Kundendienst tab header, next to the date filter:

```
+---------------------------------------------------+
| Kundendienst-Insights              [CSV hochladen] |
| Date filter: [7d] [30d] [90d] [All]              |
+---------------------------------------------------+
```

Upload button opens a file picker (`accept=".csv,.xls,.xlsx"`). On file select:
1. Show progress indicator
2. POST to `/api/kundendienst/upload` (new Next.js API route) which proxies to Python backend
3. On success: show toast with import counts, refresh tab data
4. On error: show error message

**File:** `dashboard/app/api/kundendienst/route.ts` (new)
- POST handler: accepts multipart form data, proxies file to Python backend `POST /api/v1/social-listening/import/service-cases`
- GET handler: fetches aggregated service case data for the dashboard

#### 3.2 Executive Overview KPI card

**File:** `styles/dashboard_template.html`

Add a single KPI card to the Executive Overview tab's KPI grid:

```
+-------------------------------------------------------------------+
| Total Mentions | Sentiment | Top Category | ... | Service Cases ↗ |
| 1,247          | 68% pos   | Blutdruck    |     | 245 diese Woche |
+-------------------------------------------------------------------+
```

- Card shows total cases in the current date range
- Clickable — navigates to `tab-kundendienst`
- Shows WoW delta if previous period data available
- Only visible when `kundendienstInsights` data exists (graceful hide otherwise)

Data source: `DASHBOARD_DATA.kundendienstInsights.summary.totalCases`

---

## Task 4: Known Issues per Product

### Context

On master, the product catalog is stored in `blog/product_catalog.json` as a dict of `{ model_code: { url, priority, category, type } }`. Product context flows through `blog/beurer_context.py` → `blog/article_service.py` → Stage 2 writer.

Anika will check with the Health Manager Pro team about known EM 59/BM software issues. This data needs to be available to the article generation pipeline.

### Data model

**File:** `blog/product_catalog.json`

Add optional `known_issues` array to product entries:

```json
{
  "products": {
    "EM 59": {
      "url": null,
      "priority": 1,
      "category": "pain_tens",
      "type": "tens_ems",
      "known_issues": [
        {
          "issue": "Bluetooth connection drops when using Health Manager Pro on iOS 17+",
          "severity": "high",
          "source": "internal_feedback",
          "date_reported": "2026-03-28",
          "resolved": false
        }
      ]
    }
  }
}
```

**Fields:**
- `issue` (string, required): Description of the known issue
- `severity` (string, required): `"high"` | `"medium"` | `"low"`
- `source` (string, required): Where the info came from — `"internal_feedback"` | `"salesforce"` | `"social_listening"` | `"manual"`
- `date_reported` (string, required): ISO date
- `resolved` (boolean, optional, default false): Whether the issue has been fixed

### Product catalog module update

**File:** `blog/product_catalog.py`

Add function to retrieve known issues for a product:

```python
def get_product_known_issues(model_code: str) -> list[dict] | None:
    """Return unresolved known issues for a product, or None if none exist."""
    product = CATALOG.get("products", {}).get(model_code, {})
    issues = product.get("known_issues", [])
    # Filter to unresolved only
    active = [i for i in issues if not i.get("resolved", False)]
    return active or None
```

### Article generation integration

**File:** `blog/article_service.py`

In `generate_article()`, after loading product context, check for known issues relevant to the article's keyword:

```python
# After building company_context (around line 273)
from blog.product_catalog import get_product_known_issues, find_product_for_keyword

product_model = find_product_for_keyword(keyword)
if product_model:
    known_issues = get_product_known_issues(product_model)
    if known_issues:
        issues_text = "\n".join(
            f"- [{i['severity'].upper()}] {i['issue']}" for i in known_issues
        )
        # Append to keyword_instructions
```

**File:** `blog/product_catalog.py`

Add `find_product_for_keyword(keyword: str) -> str | None` that matches a keyword against product model codes (e.g., keyword "Beurer EM 59 Erfahrung" → "EM 59").

### Prompt injection

When known issues exist for the target product, append to the article generation instructions:

```
## Bekannte Produkt-Hinweise (interne Quelle)
- [HIGH] Bluetooth-Verbindung bricht ab bei Health Manager Pro unter iOS 17+
Berücksichtige diese Information im Artikel: erwähne das Problem sachlich, biete Workarounds an falls bekannt, und vermeide Heilversprechen.
```

This is injected via `keyword_instructions` parameter, which is already passed to the Stage 2 writer.

### Salesforce integration (future)

When the Salesforce import pipeline (Task 3) is live, the `get_product_service_insights()` function from the Salesforce spec can populate `known_issues` entries with `source: "salesforce"` automatically, based on high-volume complaint patterns (e.g., >30% of cases for a product share the same reason → auto-flag as known issue).

This is deferred and out of scope for now.

### File manifest

| File | Action |
|------|--------|
| `blog/product_catalog.json` | Modify — add `known_issues` arrays to relevant products |
| `blog/product_catalog.py` | Modify — add `get_product_known_issues()` and `find_product_for_keyword()` |
| `blog/article_service.py` | Modify — inject known issues into article context |

---

## Task 5: Multi-Language Article Generation (English First)

### Context

On master, the article pipeline already accepts a `language` parameter:
- `blog/article_service.py:240` — `generate_article(language="de")`
- `blog/stage2/blog_writer.py:141` — `write_article(language="en", country="United States")`
- `blog/beurer_context.py:318` — `get_beurer_company_context(language="de")`
- DB: `blog_articles.language` column (default `'de'`)

The language parameter flows end-to-end. The gaps are:
1. No English-specific source selection / search guidance
2. No English buyer personas or tone context
3. No English product name mapping (pending Beurer confirmation)
4. `beurer_context.py` is German-focused

### Approach: Language-aware context in beurer_context.py

**File:** `blog/beurer_context.py`

The `get_beurer_company_context(language)` function already accepts language. Extend it:

**English context additions:**
```python
if language.startswith("en"):
    context["industry"] = "Health & Medical Technology"
    context["description"] = "Beurer is a German health technology company..."
    context["target_audience"] = "Health-conscious consumers in the UK and US..."
    context["value_propositions"] = [
        "German engineering quality and precision",
        "Clinically validated medical devices",
        ...
    ]
    context["tone"] = "professional, approachable"
    # English pain points, use cases, content themes
```

**Voice persona:** Add English voice/tone rules:
- Use "you" (informal, direct)
- No healing promises (same as German)
- UK/US spelling: default to UK English (Beurer's primary English market)
- Avoid Americanisms unless targeting US specifically

### English source selection

**File:** `blog/stage2/prompts/user_prompt.txt`

The Gemini writer uses Google Search grounding for sources. The prompt already receives `language` and `country` parameters. Add explicit English-market guidance when `language=en`:

```
Language: English
Country: United Kingdom

IMPORTANT: Use English-language sources only. Prioritize:
- UK health authority sites (NHS, NICE guidelines)
- English-language review sites (Which?, Trusted Reviews)
- English-language forums and communities
- PubMed / medical journals in English
Do NOT translate or cite German-language sources.
```

This is injected via the `custom_instructions_section` in the user prompt template, conditional on language.

**File:** `blog/article_service.py`

In `_build_instructions_from_context()`, add English-specific source guidance:

```python
if not is_de:
    lines.append(
        "Use only English-language sources. Prioritize UK/US health "
        "authorities (NHS, Mayo Clinic), English review sites, and "
        "English-language forums. Do not cite German sources."
    )
```

### Fallback strategy

The Gemini writer's Google Search grounding naturally returns language-appropriate results when the prompt is in English and specifies an English-speaking country. This is the primary mechanism — no separate English crawler or source database needed.

If Google Search doesn't return enough English sources, the writer falls back to its training knowledge (same as current German behavior).

### Product name mapping (deferred)

Pending confirmation from Beurer on whether English webshop uses different product names. For now, product model codes (BM 27, EM 59) are universal. The `product_catalog.json` can later gain an `english_name` field per product if needed.

### Dashboard article creation

**File:** `styles/dashboard_template.html`

The Content Planung tab's article generation UI needs a language selector:

```
Keyword: [___________________]
Language: [DE ▾]  ← dropdown: DE, EN
[Generate Article]
```

When `EN` is selected, pass `language: "en"` to the article generation API call. The article modal already shows the language badge in the header meta row.

### File manifest

| File | Action |
|------|--------|
| `blog/beurer_context.py` | Modify — add English context (industry, description, tone, personas) |
| `blog/article_service.py` | Modify — add English source guidance to `_build_instructions_from_context()` |
| `styles/dashboard_template.html` | Modify — add language selector to article generation UI |

---

## Task 6: hreflang Implementation

### Context

Beurer has a US subsidiary with its own domain. Publishing the same English content on `beurer.com/en` and the US site creates duplicate content risk. We need hreflang tags in the article HTML output.

Current state:
- `blog/shared/html_renderer.py:278` sets `<html lang="{language}">` but no hreflang link tags
- `blog/stage4/stage_4.py:85-94` strips hreflang from anchor tags (defensive, during URL replacement)
- No mechanism to link articles across languages
- `blog_articles` table has `language` column but no article grouping

### Article group linking

**File:** `migrations/011_blog_article_groups.sql` (new)

```sql
-- Group articles by topic across languages
ALTER TABLE blog_articles
ADD COLUMN IF NOT EXISTS article_group_id UUID;

-- Index for finding sibling articles
CREATE INDEX IF NOT EXISTS idx_blog_articles_group
ON blog_articles (article_group_id)
WHERE article_group_id IS NOT NULL;
```

**Behavior:**
- When generating an English version of a German article (same keyword), assign the same `article_group_id`
- When generating a standalone article, `article_group_id` is NULL (no siblings)
- Multiple articles can share a group (DE, EN, EN-US, etc.)

### Auto-linking logic

**File:** `blog/article_service.py`

When generating an article, check if a sibling exists in another language with the same keyword:

```python
# In generate_article(), after determining keyword + language
# Step 1: Check for any sibling article with same keyword in a different language
sibling = supabase.table("blog_articles") \
    .select("id, article_group_id") \
    .eq("keyword", keyword) \
    .neq("language", language) \
    .limit(1).execute()

if sibling.data:
    # Use existing group_id, or create one and backfill the sibling
    group_id = sibling.data[0].get("article_group_id")
    if not group_id:
        group_id = str(uuid4())
        supabase.table("blog_articles") \
            .update({"article_group_id": group_id}) \
            .eq("id", sibling.data[0]["id"]).execute()
else:
    group_id = None  # No sibling, no group needed yet

# Save new article with group_id
```

This handles both cases (sibling already has a group vs. sibling exists but no group yet) in a single query path.

### hreflang tag injection

**File:** `blog/shared/html_renderer.py`

Add a method to generate hreflang link tags and inject them into the HTML `<head>`:

```python
@staticmethod
def _render_hreflang_tags(
    current_language: str,
    siblings: list[dict],  # [{language, url}]
) -> str:
    """Generate hreflang link tags for alternate language versions."""
    if not siblings:
        return ""

    # Language-region mapping
    HREFLANG_MAP = {
        "de": "de",
        "en": "en",       # beurer.com/en (international English)
        "en-us": "en-US", # US site
    }

    tags = []
    for sib in siblings:
        lang = sib["language"]
        url = sib["url"]
        hreflang = HREFLANG_MAP.get(lang, lang)
        tags.append(f'<link rel="alternate" hreflang="{hreflang}" href="{url}">')

    # x-default points to German (primary market)
    de_url = next((s["url"] for s in siblings if s["language"] == "de"), None)
    if de_url:
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{de_url}">')

    return "\n    ".join(tags)
```

**Integration in `render()` method:**

In the HTML head construction (around line 320), after the OG meta tags:

```python
# hreflang tags (if siblings provided)
hreflang_html = HTMLRenderer._render_hreflang_tags(language, hreflang_siblings)
# Insert into <head> before </head>
```

The `render()` method needs an additional optional parameter `hreflang_siblings: list[dict] = None`.

### URL construction

hreflang tags need full URLs. Since Beurer manages the CMS URLs, the article needs a `publish_url` field (already exists in the `blog_articles` schema from migration 005). The hreflang URLs are constructed from sibling articles' `publish_url` values.

If `publish_url` is not set, hreflang tags are omitted (we can't generate valid hreflang without knowing the canonical URL).

### Rendering flow

1. Article is generated → saved with `article_group_id`
2. When rendering HTML (for export/preview), query sibling articles in the same group
3. For each sibling with a `publish_url`, include an hreflang link tag
4. The current article's own hreflang tag is also included (self-referencing, per Google spec)

### CMS recommendation document

**File:** `docs/hreflang-recommendation.md` (new)

Brief document for Simon to send to Beurer's CMS team:

- Explain hreflang purpose and Google's requirements
- Recommend: each article page in Makaria CMS should include hreflang tags pointing to all language versions
- Our pipeline outputs hreflang tags in the article HTML — CMS should preserve them or implement them server-side
- For the US site: use `hreflang="en-US"` with the US domain URL
- Canonical URL strategy: each language version is its own canonical (no cross-domain canonicals)
- Testing: use Google's Rich Results Test or Ahrefs Site Audit to verify hreflang implementation

### File manifest

| File | Action |
|------|--------|
| `migrations/011_blog_article_groups.sql` | New |
| `blog/shared/html_renderer.py` | Modify — add `_render_hreflang_tags()`, inject into `<head>` |
| `blog/article_service.py` | Modify — auto-link articles by keyword+language, set `article_group_id` |
| `docs/hreflang-recommendation.md` | New — CMS team guidance |

---

## Execution Order

| Priority | Task | Dependencies | Effort |
|----------|------|-------------|--------|
| 1 | Task 1: Meta SERP Preview | None | Small (1-2 hours) |
| 2 | Task 4: Known Issues | None | Small (1-2 hours) |
| 3 | Task 6: hreflang | None | Small (2-3 hours) |
| 4 | Task 2: AI Visibility | None | Medium (4-6 hours) |
| 5 | Task 5: Multi-Language | Task 6 (for linking) | Medium (3-4 hours) |
| 6 | Task 3: Salesforce Import | Existing spec complete | Large (6-8 hours) |

Tasks 1, 4, and 6 can be parallelized. Task 5 benefits from Task 6 being done first (article group linking). Task 3 follows its own existing spec.

## Open Items (Waiting on User)

- **Task 2:** Peec AI screenshot for layout reference
- **Task 3:** CSV column format from Dilyana, specific Customer Success tab metrics
- **Task 5:** English product catalog confirmation from Beurer
- **Task 5:** Whether to use `beurer.com/en` or a separate domain for English content
