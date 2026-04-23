# Content Planning & Article Generation Architecture

## Overview

The content planning system detects content opportunities from social listening data, enriches them with SEO metadata via LLM, and generates full blog articles with a complete editorial workflow. It spans three layers:

1. **Python backend** — detects content opportunities during weekly report generation, enriches with SEO metadata via Gemini 2.5 Pro
2. **Next.js dashboard** — TypeScript aggregator re-scores opportunities, Gemini 2.0 Flash generates/edits articles, serves the article viewer
3. **Admin portal** — approval workflow, topic suggestion, article viewing/editing

---

## System Diagram

```
Social Listening Data (social_items)
        │
        ▼
┌─────────────────────────┐
│  Weekly Report Pipeline  │  (Python: report/aggregator/)
│  - Detect opportunities  │
│  - Score by intent/gap   │
│  - Enrich via Gemini     │
│    2.5 Pro (SEO titles,  │
│    keywords, intent,     │
│    content brief)        │
└──────────┬──────────────┘
           │ stored in weekly_reports table
           ▼
┌─────────────────────────┐
│  Content Planning API    │  (dashboard/api/content-planning/)
│  - Re-score with TS      │
│  - Enrich topic titles   │
│  - Filter gap_score ≥ 2  │
│  - Cap at 50 results     │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐     ┌──────────────────────┐
│  Admin Portal            │────▶│  Article Generation   │
│  - Approve opportunities │     │  (Gemini 2.0 Flash)   │
│  - Suggest custom topics │     │  - Generate from      │
│  - View/edit articles    │     │    keyword + context   │
│  - Review status mgmt    │     │  - Regenerate w/      │
│                          │     │    feedback            │
│                          │     │  - Apply inline edits  │
└──────────────────────────┘     └──────────┬───────────┘
                                            │
                                            ▼
                                 ┌──────────────────────┐
                                 │  HTML Renderer         │
                                 │  - Self-contained HTML │
                                 │  - Beurer CI styling   │
                                 │  - Author card, TOC,   │
                                 │    FAQ, PAA, sources    │
                                 └──────────────────────┘
```

---

## 1. Content Opportunity Detection

### Source: Weekly Report Pipeline (Python)

**File:** `report/aggregator/product_intelligence.py` → `report/aggregator/enrichment.py`

During weekly report generation, the Python aggregator identifies content opportunities from crawled social items. Items with unanswered questions, high relevance, and strong intent signals are flagged as opportunities.

### Source: TypeScript Aggregator (Dashboard)

**File:** `dashboard/lib/aggregator/content-opportunities.ts`

**Function:** `buildContentOpportunities(items)` → top 10 opportunities

**Three-tier detection** (at least one must fire):

| Tier | Signal | Weight |
|------|--------|--------|
| LLM | `item.content_opportunity` is truthy | 3.0x |
| Intent | `INTENT_OPP_WEIGHTS[item.intent]` > 0 | 2.0x |
| Keyword | Title/content contains question words or `?` | 1.0x |

**Scoring formula (0–10 scale):**

| Factor | Multiplier | Description |
|--------|-----------|-------------|
| LLM signal | 3.0x | `content_opportunity` field exists |
| Intent weight | 2.0x | purchase_question=1.0, recommendation_request=0.9, general_question=0.7, troubleshooting=0.6, comparison=0.5 |
| Relevance | 1.5x | `relevance_score` (0.0–1.0) |
| Device relevance | 1.0x | `device_relevance_score` (0.0–1.0) |
| Unanswered boost | 1.0x | No answers = 1.0, one answer = 0.5 |
| Emotion boost | 0.5x | frustration/confusion/anxiety = 0.7 |
| Source boost | 0.5x | Preferred sources (gutefrage, reddit, health_forums) = 0.5 |
| Engagement boost | 0.5x | `engagement_score` capped at 50 |

**Minimum gap_score:** 2.0

---

## 2. Content Planning API

**File:** `dashboard/app/api/content-planning/route.ts`

**Endpoint:** `GET /api/content-planning`

**Flow:**
1. Query `weekly_reports` table (ordered by `week_start` DESC)
2. Extract `content_opportunities` array from each report's `report_data` JSON
3. Deduplicate by URL (most recent report wins)
4. Preserve LLM enrichment fields: `suggested_title`, `content_brief`, `search_intent`, `keywords`
5. Batch-fetch matching `social_items` by `source_url` (100 per batch)
6. Look up existing `blog_articles` by `source_item_id`
7. Re-score each opportunity with the TypeScript formula
8. Filter by `MIN_GAP_SCORE` (2.0), cap at 50, sort by `gap_score` DESC

**Caching:** 5-minute in-memory cache (bypassed when `approved_only=true`)

**Query params:**
- `approved_only=true` → filter to items in `approved_opportunities` table

---

## 3. SEO Enrichment

### Python Backend (Weekly Reports)

**File:** `report/text_generator.py` → `enrich_content_opportunities()`

**Model:** Gemini 2.5 Pro

Called during weekly report generation. Sends all opportunities in a single batch prompt. Returns per-opportunity:
- `suggested_title` — SEO-optimized German title (50–70 chars)
- `keywords` — 3–5 German keywords
- `search_intent` — Informational / Navigational / Transactional / Comparison
- `content_brief` — 1-sentence content recommendation (max 120 chars)

### Dashboard Topic Enrichment

**File:** `dashboard/lib/enrich-topics.ts`

**Function:** `enrichTopics(opportunities, lang)`

Refines raw forum/Reddit titles into concise, descriptive topic titles via Gemini. 15-minute cache by content hash.

### Admin "Suggest a Topic" (New)

**File:** `dashboard/app/api/admin/route.ts` → `action: enrich_topic`

**Model:** Gemini 2.0 Flash

User enters a free-text topic → Gemini generates SEO metadata inline:
- `suggested_title` — compelling article title
- `keywords[]` — 5–8 SEO keywords
- `search_intent` — one of four intent categories
- `content_brief` — 2–3 sentence brief

The enriched data populates an editable preview form. User can modify any field before triggering article generation.

---

## 4. Article Generation

### Origin: OpenBlog Neo (`blog/` package)

The current article generation system in `dashboard/lib/article-generator.ts` is a **direct TypeScript port** of the Python `blog/` package (OpenBlog Neo). The TS file explicitly states this: `// Port of blog/article_service.py + blog/stage2/blog_writer.py`.

**What was ported:**

| Python source | TypeScript port | What |
|---------------|-----------------|------|
| `blog/article_service.py` | `dashboard/lib/article-generator.ts` | `generateArticle()`, `regenerateArticle()`, `applyInlineEdits()` — identical function signatures and workflows |
| `blog/stage2/blog_writer.py` | `dashboard/lib/article-generator.ts` | System instruction, user prompt template, JSON schema — word-for-word identical |
| `blog/shared/html_renderer.py` | `dashboard/lib/html-renderer.ts` | `renderArticleHtml()`, `sanitizeHtml()`, `stripHtml()`, SVG icons — identical logic |
| `blog/shared/models.py` | (inline in article-generator.ts) | `ArticleOutput` schema (40+ fields) — identical field names |
| `blog/context.md` + `blog/persona.md` | (inline in article-generator.ts) | Beurer company context, voice persona, banned words — identical text |
| `blog/beurer_context.py` | `dashboard/lib/constants.ts` | Product catalogs, category labels — mirrors `report/constants.py` |

**What was simplified:** The Python `blog/` package has a more sophisticated 5-stage pipeline architecture:

```
Stage 1: Set Context (company research, competitor analysis — runs once per batch)
Stage 2: Blog Writer (Gemini generates article JSON — the core stage)
Stage 3: Review Agent (quality checks, fact verification)
Stage 4: HTTP Checker (validates source URLs are reachable)
Stage 5: Final Cleanup (formatting, consistency checks)
```

The TypeScript port collapses this into a **single Gemini call** (equivalent to Stage 2 only), which was sufficient for the dashboard's needs. Stages 1, 3, 4, and 5 were not ported.

**Current status:** The `blog/` Python package is **not actively running** in production — it is not imported by `app.py` or any route. All article generation runs through the TypeScript port on the Next.js dashboard (deployed on Vercel). The Python package remains in the codebase as the original reference implementation.

### Current Implementation

**File:** `dashboard/lib/article-generator.ts`

**Model:** Gemini 2.0 Flash (configurable via `GEMINI_MODEL` env var)
**Temperature:** 0.3

### Generation Flow

1. **Create** — `POST /api/blog-article` inserts row with `status: pending`
2. **Generate** — `generateArticle()` runs async (non-blocking response)
   - Builds system instruction with company context (Beurer products, competitors, categories)
   - Builds user prompt with keyword, word count, language, social context
   - Calls Gemini in JSON mode
   - Receives structured `ArticleOutput` JSON
   - Calls `renderArticleHtml()` to produce self-contained HTML
   - Updates DB: `article_html`, `article_json`, `headline`, `meta_description`, `word_count`, `status: completed`

### Article JSON Schema (Gemini Output)

| Field | Description |
|-------|-------------|
| `Headline` | Max 70 chars, includes keyword |
| `Subtitle` | Optional |
| `Teaser` | 2–3 sentence hook |
| `Direct_Answer` | 40–60 words for featured snippets |
| `Intro` | 80–120 words framing the problem |
| `Meta_Title` | Max 55 chars |
| `Meta_Description` | Max 130 chars with CTA |
| `section_01–09_title/content` | 4–6 content sections with HTML |
| `key_takeaway_01–03` | 3 key takeaways |
| `paa_01–04_question/answer` | People Also Ask (4 Q&As) |
| `faq_01–06_question/answer` | FAQ (5–6 Q&As) |
| `Sources` | **Mandatory** — 3–5 real URLs with title, url, description |
| `tables` | Optional comparison tables |

### Company Context

- **Company:** Beurer (German health device company)
- **Target audience:** 35–65 year old health-conscious German consumers
- **Products:** Blood pressure monitors (28 Beurer + 13 competitor), TENS/EMS devices, infrared lamps
- **Tone:** Professional, empathetic, trustworthy (German Sie-Form)
- **Hard rules:** No invented stats, no competitor names, no em-dashes, no robotic phrases

---

## 5. HTML Rendering

**File:** `dashboard/lib/html-renderer.ts`

**Function:** `renderArticleHtml(options)` → complete self-contained HTML document

**Features:**
- Beurer CI colors (primary `#C50050`)
- Semantic HTML5 structure
- Auto-generated Table of Contents
- Direct answer box (featured snippet targeting)
- Section content with inline images
- Comparison tables
- Key takeaways box
- PAA and FAQ sections
- Sources with clickable links
- Author card (name, title, bio, credentials, LinkedIn, photo)
- Reading time estimate (words ÷ 200 WPM)
- HTML sanitization (strips scripts, iframes, event handlers)

---

## 6. Article Editing & Review

### Editing Modes

| Mode | How | What happens |
|------|-----|-------------|
| **Inline comments** | Select text in iframe → add comment | Highlights passage, stores comment. "Apply Inline Edits" sends all to Gemini for revision. |
| **Regenerate with feedback** | Enter feedback in textarea → click Regenerate | Full re-generation incorporating feedback. Appends to `feedback_history`. |
| **Regenerate from scratch** | Click "Regenerate from Scratch" | New generation ignoring previous content. |
| **Direct HTML edit** | Click "Edit HTML" → edit in iframe | Makes iframe `contentEditable`. Save writes custom HTML to DB. Sets `html_custom: true`. |
| **Reset edits** | Click "Reset" | Re-renders from `article_json` via `renderArticleHtml()`. Clears `html_custom`. |

### Inline Edits Flow

**File:** `dashboard/lib/article-generator.ts` → `applyInlineEdits()`

1. User selects text passages in the article and adds comments
2. Frontend sends `PATCH /api/blog-article` with `edits: [{ passage_text, comment }]`
3. Backend calls Gemini with each passage + comment
4. Gemini returns revised text for each passage
5. HTML is updated with string replacements
6. `feedback_history` gets an `inline_edit` entry with count and passage previews
7. `html_custom` is set to `true`

### Feedback History

Every edit action appends to the `feedback_history` JSONB array:

```json
{
  "type": "regeneration" | "inline_edit" | "from_scratch",
  "comment": "user feedback text",
  "version": 2,
  "created_at": "2026-03-10T...",
  "edits_applied": 3  // for inline_edit type
}
```

### Review Status

Articles progress through: `draft` → `review` → `approved` → `published`

Only `approved` articles appear in the public dashboard's Articles tab.

---

## 7. Admin Portal

**File:** `dashboard/app/api/admin/route.ts`

**URL:** `/api/admin` (separate auth via `ADMIN_PASSWORD` env var)

### Features

#### Content Opportunity Approval
- Table of detected opportunities ranked by gap_score
- Approve/unapprove toggle (max 10 approved at a time)
- Approved opportunities stored in `approved_opportunities` table
- Approved items used to filter which articles appear in the dashboard

#### Suggest a Topic (Added 2026-03-10)
Two-step flow for manually creating articles:
1. **Enrich** — Enter a topic + language → Gemini generates SEO metadata (title, keywords, intent, brief)
2. **Generate** — Review/edit the enriched fields → click "Generate Article" to create

Triggered by clicking "Suggest" button or pressing Enter in the topic input.

#### Article Viewer/Editor Modal (Added 2026-03-10)
Full article editing modal ported from the dashboard, accessible via "View" button on completed editorial articles:

- **Viewer mode** — article rendered in sandboxed iframe, full-width
- **Editor panel** (sidebar) with:
  - Review status dropdown (draft/review/approved/published)
  - Feedback history display
  - Inline comments system (select text → add comment → apply edits via Gemini)
  - Feedback textarea + regeneration buttons
- **HTML edit mode** — toggle contentEditable on iframe, save/reset
- **Export** — download as HTML, copy HTML to clipboard, save as Markdown
- **Keyboard shortcuts** — Escape to close, Ctrl+Enter to submit inline comment

#### Editorial Articles Table
- Lists standalone articles (no `source_item_id`)
- Shows status (Completed/Generating/Failed/Pending) and review status (Draft/Approved)
- "View" button opens the article modal for completed articles
- "Approve" button toggles `review_status`

---

## 8. Database Schema

### `blog_articles`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `source_item_id` | UUID FK → social_items | Nullable. Links to source social item. |
| `keyword` | TEXT | Generation keyword/topic |
| `headline` | TEXT | Generated headline |
| `meta_description` | TEXT | SEO meta description |
| `article_html` | TEXT | Rendered HTML (generated or custom) |
| `article_json` | JSONB | Structured article data from Gemini |
| `language` | TEXT | `de` or `en` |
| `word_count` | INTEGER | |
| `status` | TEXT | `pending` / `generating` / `completed` / `failed` / `regenerating` |
| `error_message` | TEXT | If generation failed |
| `social_context` | JSONB | Context from social item |
| `feedback_history` | JSONB[] | Array of feedback/edit entries |
| `review_status` | TEXT | `draft` / `review` / `approved` / `published` |
| `html_custom` | BOOLEAN | `true` if manually edited |
| `author_id` | UUID FK → blog_authors | Nullable |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### `approved_opportunities`

| Column | Type | Description |
|--------|------|-------------|
| `source_url` | TEXT PK | URL of the social item |
| `source_item_id` | UUID | FK to social_items |

### `blog_authors`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `name` | TEXT | Author name |
| `title` | TEXT | Job title |
| `bio` | TEXT | Author bio |
| `image_url` | TEXT | Profile picture URL |
| `credentials` | TEXT[] | e.g. `["MD", "PhD"]` |
| `linkedin_url` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

### `article_comments`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `article_id` | UUID FK → blog_articles | CASCADE delete |
| `author` | TEXT | Reviewer name |
| `comment_text` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

---

## 9. API Reference

### Content Planning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/content-planning` | List scored content opportunities |
| GET | `/api/content-planning?approved_only=true` | Approved opportunities only |

### Blog Articles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/blog-article` | List articles (50 most recent) |
| GET | `/api/blog-article?id=<uuid>` | Get single article |
| GET | `/api/blog-article?source_item_id=<uuid>` | Check if article exists for source |
| GET | `/api/blog-article?id=<uuid>&comments=true` | Get article comments |
| POST | `/api/blog-article` | Create article + start generation |
| PUT | `/api/blog-article` | Regenerate with feedback |
| PATCH | `/api/blog-article` | Multiple actions (see below) |

**PATCH actions:**

| Action | Body | Description |
|--------|------|-------------|
| `review_status` | `{ article_id, review_status }` | Update review status |
| `save_html` | `{ article_id, article_html }` | Save custom HTML |
| `reset_html` | `{ article_id }` | Re-render from article_json |
| `add_comment` | `{ article_id, author, comment_text }` | Add review comment |
| `delete_comment` | `{ article_id, comment_id }` | Delete comment |
| `assign_author` | `{ article_id, author_id }` | Assign author |
| _(no action)_ | `{ article_id, edits: [...] }` | Apply inline edits |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin` | Admin page (login or dashboard) |
| POST | `/api/admin` | Login, approve, unapprove, enrich_topic, suggest_topic |

### Authors

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/blog-authors` | List all authors |
| POST | `/api/blog-authors` | Create author |

---

## 10. Key Files

| File | Purpose |
|------|---------|
| `dashboard/app/api/content-planning/route.ts` | Content opportunity scoring & serving |
| `dashboard/app/api/blog-article/route.ts` | Article CRUD (GET/POST/PUT/PATCH) |
| `dashboard/app/api/admin/route.ts` | Admin portal (approval, topic suggestion, article modal) |
| `dashboard/app/api/blog-authors/route.ts` | Author management |
| `dashboard/lib/article-generator.ts` | Gemini article generation, regeneration, inline edits |
| `dashboard/lib/html-renderer.ts` | Article JSON → self-contained HTML |
| `dashboard/lib/aggregator/content-opportunities.ts` | TypeScript opportunity scoring |
| `dashboard/lib/enrich-topics.ts` | Topic title refinement via Gemini |
| `report/text_generator.py` | Python SEO enrichment (weekly reports) |
| `report/aggregator/enrichment.py` | Enrichment pipeline orchestration |
| `styles/dashboard_template.html` | Dashboard UI with article modal (source of truth) |
| `blog/` | OpenBlog Neo — original Python article generation pipeline (not active, TS port used instead) |
| `blog/article_service.py` | Original Python source for `generateArticle`, `regenerateArticle`, `applyInlineEdits` |
| `blog/stage2/blog_writer.py` | Original Gemini prompts and JSON schema (ported to article-generator.ts) |
| `blog/shared/html_renderer.py` | Original HTML renderer (ported to html-renderer.ts) |
| `blog/shared/models.py` | ArticleOutput Pydantic model — defines the 40+ field JSON schema |
| `blog/pipeline.py` | 5-stage pipeline orchestrator (Stage 1–5, parallel per article) |
